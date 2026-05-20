# HikerLogix Plan Import Contract

CairnOS plan JSON is the file-based contract for the future HikerLogix mobile
companion. HikerLogix should import it as read-only planned itinerary truth,
store mobile actuals separately, and never reimplement CairnOS planner logic.

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

Optional sections such as `resupply_town_details`, `selected_experiences`, and
`season_advisories` should be displayed when present but must not block import.

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

