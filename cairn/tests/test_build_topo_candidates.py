# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
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

    assert (
        compute_file_sha256(path)
        == "55f66c2c5aeb275ff5b1ae26b321d5c0b8ceda8c034b19c2643e046d024919f3"
    )


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
    assert (
        manifest["artifact_root"]
        == "trails/vermont_long_trail/candidate/2026-06-03-contracts"
    )
    assert manifest["promoted_root"] == "trails/vermont_long_trail/compiled"

    assert manifest["artifacts"] == [
        {
            "path": (
                "trails/vermont_long_trail/candidate/"
                "2026-06-03-contracts/compiled/route_overlay.json"
            ),
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
