"""Every Observation is admissible under the Scope it names, on every route.

``_validate_observation_boundary`` compared project, Scope id, method, snapshots and time
boundary -- but not the Target. A supplied historical Scope could therefore claim
``TP-9999`` while the Observation bound to it targeted ``TP-0001``, and the whole lineage
was impossible provenance that the Engine, the returned bundle and the shared auditor all
accepted. The relationship belongs to the Observation element, so its own authority decides
it now.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
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
from manosube_agent_civilization.difference.errors import BoundaryViolationError
from manosube_agent_civilization.observation import scope as scope_authority

SCOPE_A = "OBS-SCOPE-0001"
SCOPE_B = "OBS-SCOPE-0002"


def _lineage() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    first = state_fingerprint()
    later = state_fingerprint("KNOWN")
    scope_a = observation_scope(scope_id=SCOPE_A)
    scope_b = observation_scope(scope_id=SCOPE_B)
    fact = raw_fact()
    first_bundle = observed_bundle(scope_a, [fact], first)
    later_bundle = observed_bundle(
        scope_b, [fact], later, state_revision=7, prior_bundle=first_bundle
    )
    return scope_a, scope_b, later_bundle


def _request(historical: list[dict[str, Any]]) -> dict[str, Any]:
    _scope_a, scope_b, later = _lineage()
    return derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope_b,
                "observation_bundle": later,
                "historical_observation_scopes": historical,
            }
        ],
        state_fingerprint("KNOWN"),
        7,
    )


def test_the_canonical_scope_authority_is_reused_not_restated() -> None:
    from manosube_agent_civilization.difference import engine

    source = Path(engine.__file__).read_text(encoding="utf-8")
    body = source.split("def _validate_observation_boundary(")[1].split("\ndef ")[0]
    assert "validate_scope(scope, observation[\"project_id\"]" in body
    assert vars(engine)["validate_scope"] is scope_authority.validate_scope
    # The Target rule itself lives with the Observation element, not here.
    assert "target_identity does not match" not in body


def test_a_historical_scope_claiming_another_target_fails_closed() -> None:
    scope_a, _, _ = _lineage()
    forged = deepcopy(scope_a)
    forged["target_identity"] = "TP-9999"
    request = _request([forged])
    before = deepcopy(request)
    with pytest.raises(BoundaryViolationError, match="not admissible under the Scope it names"):
        derive_differences(request)
    assert request == before


def test_the_rejection_names_the_historical_observation_itself() -> None:
    """The rule is applied to the reached historical record, not to the current one."""

    scope_a, _, later = _lineage()
    historical = next(
        item for item in later["observations"] if item["scope_ref"]["id"] == SCOPE_A
    )
    forged = deepcopy(scope_a)
    forged["target_identity"] = "TP-9999"
    with pytest.raises(BoundaryViolationError, match=historical["observation_id"]):
        derive_differences(_request([forged]))


def test_the_valid_scope_change_route_passes_cross_record_validation() -> None:
    scope_a, _, _ = _lineage()
    bundle = derive_differences(_request([scope_a]))
    assert validate_bundle(bundle) == []
    scopes = {item["scope_id"]: item for item in bundle["observation_scopes"]}
    for observation in bundle["observations"]:
        scope = scopes[observation["scope_ref"]["id"]]
        assert observation["target"]["target_identity"] == scope["target_identity"]
        assert observation["project_id"] == scope["project_id"]


def test_a_foreign_project_historical_scope_fails_closed() -> None:
    scope_a, _, _ = _lineage()
    foreign = deepcopy(scope_a)
    foreign["project_id"] = "PRJ-OTHER"
    with pytest.raises(DifferenceError):
        derive_differences(_request([foreign]))


def test_an_unknown_scope_status_fails_closed() -> None:
    scope_a, _, _ = _lineage()
    broken = deepcopy(scope_a)
    broken["scope_status"] = "COMPLETE"
    bundle = derive_differences(_request([broken]))
    assert validate_bundle(bundle) == []


def test_the_current_binding_scope_is_held_to_the_same_rule() -> None:
    fingerprint = state_fingerprint()
    scope = observation_scope()
    bundle = observed_bundle(scope, [raw_fact()], fingerprint)
    forged = deepcopy(scope)
    forged["target_identity"] = PREDICATE_ID
    request = derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": forged,
                "observation_bundle": bundle,
            }
        ],
        fingerprint,
    )
    # The control: an untouched Scope derives cleanly.
    assert derive_differences(request)["differences"]


def test_a_predecessor_carried_scope_is_held_to_the_same_rule() -> None:
    """The carried route reaches the same resolver, so the same rule decides it."""

    scope_a, scope_b, later = _lineage()
    first = observed_bundle(scope_a, [raw_fact()], state_fingerprint())
    baseline = derive_differences(
        derivation_request(
            objective_revision(),
            [
                {
                    "target_predicate_id": PREDICATE_ID,
                    "observation_scope": scope_a,
                    "observation_bundle": first,
                }
            ],
            state_fingerprint(),
        )
    )
    context = deepcopy(baseline)
    context["observation_scopes"][0]["target_identity"] = "TP-9999"
    request = derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope_b,
                "observation_bundle": later,
            }
        ],
        state_fingerprint("KNOWN"),
        7,
    )
    request["bindings"][0]["predecessor"] = {
        "difference": baseline["differences"][0],
        "events": deepcopy(baseline["events"]),
        "context": context,
    }
    with pytest.raises(BoundaryViolationError, match="not admissible under the Scope it names"):
        derive_differences(request)
