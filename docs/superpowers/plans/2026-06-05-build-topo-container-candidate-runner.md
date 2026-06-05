# build_topo Container Candidate Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a non-mutating container candidate plan command that lets CairnOS compare multiple candidate images before promoting a selected image digest and artifact set.

**Architecture:** Keep image/runtime planning in a pure compiler module and keep CLI orchestration thin. The module produces a deterministic JSON plan with candidate image identity, baseline image identity, local port assignments, smoke-test endpoints, artifact output directory, and promotion blockers; the CLI prints that plan and writes nothing unless explicitly asked to save under the candidate directory.

**Tech Stack:** Python 3, `argparse`, `json`, `pathlib`, existing `build_topo.compiler` helpers, `pytest`, subprocess-based CLI tests.

---

## Scope

Implement:

- `build_topo/compiler/container_candidate.py`
- `build_topo/scripts/plan_container_candidate.py`
- tests for image identity, side-by-side baseline/candidate ports, smoke endpoints, readiness blockers, optional candidate-local save, and no promoted mutation
- docs for image promotion versus container execution

Do not implement:

- Docker build/run execution
- automatic image promotion
- automatic artifact promotion
- OSM/TNM download automation
- planner/runtime candidate reads

## Tasks

### Task 1: Container Candidate Plan Module

**Files:**
- Create: `build_topo/compiler/container_candidate.py`
- Create: `cairn/tests/test_build_topo_container_candidate.py`

- [ ] Write tests for:
  - a ready candidate builds a plan with image tag/digest, baseline tag/digest, candidate and baseline ports, smoke endpoints, and candidate artifact directory
  - missing candidate readiness creates blockers and status `blocked`
  - save writes `container_candidate_plan.json` only inside the candidate directory
- [ ] Verify tests fail because `build_topo.compiler.container_candidate` does not exist.
- [ ] Implement `build_container_candidate_plan()` and `write_container_candidate_plan()`.
- [ ] Run `.venv/bin/python -m pytest -q cairn/tests/test_build_topo_container_candidate.py`.
- [ ] Commit with `feat: plan build_topo container candidates`.

### Task 2: Container Candidate Plan CLI

**Files:**
- Create: `build_topo/scripts/plan_container_candidate.py`
- Create: `cairn/tests/test_build_topo_plan_container_candidate_cli.py`

- [ ] Write subprocess tests for:
  - CLI prints JSON and exits 0 for a ready candidate
  - CLI exits 1 when readiness blocks container candidate promotion
  - `--save` writes only `candidate/<run_id>/container_candidate_plan.json`
- [ ] Verify tests fail because `build_topo/scripts/plan_container_candidate.py` does not exist.
- [ ] Implement the CLI with image identity, ports, smoke endpoint, and optional `--save`.
- [ ] Run `.venv/bin/python -m pytest -q cairn/tests/test_build_topo_plan_container_candidate_cli.py`.
- [ ] Commit with `feat: add container candidate plan cli`.

### Task 3: Documentation

**Files:**
- Modify: `build_topo/docs/compiler_overview.md`
- Modify: `build_topo/docs/trail_integration_guide.md`

- [ ] Document:
  - promote image digest, not running container
  - local side-by-side baseline/candidate containers use separate ports
  - container candidate planning is non-mutating
  - candidate image promotion remains manual and separate from artifact promotion
- [ ] Run `rg -n "container candidate|image digest|plan_container_candidate" build_topo/docs`.
- [ ] Commit with `docs: add container candidate workflow`.

### Task 4: Verification And PR

- [ ] Run focused tests:

```bash
.venv/bin/python -m pytest -q \
  cairn/tests/test_build_topo_container_candidate.py \
  cairn/tests/test_build_topo_plan_container_candidate_cli.py \
  cairn/tests/test_build_topo_promotion_readiness.py \
  cairn/tests/test_build_topo_check_promotion_readiness_cli.py \
  cairn/tests/test_build_topo_candidate_report.py \
  cairn/tests/test_build_topo_validate_candidate_cli.py \
  cairn/tests/test_build_topo_candidate_validation.py \
  cairn/tests/test_build_topo_candidates.py \
  cairn/tests/test_build_topo_contracts.py
```

- [ ] Run adjacent regression tests:

```bash
.venv/bin/python -m pytest -q \
  cairn/tests/test_plan_api.py \
  cairn/tests/test_gaia_reference_overlay.py \
  cairn/tests/test_overnight_reference.py
```

- [ ] Run `git diff --check`.
- [ ] Push branch `codex/issue-74-container-candidate-runner`.
- [ ] Open PR against `dev` titled `[codex] Add build_topo container candidate plan`.
- [ ] Comment on issue #74 that the container candidate safe slice is in review.

## Self-Review

- This plan supports comparing candidate images without running Docker or mutating promoted data.
- It treats images/digests as promotion targets and containers as disposable test executions.
- It does not add source downloads, automatic image promotion, automatic artifact promotion, or runtime candidate reads.
