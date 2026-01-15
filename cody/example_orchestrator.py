#!/usr/bin/env python3
"""
Example usage of the Orchestrator class.

This demonstrates how to use the Orchestrator to process messages.
"""

import asyncio
import os
from pathlib import Path

from src.config import CodyConfig
from src.orchestrator import Orchestrator


async def main() -> None:
    """Main example function."""
    # Load configuration
    config = CodyConfig.load(Path.cwd() / ".cody" / "config.yaml")

    # Create orchestrator
    orchestrator = Orchestrator(config)

    # Process a message
    print("Processing message...")
    response = await orchestrator.process_message("Hello! What's 2+2?")

    print(f"\nResponse: {response}\n")


if __name__ == "__main__":
    # Ensure API key is set
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        exit(1)

    asyncio.run(main())
