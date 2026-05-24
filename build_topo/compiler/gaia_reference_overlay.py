# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from difflib import SequenceMatcher
from pathlib import Path
import json
import sys

from build_topo.compiler.provenance import (
    repo_relative_path,
)


SCHEMA_VERSION = "1.0"

MATCH_THRESHOLD = 0.72


def resolve_trail_root(trail_root=None):

    if trail_root is not None:
        return Path(trail_root).resolve()

    return Path(
        "trails/vermont_long_trail"
    ).resolve()


def gaia_reference_path(trail_root):

    return (
        Path(trail_root) /
        "raw" /
        "geojson" /
        "gaia_reference.geojson"
    )


def route_overlay_path(trail_root):

    return (
        Path(trail_root) /
        "compiled" /
        "route_overlay.json"
    )


def output_path(trail_root):

    return (
        Path(trail_root) /
        "compiled" /
        "waypoint_reference.json"
    )


def load_json(path):

    with open(path) as f:
        return json.load(f)


def normalize_text(value):

    return (
        str(value or "")
        .strip()
    )


def normalize_match_text(value):

    text = normalize_text(value).lower()

    replacements = {
        "’": "'",
        "-": " ",
        ";": " ",
        ",": " ",
        "(": " ",
        ")": " ",
        ".": " ",
        "/": " ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return " ".join(
        text.split()
    )


def title_similarity(
    waypoint_title,
    overlay_name,
):

    waypoint_text = normalize_match_text(
        waypoint_title
    )

    overlay_text = normalize_match_text(
        overlay_name
    )

    if not waypoint_text or not overlay_text:
        return 0.0

    if waypoint_text == overlay_text:
        return 1.0

    if (
        waypoint_text in overlay_text
        or overlay_text in waypoint_text
    ):
        return 0.92

    return SequenceMatcher(
        None,
        waypoint_text,
        overlay_text,
    ).ratio()


def classify_waypoint(
    title,
    icon,
    marker_type,
):

    haystack = " ".join([
        normalize_match_text(title),
        normalize_match_text(icon),
        normalize_match_text(marker_type),
    ])

    if "shelter" in haystack:
        return "shelter"

    if (
        "campsite" in haystack
        or "camp site" in haystack
        or "tenting" in haystack
        or " camp" in f" {haystack}"
    ):
        return "campsite"

    if (
        "lodge" in haystack
        or "hut" in haystack
        or "building" in haystack
    ):
        return "lodge"

    if (
        "trailhead" in haystack
        or "parking" in haystack
        or "start end" in haystack
        or "start" in haystack
    ):
        return "trailhead"

    if (
        "resupply" in haystack
        or "car" in haystack
    ):
        return "resupply"

    if (
        "known route" in haystack
        or "division" in haystack
        or "approach" in haystack
    ):
        return "approach_reference"

    return "waypoint"


def load_overlay_nodes(
    trail_root=None,
):

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


def load_gaia_points(
    trail_root=None,
):

    trail_root = resolve_trail_root(
        trail_root
    )

    payload = load_json(
        gaia_reference_path(
            trail_root
        )
    )

    points = []

    for feature in payload.get(
        "features",
        [],
    ):

        geometry = feature.get(
            "geometry",
            {},
        )

        if geometry.get("type") != "Point":
            continue

        props = feature.get(
            "properties",
            {},
        )

        title = normalize_text(
            props.get("title")
            or props.get("name")
        )

        coordinates = geometry.get(
            "coordinates",
            [],
        )

        icon = props.get("icon")

        marker_type = props.get(
            "marker_type"
        )

        waypoint_class = classify_waypoint(
            title,
            icon,
            marker_type,
        )

        points.append({
            "source_id": props.get("id"),
            "title": title,
            "coordinates": (
                coordinates[:2]
                if len(coordinates) >= 2
                else None
            ),
            "icon": icon,
            "marker_type": marker_type,
            "marker_color": props.get(
                "marker_color"
            ),
            "marker_decoration": props.get(
                "marker_decoration"
            ),
            "deleted": bool(
                props.get("deleted")
            ),
            "waypoint_class": waypoint_class,
        })

    return points


