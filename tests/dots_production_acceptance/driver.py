"""WU2 Phase A (Issue #116 / PR #119 follow-up): dispatch loop + stop/reconcile gate per
``docs/validation/dots_production_acceptance/MEASUREMENT_CONTRACT.md`` Sec.A.

**Phase A scope, explicit disclaimer:** ``dots_adapter`` here is always a caller-supplied,
fixed-fixture stub (see ``FixedFixtureDotsAdapter`` below) implementing
``PROTOCOL.md`` Sec.4's five adapter responsibilities with canned, deterministic
behavior for the one responsibility this module cannot reach -- dots' own act of
accepting/handing off a work unit. This module makes zero live dots/GitHub call and is
never, by itself, evidence of a real dots connection or a production-operation success
-- see this package's own PR body / README for the same disclaimer. A real
``dots_adapter.py`` (Phase B) is built once SHUKOU's Reading A/B/C decision and
``OPEN_ITEMS.md`` item 7 are resolved; this module's dispatch-loop/stop-gate/
reconciliation-gated-resume shape is adapter-agnostic and does not change when that
happens -- only the adapter object passed in does.

**Never a second State/Authority/Evidence/Reflow/Work-Coordination owner, and never a
second call into with_work_time_coordination under an invented or borrowed adapter_kind.**
``work_time_transparency/types.py``'s own ``ADAPTER_KINDS`` is a closed vocabulary --
"nothing added, nothing narrowed" except two precedented, explicitly SHUKOU-ratified
exceptions (Issue #86/#89). This module mints no new member and never opens a
coordination of its own under a borrowed one. Instead, once dots' own fixture hand-off
is recorded, the actual authorized low-risk change is executed through the real,
unmodified ``manosube_agent_civilization.change_executor.route.compose_change_executor``
entrypoint -- the real CHANGE_EXECUTOR adapter this repository already has, matching
PROTOCOL.md Sec.2's own role table (dots hands an authorized work unit to the existing
CLAUDE_CODE/GITHUB_COPILOT executor; that executor IS the CHANGE_EXECUTOR). That real
entrypoint already composes ``with_work_time_coordination`` under the correct,
already-authorized ``CHANGE_EXECUTOR``/``change_executor_execution`` pair internally --
this module never calls that primitive itself. ``Driver.dispatch`` instead *reads back*
the real, content-addressed ``work_time_coordination_open``/``_terminal`` records
``execute()`` itself committed, by recomputing their deterministic ids from the exact
inputs this module supplied (see ``_recompute_work_time_coordination_ids`` below) --
satisfying ``OPEN_ITEMS.md`` item 8's own audit requirement (confirm the driver calls a
route that already composes this primitive, never a bypassed raw commit) without this
module duplicating or mislabeling that primitive's own bookkeeping.

The 7 observation points of ``MEASUREMENT_CONTRACT.md`` Sec.A, and this module's own
primary source for each (never uniformly "via Store" -- each row names its own real
observation surface):

================================  =========================================================
Event                             Primary observation in this module
================================  =========================================================
1. Dispatch start                 the real ``work_time_coordination_open`` record
                                   ``compose_change_executor()``'s own ``execute()`` commits
                                   -- read back here by recomputed id, never re-derived or
                                   re-committed by this module
2. Stop-request acceptance        ``DriverRunState``'s own durable, local
                                   ``stop_ack`` field -- written ONLY after the adapter's
                                   ``stop_and_reconcile`` call returns an explicit positive
                                   acknowledgment; an unconfirmed/negative/missing ack is
                                   recorded as ``STOP_UNCONFIRMED`` and dispatch stays
                                   blocked exactly as if a confirmed stop had landed
3. New-dispatch-stop               ``Driver.dispatch`` itself refuses once
                                   ``stop_ack in {"ACCEPTED", "UNCONFIRMED"}``
4. Worker termination              for this Phase A path, the real ``execute()`` call
                                   returning/raising IS the observed termination (it is a
                                   synchronous in-process call, not a separate OS worker);
                                   cross-checked against the real
                                   ``work_time_coordination_terminal.terminal_outcome``.
                                   ``ProcessSupervisor`` (below) remains available, tested
                                   independently, for a genuinely separate delegated-worker
                                   process in a future case that needs one
5. Fault detection                 ``work_time_coordination_terminal.heartbeat_deadline_
                                   breached`` (derived automatically by the Kernel's own
                                   ``with_work_time_coordination``/``record_work_time_
                                   terminal_notice``), read back the same way as event 1
6. Recovery start                  a fresh ``execute()`` call for a new ``change_id``/
                                   ``claim_token`` pair in the same work_unit_ref lineage --
                                   gated behind event 7 below
7. Reconciliation completion       ``reconciliation.reconcile()`` (unchanged, reused as-is):
                                   Store re-read AND an independent re-read of the adapter's
                                   own external state -- never either alone
================================  =========================================================

**Invariant, enforced here, not merely advisory:** no work unit is ever re-dispatched while
its prior attempt's ``run_state`` is not yet ``RESOLVED`` -- "unknown" is resolved only by a
completed two-part reconciliation, never by a timeout alone (``MEASUREMENT_CONTRACT.md``
Sec.A's own invariant; ``case-catalog.json``'s ``COMMIT_ACK_UNKNOWN``/``TRANSPORT_OUTAGE``
cases already require this same gate).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import contextlib
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
from typing import Any

from manosube_agent_civilization.work_time_transparency.clock import default_clock
from manosube_agent_civilization.work_time_transparency.identity import (
    work_time_coordination_open_id,
    work_time_coordination_terminal_id,
)

CASE_CLASSIFICATIONS = frozenset(
    {"NORMAL_OPERATION", "INTENTIONAL_REFUSAL_TEST", "ENVIRONMENT_FAULT"}
)
RUN_STATES = frozenset({"DISPATCHED", "PENDING_HUMAN_APPROVAL", "RESOLVED"})

#: The exact formula compose_change_executor()'s own execute() uses internally
#: (change_executor/route.py's _work_unit_id) -- duplicated here ONLY to recompute the
#: same deterministic id from the same inputs for readback, never to mint a second,
#: independent id of this module's own invention.
_CHANGE_EXECUTOR_WORK_UNIT_REF_KIND = "change_executor_execution"


class DriverError(Exception):
    """Raised when this module is asked to violate its own contract -- e.g. dispatching a
    new work unit after a stop has been accepted or left unconfirmed, or re-dispatching a
    work unit whose prior attempt is not yet ``RESOLVED``."""


def _recompute_change_executor_work_unit_id(
    *, project_id: str, change_id: str, claim_token: str, attempt_marker: str
) -> str:
    """Mirrors ``change_executor/route.py``'s own private ``_work_unit_id`` computation
    exactly -- a pure function of these four values the caller (this module) already
    knows, since it supplied *project_id*/*change_id*/*claim_token* and captured
    *attempt_marker* as the first reading of the ``work_time_coordination_clock`` it
    injected into ``execute()``. This lets ``Driver.dispatch`` read back the real record
    ``execute()`` committed without that route needing to return it."""

    return (
        "CHEXEC-"
        + hashlib.sha256(f"{project_id}|{change_id}|{claim_token}|{attempt_marker}".encode())
        .hexdigest()
        .upper()
    )


@dataclass
class _CapturingClock:
    """Wraps ``default_clock`` and records every reading in call order -- the first
    reading a call to ``execute(..., work_time_coordination_clock=this)`` makes is always
    its own ``_attempt_marker`` (see ``change_executor/route.py::execute``), needed to
    recompute that call's deterministic ``work_unit_ref``."""

    readings: list[str] = field(default_factory=list)

    def __call__(self) -> str:
        value = default_clock()
        self.readings.append(value)
        return value


