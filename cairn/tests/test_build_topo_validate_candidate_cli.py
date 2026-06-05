# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json
import subprocess
import sys

from build_topo.compiler.contracts import get_expected_artifacts


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "build_topo" / "scripts" / "validate_candidate.py"


def _payload_for_artifact(artifact, marker):
    if artifact.artifact_type == "geojson":
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "marker": marker,
                    },
                    "geometry": None,
                }
            ],
        }

    return {
        "marker": marker,
    }


def _write_json(path, payload):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_required_artifacts(root, marker):
    for artifact in get_expected_artifacts():
        _write_json(
            root / artifact.relative_path,
            _payload_for_artifact(
                artifact,
                marker,
            ),
        )


def _compiled_snapshot(trail_root):
    return {
        path.relative_to(trail_root).as_posix(): path.read_text(
            encoding="utf-8",
        )
        for path in sorted(
            (trail_root / "compiled").glob("**/*")
        )
        if path.is_file()
    }


def test_validate_candidate_cli_writes_reports_and_leaves_compiled_unchanged(
    tmp_path,
):
    trail_root = tmp_path / "trails" / "vermont_long_trail"
    candidate_root = trail_root / "candidate" / "run-1"
    _write_required_artifacts(
        trail_root,
        "promoted",
    )
    _write_required_artifacts(
        candidate_root,
        "candidate",
    )
    before = _compiled_snapshot(
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
    report = json.loads(
        result.stdout
    )
    assert report["validation"]["status"] == "passed"
    assert report["summary"]["missing_required"] == 0
    assert report["summary"]["invalid"] == 0
    assert report["summary"]["changed"] == len(
        get_expected_artifacts()
    )
    assert (
        candidate_root /
        "candidate_validation.json"
    ).exists()
    assert (
        candidate_root /
        "candidate_report.json"
    ).exists()
    assert _compiled_snapshot(
        trail_root
    ) == before


def test_validate_candidate_cli_exits_one_and_writes_evidence_when_invalid(
    tmp_path,
):
    trail_root = tmp_path / "trails" / "vermont_long_trail"
    candidate_root = trail_root / "candidate" / "run-1"
    _write_required_artifacts(
        trail_root,
        "promoted",
    )
    _write_required_artifacts(
        candidate_root,
        "candidate",
    )
    missing_artifact = get_expected_artifacts()[0]
    (
        candidate_root /
        missing_artifact.relative_path
    ).unlink()

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(candidate_root),
            "--trail-root",
            str(trail_root),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    report = json.loads(
        result.stdout
    )
    assert report["validation"]["status"] == "failed"
    assert report["validation"]["missing"] == [
        missing_artifact.relative_path,
    ]
    assert report["summary"]["missing_required"] == 1
    assert (
        candidate_root /
        "candidate_validation.json"
    ).exists()
    assert (
        candidate_root /
        "candidate_report.json"
    ).exists()
