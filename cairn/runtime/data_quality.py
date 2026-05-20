# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""Runtime dataset quality checks for CairnOS trail data."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from dataclasses import field
import json
from pathlib import Path
import sys
from typing import Any


REQUIRED_RUNTIME_FILES = [
    "raw/csv/route_master.csv",
    "raw/csv/approach_trails.csv",
    "raw/csv/resupply_amenities.csv",
    "raw/csv/town_lodging_options.csv",
    "compiled/route_overlay.json",
    "compiled/terrain.geojson",
    "compiled/spine.geojson",
    "compiled/overnight_reference.json",
    "compiled/approach_trails.json",
    "compiled/operational_graph.json",
]

ROUTE_MASTER_COLUMNS = {
    "division",
    "miles_from_MA_border_nb",
    "location",
    "elevation_ft",
}

RESUPPLY_COLUMNS = {
    "trail_mile",
    "town_access",
    "canonical_hint",
    "access_distance_miles",
    "access_distance_qualifier",
    "access_direction",
    "access_mode",
    "resupply_convenience",
    "grocery",
    "post_office",
    "outfitter",
    "lodging",
    "restaurants",
    "zero_candidate",
    "latitude",
    "longitude",
}

TOWN_LODGING_COLUMNS = {
    "lodging_id",
    "resupply_amenity_id",
    "town_access",
    "town",
    "display_name",
    "lodging_type",
    "is_hiker_focused",
    "validation_status",
    "validation_confidence",
    "source_name",
    "source_url",
    "validation_source_name",
    "validation_source_url",
    "validation_date",
    "lodging_notes",
    "food_on_site",
    "laundry",
    "mail_drop_status",
    "booking_notes",
}

TOWN_LODGING_STATUSES = {
    "validated",
    "current",
}

ACCESS_DISTANCE_QUALIFIERS = {
    "exact",
    "less_than",
    "about",
    "at_least",
    "unknown",
}

ACCESS_DIRECTIONS = {
    "east",
    "west",
    "mixed",
    "pre_trail",
    "post_trail",
    "unknown",
}

ACCESS_MODES = {
    "road_access",
    "approach_access",
    "terminus_access",
    "unknown",
}

RESUPPLY_CONVENIENCE_VALUES = {
    "on_trail",
    "near_trail",
    "moderate_side_trip",
    "long_side_trip",
    "approach",
    "terminus",
    "unknown",
}

APPROACH_COLUMNS = {
    "approach_id",
    "approach_name",
    "direction",
    "terminus",
    "sequence",
    "location",
    "cumulative_to_trail_mi",
}

VALID_SEVERITIES = {
    "error",
    "warning",
    "info",
}


@dataclass(frozen=True)
class DataQualityFinding:
    """A single runtime data-quality finding."""

    severity: str
    code: str
    message: str
    path: str = ""
    context: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "path": self.path,
            "context": self.context,
        }


def add_finding(
    findings: list[DataQualityFinding],
    severity: str,
    code: str,
    message: str,
    path: str = "",
    **context: Any,
) -> None:
    if severity not in VALID_SEVERITIES:
        raise ValueError(
            f"Invalid severity: {severity}"
        )

    findings.append(
        DataQualityFinding(
            severity=severity,
            code=code,
            message=message,
            path=path,
            context={
                key: value
                for key, value in context.items()
                if value is not None
            },
        )
    )


def error_findings(
    findings: list[DataQualityFinding],
) -> list[DataQualityFinding]:
    return [
        finding
        for finding in findings
        if finding.severity == "error"
    ]


def to_float(
    value: Any,
) -> float | None:
    if value is None:
        return None

    try:
        text = str(value).strip()
        if not text:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def is_truthy_text(
    value: Any,
) -> bool | None:
    text = str(value).strip().lower()

    if text in {
        "true",
        "yes",
        "1",
    }:
        return True

    if text in {
        "false",
        "no",
        "0",
    }:
        return False

    return None


def split_town_access_names(
    value: Any,
) -> list[str]:
    return [
        town.strip()
        for town in str(
            value or ""
        ).split("/")
        if town.strip()
    ]


def read_json_file(
    path: Path,
    findings: list[DataQualityFinding],
) -> Any | None:
    if not path.exists():
        add_finding(
            findings,
            "error",
            "missing_file",
            "Required runtime file is missing.",
            str(path),
        )
        return None

    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        add_finding(
            findings,
            "error",
            "invalid_json",
            "JSON file could not be parsed.",
            str(path),
            error=str(exc),
        )
        return None


def read_csv_file(
    path: Path,
    findings: list[DataQualityFinding],
) -> list[dict[str, str]] | None:
    if not path.exists():
        add_finding(
            findings,
            "error",
            "missing_file",
            "Required runtime file is missing.",
            str(path),
        )
        return None

    try:
        with open(
            path,
            newline="",
            encoding="utf-8-sig",
        ) as handle:
            return list(
                csv.DictReader(handle)
            )
    except csv.Error as exc:
        add_finding(
            findings,
            "error",
            "invalid_csv",
            "CSV file could not be parsed.",
            str(path),
            error=str(exc),
        )
        return None


def validate_required_columns(
    rows: list[dict[str, str]],
    required_columns: set[str],
    path: str,
) -> list[DataQualityFinding]:
    findings: list[DataQualityFinding] = []

    columns = set(
        rows[0].keys()
        if rows
        else []
    )

    missing = sorted(
        required_columns - columns
    )

    if missing:
        add_finding(
            findings,
            "error",
            "missing_required_columns",
            "CSV is missing required columns.",
            path,
            missing_columns=missing,
        )

    return findings


