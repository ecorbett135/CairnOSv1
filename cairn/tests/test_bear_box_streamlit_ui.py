# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from streamlit.testing.v1 import AppTest


def test_sidebar_exposes_bear_box_preference():
    """Test desktop planner controls expose bear-box preference."""
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

    assert "Prefer Sites With Bear Boxes" in checkboxes
    assert (
        checkboxes[
            "Prefer Sites With Bear Boxes"
        ].value
        is False
    )


def test_mobile_view_exposes_bear_box_preference():
    """Test mobile planner controls expose bear-box preference."""
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

    checkboxes = {
        widget.label: widget
        for widget in app.checkbox
    }

    assert "Prefer Sites With Bear Boxes" in checkboxes
    assert (
        checkboxes[
            "Prefer Sites With Bear Boxes"
        ].value
        is False
    )
