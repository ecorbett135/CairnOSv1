# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""Resolve Plan API required-anchor ids against promoted trail inventory."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from cairn.api.access_points import mile_inside_extent
from cairn.api.plan_request import PlanAPIValidationError
from cairn.api.trail_inventory import build_trail_inventory_response

if TYPE_CHECKING:
    from cairn.api.plan_request import PlanAPIRequest


REQUIRED_PLANNING_ANCHOR_CONTRACT_VERSION = (
    "cairnos_required_planning_anchors_v1"
)


def resolve_required_anchor_contract(
    request: PlanAPIRequest,
) -> dict[str, Any]:
    """Return planner-ready required anchors after inventory validation."""
    inventory = build_trail_inventory_response(request.trail_id)
    items_by_id = {
        item["inventory_id"]: item
        for item in inventory.get("items", [])
    }

    overnight = _resolve_anchor_ids(
        request.required_overnight_anchor_ids,
        field_name="required_overnight_anchor_ids",
        selectable_role="overnight_stop",
        direction=request.direction,
        items_by_id=items_by_id,
    )
    resupply = _resolve_anchor_ids(
        request.required_resupply_anchor_ids,
        field_name="required_resupply_anchor_ids",
        selectable_role="resupply_stop",
        direction=request.direction,
        items_by_id=items_by_id,
        validate_order=False,
    )
    _reject_duplicate_resupply_nodes(resupply)
    _validate_directional_order(
        resupply,
        "required_resupply_anchor_ids",
        request.direction,
    )
    _validate_anchors_inside_extent(
        [*overnight, *resupply],
        request.route_extent or {},
    )

    return {
        "contract_version": REQUIRED_PLANNING_ANCHOR_CONTRACT_VERSION,
        "required_overnight_anchors": overnight,
        "required_resupply_anchors": resupply,
    }


def _resolve_anchor_ids(
    inventory_ids: tuple[str, ...],
    *,
    field_name: str,
    selectable_role: str,
    direction: str,
    items_by_id: dict[str, dict[str, Any]],
    validate_order: bool = True,
) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for inventory_id in inventory_ids:
        if inventory_id in seen_ids:
            raise PlanAPIValidationError(
                f"{field_name} contains duplicate inventory_id: {inventory_id}"
            )
        seen_ids.add(inventory_id)

        item = items_by_id.get(inventory_id)
        if item is None:
            raise PlanAPIValidationError(
                f"{field_name} contains unknown inventory_id: {inventory_id}"
            )
        if selectable_role not in item.get("selectable_as", []):
            raise PlanAPIValidationError(
                f"{field_name} inventory_id is not selectable as "
                f"{selectable_role}: {inventory_id}"
            )

        anchor = {
            "inventory_id": inventory_id,
            "kind": item.get("kind"),
            "display_name": item.get("display_name"),
            "canonical_mile": float(item["canonical_mile"]),
        }
        if selectable_role == "overnight_stop":
            anchor["overlay_id"] = item.get("overlay", {}).get("overlay_id")
        else:
            anchor["planner_node_id"] = _resupply_planner_node_id(item)
            anchor["town_name"] = (
                item.get("display_name") if item.get("kind") == "town" else ""
            )
        resolved.append(anchor)

    if validate_order:
        _validate_directional_order(resolved, field_name, direction)
    return resolved


def _validate_directional_order(
    anchors: list[dict[str, Any]],
    field_name: str,
    direction: str,
) -> None:
    for previous, current in zip(anchors, anchors[1:]):
        previous_mile = previous["canonical_mile"]
        current_mile = current["canonical_mile"]
        ordered = (
            current_mile > previous_mile
            if direction == "NOBO"
            else current_mile < previous_mile
        )
        if not ordered:
            raise PlanAPIValidationError(
                f"{field_name} must follow {direction} route order; "
                f"{current['inventory_id']} cannot follow "
                f"{previous['inventory_id']}"
            )


def _reject_duplicate_resupply_nodes(
    anchors: list[dict[str, Any]],
) -> None:
    by_node_id: dict[str, str] = {}
    for anchor in anchors:
        planner_node_id = anchor["planner_node_id"]
        existing_id = by_node_id.get(planner_node_id)
        if existing_id is not None:
            raise PlanAPIValidationError(
                "required_resupply_anchor_ids resolves multiple inventory IDs "
                f"to the same resupply anchor: {existing_id}, "
                f"{anchor['inventory_id']}"
            )
        by_node_id[planner_node_id] = anchor["inventory_id"]


def _resupply_planner_node_id(item: dict[str, Any]) -> str:
    preference_id = str(item.get("planner_preference_id") or "")
    if preference_id:
        return preference_id.split("::", 1)[0]

    access_label = str(
        item.get("access", {}).get("access_label")
        or item.get("display_name")
        or ""
    )
    mile = float(item["canonical_mile"])
    return f"{access_label}:{mile:.1f}"


def _validate_anchors_inside_extent(
    anchors: list[dict[str, Any]],
    route_extent: dict[str, Any],
) -> None:
    if route_extent.get("extent_type") != "defined_trail_section":
        return
    for anchor in anchors:
        mile = float(anchor["canonical_mile"])
        if not mile_inside_extent(mile, route_extent):
            raise PlanAPIValidationError(
                "Required planning anchor is outside the selected extent: "
                f"{anchor['inventory_id']}"
            )
