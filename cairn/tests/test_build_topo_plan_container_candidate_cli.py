# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "build_topo" / "scripts" / "plan_container_candidate.py"


def _write_json(path, payload):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_ready_candidate_report(candidate_root):
    _write_json(
        candidate_root / "candidate_report.json",
        {
            "format": "cairnos_build_topo_candidate_report_v1",
            "candidate_root": "trails/vermont_long_trail/candidate/run-1",
            "promoted_root": "trails/vermont_long_trail/compiled",
            "validation": {
                "status": "passed",
                "checked_artifacts": [
                    "compiled/route_overlay.json",
                ],
                "missing": [],
                "invalid": [],
            },
            "summary": {
                "checked_artifacts": 1,
                "candidate_present": 1,
                "promoted_present": 1,
                "changed": 1,
                "missing_required": 0,
                "invalid": 0,
            },
            "artifacts": [
                {
                    "relative_path": "compiled/route_overlay.json",
                    "artifact_type": "json",
                    "required": True,
                    "candidate_present": True,
                    "promoted_present": True,
                    "changed": True,
                    "candidate": {
                        "bytes": 17,
                        "sha256": "candidate",
                    },
                    "promoted": {
                        "bytes": 19,
                        "sha256": "promoted",
                    },
                },
            ],
        },
    )


def _tree_snapshot(root):
    return {
        path.relative_to(root).as_posix(): path.read_text(
            encoding="utf-8",
        )
        for path in sorted(
            root.glob("**/*")
        )
        if path.is_file()
    }


def test_plan_container_candidate_cli_prints_ready_json_without_saving(tmp_path):
    trail_root = tmp_path / "trails" / "vermont_long_trail"
    candidate_root = trail_root / "candidate" / "run-1"
    _write_ready_candidate_report(
        candidate_root,
    )
    before = _tree_snapshot(
        trail_root
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(candidate_root),
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
    assert plan["status"] == "ready"
    assert plan["candidate_image"]["digest"] == "sha256:candidate123"
    assert plan["baseline_image"]["digest"] == "sha256:baseline456"
    assert plan["smoke_tests"][0]["candidate_url"] == "http://127.0.0.1:3011/health"
    assert not (
        candidate_root /
        "container_candidate_plan.json"
    ).exists()
    assert _tree_snapshot(
        trail_root
    ) == before


def test_plan_container_candidate_cli_blocks_without_digest(tmp_path):
    candidate_root = tmp_path / "trails" / "vermont_long_trail" / "candidate" / "run-1"
    _write_ready_candidate_report(
        candidate_root,
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(candidate_root),
            "--candidate-image",
            "cairnos-plan-api:candidate",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    plan = json.loads(
        result.stdout
    )
    assert plan["status"] == "blocked"
    assert plan["blockers"] == [
        "candidate image digest is required before promotion planning",
    ]


def test_plan_container_candidate_cli_save_writes_candidate_local_plan(tmp_path):
    trail_root = tmp_path / "trails" / "vermont_long_trail"
    candidate_root = trail_root / "candidate" / "run-1"
    _write_json(
        trail_root / "compiled" / "route_overlay.json",
        {
            "marker": "promoted",
        },
    )
    _write_ready_candidate_report(
        candidate_root,
    )
    before_compiled = _tree_snapshot(
        trail_root / "compiled"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(candidate_root),
            "--candidate-image",
            "cairnos-plan-api:candidate",
            "--candidate-digest",
            "sha256:candidate123",
            "--save",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    saved_path = candidate_root / "container_candidate_plan.json"
    assert saved_path.exists()
    assert json.loads(
        saved_path.read_text(
            encoding="utf-8",
        )
    ) == json.loads(
        result.stdout
    )
    assert _tree_snapshot(
        trail_root / "compiled"
    ) == before_compiled
