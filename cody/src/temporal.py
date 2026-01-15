"""
Temporal context for providing time awareness to the agent.

Provides current time, timezone, day of week, and time-of-day classification
for injection into system prompts.
"""

from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo


class TemporalContext:
    """
    Provides temporal context for the AI agent.

    Attributes:
        timezone: User's timezone (e.g., "America/Los_Angeles")
    """

    def __init__(self, timezone: str) -> None:
        """
        Initialize temporal context with a timezone.

        Args:
            timezone: User's timezone (e.g., "America/Los_Angeles")

        Raises:
            ValueError: If timezone is invalid or not recognized
        """
        try:
            # Validate timezone by trying to create ZoneInfo
            ZoneInfo(timezone)
            self.timezone = timezone
        except Exception as e:
            raise ValueError(f"Invalid timezone '{timezone}': {e}") from e

    def current_time(self) -> datetime:
        """
        Get the current time in the user's timezone.

        Returns:
            Current datetime in user's timezone
        """
        return datetime.now(ZoneInfo(self.timezone))

    def day_of_week(self) -> str:
        """
        Get the current day of the week.

        Returns:
            Day name (e.g., "Monday", "Tuesday", etc.)
        """
        return self.current_time().strftime("%A")

    def is_weekend(self) -> bool:
        """
        Check if the current day is a weekend (Saturday or Sunday).

        Returns:
            True if weekend, False otherwise
        """
        day = self.current_time().weekday()
        return day in (5, 6)  # Saturday=5, Sunday=6

    def time_of_day(self) -> Literal["morning", "afternoon", "evening", "night"]:
        """
        Classify current time into time-of-day period.

        Classification:
        - morning: 5:00 AM - 11:59 AM
        - afternoon: 12:00 PM - 4:59 PM
        - evening: 5:00 PM - 8:59 PM
        - night: 9:00 PM - 4:59 AM

        Returns:
            Time-of-day label
        """
        hour = self.current_time().hour

        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:  # 21-23, 0-4
            return "night"

    def to_context_string(self) -> str:
        """
        Generate a human-readable context string for prompt injection.

        Returns:
            Formatted string with temporal context, e.g.:
            "Current time: Tuesday, January 14, 2026 at 3:45 PM PST (afternoon)"
        """
        now = self.current_time()

        # Format: "Tuesday, January 14, 2026 at 3:45 PM PST"
        date_str = now.strftime("%A, %B %d, %Y")
        time_str = now.strftime("%I:%M %p").lstrip("0")  # Remove leading zero from hour
        tz_abbr = now.strftime("%Z")
        time_of_day = self.time_of_day()

        return f"Current time: {date_str} at {time_str} {tz_abbr} ({time_of_day})"
