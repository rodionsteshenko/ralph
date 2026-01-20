"""End-to-end tests for CLI functionality.

These tests verify the actual ralph command works in real scenarios.
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.mark.e2e
def test_cli_e2e_help() -> None:
    """E2E: Test ralph --help command works."""
    result = subprocess.run(
        ["ralph", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Ralph: Autonomous AI Agent Loop" in result.stdout
    assert "init" in result.stdout
    assert "execute" in result.stdout
    assert "validate" in result.stdout


@pytest.mark.e2e
def test_cli_e2e_version() -> None:
    """E2E: Test ralph --version command works."""
    result = subprocess.run(
        ["ralph", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "ralph 0.1.0" in result.stdout


@pytest.mark.e2e
def test_cli_e2e_init_workflow() -> None:
    """E2E: Test full init workflow in real directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Run init
        result = subprocess.run(
            ["ralph", "init"],
            capture_output=True,
            text=True,
            cwd=tmpdir,
        )

        assert result.returncode == 0
        assert "Ralph initialized" in result.stdout

        # Verify directory structure
        ralph_dir = Path(tmpdir) / ".ralph"
        assert ralph_dir.exists()
        assert (ralph_dir / "logs").exists()
        assert (ralph_dir / "skills").exists()
        assert (ralph_dir / "progress.md").exists()

        # Verify progress.md content
        progress_content = (ralph_dir / "progress.md").read_text()
        assert "Ralph Progress Log" in progress_content


@pytest.mark.e2e
def test_cli_e2e_init_already_initialized() -> None:
    """E2E: Test init command when already initialized."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # First init
        subprocess.run(["ralph", "init"], cwd=tmpdir, check=True)

        # Second init
        result = subprocess.run(
            ["ralph", "init"],
            capture_output=True,
            text=True,
            cwd=tmpdir,
        )

        assert result.returncode == 0
        assert "already initialized" in result.stdout


@pytest.mark.e2e
def test_cli_e2e_validate_command() -> None:
    """E2E: Test validate command with real PRD."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize
        subprocess.run(["ralph", "init"], cwd=tmpdir, check=True)

        # Create a valid PRD
        prd_path = Path(tmpdir) / ".ralph" / "prd.json"
        prd_data = {
            "project": "Test Project",
            "description": "Test description",
            "userStories": [
                {
                    "id": "US-001",
                    "title": "Test Story",
                    "description": "As a user...",
                    "acceptanceCriteria": ["Criterion 1", "Typecheck passes"],
                    "status": "incomplete",
                    "priority": 1
                }
            ]
        }
        prd_path.write_text(json.dumps(prd_data, indent=2))

        # Run validate
        result = subprocess.run(
            ["ralph", "validate"],
            capture_output=True,
            text=True,
            cwd=tmpdir,
        )

        assert result.returncode == 0
        assert "validation passed" in result.stdout


@pytest.mark.e2e
def test_cli_e2e_validate_with_errors() -> None:
    """E2E: Test validate command with invalid PRD."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize
        subprocess.run(["ralph", "init"], cwd=tmpdir, check=True)

        # Create an invalid PRD (missing userStories)
        prd_path = Path(tmpdir) / ".ralph" / "prd.json"
        prd_data = {
            "project": "Test Project"
        }
        prd_path.write_text(json.dumps(prd_data, indent=2))

        # Run validate
        result = subprocess.run(
            ["ralph", "validate"],
            capture_output=True,
            text=True,
            cwd=tmpdir,
        )

        assert result.returncode == 1
        assert "Errors" in result.stdout or "MISSING_STORIES" in result.stdout


@pytest.mark.e2e
def test_cli_e2e_select_command() -> None:
    """E2E: Test select command shows incomplete stories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize
        subprocess.run(["ralph", "init"], cwd=tmpdir, check=True)

        # Create PRD with stories
        prd_path = Path(tmpdir) / ".ralph" / "prd.json"
        prd_data = {
            "project": "Test Project",
            "userStories": [
                {
                    "id": "US-001",
                    "title": "First Story",
                    "status": "incomplete",
                    "priority": 1
                },
                {
                    "id": "US-002",
                    "title": "Second Story",
                    "status": "complete",
                    "priority": 2
                }
            ]
        }
        prd_path.write_text(json.dumps(prd_data, indent=2))

        # Run select
        result = subprocess.run(
            ["ralph", "select"],
            capture_output=True,
            text=True,
            cwd=tmpdir,
        )

        assert result.returncode == 0
        assert "US-001" in result.stdout
        assert "First Story" in result.stdout
        # US-002 should NOT appear (it's complete)
        assert "US-002" not in result.stdout


@pytest.mark.e2e
def test_cli_e2e_execute_without_prd() -> None:
    """E2E: Test execute command fails without PRD."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize
        subprocess.run(["ralph", "init"], cwd=tmpdir, check=True)

        # Try to execute without PRD
        result = subprocess.run(
            ["ralph", "execute"],
            capture_output=True,
            text=True,
            cwd=tmpdir,
        )

        assert result.returncode == 1
        assert "No PRD found" in result.stdout


@pytest.mark.e2e
def test_cli_e2e_execute_flags() -> None:
    """E2E: Test execute command accepts all flags."""
    result = subprocess.run(
        ["ralph", "execute", "--help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    # Verify all required flags are present
    required_flags = [
        "--max-iterations",
        "--phase",
        "--model",
        "--typecheck-cmd",
        "--lint-cmd",
        "--test-cmd",
        "--verbose",
        "--no-gates"
    ]
    for flag in required_flags:
        assert flag in result.stdout, f"Missing flag: {flag}"


@pytest.mark.e2e
def test_cli_e2e_all_commands_exist() -> None:
    """E2E: Test all required commands are available."""
    commands = [
        "init",
        "process-prd",
        "build-prd",
        "execute",
        "execute-plan",
        "run",
        "status",
        "select",
        "validate"
    ]

    for command in commands:
        result = subprocess.run(
            ["ralph", command, "--help"],
            capture_output=True,
            text=True,
        )
        # Should not fail with "unknown command"
        assert "invalid choice" not in result.stderr.lower()


@pytest.mark.e2e
def test_cli_e2e_build_prd_help() -> None:
    """E2E: Test build-prd command help."""
    result = subprocess.run(
        ["ralph", "build-prd", "--help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "build-prd" in result.stdout.lower()
    assert "prd_file" in result.stdout
    assert "--output" in result.stdout
    assert "--model" in result.stdout


@pytest.mark.e2e
def test_cli_e2e_build_prd_without_init() -> None:
    """E2E: Test build-prd fails without initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prd_file = Path(tmpdir) / "test-prd.txt"
        prd_file.write_text("# Test PRD")

        result = subprocess.run(
            ["ralph", "build-prd", str(prd_file)],
            capture_output=True,
            text=True,
            cwd=tmpdir,
        )

        assert result.returncode == 1
        assert "not initialized" in result.stdout


@pytest.mark.e2e
def test_cli_e2e_build_prd_file_not_found() -> None:
    """E2E: Test build-prd with non-existent file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize
        subprocess.run(["ralph", "init"], cwd=tmpdir, check=True)

        result = subprocess.run(
            ["ralph", "build-prd", "nonexistent.txt"],
            capture_output=True,
            text=True,
            cwd=tmpdir,
        )

        assert result.returncode == 1
        assert "not found" in result.stdout
