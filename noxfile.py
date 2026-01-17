"""Nox sessions for grovectl."""

from __future__ import annotations

import shutil
from pathlib import Path

import nox

# Use uv for faster dependency installation
nox.options.default_venv_backend = "uv"
nox.options.reuse_existing_virtualenvs = True

# Default sessions to run when no session is specified
nox.options.sessions = ["lint", "type_check", "tests"]

# Python versions to test against
PYTHON_VERSIONS = ["3.11", "3.12"]
PYTHON_DEFAULT = "3.11"

# Paths
SRC_DIR = "src"
TESTS_DIR = "tests"
PYTHON_PATHS = [SRC_DIR, TESTS_DIR, "noxfile.py"]


@nox.session(python=PYTHON_VERSIONS)
def tests(session: nox.Session) -> None:
    """Run the test suite with pytest.

    Usage:
        nox -s tests           # Run on all Python versions
        nox -s tests-3.11      # Run on Python 3.11 only
        nox -s tests -- -k test_config  # Run specific tests
        nox -s tests -- -x     # Stop on first failure
    """
    session.install("pytest", "pytest-cov", "pytest-mock")
    session.install("-e", ".")

    args = session.posargs or []
    session.run(
        "pytest",
        "--cov=grovectl",
        "--cov-report=term-missing",
        "--cov-report=html",
        *args,
    )


@nox.session(python=PYTHON_DEFAULT)
def lint(session: nox.Session) -> None:
    """Run ruff linting checks.

    Usage:
        nox -s lint            # Check for linting issues
        nox -s lint -- --fix   # Auto-fix issues
    """
    session.install("ruff")

    args = session.posargs or []
    if "--fix" in args:
        args = [a for a in args if a != "--fix"]
        session.run("ruff", "check", "--fix", *PYTHON_PATHS, *args)
    else:
        session.run("ruff", "check", *PYTHON_PATHS, *args)


@nox.session(name="format", python=PYTHON_DEFAULT)
def format_(session: nox.Session) -> None:
    """Format code with ruff.

    Usage:
        nox -s format          # Check formatting (CI mode)
        nox -s format -- --write  # Apply formatting
    """
    session.install("ruff")

    args = session.posargs or []
    if "--write" in args:
        args = [a for a in args if a != "--write"]
        # Sort imports and format code
        session.run("ruff", "check", "--select", "I", "--fix", *PYTHON_PATHS, *args)
        session.run("ruff", "format", *PYTHON_PATHS, *args)
    else:
        # Check mode for CI
        session.run("ruff", "check", "--select", "I", *PYTHON_PATHS, *args)
        session.run("ruff", "format", "--check", *PYTHON_PATHS, *args)


@nox.session(python=PYTHON_DEFAULT)
def type_check(session: nox.Session) -> None:
    """Run mypy type checking.

    Usage:
        nox -s type_check      # Run type checking
    """
    session.install("mypy", "types-paramiko", "types-PyYAML")
    session.install("-e", ".")

    session.run("mypy", f"{SRC_DIR}/grovectl", *session.posargs)


@nox.session(python=PYTHON_DEFAULT)
def build(session: nox.Session) -> None:
    """Build distribution packages (wheel and sdist).

    Usage:
        nox -s build           # Build packages to dist/
    """
    session.install("build")

    # Clean previous builds
    dist_dir = Path("dist")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    session.run("python", "-m", "build")
    session.log(f"Packages built in {dist_dir}/")


@nox.session(python=PYTHON_DEFAULT)
def dev(session: nox.Session) -> None:
    """Set up development environment.

    Usage:
        nox -s dev             # Install all dev dependencies
    """
    session.install("-e", ".[dev]")
    session.install("nox", "nox-uv")
    session.run("pre-commit", "install", external=True)
    session.log("Development environment ready!")


@nox.session(python=PYTHON_DEFAULT)
def install(session: nox.Session) -> None:
    """Install package in editable mode.

    Usage:
        nox -s install         # Install package only
    """
    session.install("-e", ".")
    session.log("Package installed in editable mode")


@nox.session(python=False)
def clean(session: nox.Session) -> None:
    """Remove build artifacts and cache directories.

    Usage:
        nox -s clean           # Clean all build artifacts
    """
    paths_to_remove = [
        "build",
        "dist",
        ".eggs",
        "*.egg-info",
        "src/*.egg-info",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "htmlcov",
        ".coverage",
        ".coverage.*",
        ".nox",
    ]

    for pattern in paths_to_remove:
        for path in Path().glob(pattern):
            session.log(f"Removing {path}")
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()

    # Remove __pycache__ directories
    for pycache in Path().rglob("__pycache__"):
        session.log(f"Removing {pycache}")
        shutil.rmtree(pycache)

    # Remove .pyc files
    for pyc in Path().rglob("*.pyc"):
        session.log(f"Removing {pyc}")
        pyc.unlink()

    session.log("Clean complete!")


@nox.session(python=PYTHON_DEFAULT)
def pre_commit(session: nox.Session) -> None:
    """Run pre-commit hooks on all files.

    Usage:
        nox -s pre_commit      # Run all pre-commit hooks
    """
    session.install("pre-commit")
    session.run("pre-commit", "run", "--all-files", *session.posargs)
