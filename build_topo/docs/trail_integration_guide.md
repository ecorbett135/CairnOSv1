# CairnOSv1 Trail Integration Guide

## Purpose

This document explains how to integrate:

- new trails
- new regions
- alternate route systems

into the CairnOSv1 topology compiler.

The Build_Topo architecture is intentionally designed to support:

- multiple trail systems
- regional operational overlays
- alternate route branches
- future expedition graph expansion

---

# Step 1 — Create Trail Directory

Create a new trail directory:

```text
trails/trail_name/
```

Required structure:

```text
trails/
└── trail_name/
    ├── raw/
    │   ├── csv/
    │   ├── dem/
    │   ├── gpx/
    │   └── shp/
    ├── compiled/
    └── intermediate/
```

## Artifact Boundaries

Trail data directories are separated by trust level.

```text
trails/<trail>/
  raw/           # source inputs, curated or externally obtained
  intermediate/  # transient compiler products
  candidate/     # generated candidate artifact sets, never trusted by default
  compiled/      # promoted artifacts used by runtime and planner
```

Use `candidate/<run_id>/` for generated output during modernization work.
Do not write directly to `compiled/` while testing new compiler contracts,
source ingestion, or validation behavior.

Candidate output should include:

- `candidate_manifest.json`
- `candidate_validation.json`
- `candidate_report.json`
- generated artifacts that mirror their promoted relative paths

Example:

```text
trails/vermont_long_trail/candidate/2026-06-03-contracts/
  candidate_manifest.json
  candidate_validation.json
  candidate_report.json
  compiled/
    route_overlay.json
    operational_graph.json
```

Validate candidate output before review:

```bash
python3 build_topo/scripts/validate_candidate.py \
    trails/vermont_long_trail/candidate/2026-06-03-contracts
```

The validation command writes reports only inside the candidate directory. It
does not write to `compiled/`, and a passing report is not automatic promotion.

Check whether the candidate is ready for manual promotion review:

```bash
python3 build_topo/scripts/check_promotion_readiness.py \
    trails/vermont_long_trail/candidate/2026-06-03-contracts
```

The readiness command reads `candidate_report.json`, prints checklist results
and an artifact diff summary, and writes nothing. It does not copy candidate
artifacts into `compiled/`.

Only copy candidate artifacts into `compiled/` after validation passes and the
diff has been reviewed. Keep existing promoted files recoverable until the new
candidate has been field-tested or otherwise accepted.

Example:

```text
trails/colorado_trail/
trails/pacific_crest_trail/
trails/appalachian_trail/
```

---

# Step 2 — Add Required Raw Data

Populate:

```text
raw/gpx/
raw/dem/
raw/shp/
raw/csv/
```

Expected core raw datasets include:

- trail spine GPX
- DEM elevation rasters
- OSM roads and POI layers
- route_master.csv
- approach_trails.csv

Required datasets:

- trail spine GPX
- DEM elevation data
- OSM roads
- route_master.csv
- approach_trails.csv

See:

```text
required_raw_data.md
```

for detailed requirements.

---

# Step 3 — Run Compiler

Execute:

```bash
python3 build_topo/scripts/build_topology.py \
    trails/trail_name
```

Example:

```bash
python3 build_topo/scripts/build_topology.py \
    trails/vermont_long_trail
```

---

# Compiler Outputs

Compiled datasets will be written to:

```text
trails/trail_name/compiled/
```

Core outputs include:

```text
spine.geojson
canonical_spine.geojson
segments.geojson
segments.json
crossings.geojson
crossings_refined.geojson
crossings_refined.json
logistics_nodes.json
route_overlay.json
approach_trails.json
operational_graph.json
cairn_schema_registry.json
```

---

# Integrating Alternate Routes

CairnOSv1 is designed to support:

- alternate branches
- bypass routes
- seasonal variants
- ingress and egress systems
- future multi-route expedition graphs

Approach trails are the first implementation of this concept.

The Vermont Long Trail currently models:

- Appalachian Trail southern ingress
- Williamstown approach variants
- Journey's End northern egress
- direction-aware ingress and egress semantics

Future route systems may include:

- alternate ridge traverses
- winter routes
- emergency egress routes
- resupply bypasses
- loop systems

These should be modeled as:

```text
operational graph branches
```

rather than disconnected metadata.

---

# Regional Expansion

The compiler is intended to support:

- single trails
- regional trail systems
- interconnected expedition networks

Future examples:

```text
Appalachian Trail
Long Trail
Benton MacKaye Trail
Colorado Trail
Pacific Crest Trail
Continental Divide Trail
```

The architecture intentionally supports:

```text
multi-trail operational graph systems
```

---

# Important Design Philosophy

CairnOSv1 does NOT treat trails as:

```text
simple GPX lines
```

Instead, trails are modeled as:

```text
operational expedition systems
```

That means the compiler intentionally separates:

- geometry
- terrain
- logistics
- operational semantics
- traversal continuity
- ingress and egress behavior
- expedition operational constraints

This distinction is foundational to the CairnOSv1 architecture.

---

# Current Operational Status

The Build_Topo compiler currently supports:

- generic multi-trail directory layouts
- terrain segmentation
- logistics extraction
- crossing refinement
- route overlay operational semantics
- approach trail operational semantics
- operational graph compilation
- validation pipeline execution

The Vermont Long Trail is currently the reference implementation and validation dataset for CairnOSv1.
