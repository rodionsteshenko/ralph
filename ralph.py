#!/usr/bin/env python3
"""
Ralph: Autonomous AI Agent Loop
A Python implementation of the Ralph pattern using Claude API.

Usage:
    ralph process-prd <prd_file> [--output prd.json]
    ralph execute-plan [--prd prd.json] [--max-iterations N] [--config config.json]
    ralph status [--prd prd.json]
    ralph init [--detect-config]
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.live import Live
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, TextColumn
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    console = None

try:
    from anthropic import Anthropic
except ImportError:
    print("Error: anthropic package not installed. Run: make install")
    print("Or manually: uv pip install -r requirements.txt")
    sys.exit(1)

# Try to import ASCII art display (optional dependency)
try:
    from ascii_image import display_ascii_image
    HAS_ASCII_ART = True
except ImportError:
    HAS_ASCII_ART = False


def get_anthropic_client():
    """Get Anthropic client, trying multiple authentication methods."""
    api_key = None
    
    # First, try explicit API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        return Anthropic(api_key=api_key)
    
    # Try to read from .env file in project root
    env_file = Path.cwd() / ".env"
    if env_file.exists():
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("ANTHROPIC_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if api_key:
                            return Anthropic(api_key=api_key)
        except Exception:
            pass
    
    # Try to read from home directory .anthropic_api_key file
    api_key_file = Path.home() / ".anthropic_api_key"
    if api_key_file.exists():
        try:
            with open(api_key_file, 'r') as f:
                api_key = f.read().strip()
                if api_key:
                    return Anthropic(api_key=api_key)
        except Exception:
            pass
    
    # Try to read from Ralph config file
    ralph_config_path = Path.cwd() / ".ralph" / "config.json"
    if ralph_config_path.exists():
        try:
            with open(ralph_config_path, 'r') as f:
                ralph_config = json.load(f)
                if "anthropic" in ralph_config and "apiKey" in ralph_config["anthropic"]:
                    api_key = ralph_config["anthropic"]["apiKey"]
                    if api_key:
                        return Anthropic(api_key=api_key)
        except Exception:
            pass
    
    # Try to read from Claude config file (if it contains API key)
    claude_config_path = Path.home() / ".claude.json"
    if claude_config_path.exists():
        try:
            with open(claude_config_path, 'r') as f:
                claude_config = json.load(f)
                if "api_key" in claude_config:
                    return Anthropic(api_key=claude_config["api_key"])
                if "apiKey" in claude_config:
                    return Anthropic(api_key=claude_config["apiKey"])
        except Exception:
            pass  # Continue to try other methods
    
    # If we still don't have an API key, provide helpful error message
    print("Error: Could not find Anthropic API key.")
    print("")
    print("The Anthropic Python SDK requires an explicit API key.")
    print("Even though you're logged into Claude Code, you need to get your API key separately.")
    print("")
    print("Options:")
    print("1. Get your API key from: https://console.anthropic.com/settings/keys")
    print("2. Set it as an environment variable:")
    print("   export ANTHROPIC_API_KEY=your_key_here")
    print("")
    print("3. Create a .env file in the project root with:")
    print("   ANTHROPIC_API_KEY=your_key_here")
    print("")
    print("4. Create ~/.anthropic_api_key file with your API key")
    print("")
    print("5. Add it to .ralph/config.json:")
    print('   {"anthropic": {"apiKey": "your_key_here"}}')
    print("")
    print("Note: Claude Code uses OAuth authentication which is separate from the API key.")
    print("The API key is needed for programmatic access via the Python SDK.")
    raise ValueError("ANTHROPIC_API_KEY not found")


class RalphConfig:
    """Configuration for Ralph execution."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(".ralph/config.json")
        self.config = self._load_config()
        self._ensure_directories()
    
    def _load_config(self) -> Dict:
        """Load configuration from file or create default."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        
        # Default configuration
        return {
            "project": {
                "name": "Unknown",
                "type": "node",
                "packageManager": "npm"
            },
            "commands": {
                "install": "npm install",
                "typecheck": "npm run typecheck",
                "lint": "npm run lint",
                "test": "npm run test",
                "build": "npm run build"
            },
            "qualityGates": {
                "typecheck": {
                    "command": "npm run typecheck",
                    "required": True,
                    "timeout": 300
                },
                "lint": {
                    "command": "npm run lint",
                    "required": True,
                    "timeout": 120
                },
                "test": {
                    "command": "npm run test",
                    "required": True,
                    "timeout": 600
                }
            },
            "git": {
                "baseBranch": "main",
                "commitMessageFormat": "feat: {story_id} - {story_title}",
                "autoPush": False,
                "createPR": False
            },
            "ralph": {
                "maxIterations": 20,
                "iterationTimeout": 3600,
                "maxFailures": 3,
                "updateAgentsMd": True,
                "enableMetrics": True
            },
            "paths": {
                "prdFile": "prd.json",
                "progressFile": "progress.txt",
                "archiveDir": "archive",
                "scriptsDir": ".ralph"
            },
            "claude": {
                "model": "claude-3-haiku-20240307",
                "maxTokens": 8192,
                "temperature": 0.7
            }
        }
    
    def _ensure_directories(self):
        """Ensure required directories exist."""
        paths = self.config["paths"]
        Path(paths["archiveDir"]).mkdir(parents=True, exist_ok=True)
        Path(paths["scriptsDir"]).mkdir(parents=True, exist_ok=True)
        Path(".ralph/skills").mkdir(parents=True, exist_ok=True)
    
    def save(self):
        """Save configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get(self, key: str, default=None):
        """Get configuration value using dot notation."""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value


class PRDParser:
    """Parse PRD markdown files and convert to prd.json format."""
    
    def __init__(self, config: RalphConfig):
        self.config = config
        self.claude = get_anthropic_client()
    
    def parse_prd(self, prd_path: Path, output_path: Optional[Path] = None) -> Path:
        """Parse PRD markdown and convert to prd.json."""
        if not prd_path.exists():
            raise FileNotFoundError(f"PRD file not found: {prd_path}")
        
        output_path = output_path or Path(self.config.get("paths.prdFile", "prd.json"))
        
        # Read PRD content
        with open(prd_path, 'r') as f:
            prd_content = f.read()
        
        # Use Claude to convert PRD to structured JSON
        prompt = self._build_parser_prompt(prd_content)
        
        print(f"📄 Parsing PRD: {prd_path}")
        print("🤖 Using Claude to extract user stories...")
        
        model = self.config.get("claude.model", "claude-3-haiku-20240307")
        # Adjust max_tokens based on model (Haiku has lower limit)
        default_max_tokens = 4096 if "haiku" in model.lower() else 8192
        max_tokens = min(self.config.get("claude.maxTokens", default_max_tokens), default_max_tokens)
        
        response = self.claude.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=0.3,  # Lower temperature for more structured output
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        # Extract JSON from response
        response_text = response.content[0].text
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
        with open(output_path, 'w') as f:
            json.dump(prd_json, f, indent=2)
        
        print(f"✅ PRD converted to: {output_path}")
        print(f"   Found {len(prd_json.get('userStories', []))} user stories")
        
        return output_path
    
    def _build_parser_prompt(self, prd_content: str) -> str:
        """Build prompt for Claude to parse PRD."""
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
      "passes": false,
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

