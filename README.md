# Ralph Python Implementation

A Python-based implementation of the Ralph autonomous AI agent loop using Claude API.

## Quick Start

```bash
# Install dependencies (uses UV for fast installation)
uv pip install -r requirements.txt

# Initialize configuration
python ralph.py init

# Run Ralph (provide a prd.json file first)
python ralph.py execute-plan --prd prd.json --max-iterations 1
```

## Usage

Use `python ralph.py --help` to see all available commands.

## Requirements

- Python 3.8+
- UV (Python package installer) - will be auto-installed if not present
- Claude Code CLI (authenticated)
- Git (for commits)

## License

Same as original Ralph project.
