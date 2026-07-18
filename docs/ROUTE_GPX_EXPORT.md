# CairnOS Route GPX Export

`cairn/export/route_gpx.py` builds advisory GPX artifacts for downstream
HikerLogix Platform and iOS import. `cairn/export/route_geometry.py` owns route
composition and mileage-bounded slicing behind that export surface.

The current contract emits:

- one full-plan GPX file with selected promoted ingress/egress geometry
  composed around the canonical defined-trail spine;
- one GPX file per planned day, with a moving-track slice when the day has a
  non-zero mileage interval;
- the existing planned daily start/stop waypoints in both scopes;
- standard GPX `<ele>` values on every track point whose selected route part
  has promoted source elevation;
- deterministic length, ascent, descent, and average-grade metrics; and
- manifest route-part identity, provenance, completeness, and warning metadata.

Approach geometry is never inferred from a display name and is never attached
globally. The caller supplies the stable IDs normalized by
`cairnos_route_selection_v1`, and the exporter composes only those IDs.

## Export Version

The current route GPX export version is:

```text
cairnos_route_gpx_v4
```

The top-level and full-plan manifest geometry mode remains:

```text
full_plan_track
```

Moving-day entries use:

```text
daily_track
```

Zero-mile, missing-mile, or otherwise unsliceable day entries fall back to:

```text
waypoint_only
```

If the canonical spine is unavailable, the full-plan artifact also falls back
to `waypoint_only` and reports `missing_route_spine_geometry`.

V4 is additive over v3. Every v3 top-level field, manifest field, filename,
waypoint semantic, GPX 1.1 `trk/trkseg/trkpt` shape, and CairnOS XML extension
namespace remains stable. V4 adds standard GPX `<ele>`, `route_parts`,
`route_completeness`, per-artifact `elevation`, `metrics`,
`geometry_coverage`, `route_elevation_complete`, and route-part ranges in
`geometry_sources`.

Consumers that still accept v3 can keep importing coordinates and waypoints.
Consumers that render profiles should opt into v4 and enforce the completeness
rules below instead of assuming that a non-empty track is a complete selected
route.

## Route Selection Contract

Plan API requests may include:

```json
{
  "route_selection": {
    "contract_version": "cairnos_route_selection_v1",
    "ingress_approach_id": "approach_north_adams",
    "egress_approach_id": "egress_journeys_end"
  }
}
```

Legacy `cairnos_plan_api_v1` requests that provide only `ingress_route` and
`egress_route` remain valid. CairnOS resolves each name to exactly one compiled
`approach_id`, validates direction/terminus compatibility, and echoes the
normalized stable-ID object in Plan JSON and `route_gpx`.

Unknown IDs, ID/name mismatches, direction/terminus incompatibility, and
disconnected promoted geometry return deterministic Plan API validation errors.
A known compatible selection without promoted geometry remains valid and emits
`selected_route_geometry_unavailable`; no other branch is substituted.

`GET /v1/plan-options` returns the route-selection version, stable IDs,
directional roles, and `geometry_status` for current clients.

## Public Function

Use:

```python
from cairn.export.route_gpx import build_route_gpx_artifacts

export = build_route_gpx_artifacts(
    daily_plan,
    trail_root,
    direction="NOBO",
    trail_id="vermont_long_trail",
    route_selection={
        "contract_version": "cairnos_route_selection_v1",
        "ingress_approach_id": "approach_north_adams",
        "egress_approach_id": "egress_journeys_end",
    },
)
```

The returned payload includes:

- `export_version`;
- `generated_at`;
- `trail_id`;
- `direction`;
- normalized `route_selection`;
- ordered `route_parts` for selected ingress, spine, and selected egress,
  including explicit unavailable parts;
- `route_completeness` for the full planned interval;
- `geometry_mode`;
- `warnings`;
- `manifest`;
- `artifacts`.

`artifacts` maps GPX filenames to GPX XML strings. `manifest` has one entry for
the full-plan artifact and one entry for each day. Each entry records scope,
filename, media type, export version, geometry mode, waypoint count, track
count, track-segment count, track-point count, source metadata, warning codes,
and day metadata where applicable. V4 entries additionally include:

- `elevation.status`: `complete`, `partial`, or `unavailable` for emitted track
  points;
- `elevation.unit`: `m`;
- elevation point and missing-point counts;
- `metrics.length_m`, `metrics.total_ascent_m`,
  `metrics.total_descent_m`, and `metrics.average_grade_percent`;
