"""
Message data structures for conversation history tracking.

Provides Message dataclass and MessageWindow for managing sliding window of conversation history.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)


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

    def persist(self, path: Path) -> None:
        """
        Save messages to a JSON file.

        Args:
            path: Path to save messages (e.g., .cody/messages.json)
        """
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Convert messages to dict format
        data = {
            "max_messages": self.max_messages,
            "messages": [msg.to_dict() for msg in self.messages],
        }

        # Write to file
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, path: Path) -> None:
        """
        Load messages from a JSON file.

        If the file doesn't exist, starts with an empty window.
        If the file is corrupted, starts with an empty window and logs a warning.

        Args:
            path: Path to load messages from (e.g., .cody/messages.json)
        """
        # If file doesn't exist, start empty
        if not path.exists():
            self.messages = []
            return

        # Try to load and parse JSON
        try:
            with open(path) as f:
                data = json.load(f)

            # Validate data structure
            if not isinstance(data, dict):
                raise ValueError("Invalid JSON structure: expected object")

            if "messages" not in data:
                raise ValueError("Invalid JSON structure: missing 'messages' field")

            # Update max_messages if provided
            if "max_messages" in data:
                max_messages = data["max_messages"]
                if isinstance(max_messages, int) and max_messages > 0:
                    self.max_messages = max_messages

            # Load messages
            messages_data = data["messages"]
            if not isinstance(messages_data, list):
                raise ValueError("Invalid JSON structure: 'messages' must be a list")

            self.messages = [Message.from_dict(msg_dict) for msg_dict in messages_data]

        except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
            # Log warning and start with empty window
            logger.warning(
                "Failed to load messages from %s: %s. Starting with empty window.",
                path,
                str(e),
            )
            self.messages = []
