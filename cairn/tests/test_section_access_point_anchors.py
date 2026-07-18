# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0

import copy
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import cairn.api.asgi_app as asgi_app
from cairn.api.plan_request import PlanAPIRequest, PlanAPIValidationError
from cairn.api.plan_options import build_plan_options_response
from cairn.api.plan_service import build_plan_response
from cairn.api.route_selection import (
    NONE_EGRESS_APPROACH_ID,
    NONE_INGRESS_APPROACH_ID,
)
from cairn.api.trail_inventory import build_trail_inventory_response


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "plan_api"
    / "section_access_point_plan_request.json"
)


def _request():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _build(request=None):
    return build_plan_response(
        request or _request(),
        build_sha="section-access-test",
        generated_at="20260701T120000Z",
    )


def test_section_request_normalizes_extent_and_none_route_sentinels():
    request = PlanAPIRequest.from_payload(_request())
    config = request.to_planner_config()

    assert config["trip_type"] == "SECTION"
    assert config["ingress_route"] == "No ingress route"
    assert config["egress_route"] == "No egress route"
    assert config["route_selection"] == {
        "contract_version": "cairnos_route_selection_v1",
        "ingress_approach_id": NONE_INGRESS_APPROACH_ID,
        "egress_approach_id": NONE_EGRESS_APPROACH_ID,
    }
    assert config["route_extent"]["contract_version"] == (
        "cairnos_route_extent_v1"
    )
    assert config["route_extent"]["distance_miles"] == 72.5


def test_plan_options_publish_cairnos_owned_none_sentinels():
    options = build_plan_options_response()["route_selection"]["options"]
    by_id = {option["approach_id"]: option for option in options}

    assert by_id[NONE_INGRESS_APPROACH_ID] == {
        "approach_id": NONE_INGRESS_APPROACH_ID,
        "approach_name": "No ingress route",
        "connected_terminus": None,
        "geometry_status": "not_applicable",
        "geometry_id": None,
        "selectable_roles": ["NOBO_INGRESS", "SOBO_INGRESS"],
        "sentinel": True,
    }
    assert by_id[NONE_EGRESS_APPROACH_ID] == {
        "approach_id": NONE_EGRESS_APPROACH_ID,
        "approach_name": "No egress route",
        "connected_terminus": None,
        "geometry_status": "not_applicable",
        "geometry_id": None,
        "selectable_roles": ["NOBO_EGRESS", "SOBO_EGRESS"],
        "sentinel": True,
    }


def test_section_plan_bounds_basic_and_advanced_behavior_inside_extent():
    payload = _build()
    extent = payload["route_extent"]

    assert payload["planner"]["trip_type"] == "SECTION"
    assert extent["start_access_id"].endswith("overlay_0015")
    assert extent["end_access_id"].endswith("overlay_0077")
    assert extent["canonical_start_mile"] == 14.3
    assert extent["canonical_end_mile"] == 86.8
    assert payload["expedition_summary"]["total_miles"] == 72.5

    daily_plan = payload["daily_plan"]
    assert daily_plan[0]["daily_start_mile"] == 14.3
    assert daily_plan[0]["daily_start_section_mile"] == 0.0
    assert daily_plan[-1]["daily_stop_mile"] == 86.8
    assert daily_plan[-1]["daily_stop_section_mile"] == 72.5
    assert all(
        14.3 <= row["daily_start_mile"] <= 86.8
        and 14.3 <= row["daily_stop_mile"] <= 86.8
        for row in daily_plan
    )

    assert payload["required_anchors"]["satisfied_overnight_anchor_ids"] == [
        "vermont_long_trail:overnight:overlay_0023"
    ]

    basic_request = _request()
    basic_request["required_overnight_anchor_ids"] = []
    basic_request["access_point_anchors"] = []
    basic = _build(basic_request)
    assert basic["daily_plan"][0]["daily_start_mile"] == 14.3
    assert basic["daily_plan"][-1]["daily_stop_mile"] == 86.8


