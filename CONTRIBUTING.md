# Contributing to CairnOSv1

Thank you for helping improve CairnOSv1. The project values operational trail
truth, clear provenance, deterministic planning behavior, and respectful
feedback from hikers and developers.

CairnOSv1 is alpha software. Contributions should improve trust, clarity,
testing, or itinerary realism without making the project sound production-ready.

## Development Setup

Use Python 3.11 or newer.

```bash
python -m venv venv
venv/bin/python -m pip install -r requirements.txt
```

Run the Streamlit app locally with:

```bash
venv/bin/streamlit run cairn/interfaces/streamlit_app.py
```

The hosted Streamlit alpha uses:

```text
cairn/interfaces/requirements.txt
```

That file is intentionally smaller than the root development requirements.

## Running Tests

Before opening a pull request that changes code or planner behavior, run:

```bash
venv/bin/python -m pytest cairn/tests -q
venv/bin/python -m py_compile cairn/planner/*.py cairn/runtime/*.py cairn/interfaces/streamlit_app.py
git diff --check
```

For data-quality changes, also run:

```bash
venv/bin/python -m cairn.runtime.data_quality trails/vermont_long_trail
```

For elevation calibration work, local reference files may be placed in the
ignored `elevation_calibration/` directory. Do not commit vendor route exports
unless provenance and reuse rights have been reviewed.

## Code Contribution Expectations

- Keep edits scoped to the behavior being changed.
- Prefer existing project patterns over new abstractions.
- Keep `PlannerV2` as the public planner facade.
- Preserve deterministic planner behavior, or add tests for intentional changes.
- Preserve NOBO and SOBO parity unless the change is explicitly
  direction-specific.
- Do not treat planner output as safety-critical guidance.
- Do not commit secrets, private Streamlit settings, private tester data, or
  unreviewed vendor exports.
- Do not commit private HikerLogix implementation details, mobile monetization
  experiments, private user actuals, or patent-sensitive notes to CairnOSv1.

Unless otherwise stated, source-code contributions to CairnOSv1 are made under
the Apache 2.0 license used by the project. Data contributions remain subject
to the data provenance rules below.

## Alpha Scope Boundaries

CairnOSv1 should remain an operational expedition-planning aid. It should not
try to replace:

- official trail organization guidance
- land-manager notices or closure information
- maps, navigation apps, guidebooks, or field judgment
- weather, water, medical, or emergency decision-making

Current MVP work is focused on Long Trail THRU planning, NOBO/SOBO parity,
terrain-aware pacing, resupply/recovery semantics, data quality, and exports.
SECTION planning is intentionally deferred in the UI.

## Data Contribution Rules

Every data contribution must include:

- original source
- source license
- whether it is raw, derived, manual, or generated
- transformation steps
- date collected
- maintainer or editor
- known limitations

Use these categories consistently:

- `raw`: untouched source files exactly as received
- `derived`: transformed data derived from external sources
- `manual`: manually curated Cairn datasets
- `generated`: reports, exports, caches, or generated outputs

Do not submit external data as Apache 2.0 unless the source license explicitly
allows that treatment. OSM-derived data may be subject to ODbL obligations and
must be marked accordingly.

Update `data/DATASETS.md` for any new dataset or meaningful data edit. If
provenance is incomplete, mark fields as `UNKNOWN — needs review` rather than
guessing.

## Reporting Trail-Data Corrections

Use the Trail or Data Issue template when reporting:

- incorrect shelter, campsite, or overnight metadata
- missing or misplaced road crossings or trailheads
- questionable elevation gain/loss
- resupply or town-access corrections
- Gaia export marker placement problems
- ingress or egress approach issues

Please include source links, field-observation dates, screenshots, or exported
files when available. Do not paste large excerpts from copyrighted guidebooks or
proprietary services.

## Documentation And Style

- Prefer clear, practical language over marketing language.
- Label alpha limitations honestly.
- Use `CairnOSv1` for the project name in user-facing docs.
- Use `CairnOS` only when referring to the broader architecture or internal
  package concepts.
- Keep Markdown lint-friendly: one top-level title per document, no repeated
  blank lines, and fenced code blocks for commands.
