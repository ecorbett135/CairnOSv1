# build_topo Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first issue #74 modernization slice by adding explicit `build_topo` stage contracts, candidate artifact manifests, candidate validation, and documentation without regenerating or replacing promoted trail data.

**Architecture:** Keep current promoted artifacts under `trails/<trail>/compiled/` as the only runtime substrate. Add small compiler support modules that describe stage expectations, write candidate manifests under `trails/<trail>/candidate/<run_id>/`, and validate candidate artifact sets before any future promotion command exists.

**Tech Stack:** Python 3, dataclasses, `pathlib`, `json`, `hashlib`, existing `pytest` test suite, existing `build_topo` compiler modules.

---

## Spec Source

- Design doc: `docs/design/issue-74-build-topo-modernization.md`
- GitHub issue: https://github.com/ecorbett135/CairnOSv1/issues/74
- Existing compiler entrypoint: `build_topo/scripts/build_topology.py`
- Existing compiler provenance helper: `build_topo/compiler/provenance.py`
- Existing compiler docs: `build_topo/docs/compiler_overview.md`, `build_topo/docs/trail_integration_guide.md`

## Scope Boundaries

This plan implements the first buildable slice only.

It must:

- define stage contracts for existing `build_topo` stages
- make the stage order importable and testable
- create candidate run directory helpers
- write candidate manifests with provenance and content hashes
- validate candidate directories without touching promoted `compiled/` artifacts
- document artifact boundaries and manual promotion rules

It must not:

- download OSM data
- download TNM/TNMAccess data
- regenerate Long Trail compiled files
- overwrite `trails/<trail>/compiled/`
- add automatic promotion
- change planner/runtime code to read candidates
- implement SECTION planning semantics

## File Structure

- Create `build_topo/compiler/contracts.py`
  - Owns immutable compiler stage and artifact contract declarations.
  - Exposes helpers for stage lookup and expected artifact enumeration.
- Create `build_topo/compiler/candidates.py`
  - Owns candidate run directory validation, creation, content hashing, and manifest writing.
  - Keeps all paths under `trails/<trail>/candidate/<run_id>/`.
- Create `build_topo/compiler/candidate_validation.py`
  - Owns lightweight candidate artifact validation independent from promoted `compiled/`.
  - Checks required file presence, JSON parseability, and GeoJSON shape.
- Modify `build_topo/scripts/build_topology.py`
  - Move the existing local `stages` list to a module-level `STAGES` tuple.
  - Keep runtime behavior unchanged.
- Modify `build_topo/docs/compiler_overview.md`
  - Document contract-backed stage list and candidate boundary.
- Modify `build_topo/docs/trail_integration_guide.md`
  - Document `raw/`, `intermediate/`, `candidate/`, and `compiled/` roles.
- Create `cairn/tests/test_build_topo_contracts.py`
  - Tests stage contracts and `build_topology.STAGES` alignment.
- Create `cairn/tests/test_build_topo_candidates.py`
  - Tests candidate path safety and manifest/provenance shape.
- Create `cairn/tests/test_build_topo_candidate_validation.py`
  - Tests candidate validation success and failure modes with temporary directories.

## Task 1: Make Existing Stage Order Importable

**Files:**
- Modify: `build_topo/scripts/build_topology.py`
- Test: `cairn/tests/test_build_topo_contracts.py`

- [ ] **Step 1: Write failing importability test**

Create `cairn/tests/test_build_topo_contracts.py` with this initial content:

```python
from build_topo.scripts.build_topology import STAGES


def test_build_topology_exposes_stage_order():
    assert STAGES == (
        ("Spine Import", "build_topo.compiler.spine"),
        ("Terrain Segmentation", "build_topo.compiler.segments"),
        ("Logistics Nodes", "build_topo.compiler.logistics"),
        ("Crossing Refinement", "build_topo.compiler.crossings"),
        ("Route Overlay", "build_topo.compiler.route_overlay"),
        ("Overnight Reference Overlay", "build_topo.compiler.overnight_reference"),
        ("Approach Trails", "build_topo.compiler.approach_trails"),
        ("Operational Graph", "build_topo.compiler.graph"),
        ("Schema Registry", "build_topo.compiler.schema_registry"),
        ("Validation", "build_topo.compiler.validation"),
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest -q cairn/tests/test_build_topo_contracts.py::test_build_topology_exposes_stage_order
```

