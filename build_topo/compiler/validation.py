# validate_dataset.py

from pathlib import Path
import json

import geopandas as gpd


COMPILED_DIR = Path(str(COMPILED_DIR) + "")

REGISTRY_FILE = (
    COMPILED_DIR /
    "cairn_schema_registry.json"
)

DATASETS = {

    "spine":
        COMPILED_DIR / "spine.geojson",

    "terrain":
        COMPILED_DIR / "terrain.geojson",

    "nodes":
        COMPILED_DIR / "nodes.geojson",

    "segments":
        COMPILED_DIR / "segments.geojson",

    "crossings":
        COMPILED_DIR /
        "crossings_refined.geojson",

    "logistics_nodes":
        COMPILED_DIR /
        "logistics_nodes.json",

    "operational_graph":
        COMPILED_DIR /
        "operational_graph.json",

    "itinerary":
        COMPILED_DIR /
        "itinerary.json",
}


# =========================================================
# HELPERS
# =========================================================

def load_registry():

    with open(REGISTRY_FILE) as fp:
        return json.load(fp)


def validate_file_exists(path):

    return path.exists()


def validate_geojson_fields(
    path,
    required_fields
):

    gdf = gpd.read_file(
        path,
        engine="fiona"
    )

    cols = set(gdf.columns)

    missing = []

    for field in required_fields:

        if field not in cols:
            missing.append(field)

    return missing


def validate_json_fields(
    path,
    required_fields
):

    with open(path) as fp:
        data = json.load(fp)

    missing = []

    # -------------------------------------------------
    # LIST-BASED JSON
    # -------------------------------------------------

    if isinstance(data, list):

        if len(data) == 0:

            return required_fields

        sample = data[0]

        for field in required_fields:

            if field not in sample:
                missing.append(field)

        return missing

    # -------------------------------------------------
    # OBJECT-BASED JSON
    # -------------------------------------------------

    if isinstance(data, dict):

        for field in required_fields:

            if field not in data:
                missing.append(field)

        return missing

    # -------------------------------------------------
    # UNKNOWN STRUCTURE
    # -------------------------------------------------

    return required_fields

# =========================================================
# DATASET VALIDATION
# =========================================================

def validate_dataset(
    dataset_name,
    path,
    spec
):

    print(f"\n[VALIDATING] {dataset_name}")

    if not validate_file_exists(path):

        print(f"[FAIL] Missing file: {path}")

        return False

    print(f"[OK] File exists")

    required_fields = spec.get(
        "required_fields",
        []
    )

    suffix = path.suffix.lower()

    missing = []

    try:

        if suffix == ".geojson":

            missing = validate_geojson_fields(
                path,
                required_fields
            )

        elif suffix == ".json":

            missing = validate_json_fields(
                path,
                required_fields
            )

    except Exception as e:

        print(f"[FAIL] Read error: {e}")

        return False

    if len(missing) > 0:

        print(
            f"[FAIL] Missing fields: "
            f"{missing}"
        )

        return False

    print("[OK] Required fields valid")

    return True


# =========================================================
# SPECIAL VALIDATION
# =========================================================

def validate_segments():

    print(
        "\n[CHECK] Segment continuity"
    )

    path = COMPILED_DIR / "segments.geojson"

    gdf = gpd.read_file(
        path,
        engine="fiona"
    )

    if len(gdf) == 0:

        print("[FAIL] No segments")

        return False

    total = gdf["segment_miles"].sum()

    print(
        f"[OK] Total segment miles: "
        f"{round(total,1)}"
    )

    nulls = gdf["segment_miles"].isnull().sum()

    if nulls > 0:

        print(
            f"[FAIL] Null segment distances: "
            f"{nulls}"
        )

        return False

    print("[OK] Segment distances valid")

    return True


def validate_nodes():

    print(
        "\n[CHECK] Node ordering"
    )

    path = COMPILED_DIR / "nodes.geojson"

    gdf = gpd.read_file(
        path,
        engine="fiona"
    )

    ordered = gdf.sort_values(
        by="trail_order"
    )

    miles = list(
        ordered["mile_estimate"]
    )

    for i in range(1, len(miles)):

        if miles[i] < miles[i - 1]:

            print(
                "[FAIL] Node mile ordering invalid"
            )

            return False

    print("[OK] Node ordering valid")

    return True


# =========================================================
# MAIN
# =========================================================

def main():

    print(
        "\n=== CairnOS Dataset Validation ==="
    )

    registry = load_registry()

    datasets = registry["datasets"]

    results = []

    for name, path in DATASETS.items():

        if name not in datasets:

            print(
                f"\n[WARN] No schema for {name}"
            )

            continue

        spec = datasets[name]

        result = validate_dataset(
            name,
            path,
            spec
        )

        results.append(result)

    results.append(
        validate_segments()
    )

    results.append(
        validate_nodes()
    )

    passed = results.count(True)

    total = len(results)

    print("\n[SUMMARY]\n")

    print(
        f"Passed: {passed}/{total}"
    )

    if passed == total:

        print(
            "\n[DATASET VALIDATION PASSED]"
        )

    else:

        print(
            "\n[DATASET VALIDATION FAILED]"
        )

    print("\n[DONE]\n")


if __name__ == "__main__":
    main()
