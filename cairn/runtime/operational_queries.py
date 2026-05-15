# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import json

from cairn.runtime.graph_runtime import (
    OperationalGraphRuntime,
)


class OperationalQueries:

    def __init__(
        self,
        runtime: OperationalGraphRuntime,
    ):

        self.runtime = runtime

    def list_overlay_progression(self):

        nodes = sorted(
            self.runtime.get_overlay_nodes(),
            key=lambda x: (
                x.get(
                    "trail_mile",
                    0,
                ) or 0
            ),
        )

        return [
            {
                "node_id": n.get(
                    "node_id"
                ),
                "overlay_id": n.get(
                    "overlay_id"
                ),
                "canonical_name": n.get(
                    "canonical_name"
                ),
                "name": n.get(
                    "canonical_name"
                ),
                "trail_mile": n.get(
                    "trail_mile"
                ),
                "mile": n.get(
                    "trail_mile"
                ),
                "node_class": n.get(
                    "node_class"
                ),
                "class": n.get(
                    "node_class"
                ),
                "division": n.get(
                    "division"
                ),
                "overnight": n.get(
                    "overnight"
                ),
                "resupply": n.get(
                    "resupply"
                ),
                "logistics": n.get(
                    "logistics"
                ),
                "town_access": n.get(
                    "town_access"
                ),
                "access_notes": n.get(
                    "access_notes"
                ),
                "resupply_services": n.get(
                    "resupply_services",
                    []
                ),
                "zero_candidate": n.get(
                    "zero_candidate"
                ),
            }
            for n in nodes
        ]

    def get_ingress_nodes(
        self,
        direction,
    ):

        direction = direction.upper()

        return [
            n for n in (
                self.runtime
                .get_approach_nodes()
            )
            if n.get(
                "direction",
                "",
            ).upper() == direction
        ]

    def get_overnight_nodes(self):

        return [
            n for n in (
                self.runtime
                .get_overlay_nodes()
            )
            if n.get("overnight")
        ]

    def get_shelter_nodes(self):
        """
        Get all shelter nodes from the overlay.
        
        Shelters are operational overnight facilities that should be
        preferred over synthetic camping locations.
        """
        return [
            n for n in (
                self.runtime
                .get_overlay_nodes()
            )
            if n.get("shelter")
        ]

    def load_overnight_reference(self):

        path = (
            self.runtime.compiled_dir /
            "overnight_reference.json"
        )

        if not path.exists():
            return {}

        with open(path) as handle:
            return json.load(handle)

    def get_overnight_reference_candidates(self):

        payload = (
            self.load_overnight_reference()
        )

        candidates = []

        for row in payload.get(
            "planner_candidates",
            [],
        ):

            node = {
                "canonical_name": row.get(
                    "canonical_name"
                ),
                "trail_mile": row.get(
                    "trail_mile"
                ),
                "node_class": row.get(
                    "node_class",
                    "camp",
                ),
                "division": row.get(
                    "division"
                ),
                "overnight": True,
                "shelter": row.get(
                    "shelter",
                    False,
                ),
                "camping": row.get(
                    "camping",
                    False,
                ),
                "coordinates": row.get(
                    "coordinates"
                ),
                "overnight_reference": True,
                "source_file": row.get(
                    "source_file"
                ),
                "source_id": row.get(
                    "source_id"
                ),
                "distance_to_spine_miles": (
                    row.get(
                        "distance_to_spine_miles"
                    )
                ),
            }

            if not (
                node["canonical_name"]
                and node["trail_mile"] is not None
            ):
                continue

            priority = (
                1
                if node.get("shelter")
                else 2
            )

            candidates.append({
                "node": node,
                "priority": priority,
                "type": (
                    "shelter"
                    if node.get("shelter")
                    else "camp"
                ),
            })

        return candidates

    def get_operational_overnight_nodes(self):
        """
        Get all operational overnight nodes including shelters and camps.

        Priority order for overnight selection:
        1. Shelters (node_class: "shelter")
        2. Designated campsites (node_class: "camp")
        3. Other overnight nodes (overnight: true)
        """
        overlay_nodes = self.runtime.get_overlay_nodes()

        operational_overnight = []

        # Add shelters first (highest priority)
        for node in overlay_nodes:
            if node.get("shelter"):
                operational_overnight.append({
                    "node": node,
                    "priority": 1,  # Highest priority
                    "type": "shelter"
                })

        # Add designated campsites
        for node in overlay_nodes:
            if node.get("camping") and not node.get("shelter"):
                operational_overnight.append({
                    "node": node,
                    "priority": 2,  # Medium priority
                    "type": "camp"
                })

        # Add other overnight nodes
        for node in overlay_nodes:
            if (
                node.get("overnight")
                and not node.get("shelter")
                and not node.get("camping")
            ):
                operational_overnight.append({
                    "node": node,
                    "priority": 3,  # Lower priority
                    "type": "overnight"
                })

        operational_overnight.extend(
            self.get_overnight_reference_candidates()
        )

        return operational_overnight

    def get_resupply_access_nodes(self):

        access_classes = {
            "crossing",
            "logistics",
            "trailhead",
            "access",
            "road_crossing",
        }

        rows = []

        for node in (
            self.runtime
            .get_overlay_nodes()
        ):

            has_resupply_signal = (
                node.get("resupply")
                or node.get("logistics")
                or node.get("town_access")
            )

            if not has_resupply_signal:
                continue

            if node.get("node_class") not in access_classes:
                continue

            rows.append(node)

        return sorted(
            rows,
            key=lambda x: (
                x.get("trail_mile", 0)
                or 0
            ),
        )

    def get_logistics_access_nodes(self):

        return self.get_resupply_access_nodes()

    def get_operational_progression_edges(self):

        return (
            self.runtime
            .get_edges_by_type(
                "operational_progression"
            )
        )
