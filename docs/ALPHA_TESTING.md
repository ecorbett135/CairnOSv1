# Alpha Testing

CairnOSv1 Alpha is a hosted Streamlit preview for early testers. It is meant to
collect feedback on itinerary realism, UI clarity, resupply assumptions,
SOBO/NOBO parity, Gaia export usefulness, and trail-data issues.

## Tester Guidance

- Treat all output as advisory.
- Verify routes, shelters, services, road access, closures, weather, and safety
  decisions against official sources before using anything in the field.
- Try both NOBO and SOBO THRU plans.
- Export the Gaia GeoJSON and check whether the markers land where expected.
- Note any day that feels unrealistic, confusing, too aggressive, or oddly
  conservative.
- Submit feedback through the configured Alpha feedback form.
- If using GitHub, choose the bug, trail/data, feature, or alpha-feedback issue
  template that best matches the report.

## Known Alpha Limitations

- The Streamlit UI currently supports THRU planning only.
- SECTION planning is intentionally hidden until the traversal semantics are
  ready.
- The Long Trail dataset still has provenance and data-quality gaps under
  review.
- Operational feasibility is improving, but it does not yet model food weight,
  weather, seasonal service changes, injury risk, or individual hiking style.
- The app should not be treated as a substitute for maps, guidebooks, local
  trail organizations, land manager guidance, or personal judgment.

## Streamlit Community Cloud Runtime

The hosted Alpha should run from the Streamlit entrypoint:

```text
cairn/interfaces/streamlit_app.py
```

Place the Alpha feedback form URL in Streamlit secrets:

```toml
alpha_feedback_url = "https://example.com/form"
```

Do not commit private form-management links or credentials to the repository.

## Runtime Data Package

The hosted Streamlit app does not need the topology compiler or full raw source
dataset. Runtime planning currently requires:

- `cairn/`
- `cairn/interfaces/streamlit_app.py`
- `trails/vermont_long_trail/compiled/`
- `trails/vermont_long_trail/raw/csv/approach_trails.csv`
- `trails/vermont_long_trail/raw/csv/route_master.csv`
- `trails/vermont_long_trail/raw/csv/resupply_amenities.csv`

The hosted Alpha should not need:

- `build_topo/`
- `trails/vermont_long_trail/raw/shp/`
- raw DEM files
- raw Gaia/shelter/campsite source GeoJSON
- intermediate compiler outputs
- topology compiler dependencies such as `geopandas`, `fiona`, `pyproj`, or
  `rasterio`

Do not upload private tester data, proprietary route exports, unreviewed
third-party datasets, or Streamlit secrets as part of an alpha report.

The app-specific dependency file lives beside the Streamlit entrypoint:

```text
cairn/interfaces/requirements.txt
```

Streamlit Community Cloud checks the entrypoint directory before the repository
root, so the hosted app can install lean runtime dependencies while the root
`requirements.txt` remains available for local build/topology work.

## Feedback Prompts

- Did the itinerary feel plausible for a real Long Trail hike?
- Were any overnight stops missing, misplaced, or unrealistic?
- Did the resupply strategy match how you would plan food carries?
- Were zero or nero days placed where they made sense?
- Did the SOBO or NOBO plan feel less realistic than the other?
- Did the Gaia export import cleanly and show useful marker locations?
- What was confusing in the UI or output tables?
