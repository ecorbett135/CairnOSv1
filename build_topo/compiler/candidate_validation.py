# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json

from build_topo.compiler.contracts import get_expected_artifacts


VALID_GEOJSON_TYPES = {
    "FeatureCollection",
    "Feature",
    "LineString",
    "MultiLineString",
    "Point",
    "MultiPoint",
    "Polygon",
    "MultiPolygon",
    "GeometryCollection",
}


def _load_json(path):
    with open(path, encoding="utf-8") as file_obj:
        return json.load(
            file_obj
        )


def _validate_json(path):
    _load_json(
        path
    )


def _validate_geojson(path):
    payload = _load_json(
        path
    )

    geojson_type = payload.get(
        "type"
    )

    if geojson_type not in VALID_GEOJSON_TYPES:
        raise ValueError(
            f"invalid geojson type: {geojson_type}"
        )


def _validate_artifact(path, artifact_type):
    if artifact_type == "json":
        _validate_json(
            path
        )
        return

    if artifact_type == "geojson":
        _validate_geojson(
            path
        )
        return

    raise ValueError(
        f"unsupported artifact type: {artifact_type}"
    )


def validate_candidate_artifacts(candidate_root, artifacts=None):
    candidate_root = Path(
        candidate_root
    )

    artifacts = tuple(
        artifacts
        if artifacts is not None
        else get_expected_artifacts()
    )

    checked = []
    missing = []
    invalid = []

    for artifact in artifacts:
        path = (
            candidate_root /
            artifact.relative_path
        )

        if not path.exists():
            if artifact.required:
                missing.append(
                    artifact.relative_path
                )
            continue

        checked.append(
            artifact.relative_path
        )

        try:
            _validate_artifact(
                path,
                artifact.artifact_type,
            )
        except (json.JSONDecodeError, ValueError) as exc:
            invalid.append(
                {
                    "path": artifact.relative_path,
                    "reason": (
                        f"invalid json: {exc}"
                        if artifact.artifact_type == "json"
                        else str(exc)
                    ),
                }
            )

    status = (
        "failed"
        if missing or invalid
        else "passed"
    )

    return {
        "status": status,
        "checked_artifacts": checked,
        "missing": missing,
        "invalid": invalid,
    }


def write_candidate_validation_report(candidate_root, report):
    path = (
        Path(candidate_root) /
        "candidate_validation.json"
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
