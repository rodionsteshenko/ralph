"""Tests for PRD parsing and validation."""

import json
import os
import tempfile
from pathlib import Path
from typing import Dict
from unittest.mock import MagicMock, patch

import pytest

from ralph.prd import (
    PRDParser,
    ValidationIssue,
    ValidationResult,
    call_claude_code,
    validate_prd,
)


class TestValidationIssue:
    """Tests for ValidationIssue dataclass."""

    def test_validation_issue_creation(self) -> None:
        """Test creating a ValidationIssue."""
        issue = ValidationIssue(
            severity="error",
            code="MISSING_TITLE",
            message="Story missing 'title' field",
            story_id="US-001"
        )
        assert issue.severity == "error"
        assert issue.code == "MISSING_TITLE"
        assert issue.message == "Story missing 'title' field"
        assert issue.story_id == "US-001"
        assert issue.phase is None

    def test_validation_issue_with_phase(self) -> None:
        """Test ValidationIssue with phase number."""
        issue = ValidationIssue(
            severity="warning",
            code="MISSING_PHASE_NAME",
            message="Phase '1' missing 'name' field",
            phase=1
        )
        assert issue.phase == 1


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_format_with_errors(self) -> None:
        """Test formatting ValidationResult with errors."""
        errors = [
            ValidationIssue(
                severity="error",
                code="MISSING_TITLE",
                message="Story missing 'title' field",
                story_id="US-001"
            )
        ]
        result = ValidationResult(valid=False, errors=errors, warnings=[])
        formatted = result.format()
        assert "❌ Errors:" in formatted
        assert "[MISSING_TITLE]" in formatted
        assert "US-001" in formatted

    def test_validation_result_format_with_warnings(self) -> None:
        """Test formatting ValidationResult with warnings."""
        warnings = [
            ValidationIssue(
                severity="warning",
                code="MISSING_CRITERIA",
                message="No acceptance criteria defined",
                story_id="US-002"
            )
        ]
        result = ValidationResult(valid=True, errors=[], warnings=warnings)
        formatted = result.format()
        assert "⚠️  Warnings:" in formatted
        assert "[MISSING_CRITERIA]" in formatted
        assert "US-002" in formatted

    def test_validation_result_format_success(self) -> None:
        """Test formatting ValidationResult with no issues."""
        result = ValidationResult(valid=True, errors=[], warnings=[])
        formatted = result.format()
        assert "✅ PRD validation passed" in formatted


