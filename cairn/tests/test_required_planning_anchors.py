# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path

import pytest

from cairn.api.http_contract import create_plan_response
from cairn.api.plan_request import PlanAPIRequest, PlanAPIValidationError
from cairn.api.plan_service import build_plan_response
from cairn.planner.anchors import (
    RequiredPlanningAnchorError,
    build_required_anchor_status,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "plan_api"
REQUIRED_REQUEST_PATH = FIXTURE_DIR / "required_anchor_plan_request.json"


def _required_request():
    return json.loads(REQUIRED_REQUEST_PATH.read_text(encoding="utf-8"))


def _build(payload):
    return build_plan_response(
        payload,
        build_sha="required-anchor-test",
        generated_at="20260717T120000Z",
    )


def test_required_anchor_request_fixture_uses_promoted_inventory_ids():
    payload = _required_request()
    request = PlanAPIRequest.from_payload(payload)
    config = request.to_planner_config()

    assert config["required_overnight_anchor_ids"] == [
        "vermont_long_trail:overnight:overlay_0023",
        "vermont_long_trail:overnight:overlay_0067",
    ]
    assert config["required_resupply_anchor_ids"] == [
        "vermont_long_trail:town:vt_9:14.3:bennington",
        "vermont_long_trail:access:vt_11_30:54.4",
    ]


def test_required_anchors_are_satisfied_exactly_once_in_plan_truth():
    payload = _build(_required_request())
    contract = payload["required_anchors"]

    assert contract == {
        "contract_version": "cairnos_required_planning_anchors_v1",
        "semantics": "partial_specification",
        "required_overnight_anchor_ids": [
            "vermont_long_trail:overnight:overlay_0023",
            "vermont_long_trail:overnight:overlay_0067",
        ],
        "required_resupply_anchor_ids": [
            "vermont_long_trail:town:vt_9:14.3:bennington",
            "vermont_long_trail:access:vt_11_30:54.4",
        ],
        "satisfied_overnight_anchor_ids": [
            "vermont_long_trail:overnight:overlay_0023",
            "vermont_long_trail:overnight:overlay_0067",
        ],
        "satisfied_resupply_anchor_ids": [
            "vermont_long_trail:town:vt_9:14.3:bennington",
            "vermont_long_trail:access:vt_11_30:54.4",
        ],
    }

    overnight_ids = [
        row.get("required_overnight_anchor_id")
        for row in payload["daily_plan"]
        if row.get("required_overnight_anchor_id")
    ]
    resupply_ids = [
        row.get("required_anchor_id")
        for row in payload["resupply_plan"]
        if row.get("required_anchor_id")
    ]
    assert overnight_ids == contract["required_overnight_anchor_ids"]
    assert resupply_ids == contract["required_resupply_anchor_ids"]
    assert all(overnight_ids.count(anchor_id) == 1 for anchor_id in overnight_ids)
    assert all(resupply_ids.count(anchor_id) == 1 for anchor_id in resupply_ids)
    assert any(
        row.get("notes") != "start" and not row.get("required_anchor_id")
        for row in payload["resupply_plan"]
    )

    required_overnight_rows = [
        row
        for row in payload["daily_plan"]
        if row.get("required_overnight_anchor_id")
    ]
    assert all(8 <= row["daily_miles"] <= 15 for row in required_overnight_rows)
    assert all(row["daily_elevation_gain"] <= 4000 for row in required_overnight_rows)
    assert any(
        row["daily_stop_location_type"] == "shelter"
        and not row.get("required_overnight_anchor_id")
        for row in payload["daily_plan"]
    )


def test_required_resupply_is_enforced_when_extra_resupply_is_disabled():
    request = _required_request()
    request["allow_extra_resupply_only"] = False
    request["required_overnight_anchor_ids"] = []
    request["required_resupply_anchor_ids"] = [
        "vermont_long_trail:town:vt_9:14.3:bennington"
    ]

    payload = _build(request)

    required_rows = [
        row for row in payload["resupply_plan"] if row.get("required_anchor_id")
    ]
    assert len(required_rows) == 1
    assert required_rows[0]["town_access"] == "Bennington"
    assert required_rows[0]["notes"] == "required resupply"


def test_required_anchors_preserve_sobo_route_order_and_identity():
    request = _required_request()
    request.update(
        {
            "direction": "SOBO",
            "ingress_route": "Journey's End Trail",
            "egress_route": "North Adams Approach",
            "required_overnight_anchor_ids": list(
                reversed(request["required_overnight_anchor_ids"])
            ),
            "required_resupply_anchor_ids": list(
                reversed(request["required_resupply_anchor_ids"])
            ),
        }
    )

    payload = _build(request)

    assert payload["required_anchors"]["satisfied_overnight_anchor_ids"] == request[
        "required_overnight_anchor_ids"
    ]
    assert payload["required_anchors"]["satisfied_resupply_anchor_ids"] == request[
        "required_resupply_anchor_ids"
    ]
    overnight_miles = [
        row["daily_stop_mile"]
        for row in payload["daily_plan"]
        if row.get("required_overnight_anchor_id")
    ]
    assert overnight_miles == sorted(overnight_miles, reverse=True)


def test_absent_and_empty_required_anchor_fields_preserve_plan_behavior():
    absent = _required_request()
    absent.pop("required_overnight_anchor_ids")
    absent.pop("required_resupply_anchor_ids")
    empty = {
        **absent,
        "required_overnight_anchor_ids": [],
        "required_resupply_anchor_ids": [],
    }

    assert _build(absent) == _build(empty)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    (
        (
            "required_overnight_anchor_ids",
            ["unknown"],
            "contains unknown inventory_id: unknown",
        ),
        (
            "required_overnight_anchor_ids",
            ["vermont_long_trail:access:vt_9:14.3"],
            "is not selectable as overnight_stop",
        ),
        (
            "required_resupply_anchor_ids",
            ["vermont_long_trail:overnight:overlay_0023"],
            "is not selectable as resupply_stop",
        ),
    ),
)
def test_required_anchor_ids_reject_unknown_or_incompatible_inventory(
    field_name,
    value,
    message,
):
    request = _required_request()
    request["required_overnight_anchor_ids"] = []
    request["required_resupply_anchor_ids"] = []
    request[field_name] = value

    with pytest.raises(PlanAPIValidationError, match=message):
        _build(request)


