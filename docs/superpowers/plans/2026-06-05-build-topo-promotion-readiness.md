# build_topo Promotion Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe issue #74 promotion readiness command that reviews candidate report evidence and prints a promotion checklist without copying, promoting, regenerating, or downloading artifacts.

**Architecture:** Keep readiness rules in a pure compiler module and keep CLI orchestration thin. The readiness module reads `candidate_report.json`, derives artifact diff states from candidate/promoted presence and hashes, and returns structured checklist data; the CLI prints that data as human-readable text and exits nonzero only when technical readiness fails.

**Tech Stack:** Python 3, `argparse`, `json`, `pathlib`, existing `build_topo.compiler` helpers, `pytest`, subprocess-based CLI tests.

---

## Scope

Implement:

- `build_topo/compiler/promotion_readiness.py`
- `build_topo/scripts/check_promotion_readiness.py`
- tests for ready, not-ready, missing-report, CLI output, and no file mutation
- docs for the promotion readiness workflow

Do not implement:

- artifact copying into `compiled/`
- automatic promotion
- OSM/TNM download automation
- generated candidate artifact creation
- planner/runtime candidate reads

## Tasks

### Task 1: Promotion Readiness Module

**Files:**
- Create: `build_topo/compiler/promotion_readiness.py`
- Create: `cairn/tests/test_build_topo_promotion_readiness.py`

- [ ] Write tests for:
  - valid candidate report produces `status == "ready"`
  - failed validation produces `status == "not_ready"`
  - missing report produces `status == "not_ready"` with checklist guidance to run `validate_candidate.py`
  - artifact states include `changed`, `unchanged`, and `new`
- [ ] Verify tests fail because `build_topo.compiler.promotion_readiness` does not exist.
- [ ] Implement `build_promotion_readiness(candidate_root)` and pure helpers for loading reports and classifying artifact states.
- [ ] Run `.venv/bin/python -m pytest -q cairn/tests/test_build_topo_promotion_readiness.py`.
- [ ] Commit with `feat: assess build_topo promotion readiness`.

### Task 2: Promotion Readiness CLI

**Files:**
- Create: `build_topo/scripts/check_promotion_readiness.py`
- Create: `cairn/tests/test_build_topo_check_promotion_readiness_cli.py`

- [ ] Write subprocess tests for:
  - ready candidate exits 0 and prints a readable checklist
  - not-ready candidate exits 1 and prints failed checklist items
  - command leaves candidate and promoted files unchanged
- [ ] Verify tests fail because `build_topo/scripts/check_promotion_readiness.py` does not exist.
- [ ] Implement the CLI with positional `candidate_root`.
- [ ] CLI behavior:
  - call `build_promotion_readiness(candidate_root)`
  - print human-readable status, checklist, and artifact diff states
  - return exit code 0 when readiness status is `ready`, otherwise 1
  - write no files
- [ ] Run `.venv/bin/python -m pytest -q cairn/tests/test_build_topo_check_promotion_readiness_cli.py`.
- [ ] Commit with `feat: add build_topo promotion readiness cli`.

### Task 3: Documentation

**Files:**
- Modify: `build_topo/docs/compiler_overview.md`
- Modify: `build_topo/docs/trail_integration_guide.md`

- [ ] Document:
  - `python3 build_topo/scripts/check_promotion_readiness.py trails/<trail>/candidate/<run_id>`
  - command reads candidate report evidence
  - command prints a checklist and artifact diff summary
  - command does not write reports, copy files, or promote artifacts
- [ ] Run `rg -n "check_promotion_readiness|promotion readiness|candidate_report" build_topo/docs`.
- [ ] Commit with `docs: add promotion readiness workflow`.

### Task 4: Verification And PR

- [ ] Run focused tests:

```bash
.venv/bin/python -m pytest -q \
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
  cairn/tests/test_gaia_reference_overlay.py \
  cairn/tests/test_overnight_reference.py
```

- [ ] Run `git diff --check`.
- [ ] Push branch `codex/issue-74-promotion-readiness`.
- [ ] Open PR against `dev` titled `[codex] Add build_topo promotion readiness check`.
- [ ] Comment on issue #74 that the third safe slice is in review.

## Self-Review

- This plan continues #74 without writing to promoted `compiled/` artifacts.
- It consumes existing candidate report evidence and makes manual promotion safer.
- It does not add source downloads, automatic promotion, artifact regeneration, or planner/runtime candidate reads.
