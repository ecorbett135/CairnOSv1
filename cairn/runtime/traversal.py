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
