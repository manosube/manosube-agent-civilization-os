"""Phase 20 -- the real crash-injection subprocess worker (P87-R1-F1/F2).

The PR #87 structural review named two real gaps in the session-loss proof this module exists
to close:

* **F1** (``chatgpt-codex-connector``, ``session_loss.py:68``): the previous ``restart_and_
  reconstruct_state`` only started a *reader* child process -- one that opened the Store,
  reconstructed State, and printed it back as JSON -- while the parent process that had just
  run the cycle stayed alive and went on to run the next one. A proof of session-loss recovery
  built that way can report success without ever destroying the process-local state (caches,
  imports, open handles) a real crash would destroy.
* **F2** (``orchestrator.py``, then lines 78-80): every session-loss boundary was injected
  *after* ``run_one_cycle`` had already returned and Reflow had already committed -- so the
  work-unit-before-Change, Change-before-Evidence, Evidence-before-Reflow, and commit-
  interruption recovery paths Issue #86 documents were never actually exercised; a defect that
  lost or duplicated work after a genuine mid-cycle crash would still leave every Gate 20
  assertion green.

This module is the fix for both, together: it runs cycle *k* itself, up to one of the four
named boundaries below, in a dedicated child process invoked via ``subprocess.run`` (a real,
separate operating-system process, never a thread or an in-process stand-in -- the identical
real-interpreter-restart precedent ``tests/integration/boot/test_boot_project_route.py::
test_a_fresh_python_process_boots_successfully`` already establishes), and that child process
terminates via ``os._exit()`` -- a hard, unconditional kill that skips interpreter shutdown,
``atexit`` handlers, and Python-level stack unwinding, so nothing that process held in memory
survives it, unlike an exception the caller could catch and quietly carry on from. A second,
later, entirely separate child process then performs the actual continuation, holding no object
the first child ever constructed -- it resolves every input it needs (the corpus position, the
committed State) from the Store's own on-disk files alone.

**Why the first three boundaries share one real mechanism.** Direct inspection of every owner
:mod:`tests.long_running_proof.cycle` calls before ``reflow()`` -- :func:`~manosube_agent_
civilization.observation.observe`, :func:`~manosube_agent_civilization.difference.
derive_differences`, :func:`~manosube_agent_civilization.authority.evaluate_authority`,
:func:`~manosube_agent_civilization.change.derive_change`, :func:`~manosube_agent_civilization.
evidence.engine.derive_evidence` -- confirms none of them ever calls ``store.commit`` (this
repository's own K-003/R-001 static topology scan already proves exactly one module in the
installed package, ``reflow/commit.py``, ever does). A crash at ``WORK_UNIT_BEFORE_CHANGE``,
``CHANGE_BEFORE_EVIDENCE``, or ``EVIDENCE_BEFORE_REFLOW`` therefore always finds the Store
untouched by this cycle -- nothing durable exists to reconcile, and the sound recovery is to
re-derive cycle *k* fresh, through the identical real public entrypoints :mod:`tests.
long_running_proof.cycle` itself calls, in the same order, for the identical bounded prefix of
that sequence -- proven decisively here by three distinct, separately-invoked partial call
sequences, each ending in a real process kill, rather than assumed equivalent by argument alone.

**Why the fourth boundary is different.** ``REFLOW_COMMIT_INTERRUPTION`` crashes *inside*
``reflow()``'s own atomic Store commit, via the identical, already-accepted ``fault``
crash-injection parameter :meth:`~manosube_agent_civilization.store.file_store.FileStateStore.
commit` and ``tests/natural_cycle/proof.py``'s own ``FaultInjectingStore`` already establish for
this exact purpose -- except this fault hook calls ``os._exit()``, a real kill, rather than
raising a catchable exception. The crash lands at ``AFTER_COMMIT_INTENT`` -- durably written to
the recovery journal, but before the transaction's own event is appended to the lineage log --
the exact case :meth:`~manosube_agent_civilization.store.file_store.FileStateStore.recover`
exists to forward-complete. The continuation process therefore calls ``recover()``, never a
raw retried ``reflow()`` call (which would collide with the still-open recovery journal
directory a second attempt cannot safely reuse).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any

from tests.long_running_proof import cycle
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.reflow.route import reflow
from manosube_agent_civilization.store import FileStateStore

#: The exact four positions Issue #86 documents and the PR #87 review (F2) names by name.
BOUNDARIES: tuple[str, ...] = (
    "WORK_UNIT_BEFORE_CHANGE",
    "CHANGE_BEFORE_EVIDENCE",
    "EVIDENCE_BEFORE_REFLOW",
    "REFLOW_COMMIT_INTERRUPTION",
)

#: A distinctive, unambiguous ``os._exit`` code -- never ``0`` (clean exit) or a signal-range
#: value a real unrelated crash might also produce -- so the parent can tell "the injected
#: boundary really fired" apart from "the child died some other way."
CRASH_EXIT_CODE = 75

#: The one ``FileStateStore.commit`` stage the ``REFLOW_COMMIT_INTERRUPTION`` boundary crashes
#: at: durable ``COMMIT_INTENT``, but the transaction's own event has not yet reached the
#: lineage log -- exactly the case :meth:`FileStateStore.recover` exists to complete.
REFLOW_CRASH_STAGE = "AFTER_COMMIT_INTENT"


class _CrashingStore(FileStateStore):
    """The identical ``FaultInjectingStore`` seam ``tests/natural_cycle/proof.py`` already
    established for a real ``reflow()``-driven commit's own crash/recovery behavior, except the
    fault hook calls ``os._exit()`` -- a genuine process kill -- rather than raising."""

    def commit(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        def fault(stage: str) -> None:
            if stage == REFLOW_CRASH_STAGE:
                os._exit(CRASH_EXIT_CODE)

        kwargs["fault"] = fault
        return super().commit(*args, **kwargs)


def _build_store(store_root: Path, boundary: str) -> FileStateStore:
    if boundary == "REFLOW_COMMIT_INTERRUPTION":
        return _CrashingStore(store_root, schema_root=SCHEMA_ROOT)
    return FileStateStore(store_root, schema_root=SCHEMA_ROOT)


def _crash(store_root: Path, project_id: str, k: int, boundary: str, pid_file: Path) -> None:
    """Perform real work for cycle *k* up through *boundary*, then terminate this real OS
    process via ``os._exit`` -- never returns normally for any recognized boundary."""

    pid_file.write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")
    store = _build_store(store_root, boundary)
    committed_state = store.load_current(project_id)

    before = cycle.observe_before(k, committed_state)
    diff = cycle.derive_difference(k, committed_state, before)
    cycle.verify_expected_corpus_position(k, committed_state, diff["difference"])
    authority = cycle.check_authority(k, diff["difference"])
    if boundary == "WORK_UNIT_BEFORE_CHANGE":
        os._exit(CRASH_EXIT_CODE)

    cycle.derive_the_change(authority)
    if boundary == "CHANGE_BEFORE_EVIDENCE":
        os._exit(CRASH_EXIT_CODE)

    # EVIDENCE_BEFORE_REFLOW and REFLOW_COMMIT_INTERRUPTION both need the complete assembly --
    # cycle.assemble_one_cycle is this proof's own documented seam for exactly this ("without
    # calling reflow() itself, so a required negative/interruption-route test can mutate exactly
    # one already-real input and call reflow() directly").
    assembly = cycle.assemble_one_cycle(store, k=k, committed_state=committed_state)
    cycle.verify_expected_corpus_position(k, committed_state, assembly["difference"])
    if boundary == "EVIDENCE_BEFORE_REFLOW":
        os._exit(CRASH_EXIT_CODE)

    if boundary == "REFLOW_COMMIT_INTERRUPTION":
        reflow(store, **assembly["reflow_kwargs"])
        # The fault hook always fires before this real reflow() call can return -- reaching
        # here would mean the injected crash never happened.
        raise AssertionError(
            "REFLOW_COMMIT_INTERRUPTION: reflow() returned without the injected os._exit "
            "firing at AFTER_COMMIT_INTENT -- the crash boundary did not fire"
        )

    raise AssertionError(f"unrecognized crash boundary: {boundary!r}")


def _continue(
    store_root: Path, project_id: str, k: int, boundary: str, pid_file: Path
) -> dict[str, Any]:
    """Complete cycle *k*, in a fresh process holding no object the crash process ever built,
    using only what the Store's own on-disk files make resolvable. Returns the identical shape
    :func:`~tests.long_running_proof.orchestrator.attempt_cycle`'s own committed branch does."""

    pid_file.write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)

    if boundary == "REFLOW_COMMIT_INTERRUPTION":
        pre_crash_state = store.load_current(project_id)
        assembly = cycle.assemble_one_cycle(store, k=k, committed_state=pre_crash_state)
        store.recover(project_id)
        committed_state = store.load_current(project_id)
        return {
            "outcome": "committed",
            "committed_state": committed_state,
            "identity": {
                "cycle": k,
                "difference_id": assembly["difference"]["difference_id"],
                "final_state_revision": committed_state["state_revision"],
            },
        }

    committed_state = store.load_current(project_id)
    result = cycle.run_one_cycle(store, k=k, committed_state=committed_state)
    return {
        "outcome": "committed",
        "committed_state": result["reflow_result"]["committed_state"],
        "identity": result["identity"],
    }


def main(argv: list[str]) -> int:
    mode, store_root_s, project_id, k_s, boundary, pid_file_s = argv[1:7]
    store_root = Path(store_root_s)
    k = int(k_s)
    pid_file = Path(pid_file_s)
    if boundary not in BOUNDARIES:
        raise ValueError(f"unrecognized crash boundary: {boundary!r}")

    if mode == "crash":
        _crash(store_root, project_id, k, boundary, pid_file)
        return 1  # unreachable: _crash always terminates via os._exit or raises
    if mode == "continue":
        result = _continue(store_root, project_id, k, boundary, pid_file)
        print(json.dumps(result))  # noqa: T201 -- this process's own real return channel
        return 0
    raise ValueError(f"unrecognized mode: {mode!r}")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
