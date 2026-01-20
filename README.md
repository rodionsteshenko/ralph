# Ralph

Autonomous AI agent loop for executing PRDs (Product Requirement Documents). Ralph uses Claude AI to implement user stories iteratively, auto-committing on completion.

## Installation

### From PyPI (Coming Soon)

Once published to PyPI, you'll be able to install Ralph with:

```bash
pip install ralph
```

### From Git Repository

Install directly from GitHub:

```bash
# Install latest from main branch
pip install git+https://github.com/rodionsteshenko/ralph.git

# Install from specific branch
pip install git+https://github.com/rodionsteshenko/ralph.git@branch-name

# Install from specific commit
pip install git+https://github.com/rodionsteshenko/ralph.git@commit-hash
```

After installation, verify with:

```bash
ralph --version
ralph --help
```

### From Local Source (Development)

For local development with editable install:

```bash
# Clone the repository
git clone https://github.com/rodionsteshenko/ralph.git
cd ralph

# Install in editable mode
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

## Quick Start

Ralph operates on the **current directory**, using a `.ralph/` folder to store all configuration and state.

### 1. Initialize Ralph

Navigate to your project directory and initialize Ralph:

```bash
cd /path/to/your/project
ralph init
```

This creates a `.ralph/` directory with the necessary structure.

### 2. Process Your PRD

Convert your PRD document into a structured JSON file:

```bash
# For small to medium PRDs (< 10 stories)
ralph process-prd tasks/my-feature.txt

# For large PRDs (10+ stories) - uses incremental processing
ralph build-prd tasks/large-feature.txt
```

The PRD will be saved to `.ralph/prd.json` in your current directory.

### 3. Execute the PRD

Run the autonomous loop to implement your user stories:

```bash
# Execute all stories
ralph execute

# Execute a specific phase only
ralph execute --phase 1

# Limit iterations for testing
ralph execute --max-iterations 3
```

### 4. Monitor Progress

Check status and view progress:

```bash
# Show execution status
ralph status

# View detailed PRD progress (with auto-refresh)
ralph view

# Show summary statistics
ralph summary
```

### Workflow Example

```bash
# Start in your project directory
cd ~/projects/my-app

# Initialize Ralph
ralph init

# Process your PRD
ralph process-prd feature-spec.txt

# Execute stories iteratively
ralph execute

# Check progress
ralph status

# View detailed progress (watch mode)
ralph view
```

## Command Reference

### Core Commands

#### `ralph init`
Initialize Ralph in the current directory. Creates `.ralph/` folder structure.

```bash
ralph init
```

#### `ralph process-prd <file>`
Parse a PRD text file and convert it to `.ralph/prd.json`.

```bash
ralph process-prd tasks/feature.txt

# Use a different Claude model
ralph process-prd tasks/feature.txt --model claude-opus-4-5-20251101
```

#### `ralph build-prd <file>`
Incrementally build a large PRD (10+ stories) using tool-based batching.

```bash
ralph build-prd tasks/large-project.txt

# Specify output path (default: .ralph/prd.json)
ralph build-prd tasks/large-project.txt --output custom-prd.json
```

#### `ralph execute`
Execute the PRD stories using the autonomous agent loop.

```bash
# Execute all remaining stories
ralph execute

# Execute specific phase only
ralph execute --phase 2

# Limit iterations (0 = unlimited)
ralph execute --max-iterations 10

# Use custom model
ralph execute --model claude-opus-4-5-20251101

# Show verbose output
ralph execute --verbose
```

**Aliases:** `execute-plan`, `run`

### Status & Monitoring

#### `ralph status`
Show current Ralph status and story completion.

```bash
# Show overall status
ralph status

# Show status for specific phase
ralph status --phase 1
```

#### `ralph view`
View PRD progress with rich terminal UI (watch mode by default).

```bash
# Watch mode (auto-refresh)
ralph view

# Display once and exit
ralph view --once

# Show closed phases expanded
ralph view --expand

# Custom refresh interval (seconds)
ralph view --interval 2.0
```

#### `ralph summary`
Show PRD completion statistics and metrics.

```bash
ralph summary
```

### Story Management

#### `ralph list-stories`
List stories with optional filters.

```bash
# List all stories
ralph list-stories

# Filter by phase
ralph list-stories --phase 2

