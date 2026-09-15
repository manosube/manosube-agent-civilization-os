"""Phase 20 -- real process-boundary session-loss recovery (Issue #86 section 6).

**P87-R1-F1/F2 (PR #87 structural review).** The Round 0 delivery's own ``restart_and_
reconstruct_state`` only started a *reader* child process (one that opened the Store,
reconstructed State, and printed it back as JSON) after a cycle had already run to completion,
committed, *in the parent process* -- the process that had just run the cycle stayed alive and
went on to run the next one, so the proof could report successful process-loss recovery without
ever destroying the executing process's own in-memory state (F1), and every injected boundary
landed only between two already-completed cycles, never mid-cycle, so the four documented
recovery paths (work-unit-before-Change, Change-before-Evidence, Evidence-before-Reflow,
commit-interruption) were never actually exercised (F2).

:func:`crash_mid_cycle_and_recover` is the fix for both, together: cycle *k* itself now runs,
up through one of :mod:`tests.long_running_proof.crash_worker`'s four named boundaries, inside a
dedicated child process that terminates via ``os._exit`` -- a real, unconditional kill, not a
catchable exception -- and a second, later, entirely separate child process performs the actual
continuation, holding no object the first child ever built. Both are genuine, separate operating
system processes (``subprocess.run``), the identical real-interpreter-restart precedent
``tests/integration/boot/test_boot_project_route.py::test_a_fresh_python_process_boots_
successfully`` already establishes -- never an in-process "pretend restart" that only proves
object-identity independence. See :mod:`tests.long_running_proof.crash_worker`'s own module
docstring for why the first three boundaries share one real mechanism (nothing is ever durably
committed before ``reflow()``) while the fourth -- a real crash inside ``reflow()``'s own atomic
Store commit -- is the one boundary :meth:`~manosube_agent_civilization.store.file_store.
FileStateStore.recover` exists to reconcile.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

from tests.long_running_proof import crash_worker
from tests.state_helpers import SCHEMA_ROOT

ROOT = SCHEMA_ROOT.parent

#: How long a single crash or continuation child process may run before this proof treats it as
#: hung rather than crashed/completed -- generous enough for the slowest real cycle assembly
#: (schema validation, signing) this repository's own suites already tolerate elsewhere.
SUBPROCESS_TIMEOUT_SECONDS = 120


def _run_worker(mode: str, store_root: Path, project_id: str, k: int, boundary: str) -> Any:
    with tempfile.TemporaryDirectory() as tmp:
        pid_file = Path(tmp) / "pid.json"
        proc = subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-m",
                "tests.long_running_proof.crash_worker",
                mode,
                str(store_root),
                project_id,
                str(k),
                boundary,
                str(pid_file),
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=SUBPROCESS_TIMEOUT_SECONDS,
        )
        pid = json.loads(pid_file.read_text(encoding="utf-8"))["pid"] if pid_file.exists() else None
        return proc, pid


def crash_mid_cycle_and_recover(
    store_root: Path,
    *,
    project_id: str,
    k: int,
    boundary: str,
) -> dict[str, Any]:
    """Genuinely crash cycle *k* mid-execution at *boundary* in one real, dedicated child
    process, then complete it in a second, later, entirely separate real child process.

    Raises if the first process did not actually terminate via the injected ``os._exit`` (proof
    that the boundary really fired, not merely that some unrelated failure occurred), if the
    second process did not exit cleanly, or if the two child processes turn out to share a PID
    (proof they are genuinely two separate operating-system processes, not one process this
    caller merely invoked twice)."""

    if boundary not in crash_worker.BOUNDARIES:
        raise ValueError(f"unrecognized crash boundary: {boundary!r}")

    crash_proc, crash_pid = _run_worker("crash", store_root, project_id, k, boundary)
    if crash_proc.returncode != crash_worker.CRASH_EXIT_CODE:
        raise RuntimeError(
            f"boundary {boundary} (cycle {k}): crash worker did not terminate via the "
            f"injected os._exit (exit {crash_proc.returncode}, expected "
            f"{crash_worker.CRASH_EXIT_CODE}) -- stderr:\n{crash_proc.stderr}"
        )

    continue_proc, continue_pid = _run_worker("continue", store_root, project_id, k, boundary)
    if continue_proc.returncode != 0:
        raise RuntimeError(
            f"boundary {boundary} (cycle {k}): continuation worker failed (exit "
            f"{continue_proc.returncode}) -- stderr:\n{continue_proc.stderr}"
        )

    if crash_pid is None or continue_pid is None or crash_pid == continue_pid:
        raise RuntimeError(
            f"boundary {boundary} (cycle {k}): crash and continuation must be genuinely "
            f"distinct operating-system processes -- got crash_pid={crash_pid!r}, "
            f"continue_pid={continue_pid!r}"
        )

    last_line = continue_proc.stdout.strip().splitlines()[-1]
    result: dict[str, Any] = json.loads(last_line)
    result["crash_pid"] = crash_pid
    result["continuation_pid"] = continue_pid
    return result
