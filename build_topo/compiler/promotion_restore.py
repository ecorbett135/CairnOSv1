# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json
import shutil

from build_topo.compiler.candidates import compute_file_sha256
from build_topo.compiler.provenance import repo_relative_path


RESTORE_FORMAT = "cairnos_build_topo_promotion_restore_v1"
RESTORE_REPORT_NAME = "promotion_restore_report.json"


def _infer_trail_root(snapshot_root):
    snapshot_root = Path(
        snapshot_root
    ).resolve()

    if snapshot_root.parent.name == "promotion_snapshots":
        return snapshot_root.parent.parent

    return snapshot_root.parent


def _valid_snapshot_id(snapshot_id):
    return (
        snapshot_id not in {"", ".", ".."}
        and "/" not in snapshot_id
        and "\\" not in snapshot_id
    )


def _is_snapshot_root(snapshot_root):
    snapshot_root = Path(
        snapshot_root
    )

    return (
        snapshot_root.parent.name == "promotion_snapshots"
        and _valid_snapshot_id(
            snapshot_root.name
        )
    )


def _restore_report_path(snapshot_root):
    return (
        Path(snapshot_root) /
        RESTORE_REPORT_NAME
    )


def _compiled_relative_path(path, compiled_root):
    relative = Path(path).relative_to(
        compiled_root
    )

    return (
        Path("compiled") /
        relative
    ).as_posix()


def _snapshot_restore_items(snapshot_root, trail_root):
    snapshot_compiled = (
        Path(snapshot_root) /
        "compiled"
    )
    restored = []
    blockers = []

    if not snapshot_compiled.is_dir():
        return [], [
            "snapshot compiled directory is missing."
        ]

    for path in sorted(
        snapshot_compiled.rglob("*")
    ):
        if path.is_symlink():
            blockers.append(
                (
                    "snapshot compiled directory contains unsupported "
                    f"symlink: {repo_relative_path(path, trail_root)}"
                )
            )
            continue

        if not path.is_file():
            continue

        relative_path = _compiled_relative_path(
            path,
            snapshot_compiled,
        )
        restored.append(
            {
                "relative_path": relative_path,
                "source_path": path,
                "destination_path": (
                    Path(trail_root) /
                    relative_path
                ),
            }
        )

    return restored, blockers


def _current_only_items(trail_root, restored_items):
    compiled_root = (
        Path(trail_root) /
        "compiled"
    )

    if not compiled_root.exists():
        return []

    restored_paths = {
        item["relative_path"]
        for item in restored_items
    }
    left_unchanged = []

    for path in sorted(
        compiled_root.rglob("*")
    ):
        if not path.is_file():
            continue

        relative_path = _compiled_relative_path(
            path,
            compiled_root,
        )

        if relative_path in restored_paths:
            continue

        left_unchanged.append(
            {
                "relative_path": relative_path,
                "reason": (
                    "current compiled file is not present in snapshot; "
                    "left unchanged"
                ),
            }
        )

    return left_unchanged


def _copy_snapshot_files(restore_items, trail_root):
    restored = []

    for item in restore_items:
        destination = item["destination_path"]
        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        shutil.copy2(
            item["source_path"],
            destination,
        )
        restored.append(
            {
                "relative_path": item["relative_path"],
                "source": repo_relative_path(
                    item["source_path"],
                    trail_root,
                ),
                "destination": repo_relative_path(
                    destination,
                    trail_root,
                ),
                "sha256": compute_file_sha256(
                    destination,
                ),
            }
        )

    return restored


def _verify_restored_hashes(restore_items):
    blockers = []

    for item in restore_items:
        source_hash = compute_file_sha256(
            item["source_path"]
        )
        destination_hash = compute_file_sha256(
            item["destination_path"]
        )

        if source_hash != destination_hash:
            blockers.append(
                (
                    f"{item['relative_path']} restored hash does not "
                    "match snapshot artifact."
                )
            )

    return blockers


def _report(
    *,
    status,
    snapshot_root,
    trail_root,
    dry_run,
    restored=None,
    left_unchanged=None,
    blockers=None,
):
    restored = list(
        restored or []
    )
    left_unchanged = list(
        left_unchanged or []
    )
    blockers = list(
        blockers or []
    )

    return {
        "format": RESTORE_FORMAT,
        "status": status,
        "dry_run": dry_run,
        "promotion_id": Path(snapshot_root).name,
        "snapshot_root": repo_relative_path(
            snapshot_root,
            trail_root,
        ),
        "compiled_root": repo_relative_path(
            Path(trail_root) / "compiled",
            trail_root,
        ),
        "restore_report": RESTORE_REPORT_NAME,
        "summary": {
            "restored": len(
                restored
            ),
            "left_unchanged": len(
                left_unchanged
            ),
        },
        "restored": restored,
        "left_unchanged": left_unchanged,
        "blockers": blockers,
    }


def _write_restore_report(snapshot_root, report):
    path = _restore_report_path(
        snapshot_root
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


def restore_promotion_snapshot(
    snapshot_root,
    *,
    apply=False,
):
    snapshot_root = Path(
        snapshot_root
    ).resolve()
    trail_root = _infer_trail_root(
        snapshot_root
    )
    dry_run = not apply
    blockers = []

    if not _is_snapshot_root(
        snapshot_root
    ):
        blockers.append(
            "snapshot_root must be trails/<trail>/promotion_snapshots/<promotion_id>."
        )

    if not snapshot_root.exists():
        blockers.append(
            (
                "promotion snapshot is missing: "
                f"{repo_relative_path(snapshot_root, trail_root)}"
            )
        )

    if not dry_run and _restore_report_path(
        snapshot_root
    ).exists():
        blockers.append(
            f"{RESTORE_REPORT_NAME} already exists."
        )

    restore_items = []
    left_unchanged = []

    if not blockers:
        restore_items, item_blockers = _snapshot_restore_items(
            snapshot_root,
            trail_root,
        )
        blockers.extend(
            item_blockers
        )
        left_unchanged = _current_only_items(
            trail_root,
            restore_items,
        )

    if blockers:
        return _report(
            status="blocked",
            snapshot_root=snapshot_root,
            trail_root=trail_root,
            dry_run=dry_run,
            left_unchanged=left_unchanged,
            blockers=blockers,
        )

    if dry_run:
        return _report(
            status="ready",
            snapshot_root=snapshot_root,
            trail_root=trail_root,
            dry_run=True,
            restored=[
                {
                    "relative_path": item["relative_path"],
                }
                for item in restore_items
            ],
            left_unchanged=left_unchanged,
        )

    restored = _copy_snapshot_files(
        restore_items,
        trail_root,
    )
    restore_blockers = _verify_restored_hashes(
        restore_items
    )
    status = (
        "blocked"
        if restore_blockers
        else "restored"
    )
    report = _report(
        status=status,
        snapshot_root=snapshot_root,
        trail_root=trail_root,
        dry_run=False,
        restored=restored,
        left_unchanged=left_unchanged,
        blockers=restore_blockers,
    )
    _write_restore_report(
        snapshot_root,
        report,
    )

    return report
