"""Contract tests for driver.py -- WU2 Phase A's dispatch loop + stop/reconcile gate.

Tracks #116 (WU2 Phase A). The real-dispatch tests exercise the genuine, unmodified
``compose_change_executor()`` entrypoint (``tests.fixtures.change_executor_world``'s own
proven world -- the identical fixtures ``tests/integration/change_executor/`` itself
uses), a real git worktree, and a real ``ControlledFilesystemAdapter`` (via
``CountingAdapter``) that performs a genuine file write -- never a no-op standing in for
success. The only Phase A stand-in is ``FixedFixtureDotsAdapter`` itself (dots' own
hand-off act, out of this environment's reach). Zero live dots/GitHub call anywhere.
"""

from __future__ import annotations

from pathlib import Path
import time

import pytest
from tests.dots_production_acceptance import reconciliation as recon
from tests.dots_production_acceptance.driver import (
    Driver,
    DriverError,
    FixedFixtureDotsAdapter,
    ProcessSupervisor,
    WorkUnitRecord,
    _read_proc_start_time,
)
from tests.fixtures.change_executor_kill_switch_issuer import issuer_public_key_hex
from tests.fixtures.change_executor_world import (
    CountingAdapter,
    bound,
    build_committed_change,
    commit_active_kill_switch,
    execution_boundary_for,
    git_worktree,
    operation_for,
)

from manosube_agent_civilization.change_executor.route import compose_change_executor

WORK_UNIT = {"kind": "dots_production_acceptance_work_unit", "id": "WU-TEST-0001"}


def _real_world(tmp_path: Path, *, path: str = "docs/target.md") -> dict:
    store, info = bound(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    built = build_committed_change(
        store,
        info["project_id"],
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE",
            writes=[{"path": path, "content_utf8": "hello from WU2 Phase A"}],
        ),
        paths=[path],
    )
    worktree = git_worktree(tmp_path)
    adapter = CountingAdapter()
    execute = compose_change_executor(
        store,
        project_id=info["project_id"],
        project_binding_id=info["project_binding_id"],
        execution_boundary=execution_boundary_for(worktree_root=str(worktree)),
        adapter_identity={"kind": "controlled_filesystem_adapter", "version": "0.1"},
        adapter=adapter,
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )
    return {
        "store": store,
        "info": info,
        "change": built["change"],
        "worktree": worktree,
        "adapter": adapter,
        "execute": execute,
        "path": path,
    }


def _make_driver(
    tmp_path: Path, world: dict, *, adapter: FixedFixtureDotsAdapter | None = None
) -> Driver:
    return Driver(
        world["store"],
        project_id=world["info"]["project_id"],
        run_state_path=tmp_path / "run_state.json",
        adapter=adapter or FixedFixtureDotsAdapter(),
        change_executor_execute=world["execute"],
    )


class _RaisingAdapter:
    """An adapter whose ``execute()`` always raises -- ``change_executor/route.py``'s own
    documented mechanism (module docstring item 13) for converting an adapter failure
    into a terminal UNKNOWN receipt rather than letting the raw exception propagate out
    of ``execute()``. Used below to reproduce PR #121 review finding F-Driver-1 against
    the real, unmodified CHANGE_EXECUTOR route."""

    def execute(self, operation: object, *, worktree_root: str) -> object:
        raise RuntimeError("simulated adapter crash")


def test_dispatch_executes_the_real_change_and_reads_back_real_coordination_records(
    tmp_path: Path,
) -> None:
    world = _real_world(tmp_path)
    driver = _make_driver(tmp_path, world)

    record = driver.dispatch(
        WORK_UNIT,
        case_classification="NORMAL_OPERATION",
        change_id=world["change"]["change_id"],
        claim_token="claim-wu2-phase-a",  # noqa: S106
        execution_instant="2026-09-10T00:00:01Z",
    )

    assert record.run_state == "RESOLVED"
    assert record.outcome == "SUCCEEDED"
    assert record.change_execution_receipt_outcome == "SUCCEEDED"
    assert record.work_time_coordination_open_id is not None
    assert record.work_time_coordination_terminal_id is not None

    # Genuine Store readback -- never trusted from the driver's own in-memory claim.
    open_record = world["store"].resolve_coordination_record(
        world["info"]["project_id"],
        "work_time_coordination_open",
        record.work_time_coordination_open_id,
    )
    assert open_record["adapter_kind"] == "CHANGE_EXECUTOR"
    assert open_record["work_unit_ref"]["kind"] == "change_executor_execution"

    terminal_record = world["store"].resolve_coordination_record(
        world["info"]["project_id"],
        "work_time_coordination_terminal",
        record.work_time_coordination_terminal_id,
    )
    assert terminal_record["terminal_outcome"] == "COMPLETED"

    # Genuine readback of the actual change -- not a no-op standing in for success.
    written_path = world["worktree"] / world["path"]
    assert written_path.exists()
    assert written_path.read_text() == "hello from WU2 Phase A"

    assert world["adapter"].call_count == 1  # the one real adapter.execute call


