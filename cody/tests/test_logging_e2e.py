"""
End-to-end tests for InteractionLogger module.

These tests use REAL file system operations to verify actual functionality.
"""

import json
import tempfile
from collections.abc import Generator
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.logging import InteractionLogger


@pytest.mark.e2e
class TestInteractionLoggerE2E:
    """End-to-end tests with real file system operations."""

    @pytest.fixture
    def temp_logs_dir(self) -> Generator[Path, None, None]:
        """Create temporary directory for logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def logger(self, temp_logs_dir: Path) -> InteractionLogger:
        """Create logger with temporary directory."""
        return InteractionLogger(logs_dir=temp_logs_dir)

    def test_e2e_log_intent_creates_file(self, logger: InteractionLogger) -> None:
        """Test that logging intent creates actual file."""
        request_id = logger.generate_request_id()

        logger.log_intent(
            request_id=request_id,
            system_prompt="You are helpful.",
            user_message="Hello!",
            full_context=None,
        )

        # Check file was created
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = logger.logs_dir / f"interactions-{today}.jsonl"
        assert log_file.exists()

        # Read and verify content
        with open(log_file) as f:
            line = f.readline()
            entry = json.loads(line)

        assert entry["request_id"] == request_id
        assert entry["stage"] == "intent"
        assert entry["system_prompt"] == "You are helpful."
        assert entry["user_message"] == "Hello!"

    def test_e2e_log_result_appends_to_file(self, logger: InteractionLogger) -> None:
        """Test that logging result appends to existing file."""
        request_id = logger.generate_request_id()

        # Log intent first
        logger.log_intent(
            request_id=request_id, system_prompt="System", user_message="User", full_context=None
        )

        # Log result
        logger.log_result(
            request_id=request_id,
            response="Response",
            duration_ms=1234.5,
            tools_called=None,
            error=None,
        )

        # Read file - should have 2 lines
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = logger.logs_dir / f"interactions-{today}.jsonl"

        with open(log_file) as f:
            lines = f.readlines()

        assert len(lines) == 2

        # Verify both entries
        intent_entry = json.loads(lines[0])
        result_entry = json.loads(lines[1])

        assert intent_entry["stage"] == "intent"
        assert result_entry["stage"] == "result"
        assert intent_entry["request_id"] == result_entry["request_id"]

    def test_e2e_log_interaction_writes_complete_entry(self, logger: InteractionLogger) -> None:
        """Test log_interaction writes both intent and result."""
        request_id = logger.log_interaction(
            system_prompt="System prompt",
            user_message="User message",
            response="Claude response",
            duration_ms=2500.0,
            full_context="Full context string",
            tools_called=["tool1", "tool2"],
            error=None,
        )

        # Read log file
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = logger.logs_dir / f"interactions-{today}.jsonl"

        with open(log_file) as f:
            lines = f.readlines()

        assert len(lines) == 2

        intent = json.loads(lines[0])
        result = json.loads(lines[1])

        # Verify intent
        assert intent["request_id"] == request_id
        assert intent["stage"] == "intent"
        assert intent["system_prompt"] == "System prompt"
        assert intent["user_message"] == "User message"
        assert intent["full_context"] == "Full context string"

        # Verify result
        assert result["request_id"] == request_id
        assert result["stage"] == "result"
        assert result["response"] == "Claude response"
        assert result["duration_ms"] == 2500.0
        assert result["tools_called"] == ["tool1", "tool2"]
        assert result["error"] is None

    def test_e2e_multiple_interactions(self, logger: InteractionLogger) -> None:
        """Test logging multiple interactions."""
        ids = []
        for i in range(5):
            request_id = logger.log_interaction(
                system_prompt=f"System {i}",
                user_message=f"User {i}",
                response=f"Response {i}",
                duration_ms=float(i * 100),
            )
            ids.append(request_id)

        # Should have 10 lines total (2 per interaction)
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = logger.logs_dir / f"interactions-{today}.jsonl"

        with open(log_file) as f:
            lines = f.readlines()

        assert len(lines) == 10

        # Verify all request IDs are present
        for request_id in ids:
            found = False
            for line in lines:
                entry = json.loads(line)
                if entry["request_id"] == request_id:
                    found = True
                    break
            assert found, f"Request ID {request_id} not found in logs"

    def test_e2e_read_logs_returns_entries(self, logger: InteractionLogger) -> None:
        """Test reading logs returns actual entries."""
        # Write some logs
        logger.log_interaction(
            system_prompt="S1", user_message="U1", response="R1", duration_ms=100.0
        )
        logger.log_interaction(
            system_prompt="S2", user_message="U2", response="R2", duration_ms=200.0
        )

        # Read logs
        logs = logger.read_logs()

        assert len(logs) == 4  # 2 interactions x 2 stages each
        assert all("request_id" in entry for entry in logs)
        assert all("timestamp" in entry for entry in logs)

    def test_e2e_read_logs_with_limit(self, logger: InteractionLogger) -> None:
        """Test reading logs respects limit."""
        # Write 3 interactions
        for i in range(3):
            logger.log_interaction(
                system_prompt=f"S{i}", user_message=f"U{i}", response=f"R{i}", duration_ms=100.0
            )

        # Read with limit
        logs = logger.read_logs(limit=3)

        assert len(logs) == 3  # Should stop at limit

    def test_e2e_get_interaction_by_id(self, logger: InteractionLogger) -> None:
        """Test finding specific interaction by ID."""
        request_id = logger.log_interaction(
            system_prompt="Test system",
            user_message="Test user",
            response="Test response",
            duration_ms=1500.0,
            tools_called=["tool1"],
        )

        # Find by ID
        interaction = logger.get_interaction_by_id(request_id)

        assert interaction is not None
        assert interaction["intent"] is not None
        assert interaction["result"] is not None
        assert interaction["intent"]["request_id"] == request_id
        assert interaction["result"]["request_id"] == request_id

    def test_e2e_log_with_error(self, logger: InteractionLogger) -> None:
        """Test logging interaction with error."""
        logger.log_interaction(
            system_prompt="System",
            user_message="User",
            response="",
            duration_ms=500.0,
            error="API timeout after 30s",
        )

        # Read and verify
        logs = logger.read_logs()
        result_entries = [e for e in logs if e.get("stage") == "result"]

        assert len(result_entries) == 1
        assert result_entries[0]["error"] == "API timeout after 30s"

    def test_e2e_date_rotation(self, logger: InteractionLogger) -> None:
        """Test that logs rotate by date."""
        # Log with today's date
        today_id = logger.log_interaction(
            system_prompt="Today", user_message="Today", response="Today", duration_ms=100.0
        )

        # Manually create log file for yesterday
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_file = logger.logs_dir / f"interactions-{yesterday.strftime('%Y-%m-%d')}.jsonl"

        # Write a log entry for yesterday
        yesterday_entry = {
            "timestamp": yesterday.isoformat(),
            "request_id": "yesterday-123",
            "stage": "intent",
            "system_prompt": "Yesterday",
            "user_message": "Yesterday",
            "full_context": None,
        }

        with open(yesterday_file, "w") as f:
            f.write(json.dumps(yesterday_entry) + "\n")

        # Check today's file exists and has correct entry
        today_file = logger._get_log_file_path()
        assert today_file.exists()

        with open(today_file) as f:
            lines = f.readlines()
            today_entries = [json.loads(line) for line in lines]

        assert any(e["request_id"] == today_id for e in today_entries)

        # Check yesterday's file exists separately
        assert yesterday_file.exists()

        with open(yesterday_file) as f:
            lines = f.readlines()
            assert len(lines) == 1
            entry = json.loads(lines[0])
            assert entry["request_id"] == "yesterday-123"

    def test_e2e_unicode_content(self, logger: InteractionLogger) -> None:
        """Test logging with Unicode content."""
        logger.log_interaction(
            system_prompt="System 你好",
            user_message="User مرحبا",
            response="Response नमस्ते",
            duration_ms=1000.0,
        )

        # Read and verify Unicode is preserved
        logs = logger.read_logs()
        intent_entries = [e for e in logs if e.get("stage") == "intent"]

        assert len(intent_entries) == 1
        assert intent_entries[0]["system_prompt"] == "System 你好"
        assert intent_entries[0]["user_message"] == "User مرحبا"

    def test_e2e_large_content(self, logger: InteractionLogger) -> None:
        """Test logging large content."""
        large_text = "x" * 10000  # 10KB of text

        logger.log_interaction(
            system_prompt=large_text,
            user_message=large_text,
            response=large_text,
            duration_ms=5000.0,
        )

        # Verify it was written correctly
        logs = logger.read_logs()
        assert len(logs) == 2

        intent = next(e for e in logs if e.get("stage") == "intent")
        assert len(intent["system_prompt"]) == 10000

    def test_e2e_special_characters_in_content(self, logger: InteractionLogger) -> None:
        """Test logging with special JSON characters."""
        special_text = 'Quote: " Backslash: \\ Newline: \\n Tab: \\t'

        logger.log_interaction(
            system_prompt=special_text,
            user_message=special_text,
            response=special_text,
            duration_ms=100.0,
        )

        # Verify special characters are preserved
        logs = logger.read_logs()
        intent = next(e for e in logs if e.get("stage") == "intent")

        assert intent["system_prompt"] == special_text

    def test_e2e_concurrent_logging(self, logger: InteractionLogger) -> None:
        """Test multiple logs written in quick succession."""
        ids = []
        for i in range(10):
            request_id = logger.log_interaction(
                system_prompt=f"S{i}",
                user_message=f"U{i}",
                response=f"R{i}",
                duration_ms=float(i),
            )
            ids.append(request_id)

        # All should be written
        logs = logger.read_logs()
        assert len(logs) == 20  # 10 interactions x 2 stages

        # All IDs should be present
        logged_ids = {entry["request_id"] for entry in logs}
        for request_id in ids:
            assert request_id in logged_ids

    def test_e2e_empty_values(self, logger: InteractionLogger) -> None:
        """Test logging with empty strings."""
        logger.log_interaction(
            system_prompt="",
            user_message="",
            response="",
            duration_ms=0.0,
            full_context="",
            tools_called=[],
            error=None,
        )

        logs = logger.read_logs()
        assert len(logs) == 2

        intent = next(e for e in logs if e.get("stage") == "intent")
        result = next(e for e in logs if e.get("stage") == "result")

        assert intent["system_prompt"] == ""
        assert intent["user_message"] == ""
        assert result["response"] == ""

    def test_e2e_logs_directory_creation(self, temp_logs_dir: Path) -> None:
        """Test that logs directory is created if it doesn't exist."""
        # Delete the directory
        if temp_logs_dir.exists():
            import shutil

            shutil.rmtree(temp_logs_dir)

        assert not temp_logs_dir.exists()

        # Create logger - should create directory
        logger = InteractionLogger(logs_dir=temp_logs_dir)

        assert temp_logs_dir.exists()

        # Should be able to write
        logger.log_interaction(
            system_prompt="Test", user_message="Test", response="Test", duration_ms=100.0
        )

        # Verify file was created
        log_files = list(temp_logs_dir.glob("interactions-*.jsonl"))
        assert len(log_files) == 1
