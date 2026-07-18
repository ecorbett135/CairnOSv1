# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""Project operational access-point anchors onto generated planned truth."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from cairn.api.access_points import ACCESS_POINT_ANCHOR_CONTRACT_VERSION


class AccessPointAnchorError(ValueError):
    """Raised when a generated plan cannot satisfy an access-point anchor."""


def build_access_point_anchor_status(
    *,
    access_point_anchors: list[dict[str, Any]],
    daily_plan: list[dict[str, Any]],
    resupply_plan: list[dict[str, Any]],
    start_date: str | None,
    min_daily_miles: float,
    max_daily_miles: float,
    max_daily_elevation: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = [{**row, "access_point_anchors": []} for row in daily_plan]
    satisfied_ids: list[str] = []
    projected: list[dict[str, Any]] = []

    for anchor in access_point_anchors:
        access_id = anchor["access_id"]
        crossing_row = _crossing_row(rows, float(anchor["canonical_mile"]))
        if crossing_row is None:
            raise AccessPointAnchorError(
                "Access-point anchor must appear inside generated planned truth: "
                f"{access_id} appeared 0 times"
            )

        intent = anchor["intent"]
        if intent == "overnight":
            _validate_overnight_anchor(
                anchor,
                crossing_row,
                min_daily_miles=min_daily_miles,
                max_daily_miles=max_daily_miles,
                max_daily_elevation=max_daily_elevation,
            )
        elif intent == "resupply" and not any(
            row.get("required_anchor_id") == access_id for row in resupply_plan
        ):
            raise AccessPointAnchorError(
                "Required access-point resupply anchor must appear exactly once: "
                f"{access_id} appeared 0 times"
            )

        annotation = {
            key: anchor[key]
            for key in (
                "access_id",
                "intent",
                "display_name",
                "canonical_mile",
                "section_relative_mile",
            )
        }
        for field_name in ("date", "time", "note"):
            if field_name in anchor:
                annotation[field_name] = anchor[field_name]
        crossing_row["access_point_anchors"].append(annotation)

        planned_day = crossing_row.get("day")
        planned_date = _planned_date(start_date, planned_day)
        satisfaction = {
            **annotation,
            "status": "satisfied",
            "planned_day": planned_day,
        }
        if planned_date:
            satisfaction["planned_date"] = planned_date
        projected.append(satisfaction)
        satisfied_ids.append(access_id)

    requested_ids = [anchor["access_id"] for anchor in access_point_anchors]
    return rows, {
        "contract_version": ACCESS_POINT_ANCHOR_CONTRACT_VERSION,
        "semantics": "intermediate_operational_checkpoints",
        "requested_access_point_anchor_ids": requested_ids,
        "satisfied_access_point_anchor_ids": satisfied_ids,
        "unsatisfied_access_point_anchor_ids": [],
        "anchors": projected,
    }


def _crossing_row(
    rows: list[dict[str, Any]],
    mile: float,
) -> dict[str, Any] | None:
    for row in rows:
        start = row.get("daily_start_mile")
        stop = row.get("daily_stop_mile")
        if not isinstance(start, (int, float)) or not isinstance(stop, (int, float)):
            continue
        lower = min(float(start), float(stop))
        upper = max(float(start), float(stop))
        if lower - 0.05 <= mile <= upper + 0.05:
            return row
    return None


def _validate_overnight_anchor(
    anchor: dict[str, Any],
    row: dict[str, Any],
    *,
    min_daily_miles: float,
    max_daily_miles: float,
    max_daily_elevation: float,
) -> None:
    access_id = anchor["access_id"]
    if (
        row.get("required_overnight_anchor_id") != access_id
        or abs(float(row.get("daily_stop_mile") or 0) - float(anchor["canonical_mile"]))
        > 0.05
    ):
        raise AccessPointAnchorError(
            "Required access-point overnight anchor must appear exactly once: "
            f"{access_id} appeared 0 times"
        )
    daily_miles = float(row.get("daily_miles") or 0)
    elevation = float(row.get("daily_elevation_gain") or 0)
    if 0 < daily_miles < min_daily_miles:
        raise AccessPointAnchorError(
            f"Required access-point overnight anchor {access_id} is infeasible "
            f"within min_daily_miles={min_daily_miles:g}; planned day "
            f"{row.get('day')} requires only {daily_miles:g} miles"
        )
    if daily_miles > max_daily_miles:
        raise AccessPointAnchorError(
            f"Required access-point overnight anchor {access_id} is infeasible "
            f"within max_daily_miles={max_daily_miles:g}; planned day "
            f"{row.get('day')} requires {daily_miles:g} miles"
        )
    if elevation > max_daily_elevation:
        raise AccessPointAnchorError(
            f"Required access-point overnight anchor {access_id} is infeasible "
            f"within max_daily_elevation={max_daily_elevation:g}; planned day "
            f"{row.get('day')} requires {elevation:g} feet of gain"
        )


def _planned_date(start_date: str | None, day_number: Any) -> str | None:
    if not start_date or not isinstance(day_number, int):
        return None
    try:
        parsed = date.fromisoformat(start_date)
    except ValueError:
        return None
    return (parsed + timedelta(days=day_number - 1)).isoformat()
