# Examine Candidate Drift Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, non-promoting build_topo command that examines candidate-vs-promoted drift and produces human-review evidence before any artifact or image promotion.

**Architecture:** Reuse `candidate_report.json` as the source of truth for candidate/promoted artifact hashes and validation state. When `container_candidate_plan.json` is present, probe its baseline/candidate smoke URLs and compare deterministic response fingerprints. Add a focused drift report builder plus CLI; default behavior prints a human-readable review report, while `--json` prints machine-readable JSON and `--save` writes `candidate_drift_report.json` inside the candidate root only.

**Tech Stack:** Python standard library, pytest, existing `build_topo.compiler` helpers, existing candidate/report/readiness conventions.

---

## File Structure

- Create `build_topo/compiler/candidate_drift.py`
  - Load and validate candidate report evidence.
  - Convert candidate report artifacts into deterministic drift entries.
  - Optionally load `container_candidate_plan.json` and compare baseline/candidate smoke endpoints when both are reachable.
  - Build summary, checklist, status, and next-step guidance.
  - Save `candidate_drift_report.json` only when requested by CLI.
- Create `build_topo/scripts/examine_candidate_drift.py`
  - CLI wrapper for human-readable and JSON output.
  - Exit `0` when drift evidence is reviewable.
  - Exit `1` when candidate evidence is missing, invalid, or blocked.
- Create `cairn/tests/test_build_topo_candidate_drift.py`
  - Unit tests for report shape, statuses, and missing/invalid evidence.
- Create `cairn/tests/test_build_topo_examine_candidate_drift_cli.py`
  - CLI tests for non-mutation, human output, JSON output, save behavior, and blocked evidence.
- Modify `build_topo/docs/compiler_overview.md`
  - Document deterministic create -> examine drift -> promote lifecycle.
- Modify `build_topo/docs/trail_integration_guide.md`
  - Add the copy-paste drift examination command after candidate validation/readiness.

## Task 1: Drift Report Builder

**Files:**
- Create: `build_topo/compiler/candidate_drift.py`
- Test: `cairn/tests/test_build_topo_candidate_drift.py`

- [ ] **Step 1: Write failing tests**

Create tests that build a fake `candidate_report.json` with changed, unchanged, new, and missing candidate artifacts.

Expected behaviors:

- `build_candidate_drift(candidate_root)` returns format `cairnos_build_topo_candidate_drift_v1`.
- Status is `review_required` when candidate evidence parses and validation passed.
- Summary counts `changed`, `unchanged`, `new`, `missing_candidate`, `deleted_or_absent_candidate`, and `review_required`.
- Drift entries expose `relative_path`, `state`, `required`, `artifact_type`, `review_required`, `candidate`, and `promoted`.
- Missing `container_candidate_plan.json` keeps artifact drift reviewable and records smoke checks as unavailable.
- Missing or malformed `candidate_report.json` returns status `blocked` and includes a failing checklist item.
- Failed candidate validation returns status `blocked`.
- Building the report does not write `candidate_drift_report.json`.

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
.venv/bin/python -m pytest -q cairn/tests/test_build_topo_candidate_drift.py
```

Expected: fail because `build_topo.compiler.candidate_drift` does not exist.

- [ ] **Step 3: Implement minimal drift builder**

Create `build_topo/compiler/candidate_drift.py` with:

- `DRIFT_REPORT_FORMAT = "cairnos_build_topo_candidate_drift_v1"`
- `build_candidate_drift(candidate_root)`
- `write_candidate_drift_report(candidate_root, report)`

Implementation rules:

- Read only `candidate_report.json`.
- Infer `trail_root` using the existing candidate-root convention.
- Treat missing/malformed report as blocked.
- Treat `validation.status != "passed"` as blocked.
- Classify artifact state using the same state names as promotion readiness.
- Mark `changed`, `new`, and `missing_candidate` entries as review required.
- Keep `unchanged` entries in the report for traceability.
- Load `container_candidate_plan.json` if present and expose smoke tests as `unavailable` until CLI-level probing is enabled.
- Do not write unless `write_candidate_drift_report()` is called.

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
.venv/bin/python -m pytest -q cairn/tests/test_build_topo_candidate_drift.py
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add build_topo/compiler/candidate_drift.py cairn/tests/test_build_topo_candidate_drift.py
git commit -m "feat: add build_topo candidate drift report"
```

