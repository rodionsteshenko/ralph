# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ralph is an autonomous AI agent loop that executes user stories from PRDs (Product Requirement Documents). It uses Claude API to implement features iteratively, running quality gates after each iteration to ensure code quality before committing.

**Core workflow**: PRD → Parse to JSON → Execute stories one-by-one → Run quality gates → Auto-commit on pass

## Essential Commands

### Installation & Setup
```bash
uv pip install -r requirements.txt  # Install dependencies using UV
python ralph.py init      # Initialize .ralph/config.json
```

### Primary Workflow
```bash
# 1. Process PRD document to structured JSON
# For small PRDs (<10 stories):
python ralph.py process-prd tasks/prd-feature.txt [--output prd.json]

# For large PRDs (10+ stories) - uses tool-based batching:
python prd_builder.py tasks/prd-feature.txt [--output prd.json]

# 2. Execute the plan
python ralph.py execute-plan [--max-iterations N] [--prd prd.json]

# 3. Check status
python ralph.py status [--prd prd.json]
```

### Development
```bash
ruff format             # Format code
ruff check              # Run lint checks
mypy .                  # Run type checks
pytest                  # Run tests
```

## Architecture

### Single-File Implementation
The entire implementation lives in `ralph.py` (~900 lines). Key classes:

1. **RalphConfig** (lines 31-125)
   - Manages `.ralph/config.json` with dot notation access
   - Example: `config.get("ralph.maxIterations", 20)`
   - Creates required directories automatically

2. **PRDParser** (lines 127-284)
   - Converts PRD documents to structured `prd.json`
   - Uses Claude API for parsing
   - Validates story sizing and dependencies

3. **QualityGates** (lines 286-361)
   - Runs typecheck/lint/test **statically** (outside agent control)
   - Executes via subprocess with timeouts
   - All gates must pass before commit

4. **RalphLoop** (lines 363-717)
   - Main execution loop orchestrating story execution
   - Selects next story by priority/dependencies
   - Builds fresh context each iteration
   - Handles stop conditions (completion/failures/iterations)

### Execution Flow
```
1. Load prd.json → Find remaining stories (passes: false)
2. Select next story by priority + dependencies
3. Build context:
   - Story details (id, title, description, acceptance criteria)
   - Recent progress (last 50 lines from progress.txt)
   - AGENTS.md content (codebase patterns)
   - Project config
4. Call Claude API with constructed prompt
5. Run quality gates statically (Python subprocess)
6. If all pass:
   - git add . && git commit -m "feat: {story_id} - {title}"
   - Update prd.json (passes: true)
   - Append to progress.txt
7. Check stop conditions
8. Repeat or exit
9. On completion: Generate AI-powered feature summary
   - What features were added (user-facing)
   - How to test/verify them (specific commands)
   - What's the practical impact
   - What's still pending
```

### Stop Conditions
Ralph stops when:
- All stories complete (`passes: true` for all)
- Max iterations reached (if set, 0 = unlimited)
- 3 consecutive failures (configurable)
- Manual interrupt (Ctrl+C)

### Session Summary
After execution completes, Ralph prints a comprehensive summary:
- **AI-Generated Feature Summary**: User-facing explanation of what was built and how to test it
- **Technical Details**: Story IDs, durations, file changes
- **Overall Progress**: Completion percentage, remaining stories
- **Next Steps**: Commands to continue execution

The AI feature summary translates technical story completions into practical, testable capabilities for the project owner.

## Key Design Patterns

### Configuration Access
Always use dot notation with `RalphConfig.get()`:
```python
max_iterations = config.get("ralph.maxIterations", 20)
model = config.get("claude.model", "claude-3-5-sonnet-20241022")
typecheck_cmd = config.get("commands.typecheck", "npm run typecheck")
```

### Path Handling
Use `pathlib.Path` for all file operations:
```python
from pathlib import Path
prd_path = Path(self.config.get("paths.prdFile", "prd.json"))
if prd_path.exists():
    # ...
```

