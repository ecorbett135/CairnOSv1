# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import sys
import json

import geopandas as gpd
import gpxpy
from shapely.geometry import LineString


#
# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
#

def load_gpx_track(gpx_path):

    with open(gpx_path, "r") as f:

        gpx = gpxpy.parse(f)

    coords = []

    for track in gpx.tracks:

        for segment in track.segments:

            for point in segment.points:

                coords.append(
                    (
                        point.longitude,
                        point.latitude,
                    )
                )

    if not coords:

        raise RuntimeError(
            "No GPX coordinates found"
        )

    return LineString(coords)


#
# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
#

def main():

    if len(sys.argv) != 2:

        print("")
        print("Usage:")
        print("")
        print(
            "python -m build_topo.compiler.spine "
            "trails/vermont_long_trail"
        )
        print("")

        sys.exit(1)

    trail_root = Path(sys.argv[1]).resolve()

    RAW_DIR = trail_root / "raw"
    COMPILED_DIR = trail_root / "compiled"
    INTERMEDIATE_DIR = trail_root / "intermediate"

    GPX_DIR = RAW_DIR / "gpx"

    #
    # find GPX
    #

    gpx_files = list(
        GPX_DIR.glob("*.gpx")
    )

    if not gpx_files:

        raise FileNotFoundError(
            f"No GPX files found in: {GPX_DIR}"
        )

    gpx_path = gpx_files[0]

    print("")
    print("=== CairnOSv1 Spine Builder ===")
    print("")
    print(f"Trail Root: {trail_root}")
    print(f"GPX: {gpx_path.name}")

    #
    # build geometry
    #

    line = load_gpx_track(gpx_path)

    gdf = gpd.GeoDataFrame(

        [
            {
                "trail_name": trail_root.name,
                "schema_version": "1.0",
                "geometry": line,
            }
        ],

        geometry="geometry",
        crs="EPSG:4326",
    )

    #
    # ensure dirs
    #

    COMPILED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    INTERMEDIATE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    #
    # export
    #

    compiled_path = (
        COMPILED_DIR /
        "spine.geojson"
    )

    intermediate_path = (
        INTERMEDIATE_DIR /
        "canonical_spine.geojson"
    )

    gdf.to_file(
        compiled_path,
        driver="GeoJSON",
    )

    gdf.to_file(
        intermediate_path,
        driver="GeoJSON",
    )

    #
    # metadata
    #

    metadata = {

        "trail": trail_root.name,
        "schema_version": "1.0",
        "spine_points": len(line.coords),
    }

    with open(
        COMPILED_DIR / "metadata.json",
        "w",
    ) as f:

        json.dump(
            metadata,
            f,
            indent=2,
        )

    print("")
    print("[OK] spine.geojson")
    print("[OK] canonical_spine.geojson")
    print("")
    print("[DONE]")


if __name__ == "__main__":

    main()