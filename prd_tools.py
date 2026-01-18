#!/usr/bin/env python3
"""
PRD Management Tools

Utility scripts for manipulating prd.json files programmatically.
Avoids manual JSON editing and reduces errors.

Usage:
    python prd_tools.py update-phases <prd_file> <phase_mapping_json>
    python prd_tools.py list-stories <prd_file> [--phase N] [--status STATUS]
    python prd_tools.py update-story <prd_file> <story_id> [--phase N] [--status STATUS]
    python prd_tools.py summary <prd_file>
    python prd_tools.py close-phase <prd_file> <phase_number>
    python prd_tools.py skip-story <prd_file> <story_id>
    python prd_tools.py start-story <prd_file> <story_id>
    python prd_tools.py in-progress <prd_file>
    python prd_tools.py clear-stale <prd_file> [--max-age-hours N]

Story Status Values:
    "incomplete"   - Not started (default)
    "in_progress"  - Currently being worked on
    "complete"     - Finished successfully
    "skipped"      - Intentionally closed without completing
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


class PRDManager:
    """Manager for PRD JSON file operations."""

    def __init__(self, prd_path: str):
        self.prd_path = Path(prd_path)
        self.data = self._load()

    def _load(self) -> dict:
        """Load PRD JSON file."""
        with open(self.prd_path) as f:
            return json.load(f)

    def save(self):
        """Save PRD JSON file."""
        self.data["metadata"]["lastUpdatedAt"] = datetime.now().isoformat()
        with open(self.prd_path, "w") as f:
            json.dump(self.data, f, indent=2)

    def update_story_phase(self, story_id: str, new_phase: int):
        """Update a story's phase number."""
        for story in self.data["userStories"]:
            if story["id"] == story_id:
                story["phase"] = new_phase
                return True
        return False

    def update_story_status(self, story_id: str, status: str):
        """Update a story's status (incomplete, in_progress, complete, skipped)."""
        for story in self.data["userStories"]:
            if story["id"] == story_id:
                story["status"] = status
                # Update metadata
                self.data["metadata"]["completedStories"] = sum(
                    1 for s in self.data["userStories"] if s.get("status") == "complete"
                )
                return True
        return False

    def bulk_update_phases(self, phase_mapping: dict[str, int]):
        """
        Bulk update story phases.

        Args:
            phase_mapping: Dict mapping story_id to new phase number
                          e.g. {"US-030": 3, "US-031": 3, "US-040": 1}
        """
        updated = []
        for story_id, new_phase in phase_mapping.items():
            if self.update_story_phase(story_id, new_phase):
                updated.append(story_id)
        return updated

    def update_phase_metadata(self, phase_definitions: dict[str, dict]):
        """
        Update the phases metadata section.

        Args:
            phase_definitions: Dict with phase numbers as keys, each containing:
                - name: Phase name
                - description: Phase description
                - stories: List of story IDs in this phase

        Example:
            {
                "1": {
                    "name": "RSS & Testing",
                    "description": "RSS feeds and integration tests",
                    "stories": ["US-040", "US-041", "US-042", "US-043", "US-048"]
                }
            }
        """
        self.data["metadata"]["phases"] = phase_definitions

    def list_stories(self, phase: int | None = None, status: str | None = None) -> list[dict]:
        """
        List stories with optional filters.

        Args:
            phase: Filter by phase number (None = all)
            status: Filter by status ('complete', 'incomplete', 'in_progress', 'skipped', None = all)
        """
        stories = self.data["userStories"]

        if phase is not None:
            stories = [s for s in stories if s.get("phase") == phase]

        if status is not None:
            stories = [s for s in stories if s.get("status", "incomplete") == status]

        return stories

    def get_summary(self) -> dict:
        """Get summary statistics."""
        total = len(self.data["userStories"])
        completed = sum(1 for s in self.data["userStories"] if s.get("status") == "complete")
        skipped = sum(1 for s in self.data["userStories"] if s.get("status") == "skipped")

        # Count by phase
        phase_counts: dict[int, dict[str, int]] = {}
        for story in self.data["userStories"]:
            phase = story.get("phase", 0)
            if phase not in phase_counts:
                phase_counts[phase] = {"total": 0, "completed": 0, "remaining": 0, "skipped": 0}
            phase_counts[phase]["total"] += 1
            status = story.get("status", "incomplete")
            if status == "complete":
                phase_counts[phase]["completed"] += 1
            elif status == "skipped":
                phase_counts[phase]["skipped"] += 1
                phase_counts[phase]["remaining"] += 1  # Skipped still counts as remaining
            else:
                phase_counts[phase]["remaining"] += 1

        return {
            "total_stories": total,
            "completed_stories": completed,
            "skipped_stories": skipped,
            "remaining_stories": total - completed,
            "completion_percentage": round(completed / total * 100, 1) if total > 0 else 0,
            "by_phase": phase_counts,
        }

    def reorganize_phases(self, new_phase_structure: dict[int, dict]):
        """
        Completely reorganize phases - updates both story phases and metadata.

        Args:
            new_phase_structure: Dict with phase number as key, containing:
                - name: Phase name
                - description: Phase description
                - story_ids: List of story IDs to assign to this phase

        Example:
            {
                1: {
                    "name": "RSS & Testing",
                    "description": "RSS feeds and integration tests",
                    "story_ids": ["US-040", "US-041", "US-042", "US-043", "US-048"]
                },
                2: {
                    "name": "Self-Improvement",
                    "description": "Full self-improvement cycle",
                    "story_ids": ["US-037", "US-038", ...]
                }
            }
        """
        # Update individual story phases
        for phase_num, phase_info in new_phase_structure.items():
            for story_id in phase_info["story_ids"]:
                self.update_story_phase(story_id, phase_num)

        # Build phase metadata
        phase_metadata = {}
        for phase_num, phase_info in new_phase_structure.items():
            phase_metadata[str(phase_num)] = {
                "name": phase_info["name"],
                "description": phase_info["description"],
                "stories": phase_info["story_ids"],
            }

        self.update_phase_metadata(phase_metadata)

    def close_phase(self, phase: int) -> list[str]:
        """
        Mark all incomplete stories in a phase as skipped.

        Args:
            phase: Phase number to close

        Returns:
            List of story IDs that were marked as skipped
        """
        skipped = []
        for story in self.data["userStories"]:
            if story.get("phase") == phase and story.get("status", "incomplete") not in ("complete", "skipped"):
                story["status"] = "skipped"
                story["skippedAt"] = datetime.now().isoformat()
                skipped.append(story["id"])
        return skipped

    def skip_story(self, story_id: str) -> bool:
        """
        Mark a story as skipped.

        Args:
            story_id: ID of the story to skip

        Returns:
            True if story was found and skipped, False otherwise
        """
        for story in self.data["userStories"]:
            if story["id"] == story_id:
                story["status"] = "skipped"
                story["skippedAt"] = datetime.now().isoformat()
                return True
        return False

    def start_story(self, story_id: str) -> bool:
        """
        Mark a story as in_progress with startedAt timestamp.

        Args:
            story_id: ID of the story to start

        Returns:
            True if story was found and started, False otherwise
        """
        for story in self.data["userStories"]:
            if story["id"] == story_id:
                story["status"] = "in_progress"
                story["startedAt"] = datetime.now().isoformat()
                return True
        return False

    def get_in_progress(self) -> list[dict]:
        """
        Get all stories currently marked as in_progress.

        Returns:
            List of story dicts with status='in_progress'
        """
        return [s for s in self.data["userStories"] if s.get("status") == "in_progress"]

    def clear_stale_in_progress(self, max_age_hours: int = 24) -> list[str]:
        """
        Clear in_progress status from stories that started too long ago.

        Args:
            max_age_hours: Maximum hours a story can be in_progress before being cleared

        Returns:
            List of story IDs that had their in_progress status cleared
        """
        cleared = []
        cutoff = datetime.now() - timedelta(hours=max_age_hours)

        for story in self.data["userStories"]:
            if story.get("status") == "in_progress":
                started_at_str = story.get("startedAt")
                if started_at_str:
                    try:
                        started_at = datetime.fromisoformat(started_at_str)
                        if started_at < cutoff:
                            # Clear the in_progress status but don't set to skipped
                            story.pop("status", None)
                            cleared.append(story["id"])
                    except ValueError:
                        # Invalid date format, clear it
                        story.pop("status", None)
                        cleared.append(story["id"])
                else:
                    # No startedAt timestamp, clear it
                    story.pop("status", None)
                    cleared.append(story["id"])
        return cleared

    def is_phase_closed(self, phase: int) -> bool:
        """
        Check if a phase is closed (all stories either complete or skipped).

        Args:
            phase: Phase number to check

        Returns:
            True if all stories in phase are complete or skipped
        """
        phase_stories = [s for s in self.data["userStories"] if s.get("phase") == phase]
        if not phase_stories:
            return False
        return all(s.get("status") in ("complete", "skipped") for s in phase_stories)