### Error Handling
- Try/except for external operations (API, subprocess, file I/O)
- Log failures to `progress.txt` via `_log_failure()`
- Don't crash loop on individual story failures
- Agent can retry next iteration

### Quality Gates
Gates run **statically** outside agent control:
```python
quality_result = self.quality_gates.run()
if quality_result["status"] == "PASS":
    # Commit and mark story complete
else:
    # Log failure, agent retries next iteration
```

This ensures gates can't be bypassed by the agent.

### Git Operations
Always check for changes before committing:
```python
result = subprocess.run(["git", "status", "--porcelain"], ...)
if not result.stdout.strip():
    return  # No changes to commit
```

## PRD Structure

Expected JSON format in `prd.json`:
```json
{
  "project": "ProjectName",
  "branchName": "ralph/feature-name",
  "description": "Feature description",
  "userStories": [
    {
      "id": "US-001",
      "title": "Story title",
      "description": "As a user, I want...",
      "acceptanceCriteria": [
        "Criterion 1",
        "Typecheck passes"
      ],
      "priority": 1,
      "passes": false,
      "notes": ""
    }
  ],
  "metadata": {
    "createdAt": "2024-01-01T12:00:00",
    "totalStories": 1,
    "completedStories": 0,
    "currentIteration": 0
  }
}
```

**Story validation rules:**
- Each story completable in ONE iteration (~150k tokens)
- Stories ordered by dependency (schema → backend → UI)
- Acceptance criteria must be verifiable
- Every story should include "Typecheck passes"
- UI stories should include "Verify in browser"
- **CRITICAL: Stories with external integrations (APIs, databases) MUST include "End-to-end test with real [integration] passes"**

**Why E2E testing is critical:**
- Unit tests with mocks can pass while real integration fails
- E2E tests catch real-world issues: wrong model names, auth failures, API changes
- Ralph will now enforce E2E tests for any feature that uses external services

**Story status values:**
- `undefined/null` - Not started
- `"in_progress"` - Currently being worked on (has `startedAt` timestamp)
- `"completed"` - Finished successfully (`passes=true`)
- `"skipped"` - Intentionally closed without completing (`passes=false`, has `skippedAt` timestamp)

**Phase closure logic:**
- A phase is "closed" when all stories have either `passes=true` OR `status="skipped"`
- Closed phases show `[CLOSED]` badge in prd_viewer.py

**PRD Management Tools:**
```bash
python prd_tools.py close-phase <prd_file> <phase_number>  # Mark all incomplete stories in phase as skipped
python prd_tools.py skip-story <prd_file> <story_id>       # Mark a single story as skipped
python prd_tools.py start-story <prd_file> <story_id>      # Mark story as in_progress
python prd_tools.py in-progress <prd_file>                 # Show all in-progress stories
python prd_tools.py clear-stale <prd_file> [--max-age-hours N]  # Clear stale in_progress status
```

**PRD Viewer:**
```bash
python prd_viewer.py prd.json           # Watch mode (auto-refresh)
python prd_viewer.py prd.json --once    # Display once and exit
```

## Configuration Structure

Default `.ralph/config.json`:
```json
{
  "project": {
    "name": "ProjectName",
    "type": "node",
    "packageManager": "npm"
  },
  "commands": {
    "typecheck": "npm run typecheck",
    "lint": "npm run lint",
    "test": "npm run test"
  },
  "qualityGates": {
    "typecheck": {
      "command": "npm run typecheck",
      "required": true,
      "timeout": 300
    },
    "lint": {
      "command": "npm run lint",
      "required": true,
      "timeout": 120
    },
    "test": {
      "command": "npm run test",
      "required": true,
      "timeout": 600
    }
  },
  "git": {
    "baseBranch": "main",
    "commitMessageFormat": "feat: {story_id} - {story_title}",
    "autoPush": false
  },
  "ralph": {
    "maxIterations": 20,
    "maxFailures": 3,
    "iterationTimeout": 600,
    "updateAgentsMd": false
  },
  "claude": {
    "model": "claude-3-5-sonnet-20241022",
    "maxTokens": 8192,
    "temperature": 0.7
  },
  "paths": {
    "prdFile": "prd.json",
    "progressFile": "progress.txt",
    "agentsMdFile": "AGENTS.md"
  }
}
```

