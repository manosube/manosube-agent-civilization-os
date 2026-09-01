"""An embedded record carries an identity *and* further references.

A Closure Policy reopen condition and a required completion claim each have a `kind` and an
`id` of their own, so the reference-path inventory stopped at the outer node and the nested
`objective_revision_ref`, `subject_ref` and `target_state_ref` were never declared — and
therefore never resolved. `CLOSURE_POLICY.md` requires exact resolution of that provenance.

The cause was in the inventory walker, not the registry: it returned as soon as a node was
identity-bearing. It now records the node and keeps descending, which is what makes the
both-directions comparison in `test_reference_paths.py` able to see these locations at all.
"""

from __future__ import annotations

from typing import Any

import pytest
from scripts.difference_contract_validator import validate_bundle
from tests.difference_helpers import (
    PREDICATE_ID,
    derivation_request,
    objective_revision,
    observation_scope,
    observed_bundle,
    raw_fact,
    state_fingerprint,
)
from tests.schema_reference_paths import reference_paths

from manosube_agent_civilization.difference import DifferenceError, derive_differences
from manosube_agent_civilization.difference.graph import REFERENCE_EDGES

NESTED_POLICY_PATHS = [
    "reopen_conditions[].objective_revision_ref",
    "required_claims[].subject_ref",
    "required_claims[].target_state_ref",
]


def _request(requirements: dict[str, Any]) -> dict[str, Any]:
    fingerprint = state_fingerprint()
    scope = observation_scope()
    request = derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": observed_bundle(
                    scope, [raw_fact(value="NOT-READY")], fingerprint
                ),
            }
        ],
        fingerprint,
    )
    request["closure_policy_requirements"] = requirements
    return request


def test_the_walker_descends_past_an_identity_bearing_node() -> None:
    """The root cause: the inventory stopped at the outer embedded record."""

    found = reference_paths("difference", "closure_policy.schema.json")
    for path in NESTED_POLICY_PATHS:
        assert path in found, path


@pytest.mark.parametrize("path", NESTED_POLICY_PATHS)
def test_every_nested_policy_location_is_declared(path: str) -> None:
    assert path in {edge.path for edge in REFERENCE_EDGES["closure_policy"]}


def test_the_control_policy_route_is_accepted() -> None:
    bundle = derive_differences(_request({"minimum_evidence_level": "E1"}))
    assert validate_bundle(bundle) == []


def test_an_absent_reopen_condition_objective_revision_fails_closed() -> None:
    request = _request(
        {
            "minimum_evidence_level": "E1",
            "reopen_conditions": [
                {
                    "kind": "target_predicate",
                    "id": "TP-REOPEN-0001",
                    "predicate_semantic_fingerprint": "sha256:" + "b" * 64,
                    "objective_revision_ref": {
                        "kind": "objective_revision",
                        "id": "OBJ-REV-ABSENT",
                    },
                }
            ],
        }
    )
    with pytest.raises(DifferenceError, match="objective_revisions:OBJ-REV-ABSENT"):
        derive_differences(request)


def test_a_resolving_reopen_condition_is_accepted() -> None:
    request = _request(
        {
            "minimum_evidence_level": "E1",
            "reopen_conditions": [
                {
                    "kind": "target_predicate",
                    "id": "TP-REOPEN-0001",
                    "predicate_semantic_fingerprint": "sha256:" + "b" * 64,
                    "objective_revision_ref": {
                        "kind": "objective_revision",
                        "id": "OBJ-REV-0001",
                    },
                }
            ],
        }
    )
    bundle = derive_differences(request)
    condition = bundle["policies"][0]["reopen_conditions"][0]
    assert condition["objective_revision_ref"]["id"] == "OBJ-REV-0001"
    assert validate_bundle(bundle) == []


def test_a_wrong_kind_in_a_nested_policy_reference_fails_closed() -> None:
    request = _request(
        {
            "minimum_evidence_level": "E1",
            "reopen_conditions": [
                {
                    "kind": "target_predicate",
                    "id": "TP-REOPEN-0001",
                    "predicate_semantic_fingerprint": "sha256:" + "b" * 64,
                    "objective_revision_ref": {
                        "kind": "observation",
                        "id": "OBJ-REV-0001",
                    },
                }
            ],
        }
    )
    with pytest.raises(DifferenceError, match="reference kind is not permitted here"):
        derive_differences(request)


def test_a_nested_reference_in_a_reopen_condition_evaluation_is_declared() -> None:
    """The same walker fix surfaced this location on the evaluation record."""

    declared = {edge.path for edge in REFERENCE_EDGES["reopen_condition_evaluation"]}
    assert "condition_ref.objective_revision_ref" in declared
