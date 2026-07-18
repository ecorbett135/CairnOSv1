# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0

import json

from build_topo.compiler.spine import load_gpx_track


def test_spine_compiler_retains_complete_source_gpx_elevation(trail_root):
    source_points = load_gpx_track(
        trail_root / "raw" / "gpx" / "long-trail-spine.gpx"
    )
    compiled = json.loads(
        (trail_root / "compiled" / "spine.geojson").read_text()
    )
    feature = compiled["features"][0]
    compiled_points = feature["geometry"]["coordinates"]

    assert len(source_points) == 19817
    assert compiled_points == [list(point) for point in source_points]
    assert all(len(point) == 3 for point in compiled_points)
    assert compiled_points[0] == [-73.1555346, 42.7438189, 712.0]
    assert compiled_points[-1] == [-72.4882482, 45.0086505, 631.796875]
    assert feature["properties"] == {
        "trail_name": "vermont_long_trail",
        "schema_version": "1.0",
        "geometry_id": "defined_trail_spine",
        "source_path": "raw/gpx/long-trail-spine.gpx",
        "source_kind": "Raw GPX track",
        "source_license_status": "UNKNOWN — needs review",
        "elevation_status": "complete",
        "elevation_unit": "m",
        "elevation_method": "source_embedded_gpx_ele",
        "elevation_coordinate_count": 19817,
    }


def test_spine_compiler_does_not_promote_partial_or_invalid_elevation(tmp_path):
    gpx_path = tmp_path / "partial.gpx"
    gpx_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1" version="1.1">
  <trk><trkseg>
    <trkpt lat="42.0" lon="-73.0"><ele>100.0</ele></trkpt>
    <trkpt lat="42.1" lon="-73.1"><ele>not-a-number</ele></trkpt>
    <trkpt lat="42.2" lon="-73.2" />
  </trkseg></trk>
</gpx>
""",
        encoding="utf-8",
    )

    assert load_gpx_track(gpx_path) == [
        (-73.0, 42.0),
        (-73.1, 42.1),
        (-73.2, 42.2),
    ]
