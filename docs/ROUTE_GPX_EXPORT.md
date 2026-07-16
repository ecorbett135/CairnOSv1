# CairnOS Route GPX Export

`cairn/export/route_gpx.py` builds minimal GPX artifacts for downstream
HikerLogix Platform and iOS import work.

The first version is intentionally waypoint-only. It emits planned daily
start/stop waypoints for:

- one full-plan GPX file
- one GPX file per planned day
- manifest entries describing each generated artifact

It does not emit GPX routes or tracks. CairnOS does not yet have a validated
daily route-geometry slicing contract, and the existing Gaia daily LineString
work remains a separate manual-validation task.

## Export Version

The current route GPX export version is:

```text
cairnos_route_gpx_v1
```

The export payload uses:

```text
geometry_mode: waypoint_only
```

Consumers must treat the GPX files as planned waypoint context only, not as
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
scope, filename, media type, export version, geometry mode, waypoint count, and
warning codes. Day entries also include the day number, division, start/stop
miles, daily miles, and start/stop labels from the itinerary row.

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
- future HikerLogix mobile persistence, UI, and actuals capture

Future route/track GPX geometry should be added only after CairnOS has a
validated way to slice daily route geometry without changing planner semantics
or weakening overlay-authoritative traversal rules.
