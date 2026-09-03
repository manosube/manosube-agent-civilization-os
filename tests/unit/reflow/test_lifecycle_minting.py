"""Real injected-violation tests for Reflow's lifecycle event minting (RF5)."""

from __future__ import annotations

import pytest
from tests.reflow_helpers import (
    base_closure_request,
    candidate_closure_request,
    fixture_difference,
    fixture_policy,
)

from manosube_agent_civilization.difference.identity import policy_semantic_fingerprint
from manosube_agent_civilization.difference.lifecycle import closure_evaluation_binding_errors
from manosube_agent_civilization.difference.validation import (
    DIFFERENCE_SCHEMA_BASE,
    validate_record,
)
from manosube_agent_civilization.reflow.closure import evaluate_closure
from manosube_agent_civilization.reflow.engine import decide_transition
from manosube_agent_civilization.reflow.errors import ReflowValidationError
from manosube_agent_civilization.reflow.lifecycle import mint_transition_event

REFLOW_TRANSITION_REF = {"kind": "reflow_transition", "id": "TX-" + "1" * 64}


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


def test_closed_event_is_schema_valid_and_binds_to_the_evaluation() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    evaluation = evaluate_closure(candidate_closure_request(difference, policy))
    decision = decide_transition(evaluation, "VERIFYING")

    event = mint_transition_event(
        difference=difference,
        current_status="VERIFYING",
        previous_event_id=difference["genesis_event_ref"]["id"],
        event_revision=1,
        decision=decision,
        evaluation=evaluation,
        observation_refs=evaluation["after_observation_refs"],
        evidence_refs=evaluation["change_free_verification_evidence_refs"],
        reflow_transition_ref=REFLOW_TRANSITION_REF,
    )

    validate_record(event, "difference_lifecycle_event.schema.json", base=DIFFERENCE_SCHEMA_BASE)
    assert event["to_status"] == "CLOSED"
    assert event["closure_evaluation_ref"] == {
        "kind": "closure_evaluation",
        "id": evaluation["closure_evaluation_id"],
    }
    assert event["reflow_transition_ref"] == REFLOW_TRANSITION_REF

    errors = closure_evaluation_binding_errors(
        event,
        None,
        difference,
        {evaluation["closure_evaluation_id"]: evaluation},
        {policy["closure_policy_id"]: policy},
        policy_semantic_fingerprint,
    )
    assert errors == []


def test_closed_without_reflow_transition_ref_is_refused() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    evaluation = evaluate_closure(candidate_closure_request(difference, policy))
    decision = decide_transition(evaluation, "VERIFYING")

    with pytest.raises(ReflowValidationError):
        mint_transition_event(
            difference=difference,
            current_status="VERIFYING",
            previous_event_id=difference["genesis_event_ref"]["id"],
            event_revision=1,
            decision=decision,
            evaluation=evaluation,
            observation_refs=evaluation["after_observation_refs"],
            evidence_refs=evaluation["change_free_verification_evidence_refs"],
        )


def test_blocked_event_is_schema_valid_with_a_full_blocker_payload() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    evaluation = evaluate_closure(base_closure_request(difference, policy))
    decision = decide_transition(evaluation, "VERIFYING")

    event = mint_transition_event(
        difference=difference,
        current_status="VERIFYING",
        previous_event_id=difference["genesis_event_ref"]["id"],
        event_revision=1,
        decision=decision,
        evaluation=evaluation,
        observation_refs=[],
        evidence_refs=[{"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}],
        blocker_kind="OBSERVATION_PATH",
        blocker_scope=_blocker_scope(difference),
        blocker_resolution_condition=_blocker_condition(difference),
        next_observation_ref=NEXT_OBSERVATION_REF,
    )

    validate_record(event, "difference_lifecycle_event.schema.json", base=DIFFERENCE_SCHEMA_BASE)
    assert event["to_status"] == "BLOCKED"
    assert event["reflow_transition_ref"] is None


def test_blocked_without_next_observation_ref_is_refused() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    evaluation = evaluate_closure(base_closure_request(difference, policy))
    decision = decide_transition(evaluation, "VERIFYING")

    with pytest.raises(ReflowValidationError):
        mint_transition_event(
            difference=difference,
            current_status="VERIFYING",
            previous_event_id=difference["genesis_event_ref"]["id"],
            event_revision=1,
            decision=decision,
            evaluation=evaluation,
            observation_refs=[],
            evidence_refs=[{"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}],
            blocker_kind="OBSERVATION_PATH",
            blocker_scope=_blocker_scope(difference),
            blocker_resolution_condition=_blocker_condition(difference),
        )


def test_illegal_transition_is_refused_before_any_field_is_built() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    evaluation = evaluate_closure(candidate_closure_request(difference, policy))
    decision = decide_transition(evaluation, "VERIFYING")

    with pytest.raises(ReflowValidationError):
        mint_transition_event(
            difference=difference,
            current_status="CLOSED",  # CLOSED -> CLOSED is not a legal transition
            previous_event_id=difference["genesis_event_ref"]["id"],
            event_revision=1,
            decision=decision,
            evaluation=evaluation,
            observation_refs=evaluation["after_observation_refs"],
            evidence_refs=evaluation["change_free_verification_evidence_refs"],
            reflow_transition_ref=REFLOW_TRANSITION_REF,
        )
