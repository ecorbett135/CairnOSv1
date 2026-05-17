# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from cairn.export.gaia_geojson import (
    export_itinerary_to_gaia_geojson,
    interpolate_spine_coordinate,
    load_overlay_nodes,
    load_resupply_access_reference,
    load_spine_coordinates,
    total_overlay_miles,
)


def test_gaia_export_builds_point_features(
    planner_factory,
    trail_root,
):
    planner = planner_factory(
        user_profile={
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "min_daily_miles": 8,
            "max_daily_miles": 16,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=21
    )

    export = export_itinerary_to_gaia_geojson(
        itinerary["daily_plan"],
        trail_root,
    )

    geojson = export["geojson"]
    expected_resupply_feature_count = len([
        day
        for day in itinerary["daily_plan"]
        if day.get("resupply_location")
    ])
    resupply_feature_count = len([
        feature
        for feature in geojson["features"]
        if feature.get("properties", {}).get(
            "cairnos_feature_type"
        ) == "resupply"
    ])

    assert geojson["type"] == "FeatureCollection"
    assert export["warnings"] == []
    assert (
        resupply_feature_count
        == expected_resupply_feature_count
    )
    assert len(geojson["features"]) == (
        len(itinerary["daily_plan"])
        + expected_resupply_feature_count
        + 1
    )

    spine_feature = geojson["features"][0]

    assert spine_feature["geometry"]["type"] == "LineString"
    assert (
        spine_feature["properties"]["cairnos_feature_type"]
        == "spine"
    )
    assert spine_feature["properties"]["name"].endswith(
        "spine"
    )
    assert spine_feature["properties"]["stroke"] == "#FF1493"

    first_feature = geojson["features"][1]
    first_day = itinerary["daily_plan"][0]

    assert first_feature["geometry"]["type"] == "Point"
    assert len(
        first_feature["geometry"]["coordinates"]
    ) == 2
    assert (
        first_feature["properties"]["name"]
        == (
            f"Day {first_day['day']} — "
            f"{first_day['daily_stop_location']}"
        )
    )

    for key in [
        "day",
        "division",
        "daily_start_mile",
        "daily_start_location",
        "daily_stop_mile",
        "daily_stop_location",
        "daily_stop_location_type",
        "daily_miles",
        "daily_elevation_gain",
        "notes",
    ]:
        assert key in first_feature["properties"]


def test_gaia_spine_interpolation_uses_guidebook_overlay_endpoints(
    trail_root,
):
    """Test fallback spine coordinates use public guidebook miles."""
    overlay_nodes = load_overlay_nodes(
        trail_root
    )
    spine_coordinates = load_spine_coordinates(
        trail_root
    )
    total_miles = total_overlay_miles(
        overlay_nodes
    )

    assert interpolate_spine_coordinate(
        spine_coordinates,
        0.0,
        total_miles,
    ) == spine_coordinates[0][:2]
    assert interpolate_spine_coordinate(
        spine_coordinates,
        total_miles,
        total_miles,
    ) == spine_coordinates[-1][:2]


def test_gaia_export_marks_shelters_with_gaia_icon(
    planner_factory,
    trail_root,
):
    planner = planner_factory(
        user_profile={
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "min_daily_miles": 8,
            "max_daily_miles": 16,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=21
    )

    export = export_itinerary_to_gaia_geojson(
        itinerary["daily_plan"],
        trail_root,
    )

    shelter_features = [
        feature
        for feature in export["geojson"]["features"]
        if (
            feature.get("geometry", {}).get("type")
            == "Point"
            and feature["properties"].get(
                "daily_stop_location_type"
            )
            == "shelter"
        )
    ]

    assert shelter_features

    for feature in shelter_features:
        assert (
            feature["properties"]["marker_type"]
            == "gaia-shelter"
        )
        assert (
            feature["marker_type"]
            == "gaia-shelter"
        )
        assert (
            feature["properties"]["marker_decoration"]
            == "shelter"
        )
        assert (
            feature["properties"]["marker_color"]
            == "#4ABD32"
        )


def test_gaia_export_uses_reference_coordinates_for_camps(
    trail_root,
):
    export = export_itinerary_to_gaia_geojson(
        [
            {
                "day": 1,
                "division": "division10",
                "daily_start_mile": 222.3,
                "daily_start_location": (
                    "Vt. 15 at cemetery"
                ),
                "daily_start_location_type": (
                    "logistics"
                ),
                "daily_stop_mile": 233.7,
                "daily_stop_location": (
                    "Corliss Camp"
                ),
                "daily_stop_location_type": "camp",
                "daily_miles": 11.4,
                "daily_elevation_gain": 2599,
                "notes": "",
            }
        ],
        trail_root,
    )

    corliss = next(
        feature
        for feature in export["geojson"]["features"]
        if (
            feature.get("properties", {}).get(
                "daily_stop_location"
            )
            == "Corliss Camp"
        )
    )

    assert corliss["geometry"]["coordinates"] == [
        -72.68425941467285,
        44.706028689619274,
    ]
    assert (
        corliss["properties"]["marker_type"]
        == "gaia-campsite"
    )
    assert corliss["marker_type"] == "gaia-campsite"
    assert (
        corliss["properties"]["marker_color"]
        == "#4ABD32"
    )


def test_gaia_export_uses_curated_access_coordinates_for_resupply_crossings(
    planner_factory,
    trail_root,
):
    planner = planner_factory(
        user_profile={
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "min_daily_miles": 8,
            "max_daily_miles": 16,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=32
    )

    export = export_itinerary_to_gaia_geojson(
        itinerary["daily_plan"],
        trail_root,
    )

    middlebury_gap = next(
        feature
        for feature in export["geojson"]["features"]
        if (
            feature.get("properties", {}).get(
                "daily_stop_location"
            )
            == "Vt. 125 at Middlebury Gap"
        )
    )

    middlebury_reference = next(
        record
        for record in load_resupply_access_reference(
            trail_root
        )
        if record.get("canonical_hint") == "Vt. 125"
    )

    assert middlebury_gap["geometry"]["coordinates"] == (
        middlebury_reference["coordinates"]
    )
    assert (
        middlebury_gap["properties"]["marker_type"]
        == "gaia-car"
    )
    assert (
        middlebury_gap["marker_type"]
        == "gaia-car"
    )
    assert (
        middlebury_gap["properties"]["marker_color"]
        == "#FF0000"
    )


def test_gaia_export_adds_resupply_strategy_markers(
    planner_factory,
    trail_root,
):
    planner = planner_factory(
        user_profile={
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "min_daily_miles": 8,
            "max_daily_miles": 16,
            "resupply_cadence": 5,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=24
    )

    export = export_itinerary_to_gaia_geojson(
        itinerary["daily_plan"],
        trail_root,
        itinerary["resupply_plan"],
    )

    resupply_features = [
        feature
        for feature in export["geojson"]["features"]
        if feature.get("properties", {}).get(
            "cairnos_feature_type"
        ) == "resupply"
    ]

    assert resupply_features

    exportable_resupply_rows = [
        row for row in itinerary["resupply_plan"]
        if "resupply" in row.get("notes", "")
    ]

    assert len(resupply_features) == len(
        exportable_resupply_rows
    )

    manchester = next(
        feature
        for feature in resupply_features
        if feature["properties"][
            "resupply_location"
        ] == "Vt. 11/30"
    )

    manchester_reference = next(
        record
        for record in load_resupply_access_reference(
            trail_root
        )
        if record.get("canonical_hint") == "Vt. 11/30"
    )

    assert manchester["geometry"]["coordinates"] == (
        manchester_reference["coordinates"]
    )
    assert (
        manchester["properties"]["marker_type"]
        == "gaia-car"
    )
    assert (
        manchester["properties"]["marker_color"]
        == "#FF0000"
    )


def test_gaia_export_warns_for_unresolved_synthetic_stop(
    trail_root,
):
    export = export_itinerary_to_gaia_geojson(
        [
            {
                "day": 1,
                "division": "division1",
                "daily_start_mile": 0.0,
                "daily_start_location": "Southern Terminus",
                "daily_stop_mile": None,
                "daily_stop_location": "Backcountry Camp",
                "daily_stop_location_type": "camp",
                "daily_miles": 10.0,
                "daily_elevation_gain": 2400,
                "notes": "",
            }
        ],
        trail_root,
    )

    assert len(export["geojson"]["features"]) == 1
    assert (
        export["geojson"]["features"][0]["geometry"]["type"]
        == "LineString"
    )
    assert len(export["warnings"]) == 1
    assert export["warnings"][0]["day"] == 1
    assert (
        export["warnings"][0]["reason"]
        == (
            "Synthetic location has no "
            "resolvable coordinates"
        )
    )
