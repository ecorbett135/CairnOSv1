# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from difflib import SequenceMatcher
from pathlib import Path
import json
import math
import sys


SCHEMA_VERSION = "1.0"

MATCH_THRESHOLD = 0.74

PLANNER_SPINE_DISTANCE_LIMIT_MILES = 1.0


def resolve_trail_root(trail_root=None):

    if trail_root is not None:
        return Path(trail_root).resolve()

    return Path(
        "trails/vermont_long_trail"
    ).resolve()


def raw_geojson_dir(trail_root):

    return (
        Path(trail_root) /
        "raw" /
        "geojson"
    )


def source_paths(trail_root):

    directory = raw_geojson_dir(
        trail_root
    )

    return [
        directory / "shelters.geojson",
        directory / "campsites.geojson",
    ]


def route_overlay_path(trail_root):

    return (
        Path(trail_root) /
        "compiled" /
        "route_overlay.json"
    )


def spine_path(trail_root):

    return (
        Path(trail_root) /
        "compiled" /
        "spine.geojson"
    )


def output_path(trail_root):

    return (
        Path(trail_root) /
        "compiled" /
        "overnight_reference.json"
    )


def load_json(path):

    with open(path) as f:
        return json.load(f)


def normalize_text(value):

    return str(
        value or ""
    ).strip()


def normalize_match_text(value):

    text = (
        normalize_text(value)
        .lower()
        .replace(
            "’",
            "'",
        )
    )

    replacements = {
        "-": " ",
        ";": " ",
        ",": " ",
        "(": " ",
        ")": " ",
        ".": " ",
        "/": " ",
        "&": " ",
    }

    for old, new in replacements.items():
        text = text.replace(
            old,
            new,
        )

    return " ".join(
        text.split()
    )


def match_tokens(value):

    stop_words = {
        "a",
        "an",
        "and",
        "area",
        "at",
        "camping",
        "ft",
        "mi",
        "mile",
        "miles",
        "the",
        "to",
        "trail",
        "via",
    }

    return {
        token for token in
        normalize_match_text(value).split()
        if token not in stop_words
    }


def is_generic_overnight_title(title):

    text = normalize_match_text(
        title
    )

    return text in {
        "camp site",
        "campsite",
        "camp",
        "site",
    }


def title_similarity(
    reference_title,
    overlay_name,
):

    reference_text = normalize_match_text(
        reference_title
    )

    overlay_text = normalize_match_text(
        overlay_name
    )

    if not reference_text or not overlay_text:
        return 0.0

    if reference_text == overlay_text:
        return 1.0

    if (
        reference_text in overlay_text
        or overlay_text in reference_text
    ):
        return 0.96

    reference_tokens = match_tokens(
        reference_text
    )

    overlay_tokens = match_tokens(
        overlay_text
    )

    if reference_tokens and overlay_tokens:

        shared = (
            reference_tokens &
            overlay_tokens
        )

        if reference_tokens <= overlay_tokens:
            return 0.94

        overlap = (
            len(shared) /
            max(
                len(reference_tokens),
                1,
            )
        )

        if overlap >= 0.75:
            return 0.88

    return SequenceMatcher(
        None,
        reference_text,
        overlay_text,
    ).ratio()


def classify_reference(
    title,
    icon,
    source_file,
):

    haystack = " ".join([
        normalize_match_text(title),
        normalize_match_text(icon),
        normalize_match_text(source_file),
    ])

    if (
        "campsite" in haystack
        or "tenting" in haystack
        or "camp site" in haystack
        or source_file == "campsites.geojson"
    ):
        return "campsite"

    if (
        "lodge" in haystack
        or "hut" in haystack
        or "shelter" in haystack
        or source_file == "shelters.geojson"
    ):
        return "shelter"

    return "overnight"


def node_class_for_reference(
    overnight_class,
):

    if overnight_class == "campsite":
        return "camp"

    return "shelter"


def load_overlay_nodes(trail_root=None):

    trail_root = resolve_trail_root(
        trail_root
    )

    payload = load_json(
        route_overlay_path(
            trail_root
        )
    )

    return payload.get(
        "overlay_nodes",
        []
    )


def point_coordinates(feature):

    geometry = feature.get(
        "geometry",
        {},
    )

    if geometry.get("type") != "Point":
        return None

    coordinates = geometry.get(
        "coordinates",
        [],
    )

    if len(coordinates) < 2:
        return None

    return coordinates[:2]


