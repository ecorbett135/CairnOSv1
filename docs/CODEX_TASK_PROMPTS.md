# Codex Task Prompts

Use these prompts as starting points for repeatable CairnOS work.

## Planner Regression Review

```text
Review the current CairnOS planner behavior for regressions. Read README.md, PROJECT_STATE.md, ARCHITECTURE_GUARDRAILS.md, docs/MVP_ROADMAP.md, cairn/planner/, cairn/runtime/, and relevant tests. Focus on PlannerV2 behavior, NOBO/SOBO parity, resupply/recovery semantics, terrain-derived elevation reporting, and Gaia export compatibility. Do not make code changes unless explicitly asked. Return findings with file/line references and the smallest safe fix for each issue.
```

## Trail Data Source Audit

```text
Audit candidate public data sources for adding or improving a trail in CairnOS. Prefer official trail organizations, USFS/NPS/state agencies, ArcGIS portals, and clearly licensed open repositories. For each source, record URL, owner, license/provenance status, update cadence if visible, data types, likely fields, and operational risks. Do not scrape proprietary guidebooks, EPUBs, paid apps, or copyrighted curated tables. Return a source-quality ranking and recommended ingestion path.
```

## Roadmap Update

```text
Update CairnOS roadmap language for a proposed feature. Read README.md, PROJECT_STATE.md, ARCHITECTURE_GUARDRAILS.md, and docs/MVP_ROADMAP.md first. Keep CairnOS positioned as an operational planning and export interoperability layer. Identify where the feature belongs relative to data-quality hardening, terrain/mile reconciliation, overlay-authoritative traversal, SECTION planning, and future integrations. Keep the update concise and avoid implying production safety authority.
```

## HikerLogix Integration Planning

```text
Evaluate a future HikerLogix integration for CairnOS. Treat CairnOS as the source of planned itinerary truth and HikerLogix as a future iOS field journal and actuals capture layer. Start with file-based interoperability, not a network API. Consider a schema-versioned CairnOS plan JSON export built from PlannerV2 output, plus a later user-owned actuals import for personal calibration. Preserve Gaia export behavior and do not move mobile UI, HealthKit, or offline persistence responsibilities into CairnOS.
```