def test_intentional_refusal_test_failure_is_recorded_not_raised(tmp_path: Path) -> None:
    world = _real_world(tmp_path)
    driver = _make_driver(tmp_path, world)

    record = driver.dispatch(
        WORK_UNIT,
        case_classification="INTENTIONAL_REFUSAL_TEST",
        change_id="CHANGE-DOES-NOT-EXIST-0000000000000000000000000000000000000000000000000000",
        claim_token="claim-refused",  # noqa: S106
        execution_instant="2026-09-10T00:00:01Z",
    )

    assert record.run_state == "RESOLVED"
    assert record.outcome == "FAILED"
    assert world["adapter"].call_count == 0  # refused before the real adapter was ever reached


def test_normal_operation_failure_raises_rather_than_silently_recording(tmp_path: Path) -> None:
    world = _real_world(tmp_path)
    driver = _make_driver(tmp_path, world)

    with pytest.raises(DriverError, match=r"dispatch of .* failed"):
        driver.dispatch(
            WORK_UNIT,
            case_classification="NORMAL_OPERATION",
            change_id="CHANGE-DOES-NOT-EXIST-0000000000000000000000000000000000000000000000000000",
            claim_token="claim-refused-2",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
        )
    key = f"{WORK_UNIT['kind']}:{WORK_UNIT['id']}"
    assert driver.run_state.work_units[key].outcome == "FAILED"
    assert driver.run_state.work_units[key].run_state == "RESOLVED"


def test_redispatch_blocked_while_prior_attempt_unresolved(tmp_path: Path) -> None:
    world = _real_world(tmp_path)
    driver = _make_driver(tmp_path, world)
    key = f"{WORK_UNIT['kind']}:{WORK_UNIT['id']}"

    driver.run_state.put(
        key,
        WorkUnitRecord(
            work_unit_ref=dict(WORK_UNIT),
            case_classification="NORMAL_OPERATION",
            run_state="DISPATCHED",
        ),
    )
    with pytest.raises(DriverError, match="not RESOLVED"):
        driver.dispatch(
            WORK_UNIT,
            case_classification="NORMAL_OPERATION",
            change_id=world["change"]["change_id"],
            claim_token="claim-should-not-run",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
        )
    assert world["adapter"].call_count == 0


def test_stop_accepted_only_on_explicit_positive_ack_and_then_blocks_dispatch(
    tmp_path: Path,
) -> None:
    world = _real_world(tmp_path)
    driver = _make_driver(tmp_path, world, adapter=FixedFixtureDotsAdapter(stop_acknowledges=True))

    assert driver.request_stop("RUN-1") == "ACCEPTED"
    assert driver.run_state.stop_ack == "ACCEPTED"
    with pytest.raises(DriverError, match="refusing new dispatch"):
        driver.dispatch(
            {"kind": "x", "id": "y"},
            case_classification="NORMAL_OPERATION",
            change_id=world["change"]["change_id"],
            claim_token="claim-blocked",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
        )


def test_unconfirmed_stop_blocks_dispatch_exactly_like_an_accepted_one(tmp_path: Path) -> None:
    world = _real_world(tmp_path)
    driver = _make_driver(tmp_path, world, adapter=FixedFixtureDotsAdapter(stop_acknowledges=False))

    assert driver.request_stop("RUN-1") == "UNCONFIRMED"
    assert driver.run_state.stop_ack == "UNCONFIRMED"
    with pytest.raises(DriverError, match="refusing new dispatch"):
        driver.dispatch(
            {"kind": "x", "id": "y"},
            case_classification="NORMAL_OPERATION",
            change_id=world["change"]["change_id"],
            claim_token="claim-blocked-2",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
        )


