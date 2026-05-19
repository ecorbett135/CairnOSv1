# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import json

from cairn.runtime.elevation_calibration import (
    ReferenceRoute,
    apply_route_alignment_status,
    build_anchor_audit_report,
    build_gain_check,
    build_calibration_report,
    build_manifest_calibration_report,
    build_reference_gain_checks,
    build_route_spine_alignment,
    calculate_gain_loss,
    classify_reference_delta,
    load_calibration_manifest,
    load_reference_routes,
    resolve_manifest_status,
)


def test_geojson_reference_route_summary_uses_gaia_units(
    tmp_path,
):
    path = tmp_path / "reference.geojson"
    path.write_text(
        json.dumps({
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "title": "Reference Segment",
                        "distance": 1609.344,
                        "total_ascent": 100.0,
                        "total_descent": 25.0,
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [
                                -73.0,
                                42.0,
                                100.0,
                            ],
                            [
                                -73.0,
                                42.01,
                                200.0,
                            ],
                            [
                                -73.0,
                                42.02,
                                175.0,
                            ],
                        ],
                    },
                }
            ],
        })
    )

    routes = load_reference_routes(
        path
    )
    summary = routes[0].summary()

    assert summary["title"] == "Reference Segment"
    assert summary["summary_distance_miles"] == 1.0
    assert summary["summary_gain_ft"] == 328.0
    assert summary["summary_loss_ft"] == 82.0
    assert summary["raw_gain_ft"] == 328.0


def test_gain_loss_smoothing_suppresses_small_reversals():
    points = [
        (
            -73.0,
            42.0,
            1000.0,
        ),
        (
            -73.0,
            42.01,
            1010.0,
        ),
        (
            -73.0,
            42.02,
            1005.0,
        ),
        (
            -73.0,
            42.03,
            1105.0,
        ),
    ]

    raw_gain, raw_loss = calculate_gain_loss(
        points,
        threshold_ft=0,
    )
    smooth_gain, smooth_loss = (
        calculate_gain_loss(
            points,
            threshold_ft=50,
        )
    )

    assert raw_gain == 110.0
    assert raw_loss == 5.0
    assert smooth_gain == 105.0
    assert smooth_loss == 0.0


def test_calibration_report_infers_known_long_trail_interval(
    tmp_path,
    trail_root,
):
    path = tmp_path / "LongTrailCenterlineTrackRouteNOBO.geojson"
    path.write_text(
        json.dumps({
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "title": (
                            "LongTrailCenterlineTrackRouteNOBO"
                        ),
                        "distance": 400217.45,
                        "total_ascent": 17201.4,
                        "total_descent": 17361.7,
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [
                                -73.155535,
                                42.743819,
                                712.0,
                            ],
                            [
                                -72.488248,
                                45.008651,
                                631.8,
                            ],
                        ],
                    },
                }
            ],
        })
    )

    report = build_calibration_report(
        [
            path,
        ],
        trail_root,
    )

    assert report[0]["cairn_interval"] == {
        "start_mile": 0.0,
        "stop_mile": 272.1,
    }
    assert report[0]["cairn"]["source"] == "terrain"
    assert report[0]["gain_delta_percent"] is not None


def test_calibration_report_shows_linear_and_anchor_mapping(
    tmp_path,
    trail_root,
):
    path = tmp_path / "goddardtostory.geojson"
    path.write_text(
        json.dumps({
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "title": "GoddardtoStorySpringShelters",
                        "distance": 13379.747,
                        "total_ascent": 323.8,
                        "total_descent": 586.266,
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [
                                -73.072233,
                                42.974273,
                                1086.0,
                            ],
                            [
                                -73.012413,
                                43.050631,
                                850.0,
                            ],
                        ],
                    },
                }
            ],
        })
    )

    report = build_calibration_report(
        [
            path,
        ],
        trail_root,
        start_mile=24.4,
        stop_mile=33.3,
    )

    row = report[0]

    assert row["linear_terrain_interval"] == {
        "start_mile": 22.338,
        "stop_mile": 30.485,
    }
    assert row["anchor_terrain_interval"] == {
        "start_mile": 22.558,
        "stop_mile": 30.881,
    }
    assert (
        row["cairn"]["elevation_gain_ft"]
        > row["linear_cairn"]["elevation_gain_ft"]
    )


def test_anchor_audit_report_surfaces_mapping_deltas(
    trail_root,
):
    report = build_anchor_audit_report(
        trail_root
    )

    assert report["anchor_count"] > 50
    assert report["interval_count"] > 50
    assert report["flagged_count"] > 0
    assert any(
        interval["flagged"]
        for interval in report["intervals"]
    )


