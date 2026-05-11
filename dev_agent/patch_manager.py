from pathlib import Path
import json


PATCH_DIR = Path(
    "dev_agent/generated_patches"
)

PATCH_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

MAX_OPERATIONS = 20


def save_operations(
    operations,
):

    path = (
        PATCH_DIR
        / "latest_operations.json"
    )

    path.write_text(
        json.dumps(
            operations,
            indent=2,
        )
    )

    return path


def consolidate_operations(
    operations,
):

    ops = operations.get(
        "operations",
        [],
    )

    consolidated = []

    seen = set()

    for op in ops:

        key = (
            op["file"],
            op["search"],
        )

        if key in seen:
            continue

        seen.add(key)

        consolidated.append(op)

    return {
        "operations":
            consolidated[
                :MAX_OPERATIONS
            ]
    }


def validate_operations(
    operations,
):

    errors = []

    ops = operations.get(
        "operations",
        [],
    )

    if not ops:

        errors.append(
            "No operations generated."
        )

        return errors

    if len(ops) > MAX_OPERATIONS:

        errors.append(
            f"Too many operations: {len(ops)}"
        )

    for i, op in enumerate(ops):

        if (
            "file" not in op
            or "search" not in op
            or "replace" not in op
        ):

            errors.append(
                f"Operation {i} missing required keys."
            )

            continue

        file_path = Path(
            op["file"]
        )

        if not file_path.exists():

            errors.append(
                f"Missing file: {file_path}"
            )

            continue

        original = (
            file_path.read_text()
        )

        if op["search"] not in original:

            errors.append(
                f"Search block not found in "
                f"{file_path}"
            )

    return errors


def apply_operations(
    operations,
):

    #
    # transactional apply:
    # validate EVERYTHING first
    #

    validation_errors = (
        validate_operations(
            operations
        )
    )

    if validation_errors:

        print(
            "\\nOperation validation failed:"
        )

        for err in validation_errors:

            print(f" - {err}")

        return False

    #
    # only mutate AFTER all checks pass
    #

    applied = []

    for op in operations.get(
        "operations",
        [],
    ):

        file_path = Path(
            op["file"]
        )

        original = (
            file_path.read_text()
        )

        updated = original.replace(
            op["search"],
            op["replace"],
            1,
        )

        file_path.write_text(
            updated
        )

        applied.append(
            str(file_path)
        )

    print(
        "\\nApplied operations:"
    )

    for f in applied:

        print(f" - {f}")

    return True
