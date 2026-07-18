# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import re

from cairn.planner.anchors import RequiredPlanningAnchorError


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
        required_anchor_mile=None,
        minimum_required_gap=0,
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
        corridor_miles = [
            self.node_mile(node)
            for node in corridor_nodes
            if self.node_mile(node) is not None
        ]

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

        def candidate_in_corridor(
            node,
        ):

            if not corridor_nodes:
                return True

            mile = self.node_mile(
                node
            )
            mile_delta = (
                0.6
                if node.get(
                    "overnight_reference"
                )
                else 0.15
            )
            reference = (
                self.resolve_overlay_reference(
                    node=node,
                    mile=mile,
                    canonical_name=node.get(
                        "canonical_name"
                    ),
                    corridor_nodes=corridor_nodes,
                    max_mile_delta=mile_delta,
                )
            )

            if reference:
                return True

            if (
                mile is None
                or not corridor_miles
            ):
                return False

            return (
                min(corridor_miles) - 0.05
                <= mile
                <= max(corridor_miles) + 0.05
            )

        def candidate_preserves_required_gap(node):
            if required_anchor_mile is None:
                return True
            mile = self.node_mile(node)
            if mile is None or abs(mile - required_anchor_mile) <= 0.15:
                return True
            if not self.is_forward_progress(mile, required_anchor_mile):
                return True
            return self.travel_distance(
                mile,
                required_anchor_mile,
            ) >= minimum_required_gap

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

                if not candidate_in_corridor(
                    node
                ):
                    continue

                if not candidate_preserves_required_gap(
                    node
                ):
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

                if not candidate_in_corridor(
                    node
                ):
                    continue

                if not candidate_preserves_required_gap(
                    node
                ):
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

    def resolve_required_overnight_nodes(
        self,
        overlay_nodes,
    ):
        nodes_by_overlay_id = {
            node.get("overlay_id"): node
            for node in overlay_nodes
            if node.get("overlay_id")
        }
        resolved = []
        for anchor in self.planning_required_overnight_anchors:
            node = nodes_by_overlay_id.get(
                anchor.get("overlay_id")
            )
            if node is None:
                raise RequiredPlanningAnchorError(
                    "Required overnight anchor cannot be resolved to current "
                    f"planner traversal data: {anchor.get('inventory_id')}"
                )
            required_node = dict(node)
            required_node["required_overnight_anchor_id"] = anchor[
                "inventory_id"
            ]
            resolved.append(required_node)
        return resolved

    def resolve_required_resupply_nodes(
        self,
        logistics_candidates,
    ):
        nodes_by_planner_id = {
            self.resupply_node_id(node): node
            for node in logistics_candidates
        }
        resolved = []
        for anchor in self.planning_required_resupply_anchors:
            node = anchor.get("planner_node") or nodes_by_planner_id.get(
                anchor.get("planner_node_id")
            )
            if node is None:
                raise RequiredPlanningAnchorError(
                    "Required resupply anchor cannot be resolved to current "
                    f"planner logistics data: {anchor.get('inventory_id')}"
                )
            required_node = dict(node)
            required_node["required_resupply_anchor_id"] = anchor[
                "inventory_id"
            ]
            required_node["required_resupply_town_name"] = anchor.get(
                "town_name",
                "",
            )
            resolved.append(required_node)
        return resolved

    def next_required_overnight_node(
        self,
        current_mile,
        required_nodes,
        satisfied_ids,
    ):
        for node in required_nodes:
            inventory_id = node["required_overnight_anchor_id"]
            if inventory_id in satisfied_ids:
                continue
            mile = self.node_mile(node)
            if mile is not None and self.is_forward_progress(
                current_mile,
                mile,
            ):
                return node
        return None

    def required_resupply_nodes_between(
        self,
        start_mile,
        stop_mile,
        required_nodes,
        satisfied_ids,
        *,
        include_start=False,
    ):
        matches = []
        for node in required_nodes:
            inventory_id = node["required_resupply_anchor_id"]
            if inventory_id in satisfied_ids:
                continue
            mile = self.node_mile(node)
            if mile is None:
                continue
            at_start = include_start and abs(mile - start_mile) <= 0.15
            if at_start or self.mile_in_travel_window(
                start_mile,
                stop_mile,
                mile,
            ):
                matches.append(node)
        return sorted(
            matches,
            key=lambda node: self.node_mile(node),
            reverse=self.is_sobo(),
        )

    def required_resupply_event(self, node):
        return {
            "required_anchor_id": node["required_resupply_anchor_id"],
            "location": node.get("canonical_name", ""),
            "mile": round(self.node_mile(node), 1),
            "town_access": (
                node.get("required_resupply_town_name")
                or node.get("town_access", "")
            ),
            "access_distance_miles": self.access_distance_miles(node),
            "access_notes": node.get("access_notes", ""),
            "resupply_convenience": node.get("resupply_convenience", ""),
            "access_type": node.get("node_class", "logistics"),
            "notes": "required resupply",
        }

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

    def overlay_authority_for_stop(
        self,
        selected_stop,
        overlay_by_name,
        current_mile=None,
        current_overlay_id=None,
        corridor_nodes=None,
    ):

        corridor_ids = {
            node.get("overlay_id")
            for node in corridor_nodes or []
            if node.get("overlay_id")
        }

        authoritative_overlay = (
            self.overlay_authoritative_match(
                selected_stop,
                overlay_by_name,
                current_mile=current_mile,
            )
        )

        if (
            authoritative_overlay
            and (
                not corridor_ids
                or authoritative_overlay.get(
                    "overlay_id"
                )
                in corridor_ids
            )
        ):
            return (
                authoritative_overlay,
                (
                    "section_extent_boundary"
                    if selected_stop.get(
                        "route_extent_boundary"
                    )
                    else "overlay"
                ),
                True,
            )

        mile = self.node_mile(
            selected_stop
        )
        max_mile_delta = 0.15

        if selected_stop.get(
            "overnight_reference"
        ):
            max_mile_delta = 0.6

        if selected_stop.get(
            "egress_route"
        ):
            max_mile_delta = 1.5

        overlay_reference = (
            self.resolve_overlay_reference(
                node=selected_stop,
                mile=mile,
                canonical_name=selected_stop.get(
                    "canonical_name"
                ),
                corridor_nodes=corridor_nodes,
                max_mile_delta=max_mile_delta,
            )
        )

        if not overlay_reference:
            return (
                None,
                "selected_operational_stop",
                False,
            )

        overlay_id = overlay_reference.get(
            "overlay_id"
        )

        if (
            current_overlay_id
            and overlay_id != current_overlay_id
            and not self.is_forward_overlay_progress(
                current_overlay_id,
                overlay_id,
            )
        ):
            return (
                None,
                "selected_operational_stop",
                False,
            )

        if selected_stop.get(
            "egress_route"
        ):
            authority = "egress_overlay_anchor"
        elif selected_stop.get(
            "overnight_reference"
        ):
            authority = "off_spine_overlay_anchor"
        else:
            authority = "overlay_mile_anchor"

        return (
            overlay_reference,
            authority,
            False,
        )

    def build_daily_itinerary(
        self,
        completion_days,
    ):

        overlay_nodes = list(
            self.traversal
            .ordered_overlay_nodes()
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

        required_resupply_nodes = (
            self.resolve_required_resupply_nodes(
                logistics_candidates
            )
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
            self.route_extent_node("end")
            if self.is_section_plan()
            else self._resolve_egress_node()
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

        required_overnight_nodes = (
            self.resolve_required_overnight_nodes(
                overlay_nodes
            )
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

        if self.is_section_plan():
            extent_start_mile = float(
                self.route_extent[
                    "canonical_start_mile"
                ]
            )
            extent_end_mile = float(
                self.route_extent[
                    "canonical_end_mile"
                ]
            )
            southern_mile = min(
                extent_start_mile,
                extent_end_mile,
            )
            northern_mile = max(
                extent_start_mile,
                extent_end_mile,
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
        current_overlay_reference = (
            self.resolve_overlay_reference(
                mile=current_mile,
                canonical_name=(
                    current_canonical_location
                ),
            )
        )
        current_overlay_id = (
            current_overlay_reference.get(
                "overlay_id"
            )
            if current_overlay_reference
            else None
        )

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
            current_overlay_id = (
                northern_node.get(
                    "overlay_id"
                )
            )

        if self.is_section_plan():
            start_node = self.route_extent_node(
                "start"
            )
            current_mile = float(
                start_node["trail_mile"]
            )
            current_location = start_node[
                "canonical_name"
            ]
            current_canonical_location = (
                current_location
            )
            current_access_notes = (
                start_node.get(
                    "access_notes",
                    "",
                )
                or ""
            )
            current_spine_alignment = None
            current_location_type = (
                start_node.get(
                    "node_class",
                    "road_crossing",
                )
            )
            current_division = start_node.get(
                "division",
                current_division,
            )
            current_overlay_id = start_node.get(
                "overlay_id"
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
        satisfied_required_overnight_ids = set()
        satisfied_required_resupply_ids = set()
        placed_zero_count = 0
        placed_nero_count = 0

        ingress_resolved = (
            None
            if self.is_section_plan()
            else self._resolve_ingress_node()
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
            current_canonical_location = (
                ingress_location_name
            )

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
            current_access_notes = (
                ingress_node.get(
                    "access_notes",
                    "",
                )
                or ""
            )
            current_spine_alignment = None

            current_overlay_reference = (
                self.resolve_overlay_reference(
                    node=ingress_node,
                    mile=ingress_mile,
                    canonical_name=(
                        ingress_location_name
                    ),
                    max_mile_delta=1.5,
                )
            )
            current_overlay_id = (
                current_overlay_reference.get(
                    "overlay_id"
                )
                if current_overlay_reference
                else None
            )

        day = 1
        max_planning_days = (
            completion_days + 60
        )

        while day <= max_planning_days:

            daily_start_overlay_id = (
                current_overlay_id
            )

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

            next_required_overnight = (
                self.next_required_overnight_node(
                    current_mile,
                    required_overnight_nodes,
                    satisfied_required_overnight_ids,
                )
            )
            required_overnight_stop = None
            if next_required_overnight:
                required_mile = self.node_mile(
                    next_required_overnight
                )
                if (
                    required_mile is not None
                    and self.mile_in_travel_window(
                        current_mile,
                        target_mile,
                        required_mile,
                    )
                ):
                    target_mile = round(required_mile, 1)
                    required_overnight_stop = (
                        next_required_overnight
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

            if (
                next_required_overnight
                and required_overnight_stop is None
            ):
                required_mile = self.node_mile(
                    next_required_overnight
                )
                if (
                    required_mile is not None
                    and self.mile_in_travel_window(
                        current_mile,
                        resupply_search_mile,
                        required_mile,
                    )
                ):
                    resupply_search_mile = round(
                        required_mile,
                        1,
                    )

            daily_corridor_nodes = (
                self.corridor_nodes_between(
                    current_mile,
                    resupply_search_mile,
                    include_stop=True,
                    start_overlay_id=(
                        current_overlay_id
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
                    completion_days=completion_days,
                    placed_zero_count=placed_zero_count,
                    placed_nero_count=placed_nero_count,
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

            if required_overnight_stop:
                selected_stop = required_overnight_stop
                recovery_node = None
                recovery_kind = None
            elif recovery_node:
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
                        required_anchor_mile=(
                            self.node_mile(
                                next_required_overnight
                            )
                            if next_required_overnight
                            else None
                        ),
                        minimum_required_gap=(
                            self.min_daily_miles
                        ),
                    )
                )

                if (
                    not selected_stop
                    and planned_resupply_stop
                ):
                    selected_stop = (
                        planned_resupply_stop
                    )

            if (
                selected_stop
                and next_required_overnight
                and selected_stop.get("overlay_id")
                == next_required_overnight.get("overlay_id")
            ):
                selected_stop = next_required_overnight

            if (
                selected_stop
                and next_required_overnight
                and selected_stop.get("overlay_id")
                != next_required_overnight.get("overlay_id")
            ):
                selected_mile = self.node_mile(
                    selected_stop
                )
                required_mile = self.node_mile(
                    next_required_overnight
                )
                if (
                    selected_mile is not None
                    and required_mile is not None
                    and self.is_forward_progress(
                        selected_mile,
                        required_mile,
                    )
                    and self.travel_distance(
                        selected_mile,
                        required_mile,
                    ) < self.min_daily_miles
                    and self.travel_distance(
                        current_mile,
                        required_mile,
                    ) <= self.max_daily_miles
                    and self.analyze_terrain_interval(
                        current_mile,
                        required_mile,
                    )["elevation_gain_ft"]
                    <= self.max_daily_elevation
                ):
                    selected_stop = next_required_overnight
                    recovery_node = None
                    recovery_kind = None

            if selected_stop:
                (
                    overlay_reference,
                    daily_traversal_authority,
                    use_overlay_mile,
                ) = self.overlay_authority_for_stop(
                        selected_stop,
                        overlay_by_name,
                        current_mile=current_mile,
                        current_overlay_id=(
                            current_overlay_id
                        ),
                        corridor_nodes=(
                            daily_corridor_nodes
                        ),
                    )
                stop_overlay_id = (
                    overlay_reference.get(
                        "overlay_id"
                    )
                    if overlay_reference
                    else None
                )
                mile_source = (
                    overlay_reference
                    if use_overlay_mile
                    else selected_stop
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

                    division_source = (
                        overlay_reference
                        or selected_stop
                    )
                    stop_division = (
                        division_source.get(
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
                        stop_overlay_id = (
                            matching_overlay.get(
                                "overlay_id"
                            )
                        )
                        daily_traversal_authority = (
                            "overlay"
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
                    synthetic_reference = (
                        self.resolve_overlay_reference(
                            mile=next_mile,
                            corridor_nodes=(
                                daily_corridor_nodes
                            ),
                            max_mile_delta=None,
                        )
                    )
                    stop_overlay_id = (
                        synthetic_reference.get(
                            "overlay_id"
                        )
                        if synthetic_reference
                        else None
                    )
                    daily_traversal_authority = (
                        "synthetic_fallback"
                    )
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
                synthetic_reference = (
                    self.resolve_overlay_reference(
                        mile=next_mile,
                        corridor_nodes=(
                            daily_corridor_nodes
                        ),
                        max_mile_delta=None,
                    )
                )
                stop_overlay_id = (
                    synthetic_reference.get(
                        "overlay_id"
                    )
                    if synthetic_reference
                    else None
                )
                daily_traversal_authority = (
                    "synthetic_fallback"
                )
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

            required_resupply_nodes_for_day = (
                self.required_resupply_nodes_between(
                    current_mile,
                    next_mile,
                    required_resupply_nodes,
                    satisfied_required_resupply_ids,
                    include_start=(day == 1),
                )
            )

            if required_resupply_nodes_for_day:
                resupply_node = required_resupply_nodes_for_day[0]

            elif (
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
                and not required_resupply_nodes_for_day
            ):
                resupply_mile_for_day = (
                    self.node_mile(
                        resupply_node
                    )
                )
                if (
                    resupply_mile_for_day is None
                    or not self.mile_in_travel_window(
                        current_mile,
                        next_mile,
                        resupply_mile_for_day,
                    )
                ):
                    resupply_node = None

            if (
                resupply_node
                and not recovery_kind
                and terminal_mile is not None
                and not required_resupply_nodes_for_day
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
                placed_nero_count += 1

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
            required_resupply_events = [
                self.required_resupply_event(node)
                for node in required_resupply_nodes_for_day
            ]

            if resupply_node:

                food_carry_days = 0

                last_resupply_day = day

                used_resupply_ids.add(
                    self.resupply_node_id(
                        resupply_node
                    )
                )

                for required_node in required_resupply_nodes_for_day:
                    satisfied_required_resupply_ids.add(
                        required_node[
                            "required_resupply_anchor_id"
                        ]
                    )
                    used_resupply_ids.add(
                        self.resupply_node_id(
                            required_node
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
                "daily_start_overlay_id": (
                    daily_start_overlay_id
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
                "daily_stop_overlay_id": (
                    stop_overlay_id
                ),
                "required_overnight_anchor_id": (
                    selected_stop.get(
                        "required_overnight_anchor_id"
                    )
                    if selected_stop
                    else None
                ),
                "daily_traversal_authority": (
                    daily_traversal_authority
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
                "required_resupply_anchors": (
                    required_resupply_events
                ),
                "food_carry_days_since_last_resupply": (
                    food_carry_days
                ),
                "notes": notes,
            })

            if (
                selected_stop
                and selected_stop.get(
                    "required_overnight_anchor_id"
                )
            ):
                satisfied_required_overnight_ids.add(
                    selected_stop[
                        "required_overnight_anchor_id"
                    ]
                )

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
            current_overlay_id = (
                stop_overlay_id
                or current_overlay_id
            )

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

                required_resupply_node_ids = {
                    self.resupply_node_id(node)
                    for node in required_resupply_nodes_for_day
                }

                if (
                    self.is_resupply_candidate(
                        recovery_node
                    )
                    and self.resupply_node_id(
                        recovery_node
                    ) not in required_resupply_node_ids
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
                placed_zero_count += 1

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
                    "daily_start_overlay_id": (
                        current_overlay_id
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
                    "daily_stop_overlay_id": (
                        current_overlay_id
                    ),
                    "required_overnight_anchor_id": None,
                    "daily_traversal_authority": (
                        "zero"
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
                    "required_resupply_anchors": [],
                    "food_carry_days_since_last_resupply": (
                        zero_food_carry_days
                    ),
                    "notes": zero_notes,
                })

                day = zero_day

            day += 1

        return rows
