"""Command handlers for Ralph CLI."""

import argparse
import json
import sys
from pathlib import Path

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


def build_prd_command(args: argparse.Namespace) -> None:
    """Build PRD JSON using incremental builder (for large PRDs)."""
    from ralph.builder import PRDBuilder

    prd_file = args.prd_file

    if not prd_file.exists():
        print(f"❌ PRD file not found: {prd_file}")
        sys.exit(1)

    ralph_dir = Path.cwd() / ".ralph"
    if not ralph_dir.exists():
        print("⚠️  Ralph not initialized. Run 'ralph init' first.")
        sys.exit(1)

    # Determine output path
    output_path = args.output if args.output else ralph_dir / "prd.json"

    # Build PRD using incremental builder
    builder = PRDBuilder()

    try:
        builder.build_from_prd(prd_file, output_path, model=args.model)
        print("\n✅ PRD successfully built!")
        print(f"   Output: {output_path}")
        print("\n📝 Next steps:")
        print(f"   1. Review the PRD: cat {output_path}")
        print("   2. Run: ralph execute")
    except Exception as e:
        print(f"❌ Failed to build PRD: {e}")
        sys.exit(1)


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


def summary_command(args: argparse.Namespace) -> None:
    """Show PRD summary."""
    from ralph.tools import PRDManager, resolve_prd_path

    try:
        prd_path = resolve_prd_path(Path.cwd())
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)

    manager = PRDManager(prd_path)
    summary = manager.get_summary()

    print(f"\n📊 PRD Summary ({prd_path})")
    print(f"{'=' * 50}")
    print(f"Total Stories: {summary['total_stories']}")
    print(f"Completed: {summary['completed_stories']}")
    print(f"Skipped: {summary.get('skipped_stories', 0)}")
    print(f"Remaining: {summary['remaining_stories']}")
    print(f"Progress: {summary['completion_percentage']}%")
    print("\n📋 By Phase:")

    phases_meta = manager.data.get("metadata", {}).get("phases", {})
    for phase, counts in sorted(summary["by_phase"].items()):
        phase_meta = phases_meta.get(str(phase), {})
        phase_name = phase_meta.get("name", f"Phase {phase}")
        closed_badge = " [CLOSED]" if manager.is_phase_closed(phase) else ""
        skipped = counts.get("skipped", 0)
        skipped_str = f", {skipped} skipped" if skipped > 0 else ""
        stats = f"{counts['completed']}/{counts['total']} complete{skipped_str}"
        print(f"  Phase {phase} ({phase_name}): {stats}{closed_badge}")


def close_phase_command(args: argparse.Namespace) -> None:
    """Mark all incomplete stories in a phase as skipped."""
    from ralph.tools import PRDManager, resolve_prd_path

    try:
        prd_path = resolve_prd_path(Path.cwd())
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)

    manager = PRDManager(prd_path)
    skipped = manager.close_phase(args.phase_number)
    manager.save()

    if skipped:
        print(f"⊘ Closed phase {args.phase_number}, marked {len(skipped)} stories as skipped:")
        for story_id in skipped:
            print(f"  - {story_id}")
    else:
        print(f"No incomplete stories in phase {args.phase_number}")


def skip_story_command(args: argparse.Namespace) -> None:
    """Mark a story as skipped."""
    from ralph.tools import PRDManager, resolve_prd_path

    try:
        prd_path = resolve_prd_path(Path.cwd())
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)

    manager = PRDManager(prd_path)
    if manager.skip_story(args.story_id):
        manager.save()
        print(f"⊘ Skipped story {args.story_id}")
    else:
        print(f"❌ Story {args.story_id} not found")
        sys.exit(1)


def start_story_command(args: argparse.Namespace) -> None:
    """Mark a story as in_progress."""
    from ralph.tools import PRDManager, resolve_prd_path

    try:
        prd_path = resolve_prd_path(Path.cwd())
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)

    manager = PRDManager(prd_path)
    if manager.start_story(args.story_id):
        manager.save()
        print(f"▶ Started story {args.story_id}")
    else:
        print(f"❌ Story {args.story_id} not found")
        sys.exit(1)


def in_progress_command(args: argparse.Namespace) -> None:
    """Show all in-progress stories."""
    from ralph.tools import PRDManager, resolve_prd_path

    try:
        prd_path = resolve_prd_path(Path.cwd())
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)

    manager = PRDManager(prd_path)
    in_progress = manager.get_in_progress()

    if in_progress:
        print("\n▶ Stories currently in progress:")
        for story in in_progress:
            started = story.get("startedAt", "unknown")
            print(f"  {story['id']}: {story['title']} (started: {started})")
    else:
        print("No stories currently in progress")


def clear_stale_command(args: argparse.Namespace) -> None:
    """Clear stale in_progress status."""
    from ralph.tools import PRDManager, resolve_prd_path

    try:
        prd_path = resolve_prd_path(Path.cwd())
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)

    manager = PRDManager(prd_path)
    cleared = manager.clear_stale_in_progress(args.max_age_hours)
    manager.save()

    if cleared:
        print(f"Cleared stale in_progress status from {len(cleared)} stories:")
        for story_id in cleared:
            print(f"  - {story_id}")
    else:
        print("No stale in_progress stories found")


def list_stories_command(args: argparse.Namespace) -> None:
    """List stories with optional filters."""
    from ralph.tools import PRDManager, resolve_prd_path

    try:
        prd_path = resolve_prd_path(Path.cwd())
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)

    manager = PRDManager(prd_path)
    stories = manager.list_stories(
        phase=args.phase if hasattr(args, 'phase') and args.phase else None,
        status=args.status if hasattr(args, 'status') and args.status else None
    )

    if not stories:
        print("No stories found matching filters")
        return

    for story in stories:
        status_icon = "✅" if story.get("status") == "complete" else "⏳"
        print(f"{status_icon} {story['id']}: {story['title']} (Phase {story.get('phase', '?')})")
