# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import json

from build_topo.compiler.candidate_drift import (
    build_candidate_drift,
    write_candidate_drift_report,
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


def _candidate_report(validation_status="passed", artifacts=None):
    artifacts = list(
        artifacts
        if artifacts is not None
        else []
    )

    return {
        "format": "cairnos_build_topo_candidate_report_v1",
        "candidate_root": "trails/vermont_long_trail/candidate/run-1",
        "promoted_root": "trails/vermont_long_trail/compiled",
        "validation": {
            "status": validation_status,
            "checked_artifacts": [
                artifact["relative_path"]
                for artifact in artifacts
                if artifact.get("candidate_present", False)
            ],
            "missing": [],
            "invalid": [],
        },
        "summary": {
            "checked_artifacts": sum(
                1 for artifact in artifacts
                if artifact.get("candidate_present", False)
            ),
            "candidate_present": sum(
                1 for artifact in artifacts
                if artifact.get("candidate_present", False)
            ),
            "promoted_present": sum(
                1 for artifact in artifacts
                if artifact.get("promoted_present", False)
            ),
            "changed": sum(
                1 for artifact in artifacts
                if artifact.get("changed") is True
            ),
            "missing_required": 0,
            "invalid": 0,
        },
        "artifacts": artifacts,
    }


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


def _checklist_by_id(report):
    return {
        item["id"]: item
        for item in report["checklist"]
    }


def _drift_by_path(report):
    return {
        item["relative_path"]: item
        for item in report["artifacts"]
    }


def test_build_candidate_drift_marks_artifact_drift_review_required(tmp_path):
    candidate_root = tmp_path / "trails" / "vermont_long_trail" / "candidate" / "run-1"
    _write_json(
        candidate_root / "candidate_report.json",
        _candidate_report(
            artifacts=[
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
                _artifact(
                    "compiled/segments.geojson",
                    candidate_present=False,
                    promoted_present=True,
                    changed=None,
                ),
                _artifact(
                    "compiled/metadata.json",
                    candidate_present=False,
                    promoted_present=False,
                    changed=None,
                ),
            ],
        ),
    )
    before = _tree_snapshot(
        candidate_root
    )

    drift = build_candidate_drift(
        candidate_root
    )

    assert drift["format"] == "cairnos_build_topo_candidate_drift_v1"
    assert drift["status"] == "review_required"
    assert drift["candidate_root"].endswith(
        "trails/vermont_long_trail/candidate/run-1"
    )
    assert drift["promoted_root"] == "trails/vermont_long_trail/compiled"
    assert drift["candidate_report"] == "candidate_report.json"
    assert drift["container_candidate_plan"] == "container_candidate_plan.json"
    assert drift["summary"] == {
        "artifact_changed": 1,
        "artifact_unchanged": 1,
        "artifact_new": 1,
        "artifact_missing_candidate": 1,
        "artifact_deleted_or_absent_candidate": 1,
        "artifact_review_required": 3,
        "smoke_checked": 0,
        "smoke_matched": 0,
        "smoke_changed": 0,
        "smoke_failed": 0,
        "blockers": 0,
    }

    checklist = _checklist_by_id(
        drift
    )
    assert checklist["candidate_report_present"]["status"] == "pass"
    assert checklist["candidate_validation_passed"]["status"] == "pass"
    assert checklist["artifact_drift_review"]["status"] == "review"
    assert checklist["smoke_drift_review"]["status"] == "review"
    assert "No container_candidate_plan.json" in checklist["smoke_drift_review"]["details"]

    artifacts = _drift_by_path(
        drift
    )
    assert artifacts["compiled/route_overlay.json"]["state"] == "changed"
    assert artifacts["compiled/route_overlay.json"]["review_required"] is True
    assert artifacts["compiled/operational_graph.json"]["state"] == "unchanged"
    assert artifacts["compiled/operational_graph.json"]["review_required"] is False
    assert artifacts["compiled/crossings.geojson"]["state"] == "new"
    assert artifacts["compiled/crossings.geojson"]["review_required"] is True
    assert artifacts["compiled/segments.geojson"]["state"] == "missing_candidate"
    assert artifacts["compiled/segments.geojson"]["review_required"] is True
    assert artifacts["compiled/metadata.json"]["state"] == "deleted_or_absent_candidate"
    assert artifacts["compiled/metadata.json"]["review_required"] is False
    assert drift["smoke_tests"] == []
    assert drift["blockers"] == []
    assert _tree_snapshot(
        candidate_root
    ) == before


def test_build_candidate_drift_marks_no_drift_when_artifacts_unchanged(tmp_path):
    candidate_root = tmp_path / "trails" / "vermont_long_trail" / "candidate" / "run-1"
    _write_json(
        candidate_root / "candidate_report.json",
        _candidate_report(
            artifacts=[
                _artifact(
                    "compiled/route_overlay.json",
                    candidate_present=True,
                    promoted_present=True,
                    changed=False,
                ),
            ],
        ),
    )

    drift = build_candidate_drift(
        candidate_root
    )

    assert drift["status"] == "no_drift"
    assert drift["summary"]["artifact_review_required"] == 0


def test_build_candidate_drift_blocks_missing_candidate_report(tmp_path):
    candidate_root = tmp_path / "trails" / "vermont_long_trail" / "candidate" / "run-1"
    candidate_root.mkdir(
        parents=True,
    )

    drift = build_candidate_drift(
        candidate_root
    )

    assert drift["status"] == "blocked"
    assert drift["artifacts"] == []
    assert drift["summary"]["blockers"] == 1
    checklist = _checklist_by_id(
        drift
    )
    assert checklist["candidate_report_present"]["status"] == "fail"
    assert "candidate_report.json is missing" in checklist["candidate_report_present"]["details"]


def test_build_candidate_drift_blocks_failed_candidate_validation(tmp_path):
    candidate_root = tmp_path / "trails" / "vermont_long_trail" / "candidate" / "run-1"
    _write_json(
        candidate_root / "candidate_report.json",
        _candidate_report(
            validation_status="failed",
            artifacts=[
                _artifact(
                    "compiled/route_overlay.json",
                    candidate_present=True,
                    promoted_present=True,
                    changed=True,
                ),
            ],
        ),
    )

    drift = build_candidate_drift(
        candidate_root
    )

    assert drift["status"] == "blocked"
    assert drift["summary"]["blockers"] == 1
    checklist = _checklist_by_id(
        drift
    )
    assert checklist["candidate_validation_passed"]["status"] == "fail"


def test_write_candidate_drift_report_saves_report(tmp_path):
    candidate_root = tmp_path / "trails" / "vermont_long_trail" / "candidate" / "run-1"
    candidate_root.mkdir(
        parents=True,
    )
    report = {
        "format": "cairnos_build_topo_candidate_drift_v1",
        "status": "no_drift",
    }

    path = write_candidate_drift_report(
        candidate_root,
        report,
    )

    assert path == candidate_root / "candidate_drift_report.json"
    assert json.loads(
        path.read_text(
            encoding="utf-8",
        )
    ) == report
