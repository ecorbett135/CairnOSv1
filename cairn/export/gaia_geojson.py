import csv
import json
import math
import re
from pathlib import Path


EXPORT_PROPERTIES = [
    "day",
    "division",
    "daily_start_mile",
    "daily_start_location",
    "daily_stop_mile",
    "daily_stop_location",
    "daily_stop_location_type",
    "daily_miles",
    "daily_elevation_gain",
    "notes",
]


SYNTHETIC_LOCATION_NAMES = {
    "backcountry camp",
    "operational stop",
    "trail progression",
}


LIME_GREEN = "#4ABD32"
RESUPPLY_RED = "#FF0000"
HOT_PINK = "#FF1493"

SHELTER_MARKER = {
    "marker_type": "gaia-shelter",
    "marker_decoration": "shelter",
    "marker_color": LIME_GREEN,
    "icon": "shelter",
}

CAMP_MARKER = {
    "marker_type": "gaia-campsite",
    "marker_decoration": "campsite",
    "marker_color": LIME_GREEN,
    "icon": "campsite-24",
}

RESUPPLY_MARKER = {
    "marker_type": "gaia-car",
    "marker_decoration": "car",
    "marker_color": RESUPPLY_RED,
    "icon": "car-24",
}


def normalize_name(value):

    return (
        str(value or "")
        .strip()
        .lower()
    )


def match_tokens(value):

    text = normalize_name(value)

    replacements = [
        ("vermont route", "vt"),
        ("vermont rte", "vt"),
        ("v.t.", "vt"),
        ("vt.", "vt"),
        ("u.s.", "us"),
        ("u. s.", "us"),
        ("united states route", "us"),
    ]

    for old, new in replacements:
        text = text.replace(old, new)

    tokens = set(
        re.findall(
            r"[a-z0-9]+",
            text,
        )
    )

    return {
        token
        for token in tokens
        if token not in {
            "at",
            "the",
            "and",
            "route",
            "road",
            "rd",
        }
    }


def names_likely_match(
    first,
    second,
):

    first_tokens = match_tokens(first)
    second_tokens = match_tokens(second)

    if not first_tokens or not second_tokens:
        return False

    shared = first_tokens & second_tokens
    numeric_shared = any(
        token.isdigit()
        for token in shared
    )

    if numeric_shared and len(shared) >= 2:
        return True

    if len(shared) >= min(
        len(first_tokens),
        len(second_tokens),
    ):
        return True

    return len(shared) >= 2


def parse_float(value):

    if value in (None, ""):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_json(path):

    with open(path) as f:
        return json.load(f)


def load_overlay_nodes(trail_root):

    path = (
        Path(trail_root) /
        "compiled" /
        "route_overlay.json"
    )

    payload = load_json(path)

    return payload.get(
        "overlay_nodes",
        []
    )


def load_spine_coordinates(trail_root):

    path = (
        Path(trail_root) /
        "compiled" /
        "spine.geojson"
    )

    payload = load_json(path)

    for feature in payload.get(
        "features",
        [],
    ):

        geometry = feature.get(
            "geometry",
            {},
        )

        geometry_type = geometry.get(
            "type"
        )

        coordinates = geometry.get(
            "coordinates",
            [],
        )

        if geometry_type == "LineString":
            return coordinates

        if geometry_type == "MultiLineString":
            return [
                coord
                for line in coordinates
                for coord in line
            ]

    return []


def load_waypoint_reference(trail_root):

    path = (
        Path(trail_root) /
        "compiled" /
        "waypoint_reference.json"
    )

    if not path.exists():
        return []

    payload = load_json(path)

    return (
        payload.get(
            "matched_waypoints",
            []
        )
        + payload.get(
            "unmatched_waypoints",
            []
        )
    )


def row_coordinates(row):

    latitude = parse_float(
        row.get("latitude")
        or row.get("lat")
    )

    longitude = parse_float(
        row.get("longitude")
        or row.get("lon")
        or row.get("lng")
    )

    if latitude is None or longitude is None:
        return None

    return [
        longitude,
        latitude,
    ]


