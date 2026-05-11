#!/usr/bin/env python3

import sys
import math
import json
from pathlib import Path

import gpxpy
import geopandas as gpd
import rasterio

from shapely.geometry import (
    Point,
    LineString,
    mapping
)

from difflib import SequenceMatcher


# =========================================================
# CONFIG
# =========================================================

CORRIDOR_DISTANCE_METERS = 1000

METERS_PER_DEGREE = 111320

CORRIDOR_DISTANCE_DEGREES = (
    CORRIDOR_DISTANCE_METERS /
    METERS_PER_DEGREE
)

VALID_FCLASSES = {
    "shelter",
    "camp_site",
    "alpine_hut"
}

STOP_WORDS = {
    "shelter",
    "lean",
    "lean-to",
    "camp",
    "campground",
    "campsite",
    "mountain",
    "mt",
    "trail",
    "site",
    "pond",
}

DEM_SAMPLE_INTERVAL_MILES = 0.1


# =========================================================
# NORMALIZATION
# =========================================================

def normalize(text):

    if not text:
        return ""

    text = text.lower()

    for ch in [",", ".", "'", "-", "_", "/", "(", ")"]:
        text = text.replace(ch, " ")

    words = []

    for w in text.split():

        if w not in STOP_WORDS:
            words.append(w)

    return " ".join(words).strip()


def similarity(a, b):

    return SequenceMatcher(
        None,
        normalize(a),
        normalize(b)
    ).ratio()


# =========================================================
# DISTANCE
# =========================================================

def haversine_miles(
    lat1,
    lon1,
    lat2,
    lon2
):

    R = 3958.8

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)

    dphi = math.radians(
        lat2 - lat1
    )

    dlambda = math.radians(
        lon2 - lon1
    )

    a = (
        math.sin(dphi / 2) ** 2
        +
        math.cos(phi1)
        *
        math.cos(phi2)
        *
        math.sin(dlambda / 2) ** 2
    )

    c = (
        2 *
        math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a)
        )
    )

    return R * c


# =========================================================
# GPX SPINE
# =========================================================

def load_gpx_spine(gpx_file):

    print("\n[INFO] Loading GPX spine\n")

    with open(gpx_file, "r") as f:

        gpx = gpxpy.parse(f)

    coords = []

    cumulative_miles = []

    total_miles = 0.0

    prev = None

    for track in gpx.tracks:

        for segment in track.segments:

            for p in segment.points:

                coords.append(
                    (p.longitude, p.latitude)
                )

                if prev:

                    dist = haversine_miles(
                        prev.latitude,
                        prev.longitude,
                        p.latitude,
                        p.longitude
                    )

                    total_miles += dist

                cumulative_miles.append(
                    total_miles
                )

                prev = p

    spine = LineString(coords)

    print(
        f"[INFO] Trackpoints: "
        f"{len(coords)}"
    )

    print(
        f"[INFO] Trail miles: "
        f"{round(total_miles,1)}"
    )

    return {

        "geometry": spine,

        "coords": coords,

        "mile_series": cumulative_miles,

        "total_miles": total_miles
    }


# =========================================================
# LOAD POIS
# =========================================================

def load_pois(shp_file):

    print("\n[INFO] Loading POIs\n")

    gdf = gpd.read_file(shp_file)

    print(
        f"[INFO] Raw POIs: "
        f"{len(gdf)}"
    )

    gdf = gdf[
        gdf["fclass"].isin(
            VALID_FCLASSES
        )
    ]

    gdf = gdf[
        gdf["name"].notnull()
    ]

    print(
        f"[INFO] Overnight POIs: "
        f"{len(gdf)}"
    )

    return gdf


# =========================================================
# LOAD DEMS
# =========================================================

def load_dem_files(dem_dir):

    print("\n[INFO] Loading DEM tiles\n")

    tif_files = sorted(
        Path(dem_dir).glob("*.tif")
    )

    datasets = []

    for tif in tif_files:

        ds = rasterio.open(tif)

        datasets.append(ds)

    print(
        f"[INFO] DEM tiles: "
        f"{len(datasets)}"
    )

    return datasets


# =========================================================
# DEM SAMPLING
# =========================================================

def sample_dem_elevation(
    lon,
    lat,
    dem_datasets
):

    for ds in dem_datasets:

        bounds = ds.bounds

        if (
            bounds.left <= lon <= bounds.right
            and
            bounds.bottom <= lat <= bounds.top
        ):

            try:

                row, col = ds.index(
                    lon,
                    lat
                )

                value = ds.read(1)[row, col]

                if value == ds.nodata:
                    return None

                # meters → feet
                return value * 3.28084

            except:
                return None

    return None


# =========================================================
# BUILD TERRAIN PROFILE
# =========================================================

