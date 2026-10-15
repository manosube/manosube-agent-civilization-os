"""Contract tests for reconciliation.py per MEASUREMENT_CONTRACT.md Sec.A,
"Reconciliation completion" row.

Tracks #116 (WU2). Exercises the real ``FileStateStore.read_current_consistent`` --
never a parallel read path -- paired with an injected, connection-method-independent
stub for the external side (the real dots-specific reader is ``dots_adapter.py``'s job,
not this gate's).
"""

from __future__ import annotations

from pathlib import Path

from tests.dots_production_acceptance import reconciliation as recon
from tests.fixtures.dots_production_acceptance_world import bound


def test_reconcile_true_only_when_both_store_and_external_match(tmp_path: Path) -> None:
    store, world = bound(tmp_path)
    project_id = world["project_id"]
    genesis_state = world["genesis_state"]

    result = recon.reconcile(
        store,
        project_id=project_id,
        expected_state_predicate=lambda state: state["state_revision"] == genesis_state["state_revision"],
        external_reader=lambda: {"pr_state": "merged"},
        expected_external_predicate=lambda observed: observed["pr_state"] == "merged",
    )

    assert result.store_matched is True
    assert result.external_matched is True
    assert result.reconciled is True
    assert result.store_observed["project_id"] == project_id


def test_reconcile_false_when_store_matches_but_external_does_not(tmp_path: Path) -> None:
    store, world = bound(tmp_path)
    project_id = world["project_id"]
    genesis_state = world["genesis_state"]

    result = recon.reconcile(
        store,
        project_id=project_id,
        expected_state_predicate=lambda state: state["state_revision"] == genesis_state["state_revision"],
        external_reader=lambda: {"pr_state": "open"},
        expected_external_predicate=lambda observed: observed["pr_state"] == "merged",
    )

    assert result.store_matched is True
    assert result.external_matched is False
    assert result.reconciled is False, "never reconciled from the Store side alone"


def test_reconcile_false_when_external_matches_but_store_does_not(tmp_path: Path) -> None:
    store, world = bound(tmp_path)
    project_id = world["project_id"]

    result = recon.reconcile(
        store,
        project_id=project_id,
        expected_state_predicate=lambda state: state["state_revision"] == 999,  # wrong on purpose
        external_reader=lambda: {"pr_state": "merged"},
        expected_external_predicate=lambda observed: observed["pr_state"] == "merged",
    )

    assert result.store_matched is False
    assert result.external_matched is True
    assert result.reconciled is False, "never reconciled from the external side alone"


def test_reconcile_never_mutates_store_state(tmp_path: Path) -> None:
    store, world = bound(tmp_path)
    project_id = world["project_id"]
    genesis_state = world["genesis_state"]

    recon.reconcile(
        store,
        project_id=project_id,
        expected_state_predicate=lambda state: True,
        external_reader=dict,
        expected_external_predicate=lambda observed: True,
    )

    after = store.load_current(project_id)
    assert after["state_revision"] == genesis_state["state_revision"]
    assert after["semantic_fingerprint"] == genesis_state["semantic_fingerprint"]


def test_reconcile_calls_external_reader_exactly_once(tmp_path: Path) -> None:
    store, world = bound(tmp_path)
    project_id = world["project_id"]

    calls = {"count": 0}

    def external_reader() -> dict:
        calls["count"] += 1
        return {"ok": True}

    recon.reconcile(
        store,
        project_id=project_id,
        expected_state_predicate=lambda state: True,
        external_reader=external_reader,
        expected_external_predicate=lambda observed: observed["ok"],
    )

    assert calls["count"] == 1, "never resend/retry from inside this gate -- that decision belongs to the driver"
