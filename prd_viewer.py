#!/usr/bin/env python3
"""PRD Viewer - Pretty terminal display of PRD progress with live updates."""

import argparse
import json
import select
import sys
import termios
import time
import tty
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.text import Text


def load_prd(path: Path) -> dict[str, Any] | None:
    """Load PRD from JSON file."""
    try:
        with open(path) as f:
            data: dict[str, Any] = json.load(f)
            return data
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None


def get_story_by_id(prd: dict[str, Any], story_id: str) -> dict[str, Any] | None:
    """Get a story by its ID."""
    stories: list[dict[str, Any]] = prd.get("userStories", [])
    for story in stories:
        if story.get("id") == story_id:
            return story
    return None


def format_duration(seconds: float | None) -> str:
    """Format duration in human-readable form."""
    if seconds is None:
        return ""
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f}m"
    hours = minutes / 60
    return f"{hours:.1f}h"


def is_phase_closed(phase_stories: list[dict[str, Any]]) -> bool:
    """Check if a phase is closed (all stories either complete or skipped)."""
    if not phase_stories:
        return False
    return all(
        s.get("status") in ("complete", "skipped") for s in phase_stories
    )


def build_display(
    prd: dict[str, Any] | None, path: Path, expand_closed: bool = False
) -> Table:
    """Build the Rich table display for the PRD."""
    if prd is None:
        table = Table(title="PRD Viewer", show_header=False)
        table.add_row(Text(f"Could not load PRD from {path}", style="red"))
        return table

    # Get stories
    stories: list[dict[str, Any]] = prd.get("userStories", [])
    total = len(stories)
    completed = sum(1 for s in stories if s.get("status") == "complete")
    project = prd.get("project", "Unknown Project")

    # Derive phases from stories
    phases: dict[int, list[dict[str, Any]]] = {}
    for story in stories:
        phase_num = story.get("phase", 0)
        if phase_num not in phases:
            phases[phase_num] = []
        phases[phase_num].append(story)

    # Calculate progress percentage
    progress_pct = (completed / total * 100) if total > 0 else 0

    # Build progress bar
    bar_width = 30
    filled = int(bar_width * progress_pct / 100)
    progress_bar = "[green]" + "█" * filled + "[/green]" + "░" * (bar_width - filled)

    # Create main table
    expand_hint = " [dim](Enter to expand/collapse)[/dim]" if not expand_closed else ""
    title = (
        f"[bold]{project}[/bold] - {progress_bar} "
        f"{completed}/{total} ({progress_pct:.0f}%){expand_hint}"
    )
    table = Table(title=title, show_header=True, header_style="bold cyan", expand=True)
    table.add_column("", width=2, justify="center")  # Status icon
    table.add_column("ID", width=10, no_wrap=True)
    table.add_column("Title", ratio=3)
    table.add_column("Time", width=8, justify="right")

    # Find the current in-progress story
    in_progress_id = None
    next_up_id = None

    # First pass: find any story with status="in_progress"
    for story in stories:
        if story.get("status") == "in_progress":
            in_progress_id = story.get("id")
            break

    # Second pass: find first incomplete (non-skipped) story as "next up"
    if not in_progress_id:
        for phase_num in sorted(phases.keys()):
            if phase_num == 0:
                continue  # Skip unphased
            for story in phases[phase_num]:
                # Skip if complete or skipped
                if story.get("status", "incomplete") not in ("complete", "skipped"):
                    next_up_id = story.get("id")
                    break
            if next_up_id:
                break

    # Process each phase
    for phase_num in sorted(phases.keys()):
        if phase_num == 0:
            continue  # Skip unphased stories
        phase_stories = phases[phase_num]
        phase_name = f"Phase {phase_num}"

        # Count stats in phase
        phase_completed = sum(1 for s in phase_stories if s.get("status") == "complete")
        phase_skipped = sum(1 for s in phase_stories if s.get("status") == "skipped")
        phase_total = len(phase_stories)
        phase_closed = is_phase_closed(phase_stories)

        # Phase header
        if phase_completed == phase_total:
            phase_status = "[green]✓[/green]"
        elif phase_closed:
            phase_status = "[cyan]⊘[/cyan]"  # Closed but not all completed
        elif phase_completed > 0:
            phase_status = "[yellow]◐[/yellow]"
        else:
            phase_status = "[dim]○[/dim]"

        # Build phase summary
        skipped_str = f", {phase_skipped} skipped" if phase_skipped > 0 else ""
        closed_badge = (
            " [CLOSED]" if phase_closed and phase_completed < phase_total else ""
        )
        collapsed_hint = " ▸" if phase_closed and not expand_closed else ""

        phase_summary = (
            f"[bold]{phase_name}[/bold] "
            f"({phase_completed}/{phase_total}{skipped_str}){closed_badge}{collapsed_hint}"
        )
        table.add_row(
            phase_status,
            f"[bold]Phase {phase_num}[/bold]",
            phase_summary,
            "",
            style="on grey15" if not phase_closed else "on grey7",
        )

        # Skip stories if phase is closed and not expanding
        if phase_closed and not expand_closed:
            continue

        # Stories in phase
        for story in phase_stories:
            story_id = story.get("id", "")
            story_status = story.get("status", "incomplete")
            title = story.get("title", "Unknown")
            duration = story.get("actualDuration")
            iteration = story.get("iterationNumber")

            # Determine status icon
            if story_status == "complete":
                icon = "[green]✓[/green]"
                style = "dim"
            elif story_status == "skipped":
                icon = "[cyan]⊘[/cyan]"  # Skipped
                style = "dim cyan"
            elif story_status == "in_progress" or story_id == in_progress_id:
                icon = "[yellow]▶[/yellow]"  # Actually in progress
                style = "bold yellow"
            elif story_id == next_up_id:
                icon = "[blue]→[/blue]"  # Next up
                style = "blue"
            else:
                icon = "[dim]○[/dim]"
                style = "dim"

            duration_str = format_duration(duration)
            if iteration and story_status != "complete":
                duration_str = f"iter {iteration}"

            table.add_row(
                icon,
                f"  {story_id}",
                title,
                duration_str,
                style=style,
            )

    return table


