# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import csv
import io
import json
import zipfile

from cairn.export.diagnostics import (
    DIAGNOSTIC_SCHEMA_VERSION,
    build_diagnostic_package,
    diagnostic_filename,
)
from cairn.export.gaia_geojson import (
    export_itinerary_to_gaia_geojson,
)


EXPECTED_ZIP_FILES = {
    "manifest.json",
    "plan.json",
    "itinerary.csv",
    "resupply_strategy.csv",
    "completion_analysis.json",
    "gaia.geojson",
    "gaia_warnings.json",
    "data_fingerprints.json",
    "elevation_confidence.json",
}


def read_zip_json(
    archive,
    name,
):
    return json.loads(
        archive.read(name).decode("utf-8")
    )


def test_diagnostic_package_contains_safe_runtime_bundle(
    planner_factory,
    trail_root,
):
    planner = planner_factory(
        user_profile={
            "direction": "NOBO",
            "ingress_route": "North Adams Approach",
            "min_daily_miles": 8,
            "max_daily_miles": 16,
            "max_daily_elevation": 3500,
        }
    )
    itinerary = planner.synthesize_itinerary(
        desired_days=21
    )
    gaia_export = export_itinerary_to_gaia_geojson(
        itinerary["daily_plan"],
        trail_root,
        itinerary["resupply_plan"],
    )
    planner_result = {
        "config": {
            "selected_trail": "vermont_long_trail",
            "trail_root": str(trail_root.resolve()),
            "direction": "NOBO",
            "trip_type": "THRU",
            "external_debug_path": (
                "/Users/ecorbett/Downloads/private.gpx"
            ),
        },
        "itinerary": itinerary,
        "build_sha": "abcdef123456",
    }

    package = build_diagnostic_package(
        planner_result,
        trail_root,
        gaia_export,
        "abcdef123456",
        generated_at="20260518T120000Z",
    )

    with zipfile.ZipFile(
        io.BytesIO(package)
    ) as archive:
        assert set(
            archive.namelist()
        ) == EXPECTED_ZIP_FILES

        manifest = read_zip_json(
            archive,
            "manifest.json",
        )
        plan = read_zip_json(
            archive,
            "plan.json",
        )
        completion = read_zip_json(
            archive,
            "completion_analysis.json",
        )
        elevation_confidence = read_zip_json(
            archive,
            "elevation_confidence.json",
        )
        fingerprints = read_zip_json(
            archive,
            "data_fingerprints.json",
        )

        assert (
            manifest["schema_version"]
            == DIAGNOSTIC_SCHEMA_VERSION
        )
        assert manifest["build_sha"] == "abcdef123456"
        assert manifest[
            "plan_build_sha"
        ] == "abcdef123456"
        assert (
            manifest[
                "plan_build_matches_manifest"
            ]
            is True
        )
        assert (
            manifest["planner_settings"]["trail_root"]
            == "trails/vermont_long_trail"
        )
        assert (
            manifest["planner_settings"][
                "external_debug_path"
            ]
            == "[redacted_path]"
        )
        assert (
            plan["config"]["trail_root"]
            == "trails/vermont_long_trail"
        )
        assert (
            plan["config"]["external_debug_path"]
            == "[redacted_path]"
        )
        assert "selected_experiences" in plan[
            "itinerary"
        ]
        assert completion == itinerary[
            "completion_analysis"
        ]
        assert (
            elevation_confidence["schema_version"]
            == "cairnos_elevation_confidence_v1"
        )
        assert (
            elevation_confidence["summary"][
                "total_days"
            ]
            == len(itinerary["daily_plan"])
        )
        assert (
            elevation_confidence["summary"][
                "moving_days"
            ]
            > 0
        )
        assert elevation_confidence["days"]
        assert {
            "day",
            "confidence",
            "terrain_source",
            "reported_elevation_gain_ft",
            "recomputed_elevation_gain_ft",
            "reasons",
        } <= set(
            elevation_confidence["days"][0]
        )

        text_payload = "\n".join(
            archive.read(name).decode("utf-8")
            for name in [
                "manifest.json",
                "plan.json",
                "completion_analysis.json",
                "gaia_warnings.json",
                "data_fingerprints.json",
                "elevation_confidence.json",
            ]
        )
        assert "/Users/" not in text_payload
        assert "Downloads" not in text_payload

        fingerprint_paths = {
            row["relative_path"]
            for row in fingerprints
        }
        assert (
            "trails/vermont_long_trail/compiled/route_overlay.json"
            in fingerprint_paths
        )
        assert (
            "trails/vermont_long_trail/compiled/terrain.geojson"
            in fingerprint_paths
        )
        assert (
            "trails/vermont_long_trail/raw/csv/resupply_amenities.csv"
            in fingerprint_paths
        )
        assert (
            "trails/vermont_long_trail/raw/csv/overnight_amenities.csv"
            in fingerprint_paths
        )
        assert (
            "trails/vermont_long_trail/raw/csv/town_lodging_options.csv"
            in fingerprint_paths
        )
        assert not any(
            "elevation_calibration" in path
            or "Downloads" in path
            for path in fingerprint_paths
        )
        assert all(
            "relative_path" in row
            and "sha256" in row
            and "byte_size" in row
            for row in fingerprints
        )


def test_diagnostic_package_csv_outputs_are_readable(
    planner_factory,
    trail_root,
):
    planner = planner_factory(
        user_profile={
            "direction": "SOBO",
            "ingress_route": "Journey's End Trail",
            "egress_route": "Williamstown Approach",
            "min_daily_miles": 8,
            "max_daily_miles": 16,
        }
    )
    itinerary = planner.synthesize_itinerary(
        desired_days=21
    )
    gaia_export = export_itinerary_to_gaia_geojson(
        itinerary["daily_plan"],
        trail_root,
        itinerary["resupply_plan"],
    )

    package = build_diagnostic_package(
        {
            "config": {
                "selected_trail": "vermont_long_trail",
                "trail_root": str(trail_root.resolve()),
                "direction": "SOBO",
                "trip_type": "THRU",
            },
            "itinerary": itinerary,
        },
        trail_root,
        gaia_export,
        "abcdef123456",
        generated_at="20260518T120000Z",
    )

    with zipfile.ZipFile(
        io.BytesIO(package)
    ) as archive:
        itinerary_rows = list(
            csv.DictReader(
                io.StringIO(
                    archive.read(
                        "itinerary.csv"
                    ).decode("utf-8")
                )
            )
        )
        resupply_rows = list(
            csv.DictReader(
                io.StringIO(
                    archive.read(
                        "resupply_strategy.csv"
                    ).decode("utf-8")
                )
            )
        )

    assert itinerary_rows
    assert resupply_rows
    assert "daily_stop_location" in itinerary_rows[0]
    assert "location" in resupply_rows[0]


def test_diagnostic_filename_is_stable_shape():
    filename = diagnostic_filename(
        {
            "config": {
                "selected_trail": "vermont_long_trail",
                "direction": "NOBO",
            }
        },
        "abcdef1234567890",
        generated_at="20260518T120000Z",
    )

    assert filename == (
        "cairnos_diagnostic_vermont_long_trail_nobo_"
        "20260518T120000Z_abcdef123456.zip"
    )
