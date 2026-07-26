# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""Validation and planner adaptation for required user-selected town stops."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from cairn.api.plan_request import PlanAPIRequest, PlanAPIValidationError
from cairn.api.trail_inventory import build_trail_inventory_response


TOWN_STOP_OPTIONS_VERSION = "cairnos_town_stop_options_v1"
TOWN_STOP_STATUS_VERSION = "cairnos_town_stops_v1"


def resolve_town_stop_contract(request: PlanAPIRequest) -> dict[str, Any]:
    inventory = build_trail_inventory_response(
        request.trail_id,
        direction=request.direction,
        start_access_id=request.start_access_id if request.trip_type == "SECTION" else None,
        end_access_id=request.end_access_id if request.trip_type == "SECTION" else None,
    )
    options = inventory["town_stop_options"]["options"]
    route_extent = inventory.get("route_extent")
    endpoint_total_miles = float(
        route_extent["distance_miles"]
        if route_extent
        else inventory["direction_model"]["trail_total_miles"]
    )
    options_by_town = {option["town_inventory_id"]: option for option in options}
    resolved: list[dict[str, Any]] = []
    access_to_town: dict[str, str] = {}
    for selection in request.town_stop_selections:
        town_id = selection["town_inventory_id"]
        option = options_by_town.get(town_id)
        if option is None:
            raise PlanAPIValidationError(
                "The selected town is not available on the selected route extent.",
                code="town_stop_unknown_or_outside_extent",
                context={"town_inventory_id": town_id},
            )
        unsupported = sorted(set(selection["intents"]) - set(option["supported_intents"]))
        if unsupported:
            raise PlanAPIValidationError(
                f"{option['town_name']} does not support: {', '.join(unsupported)}.",
                code="town_stop_intent_unsupported",
                context={
                    "town_inventory_id": town_id,
                    "unsupported_intents": unsupported,
                },
            )
        experience_options = {
            item["experience_inventory_id"]: item
            for item in option["experiences"]
        }
        for experience_id in selection["experience_inventory_ids"]:
            if experience_id not in experience_options:
                raise PlanAPIValidationError(
                    "The selected experience does not belong to the selected town.",
                    code="town_stop_experience_parent_mismatch",
                    context={
                        "town_inventory_id": town_id,
                        "experience_inventory_id": experience_id,
                    },
                )
        access_id = option["access_inventory_id"]
        conflicting_town = access_to_town.get(access_id)
        if conflicting_town is not None:
            raise PlanAPIValidationError(
                "Two selected towns use the same trail access point.",
                code="town_stop_shared_access_conflict",
                context={
                    "town_inventory_id": town_id,
                    "conflicting_town_inventory_id": conflicting_town,
                    "access_inventory_id": access_id,
                },
            )
        access_to_town[access_id] = town_id
        endpoint_mile = float(
            option.get("section_relative_mile", option["directional_mile"])
        )
        resolved.append(
            {
                **selection,
                **option,
                "_route_endpoint": (
                    endpoint_mile <= 0
                    or endpoint_mile >= endpoint_total_miles
                ),
            }
        )

    resolved.sort(
        key=lambda item: (float(item["directional_mile"]), item["town_inventory_id"])
    )
    resupply_anchors = [
        {
            "inventory_id": item["town_inventory_id"],
            "kind": "town",
            "display_name": item["town_name"],
            "canonical_mile": float(item["canonical_mile"]),
            "planner_node_id": _planner_node_id(item),
            "town_name": item["town_name"],
            "town_stop": True,
        }
        for item in resolved
        if "resupply" in item["intents"]
    ]
    overnight_anchors = [
        {
            "inventory_id": item["town_inventory_id"],
            "kind": "town",
            "display_name": item["town_name"],
            "canonical_mile": float(item["canonical_mile"]),
            "overlay_id": item["access_overlay_id"],
            "town_stop": True,
        }
        for item in resolved
        if (
            not item["_route_endpoint"]
            and any(
                intent in {"zero", "nero", "experience"}
                for intent in item["intents"]
            )
        )
    ]
    return {
        "contract_version": TOWN_STOP_OPTIONS_VERSION,
        "selections": resolved,
        "required_overnight_anchors": overnight_anchors,
        "required_resupply_anchors": resupply_anchors,
    }


