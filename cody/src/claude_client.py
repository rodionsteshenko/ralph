"""
Claude Agent SDK client wrapper.

Provides a ClaudeClient class that wraps the claude-agent-sdk ClaudeSDKClient
with support for system prompt injection, streaming response handling, and
clear error messages.
"""

import logging
from collections.abc import AsyncIterator
from typing import Literal

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

logger = logging.getLogger(__name__)


class ClaudeClientError(Exception):
    """Raised when Claude client encounters an error during API operations."""

    pass


class ClaudeClient:
    """
    Wrapper around Claude Agent SDK client.

    This class provides a clean interface for calling Claude with:
    - System prompt injection
    - Streaming response handling
    - Error handling with clear messages
    - Automatic connection management

    Example:
        >>> client = ClaudeClient(
        ...     api_key="sk-ant-...",
        ...     system_prompt="You are a helpful assistant."
        ... )
        >>> response = await client.send_message("Hello!")
        >>> print(response)
        "Hello! How can I help you today?"
    """

    def __init__(
        self,
        api_key: str,
        system_prompt: str = "",
        max_turns: int = 1,
        permission_mode: Literal[
            "default", "acceptEdits", "plan", "bypassPermissions"
        ] = "bypassPermissions",
    ) -> None:
        """
        Initialize Claude client with configuration.

        Args:
            api_key: Anthropic API key (required)
            system_prompt: System prompt to inject into conversation (optional)
            max_turns: Maximum number of conversation turns (default: 1 for non-interactive)
            permission_mode: Permission mode for SDK (default: "bypassPermissions")

        Raises:
            ClaudeClientError: If API key is missing or invalid
        """
        if not api_key:
            raise ClaudeClientError("API key is required but was not provided")

        self.api_key = api_key
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.permission_mode = permission_mode

        # SDK client will be created during send_message
        self._client: ClaudeSDKClient | None = None

    async def send_message(self, user_message: str) -> str:
        """
        Send a message to Claude and return the complete response.

        This method:
        1. Creates SDK client with configured options
        2. Connects to Claude API
        3. Sends user message
        4. Streams and aggregates response
        5. Disconnects and returns final response

        Args:
            user_message: The user's message to send to Claude

        Returns:
            Complete response text from Claude

        Raises:
            ClaudeClientError: If API call fails or response is invalid
        """
        try:
            # Create client with options
            options = ClaudeAgentOptions(
                system_prompt=self.system_prompt,
                max_turns=self.max_turns,
                permission_mode=self.permission_mode,
            )

            self._client = ClaudeSDKClient(options=options)

            logger.debug("Connecting to Claude Agent SDK...")
            await self._client.connect()

            try:
                # Send message
                logger.debug("Sending message: %s", user_message[:100])
                await self._client.query(user_message)

                # Receive and aggregate response
                response_text = await self._aggregate_response()

                logger.debug("Received response: %s", response_text[:100])
                return response_text

            finally:
                # Always disconnect, even on error
                logger.debug("Disconnecting from Claude Agent SDK...")
                await self._client.disconnect()
                self._client = None

        except ClaudeClientError:
            # Re-raise our own errors
            raise
        except Exception as e:
            logger.exception("Error in Claude API call")
            raise ClaudeClientError(f"Failed to send message to Claude: {e}") from e

    async def stream_message(self, user_message: str) -> AsyncIterator[str]:
        """
        Send a message and stream the response in chunks.

        This method yields response text as it arrives from Claude,
        allowing for streaming/progressive display of responses.

        Args:
            user_message: The user's message to send to Claude

        Yields:
            Text chunks from Claude's response as they arrive

        Raises:
            ClaudeClientError: If API call fails

        Example:
            >>> async for chunk in client.stream_message("Hello"):
            ...     print(chunk, end="", flush=True)
        """
        try:
            # Create client with options
            options = ClaudeAgentOptions(
                system_prompt=self.system_prompt,
                max_turns=self.max_turns,
                permission_mode=self.permission_mode,
            )

            self._client = ClaudeSDKClient(options=options)

            logger.debug("Connecting to Claude Agent SDK...")
            await self._client.connect()

            try:
                # Send message
                logger.debug("Sending message for streaming: %s", user_message[:100])
                await self._client.query(user_message)

                # Stream response chunks
                async for msg in self._client.receive_response():
                    # Extract text from message
                    if hasattr(msg, "content"):
                        for block in msg.content:
                            if hasattr(block, "text"):
                                logger.debug("Streaming chunk: %s", block.text[:50])
                                yield block.text

            finally:
                # Always disconnect
                logger.debug("Disconnecting from Claude Agent SDK...")
                await self._client.disconnect()
                self._client = None

        except ClaudeClientError:
            raise
        except Exception as e:
            logger.exception("Error streaming from Claude API")
            raise ClaudeClientError(f"Failed to stream message from Claude: {e}") from e

    async def _aggregate_response(self) -> str:
        """
        Aggregate streaming response into complete text.

        Returns:
            Complete response text

        Raises:
            ClaudeClientError: If no response is received or client not connected
        """
        if not self._client:
            raise ClaudeClientError("Client not connected")

        response_parts: list[str] = []

        logger.debug("Aggregating response from Claude...")
        async for msg in self._client.receive_response():
            logger.debug("Received message type: %s", type(msg).__name__)

            # Extract text content from message
            if hasattr(msg, "content"):
                for block in msg.content:
                    if hasattr(block, "text"):
                        response_parts.append(block.text)
                        logger.debug("Response part: %s...", block.text[:100])

        # Combine all parts
        response = "".join(response_parts).strip()

        if not response:
            raise ClaudeClientError("No response received from Claude API")

        return response
