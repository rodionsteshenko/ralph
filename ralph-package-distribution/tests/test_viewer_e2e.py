"""End-to-end tests for the viewer command."""

import json
import subprocess
from pathlib import Path

import pytest


@pytest.mark.e2e
def test_view_command_once(tmp_path: Path) -> None:
    """Test 'ralph view --once' command works end-to-end."""
    # Create .ralph directory and prd.json
    ralph_dir = tmp_path / ".ralph"
    ralph_dir.mkdir()

    prd_data = {
        "project": "Test Project",
        "userStories": [
            {
                "id": "US-001",
                "title": "Test Story",
                "phase": 1,
                "status": "incomplete",  # Use incomplete so phase isn't closed
            }
        ],
    }

    prd_path = ralph_dir / "prd.json"
    with open(prd_path, "w") as f:
        json.dump(prd_data, f)

    # Run ralph view --once
    result = subprocess.run(
        ["ralph", "view", "--once"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )

    # Check it succeeded
    assert result.returncode == 0, f"Command failed: {result.stderr}"

    # Check output contains expected content
    output = result.stdout
    assert "Test Project" in output
    assert "US-001" in output
    assert "Test Story" in output


@pytest.mark.e2e
def test_view_command_with_expand(tmp_path: Path) -> None:
    """Test 'ralph view --once --expand' command works."""
    # Create .ralph directory and prd.json with closed phase
    ralph_dir = tmp_path / ".ralph"
    ralph_dir.mkdir()

    prd_data = {
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
        ],
    }

    prd_path = ralph_dir / "prd.json"
    with open(prd_path, "w") as f:
        json.dump(prd_data, f)

    # Run ralph view --once --expand
    result = subprocess.run(
        ["ralph", "view", "--once", "--expand"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )

    # Check it succeeded
    assert result.returncode == 0, f"Command failed: {result.stderr}"

    # Check output shows individual stories (expanded)
    output = result.stdout
    assert "US-001" in output
    assert "US-002" in output


@pytest.mark.e2e
def test_view_command_no_prd(tmp_path: Path) -> None:
    """Test 'ralph view' fails gracefully when no PRD exists."""
    # Don't create .ralph directory

    # Run ralph view --once
    result = subprocess.run(
        ["ralph", "view", "--once"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )

    # Should fail
    assert result.returncode != 0

    # Should show helpful error
    assert "No prd.json found" in result.stdout or "No prd.json found" in result.stderr
