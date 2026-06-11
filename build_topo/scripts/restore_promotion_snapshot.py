#!/usr/bin/env python3
# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import argparse
import json
import sys


ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )

from build_topo.compiler.promotion_restore import (  # noqa: E402
    restore_promotion_snapshot,
)


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description=(
            "Restore files from a build_topo promotion snapshot back into "
            "compiled/. Dry-run is the default; pass --apply to mutate files."
        )
    )
    parser.add_argument(
        "snapshot_root",
        help="Path to trails/<trail>/promotion_snapshots/<promotion_id>",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Copy snapshot files back into compiled/ and write a restore report.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of human-readable output.",
    )

    return parser.parse_args(
        argv
    )


def _print_summary(report):
    print(
        "Summary:"
    )

    for key in (
        "restored",
        "left_unchanged",
    ):
        print(
            f"{key}: {report['summary'][key]}"
        )


def _print_blockers(report):
    if not report["blockers"]:
        return

    print(
        "Blockers:"
    )

    for blocker in report["blockers"]:
        print(
            f"- {blocker}"
        )


def _print_restored(report):
    if not report["restored"]:
        return

    print(
        "Restored:"
    )

    for item in report["restored"]:
        print(
            f"- {item['relative_path']}"
        )


def _print_left_unchanged(report):
    if not report["left_unchanged"]:
        return

    print(
        "Left unchanged:"
    )

    for item in report["left_unchanged"]:
        print(
            f"- {item['relative_path']} ({item['reason']})"
        )


def print_human_report(report):
    print(
        f"Promotion snapshot restore: {report['status']}"
    )
    print(
        f"Snapshot: {report['snapshot_root']}"
    )
    print(
        f"Compiled: {report['compiled_root']}"
    )
    print(
        f"Restore report: {report['restore_report']}"
    )
    print()

    _print_summary(
        report
    )
    print()
    _print_blockers(
        report
    )
    print()
    _print_restored(
        report
    )
    print()
    _print_left_unchanged(
        report
    )


def _exit_code(report):
    if report["status"] in {"restored", "ready"}:
        return 0

    if any(
        (
            "snapshot_root must be "
            "trails/<trail>/promotion_snapshots/<promotion_id>"
        ) in blocker
        for blocker in report["blockers"]
    ):
        return 2

    return 1


def main(argv=None):
    args = parse_args(
        argv if argv is not None else sys.argv[1:]
    )
    report = restore_promotion_snapshot(
        args.snapshot_root,
        apply=args.apply,
    )

    if args.json:
        print(
            json.dumps(
                report,
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print_human_report(
            report
        )

    return _exit_code(
        report
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