Output ONLY valid JSON, no markdown formatting, no explanations."""
    
    def _validate_prd_json(self, prd_json: Dict, prd_path: Path) -> Dict:
        """Validate and enhance PRD JSON structure."""
        # Ensure required fields
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
            
            if "passes" not in story:
                story["passes"] = False
            
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
            "completedStories": sum(1 for s in prd_json["userStories"] if s.get("passes", False)),
            "currentIteration": prd_json.get("metadata", {}).get("currentIteration", 0)
        }
        
        return prd_json


class QualityGates:
    """Run quality gates (tests, lint, typecheck) statically."""
    
    def __init__(self, config: RalphConfig):
        self.config = config
    
    def run(self) -> Dict:
        """Run all quality gates and return results."""
        results = {
            "status": "PASS",
            "gates": {},
            "totalDuration": 0.0,
            "timestamp": datetime.now().isoformat()
        }

        gates = self.config.get("qualityGates", {})
        start_time = time.time()

        for gate_name, gate_config in gates.items():
            if not gate_config.get("required", False):
                continue

            if HAS_RICH:
                console.print(f"\n[bold blue]▶ Running {gate_name}...[/bold blue]")
                console.print(f"[dim]  Command: {gate_config['command']}[/dim]")
            else:
                print(f"🔍 Running {gate_name}...")
                print(f"   Command: {gate_config['command']}")

            gate_result = self._run_gate(gate_name, gate_config)
            results["gates"][gate_name] = gate_result

            if gate_result["status"] == "FAIL":
                results["status"] = "FAIL"
                if HAS_RICH:
                    console.print(f"[bold red]✗ {gate_name} failed ({gate_result['duration']:.1f}s)[/bold red]")
                    if gate_result["output"]:
                        # Show first 20 lines of output
                        output_lines = gate_result["output"].split('\n')[:20]
                        console.print(Panel(
                            "\n".join(output_lines),
                            title=f"[red]{gate_name} Output (first 20 lines)[/red]",
                            border_style="red",
                            expand=False
                        ))
                else:
                    print(f"❌ {gate_name} failed")
                    if gate_result["output"]:
                        print("   Output (first 20 lines):")
                        for line in gate_result["output"].split('\n')[:20]:
                            print(f"   {line}")
                break
            else:
                if HAS_RICH:
                    console.print(f"[bold green]✓ {gate_name} passed ({gate_result['duration']:.1f}s)[/bold green]")
                else:
                    print(f"✅ {gate_name} passed ({gate_result['duration']:.1f}s)")

        results["totalDuration"] = time.time() - start_time
        return results
    
    def _run_gate(self, gate_name: str, gate_config: Dict) -> Dict:
        """Run a single quality gate."""
        command = gate_config["command"]
        timeout = gate_config.get("timeout", 300)
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=Path.cwd()
            )
            
            duration = time.time() - start_time
            
            return {
                "status": "PASS" if result.returncode == 0 else "FAIL",
                "duration": duration,
                "output": result.stdout + result.stderr,
                "returnCode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "FAIL",
                "duration": timeout,
                "output": f"Gate timed out after {timeout}s",
                "returnCode": -1
            }
        except Exception as e:
            return {
                "status": "FAIL",
                "duration": time.time() - start_time,
                "output": str(e),
                "returnCode": -1
            }


class RalphLoop:
    """Main Ralph execution loop."""

    def __init__(self, config: RalphConfig):
        self.config = config
        self.claude = get_anthropic_client()
        self.quality_gates = QualityGates(config)
        self.failure_count = 0
        self.last_story_id = None
        self.session_start_time = None
        self.session_completed_stories = []  # Stories completed in this session
        self.initial_completed_count = 0  # Stories completed before session started

    def _print_session_summary(self, prd: Dict, iteration_count: int, prd_path: Path):
        """Print comprehensive session summary at the end of execution."""
        session_duration = time.time() - self.session_start_time if self.session_start_time else 0

        # Get file changes from git
        changed_files = []
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                changed_files = [f for f in result.stdout.strip().split('\n') if f]
        except Exception:
            pass

        # Calculate stats
        total_stories = len(prd["userStories"])
        current_completed = sum(1 for s in prd["userStories"] if s.get("passes", False))
        remaining_stories = total_stories - current_completed
        session_completed_count = len(self.session_completed_stories)

        # Print summary
        print("\n" + "="*80)
        print("📊 SESSION SUMMARY")
        print("="*80)

        # Session stats
        hours = int(session_duration // 3600)
        minutes = int((session_duration % 3600) // 60)
        seconds = int(session_duration % 60)
        duration_str = f"{hours}h {minutes}m {seconds}s" if hours > 0 else f"{minutes}m {seconds}s"

        print(f"\n⏱️  Duration: {duration_str}")
        print(f"🔄 Iterations: {iteration_count}")

        # Stories completed this session
        if session_completed_count > 0:
            print(f"\n✅ Completed This Session ({session_completed_count} stories):")
            for story_info in self.session_completed_stories:
                print(f"   • {story_info['id']}: {story_info['title']} ({story_info['duration']:.1f}s)")
        else:
            print(f"\n⚠️  No stories completed this session")

        # Files changed
        if changed_files:
            print(f"\n📝 Files Changed ({len(changed_files)} files):")
            # Group by directory and show top 10
            display_files = changed_files[:10]
            for f in display_files:
                print(f"   • {f}")
            if len(changed_files) > 10:
                print(f"   ... and {len(changed_files) - 10} more")

        # Overall PRD status
        print(f"\n📋 Overall Progress:")
        print(f"   Total Stories: {total_stories}")
        print(f"   Completed: {current_completed} ({100*current_completed//total_stories if total_stories > 0 else 0}%)")
        print(f"   Remaining: {remaining_stories}")

        if remaining_stories > 0:
            print(f"\n📌 Next Stories to Complete:")
            remaining = [s for s in prd["userStories"] if not s.get("passes", False)]
            for story in remaining[:3]:  # Show next 3
                print(f"   • {story['id']}: {story['title']}")
            if len(remaining) > 3:
                print(f"   ... and {len(remaining) - 3} more")

        # Next steps
        print(f"\n💡 Next Steps:")
        if remaining_stories > 0:
            print(f"   Run: python ralph.py execute-plan")
            print(f"   Or: python ralph.py status")
        else:
            print(f"   All stories complete! Review and merge your changes.")

        print("\n" + "="*80 + "\n")

    def execute(self, prd_path: Optional[Path] = None, max_iterations: Optional[int] = None, phase: Optional[int] = None):
        """Execute Ralph loop until completion or max iterations.

        Args:
            prd_path: Path to prd.json file
            max_iterations: Maximum number of iterations (0 = unlimited)
            phase: Only execute stories in this phase (None = all incomplete stories)
        """
        prd_path = prd_path or Path(self.config.get("paths.prdFile", "prd.json"))

        if not prd_path.exists():
            raise FileNotFoundError(f"PRD file not found: {prd_path}")

        # Load PRD
        with open(prd_path, 'r') as f:
            prd = json.load(f)

        # Track session start
        self.session_start_time = time.time()

        # Track initial state
        self.initial_completed_count = sum(1 for s in prd["userStories"] if s.get("passes", False))

        max_iter = max_iterations or self.config.get("ralph.maxIterations", 20)
        max_failures = self.config.get("ralph.maxFailures", 3)

        # Display Ralph ASCII art if available
        if HAS_ASCII_ART:
            ralph_image_path = Path(__file__).parent / "ralph.jpg"
            if ralph_image_path.exists():
                try:
                    display_ascii_image(
                        str(ralph_image_path),
                        max_width=60,
                        dark_mode=True,
                        contrast_factor=1.5
                    )
                    print()  # Add spacing after ASCII art
                except Exception as e:
                    # If ASCII art fails, just continue without it
                    pass

        # Display phase info if filtering by phase
        phase_info = ""
        if phase is not None:
            phase_metadata = prd.get("metadata", {}).get("phases", {}).get(str(phase), {})
            phase_name = phase_metadata.get("name", f"Phase {phase}")
            phase_info = f"\n   🎯 Phase Filter: {phase} ({phase_name})"

        print(f"\n🚀 Starting Ralph Loop")
        print(f"   Max iterations: {max_iter if max_iter > 0 else 'unlimited'}")
        print(f"   Max consecutive failures: {max_failures}")

        # Count stories to complete (with optional phase filter)
        stories_to_complete = [s for s in prd['userStories'] if not s.get('passes', False)]
        if phase is not None:
            stories_to_complete = [s for s in stories_to_complete if s.get('phase') == phase]

        print(f"   Stories to complete: {len(stories_to_complete)}{phase_info}\n")
        
        iteration = 0
        
        while True:
            iteration += 1
            
            # Check max iterations
            if max_iter > 0 and iteration > max_iter:
                print(f"\n⚠️  Max iterations ({max_iter}) reached")
                break
            
            # Check for remaining stories (with optional phase filter)
            remaining_stories = [s for s in prd["userStories"] if not s.get("passes", False)]
            if phase is not None:
                remaining_stories = [s for s in remaining_stories if s.get("phase") == phase]

            if not remaining_stories:
                if phase is not None:
                    print(f"\n✅ All Phase {phase} stories completed!")
                else:
                    print("\n✅ All stories completed!")
                break
            
            # Check failure threshold
            if self.failure_count >= max_failures:
                print(f"\n❌ Stopping: {max_failures} consecutive failures")
                break
            
            # Select next story
            story = self._select_next_story(remaining_stories, prd)

            if HAS_RICH:
                console.print("\n")
                console.print(Panel(
                    f"[bold magenta]Iteration {iteration}[/bold magenta]\n\n"
                    f"[cyan]Story ID:[/cyan] {story['id']}\n"
                    f"[cyan]Title:[/cyan] {story['title']}\n"
                    f"[cyan]Priority:[/cyan] {story.get('priority', 'N/A')}\n"
                    f"[dim]Remaining: {len(remaining_stories)} stories[/dim]",
                    title="📋 Story Selection",
                    border_style="magenta"
                ))
            else:
                print(f"\n{'='*60}")
                print(f"  Iteration {iteration} - {story['id']}: {story['title']}")
                print(f"{'='*60}")

            iteration_start = time.time()
            
            # Execute story
            success = self._execute_story(story, prd, iteration)
            
            iteration_duration = time.time() - iteration_start
            
            if success:
                self.failure_count = 0  # Reset failure count on success
                story["passes"] = True
                # Track completed story in this session
                self.session_completed_stories.append({
                    "id": story["id"],
                    "title": story["title"],
                    "duration": iteration_duration
                })
                story["actualDuration"] = iteration_duration
                story["iterationNumber"] = iteration
                
                # Update PRD metadata
                prd["metadata"]["completedStories"] = sum(
                    1 for s in prd["userStories"] if s.get("passes", False)
                )
                prd["metadata"]["currentIteration"] = iteration
                prd["metadata"]["lastUpdatedAt"] = datetime.now().isoformat()
                
                # Save PRD
                with open(prd_path, 'w') as f:
                    json.dump(prd, f, indent=2)
                
                print(f"✅ Story {story['id']} completed ({iteration_duration:.1f}s)")
            else:
                self.failure_count += 1
                print(f"❌ Story {story['id']} failed ({iteration_duration:.1f}s)")
                print(f"   Consecutive failures: {self.failure_count}/{max_failures}")
            
            # Brief pause between iterations
            time.sleep(2)
        
        # Print session summary
        self._print_session_summary(prd, iteration, prd_path)
    
    def _select_next_story(self, stories: List[Dict], prd: Dict) -> Dict:
        """Select next story using AI analysis or simple priority-based selection."""
        # Check if AI-powered selection is enabled
        use_ai_selection = self.config.get("ralph.useAISelection", True)
        
        if use_ai_selection:
            try:
                return self._select_next_story_with_claude(stories, prd)
            except Exception as e:
                print(f"   ⚠️  AI selection failed: {e}")
                print(f"   Falling back to simple priority-based selection...")
                # Fall through to simple selection
        
        # Simple priority-based selection (fallback)
        return self._select_next_story_simple(stories, prd)
    
    def _select_next_story_simple(self, stories: List[Dict], prd: Dict) -> Dict:
        """Select next story based on priority and dependencies (simple heuristic)."""
        # Sort by priority
        stories.sort(key=lambda s: s.get("priority", 999))
        
        # Filter by dependencies (simple heuristic)
        runnable = []
        for story in stories:
            # Check if story mentions other story IDs that aren't complete
            story_text = json.dumps(story)
            mentioned_ids = re.findall(r'US-\d+', story_text)
            
            dependencies_satisfied = True
            for dep_id in mentioned_ids:
                if dep_id != story["id"]:
                    dep_story = next((s for s in prd["userStories"] if s["id"] == dep_id), None)
                    if dep_story and not dep_story.get("passes", False):
                        dependencies_satisfied = False
                        break
            
            if dependencies_satisfied:
                runnable.append(story)
        
        return runnable[0] if runnable else stories[0]
    
    def _select_next_story_with_claude(self, stories: List[Dict], prd: Dict) -> Dict:
        """Use Claude to intelligently select the next story based on codebase analysis."""
        print("🧠 Analyzing stories with Claude to select optimal next task...")
        
        # Build summary of remaining stories
        remaining_stories_summary = []
        for story in stories:
            remaining_stories_summary.append({
                "id": story["id"],
                "title": story["title"],
                "description": story.get("description", ""),
                "priority": story.get("priority", 999),
                "acceptanceCriteria": story.get("acceptanceCriteria", [])
            })
        
        # Get completed stories
        completed_stories = [s for s in prd["userStories"] if s.get("passes", False)]
        completed_ids = [s["id"] for s in completed_stories]
        
        # Get codebase structure (list key files/directories)
        codebase_summary = self._get_codebase_summary(prd)
        
        # Build prompt for Claude
        prompt = f"""You are analyzing a software project PRD to determine the optimal next user story to implement.

