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
    assert (
        itinerary["resupply_plan"][0][
            "days_to_next_recovery"
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


def test_resupply_plan_exposes_recovery_and_access_distance(
    planner_factory,
):
    """Test resupply strategy shows recovery timing and town friction."""
    planner = planner_factory(
        user_profile={
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "egress_route": "Journey's End Trail",
            "resupply_cadence": 5,
            "recovery_cadence": 5,
            "min_daily_miles": 9,
            "max_daily_miles": 15,
            "max_daily_elevation": 4000,
            "allow_extra_resupply_only": True,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=28
    )

    resupply_plan = itinerary[
        "resupply_plan"
    ]

    assert resupply_plan
    assert all(
        "days_to_next_recovery" in row
        for row in resupply_plan
    )

    inn_at_long_trail = next(
        row for row in resupply_plan
        if row["location"] == (
            "U.S. 4 west of Sherburne Pass"
        )
    )

    assert (
        inn_at_long_trail[
            "access_distance_miles"
        ]
        == 1.0
    )
    assert (
        inn_at_long_trail[
            "resupply_convenience"
        ]
        == "near_trail"
    )
    assert "Less than 1 mile" in (
        inn_at_long_trail[
            "access_notes"
        ]
    )


def test_resupply_town_details_expose_service_context_and_validation(
    planner_factory,
):
    """Test town detail rows expose validated options without scoring."""
    planner = planner_factory(
        user_profile={
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "egress_route": "Journey's End Trail",
            "resupply_cadence": 5,
            "recovery_cadence": 5,
            "min_daily_miles": 9,
            "max_daily_miles": 15,
            "max_daily_elevation": 4000,
            "allow_extra_resupply_only": True,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=28
    )

    town_details = itinerary[
        "resupply_town_details"
    ]

    assert town_details

    inn_at_long_trail = next(
        row for row in town_details
        if row["town_access"]
        == "Inn at Long Trail / Rutland"
    )

    assert (
        inn_at_long_trail[
            "business_detail_status"
        ]
        == "validated named options available"
    )
    assert (
        inn_at_long_trail[
            "zero_support"
        ]
        == "validated_lodging_and_food"
    )
    assert "Inn at Long Trail" in (
        inn_at_long_trail[
            "validated_lodging"
        ]
    )
    assert "McGrath's Irish Pub" in (
        inn_at_long_trail[
            "validated_food"
        ]
    )
    assert any(
        row["business_detail_status"]
        == (
            "category-only; named options require "
            "independent current validation"
        )
        for row in town_details
    )
    assert any(
        "Outfitter" in row[
            "service_categories"
        ]
        for row in town_details
    )
    assert any(
        row["source_name"]
        == "Long Trail Planning Guide"
        for row in town_details
    )


def test_selected_side_trips_annotate_without_changing_plan_time(
    planner_factory,
):
    """Test side trips are advisory annotations only."""
    user_profile = {
        "direction": "NOBO",
        "ingress_route": "North Adams Approach",
        "egress_route": "Journey's End Trail",
        "resupply_cadence": 5,
        "recovery_cadence": 5,
        "min_daily_miles": 9,
        "max_daily_miles": 15,
        "max_daily_elevation": 4000,
        "allow_extra_resupply_only": True,
    }
    base_planner = planner_factory(
        user_profile=user_profile,
    )
    side_trip_planner = planner_factory(
        user_profile={
            **user_profile,
            "selected_side_trip_ids": [
                "ben_jerrys_factory",
            ],
        },
    )

    base_itinerary = (
        base_planner.synthesize_itinerary(
            desired_days=28
        )
    )
    side_trip_itinerary = (
        side_trip_planner.synthesize_itinerary(
            desired_days=28
        )
    )

    assert (
        side_trip_itinerary[
            "expedition_summary"
        ]["completion_days"]
        == base_itinerary[
            "expedition_summary"
        ]["completion_days"]
    )
    assert [
        row["daily_miles"]
        for row in side_trip_itinerary[
            "daily_plan"
        ]
    ] == [
        row["daily_miles"]
        for row in base_itinerary[
            "daily_plan"
        ]
    ]

    waterbury = next(
        row for row in side_trip_itinerary[
            "resupply_town_details"
        ]
        if row["town_access"]
        == "Waterbury / Waterbury Center"
    )

    assert "Ben & Jerry's Factory Experience" in (
        waterbury["selected_side_trips"]
    )
    assert any(
        "Ben & Jerry's Factory Experience" in row.get(
            "selected_side_trips",
            "",
        )
        for row in side_trip_itinerary[
            "daily_plan"
        ]
    )


def test_access_distance_parser_extracts_nearest_town_miles(planner):
    """Test prose parsing remains as a fallback for legacy rows."""
    assert (
        planner.logistics.parse_access_distance_miles(
            "Less than 1 mile east to Inn at Long Trail"
        )
        == 1.0
    )
    assert (
        planner.logistics.parse_access_distance_miles(
            "4+ miles east to Warren and 5 miles west to Lincoln"
        )
        == 4.0
    )


def test_structured_access_distance_precedes_prose_parser(planner):
    """Test structured friction data wins over access note prose."""
    node = {
        "access_distance_miles": 2.0,
        "access_notes": (
            "Less than 1 mile to one service "
            "and 9 miles to another"
        ),
    }

    assert (
        planner.logistics.access_distance_miles(
            node
        )
        == 2.0
    )


def test_convenient_resupply_distance_is_user_configurable(
    planner_factory,
):
    """Test user preference controls extra resupply convenience."""
    strict_planner = planner_factory(
        user_profile={
            "convenient_resupply_distance_miles": 1.0,
        },
    )
    flexible_planner = planner_factory(
        user_profile={
            "convenient_resupply_distance_miles": 2.5,
        },
    )
    node = {
        "access_distance_miles": 2.0,
    }

    assert (
        strict_planner.logistics
        .is_convenient_extra_resupply(node)
        is False
    )
    assert (
        flexible_planner.logistics
        .is_convenient_extra_resupply(node)
        is True
    )


def test_overnight_display_names_keep_access_notes_separate(
    planner_factory,
):
    """Test shelter rows show site names without side-trail prose."""
    planner = planner_factory(
        user_profile={
            "trip_type": "THRU",
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "egress_route": "Journey's End Trail",
            "min_daily_miles": 10,
            "max_daily_miles": 15,
            "max_daily_elevation": 4000,
            "resupply_cadence": 5,
            "recovery_cadence": 5,
            "allow_extra_resupply_only": True,
            "avoid_long_food_carry": True,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=27
    )
    daily_plan = itinerary["daily_plan"]
    stratton_day = next(
        row for row in daily_plan
        if row["daily_stop_location"]
        == "Stratton Pond Shelter"
    )

    assert stratton_day[
        "daily_stop_canonical_location"
    ].startswith(
        "Stratton Pond Trail to "
    )
    assert stratton_day[
        "daily_stop_access_notes"
    ] == (
        "600 ft S via Stratton Pond Trail "
        "and spur"
    )
    assert "Manchester" not in stratton_day[
        "daily_stop_location"
    ]
    assert "Kelley Stand" not in stratton_day[
        "daily_stop_location"
    ]

    next_day = next(
        row for row in daily_plan
        if row["daily_start_mile"]
        == stratton_day["daily_stop_mile"]
    )
    assert (
        next_day["daily_start_location"]
        == "Stratton Pond Shelter"
    )
    assert next_day[
        "daily_start_access_notes"
    ] == stratton_day[
        "daily_stop_access_notes"
    ]


def test_off_spine_overnight_access_is_diagnostic_not_mileage(
    planner_factory,
):
    """Test side-spur shelters remain tied to mainline guidebook miles."""
    planner = planner_factory(
        user_profile={
            "trip_type": "THRU",
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "egress_route": "Journey's End Trail",
            "min_daily_miles": 10,
            "max_daily_miles": 15,
            "max_daily_elevation": 4000,
            "resupply_cadence": 5,
            "recovery_cadence": 5,
            "allow_extra_resupply_only": True,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=27
    )
    stratton_day = next(
        row for row in itinerary["daily_plan"]
        if row["daily_stop_location"]
        == "Stratton Pond Shelter"
    )

    assert (
        stratton_day["daily_stop_mile"]
        == 43.8
    )
    assert stratton_day[
        "daily_stop_spine_alignment"
    ]["status"] == (
        "off_spine_overnight_access"
    )
    assert stratton_day[
        "daily_stop_spine_alignment"
    ]["distance_to_spine_miles"] > 0.1


def test_resupply_access_scoring_penalizes_long_resupply_only_side_trips(
    planner,
):
    """Test convenience scoring favors close resupply-only access."""
    close_node = {
        "access_distance_miles": 1.0,
    }
    distant_node = {
        "access_distance_miles": 5.0,
    }

    assert (
        planner.logistics.score_access_convenience(
            close_node
        )
        > planner.logistics.score_access_convenience(
            distant_node
        )
    )
    assert (
        planner.logistics.is_convenient_extra_resupply(
            close_node
        )
        is True
    )
    assert (
        planner.logistics.is_convenient_extra_resupply(
            distant_node
        )
        is False
    )


def test_daily_elevation_gain_is_not_capped_by_user_limit(planner_factory):
    """Test fallback daily gain reports are not capped by the max limit."""
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


def test_terrain_interval_analysis_identifies_harder_sections(planner):
    """Test terrain intervals expose harder and easier trail sections."""
    easy_interval = planner.analyze_terrain_interval(
        40.0,
        50.0,
    )
    hard_interval = planner.analyze_terrain_interval(
        200.0,
        210.0,
    )

    assert easy_interval["source"] == "terrain"
    assert hard_interval["source"] == "terrain"
    assert (
        hard_interval["elevation_gain_ft"]
        > easy_interval["elevation_gain_ft"]
    )
    assert (
        hard_interval["ruggedness_score"]
        > easy_interval["ruggedness_score"]
    )


def test_terrain_mile_reconciliation_is_explicit(planner):
    """Test guidebook miles map into a named terrain sample domain."""
    reconciliation = (
        planner.terrain_mile_reconciliation()
    )
    guidebook_min, guidebook_max = (
        planner.guidebook_mainline_range()
    )
    terrain_min, terrain_max = (
        planner.terrain_mile_range()
    )

    assert reconciliation["status"] == "ready"
    assert (
        reconciliation["guidebook_domain"]
        == "northbound_reference_mainline_miles"
    )
    assert (
        reconciliation["terrain_domain"]
        == "compiled_geometry_sample_miles"
    )
    assert (
        planner.map_guidebook_to_terrain_mile(
            guidebook_min
        )
        == terrain_min
    )
    assert round(
        planner.map_guidebook_to_terrain_mile(
            guidebook_max
        ),
        6,
    ) == round(
        terrain_max,
        6,
    )


def test_terrain_mile_mapping_is_monotonic_and_mainline_only(planner):
    """Test approach miles fall back instead of entering terrain domain."""
    first = planner.map_guidebook_to_terrain_mile(
        10.0
    )
    second = planner.map_guidebook_to_terrain_mile(
        20.0
    )

    assert first is not None
    assert second is not None
    assert second > first
    assert (
        planner.map_guidebook_to_terrain_mile(
            -0.1
        )
        is None
    )


def test_anchor_based_terrain_mapping_uses_known_shelter_coordinates(
    planner,
):
    """Test known shelters map to projected terrain miles, not only ratio math."""
    goddard_terrain_mile = (
        planner.map_guidebook_to_terrain_mile(
            24.4
        )
    )
    story_terrain_mile = (
        planner.map_guidebook_to_terrain_mile(
            33.3
        )
    )

    assert round(
        goddard_terrain_mile,
        2,
    ) == 22.56
    assert round(
        story_terrain_mile,
        2,
    ) == 30.88
    assert (
        goddard_terrain_mile
        > planner.terrain
        .map_guidebook_to_terrain_mile_linear(
            24.4
        )
    )


def test_terrain_anchor_mapping_is_monotonic(planner):
    """Test projected terrain anchors preserve trail progression."""
    anchors = (
        planner.terrain.load_terrain_mile_anchors()
    )

    assert len(anchors) > 50

    for left, right in zip(
        anchors,
        anchors[1:],
    ):
        assert (
            right["guidebook_mile"]
            > left["guidebook_mile"]
        )
        assert (
            right["terrain_mile"]
            > left["terrain_mile"]
        )


def test_terrain_interval_analysis_is_direction_aware(planner_factory):
    """Test SOBO terrain gain is positive in traversal direction."""
    nobo_planner = planner_factory(
        user_profile={
            "direction": "NOBO",
        },
    )
    sobo_planner = planner_factory(
        user_profile={
            "direction": "SOBO",
        },
    )

    nobo_interval = (
        nobo_planner
        .analyze_terrain_interval(
            200.0,
            210.0,
        )
    )
    sobo_interval = (
        sobo_planner
        .analyze_terrain_interval(
            210.0,
            200.0,
        )
    )

    assert nobo_interval["source"] == "terrain"
    assert sobo_interval["source"] == "terrain"
    assert sobo_interval["elevation_gain_ft"] > 0
    assert (
        abs(
            sobo_interval["elevation_gain_ft"]
            - nobo_interval["elevation_loss_ft"]
        )
        <= 75
    )


def test_terrain_interval_crossing_approach_and_mainline_uses_mixed_sources(
    planner,
):
    """Test approach-to-mainline intervals do not fully fall back."""
    interval = planner.analyze_terrain_interval(
        -3.8,
        5.5,
    )

    assert interval["source"] == "mixed"
    assert interval["source_parts"] == [
        "route_master",
        "terrain",
    ]
    assert interval["elevation_gain_ft"] > 2500
    assert interval["elevation_loss_ft"] > 0


def test_goddard_to_story_spring_elevation_uses_anchor_mapping(
    planner,
):
    """Test known lower-trail interval stays within calibrated terrain range."""
    interval = planner.analyze_terrain_interval(
        24.4,
        33.3,
    )

    assert interval["source"] == "terrain"
    assert (
        1150
        <= interval["elevation_gain_ft"]
        <= 1300
    )
    assert interval["elevation_loss_ft"] > 1500


def test_stratton_mountain_interval_retains_mainline_climb(
    planner,
):
    """Test Story Spring to Stratton Pond keeps the Stratton climb."""
    interval = planner.analyze_terrain_interval(
        33.3,
        43.8,
    )

    assert interval["source"] == "terrain"
    assert (
        interval["elevation_gain_ft"]
        >= 1850
    )
    assert (
        interval["elevation_loss_ft"]
        >= 2200
    )


def test_stratton_pond_to_vt_11_30_counts_rolling_gain(
    planner,
):
    """Test rolling descent from Stratton Pond does not flatten to 587 ft."""
    interval = planner.analyze_terrain_interval(
        43.8,
        54.4,
    )

    assert interval["source"] == "terrain"
    assert (
        800
        <= interval["elevation_gain_ft"]
        <= 1000
    )
    assert interval["elevation_loss_ft"] >= 1600


def test_terrain_smoothing_keeps_real_rolling_gain(
    planner,
):
    """Test sub-50 ft terrain rolls are counted when cumulative."""
    interval = planner.terrain.analyze_sample_interval(
        [
            (
                0.0,
                1000.0,
            ),
            (
                0.1,
                1030.0,
            ),
            (
                0.2,
                1060.0,
            ),
            (
                0.3,
                1090.0,
            ),
        ],
        0.0,
        0.3,
        "terrain",
        reported_distance=0.3,
    )

    assert interval["elevation_gain_ft"] == 90
    assert interval["elevation_loss_ft"] == 0


def test_terrain_interval_analysis_falls_back_to_route_master(
    planner_factory,
):
    """Test route-master elevation fallback works without terrain samples."""
    planner = planner_factory()

    planner._terrain_samples = []

    interval = planner.analyze_terrain_interval(
        200.0,
        210.0,
    )

    assert interval["source"] == "route_master"
    assert interval["elevation_gain_ft"] > 0
    assert interval["gain_per_mile"] > 0


def test_terrain_aware_pacing_lowers_hard_section_target(planner):
    """Test harder upcoming terrain lowers daily mileage target."""
    easy_target = (
        planner
        .calculate_terrain_adjusted_target(
            10.0,
            1,
            current_mile=40.0,
            southern_mile=0.0,
            northern_mile=273.3,
        )
    )
    hard_target = (
        planner
        .calculate_terrain_adjusted_target(
            10.0,
            1,
            current_mile=200.0,
            southern_mile=0.0,
            northern_mile=273.3,
        )
    )

    assert hard_target < easy_target


def test_nero_notes_obey_default_mileage_window(planner_factory):
    """Test nero labels only apply inside the configured window."""
    planner = planner_factory(
        user_profile={
            "trip_type": "THRU",
            "direction": "SOBO",
            "ingress_route": "Journey's End Trail",
            "egress_route": "Williamstown Approach",
            "min_daily_miles": 9,
            "max_daily_miles": 15,
            "resupply_cadence": 5,
            "recovery_cadence": 5,
            "allow_extra_resupply_only": True,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=28
    )

    nero_rows = [
        row for row in itinerary["daily_plan"]
        if "nero" in row.get("notes", "")
    ]

    assert nero_rows

    for row in nero_rows:
        assert 5.0 <= row["daily_miles"] <= 8.0


def test_custom_nero_window_changes_classification(planner_factory):
    """Test custom nero bounds are honored when recovery days are labeled."""
    planner = planner_factory(
        user_profile={
            "trip_type": "THRU",
            "direction": "NOBO",
            "ingress_route": "Williamstown Approach",
            "egress_route": "Journey's End Trail",
            "min_daily_miles": 9,
            "max_daily_miles": 15,
            "resupply_cadence": 5,
            "recovery_cadence": 6,
            "allow_extra_resupply_only": True,
            "min_nero_miles": 1,
            "max_nero_miles": 12,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=28
    )

    nero_rows = [
        row for row in itinerary["daily_plan"]
        if "nero" in row.get("notes", "")
    ]

    assert nero_rows

    for row in nero_rows:
        assert 1.0 <= row[
            "daily_miles"
        ] <= 12.0


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


def test_summary_average_daily_miles_excludes_zero_days(planner_factory):
    """Test summary effort averages use moving days, not calendar days."""
    planner = planner_factory(
        user_profile={
            "trip_type": "THRU",
            "direction": "NOBO",
            "ingress_route": "Williamstown Approach",
            "egress_route": "Journey's End Trail",
            "min_daily_miles": 9,
            "max_daily_miles": 15,
            "resupply_cadence": 5,
            "recovery_cadence": 6,
            "allow_extra_resupply_only": True,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=28
    )

    moving_days = len([
        row for row in itinerary["daily_plan"]
        if row["daily_miles"] > 0
    ])
    summary = itinerary[
        "expedition_summary"
    ]

    assert moving_days < summary["completion_days"]
    assert summary["moving_days"] == moving_days
    assert summary["average_daily_miles"] == round(
        summary["total_miles"] / moving_days,
        1,
    )
    assert (
        summary["average_daily_miles"]
        > round(
            summary["total_miles"]
            / summary["completion_days"],
            1,
        )
    )


def _daily_rows(
    miles,
    elevation,
):
    return [
        {
            "day": index + 1,
            "daily_miles": mile,
            "daily_elevation_gain": gain,
        }
        for index, (
            mile,
            gain,
        ) in enumerate(
            zip(
                miles,
                elevation,
            )
        )
    ]


def test_sparse_mileage_exception_remains_comfortable(planner_factory):
    """Test one minor mileage overage does not overclassify a plan."""
    planner = planner_factory(
        user_profile={
            "max_daily_miles": 10,
            "max_daily_elevation": 1000,
        },
    )
    rows = _daily_rows(
        [7, 7, 7, 11, 7, 7, 7, 7, 7, 7],
        [700] * 10,
    )
    exceptions = planner.summarize_itinerary_exceptions(
        rows
    )

    evaluation = planner.build_generated_evaluation(
        rows,
        exceptions,
    )

    assert evaluation["classification"] == "comfortable"
    assert (
        evaluation["classification_reason"]
        == "sparse_preference_exceptions"
    )
    assert evaluation["combined_exception_days"] == [
        4
    ]


def test_sparse_moderate_elevation_exception_can_remain_comfortable(
    planner_factory,
):
    """Test one moderate elevation overage can remain comfortable."""
    planner = planner_factory(
        user_profile={
            "max_daily_miles": 10,
            "max_daily_elevation": 1000,
        },
    )
    rows = _daily_rows(
        [8] * 10,
        [800, 800, 1250, 800, 800, 800, 800, 800, 800, 800],
    )
    exceptions = planner.summarize_itinerary_exceptions(
        rows
    )

    evaluation = planner.build_generated_evaluation(
        rows,
        exceptions,
    )

    assert exceptions[0]["severity"] == "moderate"
    assert evaluation["classification"] == "comfortable"
    assert evaluation["exception_pressure_score"] <= 3.0


def test_repeated_moderate_exceptions_become_challenging(
    planner_factory,
):
    """Test repeated moderate pressure escalates generated difficulty."""
    planner = planner_factory(
        user_profile={
            "max_daily_miles": 10,
            "max_daily_elevation": 1000,
        },
    )
    rows = _daily_rows(
        [8] * 12,
        [1250, 800, 800, 1250, 800, 800, 1250, 800, 800, 800, 800, 800],
    )
    exceptions = planner.summarize_itinerary_exceptions(
        rows
    )

    evaluation = planner.build_generated_evaluation(
        rows,
        exceptions,
    )

    assert exceptions[0]["severity"] == "moderate"
    assert evaluation["classification"] == "challenging"
    assert (
        evaluation["classification_reason"]
        == "repeated_preference_pressure"
    )


def test_compound_same_day_exceptions_increase_pressure(
    planner_factory,
):
    """Test same-day mileage and elevation overages add stress."""
    planner = planner_factory(
        user_profile={
            "max_daily_miles": 10,
            "max_daily_elevation": 1000,
        },
    )
    separate_rows = _daily_rows(
        [12, 8, 8, 8, 8, 8, 8, 8, 8, 8],
        [800, 1250, 800, 800, 800, 800, 800, 800, 800, 800],
    )
    compound_rows = _daily_rows(
        [12, 8, 8, 8, 8, 8, 8, 8, 8, 8],
        [1250, 800, 800, 800, 800, 800, 800, 800, 800, 800],
    )

    separate = planner.build_generated_evaluation(
        separate_rows,
        planner.summarize_itinerary_exceptions(
            separate_rows
        ),
    )
    compound = planner.build_generated_evaluation(
        compound_rows,
        planner.summarize_itinerary_exceptions(
            compound_rows
        ),
    )

    assert compound["compound_exception_days"] == [
        1
    ]
    assert (
        compound["exception_pressure_score"]
        > separate["exception_pressure_score"]
    )


def test_moderate_weighted_exception_pressure_is_challenging(
    planner_factory,
):
    """Test alpha diagnostic scenario does not overclassify as aggressive."""
    planner = planner_factory(
        user_profile={
            "max_daily_miles": 15,
            "max_daily_elevation": 4000,
        },
    )
    miles = [10.0] * 28
    elevation = [2500.0] * 28
    miles[15] = 15.5
    miles[21] = 15.6
    miles[25] = 18.0
    miles[26] = 14.5
    miles[27] = 12.9
    elevation[15] = 3783.0
    elevation[21] = 4636.0
    elevation[25] = 4515.0
    elevation[26] = 4263.0
    elevation[27] = 4094.0
    rows = _daily_rows(
        miles,
        elevation,
    )

    exceptions = planner.summarize_itinerary_exceptions(
        rows
    )
    evaluation = planner.build_generated_evaluation(
        rows,
        exceptions,
    )

    assert [
        row["constraint"]
        for row in exceptions
    ] == [
        "daily_miles",
        "daily_elevation_gain",
    ]
    assert exceptions[0]["overage_percent"] == 20.0
    assert exceptions[1]["overage_percent"] == 15.9
    assert evaluation["classification"] == "challenging"
    assert (
        evaluation["classification_reason"]
        == "moderate_weighted_preference_pressure"
    )
    assert evaluation["compound_exception_days"] == [
        22,
        26,
    ]
    assert (
        evaluation["weighted_exception_pressure_percent"]
        == 26.9
    )


def test_more_than_two_compound_exception_days_are_aggressive(
    planner_factory,
):
    """Test repeated combined mileage/elevation overages escalate."""
    planner = planner_factory(
        user_profile={
            "max_daily_miles": 10,
            "max_daily_elevation": 1000,
        },
    )
    rows = _daily_rows(
        [12, 12, 12, 8, 8, 8, 8, 8, 8, 8, 8, 8],
        [1250, 1250, 1250, 800, 800, 800, 800, 800, 800, 800, 800, 800],
    )

    evaluation = planner.build_generated_evaluation(
        rows,
        planner.summarize_itinerary_exceptions(
            rows
        ),
    )

    assert evaluation["compound_exception_days"] == [
        1,
        2,
        3,
    ]
    assert evaluation["classification"] == "aggressive"
    assert (
        evaluation["classification_reason"]
        == "compound_exception_pressure"
    )


def test_frequent_exception_days_are_aggressive(
    planner_factory,
):
    """Test frequent preference misses remain visible even if small."""
    planner = planner_factory(
        user_profile={
            "max_daily_miles": 10,
            "max_daily_elevation": 1000,
        },
    )
    rows = _daily_rows(
        [10.5, 10.5, 10.5, 10.5, 8, 8, 8, 8, 8, 8],
        [800] * 10,
    )

    evaluation = planner.build_generated_evaluation(
        rows,
        planner.summarize_itinerary_exceptions(
            rows
        ),
    )

    assert evaluation["exception_day_ratio"] == 0.4
    assert evaluation["classification"] == "aggressive"
    assert (
        evaluation["classification_reason"]
        == "frequent_preference_pressure"
    )


def test_major_overage_classifies_generated_plan_aggressive(
    planner_factory,
):
    """Test major preference overages classify generated plans aggressive."""
    planner = planner_factory(
        user_profile={
            "max_daily_miles": 10,
            "max_daily_elevation": 1000,
        },
    )
    rows = _daily_rows(
        [8] * 10,
        [800, 800, 1400, 800, 800, 800, 800, 800, 800, 800],
    )
    exceptions = planner.summarize_itinerary_exceptions(
        rows
    )

    evaluation = planner.build_generated_evaluation(
        rows,
        exceptions,
    )

    assert exceptions[0]["severity"] == "major"
    assert evaluation["classification"] == "aggressive"
    assert (
        evaluation["classification_reason"]
        == "extreme_preference_overage"
    )


def test_elevation_exceptions_raise_feasibility_pressure(planner_factory):
    """Test fixed-duration plans complete and flag elevation exceptions."""
    planner = planner_factory(
        user_profile={
            "trip_type": "THRU",
            "direction": "NOBO",
            "ingress_route": "Williamstown Approach",
            "egress_route": "Journey's End Trail",
            "min_daily_miles": 9,
            "max_daily_miles": 15,
            "max_daily_elevation": 3000,
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
        in {
            "challenging",
            "aggressive",
        }
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

    assert elevation_exception["limit"] == 3000
    assert elevation_exception["observed_max"] > 3000
    assert elevation_exception["count"] > 0
    assert elevation_exception["severity"] in {
        "moderate",
        "major",
    }


def test_sparse_preference_exceptions_do_not_force_aggressive_label(
    planner_factory,
):
    """Test sparse overages avoid an aggressive generated classification."""
    planner = planner_factory(
        user_profile={
            "trip_type": "THRU",
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "egress_route": "Journey's End Trail",
            "min_daily_miles": 9,
            "max_daily_miles": 15,
            "max_daily_elevation": 4000,
            "resupply_cadence": 5,
            "recovery_cadence": 5,
            "min_nero_miles": 5,
            "max_nero_miles": 8,
            "allow_extra_resupply_only": True,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=28
    )

    completion = itinerary[
        "completion_analysis"
    ]

    assert completion[
        "has_itinerary_exceptions"
    ] is True
    assert completion[
        "evaluation"
    ] == completion[
        "generated_evaluation"
    ]
    assert (
        completion["requested_evaluation"][
            "classification"
        ]
        == "comfortable"
    )
    assert (
        completion["generated_evaluation"][
            "classification"
        ]
        == "challenging"
    )
    assert (
        completion["classification_reason"]
        == "moderate_weighted_preference_pressure"
    )


def test_extended_requested_target_has_separate_generated_evaluation(
    planner_factory,
):
    """Test extended requests do not overwrite generated-plan class."""
    planner = planner_factory(
        user_profile={
            "max_daily_miles": 12,
            "max_daily_elevation": 4000,
        },
    )
    completion = planner.negotiate_completion_target(
        desired_days=21
    )
    extended = planner.apply_completion_extension(
        completion,
        actual_days=29,
    )
    rows = _daily_rows(
        [10] * 29,
        [2000] * 29,
    )

    final = planner.apply_itinerary_exceptions(
        extended,
        rows,
    )

    assert final["completion_extended"] is True
    assert final["requested_evaluation"][
        "classification"
    ] in {
        "aggressive",
        "unrealistic",
    }
    assert (
        final["requested_evaluation"][
            "classification_reason"
        ]
        == "extended_requested_target"
    )
    assert (
        final["generated_evaluation"][
            "classification"
        ]
        == "comfortable"
    )
    assert final["evaluation"] == final[
        "generated_evaluation"
    ]


def test_sobo_uses_same_generated_feasibility_rules(
    planner_factory,
):
    """Test SOBO sparse exceptions use the same generated classifier."""
    planner = planner_factory(
        user_profile={
            "trip_type": "THRU",
            "direction": "SOBO",
            "ingress_route": "Journey's End Trail",
            "egress_route": "Williamstown Approach",
            "min_daily_miles": 8,
            "max_daily_miles": 16,
            "max_daily_elevation": 3500,
            "resupply_cadence": 5,
            "recovery_cadence": 6,
            "min_nero_miles": 5,
            "max_nero_miles": 8,
            "allow_extra_resupply_only": True,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=28
    )
    completion = itinerary[
        "completion_analysis"
    ]

    assert completion["evaluation"] == completion[
        "generated_evaluation"
    ]
    assert (
        completion["requested_evaluation"][
            "classification"
        ]
        == "comfortable"
    )
    assert (
        completion["generated_evaluation"][
            "classification"
        ]
        == "challenging"
    )
    assert (
        completion["classification_reason"]
        == "moderate_weighted_preference_pressure"
    )


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

    assert last_day["day"] >= 28
    assert (
        last_day["daily_stop_location"]
        == "Journey's End Trail Parking"
    )
    assert last_day["daily_stop_mile"] == 273.3
    assert last_day["daily_miles"] > 0
    assert last_day["notes"] == ""


def test_aggressive_target_avoids_absurd_final_catchup(
    planner_factory,
):
    """Test aggressive plans finish without excessive final catch-up."""
    planner = planner_factory(
        user_profile={
            "trip_type": "THRU",
            "direction": "NOBO",
            "ingress_route": "Williamstown Approach",
            "egress_route": "Journey's End Trail",
            "min_daily_miles": 8,
            "max_daily_miles": 16,
            "max_daily_elevation": 3500,
            "resupply_cadence": 5,
            "recovery_cadence": 6,
            "allow_extra_resupply_only": True,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=21
    )

    rows = itinerary["daily_plan"]
    completion = itinerary[
        "completion_analysis"
    ]

    mileage_cap = planner.max_daily_miles * 1.3

    assert completion.get(
        "completion_extended",
        False,
    ) is False
    assert completion[
        "generated_evaluation"
    ]["classification"] == "aggressive"
    assert rows[-1]["day"] == 21
    assert (
        rows[-1]["daily_stop_location"]
        == "Journey's End Trail Parking"
    )
    assert rows[-1]["daily_miles"] <= mileage_cap
    assert max(
        row["daily_miles"]
        for row in rows
    ) < 30


def test_extended_plan_bounds_final_day_to_overmax_allowance(
    planner_factory,
):
    """Test extended recommendations do not hide excessive final pushes."""
    planner = planner_factory(
        user_profile={
            "trip_type": "THRU",
            "direction": "NOBO",
            "ingress_route": "Williamstown Approach",
            "egress_route": "Journey's End Trail",
            "min_daily_miles": 9,
            "max_daily_miles": 12,
            "max_daily_elevation": 4000,
            "resupply_cadence": 5,
            "recovery_cadence": 5,
            "allow_extra_resupply_only": True,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=21
    )

    rows = itinerary["daily_plan"]
    completion = itinerary[
        "completion_analysis"
    ]
    mileage_cap = (
        planner.max_daily_miles * 1.3
    )

    assert completion[
        "completion_extended"
    ] is True
    assert (
        rows[-1]["daily_stop_location"]
        == "Journey's End Trail Parking"
    )
    assert rows[-1]["daily_miles"] <= mileage_cap
    assert max(
        row["daily_miles"]
        for row in rows
    ) <= mileage_cap


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
    moving_days = {
        row["day"]
        for row in itinerary["daily_plan"]
        if row["daily_miles"] > 0
    }

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
            next_row = itinerary[
                "resupply_plan"
            ][idx + 1]
            expected = len([
                day for day in moving_days
                if (
                    (
                        day >= row["day"]
                        if row["notes"] == "start"
                        else day > row["day"]
                    )
                    and day <= next_row["day"]
                )
            ])
            assert (
                row["days_to_next_resupply"]
                == expected
            )


def test_overlay_corridor_preserves_directional_order(planner_factory):
    """Test overlay corridor order follows travel direction."""
    nobo = planner_factory(
        user_profile={
            "direction": "NOBO",
        },
    )
    sobo = planner_factory(
        user_profile={
            "direction": "SOBO",
        },
    )

    nobo_nodes = nobo.build_overlay_corridor(
        start_mile=0.0,
        stop_mile=272.1,
    )
    sobo_nodes = sobo.build_overlay_corridor(
        start_mile=272.1,
        stop_mile=0.0,
    )

    assert nobo_nodes[0][
        "trail_mile"
    ] <= nobo_nodes[-1][
        "trail_mile"
    ]
    assert sobo_nodes[0][
        "trail_mile"
    ] >= sobo_nodes[-1][
        "trail_mile"
    ]
    assert nobo_nodes[0][
        "canonical_name"
    ].startswith("Southern terminus")
    assert sobo_nodes[0][
        "canonical_name"
    ].startswith("U.S.-Canadian Border")


def test_ordered_overlay_nodes_follow_operational_edge_order(planner):
    """Test overlay traversal preserves operational progression edge order."""
    ordered_ids = [
        node.get("overlay_id")
        for node in (
            planner.traversal
            .ordered_overlay_nodes()
        )
    ]
    expected_ids = []

    for edge in sorted(
        planner.queries
        .get_operational_progression_edges(),
        key=lambda item: item.get(
            "edge_id",
            "",
        ),
    ):
        for overlay_id in [
            edge.get("from_overlay"),
            edge.get("to_overlay"),
        ]:
            if (
                overlay_id
                and overlay_id
                not in expected_ids
            ):
                expected_ids.append(
                    overlay_id
                )

    assert ordered_ids[:len(expected_ids)] == expected_ids


def test_corridor_slice_handles_duplicate_southern_mile_by_overlay_index(
    planner_factory,
):
    """Test duplicate 0.0-mile nodes use overlay index, not mile sorting."""
    nobo = planner_factory(
        user_profile={
            "direction": "NOBO",
        },
    )
    sobo = planner_factory(
        user_profile={
            "direction": "SOBO",
        },
    )

    nobo_nodes = nobo.corridor_nodes_between(
        0.0,
        3.0,
        start_overlay_id="overlay_0004",
    )
    sobo_nodes = sobo.corridor_nodes_between(
        3.1,
        0.0,
        include_start=True,
        start_overlay_id="overlay_0007",
        stop_overlay_id="overlay_0004",
    )

    assert [
        node["overlay_id"]
        for node in nobo_nodes
    ] == [
        "overlay_0005",
        "overlay_0006",
    ]
    assert [
        node["overlay_id"]
        for node in sobo_nodes
    ] == [
        "overlay_0007",
        "overlay_0006",
        "overlay_0005",
        "overlay_0004",
    ]


def test_nobo_itinerary_advances_overlay_ids_in_order(
    planner_factory,
):
    """Test NOBO moving days advance by overlay order."""
    planner = planner_factory(
        user_profile={
            "trip_type": "THRU",
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "egress_route": "Journey's End Trail",
            "min_daily_miles": 9,
            "max_daily_miles": 15,
            "max_daily_elevation": 4000,
            "resupply_cadence": 5,
            "recovery_cadence": 5,
            "allow_extra_resupply_only": True,
        },
    )

    rows = planner.synthesize_itinerary(
        desired_days=28
    )["daily_plan"]

    assert rows[0]["daily_start_overlay_id"] == "overlay_0000"
    assert rows[-1]["daily_stop_location"] == (
        "Journey's End Trail Parking"
    )
    assert rows[-1]["daily_stop_overlay_id"] == "overlay_0254"

    for row in rows:
        if row["daily_miles"] == 0.0:
            continue

        start_index = planner.overlay_index(
            row["daily_start_overlay_id"]
        )
        stop_index = planner.overlay_index(
            row["daily_stop_overlay_id"]
        )

        assert start_index is not None
        assert stop_index is not None
        assert stop_index > start_index


def test_sobo_itinerary_advances_overlay_ids_in_order(
    planner_factory,
):
    """Test SOBO moving days descend through overlay order."""
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

    rows = planner.synthesize_itinerary(
        desired_days=28
    )["daily_plan"]

    assert rows[0]["daily_start_overlay_id"] == "overlay_0254"
    assert rows[-1]["daily_stop_location"] == (
        "Pine Cobble Road in Williamstown"
    )

    for row in rows:
        if row["daily_miles"] == 0.0:
            continue

        start_index = planner.overlay_index(
            row["daily_start_overlay_id"]
        )
        stop_index = planner.overlay_index(
            row["daily_stop_overlay_id"]
        )

        assert start_index is not None
        assert stop_index is not None
        assert stop_index < start_index


def test_resupply_strategy_counts_moving_food_carry_days(planner_factory):
    """Test resupply leg lengths exclude zero-day calendar inflation."""
    planner = planner_factory(
        user_profile={
            "trip_type": "THRU",
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "egress_route": "Journey's End Trail",
            "min_daily_miles": 9,
            "max_daily_miles": 15,
            "resupply_cadence": 5,
            "recovery_cadence": 5,
            "allow_extra_resupply_only": True,
            "avoid_long_food_carry": True,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=28
    )
    resupply_plan = itinerary[
        "resupply_plan"
    ]
    moving_days = {
        row["day"]
        for row in itinerary["daily_plan"]
        if row["daily_miles"] > 0
    }

    for index, row in enumerate(
        resupply_plan[:-1]
    ):
        next_row = resupply_plan[
            index + 1
        ]
        expected = len([
            day for day in moving_days
            if (
                (
                    day >= row["day"]
                    if row["notes"] == "start"
                    else day > row["day"]
                )
                and day <= next_row["day"]
            )
        ])
        assert row[
            "days_to_next_resupply"
        ] == expected


def test_avoid_long_food_carry_prefers_access_before_long_gap(
    planner_factory,
):
    """Test enabled food-carry avoidance uses a nearby future resupply."""
    planner = planner_factory(
        user_profile={
            "trip_type": "THRU",
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "egress_route": "Journey's End Trail",
            "min_daily_miles": 9,
            "max_daily_miles": 15,
            "resupply_cadence": 5,
            "recovery_cadence": 5,
            "allow_extra_resupply_only": True,
            "avoid_long_food_carry": True,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=28
    )

    locations = [
        row["location"]
        for row in itinerary["resupply_plan"]
    ]

    assert "Vt. 15 at cemetery" in locations
    assert "Vt. 242 at Jay Pass" not in locations
    assert max(
        row["days_to_next_resupply"]
        for row in itinerary["resupply_plan"]
        if row["days_to_next_resupply"]
    ) <= 6
    assert not [
        row
        for row in itinerary["resupply_plan"]
        if (
            row["notes"] == "resupply"
            and row["days_to_next_resupply"]
            is not None
            and row["days_to_next_resupply"] <= 1
        )
    ]


def test_overlay_authoritative_miles_override_enriched_stop_drift(
    planner_factory,
):
    """Test enriched overnight stops keep overlay-authoritative miles."""
    planner = planner_factory(
        user_profile={
            "trip_type": "THRU",
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "egress_route": "Journey's End Trail",
            "min_daily_miles": 9,
            "max_daily_miles": 15,
            "max_daily_elevation": 4000,
            "resupply_cadence": 5,
            "recovery_cadence": 5,
            "min_nero_miles": 5,
            "max_nero_miles": 8,
            "allow_extra_resupply_only": True,
        },
    )

    overlay_by_name = {
        node["canonical_name"].casefold(): node
        for node in (
            planner.queries
            .list_overlay_progression()
        )
        if node.get("canonical_name")
    }
    selected_stop = {
        "canonical_name": (
            "Montclair Glen Lodge"
        ),
        "trail_mile": 173.6,
    }

    authoritative = (
        planner.itinerary_builder
        .overlay_authoritative_match(
            selected_stop,
            overlay_by_name,
            current_mile=160.0,
        )
    )

    assert authoritative is not None
    assert authoritative[
        "canonical_name"
    ] == "Montclair Glen Lodge"
    assert planner.node_mile(
        authoritative
    ) == 173.8

    interval = planner.analyze_terrain_interval(
        161.4,
        planner.node_mile(
            authoritative
        ),
    )
    assert interval[
        "elevation_gain_ft"
    ] != planner.max_daily_elevation
