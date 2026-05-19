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