Expected: FAIL with an import error similar to `cannot import name 'STAGES'`.

- [ ] **Step 3: Move `stages` to module-level constant**

In `build_topo/scripts/build_topology.py`, add this constant after `COMPILER_ROOT`:

```python
STAGES = (

    (
        "Spine Import",
        "build_topo.compiler.spine",
    ),

    (
        "Terrain Segmentation",
        "build_topo.compiler.segments",
    ),

    (
        "Logistics Nodes",
        "build_topo.compiler.logistics",
    ),

    (
        "Crossing Refinement",
        "build_topo.compiler.crossings",
    ),

    (
        "Route Overlay",
        "build_topo.compiler.route_overlay",
    ),

    (
        "Overnight Reference Overlay",
        "build_topo.compiler.overnight_reference",
    ),

    (
        "Approach Trails",
        "build_topo.compiler.approach_trails",
    ),

    (
        "Operational Graph",
        "build_topo.compiler.graph",
    ),

    (
        "Schema Registry",
        "build_topo.compiler.schema_registry",
    ),

    (
        "Validation",
        "build_topo.compiler.validation",
    ),
)
```

Remove the local `stages = [...]` list from `main()`.

Change the loop in `main()` to:

```python
    for name, module in STAGES:
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest -q cairn/tests/test_build_topo_contracts.py::test_build_topology_exposes_stage_order
```

Expected: `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add build_topo/scripts/build_topology.py cairn/tests/test_build_topo_contracts.py
git commit -m "test: expose build_topo stage order"
```

## Task 2: Add Stage And Artifact Contracts

**Files:**
- Create: `build_topo/compiler/contracts.py`
- Modify: `cairn/tests/test_build_topo_contracts.py`

- [ ] **Step 1: Add failing contract tests**

Append this content to `cairn/tests/test_build_topo_contracts.py`:

```python
from build_topo.compiler.contracts import (
    ArtifactContract,
    StageContract,
    get_expected_artifacts,
    get_stage_contracts,
)


def test_stage_contracts_match_build_topology_order():
    contract_pairs = tuple(
        (contract.stage_name, contract.module)
        for contract in get_stage_contracts()
    )

    assert contract_pairs == STAGES


def test_stage_contracts_are_local_and_deterministic():
    for contract in get_stage_contracts():
        assert isinstance(contract, StageContract)
        assert contract.deterministic is True
        assert contract.network_access is False
        assert contract.generated_outputs is not None
        assert contract.validation_rules


def test_expected_artifacts_include_current_promoted_outputs():
    artifact_paths = {
        artifact.relative_path
        for artifact in get_expected_artifacts()
    }

    assert "compiled/spine.geojson" in artifact_paths
    assert "compiled/segments.geojson" in artifact_paths
    assert "compiled/crossings.geojson" in artifact_paths
    assert "compiled/crossings_refined.geojson" in artifact_paths
    assert "compiled/logistics_nodes.json" in artifact_paths
    assert "compiled/route_overlay.json" in artifact_paths
    assert "compiled/approach_trails.json" in artifact_paths
    assert "compiled/operational_graph.json" in artifact_paths
    assert "compiled/cairn_schema_registry.json" in artifact_paths


def test_expected_artifacts_are_deduplicated_by_relative_path():
    artifacts = get_expected_artifacts()
    assert all(isinstance(artifact, ArtifactContract) for artifact in artifacts)

    paths = [
        artifact.relative_path
        for artifact in artifacts
    ]

    assert len(paths) == len(set(paths))
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest -q cairn/tests/test_build_topo_contracts.py
```

Expected: FAIL with `ModuleNotFoundError: No module named 'build_topo.compiler.contracts'`.

- [ ] **Step 3: Create contract module**

Create `build_topo/compiler/contracts.py`:

