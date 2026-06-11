# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import json

from build_topo.compiler.promotion_restore import (
    restore_promotion_snapshot,
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


def _demo_snapshot(tmp_path):
    trail_root = tmp_path / "trails" / "vermont_long_trail"
    snapshot_root = trail_root / "promotion_snapshots" / "promo-1"

    _write_text(
        snapshot_root / "compiled" / "route_overlay.json",
        "snapshot route\n",
    )
    _write_text(
        snapshot_root / "compiled" / "operational_graph.json",
        "snapshot graph\n",
    )
    _write_text(
        trail_root / "compiled" / "route_overlay.json",
        "current route\n",
    )
    _write_text(
        trail_root / "compiled" / "operational_graph.json",
        "current graph\n",
    )
    _write_text(
        trail_root / "compiled" / "crossings.geojson",
        "current-only crossing\n",
    )
    _write_text(
        trail_root / "candidate" / "run-1" / "candidate_report.json",
        "candidate evidence\n",
    )

    return trail_root, snapshot_root


def test_restore_promotion_snapshot_dry_run_reports_without_mutating(tmp_path):
    trail_root, snapshot_root = _demo_snapshot(
        tmp_path
    )
    before = _tree_snapshot(
        trail_root
    )

    report = restore_promotion_snapshot(
        snapshot_root,
    )

    assert report["status"] == "ready"
    assert report["dry_run"] is True
    assert report["summary"] == {
        "restored": 2,
        "left_unchanged": 1,
    }
    assert [item["relative_path"] for item in report["restored"]] == [
        "compiled/operational_graph.json",
        "compiled/route_overlay.json",
    ]
    assert report["left_unchanged"] == [
        {
            "relative_path": "compiled/crossings.geojson",
            "reason": (
                "current compiled file is not present in snapshot; "
                "left unchanged"
            ),
        }
    ]
    assert not (
        snapshot_root / "promotion_restore_report.json"
    ).exists()
    assert _tree_snapshot(
        trail_root
    ) == before


def test_restore_promotion_snapshot_apply_restores_snapshot_files_only(tmp_path):
    trail_root, snapshot_root = _demo_snapshot(
        tmp_path
    )

    report = restore_promotion_snapshot(
        snapshot_root,
        apply=True,
    )

    restore_report = snapshot_root / "promotion_restore_report.json"

    assert report["status"] == "restored"
    assert report["dry_run"] is False
    assert (
        trail_root / "compiled" / "route_overlay.json"
    ).read_text(encoding="utf-8") == "snapshot route\n"
    assert (
        trail_root / "compiled" / "operational_graph.json"
    ).read_text(encoding="utf-8") == "snapshot graph\n"
    assert (
        trail_root / "compiled" / "crossings.geojson"
    ).read_text(encoding="utf-8") == "current-only crossing\n"
    assert (
        trail_root / "candidate" / "run-1" / "candidate_report.json"
    ).read_text(encoding="utf-8") == "candidate evidence\n"
    assert restore_report.exists()
    assert json.loads(
        restore_report.read_text(
            encoding="utf-8",
        )
    ) == report


def test_restore_promotion_snapshot_blocks_invalid_snapshot_root(tmp_path):
    trail_root, snapshot_root = _demo_snapshot(
        tmp_path
    )
    invalid_root = trail_root / "candidate" / "run-1"
    before = _tree_snapshot(
        trail_root
    )

    report = restore_promotion_snapshot(
        invalid_root,
        apply=True,
    )

    assert report["status"] == "blocked"
    assert (
        "snapshot_root must be trails/<trail>/promotion_snapshots/<promotion_id>."
        in report["blockers"]
    )
    assert not (
        snapshot_root / "promotion_restore_report.json"
    ).exists()
    assert _tree_snapshot(
        trail_root
    ) == before


def test_restore_promotion_snapshot_blocks_existing_restore_report(tmp_path):
    trail_root, snapshot_root = _demo_snapshot(
        tmp_path
    )
    _write_text(
        snapshot_root / "promotion_restore_report.json",
        "{}\n",
    )
    before = _tree_snapshot(
        trail_root
    )

    report = restore_promotion_snapshot(
        snapshot_root,
        apply=True,
    )

    assert report["status"] == "blocked"
    assert "promotion_restore_report.json already exists." in report[
        "blockers"
    ]
    assert _tree_snapshot(
        trail_root
    ) == before