- explicit metric-method identifiers;
- `geometry_coverage`, including requested/covered mile intervals and gaps;
- `route_elevation_complete`, which is true only when geometry covers the
  entire planned interval and every emitted point has elevation; and
- ordered `geometry_sources` ranges with `route_part_id`, point indexes,
  geometry identity, elevation status, and provenance.

Platform/iOS consumers should locate `scope: full_plan`, resolve its `filename`
in `artifacts`, and parse standard GPX track geometry. Clients may also use the
per-day entries for sharing or display, but CairnOS Plan JSON remains the
planned-truth contract.

## Composition And Direction

The canonical spine keeps the same horizontal coordinate order and identity in
`compiled/spine.geojson`; v4 additively retains its source-embedded third
elevation coordinate. Export composition builds a transient route from:

1. selected ingress geometry, when promoted;
2. the generated plan's covered interval on the defined-trail spine;
3. selected egress geometry, when promoted.

NOBO traverses northbound-reference miles in ascending order. SOBO reverses
the same geometry and miles; it does not create a separate mile system. A
southern approach therefore appears before the spine for NOBO ingress and after
the reversed spine for SOBO egress.

Full-plan bounds come from the first planned start mile and final planned stop
mile. Daily bounds come from each row's `daily_start_mile` and
`daily_stop_mile`. Each selected geometry piece is sliced by its explicit mile
domain over cumulative coordinate distance. A day that crosses mile 0 can
therefore contain selected southern approach geometry followed by the spine;
the equivalent SOBO day reverses that order.

This slicing is export interoperability, not planner traversal authority.
Guidebook miles and overlay semantics remain the public planning domain.

## Authoritative Elevation And Metrics

The canonical spine compiler promotes the `<ele>` value already embedded on
each point in `raw/gpx/long-trail-spine.gpx`. GPX elevation is meters. The
current source has complete elevation for all 19,817 spine points.

The approach compiler promotes the third coordinate already embedded in the
exact mapped source feature. The current North Adams source has complete meter
elevation for all 453 promoted coordinates. The compiler does not copy the
fourth coordinate, source notes, or personal metadata.

CairnOS does not fill missing route elevation from the PlannerV2 terrain
profile, `route_master.csv`, an unrelated approach, a vendor total, or a
whole-route interpolation. Mileage slicing can create a boundary point inside
one source segment. Its elevation is calculated only between the two adjacent
source points that bound that same segment and is reported as
`linear_between_adjacent_source_elevations_at_mileage_slice_boundary`. If
either adjacent point lacks elevation, the boundary point has no `<ele>` and
the artifact is incomplete.

Metrics are calculated from the exact numeric precision emitted into GPX:

- `length_m`: WGS84-coordinate haversine segment sum;
- `total_ascent_m`: sum of positive ordered `<ele>` deltas;
- `total_descent_m`: sum of absolute negative ordered `<ele>` deltas; and
- `average_grade_percent`: signed net elevation change divided by track length.

No smoothing threshold is applied to route-GPX contract metrics. This makes
them exactly reproducible from the emitted GPX. PlannerV2 terrain metrics use
their separately documented planning-oriented noise threshold and must not be
substituted for these track metrics.

`elevation.status: complete` means every emitted track point has `<ele>`.
`route_elevation_complete: true` additionally requires complete geometry for
the requested planned mileage interval. A selected branch with no promoted
geometry therefore keeps `route_elevation_complete` false even when every
emitted spine point has elevation.

Incomplete geometry emits `route_geometry_incomplete`. Any artifact that
cannot provide a complete planned-route profile emits
`authoritative_route_elevation_unavailable`. CairnOS never fabricates values to
silence either warning.

## Geometry And Elevation Provenance

Promoted approach geometry lives in additive `approach_geometries` records in:

```text
trails/vermont_long_trail/compiled/approach_trails.json
```

Each record carries a stable `approach_id`, stable `geometry_id`, connected
terminus, mile range, coordinate count, three-dimensional geometry when
source elevation is complete, elevation authority metadata, and exact minimal
provenance.
The source mapping is maintained in:

```text
trails/vermont_long_trail/raw/csv/approach_geometry_sources.csv
```

The first promoted branch is:

- approach ID: `approach_north_adams`;
- geometry ID: `approach_north_adams_geometry_v1`;
- source: `raw/geojson/gaia_reference.geojson`;
- source feature ID: `399a680d-2d50-440e-a22a-c82fd457f3fd`;
- source feature title: `North Adams Approach Trail`;
- source update timestamp: `2026-04-18T19:12:44Z`;
- source coordinate count: 453;
- source-license status: `UNKNOWN — needs review`.

The compiler copies longitude, latitude, and source-embedded elevation only.
It excludes the source feature's fourth coordinate, notes, and non-geometry
personal metadata. The unresolved source-license status remains an explicit
reuse limitation.

Current Williamstown and Journey's End selections have no promoted geometry.
They appear in ordered `route_parts` with `geometry_status: unavailable` and
`elevation.status: unavailable`, warn explicitly, and do not receive North
Adams geometry or synthesized elevation.

## Exact Platform Pass-Through Handoff

HikerLogix Platform should:

1. accept both `cairnos_route_gpx_v3` and `cairnos_route_gpx_v4` during the
   compatibility window;
2. persist and return the complete `route_gpx` object without renaming files,
   changing order, converting units, recalculating metrics, or parsing and
   reserializing GPX XML;
3. validate that every manifest `filename` resolves exactly once in
   `artifacts` and serve/download that value as `application/gpx+xml`;
4. preserve `route_selection`, `route_parts`, `route_completeness`, warnings,
   manifest order, source point indexes, identity, and provenance verbatim;
5. treat `scope: full_plan` as the full-profile artifact and `scope: day` plus
   `day` as the daily-profile mapping; and
6. expose a profile as complete only when the selected manifest entry has
   `route_elevation_complete: true`.

Platform must not backfill a missing `<ele>`, missing selected branch, or null
metric. A partial artifact may remain downloadable with its warnings, but it
must not be relabeled as a complete selected-route elevation profile.

Plan display naming remains a Platform-owned persistence/UI contract, separate
from CairnOS artifact filenames. Generated defaults are exactly
`<Trail> <Direction> Thru` for full-trail plans and
`<Trail> <Direction> Section` for bounded sections, never `... Plan` and never
CairnOS-branded. Renaming a generated or custom plan must not change its
internal UUID or human `LT###`/`CP###` display number. Apply that rule in
Django/API persistence and React creation, edit, and review surfaces.

## Exact iOS And Web Consumer Handoff

iOS and Web consumers should:

1. select the manifest entry by `scope` and, for daily profiles, exact `day`;
2. resolve its `filename` in `artifacts` without constructing a filename;
3. parse GPX 1.1 namespace-aware `trk/trkseg/trkpt` in document order;
4. parse each standard `<ele>` as meters and require
   `elevation.elevation_point_count == track_point_count` before drawing a
   complete profile;
5. use manifest `metrics` for labels/summaries and may independently verify
   them from the emitted points using the declared methods;
6. preserve traversal order exactly; SOBO is already reversed and its ascent,
   descent, and signed average grade are direction-aware;
7. use `geometry_sources[*].point_start_index` and `point_end_index` or the GPX
   `cairnos:route_parts` extension to retain ingress/spine/egress identity; and
8. disable or clearly mark the profile incomplete when
   `route_elevation_complete` is false, showing the supplied warning instead of
   interpolating a gap locally.

The committed downstream fixture is:

```text
cairn/tests/fixtures/route_gpx/elevation_contract_v4.json
```

It contains parseable GPX with `<ele>` plus manifest values that independently
recompute to the same length, descent, and signed average grade.

## Coordinate Resolution And Waypoint Preservation

Waypoints continue to use the Gaia export coordinate-resolution path:

- curated resupply access coordinates;
- Gaia waypoint reference enrichment;
- compiled crossing reference;
- compiled route overlay points;
- spine interpolation fallback.

If a waypoint cannot be resolved, the exporter omits that waypoint and reports
`missing_waypoint_coordinates` for its day and start/stop position. Track
generation does not remove or rename successfully resolved waypoints.

## Boundaries

The route GPX layer is separate from:

- CairnOS Plan JSON, the itinerary and reasoning contract;
- Gaia GeoJSON, the navigation-tool-oriented review/export output;
- developer diagnostics ZIPs;
- HikerLogix persistence, UI, actuals, and sync.

Off-spine overnight access, route deviations, turn-by-turn guidance, closures,
weather, water, and safety decisions remain outside this contract. All GPX
artifacts are advisory planned-route context and are not navigational authority.
