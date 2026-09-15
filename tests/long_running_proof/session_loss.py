"""Phase 20 -- real process-boundary session-loss recovery (Issue #86 section 6).

Reuses the identical, already-accepted real interpreter-level restart precedent
``tests/integration/boot/test_boot_project_route.py::test_a_fresh_python_process_boots_
successfully`` establishes: a genuinely separate Python process (``subprocess.run([sys.
executable, "-c", script], ...)``), never an in-process "pretend restart" that only proves
object-identity independence. This module's own restart kills every in-memory Python object
the parent process holds and reconstructs canonical State solely from the Store's own on-disk
files, through :meth:`~manosube_agent_civilization.store.file_store.FileStateStore.reconstruct`
-- the explicit ``CANONICAL_BOOT_OR_RECONSTRUCTION_REQUIRED=true`` alternative to a full
``boot_project`` call this Issue's own fixture world does not otherwise need (no Project
Binding is admitted in this proof's fixture world; a bare, real Store reconstruction is
Issue #86's own named natural-route boundary, not a shortcut around it).

**Why the four named crash boundaries collapse to two real mechanisms, not four.** Issue #86
names four positions: work-unit-open-before-Change, Change-admission-after-before-Evidence,
Evidence-after-before-Reflow, and Reflow-after-before-terminal-projection. Direct inspection of
every owner :mod:`tests.long_running_proof.cycle` calls before ``reflow()`` --
:func:`~manosube_agent_civilization.observation.observe`, :func:`~manosube_agent_civilization.
difference.derive_differences`, :func:`~manosube_agent_civilization.authority.
evaluate_authority`, :func:`~manosube_agent_civilization.change.derive_change`,
:func:`~manosube_agent_civilization.evidence.engine.derive_evidence` -- shows none of them ever
calls ``store.commit`` or any other Store write path (``topology.py``'s own K-003/R-001 static
scan already proves exactly one module in the installed package, ``reflow/commit.py``, ever
calls ``FileStateStore.commit``). A crash at any of the first three named boundaries is
therefore, by construction, identical in observable effect to a crash before this cycle's
``reflow()`` call was ever made: nothing durable exists yet to reconcile, and the correct
(and only sound) recovery is to re-derive the identical cycle fresh and retry -- proven here by
:func:`restart_before_reflow`. The fourth boundary -- crash during/after Reflow's own atomic
commit -- is the one boundary with real durable state to reconcile, and is proven by reusing
the identical, already-accepted ``FaultInjectingStore``/``fault`` crash-injection seam
``tests/natural_cycle/proof.py`` already established for exactly this purpose, together with
the Store's own real :meth:`~manosube_agent_civilization.store.file_store.FileStateStore.
recover` and a retried ``reflow()`` call -- see :func:`crash_during_reflow_commit_and_recover`.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from tests.state_helpers import SCHEMA_ROOT

ROOT = SCHEMA_ROOT.parent


def restart_and_reconstruct_state(store_root: Path, project_id: str) -> dict[str, Any]:
    """Genuinely restart in a fresh Python process (a real interpreter, not an in-process
    stand-in) and reconstruct canonical State solely from *store_root*'s own on-disk files.
    Returns the **full** reconstructed State, printed back by the child process as JSON on its
    final stdout line -- nothing from the parent process's own memory is trusted, and the
    caller may (and, for a genuine continuation proof, must) resume the next cycle directly
    from this returned value rather than any object the now-dead process held."""

    script = (
        "import json\n"
        "from pathlib import Path\n"
        "from manosube_agent_civilization.store import FileStateStore\n"
        f"store = FileStateStore(Path({str(store_root)!r}), schema_root=Path({str(SCHEMA_ROOT)!r}))\n"
        f"state = store.reconstruct({project_id!r})\n"
        "print(json.dumps(state))\n"
    )
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"real process-boundary restart failed (exit {proc.returncode}): {proc.stderr}"
        )
    last_line = proc.stdout.strip().splitlines()[-1]
    return dict(json.loads(last_line))


def restart_before_reflow(store_root: Path, project_id: str) -> dict[str, Any]:
    """The work-unit-open/Change-admission/Evidence session-loss boundaries, collapsed:
    a real process restart injected after this cycle's own pre-``reflow()`` steps have run
    (in the now-dead parent process) but before its own ``reflow()`` call was ever made.
    Nothing was durably committed by any of those steps (see module docstring), so the
    correct post-restart observation is that canonical State is still at its pre-cycle
    revision -- returned here, from a genuinely fresh process, for the caller to assert
    against and then safely retry the identical cycle."""

    return restart_and_reconstruct_state(store_root, project_id)
