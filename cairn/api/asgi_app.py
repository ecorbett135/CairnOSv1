# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""FastAPI application boundary for the CairnOS core API."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from cairn.api import http_contract
from cairn.api.http_contract import NO_STORE_HEADERS


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

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(
        request: Request,
        error: StarletteHTTPException,
    ) -> JSONResponse:
        if error.status_code == 405:
            return _json_response(http_contract.method_not_allowed_response())
        return _json_response(
            http_contract.json_response(error.status_code, {"error": "http_error"})
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request,
        error: Exception,
    ) -> JSONResponse:
        return _json_response(http_contract.internal_error_response())

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/version")
    async def version() -> dict[str, object]:
        return http_contract.version_summary("asgi")

    @app.get("/runtime")
    async def runtime() -> dict[str, object]:
        return http_contract.runtime_state("asgi")

    @app.get("/v1/plan-options")
    async def plan_options() -> JSONResponse:
        return _json_response(
            http_contract.handle_plan_api_request("GET", "/v1/plan-options", b"")
        )

    @app.post("/v1/plans")
    async def create_plan(request: Request) -> JSONResponse:
        return _json_response(
            http_contract.handle_plan_api_request(
                "POST",
                "/v1/plans",
                await request.body(),
            )
        )

    return app


def _json_response(response: http_contract.HTTPContractResponse) -> JSONResponse:
    return JSONResponse(
        status_code=response.status_code,
        content=response.payload,
        headers=response.headers,
    )


app = create_app()