def apply_town_stop_contract(
    itinerary: dict[str, Any],
    contract: dict[str, Any],
    *,
    nero_max_trail_miles: float | None,
    planned_start_date: str | None = None,
) -> dict[str, Any]:
    selections = contract["selections"]
    if not selections:
        itinerary["town_stop_status"] = _status([], [])
        return itinerary

    daily_plan = list(itinerary.get("daily_plan", []))
    resupply_plan = list(itinerary.get("resupply_plan", []))
    statuses: list[dict[str, Any]] = []
    zero_insertions: list[tuple[int, dict[str, Any]]] = []
    for selection in selections:
        town_id = selection["town_inventory_id"]
        matching_days = [
            row for row in daily_plan
            if row.get("required_overnight_anchor_id") == town_id
        ]
        matching_resupply = [
            row for row in resupply_plan if row.get("required_anchor_id") == town_id
        ]
        if "resupply" in selection["intents"] and len(matching_resupply) != 1:
            raise _infeasible(selection, "resupply_exactly_once")
        matched_at_start = False
        if len(matching_days) == 1:
            day_row = matching_days[0]
        elif selection.get("_route_endpoint"):
            day_row, matched_at_start = _endpoint_day(daily_plan, selection)
            if day_row is None:
                raise _infeasible(selection, "route_endpoint_once")
        elif set(selection["intents"]) == {"resupply"} and len(matching_resupply) == 1:
            resupply_day = int(matching_resupply[0]["day"])
            day_row = next(
                (row for row in daily_plan if int(row["day"]) == resupply_day),
                None,
            )
            if day_row is None:
                raise _infeasible(selection, "resupply_day_once")
        else:
            raise _infeasible(selection, "required_stop_exactly_once")
        planned_day = int(day_row["day"])
        intents = list(selection["intents"])
        preference_exceeded = False
        if "nero" in intents:
            miles = float(day_row.get("daily_miles") or 0)
            preference_exceeded = bool(
                nero_max_trail_miles is not None
                and miles > nero_max_trail_miles
            )
            day_row["town_stop_nero"] = True
            day_row["town_stop_nero_max_trail_miles"] = nero_max_trail_miles
            day_row["town_stop_nero_preference_exceeded"] = preference_exceeded
        day_row["town_stop_inventory_id"] = town_id
        day_row["town_stop_intents"] = intents
        day_row["town_stop_experience_inventory_ids"] = list(
            selection["experience_inventory_ids"]
        )
        selected_experience_names = [
            item["name"]
            for item in selection["experiences"]
            if item["experience_inventory_id"]
            in selection["experience_inventory_ids"]
        ]
        if selected_experience_names:
            day_row["selected_side_trips"] = "; ".join(selected_experience_names)
        if "zero" in intents:
            zero_insertions.append(
                (
                    daily_plan.index(day_row) + (0 if matched_at_start else 1),
                    _zero_row(day_row, selection, at_start=matched_at_start),
                )
            )
        status = {
            "town_inventory_id": town_id,
            "access_inventory_id": selection["access_inventory_id"],
            "planned_day": planned_day,
            "planned_date": day_row.get("date"),
            "intents": intents,
            "experience_inventory_ids": list(selection["experience_inventory_ids"]),
            "status": "satisfied",
        }
        if "nero" in intents:
            status.update(
                {
                    "planned_trail_miles": float(day_row.get("daily_miles") or 0),
                    "nero_max_trail_miles": nero_max_trail_miles,
                    "nero_preference_exceeded": preference_exceeded,
                }
            )
        statuses.append(status)

    for index, row in reversed(zero_insertions):
        daily_plan.insert(index, row)
    day_mapping = _renumber_calendar(
        daily_plan,
        resupply_plan,
        statuses,
        planned_start_date=planned_start_date,
    )
    itinerary["daily_plan"] = daily_plan
    itinerary["resupply_plan"] = resupply_plan
    _append_legacy_selected_experiences(itinerary, selections, statuses)
    _remove_internal_town_anchors(itinerary, selections)
    _update_calendar_summaries(itinerary, day_mapping, len(daily_plan))
    itinerary["town_stop_status"] = _status(selections, statuses)
    return itinerary


