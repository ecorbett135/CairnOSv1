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

from build_topo.compiler.candidate_promotion import (  # noqa: E402
    promote_candidate_artifacts,
)


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description=(
            "Promote an approved build_topo candidate artifact set into "
            "compiled/ after deterministic readiness and drift review."
        )
    )
    parser.add_argument(
        "candidate_root",
        help="Path to trails/<trail>/candidate/<run_id>",
    )
    parser.add_argument(
        "--accept-drift",
        action="store_true",
        help=(
            "Confirm deterministic drift has been reviewed and accepted."
        ),
    )
    parser.add_argument(
        "--promotion-id",
        help=(
            "Stable promotion id used for the snapshot directory. Defaults "
            "to a UTC timestamp plus candidate run id."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the promotion plan without copying or writing reports.",
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
        "copied",
        "skipped",
        "snapshotted",
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


def _print_copied(report):
    if not report["copied"]:
        return

    print(
        "Copied:"
    )

    for item in report["copied"]:
        print(
            f"- {item['relative_path']}"
        )


def _print_skipped(report):
    if not report["skipped"]:
        return

    print(
        "Skipped:"
    )

    for item in report["skipped"]:
        print(
            f"- {item['relative_path']} ({item['reason']})"
        )


def print_human_report(report):
    print(
        f"Candidate promotion: {report['status']}"
    )
    print(
        f"Candidate: {report['candidate_root']}"
    )
    print(
        f"Promoted: {report['promoted_root']}"
    )
    print(
        f"Snapshot: {report['snapshot_root']}"
    )
    print(
        f"Candidate report: {report['candidate_report']}"
    )
    print(
        f"Candidate drift report: {report['candidate_drift_report']}"
    )
    print(
        f"Promotion report: {report['promotion_report']}"
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
    _print_copied(
        report
    )
    print()
    _print_skipped(
        report
    )


def _exit_code(report):
    if report["status"] in {"promoted", "ready"}:
        return 0

    if any(
        "candidate_root must be trails/<trail>/candidate/<run_id>" in blocker
        for blocker in report["blockers"]
    ):
        return 2

    return 1


def main(argv=None):
    args = parse_args(
        argv if argv is not None else sys.argv[1:]
    )
    report = promote_candidate_artifacts(
        args.candidate_root,
        promotion_id=args.promotion_id,
        accept_drift=args.accept_drift,
        dry_run=args.dry_run,
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
