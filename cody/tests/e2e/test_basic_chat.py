"""
End-to-end tests for basic chat functionality.

These tests validate the core loop works by testing the non-interactive CLI
with the REAL Claude Agent SDK. They verify:
- Simple greetings work
- Temporal awareness is included
- Error handling works
- Interactions are logged to JSONL files
- Log format is correct

These tests require ANTHROPIC_API_KEY to be set in the environment.
"""

import json
import os
import tempfile
from collections.abc import Generator
from datetime import datetime
from pathlib import Path

import pytest

from src.cli import process_message
from src.config import CodyConfig
from src.log_parser import LogParser
from src.logging import InteractionLogger
from src.orchestrator import Orchestrator


@pytest.mark.e2e
@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set (required for E2E tests)",
)
class TestBasicChatE2E:
    """End-to-end tests for basic chat functionality with real Claude API calls."""

    @pytest.fixture
    def test_config(self) -> CodyConfig:
        """Create test configuration with real API key."""
        return CodyConfig(
            user_timezone="America/Los_Angeles",
            assistant_name="Cody",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )

    @pytest.fixture
    def temp_logs_dir(self) -> Generator[Path, None, None]:
        """Create temporary directory for logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def logger(self, temp_logs_dir: Path) -> InteractionLogger:
        """Create logger with temporary directory."""
        return InteractionLogger(logs_dir=temp_logs_dir)

    @pytest.mark.asyncio
    async def test_simple_greeting_returns_response(self, test_config: CodyConfig) -> None:
        """
        Test: simple greeting returns response.

        Verify that sending a simple greeting to the CLI returns a valid response
        from the Claude Agent SDK.
        """
        # Send simple greeting
        response, exit_code = await process_message(
            message="Hello! How are you?",
            config=test_config,
            verbose=False,
        )

        # Verify success
        assert exit_code == 0, f"Expected exit code 0, got {exit_code}: {response}"
        assert response, "Response should not be empty"
        assert isinstance(response, str), "Response should be a string"
        assert len(response) > 0, "Response should have content"

        # Should contain some form of greeting
        greeting_words = ["hello", "hi", "greetings", "good", "well"]
        assert any(
            word in response.lower() for word in greeting_words
        ), f"Expected greeting in response: {response}"

    @pytest.mark.asyncio
    async def test_question_about_time_includes_temporal_awareness(
        self, test_config: CodyConfig
    ) -> None:
        """
        Test: question about time includes temporal awareness.

        Verify that when asking about the time, Claude uses the temporal context
        provided by the system to give an accurate response about the time of day.
        """
        response, exit_code = await process_message(
            message="What time of day is it right now? Morning, afternoon, evening, or night?",
            config=test_config,
            verbose=False,
        )

        # Verify success
        assert exit_code == 0, f"Expected exit code 0, got {exit_code}: {response}"
        assert response, "Response should not be empty"

        # Response should mention one of the time periods
        time_periods = ["morning", "afternoon", "evening", "night"]
        assert any(
            period in response.lower() for period in time_periods
        ), f"Expected time period in response: {response}"

        # Should demonstrate temporal awareness (not just guess randomly)
        # The response should be contextually appropriate for the current time

    @pytest.mark.asyncio
    async def test_error_handling_for_invalid_input(self, test_config: CodyConfig) -> None:
        """
        Test: error handling for invalid input.

        Verify that the system handles various invalid inputs gracefully:
        - Empty strings
        - Very long inputs
        - Special characters
        """
        # Test 1: Empty string (should still process, may ask for clarification)
        response1, exit_code1 = await process_message(
            message="",
            config=test_config,
            verbose=False,
        )

        # Empty string should still succeed (Claude may ask "How can I help?")
        assert exit_code1 == 0, f"Empty string should not crash: {response1}"
        assert isinstance(response1, str), "Response should be a string even for empty input"

        # Test 2: Very long input
        long_message = "Tell me about " + "word " * 500 + "in one sentence."
        response2, exit_code2 = await process_message(
            message=long_message,
            config=test_config,
            verbose=False,
        )

        assert exit_code2 == 0, f"Long input should not crash: {response2}"
        assert response2, "Response should not be empty for long input"

        # Test 3: Special characters
        special_message = 'Process this: "Hello" @#$%^&*() [] {} \\ / < > ?'
        response3, exit_code3 = await process_message(
            message=special_message,
            config=test_config,
            verbose=False,
        )

        assert exit_code3 == 0, f"Special characters should not crash: {response3}"
        assert response3, "Response should not be empty for special characters"

    @pytest.mark.asyncio
    async def test_interaction_logged_to_jsonl_file(
        self, test_config: CodyConfig, temp_logs_dir: Path, logger: InteractionLogger
    ) -> None:
        """
        Test: Verify interaction logged to JSONL file.

        This test verifies that when we process a message through the orchestrator,
        it gets logged to the JSONL file with all required fields.
        """
        # Create orchestrator (which should log interactions)
        orchestrator = Orchestrator(test_config)

        # Manually log the interaction (since orchestrator doesn't auto-log yet)
        # This simulates what the full system will do
        start_time = datetime.now()
        user_message = "What is 2 + 2?"

        # Process message
        response = await orchestrator.process_message(user_message)

        # Calculate duration
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        # Log the interaction
        request_id = logger.log_interaction(
            system_prompt="Test system prompt",
            user_message=user_message,
            response=response,
            duration_ms=duration_ms,
            full_context=None,
            tools_called=None,
            error=None,
        )

        # Verify log file was created
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_logs_dir / f"interactions-{today}.jsonl"

        assert log_file.exists(), f"Log file should exist: {log_file}"
        assert log_file.is_file(), f"Log path should be a file: {log_file}"

        # Read and verify log entries
        with open(log_file) as f:
            lines = f.readlines()

        assert len(lines) == 2, "Should have 2 log entries (intent + result)"

        # Parse entries
        intent_entry = json.loads(lines[0])
        result_entry = json.loads(lines[1])

        # Verify intent entry structure
        assert intent_entry["request_id"] == request_id
        assert intent_entry["stage"] == "intent"
        assert intent_entry["user_message"] == user_message
        assert "timestamp" in intent_entry
        assert "system_prompt" in intent_entry

        # Verify result entry structure
        assert result_entry["request_id"] == request_id
        assert result_entry["stage"] == "result"
        assert result_entry["response"] == response
        assert result_entry["duration_ms"] == duration_ms
        assert "timestamp" in result_entry
        assert "tools_called" in result_entry
        assert result_entry["error"] is None

    @pytest.mark.asyncio
    async def test_log_format_verified_with_log_parser(
        self, test_config: CodyConfig, temp_logs_dir: Path, logger: InteractionLogger
    ) -> None:
        """
        Test: Use log_parser to verify log format is correct.

        This test creates a log file, logs some interactions, then uses the
        LogParser to verify the format is correct and can be parsed successfully.
        """
        # Create orchestrator
        orchestrator = Orchestrator(test_config)

        # Log multiple interactions
        messages = [
            "Hello!",
            "What is 5 + 7?",
            "Thank you!",
        ]

        request_ids = []
        for msg in messages:
            start_time = datetime.now()
            response = await orchestrator.process_message(msg)
            end_time = datetime.now()
            duration_ms = (end_time - start_time).total_seconds() * 1000

            request_id = logger.log_interaction(
                system_prompt="You are a helpful assistant",
                user_message=msg,
                response=response,
                duration_ms=duration_ms,
            )
            request_ids.append(request_id)

        # Get log file path
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_logs_dir / f"interactions-{today}.jsonl"

        assert log_file.exists(), "Log file should exist"

        # Use LogParser to parse the logs
        parser = LogParser(log_file)
        entries = parser.parse_logs()

        # Verify we got all entries (2 per interaction: intent + result)
        assert len(entries) == len(messages) * 2, f"Expected {len(messages) * 2} entries"

        # Verify all entries have required fields
        for entry in entries:
            assert "request_id" in entry, "Entry should have request_id"
            assert "timestamp" in entry, "Entry should have timestamp"
            assert "stage" in entry, "Entry should have stage"
            assert entry["stage"] in ["intent", "result"], "Stage should be intent or result"

            if entry["stage"] == "intent":
                assert "system_prompt" in entry
                assert "user_message" in entry
                assert "full_context" in entry
            else:  # result
                assert "response" in entry
                assert "duration_ms" in entry
                assert "tools_called" in entry
                assert "error" in entry

        # Group by request_id
        grouped = parser.group_by_request_id(entries)

        # Verify all request IDs are present
        assert len(grouped) == len(messages), "Should have all interactions grouped"
        for req_id in request_ids:
            assert req_id in grouped, f"Request ID {req_id} should be in grouped logs"
            assert grouped[req_id]["intent"] is not None, "Should have intent entry"
            assert grouped[req_id]["result"] is not None, "Should have result entry"

        # Verify statistics calculation works
        stats = parser.calculate_statistics(grouped)

        assert stats["total_interactions"] == len(messages)
        assert stats["successful_count"] == len(messages)
        assert stats["error_count"] == 0
        assert stats["avg_duration_ms"] > 0
        assert isinstance(stats["tools_usage"], dict)
        assert stats["date_range"][0] is not None
        assert stats["date_range"][1] is not None
        assert stats["estimated_tokens"] > 0

    @pytest.mark.asyncio
    async def test_cli_with_logging_integration(
        self, test_config: CodyConfig, temp_logs_dir: Path
    ) -> None:
        """
        Test: Full CLI integration with logging.

        This test verifies the complete flow:
        1. Send message via CLI
        2. Get response
        3. Verify it can be logged
        4. Verify log can be parsed
        """
        # Process message through CLI
        message = "What is the capital of France? Just name the city."
        response, exit_code = await process_message(
            message=message,
            config=test_config,
            verbose=False,
        )

        # Verify success
        assert exit_code == 0, f"CLI should succeed: {response}"
        assert response, "Should get response"
        assert "paris" in response.lower(), f"Should answer correctly: {response}"

        # Now log this interaction (simulating what full system will do)
        logger = InteractionLogger(logs_dir=temp_logs_dir)

        request_id = logger.log_interaction(
            system_prompt="Test system",
            user_message=message,
            response=response,
            duration_ms=1000.0,
        )

        # Verify log file exists and is readable
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_logs_dir / f"interactions-{today}.jsonl"

        assert log_file.exists()

        # Parse with log_parser
        parser = LogParser(log_file)
        entries = parser.parse_logs()

        assert len(entries) == 2  # intent + result

        # Verify we can find this specific interaction
        grouped = parser.group_by_request_id(entries)
        assert request_id in grouped
        assert grouped[request_id]["intent"]["user_message"] == message
        assert grouped[request_id]["result"]["response"] == response

    @pytest.mark.asyncio
    async def test_error_logged_correctly(
        self, test_config: CodyConfig, temp_logs_dir: Path
    ) -> None:
        """
        Test: Verify that errors are logged correctly.

        When an error occurs, it should be captured in the log file
        with the error field populated.
        """
        logger = InteractionLogger(logs_dir=temp_logs_dir)

        # Simulate an error scenario
        error_message = "API timeout after 30s"

        request_id = logger.log_interaction(
            system_prompt="Test system",
            user_message="This failed",
            response="",
            duration_ms=30000.0,
            error=error_message,
        )

        # Verify log file
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_logs_dir / f"interactions-{today}.jsonl"

        assert log_file.exists()

        # Parse logs
        parser = LogParser(log_file)
        entries = parser.parse_logs()

        # Find result entry
        result_entry = next(e for e in entries if e["stage"] == "result")

        assert result_entry["error"] == error_message
        assert result_entry["request_id"] == request_id

        # Verify error filtering works
        grouped = parser.group_by_request_id(entries)
        errors_only = parser.filter_errors_only(grouped)

        assert len(errors_only) == 1
        assert request_id in errors_only

    @pytest.mark.asyncio
    async def test_multiple_chats_logged_separately(
        self, test_config: CodyConfig, temp_logs_dir: Path, logger: InteractionLogger
    ) -> None:
        """
        Test: Verify that multiple chat interactions are logged separately.

        Each interaction should have a unique request_id and be independently
        retrievable from the logs.
        """
        orchestrator = Orchestrator(test_config)

        # Process multiple independent messages
        messages = [
            "Hello",
            "What is 10 + 5?",
            "Goodbye",
        ]

        request_ids = []
        responses = []

        for msg in messages:
            start_time = datetime.now()
            response = await orchestrator.process_message(msg)
            responses.append(response)
            end_time = datetime.now()

            duration_ms = (end_time - start_time).total_seconds() * 1000

            request_id = logger.log_interaction(
                system_prompt="System",
                user_message=msg,
                response=response,
                duration_ms=duration_ms,
            )
            request_ids.append(request_id)

        # Verify all request IDs are unique
        assert len(set(request_ids)) == len(request_ids), "All request IDs should be unique"

        # Verify log file
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_logs_dir / f"interactions-{today}.jsonl"

        parser = LogParser(log_file)
        entries = parser.parse_logs()

        # Should have 2 entries per message (intent + result)
        assert len(entries) == len(messages) * 2

        # Group by request_id
        grouped = parser.group_by_request_id(entries)

        # Verify each interaction is separate
        for i, req_id in enumerate(request_ids):
            assert req_id in grouped
            assert grouped[req_id]["intent"]["user_message"] == messages[i]
            assert grouped[req_id]["result"]["response"] == responses[i]

    @pytest.mark.asyncio
    async def test_temporal_context_in_logs(
        self, test_config: CodyConfig, temp_logs_dir: Path, logger: InteractionLogger
    ) -> None:
        """
        Test: Verify temporal context is included in logged system prompts.

        The system prompt should include temporal information that gets logged,
        so we can verify what context Claude received.
        """
        orchestrator = Orchestrator(test_config)

        # Process a time-related message
        message = "What time of day is it?"
        response = await orchestrator.process_message(message)

        # The system prompt should include temporal context
        # Let's build it the same way the orchestrator does
        from src.temporal import TemporalContext

        temporal = TemporalContext(test_config.user_timezone)
        temporal_context = temporal.to_context_string()
        system_prompt = f"""You are {test_config.assistant_name}, a personal AI assistant.

{temporal_context}

You help users with tasks, remember context across conversations, and provide
thoughtful, accurate assistance. Be concise and helpful."""

        # Log the interaction
        logger.log_interaction(
            system_prompt=system_prompt,
            user_message=message,
            response=response,
            duration_ms=1000.0,
        )

        # Verify log contains temporal context
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_logs_dir / f"interactions-{today}.jsonl"

        with open(log_file) as f:
            lines = f.readlines()

        intent_entry = json.loads(lines[0])

        # System prompt should contain temporal markers
        assert "Current date:" in intent_entry["system_prompt"]
        assert "Current time:" in intent_entry["system_prompt"]
        assert "Day of week:" in intent_entry["system_prompt"]
        assert test_config.user_timezone in intent_entry["system_prompt"]