class TestValidatePRD:
    """Tests for validate_prd function."""

    def test_validate_empty_prd(self) -> None:
        """Test validating an empty PRD."""
        prd: Dict = {}
        result = validate_prd(prd)
        assert not result.valid
        assert len(result.errors) > 0
        # Should have error about missing userStories
        assert any(issue.code == "MISSING_STORIES" for issue in result.errors)

    def test_validate_prd_with_missing_project(self) -> None:
        """Test PRD with missing project field."""
        prd = {
            "userStories": [
                {
                    "id": "US-001",
                    "title": "Test story",
                    "description": "As a user...",
                    "acceptanceCriteria": ["Typecheck passes"]
                }
            ],
            "metadata": {
                "totalStories": 1,
                "completedStories": 0,
                "currentIteration": 0
            }
        }
        result = validate_prd(prd)
        assert result.valid  # Missing project is just a warning
        assert any(issue.code == "MISSING_PROJECT" for issue in result.warnings)

    def test_validate_prd_with_duplicate_story_ids(self) -> None:
        """Test PRD with duplicate story IDs."""
        prd = {
            "project": "Test",
            "userStories": [
                {"id": "US-001", "title": "Story 1"},
                {"id": "US-001", "title": "Story 2"}  # Duplicate
            ]
        }
        result = validate_prd(prd)
        assert not result.valid
        assert any(issue.code == "DUPLICATE_ID" for issue in result.errors)

    def test_validate_prd_with_invalid_status(self) -> None:
        """Test PRD with invalid story status."""
        prd = {
            "project": "Test",
            "userStories": [
                {
                    "id": "US-001",
                    "title": "Story 1",
                    "status": "invalid_status"
                }
            ]
        }
        result = validate_prd(prd)
        assert not result.valid
        assert any(issue.code == "INVALID_STATUS" for issue in result.errors)

    def test_validate_prd_with_invalid_phase_reference(self) -> None:
        """Test PRD with invalid phase reference."""
        prd = {
            "project": "Test",
            "phases": {
                "1": {"name": "Phase 1"}
            },
            "userStories": [
                {
                    "id": "US-001",
                    "title": "Story 1",
                    "phase": 2  # References undefined phase
                }
            ]
        }
        result = validate_prd(prd)
        assert not result.valid
        assert any(issue.code == "INVALID_PHASE_REF" for issue in result.errors)

    def test_validate_prd_with_missing_typecheck(self) -> None:
        """Test PRD without typecheck in acceptance criteria."""
        prd = {
            "project": "Test",
            "userStories": [
                {
                    "id": "US-001",
                    "title": "Story 1",
                    "acceptanceCriteria": ["Some criterion"]
                }
            ],
            "metadata": {
                "totalStories": 1,
                "completedStories": 0,
                "currentIteration": 0
            }
        }
        result = validate_prd(prd)
        assert result.valid  # Missing typecheck is a warning
        assert any(issue.code == "MISSING_TYPECHECK" for issue in result.warnings)

    def test_validate_prd_with_large_story(self) -> None:
        """Test PRD with overly large story."""
        prd = {
            "project": "Test",
            "userStories": [
                {
                    "id": "US-001",
                    "title": "Story 1",
                    "description": "x" * 600,  # Very long description
                    "acceptanceCriteria": ["Typecheck passes"]
                }
            ],
            "metadata": {
                "totalStories": 1,
                "completedStories": 0,
                "currentIteration": 0
            }
        }
        result = validate_prd(prd)
        assert result.valid  # Large story is a warning
        assert any(issue.code == "LARGE_STORY" for issue in result.warnings)

    def test_validate_prd_with_circular_dependency(self) -> None:
        """Test PRD with circular dependency."""
        prd = {
            "project": "Test",
            "userStories": [
                {
                    "id": "US-001",
                    "title": "Story 1",
                    "dependencies": ["US-002"]
                },
                {
                    "id": "US-002",
                    "title": "Story 2",
                    "dependencies": ["US-001"]  # Creates cycle
                }
            ]
        }
        result = validate_prd(prd)
        assert not result.valid
        assert any(issue.code == "CIRCULAR_DEPENDENCY" for issue in result.errors)

    def test_validate_prd_with_invalid_dependency(self) -> None:
        """Test PRD with dependency on non-existent story."""
        prd = {
            "project": "Test",
            "userStories": [
                {
                    "id": "US-001",
                    "title": "Story 1",
                    "dependencies": ["US-999"]  # Non-existent
                }
            ]
        }
        result = validate_prd(prd)
        assert not result.valid
        assert any(issue.code == "INVALID_DEPENDENCY" for issue in result.errors)

    def test_validate_valid_prd(self) -> None:
        """Test validating a completely valid PRD."""
        prd = {
            "project": "Test Project",
            "description": "A test project",
            "userStories": [
                {
                    "id": "US-001",
                    "title": "Story 1",
                    "description": "As a user, I want...",
                    "acceptanceCriteria": [
                        "Feature works",
                        "Typecheck passes"
                    ],
                    "status": "incomplete",
                    "priority": 1
                }
            ],
            "metadata": {
                "totalStories": 1,
                "completedStories": 0,
                "currentIteration": 0
            }
        }
        result = validate_prd(prd)
        assert result.valid
        assert len(result.errors) == 0


class TestPRDParser:
    """Tests for PRDParser class."""

    def test_prd_parser_initialization(self) -> None:
        """Test PRDParser initialization."""
        parser = PRDParser()
        assert parser.ralph_dir == Path(".ralph")
        assert parser.model == "claude-opus-4-5"

    def test_prd_parser_custom_initialization(self) -> None:
        """Test PRDParser with custom parameters."""
        parser = PRDParser(ralph_dir=Path("custom"), model="claude-opus-4-5-20251101")
        assert parser.ralph_dir == Path("custom")
        assert parser.model == "claude-opus-4-5-20251101"

    def test_parse_prd_file_not_found(self) -> None:
        """Test parsing non-existent PRD file."""
        parser = PRDParser()
        with pytest.raises(FileNotFoundError):
            parser.parse_prd(Path("nonexistent.txt"))

    @patch('ralph.prd.call_claude_code')
    def test_parse_prd_success(self, mock_claude: MagicMock) -> None:
        """Test successful PRD parsing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            prd_file = project_dir / "test-prd.txt"
            prd_file.write_text("# Test PRD\n\n## User Stories\n\n### US-001: Test Story\n\nAs a user, I want to test.")

            # Mock Claude response
            mock_response = {
                "project": "TestProject",
                "branchName": "ralph/test-feature",
                "description": "Test feature",
                "userStories": [
                    {
                        "id": "US-001",
                        "title": "Test Story",
                        "description": "As a user, I want to test",
                        "acceptanceCriteria": ["Feature works", "Typecheck passes"],
                        "priority": 1,
                        "status": "incomplete"
                    }
                ]
            }
            mock_claude.return_value = json.dumps(mock_response)

            parser = PRDParser(ralph_dir=project_dir / ".ralph")
            output_path = parser.parse_prd(prd_file)

            assert output_path.exists()
            with open(output_path) as f:
                prd_json = json.load(f)

            assert prd_json["project"] == "TestProject"
            assert len(prd_json["userStories"]) == 1
            assert "metadata" in prd_json

    @patch('ralph.prd.call_claude_code')
    def test_parse_prd_validates_and_fixes(self, mock_claude: MagicMock) -> None:
        """Test that PRD parser validates and auto-fixes issues."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            prd_file = project_dir / "test-prd.txt"
            prd_file.write_text("Test PRD content")

            # Mock Claude response with incomplete data
            mock_response = {
                "userStories": [
                    {
                        "title": "Test Story",
                        "description": "As a user..."
                        # Missing: id, status, priority, acceptanceCriteria
                    }
                ]
                # Missing: project, branchName, description
            }
            mock_claude.return_value = json.dumps(mock_response)

            parser = PRDParser(ralph_dir=project_dir / ".ralph")
            output_path = parser.parse_prd(prd_file)

            with open(output_path) as f:
                prd_json = json.load(f)

            # Check auto-fixes
            assert "project" in prd_json
            assert "branchName" in prd_json
            assert "description" in prd_json
            story = prd_json["userStories"][0]
            assert "id" in story
            assert "status" in story
            assert "priority" in story
            assert "acceptanceCriteria" in story
            assert any("typecheck" in c.lower() for c in story["acceptanceCriteria"])

    def test_build_parser_prompt(self) -> None:
        """Test building parser prompt."""
        parser = PRDParser()
        prompt = parser._build_parser_prompt("Test PRD content")
        assert "Test PRD content" in prompt
        assert "PRD parser" in prompt
        assert "CRITICAL RULES" in prompt
        assert "END-TO-END TESTING" in prompt


