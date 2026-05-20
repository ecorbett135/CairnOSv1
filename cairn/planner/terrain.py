# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import csv
import json
import math
from statistics import median


# Keep smoothing low enough to retain real rolling trail gain while still
# ignoring small DEM jitter between adjacent terrain samples.
ELEVATION_NOISE_THRESHOLD_FT = 20.0
EARTH_RADIUS_MILES = 3958.7613
ANCHOR_PROJECTION_MAX_MILES = 0.25
ANCHOR_MIN_MATCH_SCORE = 0.9


class TerrainAnalyzer:
    """Terrain and elevation calculations for PlannerV2."""

    def __init__(
        self,
        planner,
    ):

        self.planner = planner

    def load_terrain_samples(
        self,
    ):

        if self.planner._terrain_samples is not None:
            return self.planner._terrain_samples

        terrain_path = (
            self.planner.runtime.compiled_dir /
            "terrain.geojson"
        )

        samples = []

        if terrain_path.exists():

            with open(terrain_path) as handle:
                payload = json.load(handle)

            for feature in payload.get(
                "features",
                [],
            ):

                props = feature.get(
                    "properties",
                    {},
                )

                try:
                    mile = float(
                        props.get("mile")
                    )
                    elevation = float(
                        props.get(
                            "elevation_ft"
                        )
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    continue

                samples.append(
                    (
                        mile,
                        elevation,
                    )
                )

        self.planner._terrain_samples = sorted(
            samples,
            key=lambda item: item[0],
        )

        return self.planner._terrain_samples

    def load_route_master_elevation_samples(
        self,
    ):

        if (
            self.planner
            ._route_master_elevation_samples
            is not None
        ):
            return (
                self.planner
                ._route_master_elevation_samples
            )

        route_master_path = (
            self.planner.runtime.trail_root /
            "raw" /
            "csv" /
            "route_master.csv"
        )

        samples = []

        if route_master_path.exists():

            with open(
                route_master_path,
                newline="",
            ) as handle:

                reader = csv.DictReader(handle)

                for row in reader:

                    try:
                        mile = float(
                            row.get(
                                "miles_from_MA_border_nb"
                            )
                        )
                        elevation = float(
                            row.get(
                                "elevation_ft"
                            )
                        )
                    except (
                        TypeError,
                        ValueError,
                    ):
                        continue

                    samples.append(
                        (
                            mile,
                            elevation,
                        )
                    )

        self.planner._route_master_elevation_samples = (
            sorted(
                samples,
                key=lambda item: item[0],
            )
        )

        return (
            self.planner
            ._route_master_elevation_samples
        )

    def guidebook_mainline_range(
        self,
    ):

        route_samples = (
            self.load_route_master_elevation_samples()
        )

        mainline_miles = [
            mile for mile, _ in route_samples
            if mile >= 0
        ]

        if not mainline_miles:
            return (
                0.0,
                272.0,
            )

        return (
            0.0,
            max(mainline_miles),
        )

    def terrain_mile_range(
        self,
    ):

        terrain_samples = (
            self.load_terrain_samples()
        )

        if len(terrain_samples) < 2:
            return None

        return (
            terrain_samples[0][0],
            terrain_samples[-1][0],
        )

    def terrain_mile_reconciliation(
        self,
    ):

        guidebook_min, guidebook_max = (
            self.guidebook_mainline_range()
        )
        terrain_range = (
            self.terrain_mile_range()
        )

        reconciliation = {
            "guidebook_domain": (
                "northbound_reference_mainline_miles"
            ),
            "terrain_domain": (
                "compiled_geometry_sample_miles"
            ),
            "mapping": (
                "linear_mainline_domain_reconciliation"
            ),
            "guidebook_min": guidebook_min,
            "guidebook_max": guidebook_max,
            "terrain_min": None,
            "terrain_max": None,
            "guidebook_span": None,
            "terrain_span": None,
            "terrain_miles_per_guidebook_mile": None,
            "anchor_count": 0,
            "status": "unavailable",
        }

        if terrain_range is None:
            return reconciliation

        terrain_min, terrain_max = terrain_range

        reconciliation.update({
            "terrain_min": terrain_min,
            "terrain_max": terrain_max,
        })

        guidebook_span = (
            guidebook_max - guidebook_min
        )
        terrain_span = (
            terrain_max - terrain_min
        )

        reconciliation.update({
            "guidebook_span": guidebook_span,
            "terrain_span": terrain_span,
        })

        if (
            guidebook_span <= 0
            or terrain_span <= 0
        ):
            return reconciliation

        terrain_scale = (
            terrain_span / guidebook_span
        )

        reconciliation.update({
            "terrain_miles_per_guidebook_mile": terrain_scale,
            "status": "ready",
        })

        anchors = (
            self.load_terrain_mile_anchors()
        )

        if len(anchors) >= 2:
            reconciliation.update({
                "mapping": (
                    "anchor_interpolated_mainline_reconciliation"
                ),
                "anchor_count": len(anchors),
            })

        return reconciliation

    def map_guidebook_to_terrain_mile_linear(
        self,
        guidebook_mile,
    ):

        reconciliation = (
            self.terrain_mile_reconciliation()
        )

        if (
            reconciliation["status"]
            != "ready"
        ):
            return None

        guidebook_min = reconciliation[
            "guidebook_min"
        ]
        guidebook_max = reconciliation[
            "guidebook_max"
        ]

        if (
            guidebook_mile < guidebook_min
            or guidebook_mile > guidebook_max
        ):
            return None

        terrain_min = reconciliation[
            "terrain_min"
        ]
        terrain_scale = reconciliation[
            "terrain_miles_per_guidebook_mile"
        ]

        return (
            terrain_min
            + (
                guidebook_mile
                - guidebook_min
            )
            * terrain_scale
        )

    def haversine_miles(
        self,
        left,
        right,
    ):

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
            * math.asin(
                math.sqrt(h_value)
            )
        )

    def load_spine_mile_points(
        self,
    ):

        if hasattr(
            self.planner,
            "_spine_mile_points",
        ):
            return self.planner._spine_mile_points

        spine_path = (
            self.planner.runtime.compiled_dir /
            "spine.geojson"
        )

        points = []

        if spine_path.exists():
            with open(spine_path) as handle:
                payload = json.load(handle)

            features = payload.get(
                "features",
                [],
            )

            if features:
                coordinates = (
                    features[0]
                    .get("geometry", {})
                    .get("coordinates", [])
                )
            else:
                coordinates = (
                    payload
                    .get("geometry", {})
                    .get("coordinates", [])
                )

            cumulative_mile = 0.0

            for index, coordinate in enumerate(
                coordinates
            ):
                if index > 0:
                    cumulative_mile += (
                        self.haversine_miles(
                            coordinates[index - 1],
                            coordinate,
                        )
                    )

                points.append({
                    "terrain_mile": cumulative_mile,
                    "coordinates": (
                        float(coordinate[0]),
                        float(coordinate[1]),
                    ),
                })

        self.planner._spine_mile_points = points

        return points

    def project_coordinate_to_spine(
        self,
        coordinates,
    ):

        spine_points = (
            self.load_spine_mile_points()
        )

        if not spine_points:
            return None

        try:
            coordinate = (
                float(coordinates[0]),
                float(coordinates[1]),
            )
        except (
            TypeError,
            ValueError,
            IndexError,
        ):
            return None

        best_point = min(
            spine_points,
            key=lambda point: (
                self.haversine_miles(
                    coordinate,
                    point["coordinates"],
                )
            ),
        )

        projection_distance = (
            self.haversine_miles(
                coordinate,
                best_point["coordinates"],
            )
        )

        return {
            "terrain_mile": best_point[
                "terrain_mile"
            ],
            "distance_from_spine_miles": (
                projection_distance
            ),
        }

    def reference_anchor_items(
        self,
    ):

        sources = [
            (
                self.planner.runtime.compiled_dir /
                "overnight_reference.json",
                "matched_overnight_sites",
            ),
            (
                self.planner.runtime.compiled_dir /
                "waypoint_reference.json",
                "matched_waypoints",
            ),
        ]

        for path, key in sources:
            if not path.exists():
                continue

            with open(path) as handle:
                payload = json.load(handle)

            for item in payload.get(
                key,
                [],
            ):
                if item.get("deleted") is True:
                    continue

                yield {
                    "name": (
                        item.get("canonical_name")
                        or item.get("title")
                    ),
                    "guidebook_mile": (
                        item.get("trail_mile")
                    ),
                    "coordinates": item.get(
                        "coordinates"
                    ),
                    "match_score": item.get(
                        "match_score",
                        1.0,
                    ),
                    "source": path.name,
                }

        resupply_path = (
            self.planner.runtime.trail_root /
            "raw" /
            "csv" /
            "resupply_amenities.csv"
        )

        if not resupply_path.exists():
            return

        with open(
            resupply_path,
            newline="",
        ) as handle:
            reader = csv.DictReader(handle)

            for row in reader:
                if (
                    not row.get("latitude")
                    or not row.get("longitude")
                ):
                    continue

                yield {
                    "name": (
                        row.get("canonical_hint")
                        or row.get("town_access")
                    ),
                    "guidebook_mile": row.get(
                        "trail_mile"
                    ),
                    "coordinates": (
                        row.get("longitude"),
                        row.get("latitude"),
                    ),
                    "match_score": 1.0,
                    "source": (
                        "resupply_amenities.csv"
                    ),
                }

    def build_projected_anchor(
        self,
        item,
    ):

        try:
            guidebook_mile = float(
                item.get("guidebook_mile")
            )
            match_score = float(
                item.get("match_score", 1.0)
            )
        except (
            TypeError,
            ValueError,
        ):
            return None

        guidebook_min, guidebook_max = (
            self.guidebook_mainline_range()
        )

        if (
            guidebook_mile < guidebook_min
            or guidebook_mile > guidebook_max
            or match_score < ANCHOR_MIN_MATCH_SCORE
        ):
            return None

        projection = (
            self.project_coordinate_to_spine(
                item.get("coordinates")
            )
        )

        if projection is None:
            return None

        if (
            projection["distance_from_spine_miles"]
            > ANCHOR_PROJECTION_MAX_MILES
        ):
            return None

        return {
            "guidebook_mile": guidebook_mile,
            "terrain_mile": projection[
                "terrain_mile"
            ],
            "distance_from_spine_miles": (
                projection[
                    "distance_from_spine_miles"
                ]
            ),
            "name": item.get("name"),
            "source": item.get("source"),
            "match_score": match_score,
        }

    def load_terrain_mile_anchors(
        self,
    ):

        if hasattr(
            self.planner,
            "_terrain_mile_anchors",
        ):
            return self.planner._terrain_mile_anchors

        terrain_range = self.terrain_mile_range()

        if terrain_range is None:
            self.planner._terrain_mile_anchors = []
            return self.planner._terrain_mile_anchors

        guidebook_min, guidebook_max = (
            self.guidebook_mainline_range()
        )
        terrain_min, terrain_max = terrain_range

        grouped = {}

        for item in self.reference_anchor_items():
            anchor = self.build_projected_anchor(
                item
            )

            if anchor is None:
                continue

            anchor_key = round(
                anchor["guidebook_mile"],
                3,
            )
            grouped.setdefault(
                anchor_key,
                [],
            ).append(anchor)

        anchors = [
            {
                "guidebook_mile": guidebook_min,
                "terrain_mile": terrain_min,
                "distance_from_spine_miles": 0.0,
                "name": "mainline_southern_endpoint",
                "source": "terrain_endpoint",
                "match_score": 1.0,
                "sample_count": 1,
            }
        ]

        for guidebook_mile in sorted(
            grouped
        ):
            if (
                guidebook_mile == guidebook_min
                or guidebook_mile == guidebook_max
            ):
                continue

            values = grouped[
                guidebook_mile
            ]
            nearest = min(
                values,
                key=lambda item: (
                    item[
                        "distance_from_spine_miles"
                    ]
                ),
            )

            anchors.append({
                "guidebook_mile": guidebook_mile,
                "terrain_mile": median([
                    item["terrain_mile"]
                    for item in values
                ]),
                "distance_from_spine_miles": (
                    nearest[
                        "distance_from_spine_miles"
                    ]
                ),
                "name": nearest["name"],
                "source": nearest["source"],
                "match_score": nearest[
                    "match_score"
                ],
                "sample_count": len(values),
            })

        anchors.append({
            "guidebook_mile": guidebook_max,
            "terrain_mile": terrain_max,
            "distance_from_spine_miles": 0.0,
            "name": "mainline_northern_endpoint",
            "source": "terrain_endpoint",
            "match_score": 1.0,
            "sample_count": 1,
        })

        anchors = sorted(
            anchors,
            key=lambda item: item["guidebook_mile"],
        )

        monotonic_anchors = []

        for anchor in anchors:
            if (
                monotonic_anchors
                and anchor["terrain_mile"]
                <= monotonic_anchors[-1][
                    "terrain_mile"
                ]
            ):
                continue

            monotonic_anchors.append(anchor)

        self.planner._terrain_mile_anchors = (
            monotonic_anchors
        )

        return self.planner._terrain_mile_anchors

    def map_guidebook_to_terrain_mile_anchor(
        self,
        guidebook_mile,
    ):

        guidebook_min, guidebook_max = (
            self.guidebook_mainline_range()
        )

        if (
            guidebook_mile < guidebook_min
            or guidebook_mile > guidebook_max
        ):
            return None

        anchors = (
            self.load_terrain_mile_anchors()
        )

        if len(anchors) < 2:
            return None

        if guidebook_mile == guidebook_min:
            return anchors[0]["terrain_mile"]

        if guidebook_mile == guidebook_max:
            return anchors[-1]["terrain_mile"]

        for left, right in zip(
            anchors,
            anchors[1:],
        ):
            left_mile = left["guidebook_mile"]
            right_mile = right["guidebook_mile"]

            if (
                left_mile
                <= guidebook_mile
                <= right_mile
            ):
                if right_mile == left_mile:
                    return right["terrain_mile"]

                ratio = (
                    (guidebook_mile - left_mile)
                    / (right_mile - left_mile)
                )

                return (
                    left["terrain_mile"]
                    + ratio
                    * (
                        right["terrain_mile"]
                        - left["terrain_mile"]
                    )
                )

        return None

    def map_guidebook_to_terrain_mile(
        self,
        guidebook_mile,
    ):

        anchor_mile = (
            self.map_guidebook_to_terrain_mile_anchor(
                guidebook_mile
            )
        )

        if anchor_mile is not None:
            return anchor_mile

        return self.map_guidebook_to_terrain_mile_linear(
            guidebook_mile
        )

    def interpolate_elevation(
        self,
        samples,
        mile,
    ):

        if not samples:
            return None

        if mile < samples[0][0]:
            return None

        if mile > samples[-1][0]:
            return None

        for index in range(
            len(samples) - 1
        ):

            left_mile, left_elevation = (
                samples[index]
            )
            right_mile, right_elevation = (
                samples[index + 1]
            )

            if left_mile == mile:
                return left_elevation

            if (
                left_mile
                <= mile
                <= right_mile
            ):

                if right_mile == left_mile:
                    return right_elevation

                ratio = (
                    (mile - left_mile)
                    / (right_mile - left_mile)
                )

                return (
                    left_elevation
                    + ratio
                    * (
                        right_elevation
                        - left_elevation
                    )
                )

        if mile == samples[-1][0]:
            return samples[-1][1]

        return None

    def analyze_sample_interval(
        self,
        samples,
        start_mile,
        stop_mile,
        source,
        reported_distance=None,
        elevation_noise_threshold_ft=(
            ELEVATION_NOISE_THRESHOLD_FT
        ),
    ):

        if (
            not samples
            or start_mile is None
            or stop_mile is None
        ):
            return None

        if start_mile == stop_mile:
            return {
                "source": source,
                "elevation_gain_ft": 0.0,
                "elevation_loss_ft": 0.0,
                "gain_per_mile": 0.0,
                "ruggedness_score": 0.0,
            }

        low_mile = min(
            start_mile,
            stop_mile,
        )
        high_mile = max(
            start_mile,
            stop_mile,
        )

        if (
            low_mile < samples[0][0]
            or high_mile > samples[-1][0]
        ):
            return None

        points = [
            low_mile,
            *[
                mile for mile, _ in samples
                if low_mile < mile < high_mile
            ],
            high_mile,
        ]

        elevations = []

        for mile in points:
            elevation = self.interpolate_elevation(
                samples,
                mile,
            )

            if elevation is None:
                return None

            elevations.append(
                (
                    mile,
                    elevation,
                )
            )

        if start_mile > stop_mile:
            elevations = list(
                reversed(elevations)
            )

        elevation_gain = 0.0
        elevation_loss = 0.0
        accepted_elevation = elevations[0][1]

        for (
            _,
            stop_elevation,
        ) in elevations[1:]:

            delta = (
                stop_elevation
                - accepted_elevation
            )

            if (
                abs(delta)
                < elevation_noise_threshold_ft
            ):
                continue

            if delta > 0:
                elevation_gain += delta
            else:
                elevation_loss += abs(delta)

            accepted_elevation = stop_elevation

        distance = (
            reported_distance
            if reported_distance is not None
            else abs(
                stop_mile - start_mile
            )
        )

        if distance <= 0:
            gain_per_mile = 0.0
            ruggedness_score = 0.0
        else:
            gain_per_mile = (
                elevation_gain /
                distance
            )
            ruggedness_score = (
                (
                    elevation_gain
                    + elevation_loss
                )
                / distance
            )

        return {
            "source": source,
            "elevation_gain_ft": round(
                elevation_gain,
                0,
            ),
            "elevation_loss_ft": round(
                elevation_loss,
                0,
            ),
            "gain_per_mile": round(
                gain_per_mile,
                1,
            ),
            "ruggedness_score": round(
                ruggedness_score,
                1,
            ),
        }

    def estimate_terrain_interval(
        self,
        start_mile,
        stop_mile,
    ):

        distance = self.planner.travel_distance(
            start_mile,
            stop_mile,
        )

        elevation_gain = (
            distance * 240
        )

        return {
            "source": "estimated",
            "elevation_gain_ft": round(
                elevation_gain,
                0,
            ),
            "elevation_loss_ft": round(
                elevation_gain,
                0,
            ),
            "gain_per_mile": 240.0,
            "ruggedness_score": 480.0,
        }

    def split_interval_at_mainline_boundaries(
        self,
        start_mile,
        stop_mile,
    ):

        lower_bound, upper_bound = (
            self.guidebook_mainline_range()
        )

        if start_mile == stop_mile:
            return [
                (
                    start_mile,
                    stop_mile,
                )
            ]

        increasing = stop_mile > start_mile
        boundaries = []

        for boundary in (
            lower_bound,
            upper_bound,
        ):
            if (
                increasing
                and start_mile < boundary < stop_mile
            ):
                boundaries.append(boundary)
            elif (
                not increasing
                and stop_mile < boundary < start_mile
            ):
                boundaries.append(boundary)

        boundaries = sorted(
            boundaries,
            reverse=not increasing,
        )

        points = [
            start_mile,
            *boundaries,
            stop_mile,
        ]

        return list(
            zip(
                points,
                points[1:],
            )
        )

    def combine_terrain_stats(
        self,
        parts,
        reported_distance,
    ):

        if not parts:
            return None

        if len(parts) == 1:
            return parts[0]

        elevation_gain = sum(
            part["elevation_gain_ft"]
            for part in parts
        )
        elevation_loss = sum(
            part["elevation_loss_ft"]
            for part in parts
        )

        if reported_distance <= 0:
            gain_per_mile = 0.0
            ruggedness_score = 0.0
        else:
            gain_per_mile = (
                elevation_gain
                / reported_distance
            )
            ruggedness_score = (
                (
                    elevation_gain
                    + elevation_loss
                )
                / reported_distance
            )

        source_parts = [
            part["source"]
            for part in parts
        ]

        return {
            "source": "mixed",
            "source_parts": source_parts,
            "elevation_gain_ft": round(
                elevation_gain,
                0,
            ),
            "elevation_loss_ft": round(
                elevation_loss,
                0,
            ),
            "gain_per_mile": round(
                gain_per_mile,
                1,
            ),
            "ruggedness_score": round(
                ruggedness_score,
                1,
            ),
        }

    def analyze_terrain_interval_single(
        self,
        start_mile,
        stop_mile,
    ):

        distance = self.planner.travel_distance(
            start_mile,
            stop_mile,
        )

        if distance == 0:
            return {
                "source": "none",
                "elevation_gain_ft": 0.0,
                "elevation_loss_ft": 0.0,
                "gain_per_mile": 0.0,
                "ruggedness_score": 0.0,
            }

        terrain_start = (
            self.map_guidebook_to_terrain_mile(
                start_mile
            )
        )
        terrain_stop = (
            self.map_guidebook_to_terrain_mile(
                stop_mile
            )
        )

        terrain_stats = self.analyze_sample_interval(
            self.load_terrain_samples(),
            terrain_start,
            terrain_stop,
            "terrain",
            reported_distance=distance,
        )

        if terrain_stats:
            return terrain_stats

        route_stats = self.analyze_sample_interval(
            (
                self
                .load_route_master_elevation_samples()
            ),
            start_mile,
            stop_mile,
            "route_master",
            reported_distance=distance,
        )

        if route_stats:
            return route_stats

        return self.estimate_terrain_interval(
            start_mile,
            stop_mile,
        )

    def analyze_terrain_interval(
        self,
        start_mile,
        stop_mile,
    ):

        distance = self.planner.travel_distance(
            start_mile,
            stop_mile,
        )

        if distance == 0:
            return {
                "source": "none",
                "elevation_gain_ft": 0.0,
                "elevation_loss_ft": 0.0,
                "gain_per_mile": 0.0,
                "ruggedness_score": 0.0,
            }

        interval_parts = (
            self.split_interval_at_mainline_boundaries(
                start_mile,
                stop_mile,
            )
        )

        terrain_parts = [
            self.analyze_terrain_interval_single(
                part_start,
                part_stop,
            )
            for part_start, part_stop in interval_parts
        ]

        return self.combine_terrain_stats(
            terrain_parts,
            distance,
        )

    def calculate_terrain_adjusted_target(
        self,
        base_daily_target,
        day,
        current_mile=None,
        southern_mile=None,
        northern_mile=None,
    ):

        fatigue_penalty = (
            min(
                0.12,
                (day - 1) * 0.004,
            )
        )

        terrain_multiplier = 1.0

        if current_mile is not None:

            lower_bound = (
                southern_mile
                if southern_mile is not None
                else (
                    self.planner
                    .mainline_southern_mile()
                )
            )
            upper_bound = (
                northern_mile
                if northern_mile is not None
                else (
                    self.guidebook_mainline_range()
                    [1]
                )
            )

            probe_distance = max(
                self.planner.min_daily_miles,
                min(
                    self.planner.max_daily_miles,
                    base_daily_target,
                ),
            )

            probe_stop = (
                self.planner.target_mile_for_distance(
                    current_mile,
                    probe_distance,
                    lower_bound,
                    upper_bound,
                )
            )

            terrain_stats = (
                self.analyze_terrain_interval(
                    current_mile,
                    probe_stop,
                )
            )

            gain_ratio = (
                terrain_stats[
                    "gain_per_mile"
                ]
                / 240.0
            )
            ruggedness_ratio = (
                terrain_stats[
                    "ruggedness_score"
                ]
                / 500.0
            )

            terrain_burden = (
                gain_ratio * 0.65
                + ruggedness_ratio * 0.35
            )

            terrain_multiplier = max(
                0.78,
                min(
                    1.15,
                    1.0
                    - (
                        terrain_burden
                        - 1.0
                    )
                    * 0.22,
                ),
            )

        adjusted_target = (
            base_daily_target *
            terrain_multiplier *
            (1.0 - fatigue_penalty)
        )

        adjusted_target = max(
            self.planner.min_daily_miles,
            min(
                self.planner.max_daily_miles,
                adjusted_target,
            )
        )

        return round(
            adjusted_target,
            1,
        )

    def calculate_daily_elevation(
        self,
        daily_miles,
        day,
    ):

        elevation = (
            daily_miles *
            240
        )

        return round(
            elevation,
            0,
        )
