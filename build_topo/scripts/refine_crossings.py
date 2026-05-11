# refine_crossings.py

from pathlib import Path
import json
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

COMPILED_DIR = Path("data/compiled")

INPUT_FILE = COMPILED_DIR / "crossings.geojson"

OUTPUT_GEOJSON = COMPILED_DIR / "crossings_refined.geojson"
OUTPUT_JSON = COMPILED_DIR / "crossings_refined.json"

SCHEMA_VERSION = "0.2-draft"

KEEP_FCLASSES = {
    "motorway",
    "trunk",
    "primary",
    "secondary",
    "tertiary",
    "residential",
    "service",
    "track",
    "track_grade1",
    "track_grade2",
}

ROAD_CLASS_WEIGHTS = {
    "motorway": 10,
    "trunk": 9,
    "primary": 8,
    "secondary": 7,
    "tertiary": 6,
    "residential": 5,
    "service": 4,
    "track": 3,
    "track_grade1": 3,
    "track_grade2": 2,
}

CLUSTER_DISTANCE_METERS = 150


def normalize_columns(gdf):

    if "road_type" in gdf.columns:

        gdf["fclass"] = gdf["road_type"]

    if "fclass" not in gdf.columns:

        raise RuntimeError(
            "Missing road classification column"
        )

    return gdf


def filter_crossings(gdf):
    return gdf[gdf["fclass"].isin(KEEP_FCLASSES)].copy()


def score_crossings(gdf):
    gdf["road_weight"] = gdf["fclass"].map(
        ROAD_CLASS_WEIGHTS
    ).fillna(1)

    gdf["vehicle_access"] = gdf["road_weight"] >= 3

    gdf["likely_hitchable"] = gdf["road_weight"] >= 5

    gdf["winter_access"] = gdf["road_weight"] >= 6

    gdf["access_score"] = (
        gdf["road_weight"] / 10.0
    ).round(2)

    return gdf


def cluster_crossings(gdf):
    projected = gdf.to_crs(epsg=3857)

    clusters = []
    used = set()

    rows = list(projected.iterrows())

    for idx, row in rows:

        if idx in used:
            continue

        geom = row.geometry

        cluster = [idx]

        used.add(idx)

        for idx2, row2 in rows:

            if idx2 in used:
                continue

            dist = geom.distance(row2.geometry)

            if dist <= CLUSTER_DISTANCE_METERS:
                cluster.append(idx2)
                used.add(idx2)

        clusters.append(cluster)

    keep_rows = []

    for cluster in clusters:

        subset = gdf.loc[cluster]

        best = subset.sort_values(
            by="road_weight",
            ascending=False
        ).iloc[0]

        keep_rows.append(best)

    refined = gpd.GeoDataFrame(
        keep_rows,
        geometry="geometry",
        crs=gdf.crs
    )

    refined = refined.reset_index(drop=True)

    return refined


def assign_ids(gdf):

    ids = []

    for i in range(len(gdf)):
        ids.append(f"crossing_{i:04d}")

    gdf["crossing_id"] = ids

    return gdf


def export_outputs(gdf):

    gdf.to_file(
        OUTPUT_GEOJSON,
        driver="GeoJSON"
    )

    records = json.loads(
        gdf.to_json()
    )["features"]

    simplified = []

    for f in records:

        props = f["properties"]

        simplified.append(props)

    with open(OUTPUT_JSON, "w") as fp:
        json.dump(simplified, fp, indent=2)

    print(f"[OK] {OUTPUT_GEOJSON}")
    print(f"[OK] {OUTPUT_JSON}")


def main():

    print("\n=== CairnOS Crossing Refinement ===\n")

    print("[INFO] Loading crossings")

    gdf = gpd.read_file(INPUT_FILE)

    print(f"[INFO] Raw crossings: {len(gdf)}")

    gdf = normalize_columns(gdf)

    gdf = filter_crossings(gdf)

    print(f"[INFO] Filtered crossings: {len(gdf)}")

    gdf = score_crossings(gdf)

    gdf = cluster_crossings(gdf)

    print(f"[INFO] Clustered crossings: {len(gdf)}")

    gdf = assign_ids(gdf)

    gdf["schema_version"] = SCHEMA_VERSION

    print("\n[EXPORTING]\n")

    export_outputs(gdf)

    print("\n[DONE]\n")


if __name__ == "__main__":
    main()
