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

from build_topo.compiler.candidate_report import (  # noqa: E402
    build_candidate_report,
    write_candidate_report,
)
from build_topo.compiler.candidate_validation import (  # noqa: E402
    write_candidate_validation_report,
)


def infer_trail_root(candidate_root):
    candidate_root = Path(
        candidate_root
    ).resolve()

    if candidate_root.parent.name != "candidate":
        raise ValueError(
            "Cannot infer trail root: candidate root must be under "
            "trails/<trail>/candidate/<run_id>"
        )

    return candidate_root.parent.parent


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description=(
            "Validate a build_topo candidate artifact directory and write "
            "review evidence without mutating promoted compiled artifacts."
        )
    )
    parser.add_argument(
        "candidate_root",
        help="Path to trails/<trail>/candidate/<run_id>",
    )
    parser.add_argument(
        "--trail-root",
        help=(
            "Path to trails/<trail>. If omitted, inferred from "
            "candidate_root."
        ),
    )

    return parser.parse_args(
        argv
    )


def main(argv=None):
    args = parse_args(
        argv if argv is not None else sys.argv[1:]
    )

    candidate_root = Path(
        args.candidate_root
    ).resolve()

    trail_root = (
        Path(args.trail_root).resolve()
        if args.trail_root
        else infer_trail_root(candidate_root)
    )

    report = build_candidate_report(
        candidate_root,
        trail_root,
    )

    write_candidate_validation_report(
        candidate_root,
        report["validation"],
    )
    write_candidate_report(
        candidate_root,
        report,
    )

    print(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if report["validation"]["status"] == "passed"
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
