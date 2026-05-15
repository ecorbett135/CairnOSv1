# CairnOSv1

CairnOSv1 is an operational expedition planning system for long-distance trail networks. It is designed to move beyond abstract mileage partitioning and toward realistic, logistics-aware itinerary synthesis using trail-level operational semantics.

## Screenshots

The current Streamlit workflow supports planner configuration, generated
expedition summaries, resupply strategy output, operational itinerary review,
and Gaia GeoJSON export.

![CairnOSv1 Streamlit UI](docs/images/CairnOSv1-streamlit-ui.png)

![CairnOSv1 operational itinerary and Gaia export](docs/images/CairnOSv1-streamlit-generate_gaia.png)

## What it does today

- Builds a trail topology and operational graph from compiled trail data.
- Loads route overlay metadata and operational node semantics at runtime.
- Synthesizes expedition itineraries using `cairn/planner/planner_v2.py`.
- Supports THRU trip planning with separate trip type and direction controls.
- Preserves NOBO and SOBO ingress/egress semantics over northbound-reference guidebook miles.
- Prioritizes real shelter and campsite stops over synthetic labels.
- Separates resupply cadence from zero/nero recovery cadence.
- Adds resupply-aware itinerary annotations from operational logistics nodes and curated Long Trail town-access data.
- Produces a resupply strategy table with trip-start carry segment, town access, and days to next resupply segment.
- Exports PlannerV2 itineraries as Gaia-compatible GeoJSON with daily stops, planned resupply road crossings, shelter/campsite markers, and the trail spine.
- Includes a Streamlit UI scaffold in `cairn/interfaces/streamlit_app.py` for operational presentation.
- Provides tests in `cairn/tests/` for planner behavior, operational stop selection, SOBO direction semantics, Streamlit UI controls, Gaia export behavior, and Gaia reference enrichment.

## What it is working toward

CairnOSv1 is evolving toward:

- overlay-authoritative itinerary synthesis
- cadence-aware daily planning
- fatigue and recovery modeling
- realistic logistics and resupply reasoning
- operational traversal continuity across approach/egress branches
- terrain-aware expedition planning instead of pure geometry slicing
- an expedition-grade workspace for guided trail planning and review

## Project structure

- `build_topo/` — topology compiler and operational graph generation
- `cairn/runtime/` — runtime graph loading, traversal semantics, operational queries
- `cairn/planner/` — planner core and itinerary synthesis logic
- `cairn/interfaces/` — UI and interface surfaces (Streamlit)
- `data/` — forward-looking raw/derived/manual/generated data separation structure
- `docs/` — documentation assets and provenance/licensing notes
- `trails/vermont_long_trail/` — sample trail dataset and compiled outputs
- `cairn/tests/` — automated tests for planner and runtime behavior

## Streamlit UI

The Streamlit app provides a user-facing interface for requesting expedition plans and viewing the planner's response.

Typical input parameters include:

- trip type selection (THRU / SECTION)
- direction selection (NOBO / SOBO)
- ingress / egress approaches
- daily cadence or target mileage preferences
- operational constraints such as shelter/campsite preferences
- preferred resupply cadence
- preferred zero/nero recovery cadence
- optional extra resupply-only stops

The output includes:

- a synthesized daily itinerary
- descriptive stop names and operational locations
- estimated daily elevation gain for each selected leg, reported directly
  rather than capped to the elevation preference
- a resupply strategy table tied to real road crossings, trailheads, and town-access points
- days until the next resupply segment or finish
- operational feasibility warnings when the requested timeline is achievable
  only by exceeding daily mileage or elevation preferences
- Gaia GeoJSON download with a hot-pink trail spine, lime shelter/campsite markers, and red car markers for planned resupply crossings
- alternate realistic plans when the requested itinerary is infeasible
- validation feedback when a user request is invalid or cannot be satisfied as requested
- persistent generated results until the user explicitly regenerates the plan

The screenshots above show the current Streamlit workflow: planner configuration, resupply strategy output, the operational itinerary table, and the Gaia GeoJSON export action.

## Gaia export

The Gaia export layer lives in `cairn/export/gaia_geojson.py`.

It converts a PlannerV2 operational itinerary into a Gaia-importable GeoJSON feature collection:

- one Point feature for each daily stop
- one Point feature for each planned resupply crossing selected by the resupply strategy
- one LineString feature for the compiled trail spine
- marker metadata for Gaia imports:
  - shelters: `gaia-shelter`, lime green
  - campsites: `gaia-campsite`, lime green
  - resupply road crossings: `gaia-car`, red
  - trail spine: hot pink

