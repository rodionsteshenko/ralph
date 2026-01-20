"""PRD parsing and management."""

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def call_claude_code(prompt: str, model: str = "claude-sonnet-4-5-20250929", timeout: int = 300) -> str:
    """Call Claude Code CLI and return the response text.

    Uses Claude Code's existing OAuth authentication - no API key required.

    Args:
        prompt: The prompt to send to Claude
        model: The Claude model to use
        timeout: Timeout in seconds

    Returns:
        The response text from Claude

    Raises:
        RuntimeError: If Claude Code CLI is not found or fails
        FileNotFoundError: If Claude Code CLI is not installed
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


@dataclass
class ValidationIssue:
    """A validation issue (error or warning)."""
    severity: str  # 'error' or 'warning'
    code: str      # Short code like 'INVALID_STATUS'
    message: str   # Human-readable message
    story_id: Optional[str] = None
    phase: Optional[int] = None


@dataclass
class ValidationResult:
    """Result of PRD validation."""
    valid: bool
    errors: List[ValidationIssue]
    warnings: List[ValidationIssue]

    def format(self) -> str:
        """Format validation results for display."""
        lines = []
        if self.errors:
            lines.append("❌ Errors:")
            for issue in self.errors:
                context = f" (story {issue.story_id})" if issue.story_id else ""
                context += f" (phase {issue.phase})" if issue.phase else ""
                lines.append(f"  - [{issue.code}]{context}: {issue.message}")
        if self.warnings:
            lines.append("⚠️  Warnings:")
            for issue in self.warnings:
                context = f" (story {issue.story_id})" if issue.story_id else ""
                context += f" (phase {issue.phase})" if issue.phase else ""
                lines.append(f"  - [{issue.code}]{context}: {issue.message}")
        if not self.errors and not self.warnings:
            lines.append("✅ PRD validation passed")
        return "\n".join(lines)


def validate_prd(prd: Dict) -> ValidationResult:
    """Validate PRD structure and return detailed results.

    Checks for:
    - Required fields (project, userStories)
    - Valid status values
    - Phase references
    - Unique story IDs
    - Dependency references
    - Circular dependencies
    - Story sizing concerns

    Args:
        prd: The PRD dictionary to validate

    Returns:
        ValidationResult with errors and warnings
    """
    errors: List[ValidationIssue] = []
    warnings: List[ValidationIssue] = []

    # Check required top-level fields
    if not prd.get("project"):
        warnings.append(ValidationIssue(
            severity="warning",
            code="MISSING_PROJECT",
            message="Missing 'project' field - will use current directory name"
        ))

    if not prd.get("description"):
        warnings.append(ValidationIssue(
            severity="warning",
            code="MISSING_DESCRIPTION",
            message="Missing 'description' field - add a project description"
        ))

    if "userStories" not in prd:
        errors.append(ValidationIssue(
            severity="error",
            code="MISSING_STORIES",
            message="Missing 'userStories' array - PRD must have at least one story"
        ))
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    stories = prd.get("userStories", [])
    if len(stories) == 0:
        errors.append(ValidationIssue(
            severity="error",
            code="EMPTY_STORIES",
            message="'userStories' array is empty - PRD must have at least one story"
        ))

    # Validate phases if present
    phases = prd.get("phases", {})
    for phase_key, phase_val in phases.items():
        if not isinstance(phase_val, dict):
            errors.append(ValidationIssue(
                severity="error",
                code="INVALID_PHASE",
                message=f"Phase '{phase_key}' must be an object with 'name' field",
                phase=int(phase_key) if phase_key.isdigit() else None
            ))
        elif not phase_val.get("name"):
            warnings.append(ValidationIssue(
                severity="warning",
                code="MISSING_PHASE_NAME",
                message=f"Phase '{phase_key}' missing 'name' field",
                phase=int(phase_key) if phase_key.isdigit() else None
            ))

    # Track story IDs for duplicate/dependency checking
    story_ids: set = set()
    valid_statuses = {"incomplete", "in_progress", "complete", "skipped"}
    in_progress_stories: List[str] = []

    for i, story in enumerate(stories):
        story_id = story.get("id", f"story[{i}]")

        # Check for duplicate IDs
        if story_id in story_ids:
            errors.append(ValidationIssue(
                severity="error",
                code="DUPLICATE_ID",
                message=f"Duplicate story ID: '{story_id}'",
                story_id=story_id
            ))
        story_ids.add(story_id)

        # Check required story fields
        if not story.get("id"):
            warnings.append(ValidationIssue(
                severity="warning",
                code="MISSING_ID",
                message=f"Story at index {i} missing 'id' field - will auto-generate",
                story_id=story_id
            ))

        if not story.get("title"):
            errors.append(ValidationIssue(
                severity="error",
                code="MISSING_TITLE",
                message="Story missing 'title' field",
                story_id=story_id
            ))

        # Validate status
        status = story.get("status", "incomplete")
        if status not in valid_statuses:
            errors.append(ValidationIssue(
                severity="error",
                code="INVALID_STATUS",
                message=f"Invalid status '{status}' - must be one of: {', '.join(valid_statuses)}",
                story_id=story_id
            ))

        if status == "in_progress":
            in_progress_stories.append(story_id)

        # Validate phase reference
        story_phase = story.get("phase")
        if story_phase is not None and phases:
            if str(story_phase) not in phases:
                errors.append(ValidationIssue(
                    severity="error",
                    code="INVALID_PHASE_REF",
                    message=f"References undefined phase '{story_phase}'",
                    story_id=story_id,
                    phase=story_phase
                ))

        # Check acceptance criteria
        criteria = story.get("acceptanceCriteria", [])
        if not criteria:
            warnings.append(ValidationIssue(
                severity="warning",
                code="MISSING_CRITERIA",
                message="No acceptance criteria defined",
                story_id=story_id
            ))
        elif not any("typecheck" in c.lower() for c in criteria):
            warnings.append(ValidationIssue(
                severity="warning",
                code="MISSING_TYPECHECK",
                message="Acceptance criteria should include 'Typecheck passes'",
                story_id=story_id
            ))

        # Check story size (heuristic: long description or many criteria)
        description = story.get("description", "")
        if len(description) > 500:
            warnings.append(ValidationIssue(
                severity="warning",
                code="LARGE_STORY",
                message="Description is very long - consider breaking into smaller stories",
                story_id=story_id
            ))
        if len(criteria) > 8:
            warnings.append(ValidationIssue(
                severity="warning",
                code="MANY_CRITERIA",
                message=f"{len(criteria)} acceptance criteria - story may be too large",
                story_id=story_id
            ))

    # Check for multiple in_progress stories
    if len(in_progress_stories) > 1:
        warnings.append(ValidationIssue(
            severity="warning",
            code="MULTIPLE_IN_PROGRESS",
            message=f"Multiple stories in_progress: {', '.join(in_progress_stories)}"
        ))

    # Check dependencies
    for story in stories:
        story_id = story.get("id", "unknown")
        deps = story.get("dependencies", [])
        for dep in deps:
            if dep not in story_ids:
                errors.append(ValidationIssue(
                    severity="error",
                    code="INVALID_DEPENDENCY",
                    message=f"Depends on unknown story '{dep}'",
                    story_id=story_id
                ))

    # Check for circular dependencies
    def has_circular_dep(story_id: str, visited: set, path: List[str]) -> Optional[List[str]]:
        if story_id in path:
            return path[path.index(story_id):] + [story_id]
        if story_id in visited:
            return None
        visited.add(story_id)
        path.append(story_id)
        story = next((s for s in stories if s.get("id") == story_id), None)
        if story:
            for dep in story.get("dependencies", []):
                cycle = has_circular_dep(dep, visited, path.copy())
                if cycle:
                    return cycle
        return None

    visited: set = set()
    for story in stories:
        cycle = has_circular_dep(story.get("id", ""), visited, [])
        if cycle:
            errors.append(ValidationIssue(
                severity="error",
                code="CIRCULAR_DEPENDENCY",
                message=f"Circular dependency detected: {' → '.join(cycle)}"
            ))
            break  # Only report first cycle

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


class PRDParser:
    """Parse PRD documents and convert to prd.json format.

    This class handles converting text-based PRD documents into structured
    JSON format that can be used by the Ralph execution loop.
    """

    def __init__(self, ralph_dir: Path = Path(".ralph"), model: str = "claude-sonnet-4-5-20250929"):
        """Initialize the PRD parser.

        Args:
            ralph_dir: Path to the .ralph directory (default: .ralph)
            model: Claude model to use for parsing
        """
        self.ralph_dir = ralph_dir
        self.model = model

    def parse_prd(self, prd_path: Path, output_path: Optional[Path] = None) -> Path:
        """Parse PRD content and convert to prd.json.

        Args:
            prd_path: Path to the PRD text file
            output_path: Output path for the JSON (default: .ralph/prd.json)

        Returns:
            Path to the generated prd.json file

        Raises:
            FileNotFoundError: If the PRD file doesn't exist
            ValueError: If the PRD content can't be parsed
        """
        if not prd_path.exists():
            raise FileNotFoundError(f"PRD file not found: {prd_path}")

        output_path = output_path or self.ralph_dir / "prd.json"

        # Read PRD content
        with open(prd_path, 'r') as f:
            prd_content = f.read()

        # Use Claude to convert PRD to structured JSON
        prompt = self._build_parser_prompt(prd_content)

        print(f"📄 Parsing PRD: {prd_path}")
        print("🤖 Using Claude Code to extract user stories...")

        # Call Claude Code CLI (uses OAuth, no API key needed)
        response_text = call_claude_code(prompt, model=self.model, timeout=300)
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

        if json_match:
            prd_json = json.loads(json_match.group())
        else:
            # Try to parse the whole response
            try:
                prd_json = json.loads(response_text)
            except json.JSONDecodeError:
                raise ValueError("Failed to extract valid JSON from Claude response")

        # Validate and enhance PRD JSON
        prd_json = self._validate_prd_json(prd_json, prd_path)

        # Save to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(prd_json, f, indent=2)

        print(f"✅ PRD converted to: {output_path}")
        print(f"   Found {len(prd_json.get('userStories', []))} user stories")

        return output_path

    def _build_parser_prompt(self, prd_content: str) -> str:
        """Build prompt for Claude to parse PRD.

        Args:
            prd_content: The raw PRD content

        Returns:
            The prompt string for Claude
        """
        return f"""You are a PRD parser that converts Product Requirement Documents into structured JSON format for autonomous AI agent execution.

