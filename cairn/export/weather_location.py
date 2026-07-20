# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""Authoritative planned-day weather-location export contract."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from cairn.export.route_gpx import coordinate_context, resolve_location


WEATHER_LOCATION_CONTRACT_VERSION = (
    "cairnos_planned_day_weather_location_v1"
)
WEATHER_LOCATION_ROLE = "planned_daily_stop"
WEATHER_LOCATION_AUTHORITY = "cairnos_planned_itinerary"
WGS84_CRS = "EPSG:4326"


def _plan_id(
    *,
    trail_id: str,
    direction: Any,
    trip_type: Any,
    daily_plan: list[dict[str, Any]],
) -> str:
    identity = {
        "trail_id": trail_id,
        "direction": direction,
        "trip_type": trip_type,
        "days": [
            {
                "day": row.get("day"),
                "stop_overlay_id": row.get("daily_stop_overlay_id"),
                "stop_mile": row.get("daily_stop_mile"),
                "stop_location": row.get("daily_stop_canonical_location"),
            }
            for row in daily_plan
        ],
    }
    digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:24]
    return f"cairnos-plan-{digest}"


def _valid_wgs84(coordinates: Any) -> bool:
    if not isinstance(coordinates, (list, tuple)) or len(coordinates) < 2:
        return False
    longitude, latitude = coordinates[:2]
    return (
        isinstance(longitude, (int, float))
        and not isinstance(longitude, bool)
        and isinstance(latitude, (int, float))
        and not isinstance(latitude, bool)
        and math.isfinite(longitude)
        and math.isfinite(latitude)
        and -180 <= longitude <= 180
        and -90 <= latitude <= 90
    )


def _explicit_stop_coordinates(
    day: dict[str, Any],
    context: dict[str, Any],
) -> tuple[list[float] | None, str | None]:
    alignment = day.get("daily_stop_spine_alignment")
    if isinstance(alignment, dict):
        coordinates = alignment.get("waypoint_coordinates")
        if coordinates is not None:
            return coordinates, "overnight_reference_waypoint"

    coordinates, source = resolve_location(day, "stop", context)
    if source == "spine_interpolation":
        return None, None
    return coordinates, source


def _day_record(
    day: dict[str, Any],
    *,
    plan_id: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    day_number = day.get("day")
    base = {
        "day": day_number,
        "day_id": f"{plan_id}:day:{day_number}",
        "location_role": WEATHER_LOCATION_ROLE,
        "authority": WEATHER_LOCATION_AUTHORITY,
        "planned_stop": {
            "overlay_id": day.get("daily_stop_overlay_id"),
            "canonical_location": day.get("daily_stop_canonical_location"),
            "display_location": day.get("daily_stop_location"),
            "location_type": day.get("daily_stop_location_type"),
            "trail_mile": day.get("daily_stop_mile"),
        },
    }
    coordinates, source = _explicit_stop_coordinates(day, context)
    if not _valid_wgs84(coordinates):
        return {
            **base,
            "availability": "unavailable",
            "coordinates": None,
            "provenance": None,
            "unavailable_reason": (
                "no_authoritative_planned_stop_coordinates"
                if coordinates is None
                else "invalid_authoritative_planned_stop_coordinates"
            ),
        }

    longitude, latitude = coordinates[:2]
    return {
        **base,
        "availability": "available",
        "coordinates": {
            "latitude": latitude,
            "longitude": longitude,
            "coordinate_order": "latitude_longitude",
            "crs": WGS84_CRS,
        },
        "provenance": {
            "coordinate_source": source,
            "source_reference": (
                day.get("daily_stop_overlay_id")
                or day.get("daily_stop_canonical_location")
            ),
        },
        "unavailable_reason": None,
    }


def build_planned_day_weather_locations(
    daily_plan: list[dict[str, Any]],
    trail_root: Path | str,
    *,
    trail_id: str,
    direction: Any,
    trip_type: Any,
) -> dict[str, Any]:
    """Build the additive CairnOS-owned planned-stop coordinate contract."""
    plan_id = _plan_id(
        trail_id=trail_id,
        direction=direction,
        trip_type=trip_type,
        daily_plan=daily_plan,
    )
    context = coordinate_context(trail_root)
    return {
        "contract_version": WEATHER_LOCATION_CONTRACT_VERSION,
        "plan_id": plan_id,
        "trail_id": trail_id,
        "direction": direction,
        "location_semantic": WEATHER_LOCATION_ROLE,
        "coordinate_reference_system": WGS84_CRS,
        "days": [
            _day_record(row, plan_id=plan_id, context=context)
            for row in daily_plan
        ],
    }
