"""Tests for CLI entry point."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ralph.cli import (
    execute_command,
    init_command,
    process_prd_command,
    select_command,
    status_command,
    validate_command,
)


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


def test_init_command_creates_structure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that init command creates .ralph directory structure."""
    monkeypatch.chdir(tmp_path)

    args = MagicMock()
    init_command(args)

    # Check directory structure
    assert (tmp_path / ".ralph").exists()
    assert (tmp_path / ".ralph" / "logs").exists()
    assert (tmp_path / ".ralph" / "skills").exists()
    assert (tmp_path / ".ralph" / "progress.md").exists()


def test_init_command_already_initialized(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    """Test that init command handles already initialized directory."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".ralph").mkdir()

    args = MagicMock()
    init_command(args)

    captured = capsys.readouterr()
    assert "already initialized" in captured.out


def test_process_prd_command_file_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that process-prd fails with missing file."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".ralph").mkdir()

    args = MagicMock()
    args.prd_file = tmp_path / "nonexistent.txt"
    args.model = "claude-sonnet-4-5-20250929"

    with pytest.raises(SystemExit) as exc_info:
        process_prd_command(args)

    assert exc_info.value.code == 1


def test_process_prd_command_not_initialized(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that process-prd fails if not initialized."""
    monkeypatch.chdir(tmp_path)

    # Create a PRD file
    prd_file = tmp_path / "prd.txt"
    prd_file.write_text("# Test PRD\n\nTest content")

    args = MagicMock()
    args.prd_file = prd_file
    args.model = "claude-sonnet-4-5-20250929"

    with pytest.raises(SystemExit) as exc_info:
        process_prd_command(args)

    assert exc_info.value.code == 1


@patch('ralph.cli.PRDParser')
def test_process_prd_command_success(mock_parser: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    """Test successful PRD processing."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".ralph").mkdir()

    # Create a PRD file
    prd_file = tmp_path / "prd.txt"
    prd_file.write_text("# Test PRD\n\nTest content")

    # Mock parser
    mock_instance = MagicMock()
    mock_instance.parse_prd.return_value = tmp_path / ".ralph" / "prd.json"
    mock_parser.return_value = mock_instance

    args = MagicMock()
    args.prd_file = prd_file
    args.model = "claude-sonnet-4-5-20250929"

    process_prd_command(args)

    captured = capsys.readouterr()
    assert "successfully processed" in captured.out


def test_execute_command_not_initialized(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that execute fails if not initialized."""
    monkeypatch.chdir(tmp_path)

    args = MagicMock()
    args.max_iterations = None
    args.phase = None
    args.model = None
    args.typecheck_cmd = None
    args.lint_cmd = None
    args.test_cmd = None
    args.verbose = False
    args.no_gates = False

    with pytest.raises(SystemExit) as exc_info:
        execute_command(args)

    assert exc_info.value.code == 1


def test_execute_command_no_prd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that execute fails if no PRD exists."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".ralph").mkdir()

    args = MagicMock()
    args.max_iterations = None
    args.phase = None
    args.model = None
    args.typecheck_cmd = None
    args.lint_cmd = None
    args.test_cmd = None
    args.verbose = False
    args.no_gates = False

    with pytest.raises(SystemExit) as exc_info:
        execute_command(args)

    assert exc_info.value.code == 1


@patch('ralph.config.RalphConfig')
@patch('ralph.loop.RalphLoop')
def test_execute_command_with_overrides(mock_loop: MagicMock, mock_config: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test execute command applies CLI overrides."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".ralph").mkdir()

    # Create a minimal PRD
    prd_path = tmp_path / ".ralph" / "prd.json"
    prd_path.write_text(json.dumps({
        "project": "Test",
        "userStories": []
    }))

    # Mock config and loop
    mock_config_instance = MagicMock()
    mock_config.return_value = mock_config_instance

    mock_loop_instance = MagicMock()
    mock_loop.return_value = mock_loop_instance

    args = MagicMock()
    args.max_iterations = 5
    args.phase = 1
    args.model = "claude-opus-4"
    args.typecheck_cmd = "mypy ."
    args.lint_cmd = "ruff check ."
    args.test_cmd = "pytest"
    args.verbose = True
    args.no_gates = True

    execute_command(args)

    # Check that config.set was called with overrides
    mock_config_instance.set.assert_any_call("ralph.maxIterations", 5)
    mock_config_instance.set.assert_any_call("claude.model", "claude-opus-4")
    mock_config_instance.set.assert_any_call("commands.typecheck", "mypy .")
    mock_config_instance.set.assert_any_call("commands.lint", "ruff check .")
    mock_config_instance.set.assert_any_call("commands.test", "pytest")

    # Check that loop.execute was called
    mock_loop_instance.execute.assert_called_once_with(max_iterations=5, phase=1)


def test_status_command_not_initialized(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that status fails if not initialized."""
    monkeypatch.chdir(tmp_path)

    args = MagicMock()

    with pytest.raises(SystemExit) as exc_info:
        status_command(args)

    assert exc_info.value.code == 1


@patch('ralph.config.RalphConfig')
@patch('ralph.loop.RalphLoop')
def test_status_command_success(mock_loop: MagicMock, mock_config: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test successful status display."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".ralph").mkdir()

    # Create a minimal PRD
    prd_path = tmp_path / ".ralph" / "prd.json"
    prd_path.write_text(json.dumps({
        "project": "Test",
        "userStories": []
    }))

    # Mock config and loop
    mock_config_instance = MagicMock()
    mock_config.return_value = mock_config_instance

    mock_loop_instance = MagicMock()
    mock_loop.return_value = mock_loop_instance

    args = MagicMock()
    args.phase = None

    status_command(args)

    # Check that show_info was called
    mock_loop_instance.show_info.assert_called_once()


def test_select_command_no_prd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that select fails if no PRD exists."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".ralph").mkdir()

    args = MagicMock()

    with pytest.raises(SystemExit) as exc_info:
        select_command(args)

    assert exc_info.value.code == 1


def test_select_command_all_complete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    """Test select command when all stories are complete."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".ralph").mkdir()

    # Create PRD with all stories complete
    prd_path = tmp_path / ".ralph" / "prd.json"
    prd_path.write_text(json.dumps({
        "project": "Test",
        "userStories": [
            {"id": "US-001", "title": "Test", "status": "complete"}
        ]
    }))

    args = MagicMock()
    select_command(args)

    captured = capsys.readouterr()
    assert "All stories are complete" in captured.out


def test_select_command_shows_incomplete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    """Test select command shows incomplete stories."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".ralph").mkdir()

    # Create PRD with incomplete stories
    prd_path = tmp_path / ".ralph" / "prd.json"
    prd_path.write_text(json.dumps({
        "project": "Test",
        "userStories": [
            {"id": "US-001", "title": "First Story", "status": "incomplete", "priority": 1},
            {"id": "US-002", "title": "Second Story", "status": "in_progress", "priority": 2, "phase": 1}
        ]
    }))

    args = MagicMock()
    select_command(args)

    captured = capsys.readouterr()
    assert "US-001" in captured.out
    assert "First Story" in captured.out
    assert "US-002" in captured.out
    assert "Second Story" in captured.out


def test_validate_command_no_prd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that validate fails if no PRD exists."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".ralph").mkdir()

    args = MagicMock()
    args.strict = False

    with pytest.raises(SystemExit) as exc_info:
        validate_command(args)

    assert exc_info.value.code == 1


def test_validate_command_invalid_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that validate fails on invalid JSON."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".ralph").mkdir()

    # Create invalid JSON
    prd_path = tmp_path / ".ralph" / "prd.json"
    prd_path.write_text("{invalid json")

    args = MagicMock()
    args.strict = False

    with pytest.raises(SystemExit) as exc_info:
        validate_command(args)

    assert exc_info.value.code == 1


def test_validate_command_valid_prd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    """Test validate command with valid PRD."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".ralph").mkdir()

    # Create valid PRD
    prd_path = tmp_path / ".ralph" / "prd.json"
    prd_path.write_text(json.dumps({
        "project": "Test",
        "description": "Test project",
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
    }))

    args = MagicMock()
    args.strict = False

    validate_command(args)

    captured = capsys.readouterr()
    assert "validation passed" in captured.out


def test_validate_command_with_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test validate command fails on PRD with errors."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".ralph").mkdir()

    # Create PRD with errors (no userStories)
    prd_path = tmp_path / ".ralph" / "prd.json"
    prd_path.write_text(json.dumps({
        "project": "Test"
    }))

    args = MagicMock()
    args.strict = False

    with pytest.raises(SystemExit) as exc_info:
        validate_command(args)

    assert exc_info.value.code == 1


def test_validate_command_strict_mode_warnings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test validate command in strict mode treats warnings as errors."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".ralph").mkdir()

    # Create PRD with warnings (no description)
    prd_path = tmp_path / ".ralph" / "prd.json"
    prd_path.write_text(json.dumps({
        "project": "Test",
        "userStories": [
            {
                "id": "US-001",
                "title": "Test Story",
                "status": "incomplete"
            }
        ]
    }))

    args = MagicMock()
    args.strict = True

    with pytest.raises(SystemExit) as exc_info:
        validate_command(args)

    assert exc_info.value.code == 1


def test_cli_execute_command_with_flags() -> None:
    """Test that ralph execute accepts all flags."""
    result = subprocess.run(
        ["ralph", "execute", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--max-iterations" in result.stdout
    assert "--phase" in result.stdout
    assert "--model" in result.stdout
    assert "--typecheck-cmd" in result.stdout
    assert "--lint-cmd" in result.stdout
    assert "--test-cmd" in result.stdout
    assert "--verbose" in result.stdout
    assert "--no-gates" in result.stdout


def test_cli_execute_alias_run() -> None:
    """Test that ralph run alias works."""
    result = subprocess.run(
        ["ralph", "run", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "execute" in result.stdout.lower()


def test_cli_execute_alias_execute_plan() -> None:
    """Test that ralph execute-plan alias works."""
    result = subprocess.run(
        ["ralph", "execute-plan", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "execute" in result.stdout.lower()


def test_cli_process_prd_command_requires_file() -> None:
    """Test that ralph process-prd command requires argument."""
    result = subprocess.run(
        ["ralph", "process-prd"],
        capture_output=True,
        text=True,
    )
    # Should fail because prd_file argument is required
    assert result.returncode != 0
    assert "required" in result.stderr or "error" in result.stderr


def test_cli_status_command_with_phase_flag() -> None:
    """Test that ralph status accepts --phase flag."""
    result = subprocess.run(
        ["ralph", "status", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--phase" in result.stdout


def test_cli_validate_strict_flag() -> None:
    """Test that ralph validate accepts --strict flag."""
    result = subprocess.run(
        ["ralph", "validate", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--strict" in result.stdout
