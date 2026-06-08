# Create Container Candidate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first deterministic candidate lifecycle command that creates a candidate run directory and saves container candidate planning evidence without mutating promoted artifacts.

**Architecture:** Keep run-id and candidate-root creation in a thin CLI around the existing `build_topo.compiler.container_candidate` module. The command creates `trails/<trail>/candidate/<run_id>/`, saves `container_candidate_plan.json`, prints the plan JSON, and leaves drift review, AI investigation, and promotion for separate later commands.

**Tech Stack:** Python 3, `argparse`, `json`, `pathlib`, existing `build_topo.compiler.container_candidate` helpers, `pytest`, subprocess-based CLI tests.

---

## Scope

Implement:

- `build_topo/scripts/create_container_candidate.py`
- tests for run-id creation, candidate-local plan writes, existing-run protection, and no promoted artifact mutation
- docs for the deterministic phase-1 lifecycle:
  - create candidate
  - examine deterministic drift
  - promote accepted candidate
  - later AI drift investigation as a separate layer

Do not implement:

- drift examination
- AI web investigation
- candidate promotion
- Docker build/run execution
- source downloads
- writes into `compiled/`

## Tasks

### Task 1: Create Candidate CLI

**Files:**
- Create: `build_topo/scripts/create_container_candidate.py`
- Create: `cairn/tests/test_build_topo_create_container_candidate_cli.py`

- [ ] Write subprocess tests for:
  - command creates `candidate/<run_id>/`
  - command writes `container_candidate_plan.json` inside that candidate directory
  - command prints JSON with `run_id`, candidate root, image digest, and blocked readiness when candidate artifacts are not present yet
  - command exits nonzero instead of overwriting an existing run directory
  - command does not mutate `compiled/`
- [ ] Verify tests fail because `create_container_candidate.py` does not exist.
- [ ] Implement the CLI with optional `--run-id`, default UTC timestamp run IDs, `--trail-root`, image identity args, port args, and smoke path args.
- [ ] Run `.venv/bin/python -m pytest -q cairn/tests/test_build_topo_create_container_candidate_cli.py`.
- [ ] Commit with `feat: create build_topo container candidates`.

### Task 2: Documentation

**Files:**
- Modify: `build_topo/docs/compiler_overview.md`
- Modify: `build_topo/docs/trail_integration_guide.md`

- [ ] Document deterministic phase 1:
  - `create_container_candidate.py`
  - future `examine_candidate_drift.py`
  - future `promote_candidate.py`
  - AI-assisted drift investigation as a later advisory layer
- [ ] Run `rg -n "create_container_candidate|examine_candidate_drift|promote_candidate|AI-assisted" build_topo/docs`.
- [ ] Commit with `docs: document deterministic candidate lifecycle`.

### Task 3: Verification And PR

- [ ] Run focused tests:

```bash
.venv/bin/python -m pytest -q \
  cairn/tests/test_build_topo_create_container_candidate_cli.py \
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
- [ ] Push branch `codex/issue-74-create-container-candidate`.
- [ ] Open PR against `dev` titled `[codex] Add build_topo create container candidate command`.
- [ ] Comment on issue #74 that the deterministic create-candidate slice is in review.

## Self-Review

- This plan keeps AI investigation out of phase 1 and leaves it as a later advisory layer.
- It creates candidate run directories and planning evidence only.
- It does not add source downloads, Docker execution, drift review, or promotion.
