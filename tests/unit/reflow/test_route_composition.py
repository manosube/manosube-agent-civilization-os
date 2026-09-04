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
    store_ready_for_closure,
)
from tests.state_helpers import SCHEMA_ROOT, initial_state

from manosube_agent_civilization.difference.identity import policy_semantic_fingerprint
from manosube_agent_civilization.difference.lifecycle import closure_evaluation_binding_errors
from manosube_agent_civilization.reflow.bookkeeping import apply_reflow_bookkeeping
from manosube_agent_civilization.reflow.commit import commit_reflow
from manosube_agent_civilization.reflow.errors import StaleReflowError
from manosube_agent_civilization.reflow.lifecycle import mint_transition_event
from manosube_agent_civilization.reflow.route import LIFECYCLE_EVENT_KIND, reflow
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import FileStateStore

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


def _reverify_to_verifying(
    store: FileStateStore,
    project_id: str,
    difference: dict,
    previous: dict,
    *,
    event_revision: int,
    reflow_instant: str,
) -> dict:
    """Mint and commit the ``BLOCKED -> VERIFYING`` re-verification event Difference's own
    engine (not Reflow) owns between a blocker resolving and the next Reflow cycle --
    ``DIFFERENCE_LIFECYCLE.md``'s own table routes a resolved blocker back through
    VERIFYING before anything can close. Reflow does not mint this event itself; this
    stands in for the real external re-verification step so the *next* Reflow call has a
    real, resolvable, correctly-`to_status`-VERIFYING predecessor to chain from (R2-F1).
    """

    before_state = previous["committed_state"]
    decision = {
        "to_status": "VERIFYING",
        "reason_code": "BLOCKER_RESOLVED",
        "reason": "BLOCKER_RESOLVED: external re-verification",
        "closure_evaluation_ref": None,
    }
    event = mint_transition_event(
        difference=difference,
        current_status="BLOCKED",
        previous_event_id=previous["event"]["difference_event_id"],
        event_revision=event_revision,
        decision=decision,
        evaluation={
            "evaluated_state_revision": before_state["state_revision"],
            "evaluated_state_fingerprint": before_state["semantic_fingerprint"],
        },
        observation_refs=[],
        evidence_refs=[],
    )
    difference_ref = {"kind": "difference", "id": difference["difference_id"]}
    lifecycle_event_ref = {"kind": LIFECYCLE_EVENT_KIND, "id": event["difference_event_id"]}
    tx = f"TX-REVERIFY-{event_revision:04d}"
    next_semantic_state = apply_reflow_bookkeeping(
        before_state["semantic_state"],
        difference_ref=difference_ref,
        to_status="VERIFYING",
        new_evidence_refs=[],
        lifecycle_event_ref=lifecycle_event_ref,
        contradiction_refs=[],
        transaction_ref={"kind": "state_transition", "id": tx},
    )
    committed_state, committed_ref = commit_reflow(
        store,
        project_id=project_id,
        before_project_state=before_state,
        next_semantic_state=next_semantic_state,
        transaction_id=tx,
        evidence_refs=[],
        reflow_instant=reflow_instant,
        records=[(LIFECYCLE_EVENT_KIND, event["difference_event_id"], event)],
    )
    return {"committed_state": committed_state, "state_transition_ref": committed_ref, "event": event}


def _fresh_store(tmp_path: Path) -> tuple[FileStateStore, dict]:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = initial_state()
    # R7-F3: G3 requires the committed State's own objective_revision_id to exactly match
    # fixture_difference()'s own objective_revision_ref.id -- every test in this module
    # evaluates against that fixture Difference.
    project_state["objective_revision_id"] = fixture_difference()["objective_revision_ref"]["id"]
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
        previous_event_id=difference["genesis_event_ref"]["id"],
        event_revision=1,
        closure_request=base_closure_request(difference, policy),
        observation_refs=[],
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


def test_repeated_reflow_calls_each_admit_a_fresh_transaction(tmp_path: Path) -> None:
    """F1 changed this route's retry semantics: since the predecessor State is always the
    Store's own *current* one rather than a caller-frozen snapshot, a second call built
    from the identical ``closure_request`` is not a replay of the first transaction (its
    ``transaction_id`` is bound to ``expected_revision``, which has itself advanced) -- it
    is a second, independent admission. Both must still succeed, and each must advance the
    Store by exactly one revision; nothing about a caller repeating the same call can make
    it collide with, or silently reuse, the first one's transaction."""

    store, project_state = _fresh_store(tmp_path)
    difference = fixture_difference()
    policy = fixture_policy(difference)

    kwargs = dict(
        store=store,
        project_id=project_state["project_id"],
        previous_event_id=difference["genesis_event_ref"]["id"],
        event_revision=1,
        closure_request=base_closure_request(difference, policy),
        observation_refs=[],
        reflow_instant=REFLOW_INSTANT,
        blocker_scope=_blocker_scope(difference),
        blocker_resolution_condition=_blocker_condition(difference),
        next_observation_ref=NEXT_OBSERVATION_REF,
        **BLOCKER_KWARGS,
    )
    first = reflow(**kwargs)
    reverified = _reverify_to_verifying(
        store, project_state["project_id"], difference, first, event_revision=2, reflow_instant=REFLOW_INSTANT
    )
    second_closure_request = dict(base_closure_request(difference, policy))
    second_closure_request["difference_event_head_ref"] = {
        "kind": LIFECYCLE_EVENT_KIND, "id": reverified["event"]["difference_event_id"],
    }
    second = reflow(
        **{
            **kwargs,
            "closure_request": second_closure_request,
            "previous_event_id": reverified["event"]["difference_event_id"],
            "event_revision": 3,
        }
    )

    assert first["state_transition_ref"] != second["state_transition_ref"]
    assert second["committed_state"]["state_revision"] == first["committed_state"]["state_revision"] + 2
    assert store.load_current(project_state["project_id"]) == second["committed_state"]


