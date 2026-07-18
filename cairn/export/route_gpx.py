# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""GPX route artifacts for downstream imports."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from cairn.export.gaia_geojson import (
    build_overlay_lookup,
    build_waypoint_lookup,
    load_crossing_reference,
    load_overlay_nodes,
    load_resupply_access_reference,
    load_spine_coordinates,
    load_waypoint_reference,
    resolve_day_coordinates,
    total_overlay_miles,
)
from cairn.export.plan_json import (
    slugify,
    utc_timestamp,
)
from cairn.export.route_elevation import (
    ELEVATION_UNIT,
    elevation_profile,
    normalize_track_points,
    track_metrics,
)
from cairn.export.route_geometry import (
    APPROACH_GEOMETRY_SOURCE,
    DAILY_TRACK_GEOMETRY_MODE,
    SPINE_GEOMETRY_SOURCE,
    build_composed_route_geometry,
    load_spine_route_geometry,
)


ROUTE_GPX_EXPORT_VERSION = "cairnos_route_gpx_v4"
GPX_GEOMETRY_MODE = "full_plan_track"
WAYPOINT_ONLY_GEOMETRY_MODE = "waypoint_only"
GPX_MEDIA_TYPE = "application/gpx+xml"
GPX_NAMESPACE = "http://www.topografix.com/GPX/1/1"
CAIRNOS_NAMESPACE = "https://cairnos.local/ns/route-gpx/1"


WAYPOINT_ONLY_WARNING = {
    "code": "waypoint_only_gpx",
    "severity": "warning",
    "message": (
        "CairnOS per-day GPX artifacts contain planned daily start/stop "
        "waypoints only. Daily route geometry has not been sliced."
    ),
}


FULL_PLAN_SPINE_WARNING = {
    "code": "full_plan_spine_only",
    "severity": "warning",
    "message": (
        "The full-plan GPX track contains the compiled Long Trail spine "
        "only. It does not include selected ingress or egress branches, "
        "off-spine overnight access, or per-day route slicing."
    ),
}


MISSING_SPINE_WARNING = {
    "code": "missing_route_spine_geometry",
    "severity": "warning",
    "message": (
        "The compiled Long Trail spine did not contain usable route "
        "geometry, so the full-plan GPX is waypoint-only."
    ),
}


VERIFY_OFFICIAL_SOURCES_WARNING = {
    "code": "verify_official_sources",
    "severity": "warning",
    "message": (
        "Verify routes, services, closures, weather, water, and "
        "backcountry decisions with official/current sources."
    ),
}


ET.register_namespace(
    "",
    GPX_NAMESPACE,
)
ET.register_namespace(
    "cairnos",
    CAIRNOS_NAMESPACE,
)


def namespaced(
    namespace: str,
    tag: str,
) -> str:
    return f"{{{namespace}}}{tag}"


def gpx_tag(tag: str) -> str:
    return namespaced(
        GPX_NAMESPACE,
        tag,
    )


def cairnos_tag(tag: str) -> str:
    return namespaced(
        CAIRNOS_NAMESPACE,
        tag,
    )


def coordinate_context(
    trail_root: Path | str,
) -> dict[str, Any]:
    overlay_nodes = load_overlay_nodes(
        trail_root
    )
    waypoints = load_waypoint_reference(
        trail_root
    )

    spine_coordinates = load_spine_coordinates(
        trail_root
    )
    spine_route_geometry = load_spine_route_geometry(
        trail_root
    )

    return {
        "access_references": load_resupply_access_reference(
            trail_root
        ),
        "waypoint_lookup": build_waypoint_lookup(
            waypoints
        ),
        "crossing_references": load_crossing_reference(
            trail_root
        ),
        "overlay_lookup": build_overlay_lookup(
            overlay_nodes
        ),
        "overlay_nodes": overlay_nodes,
        "spine_coordinates": spine_coordinates,
        "route_spine_coordinates": (
            spine_route_geometry["coordinates"]
            if spine_coordinates
            else []
        ),
        "route_spine_elevation": spine_route_geometry["elevation"],
        "route_spine_provenance": spine_route_geometry["provenance"],
        "total_miles": total_overlay_miles(
            overlay_nodes
        ),
    }


def directional_spine_coordinates(
    coordinates: list[list[float]],
    direction: str | None,
) -> list[list[float]]:
    if str(direction or "").upper() == "SOBO":
        return list(
            reversed(coordinates)
        )

    return list(coordinates)


