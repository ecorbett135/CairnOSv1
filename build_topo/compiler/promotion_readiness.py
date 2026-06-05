# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json

from build_topo.compiler.provenance import repo_relative_path


READINESS_FORMAT = "cairnos_build_topo_promotion_readiness_v1"
REPORT_FORMAT = "cairnos_build_topo_candidate_report_v1"


def _infer_trail_root(candidate_root):
    candidate_root = Path(
        candidate_root
    ).resolve()

    if candidate_root.parent.name == "candidate":
        return candidate_root.parent.parent

    return candidate_root.parent


def _candidate_root_label(candidate_root, trail_root):
    return repo_relative_path(
        candidate_root,
        trail_root,
    )


def _candidate_report_path(candidate_root):
    return (
        Path(candidate_root) /
        "candidate_report.json"
    )


def _load_candidate_report(candidate_root):
    path = _candidate_report_path(
        candidate_root
    )

    if not path.exists():
        return None, None

    try:
        return json.loads(
            path.read_text(
                encoding="utf-8",
            )
        ), None
    except json.JSONDecodeError as exc:
        return None, str(exc)


def _artifact_state(artifact):
    candidate_present = artifact.get(
        "candidate_present",
        False,
    )
    promoted_present = artifact.get(
        "promoted_present",
        False,
    )
    changed = artifact.get(
        "changed"
    )

    if candidate_present and promoted_present:
        return (
            "changed"
            if changed is True
            else "unchanged"
        )

    if candidate_present and not promoted_present:
        return "new"

    if not candidate_present and promoted_present:
        return "missing_candidate"

    return "deleted_or_absent_candidate"


def _readiness_artifacts(report):
    return [
        {
            "relative_path": artifact["relative_path"],
            "artifact_type": artifact.get(
                "artifact_type"
            ),
            "required": artifact.get(
                "required",
                True,
            ),
            "candidate_present": artifact.get(
                "candidate_present",
                False,
            ),
            "promoted_present": artifact.get(
                "promoted_present",
                False,
            ),
            "changed": artifact.get(
                "changed"
            ),
            "state": _artifact_state(
                artifact
            ),
        }
        for artifact in report.get(
            "artifacts",
            [],
        )
    ]


def _summary(artifacts):
    state_counts = {
        "changed": 0,
        "unchanged": 0,
        "new": 0,
        "missing_candidate": 0,
        "deleted_or_absent_candidate": 0,
    }

    for artifact in artifacts:
        state_counts[artifact["state"]] += 1

    state_counts["review_required"] = sum(
        state_counts.values()
    )

    return state_counts


def _check(status, item_id, label, details):
    return {
        "id": item_id,
        "status": status,
        "label": label,
        "details": details,
    }


def _missing_report_checklist(error=None):
    details = (
        f"candidate_report.json could not be parsed: {error}"
        if error
        else (
            "candidate_report.json is missing. Run "
            "build_topo/scripts/validate_candidate.py first."
        )
    )

    return [
        _check(
            "fail",
            "candidate_report_present",
            "Candidate report evidence exists",
            details,
        ),
        _check(
            "fail",
            "candidate_validation_passed",
            "Candidate validation passed",
            "Validation status cannot be checked without candidate report evidence.",
        ),
        _check(
            "fail",
            "required_artifacts_present",
            "Required candidate artifacts are present",
            "Required artifact presence cannot be checked without candidate report evidence.",
        ),
        _check(
            "fail",
            "candidate_artifacts_valid",
            "Candidate artifacts parsed successfully",
            "Artifact parse validity cannot be checked without candidate report evidence.",
        ),
        _check(
            "fail",
            "review_artifact_diffs",
            "Review candidate-vs-promoted artifact diffs",
            "Artifact diffs cannot be summarized without candidate report evidence.",
        ),
        _check(
            "review",
            "preserve_promoted_snapshot",
            "Preserve promoted compiled snapshot before copying",
            "Manual promotion must keep the existing compiled artifacts recoverable.",
        ),
        _check(
            "review",
            "manual_promotion_only",
            "Promote manually after review",
            "This readiness command never copies files into compiled/.",
        ),
    ]