```python
# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from dataclasses import dataclass


@dataclass(frozen=True)
class ArtifactContract:
    relative_path: str
    artifact_type: str
    required: bool = True


@dataclass(frozen=True)
class StageContract:
    stage_name: str
    module: str
    required_inputs: tuple[str, ...]
    generated_outputs: tuple[ArtifactContract, ...]
    validation_rules: tuple[str, ...]
    deterministic: bool = True
    network_access: bool = False


STAGE_CONTRACTS = (
    StageContract(
        stage_name="Spine Import",
        module="build_topo.compiler.spine",
        required_inputs=(
            "raw/route.geojson",
        ),
        generated_outputs=(
            ArtifactContract("compiled/spine.geojson", "geojson"),
            ArtifactContract("compiled/metadata.json", "json"),
            ArtifactContract("intermediate/canonical_spine.geojson", "geojson", required=False),
        ),
        validation_rules=(
            "spine geojson parses as GeoJSON",
            "spine has at least one feature",
            "metadata json parses",
        ),
    ),
    StageContract(
        stage_name="Terrain Segmentation",
        module="build_topo.compiler.segments",
        required_inputs=(
            "compiled/spine.geojson",
        ),
        generated_outputs=(
            ArtifactContract("compiled/segments.geojson", "geojson"),
            ArtifactContract("compiled/segments.json", "json", required=False),
        ),
        validation_rules=(
            "segments geojson parses as GeoJSON",
            "segments artifact exists before operational graph generation",
        ),
    ),
    StageContract(
        stage_name="Logistics Nodes",
        module="build_topo.compiler.logistics",
        required_inputs=(
            "compiled/spine.geojson",
        ),
        generated_outputs=(
            ArtifactContract("compiled/crossings.geojson", "geojson"),
            ArtifactContract("compiled/logistics_nodes.json", "json"),
        ),
        validation_rules=(
            "crossings geojson parses as GeoJSON",
            "logistics nodes json parses",
        ),
    ),
    StageContract(
        stage_name="Crossing Refinement",
        module="build_topo.compiler.crossings",
        required_inputs=(
            "compiled/crossings.geojson",
        ),
        generated_outputs=(
            ArtifactContract("compiled/crossings_refined.geojson", "geojson"),
            ArtifactContract("compiled/crossings_refined.json", "json", required=False),
        ),
        validation_rules=(
            "refined crossings geojson parses as GeoJSON",
            "refined crossings stay separate from raw crossings",
        ),
    ),
    StageContract(
        stage_name="Route Overlay",
        module="build_topo.compiler.route_overlay",
        required_inputs=(
            "compiled/spine.geojson",
            "compiled/segments.geojson",
        ),
        generated_outputs=(
            ArtifactContract("compiled/route_overlay.json", "json"),
        ),
        validation_rules=(
            "route overlay json parses",
            "route overlay contains operational stop data",
        ),
    ),
    StageContract(
        stage_name="Overnight Reference Overlay",
        module="build_topo.compiler.overnight_reference",
        required_inputs=(
            "compiled/route_overlay.json",
        ),
        generated_outputs=(
            ArtifactContract("compiled/overnight_reference.json", "json", required=False),
        ),
        validation_rules=(
            "overnight reference json parses when present",
            "unmatched reference data remains non-operational",
        ),
    ),
    StageContract(
        stage_name="Approach Trails",
        module="build_topo.compiler.approach_trails",
        required_inputs=(
            "compiled/route_overlay.json",
        ),
        generated_outputs=(
            ArtifactContract("compiled/approach_trails.json", "json"),
        ),
        validation_rules=(
            "approach trails json parses",
            "approach metadata remains explicit",
        ),
    ),
    StageContract(
        stage_name="Operational Graph",
        module="build_topo.compiler.graph",
        required_inputs=(
            "compiled/route_overlay.json",
            "compiled/approach_trails.json",
        ),
        generated_outputs=(
            ArtifactContract("compiled/operational_graph.json", "json"),
        ),
        validation_rules=(
            "operational graph json parses",
            "operational graph contains nodes and edges",
        ),
    ),
    StageContract(
        stage_name="Schema Registry",
        module="build_topo.compiler.schema_registry",
        required_inputs=(
            "compiled/operational_graph.json",
        ),
        generated_outputs=(
            ArtifactContract("compiled/cairn_schema_registry.json", "json"),
        ),
        validation_rules=(
            "schema registry json parses",
            "schema registry names generated datasets",
        ),
    ),
    StageContract(
        stage_name="Validation",
        module="build_topo.compiler.validation",
        required_inputs=(
            "compiled/spine.geojson",
            "compiled/segments.geojson",
            "compiled/operational_graph.json",
            "compiled/cairn_schema_registry.json",
        ),
        generated_outputs=(),
        validation_rules=(
            "validation runs after all generation stages",
            "validation does not generate promoted artifacts",
        ),
    ),
)


def get_stage_contracts():
    return STAGE_CONTRACTS


def get_expected_artifacts(include_optional=False):
    artifacts_by_path = {}

    for contract in STAGE_CONTRACTS:
        for artifact in contract.generated_outputs:
            if artifact.required or include_optional:
                artifacts_by_path.setdefault(
                    artifact.relative_path,
                    artifact,
                )

    return tuple(
        artifacts_by_path[path]
        for path in sorted(artifacts_by_path)
    )


def contract_for_stage(stage_name):
    for contract in STAGE_CONTRACTS:
        if contract.stage_name == stage_name:
            return contract

    raise KeyError(
        f"Unknown build_topo stage: {stage_name}"
    )
```

