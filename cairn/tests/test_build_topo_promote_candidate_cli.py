# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import hashlib
import json
import subprocess
import sys

from build_topo.compiler.candidate_drift import (
    build_candidate_drift,
    write_candidate_drift_report,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "build_topo" / "scripts" / "promote_candidate.py"


def _write_text(path, text):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        text,
        encoding="utf-8",
    )


def _write_json(path, payload):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _summary(path):
    if not path.exists():
        return None

    data = path.read_bytes()

    return {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _artifact(trail_root, candidate_root, relative_path, candidate_present, promoted_present):
    candidate_summary = _summary(
        candidate_root / relative_path
    )
    promoted_summary = _summary(
        trail_root / relative_path
    )

    return {
        "relative_path": relative_path,
        "artifact_type": "json",
        "required": True,
        "candidate_present": candidate_present,
        "promoted_present": promoted_present,
        "changed": (
            None
            if candidate_summary is None or promoted_summary is None
            else candidate_summary["sha256"] != promoted_summary["sha256"]
        ),
        "candidate": candidate_summary,
        "promoted": promoted_summary,
    }


def _candidate_report(artifacts):
    return {
        "format": "cairnos_build_topo_candidate_report_v1",
        "candidate_root": "trails/vermont_long_trail/candidate/run-1",
        "promoted_root": "trails/vermont_long_trail/compiled",
        "validation": {
            "status": "passed",
            "checked_artifacts": [
                artifact["relative_path"]
                for artifact in artifacts
                if artifact["candidate_present"]
            ],
            "missing": [],
            "invalid": [],
        },
        "summary": {
            "checked_artifacts": sum(
                1 for artifact in artifacts
                if artifact["candidate_present"]
            ),
            "candidate_present": sum(
                1 for artifact in artifacts
                if artifact["candidate_present"]
            ),
            "promoted_present": sum(
                1 for artifact in artifacts
                if artifact["promoted_present"]
            ),
            "changed": sum(
                1 for artifact in artifacts
                if artifact["changed"] is True
            ),
            "missing_required": 0,
            "invalid": 0,
        },
        "artifacts": artifacts,
    }


def _demo_candidate(tmp_path):
    trail_root = tmp_path / "trails" / "vermont_long_trail"
    candidate_root = trail_root / "candidate" / "run-1"

    _write_text(
        trail_root / "compiled" / "route_overlay.json",
        "promoted route\n",
    )
    _write_text(
        trail_root / "compiled" / "segments.geojson",
        "keep missing candidate\n",
    )
    _write_text(
        candidate_root / "compiled" / "route_overlay.json",
        "candidate route\n",
    )
    _write_text(
        candidate_root / "compiled" / "crossings.geojson",
        "candidate crossing\n",
    )

    artifacts = [
        _artifact(
            trail_root,
            candidate_root,
            "compiled/route_overlay.json",
            candidate_present=True,
            promoted_present=True,
        ),
        _artifact(
            trail_root,
            candidate_root,
            "compiled/crossings.geojson",
            candidate_present=True,
            promoted_present=False,
        ),
        _artifact(
            trail_root,
            candidate_root,
            "compiled/segments.geojson",
            candidate_present=False,
            promoted_present=True,
        ),
    ]
    _write_json(
        candidate_root / "candidate_report.json",
        _candidate_report(
            artifacts
        ),
    )
    write_candidate_drift_report(
        candidate_root,
        build_candidate_drift(
            candidate_root,
        ),
    )

    return trail_root, candidate_root


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


def test_promote_candidate_cli_blocks_without_accept_drift(tmp_path):
    trail_root, candidate_root = _demo_candidate(
        tmp_path
    )
    before = _tree_snapshot(
        trail_root
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(candidate_root),
            "--promotion-id",
            "promo-1",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Candidate promotion: blocked" in result.stdout
    assert "use --accept-drift" in result.stdout
    assert _tree_snapshot(
        trail_root
    ) == before


def test_promote_candidate_cli_promotes_with_accept_drift(tmp_path):
    trail_root, candidate_root = _demo_candidate(
        tmp_path
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(candidate_root),
            "--promotion-id",
            "promo-1",
            "--accept-drift",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Candidate promotion: promoted" in result.stdout
    assert "copied: 2" in result.stdout
    assert "skipped: 1" in result.stdout
    assert (
        trail_root / "compiled" / "route_overlay.json"
    ).read_text(encoding="utf-8") == "candidate route\n"
    assert (
        trail_root / "compiled" / "segments.geojson"
    ).read_text(encoding="utf-8") == "keep missing candidate\n"


def test_promote_candidate_cli_json_dry_run(tmp_path):
    trail_root, candidate_root = _demo_candidate(
        tmp_path
    )
    before = _tree_snapshot(
        trail_root
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(candidate_root),
            "--promotion-id",
            "promo-1",
            "--accept-drift",
            "--dry-run",
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(
        result.stdout
    )
    assert payload["status"] == "ready"
    assert payload["dry_run"] is True
    assert payload["summary"]["copied"] == 2
    assert not (
        trail_root / "promotion_snapshots" / "promo-1"
    ).exists()
    assert _tree_snapshot(
        trail_root
    ) == before
