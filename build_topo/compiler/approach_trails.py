# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import csv
import json
import math
import sys
from pathlib import Path


#
# ---------------------------------------------------------
# TRAIL ROOT
# ---------------------------------------------------------
#

trail_root = (
    Path(sys.argv[1]).resolve()
    if len(sys.argv) > 1
    else Path(
        "trails/vermont_long_trail"
    ).resolve()
)

RAW_DIR = trail_root / "raw"

COMPILED_DIR = (
    trail_root / "compiled"
)

CSV_DIR = RAW_DIR / "csv"

APPROACH_CSV = (
    CSV_DIR /
    "approach_trails.csv"
)

APPROACH_GEOMETRY_SOURCES_CSV = (
    CSV_DIR /
    "approach_geometry_sources.csv"
)

OUTPUT_PATH = (
    COMPILED_DIR /
    "approach_trails.json"
)


#
# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
#


SCHEMA_VERSION = "cairnos_approach_trails_v2"
ELEVATION_UNIT = "m"
ELEVATION_METHOD = "source_embedded_coordinate"


def _cell(row, *field_names):
    for field_name in field_names:
        value = (row.get(field_name) or "").strip()
        if value:
            return value
    return ""


def _float_cell(row, *field_names):
    value = _cell(row, *field_names)
    return float(value) if value else 0.0


def load_approach_rows(path=None):

    path = Path(path or APPROACH_CSV)

    if not path.exists():

        raise FileNotFoundError(
            f"Missing approach trail CSV: {path}"
        )

    rows = []

    with open(path, newline="", encoding="utf-8") as f:

        reader = csv.DictReader(f)

        for row in reader:

            rows.append(
                {
                    "route": _cell(row, "route", "route_name"),

                    "approach_id": _cell(row, "approach_id"),

                    "approach_name": _cell(row, "approach_name"),

                    "direction": _cell(row, "direction"),
                    "terminus": _cell(
                        row,
                        "terminus",
                        "connected_terminus",
                    ),
                    "connected_terminus": _cell(
                        row,
                        "connected_terminus",
                        "terminus",
                    ),
                    "trail_miles": _float_cell(
                        row,
                        "trail_miles",
                        "distance_to_terminus_mi",
                    ),
                    "distance_to_terminus_mi": _float_cell(
                        row,
                        "distance_to_terminus_mi",
                        "trail_miles",
                    ),
                    "elevation_gain_ft": _float_cell(
                        row,
                        "elevation_gain_ft",
                    ),
                    "access_town": _cell(row, "access_town"),
                    "location": _cell(
                        row,
                        "location",
                        "start_location",
                        "end_location",
                    ),
                    "start_location": _cell(
                        row,
                        "start_location",
                        "location",
                    ),
                    "end_location": _cell(
                        row,
                        "end_location",
                        "location",
                    ),
                    "route_name": _cell(row, "route_name", "route"),
                    "sequence": int(
                        _cell(row, "sequence") or 0
                    ),
                    "cumulative_to_trail_mi": _float_cell(
                        row,
                        "cumulative_to_trail_mi",
                    ),
                    "node_class": _cell(row, "node_class"),
                    "overnight": _cell(row, "overnight"),
                    "camping": _cell(row, "camping"),
                    "road_access": _cell(row, "road_access"),
                    "notes": _cell(row, "notes"),
                }
            )

    return rows


def _flatten_coordinate_count(geometry):
    coordinates = geometry.get("coordinates", [])
    if geometry.get("type") == "LineString":
        return len(coordinates)
    if geometry.get("type") == "MultiLineString":
        return sum(len(line) for line in coordinates)
    return 0


def _geometry_coordinates(geometry):
    coordinates = geometry.get("coordinates", [])
    if geometry.get("type") == "LineString":
        return list(coordinates)
    if geometry.get("type") == "MultiLineString":
        return [
            coordinate
            for line in coordinates
            for coordinate in line
        ]
    raise ValueError(
        "Approach geometry must be a LineString or MultiLineString"
    )


def _promoted_geometry(geometry):
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])
    source_coordinates = _geometry_coordinates(geometry)
    has_complete_elevation = bool(source_coordinates) and all(
        len(coordinate) >= 3
        and isinstance(coordinate[2], (int, float))
        and not isinstance(coordinate[2], bool)
        and math.isfinite(coordinate[2])
        for coordinate in source_coordinates
    )
    coordinate_length = 3 if has_complete_elevation else 2

    if geometry_type == "LineString":
        normalized = [
            coordinate[:coordinate_length]
            for coordinate in coordinates
        ]
    elif geometry_type == "MultiLineString":
        normalized = [
            [
                coordinate[:coordinate_length]
                for coordinate in line
            ]
            for line in coordinates
        ]
    else:
        raise ValueError(
            "Approach geometry must be a LineString or MultiLineString"
        )

    return (
        {
            "type": geometry_type,
            "coordinates": normalized,
        },
        {
            "status": (
                "complete"
                if has_complete_elevation
                else "unavailable"
            ),
            "unit": ELEVATION_UNIT,
            "method": ELEVATION_METHOD,
            "coordinate_count": len(source_coordinates),
            "elevation_coordinate_count": (
                len(source_coordinates)
                if has_complete_elevation
                else 0
            ),
        },
    )


