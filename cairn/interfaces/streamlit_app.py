# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import subprocess
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
from cairn.export.diagnostics import (
    build_diagnostic_package,
    diagnostic_filename,
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


def current_build_sha():
    try:
        result = subprocess.run(
            [
                "git",
                "rev-parse",
                "--short",
                "HEAD",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            check=True,
            text=True,
            timeout=2,
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def user_agent():
    try:
        return str(
            st.context.headers.get(
                "user-agent",
                "",
            )
            or ""
        )
    except Exception:
        return ""


def is_mobile_user_agent(
    value,
):
    lower_value = value.lower()

    return any(
        token in lower_value
        for token in [
            "android",
            "iphone",
            "ipad",
            "ipod",
            "mobile",
        ]
    )


def resolve_view_mode(
    selected_mode,
):
    if selected_mode == "Mobile":
        return "mobile"

    if selected_mode == "Desktop":
        return "desktop"

    if is_mobile_user_agent(
        user_agent()
    ):
        return "mobile"

    return "desktop"


def planner_button_label():
    return (
        "Regenerate Plan"
        if st.session_state[
            "planner_result"
        ]
        else "Generate Plan"
    )


def directional_access_help(
    trip_type,
    direction,
):
    if trip_type == "SECTION":
        return (
            "Section hike ingress selection",
            "Section hike egress selection",
        )

    if direction == "NOBO":
        return (
            "Southern access approaches toward the southern terminus",
            "Northern exit approaches away from the northern terminus",
        )

    return (
        "Northern access approaches toward the northern terminus",
        "Southern exit approaches away from the southern terminus",
    )


def directional_access_options(
    trip_type,
    direction,
):
    if trip_type == "SECTION":
        options = [
            "Williamstown Approach",
            "North Adams Approach",
            "Journey's End Trail",
        ]
        return options, options

    if direction == "NOBO":
        return (
            [
                "Williamstown Approach",
                "North Adams Approach",
            ],
            [
                "Journey's End Trail",
            ],
        )

    return (
        [
            "Journey's End Trail",
        ],
        [
            "Williamstown Approach",
            "North Adams Approach",
        ],
    )


def render_planner_controls(
    target,
    layout_mode,
):
    target.header("Planner Configuration")

    if layout_mode == "mobile":
        target.caption(
            "Mobile layout: planner controls are shown here instead of in the sidebar."
        )
        target.subheader("Trip")

    selected_trail = target.selectbox(
        "Trail",
        AVAILABLE_TRAILS,
    )

    trip_type = target.selectbox(
        "Trip Type",
        [
            "THRU",
        ],
    )

    direction = target.selectbox(
        "Direction",
        [
            "NOBO",
            "SOBO",
        ],
    )

    ingress_help, egress_help = (
        directional_access_help(
            trip_type,
            direction,
        )
    )
    ingress_options, egress_options = (
        directional_access_options(
            trip_type,
            direction,
        )
    )

    target.subheader(
        "Directional Access"
    )

    ingress_route = target.selectbox(
        "Ingress Route",
        ingress_options,
        help=ingress_help,
    )

    egress_route = target.selectbox(
        "Egress Route",
        egress_options,
        help=egress_help,
    )

    if layout_mode == "mobile":
        target.subheader("Daily Limits")

    desired_days = target.slider(
        "Desired Completion Days",
        min_value=3,
        max_value=60,
        value=28,
    )

    min_daily_miles = target.slider(
        "Minimum Daily Miles",
        min_value=4,
        max_value=25,
        value=8,
    )

    max_daily_miles = target.slider(
        "Maximum Daily Miles",
        min_value=8,
        max_value=40,
        value=16,
    )

    max_daily_elevation = target.slider(
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

    if layout_mode == "mobile":
        target.subheader("Resupply And Recovery")

    resupply_cadence = target.slider(
        "Preferred Resupply Cadence (days)",
        min_value=2,
        max_value=10,
        value=5,
    )

    recovery_cadence = target.slider(
        "Preferred Zero/Nero Cadence (days)",
        min_value=3,
        max_value=14,
        value=6,
    )

    min_nero_miles = target.slider(
        "Minimum Nero Miles",
        min_value=1,
        max_value=10,
        value=5,
        help=(
            "Lower mileage bound for labeling a recovery "
            "stop as a nero."
        ),
    )

    max_nero_miles = target.slider(
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
        target.warning(
            (
                "Maximum Nero Miles is below Minimum Nero Miles; "
                "the planner will use the minimum value for both."
            )
        )

    allow_extra_resupply_only = target.checkbox(
        "Allow Extra Resupply-Only Stops",
        value=True,
    )

    avoid_long_food_carry = target.checkbox(
        "Avoid Long Food Carry",
        value=True,
        help=(
            "Bias resupply planning toward shorter food carries. "
            "Standalone resupply-only stops still prefer access "
            "close to the trail."
        ),
    )

    convenient_resupply_distance_miles = target.slider(
        "Convenient Resupply-Only Access (miles)",
        min_value=0.5,
        max_value=5.0,
        value=1.0,
        step=0.5,
        help=(
            "Maximum off-trail access distance the planner treats "
            "as convenient for an extra resupply-only stop. Longer "
            "town trips are still considered for zeros, neros, or "
            "avoiding excessive food carries."
        ),
    )

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
        "avoid_long_food_carry": (
            avoid_long_food_carry
        ),
        "convenient_resupply_distance_miles": (
            convenient_resupply_distance_miles
        ),
        "ingress_route": ingress_route,
        "egress_route": egress_route,
    }

    run_planner = target.button(
        planner_button_label(),
        key=f"{layout_mode}_planner_button",
    )

    target.caption(
        f"Alpha build: {current_build_sha()}"
    )

    return planner_config, run_planner


def synthesize_planner_result(
    planner_config,
):
    trail_root = Path(
        planner_config[
            "trail_root"
        ]
    )

    planner = PlannerV2(
        trail_root=trail_root,
        user_profile={
            "min_daily_miles": planner_config[
                "min_daily_miles"
            ],
            "max_daily_miles": planner_config[
                "max_daily_miles"
            ],
            "max_daily_elevation": planner_config[
                "max_daily_elevation"
            ],
            "resupply_cadence": planner_config[
                "resupply_cadence"
            ],
            "recovery_cadence": planner_config[
                "recovery_cadence"
            ],
            "min_nero_miles": planner_config[
                "min_nero_miles"
            ],
            "max_nero_miles": planner_config[
                "max_nero_miles"
            ],
            "allow_extra_resupply_only": (
                planner_config[
                    "allow_extra_resupply_only"
                ]
            ),
            "avoid_long_food_carry": (
                planner_config[
                    "avoid_long_food_carry"
                ]
            ),
            "convenient_resupply_distance_miles": (
                planner_config[
                    "convenient_resupply_distance_miles"
                ]
            ),
            "trip_type": planner_config[
                "trip_type"
            ],
            "direction": planner_config[
                "direction"
            ],
            "ingress_route": planner_config[
                "ingress_route"
            ],
            "egress_route": planner_config[
                "egress_route"
            ],
        },
    )

    itinerary = planner.synthesize_itinerary(
        desired_days=planner_config[
            "desired_days"
        ]
    )

    return {
        "config": planner_config,
        "itinerary": itinerary,
    }


def render_planner_result(
    planner_result,
):
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
            if key not in {
                "food_carry_days_since_last_resupply",
                "daily_start_canonical_location",
                "daily_stop_canonical_location",
                "daily_start_spine_alignment",
                "daily_stop_spine_alignment",
                "daily_start_access_notes",
            }
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
            "daily_stop_access_notes",
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

    build_sha_for_diagnostics = current_build_sha()

    diagnostic_package = build_diagnostic_package(
        planner_result,
        trail_root,
        gaia_export,
        build_sha_for_diagnostics,
    )

    st.download_button(
        "Download Developer Diagnostics",
        data=diagnostic_package,
        file_name=diagnostic_filename(
            planner_result,
            build_sha_for_diagnostics,
        ),
        mime="application/zip",
        key="developer_diagnostics_download",
    )


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

selected_view_mode = st.radio(
    "View Mode",
    [
        "Auto",
        "Mobile",
        "Desktop",
    ],
    horizontal=True,
    key="view_mode",
    help=(
        "Use Mobile if your phone does not show Streamlit's sidebar controls."
    ),
)

layout_mode = resolve_view_mode(
    selected_view_mode
)

if layout_mode == "mobile":
    planner_config, run_planner = render_planner_controls(
        st,
        layout_mode,
    )
else:
    with st.sidebar:
        planner_config, run_planner = render_planner_controls(
            st,
            layout_mode,
        )

if run_planner:
    st.session_state["planner_result"] = (
        synthesize_planner_result(
            planner_config
        )
    )
    st.rerun()

planner_result = st.session_state.get(
    "planner_result"
)

if planner_result:
    render_planner_result(
        planner_result
    )
else:
    st.info(
        "Configure expedition goals and generate an operational itinerary."
    )
