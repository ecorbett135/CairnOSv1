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

if "planner_result" not in st.session_state:
    st.session_state["planner_result"] = None

st.title("🥾 CairnOSv1")
st.subheader(
    "Operational Expedition Planning"
)

with st.sidebar:

    st.header("Planner Configuration")

    selected_trail = st.selectbox(
        "Trail",
        AVAILABLE_TRAILS,
    )

    direction = st.selectbox(
        "Trip Type",
        [
            "NOBO",
            "SOBO",
            "SECTION",
        ],
    )

    if direction == "NOBO":

        ingress_help = (
            "Southern access approaches toward the southern terminus"
        )

        egress_help = (
            "Northern exit approaches away from the northern terminus"
        )

    elif direction == "SOBO":

        ingress_help = (
            "Northern access approaches toward the northern terminus"
        )

        egress_help = (
            "Southern exit approaches away from the southern terminus"
        )

    else:

        ingress_help = (
            "Section hike ingress selection"
        )

        egress_help = (
            "Section hike egress selection"
        )

    st.subheader(
        "Directional Access"
    )

    if direction == "NOBO":

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

    elif direction == "SOBO":

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

    else:

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

    desired_days = st.slider(
        "Desired Completion Days",
        min_value=3,
        max_value=60,
        value=21,
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
    )

    resupply_cadence = st.slider(
        "Preferred Resupply / Zero Cadence (days)",
        min_value=2,
        max_value=10,
        value=5,
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
        "direction": direction,
        "min_daily_miles": min_daily_miles,
        "max_daily_miles": max_daily_miles,
        "max_daily_elevation": max_daily_elevation,
        "resupply_cadence": resupply_cadence,
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

    if completion["accepted"]:

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

    st.caption(
        "Daily operational traversal plan using overlay semantics, shelters, logistics nodes, and ingress-aware progression."
    )

    st.dataframe(
        itinerary_rows,
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
