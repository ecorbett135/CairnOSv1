from pathlib import Path

def read_file(path):
    return Path(path).read_text()

def build_context():
    context = {}

    for folder in ["app", "tests", "docs"]:
        for path in Path(folder).rglob("*.py"):
            context[str(path)] = read_file(path)

    return context
