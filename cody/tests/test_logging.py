"""
Unit tests for InteractionLogger module.

Tests logging functionality with mocked file I/O.
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from src.logging import InteractionLogger, InteractionLoggerError


@pytest.mark.unit
class TestInteractionLoggerInit:
    """Test InteractionLogger initialization."""

    def test_init_default_path(self) -> None:
        """Test initialization with default logs directory."""
        with patch("src.logging.Path.mkdir") as mock_mkdir:
            logger = InteractionLogger()

            expected_path = Path.cwd() / ".cody" / "logs"
            assert logger.logs_dir == expected_path
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_init_custom_path(self) -> None:
        """Test initialization with custom logs directory."""
        custom_path = Path("/tmp/custom-logs")

        with patch("src.logging.Path.mkdir") as mock_mkdir:
            logger = InteractionLogger(logs_dir=custom_path)

            assert logger.logs_dir == custom_path
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)


@pytest.mark.unit
class TestGetLogFilePath:
    """Test _get_log_file_path method."""

    def test_get_log_file_path_default_today(self) -> None:
        """Test getting log file path defaults to today."""
        with patch("src.logging.Path.mkdir"):
            logger = InteractionLogger()

            path = logger._get_log_file_path()

            today = datetime.now().strftime("%Y-%m-%d")
            expected_filename = f"interactions-{today}.jsonl"
            assert path.name == expected_filename
            assert path.parent == logger.logs_dir

    def test_get_log_file_path_specific_date(self) -> None:
        """Test getting log file path for specific date."""
        with patch("src.logging.Path.mkdir"):
            logger = InteractionLogger()

            test_date = datetime(2026, 1, 14, 15, 30, 0)
            path = logger._get_log_file_path(date=test_date)

            assert path.name == "interactions-2026-01-14.jsonl"
            assert path.parent == logger.logs_dir

    def test_get_log_file_path_date_formatting(self) -> None:
        """Test date formatting in log file name."""
        with patch("src.logging.Path.mkdir"):
            logger = InteractionLogger()

            # Test single-digit month and day
            test_date = datetime(2026, 3, 5, 12, 0, 0)
            path = logger._get_log_file_path(date=test_date)

            # Should be zero-padded
            assert path.name == "interactions-2026-03-05.jsonl"


@pytest.mark.unit
class TestGenerateRequestId:
    """Test generate_request_id method."""

    def test_generate_request_id_returns_uuid(self) -> None:
        """Test that generate_request_id returns valid UUID string."""
        with patch("src.logging.Path.mkdir"):
            logger = InteractionLogger()

            request_id = logger.generate_request_id()

            # Should be a valid UUID string (36 chars with hyphens)
            assert isinstance(request_id, str)
            assert len(request_id) == 36
            assert request_id.count("-") == 4

    def test_generate_request_id_unique(self) -> None:
        """Test that multiple calls generate different IDs."""
        with patch("src.logging.Path.mkdir"):
            logger = InteractionLogger()

            id1 = logger.generate_request_id()
            id2 = logger.generate_request_id()

            assert id1 != id2


@pytest.mark.unit
class TestLogIntent:
    """Test log_intent method."""

    def test_log_intent_basic(self) -> None:
        """Test logging intent with basic fields."""
        with patch("src.logging.Path.mkdir"):
            logger = InteractionLogger()

            mock_file = mock_open()
            with patch("builtins.open", mock_file):
                logger.log_intent(
                    request_id="test-id-123",
                    system_prompt="You are a helpful assistant.",
                    user_message="Hello!",
                    full_context=None,
                )

            # Verify file was opened in append mode
            mock_file.assert_called_once()
            call_args = mock_file.call_args
            assert "a" in str(call_args)  # Append mode

            # Verify JSON was written
            handle = mock_file()
            written = handle.write.call_args[0][0]
            entry = json.loads(written.rstrip("\n"))

            assert entry["request_id"] == "test-id-123"
            assert entry["stage"] == "intent"
            assert entry["system_prompt"] == "You are a helpful assistant."
            assert entry["user_message"] == "Hello!"
            assert entry["full_context"] is None
            assert "timestamp" in entry

    def test_log_intent_with_full_context(self) -> None:
        """Test logging intent with full context."""
        with patch("src.logging.Path.mkdir"):
            logger = InteractionLogger()

            mock_file = mock_open()
            with patch("builtins.open", mock_file):
                logger.log_intent(
                    request_id="test-id-456",
                    system_prompt="System",
                    user_message="User",
                    full_context="Full context string",
                )

            handle = mock_file()
            written = handle.write.call_args[0][0]
            entry = json.loads(written.rstrip("\n"))

            assert entry["full_context"] == "Full context string"


@pytest.mark.unit
class TestLogResult:
    """Test log_result method."""

    def test_log_result_basic(self) -> None:
        """Test logging result with basic fields."""
        with patch("src.logging.Path.mkdir"):
            logger = InteractionLogger()

            mock_file = mock_open()
            with patch("builtins.open", mock_file):
                logger.log_result(
                    request_id="test-id-789",
                    response="Hello! How can I help?",
                    duration_ms=1234.5,
                    tools_called=None,
                    error=None,
                )

            handle = mock_file()
            written = handle.write.call_args[0][0]
            entry = json.loads(written.rstrip("\n"))

            assert entry["request_id"] == "test-id-789"
            assert entry["stage"] == "result"
            assert entry["response"] == "Hello! How can I help?"
            assert entry["duration_ms"] == 1234.5
            assert entry["tools_called"] == []
            assert entry["error"] is None
            assert "timestamp" in entry

    def test_log_result_with_tools(self) -> None:
        """Test logging result with tools called."""
        with patch("src.logging.Path.mkdir"):
            logger = InteractionLogger()

            mock_file = mock_open()
            with patch("builtins.open", mock_file):
                logger.log_result(
                    request_id="test-id-abc",
                    response="Done",
                    duration_ms=2000.0,
                    tools_called=["tool1", "tool2", "tool3"],
                    error=None,
                )

            handle = mock_file()
            written = handle.write.call_args[0][0]
            entry = json.loads(written.rstrip("\n"))

            assert entry["tools_called"] == ["tool1", "tool2", "tool3"]

    def test_log_result_with_error(self) -> None:
        """Test logging result with error."""
        with patch("src.logging.Path.mkdir"):
            logger = InteractionLogger()

            mock_file = mock_open()
            with patch("builtins.open", mock_file):
                logger.log_result(
                    request_id="test-id-err",
                    response="",
                    duration_ms=500.0,
                    tools_called=None,
                    error="API timeout",
                )

            handle = mock_file()
            written = handle.write.call_args[0][0]
            entry = json.loads(written.rstrip("\n"))

            assert entry["error"] == "API timeout"


@pytest.mark.unit
class TestLogInteraction:
    """Test log_interaction convenience method."""

    def test_log_interaction_generates_request_id(self) -> None:
        """Test that log_interaction auto-generates request_id."""
        with patch("src.logging.Path.mkdir"):
            logger = InteractionLogger()

            mock_file = mock_open()
            with patch("builtins.open", mock_file):
                request_id = logger.log_interaction(
                    system_prompt="System",
                    user_message="User",
                    response="Response",
                    duration_ms=1000.0,
                )

            # Should return a valid UUID
            assert isinstance(request_id, str)
            assert len(request_id) == 36

    def test_log_interaction_uses_provided_request_id(self) -> None:
        """Test that log_interaction uses provided request_id."""
        with patch("src.logging.Path.mkdir"):
            logger = InteractionLogger()

            mock_file = mock_open()
            with patch("builtins.open", mock_file):
                request_id = logger.log_interaction(
                    system_prompt="System",
                    user_message="User",
                    response="Response",
                    duration_ms=1000.0,
                    request_id="custom-id-123",
                )

            assert request_id == "custom-id-123"

    def test_log_interaction_writes_both_stages(self) -> None:
        """Test that log_interaction writes both intent and result."""
        with patch("src.logging.Path.mkdir"):
            logger = InteractionLogger()

            mock_file = mock_open()
            with patch("builtins.open", mock_file):
                logger.log_interaction(
                    system_prompt="System",
                    user_message="User",
                    response="Response",
                    duration_ms=1000.0,
                    request_id="test-id",
                )

            # Should have written twice (intent + result)
            handle = mock_file()
            assert handle.write.call_count == 2

            # Check first call (intent)
            first_call = handle.write.call_args_list[0][0][0]
            intent_entry = json.loads(first_call.rstrip("\n"))
            assert intent_entry["stage"] == "intent"
            assert intent_entry["request_id"] == "test-id"

            # Check second call (result)
            second_call = handle.write.call_args_list[1][0][0]
            result_entry = json.loads(second_call.rstrip("\n"))
            assert result_entry["stage"] == "result"
            assert result_entry["request_id"] == "test-id"


@pytest.mark.unit
class TestWriteLogEntry:
    """Test _write_log_entry method."""

    def test_write_log_entry_creates_jsonl(self) -> None:
        """Test that log entries are written as JSONL."""
        with patch("src.logging.Path.mkdir"):
            logger = InteractionLogger()

            test_entry = {"foo": "bar", "num": 42}

            mock_file = mock_open()
            with patch("builtins.open", mock_file):
                logger._write_log_entry(test_entry)

            handle = mock_file()
            written = handle.write.call_args[0][0]

            # Should be valid JSON followed by newline
            assert written.endswith("\n")
            parsed = json.loads(written.rstrip("\n"))
            assert parsed == test_entry

    def test_write_log_entry_error_handling(self) -> None:
        """Test error handling when writing fails."""
        with patch("src.logging.Path.mkdir"):
            logger = InteractionLogger()

            # Mock open to raise exception
            with patch("builtins.open", side_effect=OSError("Write failed")):
                with pytest.raises(InteractionLoggerError) as exc_info:
                    logger._write_log_entry({"test": "data"})

                assert "Failed to write log entry" in str(exc_info.value)


@pytest.mark.unit
class TestReadLogs:
    """Test read_logs method."""

    def test_read_logs_returns_empty_if_file_missing(self) -> None:
        """Test reading logs returns empty list if file doesn't exist."""
        with patch("src.logging.Path.mkdir"):
            logger = InteractionLogger()

            with patch("src.logging.Path.exists", return_value=False):
                logs = logger.read_logs()

            assert logs == []

    def test_read_logs_parses_jsonl(self) -> None:
        """Test reading logs parses JSONL correctly."""
        with patch("src.logging.Path.mkdir"):
            logger = InteractionLogger()

            # Create mock JSONL content
            entry1 = {"id": 1, "text": "first"}
            entry2 = {"id": 2, "text": "second"}
            mock_content = json.dumps(entry1) + "\n" + json.dumps(entry2) + "\n"

            mock_file = mock_open(read_data=mock_content)
            with patch("src.logging.Path.exists", return_value=True):
                with patch("builtins.open", mock_file):
                    logs = logger.read_logs()

            assert len(logs) == 2
            assert logs[0] == entry1
            assert logs[1] == entry2

    def test_read_logs_respects_limit(self) -> None:
        """Test reading logs respects limit parameter."""
        with patch("src.logging.Path.mkdir"):
            logger = InteractionLogger()

            # Create 5 entries but only read 2
            entries = [json.dumps({"id": i}) + "\n" for i in range(5)]
            mock_content = "".join(entries)

            mock_file = mock_open(read_data=mock_content)
            with patch("src.logging.Path.exists", return_value=True):
                with patch("builtins.open", mock_file):
                    logs = logger.read_logs(limit=2)

            assert len(logs) == 2

    def test_read_logs_skips_empty_lines(self) -> None:
        """Test reading logs skips empty lines."""
        with patch("src.logging.Path.mkdir"):
            logger = InteractionLogger()

            # JSONL with empty lines
            mock_content = json.dumps({"id": 1}) + "\n\n" + json.dumps({"id": 2}) + "\n\n"

            mock_file = mock_open(read_data=mock_content)
            with patch("src.logging.Path.exists", return_value=True):
                with patch("builtins.open", mock_file):
                    logs = logger.read_logs()

            assert len(logs) == 2

    def test_read_logs_error_handling(self) -> None:
        """Test error handling when reading fails."""
        with patch("src.logging.Path.mkdir"):
            logger = InteractionLogger()

            with patch("src.logging.Path.exists", return_value=True):
                with patch("builtins.open", side_effect=OSError("Read failed")):
                    with pytest.raises(InteractionLoggerError) as exc_info:
                        logger.read_logs()

                    assert "Failed to read log entries" in str(exc_info.value)


