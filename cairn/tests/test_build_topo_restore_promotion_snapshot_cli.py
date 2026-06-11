# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    REPO_ROOT /
    "build_topo" /
    "scripts" /
    "restore_promotion_snapshot.py"
)


def _write_text(path, text):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        text,
        encoding="utf-8",
    )


def _tree_snapshot(root):
    return {
        path.relative_to(root).as_posix(): path.read_text(
            encoding="utf-8",
        )
        for path in sorted(
            root.glob("**/*")
        )
        if path.is_file()
    }


def _demo_snapshot(tmp_path):
    trail_root = tmp_path / "trails" / "vermont_long_trail"
    snapshot_root = trail_root / "promotion_snapshots" / "promo-1"

    _write_text(
        snapshot_root / "compiled" / "route_overlay.json",
        "snapshot route\n",
    )
    _write_text(
        trail_root / "compiled" / "route_overlay.json",
        "current route\n",
    )
    _write_text(
        trail_root / "compiled" / "crossings.geojson",
        "current-only crossing\n",
    )

    return trail_root, snapshot_root


def test_restore_promotion_snapshot_cli_dry_run_by_default(tmp_path):
    trail_root, snapshot_root = _demo_snapshot(
        tmp_path
    )
    before = _tree_snapshot(
        trail_root
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(snapshot_root),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Promotion snapshot restore: ready" in result.stdout
    assert "restored: 1" in result.stdout
    assert "left_unchanged: 1" in result.stdout
    assert not (
        snapshot_root / "promotion_restore_report.json"
    ).exists()
    assert _tree_snapshot(
        trail_root
    ) == before


def test_restore_promotion_snapshot_cli_apply_restores_and_writes_report(
    tmp_path,
):
    trail_root, snapshot_root = _demo_snapshot(
        tmp_path
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(snapshot_root),
            "--apply",
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(
        result.stdout
    )
    assert payload["status"] == "restored"
    assert payload["dry_run"] is False
    assert (
        trail_root / "compiled" / "route_overlay.json"
    ).read_text(encoding="utf-8") == "snapshot route\n"
    assert (
        trail_root / "compiled" / "crossings.geojson"
    ).read_text(encoding="utf-8") == "current-only crossing\n"
    assert (
        snapshot_root / "promotion_restore_report.json"
    ).exists()
