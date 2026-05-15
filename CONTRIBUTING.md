# Contributing to CairnOSv1

Thank you for helping improve CairnOSv1. The project values operational trail
truth, clear provenance, and changes that keep planner behavior testable.

## Code contributions

- Keep edits scoped to the behavior being changed.
- Prefer existing project patterns over new abstractions.
- Run the test suite before proposing a stable merge:

```bash
python -m pytest cairn/tests -q
```

## Data contribution rules

Every data contribution must include:

- original source
- source license
- whether it is raw, derived, manual, or generated
- transformation steps
- date collected
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
