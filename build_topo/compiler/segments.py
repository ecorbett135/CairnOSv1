# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import sys
import json

import geopandas as gpd
import rasterio
from shapely.geometry import LineString


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

DEM_DIR = RAW_DIR / "dem"


#
# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
#

def load_spine():

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


def estimate_elevation_gain():

    dem_files = list(
        DEM_DIR.glob("*.tif")
    )

    #
    # placeholder logic for now
    #
    # later:
    # real terrain sampling
    #

    if not dem_files:

        return 0

    return 62129


def build_segments(spine_gdf):

    line = spine_gdf.geometry.iloc[0]

    if not isinstance(line, LineString):

        raise RuntimeError(
            "Spine geometry is not LineString"
        )

    coords = list(line.coords)

    #
    # simple chunking
    #
    # later:
    # terrain-aware segmentation
    #

    chunk_size = 500

    segments = []

    cumulative_miles = 0.0

    for i in range(

        0,
        len(coords) - 1,
        chunk_size,
    ):

        chunk = coords[
            i:i + chunk_size
        ]

        if len(chunk) < 2:

            continue

        segment_line = LineString(chunk)

        distance = (
            len(chunk) * 0.012
        )

        segment = {

            "segment_id":
            f"segment_{len(segments):04d}",

            "segment_index":
            len(segments),

            "start_mile":
            round(
                cumulative_miles,
                1,
            ),

            "end_mile":
            round(
                cumulative_miles +
                distance,
                1,
            ),

            "distance":
            round(
                distance,
                1,
            ),

            "elevation_gain_ft":
            0,

            "difficulty":
            "moderate",

            "schema_version":
            "1.0",

            "geometry":
            segment_line,
        }

        cumulative_miles += distance

        segments.append(segment)

    return gpd.GeoDataFrame(

        segments,

        geometry="geometry",
        crs="EPSG:4326",
    )


#
# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
#

def main():

    print("")
    print("=== CairnOS Segment Builder ===")
    print("")

    #
    # load spine
    #

    print("[INFO] Loading spine")

    spine_gdf = load_spine()

    #
    # terrain estimation
    #

    print("[INFO] Loading terrain")

    total_gain = (
        estimate_elevation_gain()
    )

    #
    # build segments
    #

    print("[INFO] Building segments")

    segments_gdf = build_segments(
        spine_gdf
    )

    #
    # distribute gain
    #

    if len(segments_gdf) > 0:

        gain_per_segment = int(
            total_gain /
            len(segments_gdf)
        )

        segments_gdf[
            "elevation_gain_ft"
        ] = gain_per_segment

    #
    # export dirs
    #

    COMPILED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    #
    # exports
    #

    geojson_path = (
        COMPILED_DIR /
        "segments.geojson"
    )

    json_path = (
        COMPILED_DIR /
        "segments.json"
    )

    segments_gdf.to_file(

        geojson_path,

        driver="GeoJSON",
    )

    #
    # json export
    #

    export_rows = []

    for _, row in (
        segments_gdf.iterrows()
    ):

        export_rows.append({

            "segment_id":
            row["segment_id"],

            "segment_index":
            int(row["segment_index"]),

            "start_mile":
            float(row["start_mile"]),

            "end_mile":
            float(row["end_mile"]),

            "distance":
            float(row["distance"]),

            "elevation_gain_ft":
            int(
                row[
                    "elevation_gain_ft"
                ]
            ),

            "difficulty":
            row["difficulty"],

            "schema_version":
            row["schema_version"],
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

    #
    # summary
    #

    total_miles = round(

        segments_gdf[
            "distance"
        ].sum(),

        1,
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

    print("")
    print("[SUMMARY]")
    print("")

    print(
        f"Segments: "
        f"{len(segments_gdf)}"
    )

    print(
        f"Total miles: "
        f"{total_miles}"
    )

    print(
        f"Total gain: "
        f"{total_gain} ft"
    )

    print("")
    print("[DONE]")


if __name__ == "__main__":

    main()