# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
def test_shelter_nodes_available(shelter_nodes):
    """Test that shelter nodes are loaded from the operational graph."""
    assert len(shelter_nodes) > 0

    for shelter in shelter_nodes:
        assert "canonical_name" in shelter
        assert "trail_mile" in shelter
        assert shelter.get("shelter") is True


def test_runtime_logistics_summary_available(planner):
    """Test that compiled logistics nodes are visible at runtime."""
    assert planner.runtime.summary()["logistics"] > 0


def test_shelter_prioritization(planner):
    """Test that shelters have priority 1 in operational overnight nodes."""
    operational_nodes = planner.queries.get_operational_overnight_nodes()
    shelters = [n for n in operational_nodes if n["type"] == "shelter"]

    for shelter in shelters:
        assert shelter["priority"] == 1


def test_operational_stop_selection_near_target(planner):
    """Test that select_operational_stop finds nodes near target mile."""
    operational_nodes = planner.queries.get_operational_overnight_nodes()
    logistics_nodes = planner.queries.get_logistics_access_nodes()

    selected_stop = planner.select_operational_stop(
        target_mile=10.0,
        operational_overnight_nodes=operational_nodes,
        logistics_nodes=logistics_nodes,
    )

    assert selected_stop is not None
    stop_mile = selected_stop.get("trail_mile", 0)
    assert abs(stop_mile - 10.0) <= 4.0


def test_operational_stop_selection_expands_after_primary_miss(planner):
    """Test that stop selection expands to eight miles when needed."""
    operational_nodes = [
        {
            "node": {
                "canonical_name": "Far Shelter",
                "trail_mile": 106.2,
                "shelter": True,
            },
            "priority": 1,
            "type": "shelter",
        }
    ]

    selected_stop = planner.select_operational_stop(
        target_mile=100.0,
        operational_overnight_nodes=operational_nodes,
        logistics_nodes=[],
    )

    assert selected_stop is not None
    assert selected_stop["canonical_name"] == "Far Shelter"
    assert 4.0 < abs(selected_stop["trail_mile"] - 100.0) <= 8.0


def test_resupply_access_nodes_available(planner):
    """Test that resupply candidates come from operational overlay access."""
    resupply_nodes = planner.queries.get_resupply_access_nodes()

    assert len(resupply_nodes) > 0

    access_classes = {
        "crossing",
        "logistics",
        "trailhead",
        "access",
        "road_crossing",
    }

    for node in resupply_nodes:
        assert node.get("canonical_name")
        assert node.get("town_access")
        assert node.get("node_class") in access_classes
        assert (
            node.get("resupply")
            or node.get("logistics")
            or node.get("town_access")
        )

    assert any(
        node.get("town_access") == "Manchester Center"
        for node in resupply_nodes
    )


def test_nobo_itinerary_resupply_notes_use_access_nodes(planner_factory):
    """Test that resupply notes follow real access nodes, not raw cadence."""
    planner = planner_factory(
        user_profile={
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "resupply_cadence": 5,
            "min_daily_miles": 8,
            "max_daily_miles": 16,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=21
    )

    resupply_days = [
        day for day in itinerary["daily_plan"]
        if day["notes"]
    ]

    assert len(resupply_days) > 0

    allowed_notes = {
        "resupply",
        "zero",
        "resupply / zero",
    }

    for day in resupply_days:
        assert day["notes"] in allowed_notes
        assert day["resupply_location"]
        assert day["resupply_mile"] is not None
        assert day["town_access"]

    assert any(
        day["town_access"] == "Manchester Center"
        for day in resupply_days
    )

    assert any(
        "Rutland" in day["town_access"]
        for day in resupply_days
    )

    assert any(
        "Shelter" in day["daily_stop_location"]
        for day in resupply_days
    )

    resupply_plan_locations = {
        row["location"]
        for row in itinerary["resupply_plan"]
    }

    assert "Vt. 11/30" in resupply_plan_locations
