# HikerLogix Companion Integration

This document records a future integration path between CairnOSv1 and the older
HikerLogix iOS prototype.

CairnOSv1 remains the source of planned itinerary truth. HikerLogix should
become a mobile field journal and personal actuals layer if this integration is
revived.

## Product Boundary

CairnOSv1 should own:

- itinerary feasibility and planning semantics
- terrain-aware pacing
- shelter and campsite selection
- resupply and recovery reasoning
- route overlay authority
- export interoperability

HikerLogix should own:

- iOS UI
- local mobile persistence
- offline field journaling
- personal hike history
- optional gear, food, weather, and HealthKit/workout actuals

Neither project should try to replace Gaia, FarOut, HiiKER, Garmin, paper maps,
guidebooks, official sources, or field judgment.

## Roadmap Placement

Track this as export interoperability first and personal calibration later.

Documentation can happen before SECTION planning because it clarifies boundaries
and reduces product drift. Implementation should wait until the CairnOS export
contract is stable enough to support downstream consumers.

Recommended order:

1. Document the companion concept.
1. Add a CairnOS-native plan JSON export.
1. Build HikerLogix import and read-only itinerary viewing.
1. Add HikerLogix offline actuals capture.
1. Add CairnOS actuals import and reporting.
1. Use actuals for personal pacing, gear, and resupply calibration.

## V1 Export Shape

The first implementation should be file-based, not network/API-based.

CairnOS should export a deterministic, schema-versioned JSON plan in addition to
the existing Gaia GeoJSON export. Gaia GeoJSON remains navigation-tool-oriented;
CairnOS plan JSON is itinerary-and-reasoning-oriented.

Minimum top-level fields:

- `export_version`, starting with `cairnos_plan_v1`
- `generated_at`
- `trail_id`
- `planner`
- `user_profile`
- `completion_analysis`
- `expedition_summary`
- `directional_access`
- `resupply_plan`
- `daily_plan`
- `warnings`

The v1 JSON should preserve existing PlannerV2 field names instead of inventing
a mobile-specific schema. HikerLogix can store the imported plan as read-only
JSON first and normalize later only if needed.

## Future Actuals Loop

HikerLogix may eventually record user-owned actuals:

- actual daily miles
- actual start and stop locations
- actual overnight location or type
- field notes
- gear used
- food and resupply actuals
- weather observations
- optional HealthKit or workout summaries

CairnOS may later import those actuals for personal calibration. Imported
actuals should inform future planning preferences, not override trail data,
terrain reconciliation, route overlay authority, or operational truth.

## Acceptance Criteria

- CairnOS plan JSON is deterministic and schema-versioned.
- Export preserves NOBO/SOBO direction, guidebook miles, ingress/egress,
  resupply rows, feasibility analysis, warnings, and daily itinerary fields.
- Existing Gaia export behavior remains unchanged.
- Existing CairnOS tests continue to pass.
- Future actuals import treats user data as calibration input only.

## Risks

- Schema drift if HikerLogix normalizes imported plans too early.
- Product drift into mobile navigation or map editing.
- Privacy risk from location, HealthKit, or workout actuals.
- Confusion between planned itinerary truth, user actuals, and curated trail
  data.

The mitigation is to keep v1 file-based, read-only on import, and explicit about
planned values versus actual values.
