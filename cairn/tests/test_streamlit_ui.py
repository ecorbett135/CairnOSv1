# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from streamlit.testing.v1 import AppTest


def test_sidebar_exposes_trip_type_and_direction_separately():
    """Test trip scope and travel direction are distinct controls."""
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
        "SECTION",
    ]
    assert selectboxes["Direction"].options == [
        "NOBO",
        "SOBO",
    ]
