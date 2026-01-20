"""PRD builder for incrementally building large PRD JSON files.

This module provides functionality for building PRD JSON files from large PRD documents
using Claude Code CLI. It processes stories in batches to avoid token limits.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from ralph.prd import call_claude_code


class PRDBuilder:
    """Builds PRD JSON incrementally using Claude Code CLI.

    This builder is designed for large PRDs (10+ stories) that may hit token limits
    when trying to generate JSON all at once. It processes stories in batches and
    incrementally builds the PRD JSON.
    """

    def __init__(self) -> None:
        """Initialize the PRD builder."""
        self.prd_data: Dict[str, Any] = {}
        self.user_stories: List[Dict[str, Any]] = []
        self.phases: Dict[int, Dict[str, Any]] = {}
        self.story_to_phase: Dict[str, int] = {}

    def _extract_phases(self, content: str) -> Dict[int, Dict[str, Any]]:
        """Extract phase information from PRD content.

        Args:
            content: The PRD content

        Returns:
            Dictionary mapping phase numbers to phase metadata
        """
        phases: Dict[int, Dict[str, Any]] = {}
        # Match phase headers like "## Phase 1: Core Loop (Foundation)"
        phase_pattern = r'##\s+Phase\s+(\d+):\s*([^\n]+)'
        matches = re.finditer(phase_pattern, content)

        for match in matches:
            phase_num = int(match.group(1))
            phase_name = match.group(2).strip()
            phases[phase_num] = {
                "name": phase_name,
                "description": "",
                "stories": []
            }

        return phases

    def _map_stories_to_phases(self, content: str) -> Dict[str, int]:
        """Map each story ID to its phase number based on position in document.

        Args:
            content: The PRD content

        Returns:
            Dictionary mapping story IDs to phase numbers
        """
        story_to_phase = {}

        # Find all phase boundaries and story positions
        phase_pattern = r'##\s+Phase\s+(\d+):'
        story_pattern = r'###\s+(US-\d+[A-Z]?):'

        # Get all phase starts with their positions
        phase_positions = [(int(m.group(1)), m.start()) for m in re.finditer(phase_pattern, content)]

        # Get all story positions
        story_matches = [(m.group(1), m.start()) for m in re.finditer(story_pattern, content)]

        # Map each story to its phase based on position
        for story_id, story_pos in story_matches:
            current_phase = 1  # Default to phase 1
            for phase_num, phase_pos in phase_positions:
                if story_pos > phase_pos:
                    current_phase = phase_num
                else:
                    break
            story_to_phase[story_id] = current_phase

        return story_to_phase

    def _split_into_stories(self, content: str) -> List[str]:
        """Split PRD content into story sections.

        Args:
            content: The PRD content

        Returns:
            List of story sections (first element is the header)
        """
        # Split on user story headers (US-XXX or US-XXXA)
        pattern = r'###\s+(US-\d+[A-Z]?:.*?)(?=###\s+US-\d+[A-Z]?:|##\s+Phase|$)'
        matches = re.findall(pattern, content, re.DOTALL)

        # If no matches, return header + full content
        if not matches:
            return [content]

        # Extract header (everything before first US)
        header_match = re.search(r'(.*?)###\s+US-\d+[A-Z]?:', content, re.DOTALL)
        header = header_match.group(1) if header_match else content[:1000]

        return [header] + matches

    def build_from_prd(
        self,
        prd_path: Path,
        output_path: Path,
        model: str = "claude-sonnet-4-5-20250929"
    ) -> Path:
        """Build PRD JSON from a PRD document using Claude Code CLI.

        Args:
            prd_path: Path to the PRD source file
            output_path: Path where the JSON should be saved
            model: Claude model to use for parsing

        Returns:
            Path to the generated JSON file

        Raises:
            FileNotFoundError: If the PRD file doesn't exist
        """
        if not prd_path.exists():
            raise FileNotFoundError(f"PRD file not found: {prd_path}")

        # Read PRD content
        with open(prd_path, 'r') as f:
            prd_content = f.read()

        print(f"📄 Building PRD from: {prd_path}")
        print(f"🤖 Using Claude Code ({model})...")

        # Extract phases from the document
        self.phases = self._extract_phases(prd_content)
        if self.phases:
            print(f"   Found {len(self.phases)} phases")

        # Map stories to phases based on document structure
        self.story_to_phase = self._map_stories_to_phases(prd_content)

        # Split PRD into sections by user story headers
        story_sections = self._split_into_stories(prd_content)

        print(f"   Found {len(story_sections)} sections to process")

        # Step 1: Extract metadata from header
        header_section = story_sections[0] if story_sections else prd_content[:2000]
        self._extract_metadata(header_section, model)

        # Step 2: Process stories in batches
        story_batch_size = 5
        stories_to_process = story_sections[1:]  # Skip header

        for i in range(0, len(stories_to_process), story_batch_size):
            batch = stories_to_process[i:i + story_batch_size]
            batch_num = (i // story_batch_size) + 1
            total_batches = (len(stories_to_process) + story_batch_size - 1) // story_batch_size

            print(f"   Processing batch {batch_num}/{total_batches} ({len(batch)} stories)...")

            self._process_story_batch(batch, model)

        # Add phase field to each story and build phase story lists
        for story in self.user_stories:
            story_id = story["id"]
            phase_num = self.story_to_phase.get(story_id, 1)
            story["phase"] = phase_num

            # Add story to phase's story list
            if phase_num in self.phases:
                self.phases[phase_num]["stories"].append(story_id)

        # Build phases metadata (convert int keys to strings for JSON)
        phases_metadata = {
            str(k): v for k, v in self.phases.items()
        } if self.phases else {}

        # Build final PRD JSON
        prd_json = {
            "project": self.prd_data.get("project", "Unknown"),
            "branchName": self.prd_data.get("branch_name", "main"),
            "description": self.prd_data.get("description", ""),
            "userStories": self.user_stories,
            "metadata": {
                "createdAt": datetime.now().isoformat(),
                "lastUpdatedAt": datetime.now().isoformat(),
                "totalStories": len(self.user_stories),
                "completedStories": 0,
                "currentIteration": 0,
                "phases": phases_metadata
            }
        }

        # Save to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(prd_json, f, indent=2)

        print(f"✅ PRD built successfully: {output_path}")
        print(f"   Found {len(self.user_stories)} user stories across {len(self.phases)} phases")

        return output_path

    def _extract_metadata(self, header_content: str, model: str) -> None:
        """Extract project metadata from PRD header.

        Args:
            header_content: The header content from the PRD
            model: The Claude model to use
        """
        prompt = f"""Extract the project metadata from this PRD header and return ONLY a JSON object.

