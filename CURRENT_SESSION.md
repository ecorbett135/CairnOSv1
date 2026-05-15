# CURRENT SESSION — PlannerV2 Direction And Cadence Stabilization

## Current Focus

This session stabilized the PlannerV2 THRU workflow around three related areas:

- NOBO / SOBO direction parity
- separate resupply and zero/nero recovery cadence semantics
- Gaia-compatible export behavior for itinerary and resupply markers

The current implementation is intentionally incremental. PlannerV2 is still
not a full overlay traversal engine, but the primary THRU workflow now behaves
like an operational expedition plan instead of a one-direction mileage slicer.

---

## Current Architectural State

PlannerV2 now supports:

- operational runtime substrate
- feasibility evaluation
- fatigue semantics
- ingress / egress semantics
- NOBO and SOBO THRU traversal over northbound-reference guidebook miles
- shelter-aware overnight selection
- logistics-aware stop synthesis
- separate resupply and recovery cadence inputs
- zero and nero annotations for recovery planning
- resupply strategy output tied to amenity-backed access points
- Gaia GeoJSON export with itinerary points, resupply road-access markers, and
  trail spine geometry
- Streamlit operational UI integration

The system has successfully moved away from:

- simple mileage partitioning
- synthetic graph traversal
- geometry-first itinerary generation

and toward:

- operational expedition modeling.

---

## Direction Semantics

The UI now separates:

- Trip Type: `THRU` / `SECTION`
- Direction: `NOBO` / `SOBO`

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

Terminal-day resupply is suppressed because it does not reduce a future food
carry.

---

## Current UI Semantics

The Streamlit UI currently supports:

- trail selection
- trip type selection
- direction selection
- ingress route selection
- egress route selection
- desired completion days
- min daily mileage
- max daily mileage
- max elevation gain
- preferred resupply cadence
- preferred zero/nero recovery cadence
- optional extra resupply-only stops
- explicit plan regeneration
- Gaia GeoJSON download

Planner output should stay visible until the user regenerates the plan. Slider,
selector, and download interactions should not implicitly wipe the displayed
plan.

---

## Current Desired Itinerary Semantics

Operational itinerary rows should communicate:

- start location
- stop location
- operational node type
- daily mileage
- realistic elevation gain
- logistics significance
- division continuity

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
- terrain semantics are still lightweight
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

## Runtime

- cairn/runtime/graph_runtime.py
- cairn/runtime/traversal.py
- cairn/runtime/operational_queries.py

## UI

- cairn/interfaces/streamlit_app.py

## Export

- cairn/export/gaia_geojson.py

## Operational Data

- trails/vermont_long_trail/compiled/route_overlay.json
- trails/vermont_long_trail/compiled/approach_trails.json
- trails/vermont_long_trail/compiled/operational_graph.json
- trails/vermont_long_trail/raw/csv/resupply_amenities.csv

---

## Current Priorities

Priority order:

1. make overlay traversal authoritative
2. improve shelter-aware overnight synthesis
3. mature logistics-aware resupply and recovery scoring
4. improve terrain-aware progression realism
5. implement section traversal substrate
6. reduce remaining synthetic stop generation
7. add food-weight effort modeling
8. rewrite planner validation layer
9. harden Gaia export regression coverage
10. reintegrate dev_agent against stabilized runtime APIs

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
