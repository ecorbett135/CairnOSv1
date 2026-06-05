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

from build_topo.compiler.container_candidate import (  # noqa: E402
    DEFAULT_BASELINE_PORT,
    DEFAULT_CANDIDATE_PORT,
    DEFAULT_SMOKE_PATHS,
    build_container_candidate_plan,
    write_container_candidate_plan,
)


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description=(
            "Create a read-only build_topo container candidate plan for "
            "side-by-side image testing before manual image promotion."
        )
    )
    parser.add_argument(
        "candidate_root",
        help="Path to trails/<trail>/candidate/<run_id>",
    )
    parser.add_argument(
        "--candidate-image",
        required=True,
        help="Candidate image tag, for example cairnos-plan-api:candidate.",
    )
    parser.add_argument(
        "--candidate-digest",
        help="Immutable candidate image digest to consider for promotion.",
    )
    parser.add_argument(
        "--baseline-image",
        default="cairnos-plan-api:baseline",
        help="Baseline image tag to compare against.",
    )
    parser.add_argument(
        "--baseline-digest",
        help="Immutable baseline image digest, when known.",
    )
    parser.add_argument(
        "--candidate-port",
        type=int,
        default=DEFAULT_CANDIDATE_PORT,
        help="Local host port for the candidate image.",
    )
    parser.add_argument(
        "--baseline-port",
        type=int,
        default=DEFAULT_BASELINE_PORT,
        help="Local host port for the baseline image.",
    )
    parser.add_argument(
        "--smoke-path",
        action="append",
        dest="smoke_paths",
        help=(
            "Smoke endpoint path. May be repeated. Defaults to "
            f"{', '.join(DEFAULT_SMOKE_PATHS)}."
        ),
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Write container_candidate_plan.json inside the candidate root.",
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

    plan = build_container_candidate_plan(
        candidate_root,
        candidate_image=args.candidate_image,
        candidate_digest=args.candidate_digest,
        baseline_image=args.baseline_image,
        baseline_digest=args.baseline_digest,
        candidate_port=args.candidate_port,
        baseline_port=args.baseline_port,
        smoke_paths=args.smoke_paths,
    )

    if args.save:
        write_container_candidate_plan(
            candidate_root,
            plan,
        )

    print(
        json.dumps(
            plan,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if plan["status"] == "ready"
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
