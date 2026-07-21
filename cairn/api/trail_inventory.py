# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""CairnOS-owned trail inventory for manual planning clients."""

from __future__ import annotations

import csv
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from cairn.api.access_points import (
    access_point_options,
    build_access_point_catalog,
    mile_inside_extent,
    normalize_route_extent,
)
from cairn.api.plan_request import (
    LONG_TRAIL_ID,
    LONG_TRAIL_ROOT,
    PlanAPIValidationError,
    VALID_DIRECTIONS,
)


CONTRACT_VERSION = "cairnos_trail_inventory_v1"
SOURCE_ARTIFACTS = {
    "route_overlay": "trails/vermont_long_trail/compiled/route_overlay.json",
    "overnight_reference": (
        "trails/vermont_long_trail/compiled/overnight_reference.json"
    ),
    "waypoint_reference": "trails/vermont_long_trail/compiled/waypoint_reference.json",
    "resupply_amenities": "trails/vermont_long_trail/raw/csv/resupply_amenities.csv",
    "side_trip_options": "trails/vermont_long_trail/raw/csv/side_trip_options.csv",
    "town_experience_mappings": (
        "trails/vermont_long_trail/raw/csv/town_experience_mappings.csv"
    ),
    "town_access_mappings": (
        "trails/vermont_long_trail/raw/csv/town_access_mappings.csv"
    ),
    "route_master": "trails/vermont_long_trail/raw/csv/route_master.csv",
}


def build_trail_inventory_response(
    trail_id: str = LONG_TRAIL_ID,
    direction: str = "NOBO",
    start_access_id: str | None = None,
    end_access_id: str | None = None,
) -> dict[str, Any]:
    if trail_id != LONG_TRAIL_ID:
        raise PlanAPIValidationError(
            f"trail_id must be {LONG_TRAIL_ID!r} for the MVP trail inventory"
        )
    if direction not in VALID_DIRECTIONS:
        raise PlanAPIValidationError("direction must be one of: NOBO, SOBO")

    total_miles = _trail_total_miles(LONG_TRAIL_ROOT)
    access_catalog = build_access_point_catalog(
        LONG_TRAIL_ROOT,
        trail_id,
    )
    if (start_access_id is None) != (end_access_id is None):
        raise PlanAPIValidationError(
            "start_access_id and end_access_id must be provided together"
        )
    route_extent = None
    if start_access_id is not None and end_access_id is not None:
        try:
            route_extent = normalize_route_extent(
                trip_type="SECTION",
                direction=direction,
                start_access_id=start_access_id,
                end_access_id=end_access_id,
                trail_root=LONG_TRAIL_ROOT,
                trail_id=trail_id,
            )
        except ValueError as error:
            raise PlanAPIValidationError(str(error)) from None
    overlay_nodes = _overlay_nodes(LONG_TRAIL_ROOT)
    overnight_lookup = _overnight_lookup(LONG_TRAIL_ROOT)
    resupply_rows = _resupply_rows_by_id(LONG_TRAIL_ROOT)

    items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for access in access_catalog.values():
        _append_unique(
            items,
            seen_ids,
            _access_point_item(access, total_miles),
        )
    for item in _overlay_items(overlay_nodes, overnight_lookup, total_miles):
        _append_unique(items, seen_ids, item)

    for item in _resupply_items(
        resupply_rows.values(),
        total_miles,
        _town_access_relationships(LONG_TRAIL_ROOT),
    ):
        _append_unique(items, seen_ids, item)

    for item in _side_trip_items(LONG_TRAIL_ROOT, resupply_rows, total_miles):
        _append_unique(items, seen_ids, item)

    sorted_items = sorted(
        items,
        key=lambda item: _directional_item_sort_key(
            item,
            direction,
        ),
    )

    return {
        "contract_version": CONTRACT_VERSION,
        "trail_id": trail_id,
        "status": "available",
        "selected_direction": direction,
        "direction_model": {
            "canonical_mile_system": "northbound_reference",
            "supported_directions": ["NOBO", "SOBO"],
            "section_model": "single_continuous_range",
            "flip_flop_supported": False,
            "trail_total_miles": _decimal_number(total_miles),
            "sobo_display_mile_rule": "trail_total_miles - canonical_mile",
        },
        "source": {
            "generated_from": "promoted_cairnos_artifacts",
            "source_artifacts": list(SOURCE_ARTIFACTS.values()),
            "notes": (
                "Generated from CairnOS route-overlay inventory plus approved "
                "resupply, overnight, and side-trip enrichment artifacts."
            ),
        },
        "route_extent": route_extent,
        "access_point_options": access_point_options(
            access_catalog,
            direction=direction,
            total_miles=float(total_miles),
        ),
        "checkpoint_options": access_point_options(
            access_catalog,
            direction=direction,
            total_miles=float(total_miles),
            route_extent=route_extent,
            intermediate_only=bool(route_extent),
        ),
        "required_anchor_options": {
            "overnight": _required_anchor_options(
                sorted_items,
                direction,
                "overnight_stop",
                route_extent,
            ),
            "resupply": _required_anchor_options(
                sorted_items,
                direction,
                "resupply_stop",
                route_extent,
            ),
        },
        "town_stop_options": {
            "contract_version": "cairnos_town_stop_options_v1",
            "semantics": "towns_grouped_by_trail_exit_access",
            "options": _town_stop_options(
                sorted_items,
                direction,
                route_extent,
            ),
        },
        "items": sorted_items,
    }


