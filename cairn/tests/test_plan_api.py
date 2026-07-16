# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0

import base64
import json
from pathlib import Path

from cairn.api.plan_request import (
    PlanAPIRequest,
    PlanAPIValidationError,
)
from cairn.api.plan_options import build_plan_options_response
import cairn.api.http_contract as http_contract
import cairn.api.lambda_handler as lambda_handler
import cairn.api.plan_options as plan_options
import cairn.api.plan_service as plan_service


def _valid_plan_api_payload():
    return {
        "trail_id": "vermont_long_trail",
        "direction": "NOBO",
        "ingress_route": "North Adams Approach",
        "egress_route": "Journey's End Trail",
        "desired_days": 28,
        "min_daily_miles": 8,
        "max_daily_miles": 15,
        "max_daily_elevation": 4000,
        "resupply_cadence": 5,
        "recovery_cadence": 6,
    }


def test_plan_api_request_builds_streamlit_equivalent_config():
    request = PlanAPIRequest.from_payload(
        {
            "trail_id": "vermont_long_trail",
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "egress_route": "Journey's End Trail",
            "desired_days": 28,
            "min_daily_miles": 8,
            "max_daily_miles": 15,
            "max_daily_elevation": 4000,
            "resupply_cadence": 5,
            "recovery_cadence": 6,
            "planned_start_date": "2026-07-01",
        }
    )

    config = request.to_planner_config()

    assert config["selected_trail"] == "vermont_long_trail"
    assert config["trip_type"] == "THRU"
    assert config["direction"] == "NOBO"
    assert config["ingress_route"] == "North Adams Approach"
    assert config["egress_route"] == "Journey's End Trail"
    assert config["desired_days"] == 28
    assert config["trail_root"].endswith("trails/vermont_long_trail")
    assert config["start_date"] == "2026-07-01"
    assert config["selected_side_trip_ids"] == []
    assert config["selected_town_ids"] == []


def test_plan_api_request_accepts_advanced_streamlit_controls():
    request = PlanAPIRequest.from_payload(
        {
            **_valid_plan_api_payload(),
            "recovery_planning_mode": "target_counts",
            "target_zero_days": 4,
            "target_nero_days": 3,
            "min_nero_miles": 4,
            "max_nero_miles": 9,
            "allow_extra_resupply_only": False,
            "avoid_long_food_carry": False,
            "prefer_bear_box_sites": True,
            "convenient_resupply_distance_miles": 2.5,
            "selected_side_trip_ids": ["lawsons_finest_taproom"],
            "selected_town_ids": ["Mass. 2:-3.8::Williamstown"],
        }
    )

    config = request.to_planner_config()

    assert config["recovery_planning_mode"] == "target_counts"
    assert config["target_zero_days"] == 4
    assert config["target_nero_days"] == 3
    assert config["min_nero_miles"] == 4.0
    assert config["max_nero_miles"] == 9.0
    assert config["allow_extra_resupply_only"] is False
    assert config["avoid_long_food_carry"] is False
    assert config["prefer_bear_box_sites"] is True
    assert config["convenient_resupply_distance_miles"] == 2.5
    assert config["selected_side_trip_ids"] == ["lawsons_finest_taproom"]
    assert config["selected_town_ids"] == ["Mass. 2:-3.8::Williamstown"]
    assert type(request.min_daily_miles) is float
    assert type(request.max_daily_miles) is float
    assert type(request.max_daily_elevation) is float
    assert type(request.min_nero_miles) is float
    assert type(request.max_nero_miles) is float


def test_plan_api_request_defaults_advanced_controls_to_streamlit_defaults():
    request = PlanAPIRequest.from_payload(_valid_plan_api_payload())

    config = request.to_planner_config()

    assert config["recovery_planning_mode"] == "cadence"
    assert config["target_zero_days"] == 0
    assert config["target_nero_days"] == 0
    assert config["min_nero_miles"] == 5.0
    assert config["max_nero_miles"] == 8.0
    assert config["allow_extra_resupply_only"] is True
    assert config["avoid_long_food_carry"] is True
    assert config["prefer_bear_box_sites"] is False
    assert config["convenient_resupply_distance_miles"] == 1.0
    assert config["selected_side_trip_ids"] == []
    assert config["selected_town_ids"] == []


