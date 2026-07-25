# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""Request validation for CairnOS Plan API payloads."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from cairn.api.access_points import (
    normalize_access_point_anchors,
    normalize_route_extent,
)
from cairn.api.plan_controls import plan_control_spec
from cairn.api.route_selection import (
    NONE_EGRESS_ROUTE_NAME,
    NONE_INGRESS_ROUTE_NAME,
    normalize_route_selection,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LONG_TRAIL_ROOT = PROJECT_ROOT / "trails" / "vermont_long_trail"

LONG_TRAIL_ID = "vermont_long_trail"
VALID_DIRECTIONS = {"NOBO", "SOBO"}
VALID_TRIP_TYPES = {"THRU", "SECTION"}
VALID_RECOVERY_PLANNING_MODES = {"cadence", "target_counts"}
VALID_INGRESS_ROUTES_BY_DIRECTION = {
    "NOBO": {
        "Williamstown Approach",
        "North Adams Approach",
    },
    "SOBO": {
        "Journey's End Trail",
    },
}
VALID_EGRESS_ROUTES_BY_DIRECTION = {
    "NOBO": {
        "Journey's End Trail",
    },
    "SOBO": {
        "Williamstown Approach",
        "North Adams Approach",
    },
}


class PlanAPIValidationError(ValueError):
    """Raised when a Plan API request payload is invalid."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "validation_error",
        context: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.context = dict(context or {})


@dataclass(frozen=True)
class PlanAPIRequest:
    """Validated HikerLogix-native MVP request for a CairnOS plan."""

    trail_id: str
    trip_type: str
    direction: str
    ingress_route: str
    egress_route: str
    desired_days: int
    min_daily_miles: float
    max_daily_miles: float
    max_daily_elevation: float
    resupply_cadence: int
    recovery_cadence: int
    recovery_planning_mode: str = "cadence"
    target_zero_days: int = 0
    target_nero_days: int = 0
    min_nero_miles: float = 5.0
    max_nero_miles: float = 8.0
    allow_extra_resupply_only: bool = True
    avoid_long_food_carry: bool = True
    prefer_bear_box_sites: bool = False
    convenient_resupply_distance_miles: float = 1.0
    selected_side_trip_ids: tuple[str, ...] = ()
    selected_town_ids: tuple[str, ...] = ()
    required_overnight_anchor_ids: tuple[str, ...] = ()
    required_resupply_anchor_ids: tuple[str, ...] = ()
    start_access_id: str | None = None
    end_access_id: str | None = None
    route_extent: dict[str, Any] | None = None
    access_point_anchors: tuple[dict[str, Any], ...] = ()
    route_selection: dict[str, str] | None = None
    planned_start_date: str | None = None
    town_stop_selections: tuple[dict[str, Any], ...] = ()
    nero_max_trail_miles: float | None = None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> PlanAPIRequest:
        required_fields = (
            "trail_id",
            "direction",
            "desired_days",
            "min_daily_miles",
            "max_daily_miles",
            "max_daily_elevation",
            "resupply_cadence",
            "recovery_cadence",
        )
        missing_fields = [field for field in required_fields if field not in payload]
        if missing_fields:
            raise PlanAPIValidationError(
                f"Missing required field(s): {', '.join(missing_fields)}"
            )

        trail_id = payload["trail_id"]
        if trail_id != LONG_TRAIL_ID:
            raise PlanAPIValidationError(
                f"trail_id must be {LONG_TRAIL_ID!r} for the MVP Plan API"
            )

        direction = payload["direction"]
        if direction not in VALID_DIRECTIONS:
            raise PlanAPIValidationError("direction must be one of: NOBO, SOBO")

        trip_type = payload.get("trip_type", "THRU")
        if not isinstance(trip_type, str) or trip_type not in VALID_TRIP_TYPES:
            raise PlanAPIValidationError("trip_type must be one of: SECTION, THRU")

        if trip_type == "THRU":
            missing_routes = [
                field_name
                for field_name in ("ingress_route", "egress_route")
                if field_name not in payload
            ]
            if missing_routes:
                raise PlanAPIValidationError(
                    f"Missing required field(s): {', '.join(missing_routes)}"
                )
            ingress_route = _validate_route_name(
                payload["ingress_route"], "ingress_route"
            )
            egress_route = _validate_route_name(
                payload["egress_route"], "egress_route"
            )
            _validate_directional_access_route(
                ingress_route,
                "ingress_route",
                VALID_INGRESS_ROUTES_BY_DIRECTION[direction],
            )
            _validate_directional_access_route(
                egress_route,
                "egress_route",
                VALID_EGRESS_ROUTES_BY_DIRECTION[direction],
            )
        else:
            ingress_route = payload.get("ingress_route", NONE_INGRESS_ROUTE_NAME)
            egress_route = payload.get("egress_route", NONE_EGRESS_ROUTE_NAME)
            if ingress_route != NONE_INGRESS_ROUTE_NAME:
                raise PlanAPIValidationError(
                    f"ingress_route must be {NONE_INGRESS_ROUTE_NAME!r} "
                    "for SECTION plans"
                )
            if egress_route != NONE_EGRESS_ROUTE_NAME:
                raise PlanAPIValidationError(
                    f"egress_route must be {NONE_EGRESS_ROUTE_NAME!r} "
                    "for SECTION plans"
                )

        desired_days = _payload_control_int(
            payload,
            "desired_days",
            required=True,
        )

        min_daily_miles = _payload_control_number(
            payload,
            "min_daily_miles",
            required=True,
        )
        max_daily_miles = _payload_control_number(
            payload,
            "max_daily_miles",
            required=True,
        )
        max_daily_elevation = _payload_control_number(
            payload,
            "max_daily_elevation",
            required=True,
        )

        if max_daily_miles < min_daily_miles:
            raise PlanAPIValidationError(
                "max_daily_miles must be greater than or equal to min_daily_miles"
            )

        resupply_cadence = _payload_control_int(
            payload,
            "resupply_cadence",
            required=True,
        )
        recovery_cadence = _payload_control_int(
            payload,
            "recovery_cadence",
            required=True,
        )

        recovery_planning_mode = _payload_choice(
            payload,
            "recovery_planning_mode",
            default=plan_control_spec("recovery_planning_mode")["default"],
            choices=VALID_RECOVERY_PLANNING_MODES,
        )

        target_zero_days = _target_count_value(
            payload,
            "target_zero_days",
            recovery_planning_mode,
        )
        target_nero_days = _target_count_value(
            payload,
            "target_nero_days",
            recovery_planning_mode,
        )
        min_nero_miles = _payload_control_number(
            payload,
            "min_nero_miles",
        )
        max_nero_miles = _payload_control_number(
            payload,
            "max_nero_miles",
        )
        if max_nero_miles < min_nero_miles:
            raise PlanAPIValidationError(
                "max_nero_miles must be greater than or equal to min_nero_miles"
            )

        allow_extra_resupply_only = _payload_bool(
            payload,
            "allow_extra_resupply_only",
        )
        avoid_long_food_carry = _payload_bool(
            payload,
            "avoid_long_food_carry",
        )
        prefer_bear_box_sites = _payload_bool(
            payload,
            "prefer_bear_box_sites",
        )
        convenient_resupply_distance_miles = _payload_control_number(
            payload,
            "convenient_resupply_distance_miles",
        )
        selected_side_trip_ids = _payload_string_list(
            payload,
            "selected_side_trip_ids",
        )
        selected_town_ids = _payload_string_list(
            payload,
            "selected_town_ids",
        )
        required_overnight_anchor_ids = _payload_unique_string_list(
            payload,
            "required_overnight_anchor_ids",
        )
        required_resupply_anchor_ids = _payload_unique_string_list(
            payload,
            "required_resupply_anchor_ids",
        )
        town_stop_selections = _payload_town_stop_selections(payload)
        has_selected_nero = any(
            "nero" in selection["intents"]
            for selection in town_stop_selections
        )
        nero_max_trail_miles = None
        if "nero_max_trail_miles" in payload:
            nero_max_trail_miles = _payload_optional_control_number(
                payload,
                "nero_max_trail_miles",
            )
        if has_selected_nero and nero_max_trail_miles is None:
            raise PlanAPIValidationError(
                "nero_max_trail_miles is required when a town stop has nero intent"
            )

        try:
            route_extent = normalize_route_extent(
                trip_type=trip_type,
                direction=direction,
                start_access_id=payload.get("start_access_id"),
                end_access_id=payload.get("end_access_id"),
                trail_root=LONG_TRAIL_ROOT,
                trail_id=trail_id,
            )
            access_point_anchors = normalize_access_point_anchors(
                payload.get("access_point_anchors", []),
                route_extent=route_extent,
                trail_root=LONG_TRAIL_ROOT,
                trail_id=trail_id,
            )
        except ValueError as error:
            raise PlanAPIValidationError(str(error)) from None

        try:
            route_selection = normalize_route_selection(
                payload,
                direction=direction,
                ingress_route=ingress_route,
                egress_route=egress_route,
                trail_root=LONG_TRAIL_ROOT,
                trip_type=trip_type,
            )
        except ValueError as error:
            raise PlanAPIValidationError(str(error)) from None

        planned_start_date = payload.get("planned_start_date")
        if planned_start_date is not None and not isinstance(planned_start_date, str):
            raise PlanAPIValidationError("planned_start_date must be a string")

        return cls(
            trail_id=trail_id,
            trip_type=trip_type,
            direction=direction,
            ingress_route=ingress_route,
            egress_route=egress_route,
            desired_days=desired_days,
            min_daily_miles=min_daily_miles,
            max_daily_miles=max_daily_miles,
            max_daily_elevation=max_daily_elevation,
            resupply_cadence=resupply_cadence,
            recovery_cadence=recovery_cadence,
            recovery_planning_mode=recovery_planning_mode,
            target_zero_days=target_zero_days,
            target_nero_days=target_nero_days,
            min_nero_miles=min_nero_miles,
            max_nero_miles=max_nero_miles,
            allow_extra_resupply_only=allow_extra_resupply_only,
            avoid_long_food_carry=avoid_long_food_carry,
            prefer_bear_box_sites=prefer_bear_box_sites,
            convenient_resupply_distance_miles=convenient_resupply_distance_miles,
            selected_side_trip_ids=selected_side_trip_ids,
            selected_town_ids=selected_town_ids,
            required_overnight_anchor_ids=required_overnight_anchor_ids,
            required_resupply_anchor_ids=required_resupply_anchor_ids,
            start_access_id=route_extent.get("start_access_id"),
            end_access_id=route_extent.get("end_access_id"),
            route_extent=route_extent,
            access_point_anchors=access_point_anchors,
            route_selection=route_selection,
            planned_start_date=planned_start_date,
            town_stop_selections=town_stop_selections,
            nero_max_trail_miles=nero_max_trail_miles,
        )

    def to_planner_config(self) -> dict[str, Any]:
        return {
            "selected_trail": self.trail_id,
            "trail_root": str(LONG_TRAIL_ROOT),
            "trip_type": self.trip_type,
            "direction": self.direction,
            "desired_days": self.desired_days,
            "min_daily_miles": self.min_daily_miles,
            "max_daily_miles": self.max_daily_miles,
            "max_daily_elevation": self.max_daily_elevation,
            "resupply_cadence": self.resupply_cadence,
            "recovery_cadence": self.recovery_cadence,
            "recovery_planning_mode": self.recovery_planning_mode,
            "target_zero_days": self.target_zero_days,
            "target_nero_days": self.target_nero_days,
            "min_nero_miles": self.min_nero_miles,
            "max_nero_miles": self.max_nero_miles,
            "allow_extra_resupply_only": self.allow_extra_resupply_only,
            "avoid_long_food_carry": self.avoid_long_food_carry,
            "prefer_bear_box_sites": self.prefer_bear_box_sites,
            "selected_side_trip_ids": list(self.selected_side_trip_ids),
            "selected_town_ids": list(self.selected_town_ids),
            "required_overnight_anchor_ids": list(
                self.required_overnight_anchor_ids
            ),
            "required_resupply_anchor_ids": list(
                self.required_resupply_anchor_ids
            ),
            "start_access_id": self.start_access_id,
            "end_access_id": self.end_access_id,
            "route_extent": dict(self.route_extent or {}),
            "access_point_anchors": [
                dict(anchor) for anchor in self.access_point_anchors
            ],
            "convenient_resupply_distance_miles": (
                self.convenient_resupply_distance_miles
            ),
            "ingress_route": self.ingress_route,
            "egress_route": self.egress_route,
            "route_selection": dict(self.route_selection or {}),
            "start_date": self.planned_start_date,
            "town_stop_selections": [
                {
                    **selection,
                    "intents": list(selection["intents"]),
                    "experience_inventory_ids": list(
                        selection["experience_inventory_ids"]
                    ),
                }
                for selection in self.town_stop_selections
            ],
            "nero_max_trail_miles": self.nero_max_trail_miles,
        }


def _validate_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PlanAPIValidationError(f"{field_name} must be an integer")
    return value


def _validate_number(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PlanAPIValidationError(f"{field_name} must be a number")
    if not math.isfinite(value):
        raise PlanAPIValidationError(f"{field_name} must be a finite number")
    return float(value)


def _payload_choice(
    payload: Mapping[str, Any],
    field_name: str,
    default: str,
    choices: set[str],
) -> str:
    value = payload.get(field_name, default)
    if not isinstance(value, str) or value not in choices:
        allowed = ", ".join(sorted(choices))
        raise PlanAPIValidationError(f"{field_name} must be one of: {allowed}")
    return value


def _payload_control_int(
    payload: Mapping[str, Any],
    field_name: str,
    *,
    required: bool = False,
) -> int:
    spec = plan_control_spec(field_name)
    value = payload[field_name] if required else payload.get(field_name, spec["default"])
    parsed = _validate_int(value, field_name)
    if not spec["min"] <= parsed <= spec["max"]:
        raise PlanAPIValidationError(
            f"{field_name} must be between {spec['min']:g} and {spec['max']:g}"
        )
    return parsed


def _payload_control_number(
    payload: Mapping[str, Any],
    field_name: str,
    *,
    required: bool = False,
) -> float:
    spec = plan_control_spec(field_name)
    value = payload[field_name] if required else payload.get(field_name, spec["default"])
    parsed = _validate_number(value, field_name)
    if not spec["min"] <= parsed <= spec["max"]:
        raise PlanAPIValidationError(
            f"{field_name} must be between {spec['min']:g} and {spec['max']:g}"
        )
    return parsed


def _payload_optional_control_number(
    payload: Mapping[str, Any],
    field_name: str,
) -> float:
    spec = plan_control_spec(field_name)
    parsed = _validate_number(payload[field_name], field_name)
    if not spec["min"] <= parsed <= spec["max"]:
        raise PlanAPIValidationError(
            f"{field_name} must be between {spec['min']:g} and {spec['max']:g}"
        )
    return parsed


def _payload_town_stop_selections(
    payload: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    value = payload.get("town_stop_selections", [])
    if not isinstance(value, list):
        raise PlanAPIValidationError("town_stop_selections must be a list")
    valid_intents = {"resupply", "zero", "nero", "experience"}
    selections: list[dict[str, Any]] = []
    seen_towns: set[str] = set()
    seen_experiences: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise PlanAPIValidationError(
                f"town_stop_selections[{index}] must be an object"
            )
        town_id = item.get("town_inventory_id")
        intents = item.get("intents")
        experience_ids = item.get("experience_inventory_ids", [])
        if not isinstance(town_id, str) or not town_id.strip():
            raise PlanAPIValidationError(
                f"town_stop_selections[{index}].town_inventory_id must be a string"
            )
        town_id = town_id.strip()
        if town_id in seen_towns:
            raise PlanAPIValidationError(
                f"town_stop_selections contains duplicate town_inventory_id: {town_id}"
            )
        seen_towns.add(town_id)
        if not isinstance(intents, list) or not intents:
            raise PlanAPIValidationError(
                f"town_stop_selections[{index}].intents must be a non-empty list"
            )
        normalized_intents: list[str] = []
        for intent in intents:
            if not isinstance(intent, str) or intent not in valid_intents:
                raise PlanAPIValidationError(
                    "town stop intents must be one of: experience, nero, resupply, zero"
                )
            if intent in normalized_intents:
                raise PlanAPIValidationError(
                    f"town_stop_selections[{index}].intents contains duplicate: {intent}"
                )
            normalized_intents.append(intent)
        if not isinstance(experience_ids, list):
            raise PlanAPIValidationError(
                f"town_stop_selections[{index}].experience_inventory_ids must be a list"
            )
        normalized_experiences: list[str] = []
        for experience_id in experience_ids:
            if not isinstance(experience_id, str) or not experience_id.strip():
                raise PlanAPIValidationError(
                    "experience_inventory_ids must contain non-empty strings"
                )
            experience_id = experience_id.strip()
            if experience_id in seen_experiences:
                raise PlanAPIValidationError(
                    f"town_stop_selections contains duplicate experience_inventory_id: {experience_id}"
                )
            seen_experiences.add(experience_id)
            normalized_experiences.append(experience_id)
        if normalized_experiences and "experience" not in normalized_intents:
            raise PlanAPIValidationError(
                "experience_inventory_ids require the experience intent"
            )
        if "experience" in normalized_intents and not normalized_experiences:
            raise PlanAPIValidationError(
                "experience intent requires at least one experience_inventory_id"
            )
        selections.append(
            {
                "town_inventory_id": town_id,
                "intents": tuple(normalized_intents),
                "experience_inventory_ids": tuple(normalized_experiences),
            }
        )
    if selections and any(
        payload.get(field_name)
        for field_name in (
            "selected_town_ids",
            "selected_side_trip_ids",
            "required_resupply_anchor_ids",
        )
    ):
        raise PlanAPIValidationError(
            "town_stop_selections cannot be combined with legacy town, side-trip, "
            "or required-resupply selections"
        )
    return tuple(selections)


def _target_count_value(
    payload: Mapping[str, Any],
    field_name: str,
    recovery_planning_mode: str,
) -> int:
    if field_name in payload or recovery_planning_mode == "target_counts":
        return _payload_control_int(payload, field_name)
    return 0


def _payload_bool(
    payload: Mapping[str, Any],
    field_name: str,
) -> bool:
    value = payload.get(field_name, plan_control_spec(field_name)["default"])
    if not isinstance(value, bool):
        raise PlanAPIValidationError(f"{field_name} must be a boolean")
    return value


def _payload_string_list(
    payload: Mapping[str, Any],
    field_name: str,
) -> tuple[str, ...]:
    value = payload.get(field_name, [])
    if not isinstance(value, list):
        raise PlanAPIValidationError(f"{field_name} must be a list of strings")

    selected_ids: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise PlanAPIValidationError(f"{field_name} must be a list of strings")
        selected_ids.append(item.strip())
    return tuple(selected_ids)


def _payload_unique_string_list(
    payload: Mapping[str, Any],
    field_name: str,
) -> tuple[str, ...]:
    selected_ids = _payload_string_list(payload, field_name)
    seen_ids: set[str] = set()
    for inventory_id in selected_ids:
        if inventory_id in seen_ids:
            raise PlanAPIValidationError(
                f"{field_name} contains duplicate inventory_id: {inventory_id}"
            )
        seen_ids.add(inventory_id)
    return selected_ids


def _validate_route_name(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlanAPIValidationError(f"{field_name} must be a non-empty string")
    return value.strip()


def _validate_directional_access_route(
    route_name: str,
    field_name: str,
    valid_routes: set[str],
) -> None:
    if route_name not in valid_routes:
        allowed = ", ".join(sorted(valid_routes))
        raise PlanAPIValidationError(
            f"{field_name} must be one of: {allowed}"
        )
