"""Command-line interface for Ralph."""

import argparse
import json
import sys
from pathlib import Path
from typing import NoReturn

from ralph import __version__
from ralph.prd import PRDParser, validate_prd


def init_command(args: argparse.Namespace) -> None:
    """Initialize Ralph in current directory."""
    ralph_dir = Path.cwd() / ".ralph"

    if ralph_dir.exists():
        print(f"⚠️  Ralph already initialized in {Path.cwd()}")
        print("   .ralph/ directory already exists")
        return

    # Create .ralph directory structure
    ralph_dir.mkdir(parents=True, exist_ok=True)
    (ralph_dir / "logs").mkdir(exist_ok=True)
    (ralph_dir / "skills").mkdir(exist_ok=True)

    # Create placeholder files
    (ralph_dir / "progress.md").write_text("# Ralph Progress Log\n\nProgress will be tracked here.\n")

    print(f"✅ Ralph initialized in {Path.cwd()}")
    print("   Created .ralph/ directory structure")
    print("\n📝 Next steps:")
    print("   1. Create a PRD file (e.g., prd.txt)")
    print("   2. Run: ralph process-prd prd.txt")
    print("   3. Run: ralph execute")


def process_prd_command(args: argparse.Namespace) -> None:
    """Process PRD file and save to .ralph/prd.json."""
    prd_file = args.prd_file

    if not prd_file.exists():
        print(f"❌ PRD file not found: {prd_file}")
        sys.exit(1)

    ralph_dir = Path.cwd() / ".ralph"
    if not ralph_dir.exists():
        print("⚠️  Ralph not initialized. Run 'ralph init' first.")
        sys.exit(1)

    # Parse PRD
    parser = PRDParser(ralph_dir=ralph_dir, model=args.model)

    try:
        output_path = parser.parse_prd(prd_file)
        print("\n✅ PRD successfully processed!")
        print(f"   Output: {output_path}")
        print("\n📝 Next steps:")
        print(f"   1. Review the PRD: cat {output_path}")
        print("   2. Run: ralph execute")
    except Exception as e:
        print(f"❌ Failed to process PRD: {e}")
        sys.exit(1)


def execute_command(args: argparse.Namespace) -> None:
    """Execute Ralph loop."""
    from ralph.config import RalphConfig
    from ralph.loop import RalphLoop

    ralph_dir = Path.cwd() / ".ralph"
    prd_path = ralph_dir / "prd.json"

    if not ralph_dir.exists():
        print("❌ Ralph not initialized. Run 'ralph init' first.")
        sys.exit(1)

    if not prd_path.exists():
        print("❌ No PRD found. Run 'ralph process-prd <prd-file>' first.")
        sys.exit(1)

    # Create config with CLI overrides
    config = RalphConfig(project_dir=Path.cwd())

    # Apply CLI overrides
    if args.max_iterations is not None:
        config.set("ralph.maxIterations", args.max_iterations)

    if args.model:
        config.set("claude.model", args.model)

    if args.typecheck_cmd:
        config.set("commands.typecheck", args.typecheck_cmd)

    if args.lint_cmd:
        config.set("commands.lint", args.lint_cmd)

    if args.test_cmd:
        config.set("commands.test", args.test_cmd)

    # Create loop and execute
    loop = RalphLoop(config=config, verbose=args.verbose, skip_gates=args.no_gates)

    try:
        loop.execute(max_iterations=args.max_iterations, phase=args.phase)
    except KeyboardInterrupt:
        print("\n\n⚠️  Execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Execution failed: {e}")
        sys.exit(1)


def status_command(args: argparse.Namespace) -> None:
    """Show Ralph status."""
    from ralph.config import RalphConfig
    from ralph.loop import RalphLoop

    ralph_dir = Path.cwd() / ".ralph"
    prd_path = ralph_dir / "prd.json"

    if not ralph_dir.exists():
        print("❌ Ralph not initialized. Run 'ralph init' first.")
        sys.exit(1)

    if not prd_path.exists():
        print("❌ No PRD found. Run 'ralph process-prd <prd-file>' first.")
        sys.exit(1)

    # Create config and show info
    config = RalphConfig(project_dir=Path.cwd())
    loop = RalphLoop(config=config)

    try:
        loop.show_info(prd_path=prd_path, phase=args.phase if hasattr(args, 'phase') else None)
    except Exception as e:
        print(f"❌ Failed to show status: {e}")
        sys.exit(1)


