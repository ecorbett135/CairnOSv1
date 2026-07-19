# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""Defined-trail route extents and operational access-point anchors."""

from __future__ import annotations

import json
import re
from datetime import date, time
from pathlib import Path
from typing import Any, Mapping


ROUTE_EXTENT_CONTRACT_VERSION = "cairnos_route_extent_v1"
ACCESS_POINT_ANCHOR_CONTRACT_VERSION = "cairnos_access_point_anchors_v1"
ACCESS_POINT_INTENTS = {"checkpoint", "meet_pickup", "resupply", "overnight"}
ACCESS_POINT_NODE_CLASSES = {"crossing", "trailhead", "logistics"}


def build_access_point_catalog(
    trail_root: Path | str,
    trail_id: str,
) -> dict[str, dict[str, Any]]:
    """Return promoted defined-trail road crossings and trailheads by stable id."""
    path = Path(trail_root) / "compiled" / "route_overlay.json"
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    catalog: dict[str, dict[str, Any]] = {}
    for node in payload.get("overlay_nodes", []):
        overlay_id = str(node.get("overlay_id") or "").strip()
        canonical_name = str(node.get("canonical_name") or "").strip()
        node_class = str(node.get("node_class") or "").strip().casefold()
        mile = _number(node.get("trail_mile"))
        if (
            not overlay_id
            or not canonical_name
            or mile is None
            or mile < 0
            or node_class not in ACCESS_POINT_NODE_CLASSES
        ):
            continue

        # Overlay logistics nodes are access points only when the promoted
        # overlay explicitly identifies a road crossing. This excludes the
        # northern terminus and avoids promoting candidate crossing data.
        road_crossing = str(node.get("road_crossing") or "").strip()
        if node_class == "logistics" and not road_crossing:
            continue

        access_id = f"{trail_id}:access:{overlay_id}"
        kind = "trailhead" if node_class == "trailhead" else "road_crossing"
        catalog[access_id] = {
            "access_id": access_id,
            "inventory_id": access_id,
            "kind": kind,
            "display_name": canonical_name,
            "canonical_mile": round(mile, 1),
            "overlay_id": overlay_id,
            "node_class": node_class,
            "division": str(node.get("division") or ""),
            "road_crossing": road_crossing or canonical_name,
            "town_access": str(node.get("town_access") or ""),
            "access_notes": str(node.get("access_notes") or ""),
            "resupply": bool(node.get("resupply")),
        }
    return catalog


def trail_total_miles(trail_root: Path | str) -> float:
    """Return the promoted overlay's public defined-trail mile maximum."""
    path = Path(trail_root) / "compiled" / "route_overlay.json"
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    miles = [
        mile
        for node in payload.get("overlay_nodes", [])
        if (mile := _number(node.get("trail_mile"))) is not None
        and mile >= 0
    ]
    if not miles:
        raise ValueError("Promoted route overlay has no defined-trail mileage")
    return round(max(miles), 1)


def normalize_route_extent(
    *,
    trip_type: str,
    direction: str,
    start_access_id: Any,
    end_access_id: Any,
    trail_root: Path | str,
    trail_id: str,
) -> dict[str, Any]:
    catalog = build_access_point_catalog(trail_root, trail_id)
    total_miles = trail_total_miles(trail_root)

    if trip_type == "THRU":
        if start_access_id is not None or end_access_id is not None:
            raise ValueError(
                "start_access_id and end_access_id are only valid for SECTION plans"
            )
        start_mile = total_miles if direction == "SOBO" else 0.0
        end_mile = 0.0 if direction == "SOBO" else total_miles
        return {
            "contract_version": ROUTE_EXTENT_CONTRACT_VERSION,
            "extent_type": "full_trail",
            "direction": direction,
            "start_access_id": None,
            "end_access_id": None,
            "start": None,
            "end": None,
            "canonical_start_mile": start_mile,
            "canonical_end_mile": end_mile,
            "canonical_min_mile": 0.0,
            "canonical_max_mile": total_miles,
            "distance_miles": total_miles,
        }

    start_id = _required_access_id(start_access_id, "start_access_id")
    end_id = _required_access_id(end_access_id, "end_access_id")
    start = catalog.get(start_id)
    end = catalog.get(end_id)
    if start is None:
        raise ValueError(f"start_access_id contains unknown access_id: {start_id}")
    if end is None:
        raise ValueError(f"end_access_id contains unknown access_id: {end_id}")
    if start_id == end_id:
        raise ValueError("start_access_id and end_access_id must be different")

    start_mile = float(start["canonical_mile"])
    end_mile = float(end["canonical_mile"])
    ordered = end_mile > start_mile if direction == "NOBO" else end_mile < start_mile
    if not ordered:
        raise ValueError(
            f"SECTION endpoints are reversed for {direction}: "
            f"end_access_id {end_id} cannot follow start_access_id {start_id}"
        )

    return {
        "contract_version": ROUTE_EXTENT_CONTRACT_VERSION,
        "extent_type": "defined_trail_section",
        "direction": direction,
        "start_access_id": start_id,
        "end_access_id": end_id,
        "start": _extent_endpoint(start, section_relative_mile=0.0),
        "end": _extent_endpoint(
            end,
            section_relative_mile=round(abs(end_mile - start_mile), 1),
        ),
        "canonical_start_mile": start_mile,
        "canonical_end_mile": end_mile,
        "canonical_min_mile": min(start_mile, end_mile),
        "canonical_max_mile": max(start_mile, end_mile),
        "distance_miles": round(abs(end_mile - start_mile), 1),
    }