def test_recovery_refused_until_reconciliation_completes_then_unblocks_dispatch(
    tmp_path: Path,
) -> None:
    world = _real_world(tmp_path)
    driver = _make_driver(tmp_path, world)
    driver.request_stop("RUN-1")
    assert driver.run_state.stop_ack == "ACCEPTED"

    incomplete = driver.reconcile_before_recovery(
        expected_state_predicate=lambda s: True,
        expected_external_predicate=lambda ext: ext.get("nonexistent_key") == "never",
    )
    assert incomplete.reconciled is False
    with pytest.raises(DriverError, match="refusing recovery"):
        driver.allow_recovery(incomplete)
    assert driver.run_state.stop_ack == "ACCEPTED"

    complete = driver.reconcile_before_recovery(
        expected_state_predicate=lambda s: True,
        expected_external_predicate=lambda ext: ext.get("stop_acknowledged_for_run_id") == "RUN-1",
    )
    assert complete.reconciled is True
    driver.allow_recovery(complete)
    assert driver.run_state.stop_ack == "NOT_REQUESTED"

    record = driver.dispatch(
        {"kind": "x", "id": "y"},
        case_classification="NORMAL_OPERATION",
        change_id=world["change"]["change_id"],
        claim_token="claim-recovered",  # noqa: S106
        execution_instant="2026-09-10T00:00:02Z",
    )
    assert record.outcome == "SUCCEEDED"


def test_reconcile_before_recovery_reuses_the_existing_reconciliation_module(
    tmp_path: Path,
) -> None:
    world = _real_world(tmp_path)
    driver = _make_driver(tmp_path, world)
    result = driver.reconcile_before_recovery(
        expected_state_predicate=lambda s: True,
        expected_external_predicate=lambda ext: True,
    )
    assert isinstance(result, recon.ReconciliationResult)


# --- Regressions for PR #121's independent review ---------------------------------


def test_dispatch_with_real_unknown_receipt_outcome_is_never_recorded_as_succeeded(
    tmp_path: Path,
) -> None:
    """F-Driver-1: a real CHANGE_EXECUTOR receipt whose own ``outcome`` is ``UNKNOWN``
    (route.py's own documented conversion of an adapter crash into a terminal UNKNOWN
    receipt, never a bare raised exception) must never be reported
    ``run_state="RESOLVED"``/``outcome="SUCCEEDED"`` merely because ``execute()`` itself
    returned without raising, and the same work unit must stay blocked from a further
    dispatch until reconciled."""

    store, info = bound(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    path = "docs/target.md"
    built = build_committed_change(
        store,
        info["project_id"],
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE", writes=[{"path": path, "content_utf8": "unused"}]
        ),
        paths=[path],
    )
    worktree = git_worktree(tmp_path)
    execute = compose_change_executor(
        store,
        project_id=info["project_id"],
        project_binding_id=info["project_binding_id"],
        execution_boundary=execution_boundary_for(worktree_root=str(worktree)),
        adapter_identity={"kind": "controlled_filesystem_adapter", "version": "0.1"},
        adapter=_RaisingAdapter(),
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )
    driver = Driver(
        store,
        project_id=info["project_id"],
        run_state_path=tmp_path / "run_state.json",
        adapter=FixedFixtureDotsAdapter(),
        change_executor_execute=execute,
    )

    with pytest.raises(DriverError, match="UNKNOWN"):
        driver.dispatch(
            WORK_UNIT,
            case_classification="NORMAL_OPERATION",
            change_id=built["change"]["change_id"],
            claim_token="claim-unknown-1",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
        )

    key = f"{WORK_UNIT['kind']}:{WORK_UNIT['id']}"
    record = driver.run_state.work_units[key]
    assert record.run_state != "RESOLVED"
    assert record.change_execution_receipt_outcome == "UNKNOWN"

    # The exact bug reproduced: a second dispatch for the same work unit must still be
    # refused -- never resent while the prior outcome is unknown.
    with pytest.raises(DriverError, match="not RESOLVED"):
        driver.dispatch(
            WORK_UNIT,
            case_classification="NORMAL_OPERATION",
            change_id=built["change"]["change_id"],
            claim_token="claim-unknown-2",  # noqa: S106
            execution_instant="2026-09-10T00:00:02Z",
        )