- [ ] **Step 4: Run contract tests**

Run:

```bash
python -m pytest -q cairn/tests/test_build_topo_contracts.py
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add build_topo/compiler/contracts.py cairn/tests/test_build_topo_contracts.py
git commit -m "feat: declare build_topo stage contracts"
```

## Task 3: Add Candidate Run Helpers And Manifest Writing

**Files:**
- Create: `build_topo/compiler/candidates.py`
- Create: `cairn/tests/test_build_topo_candidates.py`

- [ ] **Step 1: Write failing candidate helper tests**

Create `cairn/tests/test_build_topo_candidates.py`:

```python
import json

import pytest

from build_topo.compiler.candidates import (
    candidate_manifest_path,
    candidate_root_for_run,
    compute_file_sha256,
    ensure_candidate_root,
    write_candidate_manifest,
)


def test_candidate_root_lives_under_trail_candidate_directory(tmp_path):
    trail_root = tmp_path / "trails" / "vermont_long_trail"
    run_id = "2026-06-03-contracts"

    root = candidate_root_for_run(
        trail_root,
        run_id,
    )

    assert root == trail_root / "candidate" / run_id


@pytest.mark.parametrize(
    "run_id",
    [
        "",
        "../escape",
        "nested/run",
        "nested\\run",
        ".",
        "..",
    ],
)
def test_candidate_run_id_rejects_path_traversal(tmp_path, run_id):
    trail_root = tmp_path / "trails" / "vermont_long_trail"

    with pytest.raises(ValueError):
        candidate_root_for_run(
            trail_root,
            run_id,
        )


def test_ensure_candidate_root_creates_directory(tmp_path):
    trail_root = tmp_path / "trails" / "vermont_long_trail"

    root = ensure_candidate_root(
        trail_root,
        "2026-06-03-contracts",
    )

    assert root.exists()
    assert root.is_dir()


def test_compute_file_sha256_is_stable(tmp_path):
    path = tmp_path / "artifact.json"
    path.write_text(
        '{"ok": true}\n',
        encoding="utf-8",
    )

    assert compute_file_sha256(path) == "1ee0db3f17d6b07fb3c9b0e8aa23ae77036f72fe1b662e14be4ffb6db7f04164"


def test_write_candidate_manifest_records_artifacts(tmp_path):
    project_root = tmp_path / "project"
    trail_root = project_root / "trails" / "vermont_long_trail"
    candidate_root = ensure_candidate_root(
        trail_root,
        "2026-06-03-contracts",
    )

    artifact = candidate_root / "compiled" / "route_overlay.json"
    artifact.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    artifact.write_text(
        '{"route": []}\n',
        encoding="utf-8",
    )

    manifest = write_candidate_manifest(
        candidate_root=candidate_root,
        trail_root=trail_root,
        run_id="2026-06-03-contracts",
        artifacts=[
            artifact,
        ],
        command_args=[
            "build_topology.py",
            "trails/vermont_long_trail",
        ],
        stage_names=[
            "Route Overlay",
        ],
        git_commit="abc123",
        validation_status="not_run",
        warnings=[
            "candidate not promoted",
        ],
    )

    manifest_path = candidate_manifest_path(
        candidate_root
    )

    assert manifest_path.exists()
    assert manifest["trail_id"] == "vermont_long_trail"
    assert manifest["run_id"] == "2026-06-03-contracts"
    assert manifest["git_commit"] == "abc123"
    assert manifest["validation_status"] == "not_run"
    assert manifest["stage_names"] == ["Route Overlay"]
    assert manifest["warnings"] == ["candidate not promoted"]
    assert manifest["artifact_root"] == "trails/vermont_long_trail/candidate/2026-06-03-contracts"
    assert manifest["promoted_root"] == "trails/vermont_long_trail/compiled"

    assert manifest["artifacts"] == [
        {
            "path": "trails/vermont_long_trail/candidate/2026-06-03-contracts/compiled/route_overlay.json",
            "candidate_relative_path": "compiled/route_overlay.json",
            "sha256": compute_file_sha256(artifact),
            "bytes": artifact.stat().st_size,
        }
    ]

    saved = json.loads(
        manifest_path.read_text(
            encoding="utf-8",
        )
    )
    assert saved == manifest
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest -q cairn/tests/test_build_topo_candidates.py
```

