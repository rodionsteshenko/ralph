"""Tests for CLI entry point."""

import subprocess
import sys
from pathlib import Path

import pytest


def test_cli_help() -> None:
    """Test that ralph --help works."""
    result = subprocess.run(
        ["ralph", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Ralph: Autonomous AI Agent Loop" in result.stdout


def test_cli_version() -> None:
    """Test that ralph --version works."""
    result = subprocess.run(
        ["ralph", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "0.1.0" in result.stdout


def test_cli_no_command() -> None:
    """Test that ralph with no command shows help."""
    result = subprocess.run(
        ["ralph"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "Ralph: Autonomous AI Agent Loop" in result.stdout


def test_cli_init_command() -> None:
    """Test that ralph init command exists."""
    result = subprocess.run(
        ["ralph", "init"],
        capture_output=True,
        text=True,
    )
    # Placeholder implementation returns 0
    assert result.returncode == 0
    assert "not yet implemented" in result.stdout


def test_cli_status_command() -> None:
    """Test that ralph status command exists."""
    result = subprocess.run(
        ["ralph", "status"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "not yet implemented" in result.stdout


def test_cli_execute_command() -> None:
    """Test that ralph execute command exists."""
    result = subprocess.run(
        ["ralph", "execute"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "not yet implemented" in result.stdout


def test_cli_execute_alias_run() -> None:
    """Test that ralph run alias works."""
    result = subprocess.run(
        ["ralph", "run"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "not yet implemented" in result.stdout


def test_cli_process_prd_command() -> None:
    """Test that ralph process-prd command requires argument."""
    result = subprocess.run(
        ["ralph", "process-prd"],
        capture_output=True,
        text=True,
    )
    # Should fail because prd_file argument is required
    assert result.returncode != 0
    assert "required" in result.stderr or "error" in result.stderr


def test_cli_validate_command() -> None:
    """Test that ralph validate command exists."""
    result = subprocess.run(
        ["ralph", "validate"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "not yet implemented" in result.stdout


def test_cli_validate_strict_flag() -> None:
    """Test that ralph validate --strict flag works."""
    result = subprocess.run(
        ["ralph", "validate", "--strict"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "not yet implemented" in result.stdout
