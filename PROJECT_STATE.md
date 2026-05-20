# CairnOSv1 — Project State

## Executive Summary

CairnOSv1 is evolving into an operational expedition modeling system.

The architecture is intentionally moving away from:

- synthetic distance partitioning
- abstract graph traversal
- geometry-first planning
- ontology elegance without operational realism

and toward:

- operational traversal semantics
- expedition systems modeling
- cadence-aware itinerary synthesis
- terrain-aware traversal reasoning
- logistics-aware expedition planning
- ingress / egress continuity
- overlay-authoritative progression modeling
- structured resupply access-friction modeling

The planner should reason about:

- time
- effort
- terrain fatigue
- recovery
- logistics access
- town-access friction
- food-carry cadence pressure
- recovery-cadence pressure
- trail-duration baseline pressure
- overnight amenity preferences such as bear-box availability
- realistic pacing
- cadence sustainability
- the difference between mainline traversal and side-spur overnight access

NOT merely:

- partitioning mileage into evenly sized chunks.

---

## MVP Roadmap

The active MVP roadmap is documented in `docs/MVP_ROADMAP.md`.

Current execution order:

1. PlannerV2 module extraction
1. data quality/provenance hardening
1. terrain profile and mile-system reconciliation
1. overlay-authoritative traversal
1. SECTION planning

SECTION mode remains deferred and hidden from the Streamlit menu for the MVP,
while the internal code path remains available for later implementation.

Open-source, HikerLogix, and intellectual-property posture is documented in
`docs/OPEN_SOURCE_AND_IP_STRATEGY.md`. The working boundary is:

- CairnOSv1 remains public and Apache 2.0 licensed as the planning/export
  engine.
- HikerLogix can remain private/proprietary as the future mobile field
  execution layer: offline itinerary use, journal, actuals,
  planned-versus-actual review, lightweight advisory adjustments, and product
  packaging.
- Trail data provenance and commercial reuse rights are separate from the
  CairnOS source-code license.
- CairnOS Plan JSON is the intended deterministic export contract for future
  HikerLogix read-only itinerary import; Gaia GeoJSON remains
  navigation-tool-oriented.

---

# Architectural Philosophy

## Operational Truth Overrides Ontology Elegance

The most important architectural realization of CairnOSv1:

Operational truth matters more than ontology elegance.

The system should prioritize:

- real trail progression
- real logistics access
- realistic shelter progression
- operational traversal continuity
- actual expedition cadence

instead of:

- perfectly abstract graph semantics
- synthetic node generation
- GIS-style adjacency modeling

---

## Planner Philosophy

PlannerV2 is NOT:

- a mileage partition engine
- a geometric route slicer
- a naive graph traversal system

PlannerV2 IS:

- an expedition synthesis engine
- an operational traversal reasoner
- a cadence negotiation system
- a feasibility evaluator
- a recovery-aware itinerary planner

The planner should:

- evaluate feasibility
- negotiate cadence
- model degradation
- insert recovery opportunities
- synthesize realistic daily traversal
- reason about operational constraints
- preserve canonical overlay identity while presenting concise stop names to
  users

---

# Current Runtime Architecture

## build_topo/

Responsible for:

- topology compilation
- terrain segmentation
- operational overlay generation
- logistics node generation
- crossings generation
- graph substrate generation
- schema registry generation
- validation pipeline

Key Outputs:

- spine.geojson
- segments.geojson
- crossings.geojson
- crossings_refined.geojson
- operational_graph.json
- route_overlay.json
- approach_trails.json
- cairn_schema_registry.json

---

## cairn/runtime/

Responsible for:

- graph runtime loading
- operational queries
- traversal semantics, including operational-progression edge order as the
  THRU itinerary traversal authority
- overlay progression access
- operational node retrieval
- runtime substrate APIs

Key Files:

- graph_runtime.py
- traversal.py
- operational_queries.py

---

## cairn/planner/

Responsible for:

- expedition reasoning
- cadence negotiation
- itinerary synthesis
- operational stop selection
- fatigue modeling
- recovery semantics
- resupply planning
- feasibility evaluation

Key Files:

- planner_v2.py
- terrain.py
- logistics.py
- itinerary.py

Export integration should consume the `PlannerV2` result contract rather than
reconstructing planner internals.

IMPORTANT:

Do NOT endlessly mutate the facade.

PlannerV2 is the authoritative public planning substrate. Terrain, logistics
and recovery scoring, and daily itinerary synthesis should stay in focused
helper modules behind that facade.

---

## cairn/interfaces/

Responsible for:

- Streamlit operational UI
- expedition input semantics
- itinerary presentation
- feasibility feedback
- operational summaries

Key File:

- streamlit_app.py

---

