# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import json

from cairn.runtime.elevation_calibration import (
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