def validate_route_overlay_payload(
    payload: dict[str, Any],
    path: str = "compiled/route_overlay.json",
) -> list[DataQualityFinding]:
    findings: list[DataQualityFinding] = []
    _validate_route_overlay_payload(
        payload,
        path,
        findings,
    )
    return findings


def _validate_route_overlay_payload(
    payload: dict[str, Any],
    path: str,
    findings: list[DataQualityFinding],
) -> dict[str, dict[str, Any]]:
    overlay_nodes = payload.get(
        "overlay_nodes",
        [],
    )
    operational_segments = payload.get(
        "operational_segments",
        [],
    )

    if not isinstance(
        overlay_nodes,
        list,
    ):
        add_finding(
            findings,
            "error",
            "invalid_overlay_nodes",
            "route_overlay overlay_nodes must be a list.",
            path,
        )
        overlay_nodes = []

    if not isinstance(
        operational_segments,
        list,
    ):
        add_finding(
            findings,
            "error",
            "invalid_operational_segments",
            "route_overlay operational_segments must be a list.",
            path,
        )
        operational_segments = []

    add_finding(
        findings,
        "info",
        "route_overlay_summary",
        "Route overlay loaded.",
        path,
        overlay_nodes=len(overlay_nodes),
        operational_segments=len(operational_segments),
    )

    nodes_by_id: dict[str, dict[str, Any]] = {}
    duplicate_ids: set[str] = set()
    previous_mile: float | None = None
    seen_name_miles: set[tuple[str, float]] = set()

    for idx, node in enumerate(overlay_nodes):
        overlay_id = str(
            node.get(
                "overlay_id",
                "",
            )
        ).strip()
        canonical_name = str(
            node.get(
                "canonical_name",
                "",
            )
        ).strip()
        mile = to_float(
            node.get(
                "trail_mile"
            )
        )

        if not overlay_id:
            add_finding(
                findings,
                "error",
                "missing_overlay_id",
                "Overlay node is missing overlay_id.",
                path,
                index=idx,
            )
        elif overlay_id in nodes_by_id:
            duplicate_ids.add(
                overlay_id
            )
        else:
            nodes_by_id[overlay_id] = node

        if not canonical_name:
            add_finding(
                findings,
                "error",
                "missing_canonical_name",
                "Overlay node is missing canonical_name.",
                path,
                overlay_id=overlay_id,
                index=idx,
            )

        if mile is None:
            add_finding(
                findings,
                "error",
                "invalid_overlay_mile",
                "Overlay node trail_mile is not numeric.",
                path,
                overlay_id=overlay_id,
                value=node.get(
                    "trail_mile"
                ),
            )
            continue

        if (
            previous_mile is not None
            and mile < previous_mile
        ):
            add_finding(
                findings,
                "error",
                "overlay_miles_not_monotonic",
                "Overlay trail miles must be nondecreasing.",
                path,
                overlay_id=overlay_id,
                previous_mile=previous_mile,
                current_mile=mile,
            )

        previous_mile = mile

        name_key = (
            canonical_name.lower(),
            round(
                mile,
                1,
            ),
        )
        if canonical_name and name_key in seen_name_miles:
            add_finding(
                findings,
                "warning",
                "duplicate_overlay_name_mile",
                "Overlay has duplicate name and rounded mile.",
                path,
                canonical_name=canonical_name,
                trail_mile=mile,
            )
        seen_name_miles.add(
            name_key
        )

        if not str(
            node.get(
                "node_class",
                "",
            )
        ).strip():
            add_finding(
                findings,
                "warning",
                "missing_node_class",
                "Overlay node has no node_class.",
                path,
                overlay_id=overlay_id,
            )

    for overlay_id in sorted(duplicate_ids):
        add_finding(
            findings,
            "error",
            "duplicate_overlay_id",
            "Overlay IDs must be unique.",
            path,
            overlay_id=overlay_id,
        )

    for idx, segment in enumerate(operational_segments):
        start_id = segment.get(
            "start_node"
        )
        end_id = segment.get(
            "end_node"
        )

        if start_id not in nodes_by_id:
            add_finding(
                findings,
                "error",
                "bad_operational_segment_start",
                "Operational segment start_node is unknown.",
                path,
                index=idx,
                start_node=start_id,
            )

        if end_id not in nodes_by_id:
            add_finding(
                findings,
                "error",
                "bad_operational_segment_end",
                "Operational segment end_node is unknown.",
                path,
                index=idx,
                end_node=end_id,
            )

        distance = to_float(
            segment.get(
                "distance"
            )
        )
        if (
            distance is None
            or distance < 0
        ):
            add_finding(
                findings,
                "error",
                "invalid_operational_segment_distance",
                "Operational segment distance must be numeric and nonnegative.",
                path,
                index=idx,
                distance=segment.get(
                    "distance"
                ),
            )

    return nodes_by_id


