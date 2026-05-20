# Research Log

This log records external research sources that have informed CairnOSv1
planning behavior, product boundaries, data-quality priorities, or future
roadmap decisions.

Research sources are not automatically data sources. A Reddit thread, route
planner, map service, blog post, or hiking website can be useful product
research without becoming operational truth or reusable project data.

When research becomes committed data, update `data/DATASETS.md` and the
relevant raw/manual/derived dataset notes.

## Rules

- Log research sources when they influence planner behavior, data modeling,
  roadmap priority, UI copy, or alpha feedback interpretation.
- Prefer official trail organizations, land managers, public agencies, and
  clearly licensed datasets for operational data.
- Treat Reddit, forums, blogs, and social discussions as qualitative signal,
  not authoritative data.
- Treat Gaia, Garmin, HiiKER, FarOut, guidebooks, and similar tools as
  comparison references only unless explicit reuse rights are reviewed.
- Do not copy proprietary tables, maps, guidebook text, paid-app data, or
  long user comments into the repo.
- Record uncertainty directly instead of normalizing it away.

## Source Types

| Type | Meaning | Allowed Use |
| --- | --- | --- |
| Official trail or land-manager source | Trail organization, agency, park, forest, or official maintainer | Strong candidate for operational data after license/provenance review |
| Third-party planning guide | Public hiking website or independent planner | Planning context, candidate data, comparison, and provenance review |
| Community discussion | Reddit, forums, social groups, direct tester feedback | Qualitative signal and product research only |
| Navigation or mapping tool | Gaia, Garmin, HiiKER, FarOut, map layers, route summaries | Comparison and calibration only unless rights are reviewed |
| User-owned export | GPX, GeoJSON, KML, FIT, TCX, or CSV created by the maintainer/tester | Local calibration or diagnostics; do not commit unless intended and reviewed |

## Backfilled Research Sources

These rows were reconstructed from prior project discussion on 2026-05-19.
They are intentionally conservative: if exact thread URLs or collection dates
were not preserved, the row says so.