def test_route_spine_alignment_flags_reference_route_detour(
    planner,
):
    route = ReferenceRoute(
        path="local-reference.geojson",
        title="Local Reference",
        source_format="geojson",
        points=[
            (
                -73.155535,
                42.743819,
                None,
            ),
            (
                -72.0,
                44.0,
                None,
            ),
        ],
    )

    alignment = build_route_spine_alignment(
        route,
        planner,
        sample_limit=10,
    )

    assert alignment["status"] == "warn"
    assert (
        alignment[
            "severe_off_spine_sample_count"
        ]
        > 0
    )
    assert alignment["worst_points"]


def test_calibration_manifest_parses_core_fields(
    tmp_path,
):
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        "\n".join([
            "name,start_mile,stop_mile,reference_gain_ft,"
            "reference_distance_miles,source_tool,notes,file",
            "Goddard to Story,24.4,33.3,1062,8.3,Gaia,"
            "known benchmark,goddardtostory.geojson",
        ])
    )

    rows = load_calibration_manifest(
        manifest
    )

    assert len(rows) == 1
    assert rows[0].name == "Goddard to Story"
    assert rows[0].start_mile == 24.4
    assert rows[0].stop_mile == 33.3
    assert rows[0].reference_gain_ft == 1062
    assert rows[0].file == "goddardtostory.geojson"


def test_reference_delta_classification_thresholds():
    assert (
        classify_reference_delta(
            240,
            30,
        )
        == "pass"
    )
    assert (
        classify_reference_delta(
            450,
            18,
        )
        == "warn"
    )
    assert (
        classify_reference_delta(
            700,
            35,
        )
        == "fail"
    )
    assert (
        classify_reference_delta(
            None,
            None,
        )
        == "unknown"
    )


def test_manifest_status_warns_when_summary_conflicts_with_track_gain():
    route_summary = {
        "summary_gain_ft": 3200,
        "smoothed_gain_ft": 3360,
        "raw_gain_ft": 3970,
    }

    checks = build_reference_gain_checks(
        3971,
        None,
        route_summary,
    )
    primary = next(
        check
        for check in checks
        if check["source"] == "route_summary"
    )

    status, reason, best = resolve_manifest_status(
        primary,
        checks,
        manifest_gain=None,
    )

    assert primary["status"] == "fail"
    assert status == "warn"
    assert (
        reason
        == "route_summary_disagrees_with_embedded_track_elevation"
    )
    assert best["source"] == "route_raw"
    assert best["status"] == "pass"


def test_manifest_reference_gain_is_not_overridden_by_track_gain():
    primary = build_gain_check(
        3971,
        3200,
        "manifest",
    )
    checks = [
        primary,
        build_gain_check(
            3971,
            3970,
            "route_raw",
        ),
    ]

    status, reason, best = resolve_manifest_status(
        primary,
        checks,
        manifest_gain=3200,
    )

    assert status == "fail"
    assert reason == "manifest_reference_gain"
    assert best == primary


def test_route_alignment_warning_overrides_reference_pass():
    status, reason = apply_route_alignment_status(
        "pass",
        "primary_reference_gain",
        {
            "status": "warn",
        },
    )

    assert status == "warn"
    assert (
        reason
        == "reference_route_deviates_from_compiled_spine"
    )


def test_manifest_calibration_report_compares_reference_rows(
    tmp_path,
    trail_root,
):
    reference = tmp_path / "goddardtostory.geojson"
    reference.write_text(
        json.dumps({
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "title": "GoddardToStory",
                        "distance": 13379.747,
                        "total_ascent": 335.28,
                        "total_descent": 586.266,
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [
                                -73.072233,
                                42.974273,
                                1086.0,
                            ],
                            [
                                -73.012413,
                                43.050631,
                                850.0,
                            ],
                        ],
                    },
                }
            ],
        })
    )
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        "\n".join([
            "name,start_mile,stop_mile,reference_gain_ft,"
            "reference_distance_miles,source_tool,notes,file",
            "GoddardToStory,24.4,33.3,,8.3,Gaia,"
            "fixture,goddardtostory.geojson",
        ])
    )

    report = build_manifest_calibration_report(
        manifest,
        trail_root,
    )
    row = report["rows"][0]

    assert report["summary"]["rows"] == 1
    assert row["reference_gain_source"] == "route_summary"
    assert row["reference_gain_ft"] == 1100
    assert row["primary_gain_check"]["source"] == "route_summary"
    assert row["reference_gain_checks"]
    assert row["status_reason"] in {
        "primary_reference_gain",
        "route_summary_disagrees_with_embedded_track_elevation",
    }
    assert row["status"] in {
        "pass",
        "warn",
    }
    assert row["anchor_terrain_interval"] == {
        "start_mile": 22.558,
        "stop_mile": 30.881,
    }
