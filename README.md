# CairnOSv1

CairnOSv1 is an operational expedition planning system for long-distance trail networks. It is designed to move beyond abstract mileage partitioning and toward realistic, logistics-aware itinerary synthesis using trail-level operational semantics.

## What it does today

- Builds a trail topology and operational graph from compiled trail data.
- Loads route overlay metadata and operational node semantics at runtime.
- Synthesizes expedition itineraries using `cairn/planner/planner_v2.py`.
- Supports approach/egress handling and ingress-aware itinerary initialization.
- Prioritizes real shelter and campsite stops over synthetic labels.
- Includes a Streamlit UI scaffold in `cairn/interfaces/streamlit_app.py` for operational presentation.
- Provides tests in `cairn/tests/` for planner behavior, operational stop selection, and route semantics.

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
- `trails/vermont_long_trail/` — sample trail dataset and compiled outputs
- `cairn/tests/` — automated tests for planner and runtime behavior

## Data handling

- Compiled outputs are stored under `trails/vermont_long_trail/compiled/` and `trails/vermont_long_trail/intermediate/`.
- Raw DEM files are managed outside normal Git history using Git LFS to avoid repository bloat.
- `.gitattributes` already tracks `trails/vermont_long_trail/raw/dem/*.tif` with Git LFS.

## Getting started

1. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

2. Run the test suite:

```bash
python -m pytest cairn/tests -q
```

3. Launch the Streamlit interface (if desired):

```bash
streamlit run cairn/interfaces/streamlit_app.py
```

## Notes for developers

- `PlannerV2` is the authoritative current planner implementation.
- The system intentionally avoids synthetic planner behavior in favor of operational realism.
- The overlay (`route_overlay.json`) is the authoritative source for canonical stop names, shelter semantics, and progression ordering.
- The build pipeline is responsible for generating terrain and operational graph artifacts, not the planner itself.

## Current repository goals

- Keep expedition planning semantics operationally realistic.
- Preserve approach/egress semantics and negative-mileage ingress paths.
- Avoid pushing large raw terrain files into normal git history.
- Build toward a production-ready expedition modeling toolchain.
