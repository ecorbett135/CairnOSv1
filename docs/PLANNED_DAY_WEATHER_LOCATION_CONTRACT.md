# Planned-Day Weather Location Contract

`cairnos_planned_day_weather_location_v1` is the additive CairnOS-owned
coordinate contract for foreground weather enrichment. It is exported as
`planned_day_weather_locations` inside `cairnos_plan_v1`; the parent Plan JSON
version remains unchanged under the v1 additive-field rule.

## Authoritative semantic

The weather location for an itinerary day is that day's CairnOS-selected
**planned daily stop**. For a moving day this is the planned shelter, campsite,
road-access stop, terminus, or other explicit operational endpoint. For a
zero/nero row it remains the selected daily stop recorded by CairnOS. This is
not a route midpoint, moving-track endpoint, interpolated trail mile, device
location, or a downstream selection.

When the selected stop is an off-spine camp or shelter, CairnOS exports the
stop's explicit waypoint coordinates. It never substitutes the projected
spine alignment. Approaches and exits use an explicit stop reference only when
one resolves from CairnOS reference/overlay data. If no explicit source exists,
the day is unavailable; consumers must not derive a point from route geometry.

## Fields

The top-level object contains:

- `contract_version`: `cairnos_planned_day_weather_location_v1`.
- `plan_id`: deterministic identity derived from trail, direction, trip type,
  and the ordered selected daily stops. Changing a selected day stop changes
  the plan identity.
- `trail_id`, `direction`, and `location_semantic`.
- `coordinate_reference_system`: `EPSG:4326` (WGS84).
- `days`: one record for every exported itinerary row.

Each day contains `day`, deterministic `day_id`, `location_role`, `authority`,
and the selected `planned_stop` identity. An available record contains:

```json
{
  "availability": "available",
  "coordinates": {
    "latitude": 42.79804580776522,
    "longitude": -73.11836957931519,
    "coordinate_order": "latitude_longitude",
    "crs": "EPSG:4326"
  },
  "provenance": {
    "coordinate_source": "overnight_reference_waypoint",
    "source_reference": "overlay_0008"
  },
  "unavailable_reason": null
}
```

Latitude is always first by named-field contract; GeoJSON/GPX longitude-first
array conventions do not apply. Values must be finite WGS84 degrees with
latitude in `[-90, 90]` and longitude in `[-180, 180]`.

An unresolved or invalid coordinate is explicit:

```json
{
  "availability": "unavailable",
  "coordinates": null,
  "provenance": null,
  "unavailable_reason": "no_authoritative_planned_stop_coordinates"
}
```

The other possible reason is
`invalid_authoritative_planned_stop_coordinates`. Unavailable means no weather
lookup is permitted for that day. There is no approximation or fallback.

## Weather boundary

This contract supplies planned location only. It does not assert that a
forecast exists for the planned date. Forecast-date/provider availability is a
separate downstream state. Forecasts are forecasts and must never be stored,
displayed, synchronized, or analyzed as observations or user-recorded actuals.
All weather remains advisory and must be verified against current official
sources.

## Platform pass-through handoff

HikerLogix Platform must preserve the complete
`planned_day_weather_locations` object unchanged in the current-plan wrapper,
including `contract_version`, `plan_id`, every `day_id`, selected-stop identity,
availability, named latitude/longitude fields, coordinate order/CRS,
provenance, authority, and unavailable reason. Platform must not recalculate,
normalize to a different location, fill unavailable coordinates, or use the
GPX track as a substitute. iOS should join weather state by `plan_id` and
`day_id` and perform a provider request only for `availability: available`.
