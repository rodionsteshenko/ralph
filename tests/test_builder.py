"""Tests for PRD builder."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ralph.builder import PRDBuilder


class TestPRDBuilder:
    """Tests for PRDBuilder class."""

    def test_prd_builder_initialization(self) -> None:
        """Test PRDBuilder initialization."""
        builder = PRDBuilder()
        assert builder.prd_data == {}
        assert builder.user_stories == []
        assert builder.phases == {}
        assert builder.story_to_phase == {}

    def test_extract_phases(self) -> None:
        """Test extracting phases from PRD content."""
        builder = PRDBuilder()
        content = """# PRD

## Phase 1: Foundation
Core functionality

## Phase 2: Enhancement
Additional features
"""
        phases = builder._extract_phases(content)
        assert len(phases) == 2
        assert 1 in phases
        assert 2 in phases
        assert phases[1]["name"] == "Foundation"
        assert phases[2]["name"] == "Enhancement"

    def test_extract_phases_no_phases(self) -> None:
        """Test extracting phases when none exist."""
        builder = PRDBuilder()
        content = "# PRD\n\nNo phases here"
        phases = builder._extract_phases(content)
        assert len(phases) == 0

    def test_map_stories_to_phases(self) -> None:
        """Test mapping stories to phases based on position."""
        builder = PRDBuilder()
        content = """# PRD

## Phase 1: Foundation

### US-001: Story 1

### US-002: Story 2

## Phase 2: Enhancement

### US-003: Story 3
"""
        mapping = builder._map_stories_to_phases(content)
        assert mapping["US-001"] == 1
        assert mapping["US-002"] == 1
        assert mapping["US-003"] == 2

    def test_split_into_stories(self) -> None:
        """Test splitting PRD into story sections."""
        builder = PRDBuilder()
        content = """# PRD

## Overview
Project description

### US-001: First Story
Description

