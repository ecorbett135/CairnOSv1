## Summary

What changed and why?

## Type of Change

- [ ] Bug fix
- [ ] Feature
- [ ] Documentation
- [ ] Data/provenance update
- [ ] Test-only change
- [ ] Refactor with no intended behavior change

## Testing Performed

List commands run, manual Streamlit checks, exported files inspected, or explain
why testing was not run.

```text
venv/bin/python -m pytest cairn/tests -q
venv/bin/python -m py_compile cairn/planner/*.py cairn/runtime/*.py cairn/interfaces/streamlit_app.py
git diff --check
```

## Data Files Touched

- [ ] No trail/data files changed
- [ ] Raw source data changed
- [ ] Derived/compiled data changed
- [ ] Manual Cairn data changed
- [ ] Generated outputs changed intentionally

If data changed, describe source, license/provenance, transformation steps, and
whether `data/DATASETS.md` or `docs/DATA_PROVENANCE.md` needs an update.

## Research Sources Used

- [ ] No external research sources influenced this change
- [ ] `docs/RESEARCH_LOG.md` was updated for external research used
- [ ] Existing research-log entries already cover the sources used

If web, community, app-comparison, map, guidebook, or user-export research
influenced this change, list the sources and how they were used.

## Screenshots / Output Examples

Attach screenshots, CSV snippets, Gaia GeoJSON examples, or calibration reports
when the change affects UI, exports, itinerary output, or data validation.

## Planner Safety Checklist

- [ ] I did not treat CairnOSv1 output as safety-critical field guidance.
- [ ] I preserved deterministic planner behavior or added tests for intended changes.
- [ ] I preserved NOBO/SOBO parity or documented why a behavior is direction-specific.
- [ ] I did not move trail data paths without compatibility shims and tests.
- [ ] I did not commit secrets, private tester data, or unreviewed vendor exports.
- [ ] I updated docs or tests where user-facing behavior changed.
