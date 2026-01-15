"""
Unit tests for ClaudeClient module.

Tests Claude client with mocked Claude Agent SDK.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.claude_client import ClaudeClient, ClaudeClientError


@pytest.mark.unit
class TestClaudeClientInit:
    """Test ClaudeClient initialization."""

    def test_init_success(self) -> None:
        """Test successful initialization with API key."""
        client = ClaudeClient(
            api_key="test-api-key",
            system_prompt="You are a helpful assistant.",
        )

        assert client.api_key == "test-api-key"
        assert client.system_prompt == "You are a helpful assistant."
        assert client.max_turns == 1
        assert client.permission_mode == "bypassPermissions"

    def test_init_with_custom_options(self) -> None:
        """Test initialization with custom options."""
        client = ClaudeClient(
            api_key="test-key",
            system_prompt="Custom prompt",
            max_turns=5,
            permission_mode="acceptEdits",
        )

        assert client.max_turns == 5
        assert client.permission_mode == "acceptEdits"

    def test_init_missing_api_key(self) -> None:
        """Test initialization fails when API key is missing."""
        with pytest.raises(ClaudeClientError) as exc_info:
            ClaudeClient(api_key="")

        assert "API key is required" in str(exc_info.value)

    def test_init_empty_system_prompt(self) -> None:
        """Test initialization with empty system prompt (allowed)."""
        client = ClaudeClient(api_key="test-key", system_prompt="")

        assert client.system_prompt == ""


@pytest.mark.unit
class TestSendMessage:
    """Test send_message method with mocked SDK."""

    @pytest.fixture
    def client(self) -> ClaudeClient:
        """Create test client."""
        return ClaudeClient(
            api_key="test-api-key",
            system_prompt="Test prompt",
        )

    @pytest.mark.asyncio
    async def test_send_message_success(self, client: ClaudeClient) -> None:
        """Test successful message sending and response."""
        # Create mock response
        mock_block = MagicMock()
        mock_block.text = "Hello! How can I help?"

        mock_message = MagicMock()
        mock_message.content = [mock_block]

        # Mock async generator
        async def mock_receive_response() -> AsyncMock:  # type: ignore[misc]
            yield mock_message

        # Mock SDK client
        mock_sdk_client = MagicMock()
        mock_sdk_client.connect = AsyncMock()
        mock_sdk_client.query = AsyncMock()
        mock_sdk_client.disconnect = AsyncMock()
        mock_sdk_client.receive_response = mock_receive_response

        with patch("src.claude_client.ClaudeSDKClient") as mock_sdk:
            mock_sdk.return_value = mock_sdk_client

            response = await client.send_message("Hello")

            # Verify response
            assert response == "Hello! How can I help?"

            # Verify SDK calls
            mock_sdk_client.connect.assert_called_once()
            mock_sdk_client.query.assert_called_once_with("Hello")
            mock_sdk_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_multiple_blocks(self, client: ClaudeClient) -> None:
        """Test aggregating multiple content blocks."""
        mock_block1 = MagicMock()
        mock_block1.text = "Part 1 "

        mock_block2 = MagicMock()
        mock_block2.text = "Part 2"

        mock_message = MagicMock()
        mock_message.content = [mock_block1, mock_block2]

        async def mock_receive_response() -> AsyncMock:  # type: ignore[misc]
            yield mock_message

        mock_sdk_client = MagicMock()
        mock_sdk_client.connect = AsyncMock()
        mock_sdk_client.query = AsyncMock()
        mock_sdk_client.disconnect = AsyncMock()
        mock_sdk_client.receive_response = mock_receive_response

        with patch("src.claude_client.ClaudeSDKClient") as mock_sdk:
            mock_sdk.return_value = mock_sdk_client

            response = await client.send_message("Test")

            assert response == "Part 1 Part 2"

    @pytest.mark.asyncio
    async def test_send_message_multiple_messages(self, client: ClaudeClient) -> None:
        """Test aggregating multiple messages in stream."""
        mock_block1 = MagicMock()
        mock_block1.text = "First "

        mock_block2 = MagicMock()
        mock_block2.text = "Second"

        mock_msg1 = MagicMock()
        mock_msg1.content = [mock_block1]

        mock_msg2 = MagicMock()
        mock_msg2.content = [mock_block2]

        async def mock_receive_response() -> AsyncMock:  # type: ignore[misc]
            yield mock_msg1
            yield mock_msg2

        mock_sdk_client = MagicMock()
        mock_sdk_client.connect = AsyncMock()
        mock_sdk_client.query = AsyncMock()
        mock_sdk_client.disconnect = AsyncMock()
        mock_sdk_client.receive_response = mock_receive_response

        with patch("src.claude_client.ClaudeSDKClient") as mock_sdk:
            mock_sdk.return_value = mock_sdk_client

            response = await client.send_message("Test")

            assert response == "First Second"

    @pytest.mark.asyncio
    async def test_send_message_strips_whitespace(self, client: ClaudeClient) -> None:
        """Test that response is stripped of whitespace."""
        mock_block = MagicMock()
        mock_block.text = "  \n  Response  \n  "

        mock_message = MagicMock()
        mock_message.content = [mock_block]

        async def mock_receive_response() -> AsyncMock:  # type: ignore[misc]
            yield mock_message

        mock_sdk_client = MagicMock()
        mock_sdk_client.connect = AsyncMock()
        mock_sdk_client.query = AsyncMock()
        mock_sdk_client.disconnect = AsyncMock()
        mock_sdk_client.receive_response = mock_receive_response

        with patch("src.claude_client.ClaudeSDKClient") as mock_sdk:
            mock_sdk.return_value = mock_sdk_client

            response = await client.send_message("Test")

            assert response == "Response"

    @pytest.mark.asyncio
    async def test_send_message_empty_response(self, client: ClaudeClient) -> None:
        """Test error when API returns empty response."""
        mock_message = MagicMock()
        mock_message.content = []

        async def mock_receive_response() -> AsyncMock:  # type: ignore[misc]
            yield mock_message

        mock_sdk_client = MagicMock()
        mock_sdk_client.connect = AsyncMock()
        mock_sdk_client.query = AsyncMock()
        mock_sdk_client.disconnect = AsyncMock()
        mock_sdk_client.receive_response = mock_receive_response

        with patch("src.claude_client.ClaudeSDKClient") as mock_sdk:
            mock_sdk.return_value = mock_sdk_client

            with pytest.raises(ClaudeClientError) as exc_info:
                await client.send_message("Test")

            assert "No response received" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_message_connect_error(self, client: ClaudeClient) -> None:
        """Test error handling when connection fails."""
        mock_sdk_client = MagicMock()
        mock_sdk_client.connect = AsyncMock(side_effect=Exception("Connection failed"))

        with patch("src.claude_client.ClaudeSDKClient") as mock_sdk:
            mock_sdk.return_value = mock_sdk_client

            with pytest.raises(ClaudeClientError) as exc_info:
                await client.send_message("Test")

            assert "Failed to send message" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_message_query_error(self, client: ClaudeClient) -> None:
        """Test error handling when query fails."""
        mock_sdk_client = MagicMock()
        mock_sdk_client.connect = AsyncMock()
        mock_sdk_client.query = AsyncMock(side_effect=Exception("Query failed"))
        mock_sdk_client.disconnect = AsyncMock()

        with patch("src.claude_client.ClaudeSDKClient") as mock_sdk:
            mock_sdk.return_value = mock_sdk_client

            with pytest.raises(ClaudeClientError):
                await client.send_message("Test")

            # Verify disconnect was called despite error
            mock_sdk_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_receive_error(self, client: ClaudeClient) -> None:
        """Test error handling when receiving response fails."""
        mock_sdk_client = MagicMock()
        mock_sdk_client.connect = AsyncMock()
        mock_sdk_client.query = AsyncMock()
        mock_sdk_client.disconnect = AsyncMock()

        async def mock_receive_response() -> AsyncMock:  # type: ignore[misc]
            raise Exception("Receive failed")
            yield  # Never reached

        mock_sdk_client.receive_response = mock_receive_response

        with patch("src.claude_client.ClaudeSDKClient") as mock_sdk:
            mock_sdk.return_value = mock_sdk_client

            with pytest.raises(ClaudeClientError):
                await client.send_message("Test")

            # Verify disconnect was called
            mock_sdk_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_uses_system_prompt(self, client: ClaudeClient) -> None:
        """Test that system prompt is injected."""
        mock_block = MagicMock()
        mock_block.text = "Response"

        mock_message = MagicMock()
        mock_message.content = [mock_block]

        async def mock_receive_response() -> AsyncMock:  # type: ignore[misc]
            yield mock_message

        mock_sdk_client = MagicMock()
        mock_sdk_client.connect = AsyncMock()
        mock_sdk_client.query = AsyncMock()
        mock_sdk_client.disconnect = AsyncMock()
        mock_sdk_client.receive_response = mock_receive_response

        with patch("src.claude_client.ClaudeSDKClient") as mock_sdk:
            with patch("src.claude_client.ClaudeAgentOptions") as mock_options:
                mock_sdk.return_value = mock_sdk_client

                await client.send_message("Test")

                # Verify options were created with system prompt
                mock_options.assert_called_once()
                call_kwargs = mock_options.call_args.kwargs
                assert call_kwargs["system_prompt"] == "Test prompt"
                assert call_kwargs["max_turns"] == 1
                assert call_kwargs["permission_mode"] == "bypassPermissions"

    @pytest.mark.asyncio
    async def test_send_message_cleanup_on_success(self, client: ClaudeClient) -> None:
        """Test that client is cleaned up after successful send."""
        mock_block = MagicMock()
        mock_block.text = "Response"

        mock_message = MagicMock()
        mock_message.content = [mock_block]

        async def mock_receive_response() -> AsyncMock:  # type: ignore[misc]
            yield mock_message

        mock_sdk_client = MagicMock()
        mock_sdk_client.connect = AsyncMock()
        mock_sdk_client.query = AsyncMock()
        mock_sdk_client.disconnect = AsyncMock()
        mock_sdk_client.receive_response = mock_receive_response

        with patch("src.claude_client.ClaudeSDKClient") as mock_sdk:
            mock_sdk.return_value = mock_sdk_client

            await client.send_message("Test")

            # Verify client was cleaned up
            assert client._client is None


@pytest.mark.unit
class TestStreamMessage:
    """Test stream_message method."""

    @pytest.fixture
    def client(self) -> ClaudeClient:
        """Create test client."""
        return ClaudeClient(
            api_key="test-api-key",
            system_prompt="Test prompt",
        )

    @pytest.mark.asyncio
    async def test_stream_message_success(self, client: ClaudeClient) -> None:
        """Test streaming message response."""
        mock_block1 = MagicMock()
        mock_block1.text = "Part 1 "

        mock_block2 = MagicMock()
        mock_block2.text = "Part 2"

        mock_msg = MagicMock()
        mock_msg.content = [mock_block1, mock_block2]

        async def mock_receive_response() -> AsyncMock:  # type: ignore[misc]
            yield mock_msg

        mock_sdk_client = MagicMock()
        mock_sdk_client.connect = AsyncMock()
        mock_sdk_client.query = AsyncMock()
        mock_sdk_client.disconnect = AsyncMock()
        mock_sdk_client.receive_response = mock_receive_response

        with patch("src.claude_client.ClaudeSDKClient") as mock_sdk:
            mock_sdk.return_value = mock_sdk_client

            chunks: list[str] = []
            async for chunk in client.stream_message("Test"):
                chunks.append(chunk)

            # Should yield both blocks
            assert chunks == ["Part 1 ", "Part 2"]

            # Verify SDK calls
            mock_sdk_client.connect.assert_called_once()
            mock_sdk_client.query.assert_called_once_with("Test")
            mock_sdk_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_message_multiple_messages(self, client: ClaudeClient) -> None:
        """Test streaming with multiple messages."""
        mock_block1 = MagicMock()
        mock_block1.text = "Chunk 1"

        mock_block2 = MagicMock()
        mock_block2.text = "Chunk 2"

        mock_msg1 = MagicMock()
        mock_msg1.content = [mock_block1]

        mock_msg2 = MagicMock()
        mock_msg2.content = [mock_block2]

        async def mock_receive_response() -> AsyncMock:  # type: ignore[misc]
            yield mock_msg1
            yield mock_msg2

        mock_sdk_client = MagicMock()
        mock_sdk_client.connect = AsyncMock()
        mock_sdk_client.query = AsyncMock()
        mock_sdk_client.disconnect = AsyncMock()
        mock_sdk_client.receive_response = mock_receive_response

        with patch("src.claude_client.ClaudeSDKClient") as mock_sdk:
            mock_sdk.return_value = mock_sdk_client

            chunks: list[str] = []
            async for chunk in client.stream_message("Test"):
                chunks.append(chunk)

            assert chunks == ["Chunk 1", "Chunk 2"]

    @pytest.mark.asyncio
    async def test_stream_message_error_handling(self, client: ClaudeClient) -> None:
        """Test error handling during streaming."""
        mock_sdk_client = MagicMock()
        mock_sdk_client.connect = AsyncMock()
        mock_sdk_client.query = AsyncMock(side_effect=Exception("Query failed"))
        mock_sdk_client.disconnect = AsyncMock()

        with patch("src.claude_client.ClaudeSDKClient") as mock_sdk:
            mock_sdk.return_value = mock_sdk_client

            with pytest.raises(ClaudeClientError) as exc_info:
                async for _ in client.stream_message("Test"):
                    pass

            assert "Failed to stream message" in str(exc_info.value)
            # Verify disconnect was called
            mock_sdk_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_message_cleanup(self, client: ClaudeClient) -> None:
        """Test cleanup after streaming."""
        mock_block = MagicMock()
        mock_block.text = "Chunk"

        mock_msg = MagicMock()
        mock_msg.content = [mock_block]

        async def mock_receive_response() -> AsyncMock:  # type: ignore[misc]
            yield mock_msg

        mock_sdk_client = MagicMock()
        mock_sdk_client.connect = AsyncMock()
        mock_sdk_client.query = AsyncMock()
        mock_sdk_client.disconnect = AsyncMock()
        mock_sdk_client.receive_response = mock_receive_response

        with patch("src.claude_client.ClaudeSDKClient") as mock_sdk:
            mock_sdk.return_value = mock_sdk_client

            async for _ in client.stream_message("Test"):
                pass

            # Verify client was cleaned up
            assert client._client is None
