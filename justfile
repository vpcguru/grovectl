# grovectl development tasks
# Run `just` to see all available commands

# List available commands
default:
    @just --list

# Install all dependencies and set up development environment
install:
    uv sync --all-extras

# Run all checks (lint, type check, tests)
check:
    nox

# Run tests
test *args:
    nox -s tests -- {{ args }}

# Run tests for specific Python version
test-py version *args:
    nox -s tests-{{ version }} -- {{ args }}

# Run linting checks
lint:
    nox -s lint

# Fix linting issues automatically
lint-fix:
    nox -s lint -- --fix

# Check code formatting
format:
    nox -s format

# Apply code formatting
format-fix:
    nox -s format -- --write

# Run type checking
types:
    nox -s type_check

# Build distribution packages
build:
    nox -s build

# Clean all build artifacts
clean:
    nox -s clean

# Run pre-commit hooks
pre-commit:
    nox -s pre_commit

# Set up development environment
dev:
    nox -s dev

# Run the CLI
run *args:
    python -m grovectl {{ args }}

# List all nox sessions
sessions:
    nox --list
