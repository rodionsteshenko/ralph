#!/usr/bin/env python3
"""
PRD Builder: Incrementally builds PRD JSON files using Claude Code CLI.
This allows processing large PRDs without hitting token limits or parsing issues.
"""

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def call_claude_code(prompt: str, model: str = "claude-sonnet-4-5-20250929", timeout: int = 300) -> str:
    """Call Claude Code CLI and return the response text.

    Uses Claude Code's existing OAuth authentication - no API key required.
    """
    try:
        result = subprocess.run(
            [
                "claude",
                "--print",  # Output response only, no interactive mode
                "--model", model,
                "-p", prompt
            ],
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            raise RuntimeError(f"Claude Code failed with return code {result.returncode}: {result.stderr}")

        return result.stdout.strip()
    except FileNotFoundError:
        raise RuntimeError(
            "Claude Code CLI not found. Please install it:\n"
            "  npm install -g @anthropic-ai/claude-code\n"
            "Or see: https://claude.ai/code"
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Claude Code timed out after {timeout} seconds")


class PRDBuilder:
    """Builds PRD JSON incrementally using Claude Code CLI."""

    def __init__(self):
        self.prd_data: Dict[str, Any] = {}
        self.user_stories: List[Dict[str, Any]] = []

    def _split_into_stories(self, content: str) -> List[str]:
        """Split PRD content into story sections."""
        # Split on user story headers (US-XXX)
        pattern = r'###\s+(US-\d+:.*?)(?=###\s+US-\d+:|$)'
        matches = re.findall(pattern, content, re.DOTALL)

        # If no matches, return header + full content
        if not matches:
            return [content]

        # Extract header (everything before first US)
        header_match = re.search(r'(.*?)###\s+US-\d+:', content, re.DOTALL)
        header = header_match.group(1) if header_match else content[:1000]

        return [header] + matches

    def build_from_markdown(self, prd_path: Path, output_path: Path, model: str = "claude-sonnet-4-5-20250929") -> Path:
        """Build PRD JSON from markdown using Claude Code CLI."""

        if not prd_path.exists():
            raise FileNotFoundError(f"PRD file not found: {prd_path}")

        # Read PRD content
        with open(prd_path, 'r') as f:
            prd_content = f.read()

        print(f"📄 Building PRD from: {prd_path}")
        print(f"🤖 Using Claude Code ({model})...")

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
                "currentIteration": 0
            }
        }

        # Save to file
        with open(output_path, 'w') as f:
            json.dump(prd_json, f, indent=2)

        print(f"✅ PRD built successfully: {output_path}")
        print(f"   Found {len(self.user_stories)} user stories")

        return output_path

    def _extract_metadata(self, header_content: str, model: str) -> None:
        """Extract project metadata from PRD header."""
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
        """Process a batch of user stories."""
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
                        "passes": False,
                        "notes": ""
                    }
                    self.user_stories.append(story)
                    print(f"    ✓ Added {story['id']}: {story['title'][:50]}...")
            except json.JSONDecodeError as e:
                print(f"  ⚠️  Failed to parse stories JSON: {e}")
        else:
            print("  ⚠️  No JSON array found in response")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Build PRD JSON from markdown using Claude Code")
    parser.add_argument("prd_file", type=Path, help="Path to PRD markdown file")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output JSON file path")
    parser.add_argument("--model", "-m", default="claude-sonnet-4-5-20250929", help="Claude model to use")

    args = parser.parse_args()

    # Determine output path
    output_path = args.output or args.prd_file.with_suffix('.json')

    # Build PRD
    builder = PRDBuilder()
    builder.build_from_markdown(args.prd_file, output_path, model=args.model)


if __name__ == "__main__":
    main()