def location_record(
    day: dict[str, Any],
    position: str,
) -> dict[str, Any]:
    prefix = f"daily_{position}"

    return {
        "day": day.get("day"),
        "division": day.get("division"),
        "daily_stop_mile": day.get(
            f"{prefix}_mile"
        ),
        "daily_stop_location": day.get(
            f"{prefix}_location"
        ),
        "daily_stop_canonical_location": day.get(
            f"{prefix}_canonical_location"
        ),
        "daily_stop_access_notes": day.get(
            f"{prefix}_access_notes"
        ),
        "daily_stop_location_type": day.get(
            f"{prefix}_location_type"
        ),
        "daily_miles": day.get("daily_miles"),
        "daily_elevation_gain": day.get(
            "daily_elevation_gain"
        ),
        "notes": day.get("notes"),
    }


def resolve_location(
    day: dict[str, Any],
    position: str,
    context: dict[str, Any],
) -> tuple[list[float] | None, str | None]:
    coordinates, source, _ = resolve_day_coordinates(
        location_record(
            day,
            position,
        ),
        context["access_references"],
        context["waypoint_lookup"],
        context["crossing_references"],
        context["overlay_lookup"],
        context["overlay_nodes"],
        context["spine_coordinates"],
        context["total_miles"],
    )

    return coordinates, source


def waypoint_name(
    day: dict[str, Any],
    position: str,
) -> str:
    day_number = day.get(
        "day"
    )
    location = (
        day.get(f"daily_{position}_location")
        or "Unknown Location"
    )

    return (
        f"Day {format_day_label(day_number)} "
        f"{position} - {location}"
    )


def format_day_label(
    day_number: Any,
) -> str:
    try:
        return f"{int(day_number):03d}"
    except (TypeError, ValueError):
        return str(
            day_number or "unknown"
        )


def build_missing_coordinate_warning(
    day: dict[str, Any],
    position: str,
) -> dict[str, Any]:
    location = day.get(
        f"daily_{position}_location"
    )
    mile = day.get(
        f"daily_{position}_mile"
    )

    return {
        "code": "missing_waypoint_coordinates",
        "severity": "warning",
        "day": day.get("day"),
        "position": position,
        "location": location,
        "mile": mile,
        "message": (
            "Waypoint coordinates could not be resolved from "
            "resupply access data, Gaia waypoint reference, crossing "
            "reference, route overlay, or spine interpolation."
        ),
    }


def build_waypoint(
    day: dict[str, Any],
    position: str,
    coordinates: list[float],
    coordinate_source: str | None,
) -> dict[str, Any]:
    return {
        "name": waypoint_name(
            day,
            position,
        ),
        "day": day.get("day"),
        "position": position,
        "division": day.get("division"),
        "location": day.get(
            f"daily_{position}_location"
        ),
        "canonical_location": day.get(
            f"daily_{position}_canonical_location"
        ),
        "access_notes": day.get(
            f"daily_{position}_access_notes"
        ),
        "location_type": day.get(
            f"daily_{position}_location_type"
        ),
        "mile": day.get(
            f"daily_{position}_mile"
        ),
        "daily_miles": day.get("daily_miles"),
        "coordinate_source": coordinate_source,
        "coordinates": coordinates[:2],
    }


def build_daily_waypoints(
    daily_plan: list[dict[str, Any]],
    context: dict[str, Any],
) -> tuple[
    list[dict[str, Any]],
    dict[int, list[dict[str, Any]]],
    list[dict[str, Any]],
]:
    waypoints = []
    waypoints_by_day = {}
    warnings = []

    for day in daily_plan:
        day_waypoints = []

        for position in [
            "start",
            "stop",
        ]:
            coordinates, source = resolve_location(
                day,
                position,
                context,
            )

            if coordinates is None:
                warnings.append(
                    build_missing_coordinate_warning(
                        day,
                        position,
                    )
                )
                continue

            waypoint = build_waypoint(
                day,
                position,
                coordinates,
                source,
            )
            waypoints.append(waypoint)
            day_waypoints.append(waypoint)

        waypoints_by_day[
            day.get("day")
        ] = day_waypoints

    return waypoints, waypoints_by_day, warnings


def warning_codes(
    warnings: list[dict[str, Any]],
) -> list[str]:
    return sorted({
        str(warning.get("code"))
        for warning in warnings
        if warning.get("code")
    })


