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
| 2026-05-19 | NOBO resupply spacing comparison | Long Trail Planning Guide northbound resupply maps | [Northbound resupply maps](https://www.longtrailvermont.com/northbound-resupply-maps/) | Third-party planning guide | Qualitative comparison for expected resupply spacing and cadence behavior | Medium | Medium to high | Use as comparison signal only. Do not copy maps, route plans, or tables into CairnOS. |
| 2026-05-19 | SOBO resupply spacing comparison | Long Trail Planning Guide southbound resupply maps | [Southbound resupply maps](https://www.longtrailvermont.com/southbound-resupply-maps/) | Third-party planning guide | Qualitative comparison for SOBO resupply spacing and parity | Medium | Medium to high | Use as comparison signal only. Do not copy maps, route plans, or tables into CairnOS. |
| 2026-05-19 | Long Trail planning sentiment | Reddit `r/longtrail` planning search | [r/longtrail planning search](https://www.reddit.com/r/longtrail/search/?q=planning&type=posts&t=year) | Community discussion | Product research around common planning questions, resupply concerns, and tester outreach | Variable | Medium | No individual posts/comments have been formally logged. Future use should record specific post URLs and summarize, not copy. |
| 2026-05-19 | Appalachian Trail discussions mentioning Long Trail | Reddit `r/AppalachianTrail` | Not preserved as a specific URL | Community discussion | Candidate qualitative research source for Long Trail overlap, northern Vermont difficulty, and resupply norms | Variable | Medium | Mentioned as useful, but no specific thread was logged. Future research must capture exact URLs. |
| 2026-05-19 | Competitive/product boundary | HiiKER hike planner | [HiiKER hike planner](https://hiiker.app/hike-planner) | Navigation/planning product | Helped clarify CairnOS boundary: operational reasoning/export layer, not a general route planner or app replacement | Medium | Low if used only for product positioning | Do not copy UI, data, route content, or proprietary behavior. |
| 2026-05-19 | Gaia export interoperability | Gaia GPS app and route summaries | User-owned Gaia links and local exports; exact public URLs vary | Navigation/mapping tool and user-owned export | Marker compatibility, elevation comparison, and route-alignment calibration | Useful comparison; not authoritative for Cairn trail truth | Medium to high | Gaia/Garmin exports belong in ignored `elevation_calibration/` unless explicitly reviewed. |
| 2026-05-19 | Garmin elevation comparison | Garmin Explore map | [Garmin Explore](https://explore.garmin.com/Map) | Navigation/mapping tool | Candidate cross-check for elevation calibration against Gaia and Cairn terrain | Useful comparison; not authoritative for Cairn trail truth | Medium | Avoid scraping or committing proprietary Garmin-derived data. |
| 2026-05-19 | Alpha feedback collection | Google Forms alpha feedback form | Private project feedback form URL in Streamlit config/docs | Direct tester feedback | Collect tester reports without requiring GitHub literacy | High for user feedback; subjective | Low to medium | Feedback is product research unless a tester-provided file becomes a dataset or fixture. |
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