# Filter by status
ralph list-stories --status incomplete
ralph list-stories --status complete
```

#### `ralph skip-story <story_id>`
Mark a story as skipped (won't be executed).

```bash
ralph skip-story US-023
```

#### `ralph start-story <story_id>`
Mark a story as in_progress.

```bash
ralph start-story US-024
```

#### `ralph in-progress`
Show all stories currently marked as in_progress.

```bash
ralph in-progress
```

#### `ralph clear-stale`
Clear stale in_progress status from stories (default: 24 hours).

```bash
# Clear stories in_progress for more than 24 hours
ralph clear-stale

# Custom age threshold
ralph clear-stale --max-age-hours 48
```

### Phase Management

#### `ralph close-phase <phase_number>`
Mark all incomplete stories in a phase as skipped.

```bash
ralph close-phase 2
```

### Validation

#### `ralph validate`
Validate PRD structure and story definitions.

```bash
# Basic validation
ralph validate

# Strict mode (treat warnings as errors)
ralph validate --strict
```

#### `ralph select`
Interactive story selection menu.

```bash
ralph select
```

## Configuration & Auto-Detection

Ralph **auto-detects** your project type and configures appropriate commands automatically. No `config.json` needed!

### Auto-Detected Project Types

Ralph detects project type based on files in your directory:

| File | Detected Type | Default Commands |
|------|---------------|------------------|
| `package.json` | Node | `npm run typecheck`, `npm run lint`, `npm run test` |
| `pyproject.toml` | Python | `mypy .`, `ruff check .`, `pytest` |
| `setup.py` | Python | `mypy .`, `ruff check .`, `pytest` |
| `Cargo.toml` | Rust | `cargo check`, `cargo clippy`, `cargo test` |
| `go.mod` | Go | `go build`, `go vet`, `go test ./...` |

### CLI Override Flags

Override auto-detected values with CLI flags:

```bash
# Override Claude model
ralph execute --model claude-opus-4-5-20251101

# Combine multiple overrides
ralph execute \
  --model claude-opus-4-5-20251101 \
  --max-iterations 5
```

## PRD Structure

Ralph expects PRDs in a specific JSON format. Use `ralph process-prd` to convert text PRDs automatically.

Example PRD structure (`.ralph/prd.json`):

```json
{
  "project": "My Project",
  "branchName": "ralph/feature-name",
  "description": "Feature description",
  "phases": {
    "1": { "name": "Foundation", "description": "Core setup" }
  },
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
      "phase": 1,
      "status": "incomplete",
      "notes": ""
    }
  ],
  "metadata": {
    "createdAt": "2026-01-19T12:00:00",
    "totalStories": 1,
    "completedStories": 0,
    "currentIteration": 0
  }
}
```

## Project Structure

When Ralph runs on your project, it creates this structure:

```
your-project/
├── .ralph/                   # Ralph state (auto-created)
│   ├── prd.json              # Structured PRD
│   ├── progress.md           # Execution log
│   ├── guardrails.md         # Learned failures
│   └── logs/                 # Detailed iteration logs
├── src/                      # Your project code
└── tests/                    # Your tests
```

## Package Structure

Ralph's internal package structure:

```
src/ralph/
├── __init__.py      # Package initialization, version
├── cli.py           # Command-line interface
├── commands.py      # Command implementations
├── detect.py        # Project type detection
├── prd.py           # PRD parsing and management
├── loop.py          # Main execution loop
├── builder.py       # Incremental PRD builder
├── tools.py         # PRD manipulation tools
├── viewer.py        # Terminal PRD viewer
└── utils.py         # Utility functions
```

## Development

### Install Development Dependencies

```bash
pip install -e ".[dev]"
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/ralph

# Run only unit tests (exclude E2E)
pytest -m "not e2e"

# Run only E2E tests
pytest -m e2e
```

### Code Quality

```bash
# Type checking
mypy src/ralph/

# Linting
ruff check src/ tests/

# Auto-fix linting issues
ruff check --fix src/ tests/

# Format code
ruff format src/ tests/
```

## Requirements

- Python 3.9+
- Anthropic Claude API access (for agent execution)
- Git (for auto-commit functionality)

## Version

Current version: 0.1.0

## License

MIT

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

## Support

- GitHub Issues: https://github.com/rsteshenko/ralph/issues
- Documentation: See `CLAUDE.md` for detailed architecture and patterns
