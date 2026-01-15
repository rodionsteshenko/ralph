"""
Message data structures for conversation history tracking.

Provides Message dataclass and MessageWindow for managing sliding window of conversation history.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class Message:
    """
    A single message in a conversation.

    Attributes:
        role: Who sent the message ("user" or "assistant")
        content: The message content
        timestamp: When the message was created (ISO 8601 format)
        timezone: User's timezone (e.g., "America/Los_Angeles")
    """

    role: Literal["user", "assistant"]
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    timezone: str = "UTC"

    def to_dict(self) -> dict[str, str]:
        """
        Convert message to dictionary format.

        Returns:
            Dictionary representation of the message
        """
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "timezone": self.timezone,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "Message":
        """
        Create message from dictionary.

        Args:
            data: Dictionary with message fields

        Returns:
            Message instance
        """
        return cls(
            role=data["role"],  # type: ignore[arg-type]
            content=data["content"],
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            timezone=data.get("timezone", "UTC"),
        )


class MessageWindow:
    """
    Sliding window of conversation messages.

    Maintains a fixed-size window of recent messages, automatically removing
    oldest messages when the window is full.

    Attributes:
        max_messages: Maximum number of messages to keep (default: 40)
        messages: List of messages in the window
    """

    def __init__(self, max_messages: int = 40) -> None:
        """
        Initialize message window.

        Args:
            max_messages: Maximum number of messages to keep (default: 40)

        Raises:
            ValueError: If max_messages is not positive
        """
        if max_messages <= 0:
            raise ValueError(f"max_messages must be positive, got: {max_messages}")

        self.max_messages = max_messages
        self.messages: list[Message] = []

    def add(self, message: Message) -> None:
        """
        Add a message to the window.

        If the window is full, removes the oldest message first.

        Args:
            message: Message to add
        """
        self.messages.append(message)

        # Remove oldest message if we exceed max_messages
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

    def get_context(self) -> list[dict[str, str]]:
        """
        Get all messages in the window as a list of dictionaries.

        Returns:
            List of message dictionaries in chronological order
        """
        return [msg.to_dict() for msg in self.messages]

    def clear(self) -> None:
        """
        Clear all messages from the window.
        """
        self.messages.clear()

    def __len__(self) -> int:
        """
        Get the number of messages in the window.

        Returns:
            Number of messages
        """
        return len(self.messages)
