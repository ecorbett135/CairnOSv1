# CURRENT SESSION — PlannerV2 Extraction, MVP Hardening, And Data Quality

## Current Focus

This session stabilized the PlannerV2 THRU workflow around three related areas:

- PlannerV2 module extraction into terrain, logistics, and itinerary helpers
- NOBO / SOBO direction parity
- separate resupply and zero/nero recovery cadence semantics
- terrain-aware pacing and terrain-derived elevation reporting
- Gaia-compatible export behavior for itinerary and resupply markers
- runtime data-quality validation for the current Long Trail dataset
- terrain profile and mile-system reconciliation
- itinerary display-name normalization and off-spine overnight-access
  diagnostics
- open-source, HikerLogix, and IP boundary clarification

The current implementation is intentionally incremental. PlannerV2 is still
not a full overlay traversal engine, but the primary THRU workflow now behaves
like an operational expedition plan instead of a one-direction mileage slicer.
The runtime dataset now has a validator that reports internal consistency
errors and known warnings without treating validation as a provenance or
licensing guarantee. Terrain profile analysis now distinguishes public
guidebook miles from compiled geometry/sample miles and maps between those
domains explicitly.

---

## Current Architectural State

PlannerV2 now supports:

- operational runtime substrate
- feasibility evaluation
- fatigue semantics
- ingress / egress semantics
- NOBO and SOBO THRU traversal over northbound-reference guidebook miles
- shelter-aware overnight selection
- overnight reference enrichment from compiled shelter/campsite waypoints
- logistics-aware stop synthesis
- separate resupply and recovery cadence inputs
- zero and nero annotations for recovery planning
- configurable nero-mile bounds
- terrain interval analysis from compiled elevation samples
- explicit terrain mile-domain reconciliation
- requested-target and generated-plan feasibility classification
- weighted combined exception pressure for generated-plan feasibility
- resupply strategy output tied to amenity-backed access points
- structured resupply access-friction fields and user-tunable convenient
  resupply-only distance
- curated bear-box overnight amenity metadata with an optional soft planner
  preference
- clean overnight stop display names with side-spur notes separated from
  canonical overlay names
- Gaia GeoJSON export with itinerary points, resupply road-access markers, and
  trail spine geometry
- Streamlit operational UI integration
- a THRU-only MVP Streamlit trip type menu, with SECTION deferred but not
  removed from the underlying planner path

The system has successfully moved away from:

- simple mileage partitioning
- synthetic graph traversal
- geometry-first itinerary generation

and toward:

- operational expedition modeling.

---

## Direction Semantics

The UI now separates:

- Trip Type: `THRU` in the MVP UI
- Direction: `NOBO` / `SOBO`

SECTION mode remains intentionally hidden from Streamlit until the traversal
and data semantics are ready. The internal code path is still present for
future work.

Current THRU semantics:

- NOBO starts from the selected southern ingress and progresses north
- SOBO starts from the selected northern ingress and progresses south
- guidebook/trail miles remain northbound-reference miles in both directions
- SOBO daily mileage is calculated as positive travel distance while mile
  values descend
- Journey's End Trail is northern ingress/egress depending on direction
- Williamstown and North Adams approaches are southern ingress/egress branches

NOBO and SOBO should maintain feature parity for itinerary generation,
resupply strategy output, recovery notes, and Gaia export.

---

## Resupply And Recovery Semantics

PlannerV2 now separates:

- resupply cadence: food-carry management
- zero/nero cadence: recovery management
- optional extra resupply-only stops

These can overlap at the same access point, but they are not the same planner
decision.

Current note values should stay sparse:

- `resupply`
- `nero`
- `zero`
- `resupply / nero`
- `resupply / zero`

The resupply strategy table now includes:

- a day-1 trip-start carry segment anchor
- planned resupply access points
- town access metadata
- days until the next resupply segment or finish
- days until the next recovery opportunity
- parsed town access distance and access notes

Terminal-day resupply is suppressed because it does not reduce a future food
carry.

---

## Current UI Semantics

The Streamlit UI currently supports:

- trail selection
- trip type selection (`THRU` visible for MVP)
- direction selection
- view mode selection for automatic, mobile, or desktop layout
- ingress route selection
- egress route selection
- desired completion days
- min daily mileage
- max daily mileage
- max elevation gain
- preferred resupply cadence
- preferred zero/nero recovery cadence
- minimum nero miles
- maximum nero miles
- optional extra resupply-only stops
- convenient resupply-only access distance
- optional bear-box site preference
- explicit plan regeneration
- Gaia GeoJSON download
- developer diagnostics ZIP download for reproducible alpha tester reports,
  including per-day elevation confidence and off-spine overnight-access
  diagnostics

Planner output should stay visible until the user regenerates the plan. Slider,
selector, and download interactions should not implicitly wipe the displayed
plan.

---

## Current Desired Itinerary Semantics

Operational itinerary rows should communicate:

- start location
- stop location
- concise stop access notes when the stop is reached by a short spur or side
  trail
- operational node type
- daily mileage
- terrain-derived elevation gain
- logistics significance
- division continuity

Expedition summary effort averages should use moving days. Zero-mile recovery
rows remain part of completion time, but they should not dilute average daily
mileage or average daily elevation from an effort-planning perspective.

