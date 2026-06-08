#!/usr/bin/env python3
# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from datetime import datetime, timezone
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

from build_topo.compiler.candidates import candidate_root_for_run  # noqa: E402
from build_topo.compiler.container_candidate import (  # noqa: E402
    DEFAULT_BASELINE_PORT,
    DEFAULT_CANDIDATE_PORT,
    DEFAULT_SMOKE_PATHS,
    build_container_candidate_plan,
    write_container_candidate_plan,
)


def _default_run_id():
    return (
        datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") +
        "-container-candidate"
    )


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description=(
            "Create a non-mutating build_topo container candidate run and "
            "save its deterministic planning evidence."
        )
    )
    parser.add_argument(
        "--trail-root",
        default="trails/vermont_long_trail",
        help="Trail root containing compiled/ and candidate/ directories.",
    )
    parser.add_argument(
        "--run-id",
        help=(
            "Candidate run directory name. Defaults to a UTC timestamp ending "
            "in -container-candidate."
        ),
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

    return parser.parse_args(
        argv
    )


def main(argv=None):
    args = parse_args(
        argv if argv is not None else sys.argv[1:]
    )
    run_id = (
        args.run_id
        if args.run_id
        else _default_run_id()
    )

    try:
        candidate_root = candidate_root_for_run(
            Path(args.trail_root).resolve(),
            run_id,
        )
    except ValueError as error:
        print(
            str(error),
            file=sys.stderr,
        )
        return 2

    if candidate_root.exists():
        print(
            f"candidate run already exists: {candidate_root}",
            file=sys.stderr,
        )
        return 1

    candidate_root.mkdir(
        parents=True,
        exist_ok=False,
    )

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
    plan["run_id"] = run_id

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

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
