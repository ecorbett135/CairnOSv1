# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import csv
import json


ELEVATION_NOISE_THRESHOLD_FT = 50.0


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

        reconciliation.update({
            "terrain_miles_per_guidebook_mile": (
                terrain_span / guidebook_span
            ),
            "status": "ready",
        })

        return reconciliation

    def map_guidebook_to_terrain_mile(
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
