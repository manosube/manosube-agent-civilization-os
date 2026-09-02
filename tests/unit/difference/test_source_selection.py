"""Which Facts and which Target Predicate a derivation is actually built from.

Two findings, one mistake: the Engine read a *container* as the source set. An Observation
over a multi-subject Scope carries Facts for other subjects, and an Objective can declare
two Target Predicates under one identity. Selection is now decided by one authority the
independent validator also imports.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from scripts.difference_contract_validator import validate_bundle
from tests.difference_helpers import (
    PREDICATE_ID,
    PROJECT_ID,
    derivation_request,
    objective_revision,
    observation_scope,
    observed_bundle,
    raw_fact,
    state_fingerprint,
    target_predicate,
)

from manosube_agent_civilization.difference import DifferenceError, derive_differences
from manosube_agent_civilization.difference.errors import IdentityCollisionError
from manosube_agent_civilization.difference.selection import (
    contributing_facts,
    unique_target_predicates,
)
from manosube_agent_civilization.observation.identity import (
    binding_identity,
    fact_evaluation_identity,
)

TARGET_SUBJECT = "kernel.state"
OTHER_SUBJECT = "kernel.other"
BOTH = [TARGET_SUBJECT, OTHER_SUBJECT]


# --------------------------------------------------------------------------- #
# Contributing Fact selection
# --------------------------------------------------------------------------- #


def _multi_subject_request(facts: list[dict[str, Any]]) -> dict[str, Any]:
    fingerprint = state_fingerprint()
    scope = observation_scope(included=BOTH)
    bundle = observed_bundle(scope, facts, fingerprint)
    return derivation_request(
        objective_revision([target_predicate(subject=TARGET_SUBJECT)]),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": bundle,
            }
        ],
        fingerprint,
    )


def test_a_multi_subject_observation_derives_from_the_target_subject_only() -> None:
    request = _multi_subject_request(
        [raw_fact(subject=TARGET_SUBJECT), raw_fact(subject=OTHER_SUBJECT, value="IRRELEVANT")]
    )
    bundle = derive_differences(request)
    observed = bundle["differences"][0]["normalized_observed_state"]
    assert [item["value"] for item in observed["value_candidates"]["members"]] == ["NOT-READY"]
    assert validate_bundle(bundle) == []


def test_the_unrelated_subject_still_travels_as_provenance() -> None:
    """Selection narrows what contributes; it never discards what was observed."""

    request = _multi_subject_request(
        [raw_fact(subject=TARGET_SUBJECT), raw_fact(subject=OTHER_SUBJECT, value="IRRELEVANT")]
    )
    bundle = derive_differences(request)
    assert {fact["subject"] for fact in bundle["normalized_facts"]} == set(BOTH)
    observation = bundle["observations"][0]
    assert len(observation["normalized_fact_refs"]) == 2


def test_input_order_does_not_change_the_selection() -> None:
    forward = derive_differences(
        _multi_subject_request(
            [raw_fact(subject=TARGET_SUBJECT), raw_fact(subject=OTHER_SUBJECT, value="X")]
        )
    )
    reverse = derive_differences(
        _multi_subject_request(
            [raw_fact(subject=OTHER_SUBJECT, value="X"), raw_fact(subject=TARGET_SUBJECT)]
        )
    )
    assert forward["differences"][0]["difference_id"] == reverse["differences"][0]["difference_id"]


def test_an_observation_with_no_fact_for_the_target_fails_closed() -> None:
    request = _multi_subject_request([raw_fact(subject=OTHER_SUBJECT, value="X")])
    with pytest.raises(DifferenceError, match="no positive Fact"):
        derive_differences(request)


def _foreign_project_request() -> tuple[dict[str, Any], str]:
    """A genuinely minted Fact for another project, spliced into this Observation."""

    import tests.difference_helpers as helpers

    fingerprint = state_fingerprint()
    scope = observation_scope()
    ours = observed_bundle(scope, [raw_fact(value="NOT-READY")], fingerprint)

    original = helpers.PROJECT_ID
    helpers.PROJECT_ID = "PRJ-OTHER"
    try:
        foreign = observed_bundle(
            observation_scope(), [raw_fact(value="FOREIGN")], state_fingerprint()
        )
    finally:
        helpers.PROJECT_ID = original

    foreign_fact = deepcopy(foreign["facts"][0])
    ours["facts"].append(foreign_fact)
    ours["observations"][0]["normalized_fact_refs"].append(
        {"kind": "normalized_fact", "id": foreign_fact["fact_id"]}
    )
    binding = deepcopy(ours["bindings"][0])
    binding["fact_id"] = foreign_fact["fact_id"]
    binding["binding_id"] = binding_identity(binding)
    ours["bindings"].append(binding)
    evaluation = deepcopy(ours["fact_evaluations"][0])
    evaluation["fact_id"] = foreign_fact["fact_id"]
    evaluation["binding_refs"] = [
        {"kind": "fact_observation_binding", "id": binding["binding_id"]}
    ]
    evaluation["evaluation_id"] = fact_evaluation_identity(evaluation)
    ours["fact_evaluations"].append(evaluation)
    request = derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": ours,
            }
        ],
        fingerprint,
    )
    return request, foreign_fact["fact_id"]


def test_a_same_subject_fact_from_another_project_never_contributes() -> None:
    """Its identity recomputes perfectly, so only the project check can exclude it."""

    request, foreign_id = _foreign_project_request()
    bundle = derive_differences(request)
    observed = bundle["differences"][0]["normalized_observed_state"]
    values = [item["value"] for item in observed["value_candidates"]["members"]]
    assert values == ["NOT-READY"]
    assert "FOREIGN" not in values
    assert foreign_id in {fact["fact_id"] for fact in bundle["normalized_facts"]}
    assert validate_bundle(bundle) == []


def test_the_selector_is_a_pure_function_of_project_and_subject() -> None:
    facts = {
        "F-A": {"fact_id": "F-A", "project_id": PROJECT_ID, "subject": TARGET_SUBJECT},
        "F-B": {"fact_id": "F-B", "project_id": PROJECT_ID, "subject": OTHER_SUBJECT},
        "F-C": {"fact_id": "F-C", "project_id": "PRJ-OTHER", "subject": TARGET_SUBJECT},
    }
    observation = {
        "normalized_fact_refs": [
            {"kind": "normalized_fact", "id": identity} for identity in ("F-C", "F-B", "F-A")
        ]
    }
    selected = contributing_facts(observation, facts, TARGET_SUBJECT, PROJECT_ID)
    assert [fact["fact_id"] for fact in selected] == ["F-A"]
    # A reference of another kind, and a reference to an absent Fact, are simply not
    # selected -- their own gates decide them.
    observation["normalized_fact_refs"].extend(
        [{"kind": "observation", "id": "F-A"}, {"kind": "normalized_fact", "id": "F-MISSING"}]
    )
    assert [fact["fact_id"] for fact in contributing_facts(
        observation, facts, TARGET_SUBJECT, PROJECT_ID
    )] == ["F-A"]


# --------------------------------------------------------------------------- #
# Target Predicate identity
# --------------------------------------------------------------------------- #


def _duplicate_predicate_request(second: dict[str, Any]) -> dict[str, Any]:
    fingerprint = state_fingerprint()
    scope = observation_scope()
    bundle = observed_bundle(scope, [raw_fact(value="NOT-READY")], fingerprint)
    return derivation_request(
        objective_revision([target_predicate(), second]),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": bundle,
            }
        ],
        fingerprint,
    )


@pytest.mark.parametrize(
    "second",
    [
        target_predicate(expected_value="DEGRADED"),
        target_predicate(subject=OTHER_SUBJECT),
        target_predicate(operator="not_equals"),
        target_predicate(observation_scope="other"),
    ],
    ids=["expected_value", "subject", "operator", "observation_scope"],
)
def test_two_predicates_under_one_identity_fail_closed(second: dict[str, Any]) -> None:
    request = _duplicate_predicate_request(second)
    before = deepcopy(request)
    with pytest.raises(IdentityCollisionError, match=PREDICATE_ID):
        derive_differences(request)
    assert request == before


def test_the_rejection_does_not_depend_on_declaration_order() -> None:
    fingerprint = state_fingerprint()
    scope = observation_scope()
    bundle = observed_bundle(scope, [raw_fact(value="NOT-READY")], fingerprint)
    reversed_objective = objective_revision(
        [target_predicate(expected_value="DEGRADED"), target_predicate()]
    )
    request = derivation_request(
        reversed_objective,
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": bundle,
            }
        ],
        fingerprint,
    )
    with pytest.raises(IdentityCollisionError, match=PREDICATE_ID):
        derive_differences(request)


def test_an_identical_duplicate_is_idempotent() -> None:
    objective = objective_revision([target_predicate(), target_predicate()])
    predicates = unique_target_predicates(objective)
    assert list(predicates) == [PREDICATE_ID]


def test_a_single_predicate_objective_is_unaffected() -> None:
    predicates = unique_target_predicates(objective_revision())
    assert list(predicates) == [PREDICATE_ID]
    assert predicates[PREDICATE_ID]["expected_value"] == "READY"


def test_a_predicate_without_an_identity_fails_closed() -> None:
    objective = objective_revision()
    del objective["target_predicates"][0]["predicate_id"]
    with pytest.raises(DifferenceError, match="no identity"):
        unique_target_predicates(objective)
