# Ralph Python Implementation

A Python-based implementation of the Ralph autonomous AI agent loop using Claude API.

## Quick Start

```bash
# Install dependencies (uses UV for fast installation)
make install

# Set API key
export ANTHROPIC_API_KEY=your_key_here

# Run example
make run-example
```

## Development

```bash
# Set up development environment
make setup

# Install dev dependencies
make install-dev

# Format code
make format

# Run linters
make lint

# Run all checks
make check

# Clean generated files
make clean
```

## Usage

See [QUICKSTART.md](QUICKSTART.md) for detailed usage instructions.

## Documentation

- [QUICKSTART.md](QUICKSTART.md) - Quick start guide
- [ralph_python_README.md](ralph_python_README.md) - Full documentation
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Implementation details
- [agent_prompt_template.md](agent_prompt_template.md) - Prompt template docs

## Makefile Commands

Run `make help` to see all available commands:

- `make setup` - Set up development environment
- `make install` - Install Python dependencies
- `make install-dev` - Install development dependencies
- `make lint` - Run linters (ruff, mypy)
- `make format` - Format code (ruff format)
- `make format-check` - Check formatting without modifying
- `make test` - Run tests
- `make check` - Run all checks (format + lint)
- `make clean` - Clean generated files
- `make verify` - Verify installation
- `make venv` - Create virtual environment
- `make typecheck` - Run type checker
- `make version` - Show version info

## Requirements

- Python 3.8+
- UV (Python package installer) - will be auto-installed if not present
- Anthropic API key
- Git (for commits)

## License

Same as original Ralph project.
