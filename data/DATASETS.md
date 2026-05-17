# CairnOS Dataset Provenance Registry

This is a starter registry for tracked data-like assets currently present in
the repository. Unknown provenance is intentionally marked as
`UNKNOWN — needs review`; do not treat those datasets as reusable until the
missing details are resolved.

Rows may use path globs to cover related sidecar files or compiler outputs.
The registry covers the tracked non-code data-like assets found during the
initial licensing/provenance pass; it still needs human provenance review.

| Dataset | Path | Source | Source License | Derived From | Transformation Notes | Maintainer | Last Updated | Reuse Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Streamlit UI screenshots | `docs/images/*.png` | CairnOSv1 local Streamlit UI screenshots | Project documentation asset — review before external reuse | CairnOSv1 UI output | Generated manually for README documentation | Eric Corbett | 2026-05-14 | Documentation screenshot; may include UI framework styling. |
| Scenario configuration | `cairn/config/scenarios.json` | CairnOS project configuration | UNKNOWN — needs review | UNKNOWN — needs review | Test/planner scenario configuration | UNKNOWN — needs review | UNKNOWN — needs review | Treat as project config, not trail source data. |
| Long Trail route master | `trails/vermont_long_trail/raw/csv/route_master.csv` | UNKNOWN — needs review | UNKNOWN — needs review | UNKNOWN — needs review | Manual/curated operational trail route records | UNKNOWN — needs review | UNKNOWN — needs review | Core operational data; provenance must be resolved before reuse outside project. |
| Long Trail centerline CSV | `trails/vermont_long_trail/raw/csv/Centerline.csv` | UNKNOWN — needs review | UNKNOWN — needs review | UNKNOWN — needs review | Raw or legacy centerline records; exact provenance unknown | UNKNOWN — needs review | UNKNOWN — needs review | Compare against `route_master.csv`; do not assume same source/license. |
| Long Trail approach trails | `trails/vermont_long_trail/raw/csv/approach_trails.csv` | UNKNOWN — needs review | UNKNOWN — needs review | UNKNOWN — needs review | Manually curated approach/egress branch metadata | UNKNOWN — needs review | UNKNOWN — needs review | Manual Cairn data candidate; needs author/date/source notes. |
| Long Trail resupply amenities | `trails/vermont_long_trail/raw/csv/resupply_amenities.csv` | Long Trail Planning Guide plus manual coordinate curation — needs review | UNKNOWN — needs review | `https://www.longtrailvermont.com/trail-town-amenities/` and manual map review — needs review | Curated town access, services, zero-candidate flags, and road/trailhead coordinates | Eric Corbett / Cairn maintainers — needs review | 2026-05-14 | Do not assume source website content or coordinates are Apache licensed. |
| Long Trail towns CSV | `trails/vermont_long_trail/raw/csv/towns.csv` | UNKNOWN — needs review | UNKNOWN — needs review | UNKNOWN — needs review | Town/service metadata | UNKNOWN — needs review | UNKNOWN — needs review | Needs source and license confirmation. |
| Gaia reference waypoints | `trails/vermont_long_trail/raw/geojson/gaia_reference.geojson` | Gaia GPS export / manual Gaia waypoints — needs review | UNKNOWN — needs review | User-created Gaia data and possible map-derived waypoints — needs review | Raw reference enrichment; not operational truth | Eric Corbett / Cairn maintainers — needs review | 2026-05-14 | Do not redistribute as Apache without confirming waypoint/source rights. |
| Long Trail overnight reference waypoints | `trails/vermont_long_trail/raw/geojson/shelters.geojson`, `trails/vermont_long_trail/raw/geojson/campsites.geojson` | Gaia GPS export / manual shelter and campsite waypoints — needs review | UNKNOWN — needs review | User-created Gaia data and possible map-derived waypoints — needs review | Raw overnight reference enrichment; matched against route overlay and spine before planner use | Eric Corbett / Cairn maintainers — needs review | 2026-05-15 | Enrichment data only; do not redistribute as Apache without confirming waypoint/source rights. |
| Long Trail spine GPX | `trails/vermont_long_trail/raw/gpx/long-trail-spine.gpx` | UNKNOWN — needs review | UNKNOWN — needs review | UNKNOWN — needs review | Raw trail spine GPX | UNKNOWN — needs review | UNKNOWN — needs review | Core geometry source; provenance is a high-priority gap. |
| OSM POI shapefile bundle | `trails/vermont_long_trail/raw/shp/gis_osm_pois_free_1.*` | OpenStreetMap-derived shapefile export, provider UNKNOWN — needs review | ODbL likely if OSM-derived — needs review | OpenStreetMap POI data — needs review | Raw shapefile sidecar bundle | UNKNOWN — needs review | UNKNOWN — needs review | ODbL obligations may apply; preserve attribution and transformation notes. |
| OSM roads shapefile bundle | `trails/vermont_long_trail/raw/shp/gis_osm_roads_free_1.*` | OpenStreetMap-derived shapefile export, provider UNKNOWN — needs review | ODbL likely if OSM-derived — needs review | OpenStreetMap road data — needs review | Raw shapefile sidecar bundle | UNKNOWN — needs review | UNKNOWN — needs review | ODbL obligations may apply; preserve attribution and transformation notes. |
| Compiled approach trails | `trails/vermont_long_trail/compiled/approach_trails.json` | Generated by Cairn compiler — needs review | Inherits input dataset obligations — needs review | `raw/csv/approach_trails.csv` | Compiler output | Cairn compiler | 2026-05-14 | Derived data; not automatically Apache licensed. |
| Compiled schema registry | `trails/vermont_long_trail/compiled/cairn_schema_registry.json` | Generated by Cairn compiler | Project-authored schema artifact — needs review | Cairn schema/compiler definitions | Compiler output | Cairn compiler | 2026-05-14 | Likely project-authored schema artifact; verify before reuse. |
| Compiled crossings | `trails/vermont_long_trail/compiled/crossings*.geojson`, `trails/vermont_long_trail/compiled/crossings_refined.json` | Generated by Cairn compiler from OSM/trail inputs — needs review | Inherits OSM ODbL and other input obligations — needs review | OSM roads plus trail spine/overlay inputs | Road crossing detection/refinement outputs | Cairn compiler | 2026-05-14 | Treat as OSM-derived until proven otherwise. |
| Compiled logistics nodes | `trails/vermont_long_trail/compiled/logistics_nodes.json` | Generated by Cairn compiler from OSM/trail/town inputs — needs review | Inherits input dataset obligations — needs review | OSM POI/roads, towns, route overlay — needs review | Logistics node compiler output | Cairn compiler | 2026-05-14 | May include OSM-derived data; needs review. |
| Compiled route overlay | `trails/vermont_long_trail/compiled/route_overlay.json` | Generated by Cairn compiler from curated trail inputs — needs review | Inherits input dataset obligations — needs review | `route_master.csv`, resupply amenities, approach/crossing inputs | Operational overlay compiler output | Cairn compiler | 2026-05-14 | Operational truth for planner, but provenance remains mixed/unknown. |
| Compiled operational graph | `trails/vermont_long_trail/compiled/operational_graph.json` | Generated by Cairn compiler from compiled trail layers — needs review | Inherits input dataset obligations — needs review | Route overlay, crossings, logistics, approach trails, terrain layers | Graph compiler output | Cairn compiler | 2026-05-14 | Derived data; not automatically Apache licensed. |
| Compiled spine and terrain outputs | `trails/vermont_long_trail/compiled/spine.geojson`, `segments.*`, `terrain.geojson`, `nodes.geojson`, `metadata.json`, `itinerary.json` | Generated by Cairn compiler — needs review | Inherits input dataset obligations — needs review | GPX spine, DEM, route/graph inputs — needs review | Compiler/intermediate geospatial transformations | Cairn compiler | 2026-05-14 | Derived data; review DEM/GPX/source obligations. |
| Compiled waypoint reference | `trails/vermont_long_trail/compiled/waypoint_reference.json` | Generated by `gaia_reference_overlay.py` | Inherits Gaia/raw waypoint obligations — needs review | `raw/geojson/gaia_reference.geojson`, `route_overlay.json` | Gaia waypoint reference matching/enrichment output | Cairn compiler | 2026-05-14 | Enrichment data only; not operational truth. |
| Compiled overnight reference | `trails/vermont_long_trail/compiled/overnight_reference.json` | Generated by `overnight_reference.py` | Inherits raw shelter/campsite waypoint obligations — needs review | `raw/geojson/shelters.geojson`, `raw/geojson/campsites.geojson`, `route_overlay.json`, `spine.geojson` | Overnight waypoint matching, spine projection, and planner-candidate enrichment output | Cairn compiler | 2026-05-15 | Enrichment data only; supports stop selection but does not replace route overlay truth. |
| Intermediate compiler outputs | `trails/vermont_long_trail/intermediate/*` | Generated by Cairn compiler — needs review | Inherits input dataset obligations — needs review | Raw GPX/DEM/OSM and compiler stages — needs review | Intermediate geospatial compiler artifacts | Cairn compiler | UNKNOWN — needs review | Cache-like build artifacts; should be regenerated or documented before reuse. |
| DEM downloads | `data/raw/dem/*.tif`, `trails/vermont_long_trail/raw/dem/*.tif` | USGS TNM download URLs in `build_topo/scripts/download_dem.sh` | USGS/public domain status likely, but needs review | USGS elevation products | Raw DEM downloads; stored with Git LFS if committed | Cairn maintainers | UNKNOWN — needs review | Large raw source data; verify USGS license/public-domain status before redistribution. |

## Runtime Validation Status

Runtime consistency validation is available with:

```text
venv/bin/python -m cairn.runtime.data_quality trails/vermont_long_trail
```

As of 2026-05-17, the Vermont Long Trail runtime dataset has no validator
errors. Known warnings remain for:

- blank compiled approach `connected_terminus` fields
- terrain sample miles using a different domain than guidebook overlay miles
- operational graph approach transitions without explicit endpoint locations

These warnings are data-quality and reconciliation work items. They do not
resolve the provenance gaps listed above, and they do not prove that any
external dataset can be redistributed under the project code license.

## Compatibility TODO

The active codebase still reads from `trails/vermont_long_trail/`. The new
`data/` directories are placeholders for future separation, not active runtime
paths yet.

Before moving existing files:

- add compatibility shims or configuration for old and new paths
- update compiler scripts and tests
- verify Streamlit export behavior
- complete this provenance registry with source URLs, dates, and license terms
