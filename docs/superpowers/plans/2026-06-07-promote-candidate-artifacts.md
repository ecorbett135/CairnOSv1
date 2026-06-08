# Promote Candidate Artifacts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit, deterministic `build_topo` promotion command that snapshots promoted artifacts, verifies candidate evidence, and copies approved candidate artifacts into `compiled/`.

**Architecture:** Promotion remains separate from generation, validation, readiness, and drift examination. The command reads existing evidence (`candidate_report.json`, `candidate_drift_report.json`, and readiness), requires explicit drift acceptance when deterministic drift is present, snapshots current promoted artifacts, copies only candidate-present artifacts, and never deletes promoted artifacts in this slice.

**Tech Stack:** Python standard library, pytest, existing `build_topo.compiler` modules, existing script conventions under `build_topo/scripts`.

---

## File Structure

- Create `build_topo/compiler/candidate_promotion.py`
  - Owns deterministic promotion planning, evidence checks, snapshot/copy behavior, dry-run behavior, and promotion report serialization.
- Create `build_topo/scripts/promote_candidate.py`
  - CLI wrapper for the promotion module with human and JSON output.
- Create `cairn/tests/test_build_topo_candidate_promotion.py`
  - Unit coverage for promotion contract and filesystem mutation boundaries.
- Create `cairn/tests/test_build_topo_promote_candidate_cli.py`
  - CLI coverage for exit codes, human output, JSON output, and mutation behavior.
- Modify `build_topo/docs/compiler_overview.md`
  - Document the explicit promotion command and safety boundaries.
- Modify `build_topo/docs/trail_integration_guide.md`
  - Add the candidate lifecycle command sequence.
- Modify `docs/design/issue-74-build-topo-modernization.md`
  - Update the promotion model from future work to first explicit promotion slice.

## Tasks

### Task 1: Candidate Promotion Core

**Files:**
- Create: `build_topo/compiler/candidate_promotion.py`
- Test: `cairn/tests/test_build_topo_candidate_promotion.py`

- [x] **Step 1: Write failing tests**

Add tests that create temporary `trails/vermont_long_trail/candidate/run-1` and `compiled/` trees, then assert:

```python
def test_promote_candidate_blocks_when_drift_requires_acceptance(tmp_path):
    report = promote_candidate_artifacts(candidate_root, promotion_id="promo-1")
    assert report["status"] == "blocked"
    assert "use --accept-drift" in report["blockers"][0]
    assert compiled_file.read_text(encoding="utf-8") == "promoted"

def test_promote_candidate_snapshots_and_copies_candidate_present_artifacts(tmp_path):
    report = promote_candidate_artifacts(
        candidate_root,
        promotion_id="promo-1",
        accept_drift=True,
    )
    assert report["status"] == "promoted"
    assert snapshot_file.read_text(encoding="utf-8") == "promoted"
    assert compiled_file.read_text(encoding="utf-8") == "candidate"
    assert missing_candidate_promoted_file.read_text(encoding="utf-8") == "keep"

def test_promote_candidate_dry_run_does_not_mutate_files(tmp_path):
    report = promote_candidate_artifacts(
        candidate_root,
        promotion_id="promo-1",
        accept_drift=True,
        dry_run=True,
    )
    assert report["status"] == "ready"
    assert not snapshot_root.exists()
    assert compiled_file.read_text(encoding="utf-8") == "promoted"
```

- [x] **Step 2: Run tests to verify RED**

Run:

```bash
.venv/bin/python -m pytest -q cairn/tests/test_build_topo_candidate_promotion.py
```

Expected: fail because `build_topo.compiler.candidate_promotion` does not exist.

Result: failed with `ModuleNotFoundError: No module named 'build_topo.compiler.candidate_promotion'`.

- [x] **Step 3: Implement core module**

Implement `promote_candidate_artifacts(candidate_root, *, promotion_id=None, accept_drift=False, dry_run=False)` with:

- `PROMOTION_FORMAT = "cairnos_build_topo_candidate_promotion_v1"`
- candidate root guard using `is_candidate_run_root()`
- readiness check using `build_promotion_readiness()`
- JSON object loading for `candidate_report.json` and `candidate_drift_report.json`
- blocked status when readiness is not ready
- blocked status when drift report is missing, malformed, or `blocked`
- blocked status when drift status is `review_required` and `accept_drift` is false
- preflight verification that every candidate-present source file exists
- snapshot root `trails/<trail>/promotion_snapshots/<promotion_id>/`
- copy only candidate-present artifacts from candidate to promoted path
- preserve promoted files listed in the candidate report before overwriting
- skip missing-candidate artifacts and never delete promoted files
- write `candidate_promotion_report.json` only for non-dry-run promotion

- [x] **Step 4: Run tests to verify GREEN**

Run:

