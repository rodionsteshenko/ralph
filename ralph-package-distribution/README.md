# Ralph

Autonomous AI agent loop for executing PRDs (Product Requirement Documents).

## Installation

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