def build_route_geometry_incomplete_warning(
    coverage: dict[str, Any],
    day: Any = None,
) -> dict[str, Any]:
    warning = {
        "code": "route_geometry_incomplete",
        "severity": "warning",
        "message": (
            "The emitted GPX track does not cover the complete planned "
            "mileage interval because selected authoritative route geometry "
            "is unavailable."
        ),
        "geometry_coverage": coverage,
    }
    if day is not None:
        warning["day"] = day
    return warning


def build_authoritative_elevation_unavailable_warning(
    track_points: list[list[float]],
    coverage: dict[str, Any],
    day: Any = None,
) -> dict[str, Any] | None:
    profile = elevation_profile(track_points)
    if not track_points:
        return None
    if (
        coverage.get("geometry_complete")
        and profile["status"] == "complete"
    ):
        return None
    reason = (
        "route_geometry_incomplete"
        if not coverage.get("geometry_complete")
        else "track_points_missing_source_elevation"
    )
    warning = {
        "code": "authoritative_route_elevation_unavailable",
        "severity": "warning",
        "reason": reason,
        "message": (
            "A complete authoritative elevation profile is unavailable for "
            "this planned interval. CairnOS did not fill the gap with an "
            "estimated or unrelated elevation source."
        ),
        "elevation": profile,
    }
    if day is not None:
        warning["day"] = day
    return warning


def artifact_contract_warnings(
    track_points: list[list[float]],
    coverage: dict[str, Any],
    day: Any = None,
) -> list[dict[str, Any]]:
    warnings = []
    if (
        coverage.get("requested_distance_miles") not in (None, 0, 0.0)
        and not coverage.get("geometry_complete")
    ):
        warnings.append(
            build_route_geometry_incomplete_warning(coverage, day)
        )
    elevation_warning = build_authoritative_elevation_unavailable_warning(
        track_points,
        coverage,
        day,
    )
    if elevation_warning:
        warnings.append(elevation_warning)
    return warnings


def route_completeness(
    route_parts: list[dict[str, Any]],
    coverage: dict[str, Any],
    track_points: list[list[float]],
) -> dict[str, Any]:
    profile = elevation_profile(track_points)
    unavailable = [
        part["route_part_id"]
        for part in route_parts
        if part.get("geometry_status") != "available"
        or part.get("elevation", {}).get("status") != "complete"
    ]
    return {
        "geometry_complete": bool(coverage.get("geometry_complete")),
        "elevation_complete": bool(
            coverage.get("geometry_complete")
            and profile["status"] == "complete"
        ),
        "selected_route_part_count": len(route_parts),
        "geometry_available_part_count": sum(
            1
            for part in route_parts
            if part.get("geometry_status") == "available"
        ),
        "elevation_complete_part_count": sum(
            1
            for part in route_parts
            if part.get("elevation", {}).get("status") == "complete"
        ),
        "unavailable_route_part_ids": unavailable,
        "geometry_coverage": coverage,
        "track_elevation": profile,
    }


def artifact_filename(
    trail_id: str,
    direction: str | None,
    artifact_id: str,
) -> str:
    parts = [
        "cairnos_route",
        slugify(trail_id),
    ]

    if direction:
        parts.append(
            slugify(direction.lower())
        )

    parts.append(
        slugify(artifact_id)
    )

    return "_".join(parts) + ".gpx"


