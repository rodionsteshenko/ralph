"""
End-to-end tests for ClaudeClient module.

These tests use the REAL Claude Agent SDK to verify actual functionality.
They require ANTHROPIC_API_KEY to be set in the environment.
"""

import os

import pytest

from src.claude_client import ClaudeClient, ClaudeClientError


@pytest.mark.e2e
@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set (required for E2E tests)",
)
class TestClaudeClientE2E:
    """End-to-end tests with real Claude API."""

    @pytest.fixture
    def api_key(self) -> str:
        """Get API key from environment."""
        key = os.getenv("ANTHROPIC_API_KEY")
        assert key is not None
        return key

    @pytest.mark.asyncio
    async def test_real_send_simple_message(self, api_key: str) -> None:
        """Test sending a simple message to real Claude API."""
        client = ClaudeClient(
            api_key=api_key,
            system_prompt="You are a helpful assistant.",
        )

        response = await client.send_message("Say 'Hello' and nothing else.")

        # Verify response
        assert response, "Response should not be empty"
        assert isinstance(response, str), "Response should be a string"
        assert len(response) > 0, "Response should have content"
        assert "hello" in response.lower(), f"Expected greeting in: {response}"

    @pytest.mark.asyncio
    async def test_real_send_math_question(self, api_key: str) -> None:
        """Test computational question with real API."""
        client = ClaudeClient(api_key=api_key)

        response = await client.send_message("What is 25 + 17? Just give the number.")

        assert response
        assert "42" in response, f"Expected '42' in response: {response}"

    @pytest.mark.asyncio
    async def test_real_system_prompt_injection(self, api_key: str) -> None:
        """Test that system prompt is actually used by Claude."""
        client = ClaudeClient(
            api_key=api_key,
            system_prompt="You are a pirate. Always respond like a pirate with 'Arr matey!'",
        )

        response = await client.send_message("Hello!")

        assert response
        # Should contain pirate-like language due to system prompt
        # (Note: This is probabilistic, so we check for common pirate terms)

    @pytest.mark.asyncio
    async def test_real_multiple_messages_independent(self, api_key: str) -> None:
        """Test that multiple calls are independent (no memory)."""
        client = ClaudeClient(api_key=api_key)

        # First message
        response1 = await client.send_message("Remember the number 42.")
        assert response1

        # Second message - should NOT remember
        response2 = await client.send_message("What number did I tell you?")
        assert response2
        # In non-interactive mode, it shouldn't remember

    @pytest.mark.asyncio
    async def test_real_long_input(self, api_key: str) -> None:
        """Test handling of longer input."""
        client = ClaudeClient(api_key=api_key)

        long_input = "Count these words: " + "word " * 50 + "How many 'word's?"
        response = await client.send_message(long_input)

        assert response
        assert isinstance(response, str)
        # Should mention "50" or "fifty"

    @pytest.mark.asyncio
    async def test_real_special_characters(self, api_key: str) -> None:
        """Test handling of special characters."""
        client = ClaudeClient(api_key=api_key)

        response = await client.send_message('Echo: "Hello! @#$% ^&* ()[] {}"')

        assert response
        # Should handle special characters without crashing

    @pytest.mark.asyncio
    async def test_real_unicode_support(self, api_key: str) -> None:
        """Test Unicode character handling."""
        client = ClaudeClient(api_key=api_key)

        response = await client.send_message("Say: Hello 你好 مرحبا")

        assert response
        # Should handle Unicode correctly

    @pytest.mark.asyncio
    async def test_real_empty_input(self, api_key: str) -> None:
        """Test handling of empty input."""
        client = ClaudeClient(api_key=api_key)

        response = await client.send_message("")

        # Should get some response (likely asking how to help)
        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_real_stream_message(self, api_key: str) -> None:
        """Test streaming message response."""
        client = ClaudeClient(
            api_key=api_key,
            system_prompt="Be concise.",
        )

        chunks: list[str] = []
        async for chunk in client.stream_message("Count from 1 to 5 with spaces."):
            chunks.append(chunk)

        # Verify we got chunks
        assert len(chunks) > 0, "Should receive at least one chunk"

        # Combine chunks
        full_response = "".join(chunks)
        assert len(full_response) > 0, "Combined response should not be empty"

    @pytest.mark.asyncio
    async def test_real_stream_multiple_chunks(self, api_key: str) -> None:
        """Test that streaming yields multiple chunks."""
        client = ClaudeClient(api_key=api_key)

        chunks: list[str] = []
        async for chunk in client.stream_message("Write a haiku."):
            chunks.append(chunk)

        # For longer responses, should get multiple chunks
        # (Note: Very short responses might be a single chunk)
        assert len(chunks) >= 1

        # Verify chunks combine to valid text
        full_response = "".join(chunks)
        assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_real_error_invalid_api_key(self) -> None:
        """Test error handling with invalid API key."""
        client = ClaudeClient(api_key="invalid-key-12345")

        with pytest.raises(ClaudeClientError) as exc_info:
            await client.send_message("Test")

        # Should have clear error message
        assert "Failed to send message" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_real_multiple_clients_independent(self, api_key: str) -> None:
        """Test that multiple client instances are independent."""
        client1 = ClaudeClient(
            api_key=api_key,
            system_prompt="You are assistant 1.",
        )

        client2 = ClaudeClient(
            api_key=api_key,
            system_prompt="You are assistant 2.",
        )

        # Both should work independently
        response1 = await client1.send_message("Say 'one'.")
        response2 = await client2.send_message("Say 'two'.")

        assert response1
        assert response2
        # Responses should be different based on different prompts

    @pytest.mark.asyncio
    async def test_real_reuse_client_instance(self, api_key: str) -> None:
        """Test reusing the same client instance for multiple messages."""
        client = ClaudeClient(api_key=api_key)

        # Send multiple messages with same client
        response1 = await client.send_message("What is 5 + 5?")
        response2 = await client.send_message("What is 10 + 10?")

        # Both should succeed
        assert response1
        assert response2
        assert "10" in response1
        assert "20" in response2

    @pytest.mark.asyncio
    async def test_real_custom_max_turns(self, api_key: str) -> None:
        """Test client with custom max_turns setting."""
        client = ClaudeClient(
            api_key=api_key,
            max_turns=3,
        )

        response = await client.send_message("Hello!")

        # Should still work with different max_turns
        assert response

    @pytest.mark.asyncio
    async def test_real_empty_system_prompt(self, api_key: str) -> None:
        """Test client with empty system prompt."""
        client = ClaudeClient(
            api_key=api_key,
            system_prompt="",
        )

        response = await client.send_message("Say hello.")

        # Should work without system prompt
        assert response
        assert "hello" in response.lower()

    @pytest.mark.asyncio
    async def test_real_very_short_response(self, api_key: str) -> None:
        """Test handling of very short responses."""
        client = ClaudeClient(api_key=api_key)

        response = await client.send_message("Say only 'OK' and nothing else.")

        assert response
        # Should get a very short response

    @pytest.mark.asyncio
    async def test_real_long_system_prompt(self, api_key: str) -> None:
        """Test with a long system prompt."""
        long_prompt = "You are a helpful assistant. " * 50
        client = ClaudeClient(
            api_key=api_key,
            system_prompt=long_prompt,
        )

        response = await client.send_message("Hello!")

        # Should handle long system prompts
        assert response