def load_approach_geometries(
    rows,
    trail_root_path=None,
    sources_path=None,
):
    trail_root_path = Path(trail_root_path or trail_root)
    sources_path = Path(
        sources_path or APPROACH_GEOMETRY_SOURCES_CSV
    )
    if not sources_path.exists():
        return []

    approach_rows = {}
    for row in rows:
        approach_rows.setdefault(row["approach_id"], []).append(row)

    geometries = []
    with sources_path.open(newline="", encoding="utf-8") as handle:
        for source in csv.DictReader(handle):
            approach_id = _cell(source, "approach_id")
            if approach_id not in approach_rows:
                raise ValueError(
                    "Approach geometry source references unknown approach_id: "
                    f"{approach_id}"
                )

            source_path = _cell(source, "source_path")
            geojson_path = trail_root_path / source_path
            if not geojson_path.exists():
                raise FileNotFoundError(
                    f"Missing approach geometry source: {geojson_path}"
                )

            with geojson_path.open(encoding="utf-8") as geojson_handle:
                payload = json.load(geojson_handle)

            source_feature_id = _cell(source, "source_feature_id")
            matches = [
                feature
                for feature in payload.get("features", [])
                if str(
                    feature.get("id")
                    or feature.get("properties", {}).get("id")
                    or ""
                )
                == source_feature_id
            ]
            if len(matches) != 1:
                raise ValueError(
                    "Approach geometry source_feature_id must resolve exactly "
                    f"once: {source_feature_id}"
                )

            feature = matches[0]
            properties = feature.get("properties", {})
            expected_title = _cell(source, "source_feature_title")
            if expected_title and properties.get("title") != expected_title:
                raise ValueError(
                    "Approach geometry source title mismatch for "
                    f"{source_feature_id}"
                )

            geometry, elevation = _promoted_geometry(
                feature.get("geometry", {})
            )
            selected_rows = approach_rows[approach_id]
            miles = [
                row["cumulative_to_trail_mi"]
                for row in selected_rows
            ]
            connected_termini = {
                row["connected_terminus"]
                for row in selected_rows
                if row["connected_terminus"]
            }
            if len(connected_termini) != 1:
                raise ValueError(
                    "Approach geometry requires exactly one connected_terminus "
                    f"for approach_id: {approach_id}"
                )

            geometries.append({
                "geometry_id": _cell(source, "geometry_id"),
                "approach_id": approach_id,
                "approach_name": selected_rows[0]["approach_name"],
                "connected_terminus": next(iter(connected_termini)),
                "start_mile": min(miles),
                "end_mile": max(miles),
                "coordinate_count": _flatten_coordinate_count(geometry),
                "geometry": geometry,
                "elevation": {
                    **elevation,
                    "source_path": source_path,
                    "source_feature_id": source_feature_id,
                },
                "provenance": {
                    "source_path": source_path,
                    "source_feature_id": source_feature_id,
                    "source_feature_title": properties.get("title"),
                    "source_feature_updated_date": properties.get(
                        "updated_date"
                    ),
                    "source_kind": _cell(source, "source_kind"),
                    "source_license_status": _cell(
                        source,
                        "source_license_status",
                    ),
                    "transformation_notes": _cell(
                        source,
                        "transformation_notes",
                    ),
                },
            })

    return sorted(geometries, key=lambda item: item["approach_id"])


#
# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
#


def main():

    print("")
    print(
        "=== CairnOS Approach Trail Builder ==="
    )
    print("")

    print(
        "[INFO] Loading approach trails"
    )

    rows = load_approach_rows()

    print(
        f"[INFO] Approach trail rows: {len(rows)}"
    )

    payload = {
        "schema_version": SCHEMA_VERSION,
        "trail_system": trail_root.name,
        "approach_trails": rows,
        "approach_geometries": load_approach_geometries(rows),
    }

    print("")
    print("[EXPORTING]")
    print("")

    with open(OUTPUT_PATH, "w") as f:

        json.dump(
            payload,
            f,
            indent=2,
        )

    print(
        f"[OK] {OUTPUT_PATH}"
    )

    print("")
    print("[SUMMARY]")
    print("")

    print(
        f"Approach trails: {len(rows)}"
    )
    print(
        "Approach geometries: "
        f"{len(payload['approach_geometries'])}"
    )

    print("")
    print("[DONE]")


if __name__ == "__main__":

    main()