Expected: FAIL with `ModuleNotFoundError: No module named 'build_topo.compiler.candidates'`.

- [ ] **Step 3: Create candidate helper module**

Create `build_topo/compiler/candidates.py`:

```python
# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import hashlib
import json

from build_topo.compiler.provenance import repo_relative_path


def candidate_root_for_run(trail_root, run_id):
    run_id = str(
        run_id
    )

    if run_id in {"", ".", ".."}:
        raise ValueError(
            "Candidate run_id must be a non-empty directory name"
        )

    if "/" in run_id or "\\" in run_id:
        raise ValueError(
            "Candidate run_id cannot contain path separators"
        )

    return (
        Path(trail_root) /
        "candidate" /
        run_id
    )


def ensure_candidate_root(trail_root, run_id):
    root = candidate_root_for_run(
        trail_root,
        run_id,
    )

    root.mkdir(
        parents=True,
        exist_ok=True,
    )

    return root


def candidate_manifest_path(candidate_root):
    return (
        Path(candidate_root) /
        "candidate_manifest.json"
    )


def compute_file_sha256(path):
    digest = hashlib.sha256()

    with open(path, "rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(
                chunk
            )

    return digest.hexdigest()


def _candidate_relative_path(candidate_root, artifact_path):
    return (
        Path(artifact_path)
        .resolve()
        .relative_to(Path(candidate_root).resolve())
        .as_posix()
    )


def _artifact_manifest_entry(candidate_root, trail_root, artifact_path):
    artifact_path = Path(
        artifact_path
    )

    return {
        "path": repo_relative_path(
            artifact_path,
            trail_root,
        ),
        "candidate_relative_path": _candidate_relative_path(
            candidate_root,
            artifact_path,
        ),
        "sha256": compute_file_sha256(
            artifact_path,
        ),
        "bytes": artifact_path.stat().st_size,
    }


def write_candidate_manifest(
    candidate_root,
    trail_root,
    run_id,
    artifacts,
    command_args,
    stage_names,
    git_commit,
    validation_status,
    warnings=None,
):
    candidate_root = Path(
        candidate_root
    )
    trail_root = Path(
        trail_root
    )

    manifest = {
        "trail_id": trail_root.name,
        "run_id": str(run_id),
        "git_commit": str(git_commit),
        "command_args": list(command_args),
        "stage_names": list(stage_names),
        "artifact_root": repo_relative_path(
            candidate_root,
            trail_root,
        ),
        "promoted_root": repo_relative_path(
            trail_root / "compiled",
            trail_root,
        ),
        "validation_status": str(validation_status),
        "warnings": list(warnings or []),
        "artifacts": [
            _artifact_manifest_entry(
                candidate_root,
                trail_root,
                artifact,
            )
            for artifact in artifacts
        ],
    }

    path = candidate_manifest_path(
        candidate_root
    )

    path.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    return manifest
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest -q cairn/tests/test_build_topo_candidates.py
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add build_topo/compiler/candidates.py cairn/tests/test_build_topo_candidates.py
git commit -m "feat: add build_topo candidate manifests"
```

