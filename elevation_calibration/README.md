# Elevation Calibration References

This directory is for local elevation comparison inputs such as Gaia or Garmin
exports, screenshots, and manually recorded summary values.

Do not commit vendor-exported route files, proprietary map data, screenshots, or
other third-party reference material here unless provenance and reuse rights have
been reviewed and documented first.

The calibration workflow treats these files as reference measurements only.
CairnOS planner data remains derived from the project's compiled trail,
terrain, and manually curated datasets.

For repeatable checks, create a local ignored `manifest.csv` in this directory
with:

```text
name,start_mile,stop_mile,reference_gain_ft,reference_distance_miles,source_tool,notes,file
```

The `file` column is optional, but useful when a `.geojson`, `.gpx`, or `.kml`
export in this directory has the same reference route. Leave
`reference_gain_ft` blank to use a route export's summary ascent when present.

Manifest reports also include alternate gain checks when a route export has
embedded elevation points. This helps distinguish likely Cairn terrain mapping
issues from vendor summary/smoothing differences. A `warn` status means the
segment needs review; it is not a planner override.

Manifest rows with a `file` value also include `route_alignment`. This samples
the local reference route against CairnOS's compiled Long Trail spine so
side-trail detours, access-route drift, or bad vendor geometry are visible
before treating an elevation delta as a Cairn terrain problem.