def load_resupply_access_reference(trail_root):

    path = (
        Path(trail_root) /
        "raw" /
        "csv" /
        "resupply_amenities.csv"
    )

    if not path.exists():
        return []

    records = []

    with open(
        path,
        newline="",
    ) as f:

        for row in csv.DictReader(f):

            record = dict(row)
            record["trail_mile"] = parse_float(
                row.get("trail_mile")
            )
            record["coordinates"] = row_coordinates(
                row
            )
            records.append(record)

    return records


def load_crossing_reference(trail_root):

    for filename in [
        "crossings_refined.geojson",
        "crossings.geojson",
    ]:

        path = (
            Path(trail_root) /
            "compiled" /
            filename
        )

        if path.exists():
            break

    else:
        return []

    payload = load_json(path)
    records = []

    for feature in payload.get(
        "features",
        [],
    ):

        geometry = feature.get(
            "geometry",
            {},
        )

        coordinates = geometry.get(
            "coordinates",
            [],
        )

        if (
            geometry.get("type") != "Point"
            or not valid_coordinates(coordinates)
        ):
            continue

        record = dict(
            feature.get(
                "properties",
                {},
            )
        )
        record["coordinates"] = coordinates[:2]
        records.append(record)

    return records


def build_spine_feature(
    trail_root,
    coordinates,
    total_miles,
):

    if not coordinates:
        return None

    trail_name = Path(trail_root).name

    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": coordinates,
        },
        "properties": {
            "name": (
                f"{trail_name} spine"
            ),
            "cairnos_feature_type": "spine",
            "trail": trail_name,
            "total_miles": total_miles,
            "source": (
                "compiled/spine.geojson"
            ),
            "stroke": HOT_PINK,
            "stroke-width": 4,
            "stroke-opacity": 1.0,
            "marker_color": HOT_PINK,
        },
        "stroke": HOT_PINK,
        "stroke-width": 4,
        "stroke-opacity": 1.0,
    }


def node_point_coordinates(node):

    geometry = node.get(
        "geometry"
    )

    if (
        isinstance(geometry, dict)
        and geometry.get("type") == "Point"
    ):

        coordinates = geometry.get(
            "coordinates"
        )

        if valid_coordinates(coordinates):
            return coordinates[:2]

    coordinates = node.get(
        "coordinates"
    )

    if valid_coordinates(coordinates):
        return coordinates[:2]

    longitude = (
        node.get("longitude")
        or node.get("lon")
        or node.get("lng")
    )

    latitude = (
        node.get("latitude")
        or node.get("lat")
    )

    if longitude is None or latitude is None:
        return None

    return [
        float(longitude),
        float(latitude),
    ]


def valid_coordinates(coordinates):

    return (
        isinstance(coordinates, list)
        and len(coordinates) >= 2
        and coordinates[0] is not None
        and coordinates[1] is not None
    )


def build_overlay_lookup(overlay_nodes):

    by_name = {}

    for node in overlay_nodes:

        name = normalize_name(
            node.get("canonical_name")
        )

        if name:
            by_name.setdefault(
                name,
                [],
            ).append(node)

    return by_name


def build_waypoint_lookup(waypoints):

    by_name = {}

    for waypoint in waypoints:

        if waypoint.get("deleted"):
            continue

        names = [
            waypoint.get("title"),
            waypoint.get("canonical_name"),
        ]

        for name in names:

            normalized = normalize_name(
                name
            )

            if normalized:
                by_name.setdefault(
                    normalized,
                    [],
                ).append(waypoint)

    return by_name


def total_overlay_miles(overlay_nodes):

    miles = [
        node.get("trail_mile")
        for node in overlay_nodes
        if (
            isinstance(
                node.get("trail_mile"),
                (int, float),
            )
            and node.get("trail_mile") >= 0
        )
    ]

    if not miles:
        return None

    return max(miles)


