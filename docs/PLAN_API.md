# CairnOS Plan API

Copyright 2026 Eric Corbett

SPDX-License-Identifier: Apache-2.0

The CairnOS Plan API is a stateless HTTP wrapper around the Long Trail THRU
planner and `cairnos_plan_v1` export contract. It is intended for plan
generation and downstream import interoperability, not accounts, saved plans,
mobile persistence, actuals, photos, HealthKit, or field-navigation behavior.

## Endpoint

```text
POST /plan
content-type: application/json
```

Only `POST` is accepted. `GET`, `PUT`, and other methods return:

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

## Request

The body must be a JSON object with the MVP Long Trail planning fields:

| Field | Type | Range / values |
| --- | --- | --- |
| `trail_id` | string | `vermont_long_trail` |
| `direction` | string | `NOBO` or `SOBO` |
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

Error responses are narrow and stable:

| Status | Error |
| --- | --- |
| `400` | `invalid_json` |
| `400` | `validation_error` |
| `405` | `method_not_allowed` |
| `413` | `request_too_large` |

Validation errors include a `message` field describing the rejected input.

## Privacy Boundary

The API is stateless. It does not create accounts, store plans, ingest actuals,
sync journals, process photos, request HealthKit data, or persist user-owned
mobile data. Future HikerLogix work should treat this API as a planning/export
engine boundary.

## Local Development

Run the targeted Plan API tests:

```bash
venv/bin/python -m pytest cairn/tests/test_plan_api.py -q
```

Compile the API modules:

```bash
venv/bin/python -m py_compile cairn/api/lambda_handler.py cairn/api/plan_request.py cairn/api/plan_service.py
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

Runtime environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `CAIRNOS_API_MAX_BODY_BYTES` | `32768` | Maximum decoded request body size |
| `CAIRNOS_BUILD_SHA` | `api` | Build identifier passed into the plan export |

## App Runner Fallback

If Lambda container hosting is not the right operational fit, the same narrow
Plan API contract can be served from AWS App Runner with a small HTTP adapter
that calls `build_plan_response` and preserves the same request fields, error
codes, no-store headers, and stateless privacy boundary. App Runner should not
expand CairnOS into authentication, saved-plan storage, mobile actuals, or
field-navigation ownership.
