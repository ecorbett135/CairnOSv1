# build_operational_graph.py

from pathlib import Path
import json
import geopandas as gpd

COMPILED_DIR = Path("data/compiled")

SEGMENTS_FILE = COMPILED_DIR / "segments.geojson"
CROSSINGS_FILE = COMPILED_DIR / "crossings_refined.geojson"
NODES_FILE = COMPILED_DIR / "nodes.geojson"

OUTPUT_FILE = COMPILED_DIR / "operational_graph.json"

SCHEMA_VERSION = "0.2-draft"


def load_data():

    print("[INFO] Loading segments")
    segments = gpd.read_file(SEGMENTS_FILE)

    print("[INFO] Loading crossings")
    crossings = gpd.read_file(CROSSINGS_FILE)

    print("[INFO] Loading nodes")
    nodes = gpd.read_file(NODES_FILE)

    return segments, crossings, nodes


def build_graph(
    segments,
    crossings,
    nodes
):

    graph = {
        "schema_version": SCHEMA_VERSION,
        "segments": [],
        "nodes": [],
        "crossings": [],
    }

    for _, row in segments.iterrows():

        graph["segments"].append({
            "segment_id": row.get("segment_id"),
            "start_node": row.get("start_node"),
            "end_node": row.get("end_node"),
            "distance_miles": row.get("distance_miles"),
            "gain_ft": row.get("gain_ft"),
            "loss_ft": row.get("loss_ft"),
        })

    for _, row in nodes.iterrows():

        graph["nodes"].append({
            "node_id": row.get("node_id"),
            "canonical_name": row.get("canonical_name"),
            "mile": row.get("mile"),
            "node_class": row.get("node_class"),
        })

    for _, row in crossings.iterrows():

        graph["crossings"].append({
            "crossing_id": row.get("crossing_id"),
            "road_name": row.get("name"),
            "fclass": row.get("fclass"),
            "mile": row.get("mile"),
            "access_score": row.get("access_score"),
            "vehicle_access": row.get("vehicle_access"),
            "likely_hitchable": row.get("likely_hitchable"),
        })

    return graph


def export_graph(graph):

    with open(OUTPUT_FILE, "w") as fp:
        json.dump(graph, fp, indent=2)

    print(f"[OK] {OUTPUT_FILE}")


def main():

    print("\n=== CairnOS Operational Graph Builder ===\n")

    segments, crossings, nodes = load_data()

    print("\n[INFO] Building graph")

    graph = build_graph(
        segments,
        crossings,
        nodes
    )

    print("\n[EXPORTING]\n")

    export_graph(graph)

    print("\n[DONE]\n")


if __name__ == "__main__":
    main()