def get_file_mtime(path: Path) -> float:
    """Get file modification time, or 0 if file doesn't exist."""
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return 0


def check_keypress() -> str | None:
    """Check for keypress without blocking. Returns the key or None."""
    if select.select([sys.stdin], [], [], 0)[0]:
        return sys.stdin.read(1)
    return None


def run_viewer(
    prd_path: Path,
    watch: bool = True,
    refresh_interval: float = 1.0,
    expand_closed: bool = False,
) -> None:
    """Run the PRD viewer."""
    console = Console()

    if not watch:
        # One-shot display
        prd = load_prd(prd_path)
        table = build_display(prd, prd_path, expand_closed=expand_closed)
        console.print(table)
        return

    # Live updating display with keyboard toggle
    last_mtime = 0.0
    prd = load_prd(prd_path)

    # Save terminal settings and set raw mode for keypress detection
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())

        with Live(
            build_display(prd, prd_path, expand_closed),
            console=console,
            refresh_per_second=1,
        ) as live:
            while True:
                # Check for keypress
                key = check_keypress()
                if key == "\n" or key == " ":  # Enter or space toggles
                    expand_closed = not expand_closed
                    live.update(build_display(prd, prd_path, expand_closed))
                elif key == "q":  # q to quit
                    break

                # Check for file changes
                current_mtime = get_file_mtime(prd_path)
                if current_mtime != last_mtime:
                    last_mtime = current_mtime
                    prd = load_prd(prd_path)
                    live.update(build_display(prd, prd_path, expand_closed))

                time.sleep(refresh_interval)
    except KeyboardInterrupt:
        pass
    finally:
        # Restore terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="View PRD progress with pretty formatting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python prd_viewer.py ~/myproject/       # Watch .ralph/prd.json in project
  python prd_viewer.py prd.json           # Watch specific file
  python prd_viewer.py --once             # Display once and exit
  python prd_viewer.py --expand           # Show all stories (don't collapse)
  python prd_viewer.py -i 0.5             # Refresh every 0.5 seconds

Interactive Controls (watch mode):
  Enter/Space  Toggle expand/collapse closed phases
  q            Quit

Status Icons:
  ✓  Completed
  ▶  In progress
  →  Next up
  ⊘  Skipped
  ○  Pending

Phase Status:
  ✓  All stories completed
  ⊘  Closed (all stories completed or skipped)
  ◐  Partially complete
  ○  Not started
        """,
    )
    parser.add_argument(
        "path",
        type=Path,
        nargs="?",
        default=Path.cwd(),
        help="Project directory (with .ralph/) or path to prd.json (default: current dir)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Display once and exit (no watching)",
    )
    parser.add_argument(
        "--expand",
        "-e",
        action="store_true",
        help="Expand closed phases (show all stories)",
    )
    parser.add_argument(
        "-i",
        "--interval",
        type=float,
        default=1.0,
        help="Refresh interval in seconds (default: 1.0)",
    )

    args = parser.parse_args()

    # Resolve path - check if it's a directory (project) or file
    input_path = Path(args.path).resolve()

    if input_path.is_dir():
        # It's a directory - look for .ralph/prd.json
        prd_path = input_path / ".ralph" / "prd.json"
        if not prd_path.exists():
            # Fallback to prd.json in directory
            prd_path = input_path / "prd.json"
    else:
        # It's a file path
        prd_path = input_path

    run_viewer(
        prd_path,
        watch=not args.once,
        refresh_interval=args.interval,
        expand_closed=args.expand,
    )


if __name__ == "__main__":
    main()
