#!/usr/bin/env python3
"""
PRD Builder: Incrementally builds PRD JSON files using Claude with tools.
This allows processing large PRDs without hitting token limits or parsing issues.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from anthropic import Anthropic
except ImportError:
    print("Error: anthropic package not installed. Run: make install")
    sys.exit(1)


class PRDBuilder:
    """Builds PRD JSON incrementally using Claude tool calls."""

    def __init__(self, api_key: Optional[str] = None):
        self.claude = Anthropic(api_key=api_key) if api_key else Anthropic()
        self.prd_data: Dict[str, Any] = {}
        self.user_stories: List[Dict[str, Any]] = []

    def _split_into_stories(self, content: str) -> List[str]:
        """Split PRD content into story sections."""
        import re
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
        """Build PRD JSON from markdown using tool calls."""

        if not prd_path.exists():
            raise FileNotFoundError(f"PRD file not found: {prd_path}")

        # Read PRD content
        with open(prd_path, 'r') as f:
            prd_content = f.read()

        print(f"📄 Building PRD from: {prd_path}")
        print(f"🤖 Using Claude {model} with tools...")

        # Define tools for PRD construction
        tools = [
            {
                "name": "initialize_prd",
                "description": "Initialize the PRD with project metadata. Call this first before adding any user stories.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "project": {
                            "type": "string",
                            "description": "Project name"
                        },
                        "branch_name": {
                            "type": "string",
                            "description": "Git branch name (e.g., 'ralph/feature-name')"
                        },
                        "description": {
                            "type": "string",
                            "description": "Project description"
                        }
                    },
                    "required": ["project", "branch_name", "description"]
                }
            },
            {
                "name": "add_user_story",
                "description": "Add a user story to the PRD. Call this for each user story found in the document.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Story ID (e.g., 'US-001')"
                        },
                        "title": {
                            "type": "string",
                            "description": "Story title"
                        },
                        "description": {
                            "type": "string",
                            "description": "Story description (As a..., I want..., so that...)"
                        },
                        "acceptance_criteria": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of acceptance criteria"
                        },
                        "priority": {
                            "type": "integer",
                            "description": "Story priority (1 = highest)"
                        }
                    },
                    "required": ["id", "title", "description", "acceptance_criteria", "priority"]
                }
            },
            {
                "name": "finalize_prd",
                "description": "Finalize the PRD after all stories have been added. Call this last.",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        ]

        # Split PRD into sections by user story headers
        story_sections = self._split_into_stories(prd_content)

        print(f"   Found {len(story_sections)} user story sections to process")

        # Build initial prompt for metadata
        header_section = story_sections[0] if story_sections else prd_content[:2000]

        prompt = f"""You are a PRD parser. Extract the project metadata from this PRD header.

Call initialize_prd() with the project name, branch name, and description from this content:

{header_section}

Just call initialize_prd() now - we'll add stories in subsequent steps."""

        # Step 1: Initialize PRD
        messages = [{"role": "user", "content": prompt}]
        self._process_tools_until_done(model, tools, messages)

        # Step 2: Process stories in batches
        story_batch_size = 5
        stories_to_process = story_sections[1:]  # Skip header

        for i in range(0, len(stories_to_process), story_batch_size):
            batch = stories_to_process[i:i + story_batch_size]
            batch_num = (i // story_batch_size) + 1
            total_batches = (len(stories_to_process) + story_batch_size - 1) // story_batch_size

            print(f"   Processing batch {batch_num}/{total_batches} ({len(batch)} stories)...")

            batch_content = "\n\n".join(batch)
            batch_prompt = f"""Extract and add these user stories using add_user_story() tool.

Stories to add:

{batch_content}

Call add_user_story() for each story above."""

            messages = [{"role": "user", "content": batch_prompt}]
            self._process_tools_until_done(model, tools, messages)

        # Step 3: Finalize
        print("   Finalizing PRD...")
        messages = [{"role": "user", "content": "Now call finalize_prd() to complete the PRD."}]
        self._process_tools_until_done(model, tools, messages)

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

    def _process_tools_until_done(self, model: str, tools: List[Dict], messages: List[Dict]) -> None:
        """Process tool calls until completion."""
        while True:
            response = self.claude.messages.create(
                model=model,
                max_tokens=8192,  # Sonnet 4.5 max output tokens
                tools=tools,
                messages=messages
            )

            # Process tool calls
            if response.stop_reason == "tool_use":
                # Add assistant response to messages
                messages.append({"role": "assistant", "content": response.content})

                # Process each tool call
                tool_results = []
                for content_block in response.content:
                    if content_block.type == "tool_use":
                        tool_name = content_block.name
                        tool_input = content_block.input
                        tool_id = content_block.id

                        print(f"  🔧 {tool_name}({list(tool_input.keys())[0] if tool_input else ''}...)")

                        # Execute tool
                        result = self._execute_tool(tool_name, tool_input)

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": json.dumps(result)
                        })

                # Add tool results to messages
                messages.append({"role": "user", "content": tool_results})

            elif response.stop_reason == "end_turn":
                # Done processing
                break
            else:
                print(f"⚠️  Unexpected stop reason: {response.stop_reason}")
                break

    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a PRD building tool."""

        if tool_name == "initialize_prd":
            self.prd_data = {
                "project": tool_input["project"],
                "branch_name": tool_input["branch_name"],
                "description": tool_input["description"]
            }
            return {"status": "success", "message": "PRD initialized"}

        elif tool_name == "add_user_story":
            story = {
                "id": tool_input["id"],
                "title": tool_input["title"],
                "description": tool_input["description"],
                "acceptanceCriteria": tool_input["acceptance_criteria"],
                "priority": tool_input["priority"],
                "passes": False,
                "notes": ""
            }
            self.user_stories.append(story)
            return {"status": "success", "message": f"Added story {tool_input['id']}"}

        elif tool_name == "finalize_prd":
            return {
                "status": "success",
                "message": f"PRD finalized with {len(self.user_stories)} stories"
            }

        else:
            return {"status": "error", "message": f"Unknown tool: {tool_name}"}


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Build PRD JSON from markdown using Claude tools")
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
