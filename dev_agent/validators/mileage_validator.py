def validate_mileage(
    days,
    min_miles,
    max_miles,
):

    violations = []

    for idx, day in enumerate(days):

        distance = day.get(
            "distance",
            0,
        )

        if distance < min_miles:

            violations.append(
                {
                    "day": idx + 1,
                    "issue":
                        f"Below minimum mileage: {distance}",
                }
            )

        if distance > max_miles:

            violations.append(
                {
                    "day": idx + 1,
                    "issue":
                        f"Above maximum mileage: {distance}",
                }
            )

    return violations
