# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""Reference elevation comparison helpers.

This module is intentionally a calibration/reporting utility. It can read local
reference exports, but it does not make vendor data operational truth.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from cairn.planner.planner_v2 import PlannerV2


FEET_PER_METER = 3.280839895
METERS_PER_MILE = 1609.344
EARTH_RADIUS_MILES = 3958.7613
DEFAULT_ELEVATION_THRESHOLD_FT = 50.0


@dataclass
class ReferenceRoute:
    path: str
    title: str
    source_format: str
    points: list[tuple[float, float, float | None]]
    summary_distance_miles: float | None = None
    summary_gain_ft: float | None = None
    summary_loss_ft: float | None = None

    def measured_distance_miles(
        self,
    ) -> float:
        return path_distance_miles(
            self.points
        )

    def raw_gain_loss_ft(
        self,
    ) -> tuple[float | None, float | None]:
        return calculate_gain_loss(
            self.points,
            threshold_ft=0.0,
        )

    def smoothed_gain_loss_ft(
        self,
        threshold_ft=DEFAULT_ELEVATION_THRESHOLD_FT,
    ) -> tuple[float | None, float | None]:
        return calculate_gain_loss(
            self.points,
            threshold_ft=threshold_ft,
        )

    def summary(
        self,
        threshold_ft=DEFAULT_ELEVATION_THRESHOLD_FT,
    ) -> dict:
        raw_gain, raw_loss = self.raw_gain_loss_ft()
        smooth_gain, smooth_loss = (
            self.smoothed_gain_loss_ft(
                threshold_ft=threshold_ft,
            )
        )

        return {
            "path": self.path,
            "title": self.title,
            "source_format": self.source_format,
            "point_count": len(self.points),
            "measured_distance_miles": round(
                self.measured_distance_miles(),
                2,
            ),
            "summary_distance_miles": round_optional(
                self.summary_distance_miles,
                2,
            ),
            "summary_gain_ft": round_optional(
                self.summary_gain_ft,
                0,
            ),
            "summary_loss_ft": round_optional(
                self.summary_loss_ft,
                0,
            ),
            "raw_gain_ft": round_optional(
                raw_gain,
                0,
            ),
            "raw_loss_ft": round_optional(
                raw_loss,
                0,
            ),
            "smoothed_gain_ft": round_optional(
                smooth_gain,
                0,
            ),
            "smoothed_loss_ft": round_optional(
                smooth_loss,
                0,
            ),
            "smoothing_threshold_ft": threshold_ft,
        }


@dataclass
class CalibrationManifestRow:
    name: str
    start_mile: float
    stop_mile: float
    reference_gain_ft: float | None = None
    reference_distance_miles: float | None = None
    source_tool: str = ""
    notes: str = ""
    file: str | None = None


def round_optional(
    value,
    digits,
):
    if value is None:
        return None
    return round(
        value,
        digits,
    )


def haversine_miles(
    left,
    right,
) -> float:
    left_lon, left_lat = map(
        math.radians,
        left[:2],
    )
    right_lon, right_lat = map(
        math.radians,
        right[:2],
    )

    delta_lon = right_lon - left_lon
    delta_lat = right_lat - left_lat

    h_value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(left_lat)
        * math.cos(right_lat)
        * math.sin(delta_lon / 2) ** 2
    )

    return (
        2
        * EARTH_RADIUS_MILES
        * math.asin(math.sqrt(h_value))
    )


def path_distance_miles(
    points,
) -> float:
    return sum(
        haversine_miles(
            left,
            right,
        )
        for left, right in zip(
            points,
            points[1:],
        )
    )


def calculate_gain_loss(
    points,
    threshold_ft=0.0,
) -> tuple[float | None, float | None]:
    elevations = [
        point[2]
        for point in points
        if point[2] is not None
    ]

    if len(elevations) < 2:
        return (
            None,
            None,
        )

    gain = 0.0
    loss = 0.0
    accepted_elevation = elevations[0]

    for elevation in elevations[1:]:
        delta = (
            elevation
            - accepted_elevation
        )

        if abs(delta) < threshold_ft:
            continue

        if delta > 0:
            gain += delta
        else:
            loss += abs(delta)

        accepted_elevation = elevation

    return (
        gain,
        loss,
    )


def meters_to_miles(
    value,
):
    if value is None:
        return None
    return float(value) / METERS_PER_MILE


