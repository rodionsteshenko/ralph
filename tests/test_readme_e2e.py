"""End-to-end tests verifying README documentation accuracy."""

import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.mark.e2e
def test_readme_quick_start_workflow() -> None:
    """
    Verify the Quick Start workflow from README works correctly.

    Tests the documented workflow:
    1. ralph init
    2. ralph status (should work after init)
    3. ralph --version
    4. ralph --help
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Test: ralph init
        result = subprocess.run(
            ["ralph", "init"],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"ralph init failed: {result.stderr}"
        assert (project_dir / ".ralph").exists(), ".ralph directory not created"

        # Test: ralph status (should work after init)
        result = subprocess.run(
            ["ralph", "status"],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )
        # Should exit with code 1 (no PRD found) but not crash
        assert result.returncode in [0, 1], f"ralph status crashed: {result.stderr}"

        # Test: ralph --version
        result = subprocess.run(
            ["ralph", "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"ralph --version failed: {result.stderr}"
        assert "0.1.0" in result.stdout, "Version not in output"

        # Test: ralph --help
        result = subprocess.run(
            ["ralph", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"ralph --help failed: {result.stderr}"
        assert "Ralph" in result.stdout, "Help text missing"
        assert "execute" in result.stdout, "Execute command not documented in help"


@pytest.mark.e2e
def test_readme_command_reference_commands_exist() -> None:
    """
    Verify all commands documented in Command Reference section exist.

    Tests that commands mentioned in README are actually available.
    """
    # Get help output
    result = subprocess.run(
        ["ralph", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    help_text = result.stdout.lower()

    # Commands documented in README Command Reference
    documented_commands = [
        "init",
        "process-prd",
        "build-prd",
        "execute",
        "status",
        "view",
        "summary",
        "list-stories",
        "skip-story",
        "start-story",
        "in-progress",
        "clear-stale",
        "close-phase",
        "validate",
        "select",
    ]

    for command in documented_commands:
        assert command in help_text, f"Command '{command}' not found in help output"


@pytest.mark.e2e
def test_readme_cli_override_flags() -> None:
    """
    Verify CLI override flags documented in README are accepted.

    Tests that flags like --model, --verbose, etc. are recognized.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Initialize first
        subprocess.run(["ralph", "init"], cwd=project_dir, check=True)

        # Test that execute command accepts documented flags
        # (Will fail due to no PRD, but should recognize the flags)
        result = subprocess.run(
            [
                "ralph",
                "execute",
                "--model",
                "claude-opus-4-5",
                "--verbose",
                "--max-iterations",
                "1",
            ],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )

        # Should fail due to no PRD, not due to unrecognized flags
        # If flags are invalid, argparse would exit with code 2
        assert result.returncode != 2, (
            f"CLI flags not recognized (argparse error): {result.stderr}"
        )


@pytest.mark.e2e
def test_readme_project_structure() -> None:
    """
    Verify the project structure documented in README is created correctly.

    Tests that ralph init creates the documented .ralph/ structure.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Initialize Ralph
        result = subprocess.run(
            ["ralph", "init"],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        # Verify documented structure exists
        ralph_dir = project_dir / ".ralph"
        assert ralph_dir.exists(), ".ralph/ directory not created"
        assert ralph_dir.is_dir(), ".ralph/ is not a directory"

        # Should have logs directory
        logs_dir = ralph_dir / "logs"
        assert logs_dir.exists(), ".ralph/logs/ not created"


@pytest.mark.e2e
def test_readme_aliases() -> None:
    """
    Verify command aliases documented in README work correctly.

    Tests that 'execute-plan' and 'run' are aliases for 'execute'.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        subprocess.run(["ralph", "init"], cwd=project_dir, check=True)

        # Test execute-plan alias
        result = subprocess.run(
            ["ralph", "execute-plan", "--help"],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, "execute-plan alias not working"

        # Test run alias
        result = subprocess.run(
            ["ralph", "run", "--help"],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, "run alias not working"


@pytest.mark.e2e
def test_readme_version_command() -> None:
    """
    Verify --version flag works as documented in README.

    Tests installation verification command from README.
    """
    result = subprocess.run(
        ["ralph", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "0.1.0" in result.stdout, "Version string not in output"

    # Version should be on stdout, not stderr
    assert result.stdout.strip(), "Version not written to stdout"


def test_readme_exists_and_has_required_sections() -> None:
    """
    Verify README exists and contains all documented sections.

    This is a unit test that checks the README structure.
    """
    readme_path = Path(__file__).parent.parent / "README.md"
    assert readme_path.exists(), "README.md not found"

    content = readme_path.read_text()

    # Required sections from acceptance criteria
    required_sections = [
        "## Installation",
        "### From PyPI",
        "### From Git Repository",
        "## Quick Start",
        "## Command Reference",
        "## Configuration & Auto-Detection",
    ]

    for section in required_sections:
        assert section in content, f"README missing required section: {section}"

    # Check for specific content requirements
    assert "pip install ralph" in content, "PyPI installation not documented"
    assert "pip install git+" in content, "Git installation not documented"
    assert "ralph init" in content, "init command not documented"
    assert "ralph execute" in content, "execute command not documented"
    assert "auto-detect" in content.lower(), "Auto-detection not documented"


def test_readme_line_count() -> None:
    """Verify README is within reasonable size limits."""
    readme_path = Path(__file__).parent.parent / "README.md"
    lines = readme_path.read_text().splitlines()

    # README should be comprehensive but not excessively long
    assert len(lines) < 800, f"README too long: {len(lines)} lines"
    assert len(lines) > 100, f"README too short: {len(lines)} lines"
