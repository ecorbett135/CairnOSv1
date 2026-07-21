# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""Shared CairnOS Plan API controls for clients and debug interfaces."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


PLAN_CONTROL_SPECS: tuple[dict[str, Any], ...] = (
    {
        "id": "desired_days",
        "label": "Desired Completion Days",
        "input": "slider",
        "value_type": "integer",
        "min": 3,
        "max": 60,
        "default": 28,
        "step": 1,
    },
    {
        "id": "min_daily_miles",
        "label": "Minimum Daily Miles",
        "input": "slider",
        "value_type": "integer",
        "min": 4,
        "max": 25,
        "default": 8,
        "step": 1,
    },
    {
        "id": "max_daily_miles",
        "label": "Maximum Daily Miles",
        "input": "slider",
        "value_type": "integer",
        "min": 8,
        "max": 40,
        "default": 16,
        "step": 1,
    },
    {
        "id": "max_daily_elevation",
        "label": "Maximum Daily Elevation Gain",
        "input": "slider",
        "value_type": "integer",
        "min": 1000,
        "max": 10000,
        "default": 3500,
        "step": 250,
    },
    {
        "id": "resupply_cadence",
        "label": "Preferred Resupply Cadence (days)",
        "input": "slider",
        "value_type": "integer",
        "min": 2,
        "max": 10,
        "default": 5,
        "step": 1,
    },
    {
        "id": "recovery_planning_mode",
        "label": "Recovery Planning Mode",
        "input": "select",
        "value_type": "string",
        "default": "cadence",
        "choices": [
            {"value": "cadence", "label": "Cadence"},
            {"value": "target_counts", "label": "Target Counts"},
        ],
    },
    {
        "id": "recovery_cadence",
        "label": "Preferred Zero/Nero Cadence (days)",
        "input": "slider",
        "value_type": "integer",
        "min": 3,
        "max": 14,
        "default": 6,
        "step": 1,
    },
    {
        "id": "target_zero_days",
        "label": "Target Zero Days",
        "input": "slider",
        "value_type": "integer",
        "min": 0,
        "max": 10,
        "default": 3,
        "step": 1,
    },
    {
        "id": "target_nero_days",
        "label": "Target Nero Days",
        "input": "slider",
        "value_type": "integer",
        "min": 0,
        "max": 10,
        "default": 2,
        "step": 1,
    },
    {
        "id": "min_nero_miles",
        "label": "Minimum Nero Miles",
        "input": "slider",
        "value_type": "integer",
        "min": 1,
        "max": 10,
        "default": 5,
        "step": 1,
    },
    {
        "id": "max_nero_miles",
        "label": "Maximum Nero Miles",
        "input": "slider",
        "value_type": "integer",
        "min": 4,
        "max": 15,
        "default": 8,
        "step": 1,
    },
    {
        "id": "nero_max_trail_miles",
        "label": "Maximum Trail Miles for a Selected-Town Nero",
        "input": "slider",
        "value_type": "number",
        "min": 1,
        "max": 15,
        "step": 0.5,
        "required_when": {
            "town_stop_intent": "nero",
        },
        "default": None,
    },
    {
        "id": "allow_extra_resupply_only",
        "label": "Allow Extra Resupply-Only Stops",
        "input": "checkbox",
        "value_type": "boolean",
        "default": True,
    },
    {
        "id": "avoid_long_food_carry",
        "label": "Avoid Long Food Carry",
        "input": "checkbox",
        "value_type": "boolean",
        "default": True,
    },
    {
        "id": "prefer_bear_box_sites",
        "label": "Prefer Sites With Bear Boxes",
        "input": "checkbox",
        "value_type": "boolean",
        "default": False,
    },
    {
        "id": "convenient_resupply_distance_miles",
        "label": "Convenient Resupply-Only Access (miles)",
        "input": "slider",
        "value_type": "number",
        "min": 0.5,
        "max": 5.0,
        "default": 1.0,
        "step": 0.5,
    },
)

PLAN_CONTROL_SPECS_BY_ID = {
    spec["id"]: spec
    for spec in PLAN_CONTROL_SPECS
}


def plan_control_spec(control_id: str) -> dict[str, Any]:
    return PLAN_CONTROL_SPECS_BY_ID[control_id]


def build_plan_control_specs_response() -> list[dict[str, Any]]:
    return deepcopy(list(PLAN_CONTROL_SPECS))


def control_choice_labels(control_id: str) -> list[str]:
    return [
        choice["label"]
        for choice in plan_control_spec(control_id).get("choices", [])
    ]


def control_choice_value_for_label(control_id: str, label: str) -> str:
    for choice in plan_control_spec(control_id).get("choices", []):
        if choice["label"] == label:
            return choice["value"]
    raise KeyError(label)
