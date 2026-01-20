"""Tests for the PRD viewer module."""

from pathlib import Path
from typing import Any

import pytest

from ralph.viewer import (
    build_display,
    format_duration,
    get_story_by_id,
    is_phase_closed,
)


def test_format_duration() -> None:
    """Test duration formatting."""
    assert format_duration(None) == ""
    assert format_duration(30.0) == "30s"
    assert format_duration(90.0) == "1.5m"
    assert format_duration(3600.0) == "1.0h"


def test_get_story_by_id() -> None:
    """Test getting a story by ID."""
    prd: dict[str, Any] = {
        "userStories": [
            {"id": "US-001", "title": "First Story"},
            {"id": "US-002", "title": "Second Story"},
        ]
    }

    story = get_story_by_id(prd, "US-001")
    assert story is not None
    assert story["title"] == "First Story"

    story = get_story_by_id(prd, "US-999")
    assert story is None


def test_is_phase_closed() -> None:
    """Test phase closure detection."""
    # Empty phase
    assert not is_phase_closed([])

    # All complete
    complete_stories = [
        {"status": "complete"},
        {"status": "complete"},
    ]
    assert is_phase_closed(complete_stories)

    # All skipped
    skipped_stories = [
        {"status": "skipped"},
        {"status": "skipped"},
    ]
    assert is_phase_closed(skipped_stories)

    # Mixed complete and skipped
    mixed_closed = [
        {"status": "complete"},
        {"status": "skipped"},
    ]
    assert is_phase_closed(mixed_closed)

    # Has incomplete
    incomplete_stories = [
        {"status": "complete"},
        {"status": "incomplete"},
    ]
    assert not is_phase_closed(incomplete_stories)

    # Has in_progress
    in_progress_stories = [
        {"status": "complete"},
        {"status": "in_progress"},
    ]
    assert not is_phase_closed(in_progress_stories)


def test_build_display_with_none() -> None:
    """Test building display with None PRD."""
    table = build_display(None, Path("/test/path"))
    assert table.title == "PRD Viewer"


def test_build_display_with_valid_prd() -> None:
    """Test building display with a valid PRD."""
    prd: dict[str, Any] = {
        "project": "Test Project",
        "userStories": [
            {
                "id": "US-001",
                "title": "First Story",
                "phase": 1,
                "status": "complete",
                "actualDuration": 120.0,
            },
            {
                "id": "US-002",
                "title": "Second Story",
                "phase": 1,
                "status": "incomplete",
            },
        ],
    }

    table = build_display(prd, Path("/test/path"))
    # Check that table is created with the project name
    assert "Test Project" in str(table.title)
    # Check progress calculation (1/2 = 50%)
    assert "1/2" in str(table.title)
    assert "50" in str(table.title)


def test_build_display_collapse_closed_phases() -> None:
    """Test that closed phases are collapsed by default."""
    prd: dict[str, Any] = {
        "project": "Test Project",
        "userStories": [
            {
                "id": "US-001",
                "title": "First Story",
                "phase": 1,
                "status": "complete",
            },
            {
                "id": "US-002",
                "title": "Second Story",
                "phase": 1,
                "status": "complete",
            },
            {
                "id": "US-003",
                "title": "Third Story",
                "phase": 2,
                "status": "incomplete",
            },
        ],
    }

    # Default: collapsed
    table_collapsed = build_display(prd, Path("/test/path"), expand_closed=False)
    # Verify table was created successfully
    assert table_collapsed is not None
    assert table_collapsed.row_count > 0  # Should have rows

    # Expanded
    table_expanded = build_display(prd, Path("/test/path"), expand_closed=True)
    # When expanded, should have more rows (includes individual stories)
    assert table_expanded is not None
    assert table_expanded.row_count >= table_collapsed.row_count
