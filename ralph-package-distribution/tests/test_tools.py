"""Tests for PRD management tools."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

import pytest

from ralph.tools import PRDManager, resolve_prd_path


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
            "createdAt": datetime.now().isoformat(),
            "lastUpdatedAt": datetime.now().isoformat(),
            "totalStories": 3,
            "completedStories": 1,
            "currentIteration": 0,
        },
    }


@pytest.fixture
def prd_file(tmp_path: Path, sample_prd_data: Dict[str, Any]) -> Path:
    """Create a temporary PRD file."""
    ralph_dir = tmp_path / ".ralph"
    ralph_dir.mkdir()
    prd_path = ralph_dir / "prd.json"
    with open(prd_path, "w") as f:
        json.dump(sample_prd_data, f, indent=2)
    return prd_path


def test_resolve_prd_path_with_ralph_dir(tmp_path: Path, prd_file: Path) -> None:
    """Test resolving PRD path from project directory with .ralph/."""
    resolved = resolve_prd_path(tmp_path)
    assert resolved == prd_file


def test_resolve_prd_path_fallback(tmp_path: Path) -> None:
    """Test resolving PRD path fallback to project directory."""
    prd_path = tmp_path / "prd.json"
    with open(prd_path, "w") as f:
        json.dump({"project": "test"}, f)

    resolved = resolve_prd_path(tmp_path)
    assert resolved == prd_path


def test_resolve_prd_path_not_found(tmp_path: Path) -> None:
    """Test error when PRD not found."""
    with pytest.raises(FileNotFoundError):
        resolve_prd_path(tmp_path)


def test_prd_manager_load(prd_file: Path) -> None:
    """Test loading PRD file."""
    manager = PRDManager(prd_file)
    assert manager.data["project"] == "Test Project"
    assert len(manager.data["userStories"]) == 3


def test_prd_manager_save(prd_file: Path) -> None:
    """Test saving PRD file."""
    manager = PRDManager(prd_file)
    original_timestamp = manager.data["metadata"]["lastUpdatedAt"]

    # Modify data and save
    manager.data["project"] = "Modified Project"
    manager.save()

    # Reload and verify
    manager2 = PRDManager(prd_file)
    assert manager2.data["project"] == "Modified Project"
    assert manager2.data["metadata"]["lastUpdatedAt"] != original_timestamp


def test_update_story_phase(prd_file: Path) -> None:
    """Test updating story phase."""
    manager = PRDManager(prd_file)

    assert manager.update_story_phase("US-001", 2)
    assert manager.data["userStories"][0]["phase"] == 2

    # Non-existent story
    assert not manager.update_story_phase("US-999", 2)


def test_update_story_status(prd_file: Path) -> None:
    """Test updating story status."""
    manager = PRDManager(prd_file)

    assert manager.update_story_status("US-001", "complete")
    assert manager.data["userStories"][0]["status"] == "complete"
    assert manager.data["metadata"]["completedStories"] == 2

    # Non-existent story
    assert not manager.update_story_status("US-999", "complete")


def test_bulk_update_phases(prd_file: Path) -> None:
    """Test bulk updating phases."""
    manager = PRDManager(prd_file)

    phase_mapping = {"US-001": 3, "US-002": 3}
    updated = manager.bulk_update_phases(phase_mapping)

    assert len(updated) == 2
    assert "US-001" in updated
    assert manager.data["userStories"][0]["phase"] == 3
    assert manager.data["userStories"][1]["phase"] == 3


def test_list_stories_no_filter(prd_file: Path) -> None:
    """Test listing all stories."""
    manager = PRDManager(prd_file)
    stories = manager.list_stories()
    assert len(stories) == 3


def test_list_stories_by_phase(prd_file: Path) -> None:
    """Test listing stories by phase."""
    manager = PRDManager(prd_file)
    stories = manager.list_stories(phase=1)
    assert len(stories) == 2
    assert all(s["phase"] == 1 for s in stories)


def test_list_stories_by_status(prd_file: Path) -> None:
    """Test listing stories by status."""
    manager = PRDManager(prd_file)
    stories = manager.list_stories(status="complete")
    assert len(stories) == 1
    assert stories[0]["id"] == "US-002"


def test_get_summary(prd_file: Path) -> None:
    """Test getting summary statistics."""
    manager = PRDManager(prd_file)
    summary = manager.get_summary()

    assert summary["total_stories"] == 3
    assert summary["completed_stories"] == 1
    assert summary["remaining_stories"] == 2
    assert summary["completion_percentage"] == 33.3
    assert 1 in summary["by_phase"]
    assert 2 in summary["by_phase"]


def test_close_phase(prd_file: Path) -> None:
    """Test closing a phase."""
    manager = PRDManager(prd_file)

    skipped = manager.close_phase(1)
    assert len(skipped) == 1
    assert "US-001" in skipped

    # Verify story was skipped
    story = next(s for s in manager.data["userStories"] if s["id"] == "US-001")
    assert story["status"] == "skipped"
    assert "skippedAt" in story


def test_skip_story(prd_file: Path) -> None:
    """Test skipping a story."""
    manager = PRDManager(prd_file)

    assert manager.skip_story("US-001")
    story = manager.data["userStories"][0]
    assert story["status"] == "skipped"
    assert "skippedAt" in story

    # Non-existent story
    assert not manager.skip_story("US-999")


def test_start_story(prd_file: Path) -> None:
    """Test starting a story."""
    manager = PRDManager(prd_file)

    assert manager.start_story("US-001")
    story = manager.data["userStories"][0]
    assert story["status"] == "in_progress"
    assert "startedAt" in story

    # Non-existent story
    assert not manager.start_story("US-999")


def test_get_in_progress(prd_file: Path) -> None:
    """Test getting in-progress stories."""
    manager = PRDManager(prd_file)

    # Initially none
    assert len(manager.get_in_progress()) == 0

    # Start a story
    manager.start_story("US-001")
    in_progress = manager.get_in_progress()
    assert len(in_progress) == 1
    assert in_progress[0]["id"] == "US-001"


def test_clear_stale_in_progress(prd_file: Path) -> None:
    """Test clearing stale in-progress stories."""
    manager = PRDManager(prd_file)

    # Mark story as in-progress with old timestamp
    story = manager.data["userStories"][0]
    story["status"] = "in_progress"
    old_time = datetime.now() - timedelta(hours=48)
    story["startedAt"] = old_time.isoformat()

    # Clear stale (default 24 hours)
    cleared = manager.clear_stale_in_progress()
    assert len(cleared) == 1
    assert "US-001" in cleared
    assert "status" not in manager.data["userStories"][0]


def test_clear_stale_in_progress_custom_age(prd_file: Path) -> None:
    """Test clearing stale in-progress with custom max age."""
    manager = PRDManager(prd_file)

    # Mark story as in-progress with recent timestamp
    story = manager.data["userStories"][0]
    story["status"] = "in_progress"
    recent_time = datetime.now() - timedelta(hours=12)
    story["startedAt"] = recent_time.isoformat()

    # Clear with 6 hour max age
    cleared = manager.clear_stale_in_progress(max_age_hours=6)
    assert len(cleared) == 1


def test_is_phase_closed(prd_file: Path) -> None:
    """Test checking if a phase is closed."""
    manager = PRDManager(prd_file)

    # Phase 1 has incomplete stories
    assert not manager.is_phase_closed(1)

    # Mark all phase 1 stories as complete/skipped
    manager.update_story_status("US-001", "complete")
    assert manager.is_phase_closed(1)

    # Non-existent phase
    assert not manager.is_phase_closed(99)