Overnight stop display names should be human-readable site names, such as
`Stratton Pond Shelter`. Longer compiled overlay names remain available as
canonical fields for diagnostics and export resolution, while immediate spur
details such as `600 ft S via Stratton Pond Trail and spur` live in access-note
fields. Longer town-access prose belongs in resupply or logistics context, not
ordinary shelter location fields.

---

## Open Source And HikerLogix Boundary

CairnOSv1 remains public and Apache 2.0 licensed for alpha deployment,
community review, and planning/export interoperability. HikerLogix remains a
separate future mobile companion boundary and can stay private/proprietary
unless deliberately opened later.

Do not commit HikerLogix proprietary implementation details, private user
actuals, monetization experiments, or patent-sensitive implementation notes to
CairnOSv1. See `docs/OPEN_SOURCE_AND_IP_STRATEGY.md` and
`docs/HIKERLOGIX_COMPANION.md`.

NOBO example:

| Field | Example |
| --- | --- |
| day | 1 |
| daily_start_mile | -3.8 |
| daily_start_location | Mass. 2 in North Adams |
| daily_start_location_type | trailhead |
| daily_stop_mile | 5.5 |
| daily_stop_location | Seth Warner Shelter |
| daily_stop_location_type | shelter |
| daily_miles | 9.3 |
| notes | *(blank)* |

SOBO example semantics:

- day 1 may begin at Journey's End Trail
- mainline mile values descend
- daily travel mileage remains positive
- the itinerary should continue toward the selected southern egress

---

## Remaining Gaps

PlannerV2 still needs improvement in these areas:

- overlay progression should become the primary traversal substrate instead of
  target-mile search plus nearby node selection
- section hiking remains incomplete
- terrain semantics are now interval-aware and mile-domain-aware, but deeper
  fatigue, grade, and surface modeling remains future work
- town-access friction is still parsed from prose notes and should become
  structured source data
- food-carry weight is tracked only as backend planning context, not as an
  effort multiplier yet
- synthetic fallback labels should become increasingly rare as compiled
  operational data improves
- resupply and recovery scoring should continue to mature around real service
  quality, town friction, terrain, and fatigue

---

## Current Important Files

## Planner

- cairn/planner/planner_v2.py
- cairn/planner/terrain.py
- cairn/planner/logistics.py
- cairn/planner/itinerary.py

## Runtime

- cairn/runtime/graph_runtime.py
- cairn/runtime/traversal.py
- cairn/runtime/operational_queries.py
- cairn/runtime/data_quality.py

## UI

- cairn/interfaces/streamlit_app.py

## Export

- cairn/export/gaia_geojson.py

## Operational Data

- trails/vermont_long_trail/compiled/route_overlay.json
- trails/vermont_long_trail/compiled/overnight_reference.json
- trails/vermont_long_trail/compiled/approach_trails.json
- trails/vermont_long_trail/compiled/operational_graph.json
- trails/vermont_long_trail/raw/csv/resupply_amenities.csv
- trails/vermont_long_trail/raw/csv/overnight_amenities.csv
- trails/vermont_long_trail/raw/geojson/shelters.geojson
- trails/vermont_long_trail/raw/geojson/campsites.geojson

---

## Current Priorities

Priority order is now tracked in `docs/MVP_ROADMAP.md`:

1. PlannerV2 module extraction
1. data quality/provenance hardening
1. terrain profile and mile-system reconciliation
1. overlay-authoritative traversal
1. SECTION planning

The current data-quality hardening branch adds:

- a stdlib-only runtime data validator
- route overlay, route master, resupply, overnight reference, approach trail,
  terrain, spine, and operational graph consistency checks
- explicit reporting for guidebook-mile and terrain-sample-mile domain
  reconciliation
- pytest coverage for the live Long Trail dataset and representative broken
  synthetic data
- documentation that validation improves trust but does not resolve source
  licensing or provenance gaps
- IP-safe elevation calibration using ignored local reference exports and
  comparison reports
- anchor-based terrain mile mapping from trusted matched coordinate references
- manifest-driven elevation calibration reports for known reference segments,
  with pass/warn/fail diagnostics
- route-to-spine alignment checks so local reference routes that follow side
  trails or access routes are flagged before their elevation deltas are trusted
- itinerary stop resolution now prefers overlay-authoritative miles when an
  enriched overnight reference shares a canonical overlay name
- whole-trail audit reporting for suspicious local terrain intervals
- bear-box availability is recorded as structured overnight amenity metadata,
  sourced from Green Mountain Club, and available as an optional soft planner
  preference

Supporting follow-on work includes reducing synthetic stop generation, adding
food-weight effort modeling, hardening Gaia export regression coverage, and
retiring the legacy development-agent scaffold while preserving useful
validation helpers under stable CairnOS modules.

---

## Current Important Operational Principles

Operational truth overrides ontology elegance.

The planner should model:

- expeditions
- traversal continuity
- operational realism
- human pacing
- cadence sustainability
- direction parity

NOT:

- synthetic graph traversal
- arbitrary mileage partitioning
- geometry-first planning

Overlay semantics are authoritative.

Ingress / egress are traversal initialization state.

Approach trails are operational traversal branches.

The itinerary is a traversal narrative.

Resupply and recovery are related but distinct logistics concepts.
