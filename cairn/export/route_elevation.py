# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""Deterministic elevation summaries for emitted route-track points."""

from __future__ import annotations

import math
from typing import Any


ELEVATION_UNIT = "m"
EARTH_RADIUS_METERS = 6371008.8
LENGTH_METHOD = "wgs84_haversine_segment_sum"
ELEVATION_CHANGE_METHOD = "ordered_track_point_delta_sum"
AVERAGE_GRADE_METHOD = "net_elevation_change_over_length"
BOUNDARY_ELEVATION_METHOD = (
    "linear_between_adjacent_source_elevations_at_mileage_slice_boundary"
)


def normalize_track_points(
    points: list[list[float]],
) -> list[list[float]]:
    """Match the numeric precision emitted into GPX and used for metrics."""

    normalized: list[list[float]] = []
    for point in points:
        if not _valid_number_pair(point):
            continue
        normalized_point = [
            float(f"{float(point[0]):.8f}"),
            float(f"{float(point[1]):.8f}"),
        ]
        if len(point) >= 3 and _valid_number(point[2]):
            normalized_point.append(
                float(f"{float(point[2]):.3f}")
            )
        normalized.append(normalized_point)
    return normalized


def elevation_profile(
    points: list[list[float]],
) -> dict[str, Any]:
    track_point_count = len(points)
    elevation_point_count = sum(
        1
        for point in points
        if len(point) >= 3 and _valid_number(point[2])
    )
    if track_point_count and elevation_point_count == track_point_count:
        status = "complete"
    elif elevation_point_count:
        status = "partial"
    else:
        status = "unavailable"

    return {
        "status": status,
        "unit": ELEVATION_UNIT,
        "track_point_count": track_point_count,
        "elevation_point_count": elevation_point_count,
        "missing_elevation_point_count": (
            track_point_count - elevation_point_count
        ),
        "boundary_elevation_method": BOUNDARY_ELEVATION_METHOD,
    }


def track_metrics(
    points: list[list[float]],
) -> dict[str, Any]:
    """Return metrics reproducible from the emitted, ordered GPX points."""

    length_m = sum(
        haversine_meters(first, second)
        for first, second in zip(points, points[1:])
    )
    profile = elevation_profile(points)
    total_ascent_m: float | None = None
    total_descent_m: float | None = None
    average_grade_percent: float | None = None

    if profile["status"] == "complete" and points:
        total_ascent_m = 0.0
        total_descent_m = 0.0
        for first, second in zip(points, points[1:]):
            delta = float(second[2]) - float(first[2])
            if delta > 0:
                total_ascent_m += delta
            elif delta < 0:
                total_descent_m += abs(delta)
        average_grade_percent = (
            ((float(points[-1][2]) - float(points[0][2])) / length_m) * 100
            if length_m > 0
            else 0.0
        )

    return {
        "length_m": round(length_m, 3),
        "total_ascent_m": _rounded_or_none(total_ascent_m),
        "total_descent_m": _rounded_or_none(total_descent_m),
        "average_grade_percent": _rounded_or_none(
            average_grade_percent,
        ),
        "length_method": LENGTH_METHOD,
        "elevation_change_method": ELEVATION_CHANGE_METHOD,
        "average_grade_method": AVERAGE_GRADE_METHOD,
    }


def haversine_meters(
    first: list[float],
    second: list[float],
) -> float:
    first_latitude = math.radians(float(first[1]))
    second_latitude = math.radians(float(second[1]))
    latitude_delta = second_latitude - first_latitude
    longitude_delta = math.radians(
        float(second[0]) - float(first[0])
    )
    value = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(first_latitude)
        * math.cos(second_latitude)
        * math.sin(longitude_delta / 2) ** 2
    )
    return EARTH_RADIUS_METERS * 2 * math.asin(math.sqrt(value))


def _valid_number_pair(value: Any) -> bool:
    return (
        isinstance(value, (list, tuple))
        and len(value) >= 2
        and _valid_number(value[0])
        and _valid_number(value[1])
    )


def _valid_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _rounded_or_none(value: float | None) -> float | None:
    return round(value, 3) if value is not None else None
