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

## Research Sources Are Separate

External research that influences planning behavior, scoring, UI copy, roadmap
priority, or data-modeling decisions should be recorded in
`docs/RESEARCH_LOG.md`.

The research log is separate from the dataset registry. A source can be useful
qualitative research without becoming reusable data. If research material later
becomes committed raw, derived, manual, or generated data, also update
`data/DATASETS.md`.

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

Structured resupply access-friction fields, such as access distance and
convenience class, are curated data. They must retain source notes and should
not be treated as independently Apache licensed unless the upstream source
chain has been reviewed.

Structured overnight amenity fields, such as bear-box availability, are
manually curated trail data. They must retain source, access date, and curation
notes, and should be treated as planning context rather than a field guarantee.

Business-level town details, including lodging, outfitters, shuttles,
restaurants, and mail-drop acceptance, are more volatile than town-level
service categories. Do not bulk-copy third-party business listings into
committed CairnOS data. Each listing should be checked against an independent
current source, preferably the business site or an official/town tourism
source, before it becomes reusable data.

Curated lodging-support rows may improve recovery confidence, but they remain
advisory business metadata. Shuttle, pickup, reservation, and transportation
precision changes too frequently for the MVP planner output and should remain
out of user-facing tables unless a future source-validation model explicitly
supports it.

Side-trip options are also volatile experience data. A side trip may depend on
hours, reservations, transportation, season, age restrictions, or personal
interest. Treat side-trip rows as advisory annotations only unless future
planner behavior explicitly models their time cost. Named side trips should
retain candidate-source, validation-source, validation-date, and validation
status fields.

Long Trail guide pages, route-review pages, and hiking articles used during
research are not automatically reusable datasets. They can inform product
direction, UI framing, issue prioritization, and candidate-source discovery,
but do not copy route tables, business lists, reviews, maps, photos, prose, or
planning figures into CairnOS unless reuse rights and provenance are reviewed.

Season, current-condition, transportation, and water-source metadata are
especially dynamic. Prefer official trail organizations, public agencies,
business/town sites, or clearly licensed open data for committed rows. Retain
source URL, source type, validation date, validation status, and review notes,
and keep user-facing output advisory unless a future feature explicitly models
operational effects.

## Generated Reports And Exports

Generated reports, cached files, planner exports, and temporary outputs should
not automatically be assumed Apache 2.0. Their reuse depends on the input
datasets, transformation chain, and any external data embedded in the output.

Generated files should generally go under `data/generated/` or another ignored
output directory unless they are deliberate release artifacts with documented
provenance.

## Commercial And Companion-App Boundary

Future HikerLogix work may use CairnOS exports or Apache-licensed CairnOS code,
but that does not convert external trail datasets into proprietary mobile-app
assets, and it does not convert HikerLogix user actuals into CairnOS trail
truth.

Before using any dataset in a paid app, hosted service, premium trail pack, or
commercial export, record:

- source owner
- source license or terms
- attribution requirements
- redistribution limits
- whether the data can be used commercially
- whether share-alike obligations apply

If the answer is unclear, mark the dataset as `UNKNOWN — needs review` and do
not treat it as a reusable commercial asset.

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
