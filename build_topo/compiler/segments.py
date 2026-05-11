#!/usr/bin/env python3

"""
build_segments.py

Phase 3
Operational Segment Builder
"""

import json
from pathlib import Path

import geopandas as gpd
from shapely.geometry import LineString



# =========================================================
# PATHS
# =========================================================

trail_root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path("trails/vermont_long_trail").resolve()

RAW_DIR = trail_root / "raw"
COMPILED_DIR = trail_root / "compiled"
INTERMEDIATE_DIR = trail_root / "intermediate"

# =========================================================
# CONFIG
# =========================================================

DATA_DIR = Path("data")

COMPILED_DIR = DATA_DIR / "compiled"

SCHEMA_VERSION = "0.1-draft"

TOTAL_TRAIL_MILES = 249.1


# =========================================================
# HELPERS
# =========================================================

def make_segment_id(index):

    return f"seg_{index:04d}"


def estimate_difficulty(gain_per_mile):

    if gain_per_mile < 150:
        return "easy"

    if gain_per_mile < 300:
        return "moderate"

    if gain_per_mile < 500:
        return "hard"

    return "extreme"


def estimate_hours(miles, gain_ft):

    base_speed = 2.2

    gain_penalty = gain_ft / 1800

    return round(
        (miles / base_speed) + gain_penalty,
        1
    )


# =========================================================
# LOADERS
# =========================================================

def load_spine():

    print("\n[INFO] Loading spine")

    return gpd.read_file(
        COMPILED_DIR / "spine.geojson",
        engine="fiona"
    )


def load_terrain():

    print("\n[INFO] Loading terrain")

    return gpd.read_file(
        COMPILED_DIR / "terrain.geojson",
        engine="fiona"
    )


def load_nodes():

    print("\n[INFO] Loading nodes")

    gdf = gpd.read_file(
        COMPILED_DIR / "nodes.geojson",
        engine="fiona"
    )

    required = [
        "mile_estimate",
        "trail_order"
    ]

    for field in required:

        if field not in gdf.columns:

            raise RuntimeError(
                f"Missing required field: {field}"
            )

    gdf = gdf.sort_values(
        by="trail_order",
        ascending=True
    ).reset_index(drop=True)

    return gdf


# =========================================================
# TERRAIN ANALYSIS
# =========================================================

def subset_terrain(
    terrain_gdf,
    start_mile,
    end_mile
):

    return terrain_gdf[
        (terrain_gdf["mile"] >= start_mile) &
        (terrain_gdf["mile"] <= end_mile)
    ].copy()


def compute_gain_loss(segment_terrain):

    gain = 0
    loss = 0

    elevations = list(
        segment_terrain["elevation_ft"]
    )

    if len(elevations) < 2:
        return 0, 0

    for i in range(1, len(elevations)):

        delta = elevations[i] - elevations[i - 1]

        if delta > 0:
            gain += delta
        else:
            loss += abs(delta)

    return round(gain), round(loss)


# =========================================================
# BUILD SEGMENTS
# =========================================================

def build_segments(
    spine_gdf,
    terrain_gdf,
    nodes_gdf
):

    print("\n[INFO] Building segments")

    segments = []

    spine_geom = spine_gdf.iloc[0].geometry

    for idx in range(len(nodes_gdf) - 1):

        start = nodes_gdf.iloc[idx]

        end = nodes_gdf.iloc[idx + 1]

        start_mile = float(
            start["mile_estimate"]
        )

        end_mile = float(
            end["mile_estimate"]
        )

        segment_miles = round(
            end_mile - start_mile,
            1
        )

        if segment_miles <= 0:
            continue

        segment_terrain = subset_terrain(
            terrain_gdf,
            start_mile,
            end_mile
        )

        gain_ft, loss_ft = compute_gain_loss(
            segment_terrain
        )

        gain_per_mile = round(
            gain_ft / segment_miles,
            1
        )

        difficulty = estimate_difficulty(
            gain_per_mile
        )

        est_hours = estimate_hours(
            segment_miles,
            gain_ft
        )

        start_frac = (
            start_mile /
            TOTAL_TRAIL_MILES
        )

        end_frac = (
            end_mile /
            TOTAL_TRAIL_MILES
        )

        start_pt = spine_geom.interpolate(
            start_frac,
            normalized=True
        )

        end_pt = spine_geom.interpolate(
            end_frac,
            normalized=True
        )

        segment_line = LineString([
            start_pt,
            end_pt
        ])

        segment = {

            "segment_id":
                make_segment_id(idx),

            "from_node":
                start.get(
                    "canonical_name",
                    "unknown"
                ),

            "to_node":
                end.get(
                    "canonical_name",
                    "unknown"
                ),

            "start_mile":
                start_mile,

            "end_mile":
                end_mile,

            "segment_miles":
                segment_miles,

            "gain_ft":
                gain_ft,

            "loss_ft":
                loss_ft,

            "gain_per_mile":
                gain_per_mile,

            "difficulty":
                difficulty,

            "estimated_hours":
                est_hours,

            "schema_version":
                SCHEMA_VERSION,

            "geometry":
                segment_line
        }

        segments.append(segment)

    return gpd.GeoDataFrame(
        segments,
        geometry="geometry",
        crs="EPSG:4326"
    )


# =========================================================
# EXPORT
# =========================================================

def export_segments(gdf):

    print("\n[EXPORTING]\n")

    geojson_path = (
        COMPILED_DIR /
        "segments.geojson"
    )

    json_path = (
        COMPILED_DIR /
        "segments.json"
    )

    gdf.to_file(
        geojson_path,
        driver="GeoJSON"
    )

    print(f"[OK] {geojson_path}")

    records = json.loads(
        gdf.drop(
            columns="geometry"
        ).to_json()
    )

    with open(
        json_path,
        "w"
    ) as f:

        json.dump(
            records,
            f,
            indent=2
        )

    print(f"[OK] {json_path}")


# =========================================================
# SUMMARY
# =========================================================

def summarize(gdf):

    print("\n[SUMMARY]\n")

    print(
        f"Segments: {len(gdf)}"
    )

    print(
        f"Total miles: "
        f"{round(gdf['segment_miles'].sum(), 1)}"
    )

    print(
        f"Total gain: "
        f"{round(gdf['gain_ft'].sum())} ft"
    )


# =========================================================
# MAIN
# =========================================================

def main():

    print(
        "\n=== CairnOS Segment Builder ==="
    )

    spine_gdf = load_spine()

    terrain_gdf = load_terrain()

    nodes_gdf = load_nodes()

    segments_gdf = build_segments(
        spine_gdf,
        terrain_gdf,
        nodes_gdf
    )

    export_segments(
        segments_gdf
    )

    summarize(
        segments_gdf
    )

    print("\n[DONE]\n")


if __name__ == "__main__":
    main()