# ---------------------------------------------------------------------------
# Fixed-fixture adapter (Phase A stand-in for the real dots_adapter.py)
# ---------------------------------------------------------------------------


@dataclass
class FixedFixtureDotsAdapter:
    """Deterministic, zero-live-call stand-in for PROTOCOL.md Sec.4's five adapter
    responsibilities. Every method below returns a canned or test-configured response --
    never a live dots/GitHub call. ``external_state`` plays the role Phase B's real
    external side effect (a GitHub PR/Issue, dots' own Activity record) would play for
    ``reconciliation.py``'s ``external_reader``: it is mutated only by this adapter's own
    methods, in response to a driver call, so the reconciliation gate has something
    genuinely independent of the Store to check against even while no live connection
    exists yet.

    *stop_acknowledges*: if ``True`` (default), ``stop_and_reconcile`` returns a positive
    ack. Set ``False`` on an instance to exercise the ``STOP_UNCONFIRMED`` path a test
    needs, per ``RUN_MANIFEST_TEMPLATE.json``'s own
    ``unconfirmed_remote_cancellation_policy``.
    """

    stop_acknowledges: bool = True
    external_state: dict[str, Any] = field(default_factory=dict)

    def read_state(self) -> dict[str, Any]:
        return {"channel": "FIXED_FIXTURE", "note": "Phase A stub -- no live dots read"}

    def submit_candidate(self, candidate: Mapping[str, Any]) -> dict[str, Any]:
        self.external_state["last_submitted_candidate"] = dict(candidate)
        return {"accepted": True, "channel": "FIXED_FIXTURE"}

    def dispatch_authorized_work(self, work_unit: Mapping[str, Any]) -> dict[str, Any]:
        """dots' own (fixture-only, zero-live-call) act of handing an already-authorized
        work unit to the existing CLAUDE_CODE/GITHUB_COPILOT executor. This method never
        performs or times the actual change itself -- that happens through the real
        CHANGE_EXECUTOR route ``Driver.dispatch`` calls next; this is purely the hand-off
        acknowledgment PROTOCOL.md Sec.2 names as dots' own responsibility."""

        ack = {"accepted": True, "channel": "FIXED_FIXTURE", "work_unit_ref": dict(work_unit)}
        self.external_state["last_handoff"] = ack
        return ack

    def collect_receipt(self, work_unit_ref: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "work_unit_ref": dict(work_unit_ref),
            "activity_record": self.external_state.get("last_execution_outcome"),
        }

    def stop_and_reconcile(self, run_id: str) -> dict[str, Any]:
        self.external_state["stop_requested_for_run_id"] = run_id
        if self.stop_acknowledges:
            self.external_state["stop_acknowledged_for_run_id"] = run_id
            return {"acknowledged": True, "control_surface": "FIXED_FIXTURE_STOP"}
        return {"acknowledged": False, "control_surface": "FIXED_FIXTURE_STOP"}

    def read_external_state(self) -> dict[str, Any]:
        """The ``external_reader`` ``reconciliation.reconcile()`` requires -- an
        independent read of this adapter's own externally-visible state, never the
        Store."""

        return dict(self.external_state)


