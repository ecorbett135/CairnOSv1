# MVP Roadmap

CairnOSv1 is targeting a practical MVP around reliable Long Trail THRU
planning before expanding into broader route modes.

## Current MVP Scope

- NOBO and SOBO THRU itinerary generation
- selected ingress and egress route semantics
- overlay-authoritative THRU traversal over compiled operational progression
  order
- terrain-derived daily elevation reporting
- terrain-aware pacing with feasibility exceptions
- resupply and recovery cadence separation
- configurable nero-mile rules
- minor-exception-aware feasibility classification
- resupply strategy rows with recovery timing and town-access friction context
- optional bear-box overnight-site preference based on curated amenity metadata
- resupply town-detail review rows with service categories and validation status
- annotation-only side-trip preferences for validated experience options
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

Overlay-authoritative traversal in the MVP scope means NOBO and SOBO THRU daily
planning follows ordered overlay corridors for the mainline plus selected
ingress and egress endpoints. SECTION planning remains a later slice; this
work does not add user-facing SECTION controls.

Future HikerLogix companion integration is tracked separately from the core MVP
sequence. HikerLogix should become the mobile field execution layer, not
"CairnOS on a phone": offline itinerary use, daily journal, actuals capture,
planned-versus-actual review, and lightweight advisory adjustments. See
`docs/HIKERLOGIX_COMPANION.md`.

Roadmap sequencing should stay export-first:

- #12 deterministic plan JSON export is the key CairnOS unlock for HikerLogix
  offline itinerary import.
- #13 read-only HikerLogix import path is the near-term interoperability step.
- #14 actuals import and personal calibration remains Post-MVP until
  HikerLogix proves its mobile journal, actuals, and review workflow.

Do not add live town-hour, post-office-hour, store-hour, weather automation, or
product AI-agent epics before the offline plan and actuals loop is stable.

Open-source and commercial-product boundaries are tracked in
`docs/OPEN_SOURCE_AND_IP_STRATEGY.md`. The current posture is to keep CairnOSv1
public and Apache 2.0 licensed while keeping HikerLogix private/proprietary
unless a separate licensing decision is made.

External research sources that influence roadmap decisions, planner behavior,
or data modeling are tracked in `docs/RESEARCH_LOG.md`. Community research is
qualitative signal unless it is separately promoted into a provenanced dataset.
The 2026-05-19 Long Trail guide/source review reinforces that CairnOS should
stay provenance-aware while improving experience-aware planning. Active roadmap
items now track validated town details, optional side-trip annotations,
implemented date-aware season/current-condition advisories,
access/transportation friction, and future water-source reliability evaluation.
The related GitHub roadmap items are #38, #41, #42, #43, and #44.

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

The alpha planner should distinguish the original requested target from the
generated itinerary. A request that requires extension can remain classified as
aggressive or unrealistic while the generated plan is evaluated separately.
Sparse mileage or elevation exceptions can remain comfortable. Moderate
combined mileage/elevation pressure should generally classify as challenging,
not aggressive, unless the weighted pressure is high, exception days are
frequent, compound same-day exceptions repeat, or a single overage is extreme.
The UI should visually distinguish compound exception days so testers can spot
days that exceed both mileage and elevation preferences without scanning the
full itinerary.

Current resupply convenience scoring may parse town-access distance from notes.
Future data-quality work should promote this into structured source fields so
the planner can reason about shuttle friction, town distance, and short
resupply-only stops without depending on prose parsing.

Town-detail output should remain a review aid for planned resupply stops, not a
guidebook replacement. Business-level lodging, outfitter, shuttle, and mail-drop
data should remain out of planner scoring until each listing has independent
current-source validation and documented provenance.

Town and side-trip preferences should remain annotation-only in MVP hardening.
The selector should include standalone town stops as well as named experiences,
and selected preferences should show town context in a dedicated selected
experiences table near the generated plan. They must not change daily mileage,
completion days, feasibility, resupply scoring, or Gaia export behavior until a
separate planner-time model exists.

Food-carry cadence overages should be visible as feasibility exceptions when a
generated plan exceeds the user's preferred resupply cadence. These exceptions
should carry less feasibility pressure than mileage or elevation exceptions,
and much less pressure than same-day mileage plus elevation overages.

Recovery-cadence overages should also be visible as feasibility exceptions.
They represent missed zero/nero timing preferences, not physical trail effort,
so they should affect classification less than mileage/elevation pressure but
remain visible when the generated plan cannot place recovery near the requested
cadence.

Long Trail THRU feasibility classification should include a broad
duration-baseline calibration from public planning sources: under 20 days is
unrealistic, 20-24 days is aggressive, 25-28 days is challenging, and 29+ days
is comfortable before itinerary-specific exceptions are applied. This is a
planning heuristic, not an official pace standard.

Date-aware season and current-condition advisories are informational in MVP
hardening. `PlannerV2` accepts an optional planned start date and returns
advisory records for the generated trip window covering official trail-update
verification, mud season, insects, hunting season, and shoulder-season weather.
Those prompts must not become safety determinations, live trail-condition
claims, feasibility scoring inputs, or Gaia export properties.

Transportation and access friction should become explicit advisory logistics
context for town stops, termini, road crossings, and future SECTION endpoints.
This should extend structured resupply access metadata without depending on
prose parsing or guaranteeing current shuttle, transit, parking, or business
availability.

Water-source reliability remains future advisory data, not MVP feasibility
logic. Official and clearly licensed sources should be reviewed before adding
water metadata, and any output must remind hikers to verify current conditions
and treat water.

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

Hosted Alpha diagnostics should be build-consistent. Generated plans record the
build that created them, stale session-state plans are refreshed after redeploy,
and diagnostic manifests expose whether the plan build matches the current app
build.

Planner terrain smoothing should retain real rolling gain on rugged trail.
The current default suppresses small DEM jitter without flattening repeated
20-40 ft climbs, which matters in the Stratton Mountain / Stratton Pond area
and other rolling terrain intervals.

## Future Overnight Amenities

Bear-box availability is tracked as structured overnight-site amenity metadata,
not as a planner note. The source is recorded as Green Mountain Club's bear-box
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

The curated `overnight_amenities.csv` source compiles into overnight reference
metadata with a `bear_box` boolean. The Streamlit preference "Prefer Sites With
Bear Boxes" softly biases shelter/camp selection, but does not make bear boxes a
hard requirement.

## Near-Term Stabilization Notes

- Keep `PlannerV2` as the public integration facade for Streamlit, tests, and
  export code.
- Keep behavior changes separate from refactors whenever possible.
- Preserve NOBO and SOBO parity for THRU behavior.
- Keep daily overlay traversal provenance diagnostic-only unless an export
  contract explicitly opts into it.
- Treat compiled and curated data provenance as part of feature readiness, not
  cleanup after the fact.
