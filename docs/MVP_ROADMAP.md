# MVP Roadmap

CairnOSv1 is targeting a practical MVP around reliable Long Trail THRU
planning before expanding into broader route modes.

## Current MVP Scope

- NOBO and SOBO THRU itinerary generation
- selected ingress and egress route semantics
- terrain-derived daily elevation reporting
- terrain-aware pacing with feasibility exceptions
- resupply and recovery cadence separation
- configurable nero-mile rules
- minor-exception-aware feasibility classification
- resupply strategy rows with recovery timing and town-access friction context
- Gaia-compatible GeoJSON export

SECTION planning is intentionally deferred. The underlying planner branches
remain in place for later work, but the Streamlit UI hides SECTION mode until
the traversal and data semantics are ready.

## Product Boundary

CairnOSv1 should remain an operational itinerary and feasibility tool. The MVP
should avoid competing with full map/navigation platforms such as HiiKER, Gaia
GPS, Garmin, or FarOut. Those tools are downstream navigation ecosystems;
CairnOSv1 should produce better logistics-aware plans and exports for them.

Near-term work should prioritize:

- feasibility and exception reasoning
- terrain-aware daily pacing
- shelter, campsite, resupply, zero, and nero decisions
- clean exports into navigation workflows

Do not spend MVP effort on:

- general-purpose route drawing
- offline map management
- social/community trail publishing
- replacing guidebooks, official sources, or navigation apps

## Execution Order

1. PlannerV2 module extraction
1. data quality/provenance hardening
1. terrain profile and mile-system reconciliation
1. overlay-authoritative traversal
1. SECTION planning

## Current Data-Quality Work

The data-quality/provenance hardening step adds runtime validation around the
current Long Trail data foundation. It checks that route overlay, route master,
terrain, spine, resupply, overnight reference, approach trail, and operational
graph data agree where they should.

This work should not rewrite planner behavior. Its purpose is to make data
issues visible before more advanced terrain, traversal, and SECTION features
depend on them.

## Terrain Profile And Mile Systems

The planner and UI use northbound-reference guidebook miles as the public mile
system for NOBO and SOBO. Compiled terrain and spine artifacts can use internal
geometry/sample miles, which may not have the same span as guidebook miles.

PlannerV2 must reconcile those domains explicitly before using terrain samples
for interval gain, loss, ruggedness, pacing, or feasibility exceptions. Future
compiler work may emit guidebook-aware terrain metadata, but runtime planner
logic should never assume terrain sample miles and guidebook miles are the same
without an explicit mapper.

## Feasibility And Logistics Calibration

The alpha planner should distinguish minor preference exceptions from truly
aggressive plans. Small, sparse mileage or elevation overages can remain
comfortable when the base effort model and recovery pattern support that
classification; larger or repeated exceptions should escalate to challenging or
aggressive.

Current resupply convenience scoring may parse town-access distance from notes.
Future data-quality work should promote this into structured source fields so
the planner can reason about shuttle friction, town distance, and short
resupply-only stops without depending on prose parsing.

Gaia/manual elevation comparisons should feed back into terrain validation and
terrain-profile calibration, not ad hoc planner overrides.

Elevation calibration now has an IP-safe local workflow: user-owned Gaia/Garmin
exports can be compared against Cairn intervals from the ignored
`elevation_calibration/` directory. These files are reference measurements only,
not Cairn source data.

Terrain mile reconciliation now uses trusted coordinate anchors where possible
instead of relying only on a whole-trail linear scale. The anchor audit report
should be used to find suspicious local intervals before accepting future
terrain behavior changes.

## Near-Term Stabilization Notes

- Keep `PlannerV2` as the public integration facade for Streamlit, tests, and
  export code.
- Keep behavior changes separate from refactors whenever possible.
- Preserve NOBO and SOBO parity for THRU behavior.
- Treat compiled and curated data provenance as part of feature readiness, not
  cleanup after the fact.
