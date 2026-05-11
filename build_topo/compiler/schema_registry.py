# build_schema_registry.py

from pathlib import Path
import json

OUTPUT = Path(
    str(COMPILED_DIR) + "/cairn_schema_registry.json"
)

SCHEMA = {

    "schema_version": "0.3-draft",

    "datasets": {

        "spine": {

            "description":
                "Canonical LT spine geometry",

            "required_fields": [
                "geometry"
            ]
        },

        "terrain": {

            "description":
                "Terrain sampling profile",

            "required_fields": [
                "mile",
                "elevation_ft",
                "geometry"
            ]
        },

        "nodes": {

            "description":
                "Canonical overnight nodes",

            "required_fields": [
                "node_id",
                "canonical_name",
                "canonical_type",
                "mile_estimate",
                "trail_order",
                "node_class",
                "geometry"
            ]
        },

        "segments": {

            "description":
                "Operational trail segments",

            "required_fields": [
                "segment_id",
                "from_node",
                "to_node",
                "start_mile",
                "end_mile",
                "segment_miles",
                "gain_ft",
                "loss_ft",
                "difficulty",
                "estimated_hours",
                "geometry"
            ]
        },

        "crossings": {

            "description":
                "Road/trail crossings",

            "required_fields": [
                "crossing_id",
                "name",
                "road_type",
                "trail_mile",
                "vehicle_access",
                "access_score",
                "geometry"
            ]
        },

        "logistics_nodes": {

            "description":
                "Resupply and recovery nodes",

            "required_fields": [
                "logistics_id",
                "town",
                "division",
                "grocery",
                "post_office",
                "zero_candidate",
                "nero_candidate"
            ]
        },

        "operational_graph": {

            "description":
                "Unified operational planning graph",

            "required_fields": [
                "segments",
                "nodes",
                "crossings"
            ]
        },

        "itinerary": {

            "description":
                "Generated hiking itinerary",

            "required_fields": [
                "summary",
                "itinerary"
            ]
        }
    }
}


def main():

    print(
        "\n=== CairnOS Schema Registry Builder ===\n"
    )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(OUTPUT, "w") as fp:

        json.dump(
            SCHEMA,
            fp,
            indent=2
        )

    print(f"[OK] {OUTPUT}")

    print("\n[DONE]\n")


if __name__ == "__main__":
    main()
