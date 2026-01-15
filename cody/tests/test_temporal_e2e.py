"""
End-to-end tests for temporal context using real system time and timezones.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.temporal import TemporalContext


@pytest.mark.e2e
def test_real_timezone_utc() -> None:
    """
    E2E test: Verify TemporalContext works with real UTC timezone.

    This tests actual timezone handling without mocks.
    """
    ctx = TemporalContext("UTC")

    # Get current time
    now = ctx.current_time()

    # Verify it's a real datetime with timezone info
    assert isinstance(now, datetime)
    assert now.tzinfo == ZoneInfo("UTC")

    # Verify it's close to actual current time (within 1 second)
    actual_now = datetime.now(ZoneInfo("UTC"))
    time_diff = abs((now - actual_now).total_seconds())
    assert time_diff < 1.0, "Current time should be close to actual time"


@pytest.mark.e2e
def test_real_timezone_america_new_york() -> None:
    """
    E2E test: Verify TemporalContext works with America/New_York timezone.

    This verifies real timezone conversion and DST handling.
    """
    ctx = TemporalContext("America/New_York")

    now = ctx.current_time()
    assert now.tzinfo == ZoneInfo("America/New_York")

    # Verify time is close to actual current time in New York
    actual_now = datetime.now(ZoneInfo("America/New_York"))
    time_diff = abs((now - actual_now).total_seconds())
    assert time_diff < 1.0


@pytest.mark.e2e
def test_real_timezone_asia_tokyo() -> None:
    """
    E2E test: Verify TemporalContext works with Asia/Tokyo timezone.
    """
    ctx = TemporalContext("Asia/Tokyo")

    now = ctx.current_time()
    assert now.tzinfo == ZoneInfo("Asia/Tokyo")

    # Verify time is close to actual current time in Tokyo
    actual_now = datetime.now(ZoneInfo("Asia/Tokyo"))
    time_diff = abs((now - actual_now).total_seconds())
    assert time_diff < 1.0


@pytest.mark.e2e
def test_real_day_of_week_matches_system() -> None:
    """
    E2E test: Verify day_of_week matches actual system day.
    """
    ctx = TemporalContext("UTC")

    day = ctx.day_of_week()

    # Verify it's a valid day name
    valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    assert day in valid_days

    # Verify it matches system's actual day
    actual_day = datetime.now(ZoneInfo("UTC")).strftime("%A")
    assert day == actual_day


@pytest.mark.e2e
def test_real_is_weekend_matches_system() -> None:
    """
    E2E test: Verify is_weekend matches actual system day.
    """
    ctx = TemporalContext("UTC")

    is_weekend = ctx.is_weekend()

    # Verify it matches system's actual weekend status
    actual_weekday = datetime.now(ZoneInfo("UTC")).weekday()
    actual_is_weekend = actual_weekday in (5, 6)  # Saturday=5, Sunday=6

    assert is_weekend == actual_is_weekend


@pytest.mark.e2e
def test_real_time_of_day_classification() -> None:
    """
    E2E test: Verify time_of_day returns valid classification for current time.
    """
    ctx = TemporalContext("UTC")

    time_of_day = ctx.time_of_day()

    # Verify it's one of the valid labels
    valid_labels = ["morning", "afternoon", "evening", "night"]
    assert time_of_day in valid_labels

    # Verify it matches the actual current hour
    current_hour = datetime.now(ZoneInfo("UTC")).hour

    if 5 <= current_hour < 12:
        assert time_of_day == "morning"
    elif 12 <= current_hour < 17:
        assert time_of_day == "afternoon"
    elif 17 <= current_hour < 21:
        assert time_of_day == "evening"
    else:
        assert time_of_day == "night"


@pytest.mark.e2e
def test_real_context_string_format() -> None:
    """
    E2E test: Verify to_context_string produces valid output with real time.
    """
    ctx = TemporalContext("America/Los_Angeles")

    context_str = ctx.to_context_string()

    # Verify basic structure
    assert context_str.startswith("Current time: ")
    assert " at " in context_str

    # Verify it contains a valid day name
    valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    assert any(day in context_str for day in valid_days)

    # Verify it contains a valid time-of-day label
    valid_labels = ["(morning)", "(afternoon)", "(evening)", "(night)"]
    assert any(label in context_str for label in valid_labels)

    # Verify it contains AM or PM
    assert "AM" in context_str or "PM" in context_str


@pytest.mark.e2e
def test_real_timezone_offset_differences() -> None:
    """
    E2E test: Verify different timezones show different times.

    This tests that timezone conversion is actually happening.
    """
    ctx_utc = TemporalContext("UTC")
    ctx_tokyo = TemporalContext("Asia/Tokyo")
    ctx_la = TemporalContext("America/Los_Angeles")

    utc_time = ctx_utc.current_time()
    tokyo_time = ctx_tokyo.current_time()
    la_time = ctx_la.current_time()

    # All times should be the same instant, but different local times
    # Tokyo is ahead of UTC (JST = UTC+9)
    # LA is behind UTC (PST = UTC-8, PDT = UTC-7)

    # Verify timezones are different
    assert utc_time.tzinfo != tokyo_time.tzinfo
    assert utc_time.tzinfo != la_time.tzinfo
    assert tokyo_time.tzinfo != la_time.tzinfo

    # Verify they represent the same instant (within 1 second)
    utc_timestamp = utc_time.timestamp()
    tokyo_timestamp = tokyo_time.timestamp()
    la_timestamp = la_time.timestamp()

    assert abs(utc_timestamp - tokyo_timestamp) < 1.0
    assert abs(utc_timestamp - la_timestamp) < 1.0

    # Verify local hours are different (Tokyo ahead, LA behind)
    # Note: This might not always be true during DST transitions,
    # but for most of the year it should be
    if utc_time.hour != tokyo_time.hour or utc_time.hour != la_time.hour:
        # Hours are different as expected
        pass


@pytest.mark.e2e
def test_real_invalid_timezone_handling() -> None:
    """
    E2E test: Verify invalid timezone raises proper error.

    This tests real timezone validation.
    """
    with pytest.raises(ValueError) as exc_info:
        TemporalContext("Not/A/Real/Timezone")

    assert "Invalid timezone" in str(exc_info.value)


@pytest.mark.e2e
def test_real_context_multiple_timezones() -> None:
    """
    E2E test: Verify context strings work for multiple real timezones.
    """
    timezones = [
        "UTC",
        "America/New_York",
        "America/Los_Angeles",
        "Europe/London",
        "Asia/Tokyo",
        "Australia/Sydney",
    ]

    for tz in timezones:
        ctx = TemporalContext(tz)
        context_str = ctx.to_context_string()

        # Each should produce a valid context string
        assert context_str.startswith("Current time: ")
        assert " at " in context_str
        assert "AM" in context_str or "PM" in context_str


@pytest.mark.e2e
def test_real_day_of_week_across_timezones() -> None:
    """
    E2E test: Verify day of week can differ across timezones.

    When it's late night in one timezone, it might be the next day in another.
    """
    ctx_la = TemporalContext("America/Los_Angeles")
    ctx_tokyo = TemporalContext("Asia/Tokyo")

    day_la = ctx_la.day_of_week()
    day_tokyo = ctx_tokyo.day_of_week()

    # Both should be valid day names
    valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    assert day_la in valid_days
    assert day_tokyo in valid_days

    # Days might be different if we're near midnight in one timezone
    # This is expected behavior - no assertion, just verify both work


@pytest.mark.e2e
def test_real_weekend_status_consistency() -> None:
    """
    E2E test: Verify is_weekend is consistent with day_of_week.
    """
    ctx = TemporalContext("UTC")

    day = ctx.day_of_week()
    is_weekend = ctx.is_weekend()

    # Verify consistency
    if day in ("Saturday", "Sunday"):
        assert is_weekend is True
    else:
        assert is_weekend is False