def validate_route_master_rows(
    rows: list[dict[str, str]],
    path: str = "raw/csv/route_master.csv",
) -> list[DataQualityFinding]:
    findings = validate_required_columns(
        rows,
        ROUTE_MASTER_COLUMNS,
        path,
    )

    if findings:
        return findings

    add_finding(
        findings,
        "info",
        "route_master_summary",
        "Route master loaded.",
        path,
        rows=len(rows),
    )

    previous_mile: float | None = None
    seen_locations: set[tuple[str, float]] = set()

    for idx, row in enumerate(rows):
        mile = to_float(
            row.get(
                "miles_from_MA_border_nb"
            )
        )
        elevation = to_float(
            row.get(
                "elevation_ft"
            )
        )
        location = str(
            row.get(
                "location",
                "",
            )
        ).strip()

        if mile is None:
            add_finding(
                findings,
                "error",
                "invalid_route_master_mile",
                "Route master mile is not numeric.",
                path,
                row=idx + 2,
                value=row.get(
                    "miles_from_MA_border_nb"
                ),
            )
            continue

        if elevation is None:
            add_finding(
                findings,
                "error",
                "invalid_route_master_elevation",
                "Route master elevation_ft is not numeric.",
                path,
                row=idx + 2,
                value=row.get(
                    "elevation_ft"
                ),
            )

        if not location:
            add_finding(
                findings,
                "error",
                "missing_route_master_location",
                "Route master location is blank.",
                path,
                row=idx + 2,
            )

        if (
            previous_mile is not None
            and mile < previous_mile
        ):
            add_finding(
                findings,
                "error",
                "route_master_miles_not_monotonic",
                "Route master miles must be nondecreasing.",
                path,
                row=idx + 2,
                previous_mile=previous_mile,
                current_mile=mile,
            )

        previous_mile = mile

        key = (
            location.lower(),
            round(
                mile,
                1,
            ),
        )
        if location and key in seen_locations:
            add_finding(
                findings,
                "warning",
                "duplicate_route_master_location_mile",
                "Route master has duplicate location and rounded mile.",
                path,
                row=idx + 2,
                location=location,
                trail_mile=mile,
            )
        seen_locations.add(
            key
        )

    return findings


def validate_resupply_amenities_rows(
    rows: list[dict[str, str]],
    overlay_nodes: list[dict[str, Any]] | None = None,
    path: str = "raw/csv/resupply_amenities.csv",
) -> list[DataQualityFinding]:
    findings = validate_required_columns(
        rows,
        RESUPPLY_COLUMNS,
        path,
    )

    if findings:
        return findings

    add_finding(
        findings,
        "info",
        "resupply_amenities_summary",
        "Resupply amenities loaded.",
        path,
        rows=len(rows),
    )

    for idx, row in enumerate(rows):
        mile = to_float(
            row.get(
                "trail_mile"
            )
        )

        if mile is None:
            add_finding(
                findings,
                "error",
                "invalid_resupply_mile",
                "Resupply trail_mile is not numeric.",
                path,
                row=idx + 2,
                value=row.get(
                    "trail_mile"
                ),
            )
            continue

        for field_name in [
            "grocery",
            "post_office",
            "outfitter",
            "lodging",
            "restaurants",
            "zero_candidate",
        ]:
            if is_truthy_text(
                row.get(
                    field_name
                )
            ) is None:
                add_finding(
                    findings,
                    "error",
                    "invalid_boolean",
                    "Resupply boolean field must use TRUE/FALSE style values.",
                    path,
                    row=idx + 2,
                    field=field_name,
                    value=row.get(
                        field_name
                    ),
                )

        if not str(
            row.get(
                "town_access",
                "",
            )
        ).strip():
            add_finding(
                findings,
                "error",
                "missing_resupply_town_access",
                "Resupply town_access is blank.",
                path,
                row=idx + 2,
                trail_mile=mile,
            )

        access_notes = str(
            row.get(
                "access_notes",
                "",
            )
            or ""
        )
        town_names = split_town_access_names(
            row.get(
                "town_access",
                "",
            )
        )
        missing_towns = [
            town
            for town in town_names
            if town.lower()
            not in access_notes.lower()
        ]

        if (
            len(town_names) > 1
            and missing_towns
        ):
            add_finding(
                findings,
                "warning",
                "resupply_town_access_note_incomplete",
                "Grouped town_access includes towns not represented in access_notes.",
                path,
                row=idx + 2,
                trail_mile=mile,
                town_access=row.get(
                    "town_access"
                ),
                missing_towns=missing_towns,
            )

        if not str(
            row.get(
                "canonical_hint",
                "",
            )
        ).strip():
            add_finding(
                findings,
                "error",
                "missing_resupply_canonical_hint",
                "Resupply canonical_hint is blank.",
                path,
                row=idx + 2,
                trail_mile=mile,
            )

        access_distance = to_float(
            row.get(
                "access_distance_miles"
            )
        )
        if access_distance is None:
            add_finding(
                findings,
                "warning",
                "missing_resupply_access_distance",
                "Resupply row has no structured access distance.",
                path,
                row=idx + 2,
                trail_mile=mile,
            )
        elif access_distance < 0:
            add_finding(
                findings,
                "error",
                "invalid_resupply_access_distance",
                "Resupply access_distance_miles must be nonnegative.",
                path,
                row=idx + 2,
                trail_mile=mile,
                access_distance_miles=access_distance,
            )

        enum_checks = [
            (
                "access_distance_qualifier",
                ACCESS_DISTANCE_QUALIFIERS,
                "invalid_access_distance_qualifier",
            ),
            (
                "access_direction",
                ACCESS_DIRECTIONS,
                "invalid_access_direction",
            ),
            (
                "access_mode",
                ACCESS_MODES,
                "invalid_access_mode",
            ),
            (
                "resupply_convenience",
                RESUPPLY_CONVENIENCE_VALUES,
                "invalid_resupply_convenience",
            ),
        ]

        for field_name, allowed_values, code in enum_checks:
            value = str(
                row.get(
                    field_name,
                    "",
                )
                or ""
            ).strip()

            if value not in allowed_values:
                add_finding(
                    findings,
                    "error",
                    code,
                    "Resupply structured access field has an invalid value.",
                    path,
                    row=idx + 2,
                    field=field_name,
                    value=value,
                    allowed=sorted(
                        allowed_values
                    ),
                )

        latitude = to_float(
            row.get(
                "latitude"
            )
        )
        longitude = to_float(
            row.get(
                "longitude"
            )
        )
        if (
            latitude is None
            or longitude is None
        ):
            add_finding(
                findings,
                "warning",
                "missing_resupply_coordinates",
                "Resupply row has no usable latitude/longitude.",
                path,
                row=idx + 2,
                trail_mile=mile,
            )
        elif not (
            -90 <= latitude <= 90
            and -180 <= longitude <= 180
        ):
            add_finding(
                findings,
                "error",
                "invalid_resupply_coordinates",
                "Resupply latitude/longitude are outside plausible bounds.",
                path,
                row=idx + 2,
                latitude=latitude,
                longitude=longitude,
            )

        if overlay_nodes is not None:
            nearest = nearest_overlay_node(
                mile,
                overlay_nodes,
                logistics_only=True,
            )
            if (
                nearest is None
                or nearest[0] > 1.0
            ):
                add_finding(
                    findings,
                    "error",
                    "resupply_without_nearby_logistics_node",
                    "Resupply row has no nearby logistics/resupply overlay node.",
                    path,
                    row=idx + 2,
                    trail_mile=mile,
                    canonical_hint=row.get(
                        "canonical_hint"
                    ),
                )

    return findings


