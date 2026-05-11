#!/usr/bin/env python3

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

SCHEMA_VERSION = "0.1-draft"
TOPOLOGY_VERSION = "phase2"
TRAIL_NAME = "Vermont Long Trail"

DATA_DIR = Path("data")
INTERMEDIATE_DIR = DATA_DIR / "intermediate"
RAW_CSV_DIR = DATA_DIR / "raw" / "csv"
COMPILED_DIR = DATA_DIR / "compiled"

COMPILED_DIR.mkdir(parents=True, exist_ok=True)


def make_id(prefix, index):
    return f"{prefix}_{index:04d}"


def write_geojson(gdf, output_path):
    gdf.to_file(output_path, driver="GeoJSON")
    print(f"[OK] {output_path}")


def load_geojson(name):
    print(f"\\n[INFO] Loading {name}")
    return gpd.read_file(
    	INTERMEDIATE_DIR / name,
    	engine="fiona"
    )


def load_json(name):
    print(f"\\n[INFO] Loading {name}")
    with open(INTERMEDIATE_DIR / name, "r") as f:
        return json.load(f)


def load_csv(name):
    print(f"\\n[INFO] Loading {name}")
    df = pd.read_csv(RAW_CSV_DIR / name)
    print(f"[INFO] Rows: {len(df)}")
    return df


def compile_spine(gdf):
    print("\\n[INFO] Compiling spine")
    gdf = gdf.copy()
    gdf["spine_id"] = "lt_spine_001"
    gdf["trail_name"] = TRAIL_NAME
    gdf["schema_version"] = SCHEMA_VERSION
    gdf["topology_version"] = TOPOLOGY_VERSION
    return gdf


def compile_terrain(gdf):
    print("\\n[INFO] Compiling terrain")
    gdf = gdf.copy()
    gdf["sample_id"] = [
        make_id("terrain", i)
        for i in range(len(gdf))
    ]
    gdf["schema_version"] = SCHEMA_VERSION
    return gdf


def compile_nodes(gdf):
    print("\\n[INFO] Compiling nodes")
    gdf = gdf.copy()

    gdf["node_id"] = [
        make_id("node", i)
        for i in range(len(gdf))
    ]

    gdf["node_class"] = "overnight"
    gdf["schema_version"] = SCHEMA_VERSION

    return gdf


def compile_resupply_nodes(towns_df):

    print("\\n[INFO] Building resupply nodes")

    records = []

    for idx, row in towns_df.iterrows():

        record = {
            "node_id": make_id("town", idx),
            "canonical_name": row.get("town", "unknown"),
            "division": row.get("division"),
            "zip": row.get("zip"),
            "post_office": bool(row.get("post_office", False)),
            "grocery": bool(row.get("grocery", False)),
            "additional_amenities": bool(
                row.get("additional_amenities", False)
            ),
            "node_type": "resupply",
            "node_class": "logistics",
            "zero_candidate": True,
            "nero_candidate": True,
            "schema_version": SCHEMA_VERSION
        }

        records.append(record)

    print(f"[INFO] Resupply nodes: {len(records)}")

    return records


def build_topology_json(
    terrain_summary,
    nodes_gdf,
    resupply_nodes
):

    print("\\n[INFO] Building topology")

    return {
        "trail_name": TRAIL_NAME,
        "schema_version": SCHEMA_VERSION,
        "topology_version": TOPOLOGY_VERSION,
        "trail_miles": terrain_summary.get("trail_miles"),
        "total_gain_ft": terrain_summary.get("total_gain_ft"),
        "total_loss_ft": terrain_summary.get("total_loss_ft"),
        "overnight_nodes": len(nodes_gdf),
        "resupply_nodes": len(resupply_nodes)
    }


def build_metadata():

    print("\\n[INFO] Building metadata")

    return {
        "schema_version": SCHEMA_VERSION,
        "topology_version": TOPOLOGY_VERSION,
        "generated_products": [
            "spine.geojson",
            "terrain.geojson",
            "nodes.geojson",
            "resupply_nodes.json",
            "topology.json",
            "metadata.json"
        ]
    }


def main():

    print("\\n=== CairnOS Dataset Compiler ===")

    spine_gdf = load_geojson("lt_spine.geojson")
    terrain_gdf = load_geojson("terrain_profile.geojson")
    nodes_gdf = load_geojson("canonical_nodes.geojson")

    terrain_summary = load_json("terrain_summary.json")

    centerline_df = load_csv("Centerline.csv")
    towns_df = load_csv("towns.csv")

    compiled_spine = compile_spine(spine_gdf)
    compiled_terrain = compile_terrain(terrain_gdf)
    compiled_nodes = compile_nodes(nodes_gdf)

    compiled_resupply = compile_resupply_nodes(towns_df)

    topology = build_topology_json(
        terrain_summary,
        compiled_nodes,
        compiled_resupply
    )

    metadata = build_metadata()

    print("\\n[EXPORTING]\\n")

    write_geojson(
        compiled_spine,
        COMPILED_DIR / "spine.geojson"
    )

    write_geojson(
        compiled_terrain,
        COMPILED_DIR / "terrain.geojson"
    )

    write_geojson(
        compiled_nodes,
        COMPILED_DIR / "nodes.geojson"
    )

    with open(
        COMPILED_DIR / "resupply_nodes.json",
        "w"
    ) as f:

        json.dump(
            compiled_resupply,
            f,
            indent=2
        )

    print(f"[OK] {COMPILED_DIR / 'resupply_nodes.json'}")

    with open(
        COMPILED_DIR / "topology.json",
        "w"
    ) as f:

        json.dump(
            topology,
            f,
            indent=2
        )

    print(f"[OK] {COMPILED_DIR / 'topology.json'}")

    with open(
        COMPILED_DIR / "metadata.json",
        "w"
    ) as f:

        json.dump(
            metadata,
            f,
            indent=2
        )

    print(f"[OK] {COMPILED_DIR / 'metadata.json'}")

    print("\\n[SUMMARY]\\n")
    print(json.dumps(topology, indent=2))

    print("\\n[DONE]\\n")


if __name__ == "__main__":
    main()
