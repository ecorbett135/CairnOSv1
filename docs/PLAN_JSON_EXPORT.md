# CairnOS Plan JSON Export

CairnOS plan JSON is the stable file-based planned-truth export contract for
downstream itinerary consumers such as HikerLogix Platform and transition iOS
import.

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
- `route_extent`
- `access_point_anchors`
- `required_anchors`
- `resupply_plan`
- `resupply_town_details`
- `selected_experiences`
- `season_advisories`
- `daily_plan`
- `route_gpx`
- `warnings`

PlannerV2 field names are intentionally preserved inside these sections. The
goal is to let HikerLogix import the file read-only first instead of forcing a
mobile-specific normalized schema too early.

## Route GPX Artifacts

The export embeds an additive `route_gpx` section using the
`cairnos_route_gpx_v4` contract. It includes a manifest plus GPX XML artifacts
for the full plan and each planned day. The full-plan artifact composes
promoted geometry for exactly the stable `cairnos_route_selection_v1`
ingress/egress IDs around the canonical Long Trail spine. Moving-day artifacts
contain mileage-bounded track slices; all artifacts preserve planned daily
start/stop waypoints.

V4 adds source-authoritative GPX `<ele>` meters, reproducible
length/ascent/descent/signed-average-grade metrics, ordered route-part
identity/provenance, and explicit geometry/elevation completeness. See
`docs/ROUTE_GPX_EXPORT.md` for the exact Platform pass-through and iOS/Web
profile-consumer handoff.

Downstream clients may expose these artifacts for Gaia GPS, COROS, Files, or
other import workflows. They must honor manifest `geometry_sources`, surface
geometry-unavailable warnings without substituting another branch, and must not
present the GPX as navigational authority. Zero-mile or otherwise unsliceable
day artifacts use `geometry_mode: waypoint_only`.

SECTION exports use additive `cairnos_route_extent_v1` and
`cairnos_access_point_anchors_v1` sections. Canonical full-trail miles remain
the planned-truth mile fields; section-relative fields measure travel distance
from the selected access-point start. `route_gpx.route_extent` and manifest
canonical bounds identify the supplied spine slice. Exact Platform examples
are in `docs/SECTION_ACCESS_POINT_CONTRACT.md`.

## Privacy And Provenance

The export redacts absolute local paths and records the trail root as a
repository-relative path such as:

```text
trails/vermont_long_trail
```

It does not include raw third-party route exports, private tester files, local
calibration references, Streamlit secrets, or generated diagnostics payloads.

## HikerLogix Boundary

HikerLogix treats this file as planned itinerary truth from CairnOS. Platform
and iOS store user-owned actuals separately and compare those actuals against
the imported plan, but actuals should be calibration input only. They should not
override CairnOS trail data, terrain reconciliation, route overlay authority, or
operational truth.

Platform `hikerlogix_current_plan_download_v1` wraps selected field plans and
`hikerlogix_actuals_upload_v1` accepts approved actual overlays. Those are
HikerLogix-owned downstream contracts, not CairnOS export versions.

The mobile import contract is documented in
`docs/HIKERLOGIX_IMPORT_CONTRACT.md`. Deterministic NOBO and SOBO fixture exports
live under `cairn/tests/fixtures/plan_json/` and should be used as the shared
contract reference for HikerLogix import work.

## Safety Notice

CairnOS plan JSON is advisory alpha output. Hikers must verify routes, services,
closures, weather, water, and backcountry decisions with official and current
sources before relying on a plan.