def test_allow_recovery_resolves_the_specific_stuck_work_unit_and_unblocks_its_redispatch(
    tmp_path: Path,
) -> None:
    """F-Driver-2: the pre-existing recovery test used a different work_unit_ref for its
    post-recovery dispatch and so never noticed that ``allow_recovery()`` left the
    original stuck record at ``run_state="DISPATCHED"`` forever. This test uses the SAME
    work_unit_ref throughout, as the real stuck-and-resumed scenario would."""

    world = _real_world(tmp_path)
    driver = _make_driver(tmp_path, world)
    key = f"{WORK_UNIT['kind']}:{WORK_UNIT['id']}"

    # Simulate a crash/stop-interrupted attempt: a record stuck at DISPATCHED, exactly as
    # a real dispatch() call would leave behind if the process died mid-attempt.
    driver.run_state.put(
        key,
        WorkUnitRecord(
            work_unit_ref=dict(WORK_UNIT),
            case_classification="NORMAL_OPERATION",
            run_state="DISPATCHED",
        ),
    )

    with pytest.raises(DriverError, match="not RESOLVED"):
        driver.dispatch(
            WORK_UNIT,
            case_classification="NORMAL_OPERATION",
            change_id=world["change"]["change_id"],
            claim_token="claim-should-not-run",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
        )

    driver.request_stop("RUN-RECOVERY-1")
    result = driver.reconcile_before_recovery(
        expected_state_predicate=lambda s: True,
        expected_external_predicate=lambda ext: (
            ext.get("stop_acknowledged_for_run_id") == "RUN-RECOVERY-1"
        ),
    )
    assert result.reconciled is True

    resolved = driver.allow_recovery(result, WORK_UNIT, resolved_outcome="SUCCEEDED")
    assert resolved is not None
    assert resolved.run_state == "RESOLVED"
    assert resolved.outcome == "SUCCEEDED"
    assert driver.run_state.work_units[key].run_state == "RESOLVED"

    # The exact bug reproduced: a fresh dispatch for the SAME work unit is now permitted.
    record = driver.dispatch(
        WORK_UNIT,
        case_classification="NORMAL_OPERATION",
        change_id=world["change"]["change_id"],
        claim_token="claim-after-recovery",  # noqa: S106
        execution_instant="2026-09-10T00:00:02Z",
    )
    assert record.outcome == "SUCCEEDED"


def test_allow_recovery_requires_resolved_outcome_when_work_unit_ref_given(
    tmp_path: Path,
) -> None:
    world = _real_world(tmp_path)
    driver = _make_driver(tmp_path, world)
    driver.run_state.put(
        f"{WORK_UNIT['kind']}:{WORK_UNIT['id']}",
        WorkUnitRecord(
            work_unit_ref=dict(WORK_UNIT),
            case_classification="NORMAL_OPERATION",
            run_state="DISPATCHED",
        ),
    )
    reconciled = driver.reconcile_before_recovery(
        expected_state_predicate=lambda s: True,
        expected_external_predicate=lambda ext: True,
    )
    with pytest.raises(DriverError, match="resolved_outcome"):
        driver.allow_recovery(reconciled, WORK_UNIT)


def test_allow_recovery_refuses_to_resolve_a_stuck_work_unit_to_unknown(
    tmp_path: Path,
) -> None:
    """F-Driver-3: allow_recovery() must never resolve a stuck work unit to UNKNOWN (or
    any other undefined value) -- reproduced against the real CHANGE_EXECUTOR: a receipt
    outcome of UNKNOWN is correctly refused by dispatch()'s own re-dispatch guard, but a
    prior revision of allow_recovery() still accepted resolved_outcome="UNKNOWN" and set
    run_state="RESOLVED", after which the next dispatch for the same work unit proceeded
    -- a resend while the real outcome was still unknown."""

    store, info = bound(tmp_path)
    commit_active_kill_switch(store, info["project_id"])
    path = "docs/target.md"
    built = build_committed_change(
        store,
        info["project_id"],
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE", writes=[{"path": path, "content_utf8": "unused"}]
        ),
        paths=[path],
    )
    worktree = git_worktree(tmp_path)
    execute = compose_change_executor(
        store,
        project_id=info["project_id"],
        project_binding_id=info["project_binding_id"],
        execution_boundary=execution_boundary_for(worktree_root=str(worktree)),
        adapter_identity={"kind": "controlled_filesystem_adapter", "version": "0.1"},
        adapter=_RaisingAdapter(),
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )
    driver = Driver(
        store,
        project_id=info["project_id"],
        run_state_path=tmp_path / "run_state.json",
        adapter=FixedFixtureDotsAdapter(),
        change_executor_execute=execute,
    )
    key = f"{WORK_UNIT['kind']}:{WORK_UNIT['id']}"

    with pytest.raises(DriverError, match="UNKNOWN"):
        driver.dispatch(
            WORK_UNIT,
            case_classification="NORMAL_OPERATION",
            change_id=built["change"]["change_id"],
            claim_token="claim-unknown-recovery-1",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
        )
    assert driver.run_state.work_units[key].change_execution_receipt_outcome == "UNKNOWN"

    reconciled = driver.reconcile_before_recovery(
        expected_state_predicate=lambda s: True,
        expected_external_predicate=lambda ext: True,
    )
    assert reconciled.reconciled is True

    # The exact bug reproduced: resolving to UNKNOWN must be refused outright.
    with pytest.raises(DriverError, match="not a definite"):
        driver.allow_recovery(reconciled, WORK_UNIT, resolved_outcome="UNKNOWN")
    assert driver.run_state.work_units[key].run_state != "RESOLVED"

    # And the work unit must still be blocked from a fresh dispatch.
    with pytest.raises(DriverError, match="not RESOLVED"):
        driver.dispatch(
            WORK_UNIT,
            case_classification="NORMAL_OPERATION",
            change_id=built["change"]["change_id"],
            claim_token="claim-unknown-recovery-2",  # noqa: S106
            execution_instant="2026-09-10T00:00:02Z",
        )