class TestCallClaudeCode:
    """Tests for call_claude_code function."""

    @patch('ralph.prd.subprocess.run')
    def test_call_claude_code_success(self, mock_run: MagicMock) -> None:
        """Test successful Claude Code call."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Test response\n"
        mock_run.return_value = mock_result

        response = call_claude_code("Test prompt")
        assert response == "Test response"
        mock_run.assert_called_once()

    @patch('ralph.prd.subprocess.run')
    def test_call_claude_code_with_custom_model(self, mock_run: MagicMock) -> None:
        """Test Claude Code call with custom model."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Response\n"
        mock_run.return_value = mock_result

        call_claude_code("Test prompt", model="claude-opus-4-5-20251101")

        call_args = mock_run.call_args[0][0]
        assert "--model" in call_args
        model_idx = call_args.index("--model")
        assert call_args[model_idx + 1] == "claude-opus-4-5-20251101"

    @patch('ralph.prd.subprocess.run')
    def test_call_claude_code_failure(self, mock_run: MagicMock) -> None:
        """Test Claude Code call failure."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Error message"
        mock_run.return_value = mock_result

        with pytest.raises(RuntimeError, match="Claude Code failed"):
            call_claude_code("Test prompt")

    @patch('ralph.prd.subprocess.run')
    def test_call_claude_code_not_found(self, mock_run: MagicMock) -> None:
        """Test Claude Code CLI not installed."""
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(RuntimeError, match="Claude Code CLI not found"):
            call_claude_code("Test prompt")

    @patch('ralph.prd.subprocess.run')
    def test_call_claude_code_timeout(self, mock_run: MagicMock) -> None:
        """Test Claude Code call timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("claude", 300)

        with pytest.raises(RuntimeError, match="timed out"):
            call_claude_code("Test prompt", timeout=300)


@pytest.mark.e2e
class TestPRDParserE2E:
    """End-to-end tests for PRD parsing with real Claude API."""

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY") and not os.path.exists(os.path.expanduser("~/.claude/config.json")),
        reason="Claude Code CLI not configured (no API key or config)"
    )
    def test_parse_real_prd_file(self) -> None:
        """Test parsing a real PRD file with actual Claude Code CLI.

        This test requires Claude Code CLI to be installed and authenticated.
        It will be skipped if the CLI is not available.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            prd_file = project_dir / "test-prd.txt"

            # Create a simple PRD
            prd_content = """# Test Feature

## Overview
This is a test feature for the PRD parser.

## User Stories

### US-001: Simple Test Story
As a developer, I want to test the PRD parser so that I can verify it works correctly.

**Acceptance Criteria:**
- Parser extracts the story
- Story has correct ID
- Typecheck passes

### US-002: Validation Test
As a developer, I want validation to work so that invalid PRDs are caught.

**Acceptance Criteria:**
- Validation runs
- Errors are reported
- Typecheck passes
"""
            prd_file.write_text(prd_content)

            parser = PRDParser(ralph_dir=project_dir / ".ralph")

            try:
                output_path = parser.parse_prd(prd_file)

                # Verify the output
                assert output_path.exists()
                with open(output_path) as f:
                    prd_json = json.load(f)

                # Basic structure checks
                assert "project" in prd_json
                assert "userStories" in prd_json
                assert len(prd_json["userStories"]) >= 1

                # Validate the parsed PRD
                result = validate_prd(prd_json)
                assert result.valid or len(result.errors) == 0

                print(f"\n✅ E2E Test passed!")
                print(f"   Parsed {len(prd_json['userStories'])} stories")
                print(f"   Output: {output_path}")

            except RuntimeError as e:
                if "Claude Code CLI not found" in str(e):
                    pytest.skip("Claude Code CLI not installed")
                raise
