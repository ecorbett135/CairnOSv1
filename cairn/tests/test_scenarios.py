import tempfile

import pandas as pd

from app.core.planner import (
    run_planner,
)


def build_mock_route():

    return pd.DataFrame(
        {
            "division": [
                1,
                1,
                1,
                1,
            ],

            "location": [
                "Start",
                "Shelter A",
                "Shelter B",
                "Shelter C",
            ],

            "miles_from_MA_border_nb": [
                0,
                8,
                18,
                30,
            ],

            "elevation_ft": [
                1000,
                2000,
                2500,
                4000,
            ],
        }
    )


def test_scenario_runs():

    df = build_mock_route()

    with tempfile.NamedTemporaryFile(
        suffix=".csv",
        mode="w",
        delete=False,
    ) as f:

        df.to_csv(
            f.name,
            index=False,
        )

        result = run_planner(
            route_path=f.name,
            direction="NOBO",
            trip_type="THRU",
            min_miles=5,
            max_miles=15,
        )

        assert (
            result["total_days"] > 0
        )

        assert (
            result["total_distance"] > 0
        )
