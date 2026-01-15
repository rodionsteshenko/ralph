"""
Unit tests for message data structures.
"""

from datetime import datetime

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
