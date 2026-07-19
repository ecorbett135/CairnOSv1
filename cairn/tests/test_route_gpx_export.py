# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import xml.etree.ElementTree as ET
import copy
import json
import math
from pathlib import Path

import cairn.export.route_gpx as route_gpx
import cairn.export.route_geometry as route_geometry
import pytest
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
from cairn.export.route_geometry import (
    APPROACH_GEOMETRY_SOURCE,
    DAILY_TRACK_GEOMETRY_MODE,
    RouteGeometryValidationError,
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


def parsed_track_coordinates(root):
    return [
        [
            float(point.get("lon")),
            float(point.get("lat")),
            *(
                [float(point.findtext("gpx:ele", namespaces=NS))]
                if point.find("gpx:ele", NS) is not None
                else []
            ),
        ]
        for point in gpx_track_points(root)
    ]


def independent_track_metrics(points):
    radius_m = 6371008.8
    length_m = 0.0
    for first, second in zip(points, points[1:]):
        first_latitude = math.radians(first[1])
        second_latitude = math.radians(second[1])
        latitude_delta = second_latitude - first_latitude
        longitude_delta = math.radians(second[0] - first[0])
        value = (
            math.sin(latitude_delta / 2) ** 2
            + math.cos(first_latitude)
            * math.cos(second_latitude)
            * math.sin(longitude_delta / 2) ** 2
        )
        length_m += radius_m * 2 * math.asin(math.sqrt(value))
    ascent_m = sum(
        max(second[2] - first[2], 0.0)
        for first, second in zip(points, points[1:])
    )
    descent_m = sum(
        max(first[2] - second[2], 0.0)
        for first, second in zip(points, points[1:])
    )
    average_grade = (
        ((points[-1][2] - points[0][2]) / length_m) * 100
        if length_m
        else 0.0
    )
    return {
        "length_m": round(length_m, 3),
        "total_ascent_m": round(ascent_m, 3),
        "total_descent_m": round(descent_m, 3),
        "average_grade_percent": round(average_grade, 3),
    }


def selected_routes(ingress, egress):
    return {
        "contract_version": "cairnos_route_selection_v1",
        "ingress_approach_id": ingress,
        "egress_approach_id": egress,
    }


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
    assert all(
        point.find("gpx:ele", NS) is not None
        for point in track_points
    )
    assert full_entry["elevation"] == {
        "status": "complete",
        "unit": "m",
        "track_point_count": len(track_points),
        "elevation_point_count": len(track_points),
        "missing_elevation_point_count": 0,
        "boundary_elevation_method": (
            "linear_between_adjacent_source_elevations_at_"
            "mileage_slice_boundary"
        ),
    }
    parsed_points = parsed_track_coordinates(full_root)
    expected_metrics = independent_track_metrics(parsed_points)
    for field_name, value in expected_metrics.items():
        assert full_entry["metrics"][field_name] == pytest.approx(
            value,
            abs=0.001,
        )
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
    assert day_entry["geometry_mode"] == DAILY_TRACK_GEOMETRY_MODE
    assert day_entry["track_count"] == 1
    assert day_entry["track_segment_count"] == 1
    assert day_entry["track_point_count"] > 1
    assert "waypoint_only_gpx" not in day_entry["warning_codes"]
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
    assert root.find("gpx:trk", NS) is not None
    assert len(gpx_track_points(root)) == day_entry["track_point_count"]
    assert all(
        point.find("gpx:ele", NS) is not None
        for point in gpx_track_points(root)
    )
    assert day_entry["elevation"]["status"] == "complete"
    assert day_entry["metrics"]["length_m"] > 0


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


def test_selected_north_adams_ingress_precedes_nobo_spine_and_daily_slice(
    planner_factory,
    trail_root,
):
    planner = planner_factory(
        user_profile={
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "egress_route": "Journey's End Trail",
            "min_daily_miles": 8,
            "max_daily_miles": 16,
        }
    )
    itinerary = planner.synthesize_itinerary(desired_days=28)
    export = build_route_gpx_artifacts(
        itinerary["daily_plan"],
        trail_root,
        direction="NOBO",
        trail_id="vermont_long_trail",
        generated_at="20260718T120000Z",
        route_selection=selected_routes(
            "approach_north_adams",
            "egress_journeys_end",
        ),
    )

    approach_payload = json.loads(
        (
            trail_root / "compiled" / "approach_trails.json"
        ).read_text()
    )
    approach_start = approach_payload["approach_geometries"][0][
        "geometry"
    ]["coordinates"][0][0]
    spine_coordinates = load_spine_coordinates(trail_root)
    full_entry = export["manifest"][0]
    full_root = parse_gpx(export["artifacts"][full_entry["filename"]])
    full_points = gpx_track_points(full_root)

    assert full_entry["geometry_source"] == "composed_selected_route"
    assert full_entry["track_point_count"] > len(spine_coordinates)
    assert [
        source.get("approach_id")
        for source in full_entry["geometry_sources"]
    ] == ["approach_north_adams", None]
    assert float(full_points[0].get("lon")) == approach_start[0]
    assert float(full_points[0].get("lat")) == approach_start[1]
    assert (
        full_points[0].get("lon"),
        full_points[0].get("lat"),
    ) != (
        str(spine_coordinates[0][0]),
        str(spine_coordinates[0][1]),
    )
    assert "full_plan_spine_only" not in full_entry["warning_codes"]
    assert "selected_route_geometry_unavailable" in full_entry[
        "warning_codes"
    ]
    assert "route_geometry_incomplete" in full_entry["warning_codes"]
    assert (
        "authoritative_route_elevation_unavailable"
        in full_entry["warning_codes"]
    )
    assert full_entry["elevation"]["status"] == "complete"
    assert full_entry["route_elevation_complete"] is False
    assert all(
        point.find("gpx:ele", NS) is not None
        for point in full_points
    )

    route_parts = export["route_parts"]
    assert [part["role"] for part in route_parts] == [
        "ingress",
        "spine",
        "egress",
    ]
    assert [part["geometry_status"] for part in route_parts] == [
        "available",
        "available",
        "unavailable",
    ]
    assert [part["elevation"]["status"] for part in route_parts] == [
        "complete",
        "complete",
        "unavailable",
    ]
    assert route_parts[0]["route_part_id"] == (
        "ingress:approach_north_adams"
    )
    assert route_parts[0]["provenance"]["source_feature_id"] == (
        "399a680d-2d50-440e-a22a-c82fd457f3fd"
    )
    assert route_parts[1]["provenance"]["source_path"] == (
        "raw/gpx/long-trail-spine.gpx"
    )
    assert route_parts[2]["route_part_id"] == (
        "egress:egress_journeys_end"
    )
    assert export["route_completeness"]["elevation_complete"] is False
    gpx_route_parts = full_root.findall(
        "gpx:trk/gpx:extensions/cairnos:route_parts/cairnos:route_part",
        NS,
    )
    assert [part.get("id") for part in gpx_route_parts] == [
        "ingress:approach_north_adams",
        "spine:defined_trail_spine",
    ]
    assert all(
        part.find("cairnos:elevation_status", NS).text == "complete"
        for part in gpx_route_parts
    )

    first_day = export["manifest"][1]
    first_day_root = parse_gpx(
        export["artifacts"][first_day["filename"]]
    )
    first_day_points = gpx_track_points(first_day_root)
    assert first_day["geometry_mode"] == DAILY_TRACK_GEOMETRY_MODE
    assert first_day_points[0].attrib == full_points[0].attrib
    assert first_day["geometry_sources"][0]["approach_id"] == (
        "approach_north_adams"
    )
    assert first_day["route_elevation_complete"] is True
    assert first_day["elevation"]["status"] == "complete"
    assert all(
        point.find("gpx:ele", NS) is not None
        for point in first_day_points
    )
    assert first_day["geometry_sources"][0]["route_part_id"] == (
        "ingress:approach_north_adams"
    )

    final_day = export["manifest"][-1]
    assert final_day["route_elevation_complete"] is False
    assert "route_geometry_incomplete" in final_day["warning_codes"]


def test_selected_north_adams_egress_follows_sobo_spine(
    planner_factory,
    trail_root,
):
    planner = planner_factory(
        user_profile={
            "direction": "SOBO",
            "ingress_route": "Journey's End Trail",
            "egress_route": "North Adams Approach",
            "min_daily_miles": 8,
            "max_daily_miles": 16,
        }
    )
    itinerary = planner.synthesize_itinerary(desired_days=28)
    export = build_route_gpx_artifacts(
        itinerary["daily_plan"],
        trail_root,
        direction="SOBO",
        trail_id="vermont_long_trail",
        generated_at="20260718T120000Z",
        route_selection=selected_routes(
            "egress_journeys_end",
            "approach_north_adams",
        ),
    )
    approach_payload = json.loads(
        (
            trail_root / "compiled" / "approach_trails.json"
        ).read_text()
    )
    approach_start = approach_payload["approach_geometries"][0][
        "geometry"
    ]["coordinates"][0][0]
    full_entry = export["manifest"][0]
    full_points = gpx_track_points(
        parse_gpx(export["artifacts"][full_entry["filename"]])
    )

    assert float(full_points[-1].get("lon")) == approach_start[0]
    assert float(full_points[-1].get("lat")) == approach_start[1]
    assert full_entry["geometry_sources"][-1]["approach_id"] == (
        "approach_north_adams"
    )
    assert all(
        point.find("gpx:ele", NS) is not None
        for point in full_points
    )
    assert float(full_points[0].findtext("gpx:ele", namespaces=NS)) == (
        pytest.approx(631.797, abs=0.001)
    )
    assert float(full_points[-1].findtext("gpx:ele", namespaces=NS)) == (
        pytest.approx(190.4, abs=0.001)
    )
    expected_metrics = independent_track_metrics(
        parsed_track_coordinates(
            parse_gpx(export["artifacts"][full_entry["filename"]])
        )
    )
    assert full_entry["metrics"]["total_ascent_m"] == pytest.approx(
        expected_metrics["total_ascent_m"],
        abs=0.001,
    )
    assert full_entry["metrics"]["total_descent_m"] == pytest.approx(
        expected_metrics["total_descent_m"],
        abs=0.001,
    )
    last_day = export["manifest"][-1]
    assert last_day["geometry_sources"][-1]["approach_id"] == (
        "approach_north_adams"
    )


def test_section_interval_slices_selected_approach_before_spine(
    planner_factory,
    trail_root,
):
    planner = planner_factory(
        user_profile={
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "egress_route": "Journey's End Trail",
            "min_daily_miles": 8,
            "max_daily_miles": 16,
        }
    )
    first_day = planner.synthesize_itinerary(desired_days=28)["daily_plan"][0]
    section_day = {
        **first_day,
        "daily_start_mile": -2.4,
        "daily_stop_mile": 1.0,
        "daily_miles": 3.4,
    }
    export = build_route_gpx_artifacts(
        [section_day],
        trail_root,
        direction="NOBO",
        trail_id="vermont_long_trail",
        generated_at="20260718T120000Z",
        route_selection=selected_routes(
            "approach_north_adams",
            "egress_journeys_end",
        ),
    )
    full_entry = export["manifest"][0]
    full_points = gpx_track_points(
        parse_gpx(export["artifacts"][full_entry["filename"]])
    )
    source_start = json.loads(
        (
            trail_root / "compiled" / "approach_trails.json"
        ).read_text()
    )["approach_geometries"][0]["geometry"]["coordinates"][0][0]

    assert full_entry["geometry_sources"][0]["approach_id"] == (
        "approach_north_adams"
    )
    assert float(full_points[0].get("lon")) != source_start[0]
    assert export["manifest"][1]["track_point_count"] == len(full_points)
    assert all(
        point.find("gpx:ele", NS) is not None
        for point in full_points
    )
    assert full_entry["elevation"]["boundary_elevation_method"] == (
        "linear_between_adjacent_source_elevations_at_"
        "mileage_slice_boundary"
    )
    assert full_entry["route_elevation_complete"] is True


def test_alternate_selection_never_substitutes_north_adams_geometry(
    planner_factory,
    trail_root,
):
    planner = planner_factory(
        user_profile={
            "direction": "NOBO",
            "ingress_route": "Williamstown Approach",
            "egress_route": "Journey's End Trail",
            "min_daily_miles": 8,
            "max_daily_miles": 16,
        }
    )
    itinerary = planner.synthesize_itinerary(desired_days=28)
    export = build_route_gpx_artifacts(
        itinerary["daily_plan"],
        trail_root,
        direction="NOBO",
        trail_id="vermont_long_trail",
        generated_at="20260718T120000Z",
        route_selection=selected_routes(
            "approach_williamstown",
            "egress_journeys_end",
        ),
    )
    full_entry = export["manifest"][0]

    assert all(
        source.get("approach_id") != "approach_north_adams"
        for source in full_entry["geometry_sources"]
    )
    assert full_entry["geometry_source"] == SPINE_GEOMETRY_SOURCE
    assert [
        warning["approach_id"]
        for warning in export["warnings"]
        if warning["code"] == "selected_route_geometry_unavailable"
    ] == ["approach_williamstown", "egress_journeys_end"]


def test_route_gpx_flags_missing_source_elevation_without_fabrication(
    trail_root,
    monkeypatch,
):
    two_dimensional_spine = load_spine_coordinates(trail_root)
    monkeypatch.setattr(
        route_gpx,
        "load_spine_route_geometry",
        lambda _trail_root: {
            "coordinates": two_dimensional_spine,
            "elevation": {
                "status": "unavailable",
                "unit": "m",
                "method": None,
                "coordinate_count": len(two_dimensional_spine),
                "elevation_coordinate_count": 0,
            },
            "provenance": {
                "source_path": "compiled/spine.geojson",
            },
        },
    )
    export = build_route_gpx_artifacts(
        [
            {
                "day": 1,
                "division": "division01",
                "daily_start_mile": 0.0,
                "daily_stop_mile": 1.0,
                "daily_start_location": "Southern Terminus",
                "daily_stop_location": "Mile 1",
                "daily_miles": 1.0,
                "daily_elevation_gain": 0.0,
                "notes": "",
            }
        ],
        trail_root,
        direction="NOBO",
        trail_id="vermont_long_trail",
        generated_at="20260718T120000Z",
    )
    full_entry = export["manifest"][0]
    full_root = parse_gpx(export["artifacts"][full_entry["filename"]])

    assert full_entry["geometry_coverage"]["geometry_complete"] is True
    assert full_entry["elevation"]["status"] == "unavailable"
    assert full_entry["metrics"]["length_m"] > 0
    assert full_entry["metrics"]["total_ascent_m"] is None
    assert full_entry["metrics"]["total_descent_m"] is None
    assert full_entry["metrics"]["average_grade_percent"] is None
    assert (
        "authoritative_route_elevation_unavailable"
        in full_entry["warning_codes"]
    )
    assert all(
        point.find("gpx:ele", NS) is None
        for point in gpx_track_points(full_root)
    )


def test_committed_v4_consumer_fixture_is_parseable_and_metric_consistent():
    fixture = json.loads(
        (
            Path(__file__).parent
            / "fixtures"
            / "route_gpx"
            / "elevation_contract_v4.json"
        ).read_text()
    )
    entry = fixture["manifest"][0]
    root = parse_gpx(fixture["artifacts"][entry["filename"]])
    points = parsed_track_coordinates(root)

    assert fixture["export_version"] == "cairnos_route_gpx_v4"
    assert entry["elevation"]["status"] == "complete"
    assert len(points) == entry["track_point_count"]
    assert all(len(point) == 3 for point in points)
    expected_metrics = independent_track_metrics(points)
    for field_name, value in expected_metrics.items():
        assert entry["metrics"][field_name] == pytest.approx(
            value,
            abs=0.001,
        )


def test_selected_disconnected_approach_geometry_fails_deterministically(
    planner_factory,
    trail_root,
    monkeypatch,
):
    planner = planner_factory(
        user_profile={
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "egress_route": "Journey's End Trail",
            "min_daily_miles": 8,
            "max_daily_miles": 16,
        }
    )
    itinerary = planner.synthesize_itinerary(desired_days=28)
    payload = json.loads(
        (
            trail_root / "compiled" / "approach_trails.json"
        ).read_text()
    )
    disconnected = copy.deepcopy(payload)
    disconnected["approach_geometries"][0]["geometry"] = {
        "type": "LineString",
        "coordinates": [[0.0, 0.0], [0.1, 0.1]],
    }
    monkeypatch.setattr(
        route_geometry,
        "_load_approach_payload",
        lambda _trail_root: disconnected,
    )

    with pytest.raises(
        RouteGeometryValidationError,
        match=(
            "Selected ingress approach_id 'approach_north_adams' geometry "
            "is disconnected from the southern defined-trail terminus"
        ),
    ):
        build_route_gpx_artifacts(
            itinerary["daily_plan"],
            trail_root,
            direction="NOBO",
            trail_id="vermont_long_trail",
            generated_at="20260718T120000Z",
            route_selection=selected_routes(
                "approach_north_adams",
                "egress_journeys_end",
            ),
        )