def find_overlay_node(
    day,
    overlay_lookup,
    overlay_nodes,
):

    stop_name = normalize_name(
        day.get("daily_stop_location")
    )

    stop_mile = day.get(
        "daily_stop_mile"
    )

    candidates = overlay_lookup.get(
        stop_name,
        [],
    )

    if candidates:

        if isinstance(
            stop_mile,
            (int, float),
        ):

            return sorted(
                candidates,
                key=lambda node: abs(
                    (
                        node.get(
                            "trail_mile",
                            stop_mile,
                        )
                        or stop_mile
                    )
                    - stop_mile
                ),
            )[0]

        return candidates[0]

    if not isinstance(
        stop_mile,
        (int, float),
    ):
        return None

    nearby = [
        node for node in overlay_nodes
        if (
            isinstance(
                node.get("trail_mile"),
                (int, float),
            )
            and abs(
                node["trail_mile"] - stop_mile
            ) <= 0.15
        )
    ]

    if not nearby:
        return None

    return sorted(
        nearby,
        key=lambda node: abs(
            node["trail_mile"] - stop_mile
        ),
    )[0]


def find_waypoint_reference(
    day,
    waypoint_lookup,
):

    stop_name = normalize_name(
        day.get("daily_stop_location")
    )

    stop_mile = day.get(
        "daily_stop_mile"
    )

    candidates = waypoint_lookup.get(
        stop_name,
        [],
    )

    if not candidates:
        return None

    if isinstance(
        stop_mile,
        (int, float),
    ):

        return sorted(
            candidates,
            key=lambda waypoint: abs(
                (
                    waypoint.get(
                        "trail_mile",
                        stop_mile,
                    )
                    or stop_mile
                )
                - stop_mile
            ),
        )[0]

    return candidates[0]


def is_camp_stop(day):

    stop_type = normalize_name(
        day.get(
            "daily_stop_location_type"
        )
    )

    stop_location = normalize_name(
        day.get(
            "daily_stop_location"
        )
    )

    return (
        stop_type in {
            "camp",
            "campsite",
        }
        or "camp" in stop_location
        or "tenting" in stop_location
    )


def is_shelter_stop(day):

    stop_type = normalize_name(
        day.get(
            "daily_stop_location_type"
        )
    )

    stop_location = normalize_name(
        day.get(
            "daily_stop_location"
        )
    )

    return (
        stop_type == "shelter"
        or "shelter" in stop_location
    )


def is_access_stop(day):

    stop_type = normalize_name(
        day.get(
            "daily_stop_location_type"
        )
    )

    stop_location = normalize_name(
        day.get(
            "daily_stop_location"
        )
    )

    if is_shelter_stop(day) or is_camp_stop(day):
        return False

    return (
        stop_type in {
            "access",
            "crossing",
            "logistics",
            "road_crossing",
            "trailhead",
        }
        or "road" in stop_location
        or "route" in stop_location
        or "vt." in stop_location
        or "u.s." in stop_location
    )


def find_access_reference(
    location,
    mile,
    access_references,
):

    candidates = [
        record
        for record in access_references
        if valid_coordinates(
            record.get("coordinates")
        )
    ]

    if not candidates:
        return None

    ranked = []

    for idx, record in enumerate(candidates):

        record_mile = record.get(
            "trail_mile"
        )

        mile_delta = None

        if (
            isinstance(mile, (int, float))
            and isinstance(record_mile, (int, float))
        ):
            mile_delta = abs(
                mile - record_mile
            )

        name_match = any(
            names_likely_match(
                location,
                value,
            )
            for value in [
                record.get("canonical_hint"),
                record.get("town_access"),
            ]
        )

        if not name_match and (
            mile_delta is None
            or mile_delta > 0.6
        ):
            continue

        score = 0

        if name_match:
            score += 10

        if mile_delta is not None:
            score += max(
                0,
                6 - mile_delta,
            )

        ranked.append(
            (
                -score,
                mile_delta
                if mile_delta is not None
                else 999,
                idx,
                record,
            )
        )

    if not ranked:
        return None

    return sorted(ranked)[0][3]


def find_resupply_access_reference(
    day,
    access_references,
):

    if not is_access_stop(day):
        return None

    return find_access_reference(
        day.get("daily_stop_location"),
        day.get("daily_stop_mile"),
        access_references,
    )


