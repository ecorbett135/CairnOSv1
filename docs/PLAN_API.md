# CairnOS Plan API

Copyright 2026 Eric Corbett

SPDX-License-Identifier: Apache-2.0

The CairnOS Plan API is a stateless HTTP wrapper around the Long Trail THRU
planner and `cairnos_plan_v1` export contract. It is intended for plan
generation and downstream import interoperability, not accounts, saved plans,
mobile persistence, actuals, photos, HealthKit, or field-navigation behavior.

## Endpoints

The ASGI app is the target core API boundary:

```text
POST /v1/plans
GET /v1/plan-options
GET /v1/trail-inventory
GET /health
GET /version
GET /runtime
```

The Lambda adapter keeps the current compatibility paths:

```text
POST /plan
GET /plan/options
GET /options
content-type: application/json
```

Plan generation accepts only `POST`. `GET`, `PUT`, and other unsupported
methods return:

```json
{"error":"method_not_allowed"}
```

Responses include:

```text
content-type: application/json
cache-control: no-store
x-content-type-options: nosniff
```

The request body limit is controlled by `CAIRNOS_API_MAX_BODY_BYTES` and
defaults to `32768` bytes.

The ASGI and Lambda adapters share the same internal HTTP contract for request
body parsing, size-limit enforcement, route policy, build SHA handling, and
error normalization.

## Operator Runtime State

The local ASGI service exposes operator-visible runtime metadata:

```text
GET /version
GET /runtime
```

`/version` returns the service name, runtime, build SHA, API contract version,
current request body limit, and the diagnostics path. `/runtime` returns the
same identity fields plus the supported ASGI route inventory and Lambda
compatibility paths.

The API contract version is currently:

```text
cairnos_plan_api_v1
```

## Request

The body must be a JSON object with the MVP Long Trail planning fields:

| Field | Type | Range / values |
| --- | --- | --- |
| `trail_id` | string | `vermont_long_trail` |
| `direction` | string | `NOBO` or `SOBO` |
| `ingress_route` | string | NOBO: `Williamstown Approach` or `North Adams Approach`; SOBO: `Journey's End Trail` |
| `egress_route` | string | NOBO: `Journey's End Trail`; SOBO: `Williamstown Approach` or `North Adams Approach` |
| `desired_days` | integer | `3` to `60` |
| `min_daily_miles` | number | `4` to `25` |
| `max_daily_miles` | number | `8` to `40`, greater than or equal to `min_daily_miles` |
| `max_daily_elevation` | number | `1000` to `10000` feet |
| `resupply_cadence` | integer | `2` to `10` days |
| `recovery_cadence` | integer | `3` to `14` days |
| `planned_start_date` | string or null | Optional advisory start date |

Example:

```json
{
  "trail_id": "vermont_long_trail",
  "direction": "NOBO",
  "ingress_route": "North Adams Approach",
  "egress_route": "Journey's End Trail",
  "desired_days": 30,
  "min_daily_miles": 8,
  "max_daily_miles": 15,
  "max_daily_elevation": 4000,
  "resupply_cadence": 5,
  "recovery_cadence": 6,
  "planned_start_date": "2026-07-01"
}
```

## Response Contract

Successful requests return `200` with a `cairnos_plan_v1` JSON payload produced
by `cairn.api.plan_service.build_plan_response`. The payload is deterministic
planner/export output for import review and interoperability. It is advisory
planning software and is not a safety authority, guidebook, current-conditions
source, or navigation tool.

Plan responses also include the additive `route_gpx` section from
`cairnos_route_gpx_v1` when daily itinerary rows are available. The section
contains full-plan and per-day waypoint-only GPX artifacts for downstream
import/export workflows. The artifacts do not contain route or track geometry
and must remain advisory.

## Plan Options Contract

The debug and product clients should use CairnOS-owned option metadata rather
than duplicating Streamlit control values.

```text
GET /v1/plan-options
GET /plan/options
GET /options
```

Successful options responses return `200` with:

| Field | Purpose |
| --- | --- |
| `trail_id` | Current supported trail id, `vermont_long_trail` for the MVP |
| `status` | `available` when CairnOS can build the option metadata |
| `control_specs` | Shared slider/select/checkbox specs for Plan API inputs |
| `side_trip_options` | Validated optional side trip choices |
| `town_options` | Town preference choices derived from resupply amenities |

`control_specs` entries include stable `id`, user-facing `label`, `input`,
`value_type`, `default`, and range or choice metadata where applicable. The
same specs are used by the Streamlit debug UI and should be used by HikerLogix
web/mobile clients.

Town option ids are emitted only when the source row has both `canonical_hint`
and `trail_mile`, because the id is part of the planner-facing preference
contract.

## Trail Inventory Contract

HikerLogix manual planning clients should use CairnOS-owned trail inventory
instead of copying route, shelter, access, resupply, or side-trip semantics.

