"""Upstream Fact-evaluation payload proofs.

Covers the independent review finding on `9bfb176`: a Fact Evaluation identity is derived
from ``fact_id`` and ``evaluation_revision`` alone, so retaining the identity proves
nothing about the rest of the payload. Every upstream evaluation must therefore be
validated against its canonical schema and cross-record invariants -- through the single
Observation authority, never a second ruleset -- before its status, its conflict
references or its bindings are trusted.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from scripts.difference_contract_validator import validate_bundle
from scripts.observation_contract_validator import validate_bundle as audit_observation
from tests.difference_helpers import single_binding_request

from manosube_agent_civilization.difference import DifferenceError, derive_differences
from manosube_agent_civilization.observation.identity import fact_evaluation_identity
from manosube_agent_civilization.observation.verification import observation_record_errors


def _observation_bundle(request: dict[str, Any]) -> dict[str, Any]:
    bundle: dict[str, Any] = request["bindings"][0]["observation_bundle"]
    return bundle


def _evaluations(request: dict[str, Any]) -> list[dict[str, Any]]:
    evaluations: list[dict[str, Any]] = _observation_bundle(request)["fact_evaluations"]
    return evaluations


# --------------------------------------------------------------------------- #
# The exact forgery the review named: a retained identity with a mutated status.
# --------------------------------------------------------------------------- #


def test_retained_identity_with_forged_conflicted_status_is_rejected() -> None:
    """`SUPPORTED` -> `CONFLICTED` with empty conflict lists keeps the evaluation id."""

    request = single_binding_request()
    for evaluation in _evaluations(request):
        before = evaluation["evaluation_id"]
        evaluation["evaluation_status"] = "CONFLICTED"
        evaluation["conflict_fact_refs"] = []
        evaluation["conflict_negative_observation_refs"] = []
        # The identity still recomputes: identity is not payload validation.
        assert fact_evaluation_identity(evaluation) == before

    with pytest.raises(DifferenceError, match="not cross-record valid"):
        derive_differences(request)


def test_forged_conflicted_status_never_reaches_candidate_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The rejection precedes projection: no candidate is ever built from the forgery."""

    from manosube_agent_civilization.difference import engine as difference_engine

    projected: list[str] = []
    original = vars(difference_engine)["value_candidate"]

    def _record(fact: dict[str, Any], boundary: dict[str, Any]) -> dict[str, Any]:
        projected.append(fact["fact_id"])
        candidate: dict[str, Any] = original(fact, boundary)
        return candidate

    monkeypatch.setattr(difference_engine, "value_candidate", _record)

    request = single_binding_request()
    for evaluation in _evaluations(request):
        evaluation["evaluation_status"] = "CONFLICTED"
        evaluation["conflict_fact_refs"] = []
        evaluation["conflict_negative_observation_refs"] = []
    with pytest.raises(DifferenceError, match="not cross-record valid"):
        derive_differences(request)
    assert projected == []

    # The same spy proves the valid route does reach projection, so the assertion above
    # is not vacuous.
    assert derive_differences(single_binding_request())["differences"]
    assert projected != []


# --------------------------------------------------------------------------- #
# Each required conflict or reference field, mutated independently.
# --------------------------------------------------------------------------- #


def _mutation(field: str, value: Any) -> dict[str, Any]:
    request = single_binding_request()
    for evaluation in _evaluations(request):
        evaluation[field] = deepcopy(value)
    return request


@pytest.mark.parametrize(
    ("field", "value"),
    [
        # A CONFLICTED status with neither conflict channel populated.
        ("evaluation_status", "CONFLICTED"),
        # A binding reference that resolves to nothing.
        ("binding_refs", [{"kind": "fact_observation_binding", "id": "BIND-ABSENT"}]),
        # A binding reference of the wrong kind.
        ("binding_refs", [{"kind": "observation", "id": "BIND-ABSENT"}]),
        # No provenance binding at all.
        ("binding_refs", []),
        # A conflict reference naming a Negative Observation that does not answer back.
        (
            "conflict_negative_observation_refs",
            [{"kind": "negative_observation", "id": "NEG-ABSENT"}],
        ),
        # A revision that breaks the contiguous evaluation lineage.
        ("evaluation_revision", 7),
        # A predecessor claimed at revision zero.
        ("previous_evaluation_id", "FACT-EVAL-INVENTED"),
        # An unknown status value.
        ("evaluation_status", "APPROVED"),
    ],
)
def test_each_upstream_evaluation_mutation_fails_closed(field: str, value: Any) -> None:
    request = _mutation(field, value)
    with pytest.raises(DifferenceError):
        derive_differences(request)


@pytest.mark.parametrize("status", ["UNKNOWN", "INCOMPLETE", "BLOCKED", "INVALID"])
def test_a_non_supporting_evaluation_status_cannot_project_a_candidate(status: str) -> None:
    """Only SUPPORTED and CONFLICTED may carry an observed value candidate."""

    request = single_binding_request()
    for evaluation in _evaluations(request):
        evaluation["evaluation_status"] = status
    assert observation_record_errors(_observation_bundle(request)) == []
    with pytest.raises(DifferenceError, match="lacks a supporting current evaluation"):
        derive_differences(request)


def test_a_one_sided_conflict_declaration_is_rejected() -> None:
    """A CONFLICTED evaluation naming a Fact that does not name it back fails closed."""

    request = single_binding_request()
    bundle = _observation_bundle(request)
    other = bundle["facts"][0]["fact_id"]
    for evaluation in bundle["fact_evaluations"]:
        evaluation["evaluation_status"] = "CONFLICTED"
        evaluation["conflict_negative_observation_refs"] = [
            {"kind": "negative_observation", "id": other}
        ]
    with pytest.raises(DifferenceError, match="not cross-record valid"):
        derive_differences(request)


# --------------------------------------------------------------------------- #
# The valid route still derives, and every authority agrees on it.
# --------------------------------------------------------------------------- #


def test_real_observation_evaluations_still_derive_a_valid_difference() -> None:
    request = single_binding_request()
    bundle = derive_differences(deepcopy(request))
    assert bundle["differences"]
    assert validate_bundle(bundle) == []


def test_engine_authority_and_independent_auditor_agree() -> None:
    """The shared verifier and the independent Observation auditor reach one verdict."""

    valid = _observation_bundle(single_binding_request())
    assert observation_record_errors(valid) == []
    assert audit_observation(valid) == []

    forged = _observation_bundle(single_binding_request())
    for evaluation in forged["fact_evaluations"]:
        evaluation["evaluation_status"] = "CONFLICTED"
        evaluation["conflict_fact_refs"] = []
        evaluation["conflict_negative_observation_refs"] = []
    assert observation_record_errors(forged) != []


def test_the_shared_verifier_does_not_mutate_the_bundle() -> None:
    from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

    bundle = _observation_bundle(single_binding_request())
    before = canonical_json_bytes(bundle)
    observation_record_errors(bundle)
    assert canonical_json_bytes(bundle) == before
