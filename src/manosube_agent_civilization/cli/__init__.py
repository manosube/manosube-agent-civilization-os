"""CLI Boot adapter (Phase 11, Issue #47): ``KERNEL_ELEMENT=PROCESS_ADAPTER``.

Exposes the existing, already-verified :func:`~manosube_agent_civilization.boot.boot_project`
route as one explicit, read-only, provider-neutral command-line command:

.. code-block:: text

   manosube boot --store-root PATH --schema-root PATH --project-id ID --project-binding-id ID

installed as the sole ``[project.scripts]`` console-script entry point (``pyproject.toml``,
``manosube = "manosube_agent_civilization.cli.main:main"``; see ``05_CLI/CLI_CONTRACT.md``
§2). There is no second, module-execution (``python -m ...``) public entry point -- this
package's own ``main``/``run`` remain importable only as the internal API the console script
itself calls. This is not a second Boot, Store, Binding, Objective, Authority, or
reference-resolution owner: the CLI owns only argument parsing, process exit status, and
canonical-JSON serialization of the result. It never calls ``FileStateStore.initialize``,
``.commit``, ``.recover``, or ``.load_current``, never discovers a Project, and never mutates
the Store either on success or on any rejection.

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