def resupply_amenity_ids(
    rows: list[dict[str, str]],
) -> set[str]:
    ids = set()

    for row in rows:
        canonical_hint = str(
            row.get(
                "canonical_hint",
                "",
            )
        ).strip()
        trail_mile = str(
            row.get(
                "trail_mile",
                "",
            )
        ).strip()

        if canonical_hint and trail_mile:
            ids.add(
                f"{canonical_hint}:{trail_mile}"
            )

    return ids


def validate_town_lodging_options_rows(
    rows: list[dict[str, str]],
    resupply_rows: list[dict[str, str]],
    path: str = "raw/csv/town_lodging_options.csv",
) -> list[DataQualityFinding]:
    findings = validate_required_columns(
        rows,
        TOWN_LODGING_COLUMNS,
        path,
    )

    if findings:
        return findings

    valid_resupply_ids = resupply_amenity_ids(
        resupply_rows
    )
    seen_lodging_ids: set[str] = set()

    add_finding(
        findings,
        "info",
        "town_lodging_options_summary",
        "Town lodging options loaded.",
        path,
        rows=len(rows),
    )

    for idx, row in enumerate(rows):
        row_number = idx + 2
        lodging_id = str(
            row.get(
                "lodging_id",
                "",
            )
        ).strip()
        resupply_id = str(
            row.get(
                "resupply_amenity_id",
                "",
            )
        ).strip()
        display_name = str(
            row.get(
                "display_name",
                "",
            )
        ).strip()
        status = str(
            row.get(
                "validation_status",
                "",
            )
        ).strip().casefold()

        if not lodging_id:
            add_finding(
                findings,
                "error",
                "missing_lodging_id",
                "Town lodging row is missing lodging_id.",
                path,
                row=row_number,
            )
        elif lodging_id in seen_lodging_ids:
            add_finding(
                findings,
                "error",
                "duplicate_lodging_id",
                "Town lodging row has a duplicate lodging_id.",
                path,
                row=row_number,
                lodging_id=lodging_id,
            )
        seen_lodging_ids.add(
            lodging_id
        )

        if not resupply_id:
            add_finding(
                findings,
                "error",
                "missing_lodging_resupply_amenity_id",
                "Town lodging row is missing resupply_amenity_id.",
                path,
                row=row_number,
                lodging_id=lodging_id,
            )
        elif resupply_id not in valid_resupply_ids:
            add_finding(
                findings,
                "error",
                "lodging_bad_resupply_amenity_id",
                "Town lodging row references an unknown resupply amenity.",
                path,
                row=row_number,
                lodging_id=lodging_id,
                resupply_amenity_id=resupply_id,
            )

        if not display_name:
            add_finding(
                findings,
                "error",
                "missing_lodging_display_name",
                "Town lodging row is missing display_name.",
                path,
                row=row_number,
                lodging_id=lodging_id,
            )

        if status not in TOWN_LODGING_STATUSES:
            add_finding(
                findings,
                "error",
                "invalid_lodging_validation_status",
                "Town lodging row has an invalid validation_status.",
                path,
                row=row_number,
                lodging_id=lodging_id,
                validation_status=row.get(
                    "validation_status"
                ),
                allowed=sorted(
                    TOWN_LODGING_STATUSES
                ),
            )

        for field_name in [
            "is_hiker_focused",
            "food_on_site",
            "laundry",
        ]:
            if is_truthy_text(
                row.get(
                    field_name
                )
            ) is None:
                add_finding(
                    findings,
                    "error",
                    "invalid_lodging_boolean",
                    "Town lodging boolean field must use TRUE/FALSE style values.",
                    path,
                    row=row_number,
                    lodging_id=lodging_id,
                    field=field_name,
                    value=row.get(
                        field_name
                    ),
                )

        if not str(
            row.get(
                "validation_source_url",
                "",
            )
        ).strip():
            add_finding(
                findings,
                "warning",
                "missing_lodging_validation_source_url",
                "Town lodging row should include a current validation source URL.",
                path,
                row=row_number,
                lodging_id=lodging_id,
            )

        if not str(
            row.get(
                "validation_date",
                "",
            )
        ).strip():
            add_finding(
                findings,
                "warning",
                "missing_lodging_validation_date",
                "Town lodging row should include a validation date.",
                path,
                row=row_number,
                lodging_id=lodging_id,
            )

    return findings


