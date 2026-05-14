# CairnOSv1 Required Raw Data

## Purpose

The Build_Topo compiler requires multiple classes of raw operational and geospatial data.

The compiler intentionally separates:

- geometric topology
- terrain analysis
- logistics semantics
- operational trail semantics

Each data source contributes a different ontology layer.

---

# Required Directory Structure

Each trail system should follow this structure:

```text
trails/
└── trail_name/
    ├── raw/
    │   ├── csv/
    │   ├── dem/
    │   ├── geojson/
    │   ├── gpx/
    │   └── shp/
    ├── compiled/
    └── intermediate/
```

---

# Required Raw Data

## 1. GPX Trail Spine

Directory:

```text
raw/gpx/
```

Required:

- canonical trail spine GPX

Example:

```text
long-trail-spine.gpx
```

Requirements:

- continuous trail geometry
- correct trail ordering
- valid coordinates
- minimal geometry corruption

Purpose:

Provides the canonical geometric trail backbone.

---

## 2. DEM Elevation Data

Directory:

```text
raw/dem/
```

Required:

- raster elevation data

Examples:

- USGS DEM tiles
- GeoTIFF elevation rasters

Requirements:

- complete terrain coverage
- overlapping trail geometry
- consistent projection

Purpose:

Used for:

- elevation gain analysis
- terrain segmentation
- operational traversal cost modeling

---

## 3. OSM Road and POI Layers

Directory:

```text
raw/shp/
```

Required:

- road shapefiles
- POI shapefiles

Examples:

```text
gis_osm_roads_free_1.shp
gis_osm_pois_free_1.shp
```

Purpose:

Used for:

- road crossing detection
- logistics access
- operational crossing semantics
- town access modeling

---

## 4. route_master.csv

Directory:

```text
raw/csv/
```

Purpose:

Provides curated operational trail semantics.

This is NOT considered legacy data.

This is one of the highest-value ontology layers in CairnOSv1.

Expected semantics include:

- cumulative mileage
- shelter ordering
- operational progression
- resupply semantics
- crossing semantics
- operational trail continuity

Example fields:

```text
location
miles_from_MA_border_nb
division
```

The compiler uses this dataset to build:

```text
route_overlay.json
```

---

## 5. approach_trails.csv

Directory:

```text
raw/csv/
```

Purpose:

Defines operational ingress and egress branches.

Approach trails are treated as:

```text
operational graph branches
```

rather than metadata.

This allows:

- realistic expedition starts
- realistic expedition finishes
- shuttle planning
- branch traversal modeling
- direction-aware expedition behavior

Expected fields include:

```text
route
direction
connected_terminus
trail_miles
start_location
end_location
```

## 6. resupply_amenities.csv

Directory:

```text
raw/csv/
```

Purpose:

Provides curated town-access and service metadata that can be attached to
real route overlay nodes.

Expected semantics include:

- trail mile of access point
- nearby town access
- optional latitude / longitude for a known road or trailhead access point
- grocery / post office / outfitter / lodging / restaurant availability
- zero-day suitability
- source provenance

This layer allows the planner to treat resupply cadence as a soft target
around real operational access points instead of fixed day intervals.
When latitude and longitude are present, export layers may use them as
curated access-point coordinates for Gaia markers. Missing coordinates do
not make a resupply row invalid; they simply require downstream exporters to
fall back to compiled crossing geometry or trail-spine interpolation.
The Gaia export uses the resupply rows selected by the planner strategy to
emit red `gaia-car` road-access markers at the listed coordinates.

---

## 7. gaia_reference.geojson

Directory:

```text
raw/geojson/
```

Purpose:

Provides optional Gaia-exported waypoint and track reference data.

This source is enrichment data, NOT operational truth. It may contain useful
waypoint coordinates, Gaia marker metadata, shelter/campsite icons, and
approach reference tracks, but it must be reconciled against
`route_overlay.json` before it can influence any compiled operational layer.

The standalone Gaia reference compiler produces:

```text
compiled/waypoint_reference.json
```

Expected semantics include:

- point waypoint title / name
- coordinates
- Gaia icon and marker fields
- likely waypoint class
- fuzzy match status against route overlay canonical names
- matched and unmatched waypoint records
- summary counts for shelters, campsites, and approach references

---

# Optional Raw Layers

Optional future layers may include:

- water sources
- weather exposure
- avalanche zones
- snowpack models
- wildfire layers
- campsite restrictions
- permit systems
- seasonal closures
- transportation networks

The compiler architecture is intentionally extensible.

---

# Important Architectural Principle

CairnOSv1 intentionally separates:

```text
geometry
terrain
logistics
operational semantics
```

because real expedition behavior cannot be derived from geometry alone.

Operational truth must be explicitly modeled.
