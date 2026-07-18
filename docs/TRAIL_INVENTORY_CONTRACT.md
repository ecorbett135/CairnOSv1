# CairnOS Trail Inventory Contract

## Purpose

The trail-inventory contract is the future CairnOS-owned source for
HikerLogix Platform manual planning. It lets HikerLogix build an itinerary from
valid trail-shape inventory without copying CairnOS planner semantics into
Django, React, or iOS.

The live alpha endpoint implements the initial inventory metadata contract. It
does not validate user-assembled itineraries or change planner behavior.

## Contract Version

The initial contract version is:

```text
cairnos_trail_inventory_v1
```

API path:

```text
GET /v1/trail-inventory?direction=NOBO
GET /v1/trail-inventory?direction=SOBO
```

The Plan API remains the auto-build endpoint. Trail inventory is for manual
selection, validation handoff, and display-label durability.

## Authority Boundary

CairnOS owns:

- trail ids and route progression;
- canonical northbound-reference miles;
- direction-aware display miles;
- route-overlay ids and operational ordering, using
  `compiled/route_overlay.json` as the inventory backbone;
- shelters, campsites, access points, road crossings, trailheads, resupply
  towns, and side-trip inventory;
- source/provenance metadata;
- future validation of user-assembled itineraries.

HikerLogix Platform owns:

- presenting inventory choices;
- saving selected inventory ids and display-label snapshots;
- storing generated/manual trip records;
- selecting a current field plan;
- distributing selected plans to iOS.

HikerLogix Platform and iOS must not infer terrain, recovery, resupply,
feasibility, or route semantics from this contract beyond fields CairnOS
promotes explicitly.

## Top-Level Shape

```json
{
  "contract_version": "cairnos_trail_inventory_v1",
  "trail_id": "vermont_long_trail",
  "status": "available",
  "selected_direction": "NOBO",
  "direction_model": {},
  "source": {},
  "route_extent": null,
  "access_point_options": [],
  "checkpoint_options": [],
  "required_anchor_options": {
    "overnight": [],
    "resupply": []
  },
  "items": []
}
```

| Field | Required | Meaning |
| --- | --- | --- |
| `contract_version` | yes | Stable inventory contract version. |
| `trail_id` | yes | CairnOS trail id. The MVP value is `vermont_long_trail`. |
| `status` | yes | `available` when CairnOS can build inventory. |
| `selected_direction` | yes | Direction used for item and required-anchor option ordering. |
| `direction_model` | yes | Direction and mile-display rules. |
| `source` | yes | Provenance and source artifact summary. |
| `route_extent` | yes | Null or normalized selected extent from endpoint query parameters. |
| `access_point_options` | yes | Full promoted section-boundary inventory in travel order. |
| `checkpoint_options` | yes | Full-trail or selected-extent intermediate access inventory. |
| `required_anchor_options` | yes | Direction-ordered overnight and resupply selector records. |
| `items` | yes | Stable inventory records. |

The contract is additive during alpha. Consumers should ignore unknown optional
fields and preserve raw inventory records or display-label snapshots where
needed for old-plan readability.

The live endpoint is generated from promoted CairnOS artifacts, not from the
representative fixture. The fixture remains a consumer-contract example.

## Direction Model

The MVP mile authority remains northbound-reference guidebook miles. CairnOS
does not invent a separate SOBO trail dataset.

```json
{
  "canonical_mile_system": "northbound_reference",
  "supported_directions": ["NOBO", "SOBO"],
  "section_model": "single_continuous_range",
  "flip_flop_supported": false,
  "trail_total_miles": 272.1,
  "sobo_display_mile_rule": "trail_total_miles - canonical_mile"
}
```

Consumers may display NOBO and SOBO miles, but must keep canonical ordering
anchored to CairnOS inventory ids and CairnOS validation.

The endpoint defaults to `NOBO`. For both directions, `items` and each
`required_anchor_options` list are ordered by the displayed directional mile
ascending. Equal-mile records use `inventory_id`, then `display_name`, as the
stable tie-breaker. This makes the returned list follow travel order without
creating a second canonical mile system.

Expose the canonical northbound-reference mile even when displaying a SOBO
label. SOBO display miles are derived presentation values, not a separate
source dataset.

## Inventory Item Shape

Each item should include:

| Field | Required | Meaning |
| --- | --- | --- |
| `inventory_id` | yes | Stable item id for saved selections. |
| `kind` | yes | Item category. See supported kinds below. |
| `display_name` | yes | Concise user-facing name. |
| `canonical_mile` | yes | Northbound-reference trail mile. |
| `directional_miles` | yes | Direction-aware display miles for supported directions. |
| `labels` | yes | Durable user-facing labels by direction. |
| `selectable_as` | yes | Supported manual-builder roles. |
| `source_artifacts` | yes | Source artifacts that contributed the item. |

Supported initial `kind` values:

- `overnight_site`
- `access_point`
- `town`
- `side_trip`
- `trailhead`
- `road_crossing`
- `route_point`

Supported initial `selectable_as` values:

- `section_boundary`
- `day_start`
- `day_stop`
- `overnight_stop`
- `resupply_stop`
- `town_preference`
- `side_trip_preference`

