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
- manifest geometry-source and warning metadata.

Approach geometry is never inferred from a display name and is never attached
globally. The caller supplies the stable IDs normalized by
`cairnos_route_selection_v1`, and the exporter composes only those IDs.

## Export Version

The current route GPX export version is:

```text
cairnos_route_gpx_v3
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

The v3 bump records stable selected-route identity, approach/spine composition,
daily route slicing, and source manifests. Filenames, waypoint semantics, GPX
1.1 `trk/trkseg/trkpt`, and the CairnOS XML extension namespace remain stable.

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
- `geometry_mode`;
- `warnings`;
- `manifest`;
- `artifacts`.

`artifacts` maps GPX filenames to GPX XML strings. `manifest` has one entry for
the full-plan artifact and one entry for each day. Each entry records scope,
filename, media type, export version, geometry mode, waypoint count, track
count, track-segment count, track-point count, source metadata, warning codes,
and day metadata where applicable.

Platform/iOS consumers should locate `scope: full_plan`, resolve its `filename`
in `artifacts`, and parse standard GPX track geometry. Clients may also use the
per-day entries for sharing or display, but CairnOS Plan JSON remains the
planned-truth contract.

## Composition And Direction

The canonical spine remains unchanged in `compiled/spine.geojson`. Export
composition builds a transient route from:

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

## Geometry Provenance

Promoted approach geometry lives in additive `approach_geometries` records in:

```text
trails/vermont_long_trail/compiled/approach_trails.json
```

Each record carries a stable `approach_id`, stable `geometry_id`, connected
terminus, mile range, coordinate count, geometry, and exact minimal provenance.
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

The compiler copies two-dimensional geometry coordinates only. It excludes the
source feature's notes and non-geometry personal metadata. The unresolved
source-license status remains an explicit reuse limitation.

Current Williamstown and Journey's End selections have no promoted geometry.
They warn explicitly and do not receive North Adams geometry.

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
