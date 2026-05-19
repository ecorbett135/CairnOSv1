# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from build_topo.compiler import (
    overnight_reference,
)


def test_overnight_amenities_load_bear_box_source_rows(
    trail_root,
):
    amenities = (
        overnight_reference
        .load_overnight_amenities(
            trail_root
        )
    )

    assert amenities
    assert amenities[
        "seth warner"
    ]["bear_box"] is True
    assert amenities[
        "griffith lake"
    ]["amenity_source_url"] == (
        "https://www.greenmountainclub.org/bear-boxes/"
    )


def test_overnight_reference_propagates_bear_box_metadata(
    trail_root,
):
    payload = (
        overnight_reference
        .build_overnight_reference(
            trail_root
        )
    )

    assert payload["summary"]["bear_box_sites"] == 20
    assert (
        payload["summary"][
            "bear_box_planner_candidates"
        ]
        >= 1
    )

    seth = next(
        record
        for record in payload[
            "matched_overnight_sites"
        ]
        if record["title"] == "Seth Warner Shelter"
    )
    griffith = next(
        record
        for record in payload[
            "planner_candidates"
        ]
        if record["canonical_name"]
        == "Griffith Lake Camping Area"
    )

    assert seth["bear_box"] is True
    assert griffith["bear_box"] is True
    assert seth["amenity_source_name"] == (
        "Green Mountain Club Bear Box Locations"
    )


def test_runtime_exposes_bear_box_overnight_nodes(
    planner,
):
    operational_nodes = (
        planner.queries
        .get_operational_overnight_nodes()
    )

    seth = next(
        item for item in operational_nodes
        if item["node"]["canonical_name"]
        == "Seth Warner Shelter"
    )
    griffith = next(
        item for item in operational_nodes
        if item["node"]["canonical_name"]
        == "Griffith Lake Camping Area"
    )

    assert seth["node"]["bear_box"] is True
    assert griffith["node"]["bear_box"] is True


def test_bear_box_preference_softly_biases_stop_selection(
    planner_factory,
):
    base_nodes = [
        {
            "node": {
                "canonical_name": "Closer Shelter",
                "trail_mile": 10.2,
                "shelter": True,
                "bear_box": False,
            },
            "priority": 1,
            "type": "shelter",
        },
        {
            "node": {
                "canonical_name": "Bear Box Shelter",
                "trail_mile": 10.9,
                "shelter": True,
                "bear_box": True,
            },
            "priority": 1,
            "type": "shelter",
        },
    ]

    default_planner = planner_factory()
    preferred_planner = planner_factory(
        user_profile={
            "prefer_bear_box_sites": True,
        }
    )

    default_stop = (
        default_planner.select_operational_stop(
            target_mile=10.0,
            operational_overnight_nodes=base_nodes,
            logistics_nodes=[],
            current_mile=9.0,
        )
    )
    preferred_stop = (
        preferred_planner.select_operational_stop(
            target_mile=10.0,
            operational_overnight_nodes=base_nodes,
            logistics_nodes=[],
            current_mile=9.0,
        )
    )

    assert default_stop["canonical_name"] == (
        "Closer Shelter"
    )
    assert preferred_stop["canonical_name"] == (
        "Bear Box Shelter"
    )


def test_bear_box_preference_does_not_force_out_of_range_stop(
    planner_factory,
):
    planner = planner_factory(
        user_profile={
            "prefer_bear_box_sites": True,
        }
    )

    selected_stop = planner.select_operational_stop(
        target_mile=10.0,
        operational_overnight_nodes=[
            {
                "node": {
                    "canonical_name": "Too Far Bear Box",
                    "trail_mile": 19.0,
                    "shelter": True,
                    "bear_box": True,
                },
                "priority": 1,
                "type": "shelter",
            }
        ],
        logistics_nodes=[],
        current_mile=9.0,
    )

    assert selected_stop is None


def test_itinerary_rows_include_bear_box_field(
    planner_factory,
):
    planner = planner_factory(
        user_profile={
            "direction": "NOBO",
            "ingress_route": "Williamstown Approach",
            "egress_route": "Journey's End Trail",
            "min_daily_miles": 9,
            "max_daily_miles": 15,
            "max_daily_elevation": 4000,
            "prefer_bear_box_sites": True,
        }
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=28
    )

    rows = itinerary["daily_plan"]

    assert all(
        "daily_stop_bear_box" in row
        for row in rows
    )
    assert any(
        row["daily_stop_bear_box"] is True
        for row in rows
    )
