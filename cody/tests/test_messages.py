"""
Unit tests for message data structures.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import pytest

from src.messages import Message, MessageWindow


@pytest.mark.unit
def test_message_creation_with_defaults() -> None:
    """Test creating a message with default timestamp and timezone."""
    msg = Message(role="user", content="Hello")

    assert msg.role == "user"
    assert msg.content == "Hello"
    assert msg.timestamp is not None
    assert msg.timezone == "UTC"

    # Timestamp should be a valid ISO 8601 format
    datetime.fromisoformat(msg.timestamp)


@pytest.mark.unit
def test_message_creation_with_custom_values() -> None:
    """Test creating a message with custom timestamp and timezone."""
    custom_timestamp = "2024-01-15T10:30:00"
    msg = Message(
        role="assistant",
        content="Hi there!",
        timestamp=custom_timestamp,
        timezone="America/Los_Angeles",
    )

    assert msg.role == "assistant"
    assert msg.content == "Hi there!"
    assert msg.timestamp == custom_timestamp
    assert msg.timezone == "America/Los_Angeles"


@pytest.mark.unit
def test_message_to_dict() -> None:
    """Test converting message to dictionary."""
    msg = Message(
        role="user",
        content="Test message",
        timestamp="2024-01-15T10:30:00",
        timezone="America/New_York",
    )

    msg_dict = msg.to_dict()

    assert msg_dict == {
        "role": "user",
        "content": "Test message",
        "timestamp": "2024-01-15T10:30:00",
        "timezone": "America/New_York",
    }


@pytest.mark.unit
def test_message_from_dict() -> None:
    """Test creating message from dictionary."""
    msg_dict = {
        "role": "assistant",
        "content": "Response message",
        "timestamp": "2024-01-15T11:00:00",
        "timezone": "UTC",
    }

    msg = Message.from_dict(msg_dict)

    assert msg.role == "assistant"
    assert msg.content == "Response message"
    assert msg.timestamp == "2024-01-15T11:00:00"
    assert msg.timezone == "UTC"


@pytest.mark.unit
def test_message_from_dict_with_defaults() -> None:
    """Test creating message from dictionary with missing optional fields."""
    msg_dict = {
        "role": "user",
        "content": "Minimal message",
    }

    msg = Message.from_dict(msg_dict)

    assert msg.role == "user"
    assert msg.content == "Minimal message"
    # Should have defaults
    assert msg.timestamp is not None
    assert msg.timezone == "UTC"


@pytest.mark.unit
def test_message_window_creation() -> None:
    """Test creating a message window with default size."""
    window = MessageWindow()

    assert window.max_messages == 40
    assert len(window) == 0
    assert window.messages == []


@pytest.mark.unit
def test_message_window_creation_with_custom_size() -> None:
    """Test creating a message window with custom size."""
    window = MessageWindow(max_messages=10)

    assert window.max_messages == 10
    assert len(window) == 0


@pytest.mark.unit
def test_message_window_invalid_size() -> None:
    """Test that creating a window with invalid size raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        MessageWindow(max_messages=0)

    assert "max_messages must be positive" in str(exc_info.value)

    with pytest.raises(ValueError) as exc_info:
        MessageWindow(max_messages=-5)

    assert "max_messages must be positive" in str(exc_info.value)


@pytest.mark.unit
def test_add_message_to_window() -> None:
    """Test adding a message to the window."""
    window = MessageWindow()
    msg = Message(role="user", content="Hello")

    window.add(msg)

    assert len(window) == 1
    assert window.messages[0] == msg


@pytest.mark.unit
def test_add_multiple_messages() -> None:
    """Test adding multiple messages to the window."""
    window = MessageWindow()

    msg1 = Message(role="user", content="First")
    msg2 = Message(role="assistant", content="Second")
    msg3 = Message(role="user", content="Third")

    window.add(msg1)
    window.add(msg2)
    window.add(msg3)

    assert len(window) == 3
    assert window.messages[0] == msg1
    assert window.messages[1] == msg2
    assert window.messages[2] == msg3


@pytest.mark.unit
def test_window_overflow_removes_oldest() -> None:
    """Test that window removes oldest message when full."""
    window = MessageWindow(max_messages=3)

    msg1 = Message(role="user", content="First")
    msg2 = Message(role="assistant", content="Second")
    msg3 = Message(role="user", content="Third")
    msg4 = Message(role="assistant", content="Fourth")

    window.add(msg1)
    window.add(msg2)
    window.add(msg3)
    # Window is full (3 messages)

    window.add(msg4)
    # Should remove msg1 (oldest)

    assert len(window) == 3
    assert window.messages[0] == msg2
    assert window.messages[1] == msg3
    assert window.messages[2] == msg4


@pytest.mark.unit
def test_window_overflow_multiple_times() -> None:
    """Test window behavior with multiple overflows."""
    window = MessageWindow(max_messages=2)

    messages = [
        Message(role="user", content=f"Message {i}")
        for i in range(5)
    ]

    for msg in messages:
        window.add(msg)

    # Should only keep last 2 messages
    assert len(window) == 2
    assert window.messages[0] == messages[3]
    assert window.messages[1] == messages[4]


@pytest.mark.unit
def test_get_context_empty_window() -> None:
    """Test getting context from empty window."""
    window = MessageWindow()

    context = window.get_context()

    assert context == []


@pytest.mark.unit
def test_get_context_with_messages() -> None:
    """Test getting context with messages."""
    window = MessageWindow()

    msg1 = Message(
        role="user",
        content="Hello",
        timestamp="2024-01-15T10:00:00",
        timezone="UTC"
    )
    msg2 = Message(
        role="assistant",
        content="Hi!",
        timestamp="2024-01-15T10:00:01",
        timezone="UTC"
    )

    window.add(msg1)
    window.add(msg2)

    context = window.get_context()

    assert len(context) == 2
    assert context[0] == {
        "role": "user",
        "content": "Hello",
        "timestamp": "2024-01-15T10:00:00",
        "timezone": "UTC",
    }
    assert context[1] == {
        "role": "assistant",
        "content": "Hi!",
        "timestamp": "2024-01-15T10:00:01",
        "timezone": "UTC",
    }


@pytest.mark.unit
def test_get_context_returns_chronological_order() -> None:
    """Test that get_context returns messages in chronological order."""
    window = MessageWindow()

    for i in range(5):
        msg = Message(role="user", content=f"Message {i}")
        window.add(msg)

    context = window.get_context()

    assert len(context) == 5
    for i in range(5):
        assert context[i]["content"] == f"Message {i}"


@pytest.mark.unit
def test_clear_window() -> None:
    """Test clearing all messages from window."""
    window = MessageWindow()

    # Add some messages
    window.add(Message(role="user", content="First"))
    window.add(Message(role="assistant", content="Second"))
    window.add(Message(role="user", content="Third"))

    assert len(window) == 3

    # Clear window
    window.clear()

    assert len(window) == 0
    assert window.messages == []
    assert window.get_context() == []


@pytest.mark.unit
def test_clear_empty_window() -> None:
    """Test clearing an already empty window."""
    window = MessageWindow()

    assert len(window) == 0

    window.clear()

    assert len(window) == 0


@pytest.mark.unit
def test_window_len_method() -> None:
    """Test __len__ method of MessageWindow."""
    window = MessageWindow()

    assert len(window) == 0

    window.add(Message(role="user", content="Test"))
    assert len(window) == 1

    window.add(Message(role="assistant", content="Response"))
    assert len(window) == 2

    window.clear()
    assert len(window) == 0


@pytest.mark.unit
def test_window_maintains_max_size_after_many_additions() -> None:
    """Test that window consistently maintains max size."""
    window = MessageWindow(max_messages=5)

    # Add 20 messages
    for i in range(20):
        msg = Message(role="user", content=f"Message {i}")
        window.add(msg)

    # Should only keep last 5
    assert len(window) == 5

    # Verify content of last 5 messages
    for i in range(5):
        assert window.messages[i].content == f"Message {15 + i}"


@pytest.mark.unit
def test_message_window_edge_case_single_message_capacity() -> None:
    """Test window with capacity of 1."""
    window = MessageWindow(max_messages=1)

    msg1 = Message(role="user", content="First")
    msg2 = Message(role="assistant", content="Second")

    window.add(msg1)
    assert len(window) == 1
    assert window.messages[0] == msg1

    window.add(msg2)
    assert len(window) == 1
    assert window.messages[0] == msg2  # First message removed


@pytest.mark.unit
def test_get_context_does_not_modify_window() -> None:
    """Test that get_context() doesn't modify the window."""
    window = MessageWindow()

    msg = Message(role="user", content="Test")
    window.add(msg)

    context1 = window.get_context()
    context2 = window.get_context()

    assert len(window) == 1
    assert context1 == context2


@pytest.mark.unit
def test_modifying_context_does_not_affect_window() -> None:
    """Test that modifying returned context doesn't affect window."""
    window = MessageWindow()

    msg = Message(role="user", content="Original")
    window.add(msg)

    context = window.get_context()
    context[0]["content"] = "Modified"

    # Window should still have original content
    assert window.messages[0].content == "Original"


# Persistence tests


@pytest.mark.unit
def test_persist_empty_window(tmp_path: Path) -> None:
    """Test persisting an empty message window."""
    window = MessageWindow()
    persist_path = tmp_path / "messages.json"

    window.persist(persist_path)

    # File should exist
    assert persist_path.exists()

    # Check content
    with open(persist_path) as f:
        data = json.load(f)

    assert data == {"max_messages": 40, "messages": []}


@pytest.mark.unit
def test_persist_window_with_messages(tmp_path: Path) -> None:
    """Test persisting a window with messages."""
    window = MessageWindow(max_messages=10)
    msg1 = Message(
        role="user",
        content="Hello",
        timestamp="2024-01-15T10:00:00",
        timezone="America/Los_Angeles",
    )
    msg2 = Message(
        role="assistant", content="Hi!", timestamp="2024-01-15T10:00:01", timezone="UTC"
    )

    window.add(msg1)
    window.add(msg2)

    persist_path = tmp_path / "messages.json"
    window.persist(persist_path)

    # Verify file content
    with open(persist_path) as f:
        data = json.load(f)

    assert data["max_messages"] == 10
    assert len(data["messages"]) == 2
    assert data["messages"][0] == {
        "role": "user",
        "content": "Hello",
        "timestamp": "2024-01-15T10:00:00",
        "timezone": "America/Los_Angeles",
    }
    assert data["messages"][1] == {
        "role": "assistant",
        "content": "Hi!",
        "timestamp": "2024-01-15T10:00:01",
        "timezone": "UTC",
    }


@pytest.mark.unit
def test_persist_creates_directory(tmp_path: Path) -> None:
    """Test that persist() creates parent directories if needed."""
    persist_path = tmp_path / "nested" / "dir" / "messages.json"

    window = MessageWindow()
    window.add(Message(role="user", content="Test"))

    # Directory doesn't exist yet
    assert not persist_path.parent.exists()

    window.persist(persist_path)

    # Directory should be created
    assert persist_path.parent.exists()
    assert persist_path.exists()


@pytest.mark.unit
def test_load_missing_file(tmp_path: Path) -> None:
    """Test loading from a non-existent file starts with empty window."""
    window = MessageWindow()
    window.add(Message(role="user", content="Existing message"))

    # Load from non-existent file
    persist_path = tmp_path / "nonexistent.json"
    window.load(persist_path)

    # Window should be empty
    assert len(window) == 0
    assert window.messages == []


@pytest.mark.unit
def test_load_valid_file(tmp_path: Path) -> None:
    """Test loading messages from a valid JSON file."""
    persist_path = tmp_path / "messages.json"

    # Create a valid JSON file
    data = {
        "max_messages": 15,
        "messages": [
            {
                "role": "user",
                "content": "Hello",
                "timestamp": "2024-01-15T10:00:00",
                "timezone": "UTC",
            },
            {
                "role": "assistant",
                "content": "Hi!",
                "timestamp": "2024-01-15T10:00:01",
                "timezone": "America/New_York",
            },
        ],
    }

    with open(persist_path, "w") as f:
        json.dump(data, f)

    # Load into window
    window = MessageWindow()
    window.load(persist_path)

    assert window.max_messages == 15
    assert len(window) == 2
    assert window.messages[0].role == "user"
    assert window.messages[0].content == "Hello"
    assert window.messages[0].timestamp == "2024-01-15T10:00:00"
    assert window.messages[0].timezone == "UTC"
    assert window.messages[1].role == "assistant"
    assert window.messages[1].content == "Hi!"