def test_plan_api_request_defaults_target_counts_mode_to_streamlit_counts():
    request = PlanAPIRequest.from_payload(
        {
            **_valid_plan_api_payload(),
            "recovery_planning_mode": "target_counts",
        }
    )

    config = request.to_planner_config()

    assert config["recovery_planning_mode"] == "target_counts"
    assert config["target_zero_days"] == 3
    assert config["target_nero_days"] == 2


def test_plan_api_request_rejects_invalid_advanced_controls():
    invalid_cases = (
        ("recovery_planning_mode", "weekly"),
        ("recovery_planning_mode", ["cadence"]),
        ("recovery_planning_mode", {"mode": "cadence"}),
        ("target_zero_days", -1),
        ("target_zero_days", 11),
        ("target_nero_days", -1),
        ("target_nero_days", 11),
        ("min_nero_miles", 0),
        ("min_nero_miles", 11),
        ("max_nero_miles", 3),
        ("max_nero_miles", 16),
        ("allow_extra_resupply_only", "true"),
        ("avoid_long_food_carry", "false"),
        ("prefer_bear_box_sites", "yes"),
        ("convenient_resupply_distance_miles", 0.25),
        ("convenient_resupply_distance_miles", 5.5),
        ("selected_side_trip_ids", [123]),
        ("selected_town_ids", [None]),
    )

    for field_name, invalid_value in invalid_cases:
        payload = _valid_plan_api_payload()
        payload[field_name] = invalid_value

        try:
            PlanAPIRequest.from_payload(payload)
        except PlanAPIValidationError as error:
            assert field_name in str(error)
        else:
            raise AssertionError(f"Expected PlanAPIValidationError for {field_name}")


def test_plan_api_request_rejects_inverted_nero_range():
    payload = {
        **_valid_plan_api_payload(),
        "min_nero_miles": 9,
        "max_nero_miles": 6,
    }

    try:
        PlanAPIRequest.from_payload(payload)
    except PlanAPIValidationError as error:
        assert "max_nero_miles" in str(error)
    else:
        raise AssertionError("Expected PlanAPIValidationError")


def test_plan_api_request_requires_directional_access_routes():
    payload = _valid_plan_api_payload()
    del payload["ingress_route"]

    try:
        PlanAPIRequest.from_payload(payload)
    except PlanAPIValidationError as error:
        assert "ingress_route" in str(error)
    else:
        raise AssertionError("Expected PlanAPIValidationError")


def test_plan_api_request_rejects_directionally_invalid_access_routes():
    payload = _valid_plan_api_payload()
    payload["direction"] = "SOBO"
    payload["ingress_route"] = "North Adams Approach"
    payload["egress_route"] = "Journey's End Trail"

    try:
        PlanAPIRequest.from_payload(payload)
    except PlanAPIValidationError as error:
        assert "ingress_route" in str(error)
    else:
        raise AssertionError("Expected PlanAPIValidationError")


def test_plan_api_request_rejects_non_long_trail_payload():
    try:
        payload = _valid_plan_api_payload()
        payload["trail_id"] = "custom"
        PlanAPIRequest.from_payload(payload)
    except PlanAPIValidationError as error:
        assert "trail_id" in str(error)
    else:
        raise AssertionError("Expected PlanAPIValidationError")


def test_plan_api_request_rejects_inverted_mileage_range():
    try:
        payload = _valid_plan_api_payload()
        payload["direction"] = "SOBO"
        payload["ingress_route"] = "Journey's End Trail"
        payload["egress_route"] = "North Adams Approach"
        payload["min_daily_miles"] = 18
        payload["max_daily_miles"] = 12
        PlanAPIRequest.from_payload(payload)
    except PlanAPIValidationError as error:
        assert "min_daily_miles" in str(error)
    else:
        raise AssertionError("Expected PlanAPIValidationError")


def test_plan_api_request_rejects_non_finite_numeric_inputs():
    try:
        payload = _valid_plan_api_payload()
        payload["min_daily_miles"] = float("nan")
        PlanAPIRequest.from_payload(payload)
    except PlanAPIValidationError as error:
        assert "min_daily_miles" in str(error)
    else:
        raise AssertionError("Expected PlanAPIValidationError")


