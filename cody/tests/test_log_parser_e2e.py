"""
End-to-end tests for LogParser module.

Tests with real log files and actual CLI execution.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.log_parser import LogParser


@pytest.mark.e2e
class TestLogParserE2E:
    """E2E tests for LogParser with real log files."""

    @pytest.fixture
    def real_log_file(self, tmp_path: Path) -> Path:
        """Create a real log file with sample data."""
        log_file = tmp_path / "interactions-test.jsonl"

        # Create realistic log entries
        entries = [
            {
                "timestamp": "2026-01-14T10:00:00.000000",
                "request_id": "req-001",
                "stage": "intent",
                "system_prompt": "You are a helpful assistant.",
                "user_message": "What is 2+2?",
                "full_context": None,
            },
            {
                "timestamp": "2026-01-14T10:00:01.234000",
                "request_id": "req-001",
                "stage": "result",
                "response": "2+2 equals 4.",
                "duration_ms": 1234.0,
                "tools_called": [],
                "error": None,
            },
            {
                "timestamp": "2026-01-14T11:00:00.000000",
                "request_id": "req-002",
                "stage": "intent",
                "system_prompt": "You are a code assistant.",
                "user_message": "Write a hello world function",
                "full_context": "Previous context here...",
            },
            {
                "timestamp": "2026-01-14T11:00:02.500000",
                "request_id": "req-002",
                "stage": "result",
                "response": "def hello(): print('Hello, World!')",
                "duration_ms": 2500.0,
                "tools_called": ["code_generation", "syntax_check"],
                "error": None,
            },
            {
                "timestamp": "2026-01-14T12:00:00.000000",
                "request_id": "req-003",
                "stage": "intent",
                "system_prompt": "You are helpful.",
                "user_message": "Process this request",
                "full_context": None,
            },
            {
                "timestamp": "2026-01-14T12:00:00.500000",
                "request_id": "req-003",
                "stage": "result",
                "response": "",
                "duration_ms": 500.0,
                "tools_called": [],
                "error": "API timeout after 30s",
            },
        ]

        with open(log_file, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        return log_file

    def test_parse_real_log_file(self, real_log_file: Path) -> None:
        """Test parsing a real log file."""
        parser = LogParser(real_log_file)
        entries = parser.parse_logs()

        assert len(entries) == 6  # 3 requests × 2 stages each

        # Verify structure
        for entry in entries:
            assert "timestamp" in entry
            assert "request_id" in entry
            assert "stage" in entry

    def test_group_real_interactions(self, real_log_file: Path) -> None:
        """Test grouping real log entries by request_id."""
        parser = LogParser(real_log_file)
        entries = parser.parse_logs()
        grouped = parser.group_by_request_id(entries)

        assert len(grouped) == 3
        assert "req-001" in grouped
        assert "req-002" in grouped
        assert "req-003" in grouped

        # Verify each has both stages
        for req_id in ["req-001", "req-002", "req-003"]:
            assert grouped[req_id]["intent"] is not None
            assert grouped[req_id]["result"] is not None

    def test_filter_by_request_id_real(self, real_log_file: Path) -> None:
        """Test filtering by specific request ID with real data."""
        parser = LogParser(real_log_file)
        entries = parser.parse_logs()
        grouped = parser.group_by_request_id(entries)

        filtered = parser.filter_by_request_id(grouped, "req-002")

        assert len(filtered) == 1
        assert "req-002" in filtered
        assert filtered["req-002"]["intent"]["user_message"] == "Write a hello world function"

    def test_filter_errors_real(self, real_log_file: Path) -> None:
        """Test filtering errors with real data."""
        parser = LogParser(real_log_file)
        entries = parser.parse_logs()
        grouped = parser.group_by_request_id(entries)

        errors = parser.filter_errors_only(grouped)

        assert len(errors) == 1
        assert "req-003" in errors
        assert errors["req-003"]["result"]["error"] == "API timeout after 30s"

    def test_get_last_n_real(self, real_log_file: Path) -> None:
        """Test getting last N interactions with real data."""
        parser = LogParser(real_log_file)
        entries = parser.parse_logs()
        grouped = parser.group_by_request_id(entries)

        last_2 = parser.get_last_n(grouped, 2)

        assert len(last_2) == 2
        assert "req-002" in last_2
        assert "req-003" in last_2

    def test_display_json_real(
        self, real_log_file: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test JSON output with real data."""
        parser = LogParser(real_log_file)
        entries = parser.parse_logs()
        grouped = parser.group_by_request_id(entries)

        parser.display_json(grouped)

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert len(output) == 3
        assert all("request_id" in item for item in output)
        assert all("intent" in item for item in output)
        assert all("result" in item for item in output)

    def test_display_prompts_only_real(
        self, real_log_file: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test prompts-only display with real data."""
        parser = LogParser(real_log_file)
        entries = parser.parse_logs()
        grouped = parser.group_by_request_id(entries)

        # Filter to one interaction for cleaner output
        filtered = parser.filter_by_request_id(grouped, "req-001")

        parser.display_prompts_only(filtered)

        captured = capsys.readouterr()

        # Should show prompts
        assert "req-001" in captured.out
        assert "You are a helpful assistant." in captured.out
        assert "What is 2+2?" in captured.out

        # Should NOT show response
        assert "2+2 equals 4" not in captured.out

    def test_display_pretty_real(
        self, real_log_file: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test pretty display with real data."""
        parser = LogParser(real_log_file)
        entries = parser.parse_logs()
        grouped = parser.group_by_request_id(entries)

        # Display one interaction
        filtered = parser.filter_by_request_id(grouped, "req-002")

        parser.display_pretty(filtered)

        captured = capsys.readouterr()

        # Should show all parts
        assert "req-002" in captured.out
        assert "You are a code assistant." in captured.out
        assert "Write a hello world function" in captured.out
        assert "def hello():" in captured.out
        assert "code_generation" in captured.out


@pytest.mark.e2e
class TestLogParserCLI:
    """E2E tests for log parser CLI."""

    @pytest.fixture
    def real_log_file(self, tmp_path: Path) -> Path:
        """Create a real log file for CLI testing."""
        log_file = tmp_path / "cli-test.jsonl"

        entries = [
            {
                "timestamp": "2026-01-14T10:00:00.000000",
                "request_id": "cli-001",
                "stage": "intent",
                "system_prompt": "System",
                "user_message": "Test message",
                "full_context": None,
            },
            {
                "timestamp": "2026-01-14T10:00:01.000000",
                "request_id": "cli-001",
                "stage": "result",
                "response": "Test response",
                "duration_ms": 1000.0,
                "tools_called": [],
                "error": None,
            },
            {
                "timestamp": "2026-01-14T11:00:00.000000",
                "request_id": "cli-002",
                "stage": "intent",
                "system_prompt": "System",
                "user_message": "Second test",
                "full_context": None,
            },
            {
                "timestamp": "2026-01-14T11:00:01.000000",
                "request_id": "cli-002",
                "stage": "result",
                "response": "",
                "duration_ms": 500.0,
                "tools_called": [],
                "error": "Test error",
            },
        ]

        with open(log_file, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        return log_file

    def test_cli_basic_execution(self, real_log_file: Path) -> None:
        """Test basic CLI execution with real log file."""
        result = subprocess.run(
            [sys.executable, "-m", "src.log_parser", str(real_log_file)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "cli-001" in result.stdout
        assert "cli-002" in result.stdout

    def test_cli_json_output(self, real_log_file: Path) -> None:
        """Test CLI with --json flag."""
        result = subprocess.run(
            [sys.executable, "-m", "src.log_parser", str(real_log_file), "--json"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        # Should be valid JSON
        output = json.loads(result.stdout)
        assert len(output) == 2
        assert output[0]["request_id"] == "cli-001"

    def test_cli_last_n(self, real_log_file: Path) -> None:
        """Test CLI with --last N flag."""
        result = subprocess.run(
            [sys.executable, "-m", "src.log_parser", str(real_log_file), "--last", "1"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        # Should only show last interaction
        assert "cli-002" in result.stdout
        # cli-001 might appear in timestamps but not as request ID
        # Let's check JSON output for more precise verification

        result_json = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.log_parser",
                str(real_log_file),
                "--last",
                "1",
                "--json",
            ],
            capture_output=True,
            text=True,
        )

        output = json.loads(result_json.stdout)
        assert len(output) == 1
        assert output[0]["request_id"] == "cli-002"

    def test_cli_request_id_filter(self, real_log_file: Path) -> None:
        """Test CLI with --request-id flag."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.log_parser",
                str(real_log_file),
                "--request-id",
                "cli-001",
                "--json",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)
        assert len(output) == 1
        assert output[0]["request_id"] == "cli-001"

    def test_cli_errors_filter(self, real_log_file: Path) -> None:
        """Test CLI with --errors flag."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.log_parser",
                str(real_log_file),
                "--errors",
                "--json",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)
        assert len(output) == 1
        assert output[0]["request_id"] == "cli-002"
        assert output[0]["result"]["error"] == "Test error"

    def test_cli_prompts_only(self, real_log_file: Path) -> None:
        """Test CLI with --prompts-only flag."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.log_parser",
                str(real_log_file),
                "--prompts-only",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        # Should show prompts
        assert "System" in result.stdout
        assert "Test message" in result.stdout

        # Should NOT show responses
        assert "Test response" not in result.stdout

    def test_cli_nonexistent_file(self, tmp_path: Path) -> None:
        """Test CLI with non-existent file."""
        nonexistent = tmp_path / "does-not-exist.jsonl"

        result = subprocess.run(
            [sys.executable, "-m", "src.log_parser", str(nonexistent)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "Log file not found" in result.stderr

    def test_cli_combined_filters(self, real_log_file: Path) -> None:
        """Test CLI with multiple filters combined."""
        # This should work but return empty (no errors in last 1)
        # Actually cli-002 is last and has error, so it should return 1

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.log_parser",
                str(real_log_file),
                "--last",
                "1",
                "--errors",
                "--json",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)
        assert len(output) == 1
        assert output[0]["request_id"] == "cli-002"

    def test_cli_stats_flag(self, real_log_file: Path) -> None:
        """Test CLI with --stats flag."""
        result = subprocess.run(
            [sys.executable, "-m", "src.log_parser", str(real_log_file), "--stats"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        # Should show statistics headers
        assert "Log Summary Statistics" in result.stdout
        assert "Total Interactions" in result.stdout
        assert "Successful" in result.stdout
        assert "Errors" in result.stdout
        assert "Average Duration" in result.stdout
        assert "Estimated Tokens" in result.stdout
        assert "Date Range" in result.stdout

        # Should show count values
        assert "2" in result.stdout  # Total interactions

    def test_cli_stats_with_tools(self, tmp_path: Path) -> None:
        """Test CLI stats with tools usage."""
        log_file = tmp_path / "tools-test.jsonl"

        entries = [
            {
                "timestamp": "2026-01-14T10:00:00.000000",
                "request_id": "req-001",
                "stage": "intent",
                "system_prompt": "System",
                "user_message": "Test",
                "full_context": None,
            },
            {
                "timestamp": "2026-01-14T10:00:01.000000",
                "request_id": "req-001",
                "stage": "result",
                "response": "Result",
                "duration_ms": 1000.0,
                "tools_called": ["read_file", "write_file"],
                "error": None,
            },
            {
                "timestamp": "2026-01-14T11:00:00.000000",
                "request_id": "req-002",
                "stage": "intent",
                "system_prompt": "System",
                "user_message": "Test2",
                "full_context": None,
            },
            {
                "timestamp": "2026-01-14T11:00:01.000000",
                "request_id": "req-002",
                "stage": "result",
                "response": "Result2",
                "duration_ms": 2000.0,
                "tools_called": ["read_file", "execute_command"],
                "error": None,
            },
        ]

        with open(log_file, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        result = subprocess.run(
            [sys.executable, "-m", "src.log_parser", str(log_file), "--stats"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        # Should show tools section
        assert "Most Common Tools" in result.stdout
        assert "read_file" in result.stdout
        assert "write_file" in result.stdout
        assert "execute_command" in result.stdout

    def test_cli_stats_short_flag(self, real_log_file: Path) -> None:
        """Test CLI with -s short flag for stats."""
        result = subprocess.run(
            [sys.executable, "-m", "src.log_parser", str(real_log_file), "-s"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Log Summary Statistics" in result.stdout


@pytest.mark.e2e
class TestLogParserWithActualLogs:
    """E2E tests with actual log files from .cody/logs if they exist."""

    def test_parse_actual_logs_if_exist(self) -> None:
        """Test parsing actual logs from .cody/logs directory."""
        logs_dir = Path.cwd() / ".cody" / "logs"

        if not logs_dir.exists():
            pytest.skip(".cody/logs directory does not exist")

        # Find any .jsonl files
        log_files = list(logs_dir.glob("*.jsonl"))

        if not log_files:
            pytest.skip("No log files found in .cody/logs")

        # Test with the first log file found
        log_file = log_files[0]

        parser = LogParser(log_file)
        entries = parser.parse_logs()

        # Should be able to parse without errors
        assert isinstance(entries, list)

        # If there are entries, they should have expected structure
        if entries:
            for entry in entries:
                assert "timestamp" in entry
                assert "request_id" in entry
                assert "stage" in entry

            # Test grouping works
            grouped = parser.group_by_request_id(entries)
            assert len(grouped) > 0
