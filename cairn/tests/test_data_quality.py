# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0

from cairn.runtime.data_quality import (
    error_findings,
    validate_overnight_reference_payload,
    validate_resupply_amenities_rows,
    validate_route_overlay_payload,
    validate_runtime_dataset,
)


def finding_codes(
    findings,
    severity="error",
):
    return {
        finding.code
        for finding in findings
        if finding.severity == severity
    }


def test_long_trail_runtime_dataset_has_no_data_quality_errors(
    trail_root,
):
    findings = validate_runtime_dataset(
        trail_root
    )

    assert error_findings(
        findings
    ) == []


def test_route_overlay_validation_flags_duplicate_ids_and_bad_segments():
    findings = validate_route_overlay_payload({
        "overlay_nodes": [
            {
                "overlay_id": "overlay_0001",
                "canonical_name": "Start",
                "trail_mile": 0.0,
                "node_class": "trailhead",
            },
            {
                "overlay_id": "overlay_0001",
                "canonical_name": "Duplicate Start",
                "trail_mile": 1.0,
                "node_class": "trailhead",
            },
        ],
        "operational_segments": [
            {
                "start_node": "overlay_0001",
                "end_node": "missing_overlay",
                "distance": 1.0,
            }
        ],
    })

    codes = finding_codes(
        findings
    )

    assert "duplicate_overlay_id" in codes
    assert "bad_operational_segment_end" in codes


def test_resupply_validation_flags_rows_without_nearby_logistics_node():
    row = {
        "trail_mile": "50.0",
        "town_access": "Example Town",
        "canonical_hint": "Example Road",
        "grocery": "TRUE",
        "post_office": "FALSE",
        "outfitter": "FALSE",
        "lodging": "TRUE",
        "restaurants": "TRUE",
        "zero_candidate": "FALSE",
        "latitude": "44.0",
        "longitude": "-72.0",
    }
    overlay_nodes = [
        {
            "overlay_id": "overlay_0001",
            "canonical_name": "Distant Road",
            "trail_mile": 0.0,
            "node_class": "logistics",
            "logistics": True,
        }
    ]

    findings = validate_resupply_amenities_rows(
        [
            row,
        ],
        overlay_nodes,
    )

    assert (
        "resupply_without_nearby_logistics_node"
        in finding_codes(
            findings
        )
    )


def test_overnight_reference_validation_flags_summary_count_mismatch():
    findings = validate_overnight_reference_payload(
        {
            "summary": {
                "matched_points": 2,
                "unmatched_points": 0,
                "planner_candidates": 0,
            },
            "matched_overnight_sites": [
                {
                    "title": "Example Shelter",
                    "node_class": "shelter",
                    "overlay_id": "overlay_0001",
                }
            ],
            "unmatched_overnight_sites": [],
            "planner_candidates": [],
        },
        overlay_ids={
            "overlay_0001",
        },
    )

    assert (
        "overnight_summary_count_mismatch"
        in finding_codes(
            findings
        )
    )


def test_resupply_validation_flags_missing_required_columns():
    findings = validate_resupply_amenities_rows([
        {
            "trail_mile": "1.0",
        }
    ])

    assert (
        "missing_required_columns"
        in finding_codes(
            findings
        )
    )
