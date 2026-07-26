# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""Required planning-anchor result validation for PlannerV2."""

from __future__ import annotations

from typing import Any


REQUIRED_PLANNING_ANCHOR_CONTRACT_VERSION = (
    "cairnos_required_planning_anchors_v1"
)


class RequiredPlanningAnchorError(ValueError):
    """Raised when PlannerV2 cannot satisfy a required anchor contract."""


def build_required_anchor_status(
    *,
    required_overnight_anchors: list[dict[str, Any]],
    required_resupply_anchors: list[dict[str, Any]],
    daily_plan: list[dict[str, Any]],
    resupply_plan: list[dict[str, Any]],
    min_daily_miles: float,
    max_daily_miles: float,
    max_daily_elevation: float,
) -> dict[str, Any]:
    overnight_ids = [anchor["inventory_id"] for anchor in required_overnight_anchors]
    resupply_ids = [anchor["inventory_id"] for anchor in required_resupply_anchors]

    for inventory_id in overnight_ids:
        matching_rows = [
            row
            for row in daily_plan
            if row.get("required_overnight_anchor_id") == inventory_id
        ]
        _require_exactly_once("overnight", inventory_id, len(matching_rows))
        # Advanced selections are authoritative partial specifications. Mileage
        # and elevation controls remain preferences and are reported by the
        # normal itinerary-exception analysis instead of rejecting a plan that
        # successfully placed the requested anchor.
    for inventory_id in resupply_ids:
        count = sum(
            row.get("required_anchor_id") == inventory_id
            for row in resupply_plan
        )
        _require_exactly_once("resupply", inventory_id, count)

    return {
        "contract_version": REQUIRED_PLANNING_ANCHOR_CONTRACT_VERSION,
        "semantics": "partial_specification",
        "required_overnight_anchor_ids": overnight_ids,
        "required_resupply_anchor_ids": resupply_ids,
        "satisfied_overnight_anchor_ids": list(overnight_ids),
        "satisfied_resupply_anchor_ids": list(resupply_ids),
    }


def _require_exactly_once(anchor_type: str, inventory_id: str, count: int) -> None:
    if count == 1:
        return
    raise RequiredPlanningAnchorError(
        f"Required {anchor_type} anchor must appear exactly once: "
        f"{inventory_id} appeared {count} times. Adjust desired_days or daily "
        "mileage/elevation limits."
    )
