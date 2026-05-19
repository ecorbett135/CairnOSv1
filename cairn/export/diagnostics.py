# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""Developer diagnostic package export for generated CairnOS plans."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import platform
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cairn.export.elevation_confidence import (
    build_elevation_confidence_report,
)
from cairn.export.gaia_geojson import dumps_geojson


DIAGNOSTIC_SCHEMA_VERSION = "cairnos_diagnostic_v1"

RUNTIME_INPUTS = [
    "compiled/route_overlay.json",
    "compiled/operational_graph.json",
    "compiled/logistics_nodes.json",
    "compiled/spine.geojson",
    "compiled/terrain.geojson",
    "compiled/overnight_reference.json",
    "compiled/waypoint_reference.json",
    "raw/csv/route_master.csv",
    "raw/csv/approach_trails.csv",
    "raw/csv/resupply_amenities.csv",
]


def utc_timestamp() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .strftime("%Y%m%dT%H%M%SZ")
    )


def project_root_for_trail(trail_root: Path) -> Path:
    trail_root = trail_root.resolve()

    try:
        return trail_root.parents[1]
    except IndexError:
        return trail_root.parent


def relative_path(
    path: Path,
    project_root: Path,
) -> str:
    try:
        return path.resolve().relative_to(project_root).as_posix()
    except ValueError:
        return path.name


def sanitize_value(
    value: Any,
    project_root: Path,
    trail_root: Path,
    key: str | None = None,
) -> Any:
    if isinstance(value, dict):
        return {
            str(item_key): sanitize_value(
                item_value,
                project_root,
                trail_root,
                str(item_key),
            )
            for item_key, item_value in value.items()
        }

    if isinstance(value, list):
        return [
            sanitize_value(
                item,
                project_root,
                trail_root,
            )
            for item in value
        ]

    if isinstance(value, tuple):
        return [
            sanitize_value(
                item,
                project_root,
                trail_root,
            )
            for item in value
        ]

    if isinstance(value, Path):
        return sanitize_path_string(
            str(value),
            project_root,
            trail_root,
            key,
        )

    if isinstance(value, str):
        return sanitize_path_string(
            value,
            project_root,
            trail_root,
            key,
        )

    return value


def sanitize_path_string(
    value: str,
    project_root: Path,
    trail_root: Path,
    key: str | None = None,
) -> str:
    if key == "trail_root":
        return relative_path(
            trail_root,
            project_root,
        )

    if not value.startswith("/"):
        return value

    path = Path(value)

    try:
        return path.resolve().relative_to(project_root).as_posix()
    except ValueError:
        return "[redacted_path]"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with open(path, "rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def build_data_fingerprints(
    trail_root: Path,
    project_root: Path,
) -> list[dict[str, Any]]:
    fingerprints = []

    for runtime_path in RUNTIME_INPUTS:
        path = trail_root / runtime_path

        if path.exists():
            fingerprints.append(
                {
                    "relative_path": relative_path(
                        path,
                        project_root,
                    ),
                    "exists": True,
                    "byte_size": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
        else:
            fingerprints.append(
                {
                    "relative_path": (
                        Path("trails")
                        / trail_root.name
                        / runtime_path
                    ).as_posix(),
                    "exists": False,
                    "byte_size": None,
                    "sha256": None,
                }
            )

    return fingerprints


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    output = io.StringIO()

    fieldnames = sorted(
        {
            key
            for row in rows
            for key in row.keys()
        }
    )

    if fieldnames:
        writer = csv.DictWriter(
            output,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)

    return output.getvalue().encode("utf-8")


def json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        indent=2,
        sort_keys=True,
    ).encode("utf-8")


def build_manifest(
    planner_result: dict[str, Any],
    trail_root: Path,
    project_root: Path,
    build_sha: str,
    generated_at: str,
) -> dict[str, Any]:
    config = planner_result.get(
        "config",
        {},
    )

    return {
        "schema_version": DIAGNOSTIC_SCHEMA_VERSION,
        "generated_at": generated_at,
        "build_sha": build_sha or "unknown",
        "python": {
            "version": sys.version.split()[0],
            "implementation": platform.python_implementation(),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "selected_trail": config.get(
            "selected_trail",
            trail_root.name,
        ),
        "trail_root": relative_path(
            trail_root,
            project_root,
        ),
        "direction": config.get(
            "direction",
        ),
        "trip_type": config.get(
            "trip_type",
        ),
        "planner_settings": sanitize_value(
            config,
            project_root,
            trail_root,
        ),
    }


def diagnostic_filename(
    planner_result: dict[str, Any],
    build_sha: str,
    generated_at: str | None = None,
) -> str:
    config = planner_result.get(
        "config",
        {},
    )
    trail = str(
        config.get(
            "selected_trail",
            "trail",
        )
    )
    direction = str(
        config.get(
            "direction",
            "direction",
        )
    ).lower()
    timestamp = generated_at or utc_timestamp()
    build = (build_sha or "unknown")[:12]

    return (
        f"cairnos_diagnostic_{trail}_{direction}_"
        f"{timestamp}_{build}.zip"
    )


def build_diagnostic_package(
    planner_result: dict[str, Any],
    trail_root: Path | str,
    gaia_export: dict[str, Any],
    build_sha: str,
    *,
    generated_at: str | None = None,
) -> bytes:
    trail_root = Path(trail_root).resolve()
    project_root = project_root_for_trail(
        trail_root
    )
    generated_at = generated_at or utc_timestamp()

    sanitized_result = sanitize_value(
        planner_result,
        project_root,
        trail_root,
    )
    itinerary = sanitized_result.get(
        "itinerary",
        {},
    )
    daily_plan = itinerary.get(
        "daily_plan",
        [],
    )
    resupply_plan = itinerary.get(
        "resupply_plan",
        [],
    )
    completion_analysis = itinerary.get(
        "completion_analysis",
        {},
    )
    gaia_geojson = gaia_export.get(
        "geojson",
        {},
    )
    gaia_warnings = gaia_export.get(
        "warnings",
        [],
    )

    manifest = build_manifest(
        planner_result,
        trail_root,
        project_root,
        build_sha,
        generated_at,
    )
    fingerprints = build_data_fingerprints(
        trail_root,
        project_root,
    )
    elevation_confidence = (
        build_elevation_confidence_report(
            sanitized_result,
            trail_root,
        )
    )

    buffer = io.BytesIO()

    with zipfile.ZipFile(
        buffer,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "manifest.json",
            json_bytes(manifest),
        )
        archive.writestr(
            "plan.json",
            json_bytes(sanitized_result),
        )
        archive.writestr(
            "itinerary.csv",
            csv_bytes(daily_plan),
        )
        archive.writestr(
            "resupply_strategy.csv",
            csv_bytes(resupply_plan),
        )
        archive.writestr(
            "completion_analysis.json",
            json_bytes(completion_analysis),
        )
        archive.writestr(
            "gaia.geojson",
            dumps_geojson(
                gaia_geojson
            ).encode("utf-8"),
        )
        archive.writestr(
            "gaia_warnings.json",
            json_bytes(gaia_warnings),
        )
        archive.writestr(
            "data_fingerprints.json",
            json_bytes(fingerprints),
        )
        archive.writestr(
            "elevation_confidence.json",
            json_bytes(elevation_confidence),
        )

    return buffer.getvalue()
