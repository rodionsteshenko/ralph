# AGENTS.md - Ralph Python Codebase Guide

This document provides patterns, conventions, and guidance for AI agents working on the Ralph Python codebase.

## Project Overview

Ralph is an autonomous AI agent loop that executes user stories from a PRD (Product Requirement Document). It uses Claude API to implement features iteratively, running quality gates after each iteration to ensure code quality.

### Core Concept

1. **PRD Processing**: Convert PRD documents to structured JSON (`prd.json`)
2. **Autonomous Loop**: Execute stories one by one using Claude API
3. **Quality Gates**: Run typecheck, lint, and tests statically (outside agent control)
4. **Git Integration**: Auto-commit when quality gates pass
5. **Progress Tracking**: Log all iterations to `progress.txt`

## Architecture

### Key Components

#### `RalphConfig`
- **Location**: `ralph.py` lines 31-125
- **Purpose**: Manages configuration from `.ralph/config.json`
- **Pattern**: Uses dot notation for nested config access (`config.get("ralph.maxIterations")`)
- **Default Path**: `.ralph/config.json`
- **Key Methods**:
  - `get(key, default)` - Get config value with dot notation
  - `save()` - Persist config to file
  - `_ensure_directories()` - Create required directories

#### `PRDParser`
- **Location**: `ralph.py` lines 127-284
- **Purpose**: Converts PRD documents to structured JSON
- **Pattern**: Uses Claude API to parse and structure PRD content
- **Key Methods**:
  - `parse_prd(prd_path, output_path)` - Main parsing method
  - `_build_parser_prompt()` - Creates prompt for Claude
  - `_validate_prd_json()` - Ensures proper structure

#### `QualityGates`
- **Location**: `ralph.py` lines 286-361
- **Purpose**: Runs quality checks statically (outside agent control)
- **Pattern**: Executes shell commands via `subprocess.run()`
- **Key Methods**:
  - `run()` - Runs all configured quality gates
  - `_run_gate()` - Executes a single gate with timeout

#### `RalphLoop`
- **Location**: `ralph.py` lines 363-717
- **Purpose**: Main execution loop orchestrating story execution
- **Pattern**: Iterative loop with stop conditions
- **Key Methods**:
  - `execute()` - Main loop entry point
  - `_execute_story()` - Executes single story
  - `_select_next_story()` - Chooses next story by priority/dependencies
  - `_build_context()` - Builds agent context
  - `_build_agent_prompt()` - Creates prompt for Claude agent

## Code Patterns

### Configuration Access

Always use `RalphConfig.get()` with dot notation:

```python
max_iterations = config.get("ralph.maxIterations", 20)
model = config.get("claude.model", "claude-3-5-sonnet-20241022")
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

- Use try/except for external operations (API calls, subprocess, file I/O)
- Log failures to `progress.txt` via `_log_failure()`
- Don't crash the loop on individual story failures

### Quality Gate Execution

Quality gates run **statically** (outside agent control):

```python
quality_result = self.quality_gates.run()
if quality_result["status"] == "PASS":
    # Commit and mark story complete
else:
    # Log failure, agent can retry next iteration
```

### Git Operations

Always check for changes before committing:

```python
result = subprocess.run(["git", "status", "--porcelain"], ...)
if not result.stdout.strip():
    return  # No changes
```

### Context Building

Each iteration builds fresh context:

```python
context = {
    "story": story,
    "prd": {...},
    "progress": recent_progress,  # Last 50 lines
    "agentsMd": agents_md_content,
    "projectConfig": {...}
}
```

## File Structure

```
ralph/
├── ralph.py              # Main script (all classes)
├── pyproject.toml        # Python project metadata (UV)
├── requirements.txt      # Dependencies
├── prd.json              # Generated PRD (gitignored)
├── progress.txt          # Progress log (gitignored)
├── .ralph/
│   ├── config.json       # Configuration
│   └── skills/          # Project-specific skills
├── AGENTS.md            # This file
└── archive/             # Archived runs
```

## Configuration Patterns

### Default Configuration Structure

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
    }
  },
  "ralph": {
    "maxIterations": 20,
    "maxFailures": 3
  },
  "claude": {
    "model": "claude-3-5-sonnet-20241022",
    "maxTokens": 8192,
    "temperature": 0.7
  }
}
```

