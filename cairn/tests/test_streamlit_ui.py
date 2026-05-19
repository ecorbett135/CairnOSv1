# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_streamlit_exposes_alpha_advisory_notice():
    """Test hosted Alpha usage is framed as advisory."""
    app = AppTest.from_file(
        "cairn/interfaces/streamlit_app.py"
    )

    app.run(
        timeout=15
    )

    warnings = [
        widget.value
        for widget in app.warning
    ]

    assert any(
        "Alpha preview" in warning
        and "not a safety-critical" in warning
        for warning in warnings
    )


def test_sidebar_exposes_thru_trip_type_and_direction():
    """Test MVP trip scope and travel direction are distinct controls."""
    app = AppTest.from_file(
        "cairn/interfaces/streamlit_app.py"
    )

    app.run(
        timeout=15
    )

    selectboxes = {
        widget.label: widget
        for widget in app.sidebar.selectbox
    }

    assert "Trip Type" in selectboxes
    assert "Direction" in selectboxes
    assert selectboxes["Trip Type"].options == [
        "THRU",
    ]
    assert selectboxes["Direction"].options == [
        "NOBO",
        "SOBO",
    ]


def test_view_mode_control_exposes_mobile_fallback():
    """Test mobile users can switch away from sidebar controls."""
    app = AppTest.from_file(
        "cairn/interfaces/streamlit_app.py"
    )

    app.run(
        timeout=15
    )

    radios = {
        widget.label: widget
        for widget in app.radio
    }

    assert "View Mode" in radios
    assert radios["View Mode"].options == [
        "Auto",
        "Mobile",
        "Desktop",
    ]
    assert radios["View Mode"].value == "Auto"


def test_mobile_view_renders_controls_without_sidebar():
    """Test mobile planner controls render in the page body."""
    app = AppTest.from_file(
        "cairn/interfaces/streamlit_app.py"
    )

    app.run(
        timeout=15
    )

    app.radio[0].set_value(
        "Mobile"
    ).run(
        timeout=15
    )

    selectboxes = {
        widget.label: widget
        for widget in app.selectbox
    }
    sliders = {
        widget.label: widget
        for widget in app.slider
    }
    checkboxes = {
        widget.label: widget
        for widget in app.checkbox
    }

    assert app.sidebar.selectbox == []
    assert app.sidebar.slider == []
    assert app.sidebar.checkbox == []
    assert "Trail" in selectboxes
    assert "Trip Type" in selectboxes
    assert "Direction" in selectboxes
    assert "Desired Completion Days" in sliders
    assert "Preferred Resupply Cadence (days)" in sliders
    assert (
        "Convenient Resupply-Only Access (miles)"
        in sliders
    )
    assert "Allow Extra Resupply-Only Stops" in checkboxes
    assert "Avoid Long Food Carry" in checkboxes


def test_sidebar_exposes_configurable_nero_window():
    """Test recovery planning exposes nero-mile bounds."""
    app = AppTest.from_file(
        "cairn/interfaces/streamlit_app.py"
    )

    app.run(
        timeout=15
    )

    sliders = {
        widget.label: widget
        for widget in app.sidebar.slider
    }

    assert "Minimum Nero Miles" in sliders
    assert "Maximum Nero Miles" in sliders
    assert sliders["Minimum Nero Miles"].value == 5
    assert sliders["Maximum Nero Miles"].value == 8


def test_sidebar_exposes_food_carry_preference():
    """Test resupply planning exposes long-carry avoidance."""
    app = AppTest.from_file(
        "cairn/interfaces/streamlit_app.py"
    )

    app.run(
        timeout=15
    )

    checkboxes = {
        widget.label: widget
        for widget in app.sidebar.checkbox
    }

    assert "Avoid Long Food Carry" in checkboxes
    assert (
        checkboxes[
            "Avoid Long Food Carry"
        ].value
        is True
    )


def test_sidebar_exposes_convenient_resupply_access_range():
    """Test resupply-only convenience is user configurable."""
    app = AppTest.from_file(
        "cairn/interfaces/streamlit_app.py"
    )

    app.run(
        timeout=15
    )

    sliders = {
        widget.label: widget
        for widget in app.sidebar.slider
    }

    assert (
        "Convenient Resupply-Only Access (miles)"
        in sliders
    )
    assert (
        sliders[
            "Convenient Resupply-Only Access (miles)"
        ].value
        == 1.0
    )


def test_sidebar_defaults_to_alpha_safe_completion_days():
    """Test Alpha defaults avoid overly aggressive first-run plans."""
    app = AppTest.from_file(
        "cairn/interfaces/streamlit_app.py"
    )

    app.run(
        timeout=15
    )

    sliders = {
        widget.label: widget
        for widget in app.sidebar.slider
    }

    assert sliders[
        "Desired Completion Days"
    ].value == 28


def test_sidebar_exposes_alpha_build_fingerprint():
    """Test deployed Alpha can be matched to a repository commit."""
    app = AppTest.from_file(
        "cairn/interfaces/streamlit_app.py"
    )

    app.run(
        timeout=15
    )

    captions = [
        widget.value
        for widget in app.sidebar.caption
    ]

    assert any(
        caption.startswith("Alpha build: ")
        for caption in captions
    )


def test_feasibility_view_separates_requested_and_generated_labels():
    """Test feasibility UI distinguishes requested and generated plans."""
    source = Path(
        "cairn/interfaces/streamlit_app.py"
    ).read_text()

    assert "Generated Plan" in source
    assert "Requested Target" in source
    assert "requested_evaluation" in source


def test_generated_plan_exposes_developer_diagnostics_download():
    """Test generated plans expose a diagnostic bundle download."""
    source = Path(
        "cairn/interfaces/streamlit_app.py"
    ).read_text()

    assert "Download Developer Diagnostics" in source
    assert "developer_diagnostics_download" in source
    assert "build_diagnostic_package" in source


def test_itinerary_table_exposes_stop_access_notes():
    """Test itinerary display includes concise side-spur comments."""
    source = Path(
        "cairn/interfaces/streamlit_app.py"
    ).read_text()

    assert "daily_stop_access_notes" in source
    assert "daily_stop_canonical_location" in source
    assert "daily_stop_spine_alignment" in source


def test_resupply_town_details_render_with_validation_notice():
    """Test UI surfaces advisory town-service context."""
    source = Path(
        "cairn/interfaces/streamlit_app.py"
    ).read_text()

    assert "Town Details" in source
    assert "town service categories are planning context only" in (
        source.lower()
    )
    assert "business_detail_status" in source
    assert "zero_support" in source


def test_side_trip_preferences_are_annotation_only():
    """Test optional side trips do not imply itinerary mutation."""
    source = Path(
        "cairn/interfaces/streamlit_app.py"
    ).read_text()

    assert "Optional Side Trips" in source
    assert "annotation-only" in source
    assert "selected_side_trip_ids" in source
