# CairnOSv1 — Architecture Guardrails

## Purpose

- architectural invariants
- operational semantics rules
- forbidden regressions
- planner behavior constraints
- ontology guardrails
- implementation boundaries

These guardrails exist to prevent:

- semantic drift
- regression into synthetic planning behavior
- ontology-first abstractions that reduce operational realism
- accidental reintroduction of brittle planner assumptions

---

## Core Architectural Principle

### Operational Truth Overrides Ontology Elegance

This is the most important invariant in CairnOSv1.

If a choice exists between:

- operational realism
OR
- ontology elegance

ALWAYS prefer:

- operational realism.

The system exists to model:

- real expeditions
- realistic traversal
- human pacing
- operational logistics
- terrain consequences
- recovery constraints

NOT:

- idealized graph theory
- perfect taxonomy
- synthetic GIS adjacency
- abstract node purity

---

## Planner Guardrails

### PlannerV2 Is Mandatory

DO NOT:

- continue mutating legacy planner architecture endlessly
- merge old planner assumptions into PlannerV2

PlannerV2 is the authoritative public expedition planner facade.

Terrain, logistics/recovery scoring, and daily itinerary synthesis should live
behind that facade in focused helper modules. Preserve the facade contract for
Streamlit, tests, and export integrations.

Legacy planner behavior should be considered:

- deprecated
- transitional
- non-authoritative

---

### PlannerV2 Must Model Expeditions

PlannerV2 MUST reason about:

- elapsed time
- terrain fatigue
- cumulative stress
- recovery
- logistics access
- cadence sustainability
- realistic pacing
- operational feasibility

PlannerV2 MUST NOT behave like:

- a mileage partition engine
- a geometric slicer
- a simple graph shortest-path system
- a fixed-distance itinerary generator

---

### CairnOS Is Not A Navigation Platform

CairnOSv1 MUST remain an operational expedition reasoning layer.

It may export to and complement navigation tools such as:

- HiiKER
- Gaia GPS
- Garmin
- FarOut
- paper maps and guidebooks

CairnOSv1 MUST prioritize:

- itinerary feasibility
- logistics and resupply reasoning
- shelter and campsite stop selection
- recovery and effort modeling
- export interoperability

CairnOSv1 MUST NOT drift into:

- general-purpose map editing
- offline map management
- turn-by-turn navigation
- social trail publishing
- replacing official sources, guidebooks, or dedicated navigation apps

Prefer clean exports and integrations over rebuilding mature navigation
ecosystems.

---

## Overlay Authority Guardrails

### route_overlay.json Is Authoritative

The operational overlay is the authoritative traversal semantics layer.

Overlay semantics MUST control:

- canonical operational naming
- operational ordering
- progression continuity
- shelter semantics
- logistics semantics
- division continuity
- traversal authority

The planner MUST prefer overlay semantics over:

- synthetic naming
- generated stop labels
- geometric proximity assumptions
- inferred ordering

---

### Overlay Progression Must Eventually Become Traversal Authority

Current planner behavior:

- targets mileage
- searches for nearby nodes

This is transitional behavior only.

Target architecture:

- traversal follows overlay progression intrinsically
- operational stop synthesis emerges from overlay traversal
- itinerary continuity is overlay-driven

DO NOT regress toward:

- geometric distance slicing
- proximity-only planning

---

## Approach Trail Guardrails

### Approach Trails Are Operational Branches

Approach trails are NOT:

- metadata
- annotations
- optional notes
- decorative semantics

Approach trails ARE:

- traversal branches
- ingress semantics
- egress semantics
- operational initialization state

---

### Ingress / Egress Semantics Are Mandatory

The planner MUST honor:

- selected ingress routes
- selected egress routes
- traversal direction continuity
- operational branch transitions

DO NOT:

- silently reset traversal to mile 0
- ignore selected ingress branches
- collapse approach trails into mainline semantics
- treat ingress as output metadata

Ingress / egress selection is:

- traversal initialization state.

---

### NOBO / SOBO Direction Parity Is Mandatory

NOBO and SOBO are traversal directions over the same northbound-reference
guidebook miles. They are not separate mile systems.

The planner MUST preserve:

- equivalent feature support for NOBO and SOBO THRU plans
- selected ingress and egress route semantics in both directions
- northbound-reference guidebook mile values
- positive daily traversal mileage in either direction
- direction-aware resupply and recovery planning
- direction-aware Gaia export coordinates and marker semantics

For SOBO traversal:

- operational progression descends through northbound-reference miles
- daily mainline mileage is calculated from previous mile to next mile in the
  southbound direction
- Journey's End Trail is northern ingress, not a terminal one-row itinerary
- southern approach trails remain valid egress branches

DO NOT:

- invent SOBO mile markers
- treat SOBO as a special-case truncation of NOBO
- drop egress branches when reversing direction
- allow negative daily mileage except for valid signed mile references

---

### Negative Mileage Semantics Must Be Preserved

Approach trails may legitimately exist at:

- negative cumulative mileage

This is operationally correct.

Example:

- North Adams Approach begins at:
  -3.8 miles

The planner MUST preserve:

- negative approach traversal
- asymmetric day-1 mileage calculations
- operational ingress continuity

DO NOT:

- normalize approach mileage to zero
- erase negative traversal semantics

---

## Itinerary Guardrails

### The Itinerary Is A Traversal Narrative

The itinerary should communicate:

- operational progression
- realistic daily traversal
- meaningful overnight locations
- logistics significance
- cadence continuity
- division continuity

The itinerary MUST NOT resemble:

- a synthetic distance spreadsheet
- arbitrary mileage partitioning
- meaningless node hopping

---

### Synthetic Labels Are Forbidden When Better Operational Data Exists

