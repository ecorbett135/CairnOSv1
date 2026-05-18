# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from cairn.runtime.graph_runtime import (
    OperationalGraphRuntime,
)


class TraversalEngine:

    def __init__(
        self,
        runtime: OperationalGraphRuntime,
    ):

        self.runtime = runtime
        self._overlay_nodes_by_id = None
        self._ordered_overlay_nodes = None

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

    def overlay_nodes_by_id(
        self,
    ):

        if self._overlay_nodes_by_id is None:
            self._overlay_nodes_by_id = {
                node.get("overlay_id"): node
                for node in (
                    self.runtime
                    .get_overlay_nodes()
                )
                if node.get("overlay_id")
            }

        return self._overlay_nodes_by_id

    def ordered_overlay_nodes(
        self,
    ):

        if self._ordered_overlay_nodes is not None:
            return self._ordered_overlay_nodes

        nodes_by_id = self.overlay_nodes_by_id()
        operational_edges = (
            self.runtime
            .get_edges_by_type(
                "operational_progression"
            )
        )

        ordered_ids = []

        for edge in sorted(
            operational_edges,
            key=lambda item: (
                item.get("edge_id", "")
            ),
        ):

            from_id = edge.get(
                "from_overlay"
            )
            to_id = edge.get(
                "to_overlay"
            )

            if (
                from_id
                and from_id in nodes_by_id
                and from_id not in ordered_ids
            ):
                ordered_ids.append(
                    from_id
                )

            if (
                to_id
                and to_id in nodes_by_id
                and to_id not in ordered_ids
            ):
                ordered_ids.append(
                    to_id
                )

        missing_nodes = [
            node
            for node in (
                self.runtime
                .get_overlay_nodes()
            )
            if node.get("overlay_id")
            not in ordered_ids
        ]

        ordered_nodes = [
            nodes_by_id[overlay_id]
            for overlay_id in ordered_ids
            if overlay_id in nodes_by_id
        ]

        ordered_nodes.extend(
            missing_nodes
        )

        self._ordered_overlay_nodes = sorted(
            ordered_nodes,
            key=lambda node: (
                self.node_mile(node)
                if self.node_mile(node) is not None
                else 0,
                node.get("overlay_id", ""),
            ),
        )

        return self._ordered_overlay_nodes

    def build_overlay_corridor(
        self,
        direction,
        start_mile=None,
        stop_mile=None,
    ):

        direction = str(
            direction or "NOBO"
        ).upper()

        nodes = list(
            self.ordered_overlay_nodes()
        )

        if direction == "SOBO":
            nodes = list(
                reversed(nodes)
            )

        if (
            start_mile is None
            or stop_mile is None
        ):
            return nodes

        lower = min(
            start_mile,
            stop_mile,
        )
        upper = max(
            start_mile,
            stop_mile,
        )

        return [
            node for node in nodes
            if (
                self.node_mile(node)
                is not None
                and lower
                <= self.node_mile(node)
                <= upper
            )
        ]

    def corridor_nodes_between(
        self,
        direction,
        start_mile,
        stop_mile,
        include_start=False,
        include_stop=True,
    ):

        nodes = self.build_overlay_corridor(
            direction,
            start_mile,
            stop_mile,
        )

        rows = []

        for node in nodes:

            mile = self.node_mile(node)

            if mile is None:
                continue

            if self.mile_in_travel_window(
                direction,
                start_mile,
                stop_mile,
                mile,
                include_start=include_start,
                include_stop=include_stop,
            ):
                rows.append(node)

        return rows

    def is_forward_progress(
        self,
        direction,
        current_mile,
        candidate_mile,
    ):

        if current_mile is None:
            return True

        if candidate_mile is None:
            return False

        if str(direction).upper() == "SOBO":
            return candidate_mile < (
                current_mile - 0.05
            )

        return candidate_mile > (
            current_mile + 0.05
        )

    def mile_in_travel_window(
        self,
        direction,
        start_mile,
        stop_mile,
        candidate_mile,
        include_start=False,
        include_stop=True,
    ):

        if candidate_mile is None:
            return False

        lower = min(
            start_mile,
            stop_mile,
        )
        upper = max(
            start_mile,
            stop_mile,
        )

        lower_ok = (
            candidate_mile >= lower
            if (
                include_start
                and lower == start_mile
            )
            or (
                include_stop
                and lower == stop_mile
            )
            else candidate_mile > lower
        )

        upper_ok = (
            candidate_mile <= upper
            if (
                include_start
                and upper == start_mile
            )
            or (
                include_stop
                and upper == stop_mile
            )
            else candidate_mile < upper
        )

        return (
            lower_ok
            and upper_ok
        )

    def estimate_segment_effort(
        self,
        segment_node,
    ):

        distance = (
            segment_node.get(
                "distance",
                0,
            ) or 0
        )

        gain = (
            segment_node.get(
                "elevation_gain_ft",
                0,
            ) or 0
        )

        difficulty = (
            segment_node.get(
                "difficulty",
                "moderate",
            ) or "moderate"
        )

        multiplier = {
            "easy": 1.0,
            "moderate": 1.25,
            "hard": 1.5,
            "severe": 2.0,
        }.get(
            str(difficulty).lower(),
            1.25,
        )

        elevation_penalty = (
            gain / 1000
        ) * 0.5

        effort_score = (
            distance * multiplier
        ) + elevation_penalty

        return {
            "distance": distance,
            "gain_ft": gain,
            "difficulty": difficulty,
            "effort_score": round(
                effort_score,
                2,
            ),
        }

    def build_effort_profile(self):

        profiles = []

        for node in (
            self.runtime
            .get_segment_nodes()
        ):

            profiles.append({
                "segment_id": node.get(
                    "segment_id"
                ),
                "profile": (
                    self.estimate_segment_effort(
                        node
                    )
                ),
            })

        return profiles
