# CairnOSv1 Build_Topo Compiler Overview

## Introduction

The Build_Topo compiler is a critical component of the CairnOSv1 system, responsible for transforming high-level topology descriptions into optimized, operational graph representations. This process enables efficient route planning, terrain analysis, and logistics management within the CairnOSv1 environment.

## Architecture

The compiler architecture is modular and layered, designed to separate concerns between topology construction and operational semantics. It consists of several stages, each focusing on a specific aspect of the compilation pipeline:

1. **Spine Import**  
   This initial stage imports the primary spine topology, which serves as the backbone for subsequent terrain and logistics processing.

2. **Terrain Segmentation**  
   Terrain data is segmented into manageable regions, facilitating localized analysis and route planning.

3. **Logistics Nodes**  
   Key logistics nodes such as supply points, depots, and transfer stations are identified and integrated into the topology.

4. **Crossing Refinement**  
   Intersections and crossings are refined to ensure accurate connectivity and traversal properties.

5. **Route Overlay**  
   Routes are overlaid on the refined topology, enabling pathfinding and navigation.

6. **Overnight Reference Overlay (optional)**
   Shelter and campsite GeoJSON reference exports may be parsed into
   `overnight_reference.json`. This layer preserves matched and unmatched
   overnight waypoint records and exposes near-spine unmatched sites as
   planner stop candidates after reconciliation against `route_overlay.json`.

7. **Approach Trails**
   Approach trails leading into significant nodes or regions are constructed to support ingress and egress operations.

8. **Gaia Reference Overlay (optional)**
   Gaia-exported waypoint data may be parsed into `waypoint_reference.json`
   for future enrichment of shelter, campsite, lodge, trailhead, and marker
   metadata. This layer is explicitly reference data, not operational truth,
   and is not currently wired into PlannerV2.

9. **Operational Graph**
   The operational graph is generated, representing the executable routing and logistics network derived from the topology.

10. **Schema Registry**
   Throughout the compilation, a schema registry maintains structural definitions and constraints to ensure consistency.

11. **Validation**
   Final validation checks are performed to verify the integrity and correctness of the compiled graph.

## Core Architectural Principle

A fundamental architectural principle of Build_Topo is the strict separation between topology and operational semantics. Topology defines the static structural relationships—how nodes and edges connect—while operational semantics define dynamic behaviors such as routing rules, traversal costs, and logistics operations.

This separation allows for flexible adaptation of operational strategies without altering the underlying topology, enabling CairnOSv1 to support diverse scenarios and optimization goals.

## Stage Contracts And Candidate Artifacts

The compiler stage order is declared in `build_topo/scripts/build_topology.py`
and mirrored by immutable contracts in `build_topo/compiler/contracts.py`.
Those contracts describe each stage name, module, required inputs, generated
outputs, validation rules, determinism, and whether network access is allowed.

For issue #74's first modernization slice, every stage is deterministic and
network access is disabled. External source acquisition through OSM,
TNM/TNMAccess, or topoBuilder belongs to later ingestion work.

Generated candidate files live under:

```text
trails/<trail>/candidate/<run_id>/
```

Candidate directories mirror promoted artifact paths such as
`compiled/route_overlay.json`, but they are not trusted by runtime or planner
code. Runtime and planner code continue to read only promoted files under:

```text
trails/<trail>/compiled/
```

Promotion is explicit. A candidate set must have a manifest, validation
report, drift report, and human review before any promoted file is replaced.

Validate a candidate set with:

```bash
python3 build_topo/scripts/validate_candidate.py \
    trails/<trail>/candidate/<run_id>
```

The command writes `candidate_validation.json` and `candidate_report.json`
inside the candidate directory. The report summarizes required artifact
presence, parse validity, candidate hashes, promoted hashes, and changed
artifacts. It does not write to `compiled/`; passing validation is review
evidence, not promotion.

Check promotion readiness with:

