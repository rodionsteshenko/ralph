"""Tests for JSON output mode in command handlers."""

import argparse
import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from ralph import commands
from ralph.output import EXIT_ERROR, EXIT_NOTHING_TO_DO, EXIT_SUCCESS


@pytest.fixture
def sample_prd_data() -> Dict[str, Any]:
    """Sample PRD data for testing."""
    return {
        "project": "Test Project",
        "description": "A test project",
        "userStories": [
            {
                "id": "US-001",
                "title": "Story 1",
                "description": "First story",
                "status": "incomplete",
                "phase": 1,
                "priority": 1,
                "acceptanceCriteria": ["Criterion 1", "Typecheck passes"],
            },
            {
                "id": "US-002",
                "title": "Story 2",
                "description": "Second story",
                "status": "in_progress",
                "startedAt": "2024-01-01T12:00:00",
                "phase": 1,
                "priority": 2,
                "acceptanceCriteria": ["Criterion 2"],
            },
            {
                "id": "US-003",
                "title": "Story 3",
                "status": "complete",
                "phase": 2,
                "priority": 1,
                "acceptanceCriteria": [],
            },
        ],
        "phases": {
            "1": {"name": "Phase 1"},
            "2": {"name": "Phase 2"},
        },
        "metadata": {
            "completedStories": 1,
            "totalStories": 3,
            "currentIteration": 0,
            "phases": {
                "1": {"name": "Phase 1"},
                "2": {"name": "Phase 2"},
            },
        },
    }


@pytest.fixture
def mock_prd_path(tmp_path: Path, sample_prd_data: Dict[str, Any]) -> Path:
    """Create a mock PRD file and return the path."""
    ralph_dir = tmp_path / ".ralph"
    ralph_dir.mkdir()
    (ralph_dir / "logs").mkdir()
    prd_path = ralph_dir / "prd.json"
    with open(prd_path, "w") as f:
        json.dump(sample_prd_data, f)
    return prd_path


def _make_args(**kwargs: Any) -> argparse.Namespace:
    """Create an args namespace with json=True and given kwargs."""
    defaults = {"json": True, "dir": None}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# --- status command ---

