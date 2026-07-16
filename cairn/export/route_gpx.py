# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""Waypoint-only GPX route artifacts for downstream imports."""

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


ROUTE_GPX_EXPORT_VERSION = "cairnos_route_gpx_v1"
GPX_GEOMETRY_MODE = "waypoint_only"
GPX_MEDIA_TYPE = "application/gpx+xml"
GPX_NAMESPACE = "http://www.topografix.com/GPX/1/1"
CAIRNOS_NAMESPACE = "https://cairnos.local/ns/route-gpx/1"


WAYPOINT_ONLY_WARNING = {
    "code": "waypoint_only_gpx",
    "severity": "warning",
    "message": (
        "CairnOS GPX route artifacts contain planned daily start/stop "
        "waypoints only. They do not include route or track geometry."
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
        "spine_coordinates": load_spine_coordinates(
            trail_root
        ),
        "total_miles": total_overlay_miles(
            overlay_nodes
        ),
    }


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
    day: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry = {
        "artifact_id": artifact_id,
        "filename": filename,
        "scope": scope,
        "media_type": GPX_MEDIA_TYPE,
        "export_version": ROUTE_GPX_EXPORT_VERSION,
        "geometry_mode": GPX_GEOMETRY_MODE,
        "waypoint_count": len(waypoints),
        "warning_codes": warning_codes(warnings),
    }

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
        "CairnOS waypoint-only GPX.",
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


def build_gpx_document(
    name: str,
    waypoints: list[dict[str, Any]],
    generated_at: str,
    trail_id: str,
) -> str:
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
        GPX_GEOMETRY_MODE,
    )
    add_cairnos_extension(
        metadata_extensions,
        "trail_id",
        trail_id,
    )
    add_cairnos_extension(
        metadata_extensions,
        "warning",
        WAYPOINT_ONLY_WARNING["message"],
    )

    for waypoint in waypoints:
        add_waypoint_element(
            root,
            waypoint,
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
) -> dict[str, Any]:
    trail_root = Path(
        trail_root
    )
    trail_id = trail_id or trail_root.name
    generated_at = generated_at or utc_timestamp()
    context = coordinate_context(
        trail_root
    )
    all_waypoints, waypoints_by_day, missing_warnings = (
        build_daily_waypoints(
            daily_plan,
            context,
        )
    )

    advisory_warnings = [
        dict(WAYPOINT_ONLY_WARNING),
        dict(VERIFY_OFFICIAL_SOURCES_WARNING),
    ]
    warnings = [
        *advisory_warnings,
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
    )
    manifest.append(
        build_manifest_entry(
            full_artifact_id,
            full_filename,
            "full_plan",
            all_waypoints,
            warnings,
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
        day_warnings = [
            *advisory_warnings,
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
        )
        manifest.append(
            build_manifest_entry(
                artifact_id,
                filename,
                "day",
                day_waypoints,
                day_warnings,
                day,
            )
        )

    return {
        "export_version": ROUTE_GPX_EXPORT_VERSION,
        "generated_at": generated_at,
        "trail_id": trail_id,
        "direction": direction,
        "geometry_mode": GPX_GEOMETRY_MODE,
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
