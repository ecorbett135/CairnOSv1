# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0

from fastapi.testclient import TestClient

import cairn.api.asgi_app as asgi_app


def _client():
    return TestClient(
        asgi_app.create_app(),
        raise_server_exceptions=False,
    )


def test_asgi_app_reports_health_and_version(monkeypatch):
    monkeypatch.setenv("CAIRNOS_BUILD_SHA", "test-sha")
    client = _client()

    health = client.get("/health")
    version = client.get("/version")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert health.headers["cache-control"] == "no-store"
    assert health.headers["x-content-type-options"] == "nosniff"
    assert version.status_code == 200
    assert version.json() == {
        "service": "cairnos-api",
        "runtime": "asgi",
        "build_sha": "test-sha",
    }


def test_asgi_app_returns_plan_options_contract():
    response = _client().get("/v1/plan-options")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trail_id"] == "vermont_long_trail"
    assert payload["status"] == "available"
    assert payload["control_specs"]
    assert payload["side_trip_options"]
    assert payload["town_options"]


def test_asgi_app_delegates_plan_generation(monkeypatch):
    captured = {}

    def stub_build_plan_response(payload, build_sha=None, generated_at=None):
        captured["payload"] = payload
        captured["build_sha"] = build_sha
        captured["generated_at"] = generated_at
        return {
            "export_version": "cairnos_plan_v1",
            "trail_id": payload["trail_id"],
            "build_sha": build_sha,
        }

    monkeypatch.setattr(asgi_app, "build_plan_response", stub_build_plan_response)

    response = _client().post(
        "/v1/plans",
        json={
            "trail_id": "vermont_long_trail",
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "egress_route": "Journey's End Trail",
            "desired_days": 28,
            "min_daily_miles": 8,
            "max_daily_miles": 16,
            "max_daily_elevation": 3500,
            "resupply_cadence": 5,
            "recovery_cadence": 6,
        },
    )

    assert response.status_code == 200
    assert response.json()["export_version"] == "cairnos_plan_v1"
    assert captured["payload"]["trail_id"] == "vermont_long_trail"
    assert captured["build_sha"] == "api"
    assert captured["generated_at"] is None


def test_asgi_app_normalizes_validation_errors():
    response = _client().post(
        "/v1/plans",
        json={
            "trail_id": "custom",
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "egress_route": "Journey's End Trail",
            "desired_days": 28,
            "min_daily_miles": 8,
            "max_daily_miles": 16,
            "max_daily_elevation": 3500,
            "resupply_cadence": 5,
            "recovery_cadence": 6,
        },
    )

    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"
    assert "trail_id" in response.json()["message"]


def test_asgi_app_normalizes_invalid_json():
    response = _client().post(
        "/v1/plans",
        content="{",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json() == {"error": "invalid_json"}


def test_asgi_app_normalizes_method_not_allowed():
    response = _client().get("/v1/plans")

    assert response.status_code == 405
    assert response.json() == {"error": "method_not_allowed"}


def test_asgi_app_redacts_unexpected_errors(monkeypatch):
    def fail_options():
        raise RuntimeError("private options traceback")

    monkeypatch.setattr(asgi_app, "build_plan_options_response", fail_options)

    response = _client().get("/v1/plan-options")

    assert response.status_code == 500
    assert response.json() == {"error": "internal_error"}
    assert "private options traceback" not in response.text
