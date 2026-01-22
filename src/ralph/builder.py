"""PRD builder for converting any text PRD into structured JSON.

This module converts freeform PRD text into structured JSON using Claude.
It accepts any format - markdown, plain text, bullet points, etc.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ralph.prd import call_claude_code, validate_prd


# Approximate tokens per character (conservative estimate)
CHARS_PER_TOKEN = 4
MAX_TOKENS_PER_BATCH = 80000  # Leave room for prompt and response


def _estimate_tokens(text: str) -> int:
    """Estimate token count for text."""
    return len(text) // CHARS_PER_TOKEN


def _get_json_schema() -> str:
    """Return the target JSON schema for PRD output."""
    return '''{
  "project": "Project name",
  "branchName": "ralph/feature-name-kebab-case",
  "description": "Brief project description",
  "phases": {
    "1": { "name": "Phase 1 Name", "description": "What this phase accomplishes" },
    "2": { "name": "Phase 2 Name", "description": "What this phase accomplishes" }
  },
  "userStories": [
    {
      "id": "US-001",
      "title": "Short story title",
      "description": "As a [user], I want [feature] so that [benefit]",
      "acceptanceCriteria": [
        "Specific, verifiable criterion 1",
        "Specific, verifiable criterion 2",
        "Typecheck passes"
      ],
      "priority": 1,
      "phase": 1,
      "status": "incomplete",
      "notes": ""
    }
  ],
  "metadata": {
    "createdAt": "ISO timestamp",
    "lastUpdatedAt": "ISO timestamp",
    "totalStories": 0,
    "completedStories": 0,
    "currentIteration": 0
  }
}'''


def _build_conversion_prompt(prd_content: str, existing_stories: Optional[List[Dict]] = None) -> str:
    """Build prompt for Claude to convert PRD text to JSON.

    Args:
        prd_content: The raw PRD text in any format
        existing_stories: Previously parsed stories (for batched processing)

    Returns:
        The prompt string
    """
    now = datetime.now().isoformat()
    schema = _get_json_schema()

    batch_context = ""
    if existing_stories:
        existing_ids = [s.get("id", "unknown") for s in existing_stories]
        batch_context = f"""
IMPORTANT: This is a continuation. Stories {', '.join(existing_ids)} have already been parsed.
Continue numbering from US-{len(existing_stories) + 1:03d}.
Only parse NEW stories from this content - do not repeat already-parsed stories.
"""

    return f"""Convert this PRD document into structured JSON format.

TARGET SCHEMA:
{schema}

RULES:
1. Extract ALL user stories from the document
2. Each story must have a unique ID (US-001, US-002, etc.)
3. Group stories into logical phases if the document suggests phases/stages
4. If no phases mentioned, use phase 1 for all stories
5. Every story MUST include "Typecheck passes" in acceptanceCriteria
6. Stories should be ordered by dependency (foundational work first)
7. Set all story statuses to "incomplete"
8. Priority should match the logical execution order (1 = first to implement)
9. Use the current timestamp: {now}
10. totalStories in metadata must equal the actual number of stories
{batch_context}

PRD CONTENT:
{prd_content}

