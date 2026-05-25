# Human-Readable Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add cost-safe CairnOS Plan API observability for local Docker and future Lambda operation.

**Architecture:** Keep observability inside the API adapter layer. Local Docker exposes human-readable JSON endpoints and in-memory counters; Lambda-compatible structured logs capture per-request duration without payloads or custom CloudWatch metrics.

**Tech Stack:** Python standard library HTTP server, pytest, Docker Compose.

---

## File Structure

- Modify `cairn/api/http_server.py`: add `/health`, `/ready`, `/metrics`, request timing, and structured log output.
- Modify `cairn/tests/test_plan_api.py`: add focused tests for endpoint behavior and metric updates.
- Modify `docs/PLAN_API.md`: document the cost-safe local observability contract and future Prometheus reservation.

## Task 1: Local Observability Endpoints

**Files:**
- Modify: `cairn/tests/test_plan_api.py`
- Modify: `cairn/api/http_server.py`

- [ ] **Step 1: Write failing endpoint tests**

Add tests asserting:

```python
def test_http_adapter_health_alias_returns_ok():
    from cairn.api.http_server import handle_http_request

    status, _headers, body = handle_http_request("GET", "/health", b"")

    assert status == 200
    assert json.loads(body.decode("utf-8")) == {"status": "ok"}


def test_http_adapter_ready_reports_planner_and_data_availability():
    from cairn.api.http_server import handle_http_request

    status, _headers, body = handle_http_request("GET", "/ready", b"")

    payload = json.loads(body.decode("utf-8"))
    assert status == 200
    assert payload["status"] == "ready"
    assert payload["checks"]["planner"] == "ok"
    assert payload["checks"]["long_trail_data"] == "ok"


def test_http_adapter_metrics_returns_human_readable_json():
    from cairn.api import http_server

    http_server.reset_metrics_for_tests()

    status, _headers, body = http_server.handle_http_request("GET", "/metrics", b"")

    payload = json.loads(body.decode("utf-8"))
    assert status == 200
    assert payload["service"] == "cairnos-plan-api"
    assert payload["format"] == "human_json_v1"
    assert payload["requests"]["total"] == 0
    assert payload["plan"]["successes"] == 0
```

- [ ] **Step 2: Run tests and confirm RED**

Run:

```bash
.venv/bin/python -m pytest cairn/tests/test_plan_api.py -k "health_alias or ready_reports or metrics_returns" -q
```

Expected: fails because `/health`, `/ready`, `/metrics`, and `reset_metrics_for_tests` do not exist.

- [ ] **Step 3: Implement endpoints**

Update `handle_http_request` so:

- `GET /health` and `GET /healthz` return `{"status":"ok"}`.
- `GET /ready` verifies `build_plan_response` is importable and `LONG_TRAIL_ROOT.exists()` is true.
- `GET /metrics` returns a stable JSON object with `service`, `format`, `uptime_seconds`, `requests`, `plan`, and `prometheus_reserved: true`.

- [ ] **Step 4: Run tests and confirm GREEN**

Run:

```bash
.venv/bin/python -m pytest cairn/tests/test_plan_api.py -k "health_alias or ready_reports or metrics_returns" -q
```

Expected: all selected tests pass.

## Task 2: Plan Timing Metrics And Structured Logs

**Files:**
- Modify: `cairn/tests/test_plan_api.py`
- Modify: `cairn/api/http_server.py`

- [ ] **Step 1: Write failing timing/log tests**

Add tests asserting:

```python
def test_http_adapter_records_plan_duration_metrics(monkeypatch):
    from cairn.api import http_server

    http_server.reset_metrics_for_tests()

    def stub_build_plan_response(payload, build_sha=None):
        return {"export_version": "cairnos_plan_v1", "daily_plan": [{"day": 1}]}

    monkeypatch.setattr(http_server, "build_plan_response", stub_build_plan_response)

    status, _headers, _body = http_server.handle_http_request(
        "POST",
        "/plan",
        json.dumps(_valid_plan_api_payload()).encode("utf-8"),
    )

    metrics_status, _metrics_headers, metrics_body = http_server.handle_http_request(
        "GET", "/metrics", b""
    )
    metrics = json.loads(metrics_body.decode("utf-8"))

    assert status == 200
    assert metrics_status == 200
    assert metrics["requests"]["total"] == 1
    assert metrics["plan"]["successes"] == 1
    assert metrics["plan"]["last_duration_ms"] >= 0
    assert metrics["plan"]["max_duration_ms"] >= metrics["plan"]["last_duration_ms"]
    assert metrics["plan"]["last_success_at"]


def test_http_adapter_logs_compact_plan_summary(monkeypatch, capsys):
    from cairn.api import http_server

    http_server.reset_metrics_for_tests()

    def stub_build_plan_response(payload, build_sha=None):
        return {"export_version": "cairnos_plan_v1", "daily_plan": [{"day": 1}]}

    monkeypatch.setattr(http_server, "build_plan_response", stub_build_plan_response)

    http_server.handle_http_request(
        "POST",
        "/plan",
        json.dumps(_valid_plan_api_payload()).encode("utf-8"),
    )

    log_payload = json.loads(capsys.readouterr().out.strip())
    assert log_payload["event"] == "plan_request"
    assert log_payload["status_code"] == 200
    assert log_payload["duration_ms"] >= 0
    assert log_payload["trail_id"] == "vermont_long_trail"
    assert "payload" not in log_payload
```

- [ ] **Step 2: Run tests and confirm RED**

Run:

```bash
.venv/bin/python -m pytest cairn/tests/test_plan_api.py -k "duration_metrics or compact_plan_summary" -q
```

Expected: fails because metrics counters and structured logs are not implemented.

- [ ] **Step 3: Implement metrics and logs**

Add an in-memory metrics state guarded by a threading lock. For `/plan`, measure total request duration, update counters, and print one compact JSON line containing no full request payload.

- [ ] **Step 4: Run tests and confirm GREEN**

Run:

```bash
.venv/bin/python -m pytest cairn/tests/test_plan_api.py -k "duration_metrics or compact_plan_summary" -q
```

Expected: all selected tests pass.

## Task 3: Documentation And Verification

**Files:**
- Modify: `docs/PLAN_API.md`

- [ ] **Step 1: Document endpoints**

Add:

- `/health`
- `/healthz`
- `/ready`
- `/version`
- `/metrics`

Document that `/metrics` is human-readable JSON for local/dev, with Prometheus reserved for a future endpoint such as `/metrics/prometheus`.

- [ ] **Step 2: Run full verification**

Run:

```bash
.venv/bin/python -m pytest cairn/tests/test_plan_api.py -q
.venv/bin/python -m py_compile cairn/api/http_server.py cairn/api/lambda_handler.py cairn/api/plan_request.py cairn/api/plan_service.py
docker compose up -d --build cairnos-plan-api
curl -fsS http://127.0.0.1:3010/health
curl -fsS http://127.0.0.1:3010/ready
curl -fsS http://127.0.0.1:3010/metrics
git diff --check
```

Expected: tests pass, compile passes, Docker container is healthy, observability endpoints return JSON, and diff check is clean.