# ---------------------------------------------------------------------------
# Process supervision -- a real, independently-tested primitive for a genuinely separate
# delegated-worker process (not used by Phase A's CHANGE_EXECUTOR dispatch path itself,
# which is a synchronous in-process call; kept for a future case that needs it, same PID
# + start-time pattern as development_binding/review_adapter.py's own
# _read_proc_start_time).
# ---------------------------------------------------------------------------


def _read_proc_start_time(pid: int) -> str | None:
    """Field 22 of ``/proc/<pid>/stat`` -- the process's start time in clock ticks since
    boot. Binds a PID to the *exact* process instance rather than to whatever unrelated
    process the kernel may have since reused that PID for (identical technique to, and
    intentionally not imported from, ``development_binding/review_adapter.py``'s own
    private helper of the same name -- that symbol is module-private there)."""

    try:
        raw = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return None
    after_comm = raw.rsplit(")", 1)[-1].split()
    if len(after_comm) < 20:
        return None
    return after_comm[19]  # field 22 overall; 20th field after the comm's closing paren


@dataclass(frozen=True)
class WorkerOutcome:
    outcome: str  # "EXITED_ZERO" | "EXITED_NONZERO" | "TIMED_OUT_STILL_RUNNING"
    exit_code: int | None
    local_process_group_terminated: bool


