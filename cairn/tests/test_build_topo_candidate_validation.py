# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import json

from build_topo.compiler.candidate_validation import (
    validate_candidate_artifacts,
    write_candidate_validation_report,
)
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


def test_validate_candidate_artifacts_passes_for_required_json_and_geojson(
    tmp_path,
):
    candidate_root = tmp_path / "candidate" / "run"
    _write_json(
        candidate_root / "compiled" / "route_overlay.json",
        {
            "route": [],
        },
    )
    _write_json(
        candidate_root / "compiled" / "spine.geojson",
        {
            "type": "FeatureCollection",
            "features": [],
        },
    )

    report = validate_candidate_artifacts(
        candidate_root,
        artifacts=[
            ArtifactContract("compiled/route_overlay.json", "json"),
            ArtifactContract("compiled/spine.geojson", "geojson"),
        ],
    )

    assert report == {
        "status": "passed",
        "checked_artifacts": [
            "compiled/route_overlay.json",
            "compiled/spine.geojson",
        ],
        "missing": [],
        "invalid": [],
    }


def test_validate_candidate_artifacts_reports_missing_required_files(tmp_path):
    report = validate_candidate_artifacts(
        tmp_path / "candidate" / "run",
        artifacts=[
            ArtifactContract("compiled/route_overlay.json", "json"),
        ],
    )

    assert report["status"] == "failed"
    assert report["missing"] == [
        "compiled/route_overlay.json",
    ]
    assert report["invalid"] == []


def test_validate_candidate_artifacts_ignores_missing_optional_files(tmp_path):
    report = validate_candidate_artifacts(
        tmp_path / "candidate" / "run",
        artifacts=[
            ArtifactContract(
                "compiled/overnight_reference.json",
                "json",
                required=False,
            ),
        ],
    )

    assert report == {
        "status": "passed",
        "checked_artifacts": [],
        "missing": [],
        "invalid": [],
    }


def test_validate_candidate_artifacts_reports_invalid_json(tmp_path):
    path = tmp_path / "candidate" / "run" / "compiled" / "route_overlay.json"
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        "{broken",
        encoding="utf-8",
    )

    report = validate_candidate_artifacts(
        tmp_path / "candidate" / "run",
        artifacts=[
            ArtifactContract("compiled/route_overlay.json", "json"),
        ],
    )

    assert report["status"] == "failed"
    assert report["missing"] == []
    assert report["invalid"][0]["path"] == "compiled/route_overlay.json"
    assert report["invalid"][0]["reason"].startswith("invalid json:")


def test_validate_candidate_artifacts_reports_invalid_geojson_shape(tmp_path):
    _write_json(
        tmp_path / "candidate" / "run" / "compiled" / "spine.geojson",
        {
            "type": "NotGeoJSON",
        },
    )

    report = validate_candidate_artifacts(
        tmp_path / "candidate" / "run",
        artifacts=[
            ArtifactContract("compiled/spine.geojson", "geojson"),
        ],
    )

    assert report["status"] == "failed"
    assert report["invalid"] == [
        {
            "path": "compiled/spine.geojson",
            "reason": "invalid geojson type: NotGeoJSON",
        }
    ]


def test_write_candidate_validation_report_saves_report(tmp_path):
    candidate_root = tmp_path / "candidate" / "run"
    candidate_root.mkdir(
        parents=True,
    )
    report = {
        "status": "passed",
        "checked_artifacts": [],
        "missing": [],
        "invalid": [],
    }

    path = write_candidate_validation_report(
        candidate_root,
        report,
    )

    assert path == candidate_root / "candidate_validation.json"
    assert json.loads(
        path.read_text(
            encoding="utf-8",
        )
    ) == report
