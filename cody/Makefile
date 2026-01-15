.PHONY: install install-dev test typecheck lint format clean help

# Default target
help:
	@echo "Cody Project - Available commands:"
	@echo "  make install      - Install production dependencies"
	@echo "  make install-dev  - Install development dependencies"
	@echo "  make test         - Run tests with pytest"
	@echo "  make typecheck    - Run type checking with mypy"
	@echo "  make lint         - Run linting with ruff"
	@echo "  make format       - Format code with ruff"
	@echo "  make clean        - Clean build artifacts and caches"

# Install production dependencies
install:
	python3 -m pip install -e .

# Install development dependencies
install-dev:
	python3 -m pip install -e ".[dev]"

# Run tests
test:
	python3 -m pytest

# Run type checking
typecheck:
	python3 -m mypy src/

# Run linting
lint:
	python3 -m ruff check src/ tests/

# Format code
format:
	python3 -m ruff format src/ tests/
	python3 -m ruff check --fix src/ tests/

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