def build_manifest_entry(
    artifact_id: str,
    filename: str,
    scope: str,
    waypoints: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    geometry_mode: str,
    track_points: list[list[float]] | None = None,
    geometry_sources: list[dict[str, Any]] | None = None,
    geometry_coverage: dict[str, Any] | None = None,
    day: dict[str, Any] | None = None,
) -> dict[str, Any]:
    track_points = track_points or []
    geometry_sources = geometry_sources or []
    geometry_coverage = geometry_coverage or {}
    profile = elevation_profile(track_points)
    entry = {
        "artifact_id": artifact_id,
        "filename": filename,
        "scope": scope,
        "media_type": GPX_MEDIA_TYPE,
        "export_version": ROUTE_GPX_EXPORT_VERSION,
        "geometry_mode": geometry_mode,
        "waypoint_count": len(waypoints),
        "track_count": 1 if track_points else 0,
        "track_segment_count": 1 if track_points else 0,
        "track_point_count": len(track_points),
        "elevation": profile,
        "metrics": track_metrics(track_points),
        "geometry_coverage": geometry_coverage,
        "route_elevation_complete": bool(
            geometry_coverage.get("geometry_complete")
            and profile["status"] == "complete"
        ),
        "warning_codes": warning_codes(warnings),
    }

    if track_points:
        entry["geometry_source"] = (
            "composed_selected_route"
            if any(
                source.get("source") == APPROACH_GEOMETRY_SOURCE
                for source in geometry_sources
            )
            else SPINE_GEOMETRY_SOURCE
        )
        entry["geometry_sources"] = geometry_sources

    if day:
        entry.update({
            "day": day.get("day"),
            "division": day.get("division"),
            "daily_start_mile": day.get(
                "daily_start_mile"
            ),
            "daily_stop_mile": day.get(
                "daily_stop_mile"
            ),
            "daily_miles": day.get(
                "daily_miles"
            ),
            "daily_start_location": day.get(
                "daily_start_location"
            ),
            "daily_stop_location": day.get(
                "daily_stop_location"
            ),
        })

    return entry


def format_coordinate(
    value: float,
) -> str:
    return (
        f"{float(value):.8f}"
        .rstrip("0")
        .rstrip(".")
    )


def format_elevation(
    value: float,
) -> str:
    return (
        f"{float(value):.3f}"
        .rstrip("0")
        .rstrip(".")
    )


def add_text(
    parent: ET.Element,
    tag: str,
    value: Any,
) -> None:
    if value is None:
        return

    element = ET.SubElement(
        parent,
        tag,
    )
    element.text = str(value)


def add_cairnos_extension(
    parent: ET.Element,
    tag: str,
    value: Any,
) -> None:
    add_text(
        parent,
        cairnos_tag(tag),
        value,
    )


def waypoint_description(
    waypoint: dict[str, Any],
) -> str:
    parts = [
        "CairnOS planned-route GPX waypoint.",
        f"Planned {waypoint['position']} waypoint",
    ]

    if waypoint.get("mile") is not None:
        parts.append(
            f"at mile {waypoint['mile']}"
        )

    if waypoint.get("coordinate_source"):
        parts.append(
            "resolved from "
            f"{waypoint['coordinate_source']}"
        )

    return "; ".join(parts) + "."


def add_waypoint_element(
    root: ET.Element,
    waypoint: dict[str, Any],
) -> None:
    longitude, latitude = waypoint[
        "coordinates"
    ]
    element = ET.SubElement(
        root,
        gpx_tag("wpt"),
        {
            "lat": format_coordinate(
                latitude
            ),
            "lon": format_coordinate(
                longitude
            ),
        },
    )

    add_text(
        element,
        gpx_tag("name"),
        waypoint.get("name"),
    )
    add_text(
        element,
        gpx_tag("desc"),
        waypoint_description(
            waypoint
        ),
    )
    add_text(
        element,
        gpx_tag("type"),
        waypoint.get("location_type"),
    )

    extensions = ET.SubElement(
        element,
        gpx_tag("extensions"),
    )
    add_cairnos_extension(
        extensions,
        "day",
        waypoint.get("day"),
    )
    add_cairnos_extension(
        extensions,
        "position",
        waypoint.get("position"),
    )
    add_cairnos_extension(
        extensions,
        "division",
        waypoint.get("division"),
    )
    add_cairnos_extension(
        extensions,
        "mile",
        waypoint.get("mile"),
    )
    add_cairnos_extension(
        extensions,
        "location",
        waypoint.get("location"),
    )
    add_cairnos_extension(
        extensions,
        "canonical_location",
        waypoint.get("canonical_location"),
    )
    add_cairnos_extension(
        extensions,
        "access_notes",
        waypoint.get("access_notes"),
    )
    add_cairnos_extension(
        extensions,
        "coordinate_source",
        waypoint.get("coordinate_source"),
    )


def track_description(
    geometry_sources: list[dict[str, Any]],
) -> str:
    if any(
        source.get("source") == APPROACH_GEOMETRY_SOURCE
        for source in geometry_sources
    ):
        return (
            "CairnOS selected-route geometry composed from promoted "
            "approach branches and the canonical defined-trail spine."
        )
    return "CairnOS canonical defined-trail spine geometry."


