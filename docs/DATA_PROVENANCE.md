# CairnOS Data Provenance

## Code License

CairnOSv1 project code is licensed under the Apache License 2.0. Source files
should carry an SPDX identifier where appropriate:

```text
SPDX-License-Identifier: Apache-2.0
```

The Apache 2.0 license applies to the project code and project-authored
documentation unless a file says otherwise.

## Data Licenses Are Separate

Datasets are not automatically Apache licensed. Data may have separate
copyright, database rights, attribution requirements, share-alike obligations,
or redistribution limits depending on the source.

Every reusable dataset should have a provenance row in `data/DATASETS.md`
before it is treated as reusable project material.

## OSM-Derived Data

OpenStreetMap-derived data may be subject to Open Database License (ODbL)
obligations. That can include attribution, database share-alike, and notices
for derived databases.

Do not assume an OSM-derived shapefile, crossing file, logistics file, or
compiled GeoJSON is Apache licensed. Record the upstream provider, download
date, source URL, license, and transformation steps before reuse.

## Manually Curated Cairn Data

Manually curated Cairn datasets should record:

- original source
- source license
- author or editor
- date collected or edited
- whether the data is raw, derived, manual, or generated
- transformation or curation notes
- known limitations

Manual edits based on maps, guidebooks, Gaia exports, OSM, or trail websites
must still cite those sources. "Manual" does not mean source-free.

## Generated Reports And Exports

Generated reports, cached files, planner exports, and temporary outputs should
not automatically be assumed Apache 2.0. Their reuse depends on the input
datasets, transformation chain, and any external data embedded in the output.

Generated files should generally go under `data/generated/` or another ignored
output directory unless they are deliberate release artifacts with documented
provenance.

## Runtime Data Validation

CairnOS includes a lightweight runtime data-quality validator:

```text
venv/bin/python -m cairn.runtime.data_quality trails/vermont_long_trail
```

The validator checks internal consistency across runtime files such as route
overlay, route master, resupply amenities, overnight references, approach
trails, terrain samples, spine geometry, and the operational graph.

Validation can identify broken references, missing fields, suspicious
coordinates, duplicate identifiers, mismatched summary counts, and known
reconciliation warnings. It is not a licensing review and does not convert
external source data into Apache-licensed project material.

## Current Compatibility Note

The historical Long Trail dataset currently remains under:

```text
trails/vermont_long_trail/
```

Those paths are used by compiler scripts, PlannerV2 tests, and the Streamlit
UI. Do not move them blindly. Future migrations should preserve compatibility
or add explicit path shims before moving data into `data/raw/`, `data/derived/`,
or `data/manual/`.

TODO: review each existing `trails/` dataset and replace `UNKNOWN — needs
review` provenance registry entries with source URLs, collection dates,
license terms, and transformation notes.