# Operational Semantics

## Approach Trail Semantics

Approach trails are NOT:

- decorative metadata
- optional annotations
- external trail notes

Approach trails ARE:

- operational traversal branches
- ingress / egress traversal substrate
- expedition initialization state

Approach trails should support:

- NOBO ingress
- SOBO ingress
- NOBO egress
- SOBO egress
- future section traversal
- operational branch continuity

---

## Direction Semantics

NOBO and SOBO THRU plans now share the same northbound-reference trail mile
system. Direction changes traversal order, not the meaning of guidebook miles.

Current THRU semantics:

- NOBO starts from the selected southern ingress and progresses north
- SOBO starts from the selected northern ingress and progresses south
- selected egress routes are honored in both directions
- SOBO daily traversal mileage is positive even as guidebook mile values descend
- Journey's End Trail acts as northern ingress/egress, depending on direction
- Williamstown and North Adams approaches remain valid southern ingress/egress

The planner should continue to preserve NOBO / SOBO feature parity for
itinerary synthesis, resupply strategy generation, recovery annotations, and
Gaia export.

---

## Negative Mileage Semantics

Approach trails frequently exist outside:

- primary cumulative mileage

Therefore:

- ingress traversal may begin at negative mileage
- approach traversal must remain operationally meaningful

Example:

North Adams Approach:

- starts at:
  -3.8 miles

A realistic first day may therefore be:

- start:
  -3.8
- stop:
  5.5
- daily distance:
  9.3

This is operationally correct.

Subsequent days return to:

- stop_mile - previous_stop_mile

semantics.

---

## Overlay Authority

route_overlay.json is the authoritative operational progression layer.

Overlay nodes should provide:

- canonical operational names
- operational ordering
- shelter semantics
- logistics semantics
- progression continuity
- division continuity
- traversal authority

Overlay naming should always be preferred over:

- synthetic placeholders
- generated stop names
- generic labels

---

## Operational Naming Rules

The planner should NEVER prefer meaningless synthetic labels when authoritative operational names exist.

Avoid:

- Backcountry Camp
- Operational Stop
- Trail Progression

Prefer:

- Seth Warner Shelter
- Mass. 2 in North Adams
- Kid Gore Shelter
- Story Spring Shelter

Operational names are expedition semantics.

---

## Itinerary Semantics

The itinerary should behave like:

- a traversal narrative

NOT:

- a synthetic distance table

Daily rows should communicate:

- where the hiker starts
- where the hiker stops
- what type of operational node exists there
- realistic daily effort
- logistics / resupply significance
- division continuity

---

# Current UI Semantics

The Streamlit UI currently supports:

- trail selection
- view mode selection for automatic, mobile, or desktop layout
- trip type selection (`THRU` visible for MVP; `SECTION` deferred)
- direction selection (NOBO / SOBO)
- ingress route selection
- egress route selection
- desired completion days
- min daily mileage
- max daily mileage
- max elevation gain
- preferred resupply cadence
- preferred zero/nero recovery cadence
- optional extra resupply-only stops

The UI should prioritize:

- operational clarity
- expedition realism
- meaningful summaries
- itinerary readability

NOT:

- exposing internal runtime implementation details

---

# Current Stabilized Behavior And Remaining Gaps

## Ingress / Egress Continuity

Current PlannerV2 behavior now preserves selected ingress and egress routes for
the primary NOBO and SOBO THRU workflows.

Examples:

- NOBO can begin on the North Adams or Williamstown approach and end at
  Journey's End Trail
- SOBO can begin on Journey's End Trail and end through the selected southern
  approach
- approach trail negative mile semantics are preserved instead of normalized
  away

---

## Overlay Traversal Authority

The planner still primarily:

- targets mileage
- then searches for nearby nodes

Instead:

future behavior should:

- traverse overlay progression directly
- synthesize operational stop sequences intrinsically

---

## Overnight Ontology Weakness

Current overnight semantics remain weak.

The planner still lacks strong distinction between:

- shelters
- campsites
- stealth-compatible areas
- dry camps
- roadside logistics stops
- emergency bailout locations

---

## Synthetic Fallback Labels

The planner still sometimes generates:

- Backcountry Camp
- Operational Stop

These should only appear:

- when no operational node exists nearby.

---

## Terrain Modeling Now Incrementally Interval-Aware

PlannerV2 now uses compiled terrain samples to evaluate itinerary intervals.
For each moving leg it can derive:

- elevation gain
- elevation loss
- gain per mile
- ruggedness

Terrain coverage still has imperfect mile-system alignment, so PlannerV2 falls
maps northbound-reference guidebook miles into the compiled terrain sample
domain before reading dense elevation samples. It falls back to
`route_master.csv` elevation points and then to a conservative distance-based
estimate when needed.