```bash
python3 build_topo/scripts/check_promotion_readiness.py \
    trails/<trail>/candidate/<run_id>
```

The readiness command reads `candidate_report.json`, prints a checklist, and
summarizes candidate-vs-promoted artifact states. It does not write reports,
copy files, or promote artifacts. A ready result means the candidate is ready
for explicit promotion review, not that promotion has happened.

Create a deterministic container candidate run with:

```bash
python3 build_topo/scripts/create_container_candidate.py \
    --trail-root trails/<trail> \
    --candidate-image cairnos-plan-api:candidate \
    --candidate-digest sha256:<candidate-image-digest> \
    --baseline-image cairnos-plan-api:baseline \
    --baseline-port 3010 \
    --candidate-port 3011
```

The create command creates `candidate/<run_id>/` and writes
`container_candidate_plan.json` inside that run directory. It is intentionally
non-mutating: it does not run Docker, download source data, compare drift,
copy artifacts, promote images, or change `compiled/`.

The deterministic candidate lifecycle is:

1. **Create candidate** - create a candidate run directory and save container
   planning evidence.
2. **Examine deterministic drift** - compare candidate artifacts and endpoint
   smoke output against the accepted baseline, then print review evidence.
3. **Promote accepted candidate** - after human review, use an explicit
   promotion command to snapshot current promoted artifacts and copy the
   approved candidate-present artifact set into `compiled/`.

Examine deterministic drift with:

```bash
python3 build_topo/scripts/examine_candidate_drift.py \
    trails/<trail>/candidate/<run_id> \
    --save
```

The drift command reads `candidate_report.json` and, when present,
`container_candidate_plan.json`. It compares candidate/promoted artifact
hashes and probes baseline/candidate smoke URLs only if those containers are
already running. Use `--skip-smoke` for artifact-only review. The command
writes `candidate_drift_report.json` only when `--save` is present, and that
file is written inside the candidate directory only. It never runs Docker,
downloads source data, copies files into `compiled/`, or promotes images.

Promote an accepted candidate artifact set with:

```bash
python3 build_topo/scripts/promote_candidate.py \
    trails/<trail>/candidate/<run_id> \
    --accept-drift
```

The promotion command requires `candidate_report.json`,
`candidate_drift_report.json`, and ready promotion checks. When drift status is
`review_required`, `--accept-drift` confirms that the deterministic drift has
been reviewed. The command snapshots current promoted artifacts under
`trails/<trail>/promotion_snapshots/<promotion_id>/`, copies only
candidate-present artifacts into `compiled/`, writes
`candidate_promotion_report.json` inside the candidate directory, and never
deletes promoted files in this slice. Use `--dry-run` to inspect the promotion
plan without writing or copying.

AI-assisted drift investigation is a later advisory layer. It can consume the
deterministic drift report, search for recent route or facility changes, and
summarize cited evidence for a reviewer. It should not replace deterministic
checks or perform promotion directly.

For an already-created candidate root, the lower-level planning command remains
available:

```bash
python3 build_topo/scripts/plan_container_candidate.py \
    trails/<trail>/candidate/<run_id> \
    --candidate-image cairnos-plan-api:candidate \
    --candidate-digest sha256:<candidate-image-digest> \
    --baseline-image cairnos-plan-api:baseline \
    --baseline-port 3010 \
    --candidate-port 3011 \
    --save
```

The promotion target is the immutable image digest, not the running container.
Running containers are disposable test executions; approved image digests and
approved candidate artifact sets are promoted separately. Artifact promotion is
handled by `promote_candidate.py`; image promotion remains a separate release
decision.

## Conclusion

The Build_Topo compiler transforms complex topology data into actionable operational graphs through a well-defined, staged pipeline. Its modular design and clear separation of concerns contribute to the robustness and adaptability of the CairnOSv1 system.

This architectural distinction is foundational to CairnOSv1.
