# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import csv
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

from cairn.planner.terrain import (
    TerrainAnalyzer,
)

from cairn.planner.logistics import (
    LogisticsPlanner,
)

from cairn.planner.itinerary import (
    ItineraryBuilder,
)

from cairn.planner.season import (
    SeasonAdvisoryPlanner,
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

        self.min_daily_miles = (
            self.user_profile.get(
                "min_daily_miles",
                8,
            )
        )

        self.max_daily_miles = (
            self.user_profile.get(
                "max_daily_miles",
                16,
            )
        )

        self.max_daily_elevation = (
            self.user_profile.get(
                "max_daily_elevation",
                3500,
            )
        )

        self.resupply_cadence = (
            self.user_profile.get(
                "resupply_cadence",
                5,
            )
        )

        self.recovery_cadence = (
            self.user_profile.get(
                "recovery_cadence",
                6,
            )
        )

        self.recovery_planning_mode = str(
            self.user_profile.get(
                "recovery_planning_mode",
                "cadence",
            )
            or "cadence"
        ).lower()

        if self.recovery_planning_mode not in {
            "cadence",
            "target_counts",
        }:
            self.recovery_planning_mode = "cadence"

        self.target_zero_days = max(
            0,
            int(
                self.user_profile.get(
                    "target_zero_days",
                    3,
                )
                or 0
            ),
        )

        self.target_nero_days = max(
            0,
            int(
                self.user_profile.get(
                    "target_nero_days",
                    2,
                )
                or 0
            ),
        )

        self.min_nero_miles = float(
            self.user_profile.get(
                "min_nero_miles",
                5.0,
            )
        )

        self.max_nero_miles = float(
            self.user_profile.get(
                "max_nero_miles",
                8.0,
            )
        )

        if (
            self.max_nero_miles
            < self.min_nero_miles
        ):
            self.max_nero_miles = (
                self.min_nero_miles
            )

        self.allow_extra_resupply_only = (
            self.user_profile.get(
                "allow_extra_resupply_only",
                True,
            )
        )

        self.avoid_long_food_carry = (
            self.user_profile.get(
                "avoid_long_food_carry",
                True,
            )
        )

        self.convenient_resupply_distance_miles = max(
            0.0,
            float(
                self.user_profile.get(
                    "convenient_resupply_distance_miles",
                    1.0,
                )
            ),
        )

        self.prefer_bear_box_sites = bool(
            self.user_profile.get(
                "prefer_bear_box_sites",
                False,
            )
        )

        self.selected_side_trip_ids = (
            self.user_profile.get(
                "selected_side_trip_ids",
                [],
            )
            or []
        )

        self.selected_town_ids = (
            self.user_profile.get(
                "selected_town_ids",
                [],
            )
            or []
        )

        self.start_date = (
            self.user_profile.get(
                "start_date",
                None,
            )
        )

        self.direction = (
            self.user_profile.get(
                "direction",
                "NOBO",
            )
        )

        self.ingress_route = (
            self.user_profile.get(
                "ingress_route",
                None,
            )
        )

        self.egress_route = (
            self.user_profile.get(
                "egress_route",
                None,
            )
        )

        self.section_start = (
            self.user_profile.get(
                "section_start",
                None,
            )
        )

        self.section_end = (
            self.user_profile.get(
                "section_end",
                None,
            )
        )

        self._terrain_samples = None
        self._route_master_elevation_samples = None
        self.terrain = TerrainAnalyzer(
            self
        )
        self.logistics = LogisticsPlanner(
            self
        )
        self.season = SeasonAdvisoryPlanner(
            self
        )
        self.itinerary_builder = ItineraryBuilder(
            self
        )


    def load_terrain_samples(
        self,
    ):
        return self.terrain.load_terrain_samples()

    def load_route_master_elevation_samples(
        self,
    ):
        return (
            self.terrain
            .load_route_master_elevation_samples()
        )

    def guidebook_mainline_range(
        self,
    ):
        return self.terrain.guidebook_mainline_range()

    def terrain_mile_range(
        self,
    ):
        return self.terrain.terrain_mile_range()

    def terrain_mile_reconciliation(
        self,
    ):
        return (
            self.terrain
            .terrain_mile_reconciliation()
        )

    def map_guidebook_to_terrain_mile(
        self,
        guidebook_mile,
    ):
        return (
            self.terrain
            .map_guidebook_to_terrain_mile(
                guidebook_mile
            )
        )

    def interpolate_elevation(
        self,
        samples,
        mile,
    ):
        return self.terrain.interpolate_elevation(
            samples,
            mile,
        )

    def analyze_sample_interval(
        self,
        samples,
        start_mile,
        stop_mile,
        source,
        reported_distance=None,
    ):
        return self.terrain.analyze_sample_interval(
            samples,
            start_mile,
            stop_mile,
            source,
            reported_distance=reported_distance,
        )

    def estimate_terrain_interval(
        self,
        start_mile,
        stop_mile,
    ):
        return self.terrain.estimate_terrain_interval(
            start_mile,
            stop_mile,
        )

    def analyze_terrain_interval(
        self,
        start_mile,
        stop_mile,
    ):
        return self.terrain.analyze_terrain_interval(
            start_mile,
            stop_mile,
        )

    def is_nero_distance(
        self,
        daily_miles,
    ):

        return (
            self.min_nero_miles
            <= daily_miles
            <= self.max_nero_miles
        )

    def calculate_terrain_adjusted_target(
        self,
        base_daily_target,
        day,
        current_mile=None,
        southern_mile=None,
        northern_mile=None,
    ):
        return (
            self.terrain
            .calculate_terrain_adjusted_target(
                base_daily_target,
                day,
                current_mile=current_mile,
                southern_mile=southern_mile,
                northern_mile=northern_mile,
            )
        )

    def calculate_daily_elevation(
        self,
        daily_miles,
        day,
    ):
        return self.terrain.calculate_daily_elevation(
            daily_miles,
            day,
        )

    def classification_rank(
        self,
        classification,
    ):

        ranks = {
            "comfortable": 0,
            "challenging": 1,
            "aggressive": 2,
            "unrealistic": 3,
        }

        return ranks.get(
            classification,
            0,
        )

    def max_classification(
        self,
        first,
        second,
    ):

        if (
            self.classification_rank(
                second
            )
            > self.classification_rank(
                first
            )
        ):
            return second

        return first

    def trail_duration_baseline(
        self,
        completion_days,
    ):

        trail_name = (
            getattr(
                self.runtime,
                "trail_root",
                None,
            )
        )

        if trail_name is not None:
            trail_name = trail_name.name

        if (
            trail_name
            != "vermont_long_trail"
            or self.user_profile.get(
                "trip_type"
            )
            != "THRU"
            or not completion_days
        ):
            return {
                "classification": "comfortable",
                "classification_reason": (
                    "no_trail_duration_baseline"
                ),
            }

        if completion_days < 20:
            return {
                "classification": "unrealistic",
                "classification_reason": (
                    "long_trail_duration_baseline"
                ),
            }

        if completion_days <= 24:
            return {
                "classification": "aggressive",
                "classification_reason": (
                    "long_trail_duration_baseline"
                ),
            }

        if completion_days <= 28:
            return {
                "classification": "challenging",
                "classification_reason": (
                    "long_trail_duration_baseline"
                ),
            }

        return {
            "classification": "comfortable",
            "classification_reason": (
                "long_trail_duration_baseline"
            ),
        }

    def summarize_itinerary_exceptions(
        self,
        daily_plan,
        resupply_plan=None,
    ):

        moving_rows = [
            row for row in daily_plan
            if row.get(
                "daily_miles",
                0,
            ) > 0
        ]

        exceptions = []

        mileage_rows = [
            row for row in moving_rows
            if row.get(
                "daily_miles",
                0,
            ) > self.max_daily_miles
        ]

        moving_day_count = len(
            moving_rows
        )

        if mileage_rows:

            observed_max = max(
                row.get(
                    "daily_miles",
                    0,
                )
                for row in mileage_rows
            )

            exceptions.append({
                "constraint": "daily_miles",
                "limit": self.max_daily_miles,
                "observed_max": round(
                    observed_max,
                    1,
                ),
                "count": len(
                    mileage_rows
                ),
                "days": [
                    row.get("day")
                    for row in mileage_rows
                ],
                "overage_percent": (
                    self.exception_overage_percent(
                        observed_max,
                        self.max_daily_miles,
                    )
                ),
                "severity": self.exception_severity(
                    observed_max,
                    self.max_daily_miles,
                    len(
                        mileage_rows
                    ),
                    moving_day_count,
                ),
            })

        elevation_rows = [
            row for row in moving_rows
            if row.get(
                "daily_elevation_gain",
                0,
            ) > self.max_daily_elevation
        ]

        if elevation_rows:

            observed_max = max(
                row.get(
                    "daily_elevation_gain",
                    0,
                )
                for row in elevation_rows
            )

            exceptions.append({
                "constraint": "daily_elevation_gain",
                "limit": self.max_daily_elevation,
                "observed_max": round(
                    observed_max,
                    0,
                ),
                "count": len(
                    elevation_rows
                ),
                "days": [
                    row.get("day")
                    for row in elevation_rows
                ],
                "overage_percent": (
                    self.exception_overage_percent(
                        observed_max,
                        self.max_daily_elevation,
                    )
                ),
                "severity": self.exception_severity(
                    observed_max,
                    self.max_daily_elevation,
                    len(
                        elevation_rows
                    ),
                    moving_day_count,
                ),
            })

        food_carry_exception = (
            self.summarize_food_carry_exception(
                resupply_plan,
                moving_day_count,
            )
        )

        if food_carry_exception:
            exceptions.append(
                food_carry_exception
            )

        recovery_exception = (
            self.summarize_recovery_cadence_exception(
                resupply_plan,
                moving_day_count,
            )
        )

        if recovery_exception:
            exceptions.append(
                recovery_exception
            )

        recovery_count_exception = (
            self.summarize_recovery_count_exception(
                daily_plan,
                moving_day_count,
            )
        )

        if recovery_count_exception:
            exceptions.append(
                recovery_count_exception
            )

        return exceptions

    def summarize_food_carry_exception(
        self,
        resupply_plan,
        moving_day_count,
    ):

        if (
            not resupply_plan
            or not self.resupply_cadence
        ):
            return None

        overage_rows = [
            row for row in resupply_plan
            if (
                row.get(
                    "days_to_next_resupply"
                )
                is not None
                and row.get(
                    "days_to_next_resupply"
                )
                > self.resupply_cadence
            )
        ]

        if not overage_rows:
            return None

        observed_max = max(
            row.get(
                "days_to_next_resupply",
                0,
            )
            for row in overage_rows
        )

        return {
            "constraint": "food_carry_days",
            "limit": self.resupply_cadence,
            "observed_max": observed_max,
            "count": len(
                overage_rows
            ),
            "days": [
                row.get("day")
                for row in overage_rows
            ],
            "overage_percent": (
                self.exception_overage_percent(
                    observed_max,
                    self.resupply_cadence,
                )
            ),
            "severity": (
                self.exception_severity(
                    observed_max,
                    self.resupply_cadence,
                    len(
                        overage_rows
                    ),
                    moving_day_count,
                )
            ),
        }

    def summarize_recovery_cadence_exception(
        self,
        resupply_plan,
        moving_day_count,
    ):

        if (
            self.recovery_planning_mode
            != "cadence"
            or not resupply_plan
            or not self.recovery_cadence
        ):
            return None

        overage_rows = [
            row for row in resupply_plan
            if (
                row.get(
                    "days_to_next_recovery"
                )
                is not None
                and row.get(
                    "days_to_next_recovery"
                )
                > self.recovery_cadence
            )
        ]

        if not overage_rows:
            return None

        observed_max = max(
            row.get(
                "days_to_next_recovery",
                0,
            )
            for row in overage_rows
        )

        return {
            "constraint": "recovery_cadence_days",
            "limit": self.recovery_cadence,
            "observed_max": observed_max,
            "count": len(
                overage_rows
            ),
            "days": [
                row.get("day")
                for row in overage_rows
            ],
            "overage_percent": (
                self.exception_overage_percent(
                    observed_max,
                    self.recovery_cadence,
                )
            ),
            "severity": (
                self.exception_severity(
                    observed_max,
                    self.recovery_cadence,
                    len(
                        overage_rows
                    ),
                    moving_day_count,
                )
            ),
        }

    def summarize_recovery_count_exception(
        self,
        daily_plan,
        moving_day_count,
    ):

        if (
            self.recovery_planning_mode
            != "target_counts"
        ):
            return None

        target_zero = self.target_zero_days
        target_nero = self.target_nero_days
        target_total = target_zero + target_nero

        if target_total <= 0:
            return None

        zero_count = 0
        nero_count = 0

        for row in daily_plan:
            notes = str(
                row.get("notes", "")
                or ""
            )

            if "zero" in notes:
                zero_count += 1

            if "nero" in notes:
                nero_count += 1

        missing_zero = max(
            0,
            target_zero - zero_count,
        )
        missing_nero = max(
            0,
            target_nero - nero_count,
        )
        missing_total = (
            missing_zero + missing_nero
        )

        if missing_total <= 0:
            return None

        observed_total = (
            zero_count + nero_count
        )

        missing_percent = round(
            missing_total
            / target_total
            * 100,
            1,
        )

        severity = "minor"

        if (
            missing_percent > 50.0
            or missing_total >= 3
        ):
            severity = "major"
        elif (
            missing_percent > 25.0
            or missing_total >= 2
        ):
            severity = "moderate"

        return {
            "constraint": "recovery_count_days",
            "limit": target_total,
            "observed_max": observed_total,
            "count": missing_total,
            "days": [],
            "overage_percent": missing_percent,
            "severity": severity,
            "target_zero_days": target_zero,
            "target_nero_days": target_nero,
            "actual_zero_days": zero_count,
            "actual_nero_days": nero_count,
            "missing_zero_days": missing_zero,
            "missing_nero_days": missing_nero,
        }

    def exception_overage_percent(
        self,
        observed,
        limit,
    ):

        if not limit:
            return 0.0

        return round(
            max(
                0.0,
                (
                    observed
                    - limit
                )
                / limit
                * 100,
            ),
            1,
        )

    def exception_severity(
        self,
        observed,
        limit,
        count,
        moving_day_count,
    ):

        if not limit:
            return "minor"

        overage_ratio = max(
            0.0,
            (
                observed
                - limit
            )
            / limit,
        )

        count_ratio = (
            count / moving_day_count
            if moving_day_count
            else 0.0
        )

        if (
            overage_ratio <= 0.10
            and count_ratio <= 0.15
        ):
            return "minor"

        if (
            overage_ratio <= 0.30
            and count_ratio <= 0.25
        ):
            return "moderate"

        return "major"

    def summarize_exception_pressure(
        self,
        daily_plan,
        exceptions=None,
    ):

        moving_rows = [
            row for row in daily_plan
            if row.get(
                "daily_miles",
                0,
            ) > 0
        ]

        moving_day_count = len(
            moving_rows
        )

        combined_days = []
        compound_days = []
        day_pressures = []
        max_mileage_ratio = 0.0
        max_elevation_ratio = 0.0
        max_food_carry_percent = 0.0
        food_carry_exception_count = 0
        max_recovery_cadence_percent = 0.0
        recovery_cadence_exception_count = 0
        max_recovery_count_percent = 0.0
        recovery_count_exception_count = 0

        for row in moving_rows:

            mileage_ratio = 0.0
            elevation_ratio = 0.0

            if self.max_daily_miles:
                mileage_ratio = max(
                    0.0,
                    (
                        row.get(
                            "daily_miles",
                            0,
                        )
                        - self.max_daily_miles
                    )
                    / self.max_daily_miles,
                )

            if self.max_daily_elevation:
                elevation_ratio = max(
                    0.0,
                    (
                        row.get(
                            "daily_elevation_gain",
                            0,
                        )
                        - self.max_daily_elevation
                    )
                    / self.max_daily_elevation,
                )

            max_mileage_ratio = max(
                max_mileage_ratio,
                mileage_ratio,
            )
            max_elevation_ratio = max(
                max_elevation_ratio,
                elevation_ratio,
            )

            if (
                mileage_ratio <= 0
                and elevation_ratio <= 0
            ):
                continue

            day = row.get("day")
            combined_days.append(day)

            day_pressure = (
                mileage_ratio
                + elevation_ratio
            )

            if (
                mileage_ratio > 0
                and elevation_ratio > 0
            ):
                compound_days.append(day)
                day_pressure += (
                    0.10
                    + min(
                        mileage_ratio,
                        elevation_ratio,
                    )
                )

            day_pressures.append(
                day_pressure
            )

        pressure_score = 0.0

        if moving_day_count:
            pressure_score = (
                sum(day_pressures)
                / moving_day_count
                * 100
            )

        exception_day_count = len(
            combined_days
        )
        exception_day_ratio = (
            exception_day_count
            / moving_day_count
            if moving_day_count
            else 0.0
        )
        max_mileage_percent = (
            max_mileage_ratio * 100
        )
        max_elevation_percent = (
            max_elevation_ratio * 100
        )

        for exception in exceptions or []:
            if (
                exception.get("constraint")
                != "food_carry_days"
            ):
                continue

            max_food_carry_percent = max(
                max_food_carry_percent,
                float(
                    exception.get(
                        "overage_percent",
                        0.0,
                    )
                    or 0.0
                ),
            )
            food_carry_exception_count += int(
                exception.get(
                    "count",
                    0,
                )
                or 0
            )

        for exception in exceptions or []:
            if (
                exception.get("constraint")
                != "recovery_cadence_days"
            ):
                continue

            max_recovery_cadence_percent = max(
                max_recovery_cadence_percent,
                float(
                    exception.get(
                        "overage_percent",
                        0.0,
                    )
                    or 0.0
                ),
            )
            recovery_cadence_exception_count += int(
                exception.get(
                    "count",
                    0,
                )
                or 0
            )

        for exception in exceptions or []:
            if (
                exception.get("constraint")
                != "recovery_count_days"
            ):
                continue

            max_recovery_count_percent = max(
                max_recovery_count_percent,
                float(
                    exception.get(
                        "overage_percent",
                        0.0,
                    )
                    or 0.0
                ),
            )
            recovery_count_exception_count += int(
                exception.get(
                    "count",
                    0,
                )
                or 0
            )

        food_carry_pressure = (
            max_food_carry_percent * 0.10
        )
        recovery_cadence_pressure = (
            max_recovery_cadence_percent * 0.15
        )
        recovery_count_pressure = (
            max_recovery_count_percent * 0.12
        )
        daily_preference_pressure = (
            (
                max_mileage_percent
                + max_elevation_percent
            )
            * 0.75
        )
        weighted_exception_pressure = (
            daily_preference_pressure
            + food_carry_pressure
            + recovery_cadence_pressure
            + recovery_count_pressure
        )

        return {
            "combined_exception_days": combined_days,
            "compound_exception_days": compound_days,
            "exception_pressure_score": round(
                pressure_score,
                1,
            ),
            "weighted_exception_pressure_percent": round(
                weighted_exception_pressure,
                1,
            ),
            "daily_preference_pressure_percent": round(
                daily_preference_pressure,
                1,
            ),
            "exception_day_count": exception_day_count,
            "exception_day_ratio": round(
                exception_day_ratio,
                3,
            ),
            "moving_day_count": moving_day_count,
            "max_mileage_overage_percent": round(
                max_mileage_percent,
                1,
            ),
            "max_elevation_overage_percent": round(
                max_elevation_percent,
                1,
            ),
            "max_food_carry_overage_percent": round(
                max_food_carry_percent,
                1,
            ),
            "food_carry_exception_count": (
                food_carry_exception_count
            ),
            "food_carry_pressure_percent": round(
                food_carry_pressure,
                1,
            ),
            "max_recovery_cadence_overage_percent": round(
                max_recovery_cadence_percent,
                1,
            ),
            "recovery_cadence_exception_count": (
                recovery_cadence_exception_count
            ),
            "recovery_cadence_pressure_percent": round(
                recovery_cadence_pressure,
                1,
            ),
            "max_recovery_count_overage_percent": round(
                max_recovery_count_percent,
                1,
            ),
            "recovery_count_exception_count": (
                recovery_count_exception_count
            ),
            "recovery_count_pressure_percent": round(
                recovery_count_pressure,
                1,
            ),
        }

    def classify_exception_pressure(
        self,
        exceptions,
        pressure,
    ):

        severities = {
            exception.get(
                "severity",
                "major",
            )
            for exception in exceptions
        }

        if not severities:
            return (
                "comfortable",
                "no_preference_exceptions",
            )

        constraint_names = {
            exception.get(
                "constraint",
                "",
            )
            for exception in exceptions
        }
        cadence_constraints = {
            "food_carry_days",
            "recovery_cadence_days",
            "recovery_count_days",
        }
        cadence_only = bool(
            constraint_names
        ) and constraint_names.issubset(
            cadence_constraints
        )

        if cadence_only:
            cadence_overage = max(
                pressure.get(
                    "max_food_carry_overage_percent",
                    0.0,
                ),
                pressure.get(
                    "max_recovery_cadence_overage_percent",
                    0.0,
                ),
                pressure.get(
                    "max_recovery_count_overage_percent",
                    0.0,
                ),
            )
            cadence_count = (
                pressure.get(
                    "food_carry_exception_count",
                    0,
                )
                + pressure.get(
                    "recovery_cadence_exception_count",
                    0,
                )
                + pressure.get(
                    "recovery_count_exception_count",
                    0,
                )
            )

            if severities == {
                "minor",
            }:
                return (
                    "comfortable",
                    "sparse_cadence_pressure",
                )

            if (
                cadence_overage >= 100.0
                and cadence_count >= 4
            ):
                return (
                    "aggressive",
                    "extreme_cadence_pressure",
                )

            return (
                "challenging",
                "cadence_preference_pressure",
            )

        if severities == {
            "minor",
        }:
            return (
                "comfortable",
                "sparse_preference_exceptions",
            )

        pressure_score = pressure.get(
            "exception_pressure_score",
            0.0,
        )
        weighted_pressure = pressure.get(
            "weighted_exception_pressure_percent",
            pressure_score,
        )
        daily_pressure = pressure.get(
            "daily_preference_pressure_percent",
            weighted_pressure,
        )
        max_single_overage = max(
            pressure.get(
                "max_mileage_overage_percent",
                0.0,
            ),
            pressure.get(
                "max_elevation_overage_percent",
                0.0,
            ),
        )
        exception_day_ratio = pressure.get(
            "exception_day_ratio",
            0.0,
        )
        combined_count = len(
            pressure.get(
                "combined_exception_days",
                [],
            )
        )
        compound_count = len(
            pressure.get(
                "compound_exception_days",
                [],
            )
        )

        if max_single_overage > 60.0:
            return (
                "aggressive",
                "extreme_preference_overage",
            )

        if exception_day_ratio > 0.30:
            return (
                "aggressive",
                "frequent_preference_pressure",
            )

        if compound_count > 2:
            return (
                "aggressive",
                "compound_exception_pressure",
            )

        if daily_pressure > 35.0:
            return (
                "aggressive",
                "high_weighted_preference_pressure",
            )

        if (
            combined_count <= 1
            and compound_count == 0
            and max_single_overage <= 30.0
        ):
            return (
                "comfortable",
                "sparse_preference_exceptions",
            )

        if (
            pressure_score <= 3.0
            and combined_count <= 2
            and compound_count <= 2
        ):
            return (
                "comfortable",
                "sparse_preference_exceptions",
            )

        if compound_count:
            return (
                "challenging",
                "moderate_weighted_preference_pressure",
            )

        return (
            "challenging",
            "repeated_preference_pressure",
        )

    def classify_generated_base(
        self,
        daily_plan,
    ):

        moving_rows = [
            row for row in daily_plan
            if row.get(
                "daily_miles",
                0,
            ) > 0
        ]

        if not moving_rows:
            return {
                "classification": "unrealistic",
                "feasible": False,
                "classification_reason": (
                    "no_moving_days"
                ),
                "moving_days": 0,
                "average_daily_miles": 0.0,
                "average_daily_elevation": 0.0,
            }

        average_miles = mean([
            row.get(
                "daily_miles",
                0,
            )
            for row in moving_rows
        ])
        average_elevation = mean([
            row.get(
                "daily_elevation_gain",
                0,
            )
            for row in moving_rows
        ])

        mileage_ratio = (
            average_miles / self.max_daily_miles
            if self.max_daily_miles
            else 0
        )
        elevation_ratio = (
            average_elevation
            / self.max_daily_elevation
            if self.max_daily_elevation
            else 0
        )
        generated_ratio = max(
            mileage_ratio,
            elevation_ratio,
        )

        if generated_ratio <= 0.85:
            classification = "comfortable"
        elif generated_ratio <= 1.0:
            classification = "challenging"
        elif generated_ratio <= 1.25:
            classification = "aggressive"
        else:
            classification = "unrealistic"

        completion_days = (
            daily_plan[-1].get(
                "day",
                len(daily_plan),
            )
            if daily_plan
            else len(moving_rows)
        )
        duration_baseline = (
            self.trail_duration_baseline(
                completion_days
            )
        )
        final_classification = (
            self.max_classification(
                classification,
                duration_baseline[
                    "classification"
                ],
            )
        )
        classification_reason = (
            duration_baseline[
                "classification_reason"
            ]
            if (
                self.classification_rank(
                    duration_baseline[
                        "classification"
                    ]
                )
                >= self.classification_rank(
                    classification
                )
                and duration_baseline[
                    "classification_reason"
                ]
                != "no_trail_duration_baseline"
            )
            else "generated_average_effort"
        )

        return {
            "classification": (
                final_classification
            ),
            "feasible": (
                final_classification
                != "unrealistic"
            ),
            "classification_reason": (
                classification_reason
            ),
            "effort_classification": (
                classification
            ),
            "duration_baseline_classification": (
                duration_baseline[
                    "classification"
                ]
            ),
            "completion_days": completion_days,
            "moving_days": len(
                moving_rows
            ),
            "average_daily_miles": round(
                average_miles,
                1,
            ),
            "average_daily_elevation": round(
                average_elevation,
                0,
            ),
            "generated_effort_ratio": round(
                generated_ratio,
                2,
            ),
        }

    def build_generated_evaluation(
        self,
        daily_plan,
        exceptions,
    ):

        generated = (
            self.classify_generated_base(
                daily_plan
            )
        )
        pressure = (
            self.summarize_exception_pressure(
                daily_plan,
                exceptions,
            )
        )
        (
            exception_classification,
            exception_reason,
        ) = self.classify_exception_pressure(
            exceptions,
            pressure,
        )

        final_classification = (
            self.max_classification(
                generated[
                    "classification"
                ],
                exception_classification,
            )
        )

        if (
            self.classification_rank(
                exception_classification
            )
            >= self.classification_rank(
                generated[
                    "classification"
                ]
            )
        ):
            classification_reason = (
                exception_reason
            )
        else:
            classification_reason = (
                generated.get(
                    "classification_reason",
                    "generated_average_effort",
                )
            )

        return {
            **generated,
            **pressure,
            "classification": (
                final_classification
            ),
            "feasible": (
                final_classification
                != "unrealistic"
            ),
            "classification_reason": (
                classification_reason
            ),
        }

    def apply_itinerary_exceptions(
        self,
        completion_analysis,
        daily_plan,
        resupply_plan=None,
    ):

        exceptions = (
            self.summarize_itinerary_exceptions(
                daily_plan,
                resupply_plan,
            )
        )

        updated = {
            **completion_analysis,
        }

        requested_evaluation = {
            **updated.get(
                "requested_evaluation",
                updated.get(
                    "evaluation",
                    {},
                ),
            )
        }

        generated_evaluation = (
            self.build_generated_evaluation(
                daily_plan,
                exceptions,
            )
        )

        updated["accepted"] = not updated.get(
            "completion_extended",
            False,
        )
        updated["requested_evaluation"] = (
            requested_evaluation
        )
        updated["generated_evaluation"] = (
            generated_evaluation
        )
        updated["evaluation"] = (
            generated_evaluation
        )
        updated["has_itinerary_exceptions"] = bool(
            exceptions
        )
        updated["itinerary_exceptions"] = exceptions
        updated["combined_exception_days"] = (
            generated_evaluation.get(
                "combined_exception_days",
                [],
            )
        )
        updated["compound_exception_days"] = (
            generated_evaluation.get(
                "compound_exception_days",
                [],
            )
        )
        updated["exception_pressure_score"] = (
            generated_evaluation.get(
                "exception_pressure_score",
                0.0,
            )
        )
        updated["weighted_exception_pressure_percent"] = (
            generated_evaluation.get(
                "weighted_exception_pressure_percent",
                0.0,
            )
        )
        updated["exception_day_count"] = (
            generated_evaluation.get(
                "exception_day_count",
                0,
            )
        )
        updated["exception_day_ratio"] = (
            generated_evaluation.get(
                "exception_day_ratio",
                0.0,
            )
        )
        updated["classification_reason"] = (
            generated_evaluation.get(
                "classification_reason",
                "generated_average_effort",
            )
        )

        if updated.get(
            "completion_extended",
            False,
        ):
            updated["recommendation"] = (
                "Requested completion target would require unrealistic "
                "catch-up days, so an extended itinerary was generated. "
                "The generated plan is classified separately."
            )
            updated["exception_guidance"] = (
                "Use the recommended day count or adjust mileage, "
                "recovery, and elevation preferences for a gentler plan."
            )
        else:
            if not exceptions:
                updated["recommendation"] = (
                    "Requested completion target is operationally "
                    "feasible."
                )
                updated["exception_guidance"] = (
                    "No daily mileage, elevation, or food-carry "
                    "preference exceptions were detected."
                )

            elif (
                generated_evaluation[
                    "classification"
                ]
                == "comfortable"
            ):
                updated["recommendation"] = (
                    "Requested completion target is achievable. "
                    "The generated itinerary has only sparse "
                    "preference exceptions."
                )
            elif (
                generated_evaluation[
                    "classification"
                ]
                == "challenging"
            ):
                updated["recommendation"] = (
                    "Requested completion target is achievable, but the "
                    "generated itinerary has repeated or moderate "
                    "preference pressure."
                )
            else:
                updated["recommendation"] = (
                    "Requested completion target is achievable, but the "
                    "generated itinerary has major or frequent "
                    "preference pressure."
                )

            updated["exception_guidance"] = (
                "Review exception days or adjust completion days, mileage, "
                "or elevation preferences for a gentler plan."
            )

        return updated

    def apply_completion_extension(
        self,
        completion_analysis,
        actual_days,
    ):

        expected_days = (
            completion_analysis.get(
                "desired_days"
            )
            or (
                completion_analysis.get(
                    "evaluation",
                    {},
                ).get("desired_days")
            )
            or actual_days
        )

        recommended_days = (
            completion_analysis.get(
                "recommended_days"
            )
            or expected_days
        )

        if (
            actual_days <= expected_days
            and recommended_days <= expected_days
        ):
            return completion_analysis

        updated = {
            **completion_analysis,
        }

        evaluation = {
            **updated.get(
                "evaluation",
                {},
            )
        }

        evaluation["classification"] = (
            self.max_classification(
                evaluation.get(
                    "classification",
                    "comfortable",
                ),
                "aggressive",
            )
        )
        evaluation["feasible"] = (
            evaluation[
                "classification"
            ]
            != "unrealistic"
        )
        evaluation["classification_reason"] = (
            "extended_requested_target"
        )

        updated["accepted"] = False
        updated["evaluation"] = evaluation
        updated["requested_evaluation"] = (
            evaluation
        )
        updated["completion_extended"] = True
        updated["requested_days"] = expected_days
        updated["recommended_days"] = max(
            recommended_days,
            actual_days,
        )
        updated["extension_days"] = (
            updated["recommended_days"]
            - expected_days
        )
        updated["recommendation"] = (
            "Requested completion target would require unrealistic "
            "catch-up days, so an extended itinerary was generated."
        )

        return updated

    def should_insert_recovery_day(
        self,
        day,
    ):

        cadence_window = [
            self.recovery_cadence - 1,
            self.recovery_cadence,
            self.recovery_cadence + 1,
        ]

        return day in cadence_window

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
            self.max_daily_miles
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

        duration_baseline = (
            self.trail_duration_baseline(
                desired_days
            )
        )
        final_classification = (
            self.max_classification(
                classification,
                duration_baseline[
                    "classification"
                ],
            )
        )
        classification_reason = (
            duration_baseline[
                "classification_reason"
            ]
            if (
                self.classification_rank(
                    duration_baseline[
                        "classification"
                    ]
                )
                >= self.classification_rank(
                    classification
                )
                and duration_baseline[
                    "classification_reason"
                ]
                != "no_trail_duration_baseline"
            )
            else "requested_effort_ratio"
        )

        feasible = (
            final_classification
            != "unrealistic"
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
            "classification": (
                final_classification
            ),
            "effort_classification": (
                classification
            ),
            "duration_baseline_classification": (
                duration_baseline[
                    "classification"
                ]
            ),
            "classification_reason": (
                classification_reason
            ),
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
                "requested_evaluation": (
                    evaluation
                ),
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
            self.max_daily_miles
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
            "requested_evaluation": (
                evaluation
            ),
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

    def build_expedition_summary(
        self,
        completion_days,
        daily_plan=None,
    ):

        effort_model = (
            self.build_effort_model()
        )

        total_miles = 272.0

        moving_rows = [
            row for row in (
                daily_plan or []
            )
            if row.get(
                "daily_miles",
                0,
            ) > 0
        ]

        moving_days = (
            len(moving_rows)
            or completion_days
        )

        average_daily_miles = round(
            total_miles /
            moving_days,
            1,
        )

        total_elevation_gain = (
            sum(
                row.get(
                    "daily_elevation_gain",
                    0,
                )
                for row in moving_rows
            )
            if moving_rows
            else 62129
        )

        average_daily_elevation = round(
            total_elevation_gain /
            moving_days,
            0,
        )

        return {
            "total_miles": total_miles,
            "completion_days": completion_days,
            "moving_days": moving_days,
            "average_daily_miles": average_daily_miles,
            "average_daily_elevation": average_daily_elevation,
        }

    def _resolve_ingress_node(self):
        """
        Resolve the ingress node for the selected ingress route.
        
        Honors approach trail semantics:
        - Uses runtime.get_approach_nodes() instead of hardcoded searches
        - Filters by approach_name matching ingress_route
        - Returns appropriate endpoint based on direction
        - Preserves negative mileage semantics
        
        Returns:
            dict with keys:
            - node: the resolved approach node
            - location_type: trailhead or terminus
            - mile: the cumulative_to_trail_mi value
            - location_name: canonical name for the location
            OR None if ingress route is main terminus
        """
        
        if not self.ingress_route:
            return None

        approach_nodes = (
            self.runtime
            .get_approach_nodes()
        )

        filtered_nodes = [
            n for n in approach_nodes
            if n.get("approach_name", "").strip().lower() == (
                self.ingress_route.strip().lower()
            )
        ]

        if not filtered_nodes:
            return None

        sorted_nodes = sorted(
            filtered_nodes,
            key=lambda n: n.get(
                "cumulative_to_trail_mi",
                0,
            )
        )

        if self.direction == "NOBO":
            entry_node = sorted_nodes[0]
        elif self.direction == "SOBO":
            entry_node = sorted_nodes[-1]
        else:
            entry_node = sorted_nodes[0]

        ingress_mile = round(
            entry_node.get(
                "cumulative_to_trail_mi",
                0,
            ),
            1,
        )

        approach_name = entry_node.get(
            "approach_name",
            "Approach Trail"
        )

        node_class = entry_node.get(
            "node_class",
            "trailhead"
        )

        return {
            "node": entry_node,
            "location_type": node_class,
            "mile": ingress_mile,
            "location_name": approach_name,
        }

    def load_approach_records(
        self,
    ):

        if hasattr(
            self,
            "_approach_records",
        ):
            return self._approach_records

        path = (
            self.runtime.trail_root /
            "raw" /
            "csv" /
            "approach_trails.csv"
        )

        if not path.exists():
            self._approach_records = []
            return self._approach_records

        records = []

        with open(
            path,
            newline="",
        ) as handle:

            reader = csv.DictReader(handle)

            for row in reader:

                mile = self.parse_float(
                    row.get(
                        "cumulative_to_trail_mi"
                    )
                )

                if mile is None:
                    continue

                records.append({
                    "approach_id": row.get(
                        "approach_id",
                        "",
                    ),
                    "approach_name": row.get(
                        "approach_name",
                        "",
                    ),
                    "route_name": row.get(
                        "route_name",
                        "",
                    ),
                    "location": row.get(
                        "location",
                        "",
                    ),
                    "node_class": row.get(
                        "node_class",
                        "trailhead",
                    ),
                    "mile": mile,
                    "sequence": self.parse_float(
                        row.get("sequence")
                    ),
                    "road_access": self.parse_bool(
                        row.get("road_access")
                    ),
                })

        self._approach_records = records
        return self._approach_records

    def _resolve_egress_node(self):

        if not self.egress_route:
            return None

        records = [
            row
            for row in self.load_approach_records()
            if row.get(
                "approach_name",
                "",
            ).strip().lower()
            == self.egress_route.strip().lower()
        ]

        if not records:
            return None

        if self.is_sobo():
            endpoint = min(
                records,
                key=lambda row: row.get(
                    "mile",
                    0,
                ),
            )
        else:
            endpoint = max(
                records,
                key=lambda row: row.get(
                    "mile",
                    0,
                ),
            )

        location_name = (
            endpoint.get("location")
            or endpoint.get("approach_name")
            or "Egress Trailhead"
        )

        return {
            "canonical_name": location_name,
            "trail_mile": round(
                endpoint.get("mile"),
                1,
            ),
            "node_class": endpoint.get(
                "node_class",
                "trailhead",
            ),
            "division": (
                "division0"
                if endpoint.get("mile", 0) <= 0
                else "division12"
            ),
            "egress_route": endpoint.get(
                "approach_name"
            ),
        }

    def get_directional_access(
        self,
    ):

        approach_nodes = (
            self.runtime
            .get_approach_nodes()
        )

        grouped = {}

        for node in approach_nodes:

            approach_id = node.get(
                "approach_id",
                "unknown"
            )

            if approach_id not in grouped:
                grouped[approach_id] = []

            grouped[approach_id].append(node)

        ingress = []
        egress = []

        for _, nodes in grouped.items():

            sorted_nodes = sorted(
                nodes,
                key=lambda n: n.get(
                    "cumulative_to_trail_mi",
                    0,
                )
            )

            first_node = sorted_nodes[0]
            last_node = sorted_nodes[-1]

            approach_name = first_node.get(
                "approach_name",
                "Unknown"
            )

            if self.direction == "NOBO":

                if "journey" in approach_name.lower():
                    egress.append(first_node)
                else:
                    ingress.append(first_node)

            elif self.direction == "SOBO":

                if "journey" in approach_name.lower():
                    ingress.append(first_node)
                else:
                    egress.append(first_node)

        return {
            "ingress": ingress,
            "egress": egress,
        }

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

    def is_sobo(
        self,
    ):

        return (
            str(self.direction)
            .strip()
            .upper()
            == "SOBO"
        )

    def mainline_northern_mile(
        self,
        overlay_nodes,
    ):

        miles = [
            self.node_mile(node)
            for node in overlay_nodes
            if self.node_mile(node) is not None
        ]

        if not miles:
            return 272.0

        return round(
            max(miles),
            1,
        )

    def mainline_southern_mile(
        self,
    ):

        return 0.0

    def target_mile_for_distance(
        self,
        current_mile,
        distance,
        southern_mile,
        northern_mile,
    ):

        if self.is_sobo():
            return round(
                max(
                    southern_mile,
                    current_mile - distance,
                ),
                1,
            )

        return round(
            min(
                northern_mile,
                current_mile + distance,
            ),
            1,
        )

    def travel_distance(
        self,
        start_mile,
        stop_mile,
    ):

        return round(
            abs(stop_mile - start_mile),
            1,
        )

    def reached_route_end(
        self,
        current_mile,
        southern_mile,
        northern_mile,
    ):

        if self.is_sobo():
            return (
                current_mile <= southern_mile
            )

        return (
            current_mile >= northern_mile
        )

    def is_forward_progress(
        self,
        current_mile,
        candidate_mile,
    ):

        return self.traversal.is_forward_progress(
            self.direction,
            current_mile,
            candidate_mile,
        )

    def mile_in_travel_window(
        self,
        start_mile,
        stop_mile,
        candidate_mile,
        include_start=False,
        include_stop=True,
    ):

        return self.traversal.mile_in_travel_window(
            self.direction,
            start_mile,
            stop_mile,
            candidate_mile,
            include_start=include_start,
            include_stop=include_stop,
        )

    def build_overlay_corridor(
        self,
        start_mile=None,
        stop_mile=None,
        start_overlay_id=None,
        stop_overlay_id=None,
    ):

        return self.traversal.build_overlay_corridor(
            self.direction,
            start_mile=start_mile,
            stop_mile=stop_mile,
            start_overlay_id=start_overlay_id,
            stop_overlay_id=stop_overlay_id,
        )

    def corridor_nodes_between(
        self,
        start_mile,
        stop_mile,
        include_start=False,
        include_stop=True,
        start_overlay_id=None,
        stop_overlay_id=None,
    ):

        return self.traversal.corridor_nodes_between(
            self.direction,
            start_mile,
            stop_mile,
            include_start=include_start,
            include_stop=include_stop,
            start_overlay_id=start_overlay_id,
            stop_overlay_id=stop_overlay_id,
        )

    def resolve_overlay_reference(
        self,
        node=None,
        mile=None,
        canonical_name=None,
        corridor_nodes=None,
        max_mile_delta=0.15,
    ):

        return self.traversal.resolve_overlay_reference(
            node=node,
            mile=mile,
            canonical_name=canonical_name,
            corridor_nodes=corridor_nodes,
            max_mile_delta=max_mile_delta,
        )

    def overlay_index(
        self,
        node_or_id,
    ):

        return self.traversal.overlay_index(
            node_or_id
        )

    def is_forward_overlay_progress(
        self,
        current_overlay_id,
        candidate_overlay_id,
    ):

        return (
            self.traversal
            .is_forward_overlay_progress(
                self.direction,
                current_overlay_id,
                candidate_overlay_id,
            )
        )

    def extended_target_mile(
        self,
        current_mile,
        target_mile,
        southern_mile,
        northern_mile,
    ):

        if self.is_sobo():
            lower_mile = max(
                southern_mile,
                target_mile - 3.0,
                current_mile
                - self.max_daily_miles
                - 4.0,
            )

            return round(
                lower_mile,
                1,
            )

        upper_mile = min(
            northern_mile,
            target_mile + 3.0,
            current_mile
            + self.max_daily_miles
            + 4.0,
        )

        return round(
            upper_mile,
            1,
        )

    def resupply_node_id(
        self,
        node,
    ):
        return self.logistics.resupply_node_id(
            node
        )

    def parse_bool(
        self,
        value,
    ):
        return self.logistics.parse_bool(
            value
        )

    def parse_float(
        self,
        value,
    ):
        return self.logistics.parse_float(
            value
        )

    def normalize_match_tokens(
        self,
        value,
    ):
        return self.logistics.normalize_match_tokens(
            value
        )

    def load_resupply_amenities(
        self,
    ):
        return (
            self.logistics
            .load_resupply_amenities()
        )

    def find_overlay_for_amenity(
        self,
        amenity,
        overlay_nodes,
    ):
        return (
            self.logistics
            .find_overlay_for_amenity(
                amenity,
                overlay_nodes,
            )
        )

    def services_from_amenity(
        self,
        amenity,
    ):
        return self.logistics.services_from_amenity(
            amenity
        )

    def build_logistics_candidates(
        self,
    ):
        return (
            self.logistics
            .build_logistics_candidates()
        )

    def is_resupply_candidate(
        self,
        node,
    ):
        return self.logistics.is_resupply_candidate(
            node
        )

    def is_recovery_candidate(
        self,
        node,
    ):
        return self.logistics.is_recovery_candidate(
            node
        )

    def score_resupply_candidate(
        self,
        node,
    ):
        return self.logistics.score_resupply_candidate(
            node
        )

    def access_distance_miles(
        self,
        node,
    ):
        return self.logistics.access_distance_miles(
            node
        )

    def score_recovery_candidate(
        self,
        node,
    ):
        return self.logistics.score_recovery_candidate(
            node
        )

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
        return (
            self.logistics
            .select_resupply_for_day(
                start_mile,
                stop_mile,
                day,
                last_resupply_day,
                resupply_nodes,
                used_resupply_ids,
                terminal_mile=terminal_mile,
            )
        )

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
        return (
            self.logistics
            .select_recovery_for_day(
                start_mile,
                target_mile,
                day,
                last_recovery_day,
                logistics_candidates,
                used_recovery_ids,
                completion_days=completion_days,
                placed_zero_count=placed_zero_count,
                placed_nero_count=placed_nero_count,
            )
        )

    def build_logistics_note(
        self,
        resupply_node=None,
        recovery_kind=None,
    ):
        return self.logistics.build_logistics_note(
            resupply_node=resupply_node,
            recovery_kind=recovery_kind,
        )

    def build_resupply_note(
        self,
        resupply_node,
        day,
        last_resupply_day,
    ):
        return self.logistics.build_resupply_note(
            resupply_node,
            day,
            last_resupply_day,
        )

    def build_resupply_plan(
        self,
        daily_plan=None,
    ):
        return self.logistics.build_resupply_plan(
            daily_plan=daily_plan
        )

    def build_resupply_town_details(
        self,
        resupply_plan=None,
    ):
        return (
            self.logistics
            .build_resupply_town_details(
                resupply_plan=resupply_plan,
            )
        )

    def build_selected_experiences(
        self,
        resupply_plan=None,
    ):
        return (
            self.logistics
            .build_selected_experiences(
                resupply_plan=resupply_plan,
            )
        )

    def annotate_daily_plan_with_side_trips(
        self,
        daily_plan,
    ):
        return (
            self.logistics
            .annotate_daily_plan_with_side_trips(
                daily_plan
            )
        )

    def select_operational_stop(
        self,
        target_mile,
        operational_overnight_nodes,
        logistics_nodes,
        current_mile=None,
        corridor_nodes=None,
    ):
        return (
            self.itinerary_builder
            .select_operational_stop(
                target_mile,
                operational_overnight_nodes,
                logistics_nodes,
                current_mile=current_mile,
                corridor_nodes=corridor_nodes,
            )
        )

    def build_daily_itinerary(
        self,
        completion_days,
    ):
        return (
            self.itinerary_builder
            .build_daily_itinerary(
                completion_days
            )
        )

    def build_season_advisories(
        self,
        completion_days,
    ):
        return (
            self.season
            .build_season_advisories(
                completion_days
            )
        )

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

        operational_overnight_nodes = (
            self.queries
            .get_operational_overnight_nodes()
        )

        logistics_nodes = (
            self.queries
            .get_logistics_access_nodes()
        )

        recommended_days = (
            negotiation.get(
                "recommended_days",
                desired_days,
            )
        )

        directional_access = (
            self.get_directional_access()
        )

        daily_plan = (
            self.build_daily_itinerary(
                recommended_days
            )
        )

        actual_completion_days = (
            daily_plan[-1]["day"]
            if daily_plan
            else recommended_days
        )

        completion_analysis = (
            self.apply_completion_extension(
                negotiation,
                actual_completion_days,
            )
        )

        expedition_summary = (
            self.build_expedition_summary(
                actual_completion_days,
                daily_plan,
            )
        )

        resupply_plan = (
            self.build_resupply_plan(
                daily_plan
            )
        )

        completion_analysis = (
            self.apply_itinerary_exceptions(
                completion_analysis,
                daily_plan,
                resupply_plan,
            )
        )
        resupply_town_details = (
            self.build_resupply_town_details(
                resupply_plan
            )
        )
        selected_experiences = (
            self.build_selected_experiences(
                resupply_plan
            )
        )
        daily_plan = (
            self.annotate_daily_plan_with_side_trips(
                daily_plan
            )
        )

        season_advisories = (
            self.build_season_advisories(
                actual_completion_days
            )
        )

        return {
            "completion_analysis": (
                completion_analysis
            ),
            "expedition_summary": (
                expedition_summary
            ),
            "resupply_plan": (
                resupply_plan
            ),
            "resupply_town_details": (
                resupply_town_details
            ),
            "selected_experiences": (
                selected_experiences
            ),
            "directional_access": (
                directional_access
            ),
            "season_advisories": (
                season_advisories
            ),
            "daily_plan": (
                daily_plan
            ),
        }
