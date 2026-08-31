"""The bound Observation's identity and boundary are verified, never trusted.

Covers the independent review finding on `f2b1d89`: Fact, binding and evaluation
identities were recomputed, but the Observation's own identity was not. A caller could
retain `observation_id` while altering the method, time boundary, source snapshots or any
other identity input, and every reference still resolved.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from scripts.difference_contract_validator import validate_bundle
from scripts.observation_contract_validator import validate_bundle as audit_observation
from tests.difference_helpers import (
    PREDICATE_ID,
    derivation_request,
    objective_revision,
    observation_scope,
    observed_bundle,
    raw_fact,
    single_binding_request,
    state_fingerprint,
    target_predicate,
)

from manosube_agent_civilization.difference import (
    BoundaryViolationError,
    DifferenceError,
    IdentityCollisionError,
    derive_differences,
)
from manosube_agent_civilization.observation import observe
from manosube_agent_civilization.observation.identity import (
    OBSERVATION_SEMANTIC_FIELDS,
    observation_identity,
    observation_semantic_projection,
)
from manosube_agent_civilization.observation.schemas import (
    OBSERVATION_SCHEMA_BASE,
    validators,
)
from manosube_agent_civilization.observation.verification import observation_record_errors
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes


def _observations(request: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = request["bindings"][0]["observation_bundle"]["observations"]
    return records


# --------------------------------------------------------------------------- #
# Every identity-bearing Observation field, mutated while the id is retained.
# --------------------------------------------------------------------------- #

_IDENTITY_MUTATIONS: list[tuple[str, Any]] = [
    ("project_id", "PRJ-9999"),
    ("state_revision_observed", 99),
    ("state_fingerprint_observed", {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "a" * 64}),
    ("target", {"target_identity": "TP-9999", "kind": "FIXTURE"}),
    ("scope_ref", {"kind": "observation_scope", "id": "OBS-SCOPE-9999"}),
    ("method_ref", {"kind": "observation_method", "id": "OBS-METHOD-9999"}),
    (
        "time_boundary",
        {
            "observation_started_at": "2020-01-01T00:00:00Z",
            "observation_ended_at": "2020-01-01T00:01:00Z",
            "target_effective_start": "2020-01-01T00:00:00Z",
            "target_effective_end": "2020-01-01T00:01:00Z",
            "source_snapshot_time": "2020-01-01T00:00:30Z",
        },
    ),
    ("source_snapshot_refs", [{"kind": "source_snapshot", "id": "SNAP-FORGED"}]),
    ("normalization_profile", "FORGED-9.9"),
]


@pytest.mark.parametrize(("field", "value"), _IDENTITY_MUTATIONS, ids=[m[0] for m in _IDENTITY_MUTATIONS])
def test_a_forged_observation_identity_input_fails_closed(field: str, value: Any) -> None:
    request = single_binding_request()
    for observation in _observations(request):
        before = canonical_json_bytes(observation)
        observation[field] = deepcopy(value)
        # The mutation genuinely changes the payload and genuinely breaks the identity.
        assert canonical_json_bytes(observation) != before
        assert observation_identity(observation) != observation["observation_id"]
    with pytest.raises(DifferenceError):
        derive_differences(request)


def test_the_forged_method_diagnosis_is_an_identity_collision() -> None:
    """A retained id over an altered method is named as what it is."""

    request = single_binding_request()
    for observation in _observations(request):
        observation["method_ref"] = {"kind": "observation_method", "id": "OBS-METHOD-9999"}
    with pytest.raises(IdentityCollisionError, match="Observation identity does not recompute"):
        derive_differences(request)


def test_a_consistent_but_out_of_scope_observation_is_rejected() -> None:
    """A self-consistent identity is not admissibility: the Scope still decides."""

    scope = observation_scope()
    revision = 2
    fingerprint = state_fingerprint()
    foreign = observation_scope(snapshot_refs=[{"kind": "source_snapshot", "id": "SNAP-FOREIGN"}])
    bundle = observed_bundle(
        foreign,
        [raw_fact(snapshot_id="SNAP-FOREIGN")],
        fingerprint,
        state_revision=revision,
    )
    # The Observation Engine's own output is internally consistent and self-auditing.
    assert audit_observation(bundle) == []
    assert observation_record_errors(bundle) == []
    for observation in bundle["observations"]:
        assert observation["observation_id"] == observation_identity(observation)

    request = derivation_request(
        objective_revision([target_predicate()]),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                # The derivation resolves the canonical Scope, which declares SNAP-0001.
                "observation_scope": scope,
                "observation_bundle": bundle,
            }
        ],
        fingerprint,
        revision,
    )
    with pytest.raises(BoundaryViolationError, match="source snapshots escape the resolved Scope"):
        derive_differences(request)


def test_an_observation_window_outside_the_scope_is_rejected() -> None:
    scope = observation_scope()
    request = single_binding_request()
    for observation in _observations(request):
        observation["time_boundary"]["target_effective_start"] = "2020-01-01T00:00:00Z"
        observation["observation_id"] = observation_identity(observation)
    with pytest.raises(DifferenceError):
        derive_differences(request)
    assert scope["target_effective_window"]["start"] == "2026-08-30T08:00:00Z"


def test_a_mismatched_method_against_the_resolved_scope_is_rejected() -> None:
    """Recomputing the id after the mutation removes the identity defence; Scope remains."""

    request = single_binding_request()
    for observation in _observations(request):
        observation["method_ref"] = {"kind": "observation_method", "id": "OBS-METHOD-9999"}
        observation["observation_id"] = observation_identity(observation)
    with pytest.raises(DifferenceError):
        derive_differences(request)


# --------------------------------------------------------------------------- #
# Every Observation the route consumes, not only the selected head.
# --------------------------------------------------------------------------- #


def test_a_forged_earlier_observation_in_the_lineage_fails_closed() -> None:
    """The check reaches every Observation the derivation carries."""

    from tests.difference_helpers import reobservation_pair

    _, later_request = reobservation_pair()
    observations = _observations(later_request)
    assert len(observations) == 2
    earlier = min(observations, key=lambda item: item["state_revision_observed"])
    earlier["normalization_profile"] = "FORGED-9.9"
    with pytest.raises(DifferenceError):
        derive_differences(later_request)


# --------------------------------------------------------------------------- #
# The valid route, every canonical boundary form, and authority agreement.
# --------------------------------------------------------------------------- #


def test_every_canonical_observation_still_derives_and_validates() -> None:
    bundle = derive_differences(single_binding_request())
    assert validate_bundle(bundle) == []
    for observation in bundle["observations"]:
        assert observation["observation_id"] == observation_identity(observation)


def test_the_observation_owner_mints_through_the_shared_projection() -> None:
    """The Engine that mints an identity and the verifier use one closed algorithm."""

    from tests.difference_helpers import observation_request as build_request

    scope = observation_scope()
    fingerprint = state_fingerprint()
    produced = observe(build_request(scope, [raw_fact()], fingerprint))
    for observation in produced["observations"]:
        assert observation["observation_id"] == observation_identity(observation)
        projection = observation_semantic_projection(observation)
        assert set(projection) == set(OBSERVATION_SEMANTIC_FIELDS)
        # Nothing outside the projection is an identity input.
        varied = deepcopy(observation)
        varied["status"] = "INCOMPLETE"
        varied["blind_spots"] = {"status": "NONE_KNOWN", "items": []}
        assert observation_identity(varied) == observation["observation_id"]


def test_the_shared_authority_and_the_independent_auditor_agree() -> None:
    valid = _observations(single_binding_request())[0]
    assert observation_identity(valid) == valid["observation_id"]

    request = single_binding_request()
    bundle = request["bindings"][0]["observation_bundle"]
    for observation in bundle["observations"]:
        observation["normalization_profile"] = "FORGED-9.9"
    assert observation_record_errors(bundle) != []
    # The canonical Observation schema still accepts the record, so schema conformance
    # alone would not have caught this.
    validator = validators()[OBSERVATION_SCHEMA_BASE + "observation.schema.json"]
    assert list(validator.iter_errors(bundle["observations"][0])) == []


def test_the_derivation_never_mutates_the_observation_bundle() -> None:
    request = single_binding_request()
    bundle = request["bindings"][0]["observation_bundle"]
    before = canonical_json_bytes(bundle)
    derive_differences(request)
    assert canonical_json_bytes(bundle) == before


def test_the_route_stays_byte_deterministic() -> None:
    request = single_binding_request()
    assert canonical_json_bytes(derive_differences(deepcopy(request))) == canonical_json_bytes(
        derive_differences(deepcopy(request))
    )
