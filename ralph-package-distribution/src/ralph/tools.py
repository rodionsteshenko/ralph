"""PRD management tools for manipulating prd.json files."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


def resolve_prd_path(project_dir: Optional[Path] = None) -> Path:
    """Resolve PRD path from project directory.

    Args:
        project_dir: Project directory (defaults to current directory)

    Returns:
        Path to prd.json file

    Raises:
        FileNotFoundError: If prd.json not found
    """
    if project_dir is None:
        project_dir = Path.cwd()

    # Look for .ralph/prd.json
    prd_path = project_dir / ".ralph" / "prd.json"
    if prd_path.exists():
        return prd_path

    # Fallback to prd.json in directory
    prd_path = project_dir / "prd.json"
    if prd_path.exists():
        return prd_path

    raise FileNotFoundError(f"No prd.json found in {project_dir}/.ralph/ or {project_dir}/")


class PRDManager:
    """Manager for PRD JSON file operations."""

    def __init__(self, prd_path: Path):
        """Initialize PRD manager.

        Args:
            prd_path: Path to prd.json file
        """
        self.prd_path = prd_path
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load PRD JSON file."""
        with open(self.prd_path) as f:
            return json.load(f)  # type: ignore[no-any-return]

    def save(self) -> None:
        """Save PRD JSON file."""
        self.data["metadata"]["lastUpdatedAt"] = datetime.now().isoformat()
        with open(self.prd_path, "w") as f:
            json.dump(self.data, f, indent=2)

    def update_story_phase(self, story_id: str, new_phase: int) -> bool:
        """Update a story's phase number.

        Args:
            story_id: Story ID
            new_phase: New phase number

        Returns:
            True if story was found and updated
        """
        for story in self.data["userStories"]:
            if story["id"] == story_id:
                story["phase"] = new_phase
                return True
        return False

    def update_story_status(self, story_id: str, status: str) -> bool:
        """Update a story's status.

        Args:
            story_id: Story ID
            status: New status (incomplete, in_progress, complete, skipped)

        Returns:
            True if story was found and updated
        """
        for story in self.data["userStories"]:
            if story["id"] == story_id:
                story["status"] = status
                # Update metadata
                self.data["metadata"]["completedStories"] = sum(
                    1 for s in self.data["userStories"] if s.get("status") == "complete"
                )
                return True
        return False

    def bulk_update_phases(self, phase_mapping: Dict[str, int]) -> List[str]:
        """Bulk update story phases.

        Args:
            phase_mapping: Dict mapping story_id to new phase number

        Returns:
            List of story IDs that were updated
        """
        updated = []
        for story_id, new_phase in phase_mapping.items():
            if self.update_story_phase(story_id, new_phase):
                updated.append(story_id)
        return updated

    def list_stories(
        self, phase: Optional[int] = None, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List stories with optional filters.

        Args:
            phase: Filter by phase number (None = all)
            status: Filter by status (None = all)

        Returns:
            List of story dicts matching filters
        """
        stories = self.data["userStories"]

        if phase is not None:
            stories = [s for s in stories if s.get("phase") == phase]

        if status is not None:
            stories = [s for s in stories if s.get("status", "incomplete") == status]

        return stories  # type: ignore[no-any-return]

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics.

        Returns:
            Dict with summary statistics
        """
        total = len(self.data["userStories"])
        completed = sum(1 for s in self.data["userStories"] if s.get("status") == "complete")
        skipped = sum(1 for s in self.data["userStories"] if s.get("status") == "skipped")

        # Count by phase
        phase_counts: Dict[int, Dict[str, int]] = {}
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
                phase_counts[phase]["remaining"] += 1
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

    def close_phase(self, phase: int) -> List[str]:
        """Mark all incomplete stories in a phase as skipped.

        Args:
            phase: Phase number to close

        Returns:
            List of story IDs that were marked as skipped
        """
        skipped = []
        for story in self.data["userStories"]:
            if story.get("phase") == phase and story.get("status", "incomplete") not in (
                "complete",
                "skipped",
            ):
                story["status"] = "skipped"
                story["skippedAt"] = datetime.now().isoformat()
                skipped.append(story["id"])
        return skipped

    def skip_story(self, story_id: str) -> bool:
        """Mark a story as skipped.

        Args:
            story_id: ID of the story to skip

        Returns:
            True if story was found and skipped
        """
        for story in self.data["userStories"]:
            if story["id"] == story_id:
                story["status"] = "skipped"
                story["skippedAt"] = datetime.now().isoformat()
                return True
        return False

    def start_story(self, story_id: str) -> bool:
        """Mark a story as in_progress with startedAt timestamp.

        Args:
            story_id: ID of the story to start

        Returns:
            True if story was found and started
        """
        for story in self.data["userStories"]:
            if story["id"] == story_id:
                story["status"] = "in_progress"
                story["startedAt"] = datetime.now().isoformat()
                return True
        return False

    def get_in_progress(self) -> List[Dict[str, Any]]:
        """Get all stories currently marked as in_progress.

        Returns:
            List of story dicts with status='in_progress'
        """
        return [s for s in self.data["userStories"] if s.get("status") == "in_progress"]

    def clear_stale_in_progress(self, max_age_hours: int = 24) -> List[str]:
        """Clear in_progress status from stories that started too long ago.

        Args:
            max_age_hours: Maximum hours a story can be in_progress

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
        """Check if a phase is closed (all stories complete or skipped).

        Args:
            phase: Phase number to check

        Returns:
            True if all stories in phase are complete or skipped
        """
        phase_stories = [s for s in self.data["userStories"] if s.get("phase") == phase]
        if not phase_stories:
            return False
        return all(s.get("status") in ("complete", "skipped") for s in phase_stories)
