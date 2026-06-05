# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "build_topo" / "scripts" / "check_promotion_readiness.py"


def _write_json(path, payload):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _artifact(relative_path, candidate_present, promoted_present, changed):
    return {
        "relative_path": relative_path,
        "artifact_type": "json",
        "required": True,
        "candidate_present": candidate_present,
        "promoted_present": promoted_present,
        "changed": changed,
        "candidate": (
            {
                "bytes": 17,
                "sha256": "candidate-" + relative_path,
            }
            if candidate_present
            else None
        ),
        "promoted": (
            {
                "bytes": 19,
                "sha256": (
                    "candidate-" + relative_path
                    if changed is False
                    else "promoted-" + relative_path
                ),
            }
            if promoted_present
            else None
        ),
    }


def _candidate_report(validation_status="passed"):
    artifacts = [
        _artifact(
            "compiled/route_overlay.json",
            candidate_present=True,
            promoted_present=True,
            changed=True,
        ),
        _artifact(
            "compiled/operational_graph.json",
            candidate_present=True,
            promoted_present=True,
            changed=False,
        ),
        _artifact(
            "compiled/crossings.geojson",
            candidate_present=True,
            promoted_present=False,
            changed=None,
        ),
    ]

    return {
        "format": "cairnos_build_topo_candidate_report_v1",
        "candidate_root": "trails/vermont_long_trail/candidate/run-1",
        "promoted_root": "trails/vermont_long_trail/compiled",
        "validation": {
            "status": validation_status,
            "checked_artifacts": [
                artifact["relative_path"]
                for artifact in artifacts
            ],
            "missing": [],
            "invalid": [],
        },
        "summary": {
            "checked_artifacts": 3,
            "candidate_present": 3,
            "promoted_present": 2,
            "changed": 1,
            "missing_required": 0,
            "invalid": 0,
        },
        "artifacts": artifacts,
    }


def _write_demo_files(trail_root, candidate_root):
    _write_json(
        trail_root / "compiled" / "route_overlay.json",
        {
            "marker": "promoted",
        },
    )
    _write_json(
        candidate_root / "compiled" / "route_overlay.json",
        {
            "marker": "candidate",
        },
    )
    _write_json(
        candidate_root / "candidate_report.json",
        _candidate_report(),
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


def test_check_promotion_readiness_cli_prints_checklist_without_mutation(
    tmp_path,
):
    trail_root = tmp_path / "trails" / "vermont_long_trail"
    candidate_root = trail_root / "candidate" / "run-1"
    _write_demo_files(
        trail_root,
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
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Promotion readiness: ready" in result.stdout
    assert "[pass] Candidate report evidence exists" in result.stdout
    assert "[review] Review candidate-vs-promoted artifact diffs" in result.stdout
    assert "Artifact diff summary" in result.stdout
    assert "changed: 1" in result.stdout
    assert "unchanged: 1" in result.stdout
    assert "new: 1" in result.stdout
    assert "compiled/route_overlay.json changed" in result.stdout
    assert _tree_snapshot(
        trail_root
    ) == before


def test_check_promotion_readiness_cli_exits_one_when_report_missing(tmp_path):
    candidate_root = tmp_path / "trails" / "vermont_long_trail" / "candidate" / "run-1"
    candidate_root.mkdir(
        parents=True,
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(candidate_root),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Promotion readiness: not_ready" in result.stdout
    assert "[fail] Candidate report evidence exists" in result.stdout
    assert "validate_candidate.py" in result.stdout