def test_plan_api_request_rejects_values_outside_streamlit_envelope():
    invalid_cases = (
        ("desired_days", 2),
        ("min_daily_miles", 3),
        ("max_daily_miles", 7),
        ("max_daily_elevation", 999),
        ("resupply_cadence", 1),
        ("recovery_cadence", 2),
    )

    for field_name, invalid_value in invalid_cases:
        payload = _valid_plan_api_payload()
        payload[field_name] = invalid_value

        try:
            PlanAPIRequest.from_payload(payload)
        except PlanAPIValidationError as error:
            assert field_name in str(error)
        else:
            raise AssertionError(f"Expected PlanAPIValidationError for {field_name}")


def test_build_plan_response_rejects_zero_capacity_payload_before_planner_runs(
    monkeypatch,
):
    def fail_if_planner_runs(*args, **kwargs):
        raise AssertionError("PlannerV2 should not run for invalid Plan API payloads")

    monkeypatch.setattr(plan_service, "PlannerV2", fail_if_planner_runs)

    try:
        plan_service.build_plan_response(
            {
                "trail_id": "vermont_long_trail",
                "direction": "NOBO",
                "ingress_route": "North Adams Approach",
                "egress_route": "Journey's End Trail",
                "desired_days": 2,
                "min_daily_miles": 0,
                "max_daily_miles": 0,
                "max_daily_elevation": 0,
                "resupply_cadence": 1,
                "recovery_cadence": 2,
            },
            build_sha="test-build",
            generated_at="20260521T120000Z",
        )
    except PlanAPIValidationError as error:
        assert "desired_days" in str(error)
    except ZeroDivisionError as error:
        raise AssertionError("Expected PlanAPIValidationError") from error
    else:
        raise AssertionError("Expected PlanAPIValidationError")


def test_build_plan_response_returns_cairnos_plan_v1():
    payload = plan_service.build_plan_response(
        {
            "trail_id": "vermont_long_trail",
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "egress_route": "Journey's End Trail",
            "desired_days": 30,
            "min_daily_miles": 8,
            "max_daily_miles": 15,
            "max_daily_elevation": 4000,
            "resupply_cadence": 5,
            "recovery_cadence": 6,
            "planned_start_date": "2026-07-01",
        },
        build_sha="test-build",
        generated_at="20260521T120000Z",
    )

    assert payload["export_version"] == "cairnos_plan_v1"
    assert payload["trail_id"] == "vermont_long_trail"
    assert payload["planner"]["direction"] == "NOBO"
    assert payload["build_sha"] == "test-build"
    assert payload["generated_at"] == "20260521T120000Z"
    assert payload["daily_plan"]
    assert payload["warnings"]


def test_build_plan_response_includes_route_gpx_artifacts():
    payload = plan_service.build_plan_response(
        {
            "trail_id": "vermont_long_trail",
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "egress_route": "Journey's End Trail",
            "desired_days": 30,
            "min_daily_miles": 8,
            "max_daily_miles": 15,
            "max_daily_elevation": 4000,
            "resupply_cadence": 5,
            "recovery_cadence": 6,
        },
        build_sha="test-build",
        generated_at="20260521T120000Z",
    )

    route_gpx = payload["route_gpx"]

    assert (
        route_gpx["export_version"]
        == "cairnos_route_gpx_v1"
    )
    assert route_gpx["geometry_mode"] == "waypoint_only"
    assert route_gpx["direction"] == "NOBO"
    assert len(route_gpx["manifest"]) == (
        len(payload["daily_plan"]) + 1
    )
    assert set(route_gpx["artifacts"]) == {
        entry["filename"]
        for entry in route_gpx["manifest"]
    }
    assert route_gpx["manifest"][0]["scope"] == "full_plan"