def test_access_point_intents_project_without_conflating_checkpoint_semantics():
    payload = _build()
    contract = payload["access_point_anchors"]
    requested = [
        "vermont_long_trail:access:overlay_0033",
        "vermont_long_trail:access:overlay_0043",
        "vermont_long_trail:access:overlay_0061",
    ]

    assert contract["contract_version"] == "cairnos_access_point_anchors_v1"
    assert contract["requested_access_point_anchor_ids"] == requested
    assert contract["satisfied_access_point_anchor_ids"] == requested
    assert contract["unsatisfied_access_point_anchor_ids"] == []
    assert contract["anchors"][0] == {
        "access_id": requested[0],
        "intent": "meet_pickup",
        "display_name": (
            "Stratton–Arlington/Kelley Stand Road; Stratton Mtn. parking lot"
        ),
        "canonical_mile": 36.9,
        "section_relative_mile": 22.6,
        "date": "2026-07-03",
        "time": "14:00",
        "note": "Meet at Kelley Stand",
        "status": "satisfied",
        "planned_day": 3,
        "planned_date": "2026-07-03",
    }

    meet_row = next(
        row
        for row in payload["daily_plan"]
        if any(
            anchor["access_id"] == requested[0]
            for anchor in row["access_point_anchors"]
        )
    )
    assert meet_row["daily_stop_mile"] != 36.9
    assert meet_row["notes"] != "resupply"

    resupply = next(
        row
        for row in payload["resupply_plan"]
        if row.get("required_anchor_id") == requested[1]
    )
    assert resupply["mile"] == 54.4

    overnight = next(
        row
        for row in payload["daily_plan"]
        if row.get("required_overnight_anchor_id") == requested[2]
    )
    assert overnight["daily_stop_mile"] == 72.0


def test_section_route_gpx_is_bounded_by_extent_without_approach_warnings():
    payload = _build()
    route_gpx = payload["route_gpx"]

    assert route_gpx["route_extent"] == payload["route_extent"]
    assert route_gpx["route_selection"]["ingress_approach_id"] == (
        NONE_INGRESS_APPROACH_ID
    )
    assert route_gpx["route_selection"]["egress_approach_id"] == (
        NONE_EGRESS_APPROACH_ID
    )
    full_plan = route_gpx["manifest"][0]
    assert len(full_plan["geometry_sources"]) == 1
    source = full_plan["geometry_sources"][0]
    assert {
        key: source[key]
        for key in (
            "role",
            "source",
            "geometry_id",
            "canonical_min_mile",
            "canonical_max_mile",
        )
    } == {
        "role": "spine",
        "source": "compiled/spine.geojson",
        "geometry_id": "defined_trail_spine",
        "canonical_min_mile": 14.3,
        "canonical_max_mile": 86.8,
    }
    assert [part["role"] for part in route_gpx["route_parts"]] == ["spine"]
    assert route_gpx["route_completeness"]["selected_route_part_count"] == 1
    assert route_gpx["route_completeness"]["unavailable_route_part_ids"] == []
    assert not any(
        warning["code"] in {
            "full_plan_spine_only",
            "selected_route_geometry_unavailable",
        }
        for warning in route_gpx["warnings"]
    )


def test_sobo_section_reverses_endpoint_anchor_and_option_order():
    request = _request()
    request.update(
        {
            "direction": "SOBO",
            "start_access_id": "vermont_long_trail:access:overlay_0077",
            "end_access_id": "vermont_long_trail:access:overlay_0015",
            "required_overnight_anchor_ids": [
                "vermont_long_trail:overnight:overlay_0067"
            ],
            "access_point_anchors": list(
                reversed(request["access_point_anchors"])
            ),
        }
    )
    payload = _build(request)

    assert payload["daily_plan"][0]["daily_start_mile"] == 86.8
    assert payload["daily_plan"][-1]["daily_stop_mile"] == 14.3
    assert payload["daily_plan"][0]["daily_start_section_mile"] == 0.0
    assert payload["daily_plan"][-1]["daily_stop_section_mile"] == 72.5
    assert payload["access_point_anchors"][
        "satisfied_access_point_anchor_ids"
    ] == [
        "vermont_long_trail:access:overlay_0061",
        "vermont_long_trail:access:overlay_0043",
        "vermont_long_trail:access:overlay_0033",
    ]

    inventory = build_trail_inventory_response(
        direction="SOBO",
        start_access_id=request["start_access_id"],
        end_access_id=request["end_access_id"],
    )
    for key in ("checkpoint_options",):
        miles = [option["directional_mile"] for option in inventory[key]]
        assert miles == sorted(miles)
    for key in ("overnight", "resupply"):
        miles = [
            option["directional_mile"]
            for option in inventory["required_anchor_options"][key]
        ]
        assert miles == sorted(miles)


