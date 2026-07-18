# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path

from fastapi.testclient import TestClient

import cairn.api.asgi_app as asgi_app
import cairn.api.http_contract as http_contract
import cairn.api.lambda_handler as lambda_handler
from cairn.api.plan_request import PlanAPIValidationError


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "plan_api"


def _fixture_text(name):
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def _asgi_client():
    return TestClient(
        asgi_app.create_app(),
        raise_server_exceptions=False,
    )


def _lambda_event(method, path, body=None):
    return {
        "requestContext": {
            "http": {
                "method": method,
                "path": path,
            }
        },
        "rawPath": path,
        "body": body,
        "isBase64Encoded": False,
    }


def _lambda_body(response):
    return json.loads(response["body"])


def _assert_common_headers(asgi_response, lambda_response):
    for header_name, header_value in http_contract.JSON_HEADERS.items():
        assert asgi_response.headers[header_name] == header_value
        assert lambda_response["headers"][header_name] == header_value


def test_asgi_and_lambda_share_fixture_backed_plan_success(monkeypatch):
    fixture_text = _fixture_text("valid_plan_request.json")
    captured = []

    def stub_build_plan_response(payload, build_sha=None, generated_at=None):
        captured.append(
            {
                "trail_id": payload["trail_id"],
                "build_sha": build_sha,
                "generated_at": generated_at,
            }
        )
        return {
            "export_version": "cairnos_plan_v1",
            "trail_id": payload["trail_id"],
            "build_sha": build_sha,
            "runtime_contract": "shared",
        }

    monkeypatch.setenv("CAIRNOS_BUILD_SHA", "parity-sha")
    monkeypatch.setattr(
        http_contract,
        "build_plan_response",
        stub_build_plan_response,
        raising=False,
    )

    asgi_response = _asgi_client().post(
        "/v1/plans",
        content=fixture_text,
        headers={"content-type": "application/json"},
    )
    lambda_response = lambda_handler.handler(
        _lambda_event("POST", "/plan", fixture_text),
        None,
    )

    expected_body = {
        "export_version": "cairnos_plan_v1",
        "trail_id": "vermont_long_trail",
        "build_sha": "parity-sha",
        "runtime_contract": "shared",
    }
    assert asgi_response.status_code == 200
    assert lambda_response["statusCode"] == 200
    assert asgi_response.json() == expected_body
    assert _lambda_body(lambda_response) == expected_body
    assert captured == [
        {
            "trail_id": "vermont_long_trail",
            "build_sha": "parity-sha",
            "generated_at": None,
        },
        {
            "trail_id": "vermont_long_trail",
            "build_sha": "parity-sha",
            "generated_at": None,
        },
    ]
    _assert_common_headers(asgi_response, lambda_response)


def test_asgi_and_lambda_share_options_success(monkeypatch):
    expected_body = {
        "trail_id": "vermont_long_trail",
        "status": "available",
        "control_specs": [{"id": "desired_days"}],
        "side_trip_options": [{"id": "lawsons_finest_taproom"}],
        "town_options": [{"id": "Mass. 2:-3.8::Williamstown"}],
    }

    monkeypatch.setattr(
        http_contract,
        "build_plan_options_response",
        lambda trail_id="vermont_long_trail": expected_body,
        raising=False,
    )

    asgi_response = _asgi_client().get("/v1/plan-options")
    lambda_response = lambda_handler.handler(
        _lambda_event("GET", "/plan/options"),
        None,
    )

    assert asgi_response.status_code == 200
    assert lambda_response["statusCode"] == 200
    assert asgi_response.json() == expected_body
    assert _lambda_body(lambda_response) == expected_body
    _assert_common_headers(asgi_response, lambda_response)


def test_asgi_and_lambda_share_trail_inventory_success(monkeypatch):
    expected_body = {
        "contract_version": "cairnos_trail_inventory_v1",
        "trail_id": "vermont_long_trail",
        "status": "available",
        "direction_model": {"supported_directions": ["NOBO", "SOBO"]},
        "source": {"generated_from": "test"},
        "items": [{"inventory_id": "vermont_long_trail:route_point:test"}],
    }

    monkeypatch.setattr(
        http_contract,
        "build_trail_inventory_response",
        lambda trail_id="vermont_long_trail", direction="NOBO": expected_body,
        raising=False,
    )

    asgi_response = _asgi_client().get("/v1/trail-inventory")
    lambda_response = lambda_handler.handler(
        _lambda_event("GET", "/v1/trail-inventory"),
        None,
    )

    assert asgi_response.status_code == 200
    assert lambda_response["statusCode"] == 200
    assert asgi_response.json() == expected_body
    assert _lambda_body(lambda_response) == expected_body
    _assert_common_headers(asgi_response, lambda_response)


def test_asgi_and_lambda_share_validation_error_normalization(monkeypatch):
    fixture_text = _fixture_text("valid_plan_request.json")

    def reject_payload(payload, build_sha=None, generated_at=None):
        raise PlanAPIValidationError("trail_id must be vermont_long_trail")

    monkeypatch.setattr(
        http_contract,
        "build_plan_response",
        reject_payload,
        raising=False,
    )

    asgi_response = _asgi_client().post(
        "/v1/plans",
        content=fixture_text,
        headers={"content-type": "application/json"},
    )
    lambda_response = lambda_handler.handler(
        _lambda_event("POST", "/plan", fixture_text),
        None,
    )

    expected_body = {
        "error": "validation_error",
        "message": "trail_id must be vermont_long_trail",
    }
    assert asgi_response.status_code == 400
    assert lambda_response["statusCode"] == 400
    assert asgi_response.json() == expected_body
    assert _lambda_body(lambda_response) == expected_body
    _assert_common_headers(asgi_response, lambda_response)


def test_asgi_and_lambda_share_unexpected_error_redaction(monkeypatch):
    fixture_text = _fixture_text("valid_plan_request.json")

    def fail_payload(payload, build_sha=None, generated_at=None):
        raise RuntimeError("private parity traceback")

    monkeypatch.setattr(
        http_contract,
        "build_plan_response",
        fail_payload,
        raising=False,
    )

    asgi_response = _asgi_client().post(
        "/v1/plans",
        content=fixture_text,
        headers={"content-type": "application/json"},
    )
    lambda_response = lambda_handler.handler(
        _lambda_event("POST", "/plan", fixture_text),
        None,
    )

    expected_body = {"error": "internal_error"}
    assert asgi_response.status_code == 500
    assert lambda_response["statusCode"] == 500
    assert asgi_response.json() == expected_body
    assert _lambda_body(lambda_response) == expected_body
    assert "private parity traceback" not in asgi_response.text
    assert "private parity traceback" not in lambda_response["body"]
    _assert_common_headers(asgi_response, lambda_response)


def test_asgi_and_lambda_share_request_size_limit(monkeypatch):
    monkeypatch.setenv("CAIRNOS_API_MAX_BODY_BYTES", "8")
    fixture_text = _fixture_text("valid_plan_request.json")

    asgi_response = _asgi_client().post(
        "/v1/plans",
        content=fixture_text,
        headers={"content-type": "application/json"},
    )
    lambda_response = lambda_handler.handler(
        _lambda_event("POST", "/plan", fixture_text),
        None,
    )

    expected_body = {"error": "request_too_large"}
    assert asgi_response.status_code == 413
    assert lambda_response["statusCode"] == 413
    assert asgi_response.json() == expected_body
    assert _lambda_body(lambda_response) == expected_body
    _assert_common_headers(asgi_response, lambda_response)
