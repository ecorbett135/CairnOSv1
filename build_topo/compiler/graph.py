from pathlib import Path
import sys
import json

import geopandas as gpd
import pandas as pd


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
# HELPERS
# ---------------------------------------------------------
#

def make_node_id(idx):

    return f"node_{idx:04d}"


def make_edge_id(idx):

    return f"edge_{idx:04d}"


#
# ---------------------------------------------------------
# LOADERS
# ---------------------------------------------------------
#

def load_segments():

    print("\n[INFO] Loading segments")

    path = (
        COMPILED_DIR /
        "segments.geojson"
    )

    if not path.exists():

        raise FileNotFoundError(
            f"Missing segments: {path}"
        )

    gdf = gpd.read_file(
        path,
        engine="fiona",
    )

    print(
        f"[INFO] Segments: "
        f"{len(gdf)}"
    )

    return gdf


def load_crossings():

    print(
        "\n[INFO] Loading crossings"
    )

    path = (
        COMPILED_DIR /
        "crossings_refined.geojson"
    )

    if not path.exists():

        raise FileNotFoundError(
            f"Missing crossings: {path}"
        )

    gdf = gpd.read_file(
        path,
        engine="fiona",
    )

    print(
        f"[INFO] Crossings: "
        f"{len(gdf)}"
    )

    return gdf


def load_logistics_nodes():

    print(
        "\n[INFO] Loading logistics nodes"
    )

    path = (
        COMPILED_DIR /
        "logistics_nodes.json"
    )

    if not path.exists():

        raise FileNotFoundError(
            f"Missing logistics: {path}"
        )

    with open(path) as f:

        rows = json.load(f)

    print(
        f"[INFO] Logistics nodes: "
        f"{len(rows)}"
    )

    return rows


#
# ---------------------------------------------------------
# GRAPH BUILD
# ---------------------------------------------------------
#

def build_nodes(
    segments_gdf,
    crossings_gdf,
):

    print("\n[INFO] Building nodes")

    nodes = []

    idx = 0

    #
    # segment nodes
    #

    for _, row in (
        segments_gdf.iterrows()
    ):

        nodes.append({

            "node_id":
            make_node_id(idx),

            "node_type":
            "segment",

            "segment_id":
            row.get(
                "segment_id"
            ),

            "start_mile":
            row.get(
                "start_mile"
            ),

            "end_mile":
            row.get(
                "end_mile"
            ),

            "distance":
            row.get(
                "distance"
            ),

            "elevation_gain_ft":
            row.get(
                "elevation_gain_ft"
            ),

            "difficulty":
            row.get(
                "difficulty"
            ),

            "schema_version":
            SCHEMA_VERSION,
        })

        idx += 1

    #
    # crossing nodes
    #

    for _, row in (
        crossings_gdf.iterrows()
    ):

        nodes.append({

            "node_id":
            make_node_id(idx),

            "node_type":
            "crossing",

            "crossing_id":
            row.get(
                "crossing_id"
            ),

            "name":
            row.get("name"),

            "trail_mile":
            row.get(
                "trail_mile"
            ),

            "road_type":
            row.get(
                "road_type"
            ),

            "vehicle_access":
            row.get(
                "vehicle_access"
            ),

            "schema_version":
            SCHEMA_VERSION,
        })

        idx += 1

    print(
        f"[INFO] Nodes built: "
        f"{len(nodes)}"
    )

    return nodes


def build_edges(
    segments_gdf
):

    print("\n[INFO] Building edges")

    edges = []

    idx = 0

    segment_rows = list(
        segments_gdf.iterrows()
    )

    for i in range(
        len(segment_rows) - 1
    ):

        current = (
            segment_rows[i][1]
        )

        nxt = (
            segment_rows[i + 1][1]
        )

        edges.append({

            "edge_id":
            make_edge_id(idx),

            "from_segment":
            current.get(
                "segment_id"
            ),

            "to_segment":
            nxt.get(
                "segment_id"
            ),

            "distance":
            nxt.get(
                "distance"
            ),

            "elevation_gain_ft":
            nxt.get(
                "elevation_gain_ft"
            ),

            "difficulty":
            nxt.get(
                "difficulty"
            ),

            "schema_version":
            SCHEMA_VERSION,
        })

        idx += 1

    print(
        f"[INFO] Edges built: "
        f"{len(edges)}"
    )

    return edges


#
# ---------------------------------------------------------
# EXPORT
# ---------------------------------------------------------
#

def export_graph(
    nodes,
    edges,
    logistics_nodes,
):

    graph = {

        "schema_version":
        SCHEMA_VERSION,

        "trail":
        trail_root.name,

        "nodes":
        nodes,

        "edges":
        edges,

        "logistics":
        logistics_nodes,
    }

    output_path = (
        COMPILED_DIR /
        "operational_graph.json"
    )

    with open(
        output_path,
        "w",
    ) as f:

        json.dump(
            graph,
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
        "=== CairnOS Operational Graph Builder ==="
    )
    print("")

    #
    # load
    #

    segments_gdf = (
        load_segments()
    )

    crossings_gdf = (
        load_crossings()
    )

    logistics_nodes = (
        load_logistics_nodes()
    )

    #
    # build
    #

    nodes = build_nodes(

        segments_gdf,
        crossings_gdf,
    )

    edges = build_edges(
        segments_gdf
    )

    #
    # export
    #

    export_graph(

        nodes,
        edges,
        logistics_nodes,
    )

    #
    # summary
    #

    print("")
    print("[SUMMARY]")
    print("")

    print(
        f"Nodes: {len(nodes)}"
    )

    print(
        f"Edges: {len(edges)}"
    )

    print(
        f"Logistics nodes: "
        f"{len(logistics_nodes)}"
    )

    print("")
    print("[DONE]")


if __name__ == "__main__":

    main()