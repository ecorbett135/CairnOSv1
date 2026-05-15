# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path

from app.core.planner import run_planner


CONFIG_PATH = Path("config/scenarios.json")


# =========================================================
# LOAD SCENARIOS
# =========================================================


def load_scenarios():

    with open(CONFIG_PATH) as fp:

        return json.load(fp)


# =========================================================
# RUN SCENARIO
# =========================================================


def run_scenario(name, config):

    try:

        result = run_planner(
            direction="NOBO",
            trip_type="THRU",
            min_miles=config.get("min_miles", 8),
            max_miles=config.get("max_miles", 15),
            max_elevation_gain=config.get(
                "max_elevation",
                5000,
            ),
            resupply_days=config.get(
                "resupply_days",
                4,
            ),
            approach_trail=config.get(
                "approach_trail",
                False,
            ),
        )

        return {
            "scenario": name,
            "status": "ok",
            "error": None,
            "summary": {
                "days": result.get(
                    "total_days",
                    0,
                ),
                "total_distance": result.get(
                    "total_distance",
                    0,
                ),
            },
        }

    except Exception as e:

        return {
            "scenario": name,
            "status": "error",
            "error": str(e),
        }


# =========================================================
# MAIN
# =========================================================


def main():

    print(
        "\n=== CairnOS Scenario Runner ===\n"
    )

    scenarios = load_scenarios()

    results = []

    for name, config in scenarios.items():

        print(f"[RUNNING] {name}")

        result = run_scenario(
            name,
            config,
        )

        results.append(result)

        print(
            f"[{result['status'].upper()}] {name}"
        )

        if result["error"]:

            print(result["error"])

    payload = {
        "status": "success",
        "scenarios": results,
    }

    print("\n[SUMMARY]\n")

    print(
        json.dumps(
            payload,
            indent=2,
        )
    )


if __name__ == "__main__":

    main()
