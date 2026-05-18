# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import argparse
import json
import sys
from pathlib import Path

from cairn.planner.planner_v2 import PlannerV2


CONFIG_PATH = Path("cairn/config/scenarios.json")
TRAIL_ROOT = Path("trails/vermont_long_trail")


def load_scenarios(path):

    return json.loads(
        path.read_text()
    )


def default_access(direction):

    if direction == "SOBO":
        return (
            "Journey's End Trail",
            "Williamstown Approach",
        )

    return (
        "Williamstown Approach",
        "Journey's End Trail",
    )


def build_user_profile(config):

    direction = config.get(
        "direction",
        "NOBO",
    )

    ingress_route, egress_route = (
        default_access(direction)
    )

    return {
        "trip_type": config.get(
            "trip_type",
            "THRU",
        ),
        "direction": direction,
        "ingress_route": config.get(
            "ingress_route",
            ingress_route,
        ),
        "egress_route": config.get(
            "egress_route",
            egress_route,
        ),
        "min_daily_miles": config.get(
            "min_daily_miles",
            config.get("min_miles", 8),
        ),
        "max_daily_miles": config.get(
            "max_daily_miles",
            config.get("max_miles", 16),
        ),
        "max_daily_elevation": config.get(
            "max_daily_elevation",
            config.get("max_elevation", 3500),
        ),
        "resupply_cadence": config.get(
            "resupply_cadence",
            config.get("resupply_days", 5),
        ),
        "recovery_cadence": config.get(
            "recovery_cadence",
            config.get("recovery_days", 6),
        ),
        "min_nero_miles": config.get(
            "min_nero_miles",
            5,
        ),
        "max_nero_miles": config.get(
            "max_nero_miles",
            8,
        ),
        "allow_extra_resupply_only": config.get(
            "allow_extra_resupply_only",
            True,
        ),
    }


def summarize_itinerary(
    name,
    itinerary,
):

    daily_plan = itinerary.get(
        "daily_plan",
        [],
    )

    expedition_summary = itinerary.get(
        "expedition_summary",
        {},
    )

    completion_analysis = itinerary.get(
        "completion_analysis",
        {},
    )

    return {
        "scenario": name,
        "status": "ok",
        "summary": {
            "days": expedition_summary.get(
                "completion_days",
                len(daily_plan),
            ),
            "moving_days": expedition_summary.get(
                "moving_days",
            ),
            "total_miles": expedition_summary.get(
                "total_miles",
            ),
            "recommended_days":
                completion_analysis.get(
                    "recommended_days",
                ),
            "final_stop": (
                daily_plan[-1].get(
                    "daily_stop_location",
                )
                if daily_plan
                else None
            ),
        },
    }


def run_scenario(
    name,
    config,
    trail_root,
):

    try:

        planner = PlannerV2(
            trail_root=trail_root,
            user_profile=build_user_profile(
                config
            ),
        )

        itinerary = planner.synthesize_itinerary(
            desired_days=config.get(
                "desired_days",
                28,
            )
        )

        return summarize_itinerary(
            name,
            itinerary,
        )

    except Exception as exc:

        return {
            "scenario": name,
            "status": "error",
            "error": str(exc),
        }


def main(argv=None):

    parser = argparse.ArgumentParser(
        description=(
            "Run configured CairnOS PlannerV2 "
            "smoke scenarios."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=CONFIG_PATH,
    )
    parser.add_argument(
        "--trail-root",
        type=Path,
        default=TRAIL_ROOT,
    )

    args = parser.parse_args(argv)

    scenarios = load_scenarios(
        args.config
    )

    results = [
        run_scenario(
            name,
            config,
            args.trail_root,
        )
        for name, config in scenarios.items()
    ]

    passed = all(
        result["status"] == "ok"
        for result in results
    )

    payload = {
        "status": (
            "success"
            if passed
            else "error"
        ),
        "scenarios": results,
    }

    print(
        json.dumps(
            payload,
            indent=2,
        )
    )

    return 0 if passed else 1


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
