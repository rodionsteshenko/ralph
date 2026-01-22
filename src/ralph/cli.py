"""Command-line interface for Ralph."""

import argparse
import sys
from pathlib import Path
from typing import NoReturn

from ralph import __version__
from ralph import commands
from ralph.ascii_art import display_ralph_mascot


def main() -> NoReturn:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="ralph",
        description="Ralph: Autonomous AI Agent Loop for executing PRDs",
        epilog="""
Examples:
  ralph init                        # Initialize Ralph in current directory
  ralph process-prd prd.txt         # Process PRD and save to .ralph/prd.json
  ralph build-prd large-prd.txt     # Build large PRD incrementally (10+ stories)
  ralph execute                     # Execute PRD in .ralph/
  ralph execute --phase 1           # Execute only phase 1 stories
  ralph status                      # Show status
  ralph validate                    # Validate PRD structure
  ralph summary                     # Show PRD summary
  ralph skip-story US-023           # Skip a story
  ralph close-phase 2               # Close a phase
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "-C", "--dir",
        type=Path,
        default=None,
        help="Run as if ralph was started in this directory",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Init command
    subparsers.add_parser(
        "init",
        help="Initialize Ralph configuration in current directory",
    )

    # Process PRD command
    prd_parser = subparsers.add_parser(
        "process-prd",
        help="Convert PRD document to .ralph/prd.json",
    )
    prd_parser.add_argument(
        "prd_file",
        type=Path,
        help="Path to PRD text file",
    )
    prd_parser.add_argument(
        "--model",
        type=str,
        default="claude-opus-4-5",
        help="Claude model to use for parsing (default: claude-opus-4-5)",
    )

    # Build PRD command (for large PRDs)
    build_prd_parser = subparsers.add_parser(
        "build-prd",
        help="Build PRD JSON incrementally (for large PRDs with 10+ stories)",
    )
    build_prd_parser.add_argument(
        "prd_file",
        type=Path,
        help="Path to PRD text file",
    )
    build_prd_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output JSON file path (default: .ralph/prd.json)",
    )
    build_prd_parser.add_argument(
        "--model",
        type=str,
        default="claude-opus-4-5",
        help="Claude model to use for parsing (default: claude-opus-4-5)",
    )

    # Execute command
    exec_parser = subparsers.add_parser(
        "execute",
        help="Execute Ralph loop",
        aliases=["execute-plan", "run"],
    )
    exec_parser.add_argument(
        "--max-iterations",
        type=int,
        help="Maximum iterations (0 = unlimited)",
    )
    exec_parser.add_argument(
        "--phase",
        type=int,
        help="Execute specific phase only",
    )
    exec_parser.add_argument(
        "--model",
        type=str,
        help="Claude model to use (overrides auto-detected value)",
    )
    exec_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show verbose output",
    )

    # Status command
    status_parser = subparsers.add_parser(
        "status",
        help="Show Ralph status",
    )
    status_parser.add_argument(
        "--phase",
        type=int,
        help="Show status for specific phase only",
    )

    # Select command
    subparsers.add_parser(
        "select",
        help="Interactive story selection menu",
    )

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate PRD JSON structure",
    )
    validate_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )

    # Summary command
    subparsers.add_parser(
        "summary",
        help="Show PRD summary with completion statistics",
    )

    # Close phase command
    close_phase_parser = subparsers.add_parser(
        "close-phase",
        help="Mark all incomplete stories in a phase as skipped",
    )
    close_phase_parser.add_argument(
        "phase_number",
        type=int,
        help="Phase number to close",
    )

    # Skip story command
    skip_story_parser = subparsers.add_parser(
        "skip-story",
        help="Mark a story as skipped",
    )
    skip_story_parser.add_argument(
        "story_id",
        type=str,
        help="Story ID to skip (e.g., US-023)",
    )

    # Start story command
    start_story_parser = subparsers.add_parser(
        "start-story",
        help="Mark a story as in_progress",
    )
    start_story_parser.add_argument(
        "story_id",
        type=str,
        help="Story ID to start (e.g., US-023)",
    )

    # In-progress command
    subparsers.add_parser(
        "in-progress",
        help="Show all stories currently marked as in_progress",
    )

    # Clear stale command
    clear_stale_parser = subparsers.add_parser(
        "clear-stale",
        help="Clear stale in_progress status from stories",
    )
    clear_stale_parser.add_argument(
        "--max-age-hours",
        type=int,
        default=24,
        help="Maximum hours a story can be in_progress (default: 24)",
    )

    # List stories command
    list_stories_parser = subparsers.add_parser(
        "list-stories",
        help="List stories with optional filters",
    )
    list_stories_parser.add_argument(
        "--phase",
        type=int,
        help="Filter by phase number",
    )
    list_stories_parser.add_argument(
        "--status",
        type=str,
        choices=["incomplete", "in_progress", "complete", "skipped"],
        help="Filter by status",
    )

    # View command
    view_parser = subparsers.add_parser(
        "view",
        help="View PRD progress with pretty formatting",
    )
    view_parser.add_argument(
        "--once",
        action="store_true",
        help="Display once and exit (no watching)",
    )
    view_parser.add_argument(
        "--expand",
        "-e",
        action="store_true",
        help="Expand closed phases (show all stories)",
    )
    view_parser.add_argument(
        "-i",
        "--interval",
        type=float,
        default=1.0,
        help="Refresh interval in seconds (default: 1.0)",
    )

    args = parser.parse_args()

    if not args.command:
        display_ralph_mascot()
        print()  # Add spacing after mascot
        parser.print_help()
        sys.exit(0)

    # Route to command handlers
    command_map = {
        "init": commands.init_command,
        "process-prd": commands.process_prd_command,
        "build-prd": commands.build_prd_command,
        "execute": commands.execute_command,
        "execute-plan": commands.execute_command,
        "run": commands.execute_command,
        "status": commands.status_command,
        "select": commands.select_command,
        "validate": commands.validate_command,
        "summary": commands.summary_command,
        "close-phase": commands.close_phase_command,
        "skip-story": commands.skip_story_command,
        "start-story": commands.start_story_command,
        "in-progress": commands.in_progress_command,
        "clear-stale": commands.clear_stale_command,
        "list-stories": commands.list_stories_command,
        "view": commands.view_command,
    }

    handler = command_map.get(args.command)
    if handler:
        handler(args)
    else:
        print(f"❌ Unknown command: {args.command}")
        parser.print_help()
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
