"""
Interaction logging infrastructure for Claude conversations.

Logs all Claude API interactions to append-only JSONL files with automatic date-based rotation.
Each interaction gets a unique request_id for tracing and debugging.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


class InteractionLoggerError(Exception):
    """Raised when interaction logger encounters an error."""

    pass


class InteractionLogger:
    """
    Logs Claude API interactions to date-rotated JSONL files.

    Each log entry contains:
    - timestamp: ISO format timestamp
    - request_id: UUID for tracing
    - system_prompt: System prompt sent to Claude
    - user_message: User message sent to Claude
    - full_context: Complete context (if any)
    - response: Claude's response
    - tools_called: List of tools used (if any)
    - duration_ms: Time taken in milliseconds
    - error: Error message (if any)

    Logs are stored in .cody/logs/interactions-YYYY-MM-DD.jsonl
    """

    def __init__(self, logs_dir: Path | None = None) -> None:
        """
        Initialize interaction logger.

        Args:
            logs_dir: Directory for log files. Defaults to .cody/logs
        """
        if logs_dir is None:
            logs_dir = Path.cwd() / ".cody" / "logs"

        self.logs_dir = logs_dir
        self._ensure_logs_directory()

    def _ensure_logs_directory(self) -> None:
        """Create logs directory if it doesn't exist."""
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def _get_log_file_path(self, date: datetime | None = None) -> Path:
        """
        Get log file path for a specific date.

        Args:
            date: Date for log file. Defaults to today.

        Returns:
            Path to log file (e.g., .cody/logs/interactions-2026-01-14.jsonl)
        """
        if date is None:
            date = datetime.now()

        filename = f"interactions-{date.strftime('%Y-%m-%d')}.jsonl"
        return self.logs_dir / filename

    def log_intent(
        self,
        request_id: str,
        system_prompt: str,
        user_message: str,
        full_context: str | None = None,
    ) -> None:
        """
        Log the INTENT before sending to Claude.

        This logs what we're ABOUT to send, capturing the request before it's sent.

        Args:
            request_id: Unique request ID (UUID) for this interaction
            system_prompt: System prompt being sent
            user_message: User message being sent
            full_context: Full context string (if any)
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "stage": "intent",
            "system_prompt": system_prompt,
            "user_message": user_message,
            "full_context": full_context,
        }

        self._write_log_entry(log_entry)

    def log_result(
        self,
        request_id: str,
        response: str,
        duration_ms: float,
        tools_called: list[str] | None = None,
        error: str | None = None,
    ) -> None:
        """
        Log the RESULT after receiving from Claude.

        This logs what we RECEIVED, capturing the response and metadata.

        Args:
            request_id: Same request ID used in log_intent
            response: Response text from Claude
            duration_ms: Duration in milliseconds
            tools_called: List of tool names called (if any)
            error: Error message (if any)
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "stage": "result",
            "response": response,
            "duration_ms": duration_ms,
            "tools_called": tools_called or [],
            "error": error,
        }

        self._write_log_entry(log_entry)

    def log_interaction(
        self,
        system_prompt: str,
        user_message: str,
        response: str,
        duration_ms: float,
        request_id: str | None = None,
        full_context: str | None = None,
        tools_called: list[str] | None = None,
        error: str | None = None,
    ) -> str:
        """
        Log a complete interaction (convenience method).

        This is a convenience method that logs both intent and result in a single call.
        For more granular logging, use log_intent() and log_result() separately.

        Args:
            system_prompt: System prompt sent to Claude
            user_message: User message sent to Claude
            response: Response from Claude
            duration_ms: Duration in milliseconds
            request_id: Unique request ID (auto-generated if not provided)
            full_context: Full context string (if any)
            tools_called: List of tool names called (if any)
            error: Error message (if any)

        Returns:
            The request_id used for this interaction
        """
        if request_id is None:
            request_id = str(uuid.uuid4())

        # Log intent (what we sent)
        self.log_intent(request_id, system_prompt, user_message, full_context)

        # Log result (what we got back)
        self.log_result(request_id, response, duration_ms, tools_called, error)

        return request_id

    def generate_request_id(self) -> str:
        """
        Generate a unique request ID.

        Returns:
            UUID string for tracking this request
        """
        return str(uuid.uuid4())

    def _write_log_entry(self, entry: dict[str, Any]) -> None:
        """
        Write a log entry to the appropriate date-rotated file.

        Args:
            entry: Log entry dictionary to write

        Raises:
            InteractionLoggerError: If writing fails
        """
        try:
            log_file = self._get_log_file_path()

            # Append to log file (create if doesn't exist)
            with open(log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")

        except Exception as e:
            raise InteractionLoggerError(f"Failed to write log entry: {e}") from e

    def read_logs(
        self, date: datetime | None = None, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Read log entries from a specific date.

        Args:
            date: Date to read logs from. Defaults to today.
            limit: Maximum number of entries to return. None = all entries.

        Returns:
            List of log entry dictionaries

        Raises:
            InteractionLoggerError: If reading fails
        """
        try:
            log_file = self._get_log_file_path(date)

            if not log_file.exists():
                return []

            entries: list[dict[str, Any]] = []
            with open(log_file) as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))

                        if limit is not None and len(entries) >= limit:
                            break

            return entries

        except Exception as e:
            raise InteractionLoggerError(f"Failed to read log entries: {e}") from e

    def get_interaction_by_id(self, request_id: str) -> dict[str, Any] | None:
        """
        Find a complete interaction by request_id.

        This searches through log files to find both intent and result stages
        for a given request_id.

        Args:
            request_id: Request ID to search for

        Returns:
            Dictionary with 'intent' and 'result' keys, or None if not found
        """
        # Search today's logs first, then recent days
        for days_ago in range(7):  # Search last 7 days
            date = datetime.now()
            if days_ago > 0:
                from datetime import timedelta

                date = date - timedelta(days=days_ago)

            entries = self.read_logs(date=date)

            intent_entry = None
            result_entry = None

            for entry in entries:
                if entry.get("request_id") == request_id:
                    if entry.get("stage") == "intent":
                        intent_entry = entry
                    elif entry.get("stage") == "result":
                        result_entry = entry

            # If found both stages, return them
            if intent_entry or result_entry:
                return {"intent": intent_entry, "result": result_entry}

        return None
