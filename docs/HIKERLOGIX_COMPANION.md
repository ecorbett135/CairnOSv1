# HikerLogix Companion Integration

This document records a future integration path between CairnOSv1 and the older
HikerLogix iOS prototype.

CairnOSv1 remains the source of planned itinerary truth. HikerLogix should
become the mobile field execution layer if this integration is revived. It
should not be "CairnOS on a phone"; it should own what happens during trail
use: offline itinerary access, daily journal entries, actuals capture,
planned-versus-actual review, and lightweight adaptive recommendations.

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
- offline imported itinerary use
- offline field journaling
- actual start, stop, mileage, overnight, zero, and nero capture
- planned-versus-actual review
- lightweight adaptive recommendations from plan plus actuals
- personal hike history
- optional gear, food, weather observations, and HealthKit/workout summaries

Neither project should try to replace Gaia, FarOut, HiiKER, Garmin, paper maps,
guidebooks, official sources, or field judgment.

## Field Execution MVP

The first useful HikerLogix product should be built around actual trail use,
not broad mobile parity with the CairnOS Streamlit surface.

The MVP should include:

- importing a CairnOS plan JSON file
- storing the imported itinerary for offline use
- showing daily itinerary, mileage, overnight, resupply, and warnings
- recording daily journal notes and actual progress
- comparing planned values against actual field outcomes
- suggesting simple advisory adjustments from remaining plan and actual pace

Live town hours, post office hours, store hours, automated weather ingestion,
and richer reporting should stay post-MVP until data authority, freshness,
disclaimers, and failure modes are designed explicitly.

## Licensing And Repository Posture

CairnOSv1 is public and Apache 2.0 licensed because the alpha needs public
deployment, tester trust, reproducibility, and export interoperability.

HikerLogix does not need to inherit that posture. The mobile app can remain
private and proprietary while it imports CairnOS plan JSON or uses
Apache-licensed CairnOS contracts. CairnOS being public for Streamlit hosting
does not require mobile UI, local persistence, HealthKit permissions,
monetization logic, or App Store packaging to become public.

Commercial value should live primarily in HikerLogix execution and user-owned
actuals workflows:

- polished mobile UX
- offline imported itinerary use
- offline field journaling
- planned-versus-actual review
- lightweight adaptive recommendations
- personal calibration
- optional cloud backup or sync
- paid exports, analytics, or curated trail packs with clean rights

Do not commit HikerLogix proprietary implementation details, private tester
actuals, App Store monetization experiments, or patent-sensitive design notes to
CairnOSv1 simply because this repository is public.

## Roadmap Placement

Track this as export interoperability first and personal calibration later.

Documentation can happen before SECTION planning because it clarifies boundaries
and reduces product drift. Implementation should wait until the CairnOS export
contract is stable enough to support downstream consumers.

Recommended order:

1. Document the companion concept.
1. Add a CairnOS-native plan JSON export.
1. Build HikerLogix import and read-only itinerary viewing.
1. Add HikerLogix offline journal and actuals capture.
1. Add HikerLogix planned-versus-actual review and simple advisory adjustments.
1. Add CairnOS actuals import and reporting after the mobile actuals model is
   proven.
1. Use actuals for personal pacing, gear, and resupply calibration.

## V1 Export Shape

The first implementation should be file-based, not network/API-based.

CairnOS exports a deterministic, schema-versioned JSON plan in addition to the
existing Gaia GeoJSON export. Gaia GeoJSON remains navigation-tool-oriented;
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
JSON first and normalize later only if needed. The primary early consumer is an
offline itinerary view, not a live planning API.

The current contract is documented in `docs/PLAN_JSON_EXPORT.md` and starts
with `cairnos_plan_v1`. The read-only mobile import rules and deterministic
fixture expectations are documented in `docs/HIKERLOGIX_IMPORT_CONTRACT.md`.

## Multi-Repository Workflow

CairnOSv1 and HikerLogix are developed as separate repositories inside the
same VS Code multi-root workspace:

- `/Users/ecorbett/Documents/Development/CairnOS-HikerLogix.code-workspace`

Do not combine the repositories, add one as a submodule, or move source between
them unless a future architecture decision explicitly changes that boundary.

For cross-repository features, use matching short-lived branch names and
separate pull requests. CairnOS contract, export, or schema changes should land
first. HikerLogix should then update import models, fixtures, and UI against
the committed CairnOS contract. This keeps CairnOS as the planning authority and
HikerLogix as the mobile field-execution layer.

Use the GitHub MCP/plugin for issue, pull request, and roadmap updates. Use the
Build iOS Apps/XcodeBuildMCP tooling for HikerLogix simulator build, run, test,
screenshot, and UI-inspection work when available.

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

HikerLogix adaptive recommendations should remain explainable and advisory.
They may use the imported plan, remaining itinerary, and user-owned actuals to
surface options, but they must not claim live condition authority or safety
authority.

## Acceptance Criteria

- CairnOS plan JSON is deterministic and schema-versioned.
- Export preserves NOBO/SOBO direction, guidebook miles, ingress/egress,
  resupply rows, feasibility analysis, warnings, and daily itinerary fields.
- Existing Gaia export behavior remains unchanged.
- Existing CairnOS tests continue to pass.
- HikerLogix field execution starts with offline import, journal, actuals, and
  planned-versus-actual review.
- Future actuals import treats user data as calibration input only.

## Risks

- Schema drift if HikerLogix normalizes imported plans too early.
- Product drift into mobile navigation or map editing.
- Privacy risk from location, HealthKit, or workout actuals.
- Confusion between planned itinerary truth, user actuals, and curated trail
  data.
- Premature live-data features that imply authority over store hours, weather,
  closures, or safety conditions.

The mitigation is to keep v1 file-based, read-only on import, and explicit about
planned values versus actual values.

See `docs/OPEN_SOURCE_AND_IP_STRATEGY.md` for the broader CairnOS/HikerLogix
open-source, commercial-use, copyright, and patent posture.
