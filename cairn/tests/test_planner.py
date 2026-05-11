from app.core.planner import (
    score_candidate,
)


def test_score_prefers_target_distance():

    near_target = score_candidate(
        distance=12,
        elevation_gain=2000,
        location_type="shelter",
        target_min=10,
        target_max=14,
        max_elevation_gain=5000,
    )

    far_target = score_candidate(
        distance=25,
        elevation_gain=2000,
        location_type="shelter",
        target_min=10,
        target_max=14,
        max_elevation_gain=5000,
    )

    assert near_target > far_target


def test_elevation_penalty():

    low = score_candidate(
        distance=12,
        elevation_gain=2000,
        location_type="shelter",
        target_min=10,
        target_max=14,
        max_elevation_gain=5000,
    )

    high = score_candidate(
        distance=12,
        elevation_gain=9000,
        location_type="shelter",
        target_min=10,
        target_max=14,
        max_elevation_gain=5000,
    )

    assert low > high