def validate_overnight_reference_payload(
    payload: dict[str, Any],
    overlay_ids: set[str] | None = None,
    path: str = "compiled/overnight_reference.json",
) -> list[DataQualityFinding]:
    findings: list[DataQualityFinding] = []

    matched = payload.get(
        "matched_overnight_sites",
        [],
    )
    unmatched = payload.get(
        "unmatched_overnight_sites",
        [],
    )
    planner_candidates = payload.get(
        "planner_candidates",
        [],
    )
    summary = payload.get(
        "summary",
        {},
    )

    for label, value in [
        (
            "matched_overnight_sites",
            matched,
        ),
        (
            "unmatched_overnight_sites",
            unmatched,
        ),
        (
            "planner_candidates",
            planner_candidates,
        ),
    ]:
        if not isinstance(
            value,
            list,
        ):
            add_finding(
                findings,
                "error",
                "invalid_overnight_collection",
                "Overnight reference collection must be a list.",
                path,
                collection=label,
            )

    matched = matched if isinstance(
        matched,
        list,
    ) else []
    unmatched = unmatched if isinstance(
        unmatched,
        list,
    ) else []
    planner_candidates = planner_candidates if isinstance(
        planner_candidates,
        list,
    ) else []

    if not isinstance(
        summary,
        dict,
    ):
        add_finding(
            findings,
            "error",
            "invalid_overnight_summary",
            "Overnight reference summary must be an object.",
            path,
        )
        summary = {}

    add_finding(
        findings,
        "info",
        "overnight_reference_summary",
        "Overnight reference loaded.",
        path,
        matched=len(matched),
        unmatched=len(unmatched),
        planner_candidates=len(planner_candidates),
    )

    expected_counts = {
        "matched_points": len(matched),
        "unmatched_points": len(unmatched),
        "planner_candidates": len(planner_candidates),
    }

    for key, expected in expected_counts.items():
        actual = summary.get(
            key
        )
        if actual != expected:
            add_finding(
                findings,
                "error",
                "overnight_summary_count_mismatch",
                "Overnight reference summary count does not match records.",
                path,
                field=key,
                expected=expected,
                actual=actual,
            )

    valid_classes = {
        "shelter",
        "camp",
        "campsite",
        "lodge",
    }

    for item in matched:
        overlay_id = item.get(
            "overlay_id"
        )
        if (
            overlay_ids is not None
            and overlay_id not in overlay_ids
        ):
            add_finding(
                findings,
                "error",
                "overnight_bad_overlay_id",
                "Matched overnight site references an unknown overlay_id.",
                path,
                overlay_id=overlay_id,
                title=item.get(
                    "title"
                ),
            )

    for item in [
        *matched,
        *unmatched,
        *planner_candidates,
    ]:
        node_class = str(
            item.get(
                "node_class",
                item.get(
                    "overnight_class",
                    "",
                ),
            )
        ).strip()

        if (
            node_class
            and node_class not in valid_classes
        ):
            add_finding(
                findings,
                "warning",
                "unexpected_overnight_class",
                "Overnight reference has an unexpected shelter/camp class.",
                path,
                title=item.get(
                    "title",
                    item.get(
                        "canonical_name"
                    ),
                ),
                node_class=node_class,
            )

    for item in planner_candidates:
        distance = to_float(
            item.get(
                "distance_to_spine_miles"
            )
        )
        if (
            distance is None
            or distance > 1.0
        ):
            add_finding(
                findings,
                "error",
                "planner_candidate_far_from_spine",
                "Planner overnight candidate is too far from the spine.",
                path,
                name=item.get(
                    "canonical_name"
                ),
                distance_to_spine_miles=distance,
            )

    return findings


def validate_approach_rows(
    raw_rows: list[dict[str, str]],
    compiled_payload: dict[str, Any] | None = None,
    raw_path: str = "raw/csv/approach_trails.csv",
    compiled_path: str = "compiled/approach_trails.json",
) -> list[DataQualityFinding]:
    findings = validate_required_columns(
        raw_rows,
        APPROACH_COLUMNS,
        raw_path,
    )

    if findings:
        return findings

    add_finding(
        findings,
        "info",
        "approach_trails_summary",
        "Approach trails loaded.",
        raw_path,
        rows=len(raw_rows),
    )

    by_approach: dict[str, list[dict[str, str]]] = {}
    for row in raw_rows:
        by_approach.setdefault(
            row.get(
                "approach_id",
                "",
            ),
            [],
        ).append(
            row
        )

    for approach_id, rows in by_approach.items():
        previous_sequence: float | None = None
        for row in rows:
            sequence = to_float(
                row.get(
                    "sequence"
                )
            )
            if sequence is None:
                add_finding(
                    findings,
                    "error",
                    "invalid_approach_sequence",
                    "Approach sequence is not numeric.",
                    raw_path,
                    approach_id=approach_id,
                    value=row.get(
                        "sequence"
                    ),
                )
                continue

            if (
                previous_sequence is not None
                and sequence < previous_sequence
            ):
                add_finding(
                    findings,
                    "error",
                    "approach_sequence_not_monotonic",
                    "Approach sequence should be nondecreasing per approach.",
                    raw_path,
                    approach_id=approach_id,
                    previous_sequence=previous_sequence,
                    current_sequence=sequence,
                )

            previous_sequence = sequence

            direction = row.get(
                "direction"
            )
            terminus = row.get(
                "terminus"
            )
            if direction not in {
                "NOBO",
                "SOBO",
            }:
                add_finding(
                    findings,
                    "error",
                    "invalid_approach_direction",
                    "Approach direction must be NOBO or SOBO.",
                    raw_path,
                    approach_id=approach_id,
                    direction=direction,
                )

            if terminus not in {
                "southern",
                "northern",
            }:
                add_finding(
                    findings,
                    "error",
                    "invalid_approach_terminus",
                    "Approach terminus must be southern or northern.",
                    raw_path,
                    approach_id=approach_id,
                    terminus=terminus,
                )

    if compiled_payload is None:
        return findings

    compiled_rows = compiled_payload.get(
        "approach_trails",
        [],
    )
    if not isinstance(
        compiled_rows,
        list,
    ):
        add_finding(
            findings,
            "error",
            "invalid_compiled_approach_trails",
            "Compiled approach_trails must be a list.",
            compiled_path,
        )
        return findings

    raw_ids = {
        row.get(
            "approach_id"
        )
        for row in raw_rows
    }
    compiled_ids = {
        row.get(
            "approach_id"
        )
        for row in compiled_rows
    }

    missing_compiled = sorted(
        item
        for item in raw_ids - compiled_ids
        if item
    )
    if missing_compiled:
        add_finding(
            findings,
            "error",
            "compiled_approach_missing_raw_ids",
            "Compiled approach trails are missing raw approach IDs.",
            compiled_path,
            missing_approach_ids=missing_compiled,
        )

    blank_terminus_rows = []

    for row in compiled_rows:
        if not str(
            row.get(
                "connected_terminus",
                "",
            )
        ).strip():
            blank_terminus_rows.append(
                {
                    "approach_id": row.get(
                        "approach_id"
                    ),
                    "sequence": row.get(
                        "sequence"
                    ),
                }
            )

    if blank_terminus_rows:
        add_finding(
            findings,
            "warning",
            "compiled_approach_missing_terminus",
            "Compiled approach rows have blank connected_terminus values.",
            compiled_path,
            count=len(
                blank_terminus_rows
            ),
            examples=blank_terminus_rows[:5],
        )

    return findings