def find_crossing_reference(
    day,
    crossing_references,
):

    if not is_access_stop(day):
        return None

    stop_name = day.get(
        "daily_stop_location"
    )

    stop_mile = day.get(
        "daily_stop_mile"
    )

    ranked = []

    for idx, crossing in enumerate(
        crossing_references
    ):

        crossing_mile = crossing.get(
            "trail_mile"
        )

        if not (
            isinstance(stop_mile, (int, float))
            and isinstance(crossing_mile, (int, float))
        ):
            continue

        mile_delta = abs(
            stop_mile - crossing_mile
        )

        name_match = names_likely_match(
            stop_name,
            crossing.get("name"),
        )

        if name_match:
            if mile_delta > 1.0:
                continue
        elif mile_delta > 0.15:
            continue

        score = 10 if name_match else 0

        ranked.append(
            (
                -score,
                mile_delta,
                idx,
                crossing,
            )
        )

    if not ranked:
        return None

    return sorted(ranked)[0][3]


def interpolate_spine_coordinate(
    coordinates,
    mile,
    total_miles,
):

    if (
        not coordinates
        or len(coordinates) < 2
        or total_miles is None
        or total_miles <= 0
        or not isinstance(mile, (int, float))
        or mile < 0
        or mile > total_miles
    ):

        return None

    segment_lengths = []
    total_length = 0.0

    for start, end in zip(
        coordinates,
        coordinates[1:],
    ):

        length = math.hypot(
            end[0] - start[0],
            end[1] - start[1],
        )

        segment_lengths.append(length)
        total_length += length

    if total_length <= 0:
        return None

    target_length = (
        mile / total_miles
    ) * total_length

    traversed = 0.0

    for idx, length in enumerate(
        segment_lengths
    ):

        start = coordinates[idx]
        end = coordinates[idx + 1]

        if (
            traversed + length
            >= target_length
        ):

            if length == 0:
                return start[:2]

            ratio = (
                target_length - traversed
            ) / length

            return [
                start[0]
                + (
                    end[0] - start[0]
                )
                * ratio,
                start[1]
                + (
                    end[1] - start[1]
                )
                * ratio,
            ]

        traversed += length

    return coordinates[-1][:2]


def resolve_day_coordinates(
    day,
    access_references,
    waypoint_lookup,
    crossing_references,
    overlay_lookup,
    overlay_nodes,
    spine_coordinates,
    total_miles,
):

    access_reference = find_resupply_access_reference(
        day,
        access_references,
    )

    if access_reference:

        coordinates = access_reference.get(
            "coordinates"
        )

        if valid_coordinates(coordinates):
            return (
                coordinates[:2],
                "resupply_access_reference",
                None,
            )

    waypoint = find_waypoint_reference(
        day,
        waypoint_lookup,
    )

    if waypoint:

        coordinates = waypoint.get(
            "coordinates"
        )

        if valid_coordinates(coordinates):
            return (
                coordinates[:2],
                "gaia_reference",
                waypoint,
            )

    crossing_reference = find_crossing_reference(
        day,
        crossing_references,
    )

    if crossing_reference:

        coordinates = crossing_reference.get(
            "coordinates"
        )

        if valid_coordinates(coordinates):
            return (
                coordinates[:2],
                "crossing_reference",
                None,
            )

    overlay_node = find_overlay_node(
        day,
        overlay_lookup,
        overlay_nodes,
    )

    if overlay_node:

        coordinates = node_point_coordinates(
            overlay_node
        )

        if coordinates:
            return (
                coordinates,
                "route_overlay",
                None,
            )

    coordinates = interpolate_spine_coordinate(
        spine_coordinates,
        day.get("daily_stop_mile"),
        total_miles,
    )

    if coordinates:
        return (
            coordinates,
            "spine_interpolation",
            None,
        )

    return (
        None,
        None,
        None,
    )


def feature_properties(day):

    return {
        key: day.get(key)
        for key in EXPORT_PROPERTIES
    }


