# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0


class ItineraryBuilder:
    """Daily stop selection and itinerary synthesis loop for PlannerV2."""

    def __init__(
        self,
        planner,
    ):

        self.planner = planner

    def __getattr__(
        self,
        name,
    ):
        return getattr(
            self.planner,
            name,
        )

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
        max_planning_days = (
            completion_days + 60
        )

        while day <= max_planning_days:

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

            final_day_extension_limit = (
                self.max_daily_miles * 1.3
            )

            if (
                egress_node
                and day == completion_days
                and remaining_distance <= (
                    final_day_extension_limit
                )
            ):
                daily_target = remaining_distance

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
                    day >= completion_days
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

                if (
                    self.travel_distance(
                        current_mile,
                        next_mile,
                    )
                    > final_day_extension_limit
                    and not (
                        egress_node
                        and selected_stop == egress_node
                    )
                ):
                    selected_stop = None
                    next_mile = target_mile
                    stop_location = "Backcountry Camp"
                    stop_location_type = "camp"
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
            resupply_access_distance = None
            resupply_access_notes = ""

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

                resupply_access_distance = (
                    self.access_distance_miles(
                        resupply_node
                    )
                )

                resupply_access_notes = (
                    resupply_node.get(
                        "access_notes",
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
                "resupply_access_distance_miles": (
                    resupply_access_distance
                ),
                "resupply_access_notes": (
                    resupply_access_notes
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
                zero_access_distance = None
                zero_access_notes = ""

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

                    zero_access_distance = (
                        self.access_distance_miles(
                            zero_resupply_node
                        )
                    )

                    zero_access_notes = (
                        zero_resupply_node.get(
                            "access_notes",
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
                    "resupply_access_distance_miles": (
                        zero_access_distance
                    ),
                    "resupply_access_notes": (
                        zero_access_notes
                    ),
                    "food_carry_days_since_last_resupply": (
                        zero_food_carry_days
                    ),
                    "notes": zero_notes,
                })

                day = zero_day

            day += 1

        return rows
