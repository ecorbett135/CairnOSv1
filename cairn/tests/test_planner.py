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


def test_enriched_overnight_reference_stops_are_available(planner):
    """Test compiled overnight references extend stop options."""
    operational_nodes = (
        planner.queries
        .get_operational_overnight_nodes()
    )

    reference_nodes = [
        item for item in operational_nodes
        if item["node"].get(
            "overnight_reference"
        )
    ]

    assert reference_nodes
    assert any(
        item["node"]["canonical_name"]
        == "Taylor Lodge"
        for item in reference_nodes
    )

    taylor = next(
        item for item in reference_nodes
        if item["node"]["canonical_name"]
        == "Taylor Lodge"
    )

    assert taylor["priority"] == 1
    assert taylor["type"] == "shelter"
    assert taylor["node"]["shelter"] is True


def test_enriched_overnight_reference_can_be_selected(planner):
    """Test stop selection can choose an enriched overnight site."""
    operational_nodes = (
        planner.queries
        .get_operational_overnight_nodes()
    )

    selected_stop = planner.select_operational_stop(
        target_mile=201.0,
        operational_overnight_nodes=operational_nodes,
        logistics_nodes=[],
        current_mile=190.0,
    )

    assert selected_stop is not None
    assert selected_stop["canonical_name"] == "Taylor Lodge"
    assert selected_stop["overnight_reference"] is True


def test_enriched_overnight_reference_selection_has_direction_parity(
    planner_factory,
):
    """Test enriched stops can be selected in NOBO and SOBO traversal."""
    cases = [
        (
            "NOBO",
            190.0,
            201.0,
            "Taylor Lodge",
        ),
        (
            "SOBO",
            212.0,
            201.0,
            "Taylor Lodge",
        ),
        (
            "NOBO",
            240.0,
            249.8,
            "Tillotson Camp",
        ),
        (
            "SOBO",
            260.0,
            249.8,
            "Tillotson Camp",
        ),
    ]

    for (
        direction,
        current_mile,
        target_mile,
        expected_name,
    ) in cases:

        planner = planner_factory(
            user_profile={
                "direction": direction,
            },
        )

        operational_nodes = (
            planner.queries
            .get_operational_overnight_nodes()
        )

        selected_stop = (
            planner.select_operational_stop(
                target_mile=target_mile,
                operational_overnight_nodes=(
                    operational_nodes
                ),
                logistics_nodes=[],
                current_mile=current_mile,
            )
        )

        assert selected_stop is not None
        assert (
            selected_stop["canonical_name"]
            == expected_name
        )
        assert (
            selected_stop["overnight_reference"]
            is True
        )


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
        "nero",
        "zero",
        "resupply / nero",
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
        day["daily_stop_location_type"] in {
            "crossing",
            "logistics",
            "trailhead",
        }
        for day in resupply_days
    )

    resupply_plan_locations = {
        row["location"]
        for row in itinerary["resupply_plan"]
    }

    assert itinerary["resupply_plan"][0]["day"] == 1
    assert (
        itinerary["resupply_plan"][0]["notes"]
        == "start"
    )
    assert (
        itinerary["resupply_plan"][0][
            "days_to_next_resupply"
        ]
        > 0
    )
    assert "Vt. 11/30" in resupply_plan_locations