Terrain now influences:

- daily target mileage
- reported daily elevation gain
- operational feasibility exceptions

Expedition summary effort averages now use moving days, excluding zero-mile
recovery rows from average daily mileage and elevation calculations.

Operational feasibility now separates the original requested completion target
from the generated itinerary. The requested target can remain aggressive or
unrealistic when CairnOS extends the plan, while the generated plan is scored
from actual daily mileage, elevation, weighted combined exception pressure,
repeated exceptions, and compound same-day stress. Moderate preference
exceptions should classify as challenging unless they are frequent, extreme, or
compound enough to justify aggressive.

Eventually terrain should also materially influence:

- overnight selection
- recovery insertion
- cadence degradation

---

## Resupply Semantics Now Incrementally Overlay-Aware

Current resupply behavior now identifies candidate access nodes from:

- route overlay resupply / logistics flags
- route overlay town access metadata
- crossing / trailhead / logistics node classes
- curated Long Trail trail-town amenities

PlannerV2 uses resupply cadence as a food-carry target and recovery cadence
as a separate zero/nero target. Both remain soft windows: resupply is only
annotated when the itinerary actually traverses a meaningful access node near
the food-carry window, and zero/nero notes are reserved for recovery stops.

Nero annotations now require the moving day to fall inside the configured
nero-mile window. The default window is 5-8 miles, with Streamlit controls for
minimum and maximum nero mileage.

The resupply strategy table now includes:

- a trip-start carry segment anchor
- planned resupply access points
- town access metadata
- days until the next resupply segment or finish
- days until the next recovery opportunity
- parsed town access distance and access notes
- validated town-service context where current independent sources exist
- annotation-only town and side-trip preferences with planned or unplanned
  status in the selected towns/experiences output

Recovery planning now supports cadence mode and target-count mode. Cadence mode
keeps recovery near the user's preferred day window when good access exists.
Target-count mode lets the user request zero and nero counts; PlannerV2 spreads
those targets across the generated trip but records a `recovery_count_days`
exception if suitable recovery nodes cannot satisfy the request. Generic
lodging can now support recovery selection under pressure, but verified lodging
remains higher confidence and broader lodging enrichment still needs
independent current-source validation.

Validated town lodging support is now split into a dedicated curated CSV. The
planner uses it to strengthen zero/recovery confidence and the town-details
table exposes named lodging options, including hiker-focused lodging where
known. Shuttle and transportation specifics are intentionally not displayed;
those details change too often for MVP output and should remain a future
ontology/data-quality concern. Continued lodging revalidation is tracked in
GitHub issue #60.

Terminal-day resupply is avoided because it does not reduce a future food carry.

The Streamlit app also exposes a developer diagnostics ZIP for generated plans.
That bundle captures the plan result, resupply strategy, Gaia export, warnings,
runtime data fingerprints, and per-day elevation confidence diagnostics so
alpha tester reports can be reproduced without screenshots or raw/source
datasets.

The hosted alpha feedback loop is intentionally separate from planner behavior.
The UI routes testers to the public GitHub issue-template chooser. GitHub is the
preferred channel because testers can attach the Developer Diagnostics ZIP and
the report remains tied to a trackable issue. Feedback guidance asks for planner
settings only when the reporter is not attaching a diagnostics ZIP. The ZIP
already includes planner settings, generated output, warnings, Gaia export, and
runtime data fingerprints. The guidance also asks for screenshots when useful;
standalone Gaia GeoJSON is only requested for export or marker-location reports
when the diagnostics ZIP is not attached. Testers who do not use GitHub can
share screenshots plus key settings in the community channel where they found
the alpha. The app does not store tester feedback, append planner settings to
the feedback URL, or treat feedback as planner input.

PlannerV2 now accepts an optional `start_date` in `user_profile` and returns
`season_advisories` for the generated trip window. The Streamlit UI exposes this
as `Planned Start Date` near trip settings and renders compact season/current
condition prompts near the expedition summary. These prompts are advisory only:
they ask users to verify official trail updates, closures, weather, hunting
seasons, and field conditions, but they do not affect completion negotiation,
daily stops, feasibility scoring, resupply/recovery behavior, side-trip
annotations, or Gaia export.

Future semantics should still reason more deeply about:

- structured town access distance and shuttle friction
- realistic recovery opportunities
- validated lodging / food confidence for zero stops
- optional experience stops without treating them as required miles
- access/transportation friction for town stops, termini, and section endpoints
- water-source reliability as future advisory metadata only
- terrain reset points
- logistics viability
- expedition sustainability

---

## Section Hiking Not Yet Implemented

SECTION mode remains largely incomplete and is intentionally hidden from the
Streamlit trip type menu for the MVP.

