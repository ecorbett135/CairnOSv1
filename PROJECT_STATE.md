

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

The planner should reason about:

- time
- effort
- terrain fatigue
- recovery
- logistics access
- realistic pacing
- cadence sustainability

NOT merely:

- partitioning mileage into evenly sized chunks.

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
- traversal semantics
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

Key File:

- planner_v2.py

IMPORTANT:

Do NOT endlessly mutate the original planner.

PlannerV2 is the authoritative planning substrate.

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
- future section traversal
- operational branch continuity

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
- NOBO / SOBO / SECTION selection
- ingress route selection
- egress route selection
- desired completion days
- min daily mileage
- max daily mileage
- max elevation gain
- resupply / zero cadence

The UI should prioritize:

- operational clarity
- expedition realism
- meaningful summaries
- itinerary readability

NOT:

- exposing internal runtime implementation details

---

# Current Known Problems

## Ingress / Egress Continuity

Current planner behavior still sometimes:

- ignores ingress initialization
- resets traversal to mile 0
- loses approach continuity

This is a major operational bug.

---

## Overlay Traversal Authority

The planner currently:

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

## Terrain Modeling Still Simplistic

Terrain weighting currently behaves mostly as:

- decorative effort scaling

Eventually terrain should materially influence:

- overnight selection
- mileage collapse
- recovery insertion
- cadence degradation
- operational feasibility

---

## Resupply Semantics Still Simplistic

Current resupply logic remains mostly:

- cadence interval based

Future semantics should reason about:

- actual town access
- realistic recovery opportunities
- terrain reset points
- logistics viability
- expedition sustainability

---

## Section Hiking Not Yet Implemented

SECTION mode remains largely incomplete.

Future implementation must support:

- arbitrary ingress
- arbitrary egress
- crossing-based traversal
- partial overlay traversal
- partial cadence synthesis
- partial logistics optimization

---

# Current Priorities

Priority order is currently:

1. ingress / egress continuity
2. overlay-authoritative traversal synthesis
3. shelter-aware overnight selection
4. logistics-aware resupply insertion
5. terrain-aware itinerary synthesis
6. recovery semantics
7. operational cadence realism
8. section hiking substrate
9. planner validation rewrite
10. dev_agent reintegration

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

---

## UI Layer

- cairn/interfaces/streamlit_app.py

---

# Immediate Next Objectives

Immediate operational objectives:

- fully fix ingress initialization semantics
- fully honor approach trail progression
- improve overlay-authoritative stop selection
- remove remaining synthetic stop generation
- improve shelter-aware stop synthesis
- improve logistics-aware resupply planning
- improve terrain-aware progression realism
- implement section traversal substrate

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