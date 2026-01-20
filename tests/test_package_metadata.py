"""Tests for package metadata and installation."""

import importlib.metadata
import subprocess
import sys

import pytest


def test_package_version() -> None:
    """Test that package version is accessible."""
    import ralph

    assert ralph.__version__ == "0.1.0"


def test_package_metadata() -> None:
    """Test that package metadata is correct."""
    metadata = importlib.metadata.metadata("ralph")

    assert metadata["Name"] == "ralph"
    assert metadata["Version"] == "0.1.0"
    assert "Autonomous AI agent loop" in metadata["Summary"]
    assert "Rodion Steshenko" in metadata["Author-Email"]


def test_package_dependencies() -> None:
    """Test that package dependencies are correct."""
    requires = importlib.metadata.requires("ralph")
    assert requires is not None

    # Check runtime dependencies
    runtime_deps = [dep for dep in requires if "extra" not in dep]
    dep_names = [dep.split(">=")[0].split("==")[0].lower() for dep in runtime_deps]
    assert "anthropic" in dep_names
    assert "pillow" in dep_names
    assert "rich" in dep_names


def test_package_entry_points() -> None:
    """Test that package entry points are correct."""
    eps = importlib.metadata.entry_points()

    # Get console_scripts group
    if hasattr(eps, "select"):
        # Python 3.10+
        console_scripts = eps.select(group="console_scripts")
    else:
        # Python 3.9
        console_scripts = eps.get("console_scripts", [])

    # Find ralph entry point
    ralph_eps = [ep for ep in console_scripts if ep.name == "ralph"]
    assert len(ralph_eps) == 1
    assert ralph_eps[0].value == "ralph.cli:main"


def test_ralph_command_available() -> None:
    """Test that ralph command is available in PATH."""
    result = subprocess.run(
        ["which", "ralph"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "ralph" in result.stdout


def test_ralph_imports() -> None:
    """Test that ralph package can be imported."""
    import ralph
    import ralph.cli
    import ralph.detect
    import ralph.loop
    import ralph.prd
    import ralph.utils

    # All modules should be importable
    assert ralph is not None
    assert ralph.cli is not None
    assert ralph.detect is not None
    assert ralph.loop is not None
    assert ralph.prd is not None
    assert ralph.utils is not None
