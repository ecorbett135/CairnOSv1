# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import copy
import json
from pathlib import Path

import pytest

from cairn.export.weather_location import (
    WEATHER_LOCATION_CONTRACT_VERSION,
    build_planned_day_weather_locations,
)


def day(number, overlay_id, coordinates):
    return {
        "day": number,
        "daily_stop_mile": float(number),
        "daily_stop_location": f"Camp {number}",
        "daily_stop_canonical_location": f"Camp {number}",
        "daily_stop_location_type": "camp",
        "daily_stop_overlay_id": overlay_id,
        "daily_stop_spine_alignment": (
            {"status": "off_spine_overnight_access", "waypoint_coordinates": coordinates}
            if coordinates is not None
            else None
        ),
    }


def build(rows, trail_root):
    return build_planned_day_weather_locations(
        rows,
        trail_root,
        trail_id="vermont_long_trail",
        direction="NOBO",
        trip_type="THRU",
    )


def test_exports_plan_day_identity_wgs84_role_authority_and_provenance(trail_root):
    payload = build(
        [day(1, "overlay_a", [-72.5, 44.5]), day(2, "overlay_b", [-72.6, 44.6])],
        trail_root,
    )
    assert payload["contract_version"] == WEATHER_LOCATION_CONTRACT_VERSION
    assert len(payload["days"]) == 2
    first = payload["days"][0]
    assert first["day_id"] == f"{payload['plan_id']}:day:1"
    assert first["location_role"] == "planned_daily_stop"
    assert first["authority"] == "cairnos_planned_itinerary"
    assert first["coordinates"] == {
        "latitude": 44.5,
        "longitude": -72.5,
        "coordinate_order": "latitude_longitude",
        "crs": "EPSG:4326",
    }
    assert first["provenance"] == {
        "coordinate_source": "overnight_reference_waypoint",
        "source_reference": "overlay_a",
    }


def test_plan_identity_changes_when_selected_day_stop_changes(trail_root):
    rows = [day(1, "overlay_a", [-72.5, 44.5])]
    first = build(rows, trail_root)
    changed = copy.deepcopy(rows)
    changed[0]["daily_stop_overlay_id"] = "overlay_b"
    second = build(changed, trail_root)
    assert first["plan_id"] != second["plan_id"]
    assert first["days"][0]["day_id"] != second["days"][0]["day_id"]


@pytest.mark.parametrize(
    "coordinates",
    [[181, 44], [-72, 91], [float("nan"), 44], [True, 44], ["-72", 44]],
)
def test_invalid_coordinates_are_explicitly_unavailable(trail_root, coordinates):
    record = build([day(1, "overlay_a", coordinates)], trail_root)["days"][0]
    assert record["availability"] == "unavailable"
    assert record["coordinates"] is None
    assert record["provenance"] is None
    assert record["unavailable_reason"] == "invalid_authoritative_planned_stop_coordinates"


def test_missing_coordinates_do_not_interpolate(monkeypatch, trail_root):
    monkeypatch.setattr(
        "cairn.export.weather_location.resolve_location",
        lambda *_args: ([-72.7, 44.7], "spine_interpolation"),
    )
    record = build([day(1, "overlay_a", None)], trail_root)["days"][0]
    assert record["availability"] == "unavailable"
    assert record["unavailable_reason"] == "no_authoritative_planned_stop_coordinates"


def test_explicit_off_spine_endpoint_wins_over_projected_spine(monkeypatch, trail_root):
    row = day(1, "overlay_a", [-72.75, 44.75])
    row["daily_stop_spine_alignment"]["projected_coordinates"] = [-72.7, 44.7]
    monkeypatch.setattr(
        "cairn.export.weather_location.resolve_location",
        lambda *_args: ([-72.7, 44.7], "route_overlay"),
    )
    record = build([row], trail_root)["days"][0]
    assert record["coordinates"]["longitude"] == -72.75
    assert record["coordinates"]["latitude"] == 44.75


def test_multiple_plans_have_distinct_identity(trail_root):
    first = build([day(1, "overlay_a", [-72.5, 44.5])], trail_root)
    second = build([day(1, "overlay_z", [-72.5, 44.5])], trail_root)
    assert first["plan_id"] != second["plan_id"]


def test_contract_fixture():
    path = Path(__file__).parent / "fixtures" / "weather_location" / "planned_day_weather_location_v1.json"
    payload = json.loads(path.read_text())
    assert payload["contract_version"] == WEATHER_LOCATION_CONTRACT_VERSION
    assert {row["availability"] for row in payload["days"]} == {"available", "unavailable"}
