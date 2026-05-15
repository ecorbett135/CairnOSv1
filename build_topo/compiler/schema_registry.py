# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import sys
import json


#
# ---------------------------------------------------------
# TRAIL ROOT
# ---------------------------------------------------------
#

trail_root = (
    Path(sys.argv[1]).resolve()
    if len(sys.argv) > 1
    else Path(
        "trails/vermont_long_trail"
    ).resolve()
)

RAW_DIR = trail_root / "raw"

COMPILED_DIR = (
    trail_root / "compiled"
)

INTERMEDIATE_DIR = (
    trail_root / "intermediate"
)


#
# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------
#

SCHEMA_VERSION = "1.0"


#
# ---------------------------------------------------------
# SCHEMA REGISTRY
# ---------------------------------------------------------
#

def build_registry():

    registry = {

        "schema_version":
        SCHEMA_VERSION,

        "trail":
        trail_root.name,

        "datasets": {

            "spine": {

                "path":
                "compiled/spine.geojson",

                "type":
                "GeoJSON",

                "description":
                "Canonical trail spine geometry",
            },

            "segments": {

                "path":
                "compiled/segments.geojson",

                "type":
                "GeoJSON",

                "description":
                "Terrain segmentation",
            },

            "crossings": {

                "path":
                "compiled/crossings.geojson",

                "type":
                "GeoJSON",

                "description":
                "Road and trail crossings",
            },

            "crossings_refined": {

                "path":
                "compiled/crossings_refined.geojson",

                "type":
                "GeoJSON",

                "description":
                "Refined operational crossings",
            },

            "logistics_nodes": {

                "path":
                "compiled/logistics_nodes.json",

                "type":
                "JSON",

                "description":
                "Operational logistics nodes",
            },

            "operational_graph": {

                "path":
                "compiled/operational_graph.json",

                "type":
                "JSON",

                "description":
                "Operational traversal graph",
            },
        },
    }

    return registry


#
# ---------------------------------------------------------
# EXPORT
# ---------------------------------------------------------
#

def export_registry(registry):

    output_path = (
        COMPILED_DIR /
        "cairn_schema_registry.json"
    )

    with open(
        output_path,
        "w",
    ) as f:

        json.dump(

            registry,

            f,
            indent=2,
        )

    print("")
    print("[EXPORTING]")
    print("")

    print(
        f"[OK] {output_path}"
    )


#
# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
#

def main():

    print("")
    print(
        "=== CairnOS Schema Registry Builder ==="
    )
    print("")

    registry = build_registry()

    export_registry(registry)

    print("")
    print("[SUMMARY]")
    print("")

    print(
        f"Registered datasets: "
        f"{len(registry['datasets'])}"
    )

    print("")
    print("[DONE]")


if __name__ == "__main__":

    main()