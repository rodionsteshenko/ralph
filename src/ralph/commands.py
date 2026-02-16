"""Command handlers for Ralph CLI."""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from ralph.output import (
    EXIT_ERROR,
    EXIT_MAX_FAILURES,
    EXIT_MAX_ITERATIONS,
    EXIT_NOTHING_TO_DO,
    EXIT_SUCCESS,
    json_error,
    json_output,
)
from ralph.prd import PRDParser, validate_prd


def get_project_dir(args: argparse.Namespace) -> Path:
    """Get project directory from args or current working directory."""
    if hasattr(args, 'dir') and args.dir is not None:
        return Path(args.dir).resolve()
    return Path.cwd()


def _use_json(args: argparse.Namespace) -> bool:
    """Check if JSON output mode is enabled."""
    return getattr(args, 'json', False)


def init_command(args: argparse.Namespace) -> Optional[int]:
    """Initialize Ralph in current directory."""
    use_json = _use_json(args)
    project_dir = get_project_dir(args)
    ralph_dir = project_dir / ".ralph"

    if ralph_dir.exists():
        if use_json:
            return json_output({
                "initialized": False, "reason": "already_exists", "path": str(project_dir),
            })
        print(f"\u26a0\ufe0f  Ralph already initialized in {project_dir}")
        print("   .ralph/ directory already exists")
        return None

    # Create .ralph directory structure
    ralph_dir.mkdir(parents=True, exist_ok=True)
    (ralph_dir / "logs").mkdir(exist_ok=True)
    (ralph_dir / "skills").mkdir(exist_ok=True)

    # Create placeholder files
    (ralph_dir / "progress.md").write_text(
        "# Ralph Progress Log\n\nProgress will be tracked here.\n"
    )

    if use_json:
        return json_output({"initialized": True, "path": str(project_dir)})

    print(f"\u2705 Ralph initialized in {project_dir}")
    print("   Created .ralph/ directory structure")
    print("\n\U0001f4dd Next steps:")
    print("   1. Create a PRD file (e.g., prd.txt)")
    print("   2. Run: ralph process-prd prd.txt")
    print("   3. Run: ralph execute")
    return None


def process_prd_command(args: argparse.Namespace) -> Optional[int]:
    """Process PRD file and save to .ralph/prd.json."""
    use_json = _use_json(args)
    prd_file = args.prd_file

    if not prd_file.exists():
        if use_json:
            return json_error(f"PRD file not found: {prd_file}")
        print(f"\u274c PRD file not found: {prd_file}")
        sys.exit(1)

    project_dir = get_project_dir(args)
    ralph_dir = project_dir / ".ralph"
    if not ralph_dir.exists():
        if use_json:
            return json_error("Ralph not initialized. Run 'ralph init' first.")
        print("\u26a0\ufe0f  Ralph not initialized. Run 'ralph init' first.")
        sys.exit(1)

    # Parse PRD
    parser = PRDParser(ralph_dir=ralph_dir, model=args.model)

    try:
        output_path = parser.parse_prd(prd_file)
        if use_json:
            return json_output({"success": True, "output_path": str(output_path)})
        print("\n\u2705 PRD successfully processed!")
        print(f"   Output: {output_path}")
        print("\n\U0001f4dd Next steps:")
        print(f"   1. Review the PRD: cat {output_path}")
        print("   2. Run: ralph execute")
    except Exception as e:
        if use_json:
            return json_error(f"Failed to process PRD: {e}")
        print(f"\u274c Failed to process PRD: {e}")
        sys.exit(1)
    return None


