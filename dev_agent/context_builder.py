from pathlib import Path

CORE_FILES = [
    "app/core/planner.py",
    "interfaces/streamlit_app.py",
]

TEST_FILES = [
    "tests/test_planner.py",
    "tests/test_scenarios.py",
    "tests/test_semantics.py",
]

def read_file(path):
    return Path(path).read_text()

def add_files(context, files):

    for path in files:

        p = Path(path)

        if p.exists():

            context.append(
                f"\n=== FILE: {path} ===\n"
            )

            context.append(
                read_file(path)
            )

def build_repair_context(pytest_output):

    context = []

    context.append("=== REPAIR MODE ===")
    context.append("\n=== PYTEST OUTPUT ===\n")
    context.append(pytest_output)

    add_files(context, CORE_FILES)
    add_files(context, TEST_FILES)

    return "\n".join(context)

def build_feature_context(request):

    context = []

    context.append("=== FEATURE MODE ===")
    context.append("\n=== FEATURE REQUEST ===\n")
    context.append(request)

    lower = request.lower()

    files = []

    if (
        "planner" in lower
        or "overnight" in lower
        or "trail" in lower
        or "section" in lower
    ):
        files.append(
            "app/core/planner.py"
        )

    if (
        "ui" in lower
        or "streamlit" in lower
        or "input" in lower
    ):
        files.append(
            "interfaces/streamlit_app.py"
        )

    if not files:
        files = CORE_FILES

    add_files(context, files)
    add_files(context, TEST_FILES)

    return "\n".join(context)