def add_track_contract_extensions(
    extensions: ET.Element,
    geometry_sources: list[dict[str, Any]],
    geometry_coverage: dict[str, Any],
    profile: dict[str, Any],
    metrics: dict[str, Any],
) -> None:
    add_cairnos_extension(
        extensions,
        "geometry_complete",
        str(bool(geometry_coverage.get("geometry_complete"))).lower(),
    )
    add_cairnos_extension(
        extensions,
        "elevation_status",
        profile.get("status"),
    )
    add_cairnos_extension(
        extensions,
        "elevation_unit",
        profile.get("unit"),
    )
    for field_name in (
        "length_m",
        "total_ascent_m",
        "total_descent_m",
        "average_grade_percent",
    ):
        add_cairnos_extension(
            extensions,
            field_name,
            metrics.get(field_name),
        )

    route_parts = ET.SubElement(
        extensions,
        cairnos_tag("route_parts"),
    )
    for source in geometry_sources:
        route_part = ET.SubElement(
            route_parts,
            cairnos_tag("route_part"),
            {
                "id": str(source.get("route_part_id") or "unknown"),
                "role": str(source.get("role") or "unknown"),
                "point_start_index": str(source.get("point_start_index")),
                "point_end_index": str(source.get("point_end_index")),
            },
        )
        for field_name in (
            "source",
            "geometry_id",
            "approach_id",
            "start_mile",
            "end_mile",
        ):
            add_cairnos_extension(
                route_part,
                field_name,
                source.get(field_name),
            )
        add_cairnos_extension(
            route_part,
            "elevation_status",
            source.get("elevation", {}).get("status"),
        )
        provenance = source.get("provenance") or {}
        for field_name in (
            "source_path",
            "source_feature_id",
            "source_license_status",
        ):
            add_cairnos_extension(
                route_part,
                field_name,
                provenance.get(field_name),
            )


def add_track_element(
    root: ET.Element,
    name: str,
    coordinates: list[list[float]],
    direction: str | None,
    geometry_sources: list[dict[str, Any]] | None = None,
    route_selection: dict[str, str] | None = None,
    geometry_coverage: dict[str, Any] | None = None,
    profile: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
) -> None:
    if not coordinates:
        return

    track = ET.SubElement(
        root,
        gpx_tag("trk"),
    )
    add_text(
        track,
        gpx_tag("name"),
        name,
    )
    add_text(
        track,
        gpx_tag("desc"),
        track_description(geometry_sources or []),
    )
    add_text(
        track,
        gpx_tag("type"),
        "CairnOS selected route",
    )
    extensions = ET.SubElement(
        track,
        gpx_tag("extensions"),
    )
    add_cairnos_extension(
        extensions,
        "geometry_source",
        (
            "composed_selected_route"
            if any(
                source.get("source") == APPROACH_GEOMETRY_SOURCE
                for source in (geometry_sources or [])
            )
            else SPINE_GEOMETRY_SOURCE
        ),
    )
    add_cairnos_extension(
        extensions,
        "direction",
        direction,
    )
    if route_selection:
        add_cairnos_extension(
            extensions,
            "ingress_approach_id",
            route_selection.get("ingress_approach_id"),
        )
        add_cairnos_extension(
            extensions,
            "egress_approach_id",
            route_selection.get("egress_approach_id"),
        )
    add_track_contract_extensions(
        extensions,
        geometry_sources or [],
        geometry_coverage or {},
        profile or elevation_profile(coordinates),
        metrics or track_metrics(coordinates),
    )
    segment = ET.SubElement(
        track,
        gpx_tag("trkseg"),
    )

    for coordinate in coordinates:
        longitude, latitude = coordinate[:2]
        track_point = ET.SubElement(
            segment,
            gpx_tag("trkpt"),
            {
                "lat": format_coordinate(
                    latitude
                ),
                "lon": format_coordinate(
                    longitude
                ),
            },
        )
        if len(coordinate) >= 3:
            add_text(
                track_point,
                gpx_tag("ele"),
                format_elevation(coordinate[2]),
            )