def test_route_b_closed_removes_the_difference_from_open_differences(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    current_state = {
        "revision": project_state["state_revision"],
        "fingerprint": project_state["semantic_fingerprint"],
    }
    closure_request = candidate_closure_request(difference, policy, current_state=current_state)

    result = reflow(
        store,
        project_id=project_state["project_id"],
        previous_event_id=difference["genesis_event_ref"]["id"],
        event_revision=1,
        closure_request=closure_request,
        observation_refs=closure_request["reobservation"]["after_observation_refs"],
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
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    difference = fixture_difference()
    policy = fixture_policy(difference)

    first = reflow(
        store,
        project_id=project_state["project_id"],
        previous_event_id=difference["genesis_event_ref"]["id"],
        event_revision=1,
        closure_request=base_closure_request(difference, policy),
        observation_refs=[],
        reflow_instant=REFLOW_INSTANT,
        blocker_scope=_blocker_scope(difference),
        blocker_resolution_condition=_blocker_condition(difference),
        next_observation_ref=NEXT_OBSERVATION_REF,
        **BLOCKER_KWARGS,
    )
    # BLOCKED does not transition directly to CLOSED (DIFFERENCE_LIFECYCLE.md's own table
    # routes a resolved blocker back through VERIFYING first); this stands in for that
    # intervening external re-verification step (R2-F1 now requires it to be real).
    reverified = _reverify_to_verifying(
        store, project_state["project_id"], difference, first, event_revision=2, reflow_instant=REFLOW_INSTANT
    )
    second_current_state = {
        "revision": reverified["committed_state"]["state_revision"],
        "fingerprint": reverified["committed_state"]["semantic_fingerprint"],
    }
    closure_request = candidate_closure_request(difference, policy, current_state=second_current_state)
    closure_request["difference_event_head_ref"] = {
        "kind": LIFECYCLE_EVENT_KIND, "id": reverified["event"]["difference_event_id"],
    }
    second = reflow(
        store,
        project_id=project_state["project_id"],
        previous_event_id=reverified["event"]["difference_event_id"],
        event_revision=3,
        closure_request=closure_request,
        observation_refs=closure_request["reobservation"]["after_observation_refs"],
        reflow_instant="2026-08-30T13:00:00Z",
    )

    assert second["committed_state"]["state_revision"] == first["committed_state"]["state_revision"] + 2
    assert second["decision"]["to_status"] == "CLOSED"
    assert second["committed_state"]["semantic_state"]["open_differences"] == []


def test_a_stale_expected_state_revision_is_refused(tmp_path: Path) -> None:
    """F1: the predecessor State always comes from the Store, never a caller body -- so
    what a stale caller can forge is only its own *expectation* of that State, and even
    that is refused rather than silently reflowed against a State it never saw."""

    store, project_state = _fresh_store(tmp_path)
    difference = fixture_difference()
    policy = fixture_policy(difference)

    with pytest.raises(StaleReflowError):
        reflow(
            store,
            project_id=project_state["project_id"],
            previous_event_id=difference["genesis_event_ref"]["id"],
            event_revision=1,
            expected_state_revision=99,
            closure_request=base_closure_request(difference, policy),
            observation_refs=[],
            reflow_instant=REFLOW_INSTANT,
            blocker_scope=_blocker_scope(difference),
            blocker_resolution_condition=_blocker_condition(difference),
            next_observation_ref=NEXT_OBSERVATION_REF,
            **BLOCKER_KWARGS,
        )
    # And the refusal is real, not merely reported: nothing committed.
    assert store.load_current(project_state["project_id"]) == project_state


def test_closing_one_difference_leaves_other_open_differences_untouched(tmp_path: Path) -> None:
    # The other Difference's presence must be real Store state, not a local mutation of a
    # `project_state` object reflow() no longer trusts (F1) -- it is baked into the actual
    # committed genesis State before reflow() ever loads it, and the Store is then advanced
    # to a real revision G5's floor accepts (F2).
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    genesis = initial_state()
    other_ref = {"kind": "difference", "id": "D-" + "7" * 64}
    genesis["semantic_state"]["open_differences"] = [other_ref]
    project_state = store_ready_for_closure(store, genesis=genesis)

    difference = fixture_difference()
    policy = fixture_policy(difference)

    current_state = {
        "revision": project_state["state_revision"],
        "fingerprint": project_state["semantic_fingerprint"],
    }
    closure_request = candidate_closure_request(difference, policy, current_state=current_state)
    result = reflow(
        store,
        project_id=project_state["project_id"],
        previous_event_id=difference["genesis_event_ref"]["id"],
        event_revision=1,
        closure_request=closure_request,
        observation_refs=closure_request["reobservation"]["after_observation_refs"],
        reflow_instant=REFLOW_INSTANT,
    )

    assert result["committed_state"]["semantic_state"]["open_differences"] == [other_ref]