def test_build_plan_options_response_returns_cairnos_owned_choices():
    payload = build_plan_options_response("vermont_long_trail")

    assert payload["trail_id"] == "vermont_long_trail"
    assert payload["status"] == "available"
    assert payload["control_specs"]
    assert payload["side_trip_options"]
    assert payload["town_options"]

    _assert_unique_nonempty_option_ids(payload["side_trip_options"])
    _assert_unique_nonempty_option_ids(payload["town_options"])

    side_trips = _options_by_id(payload["side_trip_options"])
    assert side_trips["lawsons_finest_taproom"]["label"] == (
        "Lawson's Finest Taproom - Waitsfield (half-day)"
    )
    assert side_trips["lawsons_finest_taproom"]["name"] == (
        "Lawson's Finest Taproom"
    )
    assert side_trips["lawsons_finest_taproom"]["nobo_mile"] == "162.9"
    assert side_trips["lawsons_finest_taproom"]["sobo_mile"] == "109.2"
    assert side_trips["lawsons_finest_taproom"]["exit_point"] == "Vt. 17"
    assert side_trips["lawsons_finest_taproom"]["access_distance_miles"] == "7"
    assert side_trips["lawsons_finest_taproom"]["access_notes"] == (
        "7 miles east from Long Trail to Waitsfield"
    )
    assert side_trips["lawsons_finest_taproom"]["town_access"] == "Waitsfield"
    assert side_trips["lawsons_finest_taproom"]["category"] == "brewery"
    assert side_trips["lawsons_finest_taproom"]["estimated_time"] == "half-day"

    towns = _options_by_id(payload["town_options"])
    assert towns["Mass. 2:-3.8::Williamstown"]["label"] == (
        "Williamstown - town stop (Mass. 2)"
    )
    assert towns["Vt. 9:14.3::Bennington"]["label"] == (
        "Bennington - town stop (Vt. 9)"
    )
    assert towns["Vt. 9:14.3::Bennington"]["nobo_mile"] == "14.3"
    assert towns["Vt. 9:14.3::Bennington"]["sobo_mile"] == "257.8"
    assert towns["Vt. 9:14.3::Bennington"]["exit_point"] == "Vt. 9"
    assert towns["Vt. 9:14.3::Bennington"]["access_notes"] == (
        "4+ miles west from Long Trail to Bennington"
    )
    assert towns["Mass. 2:-3.8::Williamstown"]["town_name"] == "Williamstown"
    assert towns["Mass. 2:-3.8::North Adams"]["label"] == (
        "North Adams - town stop (Mass. 2)"
    )
    assert towns["Mass. 2:-3.8::North Adams"]["town_name"] == "North Adams"

    assert {
        "id",
        "label",
        "name",
        "nobo_mile",
        "sobo_mile",
        "exit_point",
        "access_notes",
        "access_distance_miles",
        "town_access",
        "category",
        "estimated_time",
    }.issubset(payload["side_trip_options"][0])
    assert {
        "id",
        "label",
        "nobo_mile",
        "sobo_mile",
        "exit_point",
        "access_notes",
        "town_name",
        "canonical_hint",
        "access_distance_miles",
        "resupply_convenience",
    }.issubset(payload["town_options"][0])


def test_build_plan_options_response_returns_streamlit_control_specs():
    payload = build_plan_options_response("vermont_long_trail")

    controls = _options_by_id(payload["control_specs"])

    assert controls["desired_days"] == {
        "id": "desired_days",
        "label": "Desired Completion Days",
        "input": "slider",
        "value_type": "integer",
        "min": 3,
        "max": 60,
        "default": 28,
        "step": 1,
    }
    assert controls["recovery_planning_mode"] == {
        "id": "recovery_planning_mode",
        "label": "Recovery Planning Mode",
        "input": "select",
        "value_type": "string",
        "default": "cadence",
        "choices": [
            {"value": "cadence", "label": "Cadence"},
            {"value": "target_counts", "label": "Target Counts"},
        ],
    }
    assert controls["avoid_long_food_carry"] == {
        "id": "avoid_long_food_carry",
        "label": "Avoid Long Food Carry",
        "input": "checkbox",
        "value_type": "boolean",
        "default": True,
    }
    assert controls["convenient_resupply_distance_miles"] == {
        "id": "convenient_resupply_distance_miles",
        "label": "Convenient Resupply-Only Access (miles)",
        "input": "slider",
        "value_type": "number",
        "min": 0.5,
        "max": 5.0,
        "default": 1.0,
        "step": 0.5,
    }


def _assert_unique_nonempty_option_ids(options):
    ids = [option["id"] for option in options]

    assert all(isinstance(option_id, str) and option_id for option_id in ids)
    assert len(ids) == len(set(ids))


