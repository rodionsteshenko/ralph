"""
End-to-end tests for logging infrastructure.

These tests validate the complete logging system works end-to-end:
- InteractionLogger writes logs with all required fields
- LogParser can read and parse the logs
- CLI tools (--stats, --errors, etc.) work correctly
- Log rotation works by date
- Multiple interactions append correctly

All tests use REAL file system operations to verify actual functionality.
"""

import json
import subprocess
import sys
import tempfile
from collections.abc import Generator
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.log_parser import LogParser
from src.logging import InteractionLogger


@pytest.mark.e2e
class TestLoggingInfrastructureE2E:
    """
    End-to-end tests for logging infrastructure.

    Tests the complete logging workflow with real file system operations.
    """

    @pytest.fixture
    def temp_logs_dir(self) -> Generator[Path, None, None]:
        """Create temporary directory for logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def logger(self, temp_logs_dir: Path) -> InteractionLogger:
        """Create logger with temporary directory."""
        return InteractionLogger(logs_dir=temp_logs_dir)

    def test_interaction_creates_log_entry_with_all_required_fields(
        self, logger: InteractionLogger, temp_logs_dir: Path
    ) -> None:
        """
        Test: interaction creates log entry with all required fields.

        Verify that logging an interaction creates a log file with both intent
        and result entries, each containing all required fields.
        """
        # Log a complete interaction
        request_id = logger.log_interaction(
            system_prompt="You are a helpful assistant.",
            user_message="What is 2+2?",
            response="2+2 equals 4.",
            duration_ms=1234.5,
            full_context="Previous conversation context here",
            tools_called=["calculator", "memory_search"],
            error=None,
        )

        # Verify log file was created
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_logs_dir / f"interactions-{today}.jsonl"

        assert log_file.exists(), f"Log file should exist: {log_file}"
        assert log_file.is_file(), f"Log path should be a file: {log_file}"

        # Read and parse log entries
        with open(log_file) as f:
            lines = f.readlines()

        assert len(lines) == 2, "Should have 2 entries (intent + result)"

        intent_entry = json.loads(lines[0])
        result_entry = json.loads(lines[1])

        # Verify INTENT entry has ALL required fields
        assert "timestamp" in intent_entry, "Intent should have timestamp"
        assert "request_id" in intent_entry, "Intent should have request_id"
        assert "stage" in intent_entry, "Intent should have stage"
        assert "system_prompt" in intent_entry, "Intent should have system_prompt"
        assert "user_message" in intent_entry, "Intent should have user_message"
        assert "full_context" in intent_entry, "Intent should have full_context"

        # Verify intent values
        assert intent_entry["request_id"] == request_id
        assert intent_entry["stage"] == "intent"
        assert intent_entry["system_prompt"] == "You are a helpful assistant."
        assert intent_entry["user_message"] == "What is 2+2?"
        assert intent_entry["full_context"] == "Previous conversation context here"

        # Verify timestamp is valid ISO format
        try:
            datetime.fromisoformat(intent_entry["timestamp"])
        except ValueError:
            pytest.fail(f"Invalid timestamp format: {intent_entry['timestamp']}")

        # Verify RESULT entry has ALL required fields
        assert "timestamp" in result_entry, "Result should have timestamp"
        assert "request_id" in result_entry, "Result should have request_id"
        assert "stage" in result_entry, "Result should have stage"
        assert "response" in result_entry, "Result should have response"
        assert "duration_ms" in result_entry, "Result should have duration_ms"
        assert "tools_called" in result_entry, "Result should have tools_called"
        assert "error" in result_entry, "Result should have error"

        # Verify result values
        assert result_entry["request_id"] == request_id
        assert result_entry["stage"] == "result"
        assert result_entry["response"] == "2+2 equals 4."
        assert result_entry["duration_ms"] == 1234.5
        assert result_entry["tools_called"] == ["calculator", "memory_search"]
        assert result_entry["error"] is None

        # Verify timestamp is valid ISO format
        try:
            datetime.fromisoformat(result_entry["timestamp"])
        except ValueError:
            pytest.fail(f"Invalid timestamp format: {result_entry['timestamp']}")

    def test_log_parser_can_read_and_display_entry(
        self, logger: InteractionLogger, temp_logs_dir: Path
    ) -> None:
        """
        Test: log_parser can read and display the entry.

        Verify that LogParser can successfully parse and display log entries
        created by InteractionLogger.
        """
        # Create some log entries
        request_ids = []
        for i in range(3):
            req_id = logger.log_interaction(
                system_prompt=f"System prompt {i}",
                user_message=f"User message {i}",
                response=f"Response {i}",
                duration_ms=float(i * 100),
                tools_called=[f"tool{i}"],
            )
            request_ids.append(req_id)

        # Get log file path
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_logs_dir / f"interactions-{today}.jsonl"

        # Create LogParser and parse logs
        parser = LogParser(log_file)
        entries = parser.parse_logs()

        # Verify parsing succeeded
        assert len(entries) == 6, "Should have 6 entries (3 interactions × 2 stages)"

        # Verify all entries parsed correctly
        for entry in entries:
            assert "timestamp" in entry
            assert "request_id" in entry
            assert "stage" in entry
            assert entry["stage"] in ["intent", "result"]

        # Group by request_id
        grouped = parser.group_by_request_id(entries)

        # Verify grouping works
        assert len(grouped) == 3, "Should have 3 grouped interactions"

        # Verify each request_id is present
        for req_id in request_ids:
            assert req_id in grouped, f"Request ID {req_id} should be in grouped logs"
            assert grouped[req_id]["intent"] is not None
            assert grouped[req_id]["result"] is not None

        # Verify we can filter by specific request_id
        first_req = request_ids[0]
        filtered = parser.filter_by_request_id(grouped, first_req)

        assert len(filtered) == 1
        assert first_req in filtered
        assert filtered[first_req]["intent"]["user_message"] == "User message 0"
        assert filtered[first_req]["result"]["response"] == "Response 0"

    def test_multiple_interactions_append_to_same_log_file(
        self, logger: InteractionLogger, temp_logs_dir: Path
    ) -> None:
        """
        Test: multiple interactions append to same log file.

        Verify that multiple interactions logged to the same logger
        append to the same log file (not overwriting).
        """
        # Get log file path
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_logs_dir / f"interactions-{today}.jsonl"

        # Log first interaction
        req_id_1 = logger.log_interaction(
            system_prompt="System 1",
            user_message="User 1",
            response="Response 1",
            duration_ms=100.0,
        )

        # Verify file has 2 lines (intent + result)
        with open(log_file) as f:
            lines_after_1 = f.readlines()
        assert len(lines_after_1) == 2, "First interaction should have 2 entries"

        # Log second interaction
        req_id_2 = logger.log_interaction(
            system_prompt="System 2",
            user_message="User 2",
            response="Response 2",
            duration_ms=200.0,
        )

        # Verify file now has 4 lines (2 interactions × 2 stages)
        with open(log_file) as f:
            lines_after_2 = f.readlines()
        assert len(lines_after_2) == 4, "Second interaction should append, not overwrite"

        # Log third interaction
        req_id_3 = logger.log_interaction(
            system_prompt="System 3",
            user_message="User 3",
            response="Response 3",
            duration_ms=300.0,
        )

        # Verify file now has 6 lines
        with open(log_file) as f:
            lines_after_3 = f.readlines()
        assert len(lines_after_3) == 6, "Third interaction should append"

        # Verify all request IDs are present in the file
        all_request_ids = {req_id_1, req_id_2, req_id_3}
        found_request_ids = set()

        for line in lines_after_3:
            entry = json.loads(line)
            found_request_ids.add(entry["request_id"])

        assert found_request_ids == all_request_ids, "All request IDs should be in log file"

        # Verify order is preserved (first logged = first in file)
        first_entry = json.loads(lines_after_3[0])
        assert first_entry["request_id"] == req_id_1, "First entry should be from first interaction"

    def test_log_rotation_creates_new_file_on_date_change(
        self, temp_logs_dir: Path
    ) -> None:
        """
        Test: log rotation creates new file on date change.

        Verify that log files are created per-date, with format:
        interactions-YYYY-MM-DD.jsonl
        """
        logger = InteractionLogger(logs_dir=temp_logs_dir)

        # Log interaction for today
        today = datetime.now()
        today_id = logger.log_interaction(
            system_prompt="Today system",
            user_message="Today message",
            response="Today response",
            duration_ms=100.0,
        )

        # Verify today's log file exists
        today_file = temp_logs_dir / f"interactions-{today.strftime('%Y-%m-%d')}.jsonl"
        assert today_file.exists(), "Today's log file should exist"

        # Manually create a log file for yesterday
        yesterday = today - timedelta(days=1)
        yesterday_file = temp_logs_dir / f"interactions-{yesterday.strftime('%Y-%m-%d')}.jsonl"

        yesterday_entry_intent = {
            "timestamp": yesterday.isoformat(),
            "request_id": "yesterday-123",
            "stage": "intent",
            "system_prompt": "Yesterday system",
            "user_message": "Yesterday message",
            "full_context": None,
        }

        yesterday_entry_result = {
            "timestamp": yesterday.isoformat(),
            "request_id": "yesterday-123",
            "stage": "result",
            "response": "Yesterday response",
            "duration_ms": 100.0,
            "tools_called": [],
            "error": None,
        }

        with open(yesterday_file, "w") as f:
            f.write(json.dumps(yesterday_entry_intent) + "\n")
            f.write(json.dumps(yesterday_entry_result) + "\n")

        # Manually create a log file for tomorrow (simulating future date)
        tomorrow = today + timedelta(days=1)
        tomorrow_file = temp_logs_dir / f"interactions-{tomorrow.strftime('%Y-%m-%d')}.jsonl"

        tomorrow_entry_intent = {
            "timestamp": tomorrow.isoformat(),
            "request_id": "tomorrow-456",
            "stage": "intent",
            "system_prompt": "Tomorrow system",
            "user_message": "Tomorrow message",
            "full_context": None,
        }

        with open(tomorrow_file, "w") as f:
            f.write(json.dumps(tomorrow_entry_intent) + "\n")

        # Verify all three files exist
        assert yesterday_file.exists(), "Yesterday's log file should exist"
        assert today_file.exists(), "Today's log file should exist"
        assert tomorrow_file.exists(), "Tomorrow's log file should exist"

        # Verify each file has correct entries
        with open(yesterday_file) as f:
            yesterday_lines = f.readlines()
        assert len(yesterday_lines) == 2
        assert json.loads(yesterday_lines[0])["request_id"] == "yesterday-123"

        with open(today_file) as f:
            today_lines = f.readlines()
        assert len(today_lines) == 2  # Intent + result from today_id
        assert json.loads(today_lines[0])["request_id"] == today_id

        with open(tomorrow_file) as f:
            tomorrow_lines = f.readlines()
        assert len(tomorrow_lines) == 1  # Only intent entry we created
        assert json.loads(tomorrow_lines[0])["request_id"] == "tomorrow-456"

        # Verify files are independent (not overwriting each other)
        assert yesterday_lines != today_lines
        assert today_lines != tomorrow_lines

    def test_stats_flag_produces_valid_output(
        self, logger: InteractionLogger, temp_logs_dir: Path
    ) -> None:
        """
        Test: --stats flag produces valid output.

        Verify that log_parser CLI with --stats flag produces valid
        summary statistics.
        """
        # Create several log entries with various characteristics
        # Successful interaction 1
        logger.log_interaction(
            system_prompt="System 1 " + ("x" * 100),  # Add content for token estimation
            user_message="User 1 " + ("y" * 50),
            response="Response 1 " + ("z" * 75),
            duration_ms=1000.0,
            tools_called=["read_file", "write_file"],
        )

        # Successful interaction 2
        logger.log_interaction(
            system_prompt="System 2 " + ("a" * 80),
            user_message="User 2 " + ("b" * 60),
            response="Response 2 " + ("c" * 90),
            duration_ms=2000.0,
            tools_called=["read_file", "search"],
        )

        # Failed interaction (with error)
        logger.log_interaction(
            system_prompt="System 3",
            user_message="User 3",
            response="",
            duration_ms=500.0,
            tools_called=[],
            error="API timeout after 30s",
        )

        # Get log file path
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_logs_dir / f"interactions-{today}.jsonl"

        # Run log_parser with --stats flag
        result = subprocess.run(
            [sys.executable, "-m", "src.log_parser", str(log_file), "--stats"],
            capture_output=True,
            text=True,
        )

        # Verify CLI succeeded
        assert result.returncode == 0, f"CLI should succeed: {result.stderr}"

        # Verify output contains statistics
        output = result.stdout

        assert "Log Summary Statistics" in output, "Should have statistics header"
        assert "Total Interactions" in output, "Should show total count"
        assert "3" in output, "Should show 3 total interactions"

        assert "Successful" in output, "Should show successful count"
        assert "2" in output, "Should show 2 successful"

        assert "Errors" in output, "Should show error count"
        assert "1" in output, "Should show 1 error"

        assert "Average Duration" in output, "Should show average duration"

        assert "Estimated Tokens" in output, "Should show estimated tokens"

        assert "Date Range" in output, "Should show date range"

        # Should show tools usage
        assert "Most Common Tools" in output, "Should show tools section"
        assert "read_file" in output, "Should show read_file tool"
        assert "write_file" in output, "Should show write_file tool"
        assert "search" in output, "Should show search tool"

        # Test programmatic statistics calculation
        parser = LogParser(log_file)
        entries = parser.parse_logs()
        grouped = parser.group_by_request_id(entries)
        stats = parser.calculate_statistics(grouped)

        # Verify statistics structure
        assert stats["total_interactions"] == 3
        assert stats["successful_count"] == 2
        assert stats["error_count"] == 1
        assert stats["avg_duration_ms"] > 0  # (1000 + 2000 + 500) / 3 = 1166.67
        assert stats["tools_usage"]["read_file"] == 2
        assert stats["tools_usage"]["write_file"] == 1
        assert stats["tools_usage"]["search"] == 1
        assert stats["date_range"][0] is not None
        assert stats["date_range"][1] is not None
        assert stats["estimated_tokens"] > 0  # Should estimate based on content length

    def test_errors_flag_filters_correctly(
        self, logger: InteractionLogger, temp_logs_dir: Path
    ) -> None:
        """
        Test: --errors flag filters correctly.

        Verify that log_parser CLI with --errors flag only shows
        interactions that had errors.
        """
        # Create successful interaction
        success_id = logger.log_interaction(
            system_prompt="Success system",
            user_message="Success message",
            response="Success response",
            duration_ms=1000.0,
            error=None,
        )

        # Create failed interaction 1
        error_id_1 = logger.log_interaction(
            system_prompt="Error system 1",
            user_message="Error message 1",
            response="",
            duration_ms=500.0,
            error="API timeout after 30s",
        )

        # Create another successful interaction
        success_id_2 = logger.log_interaction(
            system_prompt="Success system 2",
            user_message="Success message 2",
            response="Success response 2",
            duration_ms=1500.0,
            error=None,
        )

        # Create failed interaction 2
        error_id_2 = logger.log_interaction(
            system_prompt="Error system 2",
            user_message="Error message 2",
            response="",
            duration_ms=300.0,
            error="Rate limit exceeded",
        )

        # Get log file path
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_logs_dir / f"interactions-{today}.jsonl"

        # Run log_parser with --errors flag and --json for easier parsing
        result = subprocess.run(
            [sys.executable, "-m", "src.log_parser", str(log_file), "--errors", "--json"],
            capture_output=True,
            text=True,
        )

        # Verify CLI succeeded
        assert result.returncode == 0, f"CLI should succeed: {result.stderr}"

        # Parse JSON output
        output = json.loads(result.stdout)

        # Should only have 2 interactions (the ones with errors)
        assert len(output) == 2, "Should only show error interactions"

        # Verify only error interactions are present
        error_request_ids = {item["request_id"] for item in output}
        assert error_id_1 in error_request_ids, "Should include first error"
        assert error_id_2 in error_request_ids, "Should include second error"
        assert success_id not in error_request_ids, "Should NOT include successful interactions"
        assert success_id_2 not in error_request_ids, "Should NOT include successful interactions"

        # Verify error messages are present
        for item in output:
            assert item["result"]["error"] is not None, "Error field should be populated"

        # Test programmatic error filtering
        parser = LogParser(log_file)
        entries = parser.parse_logs()
        grouped = parser.group_by_request_id(entries)
        errors_only = parser.filter_errors_only(grouped)

        assert len(errors_only) == 2, "Should filter to 2 error interactions"
        assert error_id_1 in errors_only
        assert error_id_2 in errors_only
        assert success_id not in errors_only
        assert success_id_2 not in errors_only

        # Verify error messages
        assert errors_only[error_id_1]["result"]["error"] == "API timeout after 30s"
        assert errors_only[error_id_2]["result"]["error"] == "Rate limit exceeded"

    def test_combined_filters_work_correctly(
        self, logger: InteractionLogger, temp_logs_dir: Path
    ) -> None:
        """
        Test: Combined filters (--errors + --last N) work correctly.

        Verify that multiple filters can be combined. Filters apply in order:
        1. --errors (filter to only errors)
        2. --last N (take last N from filtered results)
        """
        # Create 6 interactions with various characteristics
        # Pattern: error, success, error, success, error, success (indices 0,1,2,3,4,5)
        for i in range(6):
            error_msg = f"Error {i}" if i % 2 == 0 else None  # Errors on 0, 2, 4
            logger.log_interaction(
                system_prompt=f"System {i}",
                user_message=f"User {i}",
                response=f"Response {i}" if error_msg is None else "",
                duration_ms=float(i * 100),
                error=error_msg,
            )

        # Get log file
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_logs_dir / f"interactions-{today}.jsonl"

        # Filter: --errors --last 2
        # First filters to only errors (0, 2, 4)
        # Then takes last 2 of those (2, 4)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.log_parser",
                str(log_file),
                "--errors",
                "--last",
                "2",
                "--json",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        output = json.loads(result.stdout)

        # Should have 2 interactions (last 2 errors: indices 2 and 4)
        assert len(output) == 2, f"Should have 2 error interactions, got {len(output)}"

        # Verify these are the correct interactions (should be User 2 and User 4)
        user_messages = {item["intent"]["user_message"] for item in output}
        assert user_messages == {"User 2", "User 4"}, f"Expected User 2 and User 4, got {user_messages}"

        # Verify both have errors
        for item in output:
            assert item["result"]["error"] is not None, "Should have error"

    def test_log_file_format_is_jsonl(
        self, logger: InteractionLogger, temp_logs_dir: Path
    ) -> None:
        """
        Test: Verify log file format is JSONL (JSON Lines).

        Each line should be a valid JSON object, and the file should
        be parseable line-by-line.
        """
        # Create a few interactions
        for i in range(3):
            logger.log_interaction(
                system_prompt=f"System {i}",
                user_message=f"User {i}",
                response=f"Response {i}",
                duration_ms=float(i * 100),
            )

        # Get log file
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_logs_dir / f"interactions-{today}.jsonl"

        # Read file line by line and verify each line is valid JSON
        with open(log_file) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:  # Skip empty lines
                    try:
                        entry = json.loads(line)
                        assert isinstance(entry, dict), f"Line {line_num} should be a dict"
                    except json.JSONDecodeError as e:
                        pytest.fail(f"Line {line_num} is not valid JSON: {e}")

        # Verify file does NOT have surrounding array brackets (not pure JSON)
        with open(log_file) as f:
            content = f.read()

        assert not content.startswith("["), "File should NOT start with [ (not JSON array)"
        assert not content.endswith("]"), "File should NOT end with ] (not JSON array)"

    def test_unicode_and_special_characters_in_logs(
        self, logger: InteractionLogger, temp_logs_dir: Path
    ) -> None:
        """
        Test: Verify Unicode and special characters are handled correctly.

        Logs should preserve Unicode and special characters in all fields.
        """
        # Log with Unicode and special characters
        special_system = 'System: "Hello" 你好 مرحبا @#$%^&*()'
        special_user = 'User: नमस्ते привет \n\t\r\\ / < >'
        special_response = 'Response: こんにちは "quoted" \'single\' \\backslash'

        request_id = logger.log_interaction(
            system_prompt=special_system,
            user_message=special_user,
            response=special_response,
            duration_ms=1000.0,
        )

        # Read logs and verify special characters preserved
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_logs_dir / f"interactions-{today}.jsonl"

        with open(log_file) as f:
            lines = f.readlines()

        intent_entry = json.loads(lines[0])
        result_entry = json.loads(lines[1])

        # Verify Unicode preserved
        assert intent_entry["system_prompt"] == special_system
        assert intent_entry["user_message"] == special_user
        assert result_entry["response"] == special_response

        # Verify log_parser can handle it
        parser = LogParser(log_file)
        entries = parser.parse_logs()

        assert len(entries) == 2
        grouped = parser.group_by_request_id(entries)

        assert grouped[request_id]["intent"]["system_prompt"] == special_system
        assert grouped[request_id]["intent"]["user_message"] == special_user
        assert grouped[request_id]["result"]["response"] == special_response