## File Organization

```
ralph/
├── ralph.py              # Single-file implementation (~900 lines)
├── pyproject.toml        # Python project metadata (uses UV)
├── requirements.txt      # anthropic>=0.34.0
├── prd.json              # Generated PRD (gitignored)
├── progress.txt          # Append-only progress log (gitignored)
├── .ralph/
│   ├── config.json       # Configuration (customize per project)
│   └── skills/          # Project-specific skills (future)
└── archive/             # Archived runs
```

## Dependencies

Uses **UV** package manager for fast Python installations:
- Runtime: `anthropic>=0.34.0`
- Dev: `ruff`, `mypy`, `black`, `pytest`

Add dependencies to `requirements.txt` or `pyproject.toml` then run `uv pip install -r requirements.txt`.

## Adding Quality Gates

1. Add to `.ralph/config.json`:
```json
"qualityGates": {
  "mygate": {
    "command": "my-command",
    "required": true,
    "timeout": 120
  }
}
```

2. Gate automatically runs if `required: true`

## Progress Logging

Format in `progress.txt`:
```text
## Iteration 1 - US-001 - 2024-01-01T12:00:00
**Story**: Story title
**Status**: ✅ PASSED
**Duration**: 45.6s

**Quality Gates**:
- ✅ typecheck: PASS (12.3s)
- ✅ lint: PASS (8.1s)

**Agent Output**:
[First 500 chars of agent output]

---
```

Last 50 lines included in context for next iteration.

## Common Patterns

### Reading PRD
```python
with open(prd_path, 'r') as f:
    prd = json.load(f)
remaining_stories = [s for s in prd["userStories"] if not s.get("passes", False)]
```

### Updating PRD
```python
story["passes"] = True
story["actualDuration"] = duration
prd["metadata"]["completedStories"] = sum(1 for s in prd["userStories"] if s.get("passes", False))
prd["metadata"]["lastUpdatedAt"] = datetime.now().isoformat()
with open(prd_path, 'w') as f:
    json.dump(prd, f, indent=2)
```

### Running Shell Commands
```python
result = subprocess.run(
    command,
    shell=True,
    capture_output=True,
    text=True,
    timeout=timeout,
    cwd=Path.cwd()
)
```

## Claude API Usage

Default configuration:
- Model: `claude-3-5-sonnet-20241022`
- Temperature: 0.7 (execution), 0.3 (PRD parsing)
- Max tokens: 8192

Prompts include:
- Story details (ID, title, description, acceptance criteria)
- Recent progress (last 50 lines)
- AGENTS.md content (codebase patterns)
- Project configuration

## PRD Builder Tool (prd_builder.py)

For large PRDs (10+ user stories), use `prd_builder.py` instead of the built-in `ralph.py process-prd`.

**Why it's needed:** Large PRDs can hit token limits when trying to generate JSON all at once. The PRD builder solves this by:

1. Using Claude's tool calling capability
2. Processing stories in batches of 5
3. Incrementally building the PRD JSON with tools:
   - `initialize_prd()` - Sets up project metadata
   - `add_user_story()` - Adds each story (called multiple times)
   - `finalize_prd()` - Completes the PRD

**Usage:**
```bash
python prd_builder.py prd-large-project.md --output prd.json
```

**How it works:**
- Splits PRD content by user story headers (###  US-XXX)
- Processes header first to extract project metadata
- Processes stories in batches (5 per batch)
- Each batch is a separate Claude API call with tools
- Aggregates all stories into final JSON

**Benefits:**
- Handles PRDs with 50+ stories without token limits
- More reliable than single-shot JSON generation
- Uses Sonnet 4.5 (cheaper than Opus)
- Progress visibility (shows batch processing)

## Agent Design Documents

The `agent/` directory contains design documents for Ralph's architecture:
- `DESIGN.md` - Full architecture and design decisions
- `PRD.md` - Original product requirements
- Various iteration documents tracking design evolution

These are reference materials, not executed code.
