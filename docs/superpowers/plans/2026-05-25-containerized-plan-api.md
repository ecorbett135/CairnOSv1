# Containerized Plan API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a persistent Docker-hosted CairnOS Plan API for SDDC-local development while preserving the existing Lambda/SAM path.

**Architecture:** Keep `cairn.api.plan_service.build_plan_response()` as the shared service boundary. Add a small standard-library HTTP adapter for local containers, and keep `cairn.api.lambda_handler` as the AWS Lambda/API Gateway adapter. Docker Compose will expose the persistent local API on `127.0.0.1:3010`.

**Tech Stack:** Python 3.11 standard library HTTP server, pytest, Docker, Docker Compose.

---

## File Structure

- Create `cairn/api/http_server.py`: persistent local HTTP adapter with `POST /plan`, `GET /healthz`, and `GET /version`.
- Create `Dockerfile.api`: local SDDC Plan API image using `python:3.11-slim`.
- Create `docker-compose.yml`: local service named `cairnos-plan-api` bound to `127.0.0.1:3010`.
- Modify `cairn/tests/test_plan_api.py`: add contract tests for the HTTP adapter.
- Modify `docs/PLAN_API.md`: document the persistent Docker path and SAM’s Lambda-parity role.

## Task 1: HTTP Adapter Contract

**Files:**
- Create: `cairn/api/http_server.py`
- Modify: `cairn/tests/test_plan_api.py`

- [ ] **Step 1: Write failing HTTP adapter tests**

Add tests to `cairn/tests/test_plan_api.py`:

```python
def test_http_adapter_healthz_returns_ok():
    from cairn.api.http_server import handle_http_request

    status, headers, body = handle_http_request("GET", "/healthz", b"")

    assert status == 200
    assert headers["content-type"] == "application/json"
    assert json.loads(body.decode("utf-8")) == {"status": "ok"}


def test_http_adapter_version_returns_service_metadata(monkeypatch):
    from cairn.api import http_server

    monkeypatch.setenv("CAIRNOS_BUILD_SHA", "local-test")

    status, _headers, body = http_server.handle_http_request("GET", "/version", b"")

    assert status == 200
    assert json.loads(body.decode("utf-8")) == {
        "service": "cairnos-plan-api",
        "build_sha": "local-test",
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
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
.venv/bin/python -m pytest cairn/tests/test_plan_api.py -k "http_adapter" -q
```

Expected: fail because `cairn.api.http_server` does not exist.

- [ ] **Step 3: Implement the HTTP adapter**

Create `cairn/api/http_server.py` with:

```python
# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""Persistent local HTTP adapter for the stateless CairnOS Plan API."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Mapping

from cairn.api.lambda_handler import DEFAULT_MAX_BODY_BYTES, HEADERS, _max_body_bytes
from cairn.api.plan_request import PlanAPIValidationError
from cairn.api.plan_service import build_plan_response


SERVICE_NAME = "cairnos-plan-api"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 3010


def handle_http_request(method: str, path: str, body: bytes) -> tuple[int, dict[str, str], bytes]:
    method = method.upper()
    path = path.split("?", 1)[0]

    if path == "/healthz" and method == "GET":
        return _json_response(200, {"status": "ok"})

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

    if len(body) > _max_body_bytes():
        return _json_response(413, {"error": "request_too_large"})

    try:
        payload = json.loads(body.decode("utf-8") if body else "{}")
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
    except Exception:
        return _json_response(500, {"error": "internal_error"})

    return _json_response(200, plan_payload)


class CairnOSPlanAPIHandler(BaseHTTPRequestHandler):
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
        print("%s - - [%s] %s" % (self.address_string(), self.log_date_time_string(), format % args))


def run() -> None:
    host = os.environ.get("CAIRNOS_API_HOST", DEFAULT_HOST)
    port = int(os.environ.get("CAIRNOS_API_PORT", str(DEFAULT_PORT)))
    server = ThreadingHTTPServer((host, port), CairnOSPlanAPIHandler)
    print(f"{SERVICE_NAME} listening on http://{host}:{port}", flush=True)
    server.serve_forever()


def _json_response(status_code: int, payload: Mapping[str, Any]) -> tuple[int, dict[str, str], bytes]:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return status_code, dict(HEADERS), body


if __name__ == "__main__":
    run()
```

- [ ] **Step 4: Run focused HTTP adapter tests**

