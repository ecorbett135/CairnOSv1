# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import json
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "build_topo" / "scripts" / "examine_candidate_drift.py"


def _write_json(path, payload):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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


def _candidate_report(artifacts=None):
    artifacts = list(
        artifacts
        if artifacts is not None
        else []
    )

    return {
        "format": "cairnos_build_topo_candidate_report_v1",
        "candidate_root": "trails/vermont_long_trail/candidate/run-1",
        "promoted_root": "trails/vermont_long_trail/compiled",
        "validation": {
            "status": "passed",
            "checked_artifacts": [
                artifact["relative_path"]
                for artifact in artifacts
                if artifact.get("candidate_present", False)
            ],
            "missing": [],
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
            "missing_required": 0,
            "invalid": 0,
        },
        "artifacts": artifacts,
    }


def _tree_snapshot(root):
    if not root.exists():
        return {}

    return {
        path.relative_to(root).as_posix(): path.read_text(
            encoding="utf-8",
        )
        for path in sorted(
            root.glob("**/*")
        )
        if path.is_file()
    }


def _write_demo_candidate(candidate_root):
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
            ],
        ),
    )


class _ResponseHandler(BaseHTTPRequestHandler):
    responses = {}

    def do_GET(self):
        response = self.responses.get(
            self.path,
            {
                "status": 404,
                "body": b"not found",
                "content_type": "text/plain",
            },
        )
        body = response["body"]

        if not isinstance(body, bytes):
            body = json.dumps(
                body,
            ).encode(
                "utf-8",
            )

        self.send_response(
            response["status"]
        )
        self.send_header(
            "Content-Type",
            response.get(
                "content_type",
                "application/json",
            ),
        )
        self.end_headers()
        self.wfile.write(
            body
        )

    def log_message(self, *args):
        return


def _server(responses):
    class Handler(_ResponseHandler):
        pass

    Handler.responses = responses
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        Handler,
    )
    thread = Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()

    return server


def _write_container_plan(candidate_root, baseline_url, candidate_url):
    _write_json(
        candidate_root / "container_candidate_plan.json",
        {
            "format": "cairnos_build_topo_container_candidate_plan_v1",
            "smoke_tests": [
                {
                    "path": "/same-json",
                    "baseline_url": baseline_url + "/same-json",
                    "candidate_url": candidate_url + "/same-json",
                },
                {
                    "path": "/changed-body",
                    "baseline_url": baseline_url + "/changed-body",
                    "candidate_url": candidate_url + "/changed-body",
                },
                {
                    "path": "/changed-status",
                    "baseline_url": baseline_url + "/changed-status",
                    "candidate_url": candidate_url + "/changed-status",
                },
            ],
        },
    )


def test_examine_candidate_drift_cli_prints_human_report_without_mutation(tmp_path):
    trail_root = tmp_path / "trails" / "vermont_long_trail"
    candidate_root = trail_root / "candidate" / "run-1"
    _write_demo_candidate(
        candidate_root
    )
    before = _tree_snapshot(
        trail_root
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(candidate_root),
            "--skip-smoke",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Candidate drift: review_required" in result.stdout
    assert "artifact_changed: 1" in result.stdout
    assert "artifact_unchanged: 1" in result.stdout
    assert "compiled/route_overlay.json changed" in result.stdout
    assert "compiled/operational_graph.json unchanged" in result.stdout
    assert _tree_snapshot(
        trail_root
    ) == before


def test_examine_candidate_drift_cli_json_and_save(tmp_path):
    candidate_root = tmp_path / "trails" / "vermont_long_trail" / "candidate" / "run-1"
    _write_demo_candidate(
        candidate_root
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(candidate_root),
            "--skip-smoke",
            "--json",
            "--save",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    report = json.loads(
        result.stdout
    )
    saved_path = candidate_root / "candidate_drift_report.json"
    assert saved_path.exists()
    assert json.loads(
        saved_path.read_text(
            encoding="utf-8",
        )
    ) == report
    assert report["status"] == "review_required"


def test_examine_candidate_drift_cli_blocks_missing_report(tmp_path):
    candidate_root = tmp_path / "trails" / "vermont_long_trail" / "candidate" / "run-1"
    candidate_root.mkdir(
        parents=True,
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(candidate_root),
            "--skip-smoke",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Candidate drift: blocked" in result.stdout
    assert "candidate_report.json is missing" in result.stdout


def test_examine_candidate_drift_cli_compares_smoke_endpoints(tmp_path):
    baseline = _server(
        {
            "/same-json": {
                "status": 200,
                "body": {
                    "status": "ok",
                    "checks": {
                        "planner": "ok",
                    },
                },
            },
            "/changed-body": {
                "status": 200,
                "body": {
                    "daily_plan_count": 29,
                },
            },
            "/changed-status": {
                "status": 200,
                "body": {
                    "status": "ok",
                },
            },
        }
    )
    candidate = _server(
        {
            "/same-json": {
                "status": 200,
                "body": {
                    "checks": {
                        "planner": "ok",
                    },
                    "status": "ok",
                },
            },
            "/changed-body": {
                "status": 200,
                "body": {
                    "daily_plan_count": 30,
                },
            },
            "/changed-status": {
                "status": 503,
                "body": {
                    "status": "warming",
                },
            },
        }
    )

    try:
        candidate_root = tmp_path / "trails" / "vermont_long_trail" / "candidate" / "run-1"
        _write_demo_candidate(
            candidate_root
        )
        _write_container_plan(
            candidate_root,
            f"http://127.0.0.1:{baseline.server_port}",
            f"http://127.0.0.1:{candidate.server_port}",
        )

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                str(candidate_root),
                "--json",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        baseline.shutdown()
        candidate.shutdown()

    assert result.returncode == 0
    report = json.loads(
        result.stdout
    )
    smoke_by_path = {
        item["path"]: item
        for item in report["smoke_tests"]
    }
    assert smoke_by_path["/same-json"]["status"] == "matched"
    assert smoke_by_path["/changed-body"]["status"] == "changed"
    assert smoke_by_path["/changed-status"]["status"] == "changed"
    assert report["summary"]["smoke_checked"] == 3
    assert report["summary"]["smoke_matched"] == 1
    assert report["summary"]["smoke_changed"] == 2
    assert report["summary"]["smoke_failed"] == 0
