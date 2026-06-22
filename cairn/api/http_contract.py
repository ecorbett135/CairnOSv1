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


DEFAULT_MAX_BODY_BYTES = 32768
DEFAULT_BUILD_SHA = "api"
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


def handle_plan_api_request(
    method: str | None,
    path: str,
    body: bytes,
    *,
    request_build_sha: str | None = None,
) -> HTTPContractResponse:
    normalized_method = _normalize_method(method)
    normalized_path = _normalize_path(path)

    if normalized_method == "GET" and normalized_path in PLAN_OPTIONS_PATHS:
        return plan_options_response()

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
