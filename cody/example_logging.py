"""
Example usage of InteractionLogger.

This demonstrates how to use the InteractionLogger to log Claude interactions.
"""

import time

from src.logging import InteractionLogger


def example_basic_usage() -> None:
    """Basic usage example."""
    # Create logger (logs to .cody/logs/ by default)
    logger = InteractionLogger()

    # Log a complete interaction (convenience method)
    request_id = logger.log_interaction(
        system_prompt="You are a helpful assistant.",
        user_message="What is 2+2?",
        response="2+2 equals 4.",
        duration_ms=1234.5,
        tools_called=[],
        error=None,
    )

    print(f"Logged interaction with request_id: {request_id}")


def example_granular_logging() -> None:
    """Example of logging intent and result separately."""
    logger = InteractionLogger()

    # Generate unique request ID
    request_id = logger.generate_request_id()

    # Log intent BEFORE sending to Claude
    logger.log_intent(
        request_id=request_id,
        system_prompt="You are a code assistant.",
        user_message="Write a hello world function",
        full_context="Previous context here...",
    )

    # Simulate API call
    start_time = time.time()
    # ... call Claude API here ...
    response = "def hello(): print('Hello, World!')"
    duration_ms = (time.time() - start_time) * 1000

    # Log result AFTER receiving from Claude
    logger.log_result(
        request_id=request_id,
        response=response,
        duration_ms=duration_ms,
        tools_called=["code_generation"],
        error=None,
    )

    print(f"Logged interaction in two stages: {request_id}")


def example_with_error() -> None:
    """Example of logging an interaction with an error."""
    logger = InteractionLogger()

    request_id = logger.log_interaction(
        system_prompt="You are helpful.",
        user_message="Process this request",
        response="",
        duration_ms=500.0,
        error="API timeout after 30s",
    )

    print(f"Logged failed interaction: {request_id}")


def example_reading_logs() -> None:
    """Example of reading logged interactions."""
    logger = InteractionLogger()

    # Read today's logs
    logs = logger.read_logs()
    print(f"Found {len(logs)} log entries today")

    # Read with limit
    recent_logs = logger.read_logs(limit=10)
    print(f"Last 10 entries: {len(recent_logs)}")

    # Find specific interaction by ID
    if logs:
        first_entry = logs[0]
        request_id = first_entry.get("request_id")

        if request_id:
            interaction = logger.get_interaction_by_id(request_id)
            if interaction:
                print(f"Found interaction: {interaction['intent']}")
                print(f"Result: {interaction['result']}")


if __name__ == "__main__":
    print("=== Basic Usage ===")
    example_basic_usage()

    print("\n=== Granular Logging ===")
    example_granular_logging()

    print("\n=== With Error ===")
    example_with_error()

    print("\n=== Reading Logs ===")
    example_reading_logs()

    print("\nLogs are stored in .cody/logs/interactions-YYYY-MM-DD.jsonl")