def meters_to_feet(
    value,
):
    if value is None:
        return None
    return float(value) * FEET_PER_METER


def coordinate_to_point(
    coordinate,
) -> tuple[float, float, float | None]:
    elevation = None

    if len(coordinate) > 2:
        elevation = meters_to_feet(
            coordinate[2]
        )

    return (
        float(coordinate[0]),
        float(coordinate[1]),
        elevation,
    )


def flatten_geojson_geometry(
    geometry,
) -> list[tuple[float, float, float | None]]:
    geometry_type = geometry.get(
        "type"
    )
    coordinates = geometry.get(
        "coordinates",
        [],
    )

    if geometry_type == "LineString":
        parts = [
            coordinates,
        ]
    elif geometry_type == "MultiLineString":
        parts = coordinates
    else:
        return []

    points = []

    for part in parts:
        points.extend(
            coordinate_to_point(
                coordinate
            )
            for coordinate in part
        )

    return points


def load_geojson_routes(
    path,
) -> list[ReferenceRoute]:
    payload = json.loads(
        Path(path).read_text()
    )
    routes = []

    for feature in payload.get(
        "features",
        [],
    ):
        geometry = feature.get(
            "geometry",
            {},
        )
        points = flatten_geojson_geometry(
            geometry
        )

        if len(points) < 2:
            continue

        properties = feature.get(
            "properties",
            {},
        )

        routes.append(
            ReferenceRoute(
                path=str(path),
                title=(
                    properties.get("title")
                    or Path(path).stem
                ),
                source_format="geojson",
                points=points,
                summary_distance_miles=meters_to_miles(
                    properties.get("distance")
                ),
                summary_gain_ft=meters_to_feet(
                    properties.get("total_ascent")
                ),
                summary_loss_ft=meters_to_feet(
                    properties.get("total_descent")
                ),
            )
        )

    return routes


def xml_local_name(
    tag,
):
    return tag.rsplit(
        "}",
        1,
    )[-1]


def child_text(
    element,
    name,
):
    for child in element:
        if xml_local_name(
            child.tag
        ) == name:
            return child.text
    return None


def load_gpx_routes(
    path,
) -> list[ReferenceRoute]:
    root = ET.parse(
        path
    ).getroot()

    points = []

    for element in root.iter():
        if xml_local_name(
            element.tag
        ) not in {
            "trkpt",
            "rtept",
        }:
            continue

        elevation_text = child_text(
            element,
            "ele",
        )

        elevation = (
            meters_to_feet(
                elevation_text
            )
            if elevation_text
            else None
        )

        points.append(
            (
                float(element.attrib["lon"]),
                float(element.attrib["lat"]),
                elevation,
            )
        )

    if len(points) < 2:
        return []

    return [
        ReferenceRoute(
            path=str(path),
            title=Path(path).stem,
            source_format="gpx",
            points=points,
        )
    ]


def parse_kml_coordinate_text(
    text,
) -> list[tuple[float, float, float | None]]:
    points = []

    for token in re.split(
        r"\s+",
        text.strip(),
    ):
        parts = token.split(",")

        if len(parts) < 2:
            continue

        elevation = (
            meters_to_feet(parts[2])
            if len(parts) > 2
            and parts[2] != ""
            else None
        )

        points.append(
            (
                float(parts[0]),
                float(parts[1]),
                elevation,
            )
        )

    return points


def load_kml_routes(
    path,
) -> list[ReferenceRoute]:
    root = ET.parse(
        path
    ).getroot()
    routes = []

    for element in root.iter():
        if xml_local_name(
            element.tag
        ) != "coordinates":
            continue

        if not element.text:
            continue

        points = parse_kml_coordinate_text(
            element.text
        )

        if len(points) < 2:
            continue

        routes.append(
            ReferenceRoute(
                path=str(path),
                title=Path(path).stem,
                source_format="kml",
                points=points,
            )
        )

    return routes


def load_reference_routes(
    path,
) -> list[ReferenceRoute]:
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix in {
        ".geojson",
        ".json",
    }:
        return load_geojson_routes(
            path
        )

    if suffix == ".gpx":
        return load_gpx_routes(
            path
        )

    if suffix == ".kml":
        return load_kml_routes(
            path
        )

    return []


def parse_optional_float(
    value,
):
    if value is None:
        return None

    value = str(value).strip()

    if value == "":
        return None

    return float(value)


def clean_manifest_key(
    key,
):
    return (
        key
        .replace("\ufeff", "")
        .strip()
    )


