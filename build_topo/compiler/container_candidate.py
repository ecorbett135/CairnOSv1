# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json

from build_topo.compiler.promotion_readiness import build_promotion_readiness
from build_topo.compiler.provenance import repo_relative_path


CONTAINER_PLAN_FORMAT = "cairnos_build_topo_container_candidate_plan_v1"
DEFAULT_BASELINE_PORT = 3010
DEFAULT_CANDIDATE_PORT = 3011
DEFAULT_CONTAINER_PORT = 8080
DEFAULT_SMOKE_PATHS = (
    "/health",
    "/ready",
    "/version",
    "/metrics",
    "/plan",
)


def _infer_trail_root(candidate_root):
    candidate_root = Path(
        candidate_root
    ).resolve()

    if candidate_root.parent.name == "candidate":
        return candidate_root.parent.parent

    return candidate_root.parent


def _base_url(port):
    return f"http://127.0.0.1:{port}"


def _normalize_path(path):
    path = str(
        path
    )

    return (
        path
        if path.startswith("/")
        else f"/{path}"
    )


def _url_for(base_url, path):
    return (
        base_url.rstrip("/") +
        _normalize_path(
            path
        )
    )


def _image_spec(image, digest, port):
    return {
        "image": image,
        "digest": digest,
        "port": port,
        "base_url": _base_url(
            port
        ),
    }


def _smoke_tests(baseline_port, candidate_port, smoke_paths):
    baseline_url = _base_url(
        baseline_port
    )
    candidate_url = _base_url(
        candidate_port
    )

    return [
        {
            "path": _normalize_path(
                path
            ),
            "baseline_url": _url_for(
                baseline_url,
                path,
            ),
            "candidate_url": _url_for(
                candidate_url,
                path,
            ),
        }
        for path in smoke_paths
    ]


def _docker_reference(image, digest):
    return (
        digest
        if digest
        else image
    )


def _docker_run_command(image, digest, host_port):
    reference = _docker_reference(
        image,
        digest,
    )

    return (
        f"docker run --rm -p {host_port}:{DEFAULT_CONTAINER_PORT} "
        f"{reference}"
    )


def _blockers(candidate_digest, readiness):
    blockers = []

    if not candidate_digest:
        blockers.append(
            "candidate image digest is required before promotion planning"
        )

    readiness_status = readiness.get(
        "status"
    )

    if readiness_status != "ready":
        blockers.append(
            f"candidate artifact readiness status is {readiness_status}"
        )

    return blockers


def _next_steps(candidate_digest):
    if candidate_digest:
        promote_line = f"Promote image digest {candidate_digest} only after smoke tests pass."
    else:
        promote_line = "Resolve candidate image digest before any image promotion."

    return [
        promote_line,
        "Run baseline and candidate containers on separate ports.",
        "Compare smoke endpoint responses and timing.",
        "Keep artifact promotion separate from image promotion.",
    ]


def build_container_candidate_plan(
    candidate_root,
    candidate_image,
    candidate_digest=None,
    baseline_image=None,
    baseline_digest=None,
    candidate_port=DEFAULT_CANDIDATE_PORT,
    baseline_port=DEFAULT_BASELINE_PORT,
    smoke_paths=None,
    readiness=None,
):
    candidate_root = Path(
        candidate_root
    ).resolve()
    trail_root = _infer_trail_root(
        candidate_root
    )
    smoke_paths = tuple(
        smoke_paths
        if smoke_paths is not None
        else DEFAULT_SMOKE_PATHS
    )
    readiness = (
        readiness
        if readiness is not None
        else build_promotion_readiness(
            candidate_root
        )
    )
    baseline_image = (
        baseline_image
        if baseline_image
        else "cairnos-plan-api:baseline"
    )
    blockers = _blockers(
        candidate_digest,
        readiness,
    )

    return {
        "format": CONTAINER_PLAN_FORMAT,
        "status": (
            "blocked"
            if blockers
            else "ready"
        ),
        "candidate_root": readiness.get(
            "candidate_root",
            repo_relative_path(
                candidate_root,
                trail_root,
            ),
        ),
        "artifact_output_root": repo_relative_path(
            candidate_root,
            trail_root,
        ),
        "candidate_image": _image_spec(
            candidate_image,
            candidate_digest,
            candidate_port,
        ),
        "baseline_image": _image_spec(
            baseline_image,
            baseline_digest,
            baseline_port,
        ),
        "promotion_target": {
            "type": "image_digest",
            "digest": candidate_digest,
            "image": candidate_image,
        },
        "smoke_tests": _smoke_tests(
            baseline_port,
            candidate_port,
            smoke_paths,
        ),
        "commands": {
            "baseline": _docker_run_command(
                baseline_image,
                baseline_digest,
                baseline_port,
            ),
            "candidate": _docker_run_command(
                candidate_image,
                candidate_digest,
                candidate_port,
            ),
        },
        "blockers": blockers,
        "readiness": readiness,
        "next_steps": _next_steps(
            candidate_digest,
        ),
    }


def write_container_candidate_plan(candidate_root, plan):
    path = (
        Path(candidate_root) /
        "container_candidate_plan.json"
    )
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(
            plan,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    return path
