"""Quality gates execution."""

import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    from rich.console import Console
    from rich.panel import Panel

    HAS_RICH = True
    console: Optional[Console] = Console()
except ImportError:
    HAS_RICH = False
    console = None

from ralph.detect import detect_project_config


class QualityGate:
    """Configuration for a single quality gate."""

    def __init__(
        self,
        name: str,
        command: str,
        required: bool = True,
        timeout: int = 300,
    ) -> None:
        """
        Initialize a quality gate.

        Args:
            name: Name of the gate (e.g., "typecheck", "lint", "test")
            command: Shell command to execute
            required: Whether this gate must pass
            timeout: Timeout in seconds
        """
        self.name = name
        self.command = command
        self.required = required
        self.timeout = timeout


class QualityGateResult:
    """Result from running a quality gate."""

    def __init__(
        self,
        status: str,
        duration: float,
        output: str,
        return_code: int,
    ) -> None:
        """
        Initialize quality gate result.

        Args:
            status: "PASS" or "FAIL"
            duration: Execution duration in seconds
            output: Combined stdout and stderr
            return_code: Process return code
        """
        self.status = status
        self.duration = duration
        self.output = output
        self.return_code = return_code

    def to_dict(self) -> Dict:
        """Convert result to dictionary."""
        return {
            "status": self.status,
            "duration": self.duration,
            "output": self.output,
            "returnCode": self.return_code,
        }


class QualityGatesResult:
    """Result from running all quality gates."""

    def __init__(
        self,
        status: str,
        gates: Dict[str, QualityGateResult],
        total_duration: float,
        timestamp: str,
    ) -> None:
        """
        Initialize quality gates result.

        Args:
            status: Overall status ("PASS" or "FAIL")
            gates: Dictionary of gate name to result
            total_duration: Total execution duration
            timestamp: ISO format timestamp
        """
        self.status = status
        self.gates = gates
        self.total_duration = total_duration
        self.timestamp = timestamp

    def to_dict(self) -> Dict:
        """Convert result to dictionary."""
        return {
            "status": self.status,
            "gates": {name: result.to_dict() for name, result in self.gates.items()},
            "totalDuration": self.total_duration,
            "timestamp": self.timestamp,
        }


class QualityGates:
    """Run quality gates (tests, lint, typecheck) statically."""

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        gates: Optional[List[QualityGate]] = None,
    ) -> None:
        """
        Initialize quality gates.

        Args:
            project_dir: Project directory to run gates in. Defaults to current directory.
            gates: List of quality gates to run. If None, auto-detects from project.
        """
        self.project_dir = project_dir or Path.cwd()
        self.gates = gates or self._detect_gates()

    def _detect_gates(self) -> List[QualityGate]:
        """
        Auto-detect quality gates from project configuration.

        Returns:
            List of detected quality gates
        """
        config = detect_project_config(self.project_dir)
        gates: List[QualityGate] = []

        # Add typecheck gate if detected
        typecheck_cmd = config.get("typecheck")
        if typecheck_cmd:
            gates.append(
                QualityGate(
                    name="typecheck",
                    command=typecheck_cmd,
                    required=True,
                    timeout=300,
                )
            )

        # Add lint gate if detected
        lint_cmd = config.get("lint")
        if lint_cmd:
            gates.append(
                QualityGate(
                    name="lint",
                    command=lint_cmd,
                    required=True,
                    timeout=120,
                )
            )

        # Add test gate if detected
        test_cmd = config.get("test")
        if test_cmd:
            gates.append(
                QualityGate(
                    name="test",
                    command=test_cmd,
                    required=True,
                    timeout=600,
                )
            )

        return gates

    def run(self) -> Dict:
        """
        Run all quality gates and return results.

        Returns:
            Dictionary with gate results in legacy format for compatibility
        """
        result = self.run_gates()
        return result.to_dict()

    def run_gates(self) -> QualityGatesResult:
        """
        Run all quality gates and return typed result.

        Returns:
            QualityGatesResult with all gate results
        """
        gate_results: Dict[str, QualityGateResult] = {}
        overall_status = "PASS"
        start_time = time.time()

        for gate in self.gates:
            if not gate.required:
                continue

            if HAS_RICH and console:
                console.print(f"\n[bold blue]▶ Running {gate.name}...[/bold blue]")
                console.print(f"[dim]  Command: {gate.command}[/dim]")
            else:
                print(f"🔍 Running {gate.name}...")
                print(f"   Command: {gate.command}")

            gate_result = self._run_gate(gate)
            gate_results[gate.name] = gate_result

            if gate_result.status == "FAIL":
                overall_status = "FAIL"
                if HAS_RICH and console:
                    console.print(
                        f"[bold red]✗ {gate.name} failed ({gate_result.duration:.1f}s)[/bold red]"
                    )
                    if gate_result.output:
                        # Show first 20 lines of output
                        output_lines = gate_result.output.split("\n")[:20]
                        console.print(
                            Panel(
                                "\n".join(output_lines),
                                title=f"[red]{gate.name} Output (first 20 lines)[/red]",
                                border_style="red",
                                expand=False,
                            )
                        )
                else:
                    print(f"❌ {gate.name} failed")
                    if gate_result.output:
                        print("   Output (first 20 lines):")
                        for line in gate_result.output.split("\n")[:20]:
                            print(f"   {line}")
                break
            else:
                if HAS_RICH and console:
                    console.print(
                        f"[bold green]✓ {gate.name} passed "
                        f"({gate_result.duration:.1f}s)[/bold green]"
                    )
                else:
                    print(f"✅ {gate.name} passed ({gate_result.duration:.1f}s)")

        total_duration = time.time() - start_time
        timestamp = datetime.now().isoformat()

        return QualityGatesResult(
            status=overall_status,
            gates=gate_results,
            total_duration=total_duration,
            timestamp=timestamp,
        )

    def _run_gate(self, gate: QualityGate) -> QualityGateResult:
        """
        Run a single quality gate.

        Args:
            gate: The quality gate to run

        Returns:
            QualityGateResult with execution results
        """
        start_time = time.time()

        try:
            result = subprocess.run(
                gate.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=gate.timeout,
                cwd=self.project_dir,
            )

            duration = time.time() - start_time

            return QualityGateResult(
                status="PASS" if result.returncode == 0 else "FAIL",
                duration=duration,
                output=result.stdout + result.stderr,
                return_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return QualityGateResult(
                status="FAIL",
                duration=gate.timeout,
                output=f"Gate timed out after {gate.timeout}s",
                return_code=-1,
            )
        except Exception as e:
            return QualityGateResult(
                status="FAIL",
                duration=time.time() - start_time,
                output=str(e),
                return_code=-1,
            )


def create_quality_gates_from_config(
    config: Dict, project_dir: Optional[Path] = None
) -> QualityGates:
    """
    Create QualityGates from a configuration dictionary (legacy format).

    Args:
        config: Configuration dictionary with qualityGates section
        project_dir: Project directory to run gates in

    Returns:
        QualityGates instance configured from the dictionary
    """
    gates_config = config.get("qualityGates", {})
    gates: List[QualityGate] = []

    for gate_name, gate_cfg in gates_config.items():
        if isinstance(gate_cfg, dict):
            gates.append(
                QualityGate(
                    name=gate_name,
                    command=gate_cfg.get("command", ""),
                    required=gate_cfg.get("required", True),
                    timeout=gate_cfg.get("timeout", 300),
                )
            )

    return QualityGates(project_dir=project_dir, gates=gates)