def validate_spine_payload(
    payload: dict[str, Any],
    path: str = "compiled/spine.geojson",
) -> list[DataQualityFinding]:
    findings: list[DataQualityFinding] = []
    features = payload.get(
        "features",
        [],
    )

    if not features:
        add_finding(
            findings,
            "error",
            "spine_missing_features",
            "Spine GeoJSON has no features.",
            path,
        )
        return findings

    line_features = [
        feature
        for feature in features
        if feature.get(
            "geometry",
            {},
        ).get(
            "type"
        ) == "LineString"
    ]

    if not line_features:
        add_finding(
            findings,
            "error",
            "spine_missing_linestring",
            "Spine GeoJSON has no LineString feature.",
            path,
        )
        return findings

    coordinates = line_features[0].get(
        "geometry",
        {},
    ).get(
        "coordinates",
        [],
    )
    if len(coordinates) < 2:
        add_finding(
            findings,
            "error",
            "spine_too_few_coordinates",
            "Spine LineString must have at least two coordinates.",
            path,
        )
    else:
        add_finding(
            findings,
            "info",
            "spine_summary",
            "Spine geometry loaded.",
            path,
            coordinates=len(coordinates),
        )

    return findings


def validate_terrain_payload(
    payload: dict[str, Any],
    overlay_miles: list[float] | None = None,
    path: str = "compiled/terrain.geojson",
) -> list[DataQualityFinding]:
    findings: list[DataQualityFinding] = []
    features = payload.get(
        "features",
        [],
    )

    if not isinstance(
        features,
        list,
    ):
        add_finding(
            findings,
            "error",
            "terrain_features_not_list",
            "Terrain GeoJSON features must be a list.",
            path,
        )
        return findings

    previous_mile: float | None = None
    miles: list[float] = []

    for idx, feature in enumerate(features):
        properties = feature.get(
            "properties",
            {},
        )
        mile = to_float(
            properties.get(
                "mile"
            )
        )
        elevation = to_float(
            properties.get(
                "elevation_ft"
            )
        )

        if mile is None:
            add_finding(
                findings,
                "error",
                "invalid_terrain_mile",
                "Terrain feature mile is not numeric.",
                path,
                index=idx,
            )
            continue

        if elevation is None:
            add_finding(
                findings,
                "error",
                "invalid_terrain_elevation",
                "Terrain feature elevation_ft is not numeric.",
                path,
                index=idx,
            )

        if (
            previous_mile is not None
            and mile < previous_mile
        ):
            add_finding(
                findings,
                "error",
                "terrain_miles_not_monotonic",
                "Terrain sample miles must be nondecreasing.",
                path,
                previous_mile=previous_mile,
                current_mile=mile,
            )

        previous_mile = mile
        miles.append(
            mile
        )

    if miles:
        add_finding(
            findings,
            "info",
            "terrain_summary",
            "Terrain samples loaded.",
            path,
            samples=len(miles),
            min_mile=min(miles),
            max_mile=max(miles),
        )

    if (
        overlay_miles
        and miles
    ):
        terrain_min = min(
            miles
        )
        terrain_max = max(
            miles
        )
        terrain_span = (
            terrain_max - terrain_min
        )
        mainline_overlay_miles = [
            mile
            for mile in overlay_miles
            if mile >= 0
        ]
        guidebook_min = (
            min(
                mainline_overlay_miles
            )
            if mainline_overlay_miles
            else min(
                overlay_miles
            )
        )
        guidebook_max = (
            max(
                mainline_overlay_miles
            )
            if mainline_overlay_miles
            else max(
                overlay_miles
            )
        )
        guidebook_span = (
            guidebook_max - guidebook_min
        )

        add_finding(
            findings,
            "info",
            "terrain_mile_reconciliation",
            (
                "Terrain samples use compiled geometry/sample "
                "miles; planner maps guidebook mainline miles "
                "into this terrain domain at runtime."
            ),
            path,
            guidebook_domain=(
                "northbound_reference_mainline_miles"
            ),
            terrain_domain=(
                "compiled_geometry_sample_miles"
            ),
            overlay_min=round(
                min(
                    overlay_miles
                ),
                1,
            ),
            overlay_max=round(
                max(
                    overlay_miles
                ),
                1,
            ),
            guidebook_mainline_min=round(
                guidebook_min,
                1,
            ),
            guidebook_mainline_max=round(
                guidebook_max,
                1,
            ),
            terrain_min=round(
                terrain_min,
                1,
            ),
            terrain_max=round(
                terrain_max,
                1,
            ),
            guidebook_span=round(
                guidebook_span,
                1,
            ),
            terrain_span=round(
                terrain_span,
                1,
            ),
        )

        overlay_span = max(
            overlay_miles
        ) - min(
            overlay_miles
        )
        if abs(
            overlay_span - terrain_span
        ) > 5.0:
            add_finding(
                findings,
                "warning",
                "terrain_mile_domain_differs",
                (
                    "Terrain sample miles and guidebook overlay "
                    "miles use different domains; PlannerV2 must "
                    "reconcile them explicitly at runtime."
                ),
                path,
                overlay_span=round(
                    overlay_span,
                    1,
                ),
                terrain_span=round(
                    terrain_span,
                    1,
                ),
            )

    return findings