def marker_metadata_from_waypoint(
    waypoint,
):

    if not waypoint:
        return {}

    metadata = {}

    for key in [
        "marker_type",
        "marker_decoration",
        "marker_color",
        "icon",
    ]:

        value = waypoint.get(key)

        if value:
            metadata[key] = value

    return metadata


def marker_metadata_for_day(
    day,
    waypoint=None,
):

    if is_camp_stop(day):
        return dict(CAMP_MARKER)

    if is_shelter_stop(day):
        return dict(SHELTER_MARKER)

    if is_access_stop(day):
        return dict(RESUPPLY_MARKER)

    waypoint_metadata = marker_metadata_from_waypoint(
        waypoint
    )

    if waypoint_metadata:
        return waypoint_metadata

    return {}


def build_gaia_feature(
    day,
    coordinates,
    waypoint=None,
):

    day_number = day.get(
        "day"
    )

    stop_location = day.get(
        "daily_stop_location",
        "Unknown Stop",
    )

    properties = feature_properties(day)

    properties["name"] = (
        f"Day {day_number} — "
        f"{stop_location}"
    )

    marker_metadata = marker_metadata_for_day(
        day,
        waypoint,
    )

    properties.update(marker_metadata)

    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": coordinates,
        },
        "properties": properties,
    }

    # Gaia stores marker fields as properties in exports, but keeping them on
    # the Feature as foreign members makes the downloaded GeoJSON easy to
    # inspect and harmless for standard GeoJSON consumers.
    feature.update(marker_metadata)

    return feature


def resupply_rows_from_plan(
    daily_plan,
    resupply_plan=None,
):

    rows = []

    for row in resupply_plan or []:

        rows.append({
            "day": row.get("day"),
            "division": row.get("division"),
            "resupply_location": row.get("location"),
            "resupply_mile": row.get("mile"),
            "resupply_location_type": row.get("access_type"),
            "town_access": row.get("town_access"),
            "notes": row.get("notes"),
        })

    for day in daily_plan:

        if not day.get("resupply_location"):
            continue

        rows.append({
            "day": day.get("day"),
            "division": day.get("division"),
            "daily_stop_location": day.get(
                "daily_stop_location"
            ),
            "resupply_location": day.get(
                "resupply_location"
            ),
            "resupply_mile": day.get(
                "resupply_mile"
            ),
            "resupply_location_type": day.get(
                "resupply_location_type"
            ),
            "town_access": day.get(
                "town_access"
            ),
            "notes": day.get("notes"),
        })

    unique_rows = []
    seen = set()

    for row in rows:

        location = normalize_name(
            row.get("resupply_location")
        )
        mile = row.get("resupply_mile")
        mile_key = (
            round(mile, 1)
            if isinstance(mile, (int, float))
            else None
        )
        key = (
            row.get("day"),
            location,
            mile_key,
        )

        if not location or key in seen:
            continue

        seen.add(key)
        unique_rows.append(row)

    return unique_rows


def build_resupply_feature(
    row,
    access_reference,
):

    coordinates = access_reference.get(
        "coordinates"
    )

    if not valid_coordinates(coordinates):
        return None

    day_number = row.get("day")
    location = row.get(
        "resupply_location"
    )
    town_access = (
        row.get("town_access")
        or access_reference.get("town_access")
    )

    properties = {
        "name": (
            f"Day {day_number} Resupply — "
            f"{location}"
        ),
        "cairnos_feature_type": (
            "resupply"
        ),
        "day": day_number,
        "division": row.get("division"),
        "daily_stop_location": row.get(
            "daily_stop_location"
        ),
        "resupply_location": location,
        "resupply_mile": row.get(
            "resupply_mile"
        ),
        "resupply_location_type": row.get(
            "resupply_location_type"
        ),
        "town_access": town_access,
        "notes": row.get("notes"),
        "canonical_hint": access_reference.get(
            "canonical_hint"
        ),
        "access_notes": access_reference.get(
            "access_notes"
        ),
        "source_name": access_reference.get(
            "source_name"
        ),
        "source_url": access_reference.get(
            "source_url"
        ),
    }

    for service in [
        "grocery",
        "post_office",
        "outfitter",
        "lodging",
        "restaurants",
        "zero_candidate",
    ]:
        properties[service] = access_reference.get(
            service
        )

    marker_metadata = dict(RESUPPLY_MARKER)
    properties.update(marker_metadata)

    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": coordinates[:2],
        },
        "properties": properties,
    }
    feature.update(marker_metadata)

    return feature


