#!/usr/bin/env python3
"""
Non-interactive CLI mode for Cody assistant.

Provides a command-line interface for sending single messages and receiving responses
without interactive prompts or loops.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import NoReturn

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from rich.console import Console
from rich.logging import RichHandler

from .config import CodyConfig, ConfigurationError
from .temporal import TemporalContext

# Configure logging
logger = logging.getLogger(__name__)


def setup_logging(verbose: bool) -> None:
    """
    Configure logging for CLI.

    Args:
        verbose: If True, enable DEBUG level logging. Otherwise, WARNING level.
    """
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=verbose)],
    )


async def process_message(
    message: str,
    config: CodyConfig,
    verbose: bool,
) -> tuple[str, int]:
    """
    Process a single message through the Claude Agent SDK.

    Args:
        message: User message to process
        config: Cody configuration
        verbose: Enable verbose output

    Returns:
        Tuple of (response text, exit code)
        Exit code: 0 on success, 1 on error
    """
    try:
        # Validate API key
        if not config.api_key:
            logger.error("ANTHROPIC_API_KEY environment variable not set")
            return "Error: ANTHROPIC_API_KEY environment variable not set", 1

        # Build temporal context for system prompt
        temporal = TemporalContext(config.user_timezone)
        temporal_context = temporal.to_context_string()

        # Build system prompt with temporal awareness
        system_prompt = f"""You are {config.assistant_name}, a personal AI assistant.

{temporal_context}

You help users with tasks, remember context across conversations, and provide
thoughtful, accurate assistance. Be concise and helpful."""

        logger.debug(f"System prompt: {system_prompt}")
        logger.debug(f"User message: {message}")

        # Create Claude SDK client with options
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            max_turns=1,  # Non-interactive: single turn only
            permission_mode="bypassPermissions",  # No interactive prompts
        )

        client = ClaudeSDKClient(options=options)

        logger.debug("Connecting to Claude Agent SDK...")
        await client.connect()

        try:
            # Send user message
            logger.debug("Sending message to Claude...")
            await client.query(message)

            # Collect response
            response_parts: list[str] = []

            logger.debug("Receiving response...")
            async for msg in client.receive_response():
                logger.debug(f"Received message type: {type(msg).__name__}")

                # Extract text content from AssistantMessage
                if hasattr(msg, "content"):
                    for block in msg.content:
                        if hasattr(block, "text"):
                            response_parts.append(block.text)
                            logger.debug(f"Response part: {block.text[:100]}...")

            response = "".join(response_parts).strip()

            if not response:
                logger.warning("No response received from Claude")
                return "Error: No response received from Claude", 1

            logger.debug(f"Full response: {response}")
            return response, 0

        finally:
            # Always disconnect
            logger.debug("Disconnecting from Claude Agent SDK...")
            await client.disconnect()

    except Exception as e:
        logger.exception("Error processing message")
        return f"Error: {e}", 1


def main() -> NoReturn:
    """
    Main entry point for non-interactive CLI.

    Exit codes:
        0: Success
        1: Error (API error, configuration error, etc.)
    """
    parser = argparse.ArgumentParser(
        description="Cody: Non-interactive AI assistant CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m cody.src.cli "What is the weather like?"
  python -m cody.src.cli "Hello" --verbose
  python -m cody.src.cli "Help me" --config /path/to/config.yaml
        """,
    )

    parser.add_argument(
        "message",
        type=str,
        help="Message to send to the assistant",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose debug output",
    )

    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        default=None,
        help="Path to config.yaml file (default: .cody/config.yaml)",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    console = Console()
    console_err = Console(stderr=True)

    try:
        # Load configuration
        logger.debug(f"Loading configuration from: {args.config or '.cody/config.yaml'}")
        config = CodyConfig.load(args.config)
        logger.debug(f"Configuration loaded: {config.to_dict()}")

        # Process message
        response, exit_code = asyncio.run(
            process_message(
                message=args.message,
                config=config,
                verbose=args.verbose,
            )
        )

        # Print response to stdout
        if exit_code == 0:
            console.print(response)
        else:
            console_err.print(f"[red]{response}[/red]")

        sys.exit(exit_code)

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        console_err.print(f"[red]Configuration error: {e}[/red]")
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        console_err.print("\n[yellow]Interrupted[/yellow]")
        sys.exit(130)  # Standard exit code for SIGINT

    except Exception as e:
        logger.exception("Unexpected error")
        console_err.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
