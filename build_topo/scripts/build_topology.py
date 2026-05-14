# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import subprocess
import sys


#
# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
#

ROOT = Path(__file__).resolve().parents[2]

COMPILER_ROOT = ROOT / "build_topo"


def run_stage(name, module, trail_root):

    print("")
    print(f"=== STAGE: {name} ===")
    print("")

    cmd = [
        sys.executable,
        "-m",
        module,
        str(trail_root),
    ]

    result = subprocess.run(cmd)

    if result.returncode != 0:

        raise RuntimeError(
            f"Stage failed: {name}"
        )


#
# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
#

def main():

    if len(sys.argv) != 2:

        print("")
        print("Usage:")
        print("")
        print(
            "python build_topology.py "
            "trails/vermont_long_trail"
        )
        print("")

        sys.exit(1)

    trail_root = Path(sys.argv[1]).resolve()

    if not trail_root.exists():

        raise FileNotFoundError(
            f"Missing trail root: {trail_root}"
        )

    print("")
    print("=== CairnOSv1 Topology Compiler ===")
    print("")
    print(f"Trail Root: {trail_root}")

    #
    # compiler stages
    #

    stages = [

        (
            "Spine Import",
            "build_topo.compiler.spine",
        ),

        (
            "Terrain Segmentation",
            "build_topo.compiler.segments",
        ),

        (
            "Logistics Nodes",
            "build_topo.compiler.logistics",
        ),

        (
            "Crossing Refinement",
            "build_topo.compiler.crossings",
        ),

        (
            "Route Overlay",
            "build_topo.compiler.route_overlay",
        ),

        (
            "Approach Trails",
            "build_topo.compiler.approach_trails",
        ),

        (
            "Operational Graph",
            "build_topo.compiler.graph",
        ),

        (
            "Schema Registry",
            "build_topo.compiler.schema_registry",
        ),

        (
            "Validation",
            "build_topo.compiler.validation",
        ),
    ]

    #
    # run stages
    #

    for name, module in stages:

        run_stage(
            name,
            module,
            trail_root,
        )

    print("")
    print("=== BUILD COMPLETE ===")
    print("")


if __name__ == "__main__":

    main()
