#!/usr/bin/env python3
"""
Example usage of ClaudeClient.

This demonstrates how to use the ClaudeClient class to send messages
and stream responses from Claude.
"""

import asyncio
import os

from src.claude_client import ClaudeClient


async def main() -> None:
    """Example usage of ClaudeClient."""
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set")
        return

    # Create client with system prompt
    client = ClaudeClient(
        api_key=api_key,
        system_prompt="You are a helpful assistant. Be concise.",
    )

    # Example 1: Send a simple message
    print("Example 1: Simple message")
    print("-" * 40)
    response = await client.send_message("What is 2 + 2? Just give the number.")
    print(f"Response: {response}\n")

    # Example 2: Stream a response
    print("Example 2: Streaming response")
    print("-" * 40)
    print("Response: ", end="", flush=True)
    async for chunk in client.stream_message("Count from 1 to 5 with spaces."):
        print(chunk, end="", flush=True)
    print("\n")

    # Example 3: Multiple messages (independent)
    print("Example 3: Multiple independent messages")
    print("-" * 40)
    response1 = await client.send_message("What color is the sky?")
    print(f"Response 1: {response1}")

    response2 = await client.send_message("What is the capital of France?")
    print(f"Response 2: {response2}\n")


if __name__ == "__main__":
    asyncio.run(main())
