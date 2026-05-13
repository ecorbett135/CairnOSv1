
def test_itinerary_generation_nobo(planner):
    itinerary = planner.synthesize_itinerary(desired_days=3)

    assert "daily_plan" in itinerary
    assert "completion_analysis" in itinerary
    assert "expedition_summary" in itinerary

    daily_plan = itinerary["daily_plan"]
    assert len(daily_plan) > 0


def test_daily_plan_structure(planner):
    itinerary = planner.synthesize_itinerary(desired_days=3)
    daily_plan = itinerary["daily_plan"]

    day1 = daily_plan[0]
    assert day1["day"] == 1
    assert "daily_start_location" in day1
    assert "daily_stop_location" in day1
    assert "daily_miles" in day1


def test_nobo_with_approach_trail(planner_factory):
    planner = planner_factory(
        user_profile={
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "min_daily_miles": 8,
            "max_daily_miles": 16,
        },
    )

    itinerary = planner.synthesize_itinerary(desired_days=3)
    daily_plan = itinerary["daily_plan"]

    first_day = daily_plan[0]
    assert "North Adams Approach" in first_day["daily_start_location"]
    assert first_day["daily_start_location"] != "Southern Terminus"
