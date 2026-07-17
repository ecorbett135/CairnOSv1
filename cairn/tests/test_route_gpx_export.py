# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import xml.etree.ElementTree as ET

import cairn.export.route_gpx as route_gpx
from cairn.export.gaia_geojson import (
    load_spine_coordinates,
)
from cairn.export.route_gpx import (
    CAIRNOS_NAMESPACE,
    GPX_GEOMETRY_MODE,
    GPX_NAMESPACE,
    ROUTE_GPX_EXPORT_VERSION,
    SPINE_GEOMETRY_SOURCE,
    WAYPOINT_ONLY_GEOMETRY_MODE,
    build_route_gpx_artifacts,
)


NS = {
    "gpx": GPX_NAMESPACE,
    "cairnos": CAIRNOS_NAMESPACE,
}


def parse_gpx(payload):
    return ET.fromstring(
        payload
    )


def gpx_waypoints(root):
    return root.findall(
        "gpx:wpt",
        NS,
    )


def gpx_track_points(root):
    return root.findall(
        "gpx:trk/gpx:trkseg/gpx:trkpt",
        NS,
    )


def test_route_gpx_export_builds_full_plan_and_daily_artifacts(
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

    export = build_route_gpx_artifacts(
        itinerary["daily_plan"],
        trail_root,
        direction="NOBO",
        trail_id="vermont_long_trail",
        generated_at="20260520T120000Z",
    )

    assert (
        export["export_version"]
        == ROUTE_GPX_EXPORT_VERSION
    )
    assert (
        export["geometry_mode"]
        == GPX_GEOMETRY_MODE
    )
    assert len(export["manifest"]) == (
        len(itinerary["daily_plan"]) + 1
    )
    assert set(export["artifacts"]) == {
        entry["filename"]
        for entry in export["manifest"]
    }

    full_entry = export["manifest"][0]

    assert full_entry["artifact_id"] == "full_plan"
    assert full_entry["scope"] == "full_plan"
    assert full_entry["filename"] == (
        "cairnos_route_vermont_long_trail_nobo_"
        "full_plan.gpx"
    )
    assert (
        full_entry["geometry_mode"]
        == GPX_GEOMETRY_MODE
    )
    assert full_entry["track_count"] == 1
    assert full_entry["track_segment_count"] == 1
    assert full_entry["track_point_count"] > 0
    assert full_entry["geometry_source"] == (
        SPINE_GEOMETRY_SOURCE
    )
    assert "full_plan_spine_only" in full_entry[
        "warning_codes"
    ]
    assert "verify_official_sources" in full_entry[
        "warning_codes"
    ]

    full_root = parse_gpx(
        export["artifacts"][
            full_entry["filename"]
        ]
    )

    assert full_root.tag == (
        f"{{{GPX_NAMESPACE}}}gpx"
    )
    assert (
        full_root.findtext(
            "gpx:metadata/gpx:time",
            namespaces=NS,
        )
        == "2026-05-20T12:00:00Z"
    )
    track = full_root.find(
        "gpx:trk",
        NS,
    )
    assert track is not None
    assert full_root.find(
        "gpx:rte",
        NS,
    ) is None
    track_points = gpx_track_points(
        full_root
    )
    spine_coordinates = load_spine_coordinates(
        trail_root
    )
    assert len(track_points) == len(
        spine_coordinates
    )
    assert len(track_points) == full_entry[
        "track_point_count"
    ]
    assert float(track_points[0].get("lon")) == (
        spine_coordinates[0][0]
    )
    assert float(track_points[0].get("lat")) == (
        spine_coordinates[0][1]
    )
    assert (
        track.findtext(
            "gpx:extensions/cairnos:geometry_source",
            namespaces=NS,
        )
        == SPINE_GEOMETRY_SOURCE
    )
    assert len(
        gpx_waypoints(full_root)
    ) == full_entry["waypoint_count"]
    assert full_entry["waypoint_count"] == (
        len(itinerary["daily_plan"]) * 2
    )

    first_waypoint = gpx_waypoints(
        full_root
    )[0]
    assert first_waypoint.get("lat")
    assert first_waypoint.get("lon")
    assert (
        first_waypoint.findtext(
            "gpx:name",
            namespaces=NS,
        )
        == (
            "Day 001 start - "
            f"{itinerary['daily_plan'][0]['daily_start_location']}"
        )
    )
    assert (
        first_waypoint.findtext(
            "gpx:extensions/cairnos:day",
            namespaces=NS,
        )
        == "1"
    )
    assert (
        first_waypoint.findtext(
            "gpx:extensions/cairnos:position",
            namespaces=NS,
        )
        == "start"
    )


def test_route_gpx_export_builds_parseable_day_artifacts(
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

    export = build_route_gpx_artifacts(
        itinerary["daily_plan"],
        trail_root,
        direction="NOBO",
        trail_id="vermont_long_trail",
        generated_at="20260520T120000Z",
    )
    day_entry = export["manifest"][1]

    assert day_entry["artifact_id"] == "day_001"
    assert day_entry["scope"] == "day"
    assert day_entry["geometry_mode"] == (
        WAYPOINT_ONLY_GEOMETRY_MODE
    )
    assert day_entry["track_count"] == 0
    assert day_entry["track_segment_count"] == 0
    assert day_entry["track_point_count"] == 0
    assert "waypoint_only_gpx" in day_entry[
        "warning_codes"
    ]
    assert day_entry["day"] == 1
    assert day_entry["daily_start_location"] == (
        itinerary["daily_plan"][0][
            "daily_start_location"
        ]
    )
    assert day_entry["daily_stop_location"] == (
        itinerary["daily_plan"][0][
            "daily_stop_location"
        ]
    )

    root = parse_gpx(
        export["artifacts"][
            day_entry["filename"]
        ]
    )
    waypoint_names = [
        waypoint.findtext(
            "gpx:name",
            namespaces=NS,
        )
        for waypoint in gpx_waypoints(root)
    ]

    assert waypoint_names == [
        (
            "Day 001 start - "
            f"{itinerary['daily_plan'][0]['daily_start_location']}"
        ),
        (
            "Day 001 stop - "
            f"{itinerary['daily_plan'][0]['daily_stop_location']}"
        ),
    ]
    assert day_entry["waypoint_count"] == 2
    assert root.find(
        "gpx:trk",
        NS,
    ) is None


def test_route_gpx_export_preserves_sobo_direction_context(
    planner_factory,
    trail_root,
):
    planner = planner_factory(
        user_profile={
            "direction": "SOBO",
            "ingress_route": "Journey's End Trail",
            "egress_route": "Williamstown Approach",
            "min_daily_miles": 8,
            "max_daily_miles": 16,
        },
    )
    itinerary = planner.synthesize_itinerary(
        desired_days=28
    )

    export = build_route_gpx_artifacts(
        itinerary["daily_plan"],
        trail_root,
        direction="SOBO",
        trail_id="vermont_long_trail",
        generated_at="20260520T120000Z",
    )
    first_day = export["manifest"][1]
    full_plan = export["manifest"][0]

    assert first_day["filename"] == (
        "cairnos_route_vermont_long_trail_sobo_"
        "day_001.gpx"
    )
    assert (
        first_day["daily_start_mile"]
        > first_day["daily_stop_mile"]
    )
    full_root = parse_gpx(
        export["artifacts"][
            full_plan["filename"]
        ]
    )
    track_points = gpx_track_points(
        full_root
    )
    spine_coordinates = load_spine_coordinates(
        trail_root
    )

    assert float(track_points[0].get("lon")) == (
        spine_coordinates[-1][0]
    )
    assert float(track_points[0].get("lat")) == (
        spine_coordinates[-1][1]
    )
    assert float(track_points[-1].get("lon")) == (
        spine_coordinates[0][0]
    )
    assert float(track_points[-1].get("lat")) == (
        spine_coordinates[0][1]
    )


def test_route_gpx_export_warns_when_spine_geometry_is_missing(
    planner_factory,
    trail_root,
    monkeypatch,
):
    monkeypatch.setattr(
        route_gpx,
        "load_spine_coordinates",
        lambda _trail_root: [],
    )
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

    export = build_route_gpx_artifacts(
        itinerary["daily_plan"],
        trail_root,
        direction="NOBO",
        trail_id="vermont_long_trail",
        generated_at="20260520T120000Z",
    )
    full_plan = export["manifest"][0]
    full_root = parse_gpx(
        export["artifacts"][
            full_plan["filename"]
        ]
    )

    assert export["geometry_mode"] == (
        WAYPOINT_ONLY_GEOMETRY_MODE
    )
    assert full_plan["geometry_mode"] == (
        WAYPOINT_ONLY_GEOMETRY_MODE
    )
    assert full_plan["track_point_count"] == 0
    assert "missing_route_spine_geometry" in full_plan[
        "warning_codes"
    ]
    assert full_root.find(
        "gpx:trk",
        NS,
    ) is None
    assert (
        full_root.findtext(
            "gpx:metadata/gpx:extensions/cairnos:warning",
            namespaces=NS,
        )
        == route_gpx.MISSING_SPINE_WARNING["message"]
    )


def test_route_gpx_export_reports_unresolved_waypoint_coordinates(
    trail_root,
):
    export = build_route_gpx_artifacts(
        [
            {
                "day": 1,
                "division": "synthetic",
                "daily_start_mile": None,
                "daily_start_location": (
                    "Unmapped Start"
                ),
                "daily_start_location_type": (
                    "synthetic"
                ),
                "daily_stop_mile": None,
                "daily_stop_location": (
                    "Unmapped Stop"
                ),
                "daily_stop_location_type": (
                    "synthetic"
                ),
                "daily_miles": 0,
                "daily_elevation_gain": 0,
                "notes": "",
            }
        ],
        trail_root,
        direction="NOBO",
        trail_id="vermont_long_trail",
        generated_at="20260520T120000Z",
    )

    missing = [
        warning for warning in export["warnings"]
        if warning["code"]
        == "missing_waypoint_coordinates"
    ]

    assert len(missing) == 2
    assert {
        warning["position"]
        for warning in missing
    } == {
        "start",
        "stop",
    }
    assert export["manifest"][0][
        "waypoint_count"
    ] == 0
    assert "missing_waypoint_coordinates" in export[
        "manifest"
    ][0]["warning_codes"]
    assert "missing_waypoint_coordinates" in export[
        "manifest"
    ][1]["warning_codes"]

    root = parse_gpx(
        export["artifacts"][
            export["manifest"][1]["filename"]
        ]
    )

    assert gpx_waypoints(root) == []
