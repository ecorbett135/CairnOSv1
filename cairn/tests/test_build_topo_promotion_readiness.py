# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import json

from build_topo.compiler.promotion_readiness import build_promotion_readiness


def _write_json(path, payload):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _candidate_report(validation_status="passed", artifacts=None):
    artifacts = list(
        artifacts
        if artifacts is not None
        else []
    )
    missing = [
        artifact["relative_path"]
        for artifact in artifacts
        if artifact.get("required", True)
        and not artifact.get("candidate_present", False)
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
                if artifact.get("candidate_present", False)
            ],
            "missing": missing,
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
            "missing_required": len(
                missing
            ),
            "invalid": 0,
        },
        "artifacts": artifacts,
    }


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


def _checklist_by_id(readiness):
    return {
        item["id"]: item
        for item in readiness["checklist"]
    }


def test_build_promotion_readiness_marks_valid_candidate_ready(tmp_path):
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
            ],
        ),
    )

    readiness = build_promotion_readiness(
        candidate_root
    )

    assert readiness["status"] == "ready"
    assert readiness["summary"] == {
        "changed": 1,
        "unchanged": 1,
        "new": 1,
        "missing_candidate": 0,
        "deleted_or_absent_candidate": 0,
        "review_required": 3,
    }

    checklist = _checklist_by_id(
        readiness
    )
    assert checklist["candidate_report_present"]["status"] == "pass"
    assert checklist["candidate_validation_passed"]["status"] == "pass"
    assert checklist["required_artifacts_present"]["status"] == "pass"
    assert checklist["candidate_artifacts_valid"]["status"] == "pass"
    assert checklist["review_artifact_diffs"]["status"] == "review"
    assert checklist["preserve_promoted_snapshot"]["status"] == "review"
    assert checklist["manual_promotion_only"]["status"] == "review"

    states_by_path = {
        artifact["relative_path"]: artifact["state"]
        for artifact in readiness["artifacts"]
    }
    assert states_by_path == {
        "compiled/route_overlay.json": "changed",
        "compiled/operational_graph.json": "unchanged",
        "compiled/crossings.geojson": "new",
    }


def test_build_promotion_readiness_marks_failed_candidate_not_ready(tmp_path):
    candidate_root = tmp_path / "trails" / "vermont_long_trail" / "candidate" / "run-1"
    _write_json(
        candidate_root / "candidate_report.json",
        _candidate_report(
            validation_status="failed",
            artifacts=[
                _artifact(
                    "compiled/route_overlay.json",
                    candidate_present=False,
                    promoted_present=True,
                    changed=None,
                ),
            ],
        ),
    )

    readiness = build_promotion_readiness(
        candidate_root
    )

    assert readiness["status"] == "not_ready"
    checklist = _checklist_by_id(
        readiness
    )
    assert checklist["candidate_validation_passed"]["status"] == "fail"
    assert checklist["required_artifacts_present"]["status"] == "fail"
    assert readiness["summary"]["missing_candidate"] == 1


def test_build_promotion_readiness_handles_missing_candidate_report(tmp_path):
    candidate_root = tmp_path / "trails" / "vermont_long_trail" / "candidate" / "run-1"
    candidate_root.mkdir(
        parents=True,
    )

    readiness = build_promotion_readiness(
        candidate_root
    )

    assert readiness["status"] == "not_ready"
    assert readiness["candidate_root"].endswith(
        "trails/vermont_long_trail/candidate/run-1"
    )
    assert readiness["artifacts"] == []
    checklist = _checklist_by_id(
        readiness
    )
    assert checklist["candidate_report_present"]["status"] == "fail"
    assert "validate_candidate.py" in checklist["candidate_report_present"]["details"]
