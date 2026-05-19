# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import re


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

    def overnight_reference_lookup(self):

        if hasattr(
            self.planner,
            "_overnight_display_lookup",
        ):
            return self.planner._overnight_display_lookup

        payload = (
            self.queries.load_overnight_reference()
        )
        lookup = {}

        for row in payload.get(
            "matched_overnight_sites",
            [],
        ):

            for key in [
                row.get("overlay_id"),
                row.get("canonical_name"),
                row.get("title"),
            ]:

                if key:
                    lookup[
                        str(key).casefold()
                    ] = row

        self.planner._overnight_display_lookup = (
            lookup
        )
        return lookup

    def overnight_reference_for_node(
        self,
        node,
    ):

        lookup = self.overnight_reference_lookup()

        for key in [
            node.get("overlay_id"),
            node.get("canonical_name"),
            node.get("title"),
        ]:

            if not key:
                continue

            match = lookup.get(
                str(key).casefold()
            )

            if match:
                return match

        return None

    def stop_is_overnight(
        self,
        node,
    ):

        node_class = str(
            node.get("node_class", "")
        ).casefold()

        return bool(
            node_class in {
                "shelter",
                "camp",
                "campsite",
            }
            or node.get("shelter")
            or node.get("camping")
            or node.get("overnight")
        )

    def extract_overnight_display_name(
        self,
        canonical_name,
    ):

        text = str(
            canonical_name or ""
        ).strip()

        if not text:
            return (
                "",
                "",
            )

        first_part = text.split(";")[0].strip()
        access_note = ""

        if "," in first_part:
            name_part, note_part = [
                part.strip()
                for part in first_part.split(
                    ",",
                    1,
                )
            ]
            access_note = note_part
        else:
            name_part = first_part

        to_match = re.search(
            (
                r"^(?P<trail>.+?)\s+to\s+"
                r"(?P<name>.+?"
                r"(?:Shelter|Camp|Lodge|"
                r"Tenting Area|Campsite))$"
            ),
            name_part,
        )

        if to_match:
            trail_name = (
                to_match.group("trail").strip()
            )
            name_part = (
                to_match.group("name").strip()
            )

            if (
                access_note
                and " via " not in access_note
            ):
                access_note = (
                    f"{access_note} via "
                    f"{trail_name}"
                )

        return (
            name_part,
            access_note,
        )

    def display_metadata_for_stop(
        self,
        node,
        fallback_location="Operational Stop",
    ):

        canonical_name = (
            node.get("canonical_name")
            or node.get("location")
            or fallback_location
        )
        access_notes = (
            node.get("access_notes")
            or ""
        )

        if not self.stop_is_overnight(node):
            return {
                "location": canonical_name,
                "canonical_location": (
                    canonical_name
                ),
                "access_notes": access_notes,
                "spine_alignment": None,
            }

        reference = (
            self.overnight_reference_for_node(
                node
            )
            or {}
        )
        display_name = (
            reference.get("title")
            or node.get("title")
        )

        parsed_name, parsed_access = (
            self.extract_overnight_display_name(
                canonical_name
            )
        )

        if not display_name:
            display_name = (
                parsed_name or canonical_name
            )

        if not access_notes:
            access_notes = parsed_access

        spine_alignment = None
        distance_to_spine = reference.get(
            "distance_to_spine_miles"
        )

        if distance_to_spine is not None:
            spine_alignment = {
                "status": (
                    "off_spine_overnight_access"
                    if distance_to_spine > 0.03
                    else "on_spine"
                ),
                "distance_to_spine_miles": (
                    distance_to_spine
                ),
                "projected_coordinates": (
                    reference.get(
                        "projected_coordinates"
                    )
                ),
                "waypoint_coordinates": (
                    reference.get(
                        "coordinates"
                    )
                ),
            }

        return {
            "location": display_name,
            "canonical_location": canonical_name,
            "access_notes": access_notes,
            "spine_alignment": spine_alignment,
        }

    def select_operational_stop(
        self,
        target_mile,
        operational_overnight_nodes,
        logistics_nodes,
        current_mile=None,
        corridor_nodes=None,
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

        corridor_nodes = corridor_nodes or []

        def corridor_rank(
            mile,
        ):

            for index, node in enumerate(
                corridor_nodes
            ):

                node_mile = self.node_mile(
                    node
                )

                if (
                    node_mile is not None
                    and abs(
                        node_mile - mile
                    ) <= 0.15
                ):
                    return index

            return len(
                corridor_nodes
            )

        def collect_candidates(search_radius):

            candidate_nodes = []
            search_stop_mile = (
                self.target_mile_for_distance(
                    target_mile,
                    search_radius,
                    min(current_mile, target_mile)
                    if current_mile is not None
                    else target_mile - search_radius,
                    max(current_mile, target_mile)
                    if current_mile is not None
                    else target_mile + search_radius,
                )
                if current_mile is not None
                else target_mile
            )

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

                if (
                    current_mile is not None
                    and not self.mile_in_travel_window(
                        current_mile,
                        search_stop_mile,
                        mile,
                    )
                    and abs(
                        mile - target_mile
                    ) > search_radius
                ):
                    continue

                delta = abs(
                    mile - target_mile
                )

                if delta <= search_radius:
                    effective_delta = delta

                    if (
                        self.prefer_bear_box_sites
                        and node.get("bear_box")
                    ):
                        effective_delta = max(
                            0,
                            delta - 1.0,
                        )

                    candidate_nodes.append({
                        "node": node,
                        "priority": priority,
                        "delta": delta,
                        "effective_delta": (
                            effective_delta
                        ),
                        "type": item["type"],
                        "corridor_rank": corridor_rank(
                            mile
                        ),
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

                if (
                    current_mile is not None
                    and not self.mile_in_travel_window(
                        current_mile,
                        search_stop_mile,
                        mile,
                    )
                    and abs(
                        mile - target_mile
                    ) > search_radius
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
                        "effective_delta": delta,
                        "type": "logistics",
                        "corridor_rank": corridor_rank(
                            mile
                        ),
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
            key=lambda x: (
                x["priority"],
                x["effective_delta"],
                x["delta"],
                x["corridor_rank"],
            )
        )

        return candidate_nodes[0]["node"]

    def overlay_authoritative_match(
        self,
        selected_stop,
        overlay_by_name,
        current_mile=None,
    ):
        canonical_name = selected_stop.get(
            "canonical_name"
        )

        if not canonical_name:
            return None

        overlay_node = overlay_by_name.get(
            canonical_name.casefold()
        )

        if not overlay_node:
            return None

        overlay_mile = self.node_mile(
            overlay_node
        )

        if overlay_mile is None:
            return None

        if (
            current_mile is not None
            and not self.is_forward_progress(
                current_mile,
                overlay_mile,
            )
        ):
            return None

        return overlay_node

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
        overlay_by_name = {
            node.get(
                "canonical_name",
                "",
            ).casefold(): node
            for node in overlay_nodes
            if node.get("canonical_name")
        }

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
        current_canonical_location = (
            current_location
        )
        current_access_notes = ""
        current_spine_alignment = None
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
            current_canonical_location = (
                current_location
            )
            current_access_notes = (
                northern_node.get(
                    "access_notes",
                    "",
                )
                or ""
            )
            current_spine_alignment = None
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

            daily_corridor_nodes = (
                self.corridor_nodes_between(
                    current_mile,
                    resupply_search_mile,
                    include_stop=True,
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
                recovery_node
                and recovery_kind == "zero"
                and day + 1 >= completion_days
            ):
                recovery_node = None
                recovery_kind = None

            if (
                recovery_node
                and recovery_kind == "zero"
            ):
                recovery_mile = (
                    self.node_mile(
                        recovery_node
                    )
                )
                remaining_after_zero = (
                    self.travel_distance(
                        recovery_mile,
                        terminal_mile,
                    )
                    if recovery_mile is not None
                    else 0
                )
                moving_days_after_zero = max(
                    1,
                    completion_days
                    - (
                        day + 1
                    ),
                )

                if (
                    remaining_after_zero
                    / moving_days_after_zero
                    > final_day_extension_limit
                ):
                    recovery_node = None
                    recovery_kind = None

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
                        terminal_mile=terminal_mile,
                    )
                )

            if recovery_node:
                selected_stop = recovery_node
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
                        corridor_nodes=daily_corridor_nodes,
                    )
                )

                if (
                    not selected_stop
                    and planned_resupply_stop
                ):
                    selected_stop = (
                        planned_resupply_stop
                    )

            if selected_stop:
                authoritative_overlay = (
                    self.overlay_authoritative_match(
                        selected_stop,
                        overlay_by_name,
                        current_mile=current_mile,
                    )
                )
                mile_source = (
                    authoritative_overlay
                    or selected_stop
                )

                next_mile = round(
                    self.node_mile(
                        mile_source
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
                    stop_access_notes = (
                        selected_stop.get(
                            "access_notes",
                            "",
                        )
                        or ""
                    )
                    stop_canonical_location = (
                        stop_location
                    )
                    stop_spine_alignment = None

                    stop_location_type = (
                        selected_stop.get(
                            "node_class",
                            "overnight",
                        )
                    )

                    stop_division = (
                        (
                            authoritative_overlay
                            or selected_stop
                        ).get(
                            "division",
                            current_division,
                        )
                        or current_division
                    )
                    stop_bear_box = bool(
                        selected_stop.get(
                            "bear_box"
                        )
                    )

                    display_metadata = (
                        self.display_metadata_for_stop(
                            selected_stop,
                            fallback_location=(
                                stop_location
                            ),
                        )
                    )
                    stop_location = (
                        display_metadata[
                            "location"
                        ]
                    )
                    stop_canonical_location = (
                        display_metadata[
                            "canonical_location"
                        ]
                    )
                    stop_access_notes = (
                        display_metadata[
                            "access_notes"
                        ]
                    )
                    stop_spine_alignment = (
                        display_metadata[
                            "spine_alignment"
                        ]
                    )

                else:

                    matching_overlay = next(
                        (
                            node
                            for node in daily_corridor_nodes
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
                        stop_canonical_location = (
                            stop_location
                        )
                        stop_access_notes = (
                            matching_overlay.get(
                                "access_notes",
                                "",
                            )
                            or ""
                        )
                        stop_spine_alignment = None
                        stop_bear_box = bool(
                            matching_overlay.get(
                                "bear_box"
                            )
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

                        display_metadata = (
                            self.display_metadata_for_stop(
                                matching_overlay,
                                fallback_location=(
                                    stop_location
                                ),
                            )
                        )
                        stop_location = (
                            display_metadata[
                                "location"
                            ]
                        )
                        stop_canonical_location = (
                            display_metadata[
                                "canonical_location"
                            ]
                        )
                        stop_access_notes = (
                            display_metadata[
                                "access_notes"
                            ]
                        )
                        stop_spine_alignment = (
                            display_metadata[
                                "spine_alignment"
                            ]
                        )

                    else:

                        stop_location = selected_stop.get(
                            "location",
                            "Operational Stop",
                        )
                        stop_canonical_location = (
                            stop_location
                        )
                        stop_access_notes = (
                            selected_stop.get(
                                "access_notes",
                                "",
                            )
                            or ""
                        )
                        stop_spine_alignment = None
                        stop_bear_box = bool(
                            selected_stop.get(
                                "bear_box"
                            )
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
                    stop_canonical_location = (
                        stop_location
                    )
                    stop_access_notes = ""
                    stop_spine_alignment = None
                    stop_bear_box = False
                    stop_location_type = "camp"
                    stop_division = current_division

            else:

                next_mile = target_mile
                stop_location = "Backcountry Camp"
                stop_canonical_location = (
                    stop_location
                )
                stop_access_notes = ""
                stop_spine_alignment = None
                stop_bear_box = False
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
                recovery_node
                and recovery_kind == "zero"
                and day + 1 >= completion_days
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
                        terminal_mile=terminal_mile,
                    )
                )

            if (
                resupply_node
                and not recovery_kind
                and terminal_mile is not None
            ):
                resupply_mile_for_terminal = (
                    self.node_mile(
                        resupply_node
                    )
                )

                if (
                    resupply_mile_for_terminal
                    is not None
                    and self.travel_distance(
                        resupply_mile_for_terminal,
                        terminal_mile,
                    )
                    <= final_day_extension_limit
                ):
                    resupply_node = None

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
            resupply_convenience = ""

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

                resupply_convenience = (
                    resupply_node.get(
                        "resupply_convenience",
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
                "daily_start_canonical_location": (
                    current_canonical_location
                ),
                "daily_start_access_notes": (
                    current_access_notes
                ),
                "daily_start_spine_alignment": (
                    current_spine_alignment
                ),
                "daily_start_location_type": (
                    current_location_type
                ),
                "daily_stop_mile": next_mile,
                "daily_stop_location": (
                    stop_location
                ),
                "daily_stop_canonical_location": (
                    stop_canonical_location
                ),
                "daily_stop_access_notes": (
                    stop_access_notes
                ),
                "daily_stop_spine_alignment": (
                    stop_spine_alignment
                ),
                "daily_stop_bear_box": (
                    stop_bear_box
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
                "resupply_convenience": (
                    resupply_convenience
                ),
                "food_carry_days_since_last_resupply": (
                    food_carry_days
                ),
                "notes": notes,
            })

            current_mile = next_mile
            current_location = stop_location
            current_canonical_location = (
                stop_canonical_location
            )
            current_access_notes = (
                stop_access_notes
            )
            current_spine_alignment = (
                stop_spine_alignment
            )
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
                zero_resupply_convenience = ""

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

                    zero_resupply_convenience = (
                        zero_resupply_node.get(
                            "resupply_convenience",
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
                    "daily_start_canonical_location": (
                        current_canonical_location
                    ),
                    "daily_start_access_notes": (
                        current_access_notes
                    ),
                    "daily_start_spine_alignment": (
                        current_spine_alignment
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
                    "daily_stop_canonical_location": (
                        current_canonical_location
                    ),
                    "daily_stop_access_notes": (
                        current_access_notes
                    ),
                    "daily_stop_spine_alignment": (
                        current_spine_alignment
                    ),
                    "daily_stop_bear_box": (
                        bool(
                            rows[-1].get(
                                "daily_stop_bear_box"
                            )
                        )
                        if rows
                        else False
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
                    "resupply_convenience": (
                        zero_resupply_convenience
                    ),
                    "food_carry_days_since_last_resupply": (
                        zero_food_carry_days
                    ),
                    "notes": zero_notes,
                })

                day = zero_day

            day += 1

        return rows