def validate_operational_graph_payload(
    payload: dict[str, Any],
    overlay_ids: set[str],
    approach_ids: set[str],
    path: str = "compiled/operational_graph.json",
) -> list[DataQualityFinding]:
    findings: list[DataQualityFinding] = []
    nodes = payload.get(
        "nodes",
        [],
    )
    edges = payload.get(
        "edges",
        [],
    )

    if not isinstance(
        nodes,
        list,
    ) or not isinstance(
        edges,
        list,
    ):
        add_finding(
            findings,
            "error",
            "invalid_operational_graph",
            "Operational graph nodes and edges must be lists.",
            path,
        )
        return findings

    add_finding(
        findings,
        "info",
        "operational_graph_summary",
        "Operational graph loaded.",
        path,
        nodes=len(nodes),
        edges=len(edges),
    )

    segment_ids = {
        node.get(
            "segment_id"
        )
        for node in nodes
        if node.get(
            "segment_id"
        )
    }

    approach_edges_missing_locations = []

    for edge in edges:
        edge_type = edge.get(
            "edge_type"
        )
        if edge_type == "operational_progression":
            for field_name in [
                "from_overlay",
                "to_overlay",
            ]:
                if edge.get(
                    field_name
                ) not in overlay_ids:
                    add_finding(
                        findings,
                        "error",
                        "graph_bad_overlay_edge",
                        "Operational graph edge references an unknown overlay ID.",
                        path,
                        edge_id=edge.get(
                            "edge_id"
                        ),
                        field=field_name,
                        value=edge.get(
                            field_name
                        ),
                    )

        elif edge_type == "terrain_continuity":
            for field_name in [
                "from_segment",
                "to_segment",
            ]:
                if edge.get(
                    field_name
                ) not in segment_ids:
                    add_finding(
                        findings,
                        "error",
                        "graph_bad_segment_edge",
                        "Terrain graph edge references an unknown segment ID.",
                        path,
                        edge_id=edge.get(
                            "edge_id"
                        ),
                        field=field_name,
                        value=edge.get(
                            field_name
                        ),
                    )

        elif edge_type == "approach_transition":
            approach_id = edge.get(
                "approach_id"
            )
            if approach_id not in approach_ids:
                add_finding(
                    findings,
                    "error",
                    "graph_bad_approach_edge",
                    "Approach transition references an unknown approach ID.",
                    path,
                    edge_id=edge.get(
                        "edge_id"
                    ),
                    approach_id=approach_id,
                )

            if (
                edge.get(
                    "from_location"
                ) is None
                or edge.get(
                    "to_location"
                ) is None
            ):
                approach_edges_missing_locations.append(
                    {
                        "edge_id": edge.get(
                            "edge_id"
                        ),
                        "approach_id": approach_id,
                    }
                )

    if approach_edges_missing_locations:
        add_finding(
            findings,
            "warning",
            "graph_approach_transition_missing_locations",
            "Approach transitions lack explicit endpoint locations.",
            path,
            count=len(
                approach_edges_missing_locations
            ),
            examples=approach_edges_missing_locations[:5],
        )

    return findings


def nearest_overlay_node(
    mile: float,
    overlay_nodes: list[dict[str, Any]],
    logistics_only: bool = False,
) -> tuple[float, dict[str, Any]] | None:
    candidates: list[tuple[float, dict[str, Any]]] = []

    for node in overlay_nodes:
        node_mile = to_float(
            node.get(
                "trail_mile"
            )
        )
        if node_mile is None:
            continue

        if logistics_only and not (
            node.get(
                "logistics"
            )
            or node.get(
                "resupply"
            )
            or node.get(
                "town_access"
            )
            or node.get(
                "node_class"
            ) in {
                "logistics",
                "crossing",
                "trailhead",
                "access",
            }
        ):
            continue

        candidates.append(
            (
                abs(
                    node_mile - mile
                ),
                node,
            )
        )

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda item: item[0],
    )


