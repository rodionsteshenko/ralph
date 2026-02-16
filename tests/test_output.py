"""Tests for output module (exit codes and JSON helpers)."""

import json

from ralph.output import (
    EXIT_ERROR,
    EXIT_MAX_FAILURES,
    EXIT_MAX_ITERATIONS,
    EXIT_NOTHING_TO_DO,
    EXIT_SUCCESS,
    json_error,
    json_output,
)


def test_exit_code_constants() -> None:
    """Test that exit code constants have expected values."""
    assert EXIT_SUCCESS == 0
    assert EXIT_ERROR == 1
    assert EXIT_MAX_FAILURES == 2
    assert EXIT_MAX_ITERATIONS == 3
    assert EXIT_NOTHING_TO_DO == 4


def test_json_output_dict(capsys: object) -> None:
    """Test json_output with a dict."""
    capsys_fixture = capsys  # type: ignore[assignment]
    result = json_output({"key": "value", "count": 42})
    assert result == EXIT_SUCCESS
    captured = capsys_fixture.readouterr()  # type: ignore[union-attr]
    data = json.loads(captured.out)
    assert data == {"key": "value", "count": 42}


def test_json_output_list(capsys: object) -> None:
    """Test json_output with a list."""
    capsys_fixture = capsys  # type: ignore[assignment]
    result = json_output([{"id": "US-001"}, {"id": "US-002"}])
    assert result == EXIT_SUCCESS
    captured = capsys_fixture.readouterr()  # type: ignore[union-attr]
    data = json.loads(captured.out)
    assert len(data) == 2
    assert data[0]["id"] == "US-001"


def test_json_output_custom_exit_code(capsys: object) -> None:
    """Test json_output with custom exit code."""
    capsys_fixture = capsys  # type: ignore[assignment]
    result = json_output({"status": "done"}, EXIT_NOTHING_TO_DO)
    assert result == EXIT_NOTHING_TO_DO
    captured = capsys_fixture.readouterr()  # type: ignore[union-attr]
    data = json.loads(captured.out)
    assert data["status"] == "done"


def test_json_error(capsys: object) -> None:
    """Test json_error outputs error JSON."""
    capsys_fixture = capsys  # type: ignore[assignment]
    result = json_error("Something went wrong")
    assert result == EXIT_ERROR
    captured = capsys_fixture.readouterr()  # type: ignore[union-attr]
    data = json.loads(captured.out)
    assert data == {"error": "Something went wrong"}


def test_json_error_custom_exit_code(capsys: object) -> None:
    """Test json_error with custom exit code."""
    capsys_fixture = capsys  # type: ignore[assignment]
    result = json_error("Max failures", EXIT_MAX_FAILURES)
    assert result == EXIT_MAX_FAILURES
    captured = capsys_fixture.readouterr()  # type: ignore[union-attr]
    data = json.loads(captured.out)
    assert data == {"error": "Max failures"}
