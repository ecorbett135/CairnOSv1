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
| `route_selection` | object | Optional `cairnos_route_selection_v1` stable-ID selection; legacy requests derive the IDs from `ingress_route` / `egress_route` |
| `desired_days` | integer | `3` to `60` |
| `min_daily_miles` | number | `4` to `25` |
| `max_daily_miles` | number | `8` to `40`, greater than or equal to `min_daily_miles` |
| `max_daily_elevation` | number | `1000` to `10000` feet |
| `resupply_cadence` | integer | `2` to `10` days |
| `recovery_cadence` | integer | `3` to `14` days |
| `required_overnight_anchor_ids` | array of strings | Optional ordered `inventory_id` values selectable as `overnight_stop`; default `[]` |
| `required_resupply_anchor_ids` | array of strings | Optional ordered `inventory_id` values selectable as `resupply_stop`; default `[]` |
| `planned_start_date` | string or null | Optional advisory start date |

`route_selection` is the additive geometry/traversal selection contract:

```json
{
  "contract_version": "cairnos_route_selection_v1",
  "ingress_approach_id": "approach_north_adams",
  "egress_approach_id": "egress_journeys_end"
}
```

The IDs come from `GET /v1/plan-options` under
`route_selection.options`. CairnOS validates that each ID exists, matches the
corresponding legacy route name, connects to the correct terminus for the
requested direction/role, and is not reused for both roles. If the object is
omitted, CairnOS resolves the existing route names to exactly one compiled
`approach_id` each and echoes the normalized shape. This preserves v1 callers
while giving export consumers stable selected-route identity.

Geometry availability is separate from route validity. A known compatible
selection with no promoted geometry remains plannable and returns
`selected_route_geometry_unavailable`; CairnOS never substitutes a different
approach. Unknown, incompatible, or disconnected selected geometry fails with
a deterministic validation error.

The required-anchor fields are additive fields in `cairnos_plan_api_v1`. Their
result status uses the explicit sub-contract version
`cairnos_required_planning_anchors_v1`.

Required-anchor semantics are partial specification:

- each selected overnight site is a hard required overnight stop;
- each selected resupply point is a hard required itinerary/resupply event;
- every required id must appear exactly once or plan generation fails;
- unselected overnight and resupply locations remain available for CairnOS to
  fill route, pacing, recovery, and food-carry gaps;
- the arrays must follow travel order for the selected direction;
- preferred, excluded, and arbitrary user-defined anchors are not part of this
  contract.

Clients should populate these arrays from `required_anchor_options` in
`GET /v1/trail-inventory?direction=NOBO|SOBO`. Do not submit display labels or
planner-internal names as ids.

Example:

