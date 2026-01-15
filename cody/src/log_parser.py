#!/usr/bin/env python3
"""
Log parser CLI tool for viewing Claude interaction logs.

Parses and displays interaction logs in various formats with filtering options.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from .logging import InteractionLogger


class LogParserError(Exception):
    """Raised when log parser encounters an error."""

    pass


class LogParser:
    """
    Parser for Claude interaction logs stored in JSONL format.

    Supports filtering by request ID, error status, and displaying in various formats.
    """

    def __init__(self, log_file: Path) -> None:
        """
        Initialize log parser.

        Args:
            log_file: Path to the JSONL log file to parse

        Raises:
            LogParserError: If log file doesn't exist or is not a file
        """
        if not log_file.exists():
            raise LogParserError(f"Log file not found: {log_file}")

        if not log_file.is_file():
            raise LogParserError(f"Not a file: {log_file}")

        self.log_file = log_file
        self.console = Console()

    def parse_logs(self) -> list[dict[str, Any]]:
        """
        Parse all log entries from the log file.

        Returns:
            List of log entry dictionaries

        Raises:
            LogParserError: If parsing fails
        """
        try:
            entries: list[dict[str, Any]] = []

            with open(self.log_file) as f:
                for line_num, line in enumerate(f, 1):
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            entries.append(entry)
                        except json.JSONDecodeError as e:
                            raise LogParserError(
                                f"Invalid JSON at line {line_num}: {e}"
                            ) from e

            return entries

        except OSError as e:
            raise LogParserError(f"Failed to read log file: {e}") from e

    def group_by_request_id(
        self, entries: list[dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """
        Group log entries by request_id, combining intent and result stages.

        Args:
            entries: List of log entries

        Returns:
            Dictionary mapping request_id to {"intent": ..., "result": ...}
        """
        grouped: dict[str, dict[str, Any]] = {}

        for entry in entries:
            request_id = entry.get("request_id")
            if not request_id:
                continue

            if request_id not in grouped:
                grouped[request_id] = {"intent": None, "result": None}

            stage = entry.get("stage")
            if stage == "intent":
                grouped[request_id]["intent"] = entry
            elif stage == "result":
                grouped[request_id]["result"] = entry

        return grouped

    def filter_by_request_id(
        self, interactions: dict[str, dict[str, Any]], request_id: str
    ) -> dict[str, dict[str, Any]]:
        """
        Filter interactions to only the specified request_id.

        Args:
            interactions: Grouped interactions
            request_id: Request ID to filter by

        Returns:
            Dictionary with only the matching request_id (or empty if not found)
        """
        if request_id in interactions:
            return {request_id: interactions[request_id]}
        return {}

    def filter_errors_only(
        self, interactions: dict[str, dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """
        Filter to only interactions that had errors.

        Args:
            interactions: Grouped interactions

        Returns:
            Dictionary with only interactions that have error field
        """
        return {
            req_id: interaction
            for req_id, interaction in interactions.items()
            if interaction.get("result", {}).get("error") is not None
        }

    def get_last_n(
        self, interactions: dict[str, dict[str, Any]], n: int
    ) -> dict[str, dict[str, Any]]:
        """
        Get the last N interactions (by timestamp).

        Args:
            interactions: Grouped interactions
            n: Number of interactions to return

        Returns:
            Dictionary with last N interactions
        """
        # Sort by timestamp from intent or result (whichever is available)
        sorted_items = sorted(
            interactions.items(),
            key=lambda x: (
                (x[1].get("intent") or {}).get("timestamp", "")
                or (x[1].get("result") or {}).get("timestamp", "")
            ),
        )

        # Take last N
        last_n = dict(sorted_items[-n:] if n > 0 else sorted_items)
        return last_n

    def display_json(self, interactions: dict[str, dict[str, Any]]) -> None:
        """
        Display interactions as JSON (machine-readable format).

        Args:
            interactions: Grouped interactions to display
        """
        # Convert to list format for cleaner JSON output
        output = []
        for request_id, interaction in interactions.items():
            output.append(
                {
                    "request_id": request_id,
                    "intent": interaction.get("intent"),
                    "result": interaction.get("result"),
                }
            )

        print(json.dumps(output, indent=2))

    def display_prompts_only(self, interactions: dict[str, dict[str, Any]]) -> None:
        """
        Display only the prompts (user messages) from interactions.

        Args:
            interactions: Grouped interactions to display
        """
        for request_id, interaction in interactions.items():
            intent = interaction.get("intent")
            if not intent:
                continue

            timestamp = intent.get("timestamp", "Unknown")
            user_message = intent.get("user_message", "")
            system_prompt = intent.get("system_prompt", "")

            self.console.print(f"\n[bold cyan]Request ID:[/bold cyan] {request_id}")
            self.console.print(f"[dim]Timestamp: {timestamp}[/dim]")
            self.console.print("\n[bold yellow]System Prompt:[/bold yellow]")
            self.console.print(system_prompt)
            self.console.print("\n[bold green]User Message:[/bold green]")
            self.console.print(user_message)
            self.console.print("\n" + "─" * 80)

    def calculate_statistics(
        self, interactions: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Calculate summary statistics from interactions.

        Args:
            interactions: Grouped interactions to analyze

        Returns:
            Dictionary with statistics including:
            - total_interactions: Total number of interactions
            - successful_count: Number of successful interactions
            - error_count: Number of failed interactions
            - avg_duration_ms: Average duration in milliseconds
            - tools_usage: Dict of tool names to usage count
            - date_range: Tuple of (earliest, latest) timestamps
            - estimated_tokens: Estimated token usage (heuristic)
        """
        if not interactions:
            return {
                "total_interactions": 0,
                "successful_count": 0,
                "error_count": 0,
                "avg_duration_ms": 0.0,
                "tools_usage": {},
                "date_range": (None, None),
                "estimated_tokens": 0,
            }

        total = len(interactions)
        successful = 0
        errors = 0
        durations: list[float] = []
        tools_counter: dict[str, int] = {}
        timestamps: list[str] = []
        total_chars = 0

        for interaction in interactions.values():
            result = interaction.get("result")
            intent = interaction.get("intent")

            # Count successes/errors
            if result:
                if result.get("error"):
                    errors += 1
                else:
                    successful += 1

                # Collect durations
                duration = result.get("duration_ms")
                if duration is not None:
                    durations.append(duration)

                # Count tools usage
                tools_called = result.get("tools_called", [])
                for tool in tools_called:
                    tools_counter[tool] = tools_counter.get(tool, 0) + 1

                # Collect timestamps
                timestamp = result.get("timestamp")
                if timestamp:
                    timestamps.append(timestamp)

            # Collect timestamps from intent too
            if intent:
                timestamp = intent.get("timestamp")
                if timestamp:
                    timestamps.append(timestamp)

                # Estimate tokens based on prompt length (rough heuristic: 1 token ≈ 4 chars)
                system_prompt = intent.get("system_prompt", "")
                user_message = intent.get("user_message", "")
                full_context = intent.get("full_context", "")

                total_chars += len(system_prompt)
                total_chars += len(user_message)
                if full_context:
                    total_chars += len(full_context)

            # Add response length for token estimation
            if result:
                response = result.get("response", "")
                total_chars += len(response)

        # Calculate average duration
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        # Determine date range
        date_range: tuple[str | None, str | None]
        if timestamps:
            sorted_timestamps = sorted(timestamps)
            date_range = (sorted_timestamps[0], sorted_timestamps[-1])
        else:
            date_range = (None, None)

        # Estimate tokens (rough heuristic: 1 token ≈ 4 characters)
        estimated_tokens = total_chars // 4

        return {
            "total_interactions": total,
            "successful_count": successful,
            "error_count": errors,
            "avg_duration_ms": avg_duration,
            "tools_usage": tools_counter,
            "date_range": date_range,
            "estimated_tokens": estimated_tokens,
        }

    def display_statistics(self, interactions: dict[str, dict[str, Any]]) -> None:
        """
        Display summary statistics for interactions.

        Args:
            interactions: Grouped interactions to analyze
        """
        stats = self.calculate_statistics(interactions)

        # Header
        self.console.print()
        self.console.rule("[bold cyan]Log Summary Statistics[/bold cyan]")
        self.console.print()

        # Create statistics table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Metric", style="bold yellow")
        table.add_column("Value", style="cyan")

        # Total interactions
        table.add_row("Total Interactions", str(stats["total_interactions"]))

        # Success/Error counts
        table.add_row(
            "Successful",
            f"[green]{stats['successful_count']}[/green]",
        )
        table.add_row(
            "Errors",
            f"[red]{stats['error_count']}[/red]",
        )

        # Average duration
        avg_dur = stats["avg_duration_ms"]
        if avg_dur > 1000:
            duration_str = f"{avg_dur / 1000:.2f}s"
        else:
            duration_str = f"{avg_dur:.1f}ms"
        table.add_row("Average Duration", duration_str)

        # Estimated tokens
        table.add_row(
            "Estimated Tokens",
            f"~{stats['estimated_tokens']:,}",
        )

        # Date range
        date_range = stats["date_range"]
        if date_range[0] and date_range[1]:
            # Parse and format dates nicely
            try:
                start_dt = datetime.fromisoformat(date_range[0])
                end_dt = datetime.fromisoformat(date_range[1])
                start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
                end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")
                table.add_row("Date Range", f"{start_str} to {end_str}")
            except (ValueError, AttributeError):
                table.add_row("Date Range", f"{date_range[0]} to {date_range[1]}")
        else:
            table.add_row("Date Range", "N/A")

        self.console.print(table)

        # Most common tools (if any)
        tools_usage = stats["tools_usage"]
        if tools_usage:
            self.console.print()
            self.console.print("[bold yellow]Most Common Tools:[/bold yellow]")

            # Sort by usage count (descending)
            sorted_tools = sorted(
                tools_usage.items(), key=lambda x: x[1], reverse=True
            )

            # Create tools table
            tools_table = Table(show_header=True, box=None, padding=(0, 2))
            tools_table.add_column("Tool", style="cyan")
            tools_table.add_column("Count", style="magenta", justify="right")

            for tool, count in sorted_tools[:10]:  # Show top 10
                tools_table.add_row(tool, str(count))

            self.console.print(tools_table)

        self.console.print()

    def display_pretty(self, interactions: dict[str, dict[str, Any]]) -> None:
        """
        Display interactions with rich formatting and colors.

        Args:
            interactions: Grouped interactions to display
        """
        if not interactions:
            self.console.print("[yellow]No interactions found[/yellow]")
            return

        for request_id, interaction in interactions.items():
            intent = interaction.get("intent")
            result = interaction.get("result")

            # Create main panel
            self.console.print()
            self.console.rule(f"[bold cyan]Interaction: {request_id}[/bold cyan]")

            # Intent section
            if intent:
                timestamp = intent.get("timestamp", "Unknown")
                self.console.print(f"\n[dim]Timestamp: {timestamp}[/dim]")

                # System prompt
                system_prompt = intent.get("system_prompt", "")
                if system_prompt:
                    self.console.print("\n[bold yellow]System Prompt:[/bold yellow]")
                    self.console.print(
                        Panel(system_prompt, border_style="yellow", padding=(0, 1))
                    )

                # User message
                user_message = intent.get("user_message", "")
                if user_message:
                    self.console.print("\n[bold green]User Message:[/bold green]")
                    self.console.print(
                        Panel(user_message, border_style="green", padding=(0, 1))
                    )

                # Full context (if present)
                full_context = intent.get("full_context")
                if full_context:
                    self.console.print("\n[bold blue]Full Context:[/bold blue]")
                    # Truncate if too long
                    if len(full_context) > 500:
                        context_preview = full_context[:500] + "..."
                    else:
                        context_preview = full_context
                    self.console.print(
                        Panel(context_preview, border_style="blue", padding=(0, 1))
                    )

            # Result section
            if result:
                timestamp = result.get("timestamp", "Unknown")
                duration = result.get("duration_ms", 0)
                self.console.print(
                    f"\n[dim]Response timestamp: {timestamp} (took {duration:.1f}ms)[/dim]"
                )

                # Response
                response = result.get("response", "")
                error = result.get("error")

                if error:
                    self.console.print("\n[bold red]Error:[/bold red]")
                    self.console.print(
                        Panel(error, border_style="red", padding=(0, 1))
                    )
                elif response:
                    self.console.print("\n[bold magenta]Response:[/bold magenta]")
                    self.console.print(
                        Panel(response, border_style="magenta", padding=(0, 1))
                    )

                # Tools called
                tools_called = result.get("tools_called", [])
                if tools_called:
                    self.console.print(
                        f"\n[bold cyan]Tools Called:[/bold cyan] {', '.join(tools_called)}"
                    )

            self.console.print()


