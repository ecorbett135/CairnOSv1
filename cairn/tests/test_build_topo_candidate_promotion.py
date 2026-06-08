# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import hashlib
import json

from build_topo.compiler.candidate_drift import (
    build_candidate_drift,
    write_candidate_drift_report,
)
from build_topo.compiler.candidate_promotion import promote_candidate_artifacts


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
    candidate_path = candidate_root / relative_path
    promoted_path = trail_root / relative_path
    candidate_summary = _summary(
        candidate_path
    )
    promoted_summary = _summary(
        promoted_path
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


def _candidate_report(trail_root, candidate_root, artifacts):
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
        trail_root / "compiled" / "operational_graph.json",
        "same graph\n",
    )
    _write_text(
        trail_root / "compiled" / "segments.geojson",
        "keep promoted missing candidate\n",
    )
    _write_text(
        candidate_root / "compiled" / "route_overlay.json",
        "candidate route\n",
    )
    _write_text(
        candidate_root / "compiled" / "operational_graph.json",
        "same graph\n",
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
            "compiled/operational_graph.json",
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
            trail_root,
            candidate_root,
            artifacts,
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


def test_promote_candidate_blocks_when_drift_requires_acceptance(tmp_path):
    trail_root, candidate_root = _demo_candidate(
        tmp_path
    )
    before = _tree_snapshot(
        trail_root
    )

    report = promote_candidate_artifacts(
        candidate_root,
        promotion_id="promo-1",
    )

    assert report["status"] == "blocked"
    assert "use --accept-drift" in report["blockers"][0]
    assert _tree_snapshot(
        trail_root
    ) == before


def test_promote_candidate_snapshots_and_copies_candidate_present_artifacts(tmp_path):
    trail_root, candidate_root = _demo_candidate(
        tmp_path
    )

    report = promote_candidate_artifacts(
        candidate_root,
        promotion_id="promo-1",
        accept_drift=True,
    )

    snapshot_root = trail_root / "promotion_snapshots" / "promo-1"
    promotion_report = candidate_root / "candidate_promotion_report.json"

    assert report["status"] == "promoted"
    assert report["summary"] == {
        "copied": 3,
        "skipped": 1,
        "snapshotted": 3,
    }
    assert (
        snapshot_root / "compiled" / "route_overlay.json"
    ).read_text(encoding="utf-8") == "promoted route\n"
    assert (
        trail_root / "compiled" / "route_overlay.json"
    ).read_text(encoding="utf-8") == "candidate route\n"
    assert (
        trail_root / "compiled" / "crossings.geojson"
    ).read_text(encoding="utf-8") == "candidate crossing\n"
    assert (
        trail_root / "compiled" / "segments.geojson"
    ).read_text(encoding="utf-8") == "keep promoted missing candidate\n"
    assert promotion_report.exists()
    assert json.loads(
        promotion_report.read_text(
            encoding="utf-8",
        )
    ) == report


def test_promote_candidate_dry_run_does_not_mutate_files(tmp_path):
    trail_root, candidate_root = _demo_candidate(
        tmp_path
    )
    before = _tree_snapshot(
        trail_root
    )

    report = promote_candidate_artifacts(
        candidate_root,
        promotion_id="promo-1",
        accept_drift=True,
        dry_run=True,
    )

    assert report["status"] == "ready"
    assert report["dry_run"] is True
    assert not (
        trail_root / "promotion_snapshots" / "promo-1"
    ).exists()
    assert not (
        candidate_root / "candidate_promotion_report.json"
    ).exists()
    assert _tree_snapshot(
        trail_root
    ) == before


def test_promote_candidate_blocks_without_drift_report(tmp_path):
    trail_root, candidate_root = _demo_candidate(
        tmp_path
    )
    (
        candidate_root / "candidate_drift_report.json"
    ).unlink()
    before = _tree_snapshot(
        trail_root
    )

    report = promote_candidate_artifacts(
        candidate_root,
        promotion_id="promo-1",
        accept_drift=True,
    )

    assert report["status"] == "blocked"
    assert "candidate_drift_report.json is missing" in report["blockers"][0]
    assert _tree_snapshot(
        trail_root
    ) == before


def test_promote_candidate_blocks_stale_candidate_hashes(tmp_path):
    trail_root, candidate_root = _demo_candidate(
        tmp_path
    )
    _write_text(
        candidate_root / "compiled" / "route_overlay.json",
        "candidate changed after report\n",
    )
    before = _tree_snapshot(
        trail_root
    )

    report = promote_candidate_artifacts(
        candidate_root,
        promotion_id="promo-1",
        accept_drift=True,
    )

    assert report["status"] == "blocked"
    assert "hash does not match candidate_report.json" in report["blockers"][0]
    assert _tree_snapshot(
        trail_root
    ) == before


def test_promote_candidate_blocks_unsafe_artifact_paths(tmp_path):
    trail_root, candidate_root = _demo_candidate(
        tmp_path
    )
    report_path = candidate_root / "candidate_report.json"
    report = json.loads(
        report_path.read_text(
            encoding="utf-8",
        )
    )
    report["artifacts"].append(
        {
            "relative_path": "compiled/../raw/escape.json",
            "artifact_type": "json",
            "required": True,
            "candidate_present": True,
            "promoted_present": False,
            "changed": None,
            "candidate": {
                "bytes": 2,
                "sha256": "bad",
            },
            "promoted": None,
        }
    )
    _write_json(
        report_path,
        report,
    )
    write_candidate_drift_report(
        candidate_root,
        build_candidate_drift(
            candidate_root,
        ),
    )
    before = _tree_snapshot(
        trail_root
    )

    promotion = promote_candidate_artifacts(
        candidate_root,
        promotion_id="promo-1",
        accept_drift=True,
    )

    assert promotion["status"] == "blocked"
    assert "unsafe artifact path" in promotion["blockers"][0]
    assert _tree_snapshot(
        trail_root
    ) == before