## Project Context

**Project**: {prd.get('project', 'Unknown')}
**Description**: {prd.get('description', 'No description')}

**Completed Stories**: {', '.join(completed_ids) if completed_ids else 'None'}

## Current Codebase Structure

{codebase_summary}

## Remaining Stories

{json.dumps(remaining_stories_summary, indent=2)}

## Your Task

Analyze the remaining stories and determine which story should be implemented next. Consider:

1. **Dependencies**: Which stories depend on others? What needs to be built first?
2. **Implementation Readiness**: What's already in the codebase that would help implement each story?
3. **Critical Path**: Which stories unlock the most other stories?
4. **Complexity**: Which stories are foundational and should come first?
5. **Priority**: Consider the priority field, but don't rely solely on it - use your judgment

## Output Format

Respond with ONLY a JSON object in this exact format:
{{
  "selectedStoryId": "US-XXX",
  "reasoning": "Brief explanation of why this story was selected (2-3 sentences)"
}}

Be specific about why this story makes sense given the current codebase state and dependencies."""

        # Call Claude API
        model = self.config.get("claude.model", "claude-sonnet-4-5-20250929")
        max_tokens = self.config.get("claude.maxTokens", 8192)
        
        response = self.claude.messages.create(
            model=model,
            max_tokens=min(max_tokens, 2048),  # Limit for selection task
            temperature=0.3,  # Lower temperature for more consistent selection
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        # Parse response
        response_text = response.content[0].text
        
        # Extract JSON from response (handle multi-line JSON)
        json_match = re.search(r'\{[^{}]*"selectedStoryId"[^{}]*"reasoning"[^{}]*\}', response_text, re.DOTALL)
        if not json_match:
            # Try simpler pattern
            json_match = re.search(r'\{.*?"selectedStoryId".*?\}', response_text, re.DOTALL)
        if json_match:
            try:
                selection = json.loads(json_match.group())
                selected_id = selection.get("selectedStoryId")
                reasoning = selection.get("reasoning", "No reasoning provided")
                
                if selected_id:
                    # Find the story
                    selected_story = next((s for s in stories if s["id"] == selected_id), None)
                    if selected_story:
                        print(f"   ✅ Selected: {selected_id} - {selected_story['title']}")
                        print(f"   💭 Reasoning: {reasoning}")
                        return selected_story
                    else:
                        print(f"   ⚠️  Selected story {selected_id} not found in remaining stories")
            except json.JSONDecodeError as e:
                print(f"   ⚠️  Failed to parse Claude response: {e}")
        
        # Fallback if parsing fails
        print(f"   ⚠️  Could not parse Claude selection, falling back to simple selection")
        return self._select_next_story_simple(stories, prd)
    
    def _get_codebase_summary(self, prd: Dict) -> str:
        """Get a summary of the current codebase structure."""
        working_dir = self.config.get("ralph.workingDirectory")
        if not working_dir and prd:
            # Derive from PRD project name
            import re
            working_dir = prd.get("project", "").lower().replace(" ", "-")
            working_dir = re.sub(r'[^a-z0-9-]', '', working_dir)
        
        if not working_dir:
            working_dir = "."
        
        work_path = Path.cwd() / working_dir
        
        if not work_path.exists():
            return "No project directory found yet."
        
        # List key files and directories
        summary_lines = []
        try:
            # Get top-level items
            items = sorted(work_path.iterdir())
            dirs = [d.name for d in items if d.is_dir() and not d.name.startswith('.')]
            files = [f.name for f in items if f.is_file() and not f.name.startswith('.')]
            
            if dirs:
                summary_lines.append(f"**Directories**: {', '.join(dirs[:10])}")
            if files:
                summary_lines.append(f"**Key Files**: {', '.join(files[:15])}")
            
            # Check for common project files
            common_files = ["pyproject.toml", "package.json", "requirements.txt", "README.md", "Makefile"]
            found_files = [f for f in common_files if (work_path / f).exists()]
            if found_files:
                summary_lines.append(f"**Project Files**: {', '.join(found_files)}")
            
        except Exception as e:
            summary_lines.append(f"Error reading directory: {e}")
        
        return "\n".join(summary_lines) if summary_lines else "Empty project directory."
    
    def _execute_story(self, story: Dict, prd: Dict, iteration: int) -> bool:
        """Execute a single story using Claude Code."""
        # Track execution time for this story
        story_start_time = time.time()

        # Build agent context
        context = self._build_context(story, prd)

        # Build prompt
        prompt = self._build_agent_prompt(story, context)

        # Determine working directory for execution
        working_dir = context.get('workingDirectory')
        if working_dir:
            work_path = Path.cwd() / working_dir
            work_path.mkdir(parents=True, exist_ok=True)
        else:
            work_path = Path.cwd()

        # Create detailed log file for this story
        logs_dir = Path.cwd() / "logs"
        logs_dir.mkdir(exist_ok=True)
        detail_log = logs_dir / f"story-{story['id']}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"

        if HAS_RICH:
            console.print(Panel(
                f"[bold cyan]Story {story['id']}: {story['title']}[/bold cyan]\n"
                f"[dim]Iteration {iteration}[/dim]\n"
                f"[dim]Log file: {detail_log}[/dim]",
                title="🤖 Claude Code Agent",
                border_style="cyan"
            ))
        else:
            print(f"🤖 Spawning Claude Code agent for story {story['id']}...")
            print(f"   Log file: {detail_log}")

        try:
            # Write prompt to log file
            with open(detail_log, 'w') as f:
                f.write("=" * 80 + "\n")
                f.write(f"Story: {story['id']} - {story['title']}\n")
                f.write(f"Iteration: {iteration}\n")
                f.write(f"Started: {datetime.now().isoformat()}\n")
                f.write("=" * 80 + "\n\n")
                f.write("PROMPT:\n")
                f.write("-" * 80 + "\n")
                f.write(prompt)
                f.write("\n" + "-" * 80 + "\n\n")
                f.write("CLAUDE CODE OUTPUT:\n")
                f.write("-" * 80 + "\n")

            # Determine if we should use streaming output
            use_streaming = self.config.get("ralph.useStreaming", True)
            
            if use_streaming:
                # Use claude-stream.py for real-time streaming output
                script_path = Path(__file__).parent / "claude-stream.py"
                cmd = [
                    "python3",
                    str(script_path),
                    "--dangerously-skip-permissions",
                    "--model", self.config.get("claude.model", "claude-sonnet-4-5-20250929"),
                    "-p", prompt
                ]
                
                # Use Popen to stream output in real-time while also capturing it
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,  # Line buffered
                    cwd=work_path
                )
                
                # Stream output in real-time and capture it
                agent_output_lines = []
                timeout_seconds = self.config.get("ralph.iterationTimeout", 3600)
                start_time = time.time()
                
                try:
                    for line in process.stdout:
                        print(line, end='', flush=True)  # Print immediately
                        agent_output_lines.append(line)

                        # Also write to detail log in real-time
                        with open(detail_log, 'a') as f:
                            f.write(line)
                        
                        # Check for timeout
                        if time.time() - start_time > timeout_seconds:
                            process.kill()
                            agent_output = ''.join(agent_output_lines)
                            raise subprocess.TimeoutExpired(cmd, timeout_seconds)
                    
                    process.wait()
                    agent_output = ''.join(agent_output_lines)
                    return_code = process.returncode
                except subprocess.TimeoutExpired:
                    process.kill()
                    agent_output = ''.join(agent_output_lines)
                    raise
            else:
                # Fallback to original non-streaming approach
                result = subprocess.run(
                    [
                        "claude",
                        "--dangerously-skip-permissions",
                        "--model", self.config.get("claude.model", "claude-sonnet-4-5-20250929"),
                        prompt  # Pass prompt as final argument
                    ],
                    capture_output=True,
                    text=True,
                    cwd=work_path,
                    timeout=self.config.get("ralph.iterationTimeout", 3600)
                )
                agent_output = result.stdout
                return_code = result.returncode

            # Write completion to log
            with open(detail_log, 'a') as f:
                f.write("\n" + "-" * 80 + "\n")
                f.write(f"Completed: {datetime.now().isoformat()}\n")
                f.write(f"Return code: {return_code}\n")
                f.write("=" * 80 + "\n")

            if return_code != 0:
                error_msg = f"Claude Code exited with error code {return_code}"
                if HAS_RICH:
                    console.print(Panel(
                        f"[bold red]{error_msg}[/bold red]\n"
                        f"[dim]Check log: {detail_log}[/dim]",
                        title="❌ Error",
                        border_style="red"
                    ))
                else:
                    print(f"❌ {error_msg}")
                    if not use_streaming:
                        print(f"   Full output: {agent_output}")

                if not use_streaming:
                    self._log_failure(story, agent_output + "\n\nSTDERR:\n" + result.stderr, None, iteration)
                else:
                    self._log_failure(story, agent_output, None, iteration)
                return False

            # Run quality gates
            if HAS_RICH:
                console.print("\n[bold yellow]🔍 Running quality gates...[/bold yellow]")
            else:
                print("🔍 Running quality gates...")

            quality_result = self.quality_gates.run()

            # Write quality results to log
            with open(detail_log, 'a') as f:
                f.write("\nQUALITY GATES:\n")
                f.write("-" * 80 + "\n")
                f.write(json.dumps(quality_result, indent=2))
                f.write("\n" + "-" * 80 + "\n")

            if quality_result["status"] == "PASS":
                # Calculate total story execution time
                total_story_duration = time.time() - story_start_time

                # Commit changes
                self._commit_changes(story, prd)

                # Update progress log
                self._update_progress_log(story, agent_output, quality_result, iteration)

                # Update agents.md if needed
                if self.config.get("ralph.updateAgentsMd", True):
                    self._update_agents_md(story, agent_output)

                # Show success summary
                if HAS_RICH:
                    console.print("\n")
                    console.print(Panel(
                        f"[bold green]✓ Story {story['id']} completed successfully![/bold green]\n\n"
                        f"[cyan]Title:[/cyan] {story['title']}\n"
                        f"[cyan]Total time:[/cyan] {total_story_duration:.1f}s\n"
                        f"[cyan]Log file:[/cyan] {detail_log}",
                        title="🎉 Success",
                        border_style="green"
                    ))
                else:
                    print(f"\n✅ Story {story['id']} completed successfully!")

                return True
            else:
                # Log failure
                self._log_failure(story, agent_output, quality_result, iteration)

                # Show failure summary
                if HAS_RICH:
                    console.print("\n")
                    console.print(Panel(
                        f"[bold red]✗ Story {story['id']} failed[/bold red]\n\n"
                        f"[cyan]Title:[/cyan] {story['title']}\n"
                        f"[cyan]Reason:[/cyan] Quality gates failed\n"
                        f"[cyan]Log file:[/cyan] {detail_log}",
                        title="❌ Failure",
                        border_style="red"
                    ))
                else:
                    print(f"\n❌ Story {story['id']} failed")

                return False

        except subprocess.TimeoutExpired:
            print(f"⏱️ Claude Code timed out after {self.config.get('ralph.iterationTimeout', 3600)}s")
            self._log_failure(story, "Claude Code execution timed out", None, iteration)
            return False
        except Exception as e:
            print(f"❌ Error executing story: {e}")
            self._log_failure(story, str(e), None, iteration)
            return False
    
    def _build_context(self, story: Dict, prd: Dict) -> Dict:
        """Build context for agent."""
        # Load progress log (recent entries)
        progress_file = Path(self.config.get("paths.progressFile", "progress.txt"))
        recent_progress = ""
        if progress_file.exists():
            with open(progress_file, 'r') as f:
                lines = f.readlines()
                # Get last 50 lines
                recent_progress = "".join(lines[-50:])

        # Find relevant agents.md files
        agents_md = self._find_agents_md()

        # Derive working directory from PRD project name or config
        working_dir = self.config.get("ralph.workingDirectory")
        if not working_dir and prd.get("project"):
            # Convert project name to directory name (kebab-case)
            working_dir = prd.get("project", "").lower().replace(" ", "-")
            # Remove special characters
            import re
            working_dir = re.sub(r'[^a-z0-9-]', '', working_dir)

        return {
            "story": story,
            "prd": {
                "description": prd.get("description", ""),
                "completedStories": [s["id"] for s in prd["userStories"] if s.get("passes", False)],
                "remainingStories": [s["id"] for s in prd["userStories"] if not s.get("passes", False)]
            },
            "progress": recent_progress,
            "agentsMd": agents_md,
            "projectConfig": {
                "commands": self.config.get("commands", {}),
                "qualityGates": self.config.get("qualityGates", {})
            },
            "workingDirectory": working_dir
        }
    
    def _build_agent_prompt(self, story: Dict, context: Dict) -> str:
        """Build prompt for Claude agent."""
        progress_section = f"\n## Recent Progress\n{context['progress']}" if context['progress'] else ""
        agents_section = f"\n## Agents.md\n{context['agentsMd']}" if context['agentsMd'] else ""

        # Add working directory instruction if specified
        working_dir = context.get('workingDirectory')
        working_dir_section = ""
        if working_dir:
            working_dir_section = f"""