Your task is to analyze the following PRD and convert it into a prd.json file with the following structure:

{{
  "project": "ProjectName",
  "branchName": "ralph/feature-name-kebab-case",
  "description": "Feature description from PRD",
  "userStories": [
    {{
      "id": "US-001",
      "title": "Story title",
      "description": "As a [user], I want [feature] so that [benefit]",
      "acceptanceCriteria": [
        "Verifiable criterion 1",
        "Verifiable criterion 2",
        "Typecheck passes"
      ],
      "priority": 1,
      "status": "incomplete",
      "notes": ""
    }}
  ],
  "metadata": {{
    "createdAt": "{datetime.now().isoformat()}",
    "lastUpdatedAt": "{datetime.now().isoformat()}",
    "totalStories": 0,
    "completedStories": 0,
    "currentIteration": 0
  }}
}}

CRITICAL RULES:
1. Each story MUST be completable in ONE iteration (one context window ~150k tokens)
2. Stories MUST be ordered by dependency (schema → backend → UI)
3. Acceptance criteria MUST be verifiable and objective (not vague)
4. Every story MUST include "Typecheck passes" as final criterion
5. UI stories MUST include "Verify in browser" as criterion
6. **END-TO-END TESTING**: Stories with external integrations (APIs, databases, services) MUST include "End-to-end test with real [API/database/service] integration passes" in acceptance criteria
7. Story size: If you can't describe it in 2-3 sentences, it's too big - split it

