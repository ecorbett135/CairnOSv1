# CairnOS Section And Access-Point Contract

Copyright 2026 Eric Corbett

SPDX-License-Identifier: Apache-2.0

This document is the Platform handoff for defined-trail SECTION extents and
intermediate operational access-point anchors. CairnOS remains the planning,
validation, inventory, canonical-mile, and export-geometry authority.
HikerLogix Platform owns input presentation, persistence, and lifecycle UI.

## Versioning And Compatibility

The change is additive to `cairnos_plan_api_v1`, `cairnos_plan_v1`,
`cairnos_trail_inventory_v1`, `cairnos_route_selection_v1`, and
`cairnos_route_gpx_v4`. It adds two explicit sub-contracts:

- `cairnos_route_extent_v1`
- `cairnos_access_point_anchors_v1`

Omitting `trip_type` still means `THRU`. Existing THRU requests with legacy
`ingress_route` and `egress_route` fields remain valid. SECTION is promoted at
the Plan API boundary but remains hidden in the current Streamlit alpha UI.

## Stable IDs And Sentinels

Promoted road crossings and trailheads use overlay-backed CairnOS IDs:

```text
vermont_long_trail:access:<overlay_id>
```

Examples:

```text
vermont_long_trail:access:overlay_0015
vermont_long_trail:access:overlay_0033
vermont_long_trail:access:overlay_0077
```

SECTION requests have no full-trail approach branch. Their normalized
`cairnos_route_selection_v1` object uses these exact CairnOS-owned sentinels:

```text
ingress_approach_id = approach_none_ingress
egress_approach_id = approach_none_egress
```

The sentinels are returned by `GET /v1/plan-options` with
`geometry_status: not_applicable` and `sentinel: true`. They are valid only for
SECTION. They do not mean missing geometry and do not produce a
`selected_route_geometry_unavailable` warning.

## Exact SECTION Request Example

The committed request fixture is
`cairn/tests/fixtures/plan_api/section_access_point_plan_request.json`:

```json
{
  "trail_id": "vermont_long_trail",
  "trip_type": "SECTION",
  "direction": "NOBO",
  "start_access_id": "vermont_long_trail:access:overlay_0015",
  "end_access_id": "vermont_long_trail:access:overlay_0077",
  "desired_days": 7,
  "min_daily_miles": 4,
  "max_daily_miles": 16,
  "max_daily_elevation": 5000,
  "resupply_cadence": 5,
  "recovery_cadence": 6,
  "required_overnight_anchor_ids": [
    "vermont_long_trail:overnight:overlay_0023"
  ],
  "required_resupply_anchor_ids": [],
  "access_point_anchors": [
    {
      "access_id": "vermont_long_trail:access:overlay_0033",
      "intent": "meet_pickup",
      "date": "2026-07-03",
      "time": "14:00",
      "note": "Meet at Kelley Stand"
    },
    {
      "access_id": "vermont_long_trail:access:overlay_0043",
      "intent": "resupply"
    },
    {
      "access_id": "vermont_long_trail:access:overlay_0061",
      "intent": "overnight"
    }
  ],
  "planned_start_date": "2026-07-01"
}
```

`start_access_id` and `end_access_id` are travel-order fields. NOBO requires
the end canonical mile to be greater than the start canonical mile. SOBO
requires it to be lower. The fields must identify different promoted access
points. Unknown, reversed, or out-of-range endpoints return
`400 validation_error`.

## Access-Point Anchor Semantics

`access_point_anchors` is optional and defaults to `[]`. Each access ID may
appear once, and the array must follow selected-direction travel order. An
anchor must be strictly between the selected SECTION endpoints. For THRU, it
must be on the defined-trail extent.

Supported intents are exact lowercase values:

| Intent | Planner effect |
| --- | --- |
| `checkpoint` | Annotate the moving day that crosses the access point. Does not force a stop or resupply. |
| `meet_pickup` | Annotate the crossing and preserve pickup metadata. Does not force a stop or resupply. |
| `resupply` | Require one resupply event at the access point. Does not force an overnight. |
| `overnight` | Require the moving day to end at the access point. Does not imply resupply. |

