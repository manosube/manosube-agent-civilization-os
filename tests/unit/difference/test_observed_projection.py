"""Unit proofs for the corrected observed-state projection.

Covers the two contract corrections recorded in
``docs/decisions/ADR-0002-DIFFERENCE_OBSERVED_PROJECTION_CORRECTIONS.md``:
the bounded pure-negative route, and lossless multi-candidate projection.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from tests.difference_helpers import (
    PREDICATE_ID,
    SUBJECT,
    binding_request,
    derivation_request,
    negative_claim,
    objective_revision,
    observation_scope,
    observed_bundle,
    raw_fact,
    state_fingerprint,
    target_predicate,
)

from manosube_agent_civilization.difference import DifferenceError, derive_differences
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

# negative_status -> (observed knowledge status, mismatch kind, comparison result)
_NEGATIVE_ROUTES = {
    "ABSENT": ("ABSENT", "MISSING", "NOT_SATISFIED"),
    "EMPTY": ("EMPTY", "MISSING", "NOT_SATISFIED"),
    "NO_RESULT": ("UNKNOWN", "UNKNOWN", "UNKNOWN"),
    "UNOBSERVED": ("UNOBSERVED", "UNKNOWN", "UNKNOWN"),
}


def _difference(bundle: dict[str, Any]) -> dict[str, Any]:
    assert len(bundle["differences"]) == 1
    difference: dict[str, Any] = bundle["differences"][0]
    return difference


# --------------------------------------------------------------------------- #
# Blocker 1: the bounded pure-negative route is canonically representable.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("negative_status", sorted(_NEGATIVE_ROUTES))
def test_pure_negative_route_derives_a_difference(negative_status: str) -> None:
    bundle = derive_differences(
        binding_request([], negative_claims=[negative_claim(negative_status)])
    )
    knowledge, mismatch, comparison = _NEGATIVE_ROUTES[negative_status]
    difference = _difference(bundle)
    assert difference["normalized_observed_state"]["knowledge_status"] == knowledge
    assert difference["structural_difference"]["mismatch_kind"] == mismatch
    assert difference["structural_difference"]["comparison_result"] == comparison
    assert difference["normalized_observed_state"]["value_candidates"]["members"] == []


@pytest.mark.parametrize("negative_status", ["NO_RESULT", "UNOBSERVED"])
def test_unresolved_negative_status_is_never_proven_absence(negative_status: str) -> None:
    bundle = derive_differences(
        binding_request([], negative_claims=[negative_claim(negative_status)])
    )
    structural = _difference(bundle)["structural_difference"]
    assert structural["observed_knowledge_status"] not in {"ABSENT", "EMPTY", "KNOWN"}
    assert structural["mismatch_kind"] != "MISSING"
    assert structural["comparison_result"] == "UNKNOWN"


@pytest.mark.parametrize("negative_status", ["ABSENT", "EMPTY"])
def test_proven_absence_keeps_its_bounded_meaning(negative_status: str) -> None:
    bundle = derive_differences(
        binding_request([], negative_claims=[negative_claim(negative_status)])
    )
    structural = _difference(bundle)["structural_difference"]
    assert structural["observed_knowledge_status"] == negative_status
    assert structural["mismatch_kind"] == "MISSING"
    assert structural["comparison_result"] == "NOT_SATISFIED"


def test_difference_binds_the_exact_union_of_both_evidence_channels() -> None:
    request = binding_request([], negative_claims=[negative_claim("ABSENT")])
    observation_bundle = request["bindings"][0]["observation_bundle"]
    observation = observation_bundle["observations"][-1]
    expected = {
        canonical_json_bytes(reference)
        for reference in observation["observation_evidence_refs"]
    } | {
        canonical_json_bytes(reference)
        for negative in observation_bundle["negative_observations"]
        for reference in negative["negative_evidence_refs"]
    }
    difference = _difference(derive_differences(request))
    actual = {
        canonical_json_bytes(reference)
        for reference in difference["observation_evidence_refs"]
    }
    assert actual == expected
    kinds = {reference["kind"] for reference in difference["observation_evidence_refs"]}
    assert kinds == {"observation_evidence", "negative_evidence"}


def test_positive_only_route_binds_observation_evidence_alone() -> None:
    difference = _difference(derive_differences(binding_request([raw_fact()])))
    assert {reference["kind"] for reference in difference["observation_evidence_refs"]} == {
        "observation_evidence"
    }


def test_conflict_route_binds_both_evidence_channels() -> None:
    difference = _difference(
        derive_differences(
            binding_request([raw_fact()], negative_claims=[negative_claim("ABSENT")])
        )
    )
    assert difference["structural_difference"]["mismatch_kind"] == "CONFLICT"
    assert {reference["kind"] for reference in difference["observation_evidence_refs"]} == {
        "observation_evidence",
        "negative_evidence",
    }


def test_proven_absence_without_bounded_negative_evidence_fails_closed() -> None:
    request = binding_request([], negative_claims=[negative_claim("ABSENT")])
    for negative in request["bindings"][0]["observation_bundle"]["negative_observations"]:
        negative["negative_evidence_refs"] = []
    with pytest.raises(DifferenceError, match="requires bounded Negative Evidence"):
        derive_differences(request)


def test_pure_negative_route_is_deterministic() -> None:
    request = binding_request([], negative_claims=[negative_claim("ABSENT")])
    assert canonical_json_bytes(derive_differences(deepcopy(request))) == canonical_json_bytes(
        derive_differences(deepcopy(request))
    )


def test_invalid_negative_observation_cannot_produce_a_difference() -> None:
    request = binding_request([], negative_claims=[negative_claim("ABSENT")])
    bundle = request["bindings"][0]["observation_bundle"]
    for evaluation in bundle["negative_evaluations"]:
        evaluation["evaluation_status"] = "INVALID"
    with pytest.raises(DifferenceError, match="INVALID Negative Observation"):
        derive_differences(request)


# --------------------------------------------------------------------------- #
# Blocker 2: multiple observed candidates are projected without loss.
# --------------------------------------------------------------------------- #


def _multi_candidate_request(
    first: str = "FAIL", second: str = "BROKEN", operator: str = "all"
) -> dict[str, Any]:
    return binding_request(
        [
            raw_fact(value=first),
            raw_fact(value=second, predicate="exists@v1"),
        ],
        predicate=target_predicate(operator=operator, expected_value="PASS"),
    )


def test_candidates_sharing_a_value_type_are_all_preserved() -> None:
    difference = _difference(derive_differences(_multi_candidate_request()))
    observed = difference["normalized_observed_state"]["value_candidates"]["members"]
    structural = difference["structural_difference"]
    assert len(observed) == 2
    assert structural["observed_value_types"]["collection_kind"] == "ORDERED_LIST"
    assert structural["observed_value_types"]["members"] == ["STRING", "STRING"]
    assert structural["observed_values"]["collection_kind"] == "ORDERED_LIST"
    assert len(structural["observed_values"]["members"]) == 2


def test_candidates_sharing_a_value_and_a_type_are_all_preserved() -> None:
    difference = _difference(derive_differences(_multi_candidate_request("FAIL", "FAIL")))
    structural = difference["structural_difference"]
    assert len(difference["normalized_observed_state"]["value_candidates"]["members"]) == 2
    assert structural["observed_values"]["members"] == ["FAIL", "FAIL"]
    assert structural["observed_value_types"]["members"] == ["STRING", "STRING"]


def test_observed_projection_order_follows_the_candidate_order() -> None:
    difference = _difference(derive_differences(_multi_candidate_request()))
    candidates = difference["normalized_observed_state"]["value_candidates"]["members"]
    structural = difference["structural_difference"]
    assert structural["observed_values"]["members"] == [item["value"] for item in candidates]
    assert structural["observed_value_types"]["members"] == [
        item["value_type"] for item in candidates
    ]


def test_source_reordering_does_not_change_the_output_bytes() -> None:
    fingerprint = state_fingerprint()
    scope = observation_scope()
    facts = [raw_fact(value="FAIL"), raw_fact(value="BROKEN", predicate="exists@v1")]
    objective = objective_revision([target_predicate(operator="all", expected_value="PASS")])

    def derive(ordered_facts: list[dict[str, Any]]) -> dict[str, Any]:
        return derive_differences(
            derivation_request(
                objective,
                [
                    {
                        "target_predicate_id": PREDICATE_ID,
                        "observation_scope": scope,
                        "observation_bundle": observed_bundle(
                            scope, ordered_facts, fingerprint
                        ),
                    }
                ],
                fingerprint,
            )
        )

    forward = derive(facts)
    backward = derive(list(reversed(facts)))
    assert canonical_json_bytes(forward) == canonical_json_bytes(backward)
    assert (
        forward["differences"][0]["difference_id"]
        == backward["differences"][0]["difference_id"]
    )


def test_multi_candidate_route_keeps_the_target_subject_bound() -> None:
    difference = _difference(derive_differences(_multi_candidate_request()))
    assert difference["subject"] == SUBJECT
    assert all(
        candidate["fact_predicate"] in {"equals@v1", "exists@v1"}
        for candidate in difference["normalized_observed_state"]["value_candidates"]["members"]
    )
