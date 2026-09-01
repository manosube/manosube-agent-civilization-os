"""Mutation coverage for the Closure Evaluation to lifecycle-event binding.

A Closure Evaluation is later-phase provenance: this phase does not execute one and claims
nothing about how it was decided. What it does decide is whether the *binding* an event
declares is authentic. That binding sits entirely outside lifecycle event identity, so a
schema-valid ``RETAINED`` event could keep its ``difference_event_id`` while its Evaluation
proposed ``BLOCKED`` -- both values valid under the Evaluation schema, every reference
resolvable -- and the Engine accepted it while the independent auditor rejected it.

The rules now live once, in the lifecycle authority both consumers import.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
import scripts.difference_contract_validator as validator
from tests.difference_helpers import retained_status_predecessor

from manosube_agent_civilization.difference import DifferenceError, derive_differences
from manosube_agent_civilization.difference.graph import reference_closure_errors
from manosube_agent_civilization.difference.lifecycle import (
    REQUIRES_CLOSURE_EVALUATION,
    closure_evaluation_binding_errors,
)

_BOUND_STATUSES = ("BLOCKED", "RETAINED")


def _request(status: str) -> dict[str, Any]:
    _, request = retained_status_predecessor(status)
    return request


def _evaluation(request: dict[str, Any]) -> dict[str, Any]:
    evaluation: dict[str, Any] = request["bindings"][0]["predecessor"]["context"][
        "evaluations"
    ][0]
    return evaluation


def test_the_engine_and_the_auditor_share_one_binding_authority() -> None:
    assert vars(validator)["closure_evaluation_binding_errors"] is closure_evaluation_binding_errors
    assert {"CLOSED", "BLOCKED", "RETAINED"} == REQUIRES_CLOSURE_EVALUATION


@pytest.mark.parametrize("status", _BOUND_STATUSES)
def test_the_unmutated_lineage_is_accepted_and_cross_record_valid(status: str) -> None:
    bundle = derive_differences(_request(status))
    assert validator.validate_bundle(bundle) == []


@pytest.mark.parametrize("status", _BOUND_STATUSES)
def test_a_proposed_terminal_status_that_is_not_the_entered_status_fails_closed(
    status: str,
) -> None:
    """The reviewed defect, reproduced and now rejected by the producer as well."""

    other = "BLOCKED" if status == "RETAINED" else "RETAINED"
    request = _request(status)
    _evaluation(request)["proposed_terminal_status"] = other
    before = deepcopy(request)
    with pytest.raises(DifferenceError, match="terminal evaluation binding mismatch"):
        derive_differences(request)
    assert request == before


@pytest.mark.parametrize("status", _BOUND_STATUSES)
def test_an_evaluation_bound_to_another_difference_fails_closed(status: str) -> None:
    request = _request(status)
    _evaluation(request)["difference_id"] = "D-" + "0" * 64
    with pytest.raises(DifferenceError):
        derive_differences(request)


@pytest.mark.parametrize("status", _BOUND_STATUSES)
def test_an_evaluation_bound_to_the_wrong_event_head_fails_closed(status: str) -> None:
    request = _request(status)
    evaluation = _evaluation(request)
    evaluation["difference_event_head_ref"] = {
        "kind": "difference_event",
        "id": request["bindings"][0]["predecessor"]["events"][0]["difference_event_id"],
    }
    with pytest.raises(DifferenceError, match="terminal evaluation binding mismatch"):
        derive_differences(request)


@pytest.mark.parametrize("status", _BOUND_STATUSES)
def test_an_evaluation_naming_another_closure_policy_fails_closed(status: str) -> None:
    request = _request(status)
    evaluation = _evaluation(request)
    evaluation["policy_ref"] = {
        **deepcopy(evaluation["policy_ref"]),
        "semantic_fingerprint": "sha256:" + "0" * 64,
    }
    with pytest.raises(DifferenceError):
        derive_differences(request)


@pytest.mark.parametrize("status", _BOUND_STATUSES)
def test_an_evaluation_of_another_state_revision_fails_closed(status: str) -> None:
    request = _request(status)
    _evaluation(request)["evaluated_state_revision"] = 99
    with pytest.raises(DifferenceError, match="terminal evaluation binding mismatch"):
        derive_differences(request)


@pytest.mark.parametrize("status", _BOUND_STATUSES)
def test_an_evaluation_of_another_state_fingerprint_fails_closed(status: str) -> None:
    request = _request(status)
    evaluation = _evaluation(request)
    evaluation["evaluated_state_fingerprint"] = {
        **deepcopy(evaluation["evaluated_state_fingerprint"]),
        "digest": "0" * 64,
    }
    with pytest.raises(DifferenceError, match="terminal evaluation binding mismatch"):
        derive_differences(request)


@pytest.mark.parametrize("status", _BOUND_STATUSES)
def test_an_evaluation_of_another_target_predicate_fails_closed(status: str) -> None:
    request = _request(status)
    _evaluation(request)["target_predicate_ref"] = {
        "kind": "target_predicate",
        "id": "TP-9999",
    }
    with pytest.raises(DifferenceError):
        derive_differences(request)


@pytest.mark.parametrize("status", _BOUND_STATUSES)
def test_an_evaluation_of_another_objective_semantics_fails_closed(status: str) -> None:
    request = _request(status)
    _evaluation(request)["objective_semantic_fingerprint_evaluated"] = "sha256:" + "0" * 64
    with pytest.raises(DifferenceError, match="terminal evaluation binding mismatch"):
        derive_differences(request)


@pytest.mark.parametrize("status", _BOUND_STATUSES)
def test_a_failing_terminal_gate_fails_closed(status: str) -> None:
    """The canonical schema pins G22 for a terminal Evaluation, so this fails earlier."""

    request = _request(status)
    _evaluation(request)["gate_results"]["G22"] = "FAIL"
    with pytest.raises(DifferenceError):
        derive_differences(request)


def test_a_reopen_that_contradicts_another_closure_fails_closed() -> None:
    """A reopen must name the very Evaluation its CLOSED head named."""

    request = _request("REOPENED")
    events = request["bindings"][0]["predecessor"]["events"]
    closed = next(event for event in events if event["to_status"] == "CLOSED")
    closed["closure_evaluation_ref"] = None
    with pytest.raises(DifferenceError):
        derive_differences(request)


#: What the auditor still reports for a REOPENED lineage, and why. Every one of these is
#: *Closure Evaluation execution* provenance -- candidate claim and invariant bindings,
#: Evidence sufficiency, mandatory gate outcomes, the Reflow commitment and the VERIFYING
#: minimum gate. Those are owned by later elements this phase does not implement, and
#: fabricating them here would be implementing Closure Evaluation execution rather than
#: validating caller-supplied provenance. The set is enumerated so the non-claim is exact:
#: a *new* kind of error, or a binding error, fails this test.
REOPENED_LATER_PHASE_NON_CLAIMS = frozenset(
    {
        "Evidence Sufficiency binding mismatch",
        "after-state Observation binding mismatch",
        "candidate claim binding set mismatch",
        "candidate input binding mismatch",
        "closed reflow commitment mismatch",
        "closure Evidence binding incomplete",
        "closure has non-PASS mandatory gate",
        "kernel invariant source mismatch",
        "verifying minimum gate missing",
    }
)


def test_reopened_binding_rules_hold_and_the_non_claim_is_exactly_stated() -> None:
    """REOPENED is validated, not skipped -- and what remains unproven is named."""

    bundle = derive_differences(_request("REOPENED"))
    statuses = set(bundle["materialized_status"].values())
    assert "REOPENED" in statuses
    reported = {error.split(":")[0] for error in validator.validate_bundle(bundle)}
    # Every binding rule this phase owns holds.
    assert "reopen closure binding mismatch" not in reported
    assert "terminal evaluation binding mismatch" not in reported
    assert "next observation binding mismatch" not in reported
    assert "next observation reason does not match status" not in reported
    assert reference_closure_errors(bundle) == []
    # And nothing else is reported beyond the enumerated later-phase non-claims.
    assert reported <= REOPENED_LATER_PHASE_NON_CLAIMS, sorted(
        reported - REOPENED_LATER_PHASE_NON_CLAIMS
    )


def test_an_event_naming_an_unresolvable_evaluation_fails_closed() -> None:
    request = _request("RETAINED")
    context = request["bindings"][0]["predecessor"]["context"]
    context["evaluations"] = []
    with pytest.raises(DifferenceError):
        derive_differences(request)
