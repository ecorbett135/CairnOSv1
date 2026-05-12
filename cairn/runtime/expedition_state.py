from cairn.runtime.traversal import (
    TraversalEngine,
)


class ExpeditionStateEngine:

    def __init__(
        self,
        runtime,
        user_profile=None,
    ):

        self.runtime = runtime

        self.traversal = (
            TraversalEngine(runtime)
        )

        self.user_profile = (
            user_profile or {}
        )

        self.base_capacity = (
            self.user_profile.get(
                "base_capacity",
                24,
            )
        )

        self.recovery_rate = (
            self.user_profile.get(
                "recovery_rate",
                0.18,
            )
        )

        self.fatigue_resistance = (
            self.user_profile.get(
                "fatigue_resistance",
                1.0,
            )
        )

    def compute_daily_stress(
        self,
        effort_score,
    ):

        normalized = (
            effort_score /
            self.base_capacity
        )

        return round(
            normalized,
            2,
        )

    def compute_fatigue_accumulation(
        self,
        prior_fatigue,
        daily_stress,
    ):

        accumulation = (
            daily_stress *
            (1.0 / self.fatigue_resistance)
        )

        fatigue = (
            prior_fatigue +
            accumulation
        )

        return round(
            fatigue,
            2,
        )

    def compute_recovery(
        self,
        fatigue,
        recovery_quality=1.0,
    ):

        recovered = (
            fatigue -
            (
                self.recovery_rate *
                recovery_quality
            )
        )

        return round(
            max(recovered, 0),
            2,
        )

    def compute_operational_capacity(
        self,
        fatigue,
    ):

        degradation = min(
            fatigue * 0.12,
            0.65,
        )

        capacity = (
            self.base_capacity *
            (1.0 - degradation)
        )

        return round(
            max(capacity, 6),
            2,
        )

    def classify_state(
        self,
        fatigue,
    ):

        if fatigue < 0.75:
            return "fresh"

        if fatigue < 1.5:
            return "stable"

        if fatigue < 2.5:
            return "fatigued"

        if fatigue < 3.5:
            return "degraded"

        return "critical"

    def simulate_segment_sequence(
        self,
        segment_nodes,
    ):

        results = []

        fatigue = 0.0

        for node in segment_nodes:

            effort = (
                self.traversal
                .estimate_segment_effort(node)
            )

            stress = (
                self.compute_daily_stress(
                    effort[
                        "effort_score"
                    ]
                )
            )

            fatigue = (
                self.compute_fatigue_accumulation(
                    fatigue,
                    stress,
                )
            )

            operational_capacity = (
                self.compute_operational_capacity(
                    fatigue
                )
            )

            state = (
                self.classify_state(
                    fatigue
                )
            )

            results.append({
                "segment_id": node.get(
                    "segment_id"
                ),
                "distance": effort.get(
                    "distance"
                ),
                "gain_ft": effort.get(
                    "gain_ft"
                ),
                "difficulty": effort.get(
                    "difficulty"
                ),
                "effort_score": effort.get(
                    "effort_score"
                ),
                "daily_stress": stress,
                "fatigue": fatigue,
                "capacity": operational_capacity,
                "state": state,
            })

        return results

    def simulate_full_trail_state(
        self,
    ):

        segment_nodes = sorted(
            self.runtime.get_segment_nodes(),
            key=lambda x: (
                x.get(
                    "start_mile",
                    0,
                ) or 0
            ),
        )

        return self.simulate_segment_sequence(
            segment_nodes
        )