## Working Directory

**IMPORTANT**: You are currently running in the `{working_dir}/` directory.
- All file paths are relative to this directory
- When you create files, they will be in `{working_dir}/`
- The project code is separate from the Ralph automation codebase
- Use relative paths (e.g., `memory/blocks.py`, not `{working_dir}/memory/blocks.py`)
"""

        # Build completed stories context with more detail
        completed_stories_context = ""
        if context['prd'].get('completedStories'):
            completed_stories_context = f"""
## What's Already Built

The following user stories have been completed and their code is in the codebase:
{chr(10).join(f"- {story_id}" for story_id in context['prd']['completedStories'])}

**IMPORTANT**: Before implementing, read the existing code to understand:
- What patterns are being used
- What utilities/helpers already exist
- How similar features are implemented
- What dependencies are available
"""

        return f"""You are an autonomous coding agent working on a software project.

## Your Task

Implement the following user story:

**Story ID**: {story['id']}
**Title**: {story['title']}
**Description**: {story.get('description', '')}

**Acceptance Criteria**:
{chr(10).join(f"- {c}" for c in story.get('acceptanceCriteria', []))}

## Project Context

**Project**: {context['prd'].get('description', 'Unknown')}
{completed_stories_context}
**Remaining Stories**: {', '.join(context['prd']['remainingStories'][:10]) or 'None'}{' (and more...)' if len(context['prd']['remainingStories']) > 10 else ''}
{progress_section}
{agents_section}
{working_dir_section}

