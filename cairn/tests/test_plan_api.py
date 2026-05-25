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


def _lambda_event(method="POST", body=None, *, is_base64_encoded=False):
    return {
        "requestContext": {"http": {"method": method}},
        "body": body,
        "isBase64Encoded": is_base64_encoded,
    }


def _json_response(response):
    return json.loads(response["body"])


def test_http_adapter_healthz_returns_ok():
    from cairn.api.http_server import handle_http_request

    status, headers, body = handle_http_request("GET", "/healthz", b"")

    assert status == 200
    assert headers["content-type"] == "application/json"
    assert json.loads(body.decode("utf-8")) == {"status": "ok"}


def test_http_adapter_health_alias_returns_ok():
    from cairn.api.http_server import handle_http_request

    status, _headers, body = handle_http_request("GET", "/health", b"")

    assert status == 200
    assert json.loads(body.decode("utf-8")) == {"status": "ok"}


def test_http_adapter_ready_reports_planner_and_data_availability():
    from cairn.api.http_server import handle_http_request

    status, _headers, body = handle_http_request("GET", "/ready", b"")

    payload = json.loads(body.decode("utf-8"))
    assert status == 200
    assert payload["status"] == "ready"
    assert payload["checks"]["planner"] == "ok"
    assert payload["checks"]["long_trail_data"] == "ok"


def test_http_adapter_metrics_returns_human_readable_json():
    from cairn.api import http_server

    http_server.reset_metrics_for_tests()

    status, _headers, body = http_server.handle_http_request("GET", "/metrics", b"")

    payload = json.loads(body.decode("utf-8"))
    assert status == 200
    assert payload["service"] == "cairnos-plan-api"
    assert payload["format"] == "human_json_v1"
    assert payload["prometheus_reserved"] is True
    assert payload["requests"]["total"] == 0
    assert payload["plan"]["successes"] == 0


def test_http_adapter_version_returns_service_metadata(monkeypatch):
    from cairn.api import http_server

    monkeypatch.setenv("CAIRNOS_BUILD_SHA", "local-test")

    status, _headers, body = http_server.handle_http_request("GET", "/version", b"")

    assert status == 200
    assert json.loads(body.decode("utf-8")) == {
        "build_sha": "local-test",
        "service": "cairnos-plan-api",
    }


def test_http_adapter_rejects_non_post_plan_requests():
    from cairn.api.http_server import handle_http_request

    status, _headers, body = handle_http_request("GET", "/plan", b"")

    assert status == 405
    assert json.loads(body.decode("utf-8")) == {"error": "method_not_allowed"}


def test_http_adapter_maps_plan_payload(monkeypatch):
    from cairn.api import http_server

    def stub_build_plan_response(payload, build_sha=None):
        return {"export_version": "cairnos_plan_v1", "build_sha": build_sha, "echo": payload}

    monkeypatch.setattr(http_server, "build_plan_response", stub_build_plan_response)
    monkeypatch.setenv("CAIRNOS_BUILD_SHA", "local-http")

    status, headers, body = http_server.handle_http_request(
        "POST",
        "/plan",
        b'{"selected_trail":"vermont_long_trail"}',
    )

    assert status == 200
    assert headers["cache-control"] == "no-store"
    assert json.loads(body.decode("utf-8")) == {
        "build_sha": "local-http",
        "echo": {"selected_trail": "vermont_long_trail"},
        "export_version": "cairnos_plan_v1",
    }


def test_http_adapter_records_plan_duration_metrics(monkeypatch):
    from cairn.api import http_server

    http_server.reset_metrics_for_tests()

    def stub_build_plan_response(payload, build_sha=None):
        return {"export_version": "cairnos_plan_v1", "daily_plan": [{"day": 1}]}

    monkeypatch.setattr(http_server, "build_plan_response", stub_build_plan_response)

    status, _headers, _body = http_server.handle_http_request(
        "POST",
        "/plan",
        json.dumps(_valid_plan_api_payload()).encode("utf-8"),
    )

    metrics_status, _metrics_headers, metrics_body = http_server.handle_http_request(
        "GET", "/metrics", b""
    )
    metrics = json.loads(metrics_body.decode("utf-8"))

    assert status == 200
    assert metrics_status == 200
    assert metrics["requests"]["total"] == 1
    assert metrics["plan"]["successes"] == 1
    assert metrics["plan"]["last_duration_ms"] >= 0
    assert metrics["plan"]["max_duration_ms"] >= metrics["plan"]["last_duration_ms"]
    assert metrics["plan"]["last_success_at"]


def test_http_adapter_logs_compact_plan_summary(monkeypatch, capsys):
    from cairn.api import http_server

    http_server.reset_metrics_for_tests()

    def stub_build_plan_response(payload, build_sha=None):
        return {"export_version": "cairnos_plan_v1", "daily_plan": [{"day": 1}]}

    monkeypatch.setattr(http_server, "build_plan_response", stub_build_plan_response)

    http_server.handle_http_request(
        "POST",
        "/plan",
        json.dumps(_valid_plan_api_payload()).encode("utf-8"),
    )

    log_payload = json.loads(capsys.readouterr().out.strip())
    assert log_payload["event"] == "plan_request"
    assert log_payload["status_code"] == 200
    assert log_payload["duration_ms"] >= 0
    assert log_payload["trail_id"] == "vermont_long_trail"
    assert "payload" not in log_payload


def test_http_adapter_metrics_separates_client_and_internal_errors():
    from cairn.api import http_server

    http_server.reset_metrics_for_tests()

    http_server.handle_http_request("POST", "/plan", b"{not-json")
    status, _headers, body = http_server.handle_http_request("GET", "/metrics", b"")

    metrics = json.loads(body.decode("utf-8"))
    assert status == 200
    assert metrics["plan"]["client_errors"] == 1
    assert metrics["plan"]["internal_errors"] == 0


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


def test_lambda_handler_maps_unexpected_errors_without_leaking_details(monkeypatch):
    def fail_payload(payload, build_sha=None):
        raise RuntimeError("private planner traceback")

    monkeypatch.setattr(lambda_handler, "build_plan_response", fail_payload)

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
