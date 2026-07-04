# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""CairnOS-owned option data for Plan API clients."""

from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from cairn.api.plan_controls import build_plan_control_specs_response
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
        "control_specs": build_plan_control_specs_response(),
        "side_trip_options": build_side_trip_options(LONG_TRAIL_ROOT),
        "town_options": build_town_options(LONG_TRAIL_ROOT),
    }


def build_side_trip_options(trail_root: Path) -> list[dict[str, Any]]:
    path = trail_root / "raw" / "csv" / "side_trip_options.csv"
    if not path.exists():
        return []

    resupply_rows = _resupply_rows_by_preference_id(trail_root)
    total_mile = _trail_total_mile(trail_root)
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
            resupply_row = resupply_rows.get(_cell(row, "resupply_amenity_id"), {})
            label = _side_trip_label(row)
            option = {
                "id": option_id,
                "label": label,
                "name": _cell(row, "name"),
                "town_access": _cell(row, "town_access"),
                "category": _cell(row, "category"),
                "estimated_time": _cell(row, "estimated_time"),
            }
            option.update(_exit_metadata(resupply_row, total_mile))
            options.append(option)
    return options


def build_town_options(trail_root: Path) -> list[dict[str, Any]]:
    path = trail_root / "raw" / "csv" / "resupply_amenities.csv"
    if not path.exists():
        return []

    total_mile = _trail_total_mile(trail_root)
    options: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            town_access = _cell(row, "town_access")
            if not town_access:
                continue

            base_id = _town_preference_id(row)
            if base_id is None:
                continue
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
                        **_exit_metadata(row, total_mile),
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


def _town_preference_id(row: dict[str, str]) -> str | None:
    canonical_hint = _cell(row, "canonical_hint")
    trail_mile = _cell(row, "trail_mile")
    if not canonical_hint or not trail_mile:
        return None
    return f"{canonical_hint}:{trail_mile}"


def _resupply_rows_by_preference_id(trail_root: Path) -> dict[str, dict[str, str]]:
    path = trail_root / "raw" / "csv" / "resupply_amenities.csv"
    if not path.exists():
        return {}

    rows: dict[str, dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            preference_id = _town_preference_id(row)
            if preference_id:
                rows[preference_id] = row
    return rows


def _trail_total_mile(trail_root: Path) -> str:
    path = trail_root / "raw" / "csv" / "route_master.csv"
    max_mile: Decimal | None = None
    if path.exists():
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                mile = _decimal_cell(row, "mile")
                if mile is not None and (max_mile is None or mile > max_mile):
                    max_mile = mile

    if max_mile is None:
        return "272.1"
    return _format_decimal(max_mile)


def _exit_metadata(row: dict[str, str], total_mile: str) -> dict[str, str]:
    nobo_mile = _cell(row, "trail_mile")
    metadata = {
        "exit_point": _cell(row, "canonical_hint"),
        "access_notes": _cell(row, "access_notes"),
        "access_distance_miles": _cell(row, "access_distance_miles"),
    }

    nobo_decimal = _parse_decimal(nobo_mile)
    total_decimal = _parse_decimal(total_mile)
    if nobo_decimal is None or total_decimal is None:
        return metadata

    metadata["nobo_mile"] = _format_decimal(nobo_decimal)
    metadata["sobo_mile"] = _format_decimal(total_decimal - nobo_decimal)
    return metadata


def _decimal_cell(row: dict[str, str], key: str) -> Decimal | None:
    return _parse_decimal(_cell(row, key))


def _parse_decimal(value: str) -> Decimal | None:
    if not value:
        return None

    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _format_decimal(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.1")))


def _split_town_access_names(town_access: str) -> list[str]:
    return [name.strip() for name in town_access.split("/") if name.strip()]


def _cell(row: dict[str, str], key: str) -> str:
    return (row.get(key) or "").strip()


_side_trip_options = build_side_trip_options
_town_options = build_town_options
