# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""Shared HTTP contract helpers for CairnOS API adapters."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Mapping

from cairn.api.plan_options import build_plan_options_response
from cairn.api.plan_request import PlanAPIValidationError
from cairn.api.plan_service import build_plan_response
from cairn.api.trail_inventory import build_trail_inventory_response


DEFAULT_MAX_BODY_BYTES = 32768
DEFAULT_BUILD_SHA = "api"
SERVICE_NAME = "cairnos-api"
API_CONTRACT_VERSION = "cairnos_plan_api_v1"
TRAIL_INVENTORY_CONTRACT_VERSION = "cairnos_trail_inventory_v1"
NO_STORE_HEADERS = {
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
}
JSON_HEADERS = {
    "content-type": "application/json",
    **NO_STORE_HEADERS,
}
PLAN_CREATE_PATHS = {"", "/plan", "/v1/plans"}
PLAN_OPTIONS_PATHS = {"/options", "/plan/options", "/v1/plan-options"}
TRAIL_INVENTORY_PATHS = {"/v1/trail-inventory"}
ASGI_SUPPORTED_ROUTES = (
    {
        "method": "GET",
        "path": "/health",
        "contract": "operator",
        "description": "Service health check",
    },
    {
        "method": "GET",
        "path": "/version",
        "contract": "operator",
        "description": "Version summary",
    },
    {
        "method": "GET",
        "path": "/runtime",
        "contract": "operator",
        "description": "Runtime diagnostics",
    },
    {
        "method": "GET",
        "path": "/v1/plan-options",
        "contract": API_CONTRACT_VERSION,
        "description": "Plan option metadata",
    },
    {
        "method": "GET",
        "path": "/v1/trail-inventory",
        "contract": TRAIL_INVENTORY_CONTRACT_VERSION,
        "description": "Trail inventory metadata",
    },
    {
        "method": "POST",
        "path": "/v1/plans",
        "contract": API_CONTRACT_VERSION,
        "description": "Plan generation",
    },
)
LAMBDA_COMPATIBILITY_ROUTES = (
    {"method": "POST", "path": "/plan"},
    {"method": "GET", "path": "/plan/options"},
    {"method": "GET", "path": "/options"},
)


@dataclass(frozen=True)
class HTTPContractResponse:
    status_code: int
    payload: Mapping[str, Any]
    headers: Mapping[str, str]


class InvalidJSONError(ValueError):
    """Raised when an HTTP request body is not a JSON object."""


class RequestTooLargeError(ValueError):
    """Raised when an HTTP request body exceeds the configured limit."""


def max_body_bytes() -> int:
    try:
        configured = int(
            os.environ.get("CAIRNOS_API_MAX_BODY_BYTES", DEFAULT_MAX_BODY_BYTES)
        )
    except ValueError:
        return DEFAULT_MAX_BODY_BYTES
    if configured <= 0:
        return DEFAULT_MAX_BODY_BYTES
    return configured


def build_sha() -> str:
    return os.environ.get("CAIRNOS_BUILD_SHA", DEFAULT_BUILD_SHA)


def version_summary(runtime: str) -> dict[str, Any]:
    return {
        "service": SERVICE_NAME,
        "runtime": runtime,
        "build_sha": build_sha(),
        "api_contract_version": API_CONTRACT_VERSION,
        "max_body_bytes": max_body_bytes(),
        "runtime_diagnostics_path": "/runtime",
    }


def runtime_state(runtime: str) -> dict[str, Any]:
    return {
        "service": SERVICE_NAME,
        "runtime": runtime,
        "build_sha": build_sha(),
        "api_contract_version": API_CONTRACT_VERSION,
        "max_body_bytes": max_body_bytes(),
        "supported_routes": supported_routes(runtime),
        "lambda_compatibility_routes": lambda_compatibility_routes(),
    }


def supported_routes(runtime: str) -> list[dict[str, str]]:
    if runtime == "asgi":
        return [dict(route) for route in ASGI_SUPPORTED_ROUTES]
    return []


