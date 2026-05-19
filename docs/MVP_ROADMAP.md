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

Future HikerLogix companion integration is tracked separately from the core MVP
sequence. It should begin as export interoperability and later become personal
calibration once CairnOS has a stable plan JSON export and SECTION semantics
are further along. See `docs/HIKERLOGIX_COMPANION.md`.

Open-source and commercial-product boundaries are tracked in
`docs/OPEN_SOURCE_AND_IP_STRATEGY.md`. The current posture is to keep CairnOSv1
public and Apache 2.0 licensed while keeping HikerLogix private/proprietary
unless a separate licensing decision is made.

Legacy development-agent cleanup is tracked as MVP hardening work, not product
AI-agent architecture. The pre-Codex coding-agent scaffold should be retired or
quarantined, while useful validation helpers should live under stable CairnOS
modules.

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

Structured resupply friction should remain user-tunable. The default convenient
resupply-only threshold is 1 mile from trail, but the UI should let hikers
choose their own access-distance tolerance while still treating longer town
trips as better suited to zero/nero recovery or unavoidable food-carry gaps.

Itinerary display should separate operational identity from presentation.
Compiled overlay names remain canonical traversal/provenance fields, but
overnight rows should show concise shelter/camp names and move short spur notes
into access-note/comment fields. Longer town-access prose belongs in resupply,
zero, nero, and logistics context.

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

Elevation calibration also supports a local ignored manifest CSV so known Gaia
or Garmin reference segments can be rechecked as pass/warn/fail diagnostics
without committing third-party route exports.

Calibration reports now include route-to-spine alignment diagnostics for local
reference route files. These warnings help separate true terrain-calibration
issues from reference routes that temporarily follow side trails, access routes,
or other non-LT geometry.

Developer diagnostics now include per-day elevation confidence details so
reported elevation rows can be inspected for dense terrain coverage,
route-master fallback, estimated fallback, or recomputation mismatch without
changing the planner's user-facing elevation output.

Per-day diagnostics also distinguish off-spine overnight access from actual
route deviation. A shelter reached by a short spur can be displayed as the
overnight site while traversal mileage and elevation remain tied to the main
Long Trail spine.

## Future Overnight Amenities

Bear-box availability should become a structured overnight-site amenity, not a
planner note. The source should be recorded as Green Mountain Club's bear-box
location page:

```text
https://www.greenmountainclub.org/bear-boxes/
```

Candidate Long Trail / Vermont AT overnight sites currently listed by GMC:

- Seth Warner Shelter
- Goddard Shelter
- Kid Gore Shelter
- Story Spring Shelter
- Stratton View Shelter
- Stratton Pond Shelter
- Peru Peak Shelter
- Griffith Lake Tenting Area
- Little Rock Pond Shelter
- Clarendon Shelter
- Governor Clement Shelter
- Tucker Johnson Shelter
- Stony Brook Shelter (AT)
- Battell Shelter
- Montclair Glen Lodge
- Bamforth Ridge Shelter
- Hump Brook Tenting Area
- Taylor Lodge
- Sterling Pond Shelter
- Tillotson Camp

Implementation should add a curated/provenanced overnight amenity source with a
boolean such as `bear_box`, compile it into overnight/reference metadata, and
optionally expose a Streamlit preference like "Prefer sites with bear boxes."
The preference should bias shelter/camp selection, not make bear boxes a hard
requirement unless a later UI explicitly asks for that mode.

## Near-Term Stabilization Notes

- Keep `PlannerV2` as the public integration facade for Streamlit, tests, and
  export code.
- Keep behavior changes separate from refactors whenever possible.
- Preserve NOBO and SOBO parity for THRU behavior.
- Treat compiled and curated data provenance as part of feature readiness, not
  cleanup after the fact.
