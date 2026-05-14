# CairnOS Data Layout

This directory is the forward-looking landing zone for project data. Existing
runtime and compiler paths under `trails/` are intentionally preserved for now
so current planner behavior and tests continue to work.

TODO: migrate existing `trails/` datasets into this structure only after the
compiler, runtime, UI, and tests have explicit compatibility shims.

| Directory | Purpose | Commit Policy |
| --- | --- | --- |
| `raw/` | Untouched source files exactly as received from upstream sources. | Commit only when source license and provenance are recorded in `DATASETS.md`; large files should use Git LFS. |
| `derived/` | Transformed datasets derived from external sources such as OSM, GPX, DEM, or other upstream datasets. | Commit only when transformation notes and upstream license obligations are documented. |
| `manual/` | Manually curated Cairn datasets authored or edited by project maintainers. | Commit with author/editor, date, source references, and curation notes. |
| `generated/` | Generated reports, plans, exports, temporary outputs, and cache files. | Ignored by default except `.gitkeep`; commit only deliberate release artifacts with provenance notes. |

See `DATASETS.md` for the current provenance registry and
`../docs/DATA_PROVENANCE.md` for data licensing guidance.