def validate_runtime_dataset(
    trail_root: str | Path,
) -> list[DataQualityFinding]:
    trail_root = Path(
        trail_root
    )
    findings: list[DataQualityFinding] = []

    route_overlay = read_json_file(
        trail_root / "compiled/route_overlay.json",
        findings,
    )
    route_master_rows = read_csv_file(
        trail_root / "raw/csv/route_master.csv",
        findings,
    )
    resupply_rows = read_csv_file(
        trail_root / "raw/csv/resupply_amenities.csv",
        findings,
    )
    town_lodging_path = (
        trail_root /
        "raw/csv/town_lodging_options.csv"
    )
    town_lodging_rows = (
        read_csv_file(
            town_lodging_path,
            findings,
        )
        if town_lodging_path.exists()
        else None
    )
    raw_approach_rows = read_csv_file(
        trail_root / "raw/csv/approach_trails.csv",
        findings,
    )
    compiled_approaches = read_json_file(
        trail_root / "compiled/approach_trails.json",
        findings,
    )
    overnight_reference = read_json_file(
        trail_root / "compiled/overnight_reference.json",
        findings,
    )
    spine = read_json_file(
        trail_root / "compiled/spine.geojson",
        findings,
    )
    terrain = read_json_file(
        trail_root / "compiled/terrain.geojson",
        findings,
    )
    operational_graph = read_json_file(
        trail_root / "compiled/operational_graph.json",
        findings,
    )

    overlay_nodes: list[dict[str, Any]] = []
    overlay_ids: set[str] = set()
    overlay_miles: list[float] = []

    if isinstance(
        route_overlay,
        dict,
    ):
        findings.extend(
            validate_route_overlay_payload(
                route_overlay
            )
        )
        overlay_nodes = [
            node
            for node in route_overlay.get(
                "overlay_nodes",
                [],
            )
            if isinstance(
                node,
                dict,
            )
        ]
        overlay_ids = {
            node.get(
                "overlay_id"
            )
            for node in overlay_nodes
            if node.get(
                "overlay_id"
            )
        }
        overlay_miles = [
            mile
            for mile in (
                to_float(
                    node.get(
                        "trail_mile"
                    )
                )
                for node in overlay_nodes
            )
            if mile is not None
        ]

    if route_master_rows is not None:
        findings.extend(
            validate_route_master_rows(
                route_master_rows
            )
        )

        route_master_miles = [
            mile
            for mile in (
                to_float(
                    row.get(
                        "miles_from_MA_border_nb"
                    )
                )
                for row in route_master_rows
            )
            if mile is not None
        ]
        if (
            overlay_miles
            and route_master_miles
        ):
            if abs(
                min(
                    overlay_miles
                )
                - min(
                    route_master_miles
                )
            ) > 1.0 or abs(
                max(
                    overlay_miles
                )
                - max(
                    route_master_miles
                )
            ) > 1.5:
                add_finding(
                    findings,
                    "warning",
                    "route_master_overlay_range_mismatch",
                    "Route master and overlay mile ranges differ.",
                    "raw/csv/route_master.csv",
                    route_master_min=min(
                        route_master_miles
                    ),
                    route_master_max=max(
                        route_master_miles
                    ),
                    overlay_min=min(
                        overlay_miles
                    ),
                    overlay_max=max(
                        overlay_miles
                    ),
                )

    if resupply_rows is not None:
        findings.extend(
            validate_resupply_amenities_rows(
                resupply_rows,
                overlay_nodes,
            )
        )

    if (
        town_lodging_rows is not None
        and resupply_rows is not None
    ):
        findings.extend(
            validate_town_lodging_options_rows(
                town_lodging_rows,
                resupply_rows,
            )
        )

    approach_ids: set[str] = set()
    if raw_approach_rows is not None:
        findings.extend(
            validate_approach_rows(
                raw_approach_rows,
                compiled_approaches
                if isinstance(
                    compiled_approaches,
                    dict,
                )
                else None,
            )
        )
        approach_ids = {
            row.get(
                "approach_id"
            )
            for row in raw_approach_rows
            if row.get(
                "approach_id"
            )
        }

    if isinstance(
        overnight_reference,
        dict,
    ):
        findings.extend(
            validate_overnight_reference_payload(
                overnight_reference,
                overlay_ids,
            )
        )

    if isinstance(
        spine,
        dict,
    ):
        findings.extend(
            validate_spine_payload(
                spine
            )
        )

    if isinstance(
        terrain,
        dict,
    ):
        findings.extend(
            validate_terrain_payload(
                terrain,
                overlay_miles,
            )
        )

    if isinstance(
        operational_graph,
        dict,
    ):
        findings.extend(
            validate_operational_graph_payload(
                operational_graph,
                overlay_ids,
                approach_ids,
            )
        )

    return findings


def summarize_findings(
    findings: list[DataQualityFinding],
) -> dict[str, int]:
    summary = {
        "error": 0,
        "warning": 0,
        "info": 0,
    }

    for finding in findings:
        summary[finding.severity] += 1

    return summary


def format_findings_markdown(
    findings: list[DataQualityFinding],
) -> str:
    summary = summarize_findings(
        findings
    )

    lines = [
        "# CairnOS Runtime Data Quality Report",
        "",
        "## Summary",
        "",
        f"- errors: {summary['error']}",
        f"- warnings: {summary['warning']}",
        f"- info: {summary['info']}",
        "",
    ]

    for severity in [
        "error",
        "warning",
        "info",
    ]:
        items = [
            finding
            for finding in findings
            if finding.severity == severity
        ]

        if not items:
            continue

        lines.extend([
            f"## {severity.title()}",
            "",
        ])

        for finding in items:
            detail = (
                f" `{finding.path}`"
                if finding.path
                else ""
            )
            lines.append(
                f"- `{finding.code}`{detail}: {finding.message}"
            )
            if finding.context:
                lines.append(
                    "  "
                    + json.dumps(
                        finding.context,
                        sort_keys=True,
                    )
                )

        lines.append(
            ""
        )

    return "\n".join(lines)


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description="Validate CairnOS runtime trail data.",
    )
    parser.add_argument(
        "trail_root",
        nargs="?",
        default="trails/vermont_long_trail",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON findings instead of Markdown.",
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit nonzero when error findings are present.",
    )

    args = parser.parse_args(
        argv
    )
    findings = validate_runtime_dataset(
        args.trail_root
    )

    if args.json:
        print(
            json.dumps(
                {
                    "summary": summarize_findings(
                        findings
                    ),
                    "findings": [
                        finding.to_dict()
                        for finding in findings
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(
            format_findings_markdown(
                findings
            )
        )

    if (
        args.fail_on_error
        and error_findings(
            findings
        )
    ):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )
