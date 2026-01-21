"""Tests for PRD builder."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ralph.builder import (
    PRDBuilder,
    _build_conversion_prompt,
    _ensure_valid_structure,
    _estimate_tokens,
    _parse_json_response,
)


class TestHelperFunctions:
    """Tests for module-level helper functions."""

    def test_estimate_tokens(self) -> None:
        """Test token estimation."""
        # ~4 chars per token
        text = "a" * 100
        assert _estimate_tokens(text) == 25

    def test_parse_json_response_direct(self) -> None:
        """Test parsing valid JSON directly."""
        response = '{"project": "Test", "userStories": []}'
        result = _parse_json_response(response)
        assert result["project"] == "Test"

    def test_parse_json_response_with_markdown(self) -> None:
        """Test parsing JSON wrapped in markdown code block."""
        response = '```json\n{"project": "Test"}\n```'
        result = _parse_json_response(response)
        assert result["project"] == "Test"

    def test_parse_json_response_with_text_before(self) -> None:
        """Test parsing JSON with text before it."""
        response = 'Here is the JSON:\n{"project": "Test"}'
        result = _parse_json_response(response)
        assert result["project"] == "Test"

    def test_parse_json_response_no_json(self) -> None:
        """Test parsing response with no JSON."""
        with pytest.raises(ValueError, match="No JSON object found"):
            _parse_json_response("Just some text")

    def test_parse_json_response_invalid_json(self) -> None:
        """Test parsing response with invalid JSON."""
        with pytest.raises(ValueError, match="Failed to parse JSON"):
            _parse_json_response('{"broken": }')

    def test_build_conversion_prompt_basic(self) -> None:
        """Test building conversion prompt."""
        prompt = _build_conversion_prompt("My PRD content")
        assert "My PRD content" in prompt
        assert "TARGET SCHEMA" in prompt
        assert "userStories" in prompt

    def test_build_conversion_prompt_with_existing_stories(self) -> None:
        """Test building prompt with existing stories for batching."""
        existing = [{"id": "US-001"}, {"id": "US-002"}]
        prompt = _build_conversion_prompt("More content", existing)
        assert "US-001" in prompt
        assert "US-002" in prompt
        assert "continuation" in prompt.lower()

    def test_ensure_valid_structure_adds_missing_fields(self) -> None:
        """Test that _ensure_valid_structure adds missing fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prd_path = Path(tmpdir) / "test.txt"
            prd_path.write_text("test")

            minimal_json = {
                "userStories": [
                    {"id": "US-001", "title": "Test"}
                ]
            }
            result = _ensure_valid_structure(minimal_json, prd_path)

            # Should add project, branchName, description
            assert "project" in result
            assert "branchName" in result
            assert "description" in result

            # Should add metadata
            assert "metadata" in result
            assert result["metadata"]["totalStories"] == 1
            assert result["metadata"]["completedStories"] == 0

            # Should add phases for referenced phase
            assert "phases" in result
            assert "1" in result["phases"]

            # Story should have defaults
            story = result["userStories"][0]
            assert story["status"] == "incomplete"
            assert story["phase"] == 1
            assert "Typecheck passes" in story["acceptanceCriteria"]

    def test_ensure_valid_structure_preserves_existing(self) -> None:
        """Test that _ensure_valid_structure preserves existing values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prd_path = Path(tmpdir) / "test.txt"
            prd_path.write_text("test")

            full_json = {
                "project": "MyProject",
                "branchName": "ralph/my-feature",
                "description": "My description",
                "phases": {
                    "1": {"name": "Phase 1", "description": "Desc"}
                },
                "userStories": [
                    {
                        "id": "US-001",
                        "title": "Test",
                        "description": "Desc",
                        "priority": 5,
                        "phase": 1,
                        "status": "complete",
                        "acceptanceCriteria": ["Custom criterion", "Typecheck passes"]
                    }
                ],
                "metadata": {
                    "createdAt": "2025-01-01T00:00:00",
                    "currentIteration": 3
                }
            }
            result = _ensure_valid_structure(full_json, prd_path)

            assert result["project"] == "MyProject"
            assert result["branchName"] == "ralph/my-feature"
            assert result["userStories"][0]["priority"] == 5
            assert result["userStories"][0]["status"] == "complete"
            assert result["metadata"]["createdAt"] == "2025-01-01T00:00:00"
            assert result["metadata"]["currentIteration"] == 3
            assert result["metadata"]["completedStories"] == 1


class TestPRDBuilder:
    """Tests for PRDBuilder class."""

    def test_prd_builder_initialization(self) -> None:
        """Test PRDBuilder initialization."""
        builder = PRDBuilder()
        assert builder.model == "claude-sonnet-4-5-20250929"

    def test_prd_builder_custom_model(self) -> None:
        """Test PRDBuilder with custom model."""
        builder = PRDBuilder(model="claude-opus-4-5-20251101")
        assert builder.model == "claude-opus-4-5-20251101"

    def test_build_from_prd_file_not_found(self) -> None:
        """Test building PRD from non-existent file."""
        builder = PRDBuilder()
        with pytest.raises(FileNotFoundError):
            builder.build_from_prd(Path("nonexistent.txt"), Path("output.json"))

    @patch('ralph.builder.call_claude_code')
    def test_build_from_prd_success(self, mock_claude: MagicMock) -> None:
        """Test successful PRD building."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            prd_file = project_dir / "test-prd.txt"
            output_file = project_dir / "prd.json"

            # Create test PRD
            prd_content = """# Test PRD

Build a simple feature with one story.

## Story 1: Test Story
As a user, I want to test.

Acceptance Criteria:
- Feature works
- Typecheck passes
"""
            prd_file.write_text(prd_content)

            # Mock Claude response - full JSON
            mock_response = json.dumps({
                "project": "TestProject",
                "branchName": "ralph/test",
                "description": "Test PRD",
                "phases": {
                    "1": {"name": "Phase 1", "description": ""}
                },
                "userStories": [
                    {
                        "id": "US-001",
                        "title": "Test Story",
                        "description": "As a user, I want to test",
                        "acceptanceCriteria": ["Feature works", "Typecheck passes"],
                        "priority": 1,
                        "phase": 1,
                        "status": "incomplete",
                        "notes": ""
                    }
                ],
                "metadata": {
                    "createdAt": "2025-01-01T00:00:00",
                    "lastUpdatedAt": "2025-01-01T00:00:00",
                    "totalStories": 1,
                    "completedStories": 0,
                    "currentIteration": 0
                }
            })
            mock_claude.return_value = mock_response

            builder = PRDBuilder()
            result_path = builder.build_from_prd(prd_file, output_file)

            # Verify output
            assert result_path.exists()
            with open(result_path) as f:
                prd_json = json.load(f)

            assert prd_json["project"] == "TestProject"
            assert len(prd_json["userStories"]) == 1
            assert prd_json["userStories"][0]["id"] == "US-001"
            assert "metadata" in prd_json
            assert prd_json["metadata"]["totalStories"] == 1

    @patch('ralph.builder.call_claude_code')
    def test_build_from_prd_with_phases(self, mock_claude: MagicMock) -> None:
        """Test building PRD with multiple phases."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            prd_file = project_dir / "test-prd.txt"
            output_file = project_dir / "prd.json"

            # Create test PRD with phases
            prd_content = """# Test PRD

