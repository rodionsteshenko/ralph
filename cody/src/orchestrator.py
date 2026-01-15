"""
Orchestrator core loop for processing messages.

Provides the Orchestrator class that processes a single message through Claude Agent SDK,
building context with temporal information and returning the response.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Any, Optional

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

from .config import CodyConfig
from .messages import Message, MessageWindow
from .temporal import TemporalContext

logger = logging.getLogger(__name__)


class OrchestratorError(Exception):
    """Raised when orchestrator encounters an error during processing."""

    pass


class Orchestrator:
    """
    Orchestrates message processing through Claude Agent SDK.

    This is a non-interactive orchestrator that processes a single message
    and returns the response without any side effects (no persistence).

    Attributes:
        config: Cody configuration
        message_window: Optional message window for conversation context
    """

    def __init__(
        self, config: CodyConfig, message_window: Optional[MessageWindow] = None
    ) -> None:
        """
        Initialize orchestrator with configuration.

        Args:
            config: Cody configuration with timezone, API key, etc.
            message_window: Optional message window for maintaining conversation context

        Raises:
            OrchestratorError: If API key is missing in config
        """
        if not config.api_key:
            raise OrchestratorError("ANTHROPIC_API_KEY is required but not set in config")

        self.config = config
        self.message_window = message_window

    async def process_message(self, user_input: str) -> str:
        """
        Process a single message and return the response.

        This method:
        1. Builds temporal context from user's timezone
        2. Constructs a system prompt with temporal awareness
        3. Adds message window context if available
        4. Calls Claude Agent SDK with the user input
        5. Stores conversation in message window if available
        6. Returns the final assistant response as a string

        Args:
            user_input: The user's message to process

        Returns:
            The assistant's response as a string

        Raises:
            OrchestratorError: If processing fails or no response is received
        """
        try:
            # Build temporal context
            temporal = TemporalContext(self.config.user_timezone)
            temporal_context = temporal.to_context_string()

            # Build system prompt with temporal awareness
            system_prompt = self._build_system_prompt(temporal_context)

            logger.debug("System prompt: %s", system_prompt)
            logger.debug("User input: %s", user_input)

            # Create Claude SDK client with options
            options = ClaudeAgentOptions(
                system_prompt=system_prompt,
                max_turns=1,  # Single turn for non-interactive mode
                permission_mode="bypassPermissions",  # No interactive prompts
            )

            client = ClaudeSDKClient(options=options)

            # Connect, query, and receive response
            logger.debug("Connecting to Claude Agent SDK...")
            await client.connect()

            try:
                # Build query with conversation history if available
                if self.message_window is not None and len(self.message_window) > 0:
                    # Get existing conversation history
                    context = self.message_window.get_context()
                    # Convert to SDK format and add the new user message
                    messages_to_send = [
                        {"role": msg["role"], "content": msg["content"]} for msg in context
                    ]
                    # Add the current user message
                    messages_to_send.append({"role": "user", "content": user_input})

                    # Create async generator for message stream
                    async def message_stream() -> AsyncGenerator[dict[str, Any], None]:
                        for msg in messages_to_send:
                            yield msg

                    # Send messages as a stream
                    logger.debug(
                        "Sending messages to Claude (with %d context messages)...",
                        len(messages_to_send) - 1,
                    )
                    await client.query(message_stream())
                else:
                    # No message window - just send the user input
                    logger.debug("Sending message to Claude...")
                    await client.query(user_input)

                # Collect response
                response_text = await self._receive_response(client)

                # Add both user and assistant messages to window after successful processing
                if self.message_window is not None:
                    # Add user message
                    user_message = Message(
                        role="user", content=user_input, timezone=self.config.user_timezone
                    )
                    self.message_window.add(user_message)

                    # Add assistant response
                    assistant_message = Message(
                        role="assistant",
                        content=response_text,
                        timezone=self.config.user_timezone,
                    )
                    self.message_window.add(assistant_message)

                logger.debug("Received response: %s", response_text[:100])
                return response_text

            finally:
                # Always disconnect, even on error
                logger.debug("Disconnecting from Claude Agent SDK...")
                await client.disconnect()

        except Exception as e:
            logger.exception("Error processing message")
            raise OrchestratorError(f"Failed to process message: {e}") from e

    def _build_system_prompt(self, temporal_context: str) -> str:
        """
        Build system prompt with temporal context.

        Args:
            temporal_context: Temporal context string (e.g., "Current time: ...")

        Returns:
            Complete system prompt with assistant identity and temporal awareness
        """
        return f"""You are {self.config.assistant_name}, a personal AI assistant.

{temporal_context}

You help users with tasks, remember context across conversations, and provide
thoughtful, accurate assistance. Be concise and helpful."""

    async def _receive_response(self, client: ClaudeSDKClient) -> str:
        """
        Receive and aggregate response from Claude SDK.

        Args:
            client: Connected Claude SDK client

        Returns:
            Complete response text

        Raises:
            OrchestratorError: If no response is received or response is empty
        """
        response_parts: list[str] = []

        logger.debug("Receiving response from Claude...")
        async for msg in client.receive_response():
            logger.debug("Received message type: %s", type(msg).__name__)

            # Extract text content from AssistantMessage
            if hasattr(msg, "content"):
                for block in msg.content:
                    if hasattr(block, "text"):
                        response_parts.append(block.text)
                        logger.debug("Response part: %s...", block.text[:100])

        # Combine all response parts
        response = "".join(response_parts).strip()

        if not response:
            raise OrchestratorError("No response received from Claude")

        return response
