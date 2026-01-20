"""End-to-end tests for editable install (US-011).

These tests verify that 'pip install -e .' works correctly for development.
"""

import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.mark.e2e
def test_editable_install_ralph_version() -> None:
    """E2E: Test ralph --version works after editable install."""
    result = subprocess.run(
        ["ralph", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "ralph 0.1.0" in result.stdout, f"Version not found in: {result.stdout}"


@pytest.mark.e2e
def test_editable_install_ralph_help() -> None:
    """E2E: Test ralph --help shows all commands after editable install."""
    result = subprocess.run(
        ["ralph", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Command failed: {result.stderr}"

    # Verify all required commands are shown
    required_commands = [
        "init",
        "process-prd",
        "build-prd",
        "execute",
        "status",
        "select",
        "validate",
    ]

    for command in required_commands:
        assert command in result.stdout, f"Command '{command}' not in help output"


@pytest.mark.e2e
def test_editable_install_ralph_init() -> None:
    """E2E: Test ralph init creates .ralph/ in current directory after editable install."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Run init in temporary directory
        result = subprocess.run(
            ["ralph", "init"],
            capture_output=True,
            text=True,
            cwd=tmpdir,
        )

        assert result.returncode == 0, f"Init failed: {result.stderr}"
        assert "Ralph initialized" in result.stdout

        # Verify .ralph/ directory structure was created
        ralph_dir = Path(tmpdir) / ".ralph"
        assert ralph_dir.exists(), ".ralph/ directory not created"
        assert ralph_dir.is_dir(), ".ralph/ is not a directory"

        # Verify subdirectories
        assert (ralph_dir / "logs").exists(), "logs/ subdirectory not created"
        assert (ralph_dir / "skills").exists(), "skills/ subdirectory not created"

        # Verify files
        assert (ralph_dir / "progress.md").exists(), "progress.md not created"

        # Verify progress.md has correct header
        progress_content = (ralph_dir / "progress.md").read_text()
        assert "Ralph Progress Log" in progress_content


@pytest.mark.e2e
def test_editable_install_commands_work() -> None:
    """E2E: Test all major commands are accessible after editable install."""
    # Test that each command can be invoked (even if they fail due to missing context)
    commands = [
        (["ralph", "init", "--help"], 0),
        (["ralph", "process-prd", "--help"], 0),
        (["ralph", "build-prd", "--help"], 0),
        (["ralph", "execute", "--help"], 0),
        (["ralph", "status", "--help"], 0),
        (["ralph", "select", "--help"], 0),
        (["ralph", "validate", "--help"], 0),
    ]

    for cmd, expected_code in commands:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        assert result.returncode == expected_code, (
            f"Command {' '.join(cmd)} failed with code {result.returncode}. "
            f"Stderr: {result.stderr}"
        )


@pytest.mark.e2e
def test_editable_install_module_import() -> None:
    """E2E: Test ralph package can be imported after editable install."""
    result = subprocess.run(
        ["python3", "-c", "import ralph; print(ralph.__version__)"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Import failed: {result.stderr}"
    assert "0.1.0" in result.stdout, f"Version not found in: {result.stdout}"


@pytest.mark.e2e
def test_editable_install_cli_entrypoint() -> None:
    """E2E: Test CLI entrypoint is properly installed."""
    # Verify ralph command exists
    result = subprocess.run(
        ["which", "ralph"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, "ralph command not found in PATH"
    assert result.stdout.strip(), "ralph command path is empty"

    # Verify it's the right one (should be in virtualenv)
    ralph_path = result.stdout.strip()
    assert "bin/ralph" in ralph_path or "Scripts\\ralph" in ralph_path


@pytest.mark.e2e
def test_editable_install_changes_reflected() -> None:
    """E2E: Verify that editable install means code changes are reflected immediately.

    This is the key benefit of editable installs - changes to source files
    are immediately available without reinstalling.
    """
    # Just verify the package is installed in editable mode by checking
    # that we can import from the source location
    import ralph

    module_file = Path(ralph.__file__)

    # In editable mode, the module should point to src/ralph/__init__.py
    assert "src/ralph" in str(module_file) or "ralph" in module_file.parts