Return ONLY valid JSON matching the schema above. No explanations or markdown."""


def _parse_json_response(response: str) -> Dict[str, Any]:
    """Extract and parse JSON from Claude's response.

    Args:
        response: The raw response text

    Returns:
        Parsed JSON dictionary

    Raises:
        ValueError: If no valid JSON found
    """
    # Try to find JSON object in response
    response = response.strip()

    # Remove markdown code blocks if present
    if response.startswith("```"):
        lines = response.split("\n")
        # Remove first line (```json or ```)
        lines = lines[1:]
        # Remove last line if it's ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        response = "\n".join(lines)

    # Try direct parse first
    try:
        result: Dict[str, Any] = json.loads(response)
        return result
    except json.JSONDecodeError:
        pass

    # Try to find JSON object boundaries
    start = response.find("{")
    if start == -1:
        raise ValueError("No JSON object found in response")

    # Find matching closing brace
    depth = 0
    end = start
    for i, char in enumerate(response[start:], start):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    try:
        parsed: Dict[str, Any] = json.loads(response[start:end])
        return parsed
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON: {e}")


def _ensure_valid_structure(prd_json: Dict[str, Any], prd_path: Path) -> Dict[str, Any]:
    """Ensure PRD JSON has all required fields with valid values.

    Args:
        prd_json: The parsed PRD JSON
        prd_path: Path to original PRD (for fallback values)

    Returns:
        The validated and enhanced PRD JSON
    """
    now = datetime.now().isoformat()

    # Ensure top-level fields
    if not prd_json.get("project"):
        prd_json["project"] = Path.cwd().name

    if not prd_json.get("branchName"):
        feature_name = prd_path.stem.replace("prd-", "").replace("_", "-").replace(" ", "-").lower()
        prd_json["branchName"] = f"ralph/{feature_name}"

    if not prd_json.get("description"):
        prd_json["description"] = "Feature implementation"

    # Ensure userStories array
    if "userStories" not in prd_json:
        prd_json["userStories"] = []

    stories = prd_json["userStories"]

    # Collect all phases referenced by stories
    phases_referenced = set()

    # Validate and enhance each story
    for i, story in enumerate(stories):
        if not story.get("id"):
            story["id"] = f"US-{i+1:03d}"

        if not story.get("title"):
            story["title"] = f"Story {i+1}"

        if "priority" not in story:
            story["priority"] = i + 1

        if "phase" not in story:
            story["phase"] = 1

        phases_referenced.add(story["phase"])

        if story.get("status") not in {"incomplete", "in_progress", "complete", "skipped"}:
            story["status"] = "incomplete"

        if "notes" not in story:
            story["notes"] = ""

        # Ensure acceptanceCriteria exists and has typecheck
        if "acceptanceCriteria" not in story:
            story["acceptanceCriteria"] = []

        criteria = story["acceptanceCriteria"]
        if not any("typecheck" in c.lower() for c in criteria):
            criteria.append("Typecheck passes")

    # Ensure phases object exists for all referenced phases
    if "phases" not in prd_json:
        prd_json["phases"] = {}

    for phase_num in phases_referenced:
        phase_key = str(phase_num)
        if phase_key not in prd_json["phases"]:
            prd_json["phases"][phase_key] = {
                "name": f"Phase {phase_num}",
                "description": ""
            }

    # Ensure metadata
    prd_json["metadata"] = {
        "createdAt": prd_json.get("metadata", {}).get("createdAt", now),
        "lastUpdatedAt": now,
        "totalStories": len(stories),
        "completedStories": sum(1 for s in stories if s.get("status") == "complete"),
        "currentIteration": prd_json.get("metadata", {}).get("currentIteration", 0)
    }

    return prd_json


class PRDBuilder:
    """Builds PRD JSON from any text format using Claude.

    This builder accepts PRD documents in any format (markdown, plain text,
    bullet points, etc.) and uses Claude to convert them to structured JSON.
    """

    def __init__(self, model: str = "claude-opus-4-5") -> None:
        """Initialize the PRD builder.

        Args:
            model: Claude model to use for parsing
        """
        self.model = model

    def build_from_prd(
        self,
        prd_path: Path,
        output_path: Path,
        model: Optional[str] = None
    ) -> Path:
        """Build PRD JSON from any text PRD document.

        Args:
            prd_path: Path to the PRD source file (any format)
            output_path: Path where the JSON should be saved
            model: Claude model to use (overrides instance default)

        Returns:
            Path to the generated JSON file

        Raises:
            FileNotFoundError: If the PRD file doesn't exist
            ValueError: If the PRD can't be parsed
        """
        if not prd_path.exists():
            raise FileNotFoundError(f"PRD file not found: {prd_path}")

        model = model or self.model

        # Read PRD content
        with open(prd_path, 'r') as f:
            prd_content = f.read()

        print(f"📄 Building PRD from: {prd_path}")
        print(f"🤖 Using Claude ({model}) to parse...")

        # Estimate if we need batching
        estimated_tokens = _estimate_tokens(prd_content)

        if estimated_tokens > MAX_TOKENS_PER_BATCH:
            print(f"   Large PRD detected (~{estimated_tokens} tokens), using batched processing...")
            prd_json = self._build_batched(prd_content, model)
        else:
            prd_json = self._build_single(prd_content, model)

        # Ensure valid structure
        prd_json = _ensure_valid_structure(prd_json, prd_path)

        # Run validation and show results
        result = validate_prd(prd_json)
        if result.errors or result.warnings:
            print("\n📋 Validation Results:")
            print(result.format())

        # Save to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(prd_json, f, indent=2)

        stories = prd_json.get("userStories", [])
        phases = prd_json.get("phases", {})
        print(f"\n✅ PRD built successfully: {output_path}")
        print(f"   {len(stories)} user stories across {len(phases)} phases")

        return output_path

    def _build_single(self, prd_content: str, model: str) -> Dict[str, Any]:
        """Build PRD JSON in a single Claude call.

        Args:
            prd_content: The full PRD text
            model: Claude model to use

        Returns:
            Parsed PRD JSON
        """
        prompt = _build_conversion_prompt(prd_content)
        response = call_claude_code(prompt, model=model, timeout=300)
        return _parse_json_response(response)

    def _build_batched(self, prd_content: str, model: str) -> Dict[str, Any]:
        """Build PRD JSON in batches for large documents.

        Splits the document by estimated token count and processes
        in chunks, accumulating stories.

        Args:
            prd_content: The full PRD text
            model: Claude model to use

        Returns:
            Merged PRD JSON with all stories
        """
        # Split into chunks by paragraph/section
        # Try to split on double newlines (paragraph boundaries)
        sections = prd_content.split("\n\n")

        chunks: List[str] = []
        current_chunk: List[str] = []
        current_tokens = 0

        for section in sections:
            section_tokens = _estimate_tokens(section)

            if current_tokens + section_tokens > MAX_TOKENS_PER_BATCH and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [section]
                current_tokens = section_tokens
            else:
                current_chunk.append(section)
                current_tokens += section_tokens

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        print(f"   Split into {len(chunks)} chunks")

        # Process first chunk to get base structure
        all_stories: List[Dict] = []
        base_json: Dict[str, Any] = {}

        for i, chunk in enumerate(chunks):
            print(f"   Processing chunk {i+1}/{len(chunks)}...")

            prompt = _build_conversion_prompt(chunk, all_stories if all_stories else None)
            response = call_claude_code(prompt, model=model, timeout=300)
            chunk_json = _parse_json_response(response)

            if i == 0:
                # First chunk - use as base
                base_json = chunk_json
                all_stories = chunk_json.get("userStories", [])
            else:
                # Subsequent chunks - merge stories
                new_stories = chunk_json.get("userStories", [])

                # Renumber to avoid ID conflicts
                for story in new_stories:
                    existing_ids = {s.get("id") for s in all_stories}
                    if story.get("id") in existing_ids:
                        # Generate new ID
                        story["id"] = f"US-{len(all_stories) + 1:03d}"
                    story["priority"] = len(all_stories) + 1

                all_stories.extend(new_stories)

                # Merge phases
                if "phases" in chunk_json and "phases" in base_json:
                    base_json["phases"].update(chunk_json["phases"])

        base_json["userStories"] = all_stories
        return base_json