def lambda_compatibility_routes() -> list[dict[str, str]]:
    return [dict(route) for route in LAMBDA_COMPATIBILITY_ROUTES]


def handle_plan_api_request(
    method: str | None,
    path: str,
    body: bytes,
    *,
    request_build_sha: str | None = None,
    query_params: Mapping[str, Any] | None = None,
) -> HTTPContractResponse:
    normalized_method = _normalize_method(method)
    normalized_path = _normalize_path(path)

    if normalized_method == "GET" and normalized_path in PLAN_OPTIONS_PATHS:
        return plan_options_response()

    if normalized_method == "GET" and normalized_path in TRAIL_INVENTORY_PATHS:
        direction = str(
            (query_params or {}).get("direction")
            or "NOBO"
        ).upper()
        return trail_inventory_response(
            direction=direction,
            start_access_id=(query_params or {}).get("start_access_id"),
            end_access_id=(query_params or {}).get("end_access_id"),
        )

    if normalized_method == "POST" and normalized_path in PLAN_CREATE_PATHS:
        return create_plan_response(
            body,
            request_build_sha=request_build_sha,
        )

    return method_not_allowed_response()


def request_uses_body(method: str | None, path: str) -> bool:
    return (
        _normalize_method(method) == "POST"
        and _normalize_path(path) in PLAN_CREATE_PATHS
    )


def plan_options_response() -> HTTPContractResponse:
    try:
        return json_response(200, build_plan_options_response())
    except PlanAPIValidationError as error:
        return validation_error_response(error)
    except Exception:
        return internal_error_response()


def trail_inventory_response(
    direction: str = "NOBO",
    start_access_id: str | None = None,
    end_access_id: str | None = None,
) -> HTTPContractResponse:
    try:
        inventory_kwargs: dict[str, Any] = {
            "direction": direction,
        }
        if start_access_id is not None:
            inventory_kwargs["start_access_id"] = start_access_id
        if end_access_id is not None:
            inventory_kwargs["end_access_id"] = end_access_id
        return json_response(
            200,
            build_trail_inventory_response(**inventory_kwargs),
        )
    except PlanAPIValidationError as error:
        return validation_error_response(error)
    except Exception:
        return internal_error_response()


def create_plan_response(
    body: bytes,
    *,
    request_build_sha: str | None = None,
) -> HTTPContractResponse:
    try:
        payload = parse_json_payload(body)
        plan_payload = build_plan_response(
            payload,
            build_sha=request_build_sha or build_sha(),
        )
    except InvalidJSONError:
        return invalid_json_response()
    except RequestTooLargeError:
        return request_too_large_response()
    except PlanAPIValidationError as error:
        return validation_error_response(error)
    except Exception:
        return internal_error_response()
    return json_response(200, plan_payload)


def parse_json_payload(body: bytes) -> dict[str, Any]:
    if len(body) > max_body_bytes():
        raise RequestTooLargeError()
    try:
        payload = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise InvalidJSONError() from None
    if not isinstance(payload, dict):
        raise InvalidJSONError()
    return payload


def json_response(
    status_code: int,
    payload: Mapping[str, Any],
) -> HTTPContractResponse:
    return HTTPContractResponse(
        status_code=status_code,
        payload=payload,
        headers=dict(JSON_HEADERS),
    )


def invalid_json_response() -> HTTPContractResponse:
    return json_response(400, {"error": "invalid_json"})


def request_too_large_response() -> HTTPContractResponse:
    return json_response(413, {"error": "request_too_large"})


def validation_error_response(error: PlanAPIValidationError) -> HTTPContractResponse:
    return json_response(
        400,
        {
            "error": "validation_error",
            "message": str(error),
        },
    )


def method_not_allowed_response() -> HTTPContractResponse:
    return json_response(405, {"error": "method_not_allowed"})


def internal_error_response() -> HTTPContractResponse:
    return json_response(500, {"error": "internal_error"})


def _normalize_method(method: str | None) -> str:
    if method is None:
        return ""
    return method.upper()


def _normalize_path(path: str) -> str:
    if path == "":
        return ""
    return path.rstrip("/")
