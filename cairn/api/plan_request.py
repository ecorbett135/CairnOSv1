# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""Request validation for CairnOS Plan API payloads."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LONG_TRAIL_ROOT = PROJECT_ROOT / "trails" / "vermont_long_trail"

LONG_TRAIL_ID = "vermont_long_trail"
VALID_DIRECTIONS = {"NOBO", "SOBO"}
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


@dataclass(frozen=True)
class PlanAPIRequest:
    """Validated HikerLogix-native MVP request for a CairnOS plan."""

    trail_id: str
    direction: str
    ingress_route: str
    egress_route: str
    desired_days: int
    min_daily_miles: float
    max_daily_miles: float
    max_daily_elevation: float
    resupply_cadence: int
    recovery_cadence: int
    planned_start_date: str | None = None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> PlanAPIRequest:
        required_fields = (
            "trail_id",
            "direction",
            "ingress_route",
            "egress_route",
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

        ingress_route = _validate_route_name(
            payload["ingress_route"], "ingress_route"
        )
        egress_route = _validate_route_name(payload["egress_route"], "egress_route")
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

        desired_days = _validate_int(payload["desired_days"], "desired_days")
        if not 3 <= desired_days <= 60:
            raise PlanAPIValidationError("desired_days must be between 3 and 60")

        min_daily_miles = _validate_number(
            payload["min_daily_miles"], "min_daily_miles"
        )
        max_daily_miles = _validate_number(
            payload["max_daily_miles"], "max_daily_miles"
        )
        max_daily_elevation = _validate_number(
            payload["max_daily_elevation"], "max_daily_elevation"
        )

        if not 4 <= min_daily_miles <= 25:
            raise PlanAPIValidationError("min_daily_miles must be between 4 and 25")
        if not 8 <= max_daily_miles <= 40:
            raise PlanAPIValidationError("max_daily_miles must be between 8 and 40")
        if not 1000 <= max_daily_elevation <= 10000:
            raise PlanAPIValidationError(
                "max_daily_elevation must be between 1000 and 10000"
            )
        if max_daily_miles < min_daily_miles:
            raise PlanAPIValidationError(
                "max_daily_miles must be greater than or equal to min_daily_miles"
            )

        resupply_cadence = _validate_int(
            payload["resupply_cadence"], "resupply_cadence"
        )
        recovery_cadence = _validate_int(
            payload["recovery_cadence"], "recovery_cadence"
        )
        if not 2 <= resupply_cadence <= 10:
            raise PlanAPIValidationError("resupply_cadence must be between 2 and 10")
        if not 3 <= recovery_cadence <= 14:
            raise PlanAPIValidationError("recovery_cadence must be between 3 and 14")

        planned_start_date = payload.get("planned_start_date")
        if planned_start_date is not None and not isinstance(planned_start_date, str):
            raise PlanAPIValidationError("planned_start_date must be a string")

        return cls(
            trail_id=trail_id,
            direction=direction,
            ingress_route=ingress_route,
            egress_route=egress_route,
            desired_days=desired_days,
            min_daily_miles=min_daily_miles,
            max_daily_miles=max_daily_miles,
            max_daily_elevation=max_daily_elevation,
            resupply_cadence=resupply_cadence,
            recovery_cadence=recovery_cadence,
            planned_start_date=planned_start_date,
        )

    def to_planner_config(self) -> dict[str, Any]:
        return {
            "selected_trail": self.trail_id,
            "trail_root": str(LONG_TRAIL_ROOT),
            "trip_type": "THRU",
            "direction": self.direction,
            "desired_days": self.desired_days,
            "min_daily_miles": self.min_daily_miles,
            "max_daily_miles": self.max_daily_miles,
            "max_daily_elevation": self.max_daily_elevation,
            "resupply_cadence": self.resupply_cadence,
            "recovery_cadence": self.recovery_cadence,
            "recovery_planning_mode": "cadence",
            "target_zero_days": 0,
            "target_nero_days": 0,
            "min_nero_miles": 5.0,
            "max_nero_miles": 8.0,
            "allow_extra_resupply_only": True,
            "avoid_long_food_carry": True,
            "prefer_bear_box_sites": False,
            "selected_side_trip_ids": [],
            "selected_town_ids": [],
            "convenient_resupply_distance_miles": 1.0,
            "ingress_route": self.ingress_route,
            "egress_route": self.egress_route,
            "start_date": self.planned_start_date,
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
    return value


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
