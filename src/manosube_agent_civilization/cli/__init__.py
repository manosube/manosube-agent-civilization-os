"""Explicit genesis initialization and read-only restoration CLI adapters.

The single manosube console script delegates to existing Binding and Boot owners.
See 05_CLI/CLI_CONTRACT.md for historical and proposed contracts.
"""

from .errors import CLIArgumentError, CLIError, CLIInvalidRootError
from .main import main, run

__all__ = [
    "CLIArgumentError",
    "CLIError",
    "CLIInvalidRootError",
    "main",
    "run",
]
