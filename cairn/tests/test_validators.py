# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from cairn.validation import (
    validate_plan,
)


def test_peak_violation():

    result = {
        "days": [
            {
                "overnight_type":
                    "peak",
                "distance":
                    12,
            }
        ]
    }

    violations = validate_plan(
        result
    )

    assert len(violations) > 0


def test_valid_plan():

    result = {
        "days": [
            {
                "overnight_type":
                    "shelter",
                "distance":
                    12,
            }
        ]
    }

    violations = validate_plan(
        result
    )

    assert len(violations) == 0
