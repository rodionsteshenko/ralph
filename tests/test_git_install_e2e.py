"""End-to-end tests for git installation."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.mark.e2e
def test_git_install_from_main() -> None:
    """Test that Ralph can be installed from git main branch."""
    with tempfile.TemporaryDirectory() as tmpdir:
        venv_path = Path(tmpdir) / "venv"

        # Create virtual environment
        result = subprocess.run(
            ["python3", "-m", "venv", str(venv_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Failed to create venv: {result.stderr}"

        # Install from git
        pip_path = venv_path / "bin" / "pip"
        result = subprocess.run(
            [
                str(pip_path),
                "install",
                "git+https://github.com/rodionsteshenko/ralph.git",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, f"Failed to install from git: {result.stderr}"
        assert "Successfully installed" in result.stdout
        assert "ralph" in result.stdout.lower()


@pytest.mark.e2e
def test_git_install_package_importable() -> None:
    """Test that Ralph package can be imported after git installation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        venv_path = Path(tmpdir) / "venv"

        # Create virtual environment
        subprocess.run(
            ["python3", "-m", "venv", str(venv_path)],
            check=True,
            capture_output=True,
        )

        # Install from git
        pip_path = venv_path / "bin" / "pip"
        subprocess.run(
            [
                str(pip_path),
                "install",
                "git+https://github.com/rodionsteshenko/ralph.git",
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )

        # Test that package can be imported
        python_path = venv_path / "bin" / "python"
        result = subprocess.run(
            [str(python_path), "-c", "import ralph; print('Import successful')"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Failed to import ralph: {result.stderr}"
        assert "Import successful" in result.stdout


@pytest.mark.e2e
@pytest.mark.skipif(
    not os.getenv("TEST_GIT_COMMANDS"),
    reason="TEST_GIT_COMMANDS not set - requires packaged branch on remote",
)
def test_git_install_commands_work() -> None:
    """Test that all Ralph commands work after git installation.

    This test requires that the packaged version (with CLI entry point)
    is available on the remote repository. Set TEST_GIT_COMMANDS env var
    to enable this test.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        venv_path = Path(tmpdir) / "venv"
        project_path = Path(tmpdir) / "project"
        project_path.mkdir()

        # Create virtual environment
        subprocess.run(
            ["python3", "-m", "venv", str(venv_path)],
            check=True,
            capture_output=True,
        )

        # Install from git
        pip_path = venv_path / "bin" / "pip"
        subprocess.run(
            [
                str(pip_path),
                "install",
                "git+https://github.com/rodionsteshenko/ralph.git",
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )

        ralph_path = venv_path / "bin" / "ralph"

        # Test --help command
        result = subprocess.run(
            [str(ralph_path), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Ralph: Autonomous AI Agent Loop" in result.stdout

        # Test --version command
        result = subprocess.run(
            [str(ralph_path), "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "ralph" in result.stdout.lower()

        # Test init command
        result = subprocess.run(
            [str(ralph_path), "init"],
            cwd=str(project_path),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Ralph initialized" in result.stdout
        assert (project_path / ".ralph").is_dir()

        # Test status command (expected to fail with no PRD)
        result = subprocess.run(
            [str(ralph_path), "status"],
            cwd=str(project_path),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "No PRD found" in result.stderr


@pytest.mark.e2e
@pytest.mark.skipif(
    not os.getenv("TEST_GIT_BRANCH"),
    reason="TEST_GIT_BRANCH environment variable not set",
)
def test_git_install_from_branch() -> None:
    """Test that Ralph can be installed from a specific git branch."""
    branch = os.getenv("TEST_GIT_BRANCH")

    with tempfile.TemporaryDirectory() as tmpdir:
        venv_path = Path(tmpdir) / "venv"

        # Create virtual environment
        subprocess.run(
            ["python3", "-m", "venv", str(venv_path)],
            check=True,
            capture_output=True,
        )

        # Install from git branch
        pip_path = venv_path / "bin" / "pip"
        result = subprocess.run(
            [
                str(pip_path),
                "install",
                f"git+https://github.com/rodionsteshenko/ralph.git@{branch}",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, f"Failed to install from branch: {result.stderr}"
        assert "Successfully installed" in result.stdout
