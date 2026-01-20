"""Tests for CLI command handlers."""

import argparse
import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from ralph import commands


@pytest.fixture
def sample_prd_data() -> Dict[str, Any]:
    """Sample PRD data for testing."""
    return {
        "project": "Test Project",
        "userStories": [
            {
                "id": "US-001",
                "title": "Story 1",
                "status": "incomplete",
                "phase": 1,
            },
            {
                "id": "US-002",
                "title": "Story 2",
                "status": "in_progress",
                "startedAt": "2024-01-01T12:00:00",
                "phase": 1,
            },
        ],
        "metadata": {
            "completedStories": 0,
            "totalStories": 2,
            "phases": {
                "1": {"name": "Phase 1", "description": "Test phase"}
            },
        },
    }


@pytest.fixture
def mock_prd_path(tmp_path: Path, sample_prd_data: Dict[str, Any]) -> Path:
    """Create a mock PRD file."""
    ralph_dir = tmp_path / ".ralph"
    ralph_dir.mkdir()
    prd_path = ralph_dir / "prd.json"
    with open(prd_path, "w") as f:
        json.dump(sample_prd_data, f)
    return prd_path


def test_summary_command(mock_prd_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test summary command."""
    args = argparse.Namespace()

    with patch("ralph.commands.Path.cwd", return_value=mock_prd_path.parent.parent):
        commands.summary_command(args)

    captured = capsys.readouterr()
    assert "PRD Summary" in captured.out
    assert "Total Stories: 2" in captured.out
    assert "Completed: 0" in captured.out


def test_summary_command_no_prd(tmp_path: Path) -> None:
    """Test summary command when PRD doesn't exist."""
    args = argparse.Namespace()

    with patch("ralph.commands.Path.cwd", return_value=tmp_path):
        with pytest.raises(SystemExit):
            commands.summary_command(args)


def test_close_phase_command(mock_prd_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test close-phase command."""
    args = argparse.Namespace(phase_number=1)

    with patch("ralph.commands.Path.cwd", return_value=mock_prd_path.parent.parent):
        commands.close_phase_command(args)

    captured = capsys.readouterr()
    assert "Closed phase 1" in captured.out
    assert "US-001" in captured.out


def test_skip_story_command(mock_prd_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test skip-story command."""
    args = argparse.Namespace(story_id="US-001")

    with patch("ralph.commands.Path.cwd", return_value=mock_prd_path.parent.parent):
        commands.skip_story_command(args)

    captured = capsys.readouterr()
    assert "Skipped story US-001" in captured.out


def test_skip_story_command_not_found(mock_prd_path: Path) -> None:
    """Test skip-story command with non-existent story."""
    args = argparse.Namespace(story_id="US-999")

    with patch("ralph.commands.Path.cwd", return_value=mock_prd_path.parent.parent):
        with pytest.raises(SystemExit):
            commands.skip_story_command(args)


def test_start_story_command(mock_prd_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test start-story command."""
    args = argparse.Namespace(story_id="US-001")

    with patch("ralph.commands.Path.cwd", return_value=mock_prd_path.parent.parent):
        commands.start_story_command(args)

    captured = capsys.readouterr()
    assert "Started story US-001" in captured.out


def test_start_story_command_not_found(mock_prd_path: Path) -> None:
    """Test start-story command with non-existent story."""
    args = argparse.Namespace(story_id="US-999")

    with patch("ralph.commands.Path.cwd", return_value=mock_prd_path.parent.parent):
        with pytest.raises(SystemExit):
            commands.start_story_command(args)


def test_in_progress_command(mock_prd_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test in-progress command."""
    args = argparse.Namespace()

    with patch("ralph.commands.Path.cwd", return_value=mock_prd_path.parent.parent):
        commands.in_progress_command(args)

    captured = capsys.readouterr()
    assert "Stories currently in progress" in captured.out
    assert "US-002" in captured.out


def test_clear_stale_command(mock_prd_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test clear-stale command."""
    args = argparse.Namespace(max_age_hours=0)

    with patch("ralph.commands.Path.cwd", return_value=mock_prd_path.parent.parent):
        commands.clear_stale_command(args)

    captured = capsys.readouterr()
    assert "Cleared stale in_progress status" in captured.out


def test_list_stories_command(mock_prd_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test list-stories command."""
    args = argparse.Namespace(phase=None, status=None)

    with patch("ralph.commands.Path.cwd", return_value=mock_prd_path.parent.parent):
        commands.list_stories_command(args)

    captured = capsys.readouterr()
    assert "US-001" in captured.out
    assert "US-002" in captured.out


def test_list_stories_command_with_filters(
    mock_prd_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Test list-stories command with filters."""
    args = argparse.Namespace(phase=1, status="incomplete")

    with patch("ralph.commands.Path.cwd", return_value=mock_prd_path.parent.parent):
        commands.list_stories_command(args)

    captured = capsys.readouterr()
    assert "US-001" in captured.out
    assert "US-002" not in captured.out