Items may include additional typed sections:

- `overlay` for route-overlay ids, node classes, and divisions;
- `access` for town access, distance, direction, mode, and notes;
- `overnight` for shelter/campsite metadata and amenities;
- `resupply` for service categories and convenience;
- `experience` for named side-trip or town-experience metadata;
- `related_inventory_ids` for links between an access point, town, and side
  trip records.

`route_overlay.json` should be treated as operational traversal truth. Enriched
references such as `overnight_reference.json`, `waypoint_reference.json`, and
raw CSV rows can add labels, coordinates, amenities, services, and provenance,
but they should not override overlay ordering or stop identity.

## Display Labels

Direction-aware labels should include the mile marker and access context:

```text
[NOBO Mile 14.3] Bennington [Vt. 9]
[SOBO Mile 257.8] Bennington [Vt. 9]
```

HikerLogix should store display-label snapshots with saved manual selections so
old plans remain readable if later CairnOS inventory labels change.

## Section Hiking

The Plan API supports one continuous defined-trail range in one direction.
SECTION is a route extent handled by PlannerV2, not a separate planner.
Consumers select CairnOS `start_access_id` and `end_access_id` values from
`access_point_options`, then request dependent inventory with both endpoint
query parameters. Exact request, response, sentinel, filtering, and Platform
handoff examples are in `docs/SECTION_ACCESS_POINT_CONTRACT.md`.

Promoted access points use stable overlay-backed IDs:

```text
vermont_long_trail:access:<overlay_id>
```

`access_point_options` always contains the full promoted boundary inventory.
When an extent is selected, `checkpoint_options` contains only access points
strictly between the endpoints while required overnight/resupply options are
filtered inclusively. All option arrays follow selected-direction travel order
and retain canonical northbound-reference miles. Extent-filtered options add
`section_relative_mile` measured from the selected start.

Complex flip-flops, disconnected sections, and mixed-direction itineraries are
out of scope for v1.

## Validation Boundary

Trail inventory alone does not prove that an itinerary is feasible. The Plan
API now accepts inventory-backed `required_overnight_anchor_ids` and
`required_resupply_anchor_ids` as a partial specification. CairnOS validates
role compatibility, direction order, duplicates, planner feasibility, and
exactly-once representation during `POST /v1/plans`.

Future full manual-itinerary validation should remain a separate CairnOS
contract that
accepts selected inventory ids and returns:

- ordered day validity;
- distance and elevation;
- recovery and resupply pressure;
- feasibility warnings;
- stale-inventory warnings;
- unsupported or missing inventory-id errors.

Until that exists, HikerLogix may save inventory-backed manual drafts, but it
must not present them as CairnOS-validated planned truth.

## Endpoint And Fixture

The live alpha endpoint emits overnight sites, overlay-promoted road crossings
and trailheads, resupply access points, towns, and validated side trips. It
does not bulk-promote candidate fields from `crossings_refined.json`.

The representative fixture lives at:

```text
cairn/tests/fixtures/trail_inventory/vermont_long_trail_inventory_v1.json
```

The fixture is intentionally small. It proves the contract shape with
representative overnight, access, town, and side-trip records. The live endpoint
is the complete current inventory response for promoted item kinds.

## Source Artifacts

The fixture and future endpoint should draw from promoted CairnOS artifacts
such as:

- `trails/vermont_long_trail/compiled/route_overlay.json`
- `trails/vermont_long_trail/compiled/operational_graph.json`
- `trails/vermont_long_trail/compiled/overnight_reference.json`
- `trails/vermont_long_trail/compiled/waypoint_reference.json`
- `trails/vermont_long_trail/raw/csv/resupply_amenities.csv`
- `trails/vermont_long_trail/raw/csv/side_trip_options.csv`
- `trails/vermont_long_trail/raw/csv/route_master.csv`

The endpoint generates inventory from these CairnOS-owned artifacts rather than
requiring HikerLogix to hand-maintain a product copy.

Crossing and trailhead metadata requires care. `crossings_refined.json` exposes
many candidate or derived crossings. Only road-crossing/trailhead semantics
already promoted into `route_overlay.json` enter the live access inventory.

Before a live endpoint is promoted, source/provenance gaps in reusable Long
Trail data should be reviewed in `data/DATASETS.md`.

## Relationship To Existing Contracts

- `GET /v1/plan-options` remains the promoted auto-build control metadata and
  preference-options endpoint.
- `POST /v1/plans` remains the CairnOS Auto Build endpoint.
- `cairnos_plan_v1` remains the generated plan export contract.
- `cairnos_trail_inventory_v1` will support HikerLogix Manual Build/Edit and
  future CairnOS validation of user-assembled itineraries.

## Open Implementation Work

- Normalize total-mile handling so plan options, inventory labels, and plan
  summaries use one documented trail-mile authority.
- Continue reviewing candidate crossing/trailhead rows before promoting any
  additional access semantics into `route_overlay.json`.
- Add a future manual-itinerary validation contract that accepts selected
  inventory ids and returns feasibility, mileage, elevation, and warnings.
