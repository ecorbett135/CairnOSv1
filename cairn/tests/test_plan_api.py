# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0

import base64
import json

from cairn.api.plan_request import (
    PlanAPIRequest,
    PlanAPIValidationError,
)
import cairn.api.lambda_handler as lambda_handler
import cairn.api.plan_service as plan_service


def _valid_plan_api_payload():
    return {
        "trail_id": "vermont_long_trail",
        "direction": "NOBO",
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
    assert config["desired_days"] == 28
    assert config["trail_root"].endswith("trails/vermont_long_trail")
    assert config["start_date"] == "2026-07-01"
    assert config["selected_side_trip_ids"] == []
    assert config["selected_town_ids"] == []


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


def _lambda_event(method="POST", body=None, *, is_base64_encoded=False):
    return {
        "requestContext": {"http": {"method": method}},
        "body": body,
        "isBase64Encoded": is_base64_encoded,
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
    monkeypatch.setattr(lambda_handler, "build_plan_response", stub_build_plan_response)

    response = lambda_handler.handler(
        _lambda_event(body=json.dumps(_valid_plan_api_payload())),
        None,
    )

    assert response["statusCode"] == 200
    assert _json_response(response)["export_version"] == "cairnos_plan_v1"


def test_lambda_handler_maps_plan_validation_errors(monkeypatch):
    def reject_payload(payload, build_sha=None):
        raise PlanAPIValidationError("desired_days must be between 3 and 60")

    monkeypatch.setattr(lambda_handler, "build_plan_response", reject_payload)

    response = lambda_handler.handler(
        _lambda_event(body=json.dumps(_valid_plan_api_payload())), None
    )

    assert response["statusCode"] == 400
    payload = _json_response(response)
    assert payload["error"] == "validation_error"
    assert "desired_days" in payload["message"]


def test_lambda_handler_returns_plan_payload_with_security_headers(monkeypatch):
    captured = {}

    def stub_build_plan_response(payload, build_sha=None):
        captured["payload"] = payload
        captured["build_sha"] = build_sha
        return {"export_version": "cairnos_plan_v1", "daily_plan": [{"day": 1}]}

    monkeypatch.setenv("CAIRNOS_BUILD_SHA", "abc123")
    monkeypatch.setattr(lambda_handler, "build_plan_response", stub_build_plan_response)
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
