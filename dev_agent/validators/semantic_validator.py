def validate_semantics(days):

    violations = []

    invalid_types = [
        "peak",
        "viewpoint",
    ]

    for idx, day in enumerate(days):

        overnight_type = day.get(
            "overnight_type",
            ""
        )

        if overnight_type in invalid_types:

            violations.append(
                {
                    "day": idx + 1,
                    "issue":
                        f"Invalid overnight type: {overnight_type}",
                }
            )

    return violations
