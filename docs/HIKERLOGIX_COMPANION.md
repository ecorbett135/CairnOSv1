# HikerLogix Integration Boundary

This document records the current three-repository product boundary. CairnOS is
the planning engine and contract authority behind HikerLogix, not a user-facing
brand inside Platform or iOS.

## Repository Ownership

CairnOS owns:

- itinerary feasibility and planner classification;
- trail ontology, route overlay/spine authority, and direction semantics;
- terrain, shelter/campsite, resupply, recovery, ingress, and egress reasoning;
- schema-versioned Plan API, trail inventory, plan JSON, and GPX artifacts;
- future personal-calibration import semantics after a separate contract.

HikerLogix Platform owns:

- Web planning workflows and centralized user/trip records;
- defined-trail Basic and Advanced planning inputs exposed to users;
- trip library, current-plan selection/download, and generated-plan history;
- `hikerlogix_current_plan_download_v1` and
  `hikerlogix_actuals_upload_v1`;
- actual-overlay persistence, server revisions, Operations/Analytics, and sync
  intake.

HikerLogix iOS owns:

- offline current-plan viewing and local persistence;
- local/freeform Custom placeholder and logbook plans;
- field journal entries, start/stop times, photos, ratings, sleep/recovery, and
  optional manual weather observations;
- planned-versus-actual overlays, pause/resume, and user-owned hike history;
- local upload queue behavior and native privacy/permission flows.

Neither HikerLogix surface should reproduce CairnOS route feasibility, trail
ontology, or planning semantics. None of the three products replaces official
sources, guidebooks, maps, navigation tools, or field judgment.

## Planning And Lifecycle Shape

The HikerLogix product recognizes three planning mechanisms:

1. Defined-trail Basic: a small set of controls submitted through Platform to
   CairnOS.
2. Defined-trail Advanced: selected anchors and controls submitted through
   Platform while CairnOS still chooses and validates the itinerary.
3. Custom: a placeholder/local/logbook plan. It is not CairnOS-validated
   planned truth.

Platform/iOS workflow language is Draft, Planned, In Progress, Paused,
Completed, and Archived. Completion locks editing until explicit reopen;
pause/resume changes eligible future actual dates without mutating planned
truth. Plan-number display, lifecycle UI, and date-cascade behavior are
HikerLogix concerns, not CairnOS contract semantics.

## Contract Layering

The current CairnOS versions remain:

- `cairnos_plan_api_v1` for stateless plan generation;
- `cairnos_plan_v1` for planned itinerary/reasoning export;
- `cairnos_trail_inventory_v1` for promoted inventory metadata;
- `cairnos_route_gpx_v1` for full-plan and per-day waypoint-only GPX artifacts.

Defined-trail Advanced may submit the additive
`required_overnight_anchor_ids` and `required_resupply_anchor_ids` fields in
`cairnos_plan_api_v1`. The ids come from the direction-ordered
`cairnos_trail_inventory_v1.required_anchor_options` lists. They are hard,
exactly-once partial anchors, not preferences or a manually assembled
itinerary. CairnOS may add any other overnight or resupply locations needed to
complete a feasible plan. Successful `cairnos_plan_v1` output reports
`cairnos_required_planning_anchors_v1` status and attaches the stable ids to
daily/resupply planned truth; invalid or infeasible anchors return a normalized
Plan API `400 validation_error`.

Platform wraps accepted planned truth in
`hikerlogix_current_plan_download_v1`. Platform accepts approved user-owned
daily actual overlays through `hikerlogix_actuals_upload_v1`. Those HikerLogix
contracts do not extend or version CairnOS schemas.

CairnOS owns route-spine/overlay authority and uses it to resolve GPX
waypoints. The current GPX artifacts do not contain route or track geometry and
must not be presented as navigation authority. Platform and iOS may expose or
share the artifacts where supported while preserving that warning.

## Actuals And Analytics Boundary

The approved HikerLogix actuals loop is implemented for non-sensitive daily
overlay fields: iOS captures and queues user-owned actuals; Platform persists
them with sync revisions and exposes them in Operations/Analytics without
mutating planned truth.

Daily records can include planned-versus-actual dates and stops, skipped
days/sections, notes, photos, start/stop times, and sync metadata. Some richer
mobile fields travel through HikerLogix TripRecord metadata rather than
`hikerlogix_actuals_upload_v1`. CairnOS does not ingest these records today.

Analytics is the HikerLogix completed/archived hike analysis surface. Future
charts, maps, and AI-assisted analysis remain HikerLogix product work and
should not move into CairnOS planning contracts.

## Weather And Future Calibration

Weather enrichment is next planned HikerLogix work, not a current CairnOS or
Platform weather-upload contract. Manual iOS observations may exist locally or
in HikerLogix TripRecord metadata. WeatherKit/provider collection, sensitive
uploads, and planning/calibration use require separate privacy and contract
review.

A future CairnOS calibration import may consume user-owned actuals for personal
pacing, gear, food, resupply, or recovery calibration. Imported actuals must
never override trail data, route-overlay authority, terrain reconciliation, or
operational truth.

## Multi-Repository Workflow

Keep CairnOSv1, HikerLogix Platform, and HikerLogix iOS as separate repository
roots. For contract changes, merge in this order:

1. CairnOS export/schema/API change.
2. Platform wrapper, persistence, API, fixture, and UI change.
3. iOS import, cache, display, actuals, and fixture change.

Record the exact authority commit and fixture version in each affected change.
No CairnOS schema update is required for the current architecture sync.

## Safety And Privacy

- Keep private journals, photos, health data, precise location, weather data,
  device identifiers, and calibration inputs out of this repository.
- CairnOS output is advisory planning information, not navigation, emergency,
  weather-safety, medical, or guidebook authority.
- Preserve planned truth and user-owned actuals as distinct layers.

See `docs/OPEN_SOURCE_AND_IP_STRATEGY.md` for licensing and product-posture
guidance.