Future implementation must support:

- arbitrary ingress
- arbitrary egress
- crossing-based traversal
- partial overlay traversal
- partial cadence synthesis
- partial logistics optimization
- endpoint access and transportation-friction context
- section-level town, resupply, and recovery viability

---

## Overnight Reference Enrichment

Current overnight enrichment now reads optional shelter and campsite GeoJSON
exports from `trails/vermont_long_trail/raw/geojson/`.

The compiler produces:

- `trails/vermont_long_trail/compiled/overnight_reference.json`

This layer:

- preserves raw shelter/campsite waypoint metadata
- matches known sites against `route_overlay.json`
- keeps matched and unmatched overnight records
- estimates trail miles from the compiled spine for unmatched near-spine sites
- exposes additional planner stop candidates without mutating the route overlay

This data remains enrichment, not operational truth. Route overlay semantics
still win when a conflict exists.

## Overlay-Authoritative THRU Traversal

THRU itinerary synthesis now slices daily movement through ordered overlay
corridors derived from `operational_progression` edges. NOBO and SOBO still use
northbound-reference guidebook miles for public output, but candidate stop
selection and traversal advancement carry overlay identity through each moving
day.

Planner rows retain internal provenance fields for the selected overlay start,
selected overlay stop, and traversal authority. These fields are diagnostic
state for CairnOS and future exports; the Streamlit itinerary table and Gaia
GeoJSON export continue to present the stable user-facing itinerary fields.

Approach and egress branches remain selected traversal endpoints. Off-spine
overnight candidates remain displayable overnight access points anchored to the
mainline overlay; they do not become route deviations or replace the compiled
route overlay as operational truth.

---

# Current Priorities

Priority order is currently:

1. overlay-authoritative traversal synthesis
2. terrain-aware itinerary synthesis
3. logistics-aware resupply insertion
4. recovery semantics
5. operational cadence realism
6. section hiking substrate
7. planner validation rewrite
8. Gaia export enrichment hardening
9. overnight provenance hardening
10. legacy development-agent retirement and validation preservation

---

# Architectural Guardrails

DO NOT:

- revert to geometric distance slicing
- generate meaningless synthetic stop names
- ignore ingress / egress semantics
- collapse approach trails into mile 0 semantics
- treat overlay semantics as optional
- generate operationally impossible itineraries
- prioritize ontology elegance over operational realism

ALWAYS:

- prefer operational truth
- prefer overlay-authoritative names
- preserve traversal continuity
- preserve operational semantics
- synthesize human-meaningful itineraries
- reason about expeditions instead of geometry

---

# Current Important Files

## Topology / Operational Data

- trails/vermont_long_trail/compiled/route_overlay.json
- trails/vermont_long_trail/compiled/overnight_reference.json
- trails/vermont_long_trail/compiled/approach_trails.json
- trails/vermont_long_trail/compiled/operational_graph.json
- trails/vermont_long_trail/compiled/segments.json
- trails/vermont_long_trail/compiled/logistics_nodes.json

---

## Runtime Layer

- cairn/runtime/graph_runtime.py
- cairn/runtime/traversal.py
- cairn/runtime/operational_queries.py

---

## Planner Layer

- cairn/planner/planner_v2.py
- cairn/planner/terrain.py
- cairn/planner/logistics.py
- cairn/planner/itinerary.py

---

## UI Layer

- cairn/interfaces/streamlit_app.py

---

# Immediate Next Objectives

Immediate operational objectives:

- keep PlannerV2 facade compatibility after helper extraction
- keep runtime data-quality validation in the normal test loop
- preserve explicit guidebook-mile to terrain-sample-mile reconciliation
- calibrate elevation gain/loss against local reference exports without making
  vendor data operational truth
- use trusted coordinate anchors to improve local guidebook-mile to
  terrain-mile mapping accuracy
- use local ignored elevation calibration manifests to recheck known reference
  segments as diagnostics
- flag local elevation reference routes that deviate from the compiled trail
  spine before treating their elevation deltas as Cairn terrain issues
- keep overlay canonical miles authoritative when enriched reference stops
  share the same canonical name
- add provenanced overnight amenity metadata such as bear-box availability
  before exposing related route preferences
- keep town-service and side-trip enrichment provenanced, independently
  validated, and separate from route authority
- make overlay traversal authoritative
- implement section traversal substrate after THRU behavior is stable

---

# Final Direction

CairnOSv1 is evolving toward:

- expedition systems modeling
- operational traversal reasoning
- cadence-aware expedition planning
- realistic traversal synthesis

NOT:

- simple itinerary generation
- GIS adjacency modeling
- synthetic graph traversal
- mileage partition automation
