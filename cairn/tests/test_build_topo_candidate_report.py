# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import json

from build_topo.compiler.candidate_report import (
    build_candidate_report,
    write_candidate_report,
)
from build_topo.compiler.candidates import compute_file_sha256
from build_topo.compiler.contracts import ArtifactContract


def _write_json(path, payload):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(payload) + "\n",
        encoding="utf-8",
    )


def test_build_candidate_report_summarizes_candidate_against_promoted(tmp_path):
    trail_root = tmp_path / "trails" / "vermont_long_trail"
    candidate_root = trail_root / "candidate" / "run-1"

    _write_json(
        trail_root / "compiled" / "route_overlay.json",
        {
            "route": [
                "promoted",
            ],
        },
    )
    _write_json(
        candidate_root / "compiled" / "route_overlay.json",
        {
            "route": [
                "candidate",
            ],
        },
    )
    _write_json(
        candidate_root / "compiled" / "spine.geojson",
        {
            "type": "FeatureCollection",
            "features": [],
        },
    )

    report = build_candidate_report(
        candidate_root,
        trail_root,
        artifacts=[
            ArtifactContract("compiled/route_overlay.json", "json"),
            ArtifactContract("compiled/spine.geojson", "geojson"),
            ArtifactContract("compiled/missing.json", "json"),
        ],
    )

    assert report["validation"]["status"] == "failed"
    assert report["candidate_root"] == "trails/vermont_long_trail/candidate/run-1"
    assert report["promoted_root"] == "trails/vermont_long_trail/compiled"
    assert report["summary"] == {
        "checked_artifacts": 2,
        "candidate_present": 2,
        "promoted_present": 1,
        "changed": 1,
        "missing_required": 1,
        "invalid": 0,
    }

    artifacts_by_path = {
        artifact["relative_path"]: artifact
        for artifact in report["artifacts"]
    }

    route_overlay = artifacts_by_path["compiled/route_overlay.json"]
    assert route_overlay["candidate_present"] is True
    assert route_overlay["promoted_present"] is True
    assert route_overlay["changed"] is True
    assert route_overlay["candidate"]["sha256"] == compute_file_sha256(
        candidate_root / "compiled" / "route_overlay.json"
    )
    assert route_overlay["promoted"]["sha256"] == compute_file_sha256(
        trail_root / "compiled" / "route_overlay.json"
    )

    spine = artifacts_by_path["compiled/spine.geojson"]
    assert spine["candidate_present"] is True
    assert spine["promoted_present"] is False
    assert spine["changed"] is None

    missing = artifacts_by_path["compiled/missing.json"]
    assert missing["candidate_present"] is False
    assert missing["promoted_present"] is False
    assert missing["changed"] is None

    assert not (
        candidate_root /
        "candidate_report.json"
    ).exists()


def test_write_candidate_report_saves_report(tmp_path):
    candidate_root = tmp_path / "trails" / "vermont_long_trail" / "candidate" / "run-1"
    candidate_root.mkdir(
        parents=True,
    )
    report = {
        "status": "passed",
        "summary": {},
        "artifacts": [],
    }

    path = write_candidate_report(
        candidate_root,
        report,
    )

    assert path == candidate_root / "candidate_report.json"
    assert json.loads(
        path.read_text(
            encoding="utf-8",
        )
    ) == report
