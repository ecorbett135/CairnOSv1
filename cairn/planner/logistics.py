# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import csv


class LogisticsPlanner:
    """Resupply, recovery, and logistics calculations for PlannerV2."""

    def __init__(
        self,
        planner,
    ):

        object.__setattr__(
            self,
            "planner",
            planner,
        )

    def __getattr__(
        self,
        name,
    ):
        return getattr(
            self.planner,
            name,
        )

    def __setattr__(
        self,
        name,
        value,
    ):

        if name in {
            "_resupply_amenities",
            "_logistics_candidates",
        }:
            setattr(
                self.planner,
                name,
                value,
            )
            return

        object.__setattr__(
            self,
            name,
            value,
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

