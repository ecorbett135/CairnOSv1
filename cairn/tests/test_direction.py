# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from cairn.planner.planner_v2 import PlannerV2


def test_nobo_direction_set(trail_root):
    planner = PlannerV2(
        trail_root=trail_root,
        user_profile={
            "direction": "NOBO",
            "min_daily_miles": 8,
            "max_daily_miles": 16,
        },
    )

    assert planner.direction == "NOBO"


def test_sobo_direction_set(planner_factory):
    planner = planner_factory(
        user_profile={
            "direction": "SOBO",
            "min_daily_miles": 8,
            "max_daily_miles": 16,
        },
    )

    assert planner.direction == "SOBO"


def test_nobo_with_ingress_resolves_node(planner_factory):
    planner = planner_factory(
        user_profile={
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "min_daily_miles": 8,
            "max_daily_miles": 16,
        },
    )

    ingress_resolved = planner._resolve_ingress_node()

    assert ingress_resolved is not None
    assert "mile" in ingress_resolved
    assert "location_name" in ingress_resolved
    assert ingress_resolved["mile"] < 0
