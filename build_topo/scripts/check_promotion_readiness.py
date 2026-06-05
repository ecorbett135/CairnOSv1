#!/usr/bin/env python3
# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import argparse
import sys


ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )

from build_topo.compiler.promotion_readiness import (  # noqa: E402
    build_promotion_readiness,
)


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description=(
            "Print a build_topo candidate promotion readiness checklist "
            "without mutating promoted compiled artifacts."
        )
    )
    parser.add_argument(
        "candidate_root",
        help="Path to trails/<trail>/candidate/<run_id>",
    )

    return parser.parse_args(
        argv
    )


def _print_checklist(readiness):
    print(
        "Checklist:"
    )

    for item in readiness["checklist"]:
        print(
            f"[{item['status']}] {item['label']}"
        )
        print(
            f"  {item['details']}"
        )


def _print_summary(readiness):
    print(
        "Artifact diff summary:"
    )

    for key in (
        "changed",
        "unchanged",
        "new",
        "missing_candidate",
        "deleted_or_absent_candidate",
        "review_required",
    ):
        print(
            f"{key}: {readiness['summary'][key]}"
        )


def _print_artifacts(readiness):
    if not readiness["artifacts"]:
        return

    print(
        "Artifacts:"
    )

    for artifact in readiness["artifacts"]:
        print(
            f"- {artifact['relative_path']} {artifact['state']}"
        )


def print_readiness(readiness):
    print(
        f"Promotion readiness: {readiness['status']}"
    )
    print(
        f"Candidate: {readiness['candidate_root']}"
    )

    if "promoted_root" in readiness:
        print(
            f"Promoted: {readiness['promoted_root']}"
        )

    print(
        f"Candidate report: {readiness['candidate_report']}"
    )
    print()

    _print_checklist(
        readiness
    )
    print()
    _print_summary(
        readiness
    )
    print()
    _print_artifacts(
        readiness
    )


def main(argv=None):
    args = parse_args(
        argv if argv is not None else sys.argv[1:]
    )

    readiness = build_promotion_readiness(
        args.candidate_root
    )
    print_readiness(
        readiness
    )

    return (
        0
        if readiness["status"] == "ready"
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
