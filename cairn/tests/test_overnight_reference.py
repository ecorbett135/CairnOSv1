# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from build_topo.compiler import (
    overnight_reference,
)


def test_overnight_reference_loads_shelter_and_campsite_points(
    trail_root,
):
    points = (
        overnight_reference
        .load_overnight_points(
            trail_root
        )
    )

    assert len(points) == 66
    assert any(
        point["title"] == "Taylor Lodge"
        for point in points
    )
    assert any(
        point["title"] == "Journey's End Camp"
        for point in points
    )
    assert {
        "shelter",
        "campsite",
    }.issubset({
        point["overnight_class"]
        for point in points
    })


def test_overnight_reference_matches_verbose_overlay_names(
    trail_root,
):
    overlay_nodes = (
        overnight_reference
        .load_overlay_nodes(
            trail_root
        )
    )
    points = (
        overnight_reference
        .load_overnight_points(
            trail_root
        )
    )
    spine_index = (
        overnight_reference
        .build_spine_index(
            trail_root
        )
    )

    matched, unmatched, planner_candidates = (
        overnight_reference
        .build_reference_records(
            points,
            overlay_nodes,
            spine_index,
        )
    )

    goddard = next(
        record for record in matched
        if record["title"] == "Goddard Shelter"
    )
    william_douglas = next(
        record for record in matched
        if record["title"] == "William B. Douglas Shelter"
    )

    assert goddard["trail_mile"] == 24.4
    assert "Goddard Shelter" in goddard[
        "canonical_name"
    ]
    assert william_douglas["trail_mile"] == 48.6
    assert "William B. Douglas Shelter" in (
        william_douglas["canonical_name"]
    )

    unmatched_titles = {
        record["title"]
        for record in unmatched
    }
    planner_titles = {
        record["canonical_name"]
        for record in planner_candidates
    }

    assert "Taylor Lodge" in unmatched_titles
    assert "Taylor Lodge" in planner_titles


def test_overnight_reference_summary_tracks_planner_candidates(
    trail_root,
):
    payload = (
        overnight_reference
        .build_overnight_reference(
            trail_root
        )
    )

    summary = payload[
        "summary"
    ]

    assert summary["total_points"] == 66
    assert summary["matched_points"] > 40
    assert summary["unmatched_points"] > 0
    assert summary["planner_candidates"] > 0
    assert summary["excluded_generic_titles"] > 0

    planner_titles = {
        record["canonical_name"]
        for record in payload[
            "planner_candidates"
        ]
    }

    assert "Taylor Lodge" in planner_titles
    assert "Camp Site" not in planner_titles


def test_overnight_reference_exports_repo_relative_sources(
    tmp_path,
):
    trail_root = (
        tmp_path /
        "trails" /
        "vermont_long_trail"
    )
    raw_geojson = (
        trail_root /
        "raw" /
        "geojson"
    )
    raw_csv = (
        trail_root /
        "raw" /
        "csv"
    )

    raw_geojson.mkdir(
        parents=True
    )
    raw_csv.mkdir(
        parents=True
    )
    (
        trail_root /
        "compiled"
    ).mkdir()

    (
        raw_geojson /
        "shelters.geojson"
    ).write_text("{}")
    (
        raw_geojson /
        "campsites.geojson"
    ).write_text("{}")
    (
        raw_csv /
        "overnight_amenities.csv"
    ).write_text("")

    payload = (
        overnight_reference
        .export_overnight_reference(
            [],
            [],
            [],
            {},
            trail_root,
        )
    )

    assert payload["sources"] == [
        (
            "trails/vermont_long_trail/raw/"
            "geojson/shelters.geojson"
        ),
        (
            "trails/vermont_long_trail/raw/"
            "geojson/campsites.geojson"
        ),
        (
            "trails/vermont_long_trail/raw/"
            "csv/overnight_amenities.csv"
        ),
    ]
    assert all(
        not source.startswith("/")
        for source in payload["sources"]
    )
