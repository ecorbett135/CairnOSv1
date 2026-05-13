from pathlib import Path
import sys
import json

import geopandas as gpd  
import pandas as pd  
from shapely.geometry import Point  


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

TOTAL_TRAIL_MILES = 273.0

ROAD_BUFFER_METERS = 120


#
# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
#

def make_id(prefix, idx):

    return f"{prefix}_{idx:04d}"


def normalize_name(name):

    if not name:
        return "unknown"

    return str(name).strip()


#
# ---------------------------------------------------------
# LOADERS
# ---------------------------------------------------------
#

def load_spine():

    print("\n[INFO] Loading spine")

    spine_path = (
        COMPILED_DIR /
        "spine.geojson"
    )

    if not spine_path.exists():

        raise FileNotFoundError(
            f"Missing spine: {spine_path}"
        )

    return gpd.read_file(
        spine_path,
        engine="fiona",
    )


def load_roads():

    print("\n[INFO] Loading roads")

    shp_files = list(
        (
            RAW_DIR / "shp"
        ).glob("*roads*.shp")
    )

    if not shp_files:

        raise FileNotFoundError(
            "No roads shapefile found"
        )

    roads_path = shp_files[0]

    gdf = gpd.read_file(
        roads_path,
        engine="fiona",
    )

    print(
        f"[INFO] Raw roads: "
        f"{len(gdf)}"
    )

    return gdf


def load_towns():

    print("\n[INFO] Loading towns")

    towns_path = (
        RAW_DIR /
        "csv" /
        "towns.csv"
    )

    if not towns_path.exists():

        raise FileNotFoundError(
            f"Missing towns.csv: "
            f"{towns_path}"
        )

    df = pd.read_csv(
        towns_path
    )

    print(
        f"[INFO] Town rows: "
        f"{len(df)}"
    )

    return df


#
# ---------------------------------------------------------
# CROSSINGS
# ---------------------------------------------------------
#

def build_crossings(
    spine_gdf,
    roads_gdf,
):

    print("\n[INFO] Building crossings")

    spine_gdf_3857 = (
        spine_gdf.to_crs(3857)
    )

    roads_3857 = (
        roads_gdf.to_crs(3857)
    )

    spine_geom = (
        spine_gdf_3857
        .iloc[0]
        .geometry
    )

    buffer_geom = spine_geom.buffer(
        ROAD_BUFFER_METERS
    )

    near_roads = roads_3857[
        roads_3857.intersects(
            buffer_geom
        )
    ].copy()

    print(
        f"[INFO] Roads near trail: "
        f"{len(near_roads)}"
    )

    crossings = []

    idx = 0

    for _, road in near_roads.iterrows():

        try:

            road_geom = road.geometry

            intersection = (
                road_geom.intersection(
                    spine_geom
                )
            )

            if intersection.is_empty:
                continue

            points = []

            if intersection.geom_type == "Point":

                points = [intersection]

            elif (
                intersection.geom_type
                == "MultiPoint"
            ):

                points = list(
                    intersection.geoms
                )

            for pt in points:

                projected = (
                    spine_geom.project(pt)
                )

                normalized = (
                    projected /
                    spine_geom.length
                )

                mile = round(
                    normalized *
                    TOTAL_TRAIL_MILES,
                    1,
                )

                crossings.append({

                    "crossing_id":
                    make_id(
                        "crossing",
                        idx,
                    ),

                    "name":
                    normalize_name(
                        road.get("name")
                    ),

                    "road_type":
                    road.get(
                        "fclass",
                        "unknown",
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
                        pt.y,
                    ),
                })

                idx += 1

        except Exception:

            continue

    crossings_gdf = gpd.GeoDataFrame(

        crossings,

        geometry="geometry",

        crs="EPSG:3857",
    )

    crossings_gdf = (
        crossings_gdf.to_crs(4326)
    )

    print(
        f"[INFO] Crossings built: "
        f"{len(crossings_gdf)}"
    )

    return crossings_gdf


#
# ---------------------------------------------------------
# LOGISTICS NODES
# ---------------------------------------------------------
#

def build_logistics_nodes(
    towns_df
):

    print(
        "\n[INFO] Building logistics nodes"
    )

    records = []

    for idx, row in (
        towns_df.iterrows()
    ):

        records.append({

            "logistics_id":
            make_id(
                "logistics",
                idx,
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
                    False,
                )
            ),

            "grocery":
            bool(
                row.get(
                    "grocery",
                    False,
                )
            ),

            "zero_candidate":
            bool(
                row.get(
                    "zero_candidate",
                    False,
                )
            ),

            "nero_candidate":
            bool(
                row.get(
                    "nero_candidate",
                    False,
                )
            ),

            "schema_version":
            SCHEMA_VERSION,
        })

    print(
        f"[INFO] Logistics nodes: "
        f"{len(records)}"
    )

    return records


#
# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
#

def main():

    print("")
    print(
        "=== CairnOS Logistics Builder ==="
    )
    print("")

    #
    # loads
    #

    spine_gdf = load_spine()

    roads_gdf = load_roads()

    towns_df = load_towns()

    #
    # crossings
    #

    crossings_gdf = build_crossings(

        spine_gdf,
        roads_gdf,
    )

    #
    # logistics
    #

    logistics_nodes = (
        build_logistics_nodes(
            towns_df
        )
    )

    #
    # ensure dirs
    #

    COMPILED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    #
    # exports
    #

    crossings_geojson = (
        COMPILED_DIR /
        "crossings.geojson"
    )

    logistics_json = (
        COMPILED_DIR /
        "logistics_nodes.json"
    )

    crossings_gdf.to_file(

        crossings_geojson,

        driver="GeoJSON",
    )

    with open(
        logistics_json,
        "w",
    ) as f:

        json.dump(
            logistics_nodes,
            f,
            indent=2,
        )

    #
    # summary
    #

    print("")
    print("[EXPORTING]")
    print("")

    print(
        f"[OK] {crossings_geojson}"
    )

    print(
        f"[OK] {logistics_json}"
    )

    print("")
    print("[SUMMARY]")
    print("")

    print(
        f"Road crossings: "
        f"{len(crossings_gdf)}"
    )

    print(
        f"Logistics nodes: "
        f"{len(logistics_nodes)}"
    )

    print("")
    print("[DONE]")


if __name__ == "__main__":

    main()