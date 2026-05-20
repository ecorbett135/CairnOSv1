# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0

from cairn.runtime.data_quality import (
    error_findings,
    validate_overnight_reference_payload,
    validate_resupply_amenities_rows,
    validate_route_overlay_payload,
    validate_runtime_dataset,
    validate_terrain_payload,
    validate_town_lodging_options_rows,
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
        "access_distance_miles": "2.0",
        "access_distance_qualifier": "exact",
        "access_direction": "east",
        "access_mode": "road_access",
        "resupply_convenience": "moderate_side_trip",
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


def test_resupply_validation_flags_invalid_structured_access_fields():
    row = {
        "trail_mile": "50.0",
        "town_access": "Example Town",
        "canonical_hint": "Example Road",
        "access_distance_miles": "-1",
        "access_distance_qualifier": "nearish",
        "access_direction": "northwest",
        "access_mode": "shuttle",
        "resupply_convenience": "easy",
        "grocery": "TRUE",
        "post_office": "FALSE",
        "outfitter": "FALSE",
        "lodging": "TRUE",
        "restaurants": "TRUE",
        "zero_candidate": "FALSE",
        "latitude": "44.0",
        "longitude": "-72.0",
    }

    findings = validate_resupply_amenities_rows([
        row,
    ])
    codes = finding_codes(
        findings
    )

    assert (
        "invalid_resupply_access_distance"
        in codes
    )
    assert (
        "invalid_access_distance_qualifier"
        in codes
    )
    assert "invalid_access_direction" in codes
    assert "invalid_access_mode" in codes
    assert "invalid_resupply_convenience" in codes


def test_resupply_validation_flags_grouped_town_access_gap():
    row = {
        "trail_mile": "151.3",
        "town_access": "Lincoln / Warren / Bristol",
        "canonical_hint": "Lincoln Gap",
        "access_distance_miles": "4",
        "access_distance_qualifier": "at_least",
        "access_direction": "mixed",
        "access_mode": "road_access",
        "resupply_convenience": "long_side_trip",
        "grocery": "TRUE",
        "post_office": "TRUE",
        "outfitter": "FALSE",
        "lodging": "TRUE",
        "restaurants": "TRUE",
        "zero_candidate": "FALSE",
        "latitude": "44.0",
        "longitude": "-72.0",
        "access_notes": (
            "4+ miles east to Warren and "
            "5 miles west to Lincoln"
        ),
    }

    findings = validate_resupply_amenities_rows([
        row,
    ])
    warnings = finding_codes(
        findings,
        severity="warning",
    )

    assert (
        "resupply_town_access_note_incomplete"
        in warnings
    )


def test_town_lodging_validation_flags_bad_resupply_id():
    resupply_rows = [
        {
            "trail_mile": "151.3",
            "canonical_hint": "Lincoln Gap",
        }
    ]
    lodging_row = {
        "lodging_id": "example_lodging",
        "resupply_amenity_id": "Missing:1.0",
        "town_access": "Example Town",
        "town": "Example Town",
        "display_name": "Example Lodging",
        "lodging_type": "hostel",
        "is_hiker_focused": "TRUE",
        "validation_status": "validated",
        "validation_confidence": "high",
        "source_name": "Example",
        "source_url": "https://example.com",
        "validation_source_name": "Example",
        "validation_source_url": "https://example.com",
        "validation_date": "2026-05-20",
        "lodging_notes": "Example only",
        "food_on_site": "FALSE",
        "laundry": "FALSE",
        "mail_drop_status": "unknown",
        "booking_notes": "Verify directly",
    }

    findings = validate_town_lodging_options_rows(
        [
            lodging_row,
        ],
        resupply_rows,
    )

    assert (
        "lodging_bad_resupply_amenity_id"
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


def test_terrain_validation_reports_mile_reconciliation_metadata():
    findings = validate_terrain_payload(
        {
            "features": [
                {
                    "properties": {
                        "mile": 0.0,
                        "elevation_ft": 1000,
                    },
                },
                {
                    "properties": {
                        "mile": 10.0,
                        "elevation_ft": 1200,
                    },
                },
            ],
        },
        overlay_miles=[
            -1.0,
            0.0,
            20.0,
        ],
    )

    info_codes = finding_codes(
        findings,
        severity="info",
    )
    warning_codes = finding_codes(
        findings,
        severity="warning",
    )
    reconciliation = next(
        finding
        for finding in findings
        if (
            finding.code
            == "terrain_mile_reconciliation"
        )
    )

    assert "terrain_mile_reconciliation" in info_codes
    assert "terrain_mile_domain_differs" in warning_codes
    assert (
        reconciliation.context["guidebook_domain"]
        == "northbound_reference_mainline_miles"
    )
    assert (
        reconciliation.context["terrain_domain"]
        == "compiled_geometry_sample_miles"
    )
