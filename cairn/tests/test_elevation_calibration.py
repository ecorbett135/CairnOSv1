# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import json

from cairn.runtime.elevation_calibration import (
    build_anchor_audit_report,
    build_calibration_report,
    calculate_gain_loss,
    load_reference_routes,
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