DO NOT generate labels like:

- Backcountry Camp
- Operational Stop
- Trail Progression

WHEN:

- overlay-authoritative names exist
- shelter names exist
- crossing names exist
- logistics names exist

Prefer:

- Seth Warner Shelter
- Kid Gore Shelter
- Mass. 2 in North Adams
- Journey's End Trail

Operational naming is critical expedition semantics.

Synthetic fallback labels should ONLY appear:

- when absolutely no operational node exists nearby.

---

### Notes Field Should Remain Operationally Sparse

The itinerary notes field should ONLY contain:

- resupply
- nero
- zero
- resupply / nero
- resupply / zero
- future operationally exceptional conditions

DO NOT clutter notes with:

- obvious overnight explanations
- generic recovery statements
- synthetic planner narration

If a stop is:

- a shelter
- a campsite
- a camp area

that is already operationally obvious.

---

## Overnight Selection Guardrails

### Overnight Selection Must Be Operationally Meaningful

Overnight selection should prioritize:

1. shelters
2. campsites
3. operational recovery locations
4. logistics-compatible stops
5. safe fallback camping

DO NOT:

- synthesize arbitrary stops solely to satisfy mileage
- ignore known operational overnight infrastructure
- treat all overnight nodes equally

Compiled overnight reference data may expand stop options when:

- the source waypoint is matched or projected near the compiled trail spine
- provenance is recorded
- route overlay semantics remain authoritative

DO NOT treat raw waypoint exports as operational truth before reconciliation.

---

### Shelter Ontology Must Remain Distinct

The system should distinguish between:

- shelters
- campsites
- stealth-compatible areas
- dry camps
- roadside logistics stops
- emergency bailout locations

Avoid flattening all overnight semantics into:

- generic overnight nodes.

---

## Terrain Modeling Guardrails

### Terrain Must Influence Traversal Meaningfully

Terrain is NOT decorative metadata.

Terrain should eventually influence:

- daily mileage collapse
- overnight selection
- recovery insertion
- cadence degradation
- operational feasibility
- traversal sustainability

DO NOT:

- reduce terrain to cosmetic effort multipliers only.

Terrain-derived daily elevation should come from actual itinerary intervals
where compiled terrain coverage exists. If terrain coverage is incomplete,
PlannerV2 may fall back to route-master elevation points or conservative
distance-based estimates, but it must not cap reported elevation to the user's
planning preference.

---

## Resupply Guardrails

### Resupply Must Become Operationally Realistic

Resupply planning MUST distinguish:

- food-carry resupply cadence
- recovery zero/nero cadence
- optional resupply-only access stops

These concepts may overlap at the same access point, but they are not the same
planner decision.

Resupply planning should continue to reason about:

- actual town access
- realistic recovery opportunities
- terrain reset points
- logistics viability
- expedition sustainability

DO NOT permanently rely on:

- fixed cadence intervals
- arbitrary node counting

Resupply strategy output should remain operationally useful:

- include the trip start as the first carry segment anchor
- report days until the next resupply segment
- avoid terminal-day resupply stops that do not help the hiker
- use sparse operational notes such as `resupply`, `nero`, `zero`,
  `resupply / nero`, and `resupply / zero`

Nero notes should only be used when the moving day falls inside the configured
nero-mile window. Days outside that window may still be useful resupply or zero
opportunities, but they should not be labeled as nero by default.

Current cadence logic is incremental and should keep moving toward richer
food-weight, terrain, and recovery modeling.

---

## Section Hiking Guardrails

### Section Hiking Is A Distinct Traversal Mode

SECTION mode is NOT:

- truncated NOBO
- truncated SOBO

SECTION mode requires:

- arbitrary ingress
- arbitrary egress
- crossing-based traversal
- partial overlay traversal
- partial cadence synthesis
- partial logistics optimization

DO NOT fake section hiking by:

- simply clipping itinerary endpoints.

SECTION mode is deferred and hidden from the Streamlit menu for the MVP. The
internal code path may remain in place, but it should not be presented as a
supported planning mode until these traversal semantics are implemented.

---

## Runtime Layer Guardrails

### Runtime APIs Must Remain Stable

The runtime layer should provide:

- traversal semantics
- overlay progression access
- operational node access
- graph traversal substrate
- logistics queries
- overnight queries

Avoid tightly coupling:

- Streamlit UI
- planner internals
- topology compiler internals

through brittle assumptions.

---

## Dev Agent Guardrails

### dev_agent Should Operate Only On Bounded Semantic Tasks

Good dev_agent tasks:

- schema propagation
- validator generation
- topology enrichment
- UI enhancement
- compiler refactors
- graph enrichment

Bad dev_agent tasks:

- ontology invention
- expedition semantics design
- planner philosophy changes
- unconstrained architectural rewrites

Human supervision is mandatory for:

- planner semantics
- traversal ontology
- operational modeling direction

---

## Forbidden Regression Patterns

DO NOT:

- revert to geometric distance slicing
- collapse operational semantics into pure graph traversal
- erase ingress / egress continuity
- normalize approach trails into mile 0 semantics
- generate operationally meaningless stop names
- flatten overnight ontology
- ignore overlay authority
- prioritize synthetic elegance over expedition realism
- generate impossible itineraries without negotiation
- silently ignore operational constraints

---

## Required Future Direction

CairnOSv1 must continue evolving toward:

- expedition systems modeling
- operational traversal synthesis
- cadence-aware planning
- terrain-aware expedition reasoning
- realistic logistics modeling
- recovery-aware traversal
- operational continuity

NOT toward:

- GIS adjacency tooling
- synthetic itinerary generation
- naive graph shortest-path systems
- geometry-first planning