def normalize_reference_name(
    value,
):
    return re.sub(
        r"[^a-z0-9]+",
        "",
        str(value).lower(),
    )


def load_calibration_manifest(
    path,
) -> list[CalibrationManifestRow]:
    manifest_path = Path(path)
    rows = []

    with manifest_path.open(
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle
        )

        for raw_row in reader:
            row = {
                clean_manifest_key(key): value
                for key, value in raw_row.items()
            }

            name = (
                row.get("name")
                or row.get("route")
                or row.get("segment")
            )

            if not name:
                continue

            rows.append(
                CalibrationManifestRow(
                    name=name.strip(),
                    start_mile=float(
                        row["start_mile"]
                    ),
                    stop_mile=float(
                        row["stop_mile"]
                    ),
                    reference_gain_ft=(
                        parse_optional_float(
                            row.get(
                                "reference_gain_ft"
                            )
                        )
                    ),
                    reference_distance_miles=(
                        parse_optional_float(
                            row.get(
                                "reference_distance_miles"
                            )
                        )
                    ),
                    source_tool=(
                        row.get("source_tool")
                        or ""
                    ).strip(),
                    notes=(
                        row.get("notes")
                        or ""
                    ).strip(),
                    file=(
                        row.get("file")
                        or None
                    ),
                )
            )

    return rows


def find_manifest_reference_file(
    manifest_path,
    manifest_row,
) -> Path | None:
    manifest_dir = Path(
        manifest_path
    ).parent

    if manifest_row.file:
        candidate = Path(
            manifest_row.file
        )

        if not candidate.is_absolute():
            candidate = (
                manifest_dir / candidate
            )

        if candidate.exists():
            return candidate

        return None

    row_name = normalize_reference_name(
        manifest_row.name
    )

    for candidate in sorted(
        manifest_dir.iterdir()
    ):
        if candidate.suffix.lower() not in {
            ".geojson",
            ".json",
            ".gpx",
            ".kml",
        }:
            continue

        if (
            normalize_reference_name(
                candidate.stem
            )
            == row_name
        ):
            return candidate

    return None


def load_first_reference_route(
    path,
) -> ReferenceRoute | None:
    if path is None:
        return None

    routes = load_reference_routes(
        path
    )

    if not routes:
        return None

    return routes[0]


def preferred_reference_value(
    manifest_value,
    route_summary,
    summary_key,
    smoothed_key=None,
):
    if manifest_value is not None:
        return (
            manifest_value,
            "manifest",
        )

    if (
        route_summary
        and route_summary.get(summary_key)
        is not None
    ):
        return (
            route_summary[summary_key],
            "route_summary",
        )

    if (
        smoothed_key
        and route_summary
        and route_summary.get(smoothed_key)
        is not None
    ):
        return (
            route_summary[smoothed_key],
            "route_smoothed",
        )

    return (
        None,
        None,
    )


def classify_reference_delta(
    delta_ft,
    delta_percent,
    pass_delta_ft=250,
    pass_delta_percent=10,
    warn_delta_ft=500,
    warn_delta_percent=20,
):
    if delta_ft is None:
        return "unknown"

    absolute_delta = abs(
        delta_ft
    )
    absolute_percent = (
        abs(delta_percent)
        if delta_percent is not None
        else None
    )

    if (
        absolute_delta <= pass_delta_ft
        or (
            absolute_percent is not None
            and absolute_percent
            <= pass_delta_percent
        )
    ):
        return "pass"

    if (
        absolute_delta <= warn_delta_ft
        or (
            absolute_percent is not None
            and absolute_percent
            <= warn_delta_percent
        )
    ):
        return "warn"

    return "fail"


def infer_cairn_interval(
    route,
    planner,
) -> tuple[float, float] | None:
    title = route.title.lower()
    mainline_max = (
        planner.guidebook_mainline_range()[1]
    )

    if "longtrailcenterline" in title:
        if "sobo" in title:
            return (
                mainline_max,
                0.0,
            )
        return (
            0.0,
            mainline_max,
        )

    if "northadamsapproach" in title:
        if "sobo" in title:
            return (
                0.0,
                -3.8,
            )
        return (
            -3.8,
            0.0,
        )

    return None