## Task 4: Add Candidate Artifact Validation

**Files:**
- Create: `build_topo/compiler/candidate_validation.py`
- Create: `cairn/tests/test_build_topo_candidate_validation.py`

- [ ] **Step 1: Write failing candidate validation tests**

Create `cairn/tests/test_build_topo_candidate_validation.py`:

```python
import json

from build_topo.compiler.candidate_validation import (
    validate_candidate_artifacts,
    write_candidate_validation_report,
)
from build_topo.compiler.contracts import ArtifactContract


def _write_json(path, payload):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(payload) + "\n",
        encoding="utf-8",
    )


def test_validate_candidate_artifacts_passes_for_required_json_and_geojson(tmp_path):
    candidate_root = tmp_path / "candidate" / "run"
    _write_json(
        candidate_root / "compiled" / "route_overlay.json",
        {
            "route": [],
        },
    )
    _write_json(
        candidate_root / "compiled" / "spine.geojson",
        {
            "type": "FeatureCollection",
            "features": [],
        },
    )

    report = validate_candidate_artifacts(
        candidate_root,
        artifacts=[
            ArtifactContract("compiled/route_overlay.json", "json"),
            ArtifactContract("compiled/spine.geojson", "geojson"),
        ],
    )

    assert report == {
        "status": "passed",
        "checked_artifacts": [
            "compiled/route_overlay.json",
            "compiled/spine.geojson",
        ],
        "missing": [],
        "invalid": [],
    }


def test_validate_candidate_artifacts_reports_missing_required_files(tmp_path):
    report = validate_candidate_artifacts(
        tmp_path / "candidate" / "run",
        artifacts=[
            ArtifactContract("compiled/route_overlay.json", "json"),
        ],
    )

    assert report["status"] == "failed"
    assert report["missing"] == [
        "compiled/route_overlay.json",
    ]
    assert report["invalid"] == []


def test_validate_candidate_artifacts_ignores_missing_optional_files(tmp_path):
    report = validate_candidate_artifacts(
        tmp_path / "candidate" / "run",
        artifacts=[
            ArtifactContract("compiled/overnight_reference.json", "json", required=False),
        ],
    )

    assert report == {
        "status": "passed",
        "checked_artifacts": [],
        "missing": [],
        "invalid": [],
    }


def test_validate_candidate_artifacts_reports_invalid_json(tmp_path):
    path = tmp_path / "candidate" / "run" / "compiled" / "route_overlay.json"
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        "{broken",
        encoding="utf-8",
    )

    report = validate_candidate_artifacts(
        tmp_path / "candidate" / "run",
        artifacts=[
            ArtifactContract("compiled/route_overlay.json", "json"),
        ],
    )

    assert report["status"] == "failed"
    assert report["missing"] == []
    assert report["invalid"][0]["path"] == "compiled/route_overlay.json"
    assert report["invalid"][0]["reason"].startswith("invalid json:")


def test_validate_candidate_artifacts_reports_invalid_geojson_shape(tmp_path):
    _write_json(
        tmp_path / "candidate" / "run" / "compiled" / "spine.geojson",
        {
            "type": "NotGeoJSON",
        },
    )

    report = validate_candidate_artifacts(
        tmp_path / "candidate" / "run",
        artifacts=[
            ArtifactContract("compiled/spine.geojson", "geojson"),
        ],
    )

    assert report["status"] == "failed"
    assert report["invalid"] == [
        {
            "path": "compiled/spine.geojson",
            "reason": "invalid geojson type: NotGeoJSON",
        }
    ]


def test_write_candidate_validation_report_saves_report(tmp_path):
    candidate_root = tmp_path / "candidate" / "run"
    candidate_root.mkdir(
        parents=True,
    )
    report = {
        "status": "passed",
        "checked_artifacts": [],
        "missing": [],
        "invalid": [],
    }

    path = write_candidate_validation_report(
        candidate_root,
        report,
    )

    assert path == candidate_root / "candidate_validation.json"
    assert json.loads(
        path.read_text(
            encoding="utf-8",
        )
    ) == report
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest -q cairn/tests/test_build_topo_candidate_validation.py
```

