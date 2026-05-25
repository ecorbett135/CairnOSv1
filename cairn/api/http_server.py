# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""Persistent local HTTP adapter for the stateless CairnOS Plan API."""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Mapping

from cairn.api.lambda_handler import HEADERS, _max_body_bytes
from cairn.api.plan_request import LONG_TRAIL_ROOT, PlanAPIValidationError
from cairn.api.plan_service import build_plan_response


SERVICE_NAME = "cairnos-plan-api"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 3010
METRICS_FORMAT = "human_json_v1"

_STARTED_AT = time.time()
_METRICS_LOCK = threading.Lock()
_METRICS = {
    "requests_total": 0,
    "request_body_bytes_total": 0,
    "plan_successes": 0,
    "plan_client_errors": 0,
    "plan_validation_errors": 0,
    "plan_internal_errors": 0,
    "plan_duration_total_ms": 0.0,
    "plan_generation_total_ms": 0.0,
    "last_duration_ms": None,
    "last_generation_ms": None,
    "max_duration_ms": 0.0,
    "last_success_at": None,
    "last_error_at": None,
    "last_error_type": None,
}


def handle_http_request(method: str, path: str, body: bytes) -> tuple[int, dict[str, str], bytes]:
    """Return a local HTTP response tuple for a Plan API request."""
    method = method.upper()
    path = path.split("?", 1)[0]

    if path in {"/health", "/healthz"} and method == "GET":
        return _json_response(200, {"status": "ok"})

    if path == "/ready" and method == "GET":
        checks = {
            "planner": "ok",
            "long_trail_data": "ok" if LONG_TRAIL_ROOT.exists() else "missing",
        }
        status = "ready" if all(value == "ok" for value in checks.values()) else "not_ready"
        return _json_response(200 if status == "ready" else 503, {"status": status, "checks": checks})

    if path == "/metrics" and method == "GET":
        return _json_response(200, _metrics_snapshot())

    if path == "/version" and method == "GET":
        return _json_response(
            200,
            {
                "service": SERVICE_NAME,
                "build_sha": os.environ.get("CAIRNOS_BUILD_SHA", "api"),
            },
        )

    if path != "/plan":
        return _json_response(404, {"error": "not_found"})

    if method != "POST":
        return _json_response(405, {"error": "method_not_allowed"})

    request_started = time.perf_counter()
    status_code = 500
    error_type = None
    trail_id = None
    direction = None
    daily_plan_count = None
    warning_count = None
    generation_ms = None

    if len(body) > _max_body_bytes():
        status_code = 413
        error_type = "request_too_large"
        return _finalize_plan_response(
            status_code,
            {"error": error_type},
            request_started,
            generation_ms,
            len(body),
            trail_id,
            direction,
            daily_plan_count,
            warning_count,
            error_type,
        )

    try:
        payload = json.loads(body.decode("utf-8") if body else "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        status_code = 400
        error_type = "invalid_json"
        return _finalize_plan_response(
            status_code,
            {"error": error_type},
            request_started,
            generation_ms,
            len(body),
            trail_id,
            direction,
            daily_plan_count,
            warning_count,
            error_type,
        )

    if not isinstance(payload, dict):
        status_code = 400
        error_type = "invalid_json"
        return _finalize_plan_response(
            status_code,
            {"error": error_type},
            request_started,
            generation_ms,
            len(body),
            trail_id,
            direction,
            daily_plan_count,
            warning_count,
            error_type,
        )

    trail_id = _optional_string(payload.get("trail_id"))
    direction = _optional_string(payload.get("direction"))

    try:
        generation_started = time.perf_counter()
        plan_payload = build_plan_response(
            payload,
            build_sha=os.environ.get("CAIRNOS_BUILD_SHA", "api"),
        )
        generation_ms = _elapsed_ms(generation_started)
        status_code = 200
        daily_plan = plan_payload.get("daily_plan")
        warnings = plan_payload.get("warnings")
        daily_plan_count = len(daily_plan) if isinstance(daily_plan, list) else None
        warning_count = len(warnings) if isinstance(warnings, list) else None
    except PlanAPIValidationError as error:
        status_code = 400
        error_type = "validation_error"
        return _finalize_plan_response(
            status_code,
            {"error": error_type, "message": str(error)},
            request_started,
            generation_ms,
            len(body),
            trail_id,
            direction,
            daily_plan_count,
            warning_count,
            error_type,
        )
    except Exception:
        status_code = 500
        error_type = "internal_error"
        return _finalize_plan_response(
            status_code,
            {"error": error_type},
            request_started,
            generation_ms,
            len(body),
            trail_id,
            direction,
            daily_plan_count,
            warning_count,
            error_type,
        )

    return _finalize_plan_response(
        status_code,
        plan_payload,
        request_started,
        generation_ms,
        len(body),
        trail_id,
        direction,
        daily_plan_count,
        warning_count,
        error_type,
    )


def reset_metrics_for_tests() -> None:
    """Reset local in-memory metrics for focused adapter tests."""
    with _METRICS_LOCK:
        _METRICS.update(
            {
                "requests_total": 0,
                "request_body_bytes_total": 0,
                "plan_successes": 0,
                "plan_client_errors": 0,
                "plan_validation_errors": 0,
                "plan_internal_errors": 0,
                "plan_duration_total_ms": 0.0,
                "plan_generation_total_ms": 0.0,
                "last_duration_ms": None,
                "last_generation_ms": None,
                "max_duration_ms": 0.0,
                "last_success_at": None,
                "last_error_at": None,
                "last_error_type": None,
            }
        )


class CairnOSPlanAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the local SDDC Plan API container."""

    server_version = "CairnOSPlanAPI/1.0"

    def do_GET(self) -> None:
        self._handle()

    def do_POST(self) -> None:
        self._handle()

    def do_OPTIONS(self) -> None:
        self._handle()

    def _handle(self) -> None:
        content_length = int(self.headers.get("content-length", "0") or "0")
        body = self.rfile.read(content_length) if content_length > 0 else b""
        status, headers, payload = handle_http_request(self.command, self.path, body)
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:
        print(
            "%s - - [%s] %s"
            % (self.address_string(), self.log_date_time_string(), format % args),
            flush=True,
        )


def run() -> None:
    """Run the local HTTP server until interrupted."""
    host = os.environ.get("CAIRNOS_API_HOST", DEFAULT_HOST)
    port = int(os.environ.get("CAIRNOS_API_PORT", str(DEFAULT_PORT)))
    server = ThreadingHTTPServer((host, port), CairnOSPlanAPIHandler)
    print(f"{SERVICE_NAME} listening on http://{host}:{port}", flush=True)
    server.serve_forever()


def _json_response(status_code: int, payload: Mapping[str, Any]) -> tuple[int, dict[str, str], bytes]:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return status_code, dict(HEADERS), body


def _finalize_plan_response(
    status_code: int,
    payload: Mapping[str, Any],
    request_started: float,
    generation_ms: float | None,
    request_body_bytes: int,
    trail_id: str | None,
    direction: str | None,
    daily_plan_count: int | None,
    warning_count: int | None,
    error_type: str | None,
) -> tuple[int, dict[str, str], bytes]:
    duration_ms = _elapsed_ms(request_started)
    _record_plan_metrics(
        status_code=status_code,
        duration_ms=duration_ms,
        generation_ms=generation_ms,
        request_body_bytes=request_body_bytes,
        error_type=error_type,
    )
    _log_plan_request(
        status_code=status_code,
        duration_ms=duration_ms,
        generation_ms=generation_ms,
        request_body_bytes=request_body_bytes,
        trail_id=trail_id,
        direction=direction,
        daily_plan_count=daily_plan_count,
        warning_count=warning_count,
        error_type=error_type,
    )
    return _json_response(status_code, payload)


def _record_plan_metrics(
    *,
    status_code: int,
    duration_ms: float,
    generation_ms: float | None,
    request_body_bytes: int,
    error_type: str | None,
) -> None:
    timestamp = _utc_now_iso()
    with _METRICS_LOCK:
        _METRICS["requests_total"] += 1
        _METRICS["request_body_bytes_total"] += request_body_bytes
        _METRICS["last_duration_ms"] = duration_ms
        _METRICS["last_generation_ms"] = generation_ms
        _METRICS["plan_duration_total_ms"] += duration_ms
        if generation_ms is not None:
            _METRICS["plan_generation_total_ms"] += generation_ms
        _METRICS["max_duration_ms"] = max(_METRICS["max_duration_ms"], duration_ms)

        if 200 <= status_code < 300:
            _METRICS["plan_successes"] += 1
            _METRICS["last_success_at"] = timestamp
        elif error_type == "validation_error":
            _METRICS["plan_validation_errors"] += 1
            _METRICS["last_error_at"] = timestamp
            _METRICS["last_error_type"] = error_type
        elif status_code < 500:
            _METRICS["plan_client_errors"] += 1
            _METRICS["last_error_at"] = timestamp
            _METRICS["last_error_type"] = error_type or "client_error"
        else:
            _METRICS["plan_internal_errors"] += 1
            _METRICS["last_error_at"] = timestamp
            _METRICS["last_error_type"] = error_type or "unknown_error"


def _metrics_snapshot() -> dict[str, Any]:
    with _METRICS_LOCK:
        requests_total = _METRICS["requests_total"]
        average_duration_ms = (
            round(_METRICS["plan_duration_total_ms"] / requests_total, 2)
            if requests_total
            else None
        )
        average_generation_ms = (
            round(_METRICS["plan_generation_total_ms"] / requests_total, 2)
            if requests_total
            else None
        )
        return {
            "service": SERVICE_NAME,
            "format": METRICS_FORMAT,
            "prometheus_reserved": True,
            "uptime_seconds": round(time.time() - _STARTED_AT, 2),
            "requests": {
                "total": requests_total,
                "request_body_bytes_total": _METRICS["request_body_bytes_total"],
            },
            "plan": {
                "successes": _METRICS["plan_successes"],
                "client_errors": _METRICS["plan_client_errors"],
                "validation_errors": _METRICS["plan_validation_errors"],
                "internal_errors": _METRICS["plan_internal_errors"],
                "last_duration_ms": _METRICS["last_duration_ms"],
                "average_duration_ms": average_duration_ms,
                "max_duration_ms": _METRICS["max_duration_ms"],
                "last_generation_ms": _METRICS["last_generation_ms"],
                "average_generation_ms": average_generation_ms,
                "last_success_at": _METRICS["last_success_at"],
                "last_error_at": _METRICS["last_error_at"],
                "last_error_type": _METRICS["last_error_type"],
            },
        }


def _log_plan_request(
    *,
    status_code: int,
    duration_ms: float,
    generation_ms: float | None,
    request_body_bytes: int,
    trail_id: str | None,
    direction: str | None,
    daily_plan_count: int | None,
    warning_count: int | None,
    error_type: str | None,
) -> None:
    log_payload = {
        "event": "plan_request",
        "service": SERVICE_NAME,
        "status_code": status_code,
        "duration_ms": duration_ms,
        "plan_generation_ms": generation_ms,
        "request_body_bytes": request_body_bytes,
        "trail_id": trail_id,
        "direction": direction,
        "daily_plan_count": daily_plan_count,
        "warning_count": warning_count,
        "error_type": error_type,
    }
    print(json.dumps(log_payload, separators=(",", ":"), sort_keys=True), flush=True)


def _elapsed_ms(started_at: float) -> float:
    return round((time.perf_counter() - started_at) * 1000, 2)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) else None


if __name__ == "__main__":
    run()