# --- ProcessSupervisor (a real, independently-tested primitive) -----------------------


def test_process_supervisor_wait_observes_real_exit_code() -> None:
    supervisor = ProcessSupervisor.spawn(["python3", "-c", "import sys; sys.exit(3)"])
    try:
        outcome = supervisor.wait(timeout_seconds=5.0)
        assert outcome.outcome == "EXITED_NONZERO"
        assert outcome.exit_code == 3
        assert outcome.local_process_group_terminated is True
    finally:
        # Reap unconditionally, even if an assert above failed -- an un-reaped child
        # here is exactly the kind of leak that cascaded into a later test's failure
        # (the independent review's own observation). terminate() is safe to call on an
        # already-reaped process (Popen.wait() returns the cached return code).
        supervisor.terminate()


def test_process_supervisor_terminate_kills_a_hanging_process() -> None:
    supervisor = ProcessSupervisor.spawn(["python3", "-c", "import time; time.sleep(30)"])
    try:
        timed_out = supervisor.wait(timeout_seconds=0.2)
        assert timed_out.outcome == "TIMED_OUT_STILL_RUNNING"
        terminated = supervisor.terminate()
        assert terminated.local_process_group_terminated is True
    finally:
        supervisor.terminate()


def test_proc_start_time_distinguishes_a_real_pid_from_a_bogus_one() -> None:
    supervisor = ProcessSupervisor.spawn(["python3", "-c", "import time; time.sleep(1)"])
    try:
        assert _read_proc_start_time(supervisor.pid) is not None
        supervisor.terminate()
        assert _read_proc_start_time(999_999_999) is None
    finally:
        supervisor.terminate()


def test_process_supervisor_terminate_reaps_a_process_that_exited_before_terminate_was_called() -> (
    None
):
    """Regression for the bulk-run flakiness the independent review observed
    (F-ProcSupervisor-1): terminate() must still reap a process that already exited on
    its own by the time terminate() is called, rather than conflating "our process
    already exited" with "a different process now holds the reused PID" and skipping
    wait() (and the reap) entirely, which leaked an unreaped child and could cascade into
    a failure in whatever test ran next.

    **Corrected again (continued flakiness after the first fix):** the review's bulk run
    still reproduced the same /proc-read failure followed by an unreaped-process
    warning. The production fix above is sound, but this test's own body left a window
    where an assertion failure between spawning the process and calling terminate()
    would itself leak an un-reaped child -- the test's structure, not terminate(), was
    the remaining leak. The spawn is now always paired with a reap in ``finally``,
    regardless of which assert (if any) fails."""

    supervisor = ProcessSupervisor.spawn(["python3", "-c", "pass"])
    try:
        time.sleep(0.3)  # let the process exit on its own, unreaped
        outcome = supervisor.terminate()
        assert outcome.outcome == "EXITED_ZERO"
        assert outcome.exit_code == 0
        assert outcome.local_process_group_terminated is True
    finally:
        supervisor.terminate()