Daily stop coordinates are resolved from compiled and enriched trail data, preferring curated reference coordinates where available and falling back to compiled route overlay or spine interpolation. Planned resupply markers are driven by `resupply_amenities.csv`, which now includes latitude and longitude for the known Long Trail resupply access points.

## Resupply and recovery semantics

PlannerV2 treats resupply cadence as a food-carry planning target and zero/nero cadence as a separate recovery planning target. Both are soft windows, not fixed intervals. Resupply notes are added only when the itinerary crosses an operationally meaningful logistics/access node, while zero and nero notes are reserved for recovery stops.

The resupply strategy table includes the trip start as the first carry segment
anchor, then lists planned resupply access points and the number of days until
the next resupply segment or the finish. Terminal-day resupply stops are
suppressed because they do not reduce a future food carry.

The current Long Trail resupply layer is sourced from:

- `trails/vermont_long_trail/raw/csv/resupply_amenities.csv`
- `trails/vermont_long_trail/compiled/route_overlay.json`

The raw CSV preserves town access, available services, zero-day suitability, source provenance, and road/trailhead coordinates. The planner still relies on route overlay semantics for operational truth; the CSV enriches access points with practical resupply metadata.

## Gaia reference enrichment

Optional Gaia-exported waypoint data can be stored at:

```text
trails/vermont_long_trail/raw/geojson/gaia_reference.geojson
```

The standalone compiler stub:

```text
build_topo/compiler/gaia_reference_overlay.py
```

parses Point features into:

```text
trails/vermont_long_trail/compiled/waypoint_reference.json
```

This enrichment layer preserves Gaia waypoint names, coordinates, icons, marker types, and marker colors. It is used by the Gaia export layer to improve shelter/campsite placement and marker metadata, but it is not operational truth and is not wired into PlannerV2 traversal behavior.

## Data handling

- Project code is licensed under Apache 2.0, but datasets may have separate
  licenses and obligations.
- Compiled outputs are stored under `trails/vermont_long_trail/compiled/` and `trails/vermont_long_trail/intermediate/`.
- Curated resupply access metadata is stored in `trails/vermont_long_trail/raw/csv/resupply_amenities.csv`.
- Optional Gaia reference waypoint data is stored in `trails/vermont_long_trail/raw/geojson/gaia_reference.geojson`.
- New data work should use the `data/` layout:
  - `data/raw/` for untouched source data
  - `data/derived/` for transformed datasets
  - `data/manual/` for manually curated Cairn datasets
  - `data/generated/` for reports, exports, cache files, and temporary outputs
- Raw DEM files are managed outside normal Git history using Git LFS to avoid repository bloat.
- `.gitattributes` already tracks `trails/vermont_long_trail/raw/dem/*.tif` with Git LFS.
- Dataset provenance is tracked in `data/DATASETS.md`; guidance lives in `docs/DATA_PROVENANCE.md`.
- Readme images and documentation assets are kept under `docs/images/` to avoid top-level directory pollution.

## Getting started

1. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

1. Run the test suite:

```bash
python -m pytest cairn/tests -q
```

1. Launch the Streamlit interface (if desired):

```bash
streamlit run cairn/interfaces/streamlit_app.py
```

## Notes for developers

- `PlannerV2` is the authoritative current planner implementation.
- The system intentionally avoids synthetic planner behavior in favor of operational realism.
- The overlay (`route_overlay.json`) is the authoritative source for canonical stop names, shelter semantics, and progression ordering.
- NOBO and SOBO use the same northbound-reference guidebook miles; direction changes traversal order, not mile semantics.
- Selected ingress and egress routes are planner state, not display-only metadata.
- Resupply behavior should stay tied to real logistics/access nodes and curated access data, not arbitrary day numbers.
- Recovery behavior should remain separate from resupply behavior even when both occur at the same access point.
- Gaia reference data is enrichment only; do not treat Gaia waypoint exports as planner traversal authority.
- Existing code still reads trail datasets from `trails/`; do not move those files without compatibility shims and tests.
- The build pipeline is responsible for generating terrain and operational graph artifacts, not the planner itself.

## License

CairnOSv1 project code is licensed under the Apache License 2.0. See `LICENSE`.

Data files are not automatically Apache licensed. Trail datasets, OSM-derived
layers, Gaia exports, DEMs, screenshots, generated reports, and manually
curated data may carry separate provenance and license obligations. See
`docs/DATA_PROVENANCE.md` and `data/DATASETS.md` before reusing datasets.

## Current repository goals

- Keep expedition planning semantics operationally realistic.
- Preserve approach/egress semantics and negative-mileage ingress paths.
- Avoid pushing large raw terrain files into normal git history.
- Build toward a production-ready expedition modeling toolchain.
