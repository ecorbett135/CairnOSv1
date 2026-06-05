# build_topo Candidate Report CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe issue #74 candidate validation/report command that produces review evidence without regenerating or promoting compiled trail artifacts.

**Architecture:** Keep validation logic in compiler modules and keep CLI orchestration thin. The report module reads candidate artifacts under `candidate/<run_id>/`, compares them to promoted files under the trail root, writes reports only inside the candidate directory, and never writes to `compiled/`.

**Tech Stack:** Python 3, `argparse`, `json`, `pathlib`, existing `build_topo.compiler` helpers, `pytest`, subprocess-based CLI tests.

---

## Scope

Implement:

- `build_topo/compiler/candidate_report.py`
- `build_topo/scripts/validate_candidate.py`
- tests for report shape, diff summaries, CLI success, CLI failure, and no promoted writes
- docs for the candidate validation workflow

Do not implement:

- compiler output redirection into candidates
- automatic candidate promotion
- OSM/TNM download automation
- route geometry semantic diffing
- changes to planner/runtime reads

## Tasks

### Task 1: Candidate Report Module

**Files:**
- Create: `build_topo/compiler/candidate_report.py`
- Create: `cairn/tests/test_build_topo_candidate_report.py`

- [ ] Write tests that build a temp trail root with `compiled/` and `candidate/<run_id>/` artifacts, then assert `build_candidate_report()` returns:
  - validation status
  - candidate root
  - promoted root
  - artifact entries with candidate/promoted presence, byte counts, hashes, and changed status
  - summary counts for checked, changed, missing required, invalid, candidate present, and promoted present
  - no `candidate_report.json` written until `write_candidate_report()` is called
- [ ] Verify tests fail because `build_topo.compiler.candidate_report` does not exist.
- [ ] Implement `build_candidate_report(candidate_root, trail_root, artifacts=None)` and `write_candidate_report(candidate_root, report)`.
- [ ] Run `python3 -m pytest -q cairn/tests/test_build_topo_candidate_report.py`.
- [ ] Commit with `feat: summarize build_topo candidate artifacts`.

### Task 2: Candidate Validation CLI

**Files:**
- Create: `build_topo/scripts/validate_candidate.py`
- Create: `cairn/tests/test_build_topo_validate_candidate_cli.py`

- [ ] Write subprocess tests for:
  - a valid candidate exits 0, prints JSON, writes `candidate_validation.json`, writes `candidate_report.json`, and leaves `compiled/` files unchanged
  - an invalid candidate exits 1, prints failed JSON, and still writes validation/report evidence inside the candidate directory
- [ ] Verify tests fail because `build_topo/scripts/validate_candidate.py` does not exist.
- [ ] Implement the CLI with positional `candidate_root` and optional `--trail-root`.
- [ ] CLI behavior:
  - infer `trail_root` from `.../candidate/<run_id>` when `--trail-root` is omitted
  - call `build_candidate_report()`
  - write `candidate_validation.json`
  - write `candidate_report.json`
  - print report JSON to stdout
  - return exit code 0 when validation status is `passed`, otherwise 1
- [ ] Run `python3 -m pytest -q cairn/tests/test_build_topo_validate_candidate_cli.py`.
- [ ] Commit with `feat: add build_topo candidate validation cli`.

### Task 3: Documentation

**Files:**
- Modify: `build_topo/docs/compiler_overview.md`
- Modify: `build_topo/docs/trail_integration_guide.md`

- [ ] Document:
  - `python3 build_topo/scripts/validate_candidate.py trails/<trail>/candidate/<run_id>`
  - reports are written only to the candidate directory
  - promoted `compiled/` files remain untouched
  - passing validation is evidence for review, not automatic promotion
- [ ] Run `rg -n "validate_candidate|candidate_report|candidate_validation" build_topo/docs`.
- [ ] Commit with `docs: add candidate validation workflow`.

### Task 4: Verification And PR

- [ ] Run focused tests:

```bash
python3 -m pytest -q \
  cairn/tests/test_build_topo_candidate_report.py \
  cairn/tests/test_build_topo_validate_candidate_cli.py \
  cairn/tests/test_build_topo_candidate_validation.py \
  cairn/tests/test_build_topo_candidates.py \
  cairn/tests/test_build_topo_contracts.py
```

- [ ] Run adjacent regression tests:

```bash
python3 -m pytest -q \
  cairn/tests/test_gaia_reference_overlay.py \
  cairn/tests/test_overnight_reference.py
```

- [ ] Run `git diff --check`.
- [ ] Push branch `codex/issue-74-candidate-report-cli`.
- [ ] Open PR against `dev` titled `[codex] Add build_topo candidate report CLI`.
- [ ] Comment on issue #74 that the second safe slice is in review.

## Self-Review

- This plan continues #74 without writing to promoted `compiled/` artifacts.
- It creates review evidence before any future generated candidate promotion work.
- It does not add source downloads, automatic promotion, or planner/runtime candidate reads.
