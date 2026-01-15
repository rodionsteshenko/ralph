# Cody: Personal AI Assistant

A stateful, personal AI assistant with persistent memory, temporal awareness, and skill-based architecture. Built on Claude Agent SDK (Python) with a CLI interface initially, expanding to Slack.

## Features

- **Persistent Memory**: Remembers conversations, facts, and context across sessions
- **Temporal Awareness**: Understands time-based context and can track events over time
- **Skill-Based Architecture**: Extensible system for adding capabilities
- **Claude Agent SDK**: Powered by Anthropic's Claude Agent SDK for advanced AI capabilities

## Project Structure

```
cody/
├── src/                    # Source code
│   └── __init__.py
├── tests/                  # Test suite
│   └── __init__.py
├── .cody/                  # Cody data directory
│   └── data/              # Persistent data storage (gitignored)
├── pyproject.toml         # Project configuration and dependencies
├── Makefile              # Build and development commands
└── README.md             # This file
```

## Requirements

- Python 3.10 or higher
- pip (Python package installer)

## Installation

### 1. Install Dependencies

```bash
# Install production dependencies
make install

# Or install with development dependencies (recommended for development)
make install-dev
```

### 2. Verify Installation

```bash
# Run type checking
make typecheck

# Run tests
make test

# Run linting
make lint
```

## Development

### Available Make Commands

```bash
make help         # Show all available commands
make install      # Install production dependencies
make install-dev  # Install development dependencies
make test         # Run tests with pytest
make typecheck    # Run type checking with mypy
make lint         # Run linting with ruff
make format       # Format code with ruff
make clean        # Clean build artifacts and caches
```

### Code Quality

This project uses:
- **mypy**: Static type checking
- **ruff**: Linting and code formatting
- **pytest**: Testing framework

All code must pass type checking, linting, and tests before merging.

### Testing

Run the test suite:

```bash
make test
```

Run specific test types:

```bash
# Run only unit tests
pytest -m unit

# Run only E2E tests
pytest -m e2e

# Run with coverage report
pytest --cov=src --cov-report=html
```

### Type Checking

```bash
make typecheck
```

### Linting and Formatting

```bash
# Check for linting issues
make lint

# Auto-format code
make format
```

## Dependencies

### Production Dependencies
- **claude-agent-sdk**: Claude Agent SDK for AI capabilities
- **pyyaml**: YAML configuration file support
- **rich**: Rich text and beautiful formatting in the terminal

### Development Dependencies
- **pytest**: Testing framework
- **pytest-asyncio**: Async testing support
- **pytest-cov**: Code coverage reporting
- **mypy**: Static type checker
- **ruff**: Fast Python linter and formatter
- **types-PyYAML**: Type stubs for PyYAML

## License

TBD

## Contributing

This project is currently in development. Contribution guidelines will be added soon.
