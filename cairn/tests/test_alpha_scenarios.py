# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0

import pytest


ALLOWED_NOTES = {
    "",
    "start",
    "resupply",
    "nero",
    "zero",
    "resupply / nero",
    "resupply / zero",
}


def assert_forward_progress(
    rows,
    direction,
):
    for row in rows:

        if row["daily_miles"] == 0.0:
            assert (
                row["daily_start_mile"]
                == row["daily_stop_mile"]
            )
            assert "zero" in row["notes"]
            continue

        assert row["daily_miles"] > 0

        if direction == "NOBO":
            assert (
                row["daily_stop_mile"]
                > row["daily_start_mile"]
            )
        else:
            assert (
                row["daily_stop_mile"]
                < row["daily_start_mile"]
            )


def assert_sparse_notes(
    itinerary,
):
    for row in itinerary["daily_plan"]:
        assert row["notes"] in ALLOWED_NOTES

    for row in itinerary["resupply_plan"]:
        assert row["notes"] in ALLOWED_NOTES


def assert_resupply_strategy_has_leg_lengths(
    itinerary,
):
    resupply_plan = itinerary["resupply_plan"]

    assert resupply_plan
    assert resupply_plan[0]["day"] == 1
    assert resupply_plan[0]["notes"] == "start"
    assert "days_to_next_resupply" in resupply_plan[0]

    for idx, row in enumerate(resupply_plan):
        assert row["location"]
        assert row["mile"] is not None
        assert "days_to_next_resupply" in row

        if idx + 1 < len(resupply_plan):
            assert (
                row["days_to_next_resupply"]
                == resupply_plan[idx + 1]["day"] - row["day"]
            )


def assert_mileage_within_extended_alpha_cap(
    itinerary,
    max_daily_miles,
):
    mileage_cap = max_daily_miles * 1.3

    assert max(
        row["daily_miles"]
        for row in itinerary["daily_plan"]
    ) <= mileage_cap + 0.1


def test_alpha_north_adams_tight_plan_extends_without_absurd_catchup(
    planner_factory,
):
    """Regression test for deployed 21-day North Adams alpha profile."""
    max_daily_miles = 12
    planner = planner_factory(
        user_profile={
            "trip_type": "THRU",
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "egress_route": "Journey's End Trail",
            "min_daily_miles": 8,
            "max_daily_miles": max_daily_miles,
            "max_daily_elevation": 4000,
            "resupply_cadence": 5,
            "recovery_cadence": 5,
            "min_nero_miles": 5,
            "max_nero_miles": 8,
            "allow_extra_resupply_only": True,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=21
    )
    rows = itinerary["daily_plan"]
    completion = itinerary["completion_analysis"]

    assert completion["completion_extended"] is True
    assert completion["recommended_days"] > 21
    assert rows[-1]["day"] == completion["recommended_days"]
    assert (
        rows[-1]["daily_stop_location"]
        == "Journey's End Trail Parking"
    )
    assert_mileage_within_extended_alpha_cap(
        itinerary,
        max_daily_miles,
    )
    assert_forward_progress(
        rows,
        "NOBO",
    )
    assert_sparse_notes(
        itinerary
    )
    assert_resupply_strategy_has_leg_lengths(
        itinerary
    )


@pytest.mark.parametrize(
    (
        "name",
        "profile",
        "desired_days",
        "expected_final_stop",
        "direction",
    ),
    [
        (
            "default_nobo_williamstown",
            {
                "trip_type": "THRU",
                "direction": "NOBO",
                "ingress_route": "Williamstown Approach",
                "egress_route": "Journey's End Trail",
                "min_daily_miles": 8,
                "max_daily_miles": 16,
                "max_daily_elevation": 3500,
                "resupply_cadence": 5,
                "recovery_cadence": 6,
                "min_nero_miles": 5,
                "max_nero_miles": 8,
                "allow_extra_resupply_only": True,
            },
            28,
            "Journey's End Trail Parking",
            "NOBO",
        ),
        (
            "default_sobo_williamstown",
            {
                "trip_type": "THRU",
                "direction": "SOBO",
                "ingress_route": "Journey's End Trail",
                "egress_route": "Williamstown Approach",
                "min_daily_miles": 8,
                "max_daily_miles": 16,
                "max_daily_elevation": 3500,
                "resupply_cadence": 5,
                "recovery_cadence": 6,
                "min_nero_miles": 5,
                "max_nero_miles": 8,
                "allow_extra_resupply_only": True,
            },
            28,
            "Pine Cobble Road in Williamstown",
            "SOBO",
        ),
        (
            "tight_nobo_williamstown",
            {
                "trip_type": "THRU",
                "direction": "NOBO",
                "ingress_route": "Williamstown Approach",
                "egress_route": "Journey's End Trail",
                "min_daily_miles": 9,
                "max_daily_miles": 12,
                "max_daily_elevation": 4000,
                "resupply_cadence": 5,
                "recovery_cadence": 5,
                "min_nero_miles": 5,
                "max_nero_miles": 8,
                "allow_extra_resupply_only": True,
            },
            21,
            "Journey's End Trail Parking",
            "NOBO",
        ),
    ],
)
def test_alpha_user_scenarios_preserve_operational_bounds(
    planner_factory,
    name,
    profile,
    desired_days,
    expected_final_stop,
    direction,
):
    planner = planner_factory(
        user_profile=profile,
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=desired_days
    )
    rows = itinerary["daily_plan"]

    assert name
    assert rows[-1]["daily_stop_location"] == expected_final_stop
    assert_mileage_within_extended_alpha_cap(
        itinerary,
        profile["max_daily_miles"],
    )
    assert_forward_progress(
        rows,
        direction,
    )
    assert_sparse_notes(
        itinerary
    )
    assert_resupply_strategy_has_leg_lengths(
        itinerary
    )
