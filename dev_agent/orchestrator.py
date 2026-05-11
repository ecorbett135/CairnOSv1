from .context import build_context
from .llm import call_llm
from .patch import apply_patch
from .test_runner import run_tests

class DevOrchestrator:
    def __init__(self, max_loops=5):
        self.max_loops = max_loops

    def run(self):
        for i in range(self.max_loops):
            print(f"Iteration {i+1}")

            context = build_context()
            patch = call_llm(context)

            if patch.strip():
                apply_patch(patch)

            result = run_tests()

            print(result["output"])

            if result["passed"]:
                print("All tests passed.")
                return

        print("Reached maximum iterations.")
