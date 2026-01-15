"""
Unit tests for LogParser module.

Tests log parsing functionality with mocked file I/O.
"""

import json
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from src.log_parser import LogParser, LogParserError


@pytest.mark.unit
class TestLogParserInit:
    """Test LogParser initialization."""

    def test_init_with_existing_file(self, tmp_path: Path) -> None:
        """Test initialization with an existing log file."""
        log_file = tmp_path / "test.jsonl"
        log_file.touch()

        parser = LogParser(log_file)
        assert parser.log_file == log_file

    def test_init_with_nonexistent_file(self, tmp_path: Path) -> None:
        """Test initialization fails with non-existent file."""
        log_file = tmp_path / "nonexistent.jsonl"

        with pytest.raises(LogParserError, match="Log file not found"):
            LogParser(log_file)

    def test_init_with_directory(self, tmp_path: Path) -> None:
        """Test initialization fails when path is a directory."""
        with pytest.raises(LogParserError, match="Not a file"):
            LogParser(tmp_path)


@pytest.mark.unit
class TestParseLogs:
    """Test parse_logs method."""

    def test_parse_empty_file(self, tmp_path: Path) -> None:
        """Test parsing an empty log file."""
        log_file = tmp_path / "empty.jsonl"
        log_file.write_text("")

        parser = LogParser(log_file)
        entries = parser.parse_logs()

        assert entries == []

    def test_parse_valid_jsonl(self, tmp_path: Path) -> None:
        """Test parsing valid JSONL content."""
        log_file = tmp_path / "test.jsonl"

        entry1 = {"id": 1, "data": "first"}
        entry2 = {"id": 2, "data": "second"}
        content = json.dumps(entry1) + "\n" + json.dumps(entry2) + "\n"

        log_file.write_text(content)

        parser = LogParser(log_file)
        entries = parser.parse_logs()

        assert len(entries) == 2
        assert entries[0] == entry1
        assert entries[1] == entry2

    def test_parse_skips_empty_lines(self, tmp_path: Path) -> None:
        """Test parsing skips empty lines."""
        log_file = tmp_path / "test.jsonl"

        entry1 = {"id": 1}
        entry2 = {"id": 2}
        content = json.dumps(entry1) + "\n\n" + json.dumps(entry2) + "\n\n"

        log_file.write_text(content)

        parser = LogParser(log_file)
        entries = parser.parse_logs()

        assert len(entries) == 2

    def test_parse_invalid_json(self, tmp_path: Path) -> None:
        """Test parsing fails on invalid JSON."""
        log_file = tmp_path / "invalid.jsonl"
        log_file.write_text('{"valid": "json"}\nINVALID JSON\n')

        parser = LogParser(log_file)

        with pytest.raises(LogParserError, match="Invalid JSON at line 2"):
            parser.parse_logs()


@pytest.mark.unit
class TestGroupByRequestId:
    """Test group_by_request_id method."""

    def test_group_empty_entries(self, tmp_path: Path) -> None:
        """Test grouping empty list of entries."""
        log_file = tmp_path / "test.jsonl"
        log_file.touch()

        parser = LogParser(log_file)
        grouped = parser.group_by_request_id([])

        assert grouped == {}

    def test_group_single_intent(self, tmp_path: Path) -> None:
        """Test grouping with single intent entry."""
        log_file = tmp_path / "test.jsonl"
        log_file.touch()

        parser = LogParser(log_file)

        entries = [
            {
                "request_id": "req-123",
                "stage": "intent",
                "user_message": "Hello",
            }
        ]

        grouped = parser.group_by_request_id(entries)

        assert "req-123" in grouped
        assert grouped["req-123"]["intent"] == entries[0]
        assert grouped["req-123"]["result"] is None

    def test_group_intent_and_result(self, tmp_path: Path) -> None:
        """Test grouping with both intent and result."""
        log_file = tmp_path / "test.jsonl"
        log_file.touch()

        parser = LogParser(log_file)

        intent = {"request_id": "req-456", "stage": "intent", "data": "intent"}
        result = {"request_id": "req-456", "stage": "result", "data": "result"}
        entries = [intent, result]

        grouped = parser.group_by_request_id(entries)

        assert "req-456" in grouped
        assert grouped["req-456"]["intent"] == intent
        assert grouped["req-456"]["result"] == result

    def test_group_multiple_requests(self, tmp_path: Path) -> None:
        """Test grouping multiple different requests."""
        log_file = tmp_path / "test.jsonl"
        log_file.touch()

        parser = LogParser(log_file)

        entries = [
            {"request_id": "req-1", "stage": "intent"},
            {"request_id": "req-1", "stage": "result"},
            {"request_id": "req-2", "stage": "intent"},
            {"request_id": "req-2", "stage": "result"},
        ]

        grouped = parser.group_by_request_id(entries)

        assert len(grouped) == 2
        assert "req-1" in grouped
        assert "req-2" in grouped

    def test_group_skips_entries_without_request_id(self, tmp_path: Path) -> None:
        """Test grouping skips entries without request_id."""
        log_file = tmp_path / "test.jsonl"
        log_file.touch()

        parser = LogParser(log_file)

        entries = [
            {"stage": "intent", "data": "no request_id"},
            {"request_id": "req-123", "stage": "intent"},
        ]

        grouped = parser.group_by_request_id(entries)

        assert len(grouped) == 1
        assert "req-123" in grouped