@pytest.mark.unit
class TestGetInteractionById:
    """Test get_interaction_by_id method."""

    def test_get_interaction_by_id_finds_both_stages(self) -> None:
        """Test finding interaction with both intent and result."""
        with patch("src.logging.Path.mkdir"):
            logger = InteractionLogger()

            # Mock logs with both stages
            intent_entry = {"request_id": "test-123", "stage": "intent", "data": "intent"}
            result_entry = {"request_id": "test-123", "stage": "result", "data": "result"}

            with patch.object(logger, "read_logs", return_value=[intent_entry, result_entry]):
                interaction = logger.get_interaction_by_id("test-123")

            assert interaction is not None
            assert interaction["intent"] == intent_entry
            assert interaction["result"] == result_entry

    def test_get_interaction_by_id_intent_only(self) -> None:
        """Test finding interaction with only intent stage."""
        with patch("src.logging.Path.mkdir"):
            logger = InteractionLogger()

            intent_entry = {"request_id": "test-456", "stage": "intent"}

            with patch.object(logger, "read_logs", return_value=[intent_entry]):
                interaction = logger.get_interaction_by_id("test-456")

            assert interaction is not None
            assert interaction["intent"] == intent_entry
            assert interaction["result"] is None

    def test_get_interaction_by_id_not_found(self) -> None:
        """Test when interaction is not found."""
        with patch("src.logging.Path.mkdir"):
            logger = InteractionLogger()

            with patch.object(logger, "read_logs", return_value=[]):
                interaction = logger.get_interaction_by_id("nonexistent")

            assert interaction is None

    def test_get_interaction_by_id_searches_multiple_days(self) -> None:
        """Test that search looks back multiple days."""
        with patch("src.logging.Path.mkdir"):
            logger = InteractionLogger()

            # Mock read_logs to return empty for first 3 calls, then data
            call_count = 0

            def mock_read_logs(date: datetime | None = None) -> list[dict[str, str]]:
                nonlocal call_count
                call_count += 1
                if call_count >= 4:
                    return [{"request_id": "old-123", "stage": "intent"}]
                return []

            with patch.object(logger, "read_logs", side_effect=mock_read_logs):
                interaction = logger.get_interaction_by_id("old-123")

            # Should have searched multiple days
            assert call_count >= 4
            assert interaction is not None