def _options_by_id(options):
    return {option["id"]: option for option in options}


def test_town_options_skip_rows_without_preference_identity(tmp_path):
    csv_dir = tmp_path / "raw" / "csv"
    csv_dir.mkdir(parents=True)
    (csv_dir / "resupply_amenities.csv").write_text(
        "\n".join(
            (
                "canonical_hint,trail_mile,town_access,"
                "access_distance_miles,resupply_convenience",
                ",12.3,Missing Hint,0.2,high",
                "VT 4,,Missing Mile,0.4,medium",
                "VT 9,99.9,Valid Town,0.8,high",
            )
        ),
        encoding="utf-8",
    )

    options = plan_options._town_options(tmp_path)

    assert [option["id"] for option in options] == ["VT 9:99.9::Valid Town"]
    assert options[0]["label"] == "Valid Town - town stop (VT 9)"


def test_build_plan_options_response_rejects_non_long_trail():
    try:
        build_plan_options_response("custom")
    except PlanAPIValidationError as error:
        assert "trail_id" in str(error)
    else:
        raise AssertionError("Expected PlanAPIValidationError")


def _lambda_event(method="POST", body=None, *, is_base64_encoded=False):
    return {
        "requestContext": {"http": {"method": method}},
        "body": body,
        "isBase64Encoded": is_base64_encoded,
    }


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


def _json_response(response):
    return json.loads(response["body"])


def test_lambda_handler_rejects_get_with_method_not_allowed():
    response = lambda_handler.handler(_lambda_event(method="GET"), None)

    assert response["statusCode"] == 405
    assert _json_response(response)["error"] == "method_not_allowed"


def test_lambda_handler_rejects_v1_non_post_with_method_not_allowed():
    response = lambda_handler.handler({"httpMethod": "PUT", "body": "{}"}, None)

    assert response["statusCode"] == 405
    assert _json_response(response)["error"] == "method_not_allowed"


def test_lambda_handler_returns_plan_options_for_get_options(monkeypatch):
    def stub_build_plan_options_response(trail_id="vermont_long_trail"):
        return {
            "trail_id": trail_id,
            "status": "available",
            "side_trip_options": [{"id": "lawsons_finest_taproom", "label": "Lawson's"}],
            "town_options": [{"id": "Mass. 2:-3.8::Williamstown", "label": "Williamstown"}],
        }

    monkeypatch.setattr(
        http_contract,
        "build_plan_options_response",
        stub_build_plan_options_response,
    )

    response = lambda_handler.handler(_lambda_get_event("/plan/options"), None)

    assert response["statusCode"] == 200
    payload = _json_response(response)
    assert payload["trail_id"] == "vermont_long_trail"
    assert payload["side_trip_options"][0]["id"] == "lawsons_finest_taproom"


def test_lambda_handler_returns_plan_options_for_get_options_trailing_slash(
    monkeypatch,
):
    def stub_build_plan_options_response(trail_id="vermont_long_trail"):
        return {
            "trail_id": trail_id,
            "status": "available",
            "side_trip_options": [{"id": "lawsons_finest_taproom"}],
            "town_options": [{"id": "Mass. 2:-3.8::Williamstown"}],
        }

    monkeypatch.setattr(
        http_contract,
        "build_plan_options_response",
        stub_build_plan_options_response,
    )

    response = lambda_handler.handler(_lambda_get_event("/plan/options/"), None)

    assert response["statusCode"] == 200
    assert _json_response(response)["trail_id"] == "vermont_long_trail"


def test_lambda_template_routes_plan_options_paths():
    template = Path("template.lambda.yaml").read_text(encoding="utf-8")

    assert "Path: /plan/options" in template
    assert "Path: /options" in template


def test_lambda_handler_rejects_get_for_unowned_options_suffix(monkeypatch):
    def fail_if_called(trail_id="vermont_long_trail"):
        raise AssertionError("Unexpected options builder call")

    monkeypatch.setattr(
        http_contract,
        "build_plan_options_response",
        fail_if_called,
    )

    response = lambda_handler.handler(_lambda_get_event("/v1/options"), None)

    assert response["statusCode"] == 405
    assert _json_response(response)["error"] == "method_not_allowed"


