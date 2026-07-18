# HikerLogix Plan Import Contract

CairnOS plan JSON is the file-based planned-truth contract for HikerLogix
Platform and transition iOS import. Consumers import it read-only, store actuals
separately, and never reimplement CairnOS planner logic.

Platform `hikerlogix_current_plan_download_v1` and
`hikerlogix_actuals_upload_v1` are downstream HikerLogix wrapper/intake
contracts. They are not CairnOS schemas and do not change `cairnos_plan_v1`.

## Supported Version

The current supported export version is:

```text
cairnos_plan_v1
```

Mobile importers must reject unsupported `export_version` values with a clear
message. During alpha, v1 is additive: importers should ignore unknown fields
and preserve the original imported JSON for troubleshooting.

## Required Sections

HikerLogix v1 import should require these top-level sections:

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
- `daily_plan`
- `warnings`

Optional additive sections such as `route_extent`, `access_point_anchors`,
`required_anchors`, `resupply_town_details`, `selected_experiences`, and
`season_advisories` should be displayed when present but must not block import.
Exact SECTION handling is documented in
`docs/SECTION_ACCESS_POINT_CONTRACT.md`.

## Read-Only Import Rules

- Imported CairnOS fields are planned values.
- HikerLogix actuals must be stored as a separate user-owned layer keyed to the
  imported plan day or stop.
- Actuals can be compared against planned rows but must not mutate imported
  CairnOS plan rows.
- HikerLogix must not treat the plan as navigation, emergency, weather, water,
  closure, medical, or official guidebook authority.
- Gaia GeoJSON remains a separate navigation-tool export and is not the mobile
  plan contract.

## Optional Route GPX Artifacts

CairnOS also embeds `cairnos_route_gpx_v3` route GPX artifacts in the additive
`route_gpx` Plan JSON section when daily plan rows are available. These
artifacts are optional companions for Platform/iOS import and sharing
workflows, not replacements for CairnOS Plan JSON.

The top-level contract uses `geometry_mode: full_plan_track`. The manifest entry
with `scope: full_plan` contains one standard GPX `trk`/`trkseg` composed from
the exact promoted `cairnos_route_selection_v1` ingress/egress IDs and the
canonical Long Trail spine, ordered for the plan direction. Moving-day entries
use `geometry_mode: daily_track` and contain a mileage-bounded slice plus their
planned start/stop waypoints. Zero-mile or otherwise unsliceable days remain
`waypoint_only`.

Platform/iOS should use the full-plan manifest `filename` to resolve the GPX
string in `artifacts` when rendering the route line. Consumers must preserve
`route_selection`, inspect manifest `geometry_sources`, and surface
`selected_route_geometry_unavailable` without synthesizing or substituting a
branch. Current data promotes North Adams geometry; Williamstown and Journey's
End remain explicit gaps. Off-spine overnight access remains omitted. All GPX
artifacts are advisory and must not be used as navigation, distance, elevation,
closure, water, weather, or safety authority.

For SECTION, `route_gpx.route_extent` echoes the selected access-ID bounds and
the full-plan geometry source exposes the canonical minimum/maximum mile slice.
Intentional `approach_none_ingress` and `approach_none_egress` selections add no
branch and are not geometry-unavailable warnings. Consumers must render the
supplied slice rather than deriving section geometry.

## Fixture Contract

Deterministic NOBO and SOBO fixtures live under:

```text
cairn/tests/fixtures/plan_json/
```

These fixtures are intentionally complete enough for mobile import work. They
include multi-day `daily_plan` rows, resupply rows, feasibility analysis,
directional access, warnings, and representative alpha planning fields.

HikerLogix should use these fixtures as shared contract references before
normalizing imported plans into native persistence models.

## Privacy And Provenance

Plan JSON must not contain absolute local paths, Streamlit secrets, private
tester data, proprietary guidebook text, local calibration files, or raw vendor
exports. Trail data and business details remain advisory and provenance-bound.
