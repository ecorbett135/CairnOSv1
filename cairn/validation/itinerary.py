# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from cairn.validation.mileage import validate_mileage
from cairn.validation.semantics import validate_semantics


def validate_plan(
    result,
    min_miles=8,
    max_miles=15,
):

    days = result.get(
        "days",
        [],
    )

    violations = []

    violations.extend(
        validate_semantics(days)
    )

    violations.extend(
        validate_mileage(
            days,
            min_miles,
            max_miles,
        )
    )

    return violations