### Adding New Configuration

1. Add to default config in `RalphConfig._load_config()`
2. Access via `config.get("section.key", default)`
3. Document in this file

## Quality Gates

### How They Work

1. Agent completes implementation
2. Quality gates run **statically** (Python subprocess)
3. All gates must pass for commit
4. If any fail, story marked failed, agent can retry

### Adding a New Quality Gate

1. Add to `config.json`:
```json
"qualityGates": {
  "mygate": {
    "command": "my-command",
    "required": true,
    "timeout": 120
  }
}
```

2. Gate will automatically run if `required: true`

### Quality Gate Results

```python
{
  "status": "PASS" | "FAIL",
  "gates": {
    "typecheck": {
      "status": "PASS",
      "duration": 12.3,
      "output": "...",
      "returnCode": 0
    }
  },
  "totalDuration": 45.6,
  "timestamp": "2024-01-01T12:00:00"
}
```

## Git Workflow

### Commit Pattern

- Commits only happen when quality gates pass
- Commit message format: `feat: {story_id} - {story_title}`
- Configurable via `git.commitMessageFormat`
- Uses `git add .` then `git commit -m "..."`

### Branch Management

- PRD includes `branchName` field
- Ralph doesn't create branches automatically (future feature)
- Work happens on current branch

## Story Execution Flow

```
1. Load PRD → Find remaining stories (passes: false)
2. Select next story (priority + dependencies)
3. Build context:
   - Story details
   - Recent progress (last 50 lines)
   - AGENTS.md content
   - Project config
4. Call Claude API with prompt
5. Run quality gates (static)
6. If passing:
   - Commit changes
   - Update prd.json (passes: true)
   - Log to progress.txt
7. Check stop conditions
8. Repeat or exit
```

## Stop Conditions

Ralph stops when:

1. ✅ **All stories complete** (`passes: true` for all)
2. ⏱️ **Max iterations reached** (if `maxIterations > 0`)
3. ❌ **Consecutive failures** (default: 3)
4. 🛑 **Manual interrupt** (Ctrl+C)

## PRD Structure

### Expected JSON Format

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
        "Criterion 2",
        "Typecheck passes"
      ],
      "priority": 1,
      "passes": false,
      "notes": ""
    }
  ],
  "metadata": {
    "createdAt": "2024-01-01T12:00:00",
    "lastUpdatedAt": "2024-01-01T12:00:00",
    "totalStories": 1,
    "completedStories": 0,
    "currentIteration": 0
  }
}
```

### Story Validation Rules

- Each story must be completable in ONE iteration (~150k tokens)
- Stories ordered by dependency (schema → backend → UI)
- Acceptance criteria must be verifiable
- Every story must include "Typecheck passes"
- UI stories must include "Verify in browser"

## Claude API Usage

### Model Configuration

- Default: `claude-3-5-sonnet-20241022`
- Configurable via `claude.model`
- Temperature: 0.7 (default), 0.3 for PRD parsing

### Prompt Building

Prompts include:
- Story details (ID, title, description, acceptance criteria)
- Project context
- Recent progress
- AGENTS.md content
- Project configuration

### API Call Pattern

```python
response = self.claude.messages.create(
    model=self.config.get("claude.model"),
    max_tokens=self.config.get("claude.maxTokens", 8192),
    temperature=self.config.get("claude.temperature", 0.7),
    messages=[{
        "role": "user",
        "content": prompt
    }]
)
```

## Progress Logging

### Format

```text
## Iteration 1 - US-001 - 2024-01-01T12:00:00
**Story**: Story title
**Status**: ✅ PASSED
**Duration**: 45.6s

**Quality Gates**:
- ✅ typecheck: PASS (12.3s)
- ✅ lint: PASS (8.1s)
- ✅ test: PASS (25.2s)

