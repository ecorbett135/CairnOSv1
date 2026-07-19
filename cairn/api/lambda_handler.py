# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""AWS Lambda proxy adapter for the stateless CairnOS Plan API."""

from __future__ import annotations

import base64
import binascii
import json
import os
from typing import Any, Mapping

from cairn.api import http_contract


def handler(event: Mapping[str, Any], context: object) -> dict[str, Any]:
    """Handle an API Gateway proxy event."""
    method = _method(event)
    path = _path(event)

    if http_contract.request_uses_body(method, path):
        try:
            body_bytes = _body_bytes(event)
        except (binascii.Error, ValueError):
            return _json_response(http_contract.invalid_json_response())
    else:
        body_bytes = b""

    return _json_response(
        http_contract.handle_plan_api_request(
            method,
            path,
            body_bytes,
            request_build_sha=os.environ.get(
                "CAIRNOS_BUILD_SHA",
                http_contract.DEFAULT_BUILD_SHA,
            ),
            query_params=_query_params(event),
        )
    )


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


def _path(event: Mapping[str, Any]) -> str:
    raw_path = event.get("rawPath")
    if isinstance(raw_path, str):
        return raw_path

    path = event.get("path")
    if isinstance(path, str):
        return path

    request_context = event.get("requestContext")
    if isinstance(request_context, Mapping):
        http = request_context.get("http")
        if isinstance(http, Mapping):
            path_value = http.get("path")
            if isinstance(path_value, str):
                return path_value

    return ""


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


def _query_params(event: Mapping[str, Any]) -> Mapping[str, Any]:
    query_params = event.get("queryStringParameters")
    if isinstance(query_params, Mapping):
        return query_params
    return {}


def _json_response(response: http_contract.HTTPContractResponse) -> dict[str, Any]:
    return {
        "statusCode": response.status_code,
        "headers": dict(response.headers),
        "body": json.dumps(response.payload, separators=(",", ":"), sort_keys=True),
    }
