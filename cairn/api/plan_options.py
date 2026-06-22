# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""CairnOS-owned option data for Plan API clients."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from cairn.api.plan_request import (
    LONG_TRAIL_ID,
    LONG_TRAIL_ROOT,
    PlanAPIValidationError,
)


def build_plan_options_response(trail_id: str = LONG_TRAIL_ID) -> dict[str, Any]:
    if trail_id != LONG_TRAIL_ID:
        raise PlanAPIValidationError(
            f"trail_id must be {LONG_TRAIL_ID!r} for the MVP Plan API"
        )

    return {
        "trail_id": trail_id,
        "status": "available",
        "side_trip_options": _side_trip_options(LONG_TRAIL_ROOT),
        "town_options": _town_options(LONG_TRAIL_ROOT),
    }


def _side_trip_options(trail_root: Path) -> list[dict[str, Any]]:
    path = trail_root / "raw" / "csv" / "side_trip_options.csv"
    if not path.exists():
        return []

    options: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if _cell(row, "validation_status").casefold() != "validated":
                continue

            option_id = _cell(row, "side_trip_id")
            if not option_id or option_id in seen_ids:
                continue

            seen_ids.add(option_id)
            label = _side_trip_label(row)
            options.append(
                {
                    "id": option_id,
                    "label": label,
                    "town_access": _cell(row, "town_access"),
                    "category": _cell(row, "category"),
                    "estimated_time": _cell(row, "estimated_time"),
                }
            )
    return options


def _town_options(trail_root: Path) -> list[dict[str, Any]]:
    path = trail_root / "raw" / "csv" / "resupply_amenities.csv"
    if not path.exists():
        return []

    options: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            town_access = _cell(row, "town_access")
            if not town_access:
                continue

            base_id = _town_preference_id(row)
            for town_name in _split_town_access_names(town_access):
                option_id = f"{base_id}::{town_name}"
                if not option_id or option_id in seen_ids:
                    continue

                seen_ids.add(option_id)
                canonical_hint = _cell(row, "canonical_hint")
                options.append(
                    {
                        "id": option_id,
                        "label": _town_label(town_name, canonical_hint),
                        "town_name": town_name,
                        "canonical_hint": canonical_hint,
                        "access_distance_miles": _cell(
                            row,
                            "access_distance_miles",
                        ),
                        "resupply_convenience": _cell(
                            row,
                            "resupply_convenience",
                        ),
                    }
                )
    return options


def _side_trip_label(row: dict[str, str]) -> str:
    town_access = _cell(row, "town_access")
    name = _cell(row, "name")
    estimated_time = _cell(row, "estimated_time")

    if town_access and name:
        label = f"{name} - {town_access}"
    else:
        label = town_access or name

    if estimated_time:
        return f"{label} ({estimated_time})"
    return label


def _town_label(town_name: str, canonical_hint: str) -> str:
    if canonical_hint:
        return f"{town_name} - town stop ({canonical_hint})"
    return f"{town_name} - town stop"


def _town_preference_id(row: dict[str, str]) -> str:
    return f"{_cell(row, 'canonical_hint')}:{_cell(row, 'trail_mile')}"


def _split_town_access_names(town_access: str) -> list[str]:
    return [name.strip() for name in town_access.split("/") if name.strip()]


def _cell(row: dict[str, str], key: str) -> str:
    return (row.get(key) or "").strip()
