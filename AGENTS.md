# Repository Instructions

## Project Boundary

CairnOSv1 is the operational expedition planning and reasoning layer. It should stay focused on itinerary feasibility, terrain-aware pacing, shelter and campsite selection, resupply and recovery reasoning, provenance-aware trail data, and clean export interoperability.

Do not turn CairnOS into a mobile app, offline navigation tool, map editor, social trail platform, guidebook replacement, or emergency/safety authority. Future HikerLogix work should treat CairnOS as the planning/export/calibration engine, not as the owner of iOS UI, HealthKit permissions, or local mobile persistence.

## Required Context

Before changing planner behavior, data semantics, exports, or roadmap language, read the relevant parts of:

- `README.md`
- `PROJECT_STATE.md`
- `ARCHITECTURE_GUARDRAILS.md`
- `docs/MVP_ROADMAP.md`
- `docs/DATA_PROVENANCE.md`

## Development Commands

Use the repository virtual environment when available:

```bash
venv/bin/python -m pytest cairn/tests -q
venv/bin/python -m py_compile cairn/planner/*.py cairn/runtime/*.py cairn/interfaces/streamlit_app.py
venv/bin/streamlit run cairn/interfaces/streamlit_app.py
```

If the venv is missing or stale, use Python 3.11 or newer and install from `requirements.txt` for full local development. The hosted Streamlit app uses `cairn/interfaces/requirements.txt`.

## Multi-Repository Workflow

CairnOSv1 and HikerLogix should be opened together as a VS Code multi-root
workspace, not combined as one Git repository or Git worktree. The expected
workspace file is:

- `/Users/ecorbett/Documents/Development/CairnOS-HikerLogix.code-workspace`

Keep repository responsibilities separate:

- CairnOSv1 owns planner behavior, data semantics, exports, diagnostics, and
  schema-versioned plan JSON.
- HikerLogix owns iOS UI, local plan import, local actuals, field logging, and
  user-owned mobile persistence.

When a feature changes the CairnOS/HikerLogix contract, use matching
short-lived branches and separate PRs in both repositories. Example:

- CairnOSv1: `codex/plan-json-v2`
- HikerLogix: `codex/import-plan-json-v2`

Merge order should preserve the contract boundary: land CairnOS export/schema
changes first, then update HikerLogix import/UI behavior against the committed
fixture or schema.

## Tooling Expectations

- Use the GitHub MCP/plugin for GitHub issue, PR, roadmap, and review work.
- Use the Build iOS Apps/XcodeBuildMCP tooling for HikerLogix build, run, test,
  simulator launch, screenshots, and UI inspection when available.
- Use shell commands for local file inspection and Python test runs when they
  are simpler and deterministic.
- Keep generated scratch outputs, private diagnostics, simulator state, and
  tester data out of both repositories unless intentionally added as fixtures.

## Research And Browser Automation

Node REPL may be used for read-only inspection, temporary structured-data
analysis, and browser automation.

Do not use Node REPL to edit CairnOS files, install npm packages into this
repository, create `package.json` or `package-lock.json`, or write generated
artifacts into the repository unless explicitly requested.

Temporary Node REPL research artifacts should go under:

- `~/.codex/scratch/cairnos-research`
- `~/.codex/scratch/hikerlogix-research`

Anything worth preserving should become a GitHub issue, documented research
note, implementation plan, or intentional repository artifact.

## Architecture Rules

- Keep `PlannerV2` as the public integration facade for Streamlit, tests, exports, and future HikerLogix interoperability.
- Keep terrain, logistics, recovery, and itinerary synthesis in focused helper modules behind `PlannerV2`.
- Preserve NOBO and SOBO parity. Direction changes traversal order over northbound-reference guidebook miles; it must not invent a separate SOBO mile system.
- Treat `route_overlay.json` and compiled operational overlay semantics as traversal authority.
- Keep behavior changes separate from refactors whenever practical, and add or update tests for intentional planner behavior changes.
- Gaia export behavior must not regress when adding other export formats.

## Data And Provenance

- Prefer official trail organizations, public agencies, and clearly licensed open datasets.
- Do not scrape or reconstruct proprietary guidebooks, EPUBs, paid apps, or copyrighted curated tables.
- Treat community datasets and third-party exports as candidate inputs until license, provenance, and operational accuracy are reviewed.
- Record external research sources in `docs/RESEARCH_LOG.md` when they influence planner behavior, data modeling, UI language, roadmap priority, or alpha-feedback interpretation.
- Do not commit secrets, private Streamlit settings, private tester data, private route exports, local calibration inputs, or generated reports unless explicitly intended.
- User-owned actuals from future HikerLogix imports should be calibration inputs only; they must not override CairnOS trail data or operational truth.

## UI And Documentation

- The Streamlit UI is an alpha review surface, not the core product boundary.
- Keep safety language explicit: CairnOS is advisory planning software and users must verify routes, services, closures, weather, water, and backcountry decisions with official sources.
- Roadmap changes should preserve the current sequence unless explicitly changed: stabilize Long Trail THRU, harden data quality, reconcile terrain/mile systems, move toward overlay-authoritative traversal, then SECTION planning before broader integrations.
