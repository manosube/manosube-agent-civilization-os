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


# --- ProcessSupervisor (a real, independently-tested primitive) -----------------------


def test_process_supervisor_wait_observes_real_exit_code() -> None:
    supervisor = ProcessSupervisor.spawn(["python3", "-c", "import sys; sys.exit(3)"])
    outcome = supervisor.wait(timeout_seconds=5.0)
    assert outcome.outcome == "EXITED_NONZERO"
    assert outcome.exit_code == 3
    assert outcome.local_process_group_terminated is True


def test_process_supervisor_terminate_kills_a_hanging_process() -> None:
    supervisor = ProcessSupervisor.spawn(["python3", "-c", "import time; time.sleep(30)"])
    timed_out = supervisor.wait(timeout_seconds=0.2)
    assert timed_out.outcome == "TIMED_OUT_STILL_RUNNING"
    terminated = supervisor.terminate()
    assert terminated.local_process_group_terminated is True


def test_proc_start_time_distinguishes_a_real_pid_from_a_bogus_one() -> None:
    supervisor = ProcessSupervisor.spawn(["python3", "-c", "import time; time.sleep(1)"])
    assert _read_proc_start_time(supervisor.pid) is not None
    supervisor.terminate()
    assert _read_proc_start_time(999_999_999) is None
