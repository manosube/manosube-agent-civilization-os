"""A returned bundle carries the transitive closure its own lineage needs.

Covers the independent review finding on `f2b1d89`: a fresh Difference derived from an
append-only Observation bundle carried the whole Fact evaluation chain but only the
current Observation's bindings, so an earlier evaluation's `binding_refs` dangled.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from scripts.difference_contract_validator import validate_bundle
from tests.difference_helpers import reobservation_pair

from manosube_agent_civilization.difference import (
    DifferenceError,
    IdentityCollisionError,
    derive_differences,
)
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes


def _fresh_request() -> dict[str, Any]:
    """A derivation over a two-Observation lineage with **no** Difference predecessor."""

    _, later_request = reobservation_pair()
    assert "predecessor" not in later_request["bindings"][0]
    bundle = later_request["bindings"][0]["observation_bundle"]
    # The premise the finding rests on: a recurring Fact evaluated across two Observations.
    assert len(bundle["observations"]) == 2
    assert len(bundle["bindings"]) == 2
    assert len(bundle["fact_evaluations"]) == 2
    return later_request


def test_a_fresh_derivation_carries_every_binding_its_evaluations_reference() -> None:
    bundle = derive_differences(_fresh_request())
    bindings = {item["binding_id"] for item in bundle["fact_observation_bindings"]}
    for evaluation in bundle["fact_evaluations"]:
        for reference in evaluation["binding_refs"]:
            assert reference["id"] in bindings, evaluation["evaluation_id"]


def test_a_fresh_derivation_carries_both_observations_and_their_facts() -> None:
    bundle = derive_differences(_fresh_request())
    observations = {item["observation_id"] for item in bundle["observations"]}
    facts = {item["fact_id"] for item in bundle["normalized_facts"]}

    assert len(observations) == 2
    for binding in bundle["fact_observation_bindings"]:
        assert binding["observation_id"] in observations
        assert binding["fact_id"] in facts
    for observation in bundle["observations"]:
        for reference in observation["normalized_fact_refs"]:
            assert reference["id"] in facts


def test_the_evaluation_chain_stays_contiguous_and_complete() -> None:
    """Append-only semantics forbid dropping an earlier revision to avoid a dangle."""

    source = _fresh_request()["bindings"][0]["observation_bundle"]
    bundle = derive_differences(_fresh_request())
    carried = sorted(
        bundle["fact_evaluations"], key=lambda item: item["evaluation_revision"]
    )
    assert [item["evaluation_revision"] for item in carried] == list(range(len(carried)))
    assert len(carried) == len(source["fact_evaluations"])
    assert carried[0]["previous_evaluation_id"] is None
    assert carried[1]["previous_evaluation_id"] == carried[0]["evaluation_id"]


def test_a_fresh_derivation_is_cross_record_valid_and_deterministic() -> None:
    bundle = derive_differences(_fresh_request())
    assert validate_bundle(bundle) == []
    assert canonical_json_bytes(derive_differences(_fresh_request())) == canonical_json_bytes(
        bundle
    )


def test_the_equivalent_reobservation_route_stays_self_contained() -> None:
    baseline_request, later_request = reobservation_pair()
    baseline = derive_differences(baseline_request)
    request = deepcopy(later_request)
    request["bindings"][0]["predecessor"] = {
        "difference": deepcopy(baseline["differences"][0]),
        "events": deepcopy(baseline["events"]),
        "context": deepcopy(baseline),
    }
    bundle = derive_differences(request)
    assert validate_bundle(bundle) == []
    bindings = {item["binding_id"] for item in bundle["fact_observation_bindings"]}
    for evaluation in bundle["fact_evaluations"]:
        for reference in evaluation["binding_refs"]:
            assert reference["id"] in bindings


# --------------------------------------------------------------------------- #
# A lineage that cannot be closed is never emitted partially.
# --------------------------------------------------------------------------- #


def test_an_evaluation_whose_binding_is_absent_fails_closed() -> None:
    request = _fresh_request()
    bundle = request["bindings"][0]["observation_bundle"]
    earlier = min(bundle["bindings"], key=lambda item: item["state_revision_observed"])
    bundle["bindings"] = [item for item in bundle["bindings"] if item is not earlier]
    with pytest.raises(DifferenceError):
        derive_differences(request)


def test_a_binding_whose_observation_is_absent_fails_closed() -> None:
    request = _fresh_request()
    bundle = request["bindings"][0]["observation_bundle"]
    earlier = min(bundle["observations"], key=lambda item: item["state_revision_observed"])
    bundle["observations"] = [item for item in bundle["observations"] if item is not earlier]
    with pytest.raises(DifferenceError):
        derive_differences(request)


def test_a_binding_whose_fact_is_absent_fails_closed() -> None:
    request = _fresh_request()
    bundle = request["bindings"][0]["observation_bundle"]
    bundle["facts"] = []
    with pytest.raises(DifferenceError):
        derive_differences(request)


def test_a_same_id_different_payload_collision_during_the_union_fails_closed() -> None:
    """The closure unions records; a contradicting duplicate is a forgery, not a retry."""

    baseline_request, later_request = reobservation_pair()
    baseline = derive_differences(baseline_request)
    request = deepcopy(later_request)
    context = deepcopy(baseline)
    context["observations"][0]["status"] = "BLOCKED"
    request["bindings"][0]["predecessor"] = {
        "difference": deepcopy(baseline["differences"][0]),
        "events": deepcopy(baseline["events"]),
        "context": context,
    }
    with pytest.raises(IdentityCollisionError, match="same-ID different-payload"):
        derive_differences(request)


def test_the_closure_never_widens_the_difference_boundary() -> None:
    """An Observation the closure reaches is still verified against the resolved Scope."""

    request = _fresh_request()
    bundle = request["bindings"][0]["observation_bundle"]
    earlier = min(bundle["observations"], key=lambda item: item["state_revision_observed"])
    earlier["scope_ref"] = {"kind": "observation_scope", "id": "OBS-SCOPE-9999"}
    with pytest.raises(DifferenceError):
        derive_differences(request)
