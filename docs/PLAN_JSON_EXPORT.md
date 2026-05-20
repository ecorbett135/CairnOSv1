# CairnOS Plan JSON Export

CairnOS plan JSON is the stable file-based export contract for downstream
itinerary consumers such as the future HikerLogix mobile companion.

It is separate from Gaia GeoJSON and developer diagnostics:

- Gaia GeoJSON is map/navigation-tool oriented.
- Developer diagnostics ZIPs are reproducible alpha debugging bundles.
- CairnOS plan JSON is the planned-itinerary and reasoning contract.

## Schema Version

The v1 export uses:

```text
cairnos_plan_v1
```

The schema is additive during alpha. Consumers should ignore unknown fields and
must not treat the export as safety-critical trail authority.

## Top-Level Shape

The export includes:

- `export_version`
- `generated_at`
- `build_sha`
- `trail_id`
- `planner`
- `user_profile`
- `completion_analysis`
- `expedition_summary`
- `directional_access`
- `resupply_plan`
- `resupply_town_details`
- `selected_experiences`
- `season_advisories`
- `daily_plan`
- `warnings`

PlannerV2 field names are intentionally preserved inside these sections. The
goal is to let HikerLogix import the file read-only first instead of forcing a
mobile-specific normalized schema too early.

## Privacy And Provenance

The export redacts absolute local paths and records the trail root as a
repository-relative path such as:

```text
trails/vermont_long_trail
```

It does not include raw third-party route exports, private tester files, local
calibration references, Streamlit secrets, or generated diagnostics payloads.

## HikerLogix Boundary

HikerLogix should treat this file as planned itinerary truth from CairnOS.
HikerLogix may later store user-owned actuals and compare those actuals against
the imported plan, but actuals should be calibration input only. They should not
override CairnOS trail data, terrain reconciliation, route overlay authority, or
operational truth.

## Safety Notice

CairnOS plan JSON is advisory alpha output. Hikers must verify routes, services,
closures, weather, water, and backcountry decisions with official and current
sources before relying on a plan.
