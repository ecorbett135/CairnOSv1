# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
def test_terrain_helper_matches_planner_facade(planner):
    """Test terrain helper remains behaviorally identical to PlannerV2."""
    helper_interval = planner.terrain.analyze_terrain_interval(
        40.0,
        50.0,
    )
    facade_interval = planner.analyze_terrain_interval(
        40.0,
        50.0,
    )

    assert helper_interval == facade_interval
    assert helper_interval["source"] == "terrain"


def test_logistics_helper_matches_planner_facade(planner):
    """Test logistics helper preserves scoring and sparse note rules."""
    candidates = planner.build_logistics_candidates()
    candidate = next(
        node for node in candidates
        if planner.is_resupply_candidate(node)
    )

    assert (
        planner.logistics.score_resupply_candidate(
            candidate
        )
        == planner.score_resupply_candidate(
            candidate
        )
    )
    assert (
        planner.logistics.build_logistics_note(
            resupply_node=candidate,
            recovery_kind="nero",
        )
        == "resupply / nero"
    )
    assert (
        planner.build_logistics_note(
            recovery_kind="zero"
        )
        == "zero"
    )


def test_validated_lodging_rows_cover_key_recovery_towns(planner):
    """Test curated lodging includes high-value recovery corridors."""
    lodging_names = {
        option["display_name"]
        for option in (
            planner.logistics
            .load_town_lodging_options()
        )
    }

    assert "The Inn at Long Trail" in lodging_names
    assert "Old Stagecoach Inn" in lodging_names
    assert "Hotel Downstreet" in lodging_names
    assert "Hampton Inn Bennington" in lodging_names


def test_validated_lodging_strength_improves_recovery_score(planner):
    """Test validated lodging has more recovery weight than generic lodging."""
    logistics = planner.logistics
    candidates = logistics.build_logistics_candidates()
    waterbury = next(
        node for node in candidates
        if (
            logistics.resupply_node_id(node)
            == "Duxbury Road:181.6"
        )
    )
    generic = {
        "canonical_name": "Generic Lodging Access",
        "town_access": "Generic Town",
        "resupply_services": [
            "lodging",
            "restaurants",
        ],
        "resupply_amenity": {
            "lodging": True,
            "restaurants": True,
            "zero_candidate": False,
        },
    }

    assert (
        logistics.has_validated_lodging(
            waterbury
        )
        is True
    )
    assert (
        logistics.validated_lodging_strength_bonus(
            waterbury
        )
        > 0
    )
    assert (
        logistics.score_recovery_candidate(
            waterbury
        )
        > logistics.score_recovery_candidate(
            generic
        )
    )


def test_itinerary_builder_matches_planner_facade_stop_selection(planner):
    """Test extracted itinerary stop selection stays behind facade."""
    operational_nodes = (
        planner.queries
        .get_operational_overnight_nodes()
    )
    logistics_nodes = (
        planner.queries
        .get_logistics_access_nodes()
    )

    helper_stop = (
        planner.itinerary_builder
        .select_operational_stop(
            target_mile=100.0,
            operational_overnight_nodes=operational_nodes,
            logistics_nodes=logistics_nodes,
            current_mile=90.0,
        )
    )
    facade_stop = planner.select_operational_stop(
        target_mile=100.0,
        operational_overnight_nodes=operational_nodes,
        logistics_nodes=logistics_nodes,
        current_mile=90.0,
    )

    assert helper_stop == facade_stop
    assert facade_stop is not None