Expected: FAIL with `ModuleNotFoundError: No module named 'build_topo.compiler.candidate_validation'`.

- [ ] **Step 3: Create validation module**

Create `build_topo/compiler/candidate_validation.py`:

```python
# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json

from build_topo.compiler.contracts import get_expected_artifacts


VALID_GEOJSON_TYPES = {
    "FeatureCollection",
    "Feature",
    "LineString",
    "MultiLineString",
    "Point",
    "MultiPoint",
    "Polygon",
    "MultiPolygon",
    "GeometryCollection",
}


def _load_json(path):
    with open(path, encoding="utf-8") as file_obj:
        return json.load(
            file_obj
        )


def _validate_json(path):
    _load_json(
        path
    )


def _validate_geojson(path):
    payload = _load_json(
        path
    )

    geojson_type = payload.get(
        "type"
    )

    if geojson_type not in VALID_GEOJSON_TYPES:
        raise ValueError(
            f"invalid geojson type: {geojson_type}"
        )


def _validate_artifact(path, artifact_type):
    if artifact_type == "json":
        _validate_json(
            path
        )
        return

    if artifact_type == "geojson":
        _validate_geojson(
            path
        )
        return

    raise ValueError(
        f"unsupported artifact type: {artifact_type}"
    )


def validate_candidate_artifacts(candidate_root, artifacts=None):
    candidate_root = Path(
        candidate_root
    )

    artifacts = tuple(
        artifacts
        if artifacts is not None
        else get_expected_artifacts()
    )

    checked = []
    missing = []
    invalid = []

    for artifact in artifacts:
        path = (
            candidate_root /
            artifact.relative_path
        )

        if not path.exists():
            if artifact.required:
                missing.append(
                    artifact.relative_path
                )
            continue

        checked.append(
            artifact.relative_path
        )

        try:
            _validate_artifact(
                path,
                artifact.artifact_type,
            )
        except (json.JSONDecodeError, ValueError) as exc:
            invalid.append(
                {
                    "path": artifact.relative_path,
                    "reason": (
                        f"invalid json: {exc}"
                        if artifact.artifact_type == "json"
                        else str(exc)
                    ),
                }
            )

    status = (
        "failed"
        if missing or invalid
        else "passed"
    )

    return {
        "status": status,
        "checked_artifacts": checked,
        "missing": missing,
        "invalid": invalid,
    }


def write_candidate_validation_report(candidate_root, report):
    path = (
        Path(candidate_root) /
        "candidate_validation.json"
    )

    path.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    return path
```

- [ ] **Step 4: Run candidate validation tests**

Run:

```bash
python -m pytest -q cairn/tests/test_build_topo_candidate_validation.py
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add build_topo/compiler/candidate_validation.py cairn/tests/test_build_topo_candidate_validation.py
git commit -m "feat: validate build_topo candidate artifacts"
```

## Task 5: Document Candidate Boundaries And Manual Promotion

**Files:**
- Modify: `build_topo/docs/compiler_overview.md`
- Modify: `build_topo/docs/trail_integration_guide.md`

- [ ] **Step 1: Update compiler overview**

Add this section to `build_topo/docs/compiler_overview.md` after `## Core Architectural Principle`:

```markdown
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

Promotion is manual. A candidate set must have a manifest, validation report,
and human review before any promoted file is replaced.
```

- [ ] **Step 2: Update trail integration guide**

Add this section to `build_topo/docs/trail_integration_guide.md` after the first architecture or setup section:

