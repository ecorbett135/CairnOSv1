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
                "name": n.get(
                    "canonical_name"
                ),
                "mile": n.get(
                    "trail_mile"
                ),
                "class": n.get(
                    "node_class"
                ),
                "overnight": n.get(
                    "overnight"
                ),
                "logistics": n.get(
                    "logistics"
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

    def get_logistics_access_nodes(self):

        return [
            n for n in (
                self.runtime
                .get_overlay_nodes()
            )
            if n.get("logistics")
        ]

    def get_operational_progression_edges(self):

        return (
            self.runtime
            .get_edges_by_type(
                "operational_progression"
            )
        )