```text
GET /v1/trail-inventory
```

Successful trail-inventory responses return `200` with:

| Field | Purpose |
| --- | --- |
| `contract_version` | Current trail inventory contract, `cairnos_trail_inventory_v1` |
| `trail_id` | Current supported trail id, `vermont_long_trail` for the MVP |
| `status` | `available` when CairnOS can build inventory |
| `direction_model` | NOBO/SOBO display-mile and continuous-section rules |
| `source` | Promoted source artifacts used to build inventory |
| `items` | Inventory records for manual planning choices |

The initial live inventory exposes overnight sites, access points, towns, and
validated side trips. It intentionally avoids bulk road-crossing and trailhead
promotion until those candidate flags are validated.

Inventory is metadata for manual selection and display-label durability. It is
not a manual-itinerary validation response and does not change Plan API
feasibility logic.

Error responses are narrow and stable:

| Status | Error |
| --- | --- |
| `400` | `invalid_json` |
| `400` | `validation_error` |
| `405` | `method_not_allowed` |
| `413` | `request_too_large` |
| `500` | `internal_error` |

Validation errors include a `message` field describing the rejected input.
Unexpected planner or server errors return `internal_error` without traceback
details in the client payload.

## Privacy Boundary

The API is stateless. It does not create accounts, store plans, ingest actuals,
sync journals, process photos, request HealthKit data, or persist user-owned
mobile data. HikerLogix Platform and iOS treat this API as a planning/export
engine boundary; Platform owns accounts, saved plans, wrapper contracts, and
actuals intake.

## Local Development

Run the targeted Plan API tests:

```bash
venv/bin/python -m pytest cairn/tests/test_plan_api.py -q
venv/bin/python -m pytest cairn/tests/test_asgi_app.py -q
```

Compile the API modules:

```bash
venv/bin/python -m py_compile cairn/api/asgi_app.py cairn/api/http_contract.py cairn/api/lambda_handler.py cairn/api/plan_controls.py cairn/api/plan_options.py cairn/api/plan_request.py cairn/api/plan_service.py
```

Run the local ASGI app:

```bash
venv/bin/uvicorn cairn.api.asgi_app:app --reload --host 127.0.0.1 --port 8010
```

Run the local Docker Desktop ASGI service:

```bash
docker compose up --build cairnos-api
```

The container exposes:

```text
GET http://127.0.0.1:8010/health
GET http://127.0.0.1:8010/version
GET http://127.0.0.1:8010/runtime
GET http://127.0.0.1:8010/v1/plan-options
GET http://127.0.0.1:8010/v1/trail-inventory
POST http://127.0.0.1:8010/v1/plans
```

The initial ASGI paths are:

```text
GET /health
GET /version
GET /runtime
GET /v1/plan-options
GET /v1/trail-inventory
POST /v1/plans
```

## Lambda Container

Build the local Lambda container image:

```bash
docker build -f Dockerfile.lambda -t cairnos-plan-api:local .
```

The image uses the AWS Lambda Python 3.11 base image and sets:

```text
CMD ["cairn.api.lambda_handler.handler"]
```

The Lambda image installs dependencies from `cairn/api/requirements.txt`, not
from the repository root `requirements.txt`. The root requirements are for full
local development and include geospatial packages such as Fiona/GDAL-backed
dependencies that are not used by the Plan API runtime path and require native
build tooling that is intentionally absent from the minimal Lambda base image.

`cairn/api/requirements.txt` is allowed to be empty or comment-only. The current
runtime path uses the Python standard library plus repository CairnOS modules:

```text
cairn.api.lambda_handler -> cairn.api.http_contract -> cairn.api.plan_service -> PlannerV2 -> plan_json
```

Runtime environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `CAIRNOS_API_MAX_BODY_BYTES` | `32768` | Maximum decoded request body size |
| `CAIRNOS_BUILD_SHA` | `api` | Build identifier passed into the plan export |

### Local API Gateway Emulation

Use the SAM template to emulate API Gateway routing to the Lambda container
handler locally:

```bash
sam validate --template template.lambda.yaml
sam build --template template.lambda.yaml
sam local start-api --template .aws-sam/build/template.yaml --port 3010
```

The DEBUG simulator endpoint is:

```text
http://127.0.0.1:3010/plan
```

This localhost endpoint is only reachable from the machine running SAM local.
A physical iPhone cannot use `127.0.0.1` for this workflow; it needs a LAN
DEBUG transport exception that points at the development machine, or a deployed
HTTPS Lambda endpoint.

## App Runner Fallback

If Lambda container hosting is not the right operational fit, the same narrow
Plan API contract can be served from AWS App Runner with a small HTTP adapter
that calls `build_plan_response` and preserves the same request fields, error
codes, no-store headers, and stateless privacy boundary. App Runner should not
expand CairnOS into authentication, saved-plan storage, mobile actuals, or
field-navigation ownership.
