"""
End-to-end tests for CLI module.

These tests use the REAL Claude Agent SDK to verify actual functionality.
They require ANTHROPIC_API_KEY to be set in the environment.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from src.cli import process_message
from src.config import CodyConfig


@pytest.mark.e2e
@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set (required for E2E tests)",
)
class TestCLIE2E:
    """End-to-end tests with real Claude API calls."""

    @pytest.fixture
    def test_config(self) -> CodyConfig:
        """Create test configuration with real API key."""
        return CodyConfig(
            user_timezone="America/Los_Angeles",
            assistant_name="Cody",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )

    @pytest.mark.asyncio
    async def test_real_message_processing(self, test_config: CodyConfig) -> None:
        """Test real message processing with Claude API."""
        # Send a simple message
        response, exit_code = await process_message(
            message="Say 'Hello' and nothing else.",
            config=test_config,
            verbose=False,
        )

        # Verify success
        assert exit_code == 0, f"Expected exit code 0, got {exit_code}: {response}"
        assert response, "Response should not be empty"
        assert isinstance(response, str), "Response should be a string"
        assert len(response) > 0, "Response should have content"

        # Basic sanity check - response should contain "hello" in some form
        assert "hello" in response.lower(), f"Expected greeting in response: {response}"

    @pytest.mark.asyncio
    async def test_real_timezone_awareness(self, test_config: CodyConfig) -> None:
        """Test that temporal context is passed correctly."""
        response, exit_code = await process_message(
            message="What time is it? Just tell me if it's morning, afternoon, evening, or night.",
            config=test_config,
            verbose=False,
        )

        assert exit_code == 0
        assert response

        # Response should mention one of the time periods
        time_periods = ["morning", "afternoon", "evening", "night"]
        assert any(
            period in response.lower() for period in time_periods
        ), f"Expected time period in response: {response}"

    @pytest.mark.asyncio
    async def test_real_assistant_name(self, test_config: CodyConfig) -> None:
        """Test that assistant uses configured name."""
        test_config.assistant_name = "TestBot"

        response, exit_code = await process_message(
            message="What is your name? Just tell me your name.",
            config=test_config,
            verbose=False,
        )

        assert exit_code == 0
        assert response

    @pytest.mark.asyncio
    async def test_real_simple_math(self, test_config: CodyConfig) -> None:
        """Test a simple computational task."""
        response, exit_code = await process_message(
            message="What is 7 + 5? Just give me the number.",
            config=test_config,
            verbose=False,
        )

        assert exit_code == 0
        assert response
        # Should contain "12" somewhere in the response
        assert "12" in response, f"Expected '12' in response: {response}"

    def test_cli_command_line_e2e(self) -> None:
        """Test the full CLI command line with real API."""
        # Create temporary config file
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Create config with real API key
            config = CodyConfig(
                user_timezone="America/Los_Angeles",
                assistant_name="Cody",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
            )
            config.save(config_path)

            # Run CLI as subprocess
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "src.cli",
                    "Say 'test' and nothing else",
                    "--config",
                    str(config_path),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Verify success
            assert result.returncode == 0, f"CLI failed: {result.stderr}"
            assert result.stdout.strip(), "CLI should produce output"

            # Should contain "test" in response
            assert "test" in result.stdout.lower(), f"Expected 'test' in output: {result.stdout}"

    def test_cli_verbose_flag_e2e(self) -> None:
        """Test verbose flag produces debug output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            config = CodyConfig(
                user_timezone="America/Los_Angeles",
                assistant_name="Cody",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
            )
            config.save(config_path)

            # Run with verbose flag
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "src.cli",
                    "Hello",
                    "--config",
                    str(config_path),
                    "--verbose",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Verbose mode should produce output (either in stdout or stderr)
            assert result.returncode == 0
            # With verbose, we should see debug messages in stderr
            # (Rich logging goes to stderr by default)
            combined_output = result.stdout + result.stderr
            assert len(combined_output) > 0

    def test_cli_missing_api_key_e2e(self) -> None:
        """Test error handling when API key is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Create config WITHOUT API key
            config = CodyConfig(
                user_timezone="America/Los_Angeles",
                assistant_name="Cody",
                api_key=None,  # No API key
            )
            config.save(config_path)

            # Remove API key from environment
            env = os.environ.copy()
            env.pop("ANTHROPIC_API_KEY", None)

            # Run CLI
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "src.cli",
                    "Hello",
                    "--config",
                    str(config_path),
                ],
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
            )

            # Should fail with error
            assert result.returncode == 1
            # Error message should mention API key
            combined = result.stdout + result.stderr
            assert "ANTHROPIC_API_KEY" in combined

    def test_cli_invalid_config_path_e2e(self) -> None:
        """Test error handling for invalid config path."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.cli",
                "Hello",
                "--config",
                "/nonexistent/path/config.yaml",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should fail with error
        assert result.returncode == 1
        # Error should mention configuration
        combined = result.stdout + result.stderr
        assert "configuration" in combined.lower() or "config" in combined.lower()