def build_resupply_warning(
    row,
    reason,
):

    return {
        "day": row.get("day"),
        "resupply_location": row.get(
            "resupply_location"
        ),
        "resupply_mile": row.get(
            "resupply_mile"
        ),
        "reason": reason,
    }


def build_warning(day, reason):

    return {
        "day": day.get("day"),
        "daily_stop_location": day.get(
            "daily_stop_location"
        ),
        "daily_stop_mile": day.get(
            "daily_stop_mile"
        ),
        "reason": reason,
    }


def export_itinerary_to_gaia_geojson(
    daily_plan,
    trail_root,
    resupply_plan=None,
):

    overlay_nodes = load_overlay_nodes(
        trail_root
    )

    waypoints = load_waypoint_reference(
        trail_root
    )

    access_references = load_resupply_access_reference(
        trail_root
    )

    crossing_references = load_crossing_reference(
        trail_root
    )

    overlay_lookup = build_overlay_lookup(
        overlay_nodes
    )

    waypoint_lookup = build_waypoint_lookup(
        waypoints
    )

    spine_coordinates = load_spine_coordinates(
        trail_root
    )

    total_miles = total_overlay_miles(
        overlay_nodes
    )

    features = []
    warnings = []

    spine_feature = build_spine_feature(
        trail_root,
        spine_coordinates,
        total_miles,
    )

    if spine_feature:
        features.append(spine_feature)

    daily_access_keys = {
        (
            day.get("day"),
            normalize_name(
                day.get("daily_stop_location")
            ),
        )
        for day in daily_plan
        if is_access_stop(day)
    }

    for day in daily_plan:

        coordinates, _, waypoint = resolve_day_coordinates(
            day,
            access_references,
            waypoint_lookup,
            crossing_references,
            overlay_lookup,
            overlay_nodes,
            spine_coordinates,
            total_miles,
        )

        if not coordinates:

            stop_name = normalize_name(
                day.get(
                    "daily_stop_location"
                )
            )

            reason = (
                "Coordinates could not be resolved "
                "from route overlay or spine"
            )

            if stop_name in SYNTHETIC_LOCATION_NAMES:
                reason = (
                    "Synthetic location has no "
                    "resolvable coordinates"
                )

            warnings.append(
                build_warning(day, reason)
            )

            continue

        features.append(
            build_gaia_feature(
                day,
                coordinates,
                waypoint,
            )
        )

    for row in resupply_rows_from_plan(
        daily_plan,
        resupply_plan,
    ):

        key = (
            row.get("day"),
            normalize_name(
                row.get("resupply_location")
            ),
        )

        if key in daily_access_keys:
            continue

        access_reference = find_access_reference(
            row.get("resupply_location"),
            row.get("resupply_mile"),
            access_references,
        )

        if not access_reference:
            warnings.append(
                build_resupply_warning(
                    row,
                    (
                        "Resupply coordinates could not "
                        "be resolved from "
                        "resupply_amenities.csv"
                    ),
                )
            )
            continue

        resupply_feature = build_resupply_feature(
            row,
            access_reference,
        )

        if resupply_feature:
            features.append(resupply_feature)
        else:
            warnings.append(
                build_resupply_warning(
                    row,
                    (
                        "Resupply coordinates could not "
                        "be resolved from "
                        "resupply_amenities.csv"
                    ),
                )
            )

    return {
        "geojson": {
            "type": "FeatureCollection",
            "properties": {
                "name": (
                    f"{Path(trail_root).name} "
                    "PlannerV2 Gaia Export"
                ),
                "cairnos_feature_type": (
                    "planner_v2_export"
                ),
            },
            "features": features,
        },
        "warnings": warnings,
    }


def dumps_geojson(payload):

    return json.dumps(
        payload,
        indent=2,
    )
