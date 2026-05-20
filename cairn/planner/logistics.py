# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import csv
import re


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
            "_town_service_options",
            "_side_trip_options",
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

    def parse_access_distance_miles(
        self,
        value,
    ):

        text = str(
            value or ""
        ).lower()

        if not text:
            return None

        less_than_match = re.search(
            r"less than\s+(\d+(?:\.\d+)?)\s*mile",
            text,
        )

        if less_than_match:
            return float(
                less_than_match.group(1)
            )

        distances = [
            float(match.group(1))
            for match in re.finditer(
                r"(\d+(?:\.\d+)?)\+?\s*miles?",
                text,
            )
        ]

        if not distances:
            return None

        return min(distances)

    def format_access_notes(
        self,
        value,
    ):

        text = str(
            value or ""
        ).strip()

        if not text:
            return ""

        return re.sub(
            (
                r"\s+and\s+"
                r"(?=(?:\d|[Ll]ess than|[Aa]bout|[Mm]ore than))"
            ),
            "; ",
            text,
        )

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

                access_distance_miles = self.parse_float(
                    row.get("access_distance_miles")
                )

                if access_distance_miles is None:
                    access_distance_miles = (
                        self.parse_access_distance_miles(
                            row.get("access_notes")
                        )
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
                        self.format_access_notes(
                            row.get("access_notes")
                        )
                    ),
                    "access_distance_miles": (
                        access_distance_miles
                    ),
                    "access_distance_qualifier": (
                        row.get(
                            "access_distance_qualifier"
                        )
                        or ""
                    ),
                    "access_direction": (
                        row.get("access_direction")
                        or ""
                    ),
                    "access_mode": (
                        row.get("access_mode")
                        or ""
                    ),
                    "resupply_convenience": (
                        row.get(
                            "resupply_convenience"
                        )
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

    def is_validated_option(
        self,
        row,
    ):

        return (
            str(
                row.get("validation_status", "")
            )
            .strip()
            .casefold()
            == "validated"
        )

    def load_town_service_options(
        self,
    ):

        if hasattr(
            self,
            "_town_service_options",
        ):
            return self._town_service_options

        path = (
            self.runtime.trail_root /
            "raw" /
            "csv" /
            "town_service_options.csv"
        )

        if not path.exists():
            self._town_service_options = []
            return self._town_service_options

        options = []

        with open(
            path,
            newline="",
        ) as handle:

            reader = csv.DictReader(handle)

            for row in reader:

                if not self.is_validated_option(
                    row
                ):
                    continue

                options.append({
                    "option_id": (
                        row.get("option_id")
                        or ""
                    ),
                    "resupply_amenity_id": (
                        row.get(
                            "resupply_amenity_id"
                        )
                        or ""
                    ),
                    "town_access": (
                        row.get("town_access")
                        or ""
                    ),
                    "service_category": (
                        row.get(
                            "service_category"
                        )
                        or ""
                    ),
                    "display_name": (
                        row.get("display_name")
                        or ""
                    ),
                    "service_notes": (
                        row.get("service_notes")
                        or ""
                    ),
                    "source_name": (
                        row.get("source_name")
                        or ""
                    ),
                    "source_url": (
                        row.get("source_url")
                        or ""
                    ),
                    "validation_status": (
                        row.get(
                            "validation_status"
                        )
                        or ""
                    ),
                    "validation_source_name": (
                        row.get(
                            "validation_source_name"
                        )
                        or ""
                    ),
                    "validation_source_url": (
                        row.get(
                            "validation_source_url"
                        )
                        or ""
                    ),
                    "validation_date": (
                        row.get(
                            "validation_date"
                        )
                        or ""
                    ),
                })

        self._town_service_options = options
        return self._town_service_options

    def load_side_trip_options(
        self,
    ):

        if hasattr(
            self,
            "_side_trip_options",
        ):
            return self._side_trip_options

        path = (
            self.runtime.trail_root /
            "raw" /
            "csv" /
            "side_trip_options.csv"
        )

        if not path.exists():
            self._side_trip_options = []
            return self._side_trip_options

        options = []

        with open(
            path,
            newline="",
        ) as handle:

            reader = csv.DictReader(handle)

            for row in reader:

                if not self.is_validated_option(
                    row
                ):
                    continue

                options.append({
                    "side_trip_id": (
                        row.get("side_trip_id")
                        or ""
                    ),
                    "resupply_amenity_id": (
                        row.get(
                            "resupply_amenity_id"
                        )
                        or ""
                    ),
                    "town_access": (
                        row.get("town_access")
                        or ""
                    ),
                    "name": (
                        row.get("name")
                        or ""
                    ),
                    "category": (
                        row.get("category")
                        or ""
                    ),
                    "estimated_time": (
                        row.get("estimated_time")
                        or ""
                    ),
                    "planning_notes": (
                        row.get("planning_notes")
                        or ""
                    ),
                    "source_name": (
                        row.get("source_name")
                        or ""
                    ),
                    "source_url": (
                        row.get("source_url")
                        or ""
                    ),
                    "validation_status": (
                        row.get(
                            "validation_status"
                        )
                        or ""
                    ),
                    "validation_source_name": (
                        row.get(
                            "validation_source_name"
                        )
                        or ""
                    ),
                    "validation_source_url": (
                        row.get(
                            "validation_source_url"
                        )
                        or ""
                    ),
                    "validation_date": (
                        row.get(
                            "validation_date"
                        )
                        or ""
                    ),
                })

        self._side_trip_options = options
        return self._side_trip_options

    def service_category_label(
        self,
        service,
    ):

        labels = {
            "grocery": "Grocery",
            "post_office": "Post office",
            "outfitter": "Outfitter",
            "lodging": "Lodging",
            "restaurants": "Restaurants",
        }

        return labels.get(
            service,
            str(service).replace(
                "_",
                " ",
            ).title(),
        )

    def options_for_resupply_node(
        self,
        node,
        options,
        id_field,
    ):

        if not node:
            return []

        node_id = self.resupply_node_id(
            node
        )

        return [
            option for option in options
            if option.get(id_field) == node_id
        ]

    def town_service_options_for_node(
        self,
        node,
    ):

        return self.options_for_resupply_node(
            node,
            self.load_town_service_options(),
            "resupply_amenity_id",
        )

    def selected_side_trip_ids(
        self,
    ):

        return set(
            str(value)
            for value in (
                self.user_profile.get(
                    "selected_side_trip_ids",
                    [],
                )
                or []
            )
            if str(value)
        )

    def selected_town_ids(
        self,
    ):

        return set(
            str(value)
            for value in (
                self.user_profile.get(
                    "selected_town_ids",
                    [],
                )
                or []
            )
            if str(value)
        )

    def town_preference_node_id(
        self,
        value,
    ):

        return str(
            value or ""
        ).split(
            "::",
            1,
        )[0]

    def town_preference_town_name(
        self,
        value,
    ):

        parts = str(
            value or ""
        ).split(
            "::",
            1,
        )

        if len(parts) < 2:
            return ""

        return parts[1].strip()

    def selected_town_ids_for_node(
        self,
        node,
    ):

        if not node:
            return []

        node_id = self.resupply_node_id(
            node
        )

        return [
            selected_id
            for selected_id in (
                self.selected_town_ids()
            )
            if (
                self.town_preference_node_id(
                    selected_id
                )
                == node_id
            )
        ]

    def selected_town_names_for_node(
        self,
        node,
    ):

        selected_ids = (
            self.selected_town_ids_for_node(
                node
            )
        )

        names = [
            self.town_preference_town_name(
                selected_id
            )
            for selected_id in selected_ids
            if self.town_preference_town_name(
                selected_id
            )
        ]

        if names:
            return names

        if selected_ids:
            return [
                node.get(
                    "town_access",
                    "",
                )
            ]

        return []

    def side_trip_options_for_node(
        self,
        node,
    ):

        selected_ids = (
            self.selected_side_trip_ids()
        )

        if not selected_ids:
            return []

        return [
            option for option in (
                self.options_for_resupply_node(
                    node,
                    self.load_side_trip_options(),
                    "resupply_amenity_id",
                )
            )
            if option.get("side_trip_id")
            in selected_ids
        ]

    def selected_town_matches_node(
        self,
        node,
    ):

        return bool(
            self.selected_town_ids_for_node(
                node
            )
        )

    def access_detail_for_selected_town(
        self,
        node,
        town_name,
        access_distance,
        access_notes,
    ):

        grouped_town_access = (
            node.get(
                "town_access",
                "",
            )
            if node
            else ""
        )

        if (
            town_name
            and "/" in grouped_town_access
            and town_name.lower()
            not in str(
                access_notes or ""
            ).lower()
        ):
            return (
                None,
                (
                    f"Access distance to {town_name} "
                    "needs source validation."
                ),
            )

        return (
            access_distance,
            access_notes,
        )

    def format_option_names(
        self,
        options,
        name_field,
    ):

        return ", ".join([
            option.get(name_field, "")
            for option in options
            if option.get(name_field)
        ])

    def zero_support_status(
        self,
        node,
        service_options,
    ):

        categories = {
            option.get(
                "service_category",
                "",
            )
            for option in service_options
        }

        has_validated_lodging = (
            "lodging" in categories
        )
        has_validated_food = bool(
            categories & {
                "food",
                "grocery",
                "restaurant",
                "restaurants",
            }
        )

        if (
            has_validated_lodging
            and has_validated_food
        ):
            return "validated_lodging_and_food"

        services = set(
            node.get(
                "resupply_services",
                [],
            )
            or []
            if node
            else []
        )

        if (
            "lodging" in services
            and services & {
                "grocery",
                "restaurants",
            }
        ):
            return "category_only"

        return "insufficient_validated_detail"

    def side_trip_note(
        self,
        side_trip_options,
    ):

        notes = []

        for option in side_trip_options:

            estimated_time = option.get(
                "estimated_time",
                "",
            )
            name = option.get(
                "name",
                "",
            )

            if not name:
                continue

            if estimated_time:
                notes.append(
                    f"{name} ({estimated_time})"
                )
            else:
                notes.append(name)

        return "; ".join(notes)

    def match_logistics_candidate_for_resupply_row(
        self,
        row,
    ):

        row_mile_value = row.get("mile")

        if row_mile_value is None:
            row_mile_value = row.get(
                "resupply_mile"
            )

        row_mile = self.parse_float(
            row_mile_value
        )
        row_town_tokens = (
            self.normalize_match_tokens(
                row.get("town_access")
            )
        )
        row_location_tokens = (
            self.normalize_match_tokens(
                row.get("location")
                or row.get("resupply_location")
            )
        )

        matches = []

        for node in self.build_logistics_candidates():

            node_mile = self.node_mile(
                node
            )
            distance = None

            if (
                row_mile is not None
                and node_mile is not None
            ):
                distance = abs(
                    row_mile - node_mile
                )

                if distance > 1.5:
                    continue

            node_town_tokens = (
                self.normalize_match_tokens(
                    node.get("town_access")
                )
            )
            node_location_tokens = (
                self.normalize_match_tokens(
                    node.get("canonical_name")
                    or node.get("location")
                )
            )
            token_match = bool(
                row_town_tokens & node_town_tokens
                or row_location_tokens
                & node_location_tokens
            )

            if (
                row_mile is None
                and not token_match
            ):
                continue

            matches.append({
                "node": node,
                "token_match": token_match,
                "distance": (
                    distance
                    if distance is not None
                    else 999
                ),
            })

        if not matches:
            return None

        matches = sorted(
            matches,
            key=lambda match: (
                not match["token_match"],
                match["distance"],
            ),
        )

        return matches[0]["node"]

    def build_resupply_town_details(
        self,
        resupply_plan=None,
    ):

        rows = []
        source_plan = (
            resupply_plan
            if resupply_plan is not None
            else self.build_resupply_plan()
        )

        for row in source_plan:

            node = (
                self.match_logistics_candidate_for_resupply_row(
                    row
                )
            )

            town_access = (
                row.get("town_access")
                or (
                    node.get("town_access")
                    if node
                    else ""
                )
            )

            if not town_access:
                continue

            service_options = (
                self.town_service_options_for_node(
                    node
                )
            )
            side_trip_options = (
                self.side_trip_options_for_node(
                    node
                )
            )

            services = (
                node.get(
                    "resupply_services",
                    [],
                )
                or []
                if node
                else []
            )
            service_categories = ", ".join([
                self.service_category_label(
                    service
                )
                for service in services
            ])
            lodging_options = [
                option for option
                in service_options
                if option.get(
                    "service_category"
                ) == "lodging"
            ]
            food_options = [
                option for option
                in service_options
                if option.get(
                    "service_category"
                ) in {
                    "food",
                    "grocery",
                    "restaurant",
                    "restaurants",
                }
            ]
            outfitter_options = [
                option for option
                in service_options
                if option.get(
                    "service_category"
                ) == "outfitter"
            ]
            mail_drop_options = [
                option for option
                in service_options
                if option.get(
                    "service_category"
                ) == "mail_drop"
            ]

            access_distance = (
                self.access_distance_miles(
                    node
                )
                if node
                else row.get(
                    "access_distance_miles"
                )
            )
            access_notes = (
                row.get("access_notes")
                or (
                    node.get(
                        "access_notes",
                        "",
                    )
                    if node
                    else ""
                )
            )

            rows.append({
                "day": row.get("day"),
                "resupply_location": row.get(
                    "location"
                ),
                "mile": row.get("mile"),
                "town_access": town_access,
                "access_distance_miles": (
                    access_distance
                ),
                "access_notes": access_notes,
                "service_categories": (
                    service_categories
                    or "Unspecified"
                ),
                "validated_lodging": (
                    self.format_option_names(
                        lodging_options,
                        "display_name",
                    )
                ),
                "validated_food": (
                    self.format_option_names(
                        food_options,
                        "display_name",
                    )
                ),
                "validated_outfitters": (
                    self.format_option_names(
                        outfitter_options,
                        "display_name",
                    )
                ),
                "validated_mail_drop": (
                    self.format_option_names(
                        mail_drop_options,
                        "display_name",
                    )
                ),
                "zero_support": (
                    self.zero_support_status(
                        node,
                        service_options,
                    )
                ),
                "selected_side_trips": (
                    self.side_trip_note(
                        side_trip_options
                    )
                ),
                "zero_candidate": (
                    bool(
                        node.get(
                            "zero_candidate"
                        )
                    )
                    if node
                    else False
                ),
                "source_name": (
                    node.get("resupply_source")
                    if node
                    else ""
                ),
                "source_url": (
                    node.get(
                        "resupply_source_url"
                    )
                    if node
                    else ""
                ),
                "business_detail_status": (
                    (
                        "validated named options "
                        "available"
                    )
                    if service_options
                    else (
                        "category-only; named "
                        "options require "
                        "independent current "
                        "validation"
                    )
                ),
            })

        return rows

    def build_selected_experiences(
        self,
        resupply_plan=None,
    ):

        rows = []
        planned_side_trip_ids = set()
        planned_town_ids = set()

        if (
            not self.selected_side_trip_ids()
            and not self.selected_town_ids()
        ):
            return rows

        source_plan = (
            resupply_plan
            if resupply_plan is not None
            else self.build_resupply_plan()
        )

        for row in source_plan:

            node = (
                self.match_logistics_candidate_for_resupply_row(
                    row
                )
            )
            side_trip_options = (
                self.side_trip_options_for_node(
                    node
                )
            )

            if not side_trip_options:
                side_trip_options = []

            town_access = (
                row.get("town_access")
                or (
                    node.get("town_access")
                    if node
                    else ""
                )
            )
            access_distance = (
                self.access_distance_miles(
                    node
                )
                if node
                else row.get(
                    "access_distance_miles"
                )
            )
            access_notes = (
                row.get("access_notes")
                or (
                    node.get(
                        "access_notes",
                        "",
                    )
                    if node
                    else ""
                )
            )

            if self.selected_town_matches_node(
                node
            ):

                for town_name in (
                    self.selected_town_names_for_node(
                        node
                    )
                ):
                    (
                        town_access_distance,
                        town_access_notes,
                    ) = (
                        self.access_detail_for_selected_town(
                            node,
                            town_name,
                            access_distance,
                            access_notes,
                        )
                    )
                    town_id = (
                        f"{self.resupply_node_id(node)}"
                        f"::{town_name}"
                    )
                    planned_town_ids.add(town_id)

                    rows.append({
                        "day": row.get("day"),
                        "location": row.get(
                            "location"
                        ),
                        "mile": row.get("mile"),
                        "town_access": town_name,
                        "experience_name": (
                            f"{town_name} town stop"
                        ),
                        "category": (
                            "town_preference"
                        ),
                        "estimated_time": "",
                        "planning_notes": (
                            "Selected town preference; "
                            "annotation only and not "
                            "included in itinerary time."
                        ),
                        "access_distance_miles": (
                            town_access_distance
                        ),
                        "access_notes": (
                            town_access_notes
                        ),
                        "validation_status": (
                            "curated"
                        ),
                        "validation_source_name": (
                            node.get(
                                "resupply_source",
                                "",
                            )
                            if node
                            else ""
                        ),
                        "validation_source_url": (
                            node.get(
                                "resupply_source_url",
                                "",
                            )
                            if node
                            else ""
                        ),
                        "validation_date": "",
                        "planning_status": "planned",
                    })

            for option in side_trip_options:
                planned_side_trip_ids.add(
                    option.get(
                        "side_trip_id",
                        "",
                    )
                )
                rows.append({
                    "day": row.get("day"),
                    "location": row.get(
                        "location"
                    ),
                    "mile": row.get("mile"),
                    "town_access": town_access,
                    "experience_name": (
                        option.get("name", "")
                    ),
                    "category": option.get(
                        "category",
                        "",
                    ),
                    "estimated_time": (
                        option.get(
                            "estimated_time",
                            "",
                        )
                    ),
                    "planning_notes": (
                        option.get(
                            "planning_notes",
                            "",
                        )
                    ),
                    "access_distance_miles": (
                        access_distance
                    ),
                    "access_notes": access_notes,
                    "validation_status": (
                        option.get(
                            "validation_status",
                            "",
                        )
                    ),
                    "validation_source_name": (
                        option.get(
                            "validation_source_name",
                            "",
                        )
                    ),
                    "validation_source_url": (
                        option.get(
                            "validation_source_url",
                            "",
                        )
                    ),
                    "validation_date": (
                        option.get(
                            "validation_date",
                            "",
                        )
                    ),
                    "planning_status": "planned",
                })

        rows.extend(
            self.unplanned_selected_preference_rows(
                planned_side_trip_ids,
                planned_town_ids,
            )
        )

        return rows

    def unplanned_selected_preference_rows(
        self,
        planned_side_trip_ids,
        planned_town_ids,
    ):

        rows = []

        for selected_id in sorted(
            self.selected_side_trip_ids()
        ):
            if selected_id in planned_side_trip_ids:
                continue

            option = next(
                (
                    candidate
                    for candidate in (
                        self.load_side_trip_options()
                    )
                    if candidate.get(
                        "side_trip_id"
                    )
                    == selected_id
                ),
                None,
            )

            if not option:
                rows.append(
                    self.unmatched_selected_preference_row(
                        selected_id,
                        "side_trip",
                    )
                )
                continue

            rows.append({
                "day": None,
                "location": "",
                "mile": None,
                "town_access": option.get(
                    "town_access",
                    "",
                ),
                "experience_name": option.get(
                    "name",
                    "",
                ),
                "category": option.get(
                    "category",
                    "",
                ),
                "estimated_time": option.get(
                    "estimated_time",
                    "",
                ),
                "planning_notes": option.get(
                    "planning_notes",
                    "",
                ),
                "access_distance_miles": None,
                "access_notes": "",
                "validation_status": option.get(
                    "validation_status",
                    "",
                ),
                "validation_source_name": (
                    option.get(
                        "validation_source_name",
                        "",
                    )
                ),
                "validation_source_url": option.get(
                    "validation_source_url",
                    "",
                ),
                "validation_date": option.get(
                    "validation_date",
                    "",
                ),
                "planning_status": (
                    "not_in_generated_plan"
                ),
            })

        candidates_by_id = {
            self.resupply_node_id(node): node
            for node in (
                self.build_logistics_candidates()
            )
        }

        for selected_id in sorted(
            self.selected_town_ids()
        ):
            node_id = (
                self.town_preference_node_id(
                    selected_id
                )
            )
            town_name = (
                self.town_preference_town_name(
                    selected_id
                )
            )

            if not town_name:
                node = candidates_by_id.get(
                    node_id
                )
                town_name = (
                    node.get(
                        "town_access",
                        "",
                    )
                    if node
                    else node_id
                )

            canonical_selected_id = (
                f"{node_id}::{town_name}"
            )

            if (
                canonical_selected_id
                in planned_town_ids
            ):
                continue

            node = candidates_by_id.get(
                node_id
            )

            if not node:
                rows.append(
                    self.unmatched_selected_preference_row(
                        selected_id,
                        "town_preference",
                    )
                )
                continue

            access_distance = (
                self.access_distance_miles(
                    node
                )
            )
            access_notes = node.get(
                "access_notes",
                "",
            )
            (
                town_access_distance,
                town_access_notes,
            ) = (
                self.access_detail_for_selected_town(
                    node,
                    town_name,
                    access_distance,
                    access_notes,
                )
            )

            rows.append({
                "day": None,
                "location": node.get(
                    "canonical_name",
                    "",
                ),
                "mile": round(
                    self.node_mile(node),
                    1,
                )
                if self.node_mile(node)
                is not None
                else None,
                "town_access": town_name,
                "experience_name": (
                    f"{town_name} town stop"
                ),
                "category": "town_preference",
                "estimated_time": "",
                "planning_notes": (
                    "Selected town preference was not "
                    "part of the generated plan."
                ),
                "access_distance_miles": (
                    town_access_distance
                ),
                "access_notes": town_access_notes,
                "validation_status": "curated",
                "validation_source_name": node.get(
                    "resupply_source",
                    "",
                ),
                "validation_source_url": node.get(
                    "resupply_source_url",
                    "",
                ),
                "validation_date": "",
                "planning_status": (
                    "not_in_generated_plan"
                ),
            })

        return rows

    def unmatched_selected_preference_row(
        self,
        selected_id,
        category,
    ):

        return {
            "day": None,
            "location": "",
            "mile": None,
            "town_access": "",
            "experience_name": selected_id,
            "category": category,
            "estimated_time": "",
            "planning_notes": (
                "Selected preference could not be matched "
                "to current runtime data."
            ),
            "access_distance_miles": None,
            "access_notes": "",
            "validation_status": "unmatched",
            "validation_source_name": "",
            "validation_source_url": "",
            "validation_date": "",
            "planning_status": "unmatched",
        }

    def annotate_daily_plan_with_side_trips(
        self,
        daily_plan,
    ):

        if not self.selected_side_trip_ids():
            return daily_plan

        annotated_rows = []

        for row in daily_plan:

            annotated = dict(row)
            node = (
                self.match_logistics_candidate_for_resupply_row({
                    "mile": row.get(
                        "resupply_mile"
                    ),
                    "town_access": row.get(
                        "town_access"
                    ),
                    "location": row.get(
                        "resupply_location"
                    ),
                })
            )
            side_trip_options = (
                self.side_trip_options_for_node(
                    node
                )
            )
            annotated[
                "selected_side_trips"
            ] = self.side_trip_note(
                side_trip_options
            )

            annotated_rows.append(
                annotated
            )

        return annotated_rows

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
                self.format_access_notes(
                    node.get("access_notes")
                    or amenity.get("access_notes")
                    or ""
                )
            )

            node[
                "access_distance_miles"
            ] = amenity.get(
                "access_distance_miles"
            )

            for key in [
                "access_distance_qualifier",
                "access_direction",
                "access_mode",
                "resupply_convenience",
            ]:
                node[key] = amenity.get(
                    key,
                    "",
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

        score += self.score_access_convenience(
            node
        )

        return score

    def access_distance_miles(
        self,
        node,
    ):

        distance = self.parse_float(
            node.get("access_distance_miles")
        )

        if distance is not None:
            return distance

        amenity = node.get(
            "resupply_amenity",
            {},
        )

        return self.parse_float(
            amenity.get(
                "access_distance_miles"
            )
        )

    def score_access_convenience(
        self,
        node,
    ):

        distance = self.access_distance_miles(
            node
        )

        if distance is None:
            return 0

        if (
            distance
            <= self.convenient_resupply_distance_miles
        ):
            return 35

        if distance <= 3.0:
            return 10

        if distance <= 5.0:
            return -10

        return -25

    def is_convenient_extra_resupply(
        self,
        node,
    ):

        distance = self.access_distance_miles(
            node
        )

        return (
            distance is None
            or distance
            <= self.convenient_resupply_distance_miles
        )

    def forward_resupply_gap_after(
        self,
        node,
        resupply_nodes,
        used_resupply_ids,
    ):

        node_mile = self.node_mile(
            node
        )

        if node_mile is None:
            return None

        forward_nodes = []

        for candidate in resupply_nodes:

            candidate_id = (
                self.resupply_node_id(
                    candidate
                )
            )

            if candidate_id in used_resupply_ids:
                continue

            if (
                candidate is node
                or candidate_id
                == self.resupply_node_id(
                    node
                )
            ):
                continue

            if not self.is_resupply_candidate(
                candidate
            ):
                continue

            candidate_mile = self.node_mile(
                candidate
            )

            if not self.is_forward_progress(
                node_mile,
                candidate_mile,
            ):
                continue

            forward_nodes.append(
                candidate
            )

        if not forward_nodes:
            return None

        next_node = sorted(
            forward_nodes,
            key=lambda candidate: (
                self.travel_distance(
                    node_mile,
                    self.node_mile(
                        candidate
                    ),
                )
            ),
        )[0]

        return self.travel_distance(
            node_mile,
            self.node_mile(
                next_node
            ),
        )

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

        if self.has_validated_lodging(
            node
        ):
            score += 65

        if amenity.get("lodging"):
            score += 35

        if amenity.get("restaurants"):
            score += 25

        if amenity.get("grocery"):
            score += 10

        if node.get("town_access"):
            score += 5

        return score

    def has_validated_lodging(
        self,
        node,
    ):

        return any(
            option.get(
                "service_category"
            )
            == "lodging"
            for option in (
                self.town_service_options_for_node(
                    node
                )
            )
        )

    def has_lodging_support(
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
            self.has_validated_lodging(
                node
            )
            or amenity.get("lodging")
            or "lodging" in services
        )

    def zero_recovery_capable(
        self,
        node,
        days_since_recovery,
        cadence,
    ):

        amenity = node.get(
            "resupply_amenity",
            {},
        )

        if (
            amenity.get("zero_candidate")
            or node.get("zero_candidate")
        ):
            return True

        return (
            days_since_recovery
            >= cadence - 1
            and self.has_lodging_support(
                node
            )
        )

    def target_recovery_total(
        self,
    ):

        return (
            self.target_zero_days
            + self.target_nero_days
        )

    def recovery_target_day(
        self,
        completion_days,
        target_index,
    ):

        total = self.target_recovery_total()

        if (
            not completion_days
            or total <= 0
        ):
            return None

        return max(
            1,
            round(
                target_index
                * completion_days
                / (
                    total + 1
                )
            ),
        )

    def recovery_target_kind(
        self,
        target_index,
    ):

        total = self.target_recovery_total()

        if total <= 0:
            return "zero"

        zero_before = round(
            (
                target_index - 1
            )
            * self.target_zero_days
            / total
        )
        zero_through = round(
            target_index
            * self.target_zero_days
            / total
        )

        if zero_through > zero_before:
            return "zero"

        return "nero"

    def recovery_target_slots(
        self,
        completion_days,
    ):

        total = self.target_recovery_total()

        if (
            not completion_days
            or total <= 0
        ):
            return []

        return [
            {
                "index": index,
                "day": self.recovery_target_day(
                    completion_days,
                    index,
                ),
                "kind": self.recovery_target_kind(
                    index
                ),
            }
            for index in range(
                1,
                total + 1,
            )
        ]

    def pending_recovery_slots(
        self,
        completion_days,
        kind,
        placed_zero_count,
        placed_nero_count,
    ):

        placed_count = (
            placed_zero_count
            if kind == "zero"
            else placed_nero_count
        )

        slots = [
            slot
            for slot in self.recovery_target_slots(
                completion_days
            )
            if slot["kind"] == kind
        ]

        return slots[
            placed_count:
        ]

    def best_recovery_slot_for_day(
        self,
        completion_days,
        kind,
        effective_recovery_day,
        placed_zero_count,
        placed_nero_count,
    ):

        slots = self.pending_recovery_slots(
            completion_days,
            kind,
            placed_zero_count,
            placed_nero_count,
        )

        eligible = [
            slot
            for slot in slots
            if (
                slot.get("day")
                is not None
                and effective_recovery_day
                >= slot["day"] - 2
            )
        ]

        if not eligible:
            return None

        return sorted(
            eligible,
            key=lambda slot: (
                abs(
                    effective_recovery_day
                    - slot["day"]
                ),
                slot["day"],
            ),
        )[0]

    def select_resupply_for_day(
        self,
        start_mile,
        stop_mile,
        day,
        last_resupply_day,
        resupply_nodes,
        used_resupply_ids,
        terminal_mile=None,
    ):

        cadence = max(
            2,
            self.resupply_cadence,
        )

        days_since_resupply = (
            day - last_resupply_day
        )

        if days_since_resupply < (
            cadence - 2
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

            if terminal_mile is not None:
                terminal_distance = (
                    self.travel_distance(
                        mile,
                        terminal_mile,
                    )
                )

                if (
                    terminal_distance
                    <= self.max_daily_miles * 1.3
                ):
                    continue

            candidate_distance = (
                self.travel_distance(
                    start_mile,
                    mile,
                )
            )

            days_due = (
                days_since_resupply
                >= cadence
            )

            if (
                candidate_distance
                < self.min_daily_miles
                and not self.is_convenient_extra_resupply(
                    node
                )
                and not (
                    self.avoid_long_food_carry
                    and days_due
                    and (
                        self.access_distance_miles(
                            node
                        )
                        is not None
                    )
                    and self.access_distance_miles(
                        node
                    ) <= 5.0
                )
            ):
                continue

            early_resupply = (
                days_since_resupply
                < cadence - 1
            )

            if early_resupply:

                forward_gap = (
                    self.forward_resupply_gap_after(
                        node,
                        resupply_nodes,
                        used_resupply_ids,
                    )
                )

                if (
                    forward_gap is None
                    and terminal_mile is not None
                ):
                    forward_gap = self.travel_distance(
                        self.node_mile(node),
                        terminal_mile,
                    )

                long_gap_ahead = bool(
                    forward_gap is not None
                    and forward_gap
                    > (
                        self.max_daily_miles
                        * 2
                    )
                )

                if (
                    not self.is_convenient_extra_resupply(
                        node
                    )
                    and not (
                        self.avoid_long_food_carry
                        and long_gap_ahead
                    )
                ):
                    continue

            score = (
                self.score_resupply_candidate(
                    node
                )
            )
            access_distance = (
                self.access_distance_miles(
                    node
                )
            )
            off_trail_penalty = 0

            if (
                access_distance is not None
                and access_distance
                > self.convenient_resupply_distance_miles
                and not (
                    days_due
                    or self.is_recovery_candidate(
                        node
                    )
                )
            ):
                off_trail_penalty = 50

            if (
                self.avoid_long_food_carry
                and days_since_resupply
                == cadence - 1
            ):
                score += 20

            candidates.append({
                "node": node,
                "score": score,
                "distance_to_stop": abs(
                    stop_mile - mile
                ),
                "early_resupply": early_resupply,
                "access_distance_miles": (
                    access_distance
                ),
                "off_trail_penalty": (
                    off_trail_penalty
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
                item["early_resupply"],
                item["off_trail_penalty"],
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
        completion_days=None,
        placed_zero_count=0,
        placed_nero_count=0,
    ):

        cadence = max(
            3,
            self.recovery_cadence,
        )

        days_since_recovery = (
            day - last_recovery_day
        )

        target_recovery_day = None
        target_recovery_kind = None
        count_mode = (
            self.recovery_planning_mode
            == "target_counts"
        )

        if count_mode:
            placed_total = (
                placed_zero_count
                + placed_nero_count
            )
            target_total = (
                self.target_recovery_total()
            )

            if (
                target_total <= 0
                or placed_total >= target_total
                or days_since_recovery < 2
            ):
                return (
                    None,
                    None,
                )
        elif days_since_recovery < (
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

            zero_capable = (
                self.zero_recovery_capable(
                    node,
                    days_since_recovery,
                    cadence,
                )
            )

            candidate_recovery_options = []

            if count_mode:
                if (
                    placed_zero_count
                    < self.target_zero_days
                    and zero_capable
                    and candidate_distance
                    >= self.min_daily_miles
                ):
                    zero_slot = (
                        self.best_recovery_slot_for_day(
                            completion_days,
                            "zero",
                            day + 1,
                            placed_zero_count,
                            placed_nero_count,
                        )
                    )
                    if zero_slot:
                        candidate_recovery_options.append(
                            {
                                "kind": "zero",
                                "slot": zero_slot,
                                "effective_day": day + 1,
                            }
                        )

                if (
                    placed_nero_count
                    < self.target_nero_days
                    and self.is_nero_distance(
                        candidate_distance
                    )
                ):
                    nero_slot = (
                        self.best_recovery_slot_for_day(
                            completion_days,
                            "nero",
                            day,
                            placed_zero_count,
                            placed_nero_count,
                        )
                    )
                    if nero_slot:
                        candidate_recovery_options.append(
                            {
                                "kind": "nero",
                                "slot": nero_slot,
                                "effective_day": day,
                            }
                        )

            else:
                candidate_kind = "nero"

                if (
                    target_recovery_kind == "zero"
                    or (
                        target_recovery_kind is None
                        and zero_capable
                    )
                ):
                    if (
                        zero_capable
                        and candidate_distance
                        >= self.min_daily_miles
                    ):
                        candidate_kind = "zero"
                    elif (
                        target_recovery_kind
                        == "zero"
                    ):
                        continue

                if (
                    candidate_kind == "nero"
                    and not self.is_nero_distance(
                        candidate_distance
                    )
                ):
                    continue

                candidate_recovery_options.append(
                    {
                        "kind": candidate_kind,
                        "slot": None,
                        "effective_day": day,
                    }
                )

            for option in candidate_recovery_options:
                slot = option.get("slot")
                candidate_kind = option["kind"]
                effective_day = option[
                    "effective_day"
                ]

                kind_penalty = 0

                if (
                    target_recovery_kind
                    and candidate_kind
                    != target_recovery_kind
                ):
                    kind_penalty = 1

                recovery_day_target = (
                    slot.get("day")
                    if slot
                    else (
                        target_recovery_day
                        or day
                    )
                )

                candidates.append({
                    "node": node,
                    "score": score,
                    "kind": candidate_kind,
                    "kind_penalty": kind_penalty,
                    "distance_to_target": abs(
                        target_mile - mile
                    ),
                    "distance_to_recovery_day": abs(
                        recovery_day_target
                        - effective_day
                    ),
                    "slot_index": (
                        slot.get("index")
                        if slot
                        else 0
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
                item[
                    "distance_to_recovery_day"
                ],
                item[
                    "slot_index"
                ],
                abs(
                    days_since_recovery
                    - cadence
                ),
                item["kind_penalty"],
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
                    "access_distance_miles": (
                        self.access_distance_miles(
                            matched_start
                        )
                        if matched_start
                        else None
                    ),
                    "access_notes": (
                        matched_start.get(
                            "access_notes",
                            ""
                        )
                        if matched_start
                        else ""
                    ),
                    "resupply_convenience": (
                        matched_start.get(
                            "resupply_convenience",
                            ""
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
                    "access_distance_miles": day.get(
                        "resupply_access_distance_miles"
                    ),
                    "access_notes": day.get(
                        "resupply_access_notes"
                    ),
                    "resupply_convenience": day.get(
                        "resupply_convenience"
                    ),
                    "access_type": day.get(
                        "resupply_location_type",
                        "logistics",
                    ),
                    "notes": day.get(
                        "notes"
                    ),
                })

            moving_days = [
                day for day in daily_plan
                if day.get(
                    "daily_miles",
                    0,
                ) > 0
            ]

            def food_carry_days_between(
                start_day,
                stop_day,
                include_start=False,
            ):

                if (
                    start_day is None
                    or stop_day is None
                ):
                    return None

                return len([
                    day for day in moving_days
                    if (
                        day.get("day")
                        is not None
                        and (
                            day.get("day")
                            >= start_day
                            if include_start
                            else day.get("day")
                            > start_day
                        )
                        and day.get("day")
                        <= stop_day
                    )
                ])

            for idx, row in enumerate(rows):

                if idx + 1 < len(rows):
                    row[
                        "days_to_next_resupply"
                    ] = food_carry_days_between(
                        row["day"],
                        rows[idx + 1]["day"],
                        include_start=(
                            row.get("notes")
                            == "start"
                        ),
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
                    ] = food_carry_days_between(
                        row["day"],
                        terminal_day
                    )

                    if (
                        row[
                            "days_to_next_resupply"
                        ]
                        is None
                    ):
                        row[
                            "days_to_next_resupply"
                        ] = max(
                            0,
                            terminal_day
                            - row["day"],
                        )

            recovery_days = [
                day.get("day")
                for day in daily_plan
                if (
                    day.get("day") is not None
                    and (
                        "zero" in str(
                            day.get("notes", "")
                        )
                        or "nero" in str(
                            day.get("notes", "")
                        )
                    )
                )
            ]

            for row in rows:

                next_recovery_day = next(
                    (
                        recovery_day
                        for recovery_day
                        in recovery_days
                        if recovery_day > row["day"]
                    ),
                    None,
                )

                row[
                    "days_to_next_recovery"
                ] = (
                    next_recovery_day
                    - row["day"]
                    if next_recovery_day
                    is not None
                    else None
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
                "access_distance_miles": (
                    self.access_distance_miles(
                        node
                    )
                ),
                "access_notes": node.get(
                    "access_notes",
                    "",
                ),
                "resupply_convenience": node.get(
                    "resupply_convenience",
                    "",
                ),
                "access_type": node.get(
                    "node_class",
                    "logistics"
                ),
                "notes": (
                    "resupply"
                ),
                "days_to_next_resupply": None,
                "days_to_next_recovery": None,
            })

        return rows[:10]
