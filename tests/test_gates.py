"""Tests for quality gates execution."""

import json
import tempfile
import time
from pathlib import Path
from typing import Dict
from unittest.mock import MagicMock, patch

import pytest

from ralph.gates import (
    QualityGate,
    QualityGateResult,
    QualityGates,
    QualityGatesResult,
    create_quality_gates_from_config,
)


class TestQualityGate:
    """Tests for QualityGate class."""

    def test_quality_gate_initialization(self) -> None:
        """Test creating a quality gate."""
        gate = QualityGate(
            name="typecheck",
            command="mypy .",
            required=True,
            timeout=300,
        )

        assert gate.name == "typecheck"
        assert gate.command == "mypy ."
        assert gate.required is True
        assert gate.timeout == 300

    def test_quality_gate_defaults(self) -> None:
        """Test quality gate with default values."""
        gate = QualityGate(name="test", command="pytest")

        assert gate.required is True
        assert gate.timeout == 300


class TestQualityGateResult:
    """Tests for QualityGateResult class."""

    def test_result_initialization(self) -> None:
        """Test creating a quality gate result."""
        result = QualityGateResult(
            status="PASS",
            duration=1.5,
            output="All checks passed",
            return_code=0,
        )

        assert result.status == "PASS"
        assert result.duration == 1.5
        assert result.output == "All checks passed"
        assert result.return_code == 0

    def test_result_to_dict(self) -> None:
        """Test converting result to dictionary."""
        result = QualityGateResult(
            status="FAIL",
            duration=2.3,
            output="Error: type mismatch",
            return_code=1,
        )

        result_dict = result.to_dict()

        assert result_dict["status"] == "FAIL"
        assert result_dict["duration"] == 2.3
        assert result_dict["output"] == "Error: type mismatch"
        assert result_dict["returnCode"] == 1


class TestQualityGatesResult:
    """Tests for QualityGatesResult class."""

    def test_gates_result_initialization(self) -> None:
        """Test creating a quality gates result."""
        gate_result = QualityGateResult("PASS", 1.5, "Success", 0)
        gates = {"typecheck": gate_result}

        result = QualityGatesResult(
            status="PASS",
            gates=gates,
            total_duration=1.5,
            timestamp="2024-01-01T12:00:00",
        )

        assert result.status == "PASS"
        assert len(result.gates) == 1
        assert result.total_duration == 1.5
        assert result.timestamp == "2024-01-01T12:00:00"

    def test_gates_result_to_dict(self) -> None:
        """Test converting gates result to dictionary."""
        gate_result = QualityGateResult("PASS", 1.5, "Success", 0)
        gates = {"typecheck": gate_result}

        result = QualityGatesResult(
            status="PASS",
            gates=gates,
            total_duration=1.5,
            timestamp="2024-01-01T12:00:00",
        )

        result_dict = result.to_dict()

        assert result_dict["status"] == "PASS"
        assert "gates" in result_dict
        assert "typecheck" in result_dict["gates"]
        assert result_dict["totalDuration"] == 1.5
        assert result_dict["timestamp"] == "2024-01-01T12:00:00"


class TestQualityGatesAutoDetection:
    """Tests for auto-detection of quality gates."""

    def test_detect_gates_for_python_project(self) -> None:
        """Test auto-detecting gates for Python project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            pyproject = """
[tool.mypy]
strict = true

[tool.ruff]
line-length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]
"""
            (project_dir / "pyproject.toml").write_text(pyproject)
            (project_dir / "tests").mkdir()

            gates = QualityGates(project_dir=project_dir)

            assert len(gates.gates) == 3
            gate_names = [g.name for g in gates.gates]
            assert "typecheck" in gate_names
            assert "lint" in gate_names
            assert "test" in gate_names

    def test_detect_gates_for_node_project(self) -> None:
        """Test auto-detecting gates for Node.js project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            package_json = {
                "scripts": {
                    "typecheck": "tsc --noEmit",
                    "lint": "eslint .",
                    "test": "jest",
                }
            }
            (project_dir / "package.json").write_text(json.dumps(package_json))

            gates = QualityGates(project_dir=project_dir)

            assert len(gates.gates) == 3
            gate_names = [g.name for g in gates.gates]
            assert "typecheck" in gate_names
            assert "lint" in gate_names
            assert "test" in gate_names

    def test_detect_partial_gates(self) -> None:
        """Test detecting only some gates when not all are configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            package_json = {"scripts": {"test": "jest"}}
            (project_dir / "package.json").write_text(json.dumps(package_json))

            gates = QualityGates(project_dir=project_dir)

            assert len(gates.gates) == 1
            assert gates.gates[0].name == "test"

    def test_detect_no_gates(self) -> None:
        """Test detecting no gates for unconfigured project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            gates = QualityGates(project_dir=project_dir)

            assert len(gates.gates) == 0


