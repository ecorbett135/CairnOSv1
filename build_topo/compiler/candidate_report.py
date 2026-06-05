# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json

from build_topo.compiler.candidate_validation import validate_candidate_artifacts
from build_topo.compiler.candidates import compute_file_sha256
from build_topo.compiler.contracts import get_expected_artifacts
from build_topo.compiler.provenance import repo_relative_path


def _artifact_file_summary(path):
    path = Path(
        path
    )

    if not path.exists():
        return None

    return {
        "bytes": path.stat().st_size,
        "sha256": compute_file_sha256(
            path
        ),
    }


def _artifact_changed(candidate_summary, promoted_summary):
    if candidate_summary is None or promoted_summary is None:
        return None

    return (
        candidate_summary["sha256"] !=
        promoted_summary["sha256"]
    )


def _artifact_report(candidate_root, trail_root, artifact):
    candidate_path = (
        candidate_root /
        artifact.relative_path
    )
    promoted_path = (
        trail_root /
        artifact.relative_path
    )

    candidate_summary = _artifact_file_summary(
        candidate_path
    )
    promoted_summary = _artifact_file_summary(
        promoted_path
    )

    return {
        "relative_path": artifact.relative_path,
        "artifact_type": artifact.artifact_type,
        "required": artifact.required,
        "candidate_present": candidate_summary is not None,
        "promoted_present": promoted_summary is not None,
        "changed": _artifact_changed(
            candidate_summary,
            promoted_summary,
        ),
        "candidate": candidate_summary,
        "promoted": promoted_summary,
    }


def _report_summary(validation, artifact_reports):
    return {
        "checked_artifacts": len(
            validation["checked_artifacts"]
        ),
        "candidate_present": sum(
            1 for artifact in artifact_reports
            if artifact["candidate_present"]
        ),
        "promoted_present": sum(
            1 for artifact in artifact_reports
            if artifact["promoted_present"]
        ),
        "changed": sum(
            1 for artifact in artifact_reports
            if artifact["changed"] is True
        ),
        "missing_required": len(
            validation["missing"]
        ),
        "invalid": len(
            validation["invalid"]
        ),
    }


def build_candidate_report(candidate_root, trail_root, artifacts=None):
    candidate_root = Path(
        candidate_root
    )
    trail_root = Path(
        trail_root
    )

    artifacts = tuple(
        artifacts
        if artifacts is not None
        else get_expected_artifacts()
    )

    validation = validate_candidate_artifacts(
        candidate_root,
        artifacts=artifacts,
    )

    artifact_reports = [
        _artifact_report(
            candidate_root,
            trail_root,
            artifact,
        )
        for artifact in artifacts
    ]

    return {
        "format": "cairnos_build_topo_candidate_report_v1",
        "candidate_root": repo_relative_path(
            candidate_root,
            trail_root,
        ),
        "promoted_root": repo_relative_path(
            trail_root / "compiled",
            trail_root,
        ),
        "validation": validation,
        "summary": _report_summary(
            validation,
            artifact_reports,
        ),
        "artifacts": artifact_reports,
    }


def write_candidate_report(candidate_root, report):
    path = (
        Path(candidate_root) /
        "candidate_report.json"
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
