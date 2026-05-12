from pathlib import Path
import sys
import json

import pandas as pd


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

def make_overlay_id(idx):

    return f"overlay_{idx:04d}"


def normalize_bool(value):

    if pd.isna(value):
        return False

    if isinstance(value, bool):
        return value

    value = str(value).strip().lower()

    return value in [
        "1",
        "true",
        "yes",
        "y",
    ]


def normalize_float(value):

    if pd.isna(value):
        return None

    try:
        return float(value)

    except Exception:
        return None


def normalize_text(value):

    if pd.isna(value):
        return None

    value = str(value).strip()

    if value == "":
        return None

    return value


#
# ---------------------------------------------------------
# LOADERS
# ---------------------------------------------------------
#

def load_route_master():

    print("\n[INFO] Loading route_master")

    route_master_path = (
        RAW_DIR /
        "csv" /
        "route_master.csv"
    )

    if not route_master_path.exists():

        raise FileNotFoundError(
            f"Missing route_master.csv: "
            f"{route_master_path}"
        )

    df = pd.read_csv(
        route_master_path
    )

    print(
        f"[INFO] Route master rows: "
        f"{len(df)}"
    )

    return df


def load_segments():

    print("\n[INFO] Loading segments")

    path = (
        COMPILED_DIR /
        "segments.json"
    )

    if not path.exists():

        raise FileNotFoundError(
            f"Missing segments: {path}"
        )

    with open(path) as f:

        rows = json.load(f)

    print(
        f"[INFO] Segments: "
        f"{len(rows)}"
    )

    return rows


#
# ---------------------------------------------------------
# OVERLAY BUILD
# ---------------------------------------------------------
#

def classify_node(row):

    name = (
        normalize_text(
            row.get("location")
        ) or ""
    ).lower()

    if "shelter" in name:
        return "shelter"

    if "camp" in name:
        return "camp"

    if "parking" in name:
        return "trailhead"

    if "road" in name:
        return "crossing"

    return "operational_node"


def build_overlay_nodes(df):

    print(
        "\n[INFO] Building overlay nodes"
    )

    nodes = []

    for idx, row in df.iterrows():

        trail_mile = normalize_float(
            row.get(
                "miles_from_MA_border_nb"
            )
        )

        if trail_mile is None:

            trail_mile = normalize_float(
                row.get(
                    "mile"
                )
            )

        node = {

            "overlay_id":
            make_overlay_id(idx),

            "canonical_name":
            normalize_text(
                row.get("location")
            ),

            "trail_mile":
            trail_mile,

            "node_class":
            classify_node(row),

            "division":
            normalize_text(
                row.get("division")
            ),

            "road_crossing":
            normalize_text(
                row.get("location")
            ),

            "town_access":
            normalize_text(
                row.get("town_access")
            ),

            "approach_trail": (
                normalize_text(
                    row.get("division")
                ) == "division0"
            ),

            "overnight":
            normalize_bool(
                row.get(
                    "overnight"
                )
            ),

            "logistics":
            normalize_bool(
                row.get(
                    "logistics"
                )
            ),

            "water":
            normalize_bool(
                row.get(
                    "water"
                )
            ),

            "shelter": (
                "shelter" in (
                    normalize_text(
                        row.get("location")
                    ) or ""
                ).lower()
            ),

            "camping": (
                "camp" in (
                    normalize_text(
                        row.get("location")
                    ) or ""
                ).lower()
            ),

            "resupply":
            normalize_bool(
                row.get(
                    "resupply"
                )
            ),

            "schema_version":
            SCHEMA_VERSION,
        }

        nodes.append(node)

    #
    # authoritative operational ordering
    #

    nodes = sorted(

        nodes,

        key=lambda x: (
            x["trail_mile"]
            if x["trail_mile"] is not None
            else 999999
        ),
    )

    print(
        f"[INFO] Overlay nodes: "
        f"{len(nodes)}"
    )

    return nodes


def build_operational_segments(
    overlay_nodes
):

    print(
        "\n[INFO] Building operational segments"
    )

    segments = []

    for idx in range(
        len(overlay_nodes) - 1
    ):

        current = overlay_nodes[idx]

        nxt = overlay_nodes[idx + 1]

        start_mile = (
            current.get(
                "trail_mile"
            )
        )

        end_mile = (
            nxt.get(
                "trail_mile"
            )
        )

        if (
            start_mile is None
            or end_mile is None
        ):
            continue

        distance = round(
            end_mile - start_mile,
            1,
        )

        if distance <= 0:
            continue

        segment = {

            "segment_id":
            f"overlay_segment_{idx:04d}",

            "start_node":
            current.get(
                "overlay_id"
            ),

            "end_node":
            nxt.get(
                "overlay_id"
            ),

            "start_name":
            current.get(
                "canonical_name"
            ),

            "end_name":
            nxt.get(
                "canonical_name"
            ),

            "distance": distance,

            "schema_version":
            SCHEMA_VERSION,
        }

        segments.append(segment)

    print(
        f"[INFO] Operational segments: "
        f"{len(segments)}"
    )

    return segments


#
# ---------------------------------------------------------
# EXPORT
# ---------------------------------------------------------
#

def export_overlay(
    overlay_nodes,
    operational_segments,
):

    overlay = {

        "schema_version":
        SCHEMA_VERSION,

        "trail":
        trail_root.name,

        "overlay_nodes":
        overlay_nodes,

        "operational_segments":
        operational_segments,
    }

    output_path = (
        COMPILED_DIR /
        "route_overlay.json"
    )

    with open(
        output_path,
        "w",
    ) as f:

        json.dump(
            overlay,
            f,
            indent=2,
        )

    print("")
    print("[EXPORTING]")
    print("")

    print(
        f"[OK] {output_path}"
    )


#
# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
#

def main():

    print("")
    print(
        "=== CairnOS Route Overlay Builder ==="
    )
    print("")

    #
    # load
    #

    route_master_df = (
        load_route_master()
    )

    load_segments()

    #
    # build
    #

    overlay_nodes = (
        build_overlay_nodes(
            route_master_df
        )
    )

    operational_segments = (
        build_operational_segments(
            overlay_nodes
        )
    )

    #
    # export
    #

    export_overlay(

        overlay_nodes,
        operational_segments,
    )

    #
    # summary
    #

    print("")
    print("[SUMMARY]")
    print("")

    print(
        f"Overlay nodes: "
        f"{len(overlay_nodes)}"
    )

    print(
        f"Operational segments: "
        f"{len(operational_segments)}"
    )

    print("")
    print("[DONE]")


if __name__ == "__main__":

    main()