# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import sys

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )

import streamlit as st

from cairn.planner.planner_v2 import (
    PlannerV2,
)

from cairn.export.gaia_geojson import (
    dumps_geojson,
    export_itinerary_to_gaia_geojson,
)


st.set_page_config(
    page_title="CairnOSv1",
    layout="wide",
)

TRAILS_ROOT = PROJECT_ROOT / "trails"

AVAILABLE_TRAILS = sorted([
    p.name
    for p in TRAILS_ROOT.iterdir()
    if p.is_dir()
])


def streamlit_secret(
    key,
    default="",
):
    try:
        return st.secrets.get(
            key,
            default,
        )
    except Exception:
        return default


if "planner_result" not in st.session_state:
    st.session_state["planner_result"] = None

st.title("🥾 CairnOSv1")
st.subheader(
    "Operational Expedition Planning"
)

st.warning(
    (
        "Alpha preview: CairnOSv1 is an advisory planning prototype, "
        "not a safety-critical trip-planning authority. Verify all routes, "
        "conditions, services, closures, and backcountry decisions with "
        "official sources before hiking."
    )
)

alpha_feedback_url = streamlit_secret(
    "alpha_feedback_url"
)

if alpha_feedback_url:
    st.markdown(
        f"[Share Alpha feedback]({alpha_feedback_url})"
    )

with st.sidebar:

    st.header("Planner Configuration")

    selected_trail = st.selectbox(
        "Trail",
        AVAILABLE_TRAILS,
    )

    trip_type = st.selectbox(
        "Trip Type",
        [
            "THRU",
        ],
    )

    direction = st.selectbox(
        "Direction",
        [
            "NOBO",
            "SOBO",
        ],
    )

    if trip_type == "SECTION":

        ingress_help = (
            "Section hike ingress selection"
        )

        egress_help = (
            "Section hike egress selection"
        )

    elif direction == "NOBO":

        ingress_help = (
            "Southern access approaches toward the southern terminus"
        )

        egress_help = (
            "Northern exit approaches away from the northern terminus"
        )

    else:

        ingress_help = (
            "Northern access approaches toward the northern terminus"
        )

        egress_help = (
            "Southern exit approaches away from the southern terminus"
        )

    st.subheader(
        "Directional Access"
    )

    if trip_type == "SECTION":

        ingress_route = st.selectbox(
            "Ingress Route",
            [
                "Williamstown Approach",
                "North Adams Approach",
                "Journey's End Trail",
            ],
            help=ingress_help,
        )

        egress_route = st.selectbox(
            "Egress Route",
            [
                "Williamstown Approach",
                "North Adams Approach",
                "Journey's End Trail",
            ],
            help=egress_help,
        )

    elif direction == "NOBO":

        ingress_route = st.selectbox(
            "Ingress Route",
            [
                "Williamstown Approach",
                "North Adams Approach",
            ],
            help=ingress_help,
        )

        egress_route = st.selectbox(
            "Egress Route",
            [
                "Journey's End Trail",
            ],
            help=egress_help,
        )

    else:

        ingress_route = st.selectbox(
            "Ingress Route",
            [
                "Journey's End Trail",
            ],
            help=ingress_help,
        )

        egress_route = st.selectbox(
            "Egress Route",
            [
                "Williamstown Approach",
                "North Adams Approach",
            ],
            help=egress_help,
        )

    desired_days = st.slider(
        "Desired Completion Days",
        min_value=3,
        max_value=60,
        value=28,
    )

    min_daily_miles = st.slider(
        "Minimum Daily Miles",
        min_value=4,
        max_value=25,
        value=8,
    )

    max_daily_miles = st.slider(
        "Maximum Daily Miles",
        min_value=8,
        max_value=40,
        value=16,
    )

    max_daily_elevation = st.slider(
        "Maximum Daily Elevation Gain",
        min_value=1000,
        max_value=10000,
        value=3500,
        step=250,
        help=(
            "Planning preference for daily climbing effort. "
            "Reported daily_elevation_gain is terrain-derived "
            "where compiled elevation coverage exists and is not "
            "capped to this value."
        ),
    )

    resupply_cadence = st.slider(
        "Preferred Resupply Cadence (days)",
        min_value=2,
        max_value=10,
        value=5,
    )

    recovery_cadence = st.slider(
        "Preferred Zero/Nero Cadence (days)",
        min_value=3,
        max_value=14,
        value=6,
    )

    min_nero_miles = st.slider(
        "Minimum Nero Miles",
        min_value=1,
        max_value=10,
        value=5,
        help=(
            "Lower mileage bound for labeling a recovery "
            "stop as a nero."
        ),
    )

    max_nero_miles = st.slider(
        "Maximum Nero Miles",
        min_value=4,
        max_value=15,
        value=8,
        help=(
            "Upper mileage bound for labeling a recovery "
            "stop as a nero."
        ),
    )

    if max_nero_miles < min_nero_miles:
        st.warning(
            (
                "Maximum Nero Miles is below Minimum Nero Miles; "
                "the planner will use the minimum value for both."
            )
        )

    allow_extra_resupply_only = st.checkbox(
        "Allow Extra Resupply-Only Stops",
        value=True,
    )

    planner_button_label = (
        "Regenerate Plan"
        if st.session_state["planner_result"]
        else "Generate Plan"
    )

    run_planner = st.button(
        planner_button_label
    )