@pytest.mark.unit
class TestFilterByRequestId:
    """Test filter_by_request_id method."""

    def test_filter_existing_request(self, tmp_path: Path) -> None:
        """Test filtering by existing request ID."""
        log_file = tmp_path / "test.jsonl"
        log_file.touch()

        parser = LogParser(log_file)

        interactions = {
            "req-1": {"intent": {"id": 1}, "result": None},
            "req-2": {"intent": {"id": 2}, "result": None},
        }

        filtered = parser.filter_by_request_id(interactions, "req-1")

        assert len(filtered) == 1
        assert "req-1" in filtered
        assert "req-2" not in filtered

    def test_filter_nonexistent_request(self, tmp_path: Path) -> None:
        """Test filtering by non-existent request ID returns empty."""
        log_file = tmp_path / "test.jsonl"
        log_file.touch()

        parser = LogParser(log_file)

        interactions = {"req-1": {"intent": {}, "result": None}}

        filtered = parser.filter_by_request_id(interactions, "nonexistent")

        assert filtered == {}


@pytest.mark.unit
class TestFilterErrorsOnly:
    """Test filter_errors_only method."""

    def test_filter_interactions_with_errors(self, tmp_path: Path) -> None:
        """Test filtering keeps only interactions with errors."""
        log_file = tmp_path / "test.jsonl"
        log_file.touch()

        parser = LogParser(log_file)

        interactions = {
            "req-1": {
                "intent": {},
                "result": {"error": "Something went wrong"},
            },
            "req-2": {
                "intent": {},
                "result": {"error": None},
            },
            "req-3": {
                "intent": {},
                "result": {"response": "Success"},
            },
        }

        filtered = parser.filter_errors_only(interactions)

        assert len(filtered) == 1
        assert "req-1" in filtered
        assert "req-2" not in filtered
        assert "req-3" not in filtered

    def test_filter_no_errors(self, tmp_path: Path) -> None:
        """Test filtering when no errors exist."""
        log_file = tmp_path / "test.jsonl"
        log_file.touch()

        parser = LogParser(log_file)

        interactions = {
            "req-1": {"intent": {}, "result": {"error": None}},
            "req-2": {"intent": {}, "result": {}},
        }

        filtered = parser.filter_errors_only(interactions)

        assert filtered == {}


@pytest.mark.unit
class TestGetLastN:
    """Test get_last_n method."""

    def test_get_last_n_basic(self, tmp_path: Path) -> None:
        """Test getting last N interactions."""
        log_file = tmp_path / "test.jsonl"
        log_file.touch()

        parser = LogParser(log_file)

        interactions = {
            "req-1": {"intent": {"timestamp": "2026-01-01T10:00:00"}, "result": None},
            "req-2": {"intent": {"timestamp": "2026-01-01T11:00:00"}, "result": None},
            "req-3": {"intent": {"timestamp": "2026-01-01T12:00:00"}, "result": None},
        }

        last_2 = parser.get_last_n(interactions, 2)

        assert len(last_2) == 2
        assert "req-2" in last_2
        assert "req-3" in last_2
        assert "req-1" not in last_2

    def test_get_last_n_more_than_available(self, tmp_path: Path) -> None:
        """Test getting more interactions than available returns all."""
        log_file = tmp_path / "test.jsonl"
        log_file.touch()

        parser = LogParser(log_file)

        interactions = {
            "req-1": {"intent": {"timestamp": "2026-01-01T10:00:00"}, "result": None},
            "req-2": {"intent": {"timestamp": "2026-01-01T11:00:00"}, "result": None},
        }

        last_10 = parser.get_last_n(interactions, 10)

        assert len(last_10) == 2

    def test_get_last_n_zero(self, tmp_path: Path) -> None:
        """Test getting zero interactions returns all."""
        log_file = tmp_path / "test.jsonl"
        log_file.touch()

        parser = LogParser(log_file)

        interactions = {
            "req-1": {"intent": {}, "result": None},
            "req-2": {"intent": {}, "result": None},
        }

        last_0 = parser.get_last_n(interactions, 0)

        assert len(last_0) == 2