PRD Header:
{header_content}

Return a JSON object with exactly these fields:
{{
  "project": "Project name from the PRD",
  "branch_name": "Git branch name like ralph/feature-name",
  "description": "Project description from the PRD"
}}

Return ONLY the JSON object, no other text."""

        response = call_claude_code(prompt, model=model, timeout=120)

        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                self.prd_data = json.loads(json_match.group())
                print(f"  🔧 Initialized: {self.prd_data.get('project', 'Unknown')}")
            except json.JSONDecodeError as e:
                print(f"  ⚠️  Failed to parse metadata JSON: {e}")
                self.prd_data = {"project": "Unknown", "branch_name": "main", "description": ""}
        else:
            print("  ⚠️  No JSON found in metadata response")
            self.prd_data = {"project": "Unknown", "branch_name": "main", "description": ""}

    def _process_story_batch(self, stories: List[str], model: str) -> None:
        """Process a batch of user stories.

        Args:
            stories: List of story sections to process
            model: The Claude model to use
        """
        batch_content = "\n\n---\n\n".join(stories)

        prompt = f"""Extract user stories from the following content and return a JSON array.

Content:
{batch_content}

Return a JSON array where each story has this structure:
[
  {{
    "id": "US-XXX",
    "title": "Story title",
    "description": "As a..., I want..., so that...",
    "acceptance_criteria": ["criterion 1", "criterion 2"],
    "priority": 1
  }}
]

Rules:
- Extract the story ID from the header (US-XXX format)
- Include all acceptance criteria as an array
- Priority should be based on the order in the document (1 = first)
- If "Typecheck passes" is not in acceptance criteria, add it

Return ONLY the JSON array, no other text."""

        response = call_claude_code(prompt, model=model, timeout=180)

        # Extract JSON array from response
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            try:
                parsed_stories = json.loads(json_match.group())
                for story_data in parsed_stories:
                    story = {
                        "id": story_data.get("id", f"US-{len(self.user_stories) + 1:03d}"),
                        "title": story_data.get("title", "Unknown"),
                        "description": story_data.get("description", ""),
                        "acceptanceCriteria": story_data.get("acceptance_criteria", []),
                        "priority": story_data.get("priority", len(self.user_stories) + 1),
                        "status": "incomplete",
                        "notes": ""
                    }
                    self.user_stories.append(story)
                    print(f"    ✓ Added {story['id']}: {story['title'][:50]}...")
            except json.JSONDecodeError as e:
                print(f"  ⚠️  Failed to parse stories JSON: {e}")
        else:
            print("  ⚠️  No JSON array found in response")