def compare_route_to_cairn(
    route,
    planner,
    start_mile=None,
    stop_mile=None,
    threshold_ft=DEFAULT_ELEVATION_THRESHOLD_FT,
) -> dict:
    interval = None

    if (
        start_mile is not None
        and stop_mile is not None
    ):
        interval = (
            float(start_mile),
            float(stop_mile),
        )
    else:
        interval = infer_cairn_interval(
            route,
            planner,
        )

    summary = route.summary(
        threshold_ft=threshold_ft,
    )

    if interval is None:
        summary["cairn_interval"] = None
        summary["cairn"] = None
        summary["linear_cairn"] = None
        summary["linear_terrain_interval"] = None
        summary["anchor_terrain_interval"] = None
        return summary

    terrain_stats = planner.analyze_terrain_interval(
        interval[0],
        interval[1],
    )
    linear_stats = analyze_mapped_terrain_interval(
        planner,
        interval,
        mapper="linear",
    )
    anchor_stats = analyze_mapped_terrain_interval(
        planner,
        interval,
        mapper="anchor",
    )
    reference_gain = (
        summary["summary_gain_ft"]
        if summary["summary_gain_ft"] is not None
        else summary["smoothed_gain_ft"]
    )

    gain_delta = None
    gain_delta_percent = None

    if reference_gain not in {
        None,
        0,
    }:
        gain_delta = (
            terrain_stats["elevation_gain_ft"]
            - reference_gain
        )
        gain_delta_percent = (
            gain_delta
            / reference_gain
            * 100.0
        )

    summary["cairn_interval"] = {
        "start_mile": interval[0],
        "stop_mile": interval[1],
    }
    summary["cairn"] = terrain_stats
    summary["linear_cairn"] = (
        linear_stats["stats"]
        if linear_stats
        else None
    )
    summary["linear_terrain_interval"] = (
        linear_stats["terrain_interval"]
        if linear_stats
        else None
    )
    summary["anchor_terrain_interval"] = (
        anchor_stats["terrain_interval"]
        if anchor_stats
        else None
    )
    summary["gain_delta_ft"] = round_optional(
        gain_delta,
        0,
    )
    summary["gain_delta_percent"] = round_optional(
        gain_delta_percent,
        1,
    )

    return summary


def analyze_mapped_terrain_interval(
    planner,
    interval,
    mapper,
) -> dict | None:
    start_mile, stop_mile = interval

    if mapper == "linear":
        mapper_function = (
            planner.terrain
            .map_guidebook_to_terrain_mile_linear
        )
        source = "terrain_linear"
    elif mapper == "anchor":
        mapper_function = (
            planner.terrain
            .map_guidebook_to_terrain_mile_anchor
        )
        source = "terrain_anchor"
    else:
        raise ValueError(
            f"Unknown terrain mapper: {mapper}"
        )

    terrain_start = mapper_function(
        start_mile
    )
    terrain_stop = mapper_function(
        stop_mile
    )

    if (
        terrain_start is None
        or terrain_stop is None
    ):
        return None

    stats = (
        planner.terrain.analyze_sample_interval(
            planner.load_terrain_samples(),
            terrain_start,
            terrain_stop,
            source,
            reported_distance=(
                planner.travel_distance(
                    start_mile,
                    stop_mile,
                )
            ),
        )
    )

    if stats is None:
        return None

    return {
        "terrain_interval": {
            "start_mile": round(
                terrain_start,
                3,
            ),
            "stop_mile": round(
                terrain_stop,
                3,
            ),
        },
        "stats": stats,
    }