def main():
    """CLI interface for PRD tools."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "update-phases":
        if len(sys.argv) < 4:
            print("Usage: prd_tools.py update-phases <prd_file> <phase_mapping_json>")
            sys.exit(1)

        prd_file = sys.argv[2]
        phase_mapping_json = sys.argv[3]

        with open(phase_mapping_json) as f:
            phase_mapping = json.load(f)

        manager = PRDManager(prd_file)
        updated = manager.bulk_update_phases(phase_mapping)
        manager.save()

        print(f"Updated {len(updated)} stories: {', '.join(updated)}")

    elif command == "list-stories":
        if len(sys.argv) < 3:
            print("Usage: prd_tools.py list-stories <prd_file> [--phase N] [--status STATUS]")
            sys.exit(1)

        prd_file = sys.argv[2]
        phase = None
        status = None

        # Parse optional flags
        for i in range(3, len(sys.argv), 2):
            if sys.argv[i] == "--phase":
                phase = int(sys.argv[i + 1])
            elif sys.argv[i] == "--status":
                status = sys.argv[i + 1]

        manager = PRDManager(prd_file)
        stories = manager.list_stories(phase=phase, status=status)

        for story in stories:
            status_icon = "✅" if story.get("status") == "complete" else "⏳"
            print(
                f"{status_icon} {story['id']}: {story['title']} (Phase {story.get('phase', '?')})"
            )

    elif command == "update-story":
        if len(sys.argv) < 4:
            print(
                "Usage: prd_tools.py update-story <prd_file> <story_id> "
                "[--phase N] [--status STATUS]"
            )
            sys.exit(1)

        prd_file = sys.argv[2]
        story_id = sys.argv[3]

        manager = PRDManager(prd_file)

        # Parse optional flags
        for i in range(4, len(sys.argv), 2):
            if sys.argv[i] == "--phase":
                new_phase = int(sys.argv[i + 1])
                if manager.update_story_phase(story_id, new_phase):
                    print(f"Updated {story_id} to phase {new_phase}")
                else:
                    print(f"Story {story_id} not found")
                    sys.exit(1)
            elif sys.argv[i] == "--status":
                new_status = sys.argv[i + 1].lower()
                if new_status in ["true", "done"]:
                    new_status = "complete"
                elif new_status == "false":
                    new_status = "incomplete"
                if manager.update_story_status(story_id, new_status):
                    print(f"Updated {story_id} status to {new_status}")
                else:
                    print(f"Story {story_id} not found")
                    sys.exit(1)

        manager.save()

    elif command == "summary":
        if len(sys.argv) < 3:
            print("Usage: prd_tools.py summary <prd_file>")
            sys.exit(1)

        prd_file = sys.argv[2]
        manager = PRDManager(prd_file)
        summary = manager.get_summary()

        print("\n📊 PRD Summary")
        print(f"{'=' * 50}")
        print(f"Total Stories: {summary['total_stories']}")
        print(f"Completed: {summary['completed_stories']}")
        print(f"Skipped: {summary.get('skipped_stories', 0)}")
        print(f"Remaining: {summary['remaining_stories']}")
        print(f"Progress: {summary['completion_percentage']}%")
        print("\n📋 By Phase:")

        for phase, counts in sorted(summary["by_phase"].items()):
            phase_meta = manager.data["metadata"]["phases"].get(str(phase), {})
            phase_name = phase_meta.get("name", f"Phase {phase}")
            closed_badge = " [CLOSED]" if manager.is_phase_closed(phase) else ""
            skipped = counts.get("skipped", 0)
            skipped_str = f", {skipped} skipped" if skipped > 0 else ""
            stats = f"{counts['completed']}/{counts['total']} complete{skipped_str}"
            print(f"  Phase {phase} ({phase_name}): {stats}{closed_badge}")

    elif command == "close-phase":
        if len(sys.argv) < 4:
            print("Usage: prd_tools.py close-phase <prd_file> <phase_number>")
            sys.exit(1)

        prd_file = sys.argv[2]
        phase = int(sys.argv[3])

        manager = PRDManager(prd_file)
        skipped = manager.close_phase(phase)
        manager.save()

        if skipped:
            print(f"⊘ Closed phase {phase}, marked {len(skipped)} stories as skipped:")
            for story_id in skipped:
                print(f"  - {story_id}")
        else:
            print(f"No incomplete stories in phase {phase}")

    elif command == "skip-story":
        if len(sys.argv) < 4:
            print("Usage: prd_tools.py skip-story <prd_file> <story_id>")
            sys.exit(1)

        prd_file = sys.argv[2]
        story_id = sys.argv[3]

        manager = PRDManager(prd_file)
        if manager.skip_story(story_id):
            manager.save()
            print(f"⊘ Skipped story {story_id}")
        else:
            print(f"Story {story_id} not found")
            sys.exit(1)

    elif command == "start-story":
        if len(sys.argv) < 4:
            print("Usage: prd_tools.py start-story <prd_file> <story_id>")
            sys.exit(1)

        prd_file = sys.argv[2]
        story_id = sys.argv[3]

        manager = PRDManager(prd_file)
        if manager.start_story(story_id):
            manager.save()
            print(f"▶ Started story {story_id}")
        else:
            print(f"Story {story_id} not found")
            sys.exit(1)

    elif command == "in-progress":
        if len(sys.argv) < 3:
            print("Usage: prd_tools.py in-progress <prd_file>")
            sys.exit(1)

        prd_file = sys.argv[2]
        manager = PRDManager(prd_file)
        in_progress = manager.get_in_progress()

        if in_progress:
            print("\n▶ Stories currently in progress:")
            for story in in_progress:
                started = story.get("startedAt", "unknown")
                print(f"  {story['id']}: {story['title']} (started: {started})")
        else:
            print("No stories currently in progress")

    elif command == "clear-stale":
        if len(sys.argv) < 3:
            print("Usage: prd_tools.py clear-stale <prd_file> [--max-age-hours N]")
            sys.exit(1)

        prd_file = sys.argv[2]
        max_age = 24  # default

        # Parse optional flags
        for i in range(3, len(sys.argv), 2):
            if sys.argv[i] == "--max-age-hours":
                max_age = int(sys.argv[i + 1])

        manager = PRDManager(prd_file)
        cleared = manager.clear_stale_in_progress(max_age)
        manager.save()

        if cleared:
            print(f"Cleared stale in_progress status from {len(cleared)} stories:")
            for story_id in cleared:
                print(f"  - {story_id}")
        else:
            print("No stale in_progress stories found")

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
