"""Bounded Negative Evidence is a channel, not a bag.

A Negative Observation Evaluation identity is derived from its owning record and its
revision alone, so an evaluation can keep its ``evaluation_id`` while its Evidence list is
replaced entirely. Consumers trusted the status and checked only that the owning record
carried *some* Evidence, so a proven ``ABSENT`` could rest on Evidence belonging to another
observation, or on Observation Evidence -- collapsing two provenance channels the contract
keeps distinct.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
import scripts.difference_contract_validator as validator
from tests.difference_helpers import (
    PREDICATE_ID,
    derivation_request,
    negative_claim,
    objective_revision,
    observation_scope,
    observed_bundle,
    state_fingerprint,
)

from manosube_agent_civilization.difference import DifferenceError, derive_differences
from manosube_agent_civilization.observation.verification import (
    EVIDENCE_BOUND_NEGATIVE_STATUSES,
    negative_evaluation_evidence_errors,
    observation_record_errors,
)

FOREIGN = {"kind": "negative_evidence", "id": "NEG-EVID-FOREIGN"}
OBSERVATION_EVIDENCE = {"kind": "observation_evidence", "id": "EVID-0001"}


def _negative_request(mutate: Any = None) -> dict[str, Any]:
    fingerprint = state_fingerprint()
    scope = observation_scope()
    bundle = observed_bundle(
        scope, [], fingerprint, negative_claims=[negative_claim("ABSENT")]
    )
    if mutate is not None:
        mutate(bundle)
    return derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": bundle,
            }
        ],
        fingerprint,
    )


def test_the_authority_is_shared_by_both_owners() -> None:
    """One rule object, owned by the Observation element, not two algorithms."""

    assert (
        vars(validator)["negative_evaluation_evidence_errors"]
        is negative_evaluation_evidence_errors
    )
    assert negative_evaluation_evidence_errors.__module__.endswith("observation.verification")
    assert {"ABSENT", "EMPTY"} == EVIDENCE_BOUND_NEGATIVE_STATUSES


def test_the_unmutated_pure_negative_route_is_unaffected() -> None:
    bundle = derive_differences(_negative_request())
    assert validator.validate_bundle(bundle) == []
    assert bundle["negative_observation_evaluations"]


@pytest.mark.parametrize(
    "forged",
    [[FOREIGN], [OBSERVATION_EVIDENCE], [FOREIGN, OBSERVATION_EVIDENCE]],
    ids=["foreign-negative", "observation-channel", "both"],
)
def test_evidence_outside_the_owning_channel_fails_closed(
    forged: list[dict[str, str]]
) -> None:
    def mutate(bundle: dict[str, Any]) -> None:
        bundle["negative_evaluations"][0]["evidence_refs"] = deepcopy(forged)

    with pytest.raises(DifferenceError, match="not declared by its own channel"):
        derive_differences(_negative_request(mutate))


@pytest.mark.parametrize("status", sorted(EVIDENCE_BOUND_NEGATIVE_STATUSES))
def test_a_bounded_negative_conclusion_requires_its_evidence(status: str) -> None:
    errors = negative_evaluation_evidence_errors(
        {
            "negative_observations": [
                {
                    "negative_observation_id": "NEG-1",
                    "observation_id": "OBS-1",
                    "negative_evidence_refs": [FOREIGN],
                }
            ],
            "negative_evaluations": [
                {
                    "evaluation_id": "NEG-EVAL-1",
                    "negative_observation_id": "NEG-1",
                    "evaluation_status": status,
                    "evidence_refs": [],
                }
            ],
        }
    )
    assert any("carries no bounded" in error for error in errors), errors


@pytest.mark.parametrize("status", ["NO_RESULT", "UNOBSERVED"])
def test_a_status_that_concludes_nothing_requires_no_evidence(status: str) -> None:
    """NO_RESULT is not proven absence, so no Evidence is demanded for it."""

    assert negative_evaluation_evidence_errors(
        {
            "negative_observations": [
                {
                    "negative_observation_id": "NEG-1",
                    "observation_id": "OBS-1",
                    "negative_evidence_refs": [],
                }
            ],
            "negative_evaluations": [
                {
                    "evaluation_id": "NEG-EVAL-1",
                    "negative_observation_id": "NEG-1",
                    "evaluation_status": status,
                    "evidence_refs": [],
                }
            ],
        }
    ) == []


def test_a_contradiction_may_cite_its_own_observation_evidence() -> None:
    """CONFLICTED concludes the negative claim was contradicted by an observed Fact."""

    payload = {
        "negative_observations": [
            {
                "negative_observation_id": "NEG-1",
                "observation_id": "OBS-1",
                "negative_evidence_refs": [FOREIGN],
            }
        ],
        "observations": [
            {"observation_id": "OBS-1", "observation_evidence_refs": [OBSERVATION_EVIDENCE]}
        ],
        "negative_evaluations": [
            {
                "evaluation_id": "NEG-EVAL-1",
                "negative_observation_id": "NEG-1",
                "evaluation_status": "CONFLICTED",
                "evidence_refs": [OBSERVATION_EVIDENCE],
            }
        ],
    }
    assert negative_evaluation_evidence_errors(payload) == []
    # It is still bound: Evidence no Observation of its own declared fails closed.
    payload["negative_evaluations"][0]["evidence_refs"] = [
        {"kind": "observation_evidence", "id": "EVID-ELSEWHERE"}
    ]
    assert negative_evaluation_evidence_errors(payload)


def test_an_evaluation_whose_owner_cannot_be_resolved_fails_closed() -> None:
    errors = negative_evaluation_evidence_errors(
        {
            "negative_observations": [],
            "negative_evaluations": [
                {
                    "evaluation_id": "NEG-EVAL-1",
                    "negative_observation_id": "NEG-ABSENT",
                    "evaluation_status": "ABSENT",
                    "evidence_refs": [],
                }
            ],
        }
    )
    assert any("no resolvable owner" in error for error in errors), errors


def test_the_observation_element_applies_the_same_rule_to_its_own_output() -> None:
    """The rule reaches every consumer through the shared record verifier."""

    fingerprint = state_fingerprint()
    bundle = observed_bundle(
        observation_scope(), [], fingerprint, negative_claims=[negative_claim("ABSENT")]
    )
    assert observation_record_errors(bundle) == []
    bundle["negative_evaluations"][0]["evidence_refs"] = [FOREIGN]
    assert any(
        "not declared by its own channel" in error
        for error in observation_record_errors(bundle)
    )