def build_anchor_audit_report(
    trail_root,
    min_delta_ft=500,
    min_delta_percent=35,
) -> dict:
    planner = PlannerV2(
        trail_root=Path(trail_root),
    )
    anchors = (
        planner.terrain.load_terrain_mile_anchors()
    )
    intervals = []

    for left, right in zip(
        anchors,
        anchors[1:],
    ):
        start_mile = left["guidebook_mile"]
        stop_mile = right["guidebook_mile"]
        guidebook_distance = (
            planner.travel_distance(
                start_mile,
                stop_mile,
            )
        )

        if guidebook_distance < 1.0:
            continue

        linear = analyze_mapped_terrain_interval(
            planner,
            (
                start_mile,
                stop_mile,
            ),
            mapper="linear",
        )
        anchor = analyze_mapped_terrain_interval(
            planner,
            (
                start_mile,
                stop_mile,
            ),
            mapper="anchor",
        )

        if (
            linear is None
            or anchor is None
        ):
            continue

        linear_gain = linear["stats"][
            "elevation_gain_ft"
        ]
        anchor_gain = anchor["stats"][
            "elevation_gain_ft"
        ]
        delta = anchor_gain - linear_gain
        delta_percent = None

        if linear_gain:
            delta_percent = (
                delta
                / linear_gain
                * 100.0
            )

        flagged = (
            abs(delta) >= min_delta_ft
            or (
                delta_percent is not None
                and abs(delta_percent)
                >= min_delta_percent
            )
        )

        intervals.append({
            "start_mile": start_mile,
            "stop_mile": stop_mile,
            "guidebook_distance": round(
                guidebook_distance,
                2,
            ),
            "geometry_distance": round(
                abs(
                    right["terrain_mile"]
                    - left["terrain_mile"]
                ),
                2,
            ),
            "start_anchor": left["name"],
            "stop_anchor": right["name"],
            "linear_gain_ft": linear_gain,
            "anchor_gain_ft": anchor_gain,
            "delta_ft": round(
                delta,
                0,
            ),
            "delta_percent": round_optional(
                delta_percent,
                1,
            ),
            "flagged": flagged,
        })

    return {
        "anchor_count": len(anchors),
        "interval_count": len(intervals),
        "flagged_count": len([
            interval for interval in intervals
            if interval["flagged"]
        ]),
        "thresholds": {
            "min_delta_ft": min_delta_ft,
            "min_delta_percent": min_delta_percent,
        },
        "intervals": intervals,
    }


def build_calibration_report(
    paths,
    trail_root,
    start_mile=None,
    stop_mile=None,
    threshold_ft=DEFAULT_ELEVATION_THRESHOLD_FT,
) -> list[dict]:
    planner = PlannerV2(
        trail_root=Path(trail_root),
    )
    report = []

    for path in paths:
        for route in load_reference_routes(
            path
        ):
            report.append(
                compare_route_to_cairn(
                    route,
                    planner,
                    start_mile=start_mile,
                    stop_mile=stop_mile,
                    threshold_ft=threshold_ft,
                )
            )

    return report


def compare_manifest_row_to_cairn(
    manifest_row,
    manifest_path,
    planner,
    threshold_ft=DEFAULT_ELEVATION_THRESHOLD_FT,
    pass_delta_ft=250,
    pass_delta_percent=10,
    warn_delta_ft=500,
    warn_delta_percent=20,
) -> dict:
    reference_path = (
        find_manifest_reference_file(
            manifest_path,
            manifest_row,
        )
    )
    reference_route = (
        load_first_reference_route(
            reference_path
        )
    )
    route_summary = (
        reference_route.summary(
            threshold_ft=threshold_ft,
        )
        if reference_route
        else None
    )
    interval = (
        manifest_row.start_mile,
        manifest_row.stop_mile,
    )
    terrain_stats = (
        planner.analyze_terrain_interval(
            interval[0],
            interval[1],
        )
    )
    linear_stats = (
        analyze_mapped_terrain_interval(
            planner,
            interval,
            mapper="linear",
        )
    )
    anchor_stats = (
        analyze_mapped_terrain_interval(
            planner,
            interval,
            mapper="anchor",
        )
    )
    reference_gain, reference_gain_source = (
        preferred_reference_value(
            manifest_row.reference_gain_ft,
            route_summary,
            "summary_gain_ft",
            smoothed_key="smoothed_gain_ft",
        )
    )
    reference_distance, reference_distance_source = (
        preferred_reference_value(
            manifest_row.reference_distance_miles,
            route_summary,
            "summary_distance_miles",
            smoothed_key="measured_distance_miles",
        )
    )

    gain_delta = None
    gain_delta_percent = None

    if reference_gain not in {
        None,
        0,
    }:
        gain_delta = (
            terrain_stats["elevation_gain_ft"]
            - reference_gain
        )
        gain_delta_percent = (
            gain_delta
            / reference_gain
            * 100.0
        )

    status = classify_reference_delta(
        gain_delta,
        gain_delta_percent,
        pass_delta_ft=pass_delta_ft,
        pass_delta_percent=pass_delta_percent,
        warn_delta_ft=warn_delta_ft,
        warn_delta_percent=warn_delta_percent,
    )

    return {
        "name": manifest_row.name,
        "file": (
            str(reference_path)
            if reference_path
            else None
        ),
        "source_tool": manifest_row.source_tool,
        "cairn_interval": {
            "start_mile": interval[0],
            "stop_mile": interval[1],
        },
        "reference_distance_miles": (
            round_optional(
                reference_distance,
                2,
            )
        ),
        "reference_distance_source": (
            reference_distance_source
        ),
        "reference_gain_ft": (
            round_optional(
                reference_gain,
                0,
            )
        ),
        "reference_gain_source": (
            reference_gain_source
        ),
        "cairn": terrain_stats,
        "linear_cairn": (
            linear_stats["stats"]
            if linear_stats
            else None
        ),
        "linear_terrain_interval": (
            linear_stats["terrain_interval"]
            if linear_stats
            else None
        ),
        "anchor_terrain_interval": (
            anchor_stats["terrain_interval"]
            if anchor_stats
            else None
        ),
        "gain_delta_ft": round_optional(
            gain_delta,
            0,
        ),
        "gain_delta_percent": round_optional(
            gain_delta_percent,
            1,
        ),
        "status": status,
        "notes": manifest_row.notes,
        "route_summary": route_summary,
    }