def _planner_node_id(option: dict[str, Any]) -> str:
    access = option.get("access", {})
    label = access.get("access_label") or option["access_name"]
    return f"{label}:{float(option['canonical_mile']):.1f}"


def _endpoint_day(
    daily_plan: list[dict[str, Any]],
    selection: dict[str, Any],
) -> tuple[dict[str, Any] | None, bool]:
    mile = float(selection["canonical_mile"])
    for row in daily_plan:
        if abs(float(row.get("daily_start_mile") or 0) - mile) <= 0.15:
            return row, True
        if abs(float(row.get("daily_stop_mile") or 0) - mile) <= 0.15:
            return row, False
    return None, False


def _zero_row(
    day_row: dict[str, Any],
    selection: dict[str, Any],
    *,
    at_start: bool = False,
) -> dict[str, Any]:
    row = dict(day_row)
    if at_start:
        mile = float(selection["canonical_mile"])
        location = selection["access_name"]
        row.update(
            {
                "daily_start_mile": mile,
                "daily_start_location": location,
                "daily_start_canonical_location": location,
                "daily_stop_mile": mile,
                "daily_stop_location": location,
                "daily_stop_canonical_location": location,
                "daily_stop_location_type": "town",
                "town_access": selection["town_name"],
            }
        )
    row.update(
        {
            "daily_miles": 0.0,
            "daily_elevation_gain": 0.0,
            "notes": "town stop / zero",
            "town_stop_zero": True,
            "town_stop_inventory_id": selection["town_inventory_id"],
            "town_stop_intents": list(selection["intents"]),
            "required_overnight_anchor_id": None,
            "required_resupply_anchors": [],
            "resupply_location": "",
            "resupply_mile": None,
            "resupply_location_type": "",
        }
    )
    return row


def _renumber_calendar(
    daily_plan: list[dict[str, Any]],
    resupply_plan: list[dict[str, Any]],
    statuses: list[dict[str, Any]],
    *,
    planned_start_date: str | None,
) -> dict[int, int]:
    old_to_new: dict[int, int] = {}
    start_date: date | None = None
    if planned_start_date:
        try:
            start_date = date.fromisoformat(planned_start_date)
        except ValueError:
            start_date = None
    for index, row in enumerate(daily_plan, start=1):
        old_day = int(row.get("day", index))
        old_to_new.setdefault(old_day, index)
        row["day"] = index
        if start_date is None and row.get("date"):
            try:
                start_date = date.fromisoformat(str(row["date"])) - timedelta(days=index - 1)
            except ValueError:
                start_date = None
        if start_date is not None:
            row["date"] = (start_date + timedelta(days=index - 1)).isoformat()
    for row in resupply_plan:
        row["day"] = old_to_new.get(int(row["day"]), int(row["day"]))
    for row in statuses:
        row["planned_day"] = old_to_new.get(row["planned_day"], row["planned_day"])
        matching = next(
            (day for day in daily_plan if day["day"] == row["planned_day"]), None
        )
        row["planned_date"] = matching.get("date") if matching else row["planned_date"]
    return old_to_new


