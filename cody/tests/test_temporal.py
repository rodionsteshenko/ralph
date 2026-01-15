"""
Unit tests for temporal context system.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from src.temporal import TemporalContext


@pytest.mark.unit
def test_temporal_context_creation() -> None:
    """Test creating a temporal context with valid timezone."""
    ctx = TemporalContext("America/Los_Angeles")
    assert ctx.timezone == "America/Los_Angeles"


@pytest.mark.unit
def test_temporal_context_creation_with_utc() -> None:
    """Test creating a temporal context with UTC timezone."""
    ctx = TemporalContext("UTC")
    assert ctx.timezone == "UTC"


@pytest.mark.unit
def test_temporal_context_invalid_timezone() -> None:
    """Test that invalid timezone raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        TemporalContext("Invalid/Timezone")

    assert "Invalid timezone" in str(exc_info.value)


@pytest.mark.unit
def test_temporal_context_empty_timezone() -> None:
    """Test that empty timezone raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        TemporalContext("")

    assert "Invalid timezone" in str(exc_info.value)


@pytest.mark.unit
def test_current_time_returns_datetime() -> None:
    """Test that current_time returns a datetime object."""
    ctx = TemporalContext("UTC")
    now = ctx.current_time()

    assert isinstance(now, datetime)
    assert now.tzinfo is not None


@pytest.mark.unit
def test_current_time_uses_correct_timezone() -> None:
    """Test that current_time uses the specified timezone."""
    ctx = TemporalContext("America/New_York")
    now = ctx.current_time()

    # Check that tzinfo matches the timezone
    assert now.tzinfo == ZoneInfo("America/New_York")


@pytest.mark.unit
@patch("src.temporal.datetime")
def test_day_of_week_monday(mock_datetime: MagicMock) -> None:
    """Test day_of_week returns 'Monday' for Monday."""
    # Mock datetime.now() to return a Monday
    mock_now = datetime(2026, 1, 12, 10, 0, 0, tzinfo=ZoneInfo("UTC"))  # Monday
    mock_datetime.now.return_value = mock_now

    ctx = TemporalContext("UTC")
    assert ctx.day_of_week() == "Monday"


@pytest.mark.unit
@patch("src.temporal.datetime")
def test_day_of_week_friday(mock_datetime: MagicMock) -> None:
    """Test day_of_week returns 'Friday' for Friday."""
    mock_now = datetime(2026, 1, 16, 10, 0, 0, tzinfo=ZoneInfo("UTC"))  # Friday
    mock_datetime.now.return_value = mock_now

    ctx = TemporalContext("UTC")
    assert ctx.day_of_week() == "Friday"


@pytest.mark.unit
@patch("src.temporal.datetime")
def test_is_weekend_saturday(mock_datetime: MagicMock) -> None:
    """Test is_weekend returns True for Saturday."""
    mock_now = datetime(2026, 1, 17, 10, 0, 0, tzinfo=ZoneInfo("UTC"))  # Saturday
    mock_datetime.now.return_value = mock_now

    ctx = TemporalContext("UTC")
    assert ctx.is_weekend() is True


@pytest.mark.unit
@patch("src.temporal.datetime")
def test_is_weekend_sunday(mock_datetime: MagicMock) -> None:
    """Test is_weekend returns True for Sunday."""
    mock_now = datetime(2026, 1, 18, 10, 0, 0, tzinfo=ZoneInfo("UTC"))  # Sunday
    mock_datetime.now.return_value = mock_now

    ctx = TemporalContext("UTC")
    assert ctx.is_weekend() is True


@pytest.mark.unit
@patch("src.temporal.datetime")
def test_is_weekend_monday(mock_datetime: MagicMock) -> None:
    """Test is_weekend returns False for Monday."""
    mock_now = datetime(2026, 1, 12, 10, 0, 0, tzinfo=ZoneInfo("UTC"))  # Monday
    mock_datetime.now.return_value = mock_now

    ctx = TemporalContext("UTC")
    assert ctx.is_weekend() is False


@pytest.mark.unit
@patch("src.temporal.datetime")
def test_is_weekend_friday(mock_datetime: MagicMock) -> None:
    """Test is_weekend returns False for Friday."""
    mock_now = datetime(2026, 1, 16, 10, 0, 0, tzinfo=ZoneInfo("UTC"))  # Friday
    mock_datetime.now.return_value = mock_now

    ctx = TemporalContext("UTC")
    assert ctx.is_weekend() is False


@pytest.mark.unit
@patch("src.temporal.datetime")
def test_time_of_day_morning(mock_datetime: MagicMock) -> None:
    """Test time_of_day returns 'morning' for 5:00 AM - 11:59 AM."""
    # Test early morning (5:00 AM)
    mock_datetime.now.return_value = datetime(2026, 1, 14, 5, 0, 0, tzinfo=ZoneInfo("UTC"))
    ctx = TemporalContext("UTC")
    assert ctx.time_of_day() == "morning"

    # Test mid-morning (9:00 AM)
    mock_datetime.now.return_value = datetime(2026, 1, 14, 9, 0, 0, tzinfo=ZoneInfo("UTC"))
    assert ctx.time_of_day() == "morning"

    # Test late morning (11:59 AM)
    mock_datetime.now.return_value = datetime(2026, 1, 14, 11, 59, 0, tzinfo=ZoneInfo("UTC"))
    assert ctx.time_of_day() == "morning"


@pytest.mark.unit
@patch("src.temporal.datetime")
def test_time_of_day_afternoon(mock_datetime: MagicMock) -> None:
    """Test time_of_day returns 'afternoon' for 12:00 PM - 4:59 PM."""
    # Test noon (12:00 PM)
    mock_datetime.now.return_value = datetime(2026, 1, 14, 12, 0, 0, tzinfo=ZoneInfo("UTC"))
    ctx = TemporalContext("UTC")
    assert ctx.time_of_day() == "afternoon"

    # Test mid-afternoon (3:00 PM)
    mock_datetime.now.return_value = datetime(2026, 1, 14, 15, 0, 0, tzinfo=ZoneInfo("UTC"))
    assert ctx.time_of_day() == "afternoon"

    # Test late afternoon (4:59 PM)
    mock_datetime.now.return_value = datetime(2026, 1, 14, 16, 59, 0, tzinfo=ZoneInfo("UTC"))
    assert ctx.time_of_day() == "afternoon"


@pytest.mark.unit
@patch("src.temporal.datetime")
def test_time_of_day_evening(mock_datetime: MagicMock) -> None:
    """Test time_of_day returns 'evening' for 5:00 PM - 8:59 PM."""
    # Test early evening (5:00 PM)
    mock_datetime.now.return_value = datetime(2026, 1, 14, 17, 0, 0, tzinfo=ZoneInfo("UTC"))
    ctx = TemporalContext("UTC")
    assert ctx.time_of_day() == "evening"

    # Test mid-evening (7:00 PM)
    mock_datetime.now.return_value = datetime(2026, 1, 14, 19, 0, 0, tzinfo=ZoneInfo("UTC"))
    assert ctx.time_of_day() == "evening"

    # Test late evening (8:59 PM)
    mock_datetime.now.return_value = datetime(2026, 1, 14, 20, 59, 0, tzinfo=ZoneInfo("UTC"))
    assert ctx.time_of_day() == "evening"


@pytest.mark.unit
@patch("src.temporal.datetime")
def test_time_of_day_night(mock_datetime: MagicMock) -> None:
    """Test time_of_day returns 'night' for 9:00 PM - 4:59 AM."""
    # Test early night (9:00 PM)
    mock_datetime.now.return_value = datetime(2026, 1, 14, 21, 0, 0, tzinfo=ZoneInfo("UTC"))
    ctx = TemporalContext("UTC")
    assert ctx.time_of_day() == "night"

    # Test midnight (12:00 AM)
    mock_datetime.now.return_value = datetime(2026, 1, 14, 0, 0, 0, tzinfo=ZoneInfo("UTC"))
    assert ctx.time_of_day() == "night"

    # Test early morning night (2:00 AM)
    mock_datetime.now.return_value = datetime(2026, 1, 14, 2, 0, 0, tzinfo=ZoneInfo("UTC"))
    assert ctx.time_of_day() == "night"

    # Test late night (4:59 AM)
    mock_datetime.now.return_value = datetime(2026, 1, 14, 4, 59, 0, tzinfo=ZoneInfo("UTC"))
    assert ctx.time_of_day() == "night"


@pytest.mark.unit
@patch("src.temporal.datetime")
def test_time_of_day_boundary_noon(mock_datetime: MagicMock) -> None:
    """Test time_of_day boundary at noon (11:59 AM vs 12:00 PM)."""
    ctx = TemporalContext("UTC")

    # 11:59 AM should be morning
    mock_datetime.now.return_value = datetime(2026, 1, 14, 11, 59, 0, tzinfo=ZoneInfo("UTC"))
    assert ctx.time_of_day() == "morning"

    # 12:00 PM should be afternoon
    mock_datetime.now.return_value = datetime(2026, 1, 14, 12, 0, 0, tzinfo=ZoneInfo("UTC"))
    assert ctx.time_of_day() == "afternoon"


@pytest.mark.unit
@patch("src.temporal.datetime")
def test_time_of_day_boundary_evening(mock_datetime: MagicMock) -> None:
    """Test time_of_day boundary at evening (4:59 PM vs 5:00 PM)."""
    ctx = TemporalContext("UTC")

    # 4:59 PM should be afternoon
    mock_datetime.now.return_value = datetime(2026, 1, 14, 16, 59, 0, tzinfo=ZoneInfo("UTC"))
    assert ctx.time_of_day() == "afternoon"

    # 5:00 PM should be evening
    mock_datetime.now.return_value = datetime(2026, 1, 14, 17, 0, 0, tzinfo=ZoneInfo("UTC"))
    assert ctx.time_of_day() == "evening"


@pytest.mark.unit
@patch("src.temporal.datetime")
def test_time_of_day_boundary_night(mock_datetime: MagicMock) -> None:
    """Test time_of_day boundary at night (8:59 PM vs 9:00 PM)."""
    ctx = TemporalContext("UTC")

    # 8:59 PM should be evening
    mock_datetime.now.return_value = datetime(2026, 1, 14, 20, 59, 0, tzinfo=ZoneInfo("UTC"))
    assert ctx.time_of_day() == "evening"

    # 9:00 PM should be night
    mock_datetime.now.return_value = datetime(2026, 1, 14, 21, 0, 0, tzinfo=ZoneInfo("UTC"))
    assert ctx.time_of_day() == "night"


@pytest.mark.unit
@patch("src.temporal.datetime")
def test_time_of_day_boundary_morning(mock_datetime: MagicMock) -> None:
    """Test time_of_day boundary at morning (4:59 AM vs 5:00 AM)."""
    ctx = TemporalContext("UTC")

    # 4:59 AM should be night
    mock_datetime.now.return_value = datetime(2026, 1, 14, 4, 59, 0, tzinfo=ZoneInfo("UTC"))
    assert ctx.time_of_day() == "night"

    # 5:00 AM should be morning
    mock_datetime.now.return_value = datetime(2026, 1, 14, 5, 0, 0, tzinfo=ZoneInfo("UTC"))
    assert ctx.time_of_day() == "morning"


@pytest.mark.unit
@patch("src.temporal.datetime")
def test_to_context_string_format(mock_datetime: MagicMock) -> None:
    """Test to_context_string returns properly formatted string."""
    # Mock a specific time: Wednesday, January 14, 2026 at 3:45 PM EST
    mock_now = datetime(
        2026, 1, 14, 15, 45, 0, tzinfo=ZoneInfo("America/New_York")
    )
    mock_datetime.now.return_value = mock_now

    ctx = TemporalContext("America/New_York")
    context_str = ctx.to_context_string()

    # Verify format
    assert "Wednesday, January 14, 2026" in context_str
    assert "3:45 PM" in context_str
    assert "EST" in context_str
    assert "(afternoon)" in context_str
    assert context_str.startswith("Current time: ")


@pytest.mark.unit
@patch("src.temporal.datetime")
def test_to_context_string_morning(mock_datetime: MagicMock) -> None:
    """Test to_context_string includes 'morning' label."""
    mock_now = datetime(2026, 1, 14, 9, 30, 0, tzinfo=ZoneInfo("UTC"))
    mock_datetime.now.return_value = mock_now

    ctx = TemporalContext("UTC")
    context_str = ctx.to_context_string()

    assert "(morning)" in context_str


@pytest.mark.unit
@patch("src.temporal.datetime")
def test_to_context_string_evening(mock_datetime: MagicMock) -> None:
    """Test to_context_string includes 'evening' label."""
    mock_now = datetime(2026, 1, 14, 19, 30, 0, tzinfo=ZoneInfo("UTC"))
    mock_datetime.now.return_value = mock_now

    ctx = TemporalContext("UTC")
    context_str = ctx.to_context_string()

    assert "(evening)" in context_str


@pytest.mark.unit
@patch("src.temporal.datetime")
def test_to_context_string_night(mock_datetime: MagicMock) -> None:
    """Test to_context_string includes 'night' label."""
    mock_now = datetime(2026, 1, 14, 23, 30, 0, tzinfo=ZoneInfo("UTC"))
    mock_datetime.now.return_value = mock_now

    ctx = TemporalContext("UTC")
    context_str = ctx.to_context_string()

    assert "(night)" in context_str


@pytest.mark.unit
@patch("src.temporal.datetime")
def test_to_context_string_no_leading_zero_in_hour(mock_datetime: MagicMock) -> None:
    """Test to_context_string doesn't have leading zero in hour (e.g., '9:30' not '09:30')."""
    mock_now = datetime(2026, 1, 14, 9, 30, 0, tzinfo=ZoneInfo("UTC"))
    mock_datetime.now.return_value = mock_now

    ctx = TemporalContext("UTC")
    context_str = ctx.to_context_string()

    # Should be "9:30 AM" not "09:30 AM"
    assert "9:30 AM" in context_str
    assert "09:30 AM" not in context_str


