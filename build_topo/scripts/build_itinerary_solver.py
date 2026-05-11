#!/usr/bin/env python3

"""
build_itinerary_solver.py

Phase 4
CairnOS Itinerary Solver
"""

import sys
from pathlib import Path

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

# =========================================================
# LOAD GRAPH
# =========================================================

def load_graph():

    print("[INFO] Loading operational graph")

    with open(GRAPH_FILE) as fp:
        return json.load(fp)


# =========================================================
# BUILD ITINERARY
# =========================================================

def build_plan(graph):

    segments = graph.get("segments", [])

    itinerary = []

    current_day = 1

    accumulated = 0.0

    total_gain = 0

    day_segments = []

    for seg in segments:

        miles = seg.get("distance_miles", 0)

        if miles is None:
            miles = 0

        gain = seg.get("gain_ft", 0)

        if gain is None:
            gain = 0

        projected_total = accumulated + miles

        if (
            projected_total > TARGET_DAILY_MILES
            and len(day_segments) > 0
        ):

            itinerary.append({

                "day":
                    current_day,

                "segments":
                    day_segments,

                "total_miles":
                    round(accumulated, 1),

                "total_gain_ft":
                    round(total_gain)
            })

            current_day += 1

            accumulated = 0.0

            total_gain = 0

            day_segments = []

        day_segments.append({

            "segment_id":
                seg.get("segment_id"),

            "from_node":
                seg.get("start_node"),

            "to_node":
                seg.get("end_node"),

            "miles":
                miles,

            "gain_ft":
                gain,

            "difficulty":
                seg.get("difficulty")
        })

        accumulated += miles

        total_gain += gain

    if len(day_segments) > 0:

        itinerary.append({

            "day":
                current_day,

            "segments":
                day_segments,

            "total_miles":
                round(accumulated, 1),

            "total_gain_ft":
                round(total_gain)
        })

    return itinerary


# =========================================================
# SUMMARY
# =========================================================

def summarize(itinerary):

    total_days = len(itinerary)

    total_miles = round(

        sum(
            day["total_miles"]
            for day in itinerary
        ),

        1
    )

    total_gain = round(

        sum(
            day["total_gain_ft"]
            for day in itinerary
        )
    )

    return {

        "schema_version":
            SCHEMA_VERSION,

        "days":
            total_days,

        "total_miles":
            total_miles,

        "total_gain_ft":
            total_gain,

        "daily_target":
            TARGET_DAILY_MILES
    }


# =========================================================
# EXPORT
# =========================================================

def export_itinerary(
    itinerary,
    summary
):

    output = {

        "summary":
            summary,

        "itinerary":
            itinerary
    }

    with open(OUTPUT_FILE, "w") as fp:

        json.dump(
            output,
            fp,
            indent=2
        )

    print(f"[OK] {OUTPUT_FILE}")


# =========================================================
# MAIN
# =========================================================

def main():

    print(
        "\n=== CairnOS Itinerary Solver ===\n"
    )

    graph = load_graph()

    print(
        "\n[INFO] Building itinerary"
    )

    itinerary = build_plan(graph)

    summary = summarize(itinerary)

    print(
        "\n[EXPORTING]\n"
    )

    export_itinerary(
        itinerary,
        summary
    )

    print(
        "\n[SUMMARY]\n"
    )

    print(
        json.dumps(
            summary,
            indent=2
        )
    )

    print("\n[DONE]\n")


if __name__ == "__main__":
    main()
