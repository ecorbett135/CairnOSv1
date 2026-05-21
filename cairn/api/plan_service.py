# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""Stateless service for CairnOS Plan API responses."""

from __future__ import annotations

from typing import Any

from cairn.api.plan_request import PlanAPIRequest
from cairn.export.plan_json import build_plan_export
from cairn.planner.planner_v2 import PlannerV2


def build_plan_response(
    payload: dict[str, Any],
    build_sha: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    request = PlanAPIRequest.from_payload(payload)
    planner_config = request.to_planner_config()
    planner = PlannerV2(
        trail_root=planner_config["trail_root"],
        user_profile={
            "min_daily_miles": planner_config["min_daily_miles"],
            "max_daily_miles": planner_config["max_daily_miles"],
            "max_daily_elevation": planner_config["max_daily_elevation"],
            "resupply_cadence": planner_config["resupply_cadence"],
            "recovery_cadence": planner_config["recovery_cadence"],
            "recovery_planning_mode": planner_config["recovery_planning_mode"],
            "target_zero_days": planner_config["target_zero_days"],
            "target_nero_days": planner_config["target_nero_days"],
            "min_nero_miles": planner_config["min_nero_miles"],
            "max_nero_miles": planner_config["max_nero_miles"],
            "allow_extra_resupply_only": planner_config[
                "allow_extra_resupply_only"
            ],
            "avoid_long_food_carry": planner_config["avoid_long_food_carry"],
            "prefer_bear_box_sites": planner_config["prefer_bear_box_sites"],
            "selected_side_trip_ids": planner_config["selected_side_trip_ids"],
            "selected_town_ids": planner_config["selected_town_ids"],
            "convenient_resupply_distance_miles": planner_config[
                "convenient_resupply_distance_miles"
            ],
            "trip_type": planner_config["trip_type"],
            "direction": planner_config["direction"],
            "ingress_route": planner_config["ingress_route"],
            "egress_route": planner_config["egress_route"],
            "start_date": planner_config["start_date"],
        },
    )
    itinerary = planner.synthesize_itinerary(
        desired_days=planner_config["desired_days"]
    )
    planner_result = {
        "config": planner_config,
        "itinerary": itinerary,
        "build_sha": build_sha or "api",
    }
    return build_plan_export(
        planner_result,
        trail_root=planner_config["trail_root"],
        build_sha=build_sha,
        generated_at=generated_at,
    )
