# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path

import pytest

from cairn.api.plan_request import PlanAPIRequest, PlanAPIValidationError
from cairn.api.plan_service import build_plan_response
from cairn.api.http_contract import create_plan_response
from cairn.api.town_stops import resolve_town_stop_contract
from cairn.api.trail_inventory import build_trail_inventory_response


FIXTURES = Path(__file__).parent / "fixtures" / "plan_api"
WAITSFIELD = "vermont_long_trail:town:vt_17:162.9:waitsfield"
LAWSONS = "vermont_long_trail:side_trip:lawsons_finest_taproom"


def request_payload():
    return json.loads((FIXTURES / "valid_plan_request.json").read_text())


def selection(town_id=WAITSFIELD, intents=None, experiences=None):
    return {
        "town_inventory_id": town_id,
        "intents": intents or ["resupply"],
        "experience_inventory_ids": experiences or [],
    }


def test_town_stop_inventory_is_directional_ordered_and_referential():
    nobo = build_trail_inventory_response(direction="NOBO")
    sobo = build_trail_inventory_response(direction="SOBO")
    items = {item["inventory_id"]: item for item in nobo["items"]}
    assert nobo["town_stop_options"]["contract_version"] == (
        "cairnos_town_stop_options_v1"
    )
    for payload in (nobo, sobo):
        options = payload["town_stop_options"]["options"]
        assert [item["directional_mile"] for item in options] == sorted(
            item["directional_mile"] for item in options
        )
    nobo_waitsfield = next(
        item for item in nobo["town_stop_options"]["options"]
        if item["town_inventory_id"] == WAITSFIELD
    )
    sobo_waitsfield = next(
        item for item in sobo["town_stop_options"]["options"]
        if item["town_inventory_id"] == WAITSFIELD
    )
    assert nobo_waitsfield["directional_mile"] == 162.9
    assert sobo_waitsfield["directional_mile"] == 109.2
    assert nobo_waitsfield["labels"]["NOBO"].startswith("[NOBO Trail Mile 162.9]")
    for option in nobo["town_stop_options"]["options"]:
        assert option["town_inventory_id"] in items
        assert option["access_inventory_id"] in items
        assert option["access_overlay_id"].startswith("overlay_")
        for experience in option["experiences"]:
            assert experience["experience_inventory_id"] in items
            assert experience["town_inventory_id"] == option["town_inventory_id"]
            assert experience["access_inventory_id"] == option["access_inventory_id"]


def test_section_inventory_excludes_towns_outside_extent():
    payload = build_trail_inventory_response(
        direction="NOBO",
        start_access_id="vermont_long_trail:access:overlay_0015",
        end_access_id="vermont_long_trail:access:overlay_0077",
    )
    options = payload["town_stop_options"]["options"]
    extent = payload["route_extent"]
    assert options
    assert all(
        extent["canonical_start_mile"] <= item["canonical_mile"]
        <= extent["canonical_end_mile"]
        for item in options
    )
    assert all("section_relative_mile" in item for item in options)


def test_experience_requires_and_confirms_its_explicit_parent_town():
    payload = request_payload()
    payload["town_stop_selections"] = [
        selection(intents=["experience"], experiences=[LAWSONS])
    ]
    result = build_plan_response(payload, generated_at="20260721T120000Z")
    stop = result["town_stop_status"]["stops"][0]
    assert stop["town_inventory_id"] == WAITSFIELD
    assert stop["experience_inventory_ids"] == [LAWSONS]
    assert result["town_stop_status"]["satisfied_town_stop_ids"] == [WAITSFIELD]


def test_multiple_intents_produce_one_stop_and_one_resupply_truth():
    payload = request_payload()
    payload["town_stop_selections"] = [
        selection(
            intents=["resupply", "zero", "experience"],
            experiences=[LAWSONS],
        )
    ]
    result = build_plan_response(payload, generated_at="20260721T120000Z")
    assert len(result["town_stop_status"]["stops"]) == 1
    assert sum(
        row.get("required_anchor_id") == WAITSFIELD
        for row in result["resupply_plan"]
    ) == 1
    zero_rows = [
        row for row in result["daily_plan"]
        if row.get("town_stop_inventory_id") == WAITSFIELD
        and row.get("town_stop_zero")
    ]
    assert len(zero_rows) == 1
    assert zero_rows[0]["daily_miles"] == 0
    assert zero_rows[0]["date"] == "2026-07-20"


def test_nero_uses_request_control_and_remains_on_selected_access():
    payload = request_payload()
    payload["town_stop_selections"] = [selection(intents=["nero"])]
    with pytest.raises(PlanAPIValidationError, match="nero_max_trail_miles"):
        PlanAPIRequest.from_payload(payload)
    payload["nero_max_trail_miles"] = 9
    with pytest.raises(PlanAPIValidationError) as raised:
        build_plan_response(payload, generated_at="20260721T120000Z")
    assert raised.value.code == "town_stop_nero_infeasible"
    payload["nero_max_trail_miles"] = 10
    result = build_plan_response(payload, generated_at="20260721T120000Z")
    stop = result["town_stop_status"]["stops"][0]
    assert stop["access_inventory_id"] == "vermont_long_trail:access:vt_17:162.9"
    arrival = next(row for row in result["daily_plan"] if row.get("town_stop_nero"))
    assert arrival["daily_miles"] <= 10


def test_shared_access_conflict_is_deterministic():
    payload = request_payload()
    payload["town_stop_selections"] = [
        selection("vermont_long_trail:town:u_s_2:184.8:jonesville"),
        selection("vermont_long_trail:town:u_s_2:184.8:burlington"),
    ]
    request = PlanAPIRequest.from_payload(payload)
    with pytest.raises(PlanAPIValidationError) as raised:
        resolve_town_stop_contract(request)
    assert raised.value.code == "town_stop_shared_access_conflict"
    assert raised.value.context["access_inventory_id"] == (
        "vermont_long_trail:access:u_s_2:184.8"
    )


def test_impossible_and_parent_mismatch_failures_are_structured():
    payload = request_payload()
    payload["town_stop_selections"] = [
        selection(
            "vermont_long_trail:town:vt_17:162.9:waitsfield",
            intents=["experience"],
            experiences=["vermont_long_trail:side_trip:ben_jerrys_factory"],
        )
    ]
    with pytest.raises(PlanAPIValidationError) as raised:
        resolve_town_stop_contract(PlanAPIRequest.from_payload(payload))
    assert raised.value.code == "town_stop_experience_parent_mismatch"
    assert "does not belong" in str(raised.value)

    response = create_plan_response(json.dumps(payload).encode())
    assert response.status_code == 400
    assert response.payload["code"] == "town_stop_experience_parent_mismatch"
    assert response.payload["message"] == (
        "The selected experience does not belong to the selected town."
    )
    assert response.payload["context"] == {
        "town_inventory_id": WAITSFIELD,
        "experience_inventory_id": "vermont_long_trail:side_trip:ben_jerrys_factory",
    }


def test_legacy_request_still_builds_compatible_export():
    result = build_plan_response(request_payload(), generated_at="20260721T120000Z")
    assert result["export_version"] == "cairnos_plan_v1"
    assert result["selected_experiences"] == []
    assert result["town_stop_status"]["requested_town_stop_ids"] == []