class TestQualityGatesExecution:
    """Tests for quality gate execution (with mocks)."""

    @patch("ralph.gates.subprocess.run")
    def test_run_single_gate_success(self, mock_run: MagicMock) -> None:
        """Test running a single gate that passes."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Success\n",
            stderr="",
        )

        gate = QualityGate("typecheck", "mypy .")
        gates = QualityGates(gates=[gate])

        result = gates.run()

        assert result["status"] == "PASS"
        assert "typecheck" in result["gates"]
        assert result["gates"]["typecheck"]["status"] == "PASS"
        assert result["gates"]["typecheck"]["returnCode"] == 0

    @patch("ralph.gates.subprocess.run")
    def test_run_single_gate_failure(self, mock_run: MagicMock) -> None:
        """Test running a single gate that fails."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: type mismatch\n",
        )

        gate = QualityGate("typecheck", "mypy .")
        gates = QualityGates(gates=[gate])

        result = gates.run()

        assert result["status"] == "FAIL"
        assert "typecheck" in result["gates"]
        assert result["gates"]["typecheck"]["status"] == "FAIL"
        assert result["gates"]["typecheck"]["returnCode"] == 1

    @patch("ralph.gates.subprocess.run")
    def test_run_multiple_gates_all_pass(self, mock_run: MagicMock) -> None:
        """Test running multiple gates that all pass."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Success\n",
            stderr="",
        )

        gates_list = [
            QualityGate("typecheck", "mypy ."),
            QualityGate("lint", "ruff check ."),
            QualityGate("test", "pytest"),
        ]
        gates = QualityGates(gates=gates_list)

        result = gates.run()

        assert result["status"] == "PASS"
        assert len(result["gates"]) == 3
        assert result["gates"]["typecheck"]["status"] == "PASS"
        assert result["gates"]["lint"]["status"] == "PASS"
        assert result["gates"]["test"]["status"] == "PASS"

    @patch("ralph.gates.subprocess.run")
    def test_run_multiple_gates_one_fails(self, mock_run: MagicMock) -> None:
        """Test running multiple gates where one fails (should stop)."""
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First gate passes
                return MagicMock(returncode=0, stdout="Success", stderr="")
            else:
                # Second gate fails
                return MagicMock(returncode=1, stdout="", stderr="Error")

        mock_run.side_effect = side_effect

        gates_list = [
            QualityGate("typecheck", "mypy ."),
            QualityGate("lint", "ruff check ."),
            QualityGate("test", "pytest"),
        ]
        gates = QualityGates(gates=gates_list)

        result = gates.run()

        assert result["status"] == "FAIL"
        assert len(result["gates"]) == 2  # Should stop after second gate
        assert result["gates"]["typecheck"]["status"] == "PASS"
        assert result["gates"]["lint"]["status"] == "FAIL"

    @patch("ralph.gates.subprocess.run")
    def test_gate_timeout(self, mock_run: MagicMock) -> None:
        """Test gate that times out."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("mypy .", 10)

        gate = QualityGate("typecheck", "mypy .", timeout=10)
        gates = QualityGates(gates=[gate])

        result = gates.run()

        assert result["status"] == "FAIL"
        assert result["gates"]["typecheck"]["status"] == "FAIL"
        assert "timed out" in result["gates"]["typecheck"]["output"]

    @patch("ralph.gates.subprocess.run")
    def test_gate_exception(self, mock_run: MagicMock) -> None:
        """Test gate that raises an exception."""
        mock_run.side_effect = Exception("Command not found")

        gate = QualityGate("typecheck", "mypy .")
        gates = QualityGates(gates=[gate])

        result = gates.run()

        assert result["status"] == "FAIL"
        assert result["gates"]["typecheck"]["status"] == "FAIL"
        assert "Command not found" in result["gates"]["typecheck"]["output"]

    @patch("ralph.gates.subprocess.run")
    def test_skip_non_required_gates(self, mock_run: MagicMock) -> None:
        """Test that non-required gates are skipped."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Success",
            stderr="",
        )

        gates_list = [
            QualityGate("typecheck", "mypy .", required=True),
            QualityGate("optional", "optional-check", required=False),
        ]
        gates = QualityGates(gates=gates_list)

        result = gates.run()

        assert result["status"] == "PASS"
        assert len(result["gates"]) == 1  # Only required gate ran
        assert "typecheck" in result["gates"]
        assert "optional" not in result["gates"]


class TestCreateQualityGatesFromConfig:
    """Tests for creating quality gates from config dictionary."""

    def test_create_from_config(self) -> None:
        """Test creating quality gates from config dictionary."""
        config = {
            "qualityGates": {
                "typecheck": {
                    "command": "mypy .",
                    "required": True,
                    "timeout": 300,
                },
                "lint": {
                    "command": "ruff check .",
                    "required": True,
                    "timeout": 120,
                },
            }
        }

        gates = create_quality_gates_from_config(config)

        assert len(gates.gates) == 2
        gate_names = [g.name for g in gates.gates]
        assert "typecheck" in gate_names
        assert "lint" in gate_names

    def test_create_from_empty_config(self) -> None:
        """Test creating quality gates from empty config."""
        config: Dict = {}

        # Use a temporary directory with no project files to avoid auto-detection
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            gates = create_quality_gates_from_config(config, project_dir=project_dir)

            assert len(gates.gates) == 0


@pytest.mark.e2e
class TestQualityGatesRealExecution:
    """End-to-end tests with real command execution."""

    def test_run_echo_command_success(self) -> None:
        """Test running a real echo command that succeeds."""
        gate = QualityGate("test", "echo 'Hello, World!'")
        gates = QualityGates(gates=[gate])

        result = gates.run()

        assert result["status"] == "PASS"
        assert result["gates"]["test"]["status"] == "PASS"
        assert result["gates"]["test"]["returnCode"] == 0

    def test_run_false_command_failure(self) -> None:
        """Test running a command that fails."""
        gate = QualityGate("test", "false")
        gates = QualityGates(gates=[gate])

        result = gates.run()

        assert result["status"] == "FAIL"
        assert result["gates"]["test"]["status"] == "FAIL"
        assert result["gates"]["test"]["returnCode"] == 1

    def test_run_invalid_command(self) -> None:
        """Test running an invalid command."""
        gate = QualityGate("test", "this-command-does-not-exist-12345")
        gates = QualityGates(gates=[gate])

        result = gates.run()

        assert result["status"] == "FAIL"
        assert result["gates"]["test"]["status"] == "FAIL"

    def test_run_with_real_project_detection(self) -> None:
        """Test running gates with real project detection on Ralph itself."""
        # This test runs against the actual Ralph project
        project_dir = Path.cwd()

        gates = QualityGates(project_dir=project_dir)

        # Ralph should detect typecheck, lint, and test gates
        assert len(gates.gates) >= 1  # At least typecheck should be detected
        gate_names = [g.name for g in gates.gates]
        assert "typecheck" in gate_names or "lint" in gate_names

    def test_gate_timeout_real(self) -> None:
        """Test that real command timeout works."""
        # Use a command that sleeps longer than timeout
        gate = QualityGate("test", "sleep 5", timeout=1)
        gates = QualityGates(gates=[gate])

        start_time = time.time()
        result = gates.run()
        duration = time.time() - start_time

        assert result["status"] == "FAIL"
        assert result["gates"]["test"]["status"] == "FAIL"
        assert "timed out" in result["gates"]["test"]["output"]
        # Should timeout around 1 second, not 5
        assert duration < 3


@pytest.mark.e2e
class TestQualityGatesWithRalphProject:
    """E2E tests running real quality gates on Ralph project."""

    @pytest.mark.skipif(
        not (Path.cwd() / "pyproject.toml").exists(),
        reason="Requires Ralph project with pyproject.toml",
    )
    def test_run_typecheck_on_ralph(self) -> None:
        """Test running typecheck on the Ralph project."""
        gate = QualityGate("typecheck", "mypy .")
        gates = QualityGates(gates=[gate])

        result = gates.run()

        # This should pass if the code is properly typed
        assert "typecheck" in result["gates"]
        # Don't assert pass/fail, just verify it ran

    @pytest.mark.skipif(
        not (Path.cwd() / "pyproject.toml").exists(),
        reason="Requires Ralph project with pyproject.toml",
    )
    def test_run_lint_on_ralph(self) -> None:
        """Test running lint on the Ralph project."""
        gate = QualityGate("lint", "ruff check .", timeout=30)
        gates = QualityGates(gates=[gate])

        result = gates.run()

        # This should pass if the code follows linting rules
        assert "lint" in result["gates"]
        # Don't assert pass/fail, just verify it ran