| Logged | Topic | Source | URL | Source Type | Used For | Reliability | IP/Data Risk | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-05-19 | Long Trail overnight site coverage | Green Mountain Club overnight accommodations | [GMC overnight accommodations](https://www.greenmountainclub.org/the-long-trail/overnight-accommodations/) | Official trail organization | Confirmed that the initial planner dataset underrepresented possible overnight shelters/campsites; motivated overnight site enrichment | High for existence/context; exact data still requires provenance review | Medium | Do not copy page text wholesale. Use as official context and cite if specific shelter/campsite attributes become data. |
| 2026-05-19 | Bear-box amenity source | Green Mountain Club bear boxes | [GMC bear boxes](https://www.greenmountainclub.org/bear-boxes/) | Official trail organization | Promoted into manually curated `overnight_amenities.csv` for structured bear-box site metadata and optional planner preference | High for current public page content, subject to change | Medium | Source is site-name amenity context only. Verify current GMC information before field use. |
| 2026-05-19 | Long Trail resupply amenities | Long Trail Planning Guide trail-town amenities | [Trail town amenities](https://www.longtrailvermont.com/trail-town-amenities/) | Third-party planning guide | Seeded resupply town/access/service concepts and current `resupply_amenities.csv` provenance | Medium; practical but not official trail authority | Medium to high | Current CSV cites this source and manual curation. Do not assume Apache licensing for copied/derived data. |
| 2026-05-19 | Long Trail SOBO resupply amenities | Long Trail Planning Guide SOBO trail-town amenities | [SOBO trail town amenities](https://www.longtrailvermont.com/trail-town-amenities-sobo/) | Third-party planning guide | Comparison source for direction-specific presentation of the same town-service concepts | Medium; practical but not official trail authority | Medium to high | Use as comparison/order context only. Preserve northbound-reference guidebook miles and do not copy page tables wholesale. |
| 2026-05-19 | Long Trail lodging, outfitters, and mail-drop candidates | Long Trail Planning Guide lodging and outfitters | [Lodging and Outfitters](https://www.longtrailvermont.com/lodging-outfitters/) | Third-party planning guide | Candidate future source for town-detail enrichment around lodging, outfitters, and mail-drop options | Medium; practical but business listings are volatile and not official trail authority | High | Do not scrape or bulk-copy the list. Validate each business against an independent current source before committing any business-level detail. |
| 2026-05-19 | Long Trail side-trip candidates | Long Trail Planning Guide side trips | [Side trips](https://www.longtrailvermont.com/side-trips/) | Third-party planning guide | Candidate source for optional brewery, town, attraction, and fishing side-trip annotations | Medium; experience suggestions are volatile and not operational trail authority | High | Do not scrape or bulk-copy the list. Independently validate named options and keep side trips annotation-only unless future planner logic models time cost. |
| 2026-05-19 | Long Trail guide research refresh | CleverHiker Long Trail guide | [CleverHiker Long Trail guide](https://www.cleverhiker.com/backpacking/a-short-guide-to-vermonts-long-trail/) | Third-party planning guide | Qualitative context for rugged terrain, season timing, resupply/zero expectations, and feature gaps around itinerary explainability | Medium; updated public guide but not official trail authority | Medium | Use for product framing only. Do not copy narrative text, photos, or planning figures into committed data. |
| 2026-05-19 | Long Trail map/review product comparison | AllTrails Long Trail page | [AllTrails Long Trail](https://www.alltrails.com/trail/us/vermont/the-long-trail--5) | Navigation or mapping tool | Comparison signal for map-first route overview, reviews, broad difficulty, and current-condition expectations | Medium for product comparison; not CairnOS trail authority | High | Do not scrape reviews, maps, ratings, or user content. Use only to identify planning gaps CairnOS can fill. |
| 2026-05-19 | Long Trail preparation and advisory context | REI Expert Advice Long Trail | [REI Long Trail advice](https://www.rei.com/learn/expert-advice/how-to-hike-the-long-trail.html) | Third-party planning guide | Qualitative context for flexible itineraries, harsh terrain, variable weather, hunting-season awareness, and preparation reminders | Medium; credible general guidance but not official trail authority | Medium | Use for roadmap/UI framing only. Official conditions and closures should still point to GMC or agency sources. |
| 2026-05-19 | Experience-aware Long Trail planning | The Trek Vermont Long Trails article | [The Trek article](https://thetrek.co/appalachian-trail/vermonts-long-trails/) | Third-party/community media | Qualitative signal that optional experiences, side trails, and town choices are part of itinerary value | Low to medium; narrative source, not reusable data | Medium | Do not copy personal narrative. Use only to frame side-trip and experience-preference roadmap work. |
| 2026-05-19 | Resupply, water, and town-planning comparison | Greenbelly Long Trail guide | [Greenbelly Long Trail guide](https://www.greenbelly.co/pages/long-trail-vermont) | Third-party planning guide | Qualitative comparison for town abundance, food-carry expectations, water-treatment reminders, and outfitter/town-service concepts | Medium; practical but not official trail authority | High | Do not copy business tables or named service lists. Validate any named option through current independent sources before committing. |
| 2026-05-19 | SECTION planning product shape | Long Trail Planning Guide section-hike suggestions | [Section hike suggestions](https://www.longtrailvermont.com/section-hike-suggestions/) | Third-party planning guide | Qualitative context for future SECTION endpoint access, transit/shuttle friction, and town-service reasoning | Medium; useful product shape but static third-party guide | High | Do not copy maps, itineraries, or tables. Use to inform SECTION semantics and access-friction issue tracking only. |
| 2026-05-19 | Official trail-season and current-condition context | Green Mountain Club mud season, trail updates, overnight sites, and Side-to-Side pages | [Mud season](https://www.greenmountainclub.org/hiking/mud-season/), [trail updates](https://www.greenmountainclub.org/hiking/trail-updates/), [overnight sites](https://www.greenmountainclub.org/the-long-trail/overnight-accommodations/), [Side-to-Side](https://www.greenmountainclub.org/the-long-trail/side-to-side/) | Official trail organization | Candidate authority for date-aware advisories, current-update prompts, overnight water caveats, and official side-trail context | High for official context; current pages can change | Medium | Use as the preferred source family for advisory language, but keep CairnOS advisory and require users to verify current conditions. |
| 2026-05-19 | NOBO resupply spacing comparison | Long Trail Planning Guide northbound resupply maps | [Northbound resupply maps](https://www.longtrailvermont.com/northbound-resupply-maps/) | Third-party planning guide | Qualitative comparison for expected resupply spacing and cadence behavior | Medium | Medium to high | Use as comparison signal only. Do not copy maps, route plans, or tables into CairnOS. |
| 2026-05-19 | SOBO resupply spacing comparison | Long Trail Planning Guide southbound resupply maps | [Southbound resupply maps](https://www.longtrailvermont.com/southbound-resupply-maps/) | Third-party planning guide | Qualitative comparison for SOBO resupply spacing and parity | Medium | Medium to high | Use as comparison signal only. Do not copy maps, route plans, or tables into CairnOS. |
| 2026-05-19 | Long Trail planning sentiment | Reddit `r/longtrail` planning search | [r/longtrail planning search](https://www.reddit.com/r/longtrail/search/?q=planning&type=posts&t=year) | Community discussion | Product research around common planning questions, resupply concerns, and tester outreach | Variable | Medium | No individual posts/comments have been formally logged. Future use should record specific post URLs and summarize, not copy. |
| 2026-05-19 | Appalachian Trail discussions mentioning Long Trail | Reddit `r/AppalachianTrail` | Not preserved as a specific URL | Community discussion | Candidate qualitative research source for Long Trail overlap, northern Vermont difficulty, and resupply norms | Variable | Medium | Mentioned as useful, but no specific thread was logged. Future research must capture exact URLs. |
| 2026-05-19 | Competitive/product boundary | HiiKER hike planner | [HiiKER hike planner](https://hiiker.app/hike-planner) | Navigation/planning product | Helped clarify CairnOS boundary: operational reasoning/export layer, not a general route planner or app replacement | Medium | Low if used only for product positioning | Do not copy UI, data, route content, or proprietary behavior. |
| 2026-05-19 | Gaia export interoperability | Gaia GPS app and route summaries | User-owned Gaia links and local exports; exact public URLs vary | Navigation/mapping tool and user-owned export | Marker compatibility, elevation comparison, and route-alignment calibration | Useful comparison; not authoritative for Cairn trail truth | Medium to high | Gaia/Garmin exports belong in ignored `elevation_calibration/` unless explicitly reviewed. |
| 2026-05-19 | Garmin elevation comparison | Garmin Explore map | [Garmin Explore](https://explore.garmin.com/Map) | Navigation/mapping tool | Candidate cross-check for elevation calibration against Gaia and Cairn terrain | Useful comparison; not authoritative for Cairn trail truth | Medium | Avoid scraping or committing proprietary Garmin-derived data. |
| 2026-05-20 | Alpha feedback collection | GitHub Issues and Reddit alpha post | [GitHub issue templates](https://github.com/ecorbett135/CairnOSv1/issues/new/choose), [Reddit alpha post](https://www.reddit.com/r/longtrail/comments/1tflcar/built_a_small_long_trail_itinerary_planner_and/) | Direct tester feedback and community discussion | Collect reproducible alpha reports through diagnostics ZIP attachments while keeping a no-account screenshot/settings fallback in community threads | High for user feedback; subjective | Low to medium | Feedback is product research unless a tester-provided file becomes a dataset or fixture. Do not publish private contact information or tester diagnostics outside the issue/report context. |
| 2026-05-20 | Long Trail completion-duration calibration | Green Mountain Club thru-hike and End-to-End planning pages; The Trek preparation guide | [GMC thru-hike page](https://www.greenmountainclub.org/hiking/thru-hike-long-trail-vermont/), [GMC End-to-End planning](https://www.greenmountainclub.org/end-end-planning/), [The Trek Long Trail preparation](https://thetrek.co/how-to-prepare-for-your-long-trail-thru-hike/) | Official trail organization and third-party planning guide | Calibrated feasibility classification so Long Trail THRU requests under roughly 20 days read unrealistic, 20-24 aggressive, 25-28 challenging, and 29+ comfortable before daily exceptions are applied | High for GMC broad completion range; medium for third-party pacing framing | Medium | Used as qualitative/product calibration only. CairnOS does not claim an official pace standard and still reports mileage/elevation/recovery exceptions separately. |
| 2026-05-20 | Recovery-mode and lodging-support planning | Green Mountain Club thru-hike planning; Long Trail Planning Guide trail-town amenities; The Hiker's Hostel | [GMC thru-hike page](https://www.greenmountainclub.org/hiking/thru-hike-long-trail-vermont/), [Trail town amenities](https://www.longtrailvermont.com/trail-town-amenities/), [The Hiker's Hostel](https://www.hikershostel.org/) | Official trail organization, third-party planning guide, and current lodging example | Supported recovery-mode design: cadence remains default, target zero/nero counts are advisory, and lodging-backed access can support recovery scoring when cadence/count pressure is high | Medium; lodging/service availability is volatile | Medium to high | Do not scrape or bulk-copy lodging lists. Use named lodging examples only after independent current-source validation and provenance review. |
| 2026-05-20 | Candidate Long Trail lodging enrichment | User-provided lodging research CSV | Local file only: `long_trail_vermont_lodging_research_20260520.csv` | User-owned research file with external source URLs | Reviewed as candidate support for future lodging enrichment around recovery towns; not committed as source data in this pass | Varies by row; requires source-by-source validation | Medium to high | Treat as a staging/research aid. Promote rows only after checking business/current-source URLs, provenance, and volatile-service caveats. |
| 2026-05-20 | Curated Long Trail lodging support | Maintainer lodging research plus independent business URLs | Local candidate CSV plus committed validation URLs in `town_lodging_options.csv` | User-owned research aid and current business/official web sources | Promoted a conservative subset into advisory lodging support for recovery scoring and town-detail output | Medium; business availability is volatile and must be revalidated | Medium | The source CSV itself is not committed. Transportation, shuttle, and pickup details are intentionally omitted from user-facing output. |
| 2026-05-19 | PCT/other long-trail planning patterns | PCT, AT, and broader trail communities | No specific URLs logged yet | Candidate community/official research | Future generalization beyond the Long Trail | Not evaluated | Unknown | Do not claim findings until specific sources are logged and reviewed. |

## Going Forward

Before implementing behavior based on external research, add a row here with:

- source URL or exact citation
- source owner or community
- date reviewed
- source type
- whether it is qualitative research, candidate data, calibration reference, or
  operational input
- reliability assessment
- copyright/provenance risk
- short notes on how it influenced the change

If a future PR uses web research but does not update this log, treat that as a
documentation gap.
