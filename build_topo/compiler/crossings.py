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

def load_crossings():

    print("\n[INFO] Loading crossings")

    crossings_path = (
        COMPILED_DIR /
        "crossings.geojson"
    )

    if not crossings_path.exists():

        raise FileNotFoundError(
            f"Missing crossings: "
            f"{crossings_path}"
        )

    gdf = gpd.read_file(
        crossings_path,
        engine="fiona",
    )

    print(
        f"[INFO] Raw crossings: "
        f"{len(gdf)}"
    )

    return gdf


def normalize_columns(gdf):

    #
    # normalize road class field
    #

    if "fclass" in gdf.columns:

        gdf["road_type"] = (
            gdf["fclass"]
        )

    elif "road_type" not in gdf.columns:

        gdf["road_type"] = (
            "unknown"
        )

    #
    # normalize name
    #

    if "name" not in gdf.columns:

        gdf["name"] = "unknown"

    #
    # ensure schema
    #

    gdf["schema_version"] = (
        SCHEMA_VERSION
    )

    return gdf


def enrich_crossings(gdf):

    print(
        "\n[INFO] Refining crossings"
    )

    #
    # future:
    # trailhead detection
    # parking semantics
    # crossing importance
    # hitchability
    #

    gdf["trailhead"] = True

    gdf["vehicle_access"] = True

    gdf["crossing_class"] = (
        "road_crossing"
    )

    return gdf


#
# ---------------------------------------------------------
# EXPORT
# ---------------------------------------------------------
#

def export_outputs(gdf):

    geojson_path = (
        COMPILED_DIR /
        "crossings_refined.geojson"
    )

    json_path = (
        COMPILED_DIR /
        "crossings_refined.json"
    )

    #
    # geojson
    #

    gdf.to_file(

        geojson_path,

        driver="GeoJSON",
    )

    #
    # json
    #

    export_rows = []

    for _, row in gdf.iterrows():

        export_rows.append({

            "crossing_id":
            row.get(
                "crossing_id"
            ),

            "name":
            row.get("name"),

            "road_type":
            row.get(
                "road_type"
            ),

            "trail_mile":
            row.get(
                "trail_mile"
            ),

            "trailhead":
            bool(
                row.get(
                    "trailhead",
                    False,
                )
            ),

            "vehicle_access":
            bool(
                row.get(
                    "vehicle_access",
                    False,
                )
            ),

            "crossing_class":
            row.get(
                "crossing_class"
            ),

            "schema_version":
            row.get(
                "schema_version"
            ),
        })

    with open(
        json_path,
        "w",
    ) as f:

        json.dump(

            export_rows,

            f,
            indent=2,
        )

    print("")
    print("[EXPORTING]")
    print("")

    print(
        f"[OK] {geojson_path}"
    )

    print(
        f"[OK] {json_path}"
    )


#
# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
#

def main():

    print("")
    print(
        "=== CairnOS Crossing Refinement ==="
    )
    print("")

    #
    # load
    #

    gdf = load_crossings()

    #
    # normalize
    #

    gdf = normalize_columns(
        gdf
    )

    #
    # enrich
    #

    gdf = enrich_crossings(
        gdf
    )

    #
    # export
    #

    export_outputs(gdf)

    #
    # summary
    #

    print("")
    print("[SUMMARY]")
    print("")

    print(
        f"Refined crossings: "
        f"{len(gdf)}"
    )

    print("")
    print("[DONE]")


if __name__ == "__main__":

    main()