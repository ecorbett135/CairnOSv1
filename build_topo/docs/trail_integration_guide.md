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

Check whether the candidate is ready for explicit promotion review:

```bash
python3 build_topo/scripts/check_promotion_readiness.py \
    trails/vermont_long_trail/candidate/2026-06-03-contracts
```

The readiness command reads `candidate_report.json`, prints checklist results
and an artifact diff summary, and writes nothing. It does not copy candidate
artifacts into `compiled/`.

Create a local side-by-side image testing candidate:

```bash
python3 build_topo/scripts/create_container_candidate.py \
    --trail-root trails/vermont_long_trail \
    --candidate-image cairnos-plan-api:candidate \
    --candidate-digest sha256:<candidate-image-digest> \
    --baseline-image cairnos-plan-api:baseline \
    --baseline-port 3010 \
    --candidate-port 3011
```

This creates a timestamped `candidate/<run_id>/` directory and writes
`container_candidate_plan.json` inside it. The plan lists baseline/candidate
ports, smoke endpoints, Docker run commands, promotion blockers, and the image
digest under review. It does not run Docker or modify `compiled/`.

After validation produces `candidate_report.json`, examine deterministic drift:

```bash
python3 build_topo/scripts/examine_candidate_drift.py \
    trails/vermont_long_trail/candidate/<run_id> \
    --save
```

The drift command prints candidate-vs-promoted artifact states and, when
`container_candidate_plan.json` is present, compares the baseline/candidate
smoke endpoints recorded by the plan. Start the baseline and candidate
containers from the plan's Docker commands before running smoke comparison, or
pass `--skip-smoke` for artifact-only review. The command writes only
`candidate_drift_report.json` inside the candidate directory when `--save` is
present.

Promote the accepted candidate after validation passes and the deterministic
drift has been reviewed:

```bash
python3 build_topo/scripts/promote_candidate.py \
    trails/vermont_long_trail/candidate/<run_id> \
    --accept-drift
```

The promotion command snapshots the current `compiled/` tree under
`promotion_snapshots/<promotion_id>/`, copies only candidate-present artifacts
into `compiled/`, and writes `candidate_promotion_report.json` inside the
candidate directory. It never deletes promoted files in this slice; artifacts
that are missing from the candidate are left unchanged. Use `--dry-run` before
promotion when you want to inspect the copy plan without writing files.

AI-assisted web investigation can be layered in later as reviewer support, but
it should consume deterministic drift evidence rather than replace it.

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

Promoted compiled datasets live under:

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