def main() -> NoReturn:
    """
    Main entry point for log parser CLI.

    Exit codes:
        0: Success
        1: Error (file not found, parsing error, etc.)
    """
    parser = argparse.ArgumentParser(
        description="Parse and view Claude interaction logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # View all interactions in today's log
  python -m cody.src.log_parser .cody/logs/interactions-2026-01-14.jsonl

  # View last 5 interactions
  python -m cody.src.log_parser .cody/logs/interactions.jsonl --last 5

  # View specific interaction by request ID
  python -m cody.src.log_parser .cody/logs/interactions.jsonl --request-id UUID

  # View only failed interactions
  python -m cody.src.log_parser .cody/logs/interactions.jsonl --errors

  # Export to JSON format
  python -m cody.src.log_parser .cody/logs/interactions.jsonl --json

  # Show only prompts (no responses)
  python -m cody.src.log_parser .cody/logs/interactions.jsonl --prompts-only

  # Show summary statistics
  python -m cody.src.log_parser .cody/logs/interactions.jsonl --stats
        """,
    )

    parser.add_argument(
        "log_file",
        type=Path,
        help="Path to the JSONL log file to parse",
    )

    parser.add_argument(
        "--last",
        "-l",
        type=int,
        metavar="N",
        help="Show only the last N interactions",
    )

    parser.add_argument(
        "--request-id",
        "-r",
        type=str,
        metavar="UUID",
        help="Show only the interaction with this request ID",
    )

    parser.add_argument(
        "--errors",
        "-e",
        action="store_true",
        help="Show only interactions that had errors",
    )

    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output in machine-readable JSON format",
    )

    parser.add_argument(
        "--prompts-only",
        "-p",
        action="store_true",
        help="Show only the prompts (system + user messages), not responses",
    )

    parser.add_argument(
        "--stats",
        "-s",
        action="store_true",
        help="Show summary statistics (total, success/error counts, avg duration, tools usage, etc.)",
    )

    args = parser.parse_args()

    try:
        # Create parser and parse logs
        log_parser = LogParser(args.log_file)
        entries = log_parser.parse_logs()

        if not entries:
            console = Console()
            console.print("[yellow]No log entries found[/yellow]")
            sys.exit(0)

        # Group by request_id
        interactions = log_parser.group_by_request_id(entries)

        # Apply filters
        if args.request_id:
            interactions = log_parser.filter_by_request_id(interactions, args.request_id)

        if args.errors:
            interactions = log_parser.filter_errors_only(interactions)

        if args.last:
            interactions = log_parser.get_last_n(interactions, args.last)

        # Display in requested format
        if args.stats:
            log_parser.display_statistics(interactions)
        elif args.json:
            log_parser.display_json(interactions)
        elif args.prompts_only:
            log_parser.display_prompts_only(interactions)
        else:
            log_parser.display_pretty(interactions)

        sys.exit(0)

    except LogParserError as e:
        console = Console(stderr=True)
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    except KeyboardInterrupt:
        console = Console(stderr=True)
        console.print("\n[yellow]Interrupted[/yellow]")
        sys.exit(130)

    except Exception as e:
        console = Console(stderr=True)
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
