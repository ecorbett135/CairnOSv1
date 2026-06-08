# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json

from build_topo.compiler.provenance import repo_relative_path


DRIFT_REPORT_FORMAT = "cairnos_build_topo_candidate_drift_v1"
REPORT_FORMAT = "cairnos_build_topo_candidate_report_v1"
CONTAINER_PLAN_NAME = "container_candidate_plan.json"


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


def _container_candidate_plan_path(candidate_root):
    return (
        Path(candidate_root) /
        CONTAINER_PLAN_NAME
    )


def _load_json(path):
    try:
        return json.loads(
            path.read_text(
                encoding="utf-8",
            )
        ), None
    except FileNotFoundError:
        return None, "missing"
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


def _artifact_review_required(state):
    return state in {
        "changed",
        "new",
        "missing_candidate",
    }


def _drift_artifacts(report):
    artifacts = []

    for artifact in report.get(
        "artifacts",
        [],
    ):
        state = _artifact_state(
            artifact
        )
        artifacts.append(
            {
                "relative_path": artifact["relative_path"],
                "artifact_type": artifact.get(
                    "artifact_type"
                ),
                "required": artifact.get(
                    "required",
                    True,
                ),
                "state": state,
                "review_required": _artifact_review_required(
                    state
                ),
                "candidate": artifact.get(
                    "candidate"
                ),
                "promoted": artifact.get(
                    "promoted"
                ),
            }
        )

    return artifacts


def _artifact_summary(artifacts):
    counts = {
        "artifact_changed": 0,
        "artifact_unchanged": 0,
        "artifact_new": 0,
        "artifact_missing_candidate": 0,
        "artifact_deleted_or_absent_candidate": 0,
        "artifact_review_required": 0,
    }

    state_to_key = {
        "changed": "artifact_changed",
        "unchanged": "artifact_unchanged",
        "new": "artifact_new",
        "missing_candidate": "artifact_missing_candidate",
        "deleted_or_absent_candidate": "artifact_deleted_or_absent_candidate",
    }

    for artifact in artifacts:
        counts[
            state_to_key[
                artifact["state"]
            ]
        ] += 1

        if artifact["review_required"]:
            counts["artifact_review_required"] += 1

    return counts


def _check(status, item_id, label, details):
    return {
        "id": item_id,
        "status": status,
        "label": label,
        "details": details,
    }


def _blocked_report(candidate_root, trail_root, details):
    checklist = [
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
            "review",
            "artifact_drift_review",
            "Review candidate-vs-promoted artifact drift",
            "Artifact drift cannot be summarized without candidate report evidence.",
        ),
        _check(
            "review",
            "smoke_drift_review",
            "Review baseline-vs-candidate smoke drift",
            "Smoke drift cannot be summarized without candidate report evidence.",
        ),
    ]

    return {
        "format": DRIFT_REPORT_FORMAT,
        "status": "blocked",
        "candidate_root": _candidate_root_label(
            candidate_root,
            trail_root,
        ),
        "candidate_report": "candidate_report.json",
        "container_candidate_plan": CONTAINER_PLAN_NAME,
        "summary": _summary(
            [],
            [],
            blockers=1,
        ),
        "checklist": checklist,
        "artifacts": [],
        "smoke_tests": [],
        "blockers": [
            details,
        ],
        "next_steps": [
            "Run build_topo/scripts/validate_candidate.py before examining drift.",
        ],
    }


def _smoke_tests_from_plan(plan):
    if plan is None:
        return []

    return [
        {
            "path": item.get(
                "path"
            ),
            "status": "unavailable",
            "baseline_url": item.get(
                "baseline_url"
            ),
            "candidate_url": item.get(
                "candidate_url"
            ),
            "matched": None,
            "reason": "smoke probing was not requested",
        }
        for item in plan.get(
            "smoke_tests",
            [],
        )
    ]


def _smoke_summary(smoke_tests):
    return {
        "smoke_checked": sum(
            1 for item in smoke_tests
            if item.get("status") in {"matched", "changed", "failed"}
        ),
        "smoke_matched": sum(
            1 for item in smoke_tests
            if item.get("status") == "matched"
        ),
        "smoke_changed": sum(
            1 for item in smoke_tests
            if item.get("status") == "changed"
        ),
        "smoke_failed": sum(
            1 for item in smoke_tests
            if item.get("status") == "failed"
        ),
    }


