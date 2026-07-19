# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0

import json

from build_topo.compiler.approach_trails import (
    load_approach_geometries,
    load_approach_rows,
)


def test_compiler_promotes_north_adams_geometry_with_exact_provenance(
    trail_root,
):
    rows = load_approach_rows(
        trail_root / "raw" / "csv" / "approach_trails.csv"
    )
    geometries = load_approach_geometries(
        rows,
        trail_root_path=trail_root,
        sources_path=(
            trail_root / "raw" / "csv" / "approach_geometry_sources.csv"
        ),
    )

    assert len(geometries) == 1
    geometry = geometries[0]
    assert geometry["geometry_id"] == "approach_north_adams_geometry_v1"
    assert geometry["approach_id"] == "approach_north_adams"
    assert geometry["connected_terminus"] == "southern"
    assert geometry["start_mile"] == -3.8
    assert geometry["end_mile"] == 0.0
    assert geometry["coordinate_count"] == 453
    assert geometry["elevation"] == {
        "status": "complete",
        "unit": "m",
        "method": "source_embedded_coordinate",
        "coordinate_count": 453,
        "elevation_coordinate_count": 453,
        "source_path": "raw/geojson/gaia_reference.geojson",
        "source_feature_id": "399a680d-2d50-440e-a22a-c82fd457f3fd",
    }
    coordinates = [
        coordinate
        for line in geometry["geometry"]["coordinates"]
        for coordinate in line
    ]
    assert all(len(coordinate) == 3 for coordinate in coordinates)
    assert coordinates[0][2] == 190.4
    assert coordinates[-1][2] == 700.2
    assert geometry["provenance"] == {
        "source_path": "raw/geojson/gaia_reference.geojson",
        "source_feature_id": "399a680d-2d50-440e-a22a-c82fd457f3fd",
        "source_feature_title": "North Adams Approach Trail",
        "source_feature_updated_date": "2026-04-18T19:12:44Z",
        "source_kind": "Maintainer-owned Gaia GPS route export",
        "source_license_status": "UNKNOWN — needs review",
        "transformation_notes": (
            "Longitude, latitude, and source-embedded elevation coordinates "
            "only; source notes and non-geometry personal metadata are "
            "excluded from the compiled artifact."
        ),
    }
    serialized = json.dumps(geometry)
    assert "Excerpt From" not in serialized
    assert "e.corbett@me.com" not in serialized


def test_committed_approach_geometry_matches_compiler_output(trail_root):
    rows = load_approach_rows(
        trail_root / "raw" / "csv" / "approach_trails.csv"
    )
    expected = load_approach_geometries(
        rows,
        trail_root_path=trail_root,
        sources_path=(
            trail_root / "raw" / "csv" / "approach_geometry_sources.csv"
        ),
    )
    compiled = json.loads(
        (
            trail_root / "compiled" / "approach_trails.json"
        ).read_text()
    )

    assert compiled["schema_version"] == "cairnos_approach_trails_v2"
    assert compiled["approach_geometries"] == expected