@pytest.mark.unit
class TestDisplayJson:
    """Test display_json method."""

    def test_display_json_output(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test JSON output is valid and complete."""
        log_file = tmp_path / "test.jsonl"
        log_file.touch()

        parser = LogParser(log_file)

        interactions = {
            "req-1": {
                "intent": {"user_message": "Hello"},
                "result": {"response": "Hi"},
            }
        }

        parser.display_json(interactions)

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert len(output) == 1
        assert output[0]["request_id"] == "req-1"
        assert output[0]["intent"]["user_message"] == "Hello"
        assert output[0]["result"]["response"] == "Hi"


@pytest.mark.unit
class TestDisplayPromptsOnly:
    """Test display_prompts_only method."""

    def test_display_prompts_only_shows_prompts(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test prompts-only mode shows system and user messages."""
        log_file = tmp_path / "test.jsonl"
        log_file.touch()

        parser = LogParser(log_file)

        interactions = {
            "req-1": {
                "intent": {
                    "timestamp": "2026-01-01T10:00:00",
                    "system_prompt": "You are helpful",
                    "user_message": "Hello",
                },
                "result": {"response": "Hi there!"},
            }
        }

        parser.display_prompts_only(interactions)

        captured = capsys.readouterr()

        # Check that prompts are shown
        assert "req-1" in captured.out
        assert "You are helpful" in captured.out
        assert "Hello" in captured.out

        # Response should NOT be shown in prompts-only mode
        # (it's in the data but display_prompts_only doesn't show it)

    def test_display_prompts_only_skips_missing_intent(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test prompts-only skips interactions without intent."""
        log_file = tmp_path / "test.jsonl"
        log_file.touch()

        parser = LogParser(log_file)

        interactions = {
            "req-1": {
                "intent": None,
                "result": {"response": "Response only"},
            }
        }

        parser.display_prompts_only(interactions)

        captured = capsys.readouterr()

        # Should not display anything for intent-less interactions
        assert "req-1" not in captured.out


@pytest.mark.unit
class TestDisplayPretty:
    """Test display_pretty method."""

    def test_display_pretty_shows_all_fields(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test pretty display shows all available fields."""
        log_file = tmp_path / "test.jsonl"
        log_file.touch()

        parser = LogParser(log_file)

        interactions = {
            "req-123": {
                "intent": {
                    "timestamp": "2026-01-01T10:00:00",
                    "system_prompt": "System",
                    "user_message": "User",
                },
                "result": {
                    "timestamp": "2026-01-01T10:00:01",
                    "response": "Response",
                    "duration_ms": 1234.5,
                    "tools_called": ["tool1", "tool2"],
                    "error": None,
                },
            }
        }

        parser.display_pretty(interactions)

        captured = capsys.readouterr()

        # Check key elements are present
        assert "req-123" in captured.out
        assert "System" in captured.out
        assert "User" in captured.out
        assert "Response" in captured.out
        assert "tool1" in captured.out
        assert "1234.5" in captured.out

    def test_display_pretty_shows_errors(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test pretty display highlights errors."""
        log_file = tmp_path / "test.jsonl"
        log_file.touch()

        parser = LogParser(log_file)

        interactions = {
            "req-err": {
                "intent": {
                    "timestamp": "2026-01-01T10:00:00",
                    "user_message": "Test",
                },
                "result": {
                    "timestamp": "2026-01-01T10:00:01",
                    "response": "",
                    "duration_ms": 500.0,
                    "error": "API timeout",
                },
            }
        }

        parser.display_pretty(interactions)

        captured = capsys.readouterr()

        assert "API timeout" in captured.out
        assert "Error" in captured.out

    def test_display_pretty_empty_interactions(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test pretty display handles empty interactions."""
        log_file = tmp_path / "test.jsonl"
        log_file.touch()

        parser = LogParser(log_file)

        parser.display_pretty({})

        captured = capsys.readouterr()

        assert "No interactions found" in captured.out
