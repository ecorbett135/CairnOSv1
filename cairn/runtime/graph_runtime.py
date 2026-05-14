from pathlib import Path
import json


class OperationalGraphRuntime:

    def __init__(
        self,
        trail_root,
    ):

        self.trail_root = Path(trail_root)

        self.compiled_dir = (
            self.trail_root /
            "compiled"
        )

        self.graph_path = (
            self.compiled_dir /
            "operational_graph.json"
        )

        self.graph = self._load_graph()

        self.nodes = self.graph.get(
            "nodes",
            []
        )

        self.edges = self.graph.get(
            "edges",
            []
        )

        self.logistics = self.graph.get(
            "logistics_nodes",
            self.graph.get(
                "logistics",
                []
            ),
        )

        self.node_index = {
            n.get("node_id"): n
            for n in self.nodes
        }

    def _load_graph(self):

        if not self.graph_path.exists():

            raise FileNotFoundError(
                f"Missing graph: {self.graph_path}"
            )

        with open(self.graph_path) as f:

            return json.load(f)

    def get_nodes_by_type(
        self,
        node_type,
    ):

        return [
            n for n in self.nodes
            if n.get("node_type") == node_type
        ]

    def get_overlay_nodes(self):

        return self.get_nodes_by_type(
            "overlay"
        )

    def get_approach_nodes(self):

        return self.get_nodes_by_type(
            "approach"
        )

    def get_crossing_nodes(self):

        return self.get_nodes_by_type(
            "crossing"
        )

    def get_segment_nodes(self):

        return self.get_nodes_by_type(
            "segment"
        )

    def get_edges_by_type(
        self,
        edge_type,
    ):

        return [
            e for e in self.edges
            if e.get("edge_type") == edge_type
        ]

    def summary(self):

        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "overlay_nodes": len(
                self.get_overlay_nodes()
            ),
            "approach_nodes": len(
                self.get_approach_nodes()
            ),
            "crossings": len(
                self.get_crossing_nodes()
            ),
            "segments": len(
                self.get_segment_nodes()
            ),
            "logistics": len(
                self.logistics
            ),
        }
