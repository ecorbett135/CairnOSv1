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


    def calculate_terrain_adjusted_target(
        self,
        base_daily_target,
        day,
    ):

        fatigue_penalty = (
            (day - 1) * 0.015
        )

        terrain_cycle = [
            0.92,
            1.05,
            0.88,
            1.08,
            0.95,
        ]

        terrain_multiplier = (
            terrain_cycle[
                (day - 1) % len(terrain_cycle)
            ]
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

        terrain_bias = [
            1.0,
            1.25,
            0.85,
            1.4,
            0.95,
        ]

        multiplier = terrain_bias[
            (day - 1) % len(terrain_bias)
        ]

        elevation = (
            daily_miles *
            240 *
            multiplier
        )

        elevation = min(
            elevation,
            self.max_daily_elevation,
        )

        return round(
            elevation,
            0,
        )

    def should_insert_recovery_day(
        self,
        day,
    ):

        cadence_window = [
            self.resupply_cadence - 1,
            self.resupply_cadence,
            self.resupply_cadence + 1,
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
    ):

        effort_model = (
            self.build_effort_model()
        )

        total_miles = 272.0

        average_daily_miles = round(
            total_miles /
            completion_days,
            1,
        )

        total_elevation_gain = 62129

        average_daily_elevation = round(
            total_elevation_gain /
            completion_days,
            0,
        )

        return {
            "total_miles": total_miles,
            "completion_days": completion_days,
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

    def resupply_node_id(
        self,
        node,
    ):

        return (
            node.get("overlay_id")
            or node.get("node_id")
            or (
                f"{node.get('canonical_name')}:"
                f"{self.node_mile(node)}"
            )
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

        lower_mile = min(
            start_mile,
            stop_mile,
        )

        upper_mile = max(
            start_mile,
            stop_mile,
        )

        candidates = []

        for node in resupply_nodes:

            node_id = (
                self.resupply_node_id(node)
            )

            if node_id in used_resupply_ids:
                continue

            mile = self.node_mile(node)

            if mile is None:
                continue

            if (
                mile <= lower_mile
                or mile > upper_mile
            ):
                continue

            services = (
                node.get(
                    "resupply_services",
                    []
                )
                or []
            )

            candidates.append({
                "node": node,
                "service_count": len(services),
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
                -item[
                    "service_count"
                ],
                item[
                    "distance_to_stop"
                ],
            ),
        )

        return candidates[0]["node"]

    def build_resupply_note(
        self,
        resupply_node,
        day,
        last_resupply_day,
    ):

        if not resupply_node:
            return ""

        cadence = max(
            2,
            self.resupply_cadence,
        )

        days_since_resupply = (
            day - last_resupply_day
        )

        if (
            resupply_node.get(
                "zero_candidate"
            )
            and days_since_resupply >= (
                cadence + 1
            )
        ):

            return "resupply / zero"

        return "resupply"

    def build_resupply_plan(
        self,
        daily_plan=None,
    ):

        if daily_plan is not None:

            rows = []

            for day in daily_plan:

                if day.get("notes") not in [
                    "resupply",
                    "zero",
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

            return rows

        resupply_nodes = (
            self.queries
            .get_resupply_access_nodes()
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
            })

        return rows[:10]

    def select_operational_stop(
        self,
        target_mile,
        operational_overnight_nodes,
        logistics_nodes,
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

        logistics_nodes = (
            self.queries
            .get_logistics_access_nodes()
        )

        resupply_nodes = (
            self.queries
            .get_resupply_access_nodes()
        )

        operational_overnight_nodes = (
            self.queries
            .get_operational_overnight_nodes()
        )

        rows = []

        total_miles = 272.0

        base_daily_target = (
            total_miles /
            completion_days
        )

        current_mile = 0.0
        current_location = "Southern Terminus"
        current_location_type = "terminus"
        current_division = "division1"
        last_resupply_day = 0
        used_resupply_ids = set()

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

        for day in range(1, completion_days + 1):

            daily_target = (
                self.calculate_terrain_adjusted_target(
                    base_daily_target,
                    day,
                )
            )

            target_mile = round(
                min(
                    total_miles,
                    current_mile + daily_target,
                ),
                1,
            )

            selected_stop = (
                self.select_operational_stop(
                    target_mile,
                    operational_overnight_nodes,
                    logistics_nodes,
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

            if day == 1 and current_mile < 0:

                daily_distance = round(
                    abs(current_mile) + next_mile,
                    1,
                )

            else:

                daily_distance = round(
                    next_mile - current_mile,
                    1,
                )

            elevation_variation = (
                self.calculate_daily_elevation(
                    daily_distance,
                    day,
                )
            )

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

            notes = (
                self.build_resupply_note(
                    resupply_node,
                    day,
                    last_resupply_day,
                )
            )

            resupply_location = ""
            resupply_mile = None
            resupply_location_type = ""
            town_access = ""

            if resupply_node:

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
                "notes": notes,
            })

            current_mile = next_mile
            current_location = stop_location
            current_location_type = (
                stop_location_type
            )
            current_division = stop_division

            if current_mile >= total_miles:
                break

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

        expedition_summary = (
            self.build_expedition_summary(
                recommended_days
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

        resupply_plan = (
            self.build_resupply_plan(
                daily_plan
            )
        )

        return {
            "completion_analysis": (
                negotiation
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