def build_gpx_document(
    name: str,
    waypoints: list[dict[str, Any]],
    generated_at: str,
    trail_id: str,
    geometry_mode: str,
    track_points: list[list[float]] | None = None,
    direction: str | None = None,
    metadata_warning: str | None = None,
    geometry_sources: list[dict[str, Any]] | None = None,
    route_selection: dict[str, str] | None = None,
    geometry_coverage: dict[str, Any] | None = None,
) -> str:
    track_points = track_points or []
    geometry_coverage = geometry_coverage or {}
    profile = elevation_profile(track_points)
    metrics = track_metrics(track_points)
    root = ET.Element(
        gpx_tag("gpx"),
        {
            "version": "1.1",
            "creator": "CairnOS",
        },
    )
    metadata = ET.SubElement(
        root,
        gpx_tag("metadata"),
    )
    add_text(
        metadata,
        gpx_tag("name"),
        name,
    )
    add_text(
        metadata,
        gpx_tag("time"),
        gpx_timestamp(
            generated_at
        ),
    )
    metadata_extensions = ET.SubElement(
        metadata,
        gpx_tag("extensions"),
    )
    add_cairnos_extension(
        metadata_extensions,
        "export_version",
        ROUTE_GPX_EXPORT_VERSION,
    )
    add_cairnos_extension(
        metadata_extensions,
        "geometry_mode",
        geometry_mode,
    )
    add_cairnos_extension(
        metadata_extensions,
        "trail_id",
        trail_id,
    )
    add_cairnos_extension(
        metadata_extensions,
        "elevation_status",
        profile.get("status"),
    )
    add_cairnos_extension(
        metadata_extensions,
        "elevation_unit",
        ELEVATION_UNIT,
    )
    add_cairnos_extension(
        metadata_extensions,
        "geometry_complete",
        str(bool(geometry_coverage.get("geometry_complete"))).lower(),
    )
    add_cairnos_extension(
        metadata_extensions,
        "warning",
        metadata_warning,
    )

    for waypoint in waypoints:
        add_waypoint_element(
            root,
            waypoint,
        )

    add_track_element(
        root,
        f"{name} route",
        track_points,
        direction,
        geometry_sources,
        route_selection,
        geometry_coverage,
        profile,
        metrics,
    )

    ET.indent(
        root,
        space="  ",
    )

    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        + ET.tostring(
            root,
            encoding="unicode",
        )
        + "\n"
    )


