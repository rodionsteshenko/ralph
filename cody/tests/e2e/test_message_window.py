"""
End-to-end tests for message window functionality.

These tests validate that the message window (conversation context) works correctly
with the REAL Claude Agent SDK. They verify:
- Sequential messages maintain context (second message can reference first)
- Agent recalls information from previous messages
- Message window persists between CLI invocations
- Window overflow correctly drops oldest messages
- All interactions are logged with full context in JSONL
- Log parsing can verify context includes previous messages

These tests require ANTHROPIC_API_KEY to be set in the environment.
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Generator

import pytest

from src.cli import process_message
from src.config import CodyConfig
from src.log_parser import LogParser
from src.logging import InteractionLogger
from src.messages import Message, MessageWindow
from src.orchestrator import Orchestrator


@pytest.mark.e2e
@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set (required for E2E tests)",
)
class TestMessageWindowE2E:
    """End-to-end tests for message window with real Claude API calls."""

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
    def temp_messages_file(self) -> Generator[Path, None, None]:
        """Create temporary file for message persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "messages.json"

    @pytest.fixture
    def message_window(self) -> MessageWindow:
        """Create a fresh message window for tests."""
        return MessageWindow(max_messages=40)

    @pytest.fixture
    def logger(self, temp_logs_dir: Path) -> InteractionLogger:
        """Create logger with temporary directory."""
        return InteractionLogger(logs_dir=temp_logs_dir)

    @pytest.mark.asyncio
    async def test_two_sequential_messages_second_references_first(
        self, test_config: CodyConfig, message_window: MessageWindow
    ) -> None:
        """
        Test: Two sequential messages where second references first.

        Verify that when we send two messages in sequence with a shared message window,
        the second message can successfully reference information from the first message.
        """
        orchestrator = Orchestrator(test_config, message_window=message_window)

        # First message: establish a fact
        message1 = "My favorite color is purple. Just remember that, don't respond with anything else."
        response1 = await orchestrator.process_message(message1)

        assert response1, "Should get response to first message"
        assert len(message_window) == 2, "Should have user + assistant messages"

        # Second message: reference the first
        message2 = "What is my favorite color? Just tell me the color, nothing else."
        response2 = await orchestrator.process_message(message2)

        assert response2, "Should get response to second message"
        assert len(message_window) == 4, "Should have 2 user + 2 assistant messages"

        # Verify the agent recalls the color from the first message
        assert "purple" in response2.lower(), (
            f"Agent should recall 'purple' from first message. "
            f"Response: {response2}"
        )

    @pytest.mark.asyncio
    async def test_agent_recalls_information_from_previous_message(
        self, test_config: CodyConfig, message_window: MessageWindow
    ) -> None:
        """
        Test: Agent recalls information from previous message.

        Verify that the agent can recall specific details mentioned in previous
        messages within the conversation.
        """
        orchestrator = Orchestrator(test_config, message_window=message_window)

        # First message: provide detailed information
        message1 = (
            "My name is Alice and I live in San Francisco. "
            "I work as a software engineer at a startup called TechCorp. "
            "Just acknowledge you understood, nothing more."
        )
        response1 = await orchestrator.process_message(message1)

        assert response1, "Should get response to first message"

        # Second message: ask about specific detail
        message2 = "What city do I live in? Just tell me the city name."
        response2 = await orchestrator.process_message(message2)

        assert "san francisco" in response2.lower(), (
            f"Agent should recall 'San Francisco' from first message. "
            f"Response: {response2}"
        )

        # Third message: ask about another detail
        message3 = "What company do I work for? Just tell me the company name."
        response3 = await orchestrator.process_message(message3)

        assert "techcorp" in response3.lower(), (
            f"Agent should recall 'TechCorp' from first message. "
            f"Response: {response3}"
        )

    @pytest.mark.asyncio
    async def test_message_window_persists_between_cli_invocations(
        self, test_config: CodyConfig, temp_messages_file: Path
    ) -> None:
        """
        Test: Message window persists between CLI invocations.

        Verify that when we save the message window to disk and load it in a new
        session, the conversation context is maintained.
        """
        # First session: establish context and persist
        window1 = MessageWindow()
        orchestrator1 = Orchestrator(test_config, message_window=window1)

        message1 = "Remember this number: 42. Just acknowledge."
        response1 = await orchestrator1.process_message(message1)

        assert response1, "Should get response"
        assert len(window1) == 2, "Should have 2 messages"

        # Persist the window
        window1.persist(temp_messages_file)

        # Verify file was created
        assert temp_messages_file.exists(), "Messages file should exist"

        # Second session: load window and verify context is maintained
        window2 = MessageWindow()
        window2.load(temp_messages_file)

        assert len(window2) == 2, "Loaded window should have 2 messages"

        orchestrator2 = Orchestrator(test_config, message_window=window2)

        message2 = "What number did I ask you to remember? Just the number."
        response2 = await orchestrator2.process_message(message2)

        assert "42" in response2, (
            f"Agent should recall '42' from previous session. "
            f"Response: {response2}"
        )

    @pytest.mark.asyncio
    async def test_window_overflow_drops_oldest_messages(
        self, test_config: CodyConfig
    ) -> None:
        """
        Test: Window overflow drops oldest messages.

        Verify that when the message window reaches its maximum size, it correctly
        drops the oldest messages and maintains only the most recent ones.
        """
        # Create a small window for testing overflow
        window = MessageWindow(max_messages=6)  # 3 exchanges (user + assistant)
        orchestrator = Orchestrator(test_config, message_window=window)

        # Send 4 messages to cause overflow
        messages = [
            "My first favorite number is 1. Just acknowledge.",
            "My second favorite number is 2. Just acknowledge.",
            "My third favorite number is 3. Just acknowledge.",
            "My fourth favorite number is 4. Just acknowledge.",
        ]

        for msg in messages:
            response = await orchestrator.process_message(msg)
            assert response, f"Should get response to: {msg}"

        # Window should have max_messages (6) messages
        # That's 3 most recent exchanges
        assert len(window) == 6, "Window should be at max capacity"

        # Verify oldest messages were dropped
        # Should NOT contain first exchange
        context = window.get_context()
        all_content = " ".join([msg["content"] for msg in context])

        # First exchange should be dropped
        assert "first favorite number is 1" not in all_content.lower(), (
            "Oldest message should have been dropped"
        )

        # Most recent exchanges should be kept
        assert "second favorite number is 2" in all_content.lower(), (
            "Second exchange should be kept"
        )
        assert "third favorite number is 3" in all_content.lower(), (
            "Third exchange should be kept"
        )
        assert "fourth favorite number is 4" in all_content.lower(), (
            "Fourth exchange should be kept"
        )

    @pytest.mark.asyncio
    async def test_interactions_logged_with_full_context(
        self,
        test_config: CodyConfig,
        message_window: MessageWindow,
        temp_logs_dir: Path,
        logger: InteractionLogger,
    ) -> None:
        """
        Test: Verify all interactions are logged with full context in JSONL.

        When using message window, all interactions should be logged to JSONL
        with the full conversation context included.
        """
        orchestrator = Orchestrator(test_config, message_window=message_window)

        # Send two messages to build context
        message1 = "My favorite animal is a cat."
        response1 = await orchestrator.process_message(message1)

        message2 = "What is my favorite animal?"
        response2 = await orchestrator.process_message(message2)

        # Get the context from message window
        full_context = message_window.get_context()

        # Manually log the second interaction (with full context)
        from src.temporal import TemporalContext

        temporal = TemporalContext(test_config.user_timezone)
        temporal_context = temporal.to_context_string()
        system_prompt = f"""You are {test_config.assistant_name}, a personal AI assistant.

{temporal_context}

You help users with tasks, remember context across conversations, and provide
thoughtful, accurate assistance. Be concise and helpful."""

        request_id = logger.log_interaction(
            system_prompt=system_prompt,
            user_message=message2,
            response=response2,
            duration_ms=1000.0,
            full_context=full_context,  # Include full context
        )

        # Verify log file was created
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_logs_dir / f"interactions-{today}.jsonl"

        assert log_file.exists(), "Log file should exist"

        # Read and verify log entries
        with open(log_file) as f:
            lines = f.readlines()

        assert len(lines) == 2, "Should have 2 log entries (intent + result)"

        # Parse intent entry
        intent_entry = json.loads(lines[0])

        # Verify full context is included in the log
        assert "full_context" in intent_entry, "Intent should include full_context"
        assert intent_entry["full_context"] is not None, "full_context should not be None"
        assert isinstance(intent_entry["full_context"], list), "full_context should be a list"
        assert len(intent_entry["full_context"]) == 4, (
            "full_context should have all 4 messages (2 exchanges)"
        )

        # Verify the first message is in the context
        context_content = [msg["content"] for msg in intent_entry["full_context"]]
        assert message1 in context_content, "First message should be in context"

    @pytest.mark.asyncio
    async def test_parse_logs_verify_context_includes_previous_messages(
        self,
        test_config: CodyConfig,
        message_window: MessageWindow,
        temp_logs_dir: Path,
        logger: InteractionLogger,
    ) -> None:
        """
        Test: Parse logs to verify context includes previous messages.

        Use the log parser to read back logs and verify that the full_context
        field correctly includes previous messages from the conversation.
        """
        orchestrator = Orchestrator(test_config, message_window=message_window)

        # Build a conversation
        messages = [
            ("My lucky number is 7.", None),
            ("My lucky color is green.", None),
            ("What is my lucky number?", None),
        ]

        responses = []
        for msg, _ in messages:
            response = await orchestrator.process_message(msg)
            responses.append(response)

        # Log the final interaction with full context
        from src.temporal import TemporalContext

        temporal = TemporalContext(test_config.user_timezone)
        temporal_context = temporal.to_context_string()
        system_prompt = f"""You are {test_config.assistant_name}, a personal AI assistant.

{temporal_context}

You help users with tasks, remember context across conversations, and provide
thoughtful, accurate assistance. Be concise and helpful."""

        full_context = message_window.get_context()

        request_id = logger.log_interaction(
            system_prompt=system_prompt,
            user_message=messages[-1][0],
            response=responses[-1],
            duration_ms=1000.0,
            full_context=full_context,
        )

        # Parse logs using LogParser
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_logs_dir / f"interactions-{today}.jsonl"

        parser = LogParser(log_file)
        entries = parser.parse_logs()

        # Group by request_id
        grouped = parser.group_by_request_id(entries)

        assert request_id in grouped, "Should find the request in logs"

        # Get the intent entry
        intent = grouped[request_id]["intent"]

        assert intent is not None, "Should have intent entry"
        assert "full_context" in intent, "Intent should have full_context"
        assert intent["full_context"] is not None, "full_context should not be None"

        # Verify all previous messages are in context
        context_messages = intent["full_context"]
        assert len(context_messages) == 6, (
            "Should have 6 messages (3 user + 3 assistant)"
        )

        # Extract content from context
        context_content = [msg["content"] for msg in context_messages]

        # Verify each original message is in the context
        assert "My lucky number is 7." in context_content
        assert "My lucky color is green." in context_content
        assert "What is my lucky number?" in context_content

        # Verify the agent's response correctly used context
        result = grouped[request_id]["result"]
        assert "7" in result["response"], (
            f"Agent should respond with '7'. Response: {result['response']}"
        )

    @pytest.mark.asyncio
    async def test_cli_process_message_with_message_window(
        self, test_config: CodyConfig, message_window: MessageWindow
    ) -> None:
        """
        Test: CLI process_message function works with message window.

        Verify that the CLI's process_message function correctly uses the
        message window when provided.
        """
        # First message
        message1 = "My favorite food is pizza."
        response1, exit_code1 = await process_message(
            message=message1,
            config=test_config,
            verbose=False,
            message_window=message_window,
        )

        assert exit_code1 == 0, f"First message should succeed: {response1}"
        assert response1, "Should get response"
        assert len(message_window) == 2, "Should have 2 messages after first exchange"

        # Second message that references first
        message2 = "What is my favorite food?"
        response2, exit_code2 = await process_message(
            message=message2,
            config=test_config,
            verbose=False,
            message_window=message_window,
        )

        assert exit_code2 == 0, f"Second message should succeed: {response2}"
        assert "pizza" in response2.lower(), (
            f"Agent should recall 'pizza' from context. Response: {response2}"
        )
        assert len(message_window) == 4, "Should have 4 messages after second exchange"

    @pytest.mark.asyncio
    async def test_multiple_exchanges_maintain_coherent_context(
        self, test_config: CodyConfig, message_window: MessageWindow
    ) -> None:
        """
        Test: Multiple exchanges maintain coherent conversation context.

        Verify that over multiple message exchanges, the context remains coherent
        and the agent can recall information from several messages ago.
        """
        orchestrator = Orchestrator(test_config, message_window=message_window)

        # Build a longer conversation
        exchanges = [
            ("I have a dog named Max.", "Max"),
            ("I also have a cat named Luna.", "Luna"),
            ("Max is 5 years old.", "5"),
            ("Luna is 3 years old.", "3"),
        ]

        # Send all setup messages
        for msg, _ in exchanges:
            response = await orchestrator.process_message(msg)
            assert response, f"Should get response to: {msg}"

        # Now ask questions that require recalling earlier context
        question1 = "What is my dog's name?"
        response1 = await orchestrator.process_message(question1)
        assert "max" in response1.lower(), f"Should recall dog's name. Response: {response1}"

        question2 = "How old is my cat?"
        response2 = await orchestrator.process_message(question2)
        assert "3" in response2, f"Should recall cat's age. Response: {response2}"

        # Verify the window has all messages
        assert len(message_window) == 12, "Should have 6 exchanges (12 messages)"