Optional `date` uses `YYYY-MM-DD`; optional `time` uses `HH:MM`; optional
`note` is a string. In v1 these are preserved operational metadata. CairnOS
reports the generated `planned_day` and, when `planned_start_date` exists, the
generated `planned_date`. The requested date/time does not independently
reschedule or time-optimize the itinerary.

Existing `required_overnight_anchor_ids` and
`required_resupply_anchor_ids` remain exactly-once partial constraints.
Unselected shelters and resupply points remain planner candidates. All
required inventory anchors and all access-point anchors must fall inside the
selected route extent.

## Exact Inventory Query And Records

Platform first loads all section-boundary access points in travel order:

```text
GET /v1/trail-inventory?direction=NOBO
```

After both endpoints are selected, Platform reloads dependent options with the
exact CairnOS access IDs:

```text
GET /v1/trail-inventory?direction=NOBO&start_access_id=vermont_long_trail%3Aaccess%3Aoverlay_0015&end_access_id=vermont_long_trail%3Aaccess%3Aoverlay_0077
```

The selected inventory response includes this exact extent shape:

```json
{
  "contract_version": "cairnos_route_extent_v1",
  "extent_type": "defined_trail_section",
  "direction": "NOBO",
  "start_access_id": "vermont_long_trail:access:overlay_0015",
  "end_access_id": "vermont_long_trail:access:overlay_0077",
  "start": {
    "access_id": "vermont_long_trail:access:overlay_0015",
    "kind": "road_crossing",
    "display_name": "Vt. 9; William D. MacArthur Memorial bridge over City Stream",
    "canonical_mile": 14.3,
    "overlay_id": "overlay_0015",
    "node_class": "logistics",
    "division": "division3",
    "road_crossing": "Vt. 9; William D. MacArthur Memorial bridge over City Stream",
    "town_access": "Bennington",
    "access_notes": "4+ miles west from Long Trail to Bennington",
    "section_relative_mile": 0.0
  },
  "end": {
    "access_id": "vermont_long_trail:access:overlay_0077",
    "kind": "road_crossing",
    "display_name": "Vt. 103",
    "canonical_mile": 86.8,
    "overlay_id": "overlay_0077",
    "node_class": "logistics",
    "division": "division5",
    "road_crossing": "Vt. 103",
    "town_access": "Shrewsbury / Cuttingsville / Rutland",
    "access_notes": "2+ miles east to Shrewsbury and 7 miles west to Rutland",
    "section_relative_mile": 72.5
  },
  "canonical_start_mile": 14.3,
  "canonical_end_mile": 86.8,
  "canonical_min_mile": 14.3,
  "canonical_max_mile": 86.8,
  "distance_miles": 72.5
}
```

The endpoint records also include their `access_id`, `kind`, `display_name`,
`canonical_mile`, `overlay_id`, `node_class`, `division`, road/access context,
and `section_relative_mile`.

An exact checkpoint option inside that extent is:

```json
{
  "access_id": "vermont_long_trail:access:overlay_0033",
  "inventory_id": "vermont_long_trail:access:overlay_0033",
  "kind": "trailhead",
  "display_name": "Stratton–Arlington/Kelley Stand Road; Stratton Mtn. parking lot",
  "canonical_mile": 36.9,
  "directional_mile": 36.9,
  "label": "[NOBO Mile 36.9] Stratton–Arlington/Kelley Stand Road; Stratton Mtn. parking lot",
  "section_relative_mile": 22.6
}
```

Inventory filtering and ordering rules are:

- `items` remains the full promoted inventory, sorted in selected-direction
  travel order for lookup and durable labels;
- `access_point_options` remains the full promoted boundary inventory, sorted
  by `directional_mile`, then `access_id`, then `display_name`;
- `checkpoint_options` is full-trail when no extent query is supplied and is
  strictly between start/end when the extent query is supplied;
- `required_anchor_options.overnight` and `.resupply` are inclusive of selected
  endpoints and filtered to the extent when the extent query is supplied;
- all dependent option lists remain in selected-direction travel order;
- every option preserves `canonical_mile`; extent-filtered options also expose
  `section_relative_mile` measured from the selected start in travel distance;
- SOBO reverses traversal order while retaining the same northbound-reference
  `canonical_mile` values.

The access inventory is generated only from promoted `route_overlay.json`
road-crossing/trailhead semantics. It does not bulk-promote candidate rows from
`crossings_refined.json`.