**Agent Output**:
```
[First 500 chars of agent output]
```

---
```

### Log Location

- File: `progress.txt` (configurable via `paths.progressFile`)
- Append-only
- Includes last 50 lines in context for next iteration

## Dependency Management

### UV Package Manager

This project uses **UV** for fast Python package installation:

- `make install` - Installs dependencies with UV
- `make install-dev` - Installs dev dependencies
- `make venv` - Creates virtual environment with UV

### Dependencies

- **Runtime**: `anthropic>=0.34.0`
- **Dev**: `ruff`, `mypy`, `black`, `pytest` (optional)

### Adding Dependencies

1. Add to `requirements.txt`:
```
new-package>=1.0.0
```

2. Or add to `pyproject.toml`:
```toml
dependencies = [
    "new-package>=1.0.0",
]
```

3. Run `make install`

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
story["iterationNumber"] = iteration

prd["metadata"]["completedStories"] = sum(
    1 for s in prd["userStories"] if s.get("passes", False)
)
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

## Best Practices

### For AI Agents

1. **Read the codebase first** - Understand existing patterns
2. **Follow existing conventions** - Match code style
3. **Keep stories small** - One iteration per story
4. **Write verifiable acceptance criteria** - Objective tests
5. **Run quality gates** - Don't skip typecheck/lint/tests
6. **Commit atomic changes** - One story per commit
7. **Update progress logs** - Document what was done

### Code Quality

- ✅ All code must pass typecheck
- ✅ All code must pass linting
- ✅ All tests must pass
- ✅ Follow existing code patterns
- ✅ Use type hints where possible
- ✅ Handle errors gracefully

### Story Implementation

1. Read acceptance criteria carefully
2. Understand dependencies (check completed stories)
3. Follow existing code patterns
4. Implement incrementally
5. Test as you go
6. Ensure all acceptance criteria met
7. Verify quality gates pass

## Extending Ralph

### Adding New Commands

1. Add subparser in `main()`:
```python
new_parser = subparsers.add_parser("new-command", help="...")
new_parser.add_argument("arg", ...)
```

2. Handle in `main()`:
```python
elif args.command == "new-command":
    # Implementation
```

### Adding New Quality Gates

1. Add to config (see Quality Gates section)
2. Gate runs automatically if `required: true`

### Customizing Agent Prompts

Modify `_build_agent_prompt()` in `RalphLoop` class to change how prompts are constructed.

### Adding New Context Sources

Modify `_build_context()` to include additional context sources.

## Troubleshooting

### Common Issues

**Quality gates failing**
- Check commands in `config.json` match your project
- Verify commands work when run manually
- Check timeout values are sufficient

**Stories too large**
- Split stories in PRD
- Each story should be completable in one iteration

**Git errors**
- Ensure git is initialized: `git init`
- Set git config: `git config user.name "Ralph"`

**API errors**
- Verify Claude Code CLI is installed and authenticated
- Verify model name is correct

## Testing

### Manual Testing

```bash
# Test PRD parsing
python ralph.py process-prd test-prd.txt

# Test configuration
python ralph.py init

# Test status
python ralph.py status

# Test execution (with limit)
python ralph.py execute-plan --max-iterations 1
```

### Quality Checks

```bash
make lint      # Run linters
make format    # Format code
make check     # Run all checks
make verify    # Verify installation
```

## Resources

- **Main Script**: `ralph.py`
- **Configuration**: `.ralph/config.json`
- **Documentation**: `README.md`, `QUICKSTART.md`, `ralph_python_README.md`
- **Implementation Details**: `IMPLEMENTATION_SUMMARY.md`
- **Prompt Template**: `agent_prompt_template.md`

## Notes for Future Agents

- This codebase is designed to be extended
- Quality gates are intentionally static (outside agent control)
- Context is rebuilt each iteration for freshness
- Progress logging helps track what's been done
- AGENTS.md is included in agent context automatically

---

**Last Updated**: 2024-01-01  
**Version**: 0.1.0
