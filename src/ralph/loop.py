"""Ralph execution loop.

NOTE: This file is large and exceeds the recommended 500-line limit.
Future work should split this into:
- story_selection.py (story selection logic)
- context_builder.py (context and prompt building)
- story_executor.py (execution)
- session_reporter.py (reporting and summaries)
"""

import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING

try:
    from rich.console import Console
    from rich.panel import Panel

    HAS_RICH = True
    console: Optional[Console] = Console()
except ImportError:
    HAS_RICH = False
    console = None

if TYPE_CHECKING:
    from ralph.config import RalphConfig


class RalphLoop:
    """Main Ralph execution loop."""

    def __init__(self, config: "RalphConfig", verbose: bool = False):
        """Initialize Ralph loop.

        Args:
            config: RalphConfig instance
            verbose: Show verbose output
        """
        self.config = config
        self.verbose = verbose
        self.failure_count = 0
        self.last_story_id: Optional[str] = None
        self.session_start_time: Optional[float] = None
        self.session_completed_stories: List[Dict] = []  # Stories completed in this session
        self.initial_completed_count = 0  # Stories completed before session started

    def _load_guardrails(self) -> str:
        """Load guardrails from .ralph/guardrails.md if it exists."""
        guardrails_path = self.config.guardrails_path
        if guardrails_path.exists():
            try:
                with open(guardrails_path, 'r') as f:
                    return f.read()
            except Exception:
                pass
        return ""

    def _update_guardrails(self, story: Dict, error_summary: str, failure_count: int) -> None:
        """Update guardrails file with a new learning after repeated failures.

        Only updates after 2+ consecutive failures on the same story.
        """
        if failure_count < 2:
            return

        guardrails_path = self.config.guardrails_path

        # Create file with header if it doesn't exist
        if not guardrails_path.exists():
            guardrails_path.parent.mkdir(parents=True, exist_ok=True)
            with open(guardrails_path, 'w') as f:
                f.write("# Guardrails\n\n")
                f.write("Learnings from failures to prevent repeated mistakes.\n\n")
                f.write("---\n\n")

        # Append new learning
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(guardrails_path, 'a') as f:
            f.write(f"## {story['id']}: {story['title']}\n")
            f.write(f"**Added**: {timestamp} (after {failure_count} failures)\n\n")
            f.write(f"**Issue**:\n```\n{error_summary[:500]}\n```\n\n")
            f.write("**Rule**: _[Agent should analyze and fill this in on next iteration]_\n\n")
            f.write("---\n\n")

        if HAS_RICH and console:
            console.print(f"[yellow]📝 Updated guardrails with learning from {story['id']}[/yellow]")
        else:
            print(f"📝 Updated guardrails with learning from {story['id']}")

    def _get_design_doc(self, prd: Dict) -> Optional[str]:
        """Get design document path from PRD if specified."""
        design_doc = prd.get("designDoc", {})
        if isinstance(design_doc, dict):
            return design_doc.get("path")
        elif isinstance(design_doc, str):
            return design_doc
        return None

    def _build_completed_stories_prose(self, prd: Dict) -> str:
        """Build a prose description of what's been completed, not just IDs."""
        completed = [s for s in prd.get("userStories", []) if s.get("status") == "complete"]
        if not completed:
            return ""

        # Group by phase if phases exist
        phases = prd.get("phases", {})
        if phases:
            by_phase: Dict[int, List[Dict]] = {}
            for story in completed:
                phase = story.get("phase", 1)
                if phase not in by_phase:
                    by_phase[phase] = []
                by_phase[phase].append(story)

            lines = []
            for phase_num in sorted(by_phase.keys()):
                phase_info = phases.get(str(phase_num), {})
                phase_name = phase_info.get("name", f"Phase {phase_num}")
                lines.append(f"\n**{phase_name}**:")
                for story in by_phase[phase_num]:
                    # Use title as the main description
                    lines.append(f"- {story['title']}")
            return "\n".join(lines)
        else:
            # No phases, just list stories
            lines = []
            for story in completed:
                lines.append(f"- {story['title']}")
            return "\n".join(lines)

    def _generate_feature_summary(self, completed_stories: List[Dict], remaining_stories: List[Dict], prd: Dict) -> str:
        """Generate AI-powered feature summary of what was built and what's testable."""
        if not completed_stories:
            return ""

        try:
            # Build context for Claude
            completed_details = []
            for story_info in completed_stories:
                # Find full story details from PRD
                full_story = next((s for s in prd["userStories"] if s["id"] == story_info["id"]), None)
                if full_story:
                    completed_details.append({
                        "id": full_story["id"],
                        "title": full_story["title"],
                        "description": full_story.get("description", ""),
                        "acceptanceCriteria": full_story.get("acceptanceCriteria", [])
                    })

            # Build remaining stories context (limited)
            remaining_details = []
            for story in remaining_stories[:5]:  # Only first 5 for context
                remaining_details.append({
                    "id": story["id"],
                    "title": story["title"]
                })

            prompt = f"""You are summarizing a software development session for the PROJECT OWNER.

## Project Context
**Project**: {prd.get('project', 'Unknown')}
**Description**: {prd.get('description', '')}

## Stories Completed This Session
{json.dumps(completed_details, indent=2)}

## Remaining Stories (Next Up)
{json.dumps(remaining_details, indent=2) if remaining_details else "All stories completed!"}

## Your Task
Write a concise, user-friendly summary that answers:
1. **What features were added?** (in plain language, not technical jargon)
2. **What can the user test/try right now?** (specific commands, actions, or ways to verify)
3. **What's the practical impact?** (what can they do now that they couldn't before)
4. **What's still pending?** (high-level feature areas, not story IDs)

## Guidelines
- Use conversational language ("You can now..." not "Story US-001 implements...")
- Focus on USER-FACING changes and capabilities
- Be specific about how to test/verify (include actual commands if applicable)
- Keep it concise (4-8 bullet points max)
- If CLI commands exist, show them
- If it's infrastructure work with no immediate user impact, explain what it enables
- Emphasize what's TESTABLE right now vs what's coming later

## Output Format
Return ONLY the summary text (no JSON, no headers). Use emoji sparingly for visual clarity.
Start with "🎯 FEATURES ADDED THIS SESSION" and then bullet points.
End with a "What's Next" section if there are remaining stories."""

            # Call Claude Code CLI (uses OAuth, no API key needed)
            from ralph.prd import call_claude_code

            model = self.config.get("claude.model", "claude-sonnet-4-5-20250929")
            response_text = call_claude_code(prompt, model=model, timeout=120)

            return response_text

        except Exception as e:
            # If AI summary fails, return empty string (fall back to mechanical summary)
            print(f"   ⚠️  Could not generate feature summary: {e}")
            return ""

    def _print_session_summary(self, prd: Dict, iteration_count: int, _prd_path: Path) -> None:
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
        current_completed = sum(1 for s in prd["userStories"] if s.get("status") == "complete")
        remaining_stories = total_stories - current_completed
        session_completed_count = len(self.session_completed_stories)

        # Generate AI feature summary first if we completed stories
        feature_summary = ""
        if session_completed_count > 0:
            remaining = [s for s in prd["userStories"] if s.get("status", "incomplete") not in ("complete", "skipped")]
            feature_summary = self._generate_feature_summary(
                self.session_completed_stories,
                remaining,
                prd
            )

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

        # Print AI-generated feature summary if available
        if feature_summary:
            print("\n" + "-"*80)
            print(feature_summary)
            print("-"*80)

        # Stories completed this session (technical details)
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
            remaining = [s for s in prd["userStories"] if s.get("status", "incomplete") not in ("complete", "skipped")]
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

    def show_info(self, prd_path: Optional[Path] = None, phase: Optional[int] = None) -> None:
        """Show startup banner and PRD info without executing anything."""
        from ralph.utils import show_ralph_banner

        prd_path = prd_path or self.config.prd_path

        if not prd_path.exists():
            raise FileNotFoundError(f"PRD file not found: {prd_path}")

        # Load PRD
        with open(prd_path, 'r') as f:
            prd = json.load(f)

        max_iter = self.config.get("ralph.maxIterations", 20)
        max_failures = self.config.get("ralph.maxFailures", 3)

        # Display Ralph ASCII art
        show_ralph_banner()

        # Display phase info if filtering by phase
        phase_info = ""
        if phase is not None:
            phase_info = f"\n   🎯 Phase Filter: Phase {phase}"

        print(f"\n🚀 Ralph - Autonomous AI Agent Loop")
        print(f"   Project: {prd.get('project', 'Unknown')}")
        print(f"   Branch: {prd.get('branchName', 'N/A')}")
        print(f"   Max iterations: {max_iter if max_iter > 0 else 'unlimited'}")
        print(f"   Max consecutive failures: {max_failures}")

        # Count stories
        all_stories = prd.get('userStories', [])
        completed = sum(1 for s in all_stories if s.get('status') == 'complete')
        total = len(all_stories)

        stories_to_complete = [s for s in all_stories if s.get('status', 'incomplete') not in ('complete', 'skipped')]
        if phase is not None:
            stories_to_complete = [s for s in stories_to_complete if s.get('phase') == phase]

        print(f"   Progress: {completed}/{total} stories ({completed/total*100:.0f}%)")
        print(f"   Stories to complete: {len(stories_to_complete)}{phase_info}")

        # Show phases summary (derived from stories)
        phases_from_stories: Dict[int, List[Dict]] = {}
        for story in all_stories:
            p = story.get("phase", 0)
            if p not in phases_from_stories:
                phases_from_stories[p] = []
            phases_from_stories[p].append(story)

        if phases_from_stories and HAS_RICH:
            print()
            for phase_num in sorted(phases_from_stories.keys()):
                if phase_num == 0:
                    continue  # Skip unphased stories in summary
                phase_stories = phases_from_stories[phase_num]
                phase_completed = sum(1 for s in phase_stories if s.get("status") == "complete")
                phase_total = len(phase_stories)
                if phase_completed == phase_total:
                    status = "✅"
                elif phase_completed > 0:
                    status = "🔄"
                else:
                    status = "⏳"
                print(f"   {status} Phase {phase_num} ({phase_completed}/{phase_total})")

        # Show next story
        if stories_to_complete:
            next_story = min(stories_to_complete, key=lambda s: (s.get('phase', 999), s.get('priority', 999)))
            print(f"\n   ➡️  Next: {next_story['id']} - {next_story['title']}")

        print(f"\n   💡 To execute: python ralph.py execute-plan" + (f" --phase {phase}" if phase else ""))
        print()

    def execute(self, prd_path: Optional[Path] = None, max_iterations: Optional[int] = None, phase: Optional[int] = None) -> None:
        """Execute Ralph loop until completion or max iterations.

        Args:
            prd_path: Path to prd.json file
            max_iterations: Maximum number of iterations (0 = unlimited)
            phase: Only execute stories in this phase (None = all incomplete stories)
        """
        from ralph.utils import show_ralph_banner

        prd_path = prd_path or self.config.prd_path

        if not prd_path.exists():
            raise FileNotFoundError(f"PRD file not found: {prd_path}")

        # Load PRD
        with open(prd_path, 'r') as f:
            prd = json.load(f)

        # Track session start
        self.session_start_time = time.time()

        # Track initial state
        self.initial_completed_count = sum(1 for s in prd["userStories"] if s.get("status") == "complete")

        max_iter = max_iterations or self.config.get("ralph.maxIterations", 20)
        max_failures = self.config.get("ralph.maxFailures", 3)

        # Display Ralph ASCII art
        show_ralph_banner()

        # Display phase info if filtering by phase
        phase_info = ""
        if phase is not None:
            phase_info = f"\n   🎯 Phase Filter: Phase {phase}"

        print(f"\n🚀 Starting Ralph Loop")
        print(f"   Max iterations: {max_iter if max_iter > 0 else 'unlimited'}")
        print(f"   Max consecutive failures: {max_failures}")

        # Count stories to complete (with optional phase filter)
        stories_to_complete = [s for s in prd['userStories'] if s.get('status', 'incomplete') not in ('complete', 'skipped')]
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
            remaining_stories = [s for s in prd["userStories"] if s.get("status", "incomplete") not in ("complete", "skipped")]
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

            if HAS_RICH and console:
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

            # Mark story as in-progress and save PRD (so viewers can see it)
            story["status"] = "in_progress"
            story["startedAt"] = datetime.now().isoformat()
            prd["metadata"]["lastUpdatedAt"] = datetime.now().isoformat()
            with open(prd_path, 'w') as f:
                json.dump(prd, f, indent=2)

            # Execute story
            success = self._execute_story(story, prd, iteration)
            
            iteration_duration = time.time() - iteration_start
            
            if success:
                self.failure_count = 0  # Reset failure count on success
                story["status"] = "complete"
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
                    1 for s in prd["userStories"] if s.get("status") == "complete"
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

                # Update guardrails after 2+ consecutive failures on same story
                if self.failure_count >= 2 and self.last_story_id == story['id']:
                    # Get error summary from the progress file (last failure logged)
                    progress_file = self.config.progress_path
                    error_summary = ""
                    if progress_file.exists():
                        with open(progress_file, 'r') as f:
                            lines = f.readlines()
                            # Get last 20 lines for error context
                            error_summary = "".join(lines[-20:])
                    self._update_guardrails(story, error_summary, self.failure_count)
            
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
                    if dep_story and dep_story.get("status", "incomplete") not in ("complete", "skipped"):
                        dependencies_satisfied = False
                        break
            
            if dependencies_satisfied:
                runnable.append(story)
        
        return runnable[0] if runnable else stories[0]
    
    def _select_next_story_with_claude(self, stories: List[Dict], prd: Dict) -> Dict:
        """Use Claude to intelligently select the next story based on codebase analysis."""
        from ralph.prd import call_claude_code

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
        completed_stories = [s for s in prd["userStories"] if s.get("status") == "complete"]
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

        # Call Claude Code CLI (uses OAuth, no API key needed)
        model = self.config.get("claude.model", "claude-sonnet-4-5-20250929")

        response_text = call_claude_code(prompt, model=model, timeout=120)
        
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
        
        if not working_dir or working_dir == ".":
            work_path = self.config.project_dir
        else:
            work_path = self.config.project_dir / working_dir

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
        # Mark story as in_progress
        story["status"] = "in_progress"

        # Track execution time for this story
        story_start_time = time.time()

        # Build agent context
        context = self._build_context(story, prd)

        # Build prompt
        prompt = self._build_agent_prompt(story, context)

        # Determine working directory for execution
        working_dir = context.get('workingDirectory')
        if working_dir and working_dir != ".":
            work_path = self.config.project_dir / working_dir
            work_path.mkdir(parents=True, exist_ok=True)
        else:
            work_path = self.config.project_dir

        # Create detailed log file for this story
        logs_dir = self.config.logs_dir
        logs_dir.mkdir(exist_ok=True)
        detail_log = logs_dir / f"story-{story['id']}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"

        if HAS_RICH and console:
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
                ]
                # Add verbose flags if requested
                if self.verbose:
                    cmd.extend(["--verbose", "--show-prompt"])
                cmd.extend(["-p", prompt])
                
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
                    assert process.stdout is not None, "stdout should not be None"
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
                if HAS_RICH and console:
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

            # Calculate total story execution time
            total_story_duration = time.time() - story_start_time

            # Commit changes
            self._commit_changes(story, prd)

            # Update progress log
            self._update_progress_log(story, agent_output, iteration)

            # Update agents.md if needed
            if self.config.get("ralph.updateAgentsMd", True):
                self._update_agents_md(story, agent_output)

            # Show success summary
            if HAS_RICH and console:
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
        # Load progress log (recent entries) from .ralph/progress.md
        progress_file = self.config.progress_path
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

        # Load guardrails (learned failures)
        guardrails = self._load_guardrails()

        # Get design doc reference
        design_doc_path = self._get_design_doc(prd)

        # Build prose description of completed work
        completed_prose = self._build_completed_stories_prose(prd)

        # Count remaining stories
        remaining_count = len([s for s in prd["userStories"] if s.get("status", "incomplete") not in ("complete", "skipped")])

        return {
            "story": story,
            "prd": {
                "project": prd.get("project", ""),
                "description": prd.get("description", ""),
                "completedProse": completed_prose,
                "remainingCount": remaining_count,
                "designDocPath": design_doc_path
            },
            "progress": recent_progress,
            "agentsMd": agents_md,
            "guardrails": guardrails,
            "projectConfig": {
                "commands": self.config.get("commands", {})
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

        # Build completed stories context with prose descriptions
        completed_stories_context = ""
        completed_prose = context['prd'].get('completedProse', '')
        if completed_prose:
            completed_stories_context = f"""
## What's Already Built

The following features have been implemented and their code is in the codebase:
{completed_prose}

**IMPORTANT**: Before implementing, read the existing code to understand:
- What patterns are being used
- What utilities/helpers already exist
- How similar features are implemented
- What dependencies are available
"""

        # Build guardrails section (learned failures)
        guardrails_section = ""
        guardrails = context.get('guardrails', '')
        if guardrails:
            guardrails_section = f"""
## Guardrails (Learned from Past Failures)

**READ THIS CAREFULLY** - These are patterns that caused failures in previous iterations:

{guardrails}

Follow these rules to avoid repeating the same mistakes.
"""

        # Build design document reference section
        design_doc_section = ""
        design_doc_path = context['prd'].get('designDocPath')
        if design_doc_path:
            design_doc_section = f"""
## Design Document

A design document is available at: `{design_doc_path}`

**IMPORTANT**: If you need to understand:
- Overall architecture decisions
- How components should interact
- Design patterns to follow
- Implementation guidelines

Read the design document for detailed guidance.
"""

        # Remaining work context
        remaining_context = ""
        remaining_count = context['prd'].get('remainingCount', 0)
        if remaining_count > 1:
            remaining_context = f"\n**Remaining**: {remaining_count - 1} more stories after this one."

        return f"""You are an autonomous coding agent working on a software project.

## Your Task

Implement the following user story:

**Story ID**: {story['id']}
**Title**: {story['title']}
**Description**: {story.get('description', '')}

**Acceptance Criteria**:
{chr(10).join(f"- {c}" for c in story.get('acceptanceCriteria', []))}

## Project Context

**Project**: {context['prd'].get('project', '')} - {context['prd'].get('description', 'Unknown')}{remaining_context}
{design_doc_section}
{guardrails_section}
{completed_stories_context}
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

**CRITICAL**: Ensure your implementation meets quality standards.

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

## Continuous Improvement: Skills & Documentation

As you work, you should continuously improve the codebase's tooling and documentation.

### Creating Claude Code Skills

**IMPORTANT**: Create skills in `.claude/skills/` for reusable operations you discover or implement.

Skills make future work faster and more reliable. Create a skill when you:
- Run the same sequence of commands repeatedly (build, test, deploy)
- Discover project-specific patterns or workflows
- Implement something that would help future agents

**Skill structure** (create in `.claude/skills/<skill-name>/SKILL.md`):
```yaml
---
name: skill-name-kebab-case
description: Brief description of when to use this skill (triggers automatic loading)
---

# Skill Name

## Quick Start
[Most common usage pattern]

## Commands
[Key commands with explanations]

## Examples
[Concrete examples]

## Common Issues
[Troubleshooting tips]
```

**Skills to consider creating:**
- `build` - How to build the project
- `test` - How to run tests (unit, E2E, specific modules)
- `lint` - How to lint and auto-fix
- `deploy` - Deployment steps if applicable
- `db-migrate` - Database migration commands
- Project-specific workflows

**Example skill** (`.claude/skills/test/SKILL.md`):
```yaml
---
name: test
description: Run tests for this project. Use when asked to test, verify, or check code works.
---

# Testing

## Quick Start
```bash
pytest tests/           # All tests
pytest tests/ -m e2e    # E2E tests only (requires API keys)
```

## Test Categories
- Unit tests: `pytest tests/ -m "not e2e"`
- E2E tests: `ANTHROPIC_API_KEY=xxx pytest -m e2e`

## Coverage
```bash
pytest --cov=src --cov-report=html
```
```

### Updating AGENTS.md

**IMPORTANT**: If you discover important codebase patterns, conventions, or knowledge that would help future agents, update `AGENTS.md`.

Add to AGENTS.md when you discover:
- Project structure patterns
- Naming conventions
- Architecture decisions
- Common gotchas or pitfalls
- Key dependencies and how they're used
- Testing patterns specific to this project

This helps future agents (and humans) work more effectively in this codebase.

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
    
    def _commit_changes(self, story: Dict, prd: Optional[Dict] = None) -> None:
        """Commit changes to git in the working directory."""
        try:
            # Get working directory
            working_dir = self.config.get("ralph.workingDirectory")
            if not working_dir and prd:
                # Derive from PRD project name
                import re
                working_dir = prd.get("project", "").lower().replace(" ", "-")
                working_dir = re.sub(r'[^a-z0-9-]', '', working_dir)

            if not working_dir or working_dir == ".":
                work_path = self.config.project_dir
            else:
                work_path = self.config.project_dir / working_dir

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

            if HAS_RICH and console:
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
    
    def _update_progress_log(self, story: Dict, agent_output: str, iteration: int) -> None:
        """Update .ralph/progress.md with iteration results."""
        progress_file = self.config.progress_path

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
            f.write(f"\n**Agent Output**:\n```\n{agent_output[:500]}...\n```\n")
            f.write(f"\n---\n")
    
    def _log_failure(self, story: Dict, agent_output: str, _unused: Optional[Dict], iteration: int) -> None:
        """Log failure to .ralph/progress.md."""
        progress_file = self.config.progress_path

        with open(progress_file, 'a') as f:
            f.write(f"\n## Iteration {iteration} - {story['id']} - {datetime.now().isoformat()}\n")
            f.write(f"**Story**: {story['title']}\n")
            f.write(f"**Status**: ❌ FAILED\n")
            f.write(f"\n**Agent Output**:\n```\n{agent_output[:500]}...\n```\n")
            f.write(f"\n---\n")
    
    def _update_agents_md(self, _story: Dict, _agent_output: str) -> None:
        """Update agents.md files with learnings."""
        # This is a simplified version - in practice, you'd parse agent_output
        # to extract learnings and update relevant agents.md files
        # For now, we'll skip this as it requires more sophisticated parsing
        pass