def test_lambda_handler_maps_unexpected_plan_options_errors_without_leaking_details(
    monkeypatch,
):
    def fail_options(trail_id="vermont_long_trail"):
        raise RuntimeError("private options traceback")

    monkeypatch.setattr(
        http_contract,
        "build_plan_options_response",
        fail_options,
    )

    response = lambda_handler.handler(_lambda_get_event("/plan/options"), None)

    assert response["statusCode"] == 500
    payload = _json_response(response)
    assert payload == {"error": "internal_error"}
    assert "private options traceback" not in response["body"]


def test_lambda_handler_rejects_invalid_json_post():
    response = lambda_handler.handler(_lambda_event(body="{not-json"), None)

    assert response["statusCode"] == 400
    assert _json_response(response)["error"] == "invalid_json"


def test_lambda_handler_rejects_malformed_base64_body():
    response = lambda_handler.handler(
        _lambda_event(body="not-base64!", is_base64_encoded=True),
        None,
    )

    assert response["statusCode"] == 400
    assert _json_response(response)["error"] == "invalid_json"


def test_lambda_handler_rejects_body_over_configured_max(monkeypatch):
    monkeypatch.setenv("CAIRNOS_API_MAX_BODY_BYTES", "8")

    response = lambda_handler.handler(_lambda_event(body='{"wide": true}'), None)

    assert response["statusCode"] == 413
    assert _json_response(response)["error"] == "request_too_large"


def test_lambda_handler_ignores_nonpositive_max_body_env(monkeypatch):
    def stub_build_plan_response(payload, build_sha=None):
        return {"export_version": "cairnos_plan_v1"}

    monkeypatch.setenv("CAIRNOS_API_MAX_BODY_BYTES", "-1")
    monkeypatch.setattr(http_contract, "build_plan_response", stub_build_plan_response)

    response = lambda_handler.handler(
        _lambda_event(body=json.dumps(_valid_plan_api_payload())),
        None,
    )

    assert response["statusCode"] == 200
    assert _json_response(response)["export_version"] == "cairnos_plan_v1"


def test_lambda_handler_maps_plan_validation_errors(monkeypatch):
    def reject_payload(payload, build_sha=None):
        raise PlanAPIValidationError("desired_days must be between 3 and 60")

    monkeypatch.setattr(http_contract, "build_plan_response", reject_payload)

    response = lambda_handler.handler(
        _lambda_event(body=json.dumps(_valid_plan_api_payload())), None
    )

    assert response["statusCode"] == 400
    payload = _json_response(response)
    assert payload["error"] == "validation_error"
    assert "desired_days" in payload["message"]


def test_lambda_handler_maps_unexpected_errors_without_leaking_details(monkeypatch):
    def fail_payload(payload, build_sha=None):
        raise RuntimeError("private planner traceback")

    monkeypatch.setattr(http_contract, "build_plan_response", fail_payload)

    response = lambda_handler.handler(
        _lambda_event(body=json.dumps(_valid_plan_api_payload())), None
    )

    assert response["statusCode"] == 500
    payload = _json_response(response)
    assert payload == {"error": "internal_error"}
    assert "private planner traceback" not in response["body"]


def test_lambda_handler_returns_plan_payload_with_security_headers(monkeypatch):
    captured = {}

    def stub_build_plan_response(payload, build_sha=None):
        captured["payload"] = payload
        captured["build_sha"] = build_sha
        return {"export_version": "cairnos_plan_v1", "daily_plan": [{"day": 1}]}

    monkeypatch.setenv("CAIRNOS_BUILD_SHA", "abc123")
    monkeypatch.setattr(http_contract, "build_plan_response", stub_build_plan_response)
    body = base64.b64encode(json.dumps(_valid_plan_api_payload()).encode("utf-8"))

    response = lambda_handler.handler(
        _lambda_event(body=body.decode("ascii"), is_base64_encoded=True),
        None,
    )

    assert response["statusCode"] == 200
    assert response["headers"] == {
        "content-type": "application/json",
        "cache-control": "no-store",
        "x-content-type-options": "nosniff",
    }
    assert _json_response(response)["daily_plan"] == [{"day": 1}]
    assert captured["payload"]["trail_id"] == "vermont_long_trail"
    assert captured["build_sha"] == "abc123"