def normalize_access_point_anchors(
    value: Any,
    *,
    route_extent: Mapping[str, Any],
    trail_root: Path | str,
    trail_id: str,
) -> tuple[dict[str, Any], ...]:
    if value is None:
        value = []
    if not isinstance(value, list):
        raise ValueError("access_point_anchors must be a list of objects")

    catalog = build_access_point_catalog(trail_root, trail_id)
    direction = str(route_extent["direction"])
    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for raw_anchor in value:
        if not isinstance(raw_anchor, Mapping):
            raise ValueError("access_point_anchors must be a list of objects")
        access_id = _required_access_id(
            raw_anchor.get("access_id"),
            "access_point_anchors[].access_id",
        )
        if access_id in seen_ids:
            raise ValueError(
                "access_point_anchors contains duplicate access_id: "
                f"{access_id}"
            )
        seen_ids.add(access_id)

        access = catalog.get(access_id)
        if access is None:
            raise ValueError(
                "access_point_anchors contains unknown access_id: "
                f"{access_id}"
            )
        intent = raw_anchor.get("intent")
        if not isinstance(intent, str) or intent not in ACCESS_POINT_INTENTS:
            allowed = ", ".join(sorted(ACCESS_POINT_INTENTS))
            raise ValueError(
                "access_point_anchors[].intent must be one of: " + allowed
            )

        mile = float(access["canonical_mile"])
        if not mile_inside_extent(mile, route_extent, include_boundaries=False):
            raise ValueError(
                f"access_point_anchors access_id is outside the selected extent: "
                f"{access_id}"
            )

        anchor = {
            "access_id": access_id,
            "intent": intent,
            "canonical_mile": mile,
            "section_relative_mile": round(
                abs(mile - float(route_extent["canonical_start_mile"])),
                1,
            ),
            "display_name": access["display_name"],
            "kind": access["kind"],
            "overlay_id": access["overlay_id"],
            "node_class": access["node_class"],
            "division": access["division"],
            "town_access": access["town_access"],
            "access_notes": access["access_notes"],
            "resupply": access["resupply"],
        }
        for field_name in ("date", "time", "note"):
            parsed = _optional_anchor_field(raw_anchor, field_name)
            if parsed is not None:
                anchor[field_name] = parsed
        normalized.append(anchor)

    for previous, current in zip(normalized, normalized[1:]):
        previous_mile = float(previous["canonical_mile"])
        current_mile = float(current["canonical_mile"])
        ordered = (
            current_mile > previous_mile
            if direction == "NOBO"
            else current_mile < previous_mile
        )
        if not ordered:
            raise ValueError(
                f"access_point_anchors must follow {direction} route order; "
                f"{current['access_id']} cannot follow {previous['access_id']}"
            )
    return tuple(normalized)


def mile_inside_extent(
    mile: float,
    route_extent: Mapping[str, Any],
    *,
    include_boundaries: bool = True,
) -> bool:
    lower = float(route_extent["canonical_min_mile"])
    upper = float(route_extent["canonical_max_mile"])
    if include_boundaries:
        return lower - 0.05 <= mile <= upper + 0.05
    return lower + 0.05 < mile < upper - 0.05


def access_point_options(
    catalog: Mapping[str, Mapping[str, Any]],
    *,
    direction: str,
    total_miles: float,
    route_extent: Mapping[str, Any] | None = None,
    intermediate_only: bool = False,
) -> list[dict[str, Any]]:
    options = []
    for access in catalog.values():
        mile = float(access["canonical_mile"])
        if route_extent and not mile_inside_extent(
            mile,
            route_extent,
            include_boundaries=not intermediate_only,
        ):
            continue
        directional_mile = mile if direction == "NOBO" else total_miles - mile
        option = {
            "access_id": access["access_id"],
            "inventory_id": access["inventory_id"],
            "kind": access["kind"],
            "display_name": access["display_name"],
            "canonical_mile": round(mile, 1),
            "directional_mile": round(directional_mile, 1),
            "label": (
                f"[{direction} Mile {directional_mile:.1f}] "
                f"{access['display_name']}"
            ),
        }
        if route_extent:
            option["section_relative_mile"] = round(
                abs(mile - float(route_extent["canonical_start_mile"])),
                1,
            )
        options.append(option)
    return sorted(
        options,
        key=lambda option: (
            option["directional_mile"],
            option["access_id"],
            option["display_name"],
        ),
    )


def _extent_endpoint(
    access: Mapping[str, Any],
    section_relative_mile: float,
) -> dict[str, Any]:
    return {
        key: access[key]
        for key in (
            "access_id",
            "kind",
            "display_name",
            "canonical_mile",
            "overlay_id",
            "node_class",
            "division",
            "road_crossing",
            "town_access",
            "access_notes",
        )
    } | {"section_relative_mile": section_relative_mile}


def _required_access_id(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _optional_anchor_field(anchor: Mapping[str, Any], field_name: str) -> str | None:
    value = anchor.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"access_point_anchors[].{field_name} must be a string")
    value = value.strip()
    if not value:
        return None
    if field_name == "date":
        try:
            date.fromisoformat(value)
        except ValueError:
            raise ValueError(
                "access_point_anchors[].date must use YYYY-MM-DD"
            ) from None
    elif field_name == "time":
        if not re.fullmatch(r"\d{2}:\d{2}", value):
            raise ValueError("access_point_anchors[].time must use HH:MM")
        try:
            time.fromisoformat(value)
        except ValueError:
            raise ValueError("access_point_anchors[].time must use HH:MM") from None
    return value


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)
