# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path

import pytest

from cairn.planner.planner_v2 import PlannerV2


@pytest.fixture(scope="session")
def trail_root():
    return Path(__file__).parents[2] / "trails" / "vermont_long_trail"


@pytest.fixture
def planner_factory(trail_root):
    def _create(user_profile=None):
        return PlannerV2(
            trail_root=trail_root,
            user_profile=user_profile or {},
        )

    return _create


@pytest.fixture(scope="session")
def planner(trail_root):
    return PlannerV2(trail_root=trail_root)


@pytest.fixture
def shelter_nodes(planner):
    return planner.queries.get_shelter_nodes()


@pytest.fixture(scope="session")
def nobo_planner(trail_root):
    return PlannerV2(
        trail_root=trail_root,
        user_profile={
            "direction": "NOBO",
            "min_daily_miles": 8,
            "max_daily_miles": 16,
            "max_daily_elevation": 3500,
        },
    )


@pytest.fixture(scope="session")
def nobo_north_adams_planner(trail_root):
    return PlannerV2(
        trail_root=trail_root,
        user_profile={
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "min_daily_miles": 8,
            "max_daily_miles": 16,
        },
    )