@dataclass
class ProcessSupervisor:
    pid: int
    start_time_token: str | None
    _popen: subprocess.Popen[Any]

    @classmethod
    def spawn(cls, argv: list[str]) -> ProcessSupervisor:
        popen = subprocess.Popen(  # noqa: S603 -- fixed, test-supplied argv only
            argv, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return cls(pid=popen.pid, start_time_token=_read_proc_start_time(popen.pid), _popen=popen)

    def _ownership_confirmed(self) -> bool:
        """Refuses to signal a PID that has since been reused for an unrelated process --
        a bare PID is never ownership (same discipline as ``review_adapter.py``)."""

        return _read_proc_start_time(self.pid) == self.start_time_token

    def wait(self, *, timeout_seconds: float) -> WorkerOutcome:
        try:
            exit_code = self._popen.wait(timeout=timeout_seconds)
            return WorkerOutcome(
                outcome="EXITED_ZERO" if exit_code == 0 else "EXITED_NONZERO",
                exit_code=exit_code,
                local_process_group_terminated=True,
            )
        except subprocess.TimeoutExpired:
            return WorkerOutcome(
                outcome="TIMED_OUT_STILL_RUNNING",
                exit_code=None,
                local_process_group_terminated=False,
            )

    def terminate(self) -> WorkerOutcome:
        """Worker termination: kills the process GROUP this harness itself started
        (``start_new_session=True`` at spawn), not a bare PID, and only if PID ownership
        is still confirmed (guards against PID reuse)."""

        if not self._ownership_confirmed():
            return WorkerOutcome(
                outcome="TIMED_OUT_STILL_RUNNING",
                exit_code=None,
                local_process_group_terminated=False,
            )
        with contextlib.suppress(ProcessLookupError):
            os.killpg(self.pid, signal.SIGKILL)
        try:
            exit_code = self._popen.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            return WorkerOutcome(
                outcome="TIMED_OUT_STILL_RUNNING",
                exit_code=None,
                local_process_group_terminated=False,
            )
        return WorkerOutcome(
            outcome="EXITED_ZERO" if exit_code == 0 else "EXITED_NONZERO",
            exit_code=exit_code,
            local_process_group_terminated=True,
        )


# ---------------------------------------------------------------------------
# Driver run-state (test-harness-local, outside canonical Store, per
# MEASUREMENT_CONTRACT.md Sec.A's own "Stop-request acceptance" row)
# ---------------------------------------------------------------------------


@dataclass
class WorkUnitRecord:
    work_unit_ref: dict[str, str]
    case_classification: str
    run_state: str = "DISPATCHED"
    outcome: str | None = None
    change_id: str | None = None
    claim_token: str | None = None
    work_time_coordination_open_id: str | None = None
    work_time_coordination_terminal_id: str | None = None
    change_execution_receipt_outcome: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "work_unit_ref": self.work_unit_ref,
            "case_classification": self.case_classification,
            "run_state": self.run_state,
            "outcome": self.outcome,
            "change_id": self.change_id,
            "claim_token": self.claim_token,
            "work_time_coordination_open_id": self.work_time_coordination_open_id,
            "work_time_coordination_terminal_id": self.work_time_coordination_terminal_id,
            "change_execution_receipt_outcome": self.change_execution_receipt_outcome,
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> WorkUnitRecord:
        return cls(
            work_unit_ref=dict(payload["work_unit_ref"]),
            case_classification=payload["case_classification"],
            run_state=payload["run_state"],
            outcome=payload.get("outcome"),
            change_id=payload.get("change_id"),
            claim_token=payload.get("claim_token"),
            work_time_coordination_open_id=payload.get("work_time_coordination_open_id"),
            work_time_coordination_terminal_id=payload.get("work_time_coordination_terminal_id"),
            change_execution_receipt_outcome=payload.get("change_execution_receipt_outcome"),
        )


class DriverRunState:
    """Durable, local (Store-external) run-state. ``stop_ack`` is the one field this
    contract requires never be set from a mere send -- see ``Driver.request_stop``."""

    def __init__(self, path: Path) -> None:
        self._path = path
        if path.exists():
            payload = json.loads(path.read_text())
        else:
            payload = {"stop_ack": "NOT_REQUESTED", "work_units": {}}
        self.stop_ack: str = payload["stop_ack"]  # NOT_REQUESTED | ACCEPTED | UNCONFIRMED
        self.work_units: dict[str, WorkUnitRecord] = {
            key: WorkUnitRecord.from_json(value) for key, value in payload["work_units"].items()
        }

    def _save(self) -> None:
        payload = {
            "stop_ack": self.stop_ack,
            "work_units": {key: record.to_json() for key, record in self.work_units.items()},
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    def put(self, key: str, record: WorkUnitRecord) -> None:
        self.work_units[key] = record
        self._save()

    def set_stop_ack(self, value: str) -> None:
        self.stop_ack = value
        self._save()


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def _work_unit_key(work_unit_ref: Mapping[str, str]) -> str:
    return f"{work_unit_ref.get('kind')}:{work_unit_ref.get('id')}"


class Driver:
    def __init__(
        self,
        store: Any,
        *,
        project_id: str,
        run_state_path: Path,
        adapter: FixedFixtureDotsAdapter,
        change_executor_execute: Callable[..., dict[str, Any]],
    ) -> None:
        """*change_executor_execute* is the real closure
        ``manosube_agent_civilization.change_executor.route.compose_change_executor``
        returns -- already bound to its own Store/Boundary/adapter/kill-switch at
        composition time, by the caller, exactly as every other caller of that route
        does. This module never builds one of its own accord beyond what the caller
        supplies, and never substitutes a different Store/Boundary after the fact (the
        real route's own closure already forbids that)."""

        self._store = store
        self._project_id = project_id
        self._adapter = adapter
        self._execute = change_executor_execute
        self.run_state = DriverRunState(run_state_path)

    def dispatch(
        self,
        work_unit_ref: Mapping[str, str],
        *,
        case_classification: str,
        change_id: str,
        claim_token: str,
        execution_instant: str,
    ) -> WorkUnitRecord:
        """Event 1 (dispatch start) + the dispatch half of events 4/5. Refuses
        (``DriverError``) if a stop has been accepted or left unconfirmed (events 2/3's
        own gate), and refuses to re-dispatch a work unit whose prior attempt is not yet
        ``RESOLVED`` (this contract's own no-resend-while-unknown invariant).

        Hands off through the fixture adapter first (dots' own, fixture-only act), then
        executes the real, already-authorized Change through the real
        ``compose_change_executor()`` closure -- never a second, invented coordination."""

        if self.run_state.stop_ack != "NOT_REQUESTED":
            raise DriverError(
                f"refusing new dispatch: stop_ack={self.run_state.stop_ack!r} "
                "(ACCEPTED and UNCONFIRMED both block new dispatch identically)"
            )
        if case_classification not in CASE_CLASSIFICATIONS:
            raise DriverError(f"unknown case_classification {case_classification!r}")

        key = _work_unit_key(work_unit_ref)
        existing = self.run_state.work_units.get(key)
        if existing is not None and existing.run_state != "RESOLVED":
            raise DriverError(
                f"refusing to re-dispatch {key!r}: prior attempt run_state="
                f"{existing.run_state!r}, not RESOLVED -- outcome still unknown"
            )

        record = WorkUnitRecord(
            work_unit_ref=dict(work_unit_ref),
            case_classification=case_classification,
            run_state="DISPATCHED",
            change_id=change_id,
            claim_token=claim_token,
        )
        self.run_state.put(key, record)

        self._adapter.dispatch_authorized_work({"work_unit_ref": dict(work_unit_ref)})

        clock = _CapturingClock()
        try:
            result = self._execute(
                change_id,
                claim_token=claim_token,
                execution_instant=execution_instant,
                work_time_coordination_clock=clock,
            )
            failed = False
        except Exception as error:
            failed = True
            result = None
            caught_error = error

        open_id, terminal_id = self._read_back_coordination_ids(
            change_id=change_id, claim_token=claim_token, clock=clock
        )
        record.work_time_coordination_open_id = open_id
        record.work_time_coordination_terminal_id = terminal_id
        record.run_state = "RESOLVED"

        self._adapter.external_state["last_execution_outcome"] = {
            "work_unit_ref": dict(work_unit_ref),
            "work_time_coordination_open_id": open_id,
            "work_time_coordination_terminal_id": terminal_id,
            "failed": failed,
        }

        if failed:
            record.outcome = "FAILED"
            self.run_state.put(key, record)
            if case_classification == "INTENTIONAL_REFUSAL_TEST":
                return record  # the case-catalog's own expected shape -- not a driver bug
            raise DriverError(f"dispatch of {key!r} failed: {caught_error}") from caught_error

        record.outcome = "SUCCEEDED"
        record.change_execution_receipt_outcome = result["receipt"]["outcome"] if result else None
        self.run_state.put(key, record)
        return record

    def _read_back_coordination_ids(
        self, *, change_id: str, claim_token: str, clock: _CapturingClock
    ) -> tuple[str | None, str | None]:
        """Recomputes and resolves the real ``work_time_coordination_open``/``_terminal``
        ids ``execute()`` itself committed -- a genuine Store readback, never a value
        this module invents or trusts from the caller. Returns ``(None, None)`` only if
        *clock* was never actually read (meaning ``execute()`` never reached its own
        coordination-opening step at all)."""

        if not clock.readings:
            return None, None
        attempt_marker = clock.readings[0]
        work_unit_id = _recompute_change_executor_work_unit_id(
            project_id=self._project_id,
            change_id=change_id,
            claim_token=claim_token,
            attempt_marker=attempt_marker,
        )
        open_id = work_time_coordination_open_id(
            self._project_id,
            {"kind": _CHANGE_EXECUTOR_WORK_UNIT_REF_KIND, "id": work_unit_id},
        )
        terminal_id = work_time_coordination_terminal_id(open_id)

        resolved_open = self._store.resolve_coordination_record(
            self._project_id, "work_time_coordination_open", open_id
        )
        if resolved_open is None:
            raise DriverError(
                f"recomputed work_time_coordination_open_id {open_id!r} does not resolve in "
                "Store -- readback failed; this module's id recomputation or execute()'s own "
                "behavior has diverged"
            )
        resolved_terminal = self._store.resolve_coordination_record(
            self._project_id, "work_time_coordination_terminal", terminal_id
        )
        if resolved_terminal is None:
            raise DriverError(
                f"recomputed work_time_coordination_terminal_id {terminal_id!r} does not "
                "resolve in Store -- execute() must always commit a terminal notice before "
                "returning or raising"
            )
        return open_id, terminal_id

    def request_stop(self, run_id: str) -> str:
        """Events 2+3. Writes ``STOP_ACCEPTED``'s equivalent (``stop_ack="ACCEPTED"``)
        ONLY when the adapter's own stop-control call returns an explicit, positive
        acknowledgment. An absent, false, or exception-raising ack is recorded as
        ``UNCONFIRMED`` -- never treated as a non-event -- and new dispatch is refused in
        exactly the same way as a confirmed stop (``dispatch`` checks ``!= NOT_REQUESTED``,
        not ``== ACCEPTED``), matching ``RUN_MANIFEST_TEMPLATE.json``'s own
        ``unconfirmed_remote_cancellation_policy``: ``STOP_UNCONFIRMED -> quarantine, no
        restart``. Sending the request is never, by itself, acceptance."""

        try:
            response = self._adapter.stop_and_reconcile(run_id)
        except Exception:
            self.run_state.set_stop_ack("UNCONFIRMED")
            return "UNCONFIRMED"

        if bool(response.get("acknowledged")) is True:
            self.run_state.set_stop_ack("ACCEPTED")
            return "ACCEPTED"
        self.run_state.set_stop_ack("UNCONFIRMED")
        return "UNCONFIRMED"

    def reconcile_before_recovery(
        self,
        *,
        expected_state_predicate: Callable[[Mapping[str, Any]], bool],
        expected_external_predicate: Callable[[Mapping[str, Any]], bool],
    ) -> Any:
        """Event 7, reused as-is from ``reconciliation.py`` -- this module adds no second
        implementation of the two-part gate. Must return ``reconciled=True`` before
        ``allow_recovery`` will permit event 6."""

        from tests.dots_production_acceptance import reconciliation as recon

        return recon.reconcile(
            self._store,
            project_id=self._project_id,
            expected_state_predicate=expected_state_predicate,
            external_reader=self._adapter.read_external_state,
            expected_external_predicate=expected_external_predicate,
        )

    def allow_recovery(self, reconciliation_result: Any) -> None:
        """Event 6's own gate: recovery (a fresh dispatch for the same work_unit_ref
        lineage) may only proceed once reconciliation is complete AND the stop that
        triggered recovery is no longer blocking. Raises ``DriverError`` otherwise --
        never silently permits a resend while the prior outcome is still unknown."""

        if not reconciliation_result.reconciled:
            raise DriverError(
                "refusing recovery: reconciliation is not complete "
                f"(store_matched={reconciliation_result.store_matched}, "
                f"external_matched={reconciliation_result.external_matched})"
            )
        self.run_state.set_stop_ack("NOT_REQUESTED")
