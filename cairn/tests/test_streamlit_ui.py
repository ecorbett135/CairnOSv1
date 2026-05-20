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


def test_sidebar_exposes_planned_start_date_control():
    """Test date-aware advisories are configurable in trip settings."""
    app = AppTest.from_file(
        "cairn/interfaces/streamlit_app.py"
    )

    app.run(
        timeout=15
    )

    date_inputs = {
        widget.label: widget
        for widget in app.sidebar.date_input
    }

    assert "Planned Start Date" in date_inputs
    assert date_inputs["Planned Start Date"].value is None


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


def test_alpha_build_fingerprint_is_import_time_constant():
    """Test footer cannot claim a newer checkout from stale imports."""
    source = Path(
        "cairn/interfaces/streamlit_app.py"
    ).read_text()

    assert "APP_BUILD_SHA = read_build_sha()" in source
    assert "def current_build_sha()" in source
    assert "return APP_BUILD_SHA" in source


def test_feasibility_view_separates_requested_and_generated_labels():
    """Test feasibility UI distinguishes requested and generated plans."""
    source = Path(
        "cairn/interfaces/streamlit_app.py"
    ).read_text()

    assert "Generated Plan" in source
    assert "Requested Target" in source
    assert "requested_evaluation" in source


def test_feasibility_exception_view_marks_compound_days():
    """Test exception table calls out combined mileage/elevation days."""
    source = Path(
        "cairn/interfaces/streamlit_app.py"
    ).read_text()

    assert "render_itinerary_exception_table" in source
    assert "compound-exception-day" in source
    assert (
        "Red day chips exceed both mileage and elevation preferences."
        in source
    )


def test_generated_plan_exposes_developer_diagnostics_download():
    """Test generated plans expose a diagnostic bundle download."""
    source = Path(
        "cairn/interfaces/streamlit_app.py"
    ).read_text()

    assert "Download CairnOS Plan JSON" in source
    assert "cairnos_plan_json_download" in source
    assert "build_plan_export" in source
    assert "plan_export_filename" in source
    assert "Download Developer Diagnostics" in source
    assert "developer_diagnostics_download" in source
    assert "build_diagnostic_package" in source


def test_generated_plan_is_build_aware_after_redeploy():
    """Test stale session plans are refreshed after Alpha build changes."""
    source = Path(
        "cairn/interfaces/streamlit_app.py"
    ).read_text()

    assert "build_sha" in source
    assert "ensure_current_cairn_modules" in source
    assert "importlib.reload" in source
    assert "loaded_cairn_build_sha" in source
    assert "refresh_stale_planner_result" in source
    assert "planner_result_build_sha" in source
    assert "regenerated with the same settings" in source


def test_season_advisory_section_preserves_safety_boundary():
    """Test date-aware advisory copy stays informational."""
    source = Path(
        "cairn/interfaces/streamlit_app.py"
    ).read_text()

    assert "render_season_advisories" in source
    assert "Season And Current Conditions" in source
    assert "Date-aware advisory prompts only" in source
    assert "Verify official trail" in source
    assert "updates" in source
    assert "does not change feasibility" in source
    assert "season_advisories" in source


def test_alpha_feedback_panel_exposes_routing_and_repro_guidance():
    """Test hosted Alpha reports ask for reproducible context."""
    source = Path(
        "cairn/interfaces/streamlit_app.py"
    ).read_text()

    assert "render_alpha_feedback_panel" in source
    assert "Open GitHub Feedback Templates" in source
    assert (
        "https://github.com/ecorbett135/CairnOSv1/issues/new/choose"
        in source
    )
    assert "GitHub requires an account" in source
    assert "channel where you found the alpha" in source
    assert "it already includes planner settings" in source
    assert "runtime data fingerprints" in source
    assert "Manual settings are only needed" in source
    assert "direction" in source
    assert "requested days" in source
    assert "mileage/elevation limits" in source
    assert "resupply/recovery settings" in source
    assert "Developer Diagnostics ZIP" in source
    assert "Gaia GeoJSON" in source
    assert "Do not include private tester data" in source
    assert "CairnOS output is advisory planning context only" in source


def test_alpha_feedback_does_not_enter_planner_inputs():
    """Test feedback routing remains separate from planner synthesis."""
    source = Path(
        "cairn/interfaces/streamlit_app.py"
    ).read_text()

    synthesize_block = source.split(
        "def synthesize_planner_result",
        1,
    )[1].split(
        "def render_planner_result",
        1,
    )[0]

    assert "render_alpha_feedback_panel" not in synthesize_block
    assert "GITHUB_FEEDBACK_URL" not in synthesize_block


def test_itinerary_table_exposes_stop_access_notes():
    """Test itinerary display includes concise side-spur comments."""
    source = Path(
        "cairn/interfaces/streamlit_app.py"
    ).read_text()

    assert "daily_stop_access_notes" in source
    assert "daily_stop_canonical_location" in source
    assert "daily_stop_spine_alignment" in source


def test_itinerary_table_hides_overlay_provenance_fields():
    """Test overlay traversal diagnostics stay out of Streamlit display."""
    source = Path(
        "cairn/interfaces/streamlit_app.py"
    ).read_text()
    display_block = source.split(
        "display_itinerary_rows =",
        1,
    )[1].split(
        "st.caption",
        1,
    )[0]
    column_order = source.split(
        "column_order=[",
        2,
    )[2].split(
        "]",
        1,
    )[0]

    for key in [
        "daily_start_overlay_id",
        "daily_stop_overlay_id",
        "daily_traversal_authority",
    ]:
        assert key in display_block
        assert key not in column_order


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

    assert "Optional Towns And Side Trips" in source
    assert 'f"{name} - {town_access}"' in source
    assert "town_preference_option_label" in source
    assert "split_town_access_names" in source
    assert "annotation-only" in source
    assert "selected_side_trip_ids" in source
    assert "selected_town_ids" in source


def test_selected_experiences_table_is_rendered_conditionally():
    """Test selected side trips get a dedicated output table."""
    source = Path(
        "cairn/interfaces/streamlit_app.py"
    ).read_text()

    assert "Selected Towns And Experiences" in source
    assert "selected_experiences" in source
    assert "experience_name" in source
    assert "town_access" in source
    assert "planning_status" in source


def test_recovery_planning_mode_controls_are_present():
    """Test UI exposes cadence and count-based recovery modes."""
    source = Path(
        "cairn/interfaces/streamlit_app.py"
    ).read_text()

    assert "Recovery Planning Mode" in source
    assert "Target Counts" in source
    assert "Target Zero Days" in source
    assert "Target Nero Days" in source
    assert "recovery_planning_mode" in source
    assert "target_zero_days" in source
    assert "target_nero_days" in source
