# Open Source And IP Strategy

This document records the current working posture for CairnOSv1, HikerLogix,
and related intellectual-property questions. It is project guidance, not legal
advice. Patent, trademark, App Store, and company-formation questions should be
reviewed with qualified counsel before major commercial decisions.

## Current Recommendation

Keep CairnOSv1 public and Apache 2.0 licensed.

That posture fits the current alpha because CairnOSv1 needs:

- public Streamlit Community Cloud deployment
- visible tester trust
- reproducible GitHub issues and diagnostics
- open collaboration around planner behavior and data quality
- a license that permits later commercial use by HikerLogix

Apache 2.0 is permissive. It allows commercial use, modification, distribution,
and private use, while preserving copyright notices and providing an express
patent license for covered contributions. That makes it a practical license for
an open planning engine that may later feed a proprietary or paid companion app.

## What Apache 2.0 Does Not Do

Apache 2.0 does not protect the business model.

It does not prevent someone from:

- using the public CairnOSv1 code in another product
- forking the planner
- deploying a competing hosted version
- building their own mobile client around the exported plans

The defensible commercial layer should therefore come from product execution,
mobile UX, personal actuals, calibration, curated datasets with clean rights,
hosted services, support, and HikerLogix packaging rather than from assuming the
public planner code cannot be reused.

## HikerLogix Boundary

HikerLogix should remain private and proprietary unless a separate decision is
made to open it.

CairnOSv1 being public for alpha deployment does not require the iOS app,
mobile persistence model, HealthKit integration, App Store packaging,
monetization logic, or personal-actuals workflow to be public or open source.

The preferred split is:

- CairnOSv1: public Apache-licensed planning/export/calibration engine
- HikerLogix: private mobile field journal, actuals, packaging, and paid
  product surface

If HikerLogix imports CairnOS plan JSON, that should be treated as normal
permissive-license use of CairnOS output and code contracts, not as a reason to
relicense the mobile app.

## Copyright Implications

Copyright protects original expression such as source code, documentation,
images, and creative UI assets. It does not protect facts, ideas, systems,
methods of operation, or the general concept of an operational hiking planner.

For CairnOSv1, copyright protection is strongest around:

- source code implementation
- project-authored documentation
- screenshots and original project assets
- authored schema definitions and explanatory text

Copyright is weaker or unavailable for:

- trail facts
- mile markers
- public road names
- shelter names
- generic planning ideas
- methods or algorithms described only as abstract concepts

Trail data can also carry separate database, attribution, or share-alike
obligations. Data provenance remains a separate concern from source-code
copyright.

## Patent Implications

The current CairnOSv1 work appears more like an applied software system than a
clearly patent-focused invention, but that should not be treated as a legal
conclusion.

Important practical points:

- Public disclosure can affect patent rights. In the United States, there may
  be a limited one-year grace period for an inventor's own disclosure, but
  foreign rights can be stricter.
- Apache 2.0 includes a patent grant from contributors for patent claims
  necessarily infringed by their contributions.
- If a future CairnOS or HikerLogix technique seems genuinely novel and
  commercially important, discuss a provisional patent strategy before
  publishing the implementation or detailed design.
- Do not publish private architecture notes, unpublished algorithm details, or
  commercial roadmap specifics merely because the repo is public.

Near-term practical posture:

- keep ordinary CairnOS planner code Apache 2.0
- keep genuinely sensitive HikerLogix monetization and mobile implementation
  private
- treat patent review as an exception path for clearly novel calibration,
  personalization, or operational feasibility techniques

## Repository Visibility

CairnOSv1 can remain public because public visibility supports alpha testing
and Streamlit hosting. Public visibility should not be confused with publishing
every related asset.

Do not commit:

- private tester diagnostics unless explicitly approved
- proprietary Gaia, Garmin, FarOut, HiiKER, guidebook, or paid-app data
- private HikerLogix implementation details
- App Store monetization experiments
- secrets, keys, health data, location actuals, or private field logs
- patent-sensitive implementation notes before review

## Licensing Alternatives Considered

No license / all rights reserved:

- possible for a public GitHub repository, but poor for outside trust and
  contributions
- would complicate tester/developer reuse
- does not undo rights already granted for Apache-licensed commits

Copyleft licenses:

- stronger reciprocity, but harder to combine with proprietary mobile and
  commercial distribution strategies
- likely unnecessary for the current alpha goals

Source-available or delayed-open licenses:

- can protect some commercial exclusivity, but are not standard open source
- add complexity and may reduce contributor trust
- not needed unless CairnOS itself becomes the paid product boundary

Current decision:

- keep CairnOSv1 Apache 2.0
- keep HikerLogix private/proprietary for now
- keep trail data provenance separate from code licensing

## Decision Triggers

Revisit this posture if:

- CairnOS becomes a hosted paid service rather than only a planning engine
- outside contributors begin submitting significant code without a contributor
  agreement
- HikerLogix starts embedding substantial CairnOS code instead of consuming
  exported plans
- premium curated datasets become a major product asset
- a truly novel personalization, calibration, or feasibility method emerges
- investors, partners, or App Store distribution create new IP requirements
