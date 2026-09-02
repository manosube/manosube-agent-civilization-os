"""A Scope-change re-observation resolves each Observation against its own Scope.

An append-only Observation lineage keeps a recurring Fact's evaluation chain across a
Scope change, so the Difference Engine's context closure reaches the *prior* Observation
through its earlier binding. That Observation was never bound to the Scope this derivation
resolved, and checking it against the current binding's Scope rejected an otherwise valid
boundary-change re-observation before it could supersede the prior Difference.
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
from manosube_agent_civilization.difference.errors import (
    BoundaryViolationError,
    IdentityCollisionError,
)

FIRST_SCOPE_ID = "OBS-SCOPE-0001"
LATER_SCOPE_ID = "OBS-SCOPE-0002"


def _scope_change_pair() -> tuple[dict[str, Any], dict[str, Any]]:
    """A baseline bundle and a re-observation of the same recurring Fact, new Scope."""

    first_fingerprint = state_fingerprint()
    later_fingerprint = state_fingerprint("KNOWN")
    first_scope = observation_scope(scope_id=FIRST_SCOPE_ID)
    later_scope = observation_scope(scope_id=LATER_SCOPE_ID)
    fact = raw_fact()
    first_bundle = observed_bundle(first_scope, [fact], first_fingerprint)
    later_bundle = observed_bundle(
        later_scope, [fact], later_fingerprint, state_revision=7, prior_bundle=first_bundle
    )
    objective = objective_revision()
    baseline = derive_differences(
        derivation_request(
            objective,
            [
                {
                    "target_predicate_id": PREDICATE_ID,
                    "observation_scope": first_scope,
                    "observation_bundle": first_bundle,
                }
            ],
            first_fingerprint,
        )
    )
    later_request = derivation_request(
        objective,
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": later_scope,
                "observation_bundle": later_bundle,
            }
        ],
        later_fingerprint,
        7,
    )
    later_request["bindings"][0]["predecessor"] = {
        "difference": baseline["differences"][0],
        "events": deepcopy(baseline["events"]),
        "context": deepcopy(baseline),
    }
    return baseline, later_request


def test_the_lineage_really_carries_one_recurring_fact_across_two_scopes() -> None:
    """The scenario below is not vacuous: both Observations share one Normalized Fact."""

    _, later_request = _scope_change_pair()
    bundle = later_request["bindings"][0]["observation_bundle"]
    assert {
        observation["scope_ref"]["id"] for observation in bundle["observations"]
    } == {FIRST_SCOPE_ID, LATER_SCOPE_ID}
    assert len({fact["fact_id"] for fact in bundle["facts"]}) == 1
    assert max(
        evaluation["evaluation_revision"] for evaluation in bundle["fact_evaluations"]
    ) >= 1


def test_a_boundary_change_reobservation_supersedes_the_prior_difference() -> None:
    baseline, later_request = _scope_change_pair()
    bundle = derive_differences(later_request)

    prior_id = baseline["differences"][0]["difference_id"]
    assert bundle["materialized_status"][prior_id] == "SUPERSEDED"
    assert len(bundle["supersession_relations"]) == 1
    assert bundle["supersession_relations"][0]["old_difference_ref"]["id"] == prior_id
    # Both Scopes travel with the bundle, and each Observation names its own.
    scopes = {scope["scope_id"] for scope in bundle["observation_scopes"]}
    assert scopes == {FIRST_SCOPE_ID, LATER_SCOPE_ID}
    assert {
        observation["scope_ref"]["id"] for observation in bundle["observations"]
    } == scopes
    assert validate_bundle(bundle) == []


def test_deleting_the_historical_scope_fails_closed() -> None:
    """The prior Scope is the only record that can verify the prior Observation."""

    _, later_request = _scope_change_pair()
    context = later_request["bindings"][0]["predecessor"]["context"]
    context["observation_scopes"] = [
        scope for scope in context["observation_scopes"] if scope["scope_id"] != FIRST_SCOPE_ID
    ]
    with pytest.raises(DifferenceError, match="names a Scope absent from the bundle"):
        derive_differences(later_request)


def test_renaming_the_historical_scope_fails_closed() -> None:
    """Nothing substitutes for the Scope an Observation actually names."""

    _, later_request = _scope_change_pair()
    context = later_request["bindings"][0]["predecessor"]["context"]
    context["observation_scopes"][0]["scope_id"] = "OBS-SCOPE-0009"
    with pytest.raises(DifferenceError):
        derive_differences(later_request)


def test_swapping_the_scope_payloads_fails_closed() -> None:
    """A Scope record that does not describe the Observation bound to it is a forgery."""

    _, later_request = _scope_change_pair()
    context = later_request["bindings"][0]["predecessor"]["context"]
    carried = context["observation_scopes"][0]
    # Keep the identity the prior Observation names, but describe a different boundary.
    carried["observation_window"] = {
        "start": "2026-08-30T07:00:00Z",
        "end": "2026-08-30T07:01:00Z",
    }
    carried["cutoff"] = "2026-08-30T07:00:00Z"
    with pytest.raises((BoundaryViolationError, IdentityCollisionError, DifferenceError)):
        derive_differences(later_request)


def test_a_same_id_different_payload_scope_collision_fails_closed() -> None:
    _, later_request = _scope_change_pair()
    context = later_request["bindings"][0]["predecessor"]["context"]
    # A second, individually valid Scope claiming the identity the current binding also
    # resolves: the conflict crosses two routes, so only the shared union can see it.
    forged = deepcopy(context["observation_scopes"][0])
    forged["scope_id"] = LATER_SCOPE_ID
    forged["freshness_limit_seconds"] = 600
    context["observation_scopes"].append(forged)
    with pytest.raises(IdentityCollisionError):
        derive_differences(later_request)


def test_the_current_scope_is_never_substituted_for_a_historical_one() -> None:
    """The prior Observation is verified against OBS-SCOPE-0001, not the new Scope."""

    _, later_request = _scope_change_pair()
    bundle = derive_differences(later_request)
    scopes = {scope["scope_id"]: scope for scope in bundle["observation_scopes"]}
    prior = next(
        observation
        for observation in bundle["observations"]
        if observation["scope_ref"]["id"] == FIRST_SCOPE_ID
    )
    assert prior["method_ref"] == scopes[FIRST_SCOPE_ID]["method_ref"]
    assert prior["source_snapshot_refs"] == scopes[FIRST_SCOPE_ID]["source_snapshot_refs"]
