# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import json

from build_topo.compiler.container_candidate import (
    build_container_candidate_plan,
    write_container_candidate_plan,
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


def _promotion_readiness(status="ready"):
    return {
        "format": "cairnos_build_topo_promotion_readiness_v1",
        "status": status,
        "candidate_root": "trails/vermont_long_trail/candidate/run-1",
        "promoted_root": "trails/vermont_long_trail/compiled",
        "candidate_report": "candidate_report.json",
        "summary": {
            "changed": 1,
            "unchanged": 1,
            "new": 0,
            "missing_candidate": 0,
            "deleted_or_absent_candidate": 0,
            "review_required": 2,
        },
        "checklist": [
            {
                "id": "candidate_report_present",
                "status": "pass",
                "label": "Candidate report evidence exists",
                "details": "candidate_report.json was found and parsed.",
            },
            {
                "id": "candidate_validation_passed",
                "status": (
                    "pass"
                    if status == "ready"
                    else "fail"
                ),
                "label": "Candidate validation passed",
                "details": "Candidate validation status.",
            },
        ],
        "artifacts": [
            {
                "relative_path": "compiled/route_overlay.json",
                "state": "changed",
            },
            {
                "relative_path": "compiled/operational_graph.json",
                "state": "unchanged",
            },
        ],
    }


def _compiled_snapshot(trail_root):
    return {
        path.relative_to(trail_root).as_posix(): path.read_text(
            encoding="utf-8",
        )
        for path in sorted(
            (trail_root / "compiled").glob("**/*")
        )
        if path.is_file()
    }


def test_build_container_candidate_plan_records_image_identity_and_smoke_tests(
    tmp_path,
):
    trail_root = tmp_path / "trails" / "vermont_long_trail"
    candidate_root = trail_root / "candidate" / "run-1"
    _write_json(
        candidate_root / "candidate_report.json",
        {
            "format": "cairnos_build_topo_candidate_report_v1",
        },
    )
    readiness = _promotion_readiness()

    plan = build_container_candidate_plan(
        candidate_root,
        candidate_image="cairnos-plan-api:candidate",
        candidate_digest="sha256:candidate123",
        baseline_image="cairnos-plan-api:baseline",
        baseline_digest="sha256:baseline456",
        candidate_port=3011,
        baseline_port=3010,
        smoke_paths=[
            "/health",
            "/ready",
            "/version",
            "/metrics",
            "/plan",
        ],
        readiness=readiness,
    )

    assert plan["format"] == "cairnos_build_topo_container_candidate_plan_v1"
    assert plan["status"] == "ready"
    assert plan["candidate_root"] == "trails/vermont_long_trail/candidate/run-1"
    assert plan["artifact_output_root"] == (
        "trails/vermont_long_trail/candidate/run-1"
    )
    assert plan["candidate_image"] == {
        "image": "cairnos-plan-api:candidate",
        "digest": "sha256:candidate123",
        "port": 3011,
        "base_url": "http://127.0.0.1:3011",
    }
    assert plan["baseline_image"] == {
        "image": "cairnos-plan-api:baseline",
        "digest": "sha256:baseline456",
        "port": 3010,
        "base_url": "http://127.0.0.1:3010",
    }
    assert plan["promotion_target"] == {
        "type": "image_digest",
        "digest": "sha256:candidate123",
        "image": "cairnos-plan-api:candidate",
    }
    assert plan["smoke_tests"] == [
        {
            "path": "/health",
            "baseline_url": "http://127.0.0.1:3010/health",
            "candidate_url": "http://127.0.0.1:3011/health",
        },
        {
            "path": "/ready",
            "baseline_url": "http://127.0.0.1:3010/ready",
            "candidate_url": "http://127.0.0.1:3011/ready",
        },
        {
            "path": "/version",
            "baseline_url": "http://127.0.0.1:3010/version",
            "candidate_url": "http://127.0.0.1:3011/version",
        },
        {
            "path": "/metrics",
            "baseline_url": "http://127.0.0.1:3010/metrics",
            "candidate_url": "http://127.0.0.1:3011/metrics",
        },
        {
            "path": "/plan",
            "baseline_url": "http://127.0.0.1:3010/plan",
            "candidate_url": "http://127.0.0.1:3011/plan",
        },
    ]
    assert plan["blockers"] == []
    assert plan["readiness"]["status"] == "ready"
    assert plan["commands"]["candidate"].startswith(
        "docker run --rm -p 3011:8080"
    )
    assert "sha256:candidate123" in plan["commands"]["candidate"]
    assert "docker run --rm -p 3010:8080" in plan["commands"]["baseline"]
    assert "Promote image digest sha256:candidate123" in plan["next_steps"][0]


def test_build_container_candidate_plan_blocks_missing_digest_or_readiness(tmp_path):
    candidate_root = tmp_path / "trails" / "vermont_long_trail" / "candidate" / "run-1"
    candidate_root.mkdir(
        parents=True,
    )
    readiness = _promotion_readiness(
        status="not_ready",
    )

    plan = build_container_candidate_plan(
        candidate_root,
        candidate_image="cairnos-plan-api:candidate",
        baseline_image="cairnos-plan-api:baseline",
        readiness=readiness,
    )

    assert plan["status"] == "blocked"
    assert plan["promotion_target"]["digest"] is None
    assert plan["blockers"] == [
        "candidate image digest is required before promotion planning",
        "candidate artifact readiness status is not_ready",
    ]


def test_write_container_candidate_plan_saves_only_inside_candidate_root(tmp_path):
    trail_root = tmp_path / "trails" / "vermont_long_trail"
    candidate_root = trail_root / "candidate" / "run-1"
    _write_json(
        trail_root / "compiled" / "route_overlay.json",
        {
            "marker": "promoted",
        },
    )
    before = _compiled_snapshot(
        trail_root
    )
    plan = build_container_candidate_plan(
        candidate_root,
        candidate_image="cairnos-plan-api:candidate",
        candidate_digest="sha256:candidate123",
        readiness=_promotion_readiness(),
    )

    path = write_container_candidate_plan(
        candidate_root,
        plan,
    )

    assert path == candidate_root / "container_candidate_plan.json"
    assert json.loads(
        path.read_text(
            encoding="utf-8",
        )
    ) == plan
    assert _compiled_snapshot(
        trail_root
    ) == before
