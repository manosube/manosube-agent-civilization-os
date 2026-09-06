"""CLI Boot adapter (Phase 11, Issue #47): ``KERNEL_ELEMENT=PROCESS_ADAPTER``.

Exposes the existing, already-verified :func:`~manosube_agent_civilization.boot.boot_project`
route as one explicit, read-only, provider-neutral command-line command:

.. code-block:: text

   manosube boot --store-root PATH --schema-root PATH --project-id ID --project-binding-id ID

invoked as ``python -m manosube_agent_civilization.cli boot ...`` (this v0.1 delivery adds no
``[project.scripts]`` console-script entry -- the module entry point below is the one this
Issue's own package/module choice resolves to; see ``05_CLI/CLI_CONTRACT.md`` §2). This is not
a second Boot, Store, Binding, Objective, Authority, or reference-resolution owner: the CLI
owns only argument parsing, process exit status, and canonical-JSON serialization of the
result. It never calls ``FileStateStore.initialize``, ``.commit``, ``.recover``, or
``.load_current``, never discovers a Project, and never mutates the Store either on success
or on any rejection.

See ``05_CLI/CLI_INDEX.md`` for the full contract set.
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