def test_required_anchor_ids_reject_duplicates_and_wrong_route_order():
    request = _required_request()
    duplicate_id = request["required_overnight_anchor_ids"][0]
    request["required_overnight_anchor_ids"] = [duplicate_id, duplicate_id]
    with pytest.raises(PlanAPIValidationError, match="duplicate inventory_id"):
        _build(request)

    request = _required_request()
    request["required_overnight_anchor_ids"].reverse()
    with pytest.raises(PlanAPIValidationError, match="must follow NOBO route order"):
        _build(request)


def test_required_resupply_ids_reject_same_physical_anchor_twice():
    request = _required_request()
    request["required_overnight_anchor_ids"] = []
    request["required_resupply_anchor_ids"] = [
        "vermont_long_trail:access:vt_9:14.3",
        "vermont_long_trail:town:vt_9:14.3:bennington",
    ]

    with pytest.raises(
        PlanAPIValidationError,
        match="same resupply anchor",
    ):
        _build(request)


def test_infeasible_required_overnight_returns_precise_contract_error():
    request = _required_request()
    request["max_daily_elevation"] = 1000
    request["required_overnight_anchor_ids"] = [
        "vermont_long_trail:overnight:overlay_0008"
    ]
    request["required_resupply_anchor_ids"] = []

    response = create_plan_response(
        json.dumps(request).encode("utf-8"),
        request_build_sha="required-anchor-test",
    )

    assert response.status_code == 400
    assert response.payload["error"] == "validation_error"
    assert response.payload["message"] == (
        "Required overnight anchor "
        "vermont_long_trail:overnight:overlay_0008 is infeasible within "
        "max_daily_elevation=1000; planned day 1 requires 2910.0 feet of gain"
    )


def test_planner_contract_fails_when_required_resupply_cannot_be_honored():
    inventory_id = "vermont_long_trail:access:vt_11_30:54.4"

    with pytest.raises(
        RequiredPlanningAnchorError,
        match=(
            "Required resupply anchor must appear exactly once: "
            f"{inventory_id} appeared 0 times"
        ),
    ):
        build_required_anchor_status(
            required_overnight_anchors=[],
            required_resupply_anchors=[{"inventory_id": inventory_id}],
            daily_plan=[],
            resupply_plan=[],
            min_daily_miles=8,
            max_daily_miles=15,
            max_daily_elevation=4000,
        )
