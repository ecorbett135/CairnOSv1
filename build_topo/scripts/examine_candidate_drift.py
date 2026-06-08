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

from build_topo.compiler.candidate_drift import (  # noqa: E402
    build_candidate_drift,
    write_candidate_drift_report,
)


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description=(
            "Examine deterministic build_topo candidate drift without "
            "promoting artifacts or images."
        )
    )
    parser.add_argument(
        "candidate_root",
        help="Path to trails/<trail>/candidate/<run_id>",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of human-readable output.",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Write candidate_drift_report.json inside the candidate root.",
    )
    parser.add_argument(
        "--skip-smoke",
        action="store_true",
        help=(
            "Do not probe baseline/candidate smoke URLs from "
            "container_candidate_plan.json."
        ),
    )

    return parser.parse_args(
        argv
    )


def _print_checklist(report):
    print(
        "Checklist:"
    )

    for item in report["checklist"]:
        print(
            f"[{item['status']}] {item['label']}"
        )
        print(
            f"  {item['details']}"
        )


def _print_summary(report):
    print(
        "Summary:"
    )

    for key in (
        "artifact_changed",
        "artifact_unchanged",
        "artifact_new",
        "artifact_missing_candidate",
        "artifact_deleted_or_absent_candidate",
        "artifact_review_required",
        "smoke_checked",
        "smoke_matched",
        "smoke_changed",
        "smoke_failed",
        "blockers",
    ):
        print(
            f"{key}: {report['summary'][key]}"
        )


def _print_artifacts(report):
    if not report["artifacts"]:
        return

    print(
        "Artifacts:"
    )

    for artifact in report["artifacts"]:
        print(
            f"- {artifact['relative_path']} {artifact['state']}"
        )


def _print_smoke_tests(report):
    if not report["smoke_tests"]:
        return

    print(
        "Smoke tests:"
    )

    for smoke_test in report["smoke_tests"]:
        print(
            f"- {smoke_test['path']} {smoke_test['status']}"
        )
        print(
            f"  {smoke_test['reason']}"
        )


def print_human_report(report):
    print(
        f"Candidate drift: {report['status']}"
    )
    print(
        f"Candidate: {report['candidate_root']}"
    )

    if "promoted_root" in report:
        print(
            f"Promoted: {report['promoted_root']}"
        )

    print(
        f"Candidate report: {report['candidate_report']}"
    )
    print(
        f"Container candidate plan: {report['container_candidate_plan']}"
    )
    print()

    _print_checklist(
        report
    )
    print()
    _print_summary(
        report
    )
    print()
    _print_artifacts(
        report
    )
    print()
    _print_smoke_tests(
        report
    )


def main(argv=None):
    args = parse_args(
        argv if argv is not None else sys.argv[1:]
    )
    candidate_root = Path(
        args.candidate_root
    )
    report = build_candidate_drift(
        candidate_root,
        probe_smoke=not args.skip_smoke,
    )

    if args.save:
        write_candidate_drift_report(
            candidate_root,
            report,
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

    return (
        1
        if report["status"] == "blocked"
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
