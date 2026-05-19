# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from cairn.export.elevation_confidence import (
    build_elevation_confidence_report,
    classify_confidence,
)


def test_confidence_classification_by_elevation_source():
    assert classify_confidence(
        {
            "source": "terrain",
        },
        10.0,
        0.0,
        0.0,
    ) == (
        "high",
        [
            "terrain_interval_resolved",
        ],
    )

    assert classify_confidence(
        {
            "source": "route_master",
        },
        10.0,
        0.0,
        0.0,
    ) == (
        "medium",
        [
            "route_master_elevation_fallback",
        ],
    )

    assert classify_confidence(
        {
            "source": "estimated",
        },
        10.0,
        0.0,
        0.0,
    ) == (
        "low",
        [
            "distance_based_elevation_estimate",
        ],
    )

    assert classify_confidence(
        {
            "source": "none",
        },
        0.0,
        0.0,
        None,
    ) == (
        "not_applicable",
        [
            "zero_or_nonmoving_day",
        ],
    )


def test_elevation_confidence_report_summarizes_itinerary(
    planner_factory,
    trail_root,
):
    planner = planner_factory(
        user_profile={
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "min_daily_miles": 8,
            "max_daily_miles": 16,
        }
    )
    itinerary = planner.synthesize_itinerary(
        desired_days=28
    )

    report = build_elevation_confidence_report(
        {
            "itinerary": itinerary,
        },
        trail_root,
    )

    assert (
        report["schema_version"]
        == "cairnos_elevation_confidence_v1"
    )
    assert (
        report["summary"]["total_days"]
        == len(itinerary["daily_plan"])
    )
    assert report["summary"]["moving_days"] > 0
    assert (
        report["summary"]["high"]
        + report["summary"]["medium"]
        + report["summary"]["low"]
        + report["summary"]["not_applicable"]
        == report["summary"]["total_days"]
    )
    assert any(
        day["confidence"] == "high"
        for day in report["days"]
    )
    assert any(
        day["confidence"] == "not_applicable"
        for day in report["days"]
    )
    assert (
        "off_spine_overnight_access_days"
        in report["summary"]
    )


def test_elevation_confidence_preserves_spur_access_diagnostics(
    planner_factory,
    trail_root,
):
    planner = planner_factory(
        user_profile={
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "egress_route": "Journey's End Trail",
            "min_daily_miles": 10,
            "max_daily_miles": 15,
            "resupply_cadence": 5,
            "recovery_cadence": 5,
            "allow_extra_resupply_only": True,
        }
    )
    itinerary = planner.synthesize_itinerary(
        desired_days=27
    )

    report = build_elevation_confidence_report(
        {
            "itinerary": itinerary,
        },
        trail_root,
    )
    stratton_day = next(
        day for day in report["days"]
        if day["daily_stop_location"]
        == "Stratton Pond Shelter"
    )

    assert stratton_day[
        "daily_stop_access_notes"
    ] == (
        "600 ft S via Stratton Pond Trail "
        "and spur"
    )
    assert stratton_day[
        "daily_stop_spine_alignment"
    ]["status"] == (
        "off_spine_overnight_access"
    )
