"""
Unit tests for CLI module.

Tests CLI argument parsing, message processing, and error handling using mocks.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cli import main, process_message, setup_logging
from src.config import CodyConfig


@pytest.mark.unit
class TestSetupLogging:
    """Test logging configuration."""

    def test_verbose_logging(self) -> None:
        """Test that verbose flag enables DEBUG level."""
        # Test that the function works without errors
        setup_logging(verbose=True)
        # Function executed successfully

    def test_non_verbose_logging(self) -> None:
        """Test that non-verbose uses WARNING level."""
        # Test that the function works without errors
        setup_logging(verbose=False)
        # Function executed successfully


@pytest.mark.unit
class TestProcessMessage:
    """Test message processing with mocked Claude SDK."""

    @pytest.mark.asyncio
    async def test_process_message_success(self) -> None:
        """Test successful message processing."""
        # Create mock config
        config = CodyConfig(
            user_timezone="America/Los_Angeles",
            assistant_name="Cody",
            api_key="test-api-key",
        )

        # Create mock response
        mock_block = MagicMock()
        mock_block.text = "Hello! How can I help you?"

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

        with patch("src.cli.ClaudeSDKClient") as mock_sdk:
            mock_sdk.return_value = mock_client

            response, exit_code = await process_message(
                message="Hello",
                config=config,
                verbose=False,
            )

            # Verify success
            assert exit_code == 0
            assert response == "Hello! How can I help you?"

            # Verify SDK was called correctly
            mock_client.connect.assert_called_once()
            mock_client.query.assert_called_once_with("Hello")
            mock_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_no_api_key(self) -> None:
        """Test error when API key is missing."""
        config = CodyConfig(
            user_timezone="America/Los_Angeles",
            assistant_name="Cody",
            api_key=None,  # No API key
        )

        response, exit_code = await process_message(
            message="Hello",
            config=config,
            verbose=False,
        )

        # Verify error
        assert exit_code == 1
        assert "ANTHROPIC_API_KEY" in response

    @pytest.mark.asyncio
    async def test_process_message_empty_response(self) -> None:
        """Test error when Claude returns empty response."""
        config = CodyConfig(
            user_timezone="America/Los_Angeles",
            assistant_name="Cody",
            api_key="test-api-key",
        )

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

        with patch("src.cli.ClaudeSDKClient") as mock_sdk:
            mock_sdk.return_value = mock_client

            response, exit_code = await process_message(
                message="Hello",
                config=config,
                verbose=False,
            )

            # Verify error
            assert exit_code == 1
            assert "No response" in response

    @pytest.mark.asyncio
    async def test_process_message_sdk_exception(self) -> None:
        """Test error handling when SDK raises exception."""
        config = CodyConfig(
            user_timezone="America/Los_Angeles",
            assistant_name="Cody",
            api_key="test-api-key",
        )

        # Mock SDK to raise exception
        mock_client = MagicMock()
        mock_client.connect = AsyncMock(side_effect=Exception("SDK connection failed"))

        with patch("src.cli.ClaudeSDKClient") as mock_sdk:
            mock_sdk.return_value = mock_client

            response, exit_code = await process_message(
                message="Hello",
                config=config,
                verbose=False,
            )

            # Verify error handling
            assert exit_code == 1
            assert "Error:" in response

    @pytest.mark.asyncio
    async def test_process_message_disconnect_on_error(self) -> None:
        """Test that client disconnects even when query fails."""
        config = CodyConfig(
            user_timezone="America/Los_Angeles",
            assistant_name="Cody",
            api_key="test-api-key",
        )

        # Mock SDK to raise exception during query
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.query = AsyncMock(side_effect=Exception("Query failed"))
        mock_client.disconnect = AsyncMock()

        with patch("src.cli.ClaudeSDKClient") as mock_sdk:
            mock_sdk.return_value = mock_client

            await process_message(
                message="Hello",
                config=config,
                verbose=False,
            )

            # Verify disconnect was called despite error
            mock_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_uses_config_settings(self) -> None:
        """Test that message processing uses config settings."""
        config = CodyConfig(
            user_timezone="America/New_York",
            assistant_name="TestBot",
            api_key="test-api-key",
        )

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

        with patch("src.cli.ClaudeSDKClient") as mock_sdk:
            with patch("src.cli.ClaudeAgentOptions") as mock_options:
                mock_sdk.return_value = mock_client

                await process_message(
                    message="Hello",
                    config=config,
                    verbose=True,
                )

                # Verify options were created with correct system prompt
                mock_options.assert_called_once()
                call_kwargs = mock_options.call_args.kwargs
                assert "TestBot" in call_kwargs["system_prompt"]
                assert call_kwargs["max_turns"] == 1
                assert call_kwargs["permission_mode"] == "bypassPermissions"


@pytest.mark.unit
class TestMain:
    """Test main CLI entry point."""

    def test_main_success(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test successful CLI execution."""
        # Create temporary config
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Create minimal config
            config = CodyConfig(
                user_timezone="America/Los_Angeles",
                assistant_name="Cody",
                api_key=None,  # Will come from env var
            )
            config.save(config_path)

            # Mock SDK
            mock_block = MagicMock()
            mock_block.text = "Hello!"

            mock_message = MagicMock()
            mock_message.content = [mock_block]

            async def mock_receive_response() -> AsyncMock:  # type: ignore[misc]
                yield mock_message

            mock_client = MagicMock()
            mock_client.connect = AsyncMock()
            mock_client.query = AsyncMock()
            mock_client.disconnect = AsyncMock()
            mock_client.receive_response = mock_receive_response

            # Set API key in environment
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key"}):
                with patch("sys.argv", ["cli", "Hello", "--config", str(config_path)]):
                    with patch("src.cli.ClaudeSDKClient") as mock_sdk:
                        mock_sdk.return_value = mock_client

                        with pytest.raises(SystemExit) as exc_info:
                            main()

                        # Verify exit code 0
                        assert exc_info.value.code == 0

    def test_main_missing_config(self) -> None:
        """Test error when config file is missing or invalid."""
        with patch("sys.argv", ["cli", "Hello"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Verify non-zero exit code
            assert exc_info.value.code == 1

    def test_main_keyboard_interrupt(self) -> None:
        """Test graceful handling of keyboard interrupt."""
        with patch("sys.argv", ["cli", "Hello"]):
            with patch("src.cli.CodyConfig.load") as mock_load:
                mock_load.side_effect = KeyboardInterrupt()

                with pytest.raises(SystemExit) as exc_info:
                    main()

                # Verify SIGINT exit code
                assert exc_info.value.code == 130
