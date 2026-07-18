# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""Compose selected approach branches with canonical route-spine geometry."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping

from cairn.api.route_selection import (
    NONE_EGRESS_APPROACH_ID,
    NONE_INGRESS_APPROACH_ID,
    ROUTE_SELECTION_CONTRACT_VERSION,
)


APPROACH_GEOMETRY_SOURCE = "compiled/approach_trails.json"
SPINE_GEOMETRY_SOURCE = "compiled/spine.geojson"
DAILY_TRACK_GEOMETRY_MODE = "daily_track"
MAX_CONNECTION_GAP_MILES = 0.15
ELEVATION_UNIT = "m"


class RouteGeometryValidationError(ValueError):
    """Raised when selected route geometry cannot form a valid route."""


def load_spine_route_geometry(
    trail_root: Path | str,
) -> dict[str, Any]:
    """Load the compiled spine without discarding its source elevation."""

    path = Path(trail_root) / SPINE_GEOMETRY_SOURCE
    if not path.exists():
        return {
            "coordinates": [],
            "elevation": _unavailable_elevation(),
            "provenance": None,
        }
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    for feature in payload.get("features", []):
        geometry = feature.get("geometry", {})
        coordinates = _flatten_geometry(geometry)
        if not coordinates:
            continue
        properties = feature.get("properties", {})
        elevation = {
            "status": str(
                properties.get("elevation_status") or "unavailable"
            ),
            "unit": str(properties.get("elevation_unit") or ELEVATION_UNIT),
            "method": properties.get("elevation_method"),
            "coordinate_count": len(coordinates),
            "elevation_coordinate_count": sum(
                1 for coordinate in coordinates if _has_elevation(coordinate)
            ),
            "source_path": properties.get("source_path"),
        }
        return {
            "coordinates": coordinates,
            "elevation": elevation,
            "provenance": {
                "source_path": properties.get("source_path"),
                "source_kind": properties.get("source_kind"),
                "source_license_status": properties.get(
                    "source_license_status"
                ),
                "transformation_notes": (
                    "Longitude, latitude, and source-embedded GPX elevation "
                    "are retained in the compiled spine; GPX elevation is "
                    "expressed in meters."
                ),
            },
        }

    return {
        "coordinates": [],
        "elevation": _unavailable_elevation(),
        "provenance": None,
    }


