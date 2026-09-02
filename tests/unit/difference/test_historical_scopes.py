"""A fresh derivation across a Scope change, with no Difference predecessor.

An append-only Observation lineage keeps a recurring Fact's evaluation chain across a Scope
change, so the context closure reaches the prior Observation. Where a Difference
predecessor exists, the prior Scope travels as carried context. A *fresh* derivation has no
predecessor, and the canonical Observation bundle carries no Scope section of its own, so
the historical Scope could never be present and a valid derivation was unbuildable.

``binding["historical_observation_scopes"]`` is the explicit supply route. It supplies
records only: every Scope crosses the same canonical input gate, the resolved Scope remains
the sole boundary of the Difference derived here, and a Scope no carried Observation names
is rejected rather than emitted.
"""

from __future__ import annotations

from copy import deepcopy
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

from manosube_agent_civilization.difference import DifferenceError, derive_differences
from manosube_agent_civilization.difference.admissibility import BINDING_KEYS
from manosube_agent_civilization.difference.errors import (
    BoundaryViolationError,
    IdentityCollisionError,
)

SCOPE_A = "OBS-SCOPE-0001"
SCOPE_B = "OBS-SCOPE-0002"


def _lineage() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    first_fingerprint = state_fingerprint()
    later_fingerprint = state_fingerprint("KNOWN")
    scope_a = observation_scope(scope_id=SCOPE_A)
    scope_b = observation_scope(scope_id=SCOPE_B)
    fact = raw_fact()
    first = observed_bundle(scope_a, [fact], first_fingerprint)
    later = observed_bundle(
        scope_b, [fact], later_fingerprint, state_revision=7, prior_bundle=first
    )
    return scope_a, scope_b, later


def _request(historical: list[dict[str, Any]] | None) -> dict[str, Any]:
    _scope_a, scope_b, later = _lineage()
    binding: dict[str, Any] = {
        "target_predicate_id": PREDICATE_ID,
        "observation_scope": scope_b,
        "observation_bundle": later,
    }
    if historical is not None:
        binding["historical_observation_scopes"] = historical
    return derivation_request(
        objective_revision(), [binding], state_fingerprint("KNOWN"), 7
    )


def test_the_lineage_really_spans_two_scopes_with_one_recurring_fact() -> None:
    _, _, later = _lineage()
    assert {item["scope_ref"]["id"] for item in later["observations"]} == {SCOPE_A, SCOPE_B}
    assert len({item["fact_id"] for item in later["facts"]}) == 1
    assert "observation_scopes" not in later, (
        "the canonical Observation bundle carries no Scope section, which is why an "
        "explicit supply route is required"
    )


def test_without_the_historical_scope_the_derivation_fails_closed_precisely() -> None:
    with pytest.raises(DifferenceError, match="names a Scope absent from the bundle"):
        derive_differences(_request(None))


def test_with_the_historical_scope_the_fresh_derivation_succeeds() -> None:
    scope_a, _, _ = _lineage()
    bundle = derive_differences(_request([scope_a]))
    assert {item["scope_id"] for item in bundle["observation_scopes"]} == {SCOPE_A, SCOPE_B}
    assert validate_bundle(bundle) == []
    assert len(bundle["differences"]) == 1


def test_the_resolved_scope_remains_the_difference_boundary() -> None:
    scope_a, _, _ = _lineage()
    bundle = derive_differences(_request([scope_a]))
    difference = bundle["differences"][0]
    assert difference["objective_scope_binding"]["scope_ref"]["id"] == SCOPE_B
    assert difference["effective_boundary"]["scope_ref"]["id"] == SCOPE_B


def test_every_observation_is_verified_against_its_own_scope() -> None:
    scope_a, _, _ = _lineage()
    bundle = derive_differences(_request([scope_a]))
    scopes = {item["scope_id"]: item for item in bundle["observation_scopes"]}
    for observation in bundle["observations"]:
        scope = scopes[observation["scope_ref"]["id"]]
        assert observation["method_ref"] == scope["method_ref"]
        assert observation["source_snapshot_refs"] == scope["source_snapshot_refs"]


def test_a_forged_historical_scope_fails_closed() -> None:
    scope_a, _, _ = _lineage()
    forged = deepcopy(scope_a)
    forged["source_snapshot_refs"] = [{"kind": "source_snapshot", "id": "SNAP-OTHER"}]
    with pytest.raises(DifferenceError):
        derive_differences(_request([forged]))


def test_a_historical_scope_naming_the_resolved_scope_differently_fails_closed() -> None:
    _, scope_b, _ = _lineage()
    contradicting = deepcopy(scope_b)
    contradicting["freshness_limit_seconds"] = 600
    with pytest.raises(IdentityCollisionError, match="contradicts the resolved Scope"):
        derive_differences(_request([contradicting]))


def test_a_historical_scope_from_another_project_fails_closed() -> None:
    scope_a, _, _ = _lineage()
    foreign = deepcopy(scope_a)
    foreign["project_id"] = "PRJ-OTHER"
    with pytest.raises(BoundaryViolationError, match="different project"):
        derive_differences(_request([foreign]))


def test_a_schema_invalid_historical_scope_fails_closed() -> None:
    scope_a, _, _ = _lineage()
    broken = deepcopy(scope_a)
    del broken["freshness_limit_seconds"]
    with pytest.raises(DifferenceError):
        derive_differences(_request([broken]))


def test_a_scope_no_carried_observation_names_is_rejected_not_emitted() -> None:
    scope_a, _, _ = _lineage()
    unrelated = observation_scope(scope_id="OBS-SCOPE-0009")
    with pytest.raises(DifferenceError, match="named by no carried Observation"):
        derive_differences(_request([scope_a, unrelated]))


def test_the_supply_route_is_not_a_list_fails_closed() -> None:
    with pytest.raises(DifferenceError, match="must be a list"):
        derive_differences(_request({"scope_id": SCOPE_A}))  # type: ignore[arg-type]


def test_the_binding_key_set_is_closed() -> None:
    """A binding key the Engine does not declare is rejected, not silently ignored."""

    assert "historical_observation_scopes" in BINDING_KEYS
    request = _request(None)
    request["bindings"][0]["unexpected_key"] = []
    with pytest.raises(DifferenceError, match="binding carries unknown sections"):
        derive_differences(request)


def test_the_request_is_never_mutated() -> None:
    scope_a, _, _ = _lineage()
    request = _request([scope_a])
    before = deepcopy(request)
    derive_differences(request)
    assert request == before