def execute_command(args: argparse.Namespace) -> Optional[int]:
    """Execute Ralph loop."""
    from ralph.config import RalphConfig
    from ralph.loop import RalphLoop

    use_json = _use_json(args)
    project_dir = get_project_dir(args)
    ralph_dir = project_dir / ".ralph"
    prd_path = ralph_dir / "prd.json"

    if not ralph_dir.exists():
        if use_json:
            return json_error("Ralph not initialized. Run 'ralph init' first.")
        print("\u274c Ralph not initialized. Run 'ralph init' first.")
        sys.exit(1)

    if not prd_path.exists():
        if use_json:
            return json_error("No PRD found. Run 'ralph process-prd <prd-file>' first.")
        print("\u274c No PRD found. Run 'ralph process-prd <prd-file>' first.")
        sys.exit(1)

    # Create config with CLI overrides
    config = RalphConfig(project_dir=project_dir)

    # Apply CLI overrides
    if args.max_iterations is not None:
        config.set("ralph.maxIterations", args.max_iterations)

    if args.model:
        config.set("claude.model", args.model)

    # Create loop and execute
    loop = RalphLoop(config=config, verbose=args.verbose, json_mode=use_json)

    try:
        result = loop.execute(max_iterations=args.max_iterations, phase=args.phase)
    except KeyboardInterrupt:
        if use_json:
            return json_error("Execution interrupted by user", EXIT_ERROR)
        print("\n\n\u26a0\ufe0f  Execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        if use_json:
            return json_error(f"Execution failed: {e}")
        print(f"\n\u274c Execution failed: {e}")
        sys.exit(1)

    if use_json:
        stop_reason = result.get("stop_reason", "completed")
        exit_code_map = {
            "completed": EXIT_SUCCESS,
            "max_iterations": EXIT_MAX_ITERATIONS,
            "max_failures": EXIT_MAX_FAILURES,
        }
        exit_code = exit_code_map.get(stop_reason, EXIT_ERROR)
        return json_output(result, exit_code)
    return None


def execute_one_command(args: argparse.Namespace) -> Optional[int]:
    """Execute exactly one story and exit."""
    from ralph.config import RalphConfig
    from ralph.loop import RalphLoop

    use_json = _use_json(args)
    project_dir = get_project_dir(args)
    ralph_dir = project_dir / ".ralph"
    prd_path = ralph_dir / "prd.json"

    if not ralph_dir.exists():
        if use_json:
            return json_error("Ralph not initialized. Run 'ralph init' first.")
        print("\u274c Ralph not initialized. Run 'ralph init' first.")
        sys.exit(1)

    if not prd_path.exists():
        if use_json:
            return json_error("No PRD found. Run 'ralph process-prd <prd-file>' first.")
        print("\u274c No PRD found. Run 'ralph process-prd <prd-file>' first.")
        sys.exit(1)

    config = RalphConfig(project_dir=project_dir)

    if args.model:
        config.set("claude.model", args.model)

    loop = RalphLoop(config=config, verbose=args.verbose, json_mode=use_json)

    try:
        result = loop.execute_one(phase=args.phase)
    except KeyboardInterrupt:
        if use_json:
            return json_error("Execution interrupted by user", EXIT_ERROR)
        print("\n\n\u26a0\ufe0f  Execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        if use_json:
            return json_error(f"Execution failed: {e}")
        print(f"\n\u274c Execution failed: {e}")
        sys.exit(1)

    if use_json:
        status = result.get("status", "failed")
        if status == "nothing_to_do":
            return json_output(result, EXIT_NOTHING_TO_DO)
        elif status == "complete":
            return json_output(result, EXIT_SUCCESS)
        else:
            return json_output(result, EXIT_ERROR)

    # Human output
    status = result.get("status", "failed")
    if status == "nothing_to_do":
        print("\u2705 All stories are already complete!")
    elif status == "complete":
        print(f"\u2705 Story {result['story_id']} completed ({result['duration_seconds']}s)")
        print(f"   Remaining: {result['remaining_stories']} stories")
    else:
        print(f"\u274c Story {result['story_id']} failed ({result['duration_seconds']}s)")
    return None


def next_story_command(args: argparse.Namespace) -> Optional[int]:
    """Show the next story that would be executed without running it."""
    from ralph.config import RalphConfig
    from ralph.loop import RalphLoop

    use_json = _use_json(args)
    project_dir = get_project_dir(args)
    ralph_dir = project_dir / ".ralph"
    prd_path = ralph_dir / "prd.json"

    if not prd_path.exists():
        if use_json:
            return json_error("No PRD found.")
        print("\u274c No PRD found. Run 'ralph process-prd <prd-file>' first.")
        sys.exit(1)

    with open(prd_path, 'r') as f:
        prd = json.load(f)

    # Find remaining stories
    remaining = [
        s for s in prd.get("userStories", [])
        if s.get("status", "incomplete") not in ("complete", "skipped")
    ]
    phase = getattr(args, 'phase', None)
    if phase is not None:
        remaining = [s for s in remaining if s.get("phase") == phase]

    if not remaining:
        if use_json:
            return json_output({"story": None, "reason": "all_complete"}, EXIT_NOTHING_TO_DO)
        print("\u2705 All stories are already complete!")
        return None

    # Use RalphLoop's selection logic (with AI selection disabled for speed)
    config = RalphConfig(project_dir=project_dir)
    config.set("ralph.useAISelection", False)
    loop = RalphLoop(config=config, json_mode=True)
    story = loop._select_next_story(remaining, prd)

    if use_json:
        return json_output({
            "story": {
                "id": story["id"],
                "title": story["title"],
                "description": story.get("description", ""),
                "phase": story.get("phase"),
                "priority": story.get("priority"),
                "acceptanceCriteria": story.get("acceptanceCriteria", []),
            },
            "remaining_stories": len(remaining),
        })

    print(f"\u27a1\ufe0f  Next story: {story['id']} - {story['title']}")
    print(f"   Phase: {story.get('phase', 'N/A')}, Priority: {story.get('priority', 'N/A')}")
    if story.get("description"):
        print(f"   {story['description'][:100]}")
    return None


def status_command(args: argparse.Namespace) -> Optional[int]:
    """Show Ralph status."""
    from ralph.config import RalphConfig
    from ralph.loop import RalphLoop
    from ralph.tools import PRDManager

    use_json = _use_json(args)
    project_dir = get_project_dir(args)
    ralph_dir = project_dir / ".ralph"
    prd_path = ralph_dir / "prd.json"

    if not ralph_dir.exists():
        if use_json:
            return json_error("Ralph not initialized. Run 'ralph init' first.")
        print("\u274c Ralph not initialized. Run 'ralph init' first.")
        sys.exit(1)

    if not prd_path.exists():
        if use_json:
            return json_error("No PRD found. Run 'ralph process-prd <prd-file>' first.")
        print("\u274c No PRD found. Run 'ralph process-prd <prd-file>' first.")
        sys.exit(1)

    if use_json:
        manager = PRDManager(prd_path)
        summary = manager.get_summary()
        with open(prd_path, 'r') as f:
            prd = json.load(f)
        stories = prd.get("userStories", [])
        phase_filter = getattr(args, 'phase', None)
        if phase_filter is not None:
            stories = [s for s in stories if s.get("phase") == phase_filter]
        return json_output({
            "project": prd.get("project", "Unknown"),
            "summary": summary,
            "stories": [
                {
                    "id": s["id"], "title": s["title"],
                    "status": s.get("status", "incomplete"),
                    "phase": s.get("phase"),
                }
                for s in stories
            ],
        })

    # Create config and show info (human mode)
    config = RalphConfig(project_dir=project_dir)
    loop = RalphLoop(config=config)

    try:
        loop.show_info(prd_path=prd_path, phase=args.phase if hasattr(args, 'phase') else None)
    except Exception as e:
        print(f"\u274c Failed to show status: {e}")
        sys.exit(1)
    return None


def select_command(args: argparse.Namespace) -> Optional[int]:
    """Interactive story selection menu."""
    use_json = _use_json(args)
    project_dir = get_project_dir(args)
    ralph_dir = project_dir / ".ralph"
    prd_path = ralph_dir / "prd.json"

    if not prd_path.exists():
        if use_json:
            return json_error("No PRD found.")
        print("\u274c No PRD found. Run 'ralph process-prd <prd-file>' first.")
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
        if use_json:
            return json_output({"stories": [], "all_complete": True})
        print("\u2705 All stories are complete!")
        return None

    if use_json:
        return json_output({
            "stories": [
                {
                    "id": s["id"], "title": s["title"],
                    "status": s.get("status", "incomplete"),
                    "phase": s.get("phase"), "priority": s.get("priority"),
                }
                for s in incomplete_stories
            ],
            "all_complete": False,
        })

    print(f"\n\U0001f4cb Incomplete Stories ({len(incomplete_stories)}):\n")

    for i, story in enumerate(incomplete_stories, 1):
        status_emoji = "\U0001f504" if story.get("status") == "in_progress" else "\u23f3"
        phase_info = f" [Phase {story.get('phase')}]" if story.get('phase') else ""
        print(f"{i}. {status_emoji} {story['id']}: {story['title']}{phase_info}")
        print(f"   Priority: {story.get('priority', 'N/A')}")
        print()

    print("\U0001f4a1 To execute: ralph execute")
    return None


def build_prd_command(args: argparse.Namespace) -> Optional[int]:
    """Build PRD JSON using incremental builder (for large PRDs)."""
    from ralph.builder import PRDBuilder

    use_json = _use_json(args)
    prd_file = args.prd_file

    if not prd_file.exists():
        if use_json:
            return json_error(f"PRD file not found: {prd_file}")
        print(f"\u274c PRD file not found: {prd_file}")
        sys.exit(1)

    project_dir = get_project_dir(args)
    ralph_dir = project_dir / ".ralph"
    if not ralph_dir.exists():
        if use_json:
            return json_error("Ralph not initialized. Run 'ralph init' first.")
        print("\u26a0\ufe0f  Ralph not initialized. Run 'ralph init' first.")
        sys.exit(1)

    # Determine output path
    output_path = args.output if args.output else ralph_dir / "prd.json"

    # Build PRD using incremental builder
    builder = PRDBuilder()

    try:
        builder.build_from_prd(prd_file, output_path, model=args.model)
        if use_json:
            return json_output({"success": True, "output_path": str(output_path)})
        print("\n\u2705 PRD successfully built!")
        print(f"   Output: {output_path}")
        print("\n\U0001f4dd Next steps:")
        print(f"   1. Review the PRD: cat {output_path}")
        print("   2. Run: ralph execute")
    except Exception as e:
        if use_json:
            return json_error(f"Failed to build PRD: {e}")
        print(f"\u274c Failed to build PRD: {e}")
        sys.exit(1)
    return None


def validate_command(args: argparse.Namespace) -> Optional[int]:
    """Validate PRD JSON structure."""
    use_json = _use_json(args)
    project_dir = get_project_dir(args)
    ralph_dir = project_dir / ".ralph"
    prd_path = ralph_dir / "prd.json"

    if not prd_path.exists():
        if use_json:
            return json_error(f"PRD not found: {prd_path}")
        print(f"\u274c PRD not found: {prd_path}")
        sys.exit(1)

    # Load and validate PRD
    try:
        with open(prd_path, 'r') as f:
            prd = json.load(f)
    except json.JSONDecodeError as e:
        if use_json:
            return json_error(f"Invalid JSON: {e}")
        print(f"\u274c Invalid JSON: {e}")
        sys.exit(1)

    result = validate_prd(prd)

    if use_json:
        exit_code = EXIT_SUCCESS
        if not result.valid:
            exit_code = EXIT_ERROR
        elif args.strict and result.warnings:
            exit_code = EXIT_ERROR
        return json_output(result.to_dict(), exit_code)

    print(result.format())

    if not result.valid:
        sys.exit(1)

    if args.strict and result.warnings:
        print("\n\u274c Validation failed (strict mode: warnings treated as errors)")
        sys.exit(1)

    if result.warnings:
        print(
            "\n\u26a0\ufe0f  Warnings found but validation passed"
            " (use --strict to treat warnings as errors)"
        )
    return None


def summary_command(args: argparse.Namespace) -> Optional[int]:
    """Show PRD summary."""
    from ralph.tools import PRDManager, resolve_prd_path

    use_json = _use_json(args)
    project_dir = get_project_dir(args)
    try:
        prd_path = resolve_prd_path(project_dir)
    except FileNotFoundError as e:
        if use_json:
            return json_error(str(e))
        print(f"\u274c {e}")
        sys.exit(1)

    manager = PRDManager(prd_path)
    summary = manager.get_summary()

    if use_json:
        return json_output(summary)

    print(f"\n\U0001f4ca PRD Summary ({prd_path})")
    print(f"{'=' * 50}")
    print(f"Total Stories: {summary['total_stories']}")
    print(f"Completed: {summary['completed_stories']}")
    print(f"Skipped: {summary.get('skipped_stories', 0)}")
    print(f"Remaining: {summary['remaining_stories']}")
    print(f"Progress: {summary['completion_percentage']}%")
    print("\n\U0001f4cb By Phase:")

    phases_meta = manager.data.get("metadata", {}).get("phases", {})
    for phase, counts in sorted(summary["by_phase"].items()):
        phase_meta = phases_meta.get(str(phase), {})
        phase_name = phase_meta.get("name", f"Phase {phase}")
        closed_badge = " [CLOSED]" if manager.is_phase_closed(phase) else ""
        skipped = counts.get("skipped", 0)
        skipped_str = f", {skipped} skipped" if skipped > 0 else ""
        stats = f"{counts['completed']}/{counts['total']} complete{skipped_str}"
        print(f"  Phase {phase} ({phase_name}): {stats}{closed_badge}")
    return None


def close_phase_command(args: argparse.Namespace) -> Optional[int]:
    """Mark all incomplete stories in a phase as skipped."""
    from ralph.tools import PRDManager, resolve_prd_path

    use_json = _use_json(args)
    try:
        prd_path = resolve_prd_path(get_project_dir(args))
    except FileNotFoundError as e:
        if use_json:
            return json_error(str(e))
        print(f"\u274c {e}")
        sys.exit(1)

    manager = PRDManager(prd_path)
    skipped = manager.close_phase(args.phase_number)
    manager.save()

    if use_json:
        return json_output({"phase": args.phase_number, "skipped_story_ids": skipped})

    if skipped:
        print(f"\u2298 Closed phase {args.phase_number}, marked {len(skipped)} stories as skipped:")
        for story_id in skipped:
            print(f"  - {story_id}")
    else:
        print(f"No incomplete stories in phase {args.phase_number}")
    return None


def skip_story_command(args: argparse.Namespace) -> Optional[int]:
    """Mark a story as skipped."""
    from ralph.tools import PRDManager, resolve_prd_path

    use_json = _use_json(args)
    try:
        prd_path = resolve_prd_path(get_project_dir(args))
    except FileNotFoundError as e:
        if use_json:
            return json_error(str(e))
        print(f"\u274c {e}")
        sys.exit(1)

    manager = PRDManager(prd_path)
    if manager.skip_story(args.story_id):
        manager.save()
        if use_json:
            return json_output({"story_id": args.story_id, "status": "skipped", "success": True})
        print(f"\u2298 Skipped story {args.story_id}")
    else:
        if use_json:
            return json_error(f"Story {args.story_id} not found")
        print(f"\u274c Story {args.story_id} not found")
        sys.exit(1)
    return None


def start_story_command(args: argparse.Namespace) -> Optional[int]:
    """Mark a story as in_progress."""
    from ralph.tools import PRDManager, resolve_prd_path

    use_json = _use_json(args)
    try:
        prd_path = resolve_prd_path(get_project_dir(args))
    except FileNotFoundError as e:
        if use_json:
            return json_error(str(e))
        print(f"\u274c {e}")
        sys.exit(1)

    manager = PRDManager(prd_path)
    if manager.start_story(args.story_id):
        manager.save()
        if use_json:
            return json_output({
                "story_id": args.story_id, "status": "in_progress", "success": True,
            })
        print(f"\u25b6 Started story {args.story_id}")
    else:
        if use_json:
            return json_error(f"Story {args.story_id} not found")
        print(f"\u274c Story {args.story_id} not found")
        sys.exit(1)
    return None


def in_progress_command(args: argparse.Namespace) -> Optional[int]:
    """Show all in-progress stories."""
    from ralph.tools import PRDManager, resolve_prd_path

    use_json = _use_json(args)
    try:
        prd_path = resolve_prd_path(get_project_dir(args))
    except FileNotFoundError as e:
        if use_json:
            return json_error(str(e))
        print(f"\u274c {e}")
        sys.exit(1)

    manager = PRDManager(prd_path)
    in_progress = manager.get_in_progress()

    if use_json:
        return json_output([
            {"id": s["id"], "title": s["title"], "startedAt": s.get("startedAt")}
            for s in in_progress
        ])

    if in_progress:
        print("\n\u25b6 Stories currently in progress:")
        for story in in_progress:
            started = story.get("startedAt", "unknown")
            print(f"  {story['id']}: {story['title']} (started: {started})")
    else:
        print("No stories currently in progress")
    return None


def clear_stale_command(args: argparse.Namespace) -> Optional[int]:
    """Clear stale in_progress status."""
    from ralph.tools import PRDManager, resolve_prd_path

    use_json = _use_json(args)
    try:
        prd_path = resolve_prd_path(get_project_dir(args))
    except FileNotFoundError as e:
        if use_json:
            return json_error(str(e))
        print(f"\u274c {e}")
        sys.exit(1)

    manager = PRDManager(prd_path)
    cleared = manager.clear_stale_in_progress(args.max_age_hours)
    manager.save()

    if use_json:
        return json_output({"cleared_story_ids": cleared})

    if cleared:
        print(f"Cleared stale in_progress status from {len(cleared)} stories:")
        for story_id in cleared:
            print(f"  - {story_id}")
    else:
        print("No stale in_progress stories found")
    return None


def list_stories_command(args: argparse.Namespace) -> Optional[int]:
    """List stories with optional filters."""
    from ralph.tools import PRDManager, resolve_prd_path

    use_json = _use_json(args)
    try:
        prd_path = resolve_prd_path(get_project_dir(args))
    except FileNotFoundError as e:
        if use_json:
            return json_error(str(e))
        print(f"\u274c {e}")
        sys.exit(1)

    manager = PRDManager(prd_path)
    stories = manager.list_stories(
        phase=args.phase if hasattr(args, 'phase') and args.phase else None,
        status=args.status if hasattr(args, 'status') and args.status else None
    )

    if use_json:
        return json_output([
            {
                "id": s["id"],
                "title": s["title"],
                "status": s.get("status", "incomplete"),
                "phase": s.get("phase"),
                "priority": s.get("priority"),
            }
            for s in stories
        ])

    if not stories:
        print("No stories found matching filters")
        return None

    for story in stories:
        status_icon = "\u2705" if story.get("status") == "complete" else "\u23f3"
        print(f"{status_icon} {story['id']}: {story['title']} (Phase {story.get('phase', '?')})")
    return None


def view_command(args: argparse.Namespace) -> Optional[int]:
    """View PRD progress with pretty formatting."""
    from ralph.tools import resolve_prd_path
    from ralph.viewer import run_viewer

    try:
        prd_path = resolve_prd_path(get_project_dir(args))
    except FileNotFoundError as e:
        print(f"\u274c {e}")
        sys.exit(1)

    try:
        run_viewer(
            prd_path,
            watch=not args.once,
            refresh_interval=args.interval,
            expand_closed=args.expand,
        )
    except Exception as e:
        print(f"\u274c Failed to run viewer: {e}")
        sys.exit(1)
    return None
