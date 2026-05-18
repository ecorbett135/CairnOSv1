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


def test_generated_plan_exposes_developer_diagnostics_download():
    """Test generated plans expose a diagnostic bundle download."""
    source = Path(
        "cairn/interfaces/streamlit_app.py"
    ).read_text()

    assert "Download Developer Diagnostics" in source
    assert "developer_diagnostics_download" in source
    assert "build_diagnostic_package" in source
