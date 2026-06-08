# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "build_topo" / "scripts" / "create_container_candidate.py"


def _write_json(path, payload):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _tree_snapshot(root):
    if not root.exists():
        return {}

    return {
        path.relative_to(root).as_posix(): path.read_text(
            encoding="utf-8",
        )
        for path in sorted(
            root.glob("**/*")
        )
        if path.is_file()
    }


def test_create_container_candidate_cli_creates_run_and_plan_without_mutation(
    tmp_path,
):
    trail_root = tmp_path / "trails" / "vermont_long_trail"
    _write_json(
        trail_root / "compiled" / "route_overlay.json",
        {
            "marker": "promoted",
        },
    )
    before_compiled = _tree_snapshot(
        trail_root / "compiled"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--trail-root",
            str(trail_root),
            "--run-id",
            "run-1",
            "--candidate-image",
            "cairnos-plan-api:candidate",
            "--candidate-digest",
            "sha256:candidate123",
            "--baseline-image",
            "cairnos-plan-api:baseline",
            "--baseline-digest",
            "sha256:baseline456",
            "--candidate-port",
            "3011",
            "--baseline-port",
            "3010",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    plan = json.loads(
        result.stdout
    )
    candidate_root = trail_root / "candidate" / "run-1"
    saved_path = candidate_root / "container_candidate_plan.json"

    assert candidate_root.is_dir()
    assert saved_path.exists()
    assert json.loads(
        saved_path.read_text(
            encoding="utf-8",
        )
    ) == plan
    assert plan["run_id"] == "run-1"
    assert plan["candidate_root"].endswith(
        "trails/vermont_long_trail/candidate/run-1"
    )
    assert plan["candidate_image"]["digest"] == "sha256:candidate123"
    assert plan["baseline_image"]["digest"] == "sha256:baseline456"
    assert plan["status"] == "blocked"
    assert plan["blockers"] == [
        "candidate artifact readiness status is not_ready",
    ]
    assert _tree_snapshot(
        trail_root / "compiled"
    ) == before_compiled


def test_create_container_candidate_cli_generates_timestamp_run_id(tmp_path):
    trail_root = tmp_path / "trails" / "vermont_long_trail"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--trail-root",
            str(trail_root),
            "--candidate-image",
            "cairnos-plan-api:candidate",
            "--candidate-digest",
            "sha256:candidate123",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    plan = json.loads(
        result.stdout
    )
    assert plan["run_id"].endswith(
        "-container-candidate"
    )
    assert (
        trail_root /
        "candidate" /
        plan["run_id"] /
        "container_candidate_plan.json"
    ).exists()


def test_create_container_candidate_cli_refuses_existing_run(tmp_path):
    trail_root = tmp_path / "trails" / "vermont_long_trail"
    candidate_root = trail_root / "candidate" / "run-1"
    _write_json(
        candidate_root / "container_candidate_plan.json",
        {
            "existing": True,
        },
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--trail-root",
            str(trail_root),
            "--run-id",
            "run-1",
            "--candidate-image",
            "cairnos-plan-api:candidate",
            "--candidate-digest",
            "sha256:candidate123",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "candidate run already exists" in result.stderr
    assert json.loads(
        (
            candidate_root /
            "container_candidate_plan.json"
        ).read_text(
            encoding="utf-8",
        )
    ) == {
        "existing": True,
    }
