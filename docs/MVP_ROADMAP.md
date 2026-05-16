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

## Near-Term Stabilization Notes

- Keep `PlannerV2` as the public integration facade for Streamlit, tests, and
  export code.
- Keep behavior changes separate from refactors whenever possible.
- Preserve NOBO and SOBO parity for THRU behavior.
- Treat compiled and curated data provenance as part of feature readiness, not
  cleanup after the fact.
