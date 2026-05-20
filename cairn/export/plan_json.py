# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""Schema-versioned CairnOS plan JSON export."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PLAN_EXPORT_SCHEMA_VERSION = "cairnos_plan_v1"


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


def plan_warnings() -> list[dict[str, str]]:
    return [
        {
            "code": "alpha_advisory",
            "severity": "warning",
            "message": (
                "CairnOS plan JSON is advisory alpha planning output, "
                "not a safety-critical trip plan."
            ),
        },
        {
            "code": "verify_official_sources",
            "severity": "warning",
            "message": (
                "Verify routes, services, closures, weather, water, "
                "and backcountry decisions with official/current sources."
            ),
        },
    ]


def build_plan_export(
    planner_result: dict[str, Any],
    trail_root: Path | str,
    build_sha: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    trail_root = Path(trail_root).resolve()
    project_root = project_root_for_trail(
        trail_root
    )
    generated_at = generated_at or utc_timestamp()
    config = planner_result.get(
        "config",
        {},
    )
    itinerary = planner_result.get(
        "itinerary",
        {},
    )
    resolved_build_sha = (
        build_sha
        or planner_result.get("build_sha")
        or "unknown"
    )
    trail_id = str(
        config.get(
            "selected_trail",
            trail_root.name,
        )
    )

    payload = {
        "export_version": PLAN_EXPORT_SCHEMA_VERSION,
        "generated_at": generated_at,
        "build_sha": resolved_build_sha,
        "trail_id": trail_id,
        "planner": {
            "name": "PlannerV2",
            "facade": "cairn.planner.planner_v2.PlannerV2",
            "trip_type": config.get("trip_type"),
            "direction": config.get("direction"),
            "trail_root": relative_path(
                trail_root,
                project_root,
            ),
        },
        "user_profile": config,
        "completion_analysis": itinerary.get(
            "completion_analysis",
            {},
        ),
        "expedition_summary": itinerary.get(
            "expedition_summary",
            {},
        ),
        "directional_access": itinerary.get(
            "directional_access",
            {},
        ),
        "resupply_plan": itinerary.get(
            "resupply_plan",
            [],
        ),
        "resupply_town_details": itinerary.get(
            "resupply_town_details",
            [],
        ),
        "selected_experiences": itinerary.get(
            "selected_experiences",
            [],
        ),
        "season_advisories": itinerary.get(
            "season_advisories",
            [],
        ),
        "daily_plan": itinerary.get(
            "daily_plan",
            [],
        ),
        "warnings": plan_warnings(),
    }

    return sanitize_value(
        payload,
        project_root,
        trail_root,
    )


def dumps_plan_export(
    payload: dict[str, Any],
) -> str:
    return json.dumps(
        payload,
        indent=2,
        sort_keys=True,
    )


def plan_export_filename(
    planner_result: dict[str, Any],
    build_sha: str | None = None,
    generated_at: str | None = None,
) -> str:
    config = planner_result.get(
        "config",
        {},
    )
    trail = slugify(
        str(
            config.get(
                "selected_trail",
                "trail",
            )
        )
    )
    direction = slugify(
        str(
            config.get(
                "direction",
                "direction",
            )
        ).lower()
    )
    timestamp = generated_at or utc_timestamp()
    build = (
        build_sha
        or planner_result.get("build_sha")
        or "unknown"
    )[:12]

    return (
        f"cairnos_plan_{trail}_{direction}_"
        f"{timestamp}_{build}.json"
    )


def slugify(value: str) -> str:
    slug = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        value.strip(),
    ).strip("_")

    return slug or "unknown"
