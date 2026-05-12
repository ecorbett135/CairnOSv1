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

REQUIRED_FILES = [

    "spine.geojson",

    "segments.geojson",

    "crossings.geojson",

    "crossings_refined.geojson",

    "logistics_nodes.json",

    "route_overlay.json",

    "approach_trails.json",

    "operational_graph.json",

    "cairn_schema_registry.json",
]


#
# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
#

def validate_required_files():

    print(
        "\n[CHECK] Required files"
    )

    missing = []

    for filename in REQUIRED_FILES:

        path = (
            COMPILED_DIR /
            filename
        )

        if path.exists():

            print(
                f"[OK] {filename}"
            )

        else:

            print(
                f"[MISSING] {filename}"
            )

            missing.append(
                filename
            )

    return missing


def validate_graph():

    print(
        "\n[CHECK] Operational graph"
    )

    graph_path = (
        COMPILED_DIR /
        "operational_graph.json"
    )

    with open(graph_path) as f:

        graph = json.load(f)

    nodes = graph.get(
        "nodes",
        []
    )

    edges = graph.get(
        "edges",
        []
    )

    logistics = graph.get(
        "logistics",
        []
    )

    print(
        f"[INFO] Nodes: "
        f"{len(nodes)}"
    )

    print(
        f"[INFO] Edges: "
        f"{len(edges)}"
    )

    print(
        f"[INFO] Logistics: "
        f"{len(logistics)}"
    )

    if len(nodes) == 0:

        raise RuntimeError(
            "Graph contains no nodes"
        )

    if len(edges) == 0:

        raise RuntimeError(
            "Graph contains no edges"
        )

    print("[OK] Graph valid")


def validate_segments():

    print(
        "\n[CHECK] Segments"
    )

    path = (
        COMPILED_DIR /
        "segments.json"
    )

    if not path.exists():

        print(
            "[WARN] segments.json "
            "missing — skipping"
        )

        return

    with open(path) as f:

        rows = json.load(f)

    total_distance = sum(

        row.get(
            "distance",
            0,
        )

        for row in rows
    )

    total_gain = sum(

        row.get(
            "elevation_gain_ft",
            0,
        )

        for row in rows
    )

    print(
        f"[INFO] Total miles: "
        f"{round(total_distance, 1)}"
    )

    print(
        f"[INFO] Total gain: "
        f"{round(total_gain)} ft"
    )

    if total_distance <= 0:

        raise RuntimeError(
            "Invalid segment mileage"
        )

    print("[OK] Segments valid")


def validate_route_overlay():

    print(
        "\n[CHECK] Route overlay"
    )

    path = (
        COMPILED_DIR /
        "route_overlay.json"
    )

    with open(path) as f:

        overlay = json.load(f)

    overlay_nodes = overlay.get(
        "overlay_nodes",
        []
    )

    operational_segments = overlay.get(
        "operational_segments",
        []
    )

    print(
        f"[INFO] Overlay nodes: "
        f"{len(overlay_nodes)}"
    )

    print(
        f"[INFO] Operational segments: "
        f"{len(operational_segments)}"
    )

    if len(overlay_nodes) == 0:

        raise RuntimeError(
            "Overlay contains no nodes"
        )

    if len(operational_segments) == 0:

        raise RuntimeError(
            "Overlay contains no operational segments"
        )

    previous = None

    for node in overlay_nodes:

        mile = node.get(
            "trail_mile"
        )

        if mile is None:
            continue

        if (
            previous is not None
            and mile < previous
        ):

            raise RuntimeError(
                "Overlay mileage ordering invalid"
            )

        previous = mile

    print("[OK] Route overlay valid")


def validate_approach_trails():

    print(
        "\n[CHECK] Approach trails"
    )

    path = (
        COMPILED_DIR /
        "approach_trails.json"
    )

    with open(path) as f:

        payload = json.load(f)

    trails = payload.get(
        "approach_trails",
        []
    )

    print(
        f"[INFO] Approach trails: "
        f"{len(trails)}"
    )

    if len(trails) == 0:

        raise RuntimeError(
            "No approach trails found"
        )

    required_fields = [
        "route",
        "direction",
        "trail_miles",
        "connected_terminus",
    ]

    for trail in trails:

        for field in required_fields:

            if field not in trail:

                raise RuntimeError(
                    f"Approach trail missing field: {field}"
                )

    print("[OK] Approach trails valid")


#
# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
#

def main():

    print("")
    print(
        "=== CairnOS Validation ==="
    )
    print("")

    #
    # files
    #

    missing = (
        validate_required_files()
    )

    if missing:

        print("")
        print("[FAILED]")
        print("")

        raise RuntimeError(

            "Missing compiled files: "
            + ", ".join(missing)
        )

    #
    # graph
    #

    validate_graph()

    #
    # segments
    #

    validate_segments()

    validate_route_overlay()

    validate_approach_trails()

    #
    # success
    #

    print("")
    print("[SUMMARY]")
    print("")

    print(
        "Validation passed"
    )

    print("")
    print("[DONE]")


if __name__ == "__main__":

    main()