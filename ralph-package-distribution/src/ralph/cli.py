"""Command-line interface for Ralph."""

import argparse
import sys
from pathlib import Path
from typing import NoReturn


def main() -> NoReturn:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Ralph: Autonomous AI Agent Loop",
        epilog="""
Examples:
    ralph init                        # Initialize Ralph in current directory
    ralph execute                     # Execute PRD in .ralph/
    ralph status                      # Show status
    ralph process-prd prd.txt         # Process PRD and save to .ralph/prd.json
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
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

    # Execute command
    exec_parser = subparsers.add_parser(
        "execute",
        help="Execute Ralph loop",
        aliases=["execute-plan", "run"],
    )
    exec_parser.add_argument(
        "--max-iterations",
        type=int,
        default=0,
        help="Maximum iterations (0 = unlimited)",
    )
    exec_parser.add_argument(
        "--phase",
        type=int,
        help="Execute specific phase only",
    )

    # Status command
    subparsers.add_parser(
        "status",
        help="Show Ralph status",
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

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Command implementations will be added in future stories
    print(f"Ralph CLI - Command '{args.command}' not yet implemented")
    print("This is a placeholder. Full implementation coming in future stories.")
    sys.exit(0)


if __name__ == "__main__":
    main()
