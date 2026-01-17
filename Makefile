.PHONY: help install install-dev test test-cov lint format type-check clean pre-commit

# Default target
help:
	@echo "grovectl - macOS VM Management CLI"
	@echo ""
	@echo "Usage:"
	@echo "  make install        Install package in production mode"
	@echo "  make install-dev    Install package in development mode with all dev dependencies"
	@echo "  make test           Run tests"
	@echo "  make test-cov       Run tests with coverage report"
	@echo "  make lint           Run linting checks"
	@echo "  make format         Format code with black and ruff"
	@echo "  make type-check     Run mypy type checking"
	@echo "  make pre-commit     Run pre-commit hooks on all files"
	@echo "  make clean          Remove build artifacts and cache files"
	@echo ""

# Installation
install:
	pip install .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

# Testing
test:
	pytest

test-cov:
	pytest --cov=grovectl --cov-report=term-missing --cov-report=html

# Linting and formatting
lint:
	ruff check src tests
	black --check src tests

format:
	ruff check --fix src tests
	black src tests

type-check:
	mypy src/grovectl

# Pre-commit
pre-commit:
	pre-commit run --all-files

# Cleanup
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf src/*.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Development helpers
run:
	python -m grovectl

shell:
	python -c "from grovectl import *; import code; code.interact(local=locals())"