def load_overnight_points(trail_root=None):

    trail_root = resolve_trail_root(
        trail_root
    )

    points = []

    for path in source_paths(
        trail_root
    ):

        if not path.exists():
            continue

        payload = load_json(
            path
        )

        for feature in payload.get(
            "features",
            [],
        ):

            coordinates = point_coordinates(
                feature
            )

            if not coordinates:
                continue

            props = feature.get(
                "properties",
                {},
            )

            title = normalize_text(
                props.get("title")
                or props.get("name")
            )

            icon = props.get(
                "icon"
            )

            overnight_class = classify_reference(
                title,
                icon,
                path.name,
            )

            points.append({
                "source_file": path.name,
                "source_id": props.get("id"),
                "title": title,
                "coordinates": coordinates,
                "longitude": coordinates[0],
                "latitude": coordinates[1],
                "icon": icon,
                "marker_type": props.get(
                    "marker_type"
                ),
                "marker_color": props.get(
                    "marker_color"
                ),
                "marker_decoration": props.get(
                    "marker_decoration"
                ),
                "deleted": bool(
                    props.get("deleted")
                ),
                "overnight_class": overnight_class,
                "node_class": node_class_for_reference(
                    overnight_class
                ),
                "generic_title": (
                    is_generic_overnight_title(
                        title
                    )
                ),
            })

    return points


def overlay_is_overnight(node):

    return bool(
        node.get("overnight")
        or node.get("shelter")
        or node.get("camping")
        or node.get("node_class") in {
            "shelter",
            "camp",
        }
    )


def best_overlay_match(
    reference,
    overlay_nodes,
):

    best = None

    overnight_nodes = [
        node for node in overlay_nodes
        if overlay_is_overnight(node)
    ]

    search_nodes = (
        overnight_nodes
        or overlay_nodes
    )

    for node in search_nodes:

        score = title_similarity(
            reference.get("title"),
            node.get("canonical_name"),
        )

        if not best or score > best["score"]:
            best = {
                "score": score,
                "node": node,
            }

    if (
        best
        and best["score"] >= MATCH_THRESHOLD
    ):

        node = best["node"]

        return {
            "matched": True,
            "match_score": round(
                best["score"],
                3,
            ),
            "overlay_id": node.get(
                "overlay_id"
            ),
            "canonical_name": node.get(
                "canonical_name"
            ),
            "trail_mile": node.get(
                "trail_mile"
            ),
            "node_class": node.get(
                "node_class"
            ),
            "division": node.get(
                "division"
            ),
            "overlay_overnight": (
                overlay_is_overnight(
                    node
                )
            ),
        }

    return {
        "matched": False,
        "match_score": round(
            best["score"],
            3,
        )
        if best
        else 0.0,
        "nearest_candidate": (
            best["node"].get(
                "canonical_name"
            )
            if best
            else None
        ),
    }


def flatten_spine_coordinates(payload):

    coordinates = []

    for feature in payload.get(
        "features",
        [],
    ):

        geometry = feature.get(
            "geometry",
            {},
        )

        if geometry.get("type") == "LineString":
            coordinates.extend(
                geometry.get(
                    "coordinates",
                    [],
                )
            )

        elif geometry.get("type") == "MultiLineString":

            for line in geometry.get(
                "coordinates",
                [],
            ):
                coordinates.extend(line)

    return [
        point[:2]
        for point in coordinates
        if len(point) >= 2
    ]


def miles_per_degree(
    latitude,
):

    lat_miles = 69.0
    lon_miles = (
        69.172 *
        math.cos(
            math.radians(
                latitude
            )
        )
    )

    return lon_miles, lat_miles


def distance_miles(
    first,
    second,
):

    avg_lat = (
        first[1] +
        second[1]
    ) / 2

    lon_miles, lat_miles = (
        miles_per_degree(
            avg_lat
        )
    )

    dx = (
        second[0] -
        first[0]
    ) * lon_miles

    dy = (
        second[1] -
        first[1]
    ) * lat_miles

    return math.hypot(
        dx,
        dy,
    )


def project_point_to_segment(
    point,
    start,
    end,
):

    avg_lat = (
        point[1] +
        start[1] +
        end[1]
    ) / 3

    lon_miles, lat_miles = (
        miles_per_degree(
            avg_lat
        )
    )

    px = point[0] * lon_miles
    py = point[1] * lat_miles
    sx = start[0] * lon_miles
    sy = start[1] * lat_miles
    ex = end[0] * lon_miles
    ey = end[1] * lat_miles

    vx = ex - sx
    vy = ey - sy
    wx = px - sx
    wy = py - sy

    segment_length_sq = (
        vx * vx +
        vy * vy
    )

    if segment_length_sq == 0:
        fraction = 0.0
    else:
        fraction = max(
            0.0,
            min(
                1.0,
                (
                    wx * vx +
                    wy * vy
                ) /
                segment_length_sq,
            ),
        )

    projected = [
        start[0] + (
            end[0] - start[0]
        ) * fraction,
        start[1] + (
            end[1] - start[1]
        ) * fraction,
    ]

    return (
        projected,
        fraction,
        distance_miles(
            point,
            projected,
        ),
    )


