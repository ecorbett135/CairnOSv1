# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "trail_inventory"
    / "vermont_long_trail_inventory_v1.json"
)


def test_trail_inventory_fixture_shape_is_versioned_and_directional():
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert payload["contract_version"] == "cairnos_trail_inventory_v1"
    assert payload["trail_id"] == "vermont_long_trail"
    assert payload["status"] == "available"
    assert payload["selected_direction"] == "NOBO"
    assert payload["direction_model"]["canonical_mile_system"] == (
        "northbound_reference"
    )
    assert payload["direction_model"]["supported_directions"] == ["NOBO", "SOBO"]
    assert payload["direction_model"]["section_model"] == "single_continuous_range"
    assert payload["direction_model"]["flip_flop_supported"] is False
    assert payload["items"]
    assert payload["required_anchor_options"]["overnight"]
    assert payload["required_anchor_options"]["resupply"]
    assert payload["access_point_options"]
    assert payload["checkpoint_options"]


def test_trail_inventory_fixture_anchor_options_are_directionally_ordered():
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    for anchor_type in ("overnight", "resupply"):
        options = payload["required_anchor_options"][anchor_type]
        sort_keys = [
            (
                option["directional_mile"],
                option["inventory_id"],
                option["display_name"],
            )
            for option in options
        ]
        assert sort_keys == sorted(sort_keys)


def test_trail_inventory_fixture_records_have_stable_ids_and_labels():
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    items = payload["items"]
    ids = [item["inventory_id"] for item in items]

    assert len(ids) == len(set(ids))
    for item in items:
        assert item["inventory_id"].startswith("vermont_long_trail:")
        assert item["kind"] in {
            "overnight_site",
            "access_point",
            "town",
            "side_trip",
            "trailhead",
            "road_crossing",
            "route_point",
        }
        assert isinstance(item["canonical_mile"], (int, float))
        assert set(item["directional_miles"]) == {"NOBO", "SOBO"}
        assert item["labels"]["NOBO"].startswith("[NOBO Mile ")
        assert item["labels"]["SOBO"].startswith("[SOBO Mile ")
        assert item["selectable_as"]
        assert item["source_artifacts"]


def test_trail_inventory_fixture_links_related_items():
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    items_by_id = {item["inventory_id"]: item for item in payload["items"]}

    for item in payload["items"]:
        for related_id in item.get("related_inventory_ids", []):
            assert related_id in items_by_id


def test_trail_inventory_fixture_contains_expected_manual_planning_examples():
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    items_by_id = {item["inventory_id"]: item for item in payload["items"]}

    bennington = items_by_id["vermont_long_trail:town:vt_9:14.3:bennington"]
    assert bennington["labels"]["NOBO"] == "[NOBO Mile 14.3] Bennington [Vt. 9]"
    assert bennington["labels"]["SOBO"] == "[SOBO Mile 257.8] Bennington [Vt. 9]"
    assert bennington["planner_preference_id"] == "Vt. 9:14.3::Bennington"

    shelter = items_by_id["vermont_long_trail:overnight:overlay_0008"]
    assert shelter["display_name"] == "Seth Warner Shelter"
    assert "overnight_stop" in shelter["selectable_as"]

    access = items_by_id["vermont_long_trail:access:overlay_0033"]
    assert access["kind"] == "trailhead"
    assert "section_boundary" in access["selectable_as"]
    assert access["supported_intents"] == [
        "checkpoint",
        "meet_pickup",
        "resupply",
        "overnight",
    ]

    side_trip = items_by_id["vermont_long_trail:side_trip:lawsons_finest_taproom"]
    assert side_trip["experience"]["validation_status"] == "validated"
    assert "side_trip_preference" in side_trip["selectable_as"]
