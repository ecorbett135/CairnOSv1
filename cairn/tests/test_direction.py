import pandas as pd

from app.core.planner import (
    prepare_route,
)


def build_df():

    return pd.DataFrame(
        {
            "mile": [0, 10, 20],
        }
    )


def test_nobo_order():

    df = build_df()

    result = prepare_route(
        df,
        direction="NOBO",
    )

    assert list(
        result["effective_mile"]
    ) == [0, 10, 20]


def test_sobo_order():

    df = build_df()

    result = prepare_route(
        df,
        direction="SOBO",
    )

    assert list(
        result["effective_mile"]
    ) == [0, 10, 20]