## Implementation Strategy

Follow this incremental approach:

1. **Explore First** (5-10 minutes)
   - Read existing codebase to understand structure and patterns
   - Identify what utilities/helpers already exist
   - Check what dependencies are available
   - Understand how similar features are implemented

2. **Plan Implementation** (2-3 minutes)
   - Break down acceptance criteria into concrete tasks
   - Identify which files need to be created/modified
   - **Determine what tests are needed (BOTH unit tests with mocks AND E2E tests with real integrations!)**
   - Plan E2E tests FIRST - they verify actual functionality
   - Consider edge cases and error handling

3. **Implement Incrementally** (iterative)
   - Start with core functionality first
   - Build one acceptance criterion at a time
   - Test each piece as you build it
   - Follow existing code patterns and conventions
   - Keep files modular and focused (see file size guidance below)

4. **Verify Quality** (before finishing)
   - Run all acceptance criteria against your implementation
   - **Run E2E tests with real integrations (CRITICAL!) - this catches issues mocks miss**
   - Ensure code is clean and maintainable
   - Check that both E2E tests and unit tests exist and pass
   - Verify type safety and error handling
   - Check file sizes and refactor if needed (see file size guidance below)

## Auto-Installation of Missing Dependencies

**IMPORTANT**: If you encounter errors running commands due to missing tools or packages, you have permission to install them automatically.

