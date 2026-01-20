# Ralph

Autonomous AI agent loop for executing PRDs (Product Requirement Documents).

## Installation

### From Git Repository

Install directly from GitHub (requires the packaged version with CLI entry point to be pushed):

```bash
# Install latest from main branch
pip install git+https://github.com/rodionsteshenko/ralph.git

# Install from specific branch
pip install git+https://github.com/rodionsteshenko/ralph.git@branch-name

# Install from specific commit
pip install git+https://github.com/rodionsteshenko/ralph.git@commit-hash
```

**Note**: Git installation requires that the packaged version (with CLI entry point defined in `pyproject.toml`) has been pushed to the remote repository. After installation, verify with:

```bash
ralph --version
ralph --help
```

### From Local Source (Development)

```bash
pip install -e .
```

## Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run type checking
mypy src/ralph/

# Run linting
ruff check src/ tests/
```

## Package Structure

```
src/ralph/
├── __init__.py      # Package initialization, version
├── cli.py           # Command-line interface
├── detect.py        # Project type detection
├── prd.py           # PRD parsing and management
├── gates.py         # Quality gates execution
├── loop.py          # Main execution loop
└── utils.py         # Utility functions
```

## Version

Current version: 0.1.0