Phase 1: Foundation - build core
Phase 2: Enhancement - add features

Story 1: Foundation work
Story 2: Enhancement work
"""
            prd_file.write_text(prd_content)

            # Mock Claude response
            mock_response = json.dumps({
                "project": "TestProject",
                "branchName": "ralph/test",
                "description": "Test PRD",
                "phases": {
                    "1": {"name": "Foundation", "description": "build core"},
                    "2": {"name": "Enhancement", "description": "add features"}
                },
                "userStories": [
                    {
                        "id": "US-001",
                        "title": "Foundation work",
                        "description": "Description",
                        "acceptanceCriteria": ["Typecheck passes"],
                        "priority": 1,
                        "phase": 1,
                        "status": "incomplete"
                    },
                    {
                        "id": "US-002",
                        "title": "Enhancement work",
                        "description": "Description",
                        "acceptanceCriteria": ["Typecheck passes"],
                        "priority": 2,
                        "phase": 2,
                        "status": "incomplete"
                    }
                ],
                "metadata": {
                    "totalStories": 2,
                    "completedStories": 0,
                    "currentIteration": 0
                }
            })
            mock_claude.return_value = mock_response

            builder = PRDBuilder()
            result_path = builder.build_from_prd(prd_file, output_file)

            # Verify phases at top level
            with open(result_path) as f:
                prd_json = json.load(f)

            assert "phases" in prd_json
            phases = prd_json["phases"]
            assert "1" in phases
            assert "2" in phases
            assert phases["1"]["name"] == "Foundation"
            assert phases["2"]["name"] == "Enhancement"

            # Verify story-to-phase mapping
            stories = prd_json["userStories"]
            assert stories[0]["phase"] == 1
            assert stories[1]["phase"] == 2

    @patch('ralph.builder.call_claude_code')
    def test_build_from_prd_model_override(self, mock_claude: MagicMock) -> None:
        """Test that model can be overridden in build_from_prd."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            prd_file = project_dir / "test-prd.txt"
            output_file = project_dir / "prd.json"

            prd_file.write_text("Simple PRD")

            mock_response = json.dumps({
                "project": "Test",
                "userStories": [],
                "metadata": {"totalStories": 0, "completedStories": 0, "currentIteration": 0}
            })
            mock_claude.return_value = mock_response

            builder = PRDBuilder(model="claude-sonnet-4-5-20250929")
            builder.build_from_prd(prd_file, output_file, model="claude-opus-4-5-20251101")

            # Verify the override model was used
            call_args = mock_claude.call_args
            assert call_args[1]["model"] == "claude-opus-4-5-20251101"

    @patch('ralph.builder.call_claude_code')
    def test_build_from_prd_adds_missing_metadata(self, mock_claude: MagicMock) -> None:
        """Test that missing metadata is added."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            prd_file = project_dir / "test-prd.txt"
            output_file = project_dir / "prd.json"

            prd_file.write_text("Simple PRD")

            # Response missing metadata
            mock_response = json.dumps({
                "project": "Test",
                "userStories": [
                    {"id": "US-001", "title": "Story"}
                ]
            })
            mock_claude.return_value = mock_response

            builder = PRDBuilder()
            builder.build_from_prd(prd_file, output_file)

            with open(output_file) as f:
                prd_json = json.load(f)

            # Metadata should be added
            assert "metadata" in prd_json
            assert prd_json["metadata"]["totalStories"] == 1
            assert prd_json["metadata"]["completedStories"] == 0
            assert "createdAt" in prd_json["metadata"]
            assert "lastUpdatedAt" in prd_json["metadata"]

    @patch('ralph.builder.call_claude_code')
    def test_build_from_prd_adds_missing_phases(self, mock_claude: MagicMock) -> None:
        """Test that phases are created for referenced phase numbers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            prd_file = project_dir / "test-prd.txt"
            output_file = project_dir / "prd.json"

            prd_file.write_text("Simple PRD")

            # Response with story referencing phase 2, but no phases defined
            mock_response = json.dumps({
                "project": "Test",
                "userStories": [
                    {"id": "US-001", "title": "Story", "phase": 2}
                ]
            })
            mock_claude.return_value = mock_response

            builder = PRDBuilder()
            builder.build_from_prd(prd_file, output_file)

            with open(output_file) as f:
                prd_json = json.load(f)

            # Phases should be created
            assert "phases" in prd_json
            assert "2" in prd_json["phases"]
            assert prd_json["phases"]["2"]["name"] == "Phase 2"
