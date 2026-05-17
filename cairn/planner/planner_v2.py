# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import csv
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

from cairn.planner.terrain import (
    TerrainAnalyzer,
)

from cairn.planner.logistics import (
    LogisticsPlanner,
)

from cairn.planner.itinerary import (
    ItineraryBuilder,
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
        self.terrain = TerrainAnalyzer(
            self
        )
        self.logistics = LogisticsPlanner(
            self
        )
        self.itinerary_builder = ItineraryBuilder(
            self
        )


    def load_terrain_samples(
        self,
    ):
        return self.terrain.load_terrain_samples()

    def load_route_master_elevation_samples(
        self,
    ):
        return (
            self.terrain
            .load_route_master_elevation_samples()
        )

    def guidebook_mainline_range(
        self,
    ):
        return self.terrain.guidebook_mainline_range()

    def terrain_mile_range(
        self,
    ):
        return self.terrain.terrain_mile_range()

    def terrain_mile_reconciliation(
        self,
    ):
        return (
            self.terrain
            .terrain_mile_reconciliation()
        )

    def map_guidebook_to_terrain_mile(
        self,
        guidebook_mile,
    ):
        return (
            self.terrain
            .map_guidebook_to_terrain_mile(
                guidebook_mile
            )
        )

    def interpolate_elevation(
        self,
        samples,
        mile,
    ):
        return self.terrain.interpolate_elevation(
            samples,
            mile,
        )

    def analyze_sample_interval(
        self,
        samples,
        start_mile,
        stop_mile,
        source,
        reported_distance=None,
    ):
        return self.terrain.analyze_sample_interval(
            samples,
            start_mile,
            stop_mile,
            source,
            reported_distance=reported_distance,
        )

    def estimate_terrain_interval(
        self,
        start_mile,
        stop_mile,
    ):
        return self.terrain.estimate_terrain_interval(
            start_mile,
            stop_mile,
        )

    def analyze_terrain_interval(
        self,
        start_mile,
        stop_mile,
    ):
        return self.terrain.analyze_terrain_interval(
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
        return (
            self.terrain
            .calculate_terrain_adjusted_target(
                base_daily_target,
                day,
                current_mile=current_mile,
                southern_mile=southern_mile,
                northern_mile=northern_mile,
            )
        )

    def calculate_daily_elevation(
        self,
        daily_miles,
        day,
    ):
        return self.terrain.calculate_daily_elevation(
            daily_miles,
            day,
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

        updated["accepted"] = not updated.get(
            "completion_extended",
            False,
        )
        updated["evaluation"] = evaluation
        updated["has_itinerary_exceptions"] = True
        updated["itinerary_exceptions"] = exceptions

        if updated.get(
            "completion_extended",
            False,
        ):
            updated["recommendation"] = (
                "Requested completion target would require unrealistic "
                "catch-up days, so an extended itinerary was generated."
            )
            updated["exception_guidance"] = (
                "Use the recommended day count or adjust mileage, "
                "recovery, and elevation preferences for a gentler plan."
            )
        else:
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

    def apply_completion_extension(
        self,
        completion_analysis,
        actual_days,
    ):

        expected_days = (
            completion_analysis.get(
                "recommended_days"
            )
            or completion_analysis.get(
                "desired_days"
            )
            or (
                completion_analysis.get(
                    "evaluation",
                    {},
                ).get("desired_days")
            )
            or actual_days
        )

        if actual_days <= expected_days:
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

        updated["accepted"] = False
        updated["evaluation"] = evaluation
        updated["completion_extended"] = True
        updated["requested_days"] = expected_days
        updated["recommended_days"] = actual_days
        updated["extension_days"] = (
            actual_days - expected_days
        )
        updated["recommendation"] = (
            "Requested completion target would require unrealistic "
            "catch-up days, so an extended itinerary was generated."
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
        return self.logistics.resupply_node_id(
            node
        )

    def parse_bool(
        self,
        value,
    ):
        return self.logistics.parse_bool(
            value
        )

    def parse_float(
        self,
        value,
    ):
        return self.logistics.parse_float(
            value
        )

    def normalize_match_tokens(
        self,
        value,
    ):
        return self.logistics.normalize_match_tokens(
            value
        )

    def load_resupply_amenities(
        self,
    ):
        return (
            self.logistics
            .load_resupply_amenities()
        )

    def find_overlay_for_amenity(
        self,
        amenity,
        overlay_nodes,
    ):
        return (
            self.logistics
            .find_overlay_for_amenity(
                amenity,
                overlay_nodes,
            )
        )

    def services_from_amenity(
        self,
        amenity,
    ):
        return self.logistics.services_from_amenity(
            amenity
        )

    def build_logistics_candidates(
        self,
    ):
        return (
            self.logistics
            .build_logistics_candidates()
        )

    def is_resupply_candidate(
        self,
        node,
    ):
        return self.logistics.is_resupply_candidate(
            node
        )

    def is_recovery_candidate(
        self,
        node,
    ):
        return self.logistics.is_recovery_candidate(
            node
        )

    def score_resupply_candidate(
        self,
        node,
    ):
        return self.logistics.score_resupply_candidate(
            node
        )

    def score_recovery_candidate(
        self,
        node,
    ):
        return self.logistics.score_recovery_candidate(
            node
        )

    def select_resupply_for_day(
        self,
        start_mile,
        stop_mile,
        day,
        last_resupply_day,
        resupply_nodes,
        used_resupply_ids,
    ):
        return (
            self.logistics
            .select_resupply_for_day(
                start_mile,
                stop_mile,
                day,
                last_resupply_day,
                resupply_nodes,
                used_resupply_ids,
            )
        )

    def select_recovery_for_day(
        self,
        start_mile,
        target_mile,
        day,
        last_recovery_day,
        logistics_candidates,
        used_recovery_ids,
    ):
        return (
            self.logistics
            .select_recovery_for_day(
                start_mile,
                target_mile,
                day,
                last_recovery_day,
                logistics_candidates,
                used_recovery_ids,
            )
        )

    def build_logistics_note(
        self,
        resupply_node=None,
        recovery_kind=None,
    ):
        return self.logistics.build_logistics_note(
            resupply_node=resupply_node,
            recovery_kind=recovery_kind,
        )

    def build_resupply_note(
        self,
        resupply_node,
        day,
        last_resupply_day,
    ):
        return self.logistics.build_resupply_note(
            resupply_node,
            day,
            last_resupply_day,
        )

    def build_resupply_plan(
        self,
        daily_plan=None,
    ):
        return self.logistics.build_resupply_plan(
            daily_plan=daily_plan
        )

    def select_operational_stop(
        self,
        target_mile,
        operational_overnight_nodes,
        logistics_nodes,
        current_mile=None,
    ):
        return (
            self.itinerary_builder
            .select_operational_stop(
                target_mile,
                operational_overnight_nodes,
                logistics_nodes,
                current_mile=current_mile,
            )
        )

    def build_daily_itinerary(
        self,
        completion_days,
    ):
        return (
            self.itinerary_builder
            .build_daily_itinerary(
                completion_days
            )
        )

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

        actual_completion_days = (
            daily_plan[-1]["day"]
            if daily_plan
            else recommended_days
        )

        completion_analysis = (
            self.apply_completion_extension(
                negotiation,
                actual_completion_days,
            )
        )

        expedition_summary = (
            self.build_expedition_summary(
                actual_completion_days,
                daily_plan,
            )
        )

        completion_analysis = (
            self.apply_itinerary_exceptions(
                completion_analysis,
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