def build_spine_index(
    trail_root=None,
):

    trail_root = resolve_trail_root(
        trail_root
    )

    path = spine_path(
        trail_root
    )

    if not path.exists():
        return None

    coordinates = flatten_spine_coordinates(
        load_json(
            path
        )
    )

    if len(coordinates) < 2:
        return None

    cumulative = [
        0.0
    ]

    for idx in range(
        len(coordinates) - 1
    ):

        cumulative.append(
            cumulative[-1] +
            distance_miles(
                coordinates[idx],
                coordinates[idx + 1],
            )
        )

    return {
        "coordinates": coordinates,
        "cumulative": cumulative,
        "total_miles": cumulative[-1],
    }


def trail_mile_bounds(overlay_nodes):

    miles = [
        node.get("trail_mile")
        for node in overlay_nodes
        if (
            node.get("trail_mile")
            is not None
            and node.get("trail_mile") >= 0
        )
    ]

    if not miles:
        return 0.0, 0.0

    return min(miles), max(miles)


def estimate_spine_position(
    point,
    spine_index,
    overlay_nodes,
):

    if not spine_index:
        return {}

    coordinates = spine_index[
        "coordinates"
    ]

    cumulative = spine_index[
        "cumulative"
    ]

    best = None

    for idx in range(
        len(coordinates) - 1
    ):

        projected, fraction, distance = (
            project_point_to_segment(
                point,
                coordinates[idx],
                coordinates[idx + 1],
            )
        )

        segment_miles = (
            cumulative[idx + 1] -
            cumulative[idx]
        )

        projected_miles = (
            cumulative[idx] +
            segment_miles * fraction
        )

        if (
            best is None
            or distance < best[
                "distance_to_spine_miles"
            ]
        ):
            best = {
                "projected_coordinates": projected,
                "spine_miles": projected_miles,
                "distance_to_spine_miles": distance,
            }

    if not best:
        return {}

    min_mile, max_mile = trail_mile_bounds(
        overlay_nodes
    )

    if spine_index["total_miles"] > 0:
        trail_mile = (
            min_mile +
            (
                best["spine_miles"] /
                spine_index["total_miles"]
            ) *
            (
                max_mile -
                min_mile
            )
        )
    else:
        trail_mile = None

    return {
        "estimated_trail_mile": (
            round(
                trail_mile,
                1,
            )
            if trail_mile is not None
            else None
        ),
        "distance_to_spine_miles": round(
            best["distance_to_spine_miles"],
            3,
        ),
        "projected_coordinates": [
            round(
                best["projected_coordinates"][0],
                7,
            ),
            round(
                best["projected_coordinates"][1],
                7,
            ),
        ],
    }


def nearest_overlay_context(
    mile,
    overlay_nodes,
):

    if mile is None:
        return {}

    nearest = min(
        overlay_nodes,
        key=lambda node: abs(
            (
                node.get("trail_mile")
                or 0
            ) - mile
        ),
    )

    return {
        "nearest_overlay_id": nearest.get(
            "overlay_id"
        ),
        "nearest_overlay_name": nearest.get(
            "canonical_name"
        ),
        "nearest_overlay_mile": nearest.get(
            "trail_mile"
        ),
        "division": nearest.get(
            "division"
        ),
    }


