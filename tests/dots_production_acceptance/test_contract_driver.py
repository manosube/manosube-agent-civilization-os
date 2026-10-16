"""Contract tests for driver.py -- WU2 Phase A's dispatch loop + stop/reconcile gate.

Tracks #116 (WU2 Phase A). Exercises the real with_work_time_coordination composition
and a real FileStateStore via tests.fixtures.dots_production_acceptance_world.bound();
the only stand-in is FixedFixtureDotsAdapter itself (Phase A's own, disclosed scope).
Zero live dots/GitHub call anywhere.
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
    _read_proc_start_time,
)
from tests.fixtures.dots_production_acceptance_world import bound

WORK_UNIT = {"kind": "dots_production_acceptance_work_unit", "id": "WU-TEST-0001"}


def _make_driver(tmp_path: Path, *, adapter: FixedFixtureDotsAdapter | None = None) -> tuple[Driver, dict]:
    store, world = bound(tmp_path)
    driver = Driver(
        store,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        run_state_path=tmp_path / "run_state.json",
        adapter=adapter or FixedFixtureDotsAdapter(),
    )
    return driver, world


def test_dispatch_succeeds_and_opens_real_work_time_coordination(tmp_path: Path) -> None:
    driver, _world = _make_driver(tmp_path)
    record = driver.dispatch(WORK_UNIT, case_classification="NORMAL_OPERATION")

    assert record.run_state == "RESOLVED"
    assert record.outcome == "SUCCEEDED"
    assert record.open_ref is not None

    resolved = driver._store.resolve_record(
        driver._project_id, "work_time_coordination_open", record.open_ref["id"]
    )
    assert resolved["work_unit_ref"] == WORK_UNIT
    assert resolved["adapter_kind"] == "DOTS_PRODUCTION_ACCEPTANCE_DISPATCH"


def test_intentional_refusal_test_failure_is_recorded_not_raised(tmp_path: Path) -> None:
    driver, _world = _make_driver(tmp_path)
    record = driver.dispatch(
        WORK_UNIT,
        case_classification="INTENTIONAL_REFUSAL_TEST",
        worker_argv=["python3", "-c", "import sys; sys.exit(1)"],
    )

    assert record.run_state == "RESOLVED"
    assert record.outcome == "FAILED"


def test_normal_operation_failure_raises_rather_than_silently_recording(tmp_path: Path) -> None:
    driver, _world = _make_driver(tmp_path)
    with pytest.raises(DriverError, match="dispatch of .* failed"):
        driver.dispatch(
            WORK_UNIT,
            case_classification="NORMAL_OPERATION",
            worker_argv=["python3", "-c", "import sys; sys.exit(1)"],
        )
    key = f"{WORK_UNIT['kind']}:{WORK_UNIT['id']}"
    assert driver.run_state.work_units[key].outcome == "FAILED"
    assert driver.run_state.work_units[key].run_state == "RESOLVED"


def test_timeout_terminates_the_still_running_worker(tmp_path: Path) -> None:
    driver, _world = _make_driver(tmp_path)
    with pytest.raises(DriverError):
        driver.dispatch(
            WORK_UNIT,
            case_classification="NORMAL_OPERATION",
            worker_argv=["python3", "-c", "import time; time.sleep(30)"],
            worker_timeout_seconds=0.2,
        )
    outcome = driver._adapter.external_state["last_dispatch_outcome"]["worker_outcome"]
    assert outcome in {"EXITED_NONZERO", "TIMED_OUT_STILL_RUNNING"}


def test_redispatch_blocked_while_prior_attempt_unresolved(tmp_path: Path) -> None:
    driver, _world = _make_driver(tmp_path)
    key = f"{WORK_UNIT['kind']}:{WORK_UNIT['id']}"
    from tests.dots_production_acceptance.driver import WorkUnitRecord

    driver.run_state.put(
        key,
        WorkUnitRecord(work_unit_ref=dict(WORK_UNIT), case_classification="NORMAL_OPERATION", run_state="DISPATCHED"),
    )
    with pytest.raises(DriverError, match="not RESOLVED"):
        driver.dispatch(WORK_UNIT, case_classification="NORMAL_OPERATION")


def test_stop_accepted_only_on_explicit_positive_ack_and_then_blocks_dispatch(tmp_path: Path) -> None:
    driver, _world = _make_driver(tmp_path, adapter=FixedFixtureDotsAdapter(stop_acknowledges=True))
    assert driver.request_stop("RUN-1") == "ACCEPTED"
    assert driver.run_state.stop_ack == "ACCEPTED"
    with pytest.raises(DriverError, match="refusing new dispatch"):
        driver.dispatch({"kind": "x", "id": "y"}, case_classification="NORMAL_OPERATION")


def test_unconfirmed_stop_blocks_dispatch_exactly_like_an_accepted_one(tmp_path: Path) -> None:
    driver, _world = _make_driver(tmp_path, adapter=FixedFixtureDotsAdapter(stop_acknowledges=False))
    assert driver.request_stop("RUN-1") == "UNCONFIRMED"
    assert driver.run_state.stop_ack == "UNCONFIRMED"
    with pytest.raises(DriverError, match="refusing new dispatch"):
        driver.dispatch({"kind": "x", "id": "y"}, case_classification="NORMAL_OPERATION")


def test_recovery_refused_until_reconciliation_completes_then_unblocks_dispatch(tmp_path: Path) -> None:
    driver, world = _make_driver(tmp_path)
    driver.request_stop("RUN-1")
    assert driver.run_state.stop_ack == "ACCEPTED"

    # (1) reconciliation incomplete (external side not yet matching) -> recovery refused.
    incomplete = driver.reconcile_before_recovery(
        expected_state_predicate=lambda s: True,
        expected_external_predicate=lambda ext: ext.get("nonexistent_key") == "never",
    )
    assert incomplete.reconciled is False
    with pytest.raises(DriverError, match="refusing recovery"):
        driver.allow_recovery(incomplete)
    assert driver.run_state.stop_ack == "ACCEPTED"  # still blocked

    # (2) both sides now match -> reconciled, recovery unblocks dispatch.
    complete = driver.reconcile_before_recovery(
        expected_state_predicate=lambda s: s["state_revision"] == world["genesis_state"]["state_revision"],
        expected_external_predicate=lambda ext: ext.get("stop_acknowledged_for_run_id") == "RUN-1",
    )
    assert complete.reconciled is True
    driver.allow_recovery(complete)
    assert driver.run_state.stop_ack == "NOT_REQUESTED"

    record = driver.dispatch({"kind": "x", "id": "y"}, case_classification="NORMAL_OPERATION")
    assert record.outcome == "SUCCEEDED"


def test_reconcile_before_recovery_reuses_the_existing_reconciliation_module(tmp_path: Path) -> None:
    driver, _world = _make_driver(tmp_path)
    result = driver.reconcile_before_recovery(
        expected_state_predicate=lambda s: True,
        expected_external_predicate=lambda ext: True,
    )
    assert isinstance(result, recon.ReconciliationResult)


# --- ProcessSupervisor (event 4) -------------------------------------------------------


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
