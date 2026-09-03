"""Real injected-violation tests for Reflow's Atomic State commit (RF6).

Every commit here goes through the real ``FileStateStore`` -- no second persistence path,
no hand-rolled CAS check. What this module adds (``build_state_transition``,
``commit_reflow``) is proven only by driving the real Store and observing its real
behavior: successful commit, idempotent replay, a stale Compare-And-Swap rejection, and a
transaction-id collision on a different payload.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from tests.state_helpers import SCHEMA_ROOT, initial_state

from manosube_agent_civilization.reflow.commit import commit_reflow
from manosube_agent_civilization.reflow.errors import ReflowValidationError
from manosube_agent_civilization.reflow.identity import transaction_id
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import FileStateStore
from manosube_agent_civilization.store.errors import StaleStateError, TransactionConflictError

PROJECT_ID = "PRJ-0001"
REFLOW_INSTANT = "2026-08-30T12:00:00Z"


def _prepared_initial() -> dict:
    state = initial_state()
    state["semantic_fingerprint"] = fingerprint_project_state(state, schema_root=SCHEMA_ROOT).as_dict()
    return state


def _next_semantic(before: dict) -> dict:
    next_semantic = deepcopy(before["semantic_state"])
    next_semantic["code"]["status"] = "KNOWN"
    return next_semantic


def _tx(expected_revision: int, decision_fingerprint: str = "sha256:" + "1" * 64) -> str:
    return transaction_id(
        project_id=PROJECT_ID,
        difference_id="D-" + "0" * 64,
        closure_decision_fingerprint=decision_fingerprint,
        evidence_sufficiency_id=None,
        expected_revision=expected_revision,
        reflow_instant=REFLOW_INSTANT,
    )


def test_commit_advances_the_real_store_and_returns_the_transition_ref(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    initial = _prepared_initial()
    store.initialize(PROJECT_ID, initial)

    tx = _tx(initial["state_revision"])
    committed, ref = commit_reflow(
        store,
        project_id=PROJECT_ID,
        before_project_state=initial,
        next_semantic_state=_next_semantic(initial),
        transaction_id=tx,
        evidence_refs=[],
        reflow_instant=REFLOW_INSTANT,
    )

    assert committed["state_revision"] == initial["state_revision"] + 1
    assert committed["lineage_head_ref"] == {"kind": "state_transition", "id": tx}
    assert ref == {"kind": "state_transition", "id": tx}
    assert store.load_current(PROJECT_ID) == committed


def test_replaying_the_same_transaction_is_idempotent(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    initial = _prepared_initial()
    store.initialize(PROJECT_ID, initial)
    tx = _tx(initial["state_revision"])
    next_semantic = _next_semantic(initial)

    first, _ = commit_reflow(
        store, project_id=PROJECT_ID, before_project_state=initial,
        next_semantic_state=next_semantic, transaction_id=tx, evidence_refs=[],
        reflow_instant=REFLOW_INSTANT,
    )
    second, _ = commit_reflow(
        store, project_id=PROJECT_ID, before_project_state=initial,
        next_semantic_state=next_semantic, transaction_id=tx, evidence_refs=[],
        reflow_instant=REFLOW_INSTANT,
    )

    assert first == second


def test_stale_before_state_is_rejected_by_the_real_store(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    initial = _prepared_initial()
    store.initialize(PROJECT_ID, initial)
    stale_before = deepcopy(initial)
    stale_before["state_revision"] = 99

    with pytest.raises(StaleStateError):
        commit_reflow(
            store, project_id=PROJECT_ID, before_project_state=stale_before,
            next_semantic_state=_next_semantic(initial), transaction_id=_tx(99),
            evidence_refs=[], reflow_instant=REFLOW_INSTANT,
        )


def test_same_transaction_id_with_a_different_payload_conflicts(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    initial = _prepared_initial()
    store.initialize(PROJECT_ID, initial)
    tx = _tx(initial["state_revision"])
    commit_reflow(
        store, project_id=PROJECT_ID, before_project_state=initial,
        next_semantic_state=_next_semantic(initial), transaction_id=tx, evidence_refs=[],
        reflow_instant=REFLOW_INSTANT,
    )

    different_semantic = deepcopy(initial["semantic_state"])
    different_semantic["code"]["status"] = "UNKNOWN"
    with pytest.raises(TransactionConflictError):
        commit_reflow(
            store, project_id=PROJECT_ID, before_project_state=initial,
            next_semantic_state=different_semantic, transaction_id=tx, evidence_refs=[],
            reflow_instant=REFLOW_INSTANT,
        )


def test_before_state_from_a_different_project_is_refused(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    initial = _prepared_initial()
    store.initialize(PROJECT_ID, initial)
    foreign = deepcopy(initial)
    foreign["project_id"] = "PRJ-OTHER"

    with pytest.raises(ReflowValidationError):
        commit_reflow(
            store, project_id=PROJECT_ID, before_project_state=foreign,
            next_semantic_state=_next_semantic(initial), transaction_id=_tx(0),
            evidence_refs=[], reflow_instant=REFLOW_INSTANT,
        )