def build_reference_records(
    references,
    overlay_nodes,
    spine_index,
):

    matched = []
    unmatched = []
    planner_candidates = []

    for reference in references:

        match = best_overlay_match(
            reference,
            overlay_nodes,
        )

        estimate = estimate_spine_position(
            reference["coordinates"],
            spine_index,
            overlay_nodes,
        )

        trail_mile = (
            match.get("trail_mile")
            if match.get("matched")
            else estimate.get(
                "estimated_trail_mile"
            )
        )

        context = nearest_overlay_context(
            trail_mile,
            overlay_nodes,
        )

        record = {
            **reference,
            **match,
            **estimate,
            **context,
            "schema_version": SCHEMA_VERSION,
        }

        planner_candidate = (
            not record.get("deleted")
            and not record.get("generic_title")
            and trail_mile is not None
            and (
                not record.get("matched")
                or not record.get(
                    "overlay_overnight"
                )
            )
            and (
                record.get(
                    "distance_to_spine_miles",
                    999,
                )
                <= PLANNER_SPINE_DISTANCE_LIMIT_MILES
            )
        )

        record["planner_candidate"] = (
            planner_candidate
        )

        if planner_candidate:

            planner_record = {
                "canonical_name": record["title"],
                "trail_mile": trail_mile,
                "node_class": record["node_class"],
                "division": record.get(
                    "division"
                ),
                "overnight": True,
                "shelter": (
                    record["node_class"]
                    == "shelter"
                ),
                "camping": (
                    record["node_class"]
                    == "camp"
                ),
                "coordinates": record.get(
                    "coordinates"
                ),
                "distance_to_spine_miles": (
                    record.get(
                        "distance_to_spine_miles"
                    )
                ),
                "source_file": record.get(
                    "source_file"
                ),
                "source_id": record.get(
                    "source_id"
                ),
                "reference_title": record.get(
                    "title"
                ),
                "reference_class": record.get(
                    "overnight_class"
                ),
            }

            planner_candidates.append(
                planner_record
            )

        if match["matched"]:
            matched.append(record)
        else:
            unmatched.append(record)

    return matched, unmatched, planner_candidates


def count_records(
    records,
    overnight_class,
):

    return len([
        record for record in records
        if record.get(
            "overnight_class"
        ) == overnight_class
    ])


def build_summary(
    references,
    matched,
    unmatched,
    planner_candidates,
):

    active = [
        record for record in references
        if not record.get("deleted")
    ]

    return {
        "total_points": len(references),
        "active_points": len(active),
        "deleted_points": (
            len(references) - len(active)
        ),
        "matched_points": len(matched),
        "unmatched_points": len(unmatched),
        "matched_shelters": count_records(
            matched,
            "shelter",
        ),
        "unmatched_shelters": count_records(
            unmatched,
            "shelter",
        ),
        "matched_campsites": count_records(
            matched,
            "campsite",
        ),
        "unmatched_campsites": count_records(
            unmatched,
            "campsite",
        ),
        "planner_candidates": len(
            planner_candidates
        ),
        "excluded_generic_titles": len([
            record for record in references
            if record.get(
                "generic_title"
            )
        ]),
    }


def export_overnight_reference(
    matched,
    unmatched,
    planner_candidates,
    summary,
    trail_root=None,
):

    trail_root = resolve_trail_root(
        trail_root
    )

    payload = {
        "schema_version": SCHEMA_VERSION,
        "trail": trail_root.name,
        "sources": [
            str(path)
            for path in source_paths(
                trail_root
            )
            if path.exists()
        ],
        "purpose": (
            "Overnight waypoint reference enrichment; "
            "not operational traversal truth"
        ),
        "summary": summary,
        "matched_overnight_sites": matched,
        "unmatched_overnight_sites": unmatched,
        "planner_candidates": planner_candidates,
    }

    with open(
        output_path(
            trail_root
        ),
        "w",
    ) as f:

        json.dump(
            payload,
            f,
            indent=2,
        )

    return payload


def build_overnight_reference(
    trail_root=None,
):

    trail_root = resolve_trail_root(
        trail_root
    )

    overlay_nodes = load_overlay_nodes(
        trail_root
    )

    references = load_overnight_points(
        trail_root
    )

    spine_index = build_spine_index(
        trail_root
    )

    matched, unmatched, planner_candidates = (
        build_reference_records(
            references,
            overlay_nodes,
            spine_index,
        )
    )

    summary = build_summary(
        references,
        matched,
        unmatched,
        planner_candidates,
    )

    return export_overnight_reference(
        matched,
        unmatched,
        planner_candidates,
        summary,
        trail_root,
    )


def main():

    trail_root = (
        Path(sys.argv[1]).resolve()
        if len(sys.argv) > 1
        else resolve_trail_root()
    )

    print("")
    print(
        "=== CairnOS Overnight Reference Overlay ==="
    )
    print("")

    if not route_overlay_path(
        trail_root
    ).exists():

        raise FileNotFoundError(
            f"Missing route overlay: "
            f"{route_overlay_path(trail_root)}"
        )

    payload = build_overnight_reference(
        trail_root
    )

    summary = payload["summary"]

    print(
        f"[INFO] Points: "
        f"{summary['total_points']}"
    )
    print(
        f"[INFO] Matched: "
        f"{summary['matched_points']}"
    )
    print(
        f"[INFO] Unmatched: "
        f"{summary['unmatched_points']}"
    )
    print(
        f"[INFO] Planner candidates: "
        f"{summary['planner_candidates']}"
    )
    print("")
    print(
        f"[OK] {output_path(trail_root)}"
    )


if __name__ == "__main__":

    main()
