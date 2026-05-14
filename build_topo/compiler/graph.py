from pathlib import Path
import sys
import json

import geopandas as gpd  


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


# ---------------------------------------------------------
# ROUTE OVERLAY & APPROACH TRAILS LOADERS
# ---------------------------------------------------------

def load_route_overlay():

    print(
        "\n[INFO] Loading route overlay"
    )

    path = (
        COMPILED_DIR /
        "route_overlay.json"
    )

    if not path.exists():

        raise FileNotFoundError(
            f"Missing route overlay: {path}"
        )

    with open(path) as f:

        payload = json.load(f)

    overlay_nodes = payload.get(
        "overlay_nodes",
        []
    )

    operational_segments = payload.get(
        "operational_segments",
        []
    )

    print(
        f"[INFO] Overlay nodes: "
        f"{len(overlay_nodes)}"
    )

    print(
        f"[INFO] Overlay segments: "
        f"{len(operational_segments)}"
    )

    return payload


def load_approach_trails():

    print(
        "\n[INFO] Loading approach trails"
    )

    path = (
        COMPILED_DIR /
        "approach_trails.json"
    )

    if not path.exists():

        raise FileNotFoundError(
            f"Missing approach trails: {path}"
        )

    with open(path) as f:

        payload = json.load(f)

    trails = payload.get(
        "approach_trails",
        []
    )

    print(
        f"[INFO] Approach trail nodes: "
        f"{len(trails)}"
    )

    return payload


#
# ---------------------------------------------------------
# GRAPH BUILD
# ---------------------------------------------------------
#

def build_nodes(
    segments_gdf,
    crossings_gdf,
    route_overlay,
    approach_trails,
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

    #
    # route overlay nodes
    #

    for row in route_overlay.get(
        "overlay_nodes",
        []
    ):

        nodes.append({

            "node_id":
            make_node_id(idx),

            "node_type":
            "overlay",

            "overlay_id":
            row.get(
                "overlay_id"
            ),

            "canonical_name":
            row.get(
                "canonical_name"
            ),

            "trail_mile":
            row.get(
                "trail_mile"
            ),

            "node_class":
            row.get(
                "node_class"
            ),

            "division":
            row.get(
                "division"
            ),

            "approach_trail":
            row.get(
                "approach_trail"
            ),

            "town_access":
            row.get(
                "town_access"
            ),

            "access_notes":
            row.get(
                "access_notes"
            ),

            "resupply_services":
            row.get(
                "resupply_services"
            ),

            "resupply_source":
            row.get(
                "resupply_source"
            ),

            "resupply_source_url":
            row.get(
                "resupply_source_url"
            ),

            "logistics":
            row.get(
                "logistics"
            ),

            "overnight":
            row.get(
                "overnight"
            ),

            "shelter":
            row.get(
                "shelter"
            ),

            "camping":
            row.get(
                "camping"
            ),

            "water":
            row.get(
                "water"
            ),

            "resupply":
            row.get(
                "resupply"
            ),

            "zero_candidate":
            row.get(
                "zero_candidate"
            ),

            "schema_version":
            SCHEMA_VERSION,
        })

        idx += 1

    #
    # approach trail nodes
    #

    for row in approach_trails.get(
        "approach_trails",
        []
    ):

        nodes.append({

            "node_id":
            make_node_id(idx),

            "node_type":
            "approach",

            "approach_id":
            row.get(
                "approach_id"
            ),

            "approach_name":
            row.get(
                "approach_name"
            ),

            "direction":
            row.get(
                "direction"
            ),

            "terminus":
            row.get(
                "terminus"
            ),

            "location":
            row.get(
                "location"
            ),

            "cumulative_to_trail_mi":
            row.get(
                "cumulative_to_trail_mi"
            ),

            "node_class":
            row.get(
                "node_class"
            ),

            "road_access":
            row.get(
                "road_access"
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
    segments_gdf,
    route_overlay,
    approach_trails,
):

    print("\n[INFO] Building edges")

    edges = []

    idx = 0

    #
    # terrain continuity edges
    #

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

            "edge_type":
            "terrain_continuity",

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

    #
    # overlay traversal edges
    #

    for segment in route_overlay.get(
        "operational_segments",
        []
    ):

        edges.append({

            "edge_id":
            make_edge_id(idx),

            "edge_type":
            "operational_progression",

            "from_overlay":
            segment.get(
                "start_node"
            ),

            "to_overlay":
            segment.get(
                "end_node"
            ),

            "distance":
            segment.get(
                "distance"
            ),

            "start_name":
            segment.get(
                "start_name"
            ),

            "end_name":
            segment.get(
                "end_name"
            ),

            "schema_version":
            SCHEMA_VERSION,
        })

        idx += 1

    #
    # approach traversal edges
    #

    trails = sorted(
        approach_trails.get(
            "approach_trails",
            []
        ),
        key=lambda x: (
            x.get(
                "approach_id"
            ),
            x.get(
                "sequence",
                0,
            ),
        ),
    )

    for i in range(
        len(trails) - 1
    ):

        current = trails[i]
        nxt = trails[i + 1]

        if (
            current.get(
                "approach_id"
            )
            != nxt.get(
                "approach_id"
            )
        ):
            continue

        edges.append({

            "edge_id":
            make_edge_id(idx),

            "edge_type":
            "approach_transition",

            "approach_id":
            current.get(
                "approach_id"
            ),

            "from_location":
            current.get(
                "location"
            ),

            "to_location":
            nxt.get(
                "location"
            ),

            "distance_to_terminus_mi":
            nxt.get(
                "distance_to_terminus_mi"
            ),

            "direction":
            current.get(
                "direction"
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

    route_overlay = (
        load_route_overlay()
    )

    approach_trails = (
        load_approach_trails()
    )

    #
    # build
    #

    nodes = build_nodes(

        segments_gdf,
        crossings_gdf,
        route_overlay,
        approach_trails,
    )

    edges = build_edges(

        segments_gdf,
        route_overlay,
        approach_trails,
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