def _remove_internal_town_anchors(
    itinerary: dict[str, Any],
    selections: list[dict[str, Any]],
) -> None:
    town_ids = {item["town_inventory_id"] for item in selections}
    status = itinerary.get("required_anchors", {})
    for key in (
        "required_resupply_anchor_ids",
        "satisfied_resupply_anchor_ids",
    ):
        status[key] = [item for item in status.get(key, []) if item not in town_ids]


def _append_legacy_selected_experiences(
    itinerary: dict[str, Any],
    selections: list[dict[str, Any]],
    statuses: list[dict[str, Any]],
) -> None:
    status_by_town = {row["town_inventory_id"]: row for row in statuses}
    rows = itinerary.setdefault("selected_experiences", [])
    for selection in selections:
        status = status_by_town[selection["town_inventory_id"]]
        selected_ids = set(selection["experience_inventory_ids"])
        for experience in selection["experiences"]:
            if experience["experience_inventory_id"] not in selected_ids:
                continue
            rows.append(
                {
                    "day": status["planned_day"],
                    "location": selection["access_name"],
                    "mile": selection["canonical_mile"],
                    "town_access": selection["town_name"],
                    "experience_name": experience["name"],
                    "category": experience.get("category", ""),
                    "estimated_time": experience.get("estimated_time", ""),
                    "planning_notes": experience.get("planning_notes", ""),
                    "access_distance_miles": selection.get("access", {}).get(
                        "access_distance_miles"
                    ),
                    "access_notes": selection.get("access", {}).get(
                        "access_notes", ""
                    ),
                    "validation_status": experience.get(
                        "validation_status", "validated"
                    ),
                    "validation_date": experience.get("validation_date", ""),
                    "planning_status": "planned",
                    "town_inventory_id": selection["town_inventory_id"],
                    "access_inventory_id": selection["access_inventory_id"],
                    "experience_inventory_id": experience[
                        "experience_inventory_id"
                    ],
                }
            )


def _update_calendar_summaries(
    itinerary: dict[str, Any],
    day_mapping: dict[int, int],
    completion_days: int,
) -> None:
    itinerary.setdefault("expedition_summary", {})["completion_days"] = completion_days
    analysis = itinerary.get("completion_analysis", {})
    for key in ("evaluation", "generated_evaluation"):
        generated = analysis.get(key)
        if isinstance(generated, dict):
            generated["completion_days"] = completion_days
            _renumber_day_lists(generated, day_mapping)
    _renumber_day_lists(analysis, day_mapping)


def _renumber_day_lists(payload: dict[str, Any], day_mapping: dict[int, int]) -> None:
    for key in (
        "combined_exception_days",
        "compound_exception_days",
        "days",
    ):
        values = payload.get(key)
        if isinstance(values, list) and all(isinstance(item, int) for item in values):
            payload[key] = [day_mapping.get(item, item) for item in values]
    for exception in payload.get("itinerary_exceptions", []):
        if isinstance(exception, dict):
            _renumber_day_lists(exception, day_mapping)


def _status(
    selections: list[dict[str, Any]],
    stops: list[dict[str, Any]],
) -> dict[str, Any]:
    requested = [item["town_inventory_id"] for item in selections]
    satisfied = [item["town_inventory_id"] for item in stops]
    return {
        "contract_version": TOWN_STOP_STATUS_VERSION,
        "semantics": "required_user_selected_town_stops",
        "requested_town_stop_ids": requested,
        "satisfied_town_stop_ids": satisfied,
        "unsatisfied_town_stop_ids": [item for item in requested if item not in satisfied],
        "stops": stops,
    }


def _infeasible(selection: dict[str, Any], constraint: str) -> PlanAPIValidationError:
    return PlanAPIValidationError(
        f"{selection['town_name']} could not be included with the current itinerary.",
        code="town_stop_infeasible",
        context={
            "town_inventory_id": selection["town_inventory_id"],
            "access_inventory_id": selection["access_inventory_id"],
            "constraint": constraint,
        },
    )
