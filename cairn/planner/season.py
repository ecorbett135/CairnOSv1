# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from datetime import date, datetime, timedelta


class SeasonAdvisoryPlanner:
    """Date-aware advisory prompts for PlannerV2."""

    def __init__(
        self,
        planner,
    ):

        self.planner = planner

    def normalize_start_date(
        self,
        value,
    ):

        if value in (
            None,
            "",
        ):
            return None

        if isinstance(
            value,
            datetime,
        ):
            return value.date()

        if isinstance(
            value,
            date,
        ):
            return value

        try:
            return date.fromisoformat(
                str(value).strip()[:10]
            )
        except (TypeError, ValueError):
            return None

    def trip_dates(
        self,
        start_date,
        completion_days,
    ):

        if not start_date:
            return []

        days = max(
            1,
            int(
                completion_days or 1
            ),
        )

        return [
            start_date + timedelta(
                days=offset
            )
            for offset in range(days)
        ]

    def date_in_month_day_window(
        self,
        value,
        start_month,
        start_day,
        end_month,
        end_day,
    ):

        current = (
            value.month,
            value.day,
        )
        start = (
            start_month,
            start_day,
        )
        end = (
            end_month,
            end_day,
        )

        if start <= end:
            return (
                start <= current <= end
            )

        return (
            current >= start
            or current <= end
        )

    def trip_overlaps_window(
        self,
        trip_dates,
        start_month,
        start_day,
        end_month,
        end_day,
    ):

        return any(
            self.date_in_month_day_window(
                trip_date,
                start_month,
                start_day,
                end_month,
                end_day,
            )
            for trip_date in trip_dates
        )

    def build_advisory(
        self,
        advisory_id,
        label,
        message,
        source_name,
        source_url,
        trip_start,
        trip_end,
        matched_window,
    ):

        return {
            "id": advisory_id,
            "advisory_id": advisory_id,
            "label": label,
            "message": message,
            "source_name": source_name,
            "source_url": source_url,
            "trip_start_date": (
                trip_start.isoformat()
            ),
            "trip_end_date": (
                trip_end.isoformat()
            ),
            "matched_window": matched_window,
            "advisory_only": True,
        }

    def build_season_advisories(
        self,
        completion_days,
    ):

        start_date = self.normalize_start_date(
            self.planner.start_date
        )

        if not start_date:
            return []

        trip_dates = self.trip_dates(
            start_date,
            completion_days,
        )
        trip_start = trip_dates[0]
        trip_end = trip_dates[-1]
        advisories = [
            self.build_advisory(
                "official_trail_updates",
                "Verify Official Trail Updates",
                (
                    "Verify current Green Mountain Club trail updates, "
                    "closures, weather forecasts, and field conditions "
                    "before using this plan. CairnOS does not provide "
                    "live condition status."
                ),
                "Green Mountain Club Trail Updates",
                "https://www.greenmountainclub.org/hiking/trail-updates/",
                trip_start,
                trip_end,
                "all planned trips",
            )
        ]

        if self.trip_overlaps_window(
            trip_dates,
            3,
            15,
            5,
            31,
        ):
            advisories.append(
                self.build_advisory(
                    "mud_season",
                    "Mud Season Awareness",
                    (
                        "The planned window overlaps Vermont mud-season "
                        "timing. Verify official trail guidance and be "
                        "prepared to change plans if trails are vulnerable "
                        "or closed. This advisory does not determine "
                        "whether a trail is currently open."
                    ),
                    "Green Mountain Club Mud Season Guidance",
                    "https://www.greenmountainclub.org/hiking/mud-season/",
                    trip_start,
                    trip_end,
                    "Mar 15-May 31",
                )
            )

        if self.trip_overlaps_window(
            trip_dates,
            6,
            1,
            7,
            15,
        ):
            advisories.append(
                self.build_advisory(
                    "peak_bugs",
                    "Peak Bug Season Awareness",
                    (
                        "The planned window overlaps early-summer bug "
                        "season. Treat this as packing and comfort context, "
                        "not a safety determination."
                    ),
                    "REI Expert Advice Long Trail Guide",
                    "https://www.rei.com/learn/expert-advice/how-to-hike-the-long-trail.html",
                    trip_start,
                    trip_end,
                    "Jun 1-Jul 15",
                )
            )

        if (
            self.trip_overlaps_window(
                trip_dates,
                3,
                15,
                5,
                31,
            )
            or self.trip_overlaps_window(
                trip_dates,
                10,
                1,
                11,
                15,
            )
        ):
            advisories.append(
                self.build_advisory(
                    "shoulder_snow_weather",
                    "Shoulder-Season Weather Awareness",
                    (
                        "The planned window overlaps shoulder-season "
                        "timing when snow, cold rain, or rapid weather "
                        "changes may affect planning. Verify current "
                        "forecasts and official trail conditions."
                    ),
                    "REI Expert Advice Long Trail Guide",
                    "https://www.rei.com/learn/expert-advice/how-to-hike-the-long-trail.html",
                    trip_start,
                    trip_end,
                    "Mar 15-May 31 or Oct 1-Nov 15",
                )
            )

        if self.trip_overlaps_window(
            trip_dates,
            10,
            1,
            12,
            15,
        ):
            advisories.append(
                self.build_advisory(
                    "hunting_visibility",
                    "Hunting Season Visibility Awareness",
                    (
                        "The planned window overlaps fall hunting-season "
                        "timing. Consider visibility and verify current "
                        "local regulations and trail notices."
                    ),
                    "REI Expert Advice Long Trail Guide",
                    "https://www.rei.com/learn/expert-advice/how-to-hike-the-long-trail.html",
                    trip_start,
                    trip_end,
                    "Oct 1-Dec 15",
                )
            )

        return advisories
