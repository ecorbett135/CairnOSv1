from app.core.planner import (
    classify_location_type,
)


def test_peak_detection():

    assert (
        classify_location_type(
            "Camel's Hump Summit"
        )
        == "peak"
    )


def test_shelter_detection():

    assert (
        classify_location_type(
            "Cooper Lodge Shelter"
        )
        == "shelter"
    )


def test_lookout_detection():

    assert (
        classify_location_type(
            "Porcupine Lookout"
        )
        == "viewpoint"
    )