def _directional_item_sort_key(
    item: dict[str, Any],
    direction: str,
) -> tuple[float, str, str]:
    return (
        float(item.get("directional_miles", {}).get(direction, 0)),
        str(item.get("inventory_id", "")),
        str(item.get("display_name", "")),
    )


def _required_anchor_options(
    items: list[dict[str, Any]],
    direction: str,
    selectable_role: str,
    route_extent: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    options = []
    for item in items:
        if selectable_role not in item.get("selectable_as", []):
            continue
        if route_extent is not None and not mile_inside_extent(
            float(item["canonical_mile"]),
            route_extent,
        ):
            continue
        option = {
            "inventory_id": item["inventory_id"],
            "kind": item["kind"],
            "display_name": item["display_name"],
            "canonical_mile": item["canonical_mile"],
            "directional_mile": item["directional_miles"][direction],
            "label": item["labels"][direction],
        }
        if route_extent is not None:
            option["section_relative_mile"] = round(
                abs(
                    float(item["canonical_mile"])
                    - float(route_extent["canonical_start_mile"])
                ),
                1,
            )
        options.append(option)
    return options


def _access_point_item(
    access: dict[str, Any],
    total_miles: Decimal,
) -> dict[str, Any]:
    mile = Decimal(str(access["canonical_mile"]))
    item = _base_item(
        inventory_id=access["inventory_id"],
        kind=access["kind"],
        display_name=access["display_name"],
        canonical_mile=mile,
        total_miles=total_miles,
        source_artifacts=[SOURCE_ARTIFACTS["route_overlay"]],
        selectable_as=[
            "section_boundary",
            "operational_checkpoint",
            "day_start",
            "day_stop",
        ],
    )
    item["access_id"] = access["access_id"]
    item["overlay"] = {
        "overlay_id": access["overlay_id"],
        "node_class": access["node_class"],
        "division": access["division"],
    }
    item["access"] = {
        key: access[key]
        for key in (
            "road_crossing",
            "town_access",
            "access_notes",
        )
        if access.get(key)
    }
    item["supported_intents"] = [
        "checkpoint",
        "meet_pickup",
        "resupply",
        "overnight",
    ]
    return item


def _overlay_items(
    overlay_nodes: list[dict[str, Any]],
    overnight_lookup: dict[str, dict[str, Any]],
    total_miles: Decimal,
) -> list[dict[str, Any]]:
    items = []
    for node in overlay_nodes:
        overlay_id = _cell(node, "overlay_id")
        mile = _decimal_value(node.get("trail_mile"))
        if not overlay_id or mile is None:
            continue

        if node.get("shelter") or node.get("camping"):
            items.append(_overnight_item(node, overnight_lookup, total_miles))
    return items


def _overnight_item(
    node: dict[str, Any],
    overnight_lookup: dict[str, dict[str, Any]],
    total_miles: Decimal,
) -> dict[str, Any]:
    overlay_id = _cell(node, "overlay_id")
    mile = _decimal_value(node.get("trail_mile")) or Decimal("0")
    display_name = _concise_name(_cell(node, "canonical_name") or overlay_id)
    reference = overnight_lookup.get(overlay_id, {})
    overnight_class = _cell(reference, "overnight_class") or _node_kind(node)

    item = _base_item(
        inventory_id=f"{LONG_TRAIL_ID}:overnight:{overlay_id}",
        kind="overnight_site",
        display_name=display_name,
        canonical_mile=mile,
        total_miles=total_miles,
        source_artifacts=[
            SOURCE_ARTIFACTS["route_overlay"],
            SOURCE_ARTIFACTS["overnight_reference"],
            SOURCE_ARTIFACTS["waypoint_reference"],
        ],
        selectable_as=["day_stop", "day_start", "overnight_stop"],
    )
    item["overlay"] = _overlay_metadata(node)
    item["overnight"] = {
        "overnight_class": overnight_class,
        "shelter": bool(node.get("shelter")),
        "camping": bool(node.get("camping")),
        "bear_box": bool(reference.get("bear_box")),
    }
    for key in (
        "amenity_source_name",
        "amenity_source_url",
        "amenity_source_accessed",
    ):
        if reference.get(key):
            item["overnight"][key] = reference[key]
    return item


def _resupply_items(
    rows: list[dict[str, str]],
    total_miles: Decimal,
    access_relationships: dict[str, str],
) -> list[dict[str, Any]]:
    items = []
    for row in rows:
        canonical_hint = _cell(row, "canonical_hint")
        mile = _decimal_cell(row, "trail_mile")
        town_access = _cell(row, "town_access")
        if not canonical_hint or mile is None or not town_access:
            continue

        access_id = _access_inventory_id(canonical_hint, mile)
        town_ids = [
            _town_inventory_id(canonical_hint, mile, town_name)
            for town_name in _split_town_access_names(town_access)
        ]
        access_item = _base_item(
            inventory_id=access_id,
            kind="access_point",
            display_name=canonical_hint,
            canonical_mile=mile,
            total_miles=total_miles,
            source_artifacts=[
                SOURCE_ARTIFACTS["route_overlay"],
                SOURCE_ARTIFACTS["resupply_amenities"],
            ],
            selectable_as=["section_boundary", "day_start", "day_stop", "resupply_stop"],
        )
        access_item["labels"] = _directional_labels(
            canonical_hint,
            mile,
            total_miles,
        )
        access_item["access"] = _access_metadata(row)
        access_item["resupply"] = _resupply_metadata(row)
        access_item["related_inventory_ids"] = town_ids
        if access_id in access_relationships:
            access_item["overlay_id"] = access_relationships[access_id]
        items.append(access_item)

        for town_name in _split_town_access_names(town_access):
            town_item = _base_item(
                inventory_id=_town_inventory_id(canonical_hint, mile, town_name),
                kind="town",
                display_name=town_name,
                canonical_mile=mile,
                total_miles=total_miles,
                source_artifacts=[SOURCE_ARTIFACTS["resupply_amenities"]],
                selectable_as=["town_preference", "resupply_stop"],
                access_label=canonical_hint,
            )
            town_item["access"] = _access_metadata(row)
            town_item["resupply"] = _resupply_metadata(row)
            town_item["planner_preference_id"] = (
                f"{canonical_hint}:{_format_mile(mile)}::{town_name}"
            )
            town_item["related_inventory_ids"] = [access_id]
            if access_id in access_relationships:
                town_item["access_overlay_id"] = access_relationships[access_id]
            items.append(town_item)
    return items


def _side_trip_items(
    trail_root: Path,
    resupply_rows: dict[str, dict[str, str]],
    total_miles: Decimal,
) -> list[dict[str, Any]]:
    path = trail_root / "raw" / "csv" / "side_trip_options.csv"
    if not path.exists():
        return []

    items = []
    relationships = _town_experience_relationships(trail_root)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if _cell(row, "validation_status").casefold() != "validated":
                continue
            side_trip_id = _cell(row, "side_trip_id")
            if not side_trip_id:
                continue
            resupply_row = resupply_rows.get(_cell(row, "resupply_amenity_id"), {})
            mile = _decimal_cell(resupply_row, "trail_mile")
            access_label = _cell(resupply_row, "canonical_hint")
            if mile is None or not access_label:
                continue
            name = _cell(row, "name")
            item = _base_item(
                inventory_id=f"{LONG_TRAIL_ID}:side_trip:{side_trip_id}",
                kind="side_trip",
                display_name=name,
                canonical_mile=mile,
                total_miles=total_miles,
                source_artifacts=[
                    SOURCE_ARTIFACTS["side_trip_options"],
                    SOURCE_ARTIFACTS["resupply_amenities"],
                    SOURCE_ARTIFACTS["town_experience_mappings"],
                ],
                selectable_as=["side_trip_preference"],
                access_label=access_label,
            )
            item["access"] = _access_metadata(resupply_row)
            item["experience"] = {
                "side_trip_id": side_trip_id,
                "category": _cell(row, "category"),
                "estimated_time": _cell(row, "estimated_time"),
                "planning_notes": _cell(row, "planning_notes"),
                "validation_status": _cell(row, "validation_status"),
                "validation_date": _cell(row, "validation_date"),
            }
            item["planner_preference_id"] = side_trip_id
            relationship = relationships.get(item["inventory_id"])
            if relationship:
                item["town_inventory_id"] = relationship["town_inventory_id"]
                item["access_inventory_id"] = relationship["access_inventory_id"]
                item["related_inventory_ids"] = [
                    relationship["town_inventory_id"],
                    relationship["access_inventory_id"],
                ]
            items.append(item)
    return items


def _town_experience_relationships(
    trail_root: Path,
) -> dict[str, dict[str, str]]:
    path = trail_root / "raw" / "csv" / "town_experience_mappings.csv"
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        return {
            _cell(row, "experience_inventory_id"): {
                "town_inventory_id": _cell(row, "town_inventory_id"),
                "access_inventory_id": _cell(row, "access_inventory_id"),
            }
            for row in csv.DictReader(handle)
            if _cell(row, "experience_inventory_id")
            and _cell(row, "town_inventory_id")
            and _cell(row, "access_inventory_id")
        }


def _town_access_relationships(trail_root: Path) -> dict[str, str]:
    path = trail_root / "raw" / "csv" / "town_access_mappings.csv"
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        return {
            _cell(row, "access_inventory_id"): _cell(row, "overlay_id")
            for row in csv.DictReader(handle)
            if _cell(row, "access_inventory_id") and _cell(row, "overlay_id")
        }


def _town_stop_options(
    items: list[dict[str, Any]],
    direction: str,
    route_extent: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    items_by_id = {item["inventory_id"]: item for item in items}
    experiences_by_town: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        town_id = item.get("town_inventory_id")
        if item.get("kind") != "side_trip" or not town_id:
            continue
        experiences_by_town.setdefault(town_id, []).append(
            {
                "experience_inventory_id": item["inventory_id"],
                "town_inventory_id": town_id,
                "access_inventory_id": item["access_inventory_id"],
                "name": item["display_name"],
                "category": item["experience"].get("category"),
                "estimated_time": item["experience"].get("estimated_time"),
                "planning_notes": item["experience"].get("planning_notes"),
                "validation_status": item["experience"].get("validation_status"),
                "validation_date": item["experience"].get("validation_date"),
            }
        )

    options: list[dict[str, Any]] = []
    for town in items:
        if town.get("kind") != "town":
            continue
        if route_extent is not None and not mile_inside_extent(
            float(town["canonical_mile"]), route_extent
        ):
            continue
        access_id = next(
            (
                related_id
                for related_id in town.get("related_inventory_ids", [])
                if items_by_id.get(related_id, {}).get("kind") == "access_point"
            ),
            None,
        )
        if access_id is None:
            continue
        access_item = items_by_id[access_id]
        experiences = sorted(
            experiences_by_town.get(town["inventory_id"], []),
            key=lambda item: item["experience_inventory_id"],
        )
        supported_intents = ["resupply", "nero"]
        if town.get("resupply", {}).get("zero_candidate"):
            supported_intents.append("zero")
        if experiences:
            supported_intents.append("experience")
        nobo_mile = town["directional_miles"]["NOBO"]
        sobo_mile = town["directional_miles"]["SOBO"]
        option_access = {
            key: value
            for key, value in town.get("access", {}).items()
            if key != "town_access"
        }
        option_access["town_name"] = town["display_name"]
        option = {
            "town_inventory_id": town["inventory_id"],
            "town_name": town["display_name"],
            "access_inventory_id": access_id,
            "access_name": access_item["display_name"],
            "access_overlay_id": access_item.get("overlay_id"),
            "canonical_mile": town["canonical_mile"],
            "directional_miles": dict(town["directional_miles"]),
            "directional_mile": town["directional_miles"][direction],
            "labels": {
                "NOBO": (
                    f"[NOBO Trail Mile {nobo_mile}] {town['display_name']} "
                    f"via {access_item['display_name']}"
                ),
                "SOBO": (
                    f"[SOBO Trail Mile {sobo_mile}] {town['display_name']} "
                    f"via {access_item['display_name']}"
                ),
            },
            "access": option_access,
            "services": list(town.get("resupply", {}).get("services", [])),
            "zero_candidate": bool(
                town.get("resupply", {}).get("zero_candidate")
            ),
            "supported_intents": supported_intents,
            "experiences": experiences,
        }
        if route_extent is not None:
            option["section_relative_mile"] = round(
                abs(
                    float(town["canonical_mile"])
                    - float(route_extent["canonical_start_mile"])
                ),
                1,
            )
        options.append(option)
    return sorted(
        options,
        key=lambda option: (
            float(option["directional_mile"]),
            option["town_inventory_id"],
        ),
    )


def _base_item(
    *,
    inventory_id: str,
    kind: str,
    display_name: str,
    canonical_mile: Decimal,
    total_miles: Decimal,
    source_artifacts: list[str],
    selectable_as: list[str],
    access_label: str = "",
) -> dict[str, Any]:
    return {
        "inventory_id": inventory_id,
        "kind": kind,
        "display_name": display_name,
        "canonical_mile": _decimal_number(canonical_mile),
        "directional_miles": {
            "NOBO": _decimal_number(canonical_mile),
            "SOBO": _decimal_number(total_miles - canonical_mile),
        },
        "labels": _directional_labels(
            display_name,
            canonical_mile,
            total_miles,
            access_label=access_label,
        ),
        "selectable_as": selectable_as,
        "source_artifacts": source_artifacts,
    }


def _directional_labels(
    display_name: str,
    mile: Decimal,
    total_miles: Decimal,
    *,
    access_label: str = "",
) -> dict[str, str]:
    suffix = f" [{access_label}]" if access_label else ""
    return {
        "NOBO": f"[NOBO Mile {_format_mile(mile)}] {display_name}{suffix}",
        "SOBO": (
            f"[SOBO Mile {_format_mile(total_miles - mile)}] "
            f"{display_name}{suffix}"
        ),
    }


def _overlay_metadata(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "overlay_id": _cell(node, "overlay_id"),
        "node_class": _cell(node, "node_class"),
        "division": _cell(node, "division"),
    }


def _access_metadata(row: dict[str, str]) -> dict[str, Any]:
    metadata = {
        "access_label": _cell(row, "canonical_hint"),
        "town_access": _cell(row, "town_access"),
        "access_notes": _cell(row, "access_notes"),
        "access_distance_miles": _decimal_or_string(row, "access_distance_miles"),
        "access_distance_qualifier": _cell(row, "access_distance_qualifier"),
        "access_direction": _cell(row, "access_direction"),
        "access_mode": _cell(row, "access_mode"),
    }
    return {key: value for key, value in metadata.items() if value not in ("", None)}


def _resupply_metadata(row: dict[str, str]) -> dict[str, Any]:
    services = [
        service
        for service in ("grocery", "post_office", "outfitter", "lodging", "restaurants")
        if _cell(row, service).upper() == "TRUE"
    ]
    return {
        "resupply_convenience": _cell(row, "resupply_convenience"),
        "services": services,
        "zero_candidate": _cell(row, "zero_candidate").upper() == "TRUE",
    }


def _overlay_nodes(trail_root: Path) -> list[dict[str, Any]]:
    path = trail_root / "compiled" / "route_overlay.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload.get("overlay_nodes", []))


def _overnight_lookup(trail_root: Path) -> dict[str, dict[str, Any]]:
    path = trail_root / "compiled" / "overnight_reference.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        row["overlay_id"]: row
        for row in payload.get("matched_overnight_sites", [])
        if row.get("overlay_id")
    }


def _resupply_rows_by_id(trail_root: Path) -> dict[str, dict[str, str]]:
    path = trail_root / "raw" / "csv" / "resupply_amenities.csv"
    if not path.exists():
        return {}

    rows = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            canonical_hint = _cell(row, "canonical_hint")
            trail_mile = _cell(row, "trail_mile")
            if canonical_hint and trail_mile:
                rows[f"{canonical_hint}:{trail_mile}"] = row
    return rows


def _trail_total_miles(trail_root: Path) -> Decimal:
    path = trail_root / "raw" / "csv" / "route_master.csv"
    max_mile: Decimal | None = None
    if path.exists():
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                mile = _decimal_cell(row, "miles_from_MA_border_nb")
                if mile is not None and (max_mile is None or mile > max_mile):
                    max_mile = mile
    return max_mile or Decimal("272.1")


def _append_unique(
    items: list[dict[str, Any]],
    seen_ids: set[str],
    item: dict[str, Any],
) -> None:
    inventory_id = item["inventory_id"]
    if inventory_id not in seen_ids:
        seen_ids.add(inventory_id)
        items.append(item)


def _access_inventory_id(canonical_hint: str, mile: Decimal) -> str:
    return f"{LONG_TRAIL_ID}:access:{_slug(canonical_hint)}:{_format_mile(mile)}"


def _town_inventory_id(canonical_hint: str, mile: Decimal, town_name: str) -> str:
    return (
        f"{LONG_TRAIL_ID}:town:{_slug(canonical_hint)}:"
        f"{_format_mile(mile)}:{_slug(town_name)}"
    )


def _node_kind(node: dict[str, Any]) -> str:
    if node.get("shelter"):
        return "shelter"
    if node.get("camping"):
        return "camp"
    return _cell(node, "node_class") or "overnight"


def _split_town_access_names(town_access: str) -> list[str]:
    return [name.strip() for name in town_access.split("/") if name.strip()]


def _concise_name(value: str) -> str:
    return value.split(";", 1)[0].strip()


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
    return slug or "unknown"


def _decimal_or_string(row: dict[str, str], key: str) -> int | float | str:
    value = _cell(row, key)
    decimal = _decimal_value(value)
    if decimal is None:
        return value
    return _decimal_number(decimal)


def _decimal_cell(row: dict[str, str], key: str) -> Decimal | None:
    return _decimal_value(_cell(row, key))


def _decimal_value(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _decimal_number(value: Decimal) -> int | float:
    quantized = value.quantize(Decimal("0.1"))
    if quantized == quantized.to_integral():
        return int(quantized)
    return float(quantized)


def _format_mile(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.1")))


def _cell(row: dict[str, Any], key: str) -> str:
    return str(row.get(key) or "").strip()