if run_planner:

    trail_root = (
        TRAILS_ROOT /
        selected_trail
    )

    planner_config = {
        "selected_trail": selected_trail,
        "trail_root": str(trail_root),
        "desired_days": desired_days,
        "trip_type": trip_type,
        "direction": direction,
        "min_daily_miles": min_daily_miles,
        "max_daily_miles": max_daily_miles,
        "max_daily_elevation": max_daily_elevation,
        "resupply_cadence": resupply_cadence,
        "recovery_cadence": recovery_cadence,
        "min_nero_miles": min_nero_miles,
        "max_nero_miles": max_nero_miles,
        "allow_extra_resupply_only": (
            allow_extra_resupply_only
        ),
        "ingress_route": ingress_route,
        "egress_route": egress_route,
    }

    planner = PlannerV2(
        trail_root=trail_root,
        user_profile={
            "min_daily_miles": min_daily_miles,
            "max_daily_miles": max_daily_miles,
            "max_daily_elevation": max_daily_elevation,
            "resupply_cadence": resupply_cadence,
            "recovery_cadence": recovery_cadence,
            "min_nero_miles": min_nero_miles,
            "max_nero_miles": max_nero_miles,
            "allow_extra_resupply_only": (
                allow_extra_resupply_only
            ),
            "trip_type": trip_type,
            "direction": direction,
            "ingress_route": ingress_route,
            "egress_route": egress_route,
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=desired_days
    )

    st.session_state["planner_result"] = {
        "config": planner_config,
        "itinerary": itinerary,
    }

    st.rerun()

planner_result = st.session_state.get(
    "planner_result"
)

if planner_result:

    planner_config = planner_result[
        "config"
    ]

    itinerary = planner_result[
        "itinerary"
    ]

    trail_root = Path(
        planner_config["trail_root"]
    )

    desired_days_for_result = planner_config[
        "desired_days"
    ]

    selected_trail_for_result = planner_config[
        "selected_trail"
    ]

    direction_for_result = planner_config[
        "direction"
    ]

    completion = itinerary[
        "completion_analysis"
    ]

    evaluation = completion[
        "evaluation"
    ]

    st.header("Expedition Summary")

    summary = itinerary[
        "expedition_summary"
    ]

    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)

    summary_col1.metric(
        "Total Trail Miles",
        summary[
            "total_miles"
        ],
    )

    summary_col2.metric(
        "Completion Time",
        summary[
            "completion_days"
        ],
    )

    summary_col3.metric(
        "Average Daily Miles",
        summary[
            "average_daily_miles"
        ],
    )

    summary_col4.metric(
        "Average Daily Elevation",
        summary[
            "average_daily_elevation"
        ],
    )

    st.header("Operational Feasibility")

    evaluation = completion[
        "evaluation"
    ]

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Classification",
        evaluation[
            "classification"
        ].title(),
    )

    col2.metric(
        "Requested Days",
        desired_days_for_result,
    )

    recommended_days = completion.get(
        "recommended_days",
        desired_days_for_result,
    )

    col3.metric(
        "Recommended Days",
        recommended_days,
    )

    if completion.get(
        "has_itinerary_exceptions"
    ):

        st.warning(
            completion[
                "recommendation"
            ]
        )

        st.dataframe(
            completion[
                "itinerary_exceptions"
            ],
            width="stretch",
            hide_index=True,
        )

        st.info(
            completion[
                "exception_guidance"
            ]
        )

    elif completion["accepted"]:

        st.success(
            completion[
                "recommendation"
            ]
        )

    else:

        st.warning(
            completion[
                "recommendation"
            ]
        )

        st.info(
            "An alternative operationally sustainable itinerary was generated."
        )

    st.header("Resupply Strategy")

    resupply_rows = itinerary[
        "resupply_plan"
    ]

    if resupply_rows:

        st.dataframe(
            resupply_rows,
            width="stretch",
        )

    st.header("Operational Itinerary")

    itinerary_rows = itinerary[
        "daily_plan"
    ]

    display_itinerary_rows = [
        {
            key: value
            for key, value in row.items()
            if key != (
                "food_carry_days_since_last_resupply"
            )
        }
        for row in itinerary_rows
    ]

    st.caption(
        "Daily operational traversal plan using overlay semantics, shelters, logistics nodes, and ingress-aware progression."
    )

    st.dataframe(
        display_itinerary_rows,
        width="stretch",
        hide_index=True,
        column_order=[
            "day",
            "division",
            "daily_start_mile",
            "daily_start_location",
            "daily_start_location_type",
            "daily_stop_mile",
            "daily_stop_location",
            "daily_stop_location_type",
            "daily_miles",
            "daily_elevation_gain",
            "resupply_location",
            "resupply_mile",
            "town_access",
            "notes",
        ],
    )

    gaia_export = export_itinerary_to_gaia_geojson(
        itinerary_rows,
        trail_root,
        resupply_rows,
    )

    gaia_warnings = gaia_export[
        "warnings"
    ]

    if gaia_warnings:

        st.warning(
            (
                "Some itinerary stops could not be "
                "included in the Gaia GeoJSON export."
            )
        )

        st.dataframe(
            gaia_warnings,
            width="stretch",
            hide_index=True,
        )

    st.download_button(
        "Download Gaia GeoJSON",
        data=dumps_geojson(
            gaia_export["geojson"]
        ),
        file_name=(
            f"{selected_trail_for_result}_"
            f"{direction_for_result.lower()}_gaia.geojson"
        ),
        mime="application/geo+json",
        key="gaia_geojson_download",
    )


else:

    st.info(
        "Configure expedition goals and generate an operational itinerary."
    )