def test_status_json(mock_prd_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test status command with --json flag."""
    args = _make_args(phase=None, dir=mock_prd_path.parent.parent)
    result = commands.status_command(args)
    assert result == EXIT_SUCCESS

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["project"] == "Test Project"
    assert "summary" in data
    assert "stories" in data
    assert len(data["stories"]) == 3


# --- summary command ---

def test_summary_json(mock_prd_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test summary command with --json flag."""
    args = _make_args()
    with patch("ralph.commands.Path.cwd", return_value=mock_prd_path.parent.parent):
        result = commands.summary_command(args)
    assert result == EXIT_SUCCESS

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["total_stories"] == 3
    assert data["completed_stories"] == 1


# --- validate command ---

def test_validate_json_valid(mock_prd_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test validate command with --json flag on valid PRD."""
    args = _make_args(strict=False, dir=mock_prd_path.parent.parent)
    commands.validate_command(args)

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "valid" in data
    assert "errors" in data
    assert "warnings" in data


def test_validate_json_invalid(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test validate command with --json flag on invalid PRD."""
    ralph_dir = tmp_path / ".ralph"
    ralph_dir.mkdir()
    prd_path = ralph_dir / "prd.json"
    prd_path.write_text(json.dumps({"project": "Test"}))

    args = _make_args(strict=False, dir=tmp_path)
    result = commands.validate_command(args)
    assert result == EXIT_ERROR

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["valid"] is False
    assert len(data["errors"]) > 0


# --- list-stories command ---

def test_list_stories_json(mock_prd_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test list-stories command with --json flag."""
    args = _make_args(phase=None, status=None)
    with patch("ralph.commands.Path.cwd", return_value=mock_prd_path.parent.parent):
        result = commands.list_stories_command(args)
    assert result == EXIT_SUCCESS

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert isinstance(data, list)
    assert len(data) == 3
    assert data[0]["id"] == "US-001"


def test_list_stories_json_filtered(mock_prd_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test list-stories command with filters in JSON mode."""
    args = _make_args(phase=1, status="incomplete")
    with patch("ralph.commands.Path.cwd", return_value=mock_prd_path.parent.parent):
        result = commands.list_stories_command(args)
    assert result == EXIT_SUCCESS

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == "US-001"


# --- in-progress command ---

def test_in_progress_json(mock_prd_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test in-progress command with --json flag."""
    args = _make_args()
    with patch("ralph.commands.Path.cwd", return_value=mock_prd_path.parent.parent):
        result = commands.in_progress_command(args)
    assert result == EXIT_SUCCESS

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == "US-002"


# --- skip-story command ---

def test_skip_story_json(mock_prd_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test skip-story command with --json flag."""
    args = _make_args(story_id="US-001")
    with patch("ralph.commands.Path.cwd", return_value=mock_prd_path.parent.parent):
        result = commands.skip_story_command(args)
    assert result == EXIT_SUCCESS

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["story_id"] == "US-001"
    assert data["status"] == "skipped"
    assert data["success"] is True


def test_skip_story_json_not_found(mock_prd_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test skip-story command with --json flag for non-existent story."""
    args = _make_args(story_id="US-999")
    with patch("ralph.commands.Path.cwd", return_value=mock_prd_path.parent.parent):
        result = commands.skip_story_command(args)
    assert result == EXIT_ERROR

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "error" in data


# --- start-story command ---

def test_start_story_json(mock_prd_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test start-story command with --json flag."""
    args = _make_args(story_id="US-001")
    with patch("ralph.commands.Path.cwd", return_value=mock_prd_path.parent.parent):
        result = commands.start_story_command(args)
    assert result == EXIT_SUCCESS

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["story_id"] == "US-001"
    assert data["status"] == "in_progress"
    assert data["success"] is True


# --- close-phase command ---

def test_close_phase_json(mock_prd_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test close-phase command with --json flag."""
    args = _make_args(phase_number=1)
    with patch("ralph.commands.Path.cwd", return_value=mock_prd_path.parent.parent):
        result = commands.close_phase_command(args)
    assert result == EXIT_SUCCESS

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["phase"] == 1
    assert isinstance(data["skipped_story_ids"], list)
    assert "US-001" in data["skipped_story_ids"]


# --- next-story command ---

def test_next_story_json(mock_prd_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test next-story command with --json flag."""
    args = _make_args(phase=None, dir=mock_prd_path.parent.parent)
    result = commands.next_story_command(args)
    assert result == EXIT_SUCCESS

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "story" in data
    assert data["story"]["id"] in ("US-001", "US-002")
    assert "remaining_stories" in data


def test_next_story_json_all_complete(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test next-story command when all stories are complete."""
    ralph_dir = tmp_path / ".ralph"
    ralph_dir.mkdir()
    prd_path = ralph_dir / "prd.json"
    prd_path.write_text(json.dumps({
        "project": "Test",
        "userStories": [
            {"id": "US-001", "title": "Done", "status": "complete", "phase": 1, "priority": 1}
        ],
        "metadata": {"completedStories": 1, "totalStories": 1, "currentIteration": 0},
    }))

    args = _make_args(phase=None, dir=tmp_path)
    result = commands.next_story_command(args)
    assert result == EXIT_NOTHING_TO_DO

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["story"] is None
    assert data["reason"] == "all_complete"


# --- execute-one command ---

@patch("ralph.loop.RalphLoop.execute_one")
@patch("ralph.config.RalphConfig")
def test_execute_one_json_success(
    mock_config: MagicMock, mock_execute_one: MagicMock,
    mock_prd_path: Path, capsys: pytest.CaptureFixture,
) -> None:
    """Test execute-one command with --json flag on success."""
    mock_execute_one.return_value = {
        "story_id": "US-001",
        "title": "Story 1",
        "status": "complete",
        "duration_seconds": 42.5,
        "log_file": "/tmp/log.txt",
        "remaining_stories": 1,
        "consecutive_failures": 0,
    }

    args = _make_args(phase=None, model=None, verbose=False, dir=mock_prd_path.parent.parent)
    result = commands.execute_one_command(args)
    assert result == EXIT_SUCCESS

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["story_id"] == "US-001"
    assert data["status"] == "complete"


@patch("ralph.loop.RalphLoop.execute_one")
@patch("ralph.config.RalphConfig")
def test_execute_one_json_nothing_to_do(
    mock_config: MagicMock, mock_execute_one: MagicMock,
    mock_prd_path: Path, capsys: pytest.CaptureFixture,
) -> None:
    """Test execute-one command when all stories are complete."""
    mock_execute_one.return_value = {
        "story_id": None,
        "title": None,
        "status": "nothing_to_do",
        "duration_seconds": 0,
        "log_file": None,
        "remaining_stories": 0,
        "consecutive_failures": 0,
    }

    args = _make_args(phase=None, model=None, verbose=False, dir=mock_prd_path.parent.parent)
    result = commands.execute_one_command(args)
    assert result == EXIT_NOTHING_TO_DO

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["status"] == "nothing_to_do"


# --- init command ---

def test_init_json_new(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test init command with --json flag in fresh directory."""
    args = _make_args(dir=tmp_path)
    result = commands.init_command(args)
    assert result == EXIT_SUCCESS

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["initialized"] is True


def test_init_json_already_exists(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test init command with --json flag when already initialized."""
    (tmp_path / ".ralph").mkdir()
    args = _make_args(dir=tmp_path)
    result = commands.init_command(args)
    assert result == EXIT_SUCCESS

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["initialized"] is False
    assert data["reason"] == "already_exists"


# --- error paths return JSON ---

def test_status_json_not_initialized(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test status returns JSON error when not initialized."""
    args = _make_args(phase=None, dir=tmp_path)
    result = commands.status_command(args)
    assert result == EXIT_ERROR

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "error" in data


def test_summary_json_no_prd(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test summary returns JSON error when no PRD found."""
    args = _make_args(dir=tmp_path)
    result = commands.summary_command(args)
    assert result == EXIT_ERROR

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "error" in data


# --- clear-stale command ---

def test_clear_stale_json(mock_prd_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test clear-stale command with --json flag."""
    args = _make_args(max_age_hours=0)
    with patch("ralph.commands.Path.cwd", return_value=mock_prd_path.parent.parent):
        result = commands.clear_stale_command(args)
    assert result == EXIT_SUCCESS

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "cleared_story_ids" in data
