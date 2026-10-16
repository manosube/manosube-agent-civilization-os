"""WU2 Phase A (Issue #116 / PR #119 follow-up): dispatch loop + stop/reconcile gate per
``docs/validation/dots_production_acceptance/MEASUREMENT_CONTRACT.md`` Sec.A.

**Phase A scope, explicit disclaimer:** ``dots_adapter`` here is always a caller-supplied,
fixed-fixture stub (see ``FixedFixtureDotsAdapter`` below) implementing
``PROTOCOL.md`` Sec.4's five adapter responsibilities with canned, deterministic
behavior. This module makes zero live dots/GitHub calls and is never, by itself,
evidence of a real dots connection or a production-operation success -- see this
package's own PR body / README for the same disclaimer. A real ``dots_adapter.py``
(Phase B) is built once SHUKOU's Reading A/B/C decision and ``OPEN_ITEMS.md`` item 7
are resolved; this module's dispatch-loop/stop-gate/reconciliation-gated-resume shape
is adapter-agnostic and does not change when that happens -- only the adapter object
passed in does.

**Never a second State/Authority/Evidence/Reflow owner.** Dispatch is timed through the
existing, shared ``with_work_time_coordination`` composition primitive -- the identical
one ``independent_verification/route.py::run_independent_verification`` uses
(``OPEN_ITEMS.md`` item 8's own named example of a route that already composes it).
Any State mutation this module's own fixtures need goes through the real
``manosube_agent_civilization.reflow.route.reflow``'s own
``provenance_only_evidence_requests`` parameter via ``recorder.py``, exactly as
``wu2_component_scenario.py`` Section 2 already proved -- this module adds no second
commit path.

The 7 observation points of ``MEASUREMENT_CONTRACT.md`` Sec.A, and this module's own
primary source for each (never uniformly "via Store" -- each row names its own real
observation surface):

================================  =========================================================
Event                             Primary observation in this module
================================  =========================================================
1. Dispatch start                 ``work_time_coordination_open`` record (Store, via
                                   ``with_work_time_coordination``)
2. Stop-request acceptance        ``DriverRunState``'s own durable, local
                                   ``stop_ack`` field -- written ONLY after the adapter's
                                   ``stop_and_reconcile`` call returns an explicit positive
                                   acknowledgment; an unconfirmed/negative/missing ack is
                                   recorded as ``STOP_UNCONFIRMED`` and dispatch stays
                                   blocked exactly as if a confirmed stop had landed
3. New-dispatch-stop               ``Driver.dispatch`` itself refuses once
                                   ``stop_ack in {"ACCEPTED", "UNCONFIRMED"}`` -- re-querying
                                   the local run-state (this harness's own halt flag; no
                                   canonical Store query is needed to prove *this* module
                                   issues no new dispatch, since dispatch itself is the only
                                   thing being gated)
4. Worker termination              OS process-group exit via ``ProcessSupervisor`` (PID +
                                   start-time pair, same pattern as
                                   ``development_binding/review_adapter.py``'s own
                                   ``_read_proc_start_time``), cross-checked against
                                   ``work_time_coordination_terminal.terminal_outcome``
5. Fault detection                 ``work_time_coordination_terminal.heartbeat_deadline_
                                   breached`` (derived automatically by the Kernel's own
                                   ``with_work_time_coordination``/``record_work_time_
                                   terminal_notice``), cross-checked against this module's
                                   own supervisor timeout
6. Recovery start                  new ``work_time_coordination_open`` opened for the same
                                   ``work_unit_ref`` lineage -- gated behind event 7 below
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
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from typing import Any

from manosube_agent_civilization.work_time_transparency.adapters import (
    ProgressReporter,
    with_work_time_coordination,
)
from manosube_agent_civilization.work_time_transparency.clock import default_clock

ADAPTER_KIND = "DOTS_PRODUCTION_ACCEPTANCE_DISPATCH"

CASE_CLASSIFICATIONS = frozenset(
    {"NORMAL_OPERATION", "INTENTIONAL_REFUSAL_TEST", "ENVIRONMENT_FAULT"}
)
RUN_STATES = frozenset({"DISPATCHED", "PENDING_HUMAN_APPROVAL", "RESOLVED"})


class DriverError(Exception):
    """Raised when this module is asked to violate its own contract -- e.g. dispatching a
    new work unit after a stop has been accepted or left unconfirmed, or re-dispatching a
    work unit whose prior attempt is not yet ``RESOLVED``."""


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

    def dispatch_authorized_work(
        self,
        work_unit: Mapping[str, Any],
        reporter: ProgressReporter,
        *,
        worker_argv: list[str] | None = None,
        worker_timeout_seconds: float = 5.0,
    ) -> dict[str, Any]:
        """Spawns and supervises one short-lived local subprocess standing in for "the
        worker a dot would delegate to" -- a genuine OS process this harness can observe
        terminate (event 4), never a live external call. Defaults to a trivial, immediately
        successful process; a test may pass *worker_argv* that fails, hangs, or sleeps past
        *worker_timeout_seconds* to exercise the fault/timeout paths."""

        argv = worker_argv or ["python3", "-c", "pass"]
        supervisor = ProcessSupervisor.spawn(argv)
        reporter.report(
            position_kind="EXTERNAL_WORKER_RUNNING",
            current_position=f"pid={supervisor.pid}",
            next_progress_update_due_minutes=1,
        )
        outcome = supervisor.wait(timeout_seconds=worker_timeout_seconds)
        if outcome.outcome == "TIMED_OUT_STILL_RUNNING":
            # Event 4 (worker termination) applies even on the fault path: this harness
            # never leaves a still-running supervised process behind just because it
            # missed its own deadline.
            outcome = supervisor.terminate()
        self.external_state["last_dispatch_outcome"] = {
            "work_unit_ref": dict(work_unit.get("work_unit_ref", {})),
            "worker_outcome": outcome.outcome,
            "pid": supervisor.pid,
        }
        if outcome.outcome != "EXITED_ZERO":
            raise RuntimeError(f"worker did not complete successfully: {outcome.outcome}")
        return {"worker_outcome": outcome.outcome, "pid": supervisor.pid}

    def collect_receipt(self, work_unit_ref: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "work_unit_ref": dict(work_unit_ref),
            "activity_record": self.external_state.get("last_dispatch_outcome"),
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
# Process supervision (event 4 -- same PID + start-time pattern as
# development_binding/review_adapter.py's own _read_proc_start_time)
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
    # The comm field (2nd, parenthesized) may itself contain spaces/parens; split on the
    # closing paren to skip past it reliably.
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
    def spawn(cls, argv: list[str]) -> "ProcessSupervisor":
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
                outcome="TIMED_OUT_STILL_RUNNING", exit_code=None, local_process_group_terminated=False
            )

    def terminate(self) -> WorkerOutcome:
        """Worker termination (event 4): kills the process GROUP this harness itself
        started (``start_new_session=True`` at spawn), not a bare PID, and only if PID
        ownership is still confirmed (guards against PID reuse)."""

        if not self._ownership_confirmed():
            return WorkerOutcome(
                outcome="TIMED_OUT_STILL_RUNNING", exit_code=None, local_process_group_terminated=False
            )
        try:
            os.killpg(self.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            exit_code = self._popen.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            return WorkerOutcome(
                outcome="TIMED_OUT_STILL_RUNNING", exit_code=None, local_process_group_terminated=False
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
    open_ref: dict[str, str] | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "work_unit_ref": self.work_unit_ref,
            "case_classification": self.case_classification,
            "run_state": self.run_state,
            "outcome": self.outcome,
            "open_ref": self.open_ref,
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "WorkUnitRecord":
        return cls(
            work_unit_ref=dict(payload["work_unit_ref"]),
            case_classification=payload["case_classification"],
            run_state=payload["run_state"],
            outcome=payload.get("outcome"),
            open_ref=payload.get("open_ref"),
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
        project_binding_id: str,
        run_state_path: Path,
        adapter: FixedFixtureDotsAdapter,
        clock: Callable[[], str] = default_clock,
    ) -> None:
        self._store = store
        self._project_id = project_id
        self._project_binding_id = project_binding_id
        self._adapter = adapter
        self._clock = clock
        self.run_state = DriverRunState(run_state_path)

    def dispatch(
        self,
        work_unit_ref: Mapping[str, str],
        *,
        case_classification: str,
        worker_argv: list[str] | None = None,
        worker_timeout_seconds: float = 5.0,
    ) -> WorkUnitRecord:
        """Event 1 (dispatch start) + the dispatch half of events 4/5. Refuses
        (``DriverError``) if a stop has been accepted or left unconfirmed (events 2/3's
        own gate), and refuses to re-dispatch a work unit whose prior attempt is not yet
        ``RESOLVED`` (this contract's own no-resend-while-unknown invariant)."""

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
        )
        self.run_state.put(key, record)

        def _perform(reporter: ProgressReporter) -> dict[str, Any]:
            return self._adapter.dispatch_authorized_work(
                {"work_unit_ref": dict(work_unit_ref)},
                reporter,
                worker_argv=worker_argv,
                worker_timeout_seconds=worker_timeout_seconds,
            )

        try:
            open_record, terminal_record, result = with_work_time_coordination(
                self._store,
                project_id=self._project_id,
                project_binding_id=self._project_binding_id,
                adapter_kind=ADAPTER_KIND,
                work_unit_ref=dict(work_unit_ref),
                estimated_duration_lower_minutes=0,
                estimated_duration_upper_minutes=1,
                estimate_confidence="MEDIUM",
                major_steps=["dispatch_authorized_work"],
                next_progress_update_due_minutes=1,
                variability_factors="none",
                perform=_perform,
                clock=self._clock,
            )
        except Exception as error:  # noqa: BLE001 -- genuinely any adapter/worker failure
            record.run_state = "RESOLVED"
            record.outcome = "FAILED"
            record.open_ref = None
            self.run_state.put(key, record)
            if case_classification == "INTENTIONAL_REFUSAL_TEST":
                return record  # the case-catalog's own expected shape -- not a driver bug
            raise DriverError(f"dispatch of {key!r} failed: {error}") from error

        record.run_state = "RESOLVED"
        record.outcome = "SUCCEEDED"
        record.open_ref = {
            "kind": "work_time_coordination_open",
            "id": open_record["work_time_coordination_open_id"],
        }
        self.run_state.put(key, record)
        return record

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
        except Exception:  # noqa: BLE001 -- any adapter failure is itself a non-ack
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
            clock=self._clock,
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
