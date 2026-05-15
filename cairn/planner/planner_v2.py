# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import csv
import json
from statistics import mean

from cairn.runtime.graph_runtime import (
    OperationalGraphRuntime,
)

from cairn.runtime.operational_queries import (
    OperationalQueries,
)

from cairn.runtime.traversal import (
    TraversalEngine,
)

from cairn.runtime.expedition_state import (
    ExpeditionStateEngine,
)


class PlannerV2:

    def __init__(
        self,
        trail_root,
        user_profile=None,
    ):

        self.runtime = (
            OperationalGraphRuntime(
                trail_root
            )
        )

        self.queries = (
            OperationalQueries(
                self.runtime
            )
        )

        self.traversal = (
            TraversalEngine(
                self.runtime
            )
        )

        self.state_engine = (
            ExpeditionStateEngine(
                self.runtime,
                user_profile=user_profile,
            )
        )

        self.user_profile = (
            user_profile or {}
        )

        self.min_daily_miles = (
            self.user_profile.get(
                "min_daily_miles",
                8,
            )
        )

        self.max_daily_miles = (
            self.user_profile.get(
                "max_daily_miles",
                16,
            )
        )

        self.max_daily_elevation = (
            self.user_profile.get(
                "max_daily_elevation",
                3500,
            )
        )

        self.resupply_cadence = (
            self.user_profile.get(
                "resupply_cadence",
                5,
            )
        )

        self.recovery_cadence = (
            self.user_profile.get(
                "recovery_cadence",
                6,
            )
        )

        self.min_nero_miles = float(
            self.user_profile.get(
                "min_nero_miles",
                5.0,
            )
        )

        self.max_nero_miles = float(
            self.user_profile.get(
                "max_nero_miles",
                8.0,
            )
        )

        if (
            self.max_nero_miles
            < self.min_nero_miles
        ):
            self.max_nero_miles = (
                self.min_nero_miles
            )

        self.allow_extra_resupply_only = (
            self.user_profile.get(
                "allow_extra_resupply_only",
                True,
            )
        )

        self.direction = (
            self.user_profile.get(
                "direction",
                "NOBO",
            )
        )

        self.ingress_route = (
            self.user_profile.get(
                "ingress_route",
                None,
            )
        )

        self.egress_route = (
            self.user_profile.get(
                "egress_route",
                None,
            )
        )

        self.section_start = (
            self.user_profile.get(
                "section_start",
                None,
            )
        )

        self.section_end = (
            self.user_profile.get(
                "section_end",
                None,
            )
        )

        self._terrain_samples = None
        self._route_master_elevation_samples = None


    def load_terrain_samples(
        self,
    ):

        if self._terrain_samples is not None:
            return self._terrain_samples

        terrain_path = (
            self.runtime.compiled_dir /
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

        self._terrain_samples = sorted(
            samples,
            key=lambda item: item[0],
        )

        return self._terrain_samples

    def load_route_master_elevation_samples(
        self,
    ):

        if (
            self._route_master_elevation_samples
            is not None
        ):
            return (
                self
                ._route_master_elevation_samples
            )

        route_master_path = (
            self.runtime.trail_root /
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

        self._route_master_elevation_samples = (
            sorted(
                samples,
                key=lambda item: item[0],
            )
        )

        return (
            self._route_master_elevation_samples
        )

    def guidebook_mainline_range(
        self,
    ):

        route_samples = (
            self
            .load_route_master_elevation_samples()
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

    def map_guidebook_to_terrain_mile(
        self,
        guidebook_mile,
    ):

        terrain_samples = (
            self.load_terrain_samples()
        )

        if len(terrain_samples) < 2:
            return None

        guidebook_min, guidebook_max = (
            self.guidebook_mainline_range()
        )

        if (
            guidebook_mile < guidebook_min
            or guidebook_mile > guidebook_max
            or guidebook_max <= guidebook_min
        ):
            return None

        terrain_min = terrain_samples[0][0]
        terrain_max = terrain_samples[-1][0]

        ratio = (
            (guidebook_mile - guidebook_min)
            / (guidebook_max - guidebook_min)
        )

        return (
            terrain_min
            + ratio
            * (terrain_max - terrain_min)
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

        for (
            _,
            start_elevation,
        ), (
            _,
            stop_elevation,
        ) in zip(
            elevations,
            elevations[1:],
        ):

            delta = (
                stop_elevation
                - start_elevation
            )

            if delta > 0:
                elevation_gain += delta
            else:
                elevation_loss += abs(delta)

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

        distance = self.travel_distance(
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

    def analyze_terrain_interval(
        self,
        start_mile,
        stop_mile,
    ):

        distance = self.travel_distance(
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

    def is_nero_distance(
        self,
        daily_miles,
    ):

        return (
            self.min_nero_miles
            <= daily_miles
            <= self.max_nero_miles
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
                else self.mainline_southern_mile()
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
                self.min_daily_miles,
                min(
                    self.max_daily_miles,
                    base_daily_target,
                ),
            )

            probe_stop = (
                self.target_mile_for_distance(
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
            self.min_daily_miles,
            min(
                self.max_daily_miles,
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

    def classification_rank(
        self,
        classification,
    ):

        ranks = {
            "comfortable": 0,
            "challenging": 1,
            "aggressive": 2,
            "unrealistic": 3,
        }

        return ranks.get(
            classification,
            0,
        )

    def max_classification(
        self,
        first,
        second,
    ):

        if (
            self.classification_rank(
                second
            )
            > self.classification_rank(
                first
            )
        ):
            return second

        return first

    def summarize_itinerary_exceptions(
        self,
        daily_plan,
    ):

        moving_rows = [
            row for row in daily_plan
            if row.get(
                "daily_miles",
                0,
            ) > 0
        ]

        exceptions = []

        mileage_rows = [
            row for row in moving_rows
            if row.get(
                "daily_miles",
                0,
            ) > self.max_daily_miles
        ]

        if mileage_rows:

            exceptions.append({
                "constraint": "daily_miles",
                "limit": self.max_daily_miles,
                "observed_max": round(
                    max(
                        row.get(
                            "daily_miles",
                            0,
                        )
                        for row in mileage_rows
                    ),
                    1,
                ),
                "count": len(
                    mileage_rows
                ),
                "days": [
                    row.get("day")
                    for row in mileage_rows
                ],
            })

        elevation_rows = [
            row for row in moving_rows
            if row.get(
                "daily_elevation_gain",
                0,
            ) > self.max_daily_elevation
        ]

        if elevation_rows:

            exceptions.append({
                "constraint": "daily_elevation_gain",
                "limit": self.max_daily_elevation,
                "observed_max": round(
                    max(
                        row.get(
                            "daily_elevation_gain",
                            0,
                        )
                        for row in elevation_rows
                    ),
                    0,
                ),
                "count": len(
                    elevation_rows
                ),
                "days": [
                    row.get("day")
                    for row in elevation_rows
                ],
            })

        return exceptions

    def apply_itinerary_exceptions(
        self,
        completion_analysis,
        daily_plan,
    ):

        exceptions = (
            self.summarize_itinerary_exceptions(
                daily_plan
            )
        )

        if not exceptions:
            return completion_analysis

        updated = {
            **completion_analysis,
        }

        evaluation = {
            **updated.get(
                "evaluation",
                {},
            )
        }

        evaluation["classification"] = (
            self.max_classification(
                evaluation.get(
                    "classification",
                    "comfortable",
                ),
                "aggressive",
            )
        )

        evaluation["feasible"] = True

        updated["accepted"] = True
        updated["evaluation"] = evaluation
        updated["has_itinerary_exceptions"] = True
        updated["itinerary_exceptions"] = exceptions
        updated["recommendation"] = (
            "Requested completion target is achievable, but the "
            "generated itinerary exceeds one or more daily preferences "
            "to finish in the requested time."
        )
        updated["exception_guidance"] = (
            "Review exception days or adjust completion days, mileage, "
            "or elevation preferences for a gentler plan."
        )

        return updated

    def should_insert_recovery_day(
        self,
        day,
    ):

        cadence_window = [
            self.recovery_cadence - 1,
            self.recovery_cadence,
            self.recovery_cadence + 1,
        ]

        return day in cadence_window

    def build_effort_model(self):

        profiles = (
            self.traversal
            .build_effort_profile()
        )

        effort_scores = [
            p["profile"][
                "effort_score"
            ]
            for p in profiles
        ]

        total_effort = round(
            sum(effort_scores),
            2,
        )

        avg_effort = round(
            mean(effort_scores),
            2,
        )

        return {
            "segments": len(profiles),
            "total_effort": total_effort,
            "average_effort": avg_effort,
        }

    def evaluate_completion_target(
        self,
        desired_days,
    ):

        effort_model = (
            self.build_effort_model()
        )

        total_effort = effort_model[
            "total_effort"
        ]

        required_daily_effort = round(
            total_effort / desired_days,
            2,
        )

        sustainable_capacity = (
            self.max_daily_miles
        )

        ratio = (
            required_daily_effort /
            sustainable_capacity
        )

        if ratio <= 0.85:
            classification = "comfortable"
        elif ratio <= 1.0:
            classification = "challenging"
        elif ratio <= 1.25:
            classification = "aggressive"
        else:
            classification = "unrealistic"

        feasible = (
            classification != "unrealistic"
        )

        return {
            "desired_days": desired_days,
            "required_daily_effort": (
                required_daily_effort
            ),
            "sustainable_capacity": (
                sustainable_capacity
            ),
            "effort_ratio": round(
                ratio,
                2,
            ),
            "classification": classification,
            "feasible": feasible,
        }

    def negotiate_completion_target(
        self,
        desired_days,
    ):

        evaluation = (
            self.evaluate_completion_target(
                desired_days
            )
        )

        if evaluation["feasible"]:

            return {
                "accepted": True,
                "evaluation": evaluation,
                "recommendation": (
                    "Requested completion "
                    "target is operationally "
                    "feasible."
                ),
            }

        total_effort = (
            self.build_effort_model()[
                "total_effort"
            ]
        )

        sustainable_capacity = (
            self.max_daily_miles
        )

        recommended_days = round(
            total_effort /
            sustainable_capacity
        )

        recommended_days = max(
            recommended_days,
            desired_days,
        )

        return {
            "accepted": False,
            "evaluation": evaluation,
            "recommended_days": (
                recommended_days
            ),
            "recommendation": (
                "Requested completion "
                "target exceeds sustainable "
                "operational cadence."
            ),
        }

    def build_operational_forecast(
        self,
    ):

        state_profile = (
            self.state_engine
            .simulate_full_trail_state()
        )

        final_state = state_profile[-1]

        peak_fatigue = max(
            x["fatigue"]
            for x in state_profile
        )

        degraded_segments = len([
            x for x in state_profile
            if x["state"] in [
                "degraded",
                "critical",
            ]
        ])

        return {
            "segments": len(state_profile),
            "peak_fatigue": round(
                peak_fatigue,
                2,
            ),
            "final_state": final_state[
                "state"
            ],
            "degraded_segments": (
                degraded_segments
            ),
        }

    def build_expedition_summary(
        self,
        completion_days,
        daily_plan=None,
    ):

        effort_model = (
            self.build_effort_model()
        )

        total_miles = 272.0

        moving_rows = [
            row for row in (
                daily_plan or []
            )
            if row.get(
                "daily_miles",
                0,
            ) > 0
        ]

        moving_days = (
            len(moving_rows)
            or completion_days
        )

        average_daily_miles = round(
            total_miles /
            moving_days,
            1,
        )

        total_elevation_gain = (
            sum(
                row.get(
                    "daily_elevation_gain",
                    0,
                )
                for row in moving_rows
            )
            if moving_rows
            else 62129
        )

        average_daily_elevation = round(
            total_elevation_gain /
            moving_days,
            0,
        )

        return {
            "total_miles": total_miles,
            "completion_days": completion_days,
            "moving_days": moving_days,
            "average_daily_miles": average_daily_miles,
            "average_daily_elevation": average_daily_elevation,
        }

    def _resolve_ingress_node(self):
        """
        Resolve the ingress node for the selected ingress route.
        
        Honors approach trail semantics:
        - Uses runtime.get_approach_nodes() instead of hardcoded searches
        - Filters by approach_name matching ingress_route
        - Returns appropriate endpoint based on direction
        - Preserves negative mileage semantics
        
        Returns:
            dict with keys:
            - node: the resolved approach node
            - location_type: trailhead or terminus
            - mile: the cumulative_to_trail_mi value
            - location_name: canonical name for the location
            OR None if ingress route is main terminus
        """
        
        if not self.ingress_route:
            return None

        approach_nodes = (
            self.runtime
            .get_approach_nodes()
        )

        filtered_nodes = [
            n for n in approach_nodes
            if n.get("approach_name", "").strip().lower() == (
                self.ingress_route.strip().lower()
            )
        ]

        if not filtered_nodes:
            return None

        sorted_nodes = sorted(
            filtered_nodes,
            key=lambda n: n.get(
                "cumulative_to_trail_mi",
                0,
            )
        )

        if self.direction == "NOBO":
            entry_node = sorted_nodes[0]
        elif self.direction == "SOBO":
            entry_node = sorted_nodes[-1]
        else:
            entry_node = sorted_nodes[0]

        ingress_mile = round(
            entry_node.get(
                "cumulative_to_trail_mi",
                0,
            ),
            1,
        )

        approach_name = entry_node.get(
            "approach_name",
            "Approach Trail"
        )

        node_class = entry_node.get(
            "node_class",
            "trailhead"
        )

        return {
            "node": entry_node,
            "location_type": node_class,
            "mile": ingress_mile,
            "location_name": approach_name,
        }

    def load_approach_records(
        self,
    ):

        if hasattr(
            self,
            "_approach_records",
        ):
            return self._approach_records

        path = (
            self.runtime.trail_root /
            "raw" /
            "csv" /
            "approach_trails.csv"
        )

        if not path.exists():
            self._approach_records = []
            return self._approach_records

        records = []

        with open(
            path,
            newline="",
        ) as handle:

            reader = csv.DictReader(handle)

            for row in reader:

                mile = self.parse_float(
                    row.get(
                        "cumulative_to_trail_mi"
                    )
                )

                if mile is None:
                    continue

                records.append({
                    "approach_id": row.get(
                        "approach_id",
                        "",
                    ),
                    "approach_name": row.get(
                        "approach_name",
                        "",
                    ),
                    "route_name": row.get(
                        "route_name",
                        "",
                    ),
                    "location": row.get(
                        "location",
                        "",
                    ),
                    "node_class": row.get(
                        "node_class",
                        "trailhead",
                    ),
                    "mile": mile,
                    "sequence": self.parse_float(
                        row.get("sequence")
                    ),
                    "road_access": self.parse_bool(
                        row.get("road_access")
                    ),
                })

        self._approach_records = records
        return self._approach_records

    def _resolve_egress_node(self):

        if not self.egress_route:
            return None

        records = [
            row
            for row in self.load_approach_records()
            if row.get(
                "approach_name",
                "",
            ).strip().lower()
            == self.egress_route.strip().lower()
        ]

        if not records:
            return None

        if self.is_sobo():
            endpoint = min(
                records,
                key=lambda row: row.get(
                    "mile",
                    0,
                ),
            )
        else:
            endpoint = max(
                records,
                key=lambda row: row.get(
                    "mile",
                    0,
                ),
            )

        location_name = (
            endpoint.get("location")
            or endpoint.get("approach_name")
            or "Egress Trailhead"
        )

        return {
            "canonical_name": location_name,
            "trail_mile": round(
                endpoint.get("mile"),
                1,
            ),
            "node_class": endpoint.get(
                "node_class",
                "trailhead",
            ),
            "division": (
                "division0"
                if endpoint.get("mile", 0) <= 0
                else "division12"
            ),
            "egress_route": endpoint.get(
                "approach_name"
            ),
        }

    def get_directional_access(
        self,
    ):

        approach_nodes = (
            self.runtime
            .get_approach_nodes()
        )

        grouped = {}

        for node in approach_nodes:

            approach_id = node.get(
                "approach_id",
                "unknown"
            )

            if approach_id not in grouped:
                grouped[approach_id] = []

            grouped[approach_id].append(node)

        ingress = []
        egress = []

        for _, nodes in grouped.items():

            sorted_nodes = sorted(
                nodes,
                key=lambda n: n.get(
                    "cumulative_to_trail_mi",
                    0,
                )
            )

            first_node = sorted_nodes[0]
            last_node = sorted_nodes[-1]

            approach_name = first_node.get(
                "approach_name",
                "Unknown"
            )

            if self.direction == "NOBO":

                if "journey" in approach_name.lower():
                    egress.append(first_node)
                else:
                    ingress.append(first_node)

            elif self.direction == "SOBO":

                if "journey" in approach_name.lower():
                    ingress.append(first_node)
                else:
                    egress.append(first_node)

        return {
            "ingress": ingress,
            "egress": egress,
        }

    def node_mile(
        self,
        node,
    ):

        if not node:
            return None

        return node.get(
            "trail_mile",
            node.get("mile"),
        )

    def is_sobo(
        self,
    ):

        return (
            str(self.direction)
            .strip()
            .upper()
            == "SOBO"
        )

    def mainline_northern_mile(
        self,
        overlay_nodes,
    ):

        miles = [
            self.node_mile(node)
            for node in overlay_nodes
            if self.node_mile(node) is not None
        ]

        if not miles:
            return 272.0

        return round(
            max(miles),
            1,
        )

    def mainline_southern_mile(
        self,
    ):

        return 0.0

    def target_mile_for_distance(
        self,
        current_mile,
        distance,
        southern_mile,
        northern_mile,
    ):

        if self.is_sobo():
            return round(
                max(
                    southern_mile,
                    current_mile - distance,
                ),
                1,
            )

        return round(
            min(
                northern_mile,
                current_mile + distance,
            ),
            1,
        )

    def travel_distance(
        self,
        start_mile,
        stop_mile,
    ):

        return round(
            abs(stop_mile - start_mile),
            1,
        )

    def reached_route_end(
        self,
        current_mile,
        southern_mile,
        northern_mile,
    ):

        if self.is_sobo():
            return (
                current_mile <= southern_mile
            )

        return (
            current_mile >= northern_mile
        )

    def is_forward_progress(
        self,
        current_mile,
        candidate_mile,
    ):

        if current_mile is None:
            return True

        if candidate_mile is None:
            return False

        if self.is_sobo():
            return candidate_mile < (
                current_mile - 0.05
            )

        return candidate_mile > (
            current_mile + 0.05
        )

    def mile_in_travel_window(
        self,
        start_mile,
        stop_mile,
        candidate_mile,
    ):

        if candidate_mile is None:
            return False

        if self.is_sobo():
            return (
                stop_mile
                <= candidate_mile
                < start_mile
            )

        return (
            start_mile
            < candidate_mile
            <= stop_mile
        )

    def extended_target_mile(
        self,
        current_mile,
        target_mile,
        southern_mile,
        northern_mile,
    ):

        if self.is_sobo():
            lower_mile = max(
                southern_mile,
                target_mile - 3.0,
                current_mile
                - self.max_daily_miles
                - 4.0,
            )

            return round(
                lower_mile,
                1,
            )

        upper_mile = min(
            northern_mile,
            target_mile + 3.0,
            current_mile
            + self.max_daily_miles
            + 4.0,
        )

        return round(
            upper_mile,
            1,
        )

    def resupply_node_id(
        self,
        node,
    ):

        return (
            node.get("resupply_amenity_id")
            or node.get("overlay_id")
            or node.get("node_id")
            or (
                f"{node.get('canonical_name')}:"
                f"{self.node_mile(node)}"
            )
        )

    def parse_bool(
        self,
        value,
    ):

        return str(
            value or ""
        ).strip().lower() in {
            "true",
            "1",
            "yes",
            "y",
        }

    def parse_float(
        self,
        value,
    ):

        try:
            return float(value)
        except (
            TypeError,
            ValueError,
        ):
            return None

    def normalize_match_tokens(
        self,
        value,
    ):

        normalized = "".join(
            char.lower()
            if char.isalnum()
            else " "
            for char in str(value or "")
        )

        return set(
            token
            for token in normalized.split()
            if token
        )

    def load_resupply_amenities(
        self,
    ):

        if hasattr(
            self,
            "_resupply_amenities",
        ):
            return self._resupply_amenities

        path = (
            self.runtime.trail_root /
            "raw" /
            "csv" /
            "resupply_amenities.csv"
        )

        if not path.exists():
            self._resupply_amenities = []
            return self._resupply_amenities

        amenities = []

        with open(
            path,
            newline="",
        ) as handle:

            reader = csv.DictReader(handle)

            for row in reader:

                trail_mile = self.parse_float(
                    row.get("trail_mile")
                )

                if trail_mile is None:
                    continue

                latitude = self.parse_float(
                    row.get("latitude")
                )

                longitude = self.parse_float(
                    row.get("longitude")
                )

                amenities.append({
                    "trail_mile": trail_mile,
                    "town_access": (
                        row.get("town_access")
                        or ""
                    ),
                    "canonical_hint": (
                        row.get("canonical_hint")
                        or ""
                    ),
                    "access_notes": (
                        row.get("access_notes")
                        or ""
                    ),
                    "grocery": self.parse_bool(
                        row.get("grocery")
                    ),
                    "post_office": self.parse_bool(
                        row.get("post_office")
                    ),
                    "outfitter": self.parse_bool(
                        row.get("outfitter")
                    ),
                    "lodging": self.parse_bool(
                        row.get("lodging")
                    ),
                    "restaurants": self.parse_bool(
                        row.get("restaurants")
                    ),
                    "zero_candidate": self.parse_bool(
                        row.get("zero_candidate")
                    ),
                    "source_name": (
                        row.get("source_name")
                        or ""
                    ),
                    "source_url": (
                        row.get("source_url")
                        or ""
                    ),
                    "latitude": latitude,
                    "longitude": longitude,
                })

        self._resupply_amenities = amenities
        return self._resupply_amenities

    def find_overlay_for_amenity(
        self,
        amenity,
        overlay_nodes,
    ):

        amenity_mile = amenity.get(
            "trail_mile"
        )

        if amenity_mile is None:
            return None

        hint_tokens = (
            self.normalize_match_tokens(
                amenity.get("canonical_hint")
            )
        )

        town_tokens = (
            self.normalize_match_tokens(
                amenity.get("town_access")
            )
        )

        candidates = []

        for node in overlay_nodes:

            node_mile = self.node_mile(node)

            if node_mile is None:
                continue

            distance = abs(
                node_mile - amenity_mile
            )

            if distance > 1.0:
                continue

            name_tokens = (
                self.normalize_match_tokens(
                    node.get("canonical_name")
                )
            )

            node_town_tokens = (
                self.normalize_match_tokens(
                    node.get("town_access")
                )
            )

            token_match = bool(
                hint_tokens & name_tokens
                or town_tokens & node_town_tokens
            )

            candidates.append({
                "node": node,
                "distance": distance,
                "token_match": token_match,
            })

        if not candidates:
            return None

        candidates = sorted(
            candidates,
            key=lambda item: (
                not item["token_match"],
                item["distance"],
            ),
        )

        return candidates[0]["node"]

    def services_from_amenity(
        self,
        amenity,
    ):

        services = []

        for service in [
            "grocery",
            "post_office",
            "outfitter",
            "lodging",
            "restaurants",
        ]:

            if amenity.get(service):
                services.append(service)

        return services

    def build_logistics_candidates(
        self,
    ):

        if hasattr(
            self,
            "_logistics_candidates",
        ):
            return self._logistics_candidates

        overlay_nodes = (
            self.queries
            .get_resupply_access_nodes()
        )

        rows = []

        amenities = (
            self.load_resupply_amenities()
        )

        if not amenities:
            self._logistics_candidates = (
                overlay_nodes
            )
            return self._logistics_candidates

        for amenity in amenities:

            overlay_node = (
                self.find_overlay_for_amenity(
                    amenity,
                    overlay_nodes,
                )
            )

            if overlay_node:
                node = dict(overlay_node)
            else:
                node = {
                    "canonical_name": (
                        amenity.get(
                            "canonical_hint"
                        )
                        or amenity.get(
                            "town_access"
                        )
                        or "Logistics Access"
                    ),
                    "trail_mile": amenity.get(
                        "trail_mile"
                    ),
                    "node_class": "logistics",
                    "division": None,
                }

            node[
                "resupply_amenity"
            ] = amenity

            node[
                "resupply_amenity_id"
            ] = (
                f"{amenity.get('canonical_hint')}:"
                f"{amenity.get('trail_mile')}"
            )

            node[
                "town_access"
            ] = (
                node.get("town_access")
                or amenity.get("town_access")
                or ""
            )

            node[
                "access_notes"
            ] = (
                node.get("access_notes")
                or amenity.get("access_notes")
                or ""
            )

            node[
                "resupply_services"
            ] = self.services_from_amenity(
                amenity
            )

            node[
                "resupply_source"
            ] = amenity.get(
                "source_name"
            )

            node[
                "resupply_source_url"
            ] = amenity.get(
                "source_url"
            )

            for key in [
                "grocery",
                "post_office",
                "outfitter",
                "lodging",
                "restaurants",
                "zero_candidate",
            ]:

                node[key] = amenity.get(
                    key,
                    False,
                )

            node["resupply"] = (
                self.is_resupply_candidate(
                    node
                )
            )

            node["recovery_candidate"] = (
                self.is_recovery_candidate(
                    node
                )
            )

            rows.append(node)

        rows = sorted(
            rows,
            key=lambda node: (
                self.node_mile(node)
                or 0
            ),
        )

        self._logistics_candidates = rows
        return self._logistics_candidates

    def is_resupply_candidate(
        self,
        node,
    ):

        amenity = node.get(
            "resupply_amenity",
            {},
        )

        services = set(
            node.get(
                "resupply_services",
                [],
            )
            or []
        )

        return bool(
            amenity.get("grocery")
            or amenity.get("post_office")
            or amenity.get("outfitter")
            or "grocery" in services
            or "post_office" in services
            or "outfitter" in services
        )

    def is_recovery_candidate(
        self,
        node,
    ):

        amenity = node.get(
            "resupply_amenity",
            {},
        )

        services = set(
            node.get(
                "resupply_services",
                [],
            )
            or []
        )

        return bool(
            amenity.get("zero_candidate")
            or amenity.get("lodging")
            or amenity.get("restaurants")
            or node.get("zero_candidate")
            or "lodging" in services
            or "restaurants" in services
        )

    def score_resupply_candidate(
        self,
        node,
    ):

        amenity = node.get(
            "resupply_amenity",
            {},
        )

        score = 0

        if amenity.get("grocery"):
            score += 100

        if amenity.get("post_office"):
            score += 35

        if amenity.get("outfitter"):
            score += 25

        if node.get("town_access"):
            score += 10

        return score

    def score_recovery_candidate(
        self,
        node,
    ):

        amenity = node.get(
            "resupply_amenity",
            {},
        )

        score = 0

        if amenity.get("zero_candidate"):
            score += 100

        if amenity.get("lodging"):
            score += 35

        if amenity.get("restaurants"):
            score += 25

        if amenity.get("grocery"):
            score += 10

        if node.get("town_access"):
            score += 5

        return score

    def select_resupply_for_day(
        self,
        start_mile,
        stop_mile,
        day,
        last_resupply_day,
        resupply_nodes,
        used_resupply_ids,
    ):

        cadence = max(
            2,
            self.resupply_cadence,
        )

        days_since_resupply = (
            day - last_resupply_day
        )

        if days_since_resupply < (
            cadence - 1
        ):
            return None

        candidates = []

        for node in resupply_nodes:

            node_id = (
                self.resupply_node_id(node)
            )

            if node_id in used_resupply_ids:
                continue

            if not self.is_resupply_candidate(
                node
            ):
                continue

            mile = self.node_mile(node)

            if mile is None:
                continue

            if not self.mile_in_travel_window(
                start_mile,
                stop_mile,
                mile,
            ):
                continue

            score = (
                self.score_resupply_candidate(
                    node
                )
            )

            candidates.append({
                "node": node,
                "score": score,
                "distance_to_stop": abs(
                    stop_mile - mile
                ),
            })

        if not candidates:
            return None

        candidates = sorted(
            candidates,
            key=lambda item: (
                abs(
                    days_since_resupply
                    - cadence
                ),
                -item["score"],
                item[
                    "distance_to_stop"
                ],
            ),
        )

        return candidates[0]["node"]

    def select_recovery_for_day(
        self,
        start_mile,
        target_mile,
        day,
        last_recovery_day,
        logistics_candidates,
        used_recovery_ids,
    ):

        cadence = max(
            3,
            self.recovery_cadence,
        )

        days_since_recovery = (
            day - last_recovery_day
        )

        if days_since_recovery < (
            cadence - 1
        ):
            return (
                None,
                None,
            )

        if self.is_sobo():
            search_stop_mile = max(
                self.mainline_southern_mile(),
                target_mile - 3.0,
                start_mile
                - self.max_daily_miles
                - 4.0,
            )
        else:
            search_stop_mile = min(
                self.mainline_northern_mile(
                    logistics_candidates
                ),
                target_mile + 3.0,
                start_mile
                + self.max_daily_miles
                + 4.0,
            )

        candidates = []

        for node in logistics_candidates:

            node_id = (
                self.resupply_node_id(node)
            )

            if node_id in used_recovery_ids:
                continue

            if not self.is_recovery_candidate(
                node
            ):
                continue

            mile = self.node_mile(node)

            if mile is None:
                continue

            if not self.mile_in_travel_window(
                start_mile,
                search_stop_mile,
                mile,
            ):
                continue

            score = (
                self.score_recovery_candidate(
                    node
                )
            )

            if score <= 0:
                continue

            amenity = node.get(
                "resupply_amenity",
                {},
            )

            candidate_distance = (
                self.travel_distance(
                    start_mile,
                    mile,
                )
            )

            candidate_kind = (
                "zero"
                if (
                    (
                        amenity.get(
                            "zero_candidate"
                        )
                        or node.get(
                            "zero_candidate"
                        )
                    )
                    and days_since_recovery
                    >= cadence
                )
                else "nero"
            )

            if (
                candidate_kind == "nero"
                and not self.is_nero_distance(
                    candidate_distance
                )
            ):
                continue

            candidates.append({
                "node": node,
                "score": score,
                "kind": candidate_kind,
                "distance_to_target": abs(
                    target_mile - mile
                ),
            })

        if not candidates:
            return (
                None,
                None,
            )

        candidates = sorted(
            candidates,
            key=lambda item: (
                abs(
                    days_since_recovery
                    - cadence
                ),
                -item["score"],
                item[
                    "distance_to_target"
                ],
            ),
        )

        selected_item = candidates[0]

        selected = selected_item["node"]
        recovery_kind = selected_item["kind"]

        return (
            selected,
            recovery_kind,
        )

    def build_logistics_note(
        self,
        resupply_node=None,
        recovery_kind=None,
    ):

        if recovery_kind == "zero":
            if resupply_node:
                return "resupply / zero"
            return "zero"

        if recovery_kind == "nero":
            if resupply_node:
                return "resupply / nero"
            return "nero"

        if resupply_node:
            return "resupply"

        return ""

    def build_resupply_note(
        self,
        resupply_node,
        day,
        last_resupply_day,
    ):

        if not resupply_node:
            return ""

        return self.build_logistics_note(
            resupply_node=resupply_node,
        )

    def build_resupply_plan(
        self,
        daily_plan=None,
    ):

        if daily_plan is not None:

            rows = []
            terminal_day = daily_plan[-1][
                "day"
            ] if daily_plan else None

            if daily_plan:

                first_day = daily_plan[0]
                start_mile = first_day.get(
                    "daily_start_mile"
                )

                matched_start = None

                for node in (
                    self.build_logistics_candidates()
                ):

                    node_mile = self.node_mile(
                        node
                    )

                    if (
                        node_mile is None
                        or start_mile is None
                    ):
                        continue

                    if abs(
                        node_mile - start_mile
                    ) <= 1.5:
                        matched_start = node
                        break

                rows.append({
                    "day": first_day.get("day"),
                    "location": first_day.get(
                        "daily_start_location"
                    ),
                    "mile": start_mile,
                    "town_access": (
                        matched_start.get(
                            "town_access"
                        )
                        if matched_start
                        else ""
                    ),
                    "access_type": first_day.get(
                        "daily_start_location_type",
                        "trailhead",
                    ),
                    "notes": "start",
                })

            for day in daily_plan:

                if (
                    terminal_day is not None
                    and day.get("day")
                    == terminal_day
                ):
                    continue

                if day.get("notes") not in [
                    "resupply",
                    "zero",
                    "nero",
                    "resupply / nero",
                    "resupply / zero",
                ]:
                    continue

                location = day.get(
                    "resupply_location"
                )

                if not location:
                    continue

                rows.append({
                    "day": day.get("day"),
                    "location": location,
                    "mile": day.get(
                        "resupply_mile"
                    ),
                    "town_access": day.get(
                        "town_access"
                    ),
                    "access_type": day.get(
                        "resupply_location_type",
                        "logistics",
                    ),
                    "notes": day.get(
                        "notes"
                    ),
                })

            for idx, row in enumerate(rows):

                if idx + 1 < len(rows):
                    row[
                        "days_to_next_resupply"
                    ] = (
                        rows[idx + 1]["day"]
                        - row["day"]
                    )
                else:
                    row[
                        "days_to_next_resupply"
                    ] = None

                if (
                    row[
                        "days_to_next_resupply"
                    ] is None
                    and terminal_day is not None
                ):
                    row[
                        "days_to_next_resupply"
                    ] = max(
                        0,
                        terminal_day
                        - row["day"],
                    )

            return rows

        resupply_nodes = (
            self.build_logistics_candidates()
        )

        rows = []

        for node in resupply_nodes:

            rows.append({
                "location": node.get(
                    "canonical_name",
                    node.get(
                        "location",
                        "Unknown"
                    )
                ),
                "mile": node.get(
                    "trail_mile",
                    "N/A"
                ),
                "town_access": node.get(
                    "town_access"
                ),
                "access_type": node.get(
                    "node_class",
                    "logistics"
                ),
                "notes": (
                    "resupply"
                ),
                "days_to_next_resupply": None,
            })

        return rows[:10]

    def select_operational_stop(
        self,
        target_mile,
        operational_overnight_nodes,
        logistics_nodes,
        current_mile=None,
    ):
        """
        Select the best operational stop near target_mile.
        
        Priority order:
        1. Shelters (highest priority for operational realism)
        2. Designated campsites
        3. Logistics nodes (town access, resupply)
        4. Other overnight nodes
        
        Only falls back to synthetic camping if no operational nodes exist nearby.
        """

        def collect_candidates(search_radius):

            candidate_nodes = []

            # Add operational overnight nodes (shelters, camps, etc.)
            for item in operational_overnight_nodes:
                node = item["node"]
                priority = item["priority"]

                mile = node.get(
                    "trail_mile",
                    node.get("mile"),
                )

                if mile is None:
                    continue

                if not self.is_forward_progress(
                    current_mile,
                    mile,
                ):
                    continue

                delta = abs(
                    mile - target_mile
                )

                if delta <= search_radius:
                    candidate_nodes.append({
                        "node": node,
                        "priority": priority,
                        "delta": delta,
                        "type": item["type"],
                    })

            # Add logistics nodes (lower priority than shelters)
            for node in logistics_nodes:
                mile = node.get(
                    "trail_mile",
                    node.get("mile"),
                )

                if mile is None:
                    continue

                if not self.is_forward_progress(
                    current_mile,
                    mile,
                ):
                    continue

                delta = abs(
                    mile - target_mile
                )

                if delta <= search_radius:
                    candidate_nodes.append({
                        "node": node,
                        "priority": 4,
                        "delta": delta,
                        "type": "logistics",
                    })

            return candidate_nodes

        candidate_nodes = collect_candidates(4)

        if not candidate_nodes:
            candidate_nodes = collect_candidates(8)

        if not candidate_nodes:
            return None

        # Sort by priority (lower number = higher priority), then by delta
        candidate_nodes = sorted(
            candidate_nodes,
            key=lambda x: (x["priority"], x["delta"])
        )

        return candidate_nodes[0]["node"]

    def build_daily_itinerary(
        self,
        completion_days,
    ):

        overlay_nodes = sorted(
            self.queries
            .list_overlay_progression(),
            key=lambda x: x.get(
                "trail_mile",
                0,
            )
        )

        logistics_candidates = (
            self.build_logistics_candidates()
        )

        resupply_nodes = (
            logistics_candidates
        )

        logistics_nodes = (
            logistics_candidates
            or (
                self.queries
                .get_logistics_access_nodes()
            )
        )

        egress_node = (
            self._resolve_egress_node()
        )

        if egress_node:
            logistics_nodes = [
                *logistics_nodes,
                egress_node,
            ]

        operational_overnight_nodes = (
            self.queries
            .get_operational_overnight_nodes()
        )

        rows = []

        southern_mile = (
            self.mainline_southern_mile()
        )

        northern_mile = (
            self.mainline_northern_mile(
                overlay_nodes
            )
        )

        total_miles = (
            northern_mile - southern_mile
        )

        base_daily_target = (
            total_miles /
            completion_days
        )

        current_mile = 0.0
        current_location = "Southern Terminus"
        current_location_type = "terminus"
        current_division = "division1"

        if self.is_sobo():

            northern_node = max(
                overlay_nodes,
                key=lambda node: (
                    self.node_mile(node)
                    or southern_mile
                ),
            )

            current_mile = northern_mile
            current_location = northern_node.get(
                "canonical_name",
                "Northern Terminus",
            )
            current_location_type = (
                northern_node.get(
                    "node_class",
                    "terminus",
                )
            )
            current_division = northern_node.get(
                "division",
                "division12",
            )

        terminal_mile = (
            southern_mile
            if self.is_sobo()
            else northern_mile
        )

        if (
            egress_node
        ):
            terminal_mile = (
                self.node_mile(
                    egress_node
                )
                or terminal_mile
            )

        last_resupply_day = 0
        last_recovery_day = 0
        used_resupply_ids = set()
        used_recovery_ids = set()

        ingress_resolved = (
            self._resolve_ingress_node()
        )

        if ingress_resolved:

            ingress_mile = (
                ingress_resolved["mile"]
            )

            ingress_location_name = (
                ingress_resolved["location_name"]
            )

            ingress_location_type = (
                ingress_resolved["location_type"]
            )

            current_mile = ingress_mile

            current_location = ingress_location_name

            current_location_type = (
                ingress_location_type
            )

            ingress_node = (
                ingress_resolved["node"]
            )

            current_division = ingress_node.get(
                "division",
                current_division,
            )

        day = 1

        while day <= completion_days:

            daily_target = (
                self.calculate_terrain_adjusted_target(
                    base_daily_target,
                    day,
                    current_mile=current_mile,
                    southern_mile=min(
                        southern_mile,
                        terminal_mile,
                    ),
                    northern_mile=max(
                        northern_mile,
                        terminal_mile,
                    ),
                )
            )

            remaining_distance = (
                self.travel_distance(
                    current_mile,
                    terminal_mile,
                )
            )

            remaining_days = max(
                1,
                completion_days - day + 1,
            )

            required_daily_target = round(
                remaining_distance /
                remaining_days,
                1,
            )

            daily_target = round(
                min(
                    self.max_daily_miles,
                    max(
                        daily_target,
                        required_daily_target,
                    ),
                ),
                1,
            )

            if (
                egress_node
                and day == completion_days
            ):
                daily_target = (
                    self.travel_distance(
                        current_mile,
                        terminal_mile,
                    )
                )

            target_mile = (
                self.target_mile_for_distance(
                    current_mile,
                    daily_target,
                    min(
                        southern_mile,
                        terminal_mile,
                    ),
                    max(
                        northern_mile,
                        terminal_mile,
                    ),
                )
            )

            resupply_search_mile = (
                self.extended_target_mile(
                    current_mile,
                    target_mile,
                    min(
                        southern_mile,
                        terminal_mile,
                    ),
                    max(
                        northern_mile,
                        terminal_mile,
                    ),
                )
            )

            recovery_node, recovery_kind = (
                (
                    None,
                    None,
                )
                if (
                    day == completion_days
                    or (
                        self.is_sobo()
                        and egress_node
                        and target_mile <= terminal_mile
                    )
                    or (
                        not self.is_sobo()
                        and egress_node
                        and target_mile >= terminal_mile
                    )
                )
                else self.select_recovery_for_day(
                    current_mile,
                    target_mile,
                    day,
                    last_recovery_day,
                    logistics_candidates,
                    used_recovery_ids,
                )
            )

            planned_resupply_stop = None

            if (
                not recovery_node
                and self.allow_extra_resupply_only
                and day < completion_days
            ):
                planned_resupply_stop = (
                    self.select_resupply_for_day(
                        current_mile,
                        resupply_search_mile,
                        day,
                        last_resupply_day,
                        resupply_nodes,
                        used_resupply_ids,
                    )
                )

            if recovery_node:
                selected_stop = recovery_node
            elif planned_resupply_stop:
                selected_stop = planned_resupply_stop
            elif (
                egress_node
                and (
                    (
                        self.is_sobo()
                        and target_mile <= terminal_mile
                    )
                    or (
                        not self.is_sobo()
                        and target_mile >= terminal_mile
                    )
                )
            ):
                selected_stop = egress_node
            else:
                selected_stop = (
                    self.select_operational_stop(
                        target_mile,
                        operational_overnight_nodes,
                        logistics_nodes,
                        current_mile=current_mile,
                    )
                )

            if selected_stop:

                next_mile = round(
                    self.node_mile(
                        selected_stop
                    )
                    or target_mile,
                    1,
                )

                if selected_stop.get(
                    "canonical_name"
                ):

                    stop_location = selected_stop.get(
                        "canonical_name"
                    )

                    stop_location_type = (
                        selected_stop.get(
                            "node_class",
                            "overnight",
                        )
                    )

                    stop_division = (
                        selected_stop.get(
                            "division",
                            current_division,
                        )
                        or current_division
                    )

                else:

                    matching_overlay = next(
                        (
                            node
                            for node in overlay_nodes
                            if abs(
                                node.get(
                                    "trail_mile",
                                    0,
                                ) - next_mile
                            ) <= 1.0
                        ),
                        None,
                    )

                    if matching_overlay:

                        stop_location = matching_overlay.get(
                            "canonical_name",
                            "Operational Stop",
                        )

                        stop_location_type = (
                            matching_overlay.get(
                                "node_class",
                                "overnight",
                            )
                        )

                        stop_division = (
                            matching_overlay.get(
                                "division",
                                current_division,
                            )
                        )

                    else:

                        stop_location = selected_stop.get(
                            "location",
                            "Operational Stop",
                        )

                        stop_location_type = (
                            selected_stop.get(
                                "node_class",
                                "overnight",
                            )
                        )

                        stop_division = current_division

            else:

                next_mile = target_mile
                stop_location = "Backcountry Camp"
                stop_location_type = "camp"
                stop_division = current_division

            daily_distance = (
                self.travel_distance(
                    current_mile,
                    next_mile,
                )
            )

            terrain_stats = (
                self.analyze_terrain_interval(
                    current_mile,
                    next_mile,
                )
            )

            elevation_variation = (
                terrain_stats[
                    "elevation_gain_ft"
                ]
            )

            resupply_node = None

            if (
                recovery_node
                and recovery_kind == "nero"
                and self.is_resupply_candidate(
                    recovery_node
                )
            ):
                resupply_node = recovery_node

            elif (
                planned_resupply_stop
            ):
                resupply_node = planned_resupply_stop

            elif (
                not recovery_node
                and self.allow_extra_resupply_only
                and day < completion_days
            ):
                resupply_node = (
                    self.select_resupply_for_day(
                        current_mile,
                        next_mile,
                        day,
                        last_resupply_day,
                        resupply_nodes,
                        used_resupply_ids,
                    )
                )

            if (
                recovery_node
                and recovery_kind == "nero"
            ):

                used_recovery_ids.add(
                    self.resupply_node_id(
                        recovery_node
                    )
                )

                last_recovery_day = day

            notes = (
                self.build_logistics_note(
                    resupply_node=resupply_node,
                    recovery_kind=(
                        recovery_kind
                        if recovery_kind == "nero"
                        else None
                    ),
                )
            )

            food_carry_days = (
                day - last_resupply_day
            )

            resupply_location = ""
            resupply_mile = None
            resupply_location_type = ""
            town_access = ""

            if resupply_node:

                food_carry_days = 0

                last_resupply_day = day

                used_resupply_ids.add(
                    self.resupply_node_id(
                        resupply_node
                    )
                )

                resupply_location = (
                    resupply_node.get(
                        "canonical_name",
                        ""
                    )
                )

                resupply_mile = round(
                    self.node_mile(
                        resupply_node
                    ),
                    1,
                )

                resupply_location_type = (
                    resupply_node.get(
                        "node_class",
                        "logistics",
                    )
                )

                town_access = (
                    resupply_node.get(
                        "town_access",
                        ""
                    )
                )

            rows.append({
                "day": day,
                "division": stop_division,
                "daily_start_mile": round(
                    current_mile,
                    1,
                ),
                "daily_start_location": (
                    current_location
                ),
                "daily_start_location_type": (
                    current_location_type
                ),
                "daily_stop_mile": next_mile,
                "daily_stop_location": (
                    stop_location
                ),
                "daily_stop_location_type": (
                    stop_location_type
                ),
                "daily_miles": daily_distance,
                "daily_elevation_gain": (
                    elevation_variation
                ),
                "resupply_location": (
                    resupply_location
                ),
                "resupply_mile": (
                    resupply_mile
                ),
                "resupply_location_type": (
                    resupply_location_type
                ),
                "town_access": (
                    town_access
                ),
                "food_carry_days_since_last_resupply": (
                    food_carry_days
                ),
                "notes": notes,
            })

            current_mile = next_mile
            current_location = stop_location
            current_location_type = (
                stop_location_type
            )
            current_division = stop_division

            if self.reached_route_end(
                current_mile,
                terminal_mile
                if self.is_sobo()
                else southern_mile,
                terminal_mile
                if not self.is_sobo()
                else northern_mile,
            ):
                break

            if (
                recovery_node
                and recovery_kind == "zero"
                and day + 1 < completion_days
            ):

                zero_day = day + 1
                zero_resupply_node = None

                if self.is_resupply_candidate(
                    recovery_node
                ):
                    zero_resupply_node = recovery_node

                zero_notes = (
                    self.build_logistics_note(
                        resupply_node=zero_resupply_node,
                        recovery_kind="zero",
                    )
                )

                zero_food_carry_days = (
                    zero_day - last_resupply_day
                )

                zero_resupply_location = ""
                zero_resupply_mile = None
                zero_resupply_location_type = ""
                zero_town_access = ""

                if zero_resupply_node:

                    zero_food_carry_days = 0

                    last_resupply_day = zero_day

                    used_resupply_ids.add(
                        self.resupply_node_id(
                            zero_resupply_node
                        )
                    )

                    zero_resupply_location = (
                        zero_resupply_node.get(
                            "canonical_name",
                            ""
                        )
                    )

                    zero_resupply_mile = round(
                        self.node_mile(
                            zero_resupply_node
                        ),
                        1,
                    )

                    zero_resupply_location_type = (
                        zero_resupply_node.get(
                            "node_class",
                            "logistics",
                        )
                    )

                    zero_town_access = (
                        zero_resupply_node.get(
                            "town_access",
                            ""
                        )
                    )

                used_recovery_ids.add(
                    self.resupply_node_id(
                        recovery_node
                    )
                )

                last_recovery_day = zero_day

                rows.append({
                    "day": zero_day,
                    "division": current_division,
                    "daily_start_mile": round(
                        current_mile,
                        1,
                    ),
                    "daily_start_location": (
                        current_location
                    ),
                    "daily_start_location_type": (
                        current_location_type
                    ),
                    "daily_stop_mile": round(
                        current_mile,
                        1,
                    ),
                    "daily_stop_location": (
                        current_location
                    ),
                    "daily_stop_location_type": (
                        current_location_type
                    ),
                    "daily_miles": 0.0,
                    "daily_elevation_gain": 0.0,
                    "resupply_location": (
                        zero_resupply_location
                    ),
                    "resupply_mile": (
                        zero_resupply_mile
                    ),
                    "resupply_location_type": (
                        zero_resupply_location_type
                    ),
                    "town_access": (
                        zero_town_access
                    ),
                    "food_carry_days_since_last_resupply": (
                        zero_food_carry_days
                    ),
                    "notes": zero_notes,
                })

                day = zero_day

            day += 1

        return rows

    def synthesize_itinerary(
        self,
        desired_days,
    ):

        negotiation = (
            self.negotiate_completion_target(
                desired_days
            )
        )

        forecast = (
            self.build_operational_forecast()
        )

        overlay_progression = (
            self.queries
            .list_overlay_progression()
        )

        operational_overnight_nodes = (
            self.queries
            .get_operational_overnight_nodes()
        )

        logistics_nodes = (
            self.queries
            .get_logistics_access_nodes()
        )

        recommended_days = (
            negotiation.get(
                "recommended_days",
                desired_days,
            )
        )

        directional_access = (
            self.get_directional_access()
        )

        daily_plan = (
            self.build_daily_itinerary(
                recommended_days
            )
        )

        expedition_summary = (
            self.build_expedition_summary(
                recommended_days,
                daily_plan=daily_plan,
            )
        )

        completion_analysis = (
            self.apply_itinerary_exceptions(
                negotiation,
                daily_plan,
            )
        )

        resupply_plan = (
            self.build_resupply_plan(
                daily_plan
            )
        )

        return {
            "completion_analysis": (
                completion_analysis
            ),
            "expedition_summary": (
                expedition_summary
            ),
            "resupply_plan": (
                resupply_plan
            ),
            "directional_access": (
                directional_access
            ),
            "daily_plan": (
                daily_plan
            ),
        }