@pytest.mark.unit
def test_load_corrupted_json(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test loading from a corrupted JSON file logs warning and starts empty."""
    persist_path = tmp_path / "corrupted.json"

    # Create corrupted JSON file
    with open(persist_path, "w") as f:
        f.write("{invalid json content")

    window = MessageWindow()
    window.add(Message(role="user", content="Existing"))

    # Load corrupted file
    with caplog.at_level(logging.WARNING):
        window.load(persist_path)

    # Should start with empty window
    assert len(window) == 0
    assert window.messages == []

    # Should log a warning
    assert "Failed to load messages" in caplog.text
    assert str(persist_path) in caplog.text


@pytest.mark.unit
def test_load_invalid_structure_not_dict(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test loading from file with invalid structure (not a dict)."""
    persist_path = tmp_path / "invalid.json"

    # Create JSON with array instead of object
    with open(persist_path, "w") as f:
        json.dump(["not", "a", "dict"], f)

    window = MessageWindow()

    with caplog.at_level(logging.WARNING):
        window.load(persist_path)

    # Should start empty
    assert len(window) == 0
    assert "Failed to load messages" in caplog.text


@pytest.mark.unit
def test_load_invalid_structure_missing_messages(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Test loading from file missing 'messages' field."""
    persist_path = tmp_path / "invalid.json"

    # Create JSON without messages field
    with open(persist_path, "w") as f:
        json.dump({"max_messages": 10}, f)

    window = MessageWindow()

    with caplog.at_level(logging.WARNING):
        window.load(persist_path)

    assert len(window) == 0
    assert "Failed to load messages" in caplog.text


@pytest.mark.unit
def test_load_invalid_messages_not_list(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test loading from file where 'messages' is not a list."""
    persist_path = tmp_path / "invalid.json"

    with open(persist_path, "w") as f:
        json.dump({"max_messages": 10, "messages": "not a list"}, f)

    window = MessageWindow()

    with caplog.at_level(logging.WARNING):
        window.load(persist_path)

    assert len(window) == 0
    assert "Failed to load messages" in caplog.text


@pytest.mark.unit
def test_persist_and_load_round_trip(tmp_path: Path) -> None:
    """Test that persist() and load() work together correctly."""
    persist_path = tmp_path / "messages.json"

    # Create window with messages
    window1 = MessageWindow(max_messages=25)
    msg1 = Message(role="user", content="First message", timezone="America/Los_Angeles")
    msg2 = Message(role="assistant", content="Second message", timezone="UTC")
    msg3 = Message(role="user", content="Third message", timezone="America/New_York")

    window1.add(msg1)
    window1.add(msg2)
    window1.add(msg3)

    # Persist to file
    window1.persist(persist_path)

    # Load into new window
    window2 = MessageWindow()
    window2.load(persist_path)

    # Should match exactly
    assert window2.max_messages == 25
    assert len(window2) == 3
    assert window2.messages[0].role == "user"
    assert window2.messages[0].content == "First message"
    assert window2.messages[0].timezone == "America/Los_Angeles"
    assert window2.messages[1].role == "assistant"
    assert window2.messages[1].content == "Second message"
    assert window2.messages[2].role == "user"
    assert window2.messages[2].content == "Third message"


@pytest.mark.unit
def test_persist_and_load_preserves_order(tmp_path: Path) -> None:
    """Test that message order is preserved across persist/load."""
    persist_path = tmp_path / "messages.json"

    window1 = MessageWindow()
    for i in range(10):
        window1.add(Message(role="user", content=f"Message {i}"))

    window1.persist(persist_path)

    window2 = MessageWindow()
    window2.load(persist_path)

    assert len(window2) == 10
    for i in range(10):
        assert window2.messages[i].content == f"Message {i}"


@pytest.mark.unit
def test_load_without_max_messages_uses_default(tmp_path: Path) -> None:
    """Test loading from file without max_messages field uses current value."""
    persist_path = tmp_path / "messages.json"

    # Create JSON without max_messages
    data = {
        "messages": [
            {
                "role": "user",
                "content": "Test",
                "timestamp": "2024-01-15T10:00:00",
                "timezone": "UTC",
            }
        ]
    }

    with open(persist_path, "w") as f:
        json.dump(data, f)

    window = MessageWindow(max_messages=50)
    window.load(persist_path)

    # Should keep the original max_messages
    assert window.max_messages == 50
    assert len(window) == 1


@pytest.mark.unit
def test_load_with_invalid_max_messages_keeps_current(tmp_path: Path) -> None:
    """Test loading with invalid max_messages doesn't change current value."""
    persist_path = tmp_path / "messages.json"

    # Create JSON with invalid max_messages
    data = {"max_messages": -5, "messages": []}

    with open(persist_path, "w") as f:
        json.dump(data, f)

    window = MessageWindow(max_messages=30)
    window.load(persist_path)

    # Should keep original max_messages
    assert window.max_messages == 30


@pytest.mark.unit
def test_persist_overwrites_existing_file(tmp_path: Path) -> None:
    """Test that persist() overwrites existing file."""
    persist_path = tmp_path / "messages.json"

    # Create first window and persist
    window1 = MessageWindow()
    window1.add(Message(role="user", content="First"))
    window1.persist(persist_path)

    # Create second window with different content and persist
    window2 = MessageWindow()
    window2.add(Message(role="assistant", content="Second"))
    window2.add(Message(role="user", content="Third"))
    window2.persist(persist_path)

    # Load and verify it has the second window's content
    window3 = MessageWindow()
    window3.load(persist_path)

    assert len(window3) == 2
    assert window3.messages[0].content == "Second"
    assert window3.messages[1].content == "Third"
