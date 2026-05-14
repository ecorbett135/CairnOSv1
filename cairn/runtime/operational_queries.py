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
            if node.get("overnight") and not node.get("shelter") and not node.get("camping"):
                operational_overnight.append({
                    "node": node,
                    "priority": 3,  # Lower priority
                    "type": "overnight"
                })
        
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
