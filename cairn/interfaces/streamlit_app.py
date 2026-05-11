import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.append(str(PROJECT_ROOT))

import pandas as pd
import streamlit as st

from app.core.planner import (
    load_route,
    prepare_route,
    build_location_options,
    run_planner,
)

#
# ------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------
#

st.set_page_config(
    page_title="CairnOS",
    layout="wide",
)

st.title("🥾 CairnOS Planner Demo")

st.markdown(
    """
AI-assisted backpacking itinerary planner.
"""
)

#
# ------------------------------------------------------------
# LOAD OPERATIONAL GRAPH
# ------------------------------------------------------------
#

route_df = load_route()

#
# ------------------------------------------------------------
# DIRECTION + TRIP TYPE
# ------------------------------------------------------------
#

col1, col2 = st.columns(2)

with col1:

    direction = st.selectbox(
        "Direction",
        [
            "NOBO",
            "SOBO",
        ],
    )

with col2:

    trip_type = st.selectbox(
        "Trip Type",
        [
            "THRU",
            "SECTION",
        ],
    )

#
# ------------------------------------------------------------
# PREPARE ROUTE
# ------------------------------------------------------------
#

prepared_df = prepare_route(
    route_df,
    direction=direction,
)

location_options = (
    build_location_options(
        prepared_df
    )
)

#
# ------------------------------------------------------------
# START / END
# ------------------------------------------------------------
#

col3, col4 = st.columns(2)

with col3:

    selected_start = st.selectbox(
        "Start Location",
        options=location_options,
        format_func=lambda o: o["label"],
        index=0,
    )

    start_location = selected_start["value"]

with col4:

    end_location = None

    if trip_type == "SECTION":

        selected_end = st.selectbox(
            "End Location",
            options=location_options,
            format_func=lambda o: o["label"],
            index=min(
                25,
                len(location_options) - 1,
            ),
        )

        end_location = selected_end["value"]

#
# ------------------------------------------------------------
# OPTIONS
# ------------------------------------------------------------
#

col5, col6, col7, col8 = st.columns(4)

with col5:

    min_miles = st.slider(
        "Min Miles",
        5,
        20,
        8,
    )

with col6:

    max_miles = st.slider(
        "Max Miles",
        8,
        30,
        15,
    )

with col7:

    max_elevation_gain = st.slider(
        "Max Elevation Gain",
        1000,
        10000,
        5000,
    )

with col8:

    resupply_days = st.slider(
        "Resupply Window (days)",
        1,
        7,
        4,
    )

#
# ------------------------------------------------------------
# APPROACH TRAIL
# ------------------------------------------------------------
#

approach_trail = st.checkbox(
    "Include Approach Trail (Division 0)",
    value=False,
)

#
# ------------------------------------------------------------
# GENERATE
# ------------------------------------------------------------
#

if st.button("Generate Plan"):

    try:

        result = run_planner(
            direction=direction,
            trip_type=trip_type,
            start_location=start_location,
            end_location=end_location,
            min_miles=min_miles,
            max_miles=max_miles,
            max_elevation_gain=max_elevation_gain,
            resupply_days=resupply_days,
            approach_trail=approach_trail,
        )

        st.success(
            "Plan generated successfully"
        )

        #
        # itinerary dataframe
        #

        df = pd.DataFrame(
            result.get("days", [])
        )

        desired_columns = [

            "start_mile",
            "start",

            "end_mile",
            "end",

            "distance",
            "elevation_gain_ft",

            "overnight_type",
            "difficulty",
        ]

        existing_columns = [
            c for c in desired_columns
            if c in df.columns
        ]

        if existing_columns:

            df = df[existing_columns]

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
            )

        #
        # metrics
        #

        metric1, metric2 = st.columns(2)

        with metric1:

            st.metric(
                "Total Days",
                result.get("total_days", 0),
            )

        with metric2:

            st.metric(
                "Total Distance",
                round(
                    result.get(
                        "total_distance",
                        0,
                    ),
                    1,
                ),
            )

        #
        # raw output debug
        #

        with st.expander(
            "Planner Output"
        ):

            st.json(result)

    except Exception as e:

        st.error(str(e))