def count_approach_line_references(
    trail_root=None,
):

    trail_root = resolve_trail_root(
        trail_root
    )

    payload = load_json(
        gaia_reference_path(
            trail_root
        )
    )

    count = 0

    for feature in payload.get(
        "features",
        [],
    ):

        geometry = feature.get(
            "geometry",
            {},
        )

        if geometry.get("type") == "Point":
            continue

        props = feature.get(
            "properties",
            {},
        )

        title = normalize_match_text(
            props.get("title")
            or props.get("name")
        )

        if "approach" in title:
            count += 1

    return count


def match_waypoint(
    waypoint,
    overlay_nodes,
):

    title = waypoint.get(
        "title"
    )

    best = None

    for node in overlay_nodes:

        score = title_similarity(
            title,
            node.get(
                "canonical_name"
            ),
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


def build_waypoint_records(
    waypoints,
    overlay_nodes,
):

    matched = []
    unmatched = []

    for waypoint in waypoints:

        match = match_waypoint(
            waypoint,
            overlay_nodes,
        )

        record = {
            **waypoint,
            **match,
            "schema_version": SCHEMA_VERSION,
        }

        if match["matched"]:
            matched.append(record)
        else:
            unmatched.append(record)

    return matched, unmatched


def count_records(
    records,
    waypoint_class,
):

    return len([
        record for record in records
        if record.get(
            "waypoint_class"
        ) == waypoint_class
    ])


def build_summary(
    waypoints,
    matched,
    unmatched,
    approach_line_references,
):

    active_waypoints = [
        waypoint for waypoint in waypoints
        if not waypoint.get("deleted")
    ]

    approach_references = [
        waypoint for waypoint in waypoints
        if (
            waypoint.get(
                "waypoint_class"
            )
            == "approach_reference"
            or "approach" in normalize_match_text(
                waypoint.get("title")
            )
        )
    ]

    return {
        "total_points": len(waypoints),
        "active_points": len(
            active_waypoints
        ),
        "deleted_points": (
            len(waypoints)
            - len(active_waypoints)
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
        "campsites": (
            count_records(
                matched,
                "campsite",
            )
            + count_records(
                unmatched,
                "campsite",
            )
        ),
        "approach_trail_references": (
            len(approach_references)
            + approach_line_references
        ),
    }


def export_waypoint_reference(
    matched,
    unmatched,
    summary,
    trail_root=None,
):

    trail_root = resolve_trail_root(
        trail_root
    )

    payload = {
        "schema_version": SCHEMA_VERSION,
        "trail": trail_root.name,
        "source": repo_relative_path(
            gaia_reference_path(
                trail_root
            ),
            trail_root,
        ),
        "purpose": (
            "Gaia waypoint reference enrichment; "
            "not operational traversal authority"
        ),
        "summary": summary,
        "matched_waypoints": matched,
        "unmatched_waypoints": unmatched,
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


def main():

    trail_root = (
        Path(sys.argv[1]).resolve()
        if len(sys.argv) > 1
        else resolve_trail_root()
    )

    gaia_path = gaia_reference_path(
        trail_root
    )

    overlay_path = route_overlay_path(
        trail_root
    )

    waypoint_output_path = output_path(
        trail_root
    )

    print("")
    print(
        "=== CairnOS Gaia Reference Overlay ==="
    )
    print("")

    if not gaia_path.exists():

        raise FileNotFoundError(
            f"Missing Gaia reference GeoJSON: "
            f"{gaia_path}"
        )

    if not overlay_path.exists():

        raise FileNotFoundError(
            f"Missing route overlay: "
            f"{overlay_path}"
        )

    overlay_nodes = load_overlay_nodes(
        trail_root
    )
    waypoints = load_gaia_points(
        trail_root
    )

    matched, unmatched = build_waypoint_records(
        waypoints,
        overlay_nodes,
    )

    summary = build_summary(
        waypoints,
        matched,
        unmatched,
        count_approach_line_references(
            trail_root
        ),
    )

    export_waypoint_reference(
        matched,
        unmatched,
        summary,
        trail_root,
    )

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
        f"[INFO] Matched shelters: "
        f"{summary['matched_shelters']}"
    )
    print(
        f"[INFO] Unmatched shelters: "
        f"{summary['unmatched_shelters']}"
    )
    print(
        f"[INFO] Campsites: "
        f"{summary['campsites']}"
    )
    print(
        f"[INFO] Approach references: "
        f"{summary['approach_trail_references']}"
    )
    print("")
    print(
        f"[OK] {waypoint_output_path}"
    )


if __name__ == "__main__":

    main()
