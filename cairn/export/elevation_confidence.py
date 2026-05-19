# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""Elevation confidence diagnostics for generated CairnOS plans."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cairn.planner.planner_v2 import PlannerV2


ELEVATION_CONFIDENCE_SCHEMA_VERSION = (
    "cairnos_elevation_confidence_v1"
)


def parse_float(
    value,
) -> float | None:
    if value in {
        None,
        "",
    }:
        return None

    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return None


def parse_int(
    value,
) -> int | None:
    if value in {
        None,
        "",
    }:
        return None

    try:
        return int(value)
    except (
        TypeError,
        ValueError,
    ):
        return None


def terrain_source_parts(
    terrain_stats,
) -> list[str]:
    if not terrain_stats:
        return []

    source_parts = terrain_stats.get(
        "source_parts"
    )

    if source_parts:
        return [
            str(source)
            for source in source_parts
        ]

    source = terrain_stats.get(
        "source"
    )

    return [
        str(source)
    ] if source else []


def gain_delta_percent(
    delta,
    reported_gain,
) -> float | None:
    if (
        delta is None
        or reported_gain in {
            None,
            0,
        }
    ):
        return None

    return (
        delta
        / reported_gain
        * 100.0
    )


def classify_confidence(
    terrain_stats,
    daily_miles,
    gain_delta,
    delta_percent,
) -> tuple[str, list[str]]:
    if (
        daily_miles is None
        or daily_miles <= 0
    ):
        return (
            "not_applicable",
            [
                "zero_or_nonmoving_day",
            ],
        )

    sources = set(
        terrain_source_parts(
            terrain_stats
        )
    )
    reasons = []

    if not sources or "none" in sources:
        return (
            "not_applicable",
            [
                "no_elevation_interval",
            ],
        )

    if "estimated" in sources:
        reasons.append(
            "distance_based_elevation_estimate"
        )
        confidence = "low"
    elif "route_master" in sources:
        reasons.append(
            "route_master_elevation_fallback"
        )
        confidence = "medium"
    else:
        confidence = "high"

    if (
        gain_delta is not None
        and abs(gain_delta) > 100
        and (
            delta_percent is None
            or abs(delta_percent) > 5
        )
    ):
        reasons.append(
            "reported_gain_differs_from_recomputed_interval"
        )
        if confidence == "high":
            confidence = "medium"

    if not reasons:
        reasons.append(
            "terrain_interval_resolved"
        )

    return (
        confidence,
        reasons,
    )


def summarize_days(
    days,
) -> dict[str, Any]:
    summary = {
        "total_days": len(days),
        "moving_days": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "not_applicable": 0,
        "flagged_days": [],
        "off_spine_overnight_access_days": [],
    }

    for day in days:
        confidence = day["confidence"]
        summary[confidence] = (
            summary.get(
                confidence,
                0,
            )
            + 1
        )

        if confidence != "not_applicable":
            summary["moving_days"] += 1

        if confidence in {
            "medium",
            "low",
        }:
            summary["flagged_days"].append(
                day["day"]
            )

        stop_alignment = day.get(
            "daily_stop_spine_alignment"
        )

        if (
            isinstance(stop_alignment, dict)
            and stop_alignment.get("status")
            == "off_spine_overnight_access"
        ):
            summary[
                "off_spine_overnight_access_days"
            ].append(day["day"])

    return summary


def build_day_confidence(
    planner,
    row,
) -> dict[str, Any]:
    day = parse_int(
        row.get("day")
    )
    start_mile = parse_float(
        row.get("daily_start_mile")
    )
    stop_mile = parse_float(
        row.get("daily_stop_mile")
    )
    daily_miles = parse_float(
        row.get("daily_miles")
    )
    reported_gain = parse_float(
        row.get("daily_elevation_gain")
    )
    terrain_stats = None

    if (
        start_mile is not None
        and stop_mile is not None
    ):
        terrain_stats = (
            planner.analyze_terrain_interval(
                start_mile,
                stop_mile,
            )
        )

    recomputed_gain = (
        terrain_stats.get(
            "elevation_gain_ft"
        )
        if terrain_stats
        else None
    )
    delta = None

    if (
        reported_gain is not None
        and recomputed_gain is not None
    ):
        delta = (
            recomputed_gain
            - reported_gain
        )

    delta_percent = gain_delta_percent(
        delta,
        reported_gain,
    )
    confidence, reasons = classify_confidence(
        terrain_stats,
        daily_miles,
        delta,
        delta_percent,
    )

    return {
        "day": day,
        "daily_start_mile": start_mile,
        "daily_stop_mile": stop_mile,
        "daily_miles": daily_miles,
        "daily_start_location": row.get(
            "daily_start_location"
        ),
        "daily_start_canonical_location": row.get(
            "daily_start_canonical_location"
        ),
        "daily_start_access_notes": row.get(
            "daily_start_access_notes"
        ),
        "daily_start_spine_alignment": row.get(
            "daily_start_spine_alignment"
        ),
        "daily_stop_location": row.get(
            "daily_stop_location"
        ),
        "daily_stop_canonical_location": row.get(
            "daily_stop_canonical_location"
        ),
        "daily_stop_access_notes": row.get(
            "daily_stop_access_notes"
        ),
        "daily_stop_spine_alignment": row.get(
            "daily_stop_spine_alignment"
        ),
        "reported_elevation_gain_ft": (
            reported_gain
        ),
        "recomputed_elevation_gain_ft": (
            recomputed_gain
        ),
        "gain_delta_ft": (
            round(
                delta,
                0,
            )
            if delta is not None
            else None
        ),
        "gain_delta_percent": (
            round(
                delta_percent,
                1,
            )
            if delta_percent is not None
            else None
        ),
        "terrain_source": (
            terrain_stats.get("source")
            if terrain_stats
            else None
        ),
        "terrain_source_parts": (
            terrain_stats.get("source_parts")
            if terrain_stats
            else None
        ),
        "gain_per_mile": (
            terrain_stats.get("gain_per_mile")
            if terrain_stats
            else None
        ),
        "ruggedness_score": (
            terrain_stats.get(
                "ruggedness_score"
            )
            if terrain_stats
            else None
        ),
        "confidence": confidence,
        "reasons": reasons,
    }


def build_elevation_confidence_report(
    planner_result: dict[str, Any],
    trail_root: Path | str,
) -> dict[str, Any]:
    planner = PlannerV2(
        trail_root=Path(trail_root),
    )
    daily_plan = (
        planner_result
        .get("itinerary", {})
        .get("daily_plan", [])
    )
    days = [
        build_day_confidence(
            planner,
            row,
        )
        for row in daily_plan
    ]

    return {
        "schema_version": (
            ELEVATION_CONFIDENCE_SCHEMA_VERSION
        ),
        "summary": summarize_days(
            days
        ),
        "days": days,
    }
