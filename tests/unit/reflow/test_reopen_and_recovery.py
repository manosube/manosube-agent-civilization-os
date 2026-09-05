"""Real tests for Route C: Reopen (reflow.route.reopen) and crash recovery + replay.

The crash-recovery half does not reimplement anything the Store's own
``tests/integration/store/test_file_store.py::test_every_crash_point_converges`` already
proves about ``FileStateStore`` -- it proves that *Reflow's own* commit path
(``reflow.commit.commit_reflow``) produces a ``transition`` record the Store's crash
recovery converges on, at every one of the Store's own injectable ``STAGES``, and that a
second, identical Reflow cycle after recovery replays idempotently rather than
double-committing.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.reflow_helpers import (
    candidate_closure_request,
    fixture_difference,
    fixture_genesis_lifecycle_event,
    fixture_policy,
    store_ready_for_closure,
)
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.difference.validation import (
    DIFFERENCE_SCHEMA_BASE,
    validate_record,
)
from manosube_agent_civilization.reflow.commit import commit_reflow
from manosube_agent_civilization.reflow.errors import ReflowValidationError
from manosube_agent_civilization.reflow.identity import transaction_id
from manosube_agent_civilization.reflow.reopen import decide_reopen
from manosube_agent_civilization.reflow.route import reflow, reopen
from manosube_agent_civilization.store import STAGES, FileStateStore
from manosube_agent_civilization.store.errors import SimulatedCrash

REFLOW_INSTANT = "2026-08-30T12:00:00Z"
CONTRADICTION_REF = {"kind": "material_contradiction", "id": "CONTRA-" + "5" * 64}
REOPEN_NEXT_OBSERVATION_REF = {"kind": "next_observation_request", "id": "OBS-REQ-" + "9" * 64}


def _fresh_store(tmp_path: Path) -> tuple[FileStateStore, dict]:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    project_state = store_ready_for_closure(store)
    return store, project_state


def _close(store: FileStateStore, project_state: dict, difference: dict, policy: dict) -> dict:
    current_state = {
        "revision": project_state["state_revision"],
        "fingerprint": project_state["semantic_fingerprint"],
    }
    closure_request = candidate_closure_request(difference, policy, current_state=current_state)
    return reflow(
        store,
        project_id=project_state["project_id"],
        previous_event_id=difference["genesis_event_ref"]["id"],
        genesis_lifecycle_event=fixture_genesis_lifecycle_event(difference),
        event_revision=1,
        closure_request=closure_request,
        observation_refs=closure_request["reobservation"]["after_observation_refs"],
        reflow_instant=REFLOW_INSTANT,
    )


def test_material_contradiction_reopens_a_closed_difference(tmp_path: Path) -> None:
    store, project_state = _fresh_store(tmp_path)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    closed = _close(store, project_state, difference, policy)

    result = reopen(
        store,
        project_id=project_state["project_id"],
        difference=difference,
        trigger="MATERIAL_CONTRADICTION",
        previous_event_id=closed["event"]["difference_event_id"],
        event_revision=2,
        next_observation_ref=REOPEN_NEXT_OBSERVATION_REF,
        observation_refs=[],
        contradiction_evidence_refs=[CONTRADICTION_REF],
        contradiction_refs=[CONTRADICTION_REF],
        reflow_instant="2026-08-30T14:00:00Z",
    )

    assert result["decision"]["to_status"] == "REOPENED"
    validate_record(
        result["event"], "difference_lifecycle_event.schema.json", base=DIFFERENCE_SCHEMA_BASE
    )
    semantic = result["committed_state"]["semantic_state"]
    assert {"kind": "difference", "id": difference["difference_id"]} in semantic["open_differences"]
    assert CONTRADICTION_REF in semantic["unresolved_contradictions"]
    assert (
        result["committed_state"]["state_revision"]
        == closed["committed_state"]["state_revision"] + 1
    )


def test_reopen_refuses_an_evaluation_that_never_closed() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    closure_request = candidate_closure_request(difference, policy)
    from manosube_agent_civilization.reflow.closure import evaluate_closure

    evaluation = evaluate_closure(closure_request)
    not_closed = dict(evaluation)
    not_closed["result"] = "NOT_SATISFIED"

    with pytest.raises(ReflowValidationError):
        decide_reopen(not_closed, "MATERIAL_CONTRADICTION")


def test_unimplemented_reopen_trigger_is_refused_not_silently_accepted() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    closure_request = candidate_closure_request(difference, policy)
    from manosube_agent_civilization.reflow.closure import evaluate_closure

    evaluation = evaluate_closure(closure_request)

    with pytest.raises(ReflowValidationError):
        decide_reopen(evaluation, "POLICY_REOPEN_CONDITION_SATISFIED")


@pytest.mark.parametrize("stage", STAGES)
def test_reflow_commit_converges_after_a_crash_at_every_stage(stage: str, tmp_path: Path) -> None:
    store, project_state = _fresh_store(tmp_path)
    difference = fixture_difference()
    policy = fixture_policy(difference)
    closure_request = candidate_closure_request(difference, policy)

    from manosube_agent_civilization.reflow.closure import evaluate_closure
    from manosube_agent_civilization.reflow.identity import closure_evaluation_decision_fingerprint

    evaluation = evaluate_closure(closure_request)
    tx = transaction_id(
        project_id=project_state["project_id"],
        difference_id=difference["difference_id"],
        closure_decision_fingerprint=closure_evaluation_decision_fingerprint(evaluation),
        evidence_sufficiency_id=evaluation["evidence_sufficiency_ref"]["id"],
        expected_revision=project_state["state_revision"],
        reflow_instant=REFLOW_INSTANT,
    )

    def fault(current: str) -> None:
        if current == stage:
            raise SimulatedCrash(stage)

    with pytest.raises(SimulatedCrash):
        commit_reflow(
            store,
            project_id=project_state["project_id"],
            before_project_state=project_state,
            next_semantic_state=evaluation["after_state_candidate"]["semantic_state"],
            transaction_id=tx,
            evidence_refs=closure_request["change_free_verification_evidence_refs"],
            reflow_instant=REFLOW_INSTANT,
            fault=fault,
        )

    recovered = store.recover(project_state["project_id"])
    early_stage = stage in STAGES[: STAGES.index("AFTER_COMMIT_INTENT")]
    base_revision = project_state["state_revision"]
    assert recovered["state_revision"] == (base_revision if early_stage else base_revision + 1)
    assert store.load_current(project_state["project_id"]) == recovered

    if not early_stage:
        # Replaying the identical transaction after recovery is idempotent, not a second
        # commit: the Store's own transaction-id contract, exercised through Reflow's
        # commit path rather than assumed.
        replayed, _ = commit_reflow(
            store,
            project_id=project_state["project_id"],
            before_project_state=project_state,
            next_semantic_state=evaluation["after_state_candidate"]["semantic_state"],
            transaction_id=tx,
            evidence_refs=closure_request["change_free_verification_evidence_refs"],
            reflow_instant=REFLOW_INSTANT,
        )
        assert replayed == recovered