### When to Auto-Install

If a command fails with errors like:
- "command not found"
- "No such file or directory"
- "package not found"
- Missing executables or tools

### How to Install

**On macOS (detected by `uname -s` == "Darwin"):**
- Use Homebrew: `brew install <package-name>`
- For Python packages: `pip install <package>` or `uv pip install <package>`
- For Node packages: `npm install -g <package>` or `npm install <package>`
- For system tools: `brew install <tool>`

**On Linux (detected by `uname -s` == "Linux"):**
- Use apt: `sudo apt-get update && sudo apt-get install -y <package>`
- Use yum/dnf: `sudo yum install -y <package>` or `sudo dnf install -y <package>`
- For Python packages: `pip install <package>` or `pip3 install <package>`
- For Node packages: `npm install -g <package>` or `npm install <package>`

**General Guidelines:**
- Check if tool exists first: `which <tool>` or `command -v <tool>`
- Install missing dependencies before retrying the failed command
- For Python projects, check if virtual environment needs activation
- For Node projects, check if `node_modules` needs installation
- You have permission to use `sudo` when needed for system packages

### Examples

```bash
# If `jq` command not found:
brew install jq  # macOS
sudo apt-get install -y jq  # Linux

# If Python package missing:
pip install missing-package
# or
uv pip install missing-package

# If Node command not found:
npm install -g typescript

# If git command fails, check if git is installed:
which git || brew install git  # macOS
```

**Always retry the original command after installation to verify it works.**

## File Size and Modularity

**CRITICAL**: Keep code files small, focused, and maintainable.

### File Size Limits
- **Maximum file size**: 500 lines (including imports, docstrings, and whitespace)
- **Target file size**: 200-300 lines for most files
- **If a file exceeds 500 lines**: Refactor it immediately into smaller modules

### When to Split Files

Split a file when:
- It exceeds 500 lines
- It contains multiple unrelated responsibilities
- It has more than 5-7 classes or 10-15 functions
- It handles multiple distinct concerns

### How to Refactor Large Files

