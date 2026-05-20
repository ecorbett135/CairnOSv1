# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0


def advisory_ids(
    advisories,
):
    return {
        advisory["id"]
        for advisory in advisories
    }


def test_no_start_date_returns_no_season_advisories(
    planner_factory,
):
    planner = planner_factory(
        user_profile={
            "direction": "NOBO",
        },
    )

    assert planner.build_season_advisories(28) == []


def test_april_start_flags_mud_shoulder_and_official_updates(
    planner_factory,
):
    planner = planner_factory(
        user_profile={
            "start_date": "2026-04-15",
        },
    )

    advisories = planner.build_season_advisories(10)
    ids = advisory_ids(
        advisories
    )

    assert {
        "official_trail_updates",
        "mud_season",
        "shoulder_snow_weather",
    }.issubset(ids)


def test_june_start_flags_peak_bugs_and_official_updates(
    planner_factory,
):
    planner = planner_factory(
        user_profile={
            "start_date": "2026-06-20",
        },
    )

    advisories = planner.build_season_advisories(10)
    ids = advisory_ids(
        advisories
    )

    assert "official_trail_updates" in ids
    assert "peak_bugs" in ids
    assert "mud_season" not in ids
    assert "shoulder_snow_weather" not in ids


def test_october_start_flags_hunting_shoulder_and_official_updates(
    planner_factory,
):
    planner = planner_factory(
        user_profile={
            "start_date": "2026-10-10",
        },
    )

    advisories = planner.build_season_advisories(10)
    ids = advisory_ids(
        advisories
    )

    assert {
        "official_trail_updates",
        "hunting_visibility",
        "shoulder_snow_weather",
    }.issubset(ids)


def test_late_july_start_only_flags_official_updates(
    planner_factory,
):
    planner = planner_factory(
        user_profile={
            "start_date": "2026-07-20",
        },
    )

    advisories = planner.build_season_advisories(10)

    assert advisory_ids(advisories) == {
        "official_trail_updates",
    }


def test_start_date_does_not_change_core_planner_outputs(
    planner_factory,
):
    base_profile = {
        "direction": "NOBO",
        "ingress_route": "North Adams Approach",
        "egress_route": "Journey's End Trail",
        "min_daily_miles": 8,
        "max_daily_miles": 16,
        "max_daily_elevation": 3500,
        "resupply_cadence": 5,
        "recovery_cadence": 6,
    }
    base_itinerary = planner_factory(
        user_profile=base_profile
    ).synthesize_itinerary(
        desired_days=28
    )
    dated_itinerary = planner_factory(
        user_profile={
            **base_profile,
            "start_date": "2026-06-20",
        }
    ).synthesize_itinerary(
        desired_days=28
    )

    for key in [
        "completion_analysis",
        "expedition_summary",
        "resupply_plan",
        "resupply_town_details",
        "directional_access",
        "daily_plan",
    ]:
        assert dated_itinerary[key] == base_itinerary[key]

    assert base_itinerary["season_advisories"] == []
    assert advisory_ids(
        dated_itinerary["season_advisories"]
    ) == {
        "official_trail_updates",
        "peak_bugs",
    }