@pytest.mark.parametrize(
    ("updates", "message"),
    (
        (
            {
                "start_access_id": "vermont_long_trail:access:overlay_0077",
                "end_access_id": "vermont_long_trail:access:overlay_0015",
            },
            "SECTION endpoints are reversed for NOBO",
        ),
        (
            {"start_access_id": "unknown"},
            "start_access_id contains unknown access_id",
        ),
    ),
)
def test_section_rejects_reversed_or_unknown_endpoints(updates, message):
    request = _request()
    request.update(updates)
    with pytest.raises(PlanAPIValidationError, match=message):
        PlanAPIRequest.from_payload(request)


def test_section_rejects_access_and_required_anchors_outside_extent():
    request = _request()
    request["access_point_anchors"] = [
        {
            "access_id": "vermont_long_trail:access:overlay_0090",
            "intent": "checkpoint",
        }
    ]
    with pytest.raises(PlanAPIValidationError, match="outside the selected extent"):
        PlanAPIRequest.from_payload(request)

    request = _request()
    request["required_overnight_anchor_ids"] = [
        "vermont_long_trail:overnight:overlay_0008"
    ]
    with pytest.raises(PlanAPIValidationError, match="outside the selected extent"):
        _build(request)

    request = _request()
    request["required_overnight_anchor_ids"] = []
    request["required_resupply_anchor_ids"] = [
        "vermont_long_trail:access:vt_125:134.0"
    ]
    with pytest.raises(PlanAPIValidationError, match="outside the selected extent"):
        _build(request)


def test_inventory_extent_filters_checkpoint_overnight_and_resupply_options():
    payload = build_trail_inventory_response(
        direction="NOBO",
        start_access_id="vermont_long_trail:access:overlay_0015",
        end_access_id="vermont_long_trail:access:overlay_0077",
    )
    extent = payload["route_extent"]
    assert extent["distance_miles"] == 72.5
    assert payload["access_point_options"][0]["directional_mile"] < (
        payload["access_point_options"][-1]["directional_mile"]
    )
    assert all(
        14.3 < option["canonical_mile"] < 86.8
        for option in payload["checkpoint_options"]
    )
    for anchor_type in ("overnight", "resupply"):
        options = payload["required_anchor_options"][anchor_type]
        assert all(14.3 <= option["canonical_mile"] <= 86.8 for option in options)
        assert all("section_relative_mile" in option for option in options)


def test_asgi_inventory_accepts_extent_query_and_rejects_partial_extent():
    client = TestClient(asgi_app.create_app(), raise_server_exceptions=False)
    response = client.get(
        "/v1/trail-inventory",
        params={
            "direction": "NOBO",
            "start_access_id": "vermont_long_trail:access:overlay_0015",
            "end_access_id": "vermont_long_trail:access:overlay_0077",
        },
    )
    assert response.status_code == 200
    assert response.json()["route_extent"]["distance_miles"] == 72.5

    partial = client.get(
        "/v1/trail-inventory",
        params={"start_access_id": "vermont_long_trail:access:overlay_0015"},
    )
    assert partial.status_code == 400
    assert partial.json()["message"] == (
        "start_access_id and end_access_id must be provided together"
    )


def test_thru_defaults_remain_additive_and_allow_non_stopping_checkpoint():
    request = _request()
    thru = {
        key: value
        for key, value in copy.deepcopy(request).items()
        if key not in {"trip_type", "start_access_id", "end_access_id"}
    }
    thru.update(
        {
            "ingress_route": "North Adams Approach",
            "egress_route": "Journey's End Trail",
            "desired_days": 30,
            "required_overnight_anchor_ids": [],
            "access_point_anchors": [
                {
                    "access_id": "vermont_long_trail:access:overlay_0033",
                    "intent": "checkpoint",
                }
            ],
        }
    )
    payload = _build(thru)
    assert payload["planner"]["trip_type"] == "THRU"
    assert payload["route_extent"]["extent_type"] == "full_trail"
    checkpoint = payload["access_point_anchors"]["anchors"][0]
    assert checkpoint["intent"] == "checkpoint"
    checkpoint_row = next(
        row
        for row in payload["daily_plan"]
        if row["access_point_anchors"]
    )
    assert checkpoint_row["daily_stop_mile"] != checkpoint["canonical_mile"]