1. **Identify logical groupings**: Group related functions/classes together
2. **Extract into separate modules**: Create new files for each logical grouping
3. **Use clear naming**: Module names should clearly indicate their purpose
4. **Update imports**: Ensure all imports are updated correctly
5. **Maintain public API**: Use `__init__.py` to re-export if needed

### Examples of Good File Organization

**Bad** (one large file):
```
slack_bot/client.py  (800 lines)
- Socket mode connection
- Event handlers
- Message formatting
- User management
- Channel management
- Error handling
- Logging setup
```

**Good** (split into focused modules):
```
slack_bot/
├── client.py           (150 lines) - Main client and connection
├── events.py           (200 lines) - Event handlers
├── formatting.py       (120 lines) - Message formatting
├── users.py            (180 lines) - User management
├── channels.py         (150 lines) - Channel management
└── errors.py           (100 lines) - Error handling
```

### Proactive Refactoring

**Before creating new code:**
- Check if existing files in the area are approaching 500 lines
- If so, refactor them first before adding new functionality
- This prevents files from growing too large

**When adding to existing files:**
- Check current file size first
- If adding would exceed 500 lines, refactor before adding
- Consider if the new code belongs in a separate module

### File Size Check

Before finishing your implementation:
1. Check line count of all modified/created files: `wc -l <file>`
2. If any file exceeds 500 lines, refactor it into smaller modules
3. Ensure each module has a single, clear responsibility
4. Update all imports and ensure tests still pass

## Quality Requirements & Testing

**CRITICAL**: After implementation, your code will be tested with quality gates. All gates must pass.

### Type Safety
- Add type hints to all function signatures
- Use strict typing (no `Any` unless absolutely necessary)
- Ensure mypy/pyright passes with no errors
- Import types from `typing` module as needed

### Testing Strategy

**CRITICAL**: You MUST implement BOTH unit tests AND end-to-end tests. E2E tests are the most important!

#### 1. End-to-End (E2E) Tests - **REQUIRED**
- **Purpose**: Verify the ACTUAL functionality works with real integrations
- **What to test**: Full user-facing workflows with real external systems
- **Examples**:
  - CLI that calls Anthropic API → Test with REAL API calls
  - Database operations → Test with REAL database
  - File I/O → Test with REAL file system
  - Network requests → Test with REAL endpoints (or local test servers)
- **How to mark**: Use `@pytest.mark.e2e` decorator
- **API Keys**: Use `@pytest.mark.skipif(not os.getenv('API_KEY'))` to skip if missing
- **Critical**: E2E tests catch issues that mocks miss (model names, API changes, auth issues)

#### 2. Unit Tests - Use Mocks
- **Purpose**: Test individual functions and classes in isolation
- **When to mock**: External APIs, databases, network calls (but only in unit tests!)
- **Examples**: `@patch('anthropic.Anthropic')`, `@patch('requests.get')`

#### 3. Integration Tests
- **Purpose**: Test how components work together (but may still use test doubles)
- **Examples**: Multiple modules interacting, data flowing through system

#### 4. Edge Cases
- **Purpose**: Test boundary conditions, empty inputs, error states

**Test file naming**: `test_<module_name>.py` or `test_<feature>_e2e.py` for E2E tests

**Running tests**:
```bash
pytest tests/              # Run all tests
pytest tests/ -m e2e       # Run only E2E tests
pytest tests/ -m "not e2e" # Run only unit/integration tests
```

### Code Quality
- Follow existing code patterns and conventions
- Keep functions small and focused (< 50 lines)
- Use descriptive variable and function names
- Add docstrings for public functions and classes
- Handle errors gracefully with try/except where appropriate
- No commented-out code or debug print statements
- Clean up imports (no unused imports)

### Linting & Formatting
- Code must pass linting (ruff, pylint, or project-specific linter)
- Follow PEP 8 style guidelines
- Use consistent formatting (spaces, line breaks, etc.)
- Maximum line length: 100-120 characters

### Self-Review Checklist

Before finishing, verify:
- [ ] All acceptance criteria are met
- [ ] Type hints added to all functions
- [ ] **END-TO-END TESTS written and passing** (with real integrations - CRITICAL!)
- [ ] Unit tests written and passing (with mocks for external dependencies)
- [ ] **All files are under 500 lines** (check with `wc -l`)
- [ ] Large files refactored into smaller, focused modules
- [ ] No obvious bugs or edge cases missed
- [ ] Error handling is appropriate
- [ ] Code follows existing patterns
- [ ] No debug code or print statements left in
- [ ] Documentation/comments added where needed

**CRITICAL REMINDER**: If your feature calls external APIs, databases, or services, you MUST have E2E tests that verify it works with the REAL system. Mocked unit tests alone are NOT sufficient!

## Output Format

After implementing, provide a summary with:

**✅ Implemented:**
- List of acceptance criteria met
- Key files created/modified
- File sizes (line counts) for all new/modified code files

**🧪 Tests:**
- **E2E tests**: List E2E test files and what they verify (REQUIRED if feature has external integrations)
- **Unit tests**: List unit test files and coverage
- Test coverage areas
- How to run the tests (including how to run E2E tests with API keys)

**🔧 Refactoring:**
- Any files that were split/refactored due to size
- Any proactive refactoring done to keep files under 500 lines

**📝 Notes:**
- Any important patterns or decisions made
- Dependencies added
- Known limitations or future improvements needed

