# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""FastAPI application boundary for the CairnOS core API."""

from __future__ import annotations

import json
import os
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from cairn.api.http_contract import NO_STORE_HEADERS, max_body_bytes
from cairn.api.plan_options import build_plan_options_response
from cairn.api.plan_request import PlanAPIValidationError
from cairn.api.plan_service import build_plan_response


DEFAULT_BUILD_SHA = "api"


class InvalidJSONError(ValueError):
    """Raised when an HTTP request body is not a JSON object."""


class RequestTooLargeError(ValueError):
    """Raised when an HTTP request body exceeds the configured limit."""


def create_app() -> FastAPI:
    app = FastAPI(
        title="CairnOS API",
        version="0.1.0",
    )

    @app.middleware("http")
    async def add_common_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        for header_name, header_value in NO_STORE_HEADERS.items():
            response.headers[header_name] = header_value
        return response

    @app.exception_handler(InvalidJSONError)
    async def handle_invalid_json_error(
        request: Request,
        error: InvalidJSONError,
    ) -> JSONResponse:
        return _json_response(400, {"error": "invalid_json"})

    @app.exception_handler(RequestTooLargeError)
    async def handle_request_too_large_error(
        request: Request,
        error: RequestTooLargeError,
    ) -> JSONResponse:
        return _json_response(413, {"error": "request_too_large"})

    @app.exception_handler(PlanAPIValidationError)
    async def handle_plan_validation_error(
        request: Request,
        error: PlanAPIValidationError,
    ) -> JSONResponse:
        return _json_response(
            400,
            {
                "error": "validation_error",
                "message": str(error),
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(
        request: Request,
        error: StarletteHTTPException,
    ) -> JSONResponse:
        if error.status_code == 405:
            return _json_response(405, {"error": "method_not_allowed"})
        return _json_response(error.status_code, {"error": "http_error"})

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request,
        error: Exception,
    ) -> JSONResponse:
        return _json_response(500, {"error": "internal_error"})

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/version")
    async def version() -> dict[str, str]:
        return {
            "service": "cairnos-api",
            "runtime": "asgi",
            "build_sha": _build_sha(),
        }

    @app.get("/v1/plan-options")
    async def plan_options() -> dict[str, object]:
        return build_plan_options_response()

    @app.post("/v1/plans")
    async def create_plan(request: Request) -> dict[str, object]:
        payload = await _json_payload(request)
        return build_plan_response(
            payload,
            build_sha=_build_sha(),
        )

    return app


async def _json_payload(request: Request) -> dict[str, object]:
    body = await request.body()
    if len(body) > max_body_bytes():
        raise RequestTooLargeError()
    try:
        payload = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise InvalidJSONError() from None
    if not isinstance(payload, dict):
        raise InvalidJSONError()
    return payload


def _json_response(status_code: int, payload: dict[str, object]) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=payload,
        headers=NO_STORE_HEADERS,
    )


def _build_sha() -> str:
    return os.environ.get("CAIRNOS_BUILD_SHA", DEFAULT_BUILD_SHA)


app = create_app()
