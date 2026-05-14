# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from .validator_runner import (
    run_pytest,
    run_scenarios,
)

from .context_builder import (
    build_repair_context,
    build_feature_context,
)

from .llm_client import (
    generate_operations,
)

from .patch_manager import (
    save_operations,
    apply_operations,
    consolidate_operations,
)

from .git_tools import (
    ensure_clean_git,
    create_restore_point,
    restore_git,
)


class DevAgent:

    def validate(self):

        pytest_result = run_pytest()

        scenarios_result = run_scenarios()

        return (
            pytest_result,
            scenarios_result,
        )

    def summarize(
        self,
        pytest_result,
        scenarios_result,
    ):

        print(
            "\\n=== Validation Summary ===\\n"
        )

        print(
            "Pytest:",
            "PASS"
            if pytest_result["passed"]
            else "FAIL",
        )

        print(
            "Scenarios:",
            "PASS"
            if scenarios_result["passed"]
            else "FAIL",
        )

        if not pytest_result["passed"]:

            print(
                "\\nPytest Output:\\n"
            )

            print(
                pytest_result["output"]
            )

        print(
            "\\nScenario Output:\\n"
        )

        print(
            scenarios_result["output"]
        )

    def run_repair(self):

        print(
            "\\n=== CairnOS Dev Agent v1.3 (Repair) ===\\n"
        )

        ensure_clean_git()

        pytest_result = run_pytest()

        if pytest_result["passed"]:

            print(
                "No failing tests detected."
            )

            return

        context = build_repair_context(
            pytest_result["output"]
        )

        self.execute_operations(
            context
        )

    def run_feature(
        self,
        request,
    ):

        print(
            "\\n=== CairnOS Dev Agent v1.3 (Feature) ===\\n"
        )

        print(
            f"Feature Request: {request}"
        )

        ensure_clean_git()

        context = build_feature_context(
            request
        )

        self.execute_operations(
            context
        )

    def execute_operations(
        self,
        context,
    ):

        create_restore_point()

        operations = generate_operations(
            context
        )

        operations = consolidate_operations(
            operations
        )

        save_path = save_operations(
            operations
        )

        print(
            f"Saved operations: {save_path}"
        )

        applied = apply_operations(
            operations
        )

        if not applied:

            print(
                "\\nNo mutations applied."
            )

            return

        pytest_result, scenarios_result = (
            self.validate()
        )

        if (
            not pytest_result["passed"]
            or not scenarios_result["passed"]
        ):

            print(
                "\\nValidation failed."
            )

            print(
                "Rolling back changes..."
            )

            restore_git()

        self.summarize(
            pytest_result,
            scenarios_result,
        )