Run:

```bash
.venv/bin/python -m pytest cairn/tests/test_plan_api.py -k "http_adapter" -q
```

Expected: pass.

## Task 2: Persistent Docker Service

**Files:**
- Create: `Dockerfile.api`
- Create: `docker-compose.yml`

- [ ] **Step 1: Create the API Dockerfile**

Create `Dockerfile.api`:

```dockerfile
# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV CAIRNOS_API_HOST=0.0.0.0
ENV CAIRNOS_API_PORT=3010
ENV CAIRNOS_API_MAX_BODY_BYTES=32768
ENV CAIRNOS_BUILD_SHA=local-docker-api

WORKDIR /app

COPY cairn/api/requirements.txt /app/cairn/api/requirements.txt
RUN if grep -Eq '^[[:space:]]*[^#[:space:]]' /app/cairn/api/requirements.txt; then \
        python -m pip install --no-cache-dir -r /app/cairn/api/requirements.txt; \
    else \
        echo "No API runtime dependencies to install."; \
    fi

COPY cairn/ /app/cairn/
COPY trails/vermont_long_trail/compiled/ /app/trails/vermont_long_trail/compiled/
COPY trails/vermont_long_trail/raw/csv/ /app/trails/vermont_long_trail/raw/csv/
RUN chmod -R a+rX /app/trails/vermont_long_trail

EXPOSE 3010

CMD ["python", "-m", "cairn.api.http_server"]
```

- [ ] **Step 2: Create Docker Compose service**

Create `docker-compose.yml`:

```yaml
services:
  cairnos-plan-api:
    build:
      context: .
      dockerfile: Dockerfile.api
    image: cairnos-plan-api:local
    container_name: cairnos-plan-api
    environment:
      CAIRNOS_API_HOST: 0.0.0.0
      CAIRNOS_API_PORT: "3010"
      CAIRNOS_API_MAX_BODY_BYTES: "32768"
      CAIRNOS_BUILD_SHA: local-docker-api
    ports:
      - "127.0.0.1:3010:3010"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3010/healthz', timeout=2).read()"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
```

- [ ] **Step 3: Build and run on alternate port first if SAM is using 3010**

Run:

```bash
docker compose build cairnos-plan-api
```

Expected: image `cairnos-plan-api:local` builds successfully.

## Task 3: Documentation and Verification

**Files:**
- Modify: `docs/PLAN_API.md`

- [ ] **Step 1: Document local Docker-first workflow**

Add a section to `docs/PLAN_API.md` explaining:

```markdown
## Local SDDC Docker Workflow

The preferred local development path is the persistent Docker service:

```bash
docker compose up --build cairnos-plan-api
```

The service exposes:

- `POST http://127.0.0.1:3010/plan`
- `GET http://127.0.0.1:3010/healthz`
- `GET http://127.0.0.1:3010/version`

SAM remains available for Lambda/API Gateway parity checks before AWS deployment, but it is not the default SDDC-local runtime.
```

- [ ] **Step 2: Stop SAM and start persistent Docker API on 3010**

Run:

```bash
pkill -f "sam local start-api --template .aws-sam/build/template.yaml --port 3010" || true
docker compose up -d --build cairnos-plan-api
```

Expected: Docker Desktop shows `cairnos-plan-api` running and healthy.

- [ ] **Step 3: Smoke test health and plan contract**

Run:

```bash
curl -fsS http://127.0.0.1:3010/healthz
curl -fsS http://127.0.0.1:3010/version
curl -fsS -X POST http://127.0.0.1:3010/plan \
  -H 'content-type: application/json' \
  --data '{"selected_trail":"vermont_long_trail","trip_type":"THRU","direction":"NOBO","start_date":"2026-06-01","desired_days":28,"min_daily_miles":8,"max_daily_miles":15,"max_daily_elevation":4000,"resupply_cadence":5,"recovery_cadence":5,"ingress_route":"North Adams Approach","egress_route":"Journey'\''s End Trail"}' \
  | python -m json.tool | head -40
```

Expected: health returns `{"status":"ok"}`, version returns `local-docker-api`, and `/plan` returns `export_version` `cairnos_plan_v1`.

- [ ] **Step 4: Run focused API tests**

Run:

```bash
.venv/bin/python -m pytest cairn/tests/test_plan_api.py -q
```

Expected: pass.
