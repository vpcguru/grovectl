"""Entry point for running grovectl as a module.

This allows running the CLI with:
    python -m grovectl
"""

from grovectl.cli.main import cli

if __name__ == "__main__":
    cli()
