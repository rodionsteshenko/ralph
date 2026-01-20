"""End-to-end tests for PRD management tools CLI commands."""

import json
import subprocess
from pathlib import Path
from typing import Any, Dict

import pytest


@pytest.fixture
def sample_prd_data() -> Dict[str, Any]:
    """Sample PRD data for testing."""
    return {
        "project": "Test Project",
        "branchName": "test-branch",
        "description": "Test description",
        "userStories": [
            {
                "id": "US-001",
                "title": "Story 1",
                "description": "Description 1",
                "acceptanceCriteria": ["AC1"],
                "priority": 1,
                "phase": 1,
                "status": "incomplete",
            },
            {
                "id": "US-002",
                "title": "Story 2",
                "description": "Description 2",
                "acceptanceCriteria": ["AC2"],
                "priority": 2,
                "phase": 1,
                "status": "complete",
            },
            {
                "id": "US-003",
                "title": "Story 3",
                "description": "Description 3",
                "acceptanceCriteria": ["AC3"],
                "priority": 3,
                "phase": 2,
                "status": "incomplete",
            },
        ],
        "metadata": {
            "createdAt": "2024-01-01T12:00:00",
            "lastUpdatedAt": "2024-01-01T12:00:00",
            "totalStories": 3,
            "completedStories": 1,
            "currentIteration": 0,
            "phases": {
                "1": {"name": "Phase 1", "description": "First phase"},
                "2": {"name": "Phase 2", "description": "Second phase"},
            },
        },
    }


@pytest.fixture
def test_project_dir(tmp_path: Path, sample_prd_data: Dict[str, Any]) -> Path:
    """Create a test project directory with PRD."""
    ralph_dir = tmp_path / ".ralph"
    ralph_dir.mkdir()
    prd_path = ralph_dir / "prd.json"
    with open(prd_path, "w") as f:
        json.dump(sample_prd_data, f, indent=2)
    return tmp_path


@pytest.mark.e2e
def test_summary_command_e2e(test_project_dir: Path) -> None:
    """Test summary command end-to-end."""
    result = subprocess.run(
        ["ralph", "summary"],
        cwd=test_project_dir,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "PRD Summary" in result.stdout
    assert "Total Stories: 3" in result.stdout
    assert "Completed: 1" in result.stdout
    assert "Phase 1" in result.stdout


@pytest.mark.e2e
def test_skip_story_command_e2e(test_project_dir: Path) -> None:
    """Test skip-story command end-to-end."""
    result = subprocess.run(
        ["ralph", "skip-story", "US-001"],
        cwd=test_project_dir,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Skipped story US-001" in result.stdout

    # Verify story was skipped
    prd_path = test_project_dir / ".ralph" / "prd.json"
    with open(prd_path) as f:
        prd = json.load(f)
    story = next(s for s in prd["userStories"] if s["id"] == "US-001")
    assert story["status"] == "skipped"


@pytest.mark.e2e
def test_start_story_command_e2e(test_project_dir: Path) -> None:
    """Test start-story command end-to-end."""
    result = subprocess.run(
        ["ralph", "start-story", "US-001"],
        cwd=test_project_dir,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Started story US-001" in result.stdout

    # Verify story was started
    prd_path = test_project_dir / ".ralph" / "prd.json"
    with open(prd_path) as f:
        prd = json.load(f)
    story = next(s for s in prd["userStories"] if s["id"] == "US-001")
    assert story["status"] == "in_progress"
    assert "startedAt" in story


@pytest.mark.e2e
def test_in_progress_command_e2e(test_project_dir: Path) -> None:
    """Test in-progress command end-to-end."""
    # First start a story
    subprocess.run(
        ["ralph", "start-story", "US-001"],
        cwd=test_project_dir,
        capture_output=True,
    )

    # Then check in-progress
    result = subprocess.run(
        ["ralph", "in-progress"],
        cwd=test_project_dir,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Stories currently in progress" in result.stdout
    assert "US-001" in result.stdout


@pytest.mark.e2e
def test_close_phase_command_e2e(test_project_dir: Path) -> None:
    """Test close-phase command end-to-end."""
    result = subprocess.run(
        ["ralph", "close-phase", "2"],
        cwd=test_project_dir,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Closed phase 2" in result.stdout
    assert "US-003" in result.stdout

    # Verify story was skipped
    prd_path = test_project_dir / ".ralph" / "prd.json"
    with open(prd_path) as f:
        prd = json.load(f)
    story = next(s for s in prd["userStories"] if s["id"] == "US-003")
    assert story["status"] == "skipped"


@pytest.mark.e2e
def test_clear_stale_command_e2e(test_project_dir: Path) -> None:
    """Test clear-stale command end-to-end."""
    # Start a story with old timestamp
    prd_path = test_project_dir / ".ralph" / "prd.json"
    with open(prd_path) as f:
        prd = json.load(f)
    prd["userStories"][0]["status"] = "in_progress"
    prd["userStories"][0]["startedAt"] = "2024-01-01T00:00:00"
    with open(prd_path, "w") as f:
        json.dump(prd, f)

    # Clear stale with 1 hour max age
    result = subprocess.run(
        ["ralph", "clear-stale", "--max-age-hours", "1"],
        cwd=test_project_dir,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Cleared stale in_progress status" in result.stdout
    assert "US-001" in result.stdout


@pytest.mark.e2e
def test_list_stories_command_e2e(test_project_dir: Path) -> None:
    """Test list-stories command end-to-end."""
    result = subprocess.run(
        ["ralph", "list-stories"],
        cwd=test_project_dir,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "US-001" in result.stdout
    assert "US-002" in result.stdout
    assert "US-003" in result.stdout


@pytest.mark.e2e
def test_list_stories_with_filters_e2e(test_project_dir: Path) -> None:
    """Test list-stories command with filters end-to-end."""
    result = subprocess.run(
        ["ralph", "list-stories", "--phase", "1", "--status", "incomplete"],
        cwd=test_project_dir,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "US-001" in result.stdout
    assert "US-002" not in result.stdout
    assert "US-003" not in result.stdout


@pytest.mark.e2e
def test_command_error_handling_e2e(test_project_dir: Path) -> None:
    """Test error handling for non-existent story."""
    result = subprocess.run(
        ["ralph", "skip-story", "US-999"],
        cwd=test_project_dir,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "not found" in result.stdout.lower()
