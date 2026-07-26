# CairnOS Unified Town Stop Contract

Copyright 2026 Eric Corbett

SPDX-License-Identifier: Apache-2.0

## Authority and versions

CairnOS owns town, trail-exit access, experience relationships, required-stop
planning, and satisfaction truth. The additive inventory and generated-plan
contracts are `cairnos_town_stop_options_v1` and `cairnos_town_stops_v1`.
They remain enclosed by legacy-compatible `cairnos_plan_api_v1` and
`cairnos_plan_v1` payloads.

Platform and iOS must use stable IDs returned by CairnOS. They must not match
towns or experiences by names or floating-point miles.

## Inventory

`GET /v1/trail-inventory` returns `town_stop_options`. Each option represents
one town reached through one stable trail access point. Composite access rows
are expanded into separate town options. Experiences have explicit, separate
town and access mappings in
`trails/vermont_long_trail/raw/csv/town_experience_mappings.csv`.
Trail-exit access IDs map explicitly to planner overlay IDs in
`trails/vermont_long_trail/raw/csv/town_access_mappings.csv`; planner code does
not infer the required stop from names or mile proximity.

The displayed mile is the trail exit mile, never a town location. NOBO uses
the canonical northbound-reference mile. SOBO uses trail total miles minus
canonical mile. SECTION inventory retains that directional trail mile, adds a
`section_relative_mile`, and excludes towns outside the normalized extent.
Options follow selected-direction travel order.

## Request

New clients submit only `town_stop_selections` for this workflow:

```json
{
  "town_stop_selections": [
    {
      "town_inventory_id": "vermont_long_trail:town:vt_17:162.9:waitsfield",
      "intents": ["resupply", "zero", "experience"],
      "experience_inventory_ids": [
        "vermont_long_trail:side_trip:lawsons_finest_taproom"
      ]
    }
  ]
}
```

A selected town is required exactly once. Several intents remain one stop.
Experiences must explicitly belong to the selected town and access. An
experience ID requires the `experience` intent, which requires at least one
experience ID. Selecting two towns sharing one access is a deterministic
conflict.

When any selection includes `nero`, the request must supply
`nero_max_trail_miles`. CairnOS publishes its allowed range in control metadata
but intentionally supplies no product default. Platform and iOS must not embed
a threshold. In Advanced planning the selected value is an explicit preference:
the selected town remains authoritative when the generated arrival or departure
day exceeds it, and the overage is reported in `town_stop_status`.

New town-stop selections cannot be mixed with legacy `selected_town_ids`,
`selected_side_trip_ids`, or `required_resupply_anchor_ids`. Requests using
only legacy fields continue to decode and produce legacy output.

## Generated-plan truth

`town_stop_status` reports requested, satisfied, and unsatisfied town IDs plus
one row per selected town. Each row carries its access ID, planned day/date,
combined intents, and experience IDs.

- `resupply` appears exactly once in `resupply_plan` and does not by itself
  require an overnight stop;
- `zero` inserts one deterministic zero-mile calendar row at the town;
- `nero` stays attached to the selected access and reports whether the generated
  day exceeds the user's `nero_max_trail_miles` preference;
- `experience` is confirmed on the same single town-stop row.

Explicit Advanced selections take precedence over automatic mileage, elevation,
resupply-cadence, and recovery-cadence preferences. Those overages remain
visible as itinerary or town-stop exceptions. Failure remains atomic for
unsupported relationships, unresolved route identity, duplicate satisfaction,
or genuinely unplaceable route geometry and returns a plain-language message,
stable `code`, and structured `context`. Stable codes are
`town_stop_unknown_or_outside_extent`, `town_stop_intent_unsupported`,
`town_stop_experience_parent_mismatch`, `town_stop_shared_access_conflict`,
`town_stop_nero_infeasible`, and `town_stop_infeasible`.

The contract is additive. Existing request fields, `selected_experiences`,
human-readable resupply output, and `cairnos_plan_v1` remain available. New
consumers must compare their request against `town_stop_status` exactly.