```markdown
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
- generated artifacts that mirror their promoted relative paths

Example:

```text
trails/vermont_long_trail/candidate/2026-06-03-contracts/
  candidate_manifest.json
  candidate_validation.json
  compiled/
    route_overlay.json
    operational_graph.json
```

Only copy candidate artifacts into `compiled/` after validation passes and the
diff has been reviewed. Keep existing promoted files recoverable until the new
candidate has been field-tested or otherwise accepted.
```

- [ ] **Step 3: Run markdown sanity checks**

Run:

```bash
rg -n "candidate/<run_id>|manual|compiled/" build_topo/docs/compiler_overview.md build_topo/docs/trail_integration_guide.md
```

Expected: output includes the new candidate boundary text in both docs.

- [ ] **Step 4: Commit**

```bash
git add build_topo/docs/compiler_overview.md build_topo/docs/trail_integration_guide.md
git commit -m "docs: document build_topo candidate boundaries"
```

## Task 6: Run Focused And Regression Verification

**Files:**
- Verify only.

- [ ] **Step 1: Run focused build_topo modernization tests**

Run:

```bash
python -m pytest -q \
  cairn/tests/test_build_topo_contracts.py \
  cairn/tests/test_build_topo_candidates.py \
  cairn/tests/test_build_topo_candidate_validation.py
```

Expected: all tests pass.

- [ ] **Step 2: Run adjacent existing compiler tests**

Run:

```bash
python -m pytest -q \
  cairn/tests/test_gaia_reference_overlay.py \
  cairn/tests/test_overnight_reference.py
```

Expected: all tests pass.

- [ ] **Step 3: Check working tree and whitespace**

Run:

```bash
git diff --check
git status --short
```

Expected:

- `git diff --check` exits 0.
- `git status --short` shows no uncommitted files after all commits.

## Task 7: Finish The Branch

**Files:**
- Verify only.

- [ ] **Step 1: Review commit history**

Run:

```bash
git log --oneline --decorate -5
```

Expected: latest commits are the task commits above.

- [ ] **Step 2: Push branch**

Run:

```bash
git push -u origin codex/issue-74-build-topo-contract-plan
```

Expected: branch pushes cleanly.

- [ ] **Step 3: Open PR**

Open a PR against `dev` with this title:

```text
[codex] Implement build_topo candidate contracts
```

Use this PR body:

```markdown
## Summary

- exposes the existing `build_topo` stage order for contract testing
- adds immutable stage/artifact contracts for the current compiler pipeline
- adds candidate directory helpers, manifests, content hashes, and lightweight candidate validation
- documents the candidate versus promoted artifact boundary for issue #74

## Scope

This does not regenerate Long Trail compiled data, download OSM/TNM inputs, add automatic promotion, or change planner/runtime reads.

## Tests

- `python -m pytest -q cairn/tests/test_build_topo_contracts.py cairn/tests/test_build_topo_candidates.py cairn/tests/test_build_topo_candidate_validation.py`
- `python -m pytest -q cairn/tests/test_gaia_reference_overlay.py cairn/tests/test_overnight_reference.py`
- `git diff --check`
```

- [ ] **Step 4: Update issue #74**

Add a short issue comment:

```markdown
First buildable slice is in review: stage contracts, candidate manifests, candidate validation, and artifact boundary docs. This intentionally avoids OSM/TNM downloads and does not regenerate promoted Long Trail compiled files.
```

## Self-Review Checklist

- Spec coverage:
  - Stage contracts: Tasks 1 and 2
  - Artifact classes and output boundaries: Tasks 2, 3, and 5
  - Provenance metadata for candidates: Task 3
  - Candidate validation without promoted artifact writes: Task 4
  - Manual promotion model documentation: Task 5
- Placeholder scan:
  - No task contains placeholder markers or unspecified implementation instructions.
  - Every code-changing task includes concrete tests, code, commands, and expected output.
- Type consistency:
  - `ArtifactContract.relative_path`, `artifact_type`, and `required` are used consistently by contracts and validation.
  - `StageContract.stage_name` and `module` align with `build_topology.STAGES`.
  - Candidate manifests use repo-relative paths through `repo_relative_path()`.