## Exact Response Contract Sections

A successful response echoes the normalized route selection:

```json
{
  "contract_version": "cairnos_route_selection_v1",
  "ingress_approach_id": "approach_none_ingress",
  "egress_approach_id": "approach_none_egress"
}
```

It returns the `route_extent` shape above at the Plan JSON top level and inside
`user_profile`. Canonical daily miles remain in `daily_start_mile` and
`daily_stop_mile`; additive travel-distance fields are
`daily_start_section_mile` and `daily_stop_section_mile`.

For the exact request example, the satisfaction section is:

```json
{
  "contract_version": "cairnos_access_point_anchors_v1",
  "semantics": "intermediate_operational_checkpoints",
  "requested_access_point_anchor_ids": [
    "vermont_long_trail:access:overlay_0033",
    "vermont_long_trail:access:overlay_0043",
    "vermont_long_trail:access:overlay_0061"
  ],
  "satisfied_access_point_anchor_ids": [
    "vermont_long_trail:access:overlay_0033",
    "vermont_long_trail:access:overlay_0043",
    "vermont_long_trail:access:overlay_0061"
  ],
  "unsatisfied_access_point_anchor_ids": [],
  "anchors": [
    {
      "access_id": "vermont_long_trail:access:overlay_0033",
      "intent": "meet_pickup",
      "display_name": "Stratton–Arlington/Kelley Stand Road; Stratton Mtn. parking lot",
      "canonical_mile": 36.9,
      "section_relative_mile": 22.6,
      "date": "2026-07-03",
      "time": "14:00",
      "note": "Meet at Kelley Stand",
      "status": "satisfied",
      "planned_day": 3,
      "planned_date": "2026-07-03"
    },
    {
      "access_id": "vermont_long_trail:access:overlay_0043",
      "intent": "resupply",
      "display_name": "Vt. 11/30",
      "canonical_mile": 54.4,
      "section_relative_mile": 40.1,
      "status": "satisfied",
      "planned_day": 4,
      "planned_date": "2026-07-04"
    },
    {
      "access_id": "vermont_long_trail:access:overlay_0061",
      "intent": "overnight",
      "display_name": "USFS Road 10, east junction",
      "canonical_mile": 72.0,
      "section_relative_mile": 57.7,
      "status": "satisfied",
      "planned_day": 6,
      "planned_date": "2026-07-06"
    }
  ]
}
```

Every `daily_plan` row has an additive `access_point_anchors` array. The
`resupply` example also appears once as
`resupply_plan[].required_anchor_id`; the `overnight` example appears once as
`daily_plan[].required_overnight_anchor_id`. A successful plan has no
unsatisfied access IDs. Generation fails with `400 validation_error` instead
of returning partial satisfaction.

`route_gpx.route_extent` echoes the extent. Its full-plan manifest geometry
source records `canonical_min_mile: 14.3` and `canonical_max_mile: 86.8`; the
track contains only that selected defined-trail slice. The none sentinels add
no approach branch, are omitted from `route_gpx.route_parts`, and do not enter
`route_completeness.unavailable_route_part_ids`. Daily tracks remain bounded by
each daily canonical-mile interval.

## Platform Implementation Handoff

Platform should:

1. Fetch access IDs from CairnOS; never construct IDs or canonical miles.
2. Submit the selected travel-order endpoints to both inventory filtering and
   plan generation.
3. Use the same selected extent for Basic and Advanced. Advanced adds partial
   anchors; it does not invoke another planner.
4. Persist normalized `route_extent`, `route_selection`, and access-point
   satisfaction records with planned truth.
5. Display canonical miles from CairnOS and use `section_relative_mile` only as
   an extent-relative presentation value.
6. Treat requested checkpoint date/time as operational metadata and display
   CairnOS `planned_day`/`planned_date` separately.
7. Surface Plan API validation messages for reversed endpoints, unknown IDs,
   out-of-extent anchors, bad order, and infeasible overnight constraints.
8. Render the supplied GPX slice; do not derive or substitute section,
   ingress, or egress geometry.
9. Keep parking, pickup, shuttle, service, closure, weather, water, and route
   verification advisory and current-source dependent.

Platform and iOS implementation, persistence, auth, weather, COROS, AWS, and
field-navigation behavior remain outside this CairnOS contract slice.
