.PHONY: help setup install lint format test clean run-example check

# Default target
help:
	@echo "Ralph Python - Makefile Commands"
	@echo ""
	@echo "  make setup       - Set up development environment"
	@echo "  make install     - Install Python dependencies"
	@echo "  make lint        - Run linters (ruff, mypy)"
	@echo "  make format      - Format code (ruff format)"
	@echo "  make test        - Run tests (if available)"
	@echo "  make check       - Run lint and format check"
	@echo "  make clean       - Clean generated files"
	@echo "  make run-example - Run example workflow"
	@echo ""

# Set up development environment
setup: install
	@echo "✅ Development environment ready"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Set ANTHROPIC_API_KEY: export ANTHROPIC_API_KEY=your_key"
	@echo "  2. Run: make run-example"
	@echo ""

# Install dependencies
install:
	@echo "📦 Installing Python dependencies with UV..."
	@if command -v uv > /dev/null; then \
		uv pip install -r requirements.txt; \
	else \
		echo "⚠️  UV not found. Installing UV..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
		uv pip install -r requirements.txt; \
	fi
	@echo "✅ Dependencies installed"

# Install development dependencies
install-dev: install
	@echo "📦 Installing development dependencies with UV..."
	@if command -v uv > /dev/null; then \
		uv pip install ruff mypy black pytest; \
	else \
		echo "⚠️  UV not found. Installing UV..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
		uv pip install ruff mypy black pytest; \
	fi
	@echo "✅ Development dependencies installed"

# Run linters
lint:
	@echo "🔍 Running linters..."
	@if command -v ruff > /dev/null; then \
		ruff check ralph.py; \
	else \
		echo "⚠️  ruff not installed. Run: make install-dev"; \
	fi
	@if command -v mypy > /dev/null; then \
		mypy ralph.py --ignore-missing-imports || true; \
	else \
		echo "⚠️  mypy not installed. Run: make install-dev"; \
	fi
	@echo "✅ Linting complete"

# Format code
format:
	@echo "✨ Formatting code..."
	@if command -v ruff > /dev/null; then \
		ruff format ralph.py; \
		echo "✅ Code formatted"; \
	else \
		echo "⚠️  ruff not installed. Run: make install-dev"; \
	fi

# Check formatting (without modifying)
format-check:
	@echo "🔍 Checking code formatting..."
	@if command -v ruff > /dev/null; then \
		ruff format --check ralph.py; \
	else \
		echo "⚠️  ruff not installed. Run: make install-dev"; \
	fi

# Run tests
test:
	@echo "🧪 Running tests..."
	@if [ -d "tests" ]; then \
		pytest tests/ -v; \
	else \
		echo "⚠️  No tests directory found"; \
	fi

# Run all checks
check: format-check lint
	@echo "✅ All checks passed"

# Clean generated files
clean:
	@echo "🧹 Cleaning generated files..."
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name ".pytest_cache" -delete 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -r {} + 2>/dev/null || true
	@echo "✅ Clean complete"

# Run example workflow (requires API key)
run-example:
	@echo "🚀 Running example workflow..."
	@if [ -z "$$ANTHROPIC_API_KEY" ]; then \
		echo "❌ Error: ANTHROPIC_API_KEY not set"; \
		echo "   Set it with: export ANTHROPIC_API_KEY=your_key"; \
		exit 1; \
	fi
	@echo "✅ API key found"
	@echo ""
	@echo "Example commands:"
	@echo "  python ralph.py process-prd <prd_file>"
	@echo "  python ralph.py execute-plan --max-iterations 10"
	@echo "  python ralph.py status"

# Verify installation
verify:
	@echo "🔍 Verifying installation..."
	@python3 --version || (echo "❌ Python 3 not found" && exit 1)
	@python3 -c "import anthropic" || (echo "❌ anthropic package not installed. Run: make install" && exit 1)
	@python3 ralph.py --help > /dev/null || (echo "❌ ralph.py not executable" && exit 1)
	@echo "✅ Installation verified"

# Create virtual environment
venv:
	@echo "📦 Creating virtual environment with UV..."
	@if command -v uv > /dev/null; then \
		uv venv; \
		echo "✅ Virtual environment created"; \
		echo ""; \
		echo "Activate with: source .venv/bin/activate"; \
	else \
		echo "⚠️  UV not found. Installing UV..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
		uv venv; \
		echo "✅ Virtual environment created"; \
		echo ""; \
		echo "Activate with: source .venv/bin/activate"; \
	fi

# Type check
typecheck:
	@echo "🔍 Running type checker..."
	@if command -v mypy > /dev/null; then \
		mypy ralph.py --ignore-missing-imports; \
	else \
		echo "⚠️  mypy not installed. Run: make install-dev"; \
	fi

# Show version info
version:
	@echo "Ralph Python Implementation"
	@echo "Python version: $$(python3 --version)"
	@if command -v uv > /dev/null; then \
		echo "UV version: $$(uv --version)"; \
	else \
		echo "UV: not installed"; \
	fi
	@if command -v ruff > /dev/null; then \
		echo "ruff version: $$(ruff --version)"; \
	fi
	@if command -v mypy > /dev/null; then \
		echo "mypy version: $$(mypy --version)"; \
	fi
	@python3 -c "import anthropic; print(f'anthropic version: {anthropic.__version__}')" 2>/dev/null || echo "anthropic: not installed"
