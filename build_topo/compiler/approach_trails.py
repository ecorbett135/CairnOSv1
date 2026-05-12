from pathlib import Path
import csv
import json
import sys


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

CSV_DIR = RAW_DIR / "csv"

APPROACH_CSV = (
    CSV_DIR /
    "approach_trails.csv"
)

OUTPUT_PATH = (
    COMPILED_DIR /
    "approach_trails.json"
)


#
# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
#


def load_approach_rows():

    if not APPROACH_CSV.exists():

        raise FileNotFoundError(
            f"Missing approach trail CSV: {APPROACH_CSV}"
        )

    rows = []

    with open(APPROACH_CSV, newline="") as f:

        reader = csv.DictReader(f)

        for row in reader:

            rows.append(
                {
                    "route": row.get("route", "").strip(),

                    "approach_id": row.get(
                        "approach_id",
                        ""
                    ).strip(),

                    "approach_name": row.get(
                        "approach_name",
                        ""
                    ).strip(),

                    "direction": row.get("direction", "").strip(),
                    "connected_terminus": row.get(
                        "connected_terminus",
                        ""
                    ).strip(),
                    "trail_miles": float(
                        row.get("trail_miles", 0)
                    ),
                    "elevation_gain_ft": float(
                        row.get(
                            "elevation_gain_ft",
                            0
                        )
                    ),
                    "start_location": row.get(
                        "start_location",
                        ""
                    ).strip(),
                    "end_location": row.get(
                        "end_location",
                        ""
                    ).strip(),
                    "route_name": row.get(
                        "route_name",
                        ""
                    ).strip(),
                    "sequence": int(
                        row.get("sequence", 0)
                    ),
                    "cumulative_to_trail_mi": float(
                        row.get(
                            "cumulative_to_trail_mi",
                            0
                        )
                    ),
                    "node_class": row.get(
                        "node_class",
                        ""
                    ).strip(),
                    "overnight": row.get(
                        "overnight",
                        ""
                    ).strip(),
                    "camping": row.get(
                        "camping",
                        ""
                    ).strip(),
                    "road_access": row.get(
                        "road_access",
                        ""
                    ).strip(),
                    "notes": row.get(
                        "notes",
                        ""
                    ).strip(),
                }
            )

    return rows


#
# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
#


def main():

    print("")
    print(
        "=== CairnOS Approach Trail Builder ==="
    )
    print("")

    print(
        "[INFO] Loading approach trails"
    )

    rows = load_approach_rows()

    print(
        f"[INFO] Approach trail rows: {len(rows)}"
    )

    payload = {
        "trail_system": trail_root.name,
        "approach_trails": rows,
    }

    print("")
    print("[EXPORTING]")
    print("")

    with open(OUTPUT_PATH, "w") as f:

        json.dump(
            payload,
            f,
            indent=2,
        )

    print(
        f"[OK] {OUTPUT_PATH}"
    )

    print("")
    print("[SUMMARY]")
    print("")

    print(
        f"Approach trails: {len(rows)}"
    )

    print("")
    print("[DONE]")


if __name__ == "__main__":

    main()