def test_resupply_and_recovery_cadence_are_separate(planner_factory):
    """Test separate food-carry and recovery cadence behavior."""
    planner = planner_factory(
        user_profile={
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "resupply_cadence": 5,
            "recovery_cadence": 6,
            "allow_extra_resupply_only": True,
            "min_daily_miles": 8,
            "max_daily_miles": 12,
            "max_daily_elevation": 3750,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=28
    )

    rows = itinerary["daily_plan"]

    allowed_notes = {
        "resupply",
        "nero",
        "zero",
        "resupply / nero",
        "resupply / zero",
    }

    noted_rows = [
        row for row in rows
        if row.get("notes")
    ]

    assert noted_rows

    for row in noted_rows:
        assert row["notes"] in allowed_notes

    zero_rows = [
        row for row in rows
        if "zero" in row.get("notes", "")
    ]

    assert zero_rows

    for row in zero_rows:
        assert row["daily_miles"] == 0.0
        assert row["daily_start_mile"] == row["daily_stop_mile"]
        assert (
            row["daily_start_location"]
            == row["daily_stop_location"]
        )
        assert (
            row["daily_start_location_type"]
            == row["daily_stop_location_type"]
        )

    resupply_rows = [
        row for row in rows
        if "resupply" in row.get("notes", "")
    ]

    assert resupply_rows

    for row in resupply_rows:
        assert (
            row["food_carry_days_since_last_resupply"]
            == 0
        )

    assert any(
        row["notes"] == "resupply"
        for row in resupply_rows
    )

    assert any(
        row["notes"] == "resupply / zero"
        for row in zero_rows
    )


def test_extra_resupply_only_stops_can_be_disabled(planner_factory):
    """Test standalone resupply cadence does not force recovery stops."""
    profile = {
        "direction": "NOBO",
        "ingress_route": "North Adams Approach",
        "resupply_cadence": 5,
        "recovery_cadence": 6,
        "min_daily_miles": 8,
        "max_daily_miles": 12,
    }

    with_extra = planner_factory(
        user_profile={
            **profile,
            "allow_extra_resupply_only": True,
        },
    ).synthesize_itinerary(
        desired_days=28
    )

    without_extra = planner_factory(
        user_profile={
            **profile,
            "allow_extra_resupply_only": False,
        },
    ).synthesize_itinerary(
        desired_days=28
    )

    with_resupply_only = [
        row for row in with_extra["daily_plan"]
        if row.get("notes") == "resupply"
    ]

    without_resupply_only = [
        row for row in without_extra["daily_plan"]
        if row.get("notes") == "resupply"
    ]

    assert len(with_resupply_only) > len(
        without_resupply_only
    )


def test_daily_elevation_gain_is_not_capped_by_user_limit(planner_factory):
    """Test displayed daily gain reports estimated gain, not the max limit."""
    low_limit_planner = planner_factory(
        user_profile={
            "max_daily_elevation": 3500,
        },
    )

    high_limit_planner = planner_factory(
        user_profile={
            "max_daily_elevation": 6000,
        },
    )

    low_limit_gain = (
        low_limit_planner.calculate_daily_elevation(
            daily_miles=14.9,
            day=24,
        )
    )

    high_limit_gain = (
        high_limit_planner.calculate_daily_elevation(
            daily_miles=14.9,
            day=24,
        )
    )

    assert low_limit_gain == high_limit_gain
    assert low_limit_gain > 3500


def test_itinerary_elevation_gain_can_exceed_requested_limit(planner_factory):
    """Test itinerary rows are not overwritten by the elevation slider cap."""
    planner = planner_factory(
        user_profile={
            "direction": "NOBO",
            "ingress_route": "Williamstown Approach",
            "egress_route": "Journey's End Trail",
            "min_daily_miles": 8,
            "max_daily_miles": 16,
            "max_daily_elevation": 3500,
            "resupply_cadence": 99,
            "recovery_cadence": 99,
            "allow_extra_resupply_only": False,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=28
    )

    daily_gains = [
        row["daily_elevation_gain"]
        for row in itinerary["daily_plan"]
        if row["daily_miles"] > 0
    ]

    assert max(daily_gains) > 3500

    capped_rows = [
        gain for gain in daily_gains
        if gain == 3500
    ]

    assert not capped_rows


def test_elevation_exceptions_escalate_feasibility(planner_factory):
    """Test fixed-duration plans complete and flag elevation exceptions."""
    planner = planner_factory(
        user_profile={
            "trip_type": "THRU",
            "direction": "NOBO",
            "ingress_route": "Williamstown Approach",
            "egress_route": "Journey's End Trail",
            "min_daily_miles": 9,
            "max_daily_miles": 15,
            "max_daily_elevation": 3500,
            "resupply_cadence": 99,
            "recovery_cadence": 99,
            "allow_extra_resupply_only": False,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=28
    )

    completion = itinerary[
        "completion_analysis"
    ]

    assert completion[
        "accepted"
    ] is True
    assert completion[
        "has_itinerary_exceptions"
    ] is True
    assert (
        completion["evaluation"]["classification"]
        == "aggressive"
    )

    assert (
        itinerary["daily_plan"][-1][
            "daily_stop_location"
        ]
        == "Journey's End Trail Parking"
    )

    elevation_exception = next(
        row for row in completion[
            "itinerary_exceptions"
        ]
        if row["constraint"] == "daily_elevation_gain"
    )

    assert elevation_exception["limit"] == 3500
    assert elevation_exception["observed_max"] > 3500
    assert elevation_exception["count"] > 0


def test_late_recovery_zero_does_not_replace_final_egress(
    planner_factory,
):
    """Test final completion takes priority over late recovery zeros."""
    planner = planner_factory(
        user_profile={
            "trip_type": "THRU",
            "direction": "NOBO",
            "ingress_route": "Williamstown Approach",
            "egress_route": "Journey's End Trail",
            "min_daily_miles": 9,
            "max_daily_miles": 15,
            "max_daily_elevation": 3500,
            "resupply_cadence": 5,
            "recovery_cadence": 6,
            "allow_extra_resupply_only": True,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=28
    )

    last_day = itinerary["daily_plan"][-1]

    assert last_day["day"] == 28
    assert (
        last_day["daily_stop_location"]
        == "Journey's End Trail Parking"
    )
    assert last_day["daily_stop_mile"] == 273.3
    assert last_day["daily_miles"] > 0
    assert last_day["notes"] == ""


def test_sobo_itinerary_descends_with_positive_travel_miles(planner_factory):
    """Test SOBO traverses south using northbound-reference miles."""
    planner = planner_factory(
        user_profile={
            "trip_type": "THRU",
            "direction": "SOBO",
            "ingress_route": "Journey's End Trail",
            "egress_route": "Williamstown Approach",
            "min_daily_miles": 9,
            "max_daily_miles": 15,
            "max_daily_elevation": 4000,
            "resupply_cadence": 7,
            "recovery_cadence": 5,
            "allow_extra_resupply_only": True,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=28
    )

    rows = itinerary["daily_plan"]

    assert len(rows) > 1

    first_day = rows[0]
    last_day = rows[-1]

    assert (
        first_day["daily_start_location"]
        == "Journey's End Trail"
    )
    assert (
        first_day["daily_stop_mile"]
        < first_day["daily_start_mile"]
    )
    assert (
        last_day["daily_stop_location"]
        == "Pine Cobble Road in Williamstown"
    )
    assert last_day["daily_stop_mile"] == -3.3

    for row in rows:

        if row["daily_miles"] == 0.0:
            assert "zero" in row.get("notes", "")
            continue

        assert row["daily_miles"] > 0
        assert (
            row["daily_stop_mile"]
            < row["daily_start_mile"]
        )


def test_sobo_resupply_strategy_is_populated(planner_factory):
    """Test SOBO produces resupply rows from valid amenity data."""
    planner = planner_factory(
        user_profile={
            "trip_type": "THRU",
            "direction": "SOBO",
            "ingress_route": "Journey's End Trail",
            "egress_route": "Williamstown Approach",
            "min_daily_miles": 9,
            "max_daily_miles": 15,
            "resupply_cadence": 7,
            "recovery_cadence": 5,
            "allow_extra_resupply_only": True,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=28
    )

    assert itinerary["resupply_plan"]

    assert itinerary["resupply_plan"][0]["day"] == 1
    assert (
        itinerary["resupply_plan"][0]["location"]
        == "Journey's End Trail"
    )
    assert (
        itinerary["resupply_plan"][0]["notes"]
        == "start"
    )
    assert (
        itinerary["resupply_plan"][-1]["day"]
        < itinerary["daily_plan"][-1]["day"]
    )

    for idx, row in enumerate(
        itinerary["resupply_plan"]
    ):
        assert row["location"]
        assert row["mile"] is not None
        assert row["town_access"]

        if idx + 1 < len(
            itinerary["resupply_plan"]
        ):
            assert (
                row["days_to_next_resupply"]
                == (
                    itinerary["resupply_plan"][idx + 1]["day"]
                    - row["day"]
                )
            )
