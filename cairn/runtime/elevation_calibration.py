# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""Reference elevation comparison helpers.

This module is intentionally a calibration/reporting utility. It can read local
reference exports, but it does not make vendor data operational truth.
"""

from __future__ import annotations

import argparse
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
