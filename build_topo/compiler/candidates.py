# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import hashlib
import json

from build_topo.compiler.provenance import repo_relative_path


def candidate_root_for_run(trail_root, run_id):
    run_id = str(
        run_id
    )

    if run_id in {"", ".", ".."}:
        raise ValueError(
            "Candidate run_id must be a non-empty directory name"
        )

    if "/" in run_id or "\\" in run_id:
        raise ValueError(
            "Candidate run_id cannot contain path separators"
        )

    return (
        Path(trail_root) /
        "candidate" /
        run_id
    )


def ensure_candidate_root(trail_root, run_id):
    root = candidate_root_for_run(
        trail_root,
        run_id,
    )

    root.mkdir(
        parents=True,
        exist_ok=True,
    )

    return root


def candidate_manifest_path(candidate_root):
    return (
        Path(candidate_root) /
        "candidate_manifest.json"
    )


def compute_file_sha256(path):
    digest = hashlib.sha256()

    with open(path, "rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(
                chunk
            )

    return digest.hexdigest()


def _candidate_relative_path(candidate_root, artifact_path):
    return (
        Path(artifact_path)
        .resolve()
        .relative_to(Path(candidate_root).resolve())
        .as_posix()
    )


def _artifact_manifest_entry(candidate_root, trail_root, artifact_path):
    artifact_path = Path(
        artifact_path
    )

    return {
        "path": repo_relative_path(
            artifact_path,
            trail_root,
        ),
        "candidate_relative_path": _candidate_relative_path(
            candidate_root,
            artifact_path,
        ),
        "sha256": compute_file_sha256(
            artifact_path,
        ),
        "bytes": artifact_path.stat().st_size,
    }


def write_candidate_manifest(
    candidate_root,
    trail_root,
    run_id,
    artifacts,
    command_args,
    stage_names,
    git_commit,
    validation_status,
    warnings=None,
):
    candidate_root = Path(
        candidate_root
    )
    trail_root = Path(
        trail_root
    )

    manifest = {
        "trail_id": trail_root.name,
        "run_id": str(run_id),
        "git_commit": str(git_commit),
        "command_args": list(command_args),
        "stage_names": list(stage_names),
        "artifact_root": repo_relative_path(
            candidate_root,
            trail_root,
        ),
        "promoted_root": repo_relative_path(
            trail_root / "compiled",
            trail_root,
        ),
        "validation_status": str(validation_status),
        "warnings": list(warnings or []),
        "artifacts": [
            _artifact_manifest_entry(
                candidate_root,
                trail_root,
                artifact,
            )
            for artifact in artifacts
        ],
    }

    path = candidate_manifest_path(
        candidate_root
    )

    path.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    return manifest
