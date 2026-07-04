# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path

from fastapi.testclient import TestClient

import cairn.api.asgi_app as asgi_app
import cairn.api.http_contract as http_contract
import cairn.api.lambda_handler as lambda_handler
from cairn.api.trail_inventory import build_trail_inventory_response


def _client():
    return TestClient(
        asgi_app.create_app(),
        raise_server_exceptions=False,
    )


def _json_response(response):
    return json.loads(response["body"])


def _lambda_get_event(path):
    return {
        "requestContext": {
            "http": {
                "method": "GET",
                "path": path,
            }
        },
        "rawPath": path,
    }


def _items_by_id(payload):
    return {item["inventory_id"]: item for item in payload["items"]}


def test_build_trail_inventory_response_returns_live_contract_inventory():
    payload = build_trail_inventory_response("vermont_long_trail")

    assert payload["contract_version"] == "cairnos_trail_inventory_v1"
    assert payload["trail_id"] == "vermont_long_trail"
    assert payload["status"] == "available"
    assert payload["direction_model"] == {
        "canonical_mile_system": "northbound_reference",
        "supported_directions": ["NOBO", "SOBO"],
        "section_model": "single_continuous_range",
        "flip_flop_supported": False,
        "trail_total_miles": 272.1,
        "sobo_display_mile_rule": "trail_total_miles - canonical_mile",
    }
    assert payload["source"]["generated_from"] == "promoted_cairnos_artifacts"
    assert len(payload["items"]) > 50
    assert {item["kind"] for item in payload["items"]} == {
        "access_point",
        "overnight_site",
        "side_trip",
        "town",
    }

    ids = [item["inventory_id"] for item in payload["items"]]
    assert len(ids) == len(set(ids))
    items_by_id = _items_by_id(payload)
    for item in payload["items"]:
        for related_id in item.get("related_inventory_ids", []):
            assert related_id in items_by_id


def test_build_trail_inventory_response_includes_key_manual_planning_records():
    payload = build_trail_inventory_response("vermont_long_trail")
    items_by_id = _items_by_id(payload)

    shelter = items_by_id["vermont_long_trail:overnight:overlay_0008"]
    assert shelter["display_name"] == "Seth Warner Shelter"
    assert shelter["labels"]["NOBO"] == "[NOBO Mile 5.5] Seth Warner Shelter"
    assert shelter["labels"]["SOBO"] == "[SOBO Mile 266.6] Seth Warner Shelter"
    assert "overnight_stop" in shelter["selectable_as"]

    bennington = items_by_id["vermont_long_trail:town:vt_9:14.3:bennington"]
    assert bennington["labels"]["NOBO"] == "[NOBO Mile 14.3] Bennington [Vt. 9]"
    assert bennington["labels"]["SOBO"] == "[SOBO Mile 257.8] Bennington [Vt. 9]"
    assert bennington["planner_preference_id"] == "Vt. 9:14.3::Bennington"
    assert "resupply_stop" in bennington["selectable_as"]

    side_trip = items_by_id["vermont_long_trail:side_trip:lawsons_finest_taproom"]
    assert side_trip["labels"]["NOBO"] == (
        "[NOBO Mile 162.9] Lawson's Finest Taproom [Vt. 17]"
    )
    assert side_trip["experience"]["validation_status"] == "validated"
    assert side_trip["planner_preference_id"] == "lawsons_finest_taproom"


def test_asgi_app_returns_trail_inventory_contract():
    response = _client().get("/v1/trail-inventory")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    payload = response.json()
    assert payload["contract_version"] == "cairnos_trail_inventory_v1"
    assert payload["trail_id"] == "vermont_long_trail"
    assert payload["items"]


def test_asgi_runtime_lists_trail_inventory_route():
    response = _client().get("/runtime")

    routes = response.json()["supported_routes"]
    assert {
        "method": "GET",
        "path": "/v1/trail-inventory",
        "contract": "cairnos_trail_inventory_v1",
        "description": "Trail inventory metadata",
    } in routes


def test_lambda_handler_returns_trail_inventory_contract():
    response = lambda_handler.handler(_lambda_get_event("/v1/trail-inventory"), None)

    assert response["statusCode"] == 200
    assert response["headers"]["cache-control"] == "no-store"
    payload = _json_response(response)
    assert payload["contract_version"] == "cairnos_trail_inventory_v1"
    assert payload["trail_id"] == "vermont_long_trail"
    assert payload["items"]


def test_lambda_handler_returns_trail_inventory_for_trailing_slash():
    response = lambda_handler.handler(_lambda_get_event("/v1/trail-inventory/"), None)

    assert response["statusCode"] == 200
    payload = _json_response(response)
    assert payload["contract_version"] == "cairnos_trail_inventory_v1"


def test_lambda_handler_rejects_unowned_inventory_alias():
    response = lambda_handler.handler(_lambda_get_event("/trail-inventory"), None)

    assert response["statusCode"] == 405
    assert _json_response(response) == {"error": "method_not_allowed"}


def test_trail_inventory_errors_do_not_leak_details(monkeypatch):
    def fail_inventory(trail_id="vermont_long_trail"):
        raise RuntimeError("private inventory traceback")

    monkeypatch.setattr(
        http_contract,
        "build_trail_inventory_response",
        fail_inventory,
    )

    response = _client().get("/v1/trail-inventory")

    assert response.status_code == 500
    assert response.json() == {"error": "internal_error"}
    assert "private inventory traceback" not in response.text


def test_lambda_template_routes_trail_inventory_path():
    template = Path("template.lambda.yaml").read_text(encoding="utf-8")

    assert "Path: /v1/trail-inventory" in template
