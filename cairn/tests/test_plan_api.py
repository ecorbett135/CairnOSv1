# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0

from cairn.api.plan_request import (
    PlanAPIRequest,
    PlanAPIValidationError,
)


def test_plan_api_request_builds_streamlit_equivalent_config():
    request = PlanAPIRequest.from_payload(
        {
            "trail_id": "vermont_long_trail",
            "direction": "NOBO",
            "desired_days": 28,
            "min_daily_miles": 8,
            "max_daily_miles": 15,
            "max_daily_elevation": 4000,
            "resupply_cadence": 5,
            "recovery_cadence": 6,
            "planned_start_date": "2026-07-01",
        }
    )

    config = request.to_planner_config()

    assert config["selected_trail"] == "vermont_long_trail"
    assert config["trip_type"] == "THRU"
    assert config["direction"] == "NOBO"
    assert config["desired_days"] == 28
    assert config["trail_root"].endswith("trails/vermont_long_trail")
    assert config["start_date"] == "2026-07-01"
    assert config["selected_side_trip_ids"] == []
    assert config["selected_town_ids"] == []


def test_plan_api_request_rejects_non_long_trail_payload():
    try:
        PlanAPIRequest.from_payload(
            {
                "trail_id": "custom",
                "direction": "NOBO",
                "desired_days": 28,
                "min_daily_miles": 8,
                "max_daily_miles": 15,
                "max_daily_elevation": 4000,
                "resupply_cadence": 5,
                "recovery_cadence": 6,
            }
        )
    except PlanAPIValidationError as error:
        assert "trail_id" in str(error)
    else:
        raise AssertionError("Expected PlanAPIValidationError")


def test_plan_api_request_rejects_inverted_mileage_range():
    try:
        PlanAPIRequest.from_payload(
            {
                "trail_id": "vermont_long_trail",
                "direction": "SOBO",
                "desired_days": 28,
                "min_daily_miles": 18,
                "max_daily_miles": 12,
                "max_daily_elevation": 4000,
                "resupply_cadence": 5,
                "recovery_cadence": 6,
            }
        )
    except PlanAPIValidationError as error:
        assert "min_daily_miles" in str(error)
    else:
        raise AssertionError("Expected PlanAPIValidationError")


def test_plan_api_request_rejects_non_finite_numeric_inputs():
    try:
        PlanAPIRequest.from_payload(
            {
                "trail_id": "vermont_long_trail",
                "direction": "NOBO",
                "desired_days": 28,
                "min_daily_miles": float("nan"),
                "max_daily_miles": 15,
                "max_daily_elevation": 4000,
                "resupply_cadence": 5,
                "recovery_cadence": 6,
            }
        )
    except PlanAPIValidationError as error:
        assert "min_daily_miles" in str(error)
    else:
        raise AssertionError("Expected PlanAPIValidationError")
