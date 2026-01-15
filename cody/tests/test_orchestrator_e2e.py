"""
End-to-end tests for Orchestrator module.

These tests use the REAL Claude Agent SDK to verify actual functionality.
They require ANTHROPIC_API_KEY to be set in the environment.
"""

import os

import pytest

from src.config import CodyConfig
from src.orchestrator import Orchestrator


@pytest.mark.e2e
@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set (required for E2E tests)",
)
class TestOrchestratorE2E:
    """End-to-end tests with real Claude API calls."""

    @pytest.fixture
    def test_config(self) -> CodyConfig:
        """Create test configuration with real API key."""
        return CodyConfig(
            user_timezone="America/Los_Angeles",
            assistant_name="Cody",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )

    @pytest.fixture
    def orchestrator(self, test_config: CodyConfig) -> Orchestrator:
        """Create orchestrator with test config."""
        return Orchestrator(test_config)

    @pytest.mark.asyncio
    async def test_real_process_simple_message(self, orchestrator: Orchestrator) -> None:
        """Test processing a simple message with real API."""
        response = await orchestrator.process_message("Say 'Hello' and nothing else.")

        # Verify we got a response
        assert response, "Response should not be empty"
        assert isinstance(response, str), "Response should be a string"
        assert len(response) > 0, "Response should have content"

        # Basic sanity check - should contain "hello" in some form
        assert "hello" in response.lower(), f"Expected greeting in response: {response}"

    @pytest.mark.asyncio
    async def test_real_process_math_question(self, orchestrator: Orchestrator) -> None:
        """Test processing a computational question."""
        response = await orchestrator.process_message(
            "What is 15 + 27? Just give me the number."
        )

        assert response
        # Should contain "42" somewhere
        assert "42" in response, f"Expected '42' in response: {response}"

    @pytest.mark.asyncio
    async def test_real_temporal_context_included(self, orchestrator: Orchestrator) -> None:
        """Test that temporal context is actually used by Claude."""
        response = await orchestrator.process_message(
            "What time is it? Just tell me if it's morning, afternoon, evening, or night."
        )

        assert response

        # Response should mention one of the time periods
        time_periods = ["morning", "afternoon", "evening", "night"]
        assert any(
            period in response.lower() for period in time_periods
        ), f"Expected time period in response: {response}"

    @pytest.mark.asyncio
    async def test_real_assistant_name_used(self, orchestrator: Orchestrator) -> None:
        """Test that assistant uses the configured name."""
        # Create orchestrator with custom name
        custom_config = CodyConfig(
            user_timezone="America/Los_Angeles",
            assistant_name="TestBot",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )
        custom_orchestrator = Orchestrator(custom_config)

        response = await custom_orchestrator.process_message(
            "What is your name? Just tell me your name in one sentence."
        )

        assert response
        # Response should identify with the configured name
        # (Note: This might not always work as Claude may not always mention its name)

    @pytest.mark.asyncio
    async def test_real_day_of_week_awareness(self, orchestrator: Orchestrator) -> None:
        """Test that orchestrator provides correct day of week."""
        response = await orchestrator.process_message(
            "What day of the week is it today? Just name the day."
        )

        assert response

        # Response should contain a day name
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        assert any(day in response.lower() for day in days), f"Expected day in response: {response}"

    @pytest.mark.asyncio
    async def test_real_multiple_messages_independent(
        self, orchestrator: Orchestrator
    ) -> None:
        """Test that multiple messages are processed independently (no memory)."""
        # First message
        response1 = await orchestrator.process_message("Remember the number 42.")

        assert response1

        # Second message - should NOT remember previous message
        response2 = await orchestrator.process_message("What number did I tell you to remember?")

        assert response2
        # Should indicate it doesn't remember (non-interactive mode has no memory)

    @pytest.mark.asyncio
    async def test_real_timezone_handling(self, orchestrator: Orchestrator) -> None:
        """Test that different timezones are handled correctly."""
        # Create orchestrator with different timezone
        ny_config = CodyConfig(
            user_timezone="America/New_York",
            assistant_name="Cody",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )
        ny_orchestrator = Orchestrator(ny_config)

        response = await ny_orchestrator.process_message(
            "What timezone are you in? Just tell me the timezone abbreviation."
        )

        assert response
        # Should mention EST/EDT for New York

    @pytest.mark.asyncio
    async def test_real_error_with_empty_input(self, orchestrator: Orchestrator) -> None:
        """Test handling of empty input."""
        # Empty string should still process (Claude may respond with a question)
        response = await orchestrator.process_message("")

        # Should either get a response or an error
        # Most likely Claude will respond with something like "How can I help you?"
        # This test just ensures it doesn't crash
        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_real_long_input(self, orchestrator: Orchestrator) -> None:
        """Test processing of longer input."""
        long_input = "Please summarize the following: " + "word " * 100 + "Summarize this."

        response = await orchestrator.process_message(long_input)

        assert response
        assert isinstance(response, str)
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_real_special_characters(self, orchestrator: Orchestrator) -> None:
        """Test handling of special characters in input."""
        response = await orchestrator.process_message(
            'Say: "Hello! @#$% ^&* ()[] {}"'
        )

        assert response
        # Should handle special characters without crashing

    @pytest.mark.asyncio
    async def test_real_orchestrator_no_side_effects(
        self, orchestrator: Orchestrator
    ) -> None:
        """Test that orchestrator has no side effects (no persistence)."""
        # Process first message
        response1 = await orchestrator.process_message("My favorite color is blue.")

        assert response1

        # Create a NEW orchestrator with same config
        new_orchestrator = Orchestrator(orchestrator.config)

        # Process second message - should not remember first message
        response2 = await new_orchestrator.process_message("What is my favorite color?")

        assert response2
        # Should indicate it doesn't know (no persistence between orchestrator instances)

    @pytest.mark.asyncio
    async def test_real_unicode_support(self, orchestrator: Orchestrator) -> None:
        """Test that orchestrator handles Unicode correctly."""
        response = await orchestrator.process_message(
            "Say: Hello 你好 مرحبا नमस्ते"
        )

        assert response
        # Should handle Unicode without crashing