**Examples of E2E acceptance criteria:**
- "End-to-end test calling real Anthropic API passes"
- "End-to-end test with real SQLite database passes"
- "End-to-end test sending real Slack message passes (in test workspace)"
- "Integration test with real file system operations passes"

PRD Content:
{prd_content}

Output ONLY valid JSON, no extra formatting or explanations."""

    def _validate_prd_json(self, prd_json: Dict, prd_path: Path) -> Dict:
        """Validate and enhance PRD JSON structure.

        Args:
            prd_json: The parsed PRD JSON
            prd_path: Path to the original PRD file

        Returns:
            The validated and enhanced PRD JSON
        """
        # Run structured validation first
        result = validate_prd(prd_json)
        if result.errors or result.warnings:
            print("\n📋 PRD Validation Results:")
            print(result.format())
            if result.errors:
                print("\n⚠️  Errors found - auto-fixing where possible...")

        # Ensure required fields (auto-fix)
        if "project" not in prd_json:
            prd_json["project"] = Path.cwd().name

        if "branchName" not in prd_json:
            # Generate from project name or PRD filename
            feature_name = prd_path.stem.replace("prd-", "").replace("_", "-")
            prd_json["branchName"] = f"ralph/{feature_name}"

        if "description" not in prd_json:
            prd_json["description"] = "Feature implementation"

        # Ensure userStories array
        if "userStories" not in prd_json:
            prd_json["userStories"] = []

        # Validate and enhance each story
        for i, story in enumerate(prd_json["userStories"]):
            if "id" not in story:
                story["id"] = f"US-{i+1:03d}"

            if "priority" not in story:
                story["priority"] = i + 1

            if "status" not in story:
                story["status"] = "incomplete"

            if "notes" not in story:
                story["notes"] = ""

            # Ensure acceptance criteria includes typecheck
            if "acceptanceCriteria" in story:
                criteria = story["acceptanceCriteria"]
                if not any("typecheck" in c.lower() for c in criteria):
                    criteria.append("Typecheck passes")
            else:
                story["acceptanceCriteria"] = ["Typecheck passes"]

        # Add metadata
        now = datetime.now().isoformat()
        prd_json["metadata"] = {
            "createdAt": prd_json.get("metadata", {}).get("createdAt", now),
            "lastUpdatedAt": now,
            "totalStories": len(prd_json["userStories"]),
            "completedStories": sum(1 for s in prd_json["userStories"] if s.get("status") == "complete"),
            "currentIteration": prd_json.get("metadata", {}).get("currentIteration", 0)
        }

        return prd_json
