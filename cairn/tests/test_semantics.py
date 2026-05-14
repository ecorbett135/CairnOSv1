# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0

def test_shelter_nodes_exist(shelter_nodes):
    assert len(shelter_nodes) > 0

    for shelter in shelter_nodes:
        assert shelter.get("shelter") is True


def test_canonical_names_for_shelters(shelter_nodes):

    for shelter in shelter_nodes:
        name = shelter.get("canonical_name", "")
        assert name != ""
        assert "Shelter" in name or "shelter" in name.lower()


def test_shelter_names_in_itinerary(planner):
    itinerary = planner.synthesize_itinerary(desired_days=5)
    daily_plan = itinerary["daily_plan"]

    stop_locations = [day["daily_stop_location"] for day in daily_plan]
    shelter_count = sum(1 for stop in stop_locations if "Shelter" in stop)

    assert shelter_count > 0