def summarize_manifest_rows(
    rows,
) -> dict:
    statuses = {
        "pass": 0,
        "warn": 0,
        "fail": 0,
        "unknown": 0,
    }

    for row in rows:
        statuses[
            row.get(
                "status",
                "unknown",
            )
        ] = (
            statuses.get(
                row.get(
                    "status",
                    "unknown",
                ),
                0,
            )
            + 1
        )

    return {
        "rows": len(rows),
        **statuses,
    }


def build_manifest_calibration_report(
    manifest_path,
    trail_root,
    threshold_ft=DEFAULT_ELEVATION_THRESHOLD_FT,
    pass_delta_ft=250,
    pass_delta_percent=10,
    warn_delta_ft=500,
    warn_delta_percent=20,
) -> dict:
    manifest_path = Path(
        manifest_path
    )
    planner = PlannerV2(
        trail_root=Path(trail_root),
    )
    rows = [
        compare_manifest_row_to_cairn(
            row,
            manifest_path,
            planner,
            threshold_ft=threshold_ft,
            pass_delta_ft=pass_delta_ft,
            pass_delta_percent=pass_delta_percent,
            warn_delta_ft=warn_delta_ft,
            warn_delta_percent=warn_delta_percent,
        )
        for row in load_calibration_manifest(
            manifest_path
        )
    ]

    return {
        "manifest": str(manifest_path),
        "thresholds": {
            "pass_delta_ft": pass_delta_ft,
            "pass_delta_percent": pass_delta_percent,
            "warn_delta_ft": warn_delta_ft,
            "warn_delta_percent": warn_delta_percent,
            "smoothing_threshold_ft": threshold_ft,
        },
        "summary": summarize_manifest_rows(
            rows
        ),
        "rows": rows,
    }


def main(
    argv=None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare local elevation reference exports "
            "against CairnOS terrain intervals."
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Local GeoJSON, GPX, or KML reference files.",
    )
    parser.add_argument(
        "--trail-root",
        default="trails/vermont_long_trail",
    )
    parser.add_argument(
        "--start-mile",
        type=float,
    )
    parser.add_argument(
        "--stop-mile",
        type=float,
    )
    parser.add_argument(
        "--threshold-ft",
        type=float,
        default=DEFAULT_ELEVATION_THRESHOLD_FT,
    )
    parser.add_argument(
        "--manifest",
        help=(
            "Local calibration manifest CSV. "
            "Manifest rows define Cairn intervals and "
            "optional reference files/summary values."
        ),
    )
    parser.add_argument(
        "--audit-anchors",
        action="store_true",
        help=(
            "Report trail-wide anchor mapping deltas "
            "without requiring reference files."
        ),
    )

    args = parser.parse_args(
        argv
    )

    if args.audit_anchors:
        print(
            json.dumps(
                build_anchor_audit_report(
                    args.trail_root,
                ),
                indent=2,
            )
        )
        return 0

    if args.manifest:
        print(
            json.dumps(
                build_manifest_calibration_report(
                    args.manifest,
                    args.trail_root,
                    threshold_ft=args.threshold_ft,
                ),
                indent=2,
            )
        )
        return 0

    report = build_calibration_report(
        args.paths,
        args.trail_root,
        start_mile=args.start_mile,
        stop_mile=args.stop_mile,
        threshold_ft=args.threshold_ft,
    )

    print(
        json.dumps(
            report,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