## Task 2: Drift Examination CLI

**Files:**
- Create: `build_topo/scripts/examine_candidate_drift.py`
- Test: `cairn/tests/test_build_topo_examine_candidate_drift_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Create tests for:

- Human output prints `Candidate drift: review_required`, summary counts, and artifact states.
- `--json` prints parseable JSON.
- `--save` writes `candidate_drift_report.json` inside candidate root.
- Without `--save`, candidate root contents are unchanged.
- Missing report exits `1` and prints the blocked reason.
- Endpoint comparison with local fake HTTP servers reports canonical JSON matches despite key-order differences and reports status/body drift when responses differ.

- [ ] **Step 2: Run CLI tests to verify RED**

Run:

```bash
.venv/bin/python -m pytest -q cairn/tests/test_build_topo_examine_candidate_drift_cli.py
```

Expected: fail because `build_topo/scripts/examine_candidate_drift.py` does not exist.

- [ ] **Step 3: Implement CLI**

Create `build_topo/scripts/examine_candidate_drift.py` using the existing script style:

- positional `candidate_root`
- optional `--json`
- optional `--save`
- optional `--skip-smoke`
- `main()` returns `0` for non-blocked reports and `1` for blocked reports.
- Human output includes status, candidate, promoted root when present, checklist, summary, and artifacts.
- By default, probe smoke URLs from `container_candidate_plan.json` when present. `--skip-smoke` leaves smoke checks marked unavailable.

- [ ] **Step 4: Run CLI tests to verify GREEN**

Run:

```bash
.venv/bin/python -m pytest -q cairn/tests/test_build_topo_examine_candidate_drift_cli.py
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add build_topo/scripts/examine_candidate_drift.py cairn/tests/test_build_topo_examine_candidate_drift_cli.py
git commit -m "feat: add candidate drift examination CLI"
```

## Task 3: Documentation

**Files:**
- Modify: `build_topo/docs/compiler_overview.md`
- Modify: `build_topo/docs/trail_integration_guide.md`

- [ ] **Step 1: Document command**

Add this command after candidate validation/readiness:

```bash
python3 build_topo/scripts/examine_candidate_drift.py \
    trails/vermont_long_trail/candidate/<run_id> \
    --save
```

Document:

- It reads `candidate_report.json` and, when present, `container_candidate_plan.json`.
- It expects baseline/candidate containers to already be running if smoke checks are not skipped.
- It writes only `candidate_drift_report.json` when `--save` is present.
- It never copies to `compiled/`.
- Drift can be acceptable when trail data legitimately changed.
- AI-assisted investigation is a later advisory layer that consumes this deterministic report.

- [ ] **Step 2: Verify docs references**

Run:

```bash
rg -n "examine_candidate_drift|candidate_drift_report|AI-assisted" build_topo/docs
```

Expected: both docs mention the command and the AI-later boundary.

- [ ] **Step 3: Commit**

```bash
git add build_topo/docs/compiler_overview.md build_topo/docs/trail_integration_guide.md
git commit -m "docs: document candidate drift examination"
```

## Task 4: Verification And Publication

- [ ] **Step 1: Run focused candidate tests**

```bash
.venv/bin/python -m pytest -q \
  cairn/tests/test_build_topo_candidate_drift.py \
  cairn/tests/test_build_topo_examine_candidate_drift_cli.py \
  cairn/tests/test_build_topo_candidate_report.py \
  cairn/tests/test_build_topo_promotion_readiness.py \
  cairn/tests/test_build_topo_check_promotion_readiness_cli.py \
  cairn/tests/test_build_topo_create_container_candidate_cli.py \
  cairn/tests/test_build_topo_container_candidate.py \
  cairn/tests/test_build_topo_plan_container_candidate_cli.py
```

Expected: pass.

- [ ] **Step 2: Run adjacent regressions**

```bash
.venv/bin/python -m pytest -q \
  cairn/tests/test_plan_api.py \
  cairn/tests/test_gaia_reference_overlay.py \
  cairn/tests/test_overnight_reference.py
```

Expected: pass.

- [ ] **Step 3: Run whitespace check**

```bash
git diff --check
```

Expected: no output.

- [ ] **Step 4: Open and merge PR if CI passes**

Push branch, open PR against `dev`, update issue #74, wait for CI, squash merge if clean, sync local `dev`, and delete the feature branch.