```json
{
  "trail_id": "vermont_long_trail",
  "direction": "NOBO",
  "ingress_route": "North Adams Approach",
  "egress_route": "Journey's End Trail",
  "route_selection": {
    "contract_version": "cairnos_route_selection_v1",
    "ingress_approach_id": "approach_north_adams",
    "egress_approach_id": "egress_journeys_end"
  },
  "desired_days": 30,
  "min_daily_miles": 8,
  "max_daily_miles": 15,
  "max_daily_elevation": 4000,
  "resupply_cadence": 5,
  "recovery_cadence": 6,
  "required_overnight_anchor_ids": [
    "vermont_long_trail:overnight:overlay_0023"
  ],
  "required_resupply_anchor_ids": [
    "vermont_long_trail:town:vt_9:14.3:bennington"
  ],
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
`cairnos_route_gpx_v4` when daily itinerary rows are available. The section
contains a full-plan GPX track composed from the exact promoted ingress/egress
IDs plus the canonical defined-trail spine in traversal order. Each moving-day
artifact contains the mileage-bounded portion of the same selected route and
retains the existing planned waypoints. Zero-mile or otherwise unsliceable days
remain waypoint-only. Off-spine overnight access is not included, and all
artifacts remain advisory.

V4 emits source-authoritative GPX `<ele>` meters, deterministic track metrics,
ordered route-part identity/provenance, and separate emitted-track versus
selected-route completeness. Consumers must not synthesize missing branch
geometry/elevation. Exact pass-through and profile rules are documented in
`docs/ROUTE_GPX_EXPORT.md`.

The response echoes `route_selection` in `user_profile` and in `route_gpx`.
Manifest `geometry_sources` entries identify the spine and any composed
approach IDs, geometry IDs, connection gap, and promoted provenance. Current
Long Trail data promotes North Adams approach geometry; Williamstown and
Journey's End report geometry-unavailable warnings until separately promoted.

When required-anchor fields are present, the response includes:

```json
{
  "required_anchors": {
    "contract_version": "cairnos_required_planning_anchors_v1",
    "semantics": "partial_specification",
    "required_overnight_anchor_ids": [
      "vermont_long_trail:overnight:overlay_0023"
    ],
    "required_resupply_anchor_ids": [
      "vermont_long_trail:town:vt_9:14.3:bennington"
    ],
    "satisfied_overnight_anchor_ids": [
      "vermont_long_trail:overnight:overlay_0023"
    ],
    "satisfied_resupply_anchor_ids": [
      "vermont_long_trail:town:vt_9:14.3:bennington"
    ]
  }
}
```

The same ids are attached to planned truth for deterministic consumer checks:

- `daily_plan[].required_overnight_anchor_id` identifies the required overnight
  represented by that row, or is null;
- `daily_plan[].required_resupply_anchors` lists required resupply events crossed
  on that day;
- `resupply_plan[].required_anchor_id` identifies a required resupply
  projection; optional planner-added rows omit it;
- `user_profile.required_overnight_anchor_ids` and
  `user_profile.required_resupply_anchor_ids` echo the normalized request.

For a successful response, each requested id appears once in its corresponding
planned-truth annotation and once in the matching `satisfied_*` list.

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
| `route_selection` | `cairnos_route_selection_v1` metadata, stable approach IDs, directional roles, and geometry availability |
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
GET /v1/trail-inventory?direction=NOBO
GET /v1/trail-inventory?direction=SOBO
```

Successful trail-inventory responses return `200` with:

| Field | Purpose |
| --- | --- |
| `contract_version` | Current trail inventory contract, `cairnos_trail_inventory_v1` |
| `trail_id` | Current supported trail id, `vermont_long_trail` for the MVP |
| `status` | `available` when CairnOS can build inventory |
| `selected_direction` | Direction used to order displayed options; default `NOBO` |
| `direction_model` | NOBO/SOBO display-mile and continuous-section rules |
| `source` | Promoted source artifacts used to build inventory |
| `required_anchor_options` | Direction-ordered `overnight` and `resupply` selector records |
| `items` | Inventory records for manual planning choices |

The initial live inventory exposes overnight sites, access points, towns, and
validated side trips. It intentionally avoids bulk road-crossing and trailhead
promotion until those candidate flags are validated.

Each required-anchor option contains `inventory_id`, `kind`, `display_name`,
`directional_mile`, and `label`. Both option lists are sorted by displayed
directional mile ascending, then by `inventory_id` and `display_name` for
stable ties. SOBO therefore returns the reverse canonical traversal as
ascending SOBO display miles.

Inventory is metadata for selection and display-label durability. Required
anchor feasibility is validated only by `POST /v1/plans`.

Required-anchor validation uses stable `400 validation_error` responses. Exact
message families include:

```text
required_overnight_anchor_ids contains unknown inventory_id: <id>
required_resupply_anchor_ids inventory_id is not selectable as resupply_stop: <id>
required_overnight_anchor_ids contains duplicate inventory_id: <id>
required_resupply_anchor_ids resolves multiple inventory IDs to the same resupply anchor: <id>, <id>
required_overnight_anchor_ids must follow SOBO route order; <id> cannot follow <id>
Required resupply anchor must appear exactly once: <id> appeared 0 times. Adjust desired_days or daily mileage/elevation limits.
route_selection.ingress_approach_id unknown approach_id: <id>
route_selection.ingress_approach_id is incompatible with ingress_route '<name>': <id> identifies '<other-name>'
Selected ingress approach_id '<id>' geometry is disconnected from the southern defined-trail terminus by <miles> miles
```

Unknown, incompatible, duplicate, out-of-order, and infeasible anchors never
fall back to preferences or silent omission.

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