def build_terrain_profile(
    spine,
    dem_datasets
):

    print(
        "\n[INFO] Building terrain profile\n"
    )

    line = spine["geometry"]

    total_miles = spine["total_miles"]

    sample_count = int(
        total_miles /
        DEM_SAMPLE_INTERVAL_MILES
    )

    features = []

    total_gain = 0.0
    total_loss = 0.0

    prev_ele = None

    for i in range(sample_count + 1):

        normalized = (
            i / sample_count
        )

        point = line.interpolate(
            normalized,
            normalized=True
        )

        lon = point.x
        lat = point.y

        ele = sample_dem_elevation(
            lon,
            lat,
            dem_datasets
        )

        if ele is None:
            continue

        mile = (
            normalized *
            total_miles
        )

        if prev_ele is not None:

            delta = ele - prev_ele

            if delta > 0:
                total_gain += delta
            else:
                total_loss += abs(delta)

        prev_ele = ele

        features.append({

            "type": "Feature",

            "geometry":
                mapping(point),

            "properties": {

                "mile":
                    round(mile, 2),

                "elevation_ft":
                    round(ele, 1)
            }
        })

    summary = {

        "trail_miles":
            round(total_miles, 1),

        "total_gain_ft":
            round(total_gain),

        "total_loss_ft":
            round(total_loss),

        "sample_interval_miles":
            DEM_SAMPLE_INTERVAL_MILES,

        "sample_points":
            len(features)
    }

    print(
        f"[INFO] DEM ascent: "
        f"{round(total_gain)} ft"
    )

    return features, summary


# =========================================================
# NODE PROJECTION
# =========================================================

def project_to_spine(
    point,
    spine_geom,
    total_miles
):

    projected = spine_geom.project(point)

    normalized = (
        projected /
        spine_geom.length
    )

    mile = (
        normalized *
        total_miles
    )

    return normalized, mile


# =========================================================
# BUILD NODES
# =========================================================

def build_nodes(
    spine,
    poi_gdf
):

    print(
        "\n[INFO] Building canonical nodes\n"
    )

    corridor = spine[
        "geometry"
    ].buffer(
        CORRIDOR_DISTANCE_DEGREES
    )

    features = []

    seen = set()

    for idx, row in poi_gdf.iterrows():

        geom = row.geometry

        if geom is None:
            continue

        if not geom.intersects(
            corridor
        ):
            continue

        name = row.get("name")

        if not name:
            continue

        norm = normalize(name)

        duplicate = False

        for existing in seen:

            if (
                similarity(
                    norm,
                    existing
                ) > 0.92
            ):
                duplicate = True
                break

        if duplicate:
            continue

        seen.add(norm)

        trail_order, mile = (
            project_to_spine(
                geom,
                spine["geometry"],
                spine["total_miles"]
            )
        )

        features.append({

            "type": "Feature",

            "geometry":
                mapping(geom),

            "properties": {

                "canonical_name":
                    name,

                "canonical_type":
                    row.get("fclass"),

                "mile_estimate":
                    round(mile, 1),

                "trail_order":
                    round(
                        trail_order,
                        6
                    )
            }
        })

    features.sort(
        key=lambda f:
            f["properties"][
                "trail_order"
            ]
    )

    for i, feat in enumerate(features):

        feat["properties"][
            "node_index"
        ] = i

    print(
        f"[INFO] Canonical nodes: "
        f"{len(features)}"
    )

    return features


# =========================================================
# EXPORTS
# =========================================================

def export_geojson(
    filename,
    features
):

    gdf = gpd.GeoDataFrame.from_features(
        features,
        crs="EPSG:4326"
    )

    gdf.to_file(
        filename,
        driver="GeoJSON"
    )

    print(f"[OK] {filename}")


# =========================================================
# MAIN
# =========================================================

def main():

    if len(sys.argv) < 4:

        print(
            "\nUsage:\n"
            "python build_lt_topology.py "
            "long-trail-spine.gpx "
            "data/gis_osm_pois_free_1.shp "
            "data/dem\n"
        )

        sys.exit(1)

    gpx_file = sys.argv[1]
    shp_file = sys.argv[2]
    dem_dir = sys.argv[3]

    spine = load_gpx_spine(
        gpx_file
    )

    pois = load_pois(
        shp_file
    )

    dem_datasets = load_dem_files(
        dem_dir
    )

    terrain_features, terrain_summary = (
        build_terrain_profile(
            spine,
            dem_datasets
        )
    )

    nodes = build_nodes(
        spine,
        pois
    )

    print("\n[EXPORTING]\n")

    export_geojson(
        "terrain_profile.geojson",
        terrain_features
    )

    export_geojson(
        "canonical_nodes.geojson",
        nodes
    )

    export_geojson(
        "lt_spine.geojson",
        [{
            "type": "Feature",
            "geometry":
                mapping(
                    spine["geometry"]
                ),
            "properties": {
                "trail_miles":
                    round(
                        spine["total_miles"],
                        1
                    )
            }
        }]
    )

    with open(
        "terrain_summary.json",
        "w"
    ) as f:

        json.dump(
            terrain_summary,
            f,
            indent=2
        )

    print(
        "[OK] terrain_summary.json"
    )

    print("\n[SUMMARY]\n")

    print(
        json.dumps(
            terrain_summary,
            indent=2
        )
    )

    print("\n[DONE]\n")


if __name__ == "__main__":
    main()