def select_command(args: argparse.Namespace) -> None:
    """Interactive story selection menu."""
    ralph_dir = Path.cwd() / ".ralph"
    prd_path = ralph_dir / "prd.json"

    if not prd_path.exists():
        print("❌ No PRD found. Run 'ralph process-prd <prd-file>' first.")
        sys.exit(1)

    # Load PRD
    with open(prd_path, 'r') as f:
        prd = json.load(f)

    # Get incomplete stories
    incomplete_stories = [
        s for s in prd.get("userStories", [])
        if s.get("status", "incomplete") not in ("complete", "skipped")
    ]

    if not incomplete_stories:
        print("✅ All stories are complete!")
        return

    print(f"\n📋 Incomplete Stories ({len(incomplete_stories)}):\n")

    for i, story in enumerate(incomplete_stories, 1):
        status_emoji = "🔄" if story.get("status") == "in_progress" else "⏳"
        phase_info = f" [Phase {story.get('phase')}]" if story.get('phase') else ""
        print(f"{i}. {status_emoji} {story['id']}: {story['title']}{phase_info}")
        print(f"   Priority: {story.get('priority', 'N/A')}")
        print()

    print("💡 To execute: ralph execute")


def validate_command(args: argparse.Namespace) -> None:
    """Validate PRD JSON structure."""
    ralph_dir = Path.cwd() / ".ralph"
    prd_path = ralph_dir / "prd.json"

    if not prd_path.exists():
        print(f"❌ PRD not found: {prd_path}")
        sys.exit(1)

    # Load and validate PRD
    try:
        with open(prd_path, 'r') as f:
            prd = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        sys.exit(1)

    result = validate_prd(prd)
    print(result.format())

    if not result.valid:
        sys.exit(1)

    if args.strict and result.warnings:
        print("\n❌ Validation failed (strict mode: warnings treated as errors)")
        sys.exit(1)

    if result.warnings:
        print("\n⚠️  Warnings found but validation passed (use --strict to treat warnings as errors)")


def main() -> NoReturn:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="ralph",
        description="Ralph: Autonomous AI Agent Loop for executing PRDs",
        epilog="""
Examples:
  ralph init                        # Initialize Ralph in current directory
  ralph process-prd prd.txt         # Process PRD and save to .ralph/prd.json
  ralph execute                     # Execute PRD in .ralph/
  ralph execute --phase 1           # Execute only phase 1 stories
  ralph status                      # Show status
  ralph validate                    # Validate PRD structure
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
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
        default="claude-sonnet-4-5-20250929",
        help="Claude model to use for parsing (default: claude-sonnet-4-5-20250929)",
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
        "--typecheck-cmd",
        type=str,
        help="Typecheck command (overrides auto-detected value)",
    )
    exec_parser.add_argument(
        "--lint-cmd",
        type=str,
        help="Lint command (overrides auto-detected value)",
    )
    exec_parser.add_argument(
        "--test-cmd",
        type=str,
        help="Test command (overrides auto-detected value)",
    )
    exec_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show verbose output",
    )
    exec_parser.add_argument(
        "--no-gates",
        action="store_true",
        help="Skip quality gates (for debugging)",
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

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Route to command handlers
    if args.command == "init":
        init_command(args)
    elif args.command == "process-prd":
        process_prd_command(args)
    elif args.command in ("execute", "execute-plan", "run"):
        execute_command(args)
    elif args.command == "status":
        status_command(args)
    elif args.command == "select":
        select_command(args)
    elif args.command == "validate":
        validate_command(args)
    else:
        print(f"❌ Unknown command: {args.command}")
        parser.print_help()
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