def build_composed_route_geometry(
    daily_plan: list[dict[str, Any]],
    trail_root: Path | str,
    spine_coordinates: list[list[float]],
    total_miles: float | None,
    *,
    direction: str | None,
    route_selection: Mapping[str, Any] | None,
    spine_elevation: Mapping[str, Any] | None = None,
    spine_provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_direction = str(direction or "NOBO").upper()
    if normalized_direction not in {"NOBO", "SOBO"}:
        raise RouteGeometryValidationError(
            "Route GPX direction must be one of: NOBO, SOBO"
        )

    pieces: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if spine_coordinates and isinstance(total_miles, (int, float)):
        pieces.append({
            "role": "spine",
            "start_mile": 0.0,
            "end_mile": float(total_miles),
            "coordinates": _deduplicate_coordinates(spine_coordinates),
            "source": SPINE_GEOMETRY_SOURCE,
            "geometry_id": "defined_trail_spine",
            "approach_id": None,
            "connected_terminus": None,
            "connection_gap_miles": None,
            "elevation": dict(
                spine_elevation or _unavailable_elevation()
            ),
            "provenance": dict(spine_provenance or {}) or None,
        })

    normalized_selection = _normalize_selection(route_selection)
    catalog: dict[str, dict[str, str]] = {}
    if normalized_selection:
        approach_payload = _load_approach_payload(trail_root)
        catalog = _approach_catalog(approach_payload)
        geometry_by_approach_id = {
            geometry.get("approach_id"): geometry
            for geometry in approach_payload.get("approach_geometries", [])
            if geometry.get("approach_id")
        }
        for role in ("ingress", "egress"):
            approach_id = normalized_selection[f"{role}_approach_id"]
            sentinel_id = (
                NONE_INGRESS_APPROACH_ID
                if role == "ingress"
                else NONE_EGRESS_APPROACH_ID
            )
            if approach_id == sentinel_id:
                continue
            entry = catalog.get(approach_id)
            if entry is None:
                raise RouteGeometryValidationError(
                    f"Selected {role} approach_id is unknown: {approach_id}"
                )

            expected_terminus = _expected_terminus(
                normalized_direction,
                role,
            )
            actual_terminus = entry["connected_terminus"]
            if actual_terminus != expected_terminus:
                raise RouteGeometryValidationError(
                    f"Selected {role} approach_id {approach_id!r} is "
                    f"incompatible with {normalized_direction} {role}: "
                    f"expected connected_terminus {expected_terminus!r}, "
                    f"got {actual_terminus!r}"
                )

            geometry = geometry_by_approach_id.get(approach_id)
            if geometry is None:
                warnings.append(
                    _missing_selected_geometry_warning(role, approach_id)
                )
                continue
            if not spine_coordinates:
                warnings.append(
                    _missing_selected_geometry_connection_warning(
                        role,
                        approach_id,
                    )
                )
                continue

            pieces.append(
                _approach_piece(
                    geometry,
                    role=role,
                    expected_terminus=expected_terminus,
                    spine_coordinates=spine_coordinates,
                    total_miles=total_miles,
                )
            )

    full_start_mile, full_stop_mile = _full_route_bounds(
        daily_plan,
        normalized_direction,
        total_miles,
    )
    full_track, full_sources = _slice_pieces(
        pieces,
        full_start_mile,
        full_stop_mile,
    )
    full_coverage = _interval_coverage(
        pieces,
        full_start_mile,
        full_stop_mile,
    )

    daily_tracks: dict[Any, list[list[float]]] = {}
    daily_sources: dict[Any, list[dict[str, Any]]] = {}
    daily_coverage: dict[Any, dict[str, Any]] = {}
    for day in daily_plan:
        day_number = day.get("day")
        start_mile = _number(day.get("daily_start_mile"))
        stop_mile = _number(day.get("daily_stop_mile"))
        if start_mile is None or stop_mile is None or start_mile == stop_mile:
            daily_tracks[day_number] = []
            daily_sources[day_number] = []
            daily_coverage[day_number] = _interval_coverage(
                pieces,
                start_mile,
                stop_mile,
            )
            continue
        track, sources = _slice_pieces(
            pieces,
            start_mile,
            stop_mile,
        )
        daily_tracks[day_number] = track if len(track) >= 2 else []
        daily_sources[day_number] = sources if len(track) >= 2 else []
        daily_coverage[day_number] = _interval_coverage(
            pieces,
            start_mile,
            stop_mile,
        )

    return {
        "route_selection": normalized_selection,
        "route_parts": _selected_route_parts(
            pieces,
            normalized_selection,
            catalog,
        ),
        "full_track_points": full_track if len(full_track) >= 2 else [],
        "full_geometry_sources": full_sources,
        "full_coverage": full_coverage,
        "daily_track_points": daily_tracks,
        "daily_geometry_sources": daily_sources,
        "daily_coverage": daily_coverage,
        "warnings": warnings,
    }


def _normalize_selection(
    route_selection: Mapping[str, Any] | None,
) -> dict[str, str] | None:
    if route_selection is None:
        return None
    if not isinstance(route_selection, Mapping):
        raise RouteGeometryValidationError("route_selection must be an object")
    if route_selection.get("contract_version") != ROUTE_SELECTION_CONTRACT_VERSION:
        raise RouteGeometryValidationError(
            "route_selection.contract_version must be "
            f"{ROUTE_SELECTION_CONTRACT_VERSION!r}"
        )

    normalized = {"contract_version": ROUTE_SELECTION_CONTRACT_VERSION}
    for field_name in ("ingress_approach_id", "egress_approach_id"):
        value = route_selection.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise RouteGeometryValidationError(
                f"route_selection.{field_name} must be a non-empty string"
            )
        normalized[field_name] = value.strip()
    return normalized


def _load_approach_payload(trail_root: Path | str) -> dict[str, Any]:
    path = Path(trail_root) / APPROACH_GEOMETRY_SOURCE
    if not path.exists():
        raise RouteGeometryValidationError(
            "Selected route geometry requires compiled/approach_trails.json"
        )
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _approach_catalog(payload: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in payload.get("approach_trails", []):
        approach_id = str(row.get("approach_id") or "").strip()
        if approach_id:
            grouped.setdefault(approach_id, []).append(row)

    catalog: dict[str, dict[str, str]] = {}
    for approach_id, rows in grouped.items():
        names = {
            str(row.get("approach_name") or "").strip()
            for row in rows
            if str(row.get("approach_name") or "").strip()
        }
        termini = {
            str(
                row.get("connected_terminus")
                or row.get("terminus")
                or ""
            ).strip().lower()
            for row in rows
            if str(
                row.get("connected_terminus")
                or row.get("terminus")
                or ""
            ).strip()
        }
        if len(names) != 1 or len(termini) != 1:
            raise RouteGeometryValidationError(
                "Compiled approach metadata is inconsistent for approach_id: "
                f"{approach_id}"
            )
        catalog[approach_id] = {
            "approach_name": next(iter(names)),
            "connected_terminus": next(iter(termini)),
        }
    return catalog


def _expected_terminus(direction: str, role: str) -> str:
    if (direction, role) in {
        ("NOBO", "ingress"),
        ("SOBO", "egress"),
    }:
        return "southern"
    return "northern"


def _approach_piece(
    geometry: Mapping[str, Any],
    *,
    role: str,
    expected_terminus: str,
    spine_coordinates: list[list[float]],
    total_miles: float | None,
) -> dict[str, Any]:
    approach_id = str(geometry.get("approach_id") or "")
    coordinates = _flatten_geometry(geometry.get("geometry", {}))
    if len(coordinates) < 2:
        raise RouteGeometryValidationError(
            f"Selected {role} approach_id {approach_id!r} has no usable geometry"
        )

    spine_endpoint = (
        spine_coordinates[0]
        if expected_terminus == "southern"
        else spine_coordinates[-1]
    )
    first_gap = haversine_miles(coordinates[0], spine_endpoint)
    last_gap = haversine_miles(coordinates[-1], spine_endpoint)
    connection_gap = min(first_gap, last_gap)
    if connection_gap > MAX_CONNECTION_GAP_MILES:
        raise RouteGeometryValidationError(
            f"Selected {role} approach_id {approach_id!r} geometry is "
            f"disconnected from the {expected_terminus} defined-trail "
            f"terminus by {connection_gap:.3f} miles"
        )

    connected_at_first = first_gap <= last_gap
    should_connect_at_first = expected_terminus == "northern"
    if connected_at_first != should_connect_at_first:
        coordinates = list(reversed(coordinates))

    start_mile = _number(geometry.get("start_mile"))
    end_mile = _number(geometry.get("end_mile"))
    if start_mile is None or end_mile is None or start_mile >= end_mile:
        raise RouteGeometryValidationError(
            f"Selected {role} approach_id {approach_id!r} has invalid mileage bounds"
        )
    if expected_terminus == "southern" and abs(end_mile) > 0.15:
        raise RouteGeometryValidationError(
            f"Selected {role} approach_id {approach_id!r} has incompatible "
            "southern terminus mileage"
        )
    if (
        expected_terminus == "northern"
        and isinstance(total_miles, (int, float))
        and abs(start_mile - float(total_miles)) > 0.15
    ):
        raise RouteGeometryValidationError(
            f"Selected {role} approach_id {approach_id!r} has incompatible "
            "northern terminus mileage"
        )
    if expected_terminus == "southern":
        end_mile = 0.0
    elif isinstance(total_miles, (int, float)):
        start_mile = float(total_miles)

    return {
        "role": role,
        "start_mile": start_mile,
        "end_mile": end_mile,
        "coordinates": coordinates,
        "source": APPROACH_GEOMETRY_SOURCE,
        "geometry_id": geometry.get("geometry_id"),
        "approach_id": approach_id,
        "connected_terminus": expected_terminus,
        "connection_gap_miles": round(connection_gap, 4),
        "elevation": dict(
            geometry.get("elevation") or _unavailable_elevation()
        ),
        "provenance": geometry.get("provenance"),
    }


def _flatten_geometry(geometry: Mapping[str, Any]) -> list[list[float]]:
    geometry_type = geometry.get("type")
    raw_coordinates = geometry.get("coordinates", [])
    if geometry_type == "LineString":
        coordinates = raw_coordinates
    elif geometry_type == "MultiLineString":
        coordinates = [
            coordinate
            for line in raw_coordinates
            for coordinate in line
        ]
    else:
        return []
    return _deduplicate_coordinates(coordinates)


def _deduplicate_coordinates(
    coordinates: list[list[float]],
) -> list[list[float]]:
    deduplicated: list[list[float]] = []
    for coordinate in coordinates:
        if not _valid_coordinate(coordinate):
            continue
        normalized = [float(coordinate[0]), float(coordinate[1])]
        if _has_elevation(coordinate):
            normalized.append(float(coordinate[2]))
        if not deduplicated or normalized != deduplicated[-1]:
            deduplicated.append(normalized)
    return deduplicated


def _valid_coordinate(coordinate: Any) -> bool:
    return (
        isinstance(coordinate, (list, tuple))
        and len(coordinate) >= 2
        and all(
            isinstance(value, (int, float)) and math.isfinite(value)
            for value in coordinate[:2]
        )
    )


def _has_elevation(coordinate: Any) -> bool:
    return (
        isinstance(coordinate, (list, tuple))
        and len(coordinate) >= 3
        and isinstance(coordinate[2], (int, float))
        and not isinstance(coordinate[2], bool)
        and math.isfinite(coordinate[2])
    )


def _full_route_bounds(
    daily_plan: list[dict[str, Any]],
    direction: str,
    total_miles: float | None,
) -> tuple[float, float]:
    for day in daily_plan:
        start_mile = _number(day.get("daily_start_mile"))
        if start_mile is not None:
            break
    else:
        start_mile = 0.0 if direction == "NOBO" else float(total_miles or 0)

    for day in reversed(daily_plan):
        stop_mile = _number(day.get("daily_stop_mile"))
        if stop_mile is not None:
            break
    else:
        stop_mile = float(total_miles or 0) if direction == "NOBO" else 0.0

    return start_mile, stop_mile


def _slice_pieces(
    pieces: list[dict[str, Any]],
    start_mile: float,
    stop_mile: float,
) -> tuple[list[list[float]], list[dict[str, Any]]]:
    ascending = stop_mile >= start_mile
    ordered_pieces = sorted(
        pieces,
        key=lambda piece: piece["start_mile"],
        reverse=not ascending,
    )
    track: list[list[float]] = []
    sources: list[dict[str, Any]] = []
    requested_low = min(start_mile, stop_mile)
    requested_high = max(start_mile, stop_mile)

    for piece in ordered_pieces:
        overlap_low = max(requested_low, piece["start_mile"])
        overlap_high = min(requested_high, piece["end_mile"])
        if overlap_high <= overlap_low:
            continue
        span = piece["end_mile"] - piece["start_mile"]
        low_fraction = (overlap_low - piece["start_mile"]) / span
        high_fraction = (overlap_high - piece["start_mile"]) / span
        coordinates = _slice_line(
            piece["coordinates"],
            low_fraction,
            high_fraction,
        )
        if not ascending:
            coordinates.reverse()
        if not coordinates:
            continue

        point_start_index = len(track)
        if track and track[-1] == coordinates[0]:
            point_start_index -= 1
            coordinates = coordinates[1:]
        track.extend(coordinates)
        point_end_index = len(track) - 1
        source = {
            key: piece.get(key)
            for key in (
                "role",
                "source",
                "geometry_id",
                "approach_id",
                "connected_terminus",
                "connection_gap_miles",
                "elevation",
                "provenance",
            )
            if piece.get(key) is not None
        }
        source.update({
            "route_part_id": _route_part_id(piece),
            "start_mile": overlap_low if ascending else overlap_high,
            "end_mile": overlap_high if ascending else overlap_low,
            "canonical_min_mile": round(overlap_low, 1),
            "canonical_max_mile": round(overlap_high, 1),
            "point_start_index": point_start_index,
            "point_end_index": point_end_index,
            "point_count": point_end_index - point_start_index + 1,
        })
        emitted_part_points = track[
            point_start_index:point_end_index + 1
        ]
        emitted_elevation = dict(source.get("elevation") or {})
        emitted_elevation_count = sum(
            1
            for coordinate in emitted_part_points
            if _has_elevation(coordinate)
        )
        emitted_elevation.update({
            "status": (
                "complete"
                if emitted_part_points
                and emitted_elevation_count == len(emitted_part_points)
                else "unavailable"
            ),
            "unit": str(
                emitted_elevation.get("unit") or ELEVATION_UNIT
            ),
            "coordinate_count": len(emitted_part_points),
            "elevation_coordinate_count": emitted_elevation_count,
        })
        source["elevation"] = emitted_elevation
        sources.append(source)

    return track, sources


def _slice_line(
    coordinates: list[list[float]],
    start_fraction: float,
    end_fraction: float,
) -> list[list[float]]:
    if len(coordinates) < 2:
        return []
    start_fraction = max(0.0, min(1.0, start_fraction))
    end_fraction = max(0.0, min(1.0, end_fraction))
    if end_fraction <= start_fraction:
        return []

    segment_lengths = [
        haversine_miles(start, end)
        for start, end in zip(coordinates, coordinates[1:])
    ]
    total_length = sum(segment_lengths)
    if total_length <= 0:
        return []

    start_distance = start_fraction * total_length
    end_distance = end_fraction * total_length
    result = [_coordinate_at_distance(
        coordinates,
        segment_lengths,
        start_distance,
    )]
    traversed = 0.0
    for index, segment_length in enumerate(segment_lengths):
        traversed += segment_length
        if start_distance < traversed < end_distance:
            result.append(coordinates[index + 1][:3])
    result.append(_coordinate_at_distance(
        coordinates,
        segment_lengths,
        end_distance,
    ))
    return _deduplicate_coordinates(result)


def _coordinate_at_distance(
    coordinates: list[list[float]],
    segment_lengths: list[float],
    target_distance: float,
) -> list[float]:
    if target_distance <= 0:
        return coordinates[0][:3]
    traversed = 0.0
    for index, segment_length in enumerate(segment_lengths):
        if traversed + segment_length >= target_distance:
            if segment_length <= 0:
                return coordinates[index][:3]
            ratio = (target_distance - traversed) / segment_length
            start = coordinates[index]
            end = coordinates[index + 1]
            result = [
                start[0] + (end[0] - start[0]) * ratio,
                start[1] + (end[1] - start[1]) * ratio,
            ]
            if _has_elevation(start) and _has_elevation(end):
                result.append(
                    start[2] + (end[2] - start[2]) * ratio
                )
            return result
        traversed += segment_length
    return coordinates[-1][:3]


def _interval_coverage(
    pieces: list[dict[str, Any]],
    start_mile: float | None,
    stop_mile: float | None,
) -> dict[str, Any]:
    if start_mile is None or stop_mile is None:
        return {
            "requested_start_mile": start_mile,
            "requested_stop_mile": stop_mile,
            "requested_distance_miles": None,
            "covered_distance_miles": 0.0,
            "coverage_fraction": 0.0,
            "geometry_complete": False,
            "uncovered_intervals": [],
        }
    if start_mile == stop_mile:
        return {
            "requested_start_mile": start_mile,
            "requested_stop_mile": stop_mile,
            "requested_distance_miles": 0.0,
            "covered_distance_miles": 0.0,
            "coverage_fraction": 1.0,
            "geometry_complete": True,
            "uncovered_intervals": [],
        }

    ascending = stop_mile > start_mile
    requested_low = min(start_mile, stop_mile)
    requested_high = max(start_mile, stop_mile)
    intervals = sorted(
        (
            max(requested_low, float(piece["start_mile"])),
            min(requested_high, float(piece["end_mile"])),
        )
        for piece in pieces
        if min(requested_high, float(piece["end_mile"]))
        > max(requested_low, float(piece["start_mile"]))
    )
    merged: list[list[float]] = []
    for low, high in intervals:
        if not merged or low > merged[-1][1] + 1e-9:
            merged.append([low, high])
        else:
            merged[-1][1] = max(merged[-1][1], high)

    uncovered: list[list[float]] = []
    cursor = requested_low
    for low, high in merged:
        if low > cursor + 1e-9:
            uncovered.append([cursor, low])
        cursor = max(cursor, high)
    if cursor < requested_high - 1e-9:
        uncovered.append([cursor, requested_high])

    requested_distance = requested_high - requested_low
    covered_distance = sum(high - low for low, high in merged)
    if not ascending:
        uncovered = [[high, low] for low, high in reversed(uncovered)]

    return {
        "requested_start_mile": start_mile,
        "requested_stop_mile": stop_mile,
        "requested_distance_miles": round(requested_distance, 3),
        "covered_distance_miles": round(covered_distance, 3),
        "coverage_fraction": round(
            covered_distance / requested_distance,
            6,
        ),
        "geometry_complete": not uncovered,
        "uncovered_intervals": [
            {
                "start_mile": round(low, 3),
                "stop_mile": round(high, 3),
            }
            for low, high in uncovered
        ],
    }


def _selected_route_parts(
    pieces: list[dict[str, Any]],
    route_selection: Mapping[str, str] | None,
    catalog: Mapping[str, Mapping[str, str]],
) -> list[dict[str, Any]]:
    spine_piece = next(
        (piece for piece in pieces if piece.get("role") == "spine"),
        None,
    )
    ordered: list[tuple[str, dict[str, Any] | None, str | None]] = []
    if route_selection:
        ingress_id = route_selection["ingress_approach_id"]
        egress_id = route_selection["egress_approach_id"]
        if ingress_id != NONE_INGRESS_APPROACH_ID:
            ordered.append((
                "ingress",
                next(
                    (
                        piece
                        for piece in pieces
                        if piece.get("role") == "ingress"
                        and piece.get("approach_id") == ingress_id
                    ),
                    None,
                ),
                ingress_id,
            ))
    ordered.append(("spine", spine_piece, None))
    if route_selection and egress_id != NONE_EGRESS_APPROACH_ID:
        ordered.append((
            "egress",
            next(
                (
                    piece
                    for piece in pieces
                    if piece.get("role") == "egress"
                    and piece.get("approach_id") == egress_id
                ),
                None,
            ),
            egress_id,
        ))

    route_parts = []
    for order, (role, piece, approach_id) in enumerate(ordered):
        if piece:
            elevation = _verified_piece_elevation(piece)
            route_parts.append({
                "order": order,
                "route_part_id": _route_part_id(piece),
                "role": role,
                "approach_id": piece.get("approach_id"),
                "geometry_id": piece.get("geometry_id"),
                "geometry_status": "available",
                "start_mile": piece.get("start_mile"),
                "end_mile": piece.get("end_mile"),
                "point_count": len(piece.get("coordinates", [])),
                "source": piece.get("source"),
                "elevation": elevation,
                "provenance": piece.get("provenance"),
            })
            continue

        catalog_entry = catalog.get(str(approach_id or ""), {})
        route_parts.append({
            "order": order,
            "route_part_id": (
                f"{role}:{approach_id}"
                if approach_id
                else "spine:defined_trail_spine"
            ),
            "role": role,
            "approach_id": approach_id,
            "geometry_id": (
                "defined_trail_spine" if role == "spine" else None
            ),
            "geometry_status": "unavailable",
            "approach_name": catalog_entry.get("approach_name"),
            "connected_terminus": catalog_entry.get("connected_terminus"),
            "point_count": 0,
            "source": (
                SPINE_GEOMETRY_SOURCE
                if role == "spine"
                else APPROACH_GEOMETRY_SOURCE
            ),
            "elevation": _unavailable_elevation(),
            "provenance": None,
        })
    return route_parts


def _verified_piece_elevation(
    piece: Mapping[str, Any],
) -> dict[str, Any]:
    coordinates = piece.get("coordinates", [])
    elevation_coordinate_count = sum(
        1 for coordinate in coordinates if _has_elevation(coordinate)
    )
    elevation = dict(piece.get("elevation") or {})
    elevation.update({
        "status": (
            "complete"
            if coordinates and elevation_coordinate_count == len(coordinates)
            else "unavailable"
        ),
        "unit": str(elevation.get("unit") or ELEVATION_UNIT),
        "coordinate_count": len(coordinates),
        "elevation_coordinate_count": elevation_coordinate_count,
    })
    return elevation


def _route_part_id(piece: Mapping[str, Any]) -> str:
    role = str(piece.get("role") or "route_part")
    identity = (
        piece.get("approach_id")
        or piece.get("geometry_id")
        or "unknown"
    )
    return f"{role}:{identity}"


def _unavailable_elevation() -> dict[str, Any]:
    return {
        "status": "unavailable",
        "unit": ELEVATION_UNIT,
        "method": None,
        "coordinate_count": 0,
        "elevation_coordinate_count": 0,
    }


def haversine_miles(first: list[float], second: list[float]) -> float:
    earth_radius_miles = 3958.7613
    first_latitude = math.radians(first[1])
    second_latitude = math.radians(second[1])
    latitude_delta = second_latitude - first_latitude
    longitude_delta = math.radians(second[0] - first[0])
    value = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(first_latitude)
        * math.cos(second_latitude)
        * math.sin(longitude_delta / 2) ** 2
    )
    return earth_radius_miles * 2 * math.asin(math.sqrt(value))


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value):
        return None
    return float(value)


def _missing_selected_geometry_warning(
    role: str,
    approach_id: str,
) -> dict[str, Any]:
    return {
        "code": "selected_route_geometry_unavailable",
        "severity": "warning",
        "role": role,
        "approach_id": approach_id,
        "message": (
            f"The selected {role} approach_id {approach_id!r} has no "
            "promoted geometry; no other approach geometry was substituted."
        ),
    }


def _missing_selected_geometry_connection_warning(
    role: str,
    approach_id: str,
) -> dict[str, Any]:
    return {
        "code": "selected_route_geometry_not_composed",
        "severity": "warning",
        "role": role,
        "approach_id": approach_id,
        "message": (
            f"The selected {role} approach_id {approach_id!r} could not be "
            "connected because the defined-trail spine is unavailable."
        ),
    }
