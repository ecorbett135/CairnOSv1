# CairnOS Route GPX Export

`cairn/export/route_gpx.py` builds GPX artifacts for downstream HikerLogix
Platform and iOS import work.

The current contract emits planned daily start/stop waypoints for:

- one full-plan GPX file with the compiled Long Trail spine as a GPX track
- one waypoint-only GPX file per planned day
- manifest entries describing each generated artifact

The full-plan file preserves all existing waypoints and adds one standard GPX
`trk` with one `trkseg`. Its `trkpt` values come from
`compiled/spine.geojson`. They remain in source order for NOBO and are reversed
for SOBO. Per-day files do not contain `trk` or `rte` geometry because CairnOS
does not yet have a validated daily route-geometry slicing contract.

## Export Version

The current route GPX export version is:

```text
cairnos_route_gpx_v2
```

The export payload uses:

```text
geometry_mode: full_plan_track
```

The top-level `geometry_mode` and the full-plan manifest entry use
`full_plan_track`. Per-day manifest entries continue to use:

```text
geometry_mode: waypoint_only
```

If compiled spine geometry is unavailable, v2 falls back to
`geometry_mode: waypoint_only`, emits no track, and reports
`missing_route_spine_geometry`.

The v2 bump records the addition of track geometry. Existing artifact
filenames, GPX waypoints, and the CairnOS XML extension namespace are preserved.

Consumers must treat the GPX files as advisory planned-route context, not as
navigation, turn-by-turn, distance, elevation, closure, water, weather, or
safety authority.

## Public Function

Use:

```python
from cairn.export.route_gpx import build_route_gpx_artifacts

export = build_route_gpx_artifacts(
    daily_plan,
    trail_root,
    direction="NOBO",
    trail_id="vermont_long_trail",
)
```

The returned payload includes:

- `export_version`
- `generated_at`
- `trail_id`
- `direction`
- `geometry_mode`
- `warnings`
- `manifest`
- `artifacts`

`artifacts` maps GPX filenames to GPX XML strings. `manifest` has one entry for
the full-plan artifact and one entry for each day artifact. Each entry records
scope, filename, media type, export version, geometry mode, waypoint count,
track count, track-segment count, track-point count, and warning codes. The
full-plan entry also records `geometry_source: compiled/spine.geojson`. Day
entries include the day number, division, start/stop miles, daily miles, and
start/stop labels from the itinerary row.

Platform/iOS consumers should locate the manifest entry with
`scope: full_plan`, resolve its `filename` in `artifacts`, and parse the standard
GPX `trk/trkseg/trkpt` hierarchy. The day entries remain useful as shareable
waypoint context but must not be expected to render a route line.

## Coordinate Resolution

The GPX exporter reuses the existing Gaia export coordinate-resolution path for
daily start and stop waypoints:

- curated resupply access coordinates
- Gaia waypoint reference enrichment
- compiled crossing reference
- compiled route overlay points
- spine interpolation fallback

If a waypoint cannot be resolved, the exporter omits that waypoint and returns
a `missing_waypoint_coordinates` warning for the affected day and start/stop
position.

## Boundaries

The route GPX artifact layer is separate from:

- CairnOS Plan JSON, which remains the itinerary and reasoning contract
- Gaia GeoJSON, which remains navigation-tool-oriented review/export output
- developer diagnostics ZIPs
- HikerLogix Platform/iOS persistence, UI, and actuals capture

The full-plan track is the compiled mainline Long Trail spine. It does not
include selected ingress/egress branches, off-spine overnight access, or route
deviations. Those boundaries are explicit in the GPX description and the
`full_plan_spine_only` warning.

Future per-day route/track geometry should be added only after CairnOS has a
validated way to slice daily route geometry without changing planner semantics
or weakening overlay-authoritative traversal rules. The spine's source and
reuse rights remain subject to the unresolved provenance entries in
`data/DATASETS.md`.

CairnOS remains the route-spine/overlay authority. The current
`cairnos_route_gpx_v2` artifacts use that authority to resolve planned
waypoints and expose the compiled mainline spine as advisory full-plan GPX
track geometry.