```bash
.venv/bin/python -m pytest -q cairn/tests/test_build_topo_candidate_promotion.py
```

Expected: all tests pass.

Result: `6 passed in 0.05s`.

### Task 2: Promotion CLI

**Files:**
- Create: `build_topo/scripts/promote_candidate.py`
- Test: `cairn/tests/test_build_topo_promote_candidate_cli.py`

- [x] **Step 1: Write failing CLI tests**

Add tests that call the script with `subprocess.run()` and assert:

```python
def test_promote_candidate_cli_blocks_without_accept_drift(tmp_path):
    result = subprocess.run([...], check=False)
    assert result.returncode == 1
    assert "Candidate promotion: blocked" in result.stdout
    assert "use --accept-drift" in result.stdout

def test_promote_candidate_cli_promotes_with_accept_drift(tmp_path):
    result = subprocess.run([... , "--accept-drift"], check=False)
    assert result.returncode == 0
    assert "Candidate promotion: promoted" in result.stdout
    assert "copied: 2" in result.stdout

def test_promote_candidate_cli_json_dry_run(tmp_path):
    result = subprocess.run([... , "--accept-drift", "--dry-run", "--json"], check=False)
    payload = json.loads(result.stdout)
    assert payload["status"] == "ready"
```

- [x] **Step 2: Run tests to verify RED**

Run:

```bash
.venv/bin/python -m pytest -q cairn/tests/test_build_topo_promote_candidate_cli.py
```

Expected: fail because `build_topo/scripts/promote_candidate.py` does not exist.

Result: failed because `build_topo/scripts/promote_candidate.py` did not exist.

- [x] **Step 3: Implement CLI**

CLI behavior:

```bash
python3 build_topo/scripts/promote_candidate.py \
    trails/<trail>/candidate/<run_id> \
    --accept-drift
```

Options:

- `--accept-drift`: required for `review_required` drift
- `--promotion-id`: deterministic snapshot/report id, useful in tests
- `--dry-run`: print what would happen without writing or copying
- `--json`: print machine-readable JSON

Exit codes:

- `0` when status is `promoted` or dry-run `ready`
- `1` when status is `blocked`
- `2` for unsafe path errors

- [x] **Step 4: Run CLI tests to verify GREEN**

Run:

```bash
.venv/bin/python -m pytest -q cairn/tests/test_build_topo_promote_candidate_cli.py
```

Expected: all tests pass.

Result: `3 passed in 0.14s`.

### Task 3: Documentation

**Files:**
- Modify: `build_topo/docs/compiler_overview.md`
- Modify: `build_topo/docs/trail_integration_guide.md`
- Modify: `docs/design/issue-74-build-topo-modernization.md`

- [x] **Step 1: Update lifecycle docs**

Document the sequence:

```bash
python3 build_topo/scripts/validate_candidate.py trails/<trail>/candidate/<run_id>
python3 build_topo/scripts/check_promotion_readiness.py trails/<trail>/candidate/<run_id>
python3 build_topo/scripts/examine_candidate_drift.py trails/<trail>/candidate/<run_id> --save
python3 build_topo/scripts/promote_candidate.py trails/<trail>/candidate/<run_id> --accept-drift
```

- [x] **Step 2: State promotion boundaries**

Document that promotion:

- requires existing readiness and drift evidence
- snapshots current promoted artifacts under `promotion_snapshots/`
- copies only candidate-present files
- never deletes promoted files in this slice
- writes `candidate_promotion_report.json`
- is deterministic and non-AI

### Task 4: Verification And Branch Finish

**Files:**
- Modify: `docs/superpowers/plans/2026-06-07-promote-candidate-artifacts.md`

- [x] **Step 1: Run focused tests**

```bash
.venv/bin/python -m pytest -q \
  cairn/tests/test_build_topo_candidate_promotion.py \
  cairn/tests/test_build_topo_promote_candidate_cli.py \
  cairn/tests/test_build_topo_candidate_drift.py \
  cairn/tests/test_build_topo_examine_candidate_drift_cli.py \
  cairn/tests/test_build_topo_candidate_report.py \
  cairn/tests/test_build_topo_promotion_readiness.py \
  cairn/tests/test_build_topo_check_promotion_readiness_cli.py
```

- [x] **Step 2: Run broader tests and whitespace check**

```bash
.venv/bin/python -m pytest -q cairn/tests
git diff --check
```

- [x] **Step 3: Update this plan**

Check off completed tasks and record verification results in this file.

Verification results:

- Focused candidate lifecycle suite: `30 passed in 1.54s`.
- Full `cairn/tests` suite: `270 passed in 65.28s`.
- `git diff --check`: passed with no output.

- [ ] **Step 4: Commit and open PR**

Commit the branch, push to origin, open a PR against `dev`, and attach a concise issue #74 update.
