#!/usr/bin/env python3

"""
build_logistics_nodes.py

Phase 3.5
CairnOS Logistics Graph Builder

Builds:
- road crossings
- trailheads
- resupply access nodes
- logistics connectors

Inputs:
    data/compiled/spine.geojson
    data/compiled/nodes.geojson
    data/raw/csv/towns.csv
    data/raw/shp/gis_osm_roads_free_1.shp

Outputs:
    data/compiled/logistics_nodes.geojson
    data/compiled/crossings.geojson
"""

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point


# =========================================================
# CONFIG
# =========================================================

DATA_DIR = Path("data")

RAW_DIR = DATA_DIR / "raw"

COMPILED_DIR = DATA_DIR / "compiled"

SCHEMA_VERSION = "0.1-draft"

TOTAL_TRAIL_MILES = 249.1

ROAD_BUFFER_METERS = 120


# =========================================================
# HELPERS
# =========================================================

def make_id(prefix, idx):

    return f"{prefix}_{idx:04d}"


def normalize_name(name):

    if not name:
        return "unknown"

    return str(name).strip()


# =========================================================
# LOADERS
# =========================================================

def load_spine():

    print("\n[INFO] Loading spine")

    return gpd.read_file(
        COMPILED_DIR / "spine.geojson",
        engine="fiona"
    )


def load_nodes():

    print("\n[INFO] Loading nodes")

    return gpd.read_file(
        COMPILED_DIR / "nodes.geojson",
        engine="fiona"
    )


def load_roads():

    print("\n[INFO] Loading roads")

    shp = (
        RAW_DIR /
        "shp" /
        "gis_osm_roads_free_1.shp"
    )

    gdf = gpd.read_file(
        shp,
        engine="fiona"
    )

    print(f"[INFO] Raw roads: {len(gdf)}")

    return gdf


def load_towns():

    print("\n[INFO] Loading towns")

    df = pd.read_csv(
        RAW_DIR /
        "csv" /
        "towns.csv"
    )

    print(f"[INFO] Town rows: {len(df)}")

    return df


# =========================================================
# ROAD CROSSINGS
# =========================================================

def build_crossings(
    spine_gdf,
    roads_gdf
):

    print("\n[INFO] Building crossings")

    spine = spine_gdf.iloc[0].geometry

    spine_gdf_3857 = spine_gdf.to_crs(3857)

    roads_3857 = roads_gdf.to_crs(3857)

    spine_geom_3857 = spine_gdf_3857.iloc[0].geometry

    buffer_geom = spine_geom_3857.buffer(
        ROAD_BUFFER_METERS
    )

    near_roads = roads_3857[
        roads_3857.intersects(buffer_geom)
    ].copy()

    print(
        f"[INFO] Roads near trail: "
        f"{len(near_roads)}"
    )

    crossings = []

    idx = 0

    for _, road in near_roads.iterrows():

        road_geom = road.geometry

        try:

            intersection = road_geom.intersection(
                spine_geom_3857
            )

            if intersection.is_empty:
                continue

            points = []

            if intersection.geom_type == "Point":
                points = [intersection]

            elif intersection.geom_type == "MultiPoint":
                points = list(intersection.geoms)

            for pt in points:

                projected = spine_geom_3857.project(pt)

                normalized = (
                    projected /
                    spine_geom_3857.length
                )

                mile = round(
                    normalized *
                    TOTAL_TRAIL_MILES,
                    1
                )

                road_name = normalize_name(
                    road.get("name")
                )

                crossings.append({

                    "crossing_id":
                        make_id(
                            "crossing",
                            idx
                        ),

                    "name":
                        road_name,

                    "road_type":
                        road.get(
                            "fclass",
                            "unknown"
                        ),

                    "trail_mile":
                        mile,

                    "vehicle_access":
                        True,

                    "trailhead":
                        True,

                    "schema_version":
                        SCHEMA_VERSION,

                    "geometry":
                        Point(
                            pt.x,
                            pt.y
                        )
                })

                idx += 1

        except Exception:
            continue

    crossings_gdf = gpd.GeoDataFrame(
        crossings,
        geometry="geometry",
        crs="EPSG:3857"
    )

    crossings_gdf = crossings_gdf.to_crs(
        4326
    )

    print(
        f"[INFO] Crossings built: "
        f"{len(crossings_gdf)}"
    )

    return crossings_gdf


# =========================================================
# RESUPPLY LOGISTICS
# =========================================================

def build_logistics_nodes(
    towns_df
):

    print("\n[INFO] Building logistics nodes")

    records = []

    for idx, row in towns_df.iterrows():

        node = {

            "logistics_id":
                make_id(
                    "logistics",
                    idx
                ),

            "town":
                normalize_name(
                    row.get("town")
                ),

            "division":
                row.get("division"),

            "zip":
                row.get("zip"),

            "post_office":
                bool(
                    row.get(
                        "post_office",
                        False
                    )
                ),

            "grocery":
                bool(
                    row.get(
                        "grocery",
                        False
                    )
                ),

            "additional_amenities":
                bool(
                    row.get(
                        "additional_amenities",
                        False
                    )
                ),

            "resupply_access":
                True,

            "zero_candidate":
                True,

            "nero_candidate":
                True,

            "schema_version":
                SCHEMA_VERSION
        }

        records.append(node)

    print(
        f"[INFO] Logistics nodes: "
        f"{len(records)}"
    )

    return records


# =========================================================
# EXPORT
# =========================================================

def export_crossings(gdf):

    print("\n[EXPORTING]\n")

    output = (
        COMPILED_DIR /
        "crossings.geojson"
    )

    gdf.to_file(
        output,
        driver="GeoJSON"
    )

    print(f"[OK] {output}")


def export_logistics(nodes):

    output = (
        COMPILED_DIR /
        "logistics_nodes.json"
    )

    with open(output, "w") as f:

        json.dump(
            nodes,
            f,
            indent=2
        )

    print(f"[OK] {output}")


# =========================================================
# SUMMARY
# =========================================================

def summarize(
    crossings_gdf,
    logistics_nodes
):

    print("\n[SUMMARY]\n")

    print(
        f"Road crossings: "
        f"{len(crossings_gdf)}"
    )

    print(
        f"Logistics nodes: "
        f"{len(logistics_nodes)}"
    )


# =========================================================
# MAIN
# =========================================================

def main():

    print(
        "\n=== CairnOS Logistics Builder ==="
    )

    spine_gdf = load_spine()

    nodes_gdf = load_nodes()

    roads_gdf = load_roads()

    towns_df = load_towns()

    crossings_gdf = build_crossings(
        spine_gdf,
        roads_gdf
    )

    logistics_nodes = build_logistics_nodes(
        towns_df
    )

    export_crossings(
        crossings_gdf
    )

    export_logistics(
        logistics_nodes
    )

    summarize(
        crossings_gdf,
        logistics_nodes
    )

    print("\n[DONE]\n")


if __name__ == "__main__":
    main()
