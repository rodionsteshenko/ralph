# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ralph is an autonomous AI agent loop that executes user stories from PRDs (Product Requirement Documents). It uses Claude AI to implement features iteratively, running quality gates after each iteration to ensure code quality before committing.

**Core workflow**: PRD → Parse to JSON → Execute stories one-by-one → Run quality gates → Auto-commit on pass

## Repository Structure

This repo contains Ralph as a pip-installable Python package:

```
ralph/
├── ralph-package-distribution/   # The actual package (src layout)
│   ├── src/ralph/               # Package source code
│   │   ├── cli.py              # CLI entry point
│   │   ├── commands.py         # Command implementations
│   │   ├── loop.py             # Main execution loop (~1550 lines)
│   │   ├── prd.py              # PRD parsing and validation
│   │   ├── gates.py            # Quality gates
│   │   ├── detect.py           # Project type auto-detection
│   │   ├── builder.py          # Incremental PRD builder
│   │   ├── tools.py            # PRD manipulation tools
│   │   ├── viewer.py           # Terminal PRD viewer
│   │   └── config.py           # Configuration management
│   ├── tests/                   # Test suite
│   └── pyproject.toml          # Package metadata
├── *.py (root level)            # DEPRECATED stubs that show deprecation notice
└── agent/                       # Design documents (reference only)
```

## Installation & Development

```bash
cd ralph-package-distribution/

# Install in editable mode for development
pip install -e ".[dev]"

# Verify installation
ralph --version
ralph --help
```

## Development Commands

Run these from `ralph-package-distribution/`:

```bash
# Type checking
mypy src/ralph/

# Linting
ruff check src/ tests/
ruff check --fix src/ tests/   # Auto-fix issues

# Format code
ruff format src/ tests/

# Run all tests
pytest

# Run with coverage
pytest --cov=src/ralph

# Run only unit tests (exclude E2E)
pytest -m "not e2e"

# Run specific test file
pytest tests/test_cli.py

# Run specific test
pytest tests/test_cli.py::test_init_creates_ralph_dir
```

## Ralph CLI Usage

After installing, use `ralph` from your project directory:

```bash
cd your-project/
ralph init                    # Initialize .ralph/ directory
ralph process-prd prd.txt     # Parse PRD to .ralph/prd.json
ralph build-prd large-prd.txt # For PRDs with 10+ stories (batched)
ralph execute                 # Run the agent loop
ralph execute --phase 1       # Execute specific phase
ralph status                  # Show completion status
ralph view                    # Watch mode with rich terminal UI
ralph validate --strict       # Validate PRD structure
```

## Architecture

### Module Responsibilities

- **cli.py** - Argument parsing, routes to command handlers
- **commands.py** - Command implementations (init, execute, status, etc.)
- **loop.py** - Main `RalphLoop` class: story selection, context building, execution, quality gates
- **prd.py** - `PRDParser` class, `validate_prd()`, `call_claude_code()` helper
- **gates.py** - `QualityGates` class, runs typecheck/lint/test statically
- **detect.py** - Auto-detects project type (Node, Python, Rust, Go) from files
- **builder.py** - Incremental PRD builder using Claude tool calling
- **config.py** - `RalphConfig` class for dot-notation config access

### Execution Flow

```
1. RalphLoop.execute() called with phase/iterations
2. Load prd.json → Select next story by priority + dependencies
3. Build context: story details, recent progress, AGENTS.md, guardrails
4. Call Claude Code CLI to implement the story
5. Run quality gates (subprocess, outside agent control)
6. If all pass: git commit, update prd.json status
7. Check stop conditions, repeat or print session summary
```

### Quality Gates

Gates run **statically** outside agent control in `gates.py`:
- Commands auto-detected from project type
- Can be overridden via CLI flags (--typecheck-cmd, --lint-cmd, --test-cmd)
- All gates must pass before commit

### Project Auto-Detection

In `detect.py`, Ralph detects project type from files:
- `package.json` → Node (npm run typecheck/lint/test)
- `pyproject.toml` → Python (mypy, ruff, pytest)
- `Cargo.toml` → Rust (cargo check/clippy/test)
- `go.mod` → Go (go build/vet/test)

## PRD JSON Structure

```json
{
  "project": "ProjectName",
  "branchName": "ralph/feature-name",
  "phases": { "1": { "name": "Phase Name" } },
  "userStories": [
    {
      "id": "US-001",
      "title": "Story title",
      "description": "As a user, I want...",
      "acceptanceCriteria": ["Criterion 1", "Typecheck passes"],
      "priority": 1,
      "phase": 1,
      "status": "incomplete"
    }
  ],
  "metadata": { "totalStories": 1, "completedStories": 0 }
}
```

**Status values**: `incomplete`, `in_progress`, `complete`, `skipped`

## Testing Patterns

Test files follow the pattern:
- `test_<module>.py` - Unit tests
- `test_<module>_e2e.py` - End-to-end tests (marked with `@pytest.mark.e2e`)

E2E tests require real Claude API access and are skipped by default. Run with:
```bash
pytest -m e2e
```

## Key Design Patterns

### Configuration with Dot Notation
```python
from ralph.config import RalphConfig
config = RalphConfig(project_dir)
max_iter = config.get("ralph.maxIterations", 20)
```

### Path Handling
All paths use `pathlib.Path`. Config provides path properties:
```python
config.prd_path       # .ralph/prd.json
config.progress_path  # .ralph/progress.md
config.guardrails_path # .ralph/guardrails.md
```

### Guardrails (Learning from Failures)
After 2+ consecutive failures, Ralph writes to `.ralph/guardrails.md` and includes it in future prompts to prevent repeating mistakes.