### US-002: Second Story
Description
"""
        sections = builder._split_into_stories(content)
        assert len(sections) == 3  # Header + 2 stories
        assert "Overview" in sections[0]
        assert "US-001" in sections[1]
        assert "US-002" in sections[2]

    def test_split_into_stories_no_stories(self) -> None:
        """Test splitting PRD with no user stories."""
        builder = PRDBuilder()
        content = "# PRD\n\nNo stories here"
        sections = builder._split_into_stories(content)
        assert len(sections) == 1
        assert sections[0] == content

    @patch('ralph.builder.call_claude_code')
    def test_extract_metadata_success(self, mock_claude: MagicMock) -> None:
        """Test successful metadata extraction."""
        builder = PRDBuilder()
        mock_response = json.dumps({
            "project": "TestProject",
            "branch_name": "ralph/test-feature",
            "description": "Test description"
        })
        mock_claude.return_value = mock_response

        builder._extract_metadata("# Test PRD", "claude-sonnet-4-5-20250929")

        assert builder.prd_data["project"] == "TestProject"
        assert builder.prd_data["branch_name"] == "ralph/test-feature"
        assert builder.prd_data["description"] == "Test description"

    @patch('ralph.builder.call_claude_code')
    def test_extract_metadata_parse_error(self, mock_claude: MagicMock) -> None:
        """Test metadata extraction with parse error."""
        builder = PRDBuilder()
        mock_claude.return_value = "Invalid JSON response"

        builder._extract_metadata("# Test PRD", "claude-sonnet-4-5-20250929")

        # Should fall back to defaults
        assert builder.prd_data["project"] == "Unknown"
        assert builder.prd_data["branch_name"] == "main"

    @patch('ralph.builder.call_claude_code')
    def test_process_story_batch_success(self, mock_claude: MagicMock) -> None:
        """Test successful story batch processing."""
        builder = PRDBuilder()
        mock_response = json.dumps([
            {
                "id": "US-001",
                "title": "Test Story",
                "description": "As a user...",
                "acceptance_criteria": ["Criterion 1", "Typecheck passes"],
                "priority": 1
            }
        ])
        mock_claude.return_value = mock_response

        stories = ["### US-001: Test Story\n\nDescription"]
        builder._process_story_batch(stories, "claude-sonnet-4-5-20250929")

        assert len(builder.user_stories) == 1
        assert builder.user_stories[0]["id"] == "US-001"
        assert builder.user_stories[0]["title"] == "Test Story"
        assert builder.user_stories[0]["status"] == "incomplete"

    @patch('ralph.builder.call_claude_code')
    def test_process_story_batch_parse_error(self, mock_claude: MagicMock) -> None:
        """Test story batch processing with parse error."""
        builder = PRDBuilder()
        mock_claude.return_value = "Invalid JSON response"

        stories = ["### US-001: Test Story"]
        builder._process_story_batch(stories, "claude-sonnet-4-5-20250929")

        # Should not add stories on parse error
        assert len(builder.user_stories) == 0

    @patch('ralph.builder.call_claude_code')
    def test_build_from_prd_success(self, mock_claude: MagicMock) -> None:
        """Test successful PRD building."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            prd_file = project_dir / "test-prd.txt"
            output_file = project_dir / "prd.json"

            # Create test PRD
            prd_content = """# Test PRD

## Phase 1: Foundation

### US-001: Test Story
As a user, I want to test.

**Acceptance Criteria:**
- Feature works
- Typecheck passes
"""
            prd_file.write_text(prd_content)

            # Mock Claude responses
            metadata_response = json.dumps({
                "project": "TestProject",
                "branch_name": "ralph/test",
                "description": "Test PRD"
            })
            stories_response = json.dumps([
                {
                    "id": "US-001",
                    "title": "Test Story",
                    "description": "As a user, I want to test",
                    "acceptance_criteria": ["Feature works", "Typecheck passes"],
                    "priority": 1
                }
            ])
            mock_claude.side_effect = [metadata_response, stories_response]

            builder = PRDBuilder()
            result_path = builder.build_from_prd(prd_file, output_file)

            # Verify output
            assert result_path.exists()
            with open(result_path) as f:
                prd_json = json.load(f)

            assert prd_json["project"] == "TestProject"
            assert len(prd_json["userStories"]) == 1
            assert prd_json["userStories"][0]["id"] == "US-001"
            assert prd_json["userStories"][0]["phase"] == 1
            assert "metadata" in prd_json
            assert prd_json["metadata"]["totalStories"] == 1

    def test_build_from_prd_file_not_found(self) -> None:
        """Test building PRD from non-existent file."""
        builder = PRDBuilder()
        with pytest.raises(FileNotFoundError):
            builder.build_from_prd(Path("nonexistent.txt"), Path("output.json"))

    @patch('ralph.builder.call_claude_code')
    def test_build_from_prd_with_phases(self, mock_claude: MagicMock) -> None:
        """Test building PRD with multiple phases."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            prd_file = project_dir / "test-prd.txt"
            output_file = project_dir / "prd.json"

            # Create test PRD with phases
            prd_content = """# Test PRD

## Phase 1: Foundation

### US-001: Story 1
Description

## Phase 2: Enhancement

### US-002: Story 2
Description
"""
            prd_file.write_text(prd_content)

            # Mock Claude responses
            metadata_response = json.dumps({
                "project": "TestProject",
                "branch_name": "ralph/test",
                "description": "Test PRD"
            })
            stories_response = json.dumps([
                {
                    "id": "US-001",
                    "title": "Story 1",
                    "description": "Description",
                    "acceptance_criteria": ["Typecheck passes"],
                    "priority": 1
                },
                {
                    "id": "US-002",
                    "title": "Story 2",
                    "description": "Description",
                    "acceptance_criteria": ["Typecheck passes"],
                    "priority": 2
                }
            ])
            mock_claude.side_effect = [metadata_response, stories_response]

            builder = PRDBuilder()
            result_path = builder.build_from_prd(prd_file, output_file)

            # Verify phases
            with open(result_path) as f:
                prd_json = json.load(f)

            assert "phases" in prd_json["metadata"]
            phases = prd_json["metadata"]["phases"]
            assert "1" in phases
            assert "2" in phases
            assert phases["1"]["name"] == "Foundation"
            assert phases["2"]["name"] == "Enhancement"

            # Verify story-to-phase mapping
            stories = prd_json["userStories"]
            assert stories[0]["phase"] == 1
            assert stories[1]["phase"] == 2