def build_route_gpx_artifacts(
    daily_plan: list[dict[str, Any]],
    trail_root: Path | str,
    direction: str | None = None,
    trail_id: str | None = None,
    generated_at: str | None = None,
    route_selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    trail_root = Path(
        trail_root
    )
    trail_id = trail_id or trail_root.name
    generated_at = generated_at or utc_timestamp()
    context = coordinate_context(
        trail_root
    )
    geometry = build_composed_route_geometry(
        daily_plan,
        trail_root,
        context["route_spine_coordinates"],
        context["total_miles"],
        direction=direction,
        route_selection=route_selection,
        spine_elevation=context["route_spine_elevation"],
        spine_provenance=context["route_spine_provenance"],
    )
    track_points = normalize_track_points(
        geometry["full_track_points"]
    )
    full_geometry_sources = geometry["full_geometry_sources"]
    daily_track_points = {
        day: normalize_track_points(points)
        for day, points in geometry["daily_track_points"].items()
    }
    daily_geometry_sources = geometry["daily_geometry_sources"]
    full_geometry_mode = (
        GPX_GEOMETRY_MODE
        if track_points
        else WAYPOINT_ONLY_GEOMETRY_MODE
    )
    all_waypoints, waypoints_by_day, missing_warnings = (
        build_daily_waypoints(
            daily_plan,
            context,
        )
    )

    has_approach_geometry = any(
        source.get("source") == APPROACH_GEOMETRY_SOURCE
        for source in full_geometry_sources
    )
    spine_warnings = []
    if not track_points:
        spine_warnings.append(dict(MISSING_SPINE_WARNING))
    elif not has_approach_geometry:
        spine_warnings.append(dict(FULL_PLAN_SPINE_WARNING))
    full_contract_warnings = artifact_contract_warnings(
        track_points,
        geometry["full_coverage"],
    )
    daily_contract_warnings = {
        day.get("day"): artifact_contract_warnings(
            daily_track_points.get(day.get("day"), []),
            geometry["daily_coverage"].get(day.get("day"), {}),
            day.get("day"),
        )
        for day in daily_plan
    }
    full_plan_advisory_warnings = [
        *spine_warnings,
        *full_contract_warnings,
        dict(VERIFY_OFFICIAL_SOURCES_WARNING),
    ]
    warnings = [
        *spine_warnings,
        *geometry["warnings"],
        *full_contract_warnings,
        *[
            warning
            for day_warnings in daily_contract_warnings.values()
            for warning in day_warnings
        ],
        *(
            [dict(WAYPOINT_ONLY_WARNING)]
            if any(
                not points
                for points in daily_track_points.values()
            )
            else []
        ),
        dict(VERIFY_OFFICIAL_SOURCES_WARNING),
        *missing_warnings,
    ]
    artifacts = {}
    manifest = []

    full_artifact_id = "full_plan"
    full_filename = artifact_filename(
        trail_id,
        direction,
        full_artifact_id,
    )
    artifacts[full_filename] = build_gpx_document(
        f"{trail_id} full plan",
        all_waypoints,
        generated_at,
        trail_id,
        full_geometry_mode,
        track_points,
        direction,
        (
            spine_warnings[0]["message"]
            if spine_warnings
            else VERIFY_OFFICIAL_SOURCES_WARNING["message"]
        ),
        full_geometry_sources,
        geometry["route_selection"],
        geometry["full_coverage"],
    )
    manifest.append(
        build_manifest_entry(
            full_artifact_id,
            full_filename,
            "full_plan",
            all_waypoints,
            [
                *full_plan_advisory_warnings,
                *geometry["warnings"],
                *missing_warnings,
            ],
            full_geometry_mode,
            track_points,
            full_geometry_sources,
            geometry["full_coverage"],
        )
    )

    for day in daily_plan:
        day_number = day.get(
            "day"
        )
        artifact_id = (
            f"day_{format_day_label(day_number)}"
        )
        day_waypoints = waypoints_by_day.get(
            day_number,
            [],
        )
        day_missing_warnings = [
            warning for warning in missing_warnings
            if warning.get("day") == day_number
        ]
        day_points = daily_track_points.get(
            day_number,
            [],
        )
        day_sources = daily_geometry_sources.get(
            day_number,
            [],
        )
        day_geometry_mode = (
            DAILY_TRACK_GEOMETRY_MODE
            if day_points
            else WAYPOINT_ONLY_GEOMETRY_MODE
        )
        day_warnings = [
            *(
                []
                if day_points
                else [dict(WAYPOINT_ONLY_WARNING)]
            ),
            dict(VERIFY_OFFICIAL_SOURCES_WARNING),
            *daily_contract_warnings.get(day_number, []),
            *day_missing_warnings,
        ]
        filename = artifact_filename(
            trail_id,
            direction,
            artifact_id,
        )
        artifacts[filename] = build_gpx_document(
            (
                f"{trail_id} day "
                f"{format_day_label(day_number)}"
            ),
            day_waypoints,
            generated_at,
            trail_id,
            day_geometry_mode,
            day_points,
            direction=direction,
            metadata_warning=(
                VERIFY_OFFICIAL_SOURCES_WARNING["message"]
                if day_points
                else WAYPOINT_ONLY_WARNING["message"]
            ),
            geometry_sources=day_sources,
            route_selection=geometry["route_selection"],
            geometry_coverage=geometry["daily_coverage"].get(
                day_number,
                {},
            ),
        )
        manifest.append(
            build_manifest_entry(
                artifact_id,
                filename,
                "day",
                day_waypoints,
                day_warnings,
                day_geometry_mode,
                day_points,
                day_sources,
                geometry["daily_coverage"].get(day_number, {}),
                day=day,
            )
        )

    return {
        "export_version": ROUTE_GPX_EXPORT_VERSION,
        "generated_at": generated_at,
        "trail_id": trail_id,
        "direction": direction,
        "route_selection": geometry["route_selection"],
        "route_parts": geometry["route_parts"],
        "route_completeness": route_completeness(
            geometry["route_parts"],
            geometry["full_coverage"],
            track_points,
        ),
        "geometry_mode": full_geometry_mode,
        "warnings": warnings,
        "manifest": manifest,
        "artifacts": artifacts,
    }


def gpx_timestamp(
    value: str,
) -> str:
    if (
        len(value) == 16
        and value[8] == "T"
        and value.endswith("Z")
        and value[:8].isdigit()
        and value[9:15].isdigit()
    ):
        return (
            f"{value[:4]}-{value[4:6]}-{value[6:8]}"
            f"T{value[9:11]}:{value[11:13]}:"
            f"{value[13:15]}Z"
        )

    return value
