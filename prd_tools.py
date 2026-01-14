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
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


class PRDManager:
    """Manager for PRD JSON file operations."""

    def __init__(self, prd_path: str):
        self.prd_path = Path(prd_path)
        self.data = self._load()

    def _load(self) -> Dict:
        """Load PRD JSON file."""
        with open(self.prd_path, 'r') as f:
            return json.load(f)

    def save(self):
        """Save PRD JSON file."""
        self.data['metadata']['lastUpdatedAt'] = datetime.now().isoformat()
        with open(self.prd_path, 'w') as f:
            json.dump(self.data, f, indent=2)

    def update_story_phase(self, story_id: str, new_phase: int):
        """Update a story's phase number."""
        for story in self.data['userStories']:
            if story['id'] == story_id:
                story['phase'] = new_phase
                return True
        return False

    def update_story_status(self, story_id: str, passes: bool):
        """Update a story's completion status."""
        for story in self.data['userStories']:
            if story['id'] == story_id:
                story['passes'] = passes
                # Update metadata
                if passes:
                    self.data['metadata']['completedStories'] = sum(
                        1 for s in self.data['userStories'] if s.get('passes', False)
                    )
                return True
        return False

    def bulk_update_phases(self, phase_mapping: Dict[str, int]):
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

    def update_phase_metadata(self, phase_definitions: Dict[str, Dict]):
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
        self.data['metadata']['phases'] = phase_definitions

    def list_stories(self, phase: Optional[int] = None, status: Optional[str] = None) -> List[Dict]:
        """
        List stories with optional filters.

        Args:
            phase: Filter by phase number (None = all)
            status: Filter by status ('complete', 'incomplete', None = all)
        """
        stories = self.data['userStories']

        if phase is not None:
            stories = [s for s in stories if s.get('phase') == phase]

        if status == 'complete':
            stories = [s for s in stories if s.get('passes', False)]
        elif status == 'incomplete':
            stories = [s for s in stories if not s.get('passes', False)]

        return stories

    def get_summary(self) -> Dict:
        """Get summary statistics."""
        total = len(self.data['userStories'])
        completed = sum(1 for s in self.data['userStories'] if s.get('passes', False))

        # Count by phase
        phase_counts = {}
        for story in self.data['userStories']:
            phase = story.get('phase', 0)
            if phase not in phase_counts:
                phase_counts[phase] = {'total': 0, 'completed': 0, 'remaining': 0}
            phase_counts[phase]['total'] += 1
            if story.get('passes', False):
                phase_counts[phase]['completed'] += 1
            else:
                phase_counts[phase]['remaining'] += 1

        return {
            'total_stories': total,
            'completed_stories': completed,
            'remaining_stories': total - completed,
            'completion_percentage': round(completed / total * 100, 1) if total > 0 else 0,
            'by_phase': phase_counts
        }

    def reorganize_phases(self, new_phase_structure: Dict[int, Dict]):
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
            for story_id in phase_info['story_ids']:
                self.update_story_phase(story_id, phase_num)

        # Build phase metadata
        phase_metadata = {}
        for phase_num, phase_info in new_phase_structure.items():
            phase_metadata[str(phase_num)] = {
                'name': phase_info['name'],
                'description': phase_info['description'],
                'stories': phase_info['story_ids']
            }

        self.update_phase_metadata(phase_metadata)


def main():
    """CLI interface for PRD tools."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == 'update-phases':
        if len(sys.argv) < 4:
            print("Usage: prd_tools.py update-phases <prd_file> <phase_mapping_json>")
            sys.exit(1)

        prd_file = sys.argv[2]
        phase_mapping_json = sys.argv[3]

        with open(phase_mapping_json, 'r') as f:
            phase_mapping = json.load(f)

        manager = PRDManager(prd_file)
        updated = manager.bulk_update_phases(phase_mapping)
        manager.save()

        print(f"Updated {len(updated)} stories: {', '.join(updated)}")

    elif command == 'list-stories':
        if len(sys.argv) < 3:
            print("Usage: prd_tools.py list-stories <prd_file> [--phase N] [--status STATUS]")
            sys.exit(1)

        prd_file = sys.argv[2]
        phase = None
        status = None

        # Parse optional flags
        for i in range(3, len(sys.argv), 2):
            if sys.argv[i] == '--phase':
                phase = int(sys.argv[i + 1])
            elif sys.argv[i] == '--status':
                status = sys.argv[i + 1]

        manager = PRDManager(prd_file)
        stories = manager.list_stories(phase=phase, status=status)

        for story in stories:
            status_icon = "✅" if story.get('passes', False) else "⏳"
            print(f"{status_icon} {story['id']}: {story['title']} (Phase {story.get('phase', '?')})")

    elif command == 'update-story':
        if len(sys.argv) < 4:
            print("Usage: prd_tools.py update-story <prd_file> <story_id> [--phase N] [--status STATUS]")
            sys.exit(1)

        prd_file = sys.argv[2]
        story_id = sys.argv[3]

        manager = PRDManager(prd_file)

        # Parse optional flags
        for i in range(4, len(sys.argv), 2):
            if sys.argv[i] == '--phase':
                new_phase = int(sys.argv[i + 1])
                if manager.update_story_phase(story_id, new_phase):
                    print(f"Updated {story_id} to phase {new_phase}")
                else:
                    print(f"Story {story_id} not found")
                    sys.exit(1)
            elif sys.argv[i] == '--status':
                passes = sys.argv[i + 1].lower() in ['true', 'complete', 'done']
                if manager.update_story_status(story_id, passes):
                    print(f"Updated {story_id} status to {'complete' if passes else 'incomplete'}")
                else:
                    print(f"Story {story_id} not found")
                    sys.exit(1)

        manager.save()

    elif command == 'summary':
        if len(sys.argv) < 3:
            print("Usage: prd_tools.py summary <prd_file>")
            sys.exit(1)

        prd_file = sys.argv[2]
        manager = PRDManager(prd_file)
        summary = manager.get_summary()

        print(f"\n📊 PRD Summary")
        print(f"{'=' * 50}")
        print(f"Total Stories: {summary['total_stories']}")
        print(f"Completed: {summary['completed_stories']}")
        print(f"Remaining: {summary['remaining_stories']}")
        print(f"Progress: {summary['completion_percentage']}%")
        print(f"\n📋 By Phase:")

        for phase, counts in sorted(summary['by_phase'].items()):
            phase_name = manager.data['metadata']['phases'].get(str(phase), {}).get('name', f'Phase {phase}')
            print(f"  Phase {phase} ({phase_name}): {counts['completed']}/{counts['total']} complete, {counts['remaining']} remaining")

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    main()
