def test_shelter_nodes_available(shelter_nodes):
    """Test that shelter nodes are loaded from the operational graph."""
    assert len(shelter_nodes) > 0

    for shelter in shelter_nodes:
        assert "canonical_name" in shelter
        assert "trail_mile" in shelter
        assert shelter.get("shelter") is True


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