Begin implementation now."""
    
    def _find_agents_md(self) -> str:
        """Find and load relevant agents.md files."""
        agents_files = []
        
        # Look for agents.md in current directory and parents
        current = Path.cwd()
        for _ in range(3):  # Check up to 3 levels up
            agents_path = current / "AGENTS.md"
            if agents_path.exists():
                with open(agents_path, 'r') as f:
                    agents_files.append(f"## {current.name}\n{f.read()}")
            current = current.parent
        
        return "\n\n".join(agents_files)
    
    def _commit_changes(self, story: Dict, prd: Dict = None):
        """Commit changes to git in the working directory."""
        try:
            # Get working directory
            working_dir = self.config.get("ralph.workingDirectory")
            if not working_dir and prd:
                # Derive from PRD project name
                import re
                working_dir = prd.get("project", "").lower().replace(" ", "-")
                working_dir = re.sub(r'[^a-z0-9-]', '', working_dir)

            if not working_dir:
                working_dir = "."

            work_path = Path.cwd() / working_dir

            if not work_path.exists():
                print(f"   ⚠️  Working directory {working_dir} doesn't exist")
                return

            # Check if there are changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=work_path
            )

            if not result.stdout.strip():
                print("   No changes to commit")
                return

            # Get or create branch from PRD
            branch_name = prd.get("branchName", "main") if prd else "main"

            # Check current branch
            current_branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                cwd=work_path
            )
            current_branch = current_branch_result.stdout.strip()

            # Create and checkout branch if needed
            if current_branch != branch_name:
                print(f"   📌 Creating/switching to branch: {branch_name}")
                # Try to create branch (will fail if exists, that's ok)
                subprocess.run(
                    ["git", "checkout", "-b", branch_name],
                    capture_output=True,
                    cwd=work_path
                )
                # If that failed, try to checkout existing branch
                subprocess.run(
                    ["git", "checkout", branch_name],
                    capture_output=True,
                    cwd=work_path
                )

            # Commit
            commit_msg = self.config.get("git.commitMessageFormat", "feat: {story_id} - {story_title}").format(
                story_id=story["id"],
                story_title=story["title"]
            )

            subprocess.run(
                ["git", "add", "."],
                check=True,
                cwd=work_path
            )

            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                check=True,
                cwd=work_path
            )

            if HAS_RICH:
                console.print(Panel(
                    f"[bold green]✓ Changes committed[/bold green]\n\n"
                    f"[cyan]Branch:[/cyan] {branch_name}\n"
                    f"[cyan]Message:[/cyan] {commit_msg}\n"
                    f"[dim]Working directory: {work_path}[/dim]",
                    title="📦 Git Commit",
                    border_style="green"
                ))
            else:
                print(f"   ✅ Committed to branch '{branch_name}': {commit_msg}")
                print(f"   📍 Branch: {branch_name}")

        except subprocess.CalledProcessError as e:
            print(f"   ⚠️  Git commit failed: {e}")
        except FileNotFoundError:
            print("   ⚠️  Git not found, skipping commit")
    
    def _update_progress_log(self, story: Dict, agent_output: str, quality_result: Dict, iteration: int):
        """Update progress.txt with iteration results."""
        progress_file = Path(self.config.get("paths.progressFile", "progress.txt"))
        
        # Initialize if needed
        if not progress_file.exists():
            with open(progress_file, 'w') as f:
                f.write(f"# Ralph Progress Log\n")
                f.write(f"Started: {datetime.now().isoformat()}\n")
                f.write(f"---\n\n")
        
        # Append iteration log
        with open(progress_file, 'a') as f:
            f.write(f"\n## Iteration {iteration} - {story['id']} - {datetime.now().isoformat()}\n")
            f.write(f"**Story**: {story['title']}\n")
            f.write(f"**Status**: ✅ PASSED\n")
            f.write(f"**Duration**: {quality_result.get('totalDuration', 0):.1f}s\n")
            f.write(f"\n**Quality Gates**:\n")
            for gate_name, gate_result in quality_result.get("gates", {}).items():
                status = "✅" if gate_result["status"] == "PASS" else "❌"
                f.write(f"- {status} {gate_name}: {gate_result['status']} ({gate_result['duration']:.1f}s)\n")
            f.write(f"\n**Agent Output**:\n```\n{agent_output[:500]}...\n```\n")
            f.write(f"\n---\n")
    
    def _log_failure(self, story: Dict, agent_output: str, quality_result: Optional[Dict], iteration: int):
        """Log failure to progress.txt."""
        progress_file = Path(self.config.get("paths.progressFile", "progress.txt"))
        
        with open(progress_file, 'a') as f:
            f.write(f"\n## Iteration {iteration} - {story['id']} - {datetime.now().isoformat()}\n")
            f.write(f"**Story**: {story['title']}\n")
            f.write(f"**Status**: ❌ FAILED\n")
            
            if quality_result:
                f.write(f"**Quality Gates**:\n")
                for gate_name, gate_result in quality_result.get("gates", {}).items():
                    status = "✅" if gate_result["status"] == "PASS" else "❌"
                    f.write(f"- {status} {gate_name}: {gate_result['status']}\n")
                    if gate_result["status"] == "FAIL":
                        f.write(f"  ```\n{gate_result.get('output', '')[:500]}\n  ```\n")
            
            f.write(f"\n**Agent Output**:\n```\n{agent_output[:500]}...\n```\n")
            f.write(f"\n---\n")
    
    def _update_agents_md(self, story: Dict, agent_output: str):
        """Update agents.md files with learnings."""
        # This is a simplified version - in practice, you'd parse agent_output
        # to extract learnings and update relevant agents.md files
        # For now, we'll skip this as it requires more sophisticated parsing
        pass


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Ralph: Autonomous AI Agent Loop")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # process-prd command
    prd_parser = subparsers.add_parser("process-prd", help="Convert PRD markdown to prd.json")
    prd_parser.add_argument("prd_file", type=Path, help="Path to PRD markdown file")
    prd_parser.add_argument("--output", type=Path, help="Output prd.json path")
    
    # execute-plan command
    exec_parser = subparsers.add_parser("execute-plan", help="Execute Ralph loop")
    exec_parser.add_argument("--prd", type=Path, help="Path to prd.json file")
    exec_parser.add_argument("--max-iterations", type=int, help="Max iterations (0 = unlimited)")
    exec_parser.add_argument("--phase", type=int, help="Execute only stories in this phase (e.g., 1, 2, 3)")
    exec_parser.add_argument("--config", type=Path, help="Path to config file")
    
    # status command
    status_parser = subparsers.add_parser("status", help="Show Ralph status")
    status_parser.add_argument("--prd", type=Path, help="Path to prd.json file")
    
    # init command
    init_parser = subparsers.add_parser("init", help="Initialize Ralph configuration")
    init_parser.add_argument("--detect-config", action="store_true", help="Auto-detect project configuration")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Note: API key is optional - Anthropic SDK will use Claude Code authentication if available
    # Load config
    config_path = args.config if hasattr(args, 'config') and args.config else None
    config = RalphConfig(config_path)
    
    if args.command == "process-prd":
        parser = PRDParser(config)
        parser.parse_prd(args.prd_file, args.output)
    
    elif args.command == "execute-plan":
        loop = RalphLoop(config)
        phase = args.phase if hasattr(args, 'phase') else None
        loop.execute(args.prd, args.max_iterations, phase=phase)
    
    elif args.command == "status":
        prd_path = args.prd or Path(config.get("paths.prdFile", "prd.json"))
        if prd_path.exists():
            with open(prd_path, 'r') as f:
                prd = json.load(f)
            completed = sum(1 for s in prd["userStories"] if s.get("passes", False))
            total = len(prd["userStories"])
            print(f"Status: {completed}/{total} stories completed")
        else:
            print("No prd.json found")
    
    elif args.command == "init":
        config.save()
        print(f"✅ Configuration saved to {config.config_path}")


if __name__ == "__main__":
    main()
