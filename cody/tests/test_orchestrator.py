"""
Unit tests for Orchestrator module.

Tests orchestrator message processing with mocked Claude SDK.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config import CodyConfig
from src.orchestrator import Orchestrator, OrchestratorError


@pytest.mark.unit
class TestOrchestratorInit:
    """Test Orchestrator initialization."""

    def test_init_success(self) -> None:
        """Test successful initialization with valid config."""
        config = CodyConfig(
            user_timezone="America/Los_Angeles",
            assistant_name="Cody",
            api_key="test-api-key",
        )

        orchestrator = Orchestrator(config)

        assert orchestrator.config == config

    def test_init_missing_api_key(self) -> None:
        """Test initialization fails when API key is missing."""
        config = CodyConfig(
            user_timezone="America/Los_Angeles",
            assistant_name="Cody",
            api_key=None,  # No API key
        )

        with pytest.raises(OrchestratorError) as exc_info:
            Orchestrator(config)

        assert "ANTHROPIC_API_KEY" in str(exc_info.value)


@pytest.mark.unit
class TestProcessMessage:
    """Test process_message method with mocked Claude SDK."""

    @pytest.fixture
    def config(self) -> CodyConfig:
        """Create test configuration."""
        return CodyConfig(
            user_timezone="America/Los_Angeles",
            assistant_name="Cody",
            api_key="test-api-key",
        )

    @pytest.fixture
    def orchestrator(self, config: CodyConfig) -> Orchestrator:
        """Create orchestrator instance."""
        return Orchestrator(config)

    @pytest.mark.asyncio
    async def test_process_message_success(self, orchestrator: Orchestrator) -> None:
        """Test successful message processing."""
        # Create mock response
        mock_block = MagicMock()
        mock_block.text = "Hello! How can I help you today?"

        mock_message = MagicMock()
        mock_message.content = [mock_block]

        # Mock async generator for receive_response
        async def mock_receive_response() -> AsyncMock:  # type: ignore[misc]
            yield mock_message

        # Mock Claude SDK client
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.receive_response = mock_receive_response

        with patch("src.orchestrator.ClaudeSDKClient") as mock_sdk:
            mock_sdk.return_value = mock_client

            # Process message
            response = await orchestrator.process_message("Hello")

            # Verify response
            assert response == "Hello! How can I help you today?"

            # Verify SDK was called correctly
            mock_client.connect.assert_called_once()
            mock_client.query.assert_called_once_with("Hello")
            mock_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_multiple_blocks(self, orchestrator: Orchestrator) -> None:
        """Test processing message with multiple content blocks."""
        # Create mock response with multiple blocks
        mock_block1 = MagicMock()
        mock_block1.text = "Part 1 "

        mock_block2 = MagicMock()
        mock_block2.text = "Part 2"

        mock_message = MagicMock()
        mock_message.content = [mock_block1, mock_block2]

        async def mock_receive_response() -> AsyncMock:  # type: ignore[misc]
            yield mock_message

        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.receive_response = mock_receive_response

        with patch("src.orchestrator.ClaudeSDKClient") as mock_sdk:
            mock_sdk.return_value = mock_client

            response = await orchestrator.process_message("Test")

            # Should combine both blocks
            assert response == "Part 1 Part 2"

    @pytest.mark.asyncio
    async def test_process_message_empty_response(self, orchestrator: Orchestrator) -> None:
        """Test error when Claude returns empty response."""
        # Mock empty response
        mock_message = MagicMock()
        mock_message.content = []

        async def mock_receive_response() -> AsyncMock:  # type: ignore[misc]
            yield mock_message

        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.receive_response = mock_receive_response

        with patch("src.orchestrator.ClaudeSDKClient") as mock_sdk:
            mock_sdk.return_value = mock_client

            with pytest.raises(OrchestratorError) as exc_info:
                await orchestrator.process_message("Hello")

            assert "No response" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_process_message_strips_whitespace(self, orchestrator: Orchestrator) -> None:
        """Test that response is stripped of leading/trailing whitespace."""
        mock_block = MagicMock()
        mock_block.text = "  \n  Response  \n  "

        mock_message = MagicMock()
        mock_message.content = [mock_block]

        async def mock_receive_response() -> AsyncMock:  # type: ignore[misc]
            yield mock_message

        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.receive_response = mock_receive_response

        with patch("src.orchestrator.ClaudeSDKClient") as mock_sdk:
            mock_sdk.return_value = mock_client

            response = await orchestrator.process_message("Test")

            assert response == "Response"

    @pytest.mark.asyncio
    async def test_process_message_sdk_connect_error(self, orchestrator: Orchestrator) -> None:
        """Test error handling when SDK fails to connect."""
        mock_client = MagicMock()
        mock_client.connect = AsyncMock(side_effect=Exception("Connection failed"))

        with patch("src.orchestrator.ClaudeSDKClient") as mock_sdk:
            mock_sdk.return_value = mock_client

            with pytest.raises(OrchestratorError) as exc_info:
                await orchestrator.process_message("Hello")

            assert "Failed to process message" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_process_message_sdk_query_error(self, orchestrator: Orchestrator) -> None:
        """Test error handling when SDK query fails."""
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.query = AsyncMock(side_effect=Exception("Query failed"))
        mock_client.disconnect = AsyncMock()

        with patch("src.orchestrator.ClaudeSDKClient") as mock_sdk:
            mock_sdk.return_value = mock_client

            with pytest.raises(OrchestratorError):
                await orchestrator.process_message("Hello")

            # Verify disconnect was called despite error
            mock_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_disconnect_on_error(self, orchestrator: Orchestrator) -> None:
        """Test that client disconnects even when receive_response fails."""
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.disconnect = AsyncMock()

        # Mock receive_response to raise exception
        async def mock_receive_response() -> AsyncMock:  # type: ignore[misc]
            raise Exception("Receive failed")
            yield  # Never reached, but needed for typing

        mock_client.receive_response = mock_receive_response

        with patch("src.orchestrator.ClaudeSDKClient") as mock_sdk:
            mock_sdk.return_value = mock_client

            with pytest.raises(OrchestratorError):
                await orchestrator.process_message("Hello")

            # Verify disconnect was called despite error
            mock_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_uses_config_settings(
        self, orchestrator: Orchestrator
    ) -> None:
        """Test that message processing uses config settings."""
        # Use custom config
        custom_config = CodyConfig(
            user_timezone="America/New_York",
            assistant_name="TestBot",
            api_key="test-api-key",
        )
        custom_orchestrator = Orchestrator(custom_config)

        mock_block = MagicMock()
        mock_block.text = "Response"

        mock_message = MagicMock()
        mock_message.content = [mock_block]

        async def mock_receive_response() -> AsyncMock:  # type: ignore[misc]
            yield mock_message

        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.receive_response = mock_receive_response

        with patch("src.orchestrator.ClaudeSDKClient") as mock_sdk:
            with patch("src.orchestrator.ClaudeAgentOptions") as mock_options:
                mock_sdk.return_value = mock_client

                await custom_orchestrator.process_message("Hello")

                # Verify options were created with correct system prompt
                mock_options.assert_called_once()
                call_kwargs = mock_options.call_args.kwargs
                assert "TestBot" in call_kwargs["system_prompt"]
                assert call_kwargs["max_turns"] == 1
                assert call_kwargs["permission_mode"] == "bypassPermissions"

    @pytest.mark.asyncio
    async def test_process_message_includes_temporal_context(
        self, orchestrator: Orchestrator
    ) -> None:
        """Test that temporal context is included in system prompt."""
        mock_block = MagicMock()
        mock_block.text = "Response"

        mock_message = MagicMock()
        mock_message.content = [mock_block]

        async def mock_receive_response() -> AsyncMock:  # type: ignore[misc]
            yield mock_message

        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.receive_response = mock_receive_response

        with patch("src.orchestrator.ClaudeSDKClient") as mock_sdk:
            with patch("src.orchestrator.ClaudeAgentOptions") as mock_options:
                mock_sdk.return_value = mock_client

                await orchestrator.process_message("Hello")

                # Verify temporal context is in system prompt
                mock_options.assert_called_once()
                call_kwargs = mock_options.call_args.kwargs
                system_prompt = call_kwargs["system_prompt"]

                # Should contain temporal context
                assert "Current time:" in system_prompt


@pytest.mark.unit
class TestBuildSystemPrompt:
    """Test _build_system_prompt method."""

    def test_build_system_prompt(self) -> None:
        """Test system prompt construction."""
        config = CodyConfig(
            user_timezone="America/Los_Angeles",
            assistant_name="TestBot",
            api_key="test-api-key",
        )
        orchestrator = Orchestrator(config)

        temporal_context = "Current time: Monday, January 14, 2026 at 3:00 PM PST (afternoon)"
        prompt = orchestrator._build_system_prompt(temporal_context)

        # Verify prompt contains expected elements
        assert "TestBot" in prompt
        assert temporal_context in prompt
        assert "personal AI assistant" in prompt
        assert "concise and helpful" in prompt

    def test_build_system_prompt_different_assistant_name(self) -> None:
        """Test system prompt uses configured assistant name."""
        config = CodyConfig(
            user_timezone="America/Los_Angeles",
            assistant_name="MyCustomBot",
            api_key="test-api-key",
        )
        orchestrator = Orchestrator(config)

        prompt = orchestrator._build_system_prompt("temporal context")

        assert "MyCustomBot" in prompt
        assert "Cody" not in prompt  # Should not contain default name
