# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""AWS Lambda proxy adapter for the stateless CairnOS Plan API."""

from __future__ import annotations

import base64
import binascii
import json
import os
from typing import Any, Mapping

from cairn.api.plan_request import PlanAPIValidationError
from cairn.api.plan_service import build_plan_response


DEFAULT_MAX_BODY_BYTES = 32768
HEADERS = {
    "content-type": "application/json",
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
}


def handler(event: Mapping[str, Any], context: object) -> dict[str, Any]:
    """Handle an API Gateway proxy event."""
    if _method(event) != "POST":
        return _json_response(405, {"error": "method_not_allowed"})

    try:
        body_bytes = _body_bytes(event)
    except (binascii.Error, ValueError):
        return _json_response(400, {"error": "invalid_json"})

    if len(body_bytes) > _max_body_bytes():
        return _json_response(413, {"error": "request_too_large"})

    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _json_response(400, {"error": "invalid_json"})

    if not isinstance(payload, dict):
        return _json_response(400, {"error": "invalid_json"})

    try:
        plan_payload = build_plan_response(
            payload,
            build_sha=os.environ.get("CAIRNOS_BUILD_SHA", "api"),
        )
    except PlanAPIValidationError as error:
        return _json_response(
            400,
            {"error": "validation_error", "message": str(error)},
        )

    return _json_response(200, plan_payload)


def _method(event: Mapping[str, Any]) -> str | None:
    request_context = event.get("requestContext")
    if isinstance(request_context, Mapping):
        http = request_context.get("http")
        if isinstance(http, Mapping):
            method = http.get("method")
            if isinstance(method, str):
                return method.upper()

    method = event.get("httpMethod")
    if isinstance(method, str):
        return method.upper()
    return None


def _body_bytes(event: Mapping[str, Any]) -> bytes:
    body = event.get("body")
    if body is None:
        return b""
    if isinstance(body, bytes):
        body_bytes = body
    else:
        body_bytes = str(body).encode("utf-8")
    if event.get("isBase64Encoded") is True:
        return base64.b64decode(body_bytes, validate=True)
    return body_bytes


def _max_body_bytes() -> int:
    try:
        max_body_bytes = int(
            os.environ.get("CAIRNOS_API_MAX_BODY_BYTES", DEFAULT_MAX_BODY_BYTES)
        )
    except ValueError:
        return DEFAULT_MAX_BODY_BYTES
    if max_body_bytes <= 0:
        return DEFAULT_MAX_BODY_BYTES
    return max_body_bytes


def _json_response(status_code: int, payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(payload, separators=(",", ":"), sort_keys=True),
    }
