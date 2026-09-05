"""Real injected-violation tests for Reflow's transition decision layer (RF4)."""

from __future__ import annotations

import pytest
from tests.reflow_helpers import (
    base_closure_request,
    candidate_closure_request,
    fixture_difference,
    fixture_policy,
)

from manosube_agent_civilization.reflow.closure import evaluate_closure
from manosube_agent_civilization.reflow.engine import REASON_CODES, decide_transition
from manosube_agent_civilization.reflow.errors import ReflowValidationError


def test_satisfied_evaluation_admits_closed() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    evaluation = evaluate_closure(candidate_closure_request(difference, policy))

    decision = decide_transition(evaluation, "VERIFYING")

    assert decision["to_status"] == "CLOSED"
    assert decision["reason_code"] == REASON_CODES["SATISFIED"]
    assert decision["closure_evaluation_ref"] == {
        "kind": "closure_evaluation",
        "id": evaluation["closure_evaluation_id"],
    }


def test_blocked_evaluation_admits_the_proposed_status() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    evaluation = evaluate_closure(base_closure_request(difference, policy))

    decision = decide_transition(evaluation, "VERIFYING")

    assert evaluation["result"] == "BLOCKED"
    assert decision["to_status"] == "BLOCKED"
    assert decision["reason_code"] == REASON_CODES["BLOCKED"]


def test_current_status_no_longer_matches_is_rejected() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    evaluation = evaluate_closure(candidate_closure_request(difference, policy))

    # The Difference moved to CLOSED (say, another caller already closed it) between the
    # Evaluation being produced and this decision being applied. VERIFYING -> CLOSED is
    # legal; CLOSED -> CLOSED is not, and admitting it anyway would double-close.
    with pytest.raises(ReflowValidationError):
        decide_transition(evaluation, "CLOSED")


def test_unknown_result_admits_no_decision() -> None:
    difference = fixture_difference()
    policy = fixture_policy(difference)
    evaluation = evaluate_closure(base_closure_request(difference, policy))
    evaluation = dict(evaluation)
    evaluation["result"] = "EVALUATING"

    with pytest.raises(ReflowValidationError):
        decide_transition(evaluation, "VERIFYING")