@pytest.mark.unit
@patch("src.temporal.datetime")
def test_to_context_string_with_different_timezones(mock_datetime: MagicMock) -> None:
    """Test to_context_string works with different timezones."""
    # Test with Pacific time
    mock_now_pacific = datetime(2026, 1, 14, 15, 45, 0, tzinfo=ZoneInfo("America/Los_Angeles"))
    mock_datetime.now.return_value = mock_now_pacific

    ctx_pacific = TemporalContext("America/Los_Angeles")
    context_pacific = ctx_pacific.to_context_string()

    assert "PST" in context_pacific or "PDT" in context_pacific

    # Test with Tokyo time
    mock_now_tokyo = datetime(2026, 1, 14, 15, 45, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
    mock_datetime.now.return_value = mock_now_tokyo

    ctx_tokyo = TemporalContext("Asia/Tokyo")
    context_tokyo = ctx_tokyo.to_context_string()

    assert "JST" in context_tokyo


@pytest.mark.unit
@patch("src.temporal.datetime")
def test_multiple_calls_return_same_result_when_time_unchanged(mock_datetime: MagicMock) -> None:
    """Test that multiple calls with same mocked time return consistent results."""
    mock_now = datetime(2026, 1, 14, 15, 45, 0, tzinfo=ZoneInfo("UTC"))
    mock_datetime.now.return_value = mock_now

    ctx = TemporalContext("UTC")

    # Multiple calls should return same results
    assert ctx.time_of_day() == ctx.time_of_day()
    assert ctx.day_of_week() == ctx.day_of_week()
    assert ctx.is_weekend() == ctx.is_weekend()
    assert ctx.to_context_string() == ctx.to_context_string()
