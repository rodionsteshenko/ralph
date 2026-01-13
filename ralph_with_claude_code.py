#!/usr/bin/env python3
"""
Ralph with Claude Code Integration
Modified version that spawns Claude Code agents instead of just calling Claude API.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

# Add this method to RalphLoop class to replace _execute_story

def _execute_story_with_claude_code(self, story: dict, prd: dict, iteration: int) -> bool:
    """Execute a single story using Claude Code CLI."""
    # Build agent context
    context = self._build_context(story, prd)

    # Build prompt
    prompt = self._build_agent_prompt(story, context)

    # Write prompt to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        prompt_file = Path(f.name)
        f.write(prompt)

    print(f"🤖 Spawning Claude Code agent for story {story['id']}...")

    try:
        # Run Claude Code with the prompt
        # Using --dangerously-skip-permissions to auto-approve all actions
        result = subprocess.run(
            [
                "claude",
                "code",
                "--prompt-file", str(prompt_file),
                "--dangerously-skip-permissions",
                "--model", self.config.get("claude.model", "claude-sonnet-4-5-20250929")
            ],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
            timeout=self.config.get("ralph.iterationTimeout", 3600)
        )

        agent_output = result.stdout

        if result.returncode != 0:
            print(f"❌ Claude Code exited with error: {result.stderr}")
            self._log_failure(story, agent_output, None, iteration)
            return False

        # Run quality gates
        print("🔍 Running quality gates...")
        quality_result = self.quality_gates.run()

        if quality_result["status"] == "PASS":
            # Commit changes
            self._commit_changes(story)

            # Update progress log
            self._update_progress_log(story, agent_output, quality_result, iteration)

            # Update agents.md if needed
            if self.config.get("ralph.updateAgentsMd", True):
                self._update_agents_md(story, agent_output)

            return True
        else:
            # Log failure
            self._log_failure(story, agent_output, quality_result, iteration)
            return False

    except subprocess.TimeoutExpired:
        print(f"⏱️ Claude Code timed out after {self.config.get('ralph.iterationTimeout', 3600)}s")
        self._log_failure(story, "Timeout", None, iteration)
        return False
    except Exception as e:
        print(f"❌ Error executing story: {e}")
        self._log_failure(story, str(e), None, iteration)
        return False
    finally:
        # Clean up prompt file
        if prompt_file.exists():
            prompt_file.unlink()


# Alternate approach: Use subprocess to spawn interactive Claude Code session
def _execute_story_with_claude_code_interactive(self, story: dict, prd: dict, iteration: int) -> bool:
    """Execute story by spawning Claude Code and piping prompt to stdin."""
    context = self._build_context(story, prd)
    prompt = self._build_agent_prompt(story, context)

    print(f"🤖 Spawning Claude Code agent for story {story['id']}...")

    try:
        # Spawn Claude Code with prompt piped to stdin
        process = subprocess.Popen(
            [
                "claude",
                "code",
                "--dangerously-skip-permissions",
                "--model", self.config.get("claude.model", "claude-sonnet-4-5-20250929")
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=Path.cwd()
        )

        # Send prompt and close stdin
        stdout, stderr = process.communicate(input=prompt, timeout=self.config.get("ralph.iterationTimeout", 3600))

        if process.returncode != 0:
            print(f"❌ Claude Code exited with error: {stderr}")
            self._log_failure(story, stdout, None, iteration)
            return False

        # Run quality gates
        print("🔍 Running quality gates...")
        quality_result = self.quality_gates.run()

        if quality_result["status"] == "PASS":
            self._commit_changes(story)
            self._update_progress_log(story, stdout, quality_result, iteration)
            if self.config.get("ralph.updateAgentsMd", True):
                self._update_agents_md(story, stdout)
            return True
        else:
            self._log_failure(story, stdout, quality_result, iteration)
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        self._log_failure(story, str(e), None, iteration)
        return False


print("""
This file shows how to modify Ralph to use Claude Code instead of Claude API.

To integrate this into ralph.py:

1. Replace the _execute_story() method in RalphLoop class with _execute_story_with_claude_code()
2. This will make Ralph spawn Claude Code CLI with --dangerously-skip-permissions flag
3. Claude Code will have full access to read/write files, run commands, etc.

Key changes:
- Uses subprocess to call 'claude code' CLI
- Passes --dangerously-skip-permissions to auto-approve all actions
- Prompt is passed via temp file or stdin
- Agent output captured from stdout
- Quality gates still run after Claude Code finishes

Commands Claude Code will have access to:
- Read/Write/Edit files
- Bash commands
- Git operations
- Everything in Claude Code's tool suite
""")
