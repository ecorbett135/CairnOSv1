# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path

from cairn.export.plan_json import (
    PLAN_EXPORT_SCHEMA_VERSION,
    build_plan_export,
    dumps_plan_export,
    plan_export_filename,
)


REQUIRED_TOP_LEVEL_FIELDS = {
    "export_version",
    "generated_at",
    "build_sha",
    "trail_id",
    "planner",
    "user_profile",
    "completion_analysis",
    "expedition_summary",
    "directional_access",
    "resupply_plan",
    "resupply_town_details",
    "selected_experiences",
    "season_advisories",
    "daily_plan",
    "warnings",
}


def planner_result_for_export(
    planner_factory,
    trail_root,
    direction,
):
    user_profile = {
        "direction": direction,
        "trip_type": "THRU",
        "ingress_route": (
            "Journey's End Trail"
            if direction == "SOBO"
            else "North Adams Approach"
        ),
        "egress_route": (
            "Williamstown Approach"
            if direction == "SOBO"
            else "Journey's End Trail"
        ),
        "min_daily_miles": 8,
        "max_daily_miles": 16,
        "max_daily_elevation": 4000,
        "selected_side_trip_ids": [
            "ben_jerrys_factory"
        ],
    }
    planner = planner_factory(
        user_profile=user_profile,
    )
    itinerary = planner.synthesize_itinerary(
        desired_days=28
    )

    return {
        "config": {
            "selected_trail": "vermont_long_trail",
            "trail_root": str(trail_root.resolve()),
            "desired_days": 28,
            "direction": direction,
            "trip_type": "THRU",
            "external_debug_path": (
                "/Users/ecorbett/Downloads/private.gpx"
            ),
            **user_profile,
        },
        "itinerary": itinerary,
        "build_sha": "abcdef123456",
    }


def test_plan_json_export_contains_versioned_contract(
    planner_factory,
    trail_root,
):
    planner_result = planner_result_for_export(
        planner_factory,
        trail_root,
        "NOBO",
    )

    export = build_plan_export(
        planner_result,
        trail_root,
        "abcdef123456",
        generated_at="20260520T120000Z",
    )

    assert REQUIRED_TOP_LEVEL_FIELDS <= set(export)
    assert (
        export["export_version"]
        == PLAN_EXPORT_SCHEMA_VERSION
    )
    assert export["generated_at"] == "20260520T120000Z"
    assert export["build_sha"] == "abcdef123456"
    assert export["trail_id"] == "vermont_long_trail"
    assert export["planner"]["name"] == "PlannerV2"
    assert (
        export["planner"]["trail_root"]
        == "trails/vermont_long_trail"
    )
    assert (
        export["user_profile"]["trail_root"]
        == "trails/vermont_long_trail"
    )
    assert (
        export["user_profile"]["external_debug_path"]
        == "[redacted_path]"
    )
    assert export["daily_plan"]
    assert export["resupply_plan"]
    assert export["completion_analysis"]
    assert export["expedition_summary"]
    assert export["directional_access"]
    assert export["selected_experiences"]
    assert any(
        warning["code"] == "alpha_advisory"
        for warning in export["warnings"]
    )


def test_plan_json_export_is_deterministic_for_fixed_inputs(
    planner_factory,
    trail_root,
):
    planner_result = planner_result_for_export(
        planner_factory,
        trail_root,
        "NOBO",
    )
    first = dumps_plan_export(
        build_plan_export(
            planner_result,
            trail_root,
            "abcdef123456",
            generated_at="20260520T120000Z",
        )
    )
    second = dumps_plan_export(
        build_plan_export(
            planner_result,
            trail_root,
            "abcdef123456",
            generated_at="20260520T120000Z",
        )
    )

    assert first == second
    assert "/Users/" not in first
    assert "Downloads" not in first
    assert json.loads(first)["daily_plan"][0]["day"] == 1


def test_plan_json_export_preserves_sobo_semantics(
    planner_factory,
    trail_root,
):
    planner_result = planner_result_for_export(
        planner_factory,
        trail_root,
        "SOBO",
    )

    export = build_plan_export(
        planner_result,
        trail_root,
        "abcdef123456",
        generated_at="20260520T120000Z",
    )

    assert export["planner"]["direction"] == "SOBO"
    assert export["user_profile"]["direction"] == "SOBO"
    ingress_names = {
        row.get("approach_name")
        for row in export["directional_access"].get(
            "ingress",
            [],
        )
    }
    egress_names = {
        row.get("approach_name")
        for row in export["directional_access"].get(
            "egress",
            [],
        )
    }
    assert "Journey's End Trail" in ingress_names
    assert (
        "Williamstown Approach"
        in egress_names
    )
    moving_days = [
        row for row in export["daily_plan"]
        if row["daily_miles"] > 0
    ]
    assert moving_days
    assert all(
        row["daily_miles"] > 0
        for row in moving_days
    )


def test_plan_json_filename_is_stable_shape():
    filename = plan_export_filename(
        {
            "config": {
                "selected_trail": "vermont_long_trail",
                "direction": "NOBO",
            }
        },
        "abcdef1234567890",
        generated_at="20260520T120000Z",
    )

    assert filename == (
        "cairnos_plan_vermont_long_trail_nobo_"
        "20260520T120000Z_abcdef123456.json"
    )


def test_committed_plan_json_fixtures_match_schema():
    fixture_dir = (
        Path(__file__).parent
        / "fixtures"
        / "plan_json"
    )

    for path in fixture_dir.glob("*.json"):
        payload = json.loads(
            path.read_text()
        )

        assert REQUIRED_TOP_LEVEL_FIELDS <= set(payload)
        assert (
            payload["export_version"]
            == PLAN_EXPORT_SCHEMA_VERSION
        )
