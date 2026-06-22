# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""Request validation for CairnOS Plan API payloads."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from cairn.api.plan_controls import plan_control_spec


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LONG_TRAIL_ROOT = PROJECT_ROOT / "trails" / "vermont_long_trail"

LONG_TRAIL_ID = "vermont_long_trail"
VALID_DIRECTIONS = {"NOBO", "SOBO"}
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
            "convenient_resupply_distance_miles": (
                self.convenient_resupply_distance_miles
            ),
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
