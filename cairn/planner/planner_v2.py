

from statistics import mean

from cairn.runtime.graph_runtime import (
    OperationalGraphRuntime,
)

from cairn.runtime.operational_queries import (
    OperationalQueries,
)

from cairn.runtime.traversal import (
    TraversalEngine,
)

from cairn.runtime.expedition_state import (
    ExpeditionStateEngine,
)


class PlannerV2:

    def __init__(
        self,
        trail_root,
        user_profile=None,
    ):

        self.runtime = (
            OperationalGraphRuntime(
                trail_root
            )
        )

        self.queries = (
            OperationalQueries(
                self.runtime
            )
        )

        self.traversal = (
            TraversalEngine(
                self.runtime
            )
        )

        self.state_engine = (
            ExpeditionStateEngine(
                self.runtime,
                user_profile=user_profile,
            )
        )

        self.user_profile = (
            user_profile or {}
        )

    def build_effort_model(self):

        profiles = (
            self.traversal
            .build_effort_profile()
        )

        effort_scores = [
            p["profile"][
                "effort_score"
            ]
            for p in profiles
        ]

        total_effort = round(
            sum(effort_scores),
            2,
        )

        avg_effort = round(
            mean(effort_scores),
            2,
        )

        return {
            "segments": len(profiles),
            "total_effort": total_effort,
            "average_effort": avg_effort,
        }

    def evaluate_completion_target(
        self,
        desired_days,
    ):

        effort_model = (
            self.build_effort_model()
        )

        total_effort = effort_model[
            "total_effort"
        ]

        required_daily_effort = round(
            total_effort / desired_days,
            2,
        )

        sustainable_capacity = (
            self.state_engine
            .base_capacity
        )

        ratio = (
            required_daily_effort /
            sustainable_capacity
        )

        if ratio <= 0.85:
            classification = "comfortable"
        elif ratio <= 1.0:
            classification = "challenging"
        elif ratio <= 1.25:
            classification = "aggressive"
        else:
            classification = "unrealistic"

        feasible = (
            classification != "unrealistic"
        )

        return {
            "desired_days": desired_days,
            "required_daily_effort": (
                required_daily_effort
            ),
            "sustainable_capacity": (
                sustainable_capacity
            ),
            "effort_ratio": round(
                ratio,
                2,
            ),
            "classification": classification,
            "feasible": feasible,
        }

    def negotiate_completion_target(
        self,
        desired_days,
    ):

        evaluation = (
            self.evaluate_completion_target(
                desired_days
            )
        )

        if evaluation["feasible"]:

            return {
                "accepted": True,
                "evaluation": evaluation,
                "recommendation": (
                    "Requested completion "
                    "target is operationally "
                    "feasible."
                ),
            }

        total_effort = (
            self.build_effort_model()[
                "total_effort"
            ]
        )

        sustainable_capacity = (
            self.state_engine
            .base_capacity
        )

        recommended_days = round(
            total_effort /
            sustainable_capacity
        )

        recommended_days = max(
            recommended_days,
            desired_days,
        )

        return {
            "accepted": False,
            "evaluation": evaluation,
            "recommended_days": (
                recommended_days
            ),
            "recommendation": (
                "Requested completion "
                "target exceeds sustainable "
                "operational cadence."
            ),
        }

    def build_operational_forecast(
        self,
    ):

        state_profile = (
            self.state_engine
            .simulate_full_trail_state()
        )

        final_state = state_profile[-1]

        peak_fatigue = max(
            x["fatigue"]
            for x in state_profile
        )

        degraded_segments = len([
            x for x in state_profile
            if x["state"] in [
                "degraded",
                "critical",
            ]
        ])

        return {
            "segments": len(state_profile),
            "peak_fatigue": round(
                peak_fatigue,
                2,
            ),
            "final_state": final_state[
                "state"
            ],
            "degraded_segments": (
                degraded_segments
            ),
        }

    def synthesize_itinerary(
        self,
        desired_days,
    ):

        negotiation = (
            self.negotiate_completion_target(
                desired_days
            )
        )

        forecast = (
            self.build_operational_forecast()
        )

        overlay_progression = (
            self.queries
            .list_overlay_progression()
        )

        overnight_nodes = (
            self.queries
            .get_overnight_nodes()
        )

        logistics_nodes = (
            self.queries
            .get_logistics_access_nodes()
        )

        return {
            "runtime_summary": (
                self.runtime.summary()
            ),
            "completion_analysis": (
                negotiation
            ),
            "forecast": forecast,
            "overlay_nodes": len(
                overlay_progression
            ),
            "overnight_nodes": len(
                overnight_nodes
            ),
            "logistics_nodes": len(
                logistics_nodes
            ),
        }