def _checklist(report, artifacts):
    validation = report.get(
        "validation",
        {},
    )
    report_summary = report.get(
        "summary",
        {},
    )
    validation_passed = validation.get(
        "status"
    ) == "passed"
    missing_required = int(
        report_summary.get(
            "missing_required",
            0,
        )
    )
    invalid = int(
        report_summary.get(
            "invalid",
            0,
        )
    )
    artifact_summary = _summary(
        artifacts
    )

    return [
        _check(
            "pass",
            "candidate_report_present",
            "Candidate report evidence exists",
            "candidate_report.json was found and parsed.",
        ),
        _check(
            "pass" if validation_passed else "fail",
            "candidate_validation_passed",
            "Candidate validation passed",
            (
                "Candidate validation status is passed."
                if validation_passed
                else f"Candidate validation status is {validation.get('status')}."
            ),
        ),
        _check(
            "pass" if missing_required == 0 else "fail",
            "required_artifacts_present",
            "Required candidate artifacts are present",
            (
                "No required artifacts are missing."
                if missing_required == 0
                else f"{missing_required} required artifact(s) are missing."
            ),
        ),
        _check(
            "pass" if invalid == 0 else "fail",
            "candidate_artifacts_valid",
            "Candidate artifacts parsed successfully",
            (
                "No invalid artifacts were reported."
                if invalid == 0
                else f"{invalid} invalid artifact(s) were reported."
            ),
        ),
        _check(
            "review",
            "review_artifact_diffs",
            "Review candidate-vs-promoted artifact diffs",
            (
                f"{artifact_summary['review_required']} artifact(s) need "
                "human review before promotion."
            ),
        ),
        _check(
            "review",
            "preserve_promoted_snapshot",
            "Preserve promoted compiled snapshot before copying",
            "Manual promotion must keep the existing compiled artifacts recoverable.",
        ),
        _check(
            "review",
            "manual_promotion_only",
            "Promote manually after review",
            "This readiness command never copies files into compiled/.",
        ),
    ]


def _has_blocking_failure(checklist):
    return any(
        item["status"] == "fail"
        for item in checklist
    )


def build_promotion_readiness(candidate_root):
    candidate_root = Path(
        candidate_root
    ).resolve()
    trail_root = _infer_trail_root(
        candidate_root
    )
    report, report_error = _load_candidate_report(
        candidate_root
    )

    if report is None:
        checklist = _missing_report_checklist(
            report_error,
        )
        return {
            "format": READINESS_FORMAT,
            "status": "not_ready",
            "candidate_root": _candidate_root_label(
                candidate_root,
                trail_root,
            ),
            "candidate_report": _candidate_report_path(
                candidate_root
            ).name,
            "summary": _summary(
                []
            ),
            "checklist": checklist,
            "artifacts": [],
        }

    artifacts = _readiness_artifacts(
        report
    )
    checklist = _checklist(
        report,
        artifacts,
    )

    return {
        "format": READINESS_FORMAT,
        "status": (
            "not_ready"
            if _has_blocking_failure(checklist)
            else "ready"
        ),
        "candidate_root": report.get(
            "candidate_root",
            _candidate_root_label(
                candidate_root,
                trail_root,
            ),
        ),
        "promoted_root": report.get(
            "promoted_root",
            repo_relative_path(
                trail_root / "compiled",
                trail_root,
            ),
        ),
        "candidate_report": _candidate_report_path(
            candidate_root
        ).name,
        "candidate_report_format": report.get(
            "format",
            REPORT_FORMAT,
        ),
        "summary": _summary(
            artifacts
        ),
        "checklist": checklist,
        "artifacts": artifacts,
    }
