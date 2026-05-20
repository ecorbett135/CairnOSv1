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
        self._overlay_index_by_id = None

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

        for missing_node in sorted(
            missing_nodes,
            key=lambda node: (
                self.node_mile(node)
                if self.node_mile(node) is not None
                else float("inf"),
                node.get("overlay_id", ""),
            ),
        ):

            missing_mile = self.node_mile(
                missing_node
            )
            inserted = False

            if missing_mile is not None:
                for index, node in enumerate(
                    ordered_nodes
                ):
                    node_mile = self.node_mile(
                        node
                    )

                    if (
                        node_mile is not None
                        and missing_mile < node_mile
                    ):
                        ordered_nodes.insert(
                            index,
                            missing_node,
                        )
                        inserted = True
                        break

            if not inserted:
                ordered_nodes.append(
                    missing_node
                )

        self._ordered_overlay_nodes = (
            ordered_nodes
        )
        self._overlay_index_by_id = None

        return self._ordered_overlay_nodes

    def overlay_index_by_id(
        self,
    ):

        if self._overlay_index_by_id is None:
            self._overlay_index_by_id = {
                node.get("overlay_id"): index
                for index, node in enumerate(
                    self.ordered_overlay_nodes()
                )
                if node.get("overlay_id")
            }

        return self._overlay_index_by_id

    def overlay_index(
        self,
        node_or_id,
    ):

        overlay_id = node_or_id

        if isinstance(
            node_or_id,
            dict,
        ):
            overlay_id = node_or_id.get(
                "overlay_id"
            )

        if not overlay_id:
            return None

        return self.overlay_index_by_id().get(
            overlay_id
        )

    def ordered_overlay_nodes_for_direction(
        self,
        direction,
    ):

        nodes = list(
            self.ordered_overlay_nodes()
        )

        if str(direction).upper() == "SOBO":
            return list(
                reversed(nodes)
            )

        return nodes

    def resolve_overlay_reference(
        self,
        node=None,
        mile=None,
        canonical_name=None,
        corridor_nodes=None,
        max_mile_delta=0.15,
    ):

        nodes_by_id = self.overlay_nodes_by_id()
        corridor_ids = None

        if corridor_nodes is not None:
            corridor_ids = {
                corridor_node.get("overlay_id")
                for corridor_node in corridor_nodes
                if corridor_node.get("overlay_id")
            }

        def allowed(reference):

            if reference is None:
                return False

            if corridor_ids is None:
                return True

            return reference.get(
                "overlay_id"
            ) in corridor_ids

        if isinstance(
            node,
            dict,
        ):
            overlay_id = node.get(
                "overlay_id"
            )

            if (
                overlay_id
                and overlay_id in nodes_by_id
                and allowed(
                    nodes_by_id[overlay_id]
                )
            ):
                return nodes_by_id[
                    overlay_id
                ]

            if mile is None:
                mile = self.node_mile(
                    node
                )

        else:
            overlay_id = node

            if (
                overlay_id
                and overlay_id in nodes_by_id
                and allowed(
                    nodes_by_id[overlay_id]
                )
            ):
                return nodes_by_id[
                    overlay_id
                ]

        names = [
            canonical_name,
        ]

        if isinstance(
            node,
            dict,
        ):
            names.extend([
                node.get("canonical_name"),
                node.get("location"),
                node.get("title"),
                node.get("display_name"),
            ])

        for name in names:

            if not name:
                continue

            candidates = [
                reference
                for reference in (
                    corridor_nodes
                    if corridor_nodes is not None
                    else self.ordered_overlay_nodes()
                )
                if str(
                    reference.get(
                        "canonical_name",
                        "",
                    )
                ).casefold()
                == str(name).casefold()
            ]

            if not candidates:
                continue

            if mile is not None:
                return sorted(
                    candidates,
                    key=lambda reference: (
                        abs(
                            (
                                self.node_mile(
                                    reference
                                )
                                or mile
                            )
                            - mile
                        ),
                        self.overlay_index(
                            reference
                        )
                        or 0,
                    ),
                )[0]

            return sorted(
                candidates,
                key=lambda reference: (
                    self.overlay_index(
                        reference
                    )
                    or 0
                ),
            )[0]

        if mile is None:
            return None

        nearby = []

        for reference in (
            corridor_nodes
            if corridor_nodes is not None
            else self.ordered_overlay_nodes()
        ):

            reference_mile = self.node_mile(
                reference
            )

            if reference_mile is None:
                continue

            delta = abs(
                reference_mile - mile
            )

            if (
                max_mile_delta is not None
                and delta > max_mile_delta
            ):
                continue

            nearby.append(
                (
                    delta,
                    self.overlay_index(
                        reference
                    )
                    or 0,
                    reference,
                )
            )

        if not nearby:
            return None

        return sorted(
            nearby
        )[0][2]

    def _boundary_index(
        self,
        direction,
        mile,
        overlay_id=None,
        boundary="start",
        include=True,
    ):

        direction = str(
            direction or "NOBO"
        ).upper()

        index_by_id = self.overlay_index_by_id()

        if (
            overlay_id
            and overlay_id in index_by_id
        ):
            index = index_by_id[
                overlay_id
            ]

            if include:
                return index

            if boundary == "start":
                return (
                    index - 1
                    if direction == "SOBO"
                    else index + 1
                )

            return (
                index + 1
                if direction == "SOBO"
                else index - 1
            )

        if mile is None:
            return None

        indexed_miles = [
            (
                index,
                self.node_mile(node),
            )
            for index, node in enumerate(
                self.ordered_overlay_nodes()
            )
            if self.node_mile(node) is not None
        ]

        if direction == "SOBO":

            if boundary == "start":
                candidates = [
                    index
                    for index, node_mile in indexed_miles
                    if (
                        node_mile <= mile
                        if include
                        else node_mile < mile
                    )
                ]

                return (
                    max(candidates)
                    if candidates
                    else None
                )

            candidates = [
                index
                for index, node_mile in indexed_miles
                if (
                    node_mile >= mile
                    if include
                    else node_mile > mile
                )
            ]

            return (
                min(candidates)
                if candidates
                else None
            )

        if boundary == "start":
            candidates = [
                index
                for index, node_mile in indexed_miles
                if (
                    node_mile >= mile
                    if include
                    else node_mile > mile
                )
            ]

            return (
                min(candidates)
                if candidates
                else None
            )

        candidates = [
            index
            for index, node_mile in indexed_miles
            if (
                node_mile <= mile
                if include
                else node_mile < mile
            )
        ]

        return (
            max(candidates)
            if candidates
            else None
        )

    def _ordered_corridor_slice(
        self,
        direction,
        start_mile,
        stop_mile,
        include_start=True,
        include_stop=True,
        start_overlay_id=None,
        stop_overlay_id=None,
    ):

        direction = str(
            direction or "NOBO"
        ).upper()

        ordered_nodes = self.ordered_overlay_nodes()

        if (
            start_mile is None
            or stop_mile is None
        ):
            return self.ordered_overlay_nodes_for_direction(
                direction
            )

        start_index = self._boundary_index(
            direction,
            start_mile,
            overlay_id=start_overlay_id,
            boundary="start",
            include=include_start,
        )
        stop_index = self._boundary_index(
            direction,
            stop_mile,
            overlay_id=stop_overlay_id,
            boundary="stop",
            include=include_stop,
        )

        if (
            start_index is None
            or stop_index is None
            or start_index < 0
            or stop_index < 0
            or start_index >= len(
                ordered_nodes
            )
            or stop_index >= len(
                ordered_nodes
            )
        ):
            return None

        if direction == "SOBO":
            if start_index < stop_index:
                return []

            nodes = list(
                ordered_nodes[
                    stop_index:
                    start_index + 1
                ]
            )
            return list(
                reversed(nodes)
            )

        if start_index > stop_index:
            return []

        return list(
            ordered_nodes[
                start_index:
                stop_index + 1
            ]
        )

    def build_overlay_corridor(
        self,
        direction,
        start_mile=None,
        stop_mile=None,
        start_overlay_id=None,
        stop_overlay_id=None,
    ):

        direction = str(
            direction or "NOBO"
        ).upper()

        nodes = self._ordered_corridor_slice(
            direction,
            start_mile,
            stop_mile,
            include_start=True,
            include_stop=True,
            start_overlay_id=start_overlay_id,
            stop_overlay_id=stop_overlay_id,
        )

        if nodes is not None:
            return nodes

        nodes = (
            self.ordered_overlay_nodes_for_direction(
                direction
            )
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
        start_overlay_id=None,
        stop_overlay_id=None,
    ):

        nodes = self._ordered_corridor_slice(
            direction,
            start_mile,
            stop_mile,
            include_start=include_start,
            include_stop=include_stop,
            start_overlay_id=start_overlay_id,
            stop_overlay_id=stop_overlay_id,
        )

        if nodes is not None:
            return nodes

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

    def is_forward_overlay_progress(
        self,
        direction,
        current_overlay_id,
        candidate_overlay_id,
    ):

        if not current_overlay_id:
            return True

        if not candidate_overlay_id:
            return False

        index_by_id = self.overlay_index_by_id()

        current_index = index_by_id.get(
            current_overlay_id
        )
        candidate_index = index_by_id.get(
            candidate_overlay_id
        )

        if current_index is None:
            return True

        if candidate_index is None:
            return False

        if str(direction).upper() == "SOBO":
            return candidate_index < current_index

        return candidate_index > current_index

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
