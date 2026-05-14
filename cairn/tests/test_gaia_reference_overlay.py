from build_topo.compiler import (
    gaia_reference_overlay,
)


def test_gaia_reference_extracts_point_waypoints(
    trail_root,
):
    waypoints = (
        gaia_reference_overlay
        .load_gaia_points(
            trail_root
        )
    )

    assert len(waypoints) > 0
    assert all(
        waypoint.get("coordinates")
        for waypoint in waypoints
    )

    shelter = next(
        waypoint for waypoint in waypoints
        if waypoint["title"] == "Congdon Shelter"
    )

    assert shelter["waypoint_class"] == "shelter"
    assert shelter["icon"] == "shelter"
    assert shelter["marker_type"] == "outlined-icon"


def test_gaia_reference_fuzzy_matches_route_overlay(
    trail_root,
):
    overlay_nodes = (
        gaia_reference_overlay
        .load_overlay_nodes(
            trail_root
        )
    )
    waypoints = (
        gaia_reference_overlay
        .load_gaia_points(
            trail_root
        )
    )

    matched, unmatched = (
        gaia_reference_overlay
        .build_waypoint_records(
            waypoints,
            overlay_nodes,
        )
    )

    summary = (
        gaia_reference_overlay
        .build_summary(
            waypoints,
            matched,
            unmatched,
            gaia_reference_overlay
            .count_approach_line_references(
                trail_root
            ),
        )
    )

    assert summary["matched_points"] > 0
    assert summary["matched_shelters"] > 0
    assert summary["unmatched_shelters"] > 0
    assert summary["campsites"] > 0
    assert (
        summary["approach_trail_references"]
        > 0
    )

    congdon = next(
        record for record in matched
        if record["title"] == "Congdon Shelter"
    )

    assert congdon["canonical_name"] == "Congdon Shelter"
    assert congdon["trail_mile"] == 10.0