def _summary(artifacts, smoke_tests, blockers=0):
    return {
        **_artifact_summary(
            artifacts
        ),
        **_smoke_summary(
            smoke_tests
        ),
        "blockers": blockers,
    }


def _checklist(report, artifacts, smoke_tests, plan_present, blockers):
    validation = report.get(
        "validation",
        {},
    )
    validation_status = validation.get(
        "status"
    )
    artifact_review_required = sum(
        1 for artifact in artifacts
        if artifact["review_required"]
    )
    smoke_checked = _smoke_summary(
        smoke_tests
    )["smoke_checked"]

    return [
        _check(
            "pass",
            "candidate_report_present",
            "Candidate report evidence exists",
            "candidate_report.json was found and parsed.",
        ),
        _check(
            "pass" if validation_status == "passed" else "fail",
            "candidate_validation_passed",
            "Candidate validation passed",
            (
                "Candidate validation status is passed."
                if validation_status == "passed"
                else f"Candidate validation status is {validation_status}."
            ),
        ),
        _check(
            "review",
            "artifact_drift_review",
            "Review candidate-vs-promoted artifact drift",
            (
                f"{artifact_review_required} artifact drift item(s) need review."
            ),
        ),
        _check(
            "review",
            "smoke_drift_review",
            "Review baseline-vs-candidate smoke drift",
            (
                f"{smoke_checked} smoke endpoint(s) were checked."
                if plan_present
                else (
                    "No container_candidate_plan.json was found; "
                    "smoke drift is unavailable."
                )
            ),
        ),
        _check(
            "review",
            "manual_review_only",
            "Promote only after human review",
            "This command never copies artifacts into compiled/.",
        ),
    ]


def _status(artifacts, smoke_tests, blockers):
    if blockers:
        return "blocked"

    if any(
        artifact["review_required"]
        for artifact in artifacts
    ):
        return "review_required"

    if any(
        item.get("status") == "changed"
        for item in smoke_tests
    ):
        return "review_required"

    return "no_drift"


def _next_steps(status):
    if status == "blocked":
        return [
            "Resolve blocked candidate evidence before drift review.",
        ]

    if status == "review_required":
        return [
            "Review changed, new, and missing candidate drift before promotion.",
            "Confirm drift is expected before promoting any image or artifact set.",
        ]

    return [
        "No deterministic drift was detected in available evidence.",
    ]


def build_candidate_drift(candidate_root, smoke_tests=None):
    candidate_root = Path(
        candidate_root
    ).resolve()
    trail_root = _infer_trail_root(
        candidate_root
    )
    report, report_error = _load_json(
        _candidate_report_path(
            candidate_root
        )
    )

    if report is None:
        details = (
            f"candidate_report.json could not be parsed: {report_error}"
            if report_error != "missing"
            else "candidate_report.json is missing."
        )
        return _blocked_report(
            candidate_root,
            trail_root,
            details,
        )

    artifacts = _drift_artifacts(
        report
    )
    plan, _plan_error = _load_json(
        _container_candidate_plan_path(
            candidate_root
        )
    )
    smoke_tests = (
        list(smoke_tests)
        if smoke_tests is not None
        else _smoke_tests_from_plan(
            plan
        )
    )
    blockers = []
    validation_status = report.get(
        "validation",
        {},
    ).get(
        "status"
    )

    if validation_status != "passed":
        blockers.append(
            f"candidate validation status is {validation_status}"
        )

    status = _status(
        artifacts,
        smoke_tests,
        blockers,
    )

    return {
        "format": DRIFT_REPORT_FORMAT,
        "status": status,
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
        "container_candidate_plan": CONTAINER_PLAN_NAME,
        "summary": _summary(
            artifacts,
            smoke_tests,
            blockers=len(
                blockers
            ),
        ),
        "checklist": _checklist(
            report,
            artifacts,
            smoke_tests,
            plan is not None,
            blockers,
        ),
        "artifacts": artifacts,
        "smoke_tests": smoke_tests,
        "blockers": blockers,
        "next_steps": _next_steps(
            status
        ),
    }


def write_candidate_drift_report(candidate_root, report):
    path = (
        Path(candidate_root) /
        "candidate_drift_report.json"
    )

    path.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    return path
