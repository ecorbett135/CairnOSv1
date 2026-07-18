# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""Stable ingress/egress route-selection contract helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


ROUTE_SELECTION_CONTRACT_VERSION = "cairnos_route_selection_v1"


def load_approach_catalog(
    trail_root: Path | str,
) -> dict[str, dict[str, Any]]:
    path = Path(trail_root) / "compiled" / "approach_trails.json"
    if not path.exists():
        raise ValueError(
            "Compiled approach route catalog is unavailable: "
            "compiled/approach_trails.json"
        )

    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    geometries = {
        geometry.get("approach_id"): geometry
        for geometry in payload.get("approach_geometries", [])
        if geometry.get("approach_id")
    }
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in payload.get("approach_trails", []):
        approach_id = str(row.get("approach_id") or "").strip()
        if approach_id:
            grouped.setdefault(approach_id, []).append(row)

    catalog: dict[str, dict[str, Any]] = {}
    for approach_id, rows in sorted(grouped.items()):
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
            raise ValueError(
                "Compiled approach route metadata is inconsistent for "
                f"approach_id: {approach_id}"
            )

        geometry = geometries.get(approach_id)
        catalog[approach_id] = {
            "approach_id": approach_id,
            "approach_name": next(iter(names)),
            "connected_terminus": next(iter(termini)),
            "geometry_status": "available" if geometry else "unavailable",
            "geometry_id": geometry.get("geometry_id") if geometry else None,
        }
    return catalog


def route_roles(connected_terminus: str) -> list[str]:
    if connected_terminus == "southern":
        return ["NOBO_INGRESS", "SOBO_EGRESS"]
    if connected_terminus == "northern":
        return ["NOBO_EGRESS", "SOBO_INGRESS"]
    return []


def build_route_selection_options(
    trail_root: Path | str,
) -> dict[str, Any]:
    catalog = load_approach_catalog(trail_root)
    return {
        "contract_version": ROUTE_SELECTION_CONTRACT_VERSION,
        "semantics": "selected_approach_ids",
        "options": [
            {
                **entry,
                "selectable_roles": route_roles(
                    entry["connected_terminus"]
                ),
            }
            for entry in catalog.values()
        ],
    }


def normalize_route_selection(
    payload: Mapping[str, Any],
    *,
    direction: str,
    ingress_route: str,
    egress_route: str,
    trail_root: Path | str,
) -> dict[str, str]:
    catalog = load_approach_catalog(trail_root)
    raw_selection = payload.get("route_selection")

    if raw_selection is None:
        ingress_id = _approach_id_for_name(
            catalog,
            ingress_route,
            "ingress_route",
        )
        egress_id = _approach_id_for_name(
            catalog,
            egress_route,
            "egress_route",
        )
    else:
        if not isinstance(raw_selection, Mapping):
            raise ValueError("route_selection must be an object")
        version = raw_selection.get("contract_version")
        if version != ROUTE_SELECTION_CONTRACT_VERSION:
            raise ValueError(
                "route_selection.contract_version must be "
                f"{ROUTE_SELECTION_CONTRACT_VERSION!r}"
            )
        ingress_id = _selection_id(
            raw_selection,
            "ingress_approach_id",
        )
        egress_id = _selection_id(
            raw_selection,
            "egress_approach_id",
        )

    _validate_selected_approach(
        catalog,
        approach_id=ingress_id,
        route_name=ingress_route,
        field_name="route_selection.ingress_approach_id",
        direction=direction,
        role="ingress",
    )
    _validate_selected_approach(
        catalog,
        approach_id=egress_id,
        route_name=egress_route,
        field_name="route_selection.egress_approach_id",
        direction=direction,
        role="egress",
    )
    if ingress_id == egress_id:
        raise ValueError(
            "route_selection ingress and egress approach_ids must be different"
        )

    return {
        "contract_version": ROUTE_SELECTION_CONTRACT_VERSION,
        "ingress_approach_id": ingress_id,
        "egress_approach_id": egress_id,
    }


def _approach_id_for_name(
    catalog: Mapping[str, Mapping[str, Any]],
    route_name: str,
    field_name: str,
) -> str:
    matches = [
        approach_id
        for approach_id, entry in catalog.items()
        if entry.get("approach_name") == route_name
    ]
    if len(matches) != 1:
        raise ValueError(
            f"{field_name} must resolve to exactly one compiled approach_id"
        )
    return matches[0]


def _selection_id(
    selection: Mapping[str, Any],
    field_name: str,
) -> str:
    value = selection.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"route_selection.{field_name} must be a non-empty string"
        )
    return value.strip()


def _validate_selected_approach(
    catalog: Mapping[str, Mapping[str, Any]],
    *,
    approach_id: str,
    route_name: str,
    field_name: str,
    direction: str,
    role: str,
) -> None:
    entry = catalog.get(approach_id)
    if entry is None:
        raise ValueError(
            f"{field_name} unknown approach_id: {approach_id}"
        )
    if entry.get("approach_name") != route_name:
        raise ValueError(
            f"{field_name} is incompatible with {role}_route "
            f"{route_name!r}: {approach_id} identifies "
            f"{entry.get('approach_name')!r}"
        )

    expected_terminus = (
        "southern"
        if (direction, role) in {
            ("NOBO", "ingress"),
            ("SOBO", "egress"),
        }
        else "northern"
    )
    actual_terminus = entry.get("connected_terminus")
    if actual_terminus != expected_terminus:
        raise ValueError(
            f"{field_name} is incompatible with {direction} {role}: "
            f"expected connected_terminus {expected_terminus!r}, got "
            f"{actual_terminus!r}"
        )
