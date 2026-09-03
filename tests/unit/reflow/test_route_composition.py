"""End-to-end real-composition tests for reflow.route.reflow (RF7 non-closure routes,
RF8 the closure-capable route).

Every record here is produced by the real chain: derive_differences -> evaluate_closure
-> decide_transition -> mint_transition_event -> apply_reflow_bookkeeping ->
commit_reflow -> the real FileStateStore. Nothing is hand-assembled to look like a
Reflow outcome; each test drives the actual composition and checks the actual committed
State.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.reflow_helpers import (
    base_closure_request,
    candidate_closure_request,
    fixture_difference,
    fixture_policy,
)
from tests.state_helpers import SCHEMA_ROOT, initial_state

from manosube_agent_civilization.difference.identity import policy_semantic_fingerprint
from manosube_agent_civilization.difference.lifecycle import closure_evaluation_binding_errors
from manosube_agent_civilization.reflow.route import reflow
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import FileStateStore
from manosube_agent_civilization.store.errors import StaleStateError

REFLOW_INSTANT = "2026-08-30T12:00:00Z"

BLOCKER_KWARGS = {
    "blocker_kind": "OBSERVATION_PATH",
}


def _blocker_scope(difference: dict) -> dict:
    return {
        "kind": "difference_blocker_scope",
        "affected_subject_refs": {
            "collection_kind": "UNORDERED_SET",
            "members": [{"kind": "difference", "id": difference["difference_id"]}],
        },
        "effective_boundary": difference["effective_boundary"],
        "blocked_stage": "OBSERVATION",
    }


def _blocker_condition(difference: dict) -> dict:
    return {
        "kind": "blocker_resolution_condition",
        "condition_code": "OBSERVATION_PATH_AVAILABLE",
        "subject_ref": {"kind": "difference", "id": difference["difference_id"]},
        "expected_state": "AVAILABLE",
        "verification_request_ref": {
            "kind": "next_observation_request",
            "id": "OBS-REQ-" + "2" * 64,
        },
    }


NEXT_OBSERVATION_REF = {"kind": "next_observation_request", "id": "OBS-REQ-" + "2" * 64}


def _fresh_store(tmp_path: Path) -> tuple[FileStateStore, dict]:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = initial_state()
    project_state["semantic_fingerprint"] = fingerprint_project_state(
        project_state, schema_root=SCHEMA_ROOT
    ).as_dict()
    store.initialize(project_state["project_id"], project_state)
    return store, project_state


def test_route_a_blocked_commits_bookkeeping_without_closing(tmp_path: Path) -> None:
    store, project_state = _fresh_store(tmp_path)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    difference_ref = {"kind": "difference", "id": difference["difference_id"]}

    result = reflow(
        store,
        project_id=project_state["project_id"],
        difference=difference,
        current_status="VERIFYING",
        previous_event_id=difference["genesis_event_ref"]["id"],
        event_revision=1,
        before_project_state=project_state,
        closure_request=base_closure_request(difference, policy),
        observation_refs=[],
        evidence_refs=[{"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}],
        reflow_instant=REFLOW_INSTANT,
        blocker_scope=_blocker_scope(difference),
        blocker_resolution_condition=_blocker_condition(difference),
        next_observation_ref=NEXT_OBSERVATION_REF,
        **BLOCKER_KWARGS,
    )

    assert result["decision"]["to_status"] == "BLOCKED"
    assert result["event"]["reflow_transition_ref"] is None
    committed_semantic = result["committed_state"]["semantic_state"]
    assert difference_ref in committed_semantic["open_differences"]
    assert committed_semantic["reflow_state"]["last_transaction_ref"] == result["state_transition_ref"]
    assert store.load_current(project_state["project_id"]) == result["committed_state"]


def test_route_a_is_idempotent_under_the_same_transaction(tmp_path: Path) -> None:
    store, project_state = _fresh_store(tmp_path)
    difference = fixture_difference()
    policy = fixture_policy(difference)

    kwargs = dict(
        store=store,
        project_id=project_state["project_id"],
        difference=difference,
        current_status="VERIFYING",
        previous_event_id=difference["genesis_event_ref"]["id"],
        event_revision=1,
        before_project_state=project_state,
        closure_request=base_closure_request(difference, policy),
        observation_refs=[],
        evidence_refs=[{"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}],
        reflow_instant=REFLOW_INSTANT,
        blocker_scope=_blocker_scope(difference),
        blocker_resolution_condition=_blocker_condition(difference),
        next_observation_ref=NEXT_OBSERVATION_REF,
        **BLOCKER_KWARGS,
    )
    first = reflow(**kwargs)
    second = reflow(**kwargs)

    assert first["committed_state"] == second["committed_state"]
    assert first["state_transition_ref"] == second["state_transition_ref"]


def test_route_b_closed_removes_the_difference_from_open_differences(tmp_path: Path) -> None:
    store, project_state = _fresh_store(tmp_path)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    closure_request = candidate_closure_request(difference, policy)

    result = reflow(
        store,
        project_id=project_state["project_id"],
        difference=difference,
        current_status="VERIFYING",
        previous_event_id=difference["genesis_event_ref"]["id"],
        event_revision=1,
        before_project_state=project_state,
        closure_request=closure_request,
        observation_refs=closure_request["reobservation"]["after_observation_refs"],
        evidence_refs=closure_request["change_free_verification_evidence_refs"],
        reflow_instant=REFLOW_INSTANT,
    )

    assert result["decision"]["to_status"] == "CLOSED"
    assert result["event"]["reflow_transition_ref"] == result["state_transition_ref"]
    assert result["committed_state"]["semantic_state"]["open_differences"] == []

    errors = closure_evaluation_binding_errors(
        result["event"],
        None,
        difference,
        {result["evaluation"]["closure_evaluation_id"]: result["evaluation"]},
        {policy["closure_policy_id"]: policy},
        policy_semantic_fingerprint,
    )
    assert errors == []


def test_a_second_reflow_cycle_advances_the_real_store_again(tmp_path: Path) -> None:
    store, project_state = _fresh_store(tmp_path)
    difference = fixture_difference()
    policy = fixture_policy(difference)

    first = reflow(
        store,
        project_id=project_state["project_id"],
        difference=difference,
        current_status="VERIFYING",
        previous_event_id=difference["genesis_event_ref"]["id"],
        event_revision=1,
        before_project_state=project_state,
        closure_request=base_closure_request(difference, policy),
        observation_refs=[],
        evidence_refs=[{"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}],
        reflow_instant=REFLOW_INSTANT,
        blocker_scope=_blocker_scope(difference),
        blocker_resolution_condition=_blocker_condition(difference),
        next_observation_ref=NEXT_OBSERVATION_REF,
        **BLOCKER_KWARGS,
    )
    closure_request = candidate_closure_request(difference, policy)
    # BLOCKED does not transition directly to CLOSED (DIFFERENCE_LIFECYCLE.md's own table
    # routes a resolved blocker back through VERIFYING first); this second cycle stands in
    # for that intervening re-verification and evaluates fresh from VERIFYING again.
    second = reflow(
        store,
        project_id=project_state["project_id"],
        difference=difference,
        current_status="VERIFYING",
        previous_event_id=first["event"]["difference_event_id"],
        event_revision=2,
        before_project_state=first["committed_state"],
        closure_request=closure_request,
        observation_refs=closure_request["reobservation"]["after_observation_refs"],
        evidence_refs=closure_request["change_free_verification_evidence_refs"],
        reflow_instant="2026-08-30T13:00:00Z",
    )

    assert second["committed_state"]["state_revision"] == first["committed_state"]["state_revision"] + 1
    assert second["decision"]["to_status"] == "CLOSED"
    assert second["committed_state"]["semantic_state"]["open_differences"] == []


def test_a_stale_before_project_state_is_refused(tmp_path: Path) -> None:
    store, project_state = _fresh_store(tmp_path)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    stale = dict(project_state)
    stale["state_revision"] = 99

    with pytest.raises(StaleStateError):
        reflow(
            store,
            project_id=project_state["project_id"],
            difference=difference,
            current_status="VERIFYING",
            previous_event_id=difference["genesis_event_ref"]["id"],
            event_revision=1,
            before_project_state=stale,
            closure_request=base_closure_request(difference, policy),
            observation_refs=[],
            evidence_refs=[{"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}],
            reflow_instant=REFLOW_INSTANT,
            blocker_scope=_blocker_scope(difference),
            blocker_resolution_condition=_blocker_condition(difference),
            next_observation_ref=NEXT_OBSERVATION_REF,
            **BLOCKER_KWARGS,
        )


def test_closing_one_difference_leaves_other_open_differences_untouched(tmp_path: Path) -> None:
    store, project_state = _fresh_store(tmp_path)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    other_ref = {"kind": "difference", "id": "D-" + "7" * 64}
    project_state["semantic_state"]["open_differences"] = [other_ref]

    closure_request = candidate_closure_request(difference, policy)
    result = reflow(
        store,
        project_id=project_state["project_id"],
        difference=difference,
        current_status="VERIFYING",
        previous_event_id=difference["genesis_event_ref"]["id"],
        event_revision=1,
        before_project_state=project_state,
        closure_request=closure_request,
        observation_refs=closure_request["reobservation"]["after_observation_refs"],
        evidence_refs=closure_request["change_free_verification_evidence_refs"],
        reflow_instant=REFLOW_INSTANT,
    )

    assert result["committed_state"]["semantic_state"]["open_differences"] == [other_ref]
