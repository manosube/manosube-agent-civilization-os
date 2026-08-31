"""Upstream integrity proofs: Fact boundary kinds, identities, and predecessor context.

Covers the independent review findings on `6d169d2`: every canonical positive-Fact
boundary kind is accepted, every identity-bearing upstream record is recomputed before it
is trusted, and a predecessor is rejected unless its retained lineage is self-contained.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from scripts.difference_contract_validator import _fact_boundary_observed, validate_bundle
from tests.difference_helpers import (
    PREDICATE_ID,
    derivation_request,
    objective_revision,
    observation_scope,
    observed_bundle,
    raw_fact,
    reobservation_pair,
    single_binding_request,
    state_fingerprint,
)

from manosube_agent_civilization.difference import (
    BoundaryViolationError,
    DifferenceError,
    IdentityCollisionError,
    derive_differences,
)
from manosube_agent_civilization.observation.boundary import fact_boundary_observed
from manosube_agent_civilization.observation.identity import (
    binding_identity,
    fact_evaluation_identity,
    fact_identity,
)

# Each canonical boundary form, matching the helper Observation's exact binding.
_SNAPSHOT: dict[str, Any] = {
    "kind": "SOURCE_SNAPSHOT",
    "identity": "SNAP-0001",
    "start": None,
    "end": None,
}
_INTERVAL: dict[str, Any] = {
    "kind": "TIME_INTERVAL",
    "identity": "kernel",
    "start": "2026-08-30T08:00:00Z",
    "end": "2026-08-30T09:00:00Z",
}
_REVISION: dict[str, Any] = {
    "kind": "STATE_REVISION",
    "identity": "kernel",
    "start": 2,
    "end": 2,
}
_BOUNDARIES: dict[str, dict[str, Any]] = {
    "SOURCE_SNAPSHOT": _SNAPSHOT,
    "TIME_INTERVAL": _INTERVAL,
    "STATE_REVISION": _REVISION,
}


def _request_with_boundary(boundary: dict[str, Any]) -> dict[str, Any]:
    fingerprint = state_fingerprint()
    scope = observation_scope()
    fact = raw_fact()
    fact["effective_boundary"] = deepcopy(boundary)
    return derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": observed_bundle(scope, [fact], fingerprint),
            }
        ],
        fingerprint,
    )


# --------------------------------------------------------------------------- #
# Finding 1: every canonical positive-Fact boundary kind is accepted.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("kind", sorted(_BOUNDARIES))
def test_every_canonical_fact_boundary_kind_derives_a_difference(kind: str) -> None:
    bundle = derive_differences(_request_with_boundary(_BOUNDARIES[kind]))
    assert len(bundle["differences"]) == 1
    assert validate_bundle(bundle) == []
    fact = bundle["normalized_facts"][0]
    assert fact["effective_boundary"]["kind"] == kind


@pytest.mark.parametrize("kind", sorted(_BOUNDARIES))
def test_engine_observation_owner_and_auditor_agree_on_the_boundary(kind: str) -> None:
    """One authority: the Engine, the Observation owner and the auditor all use it."""

    bundle = derive_differences(_request_with_boundary(_BOUNDARIES[kind]))
    observation = bundle["observations"][0]
    fact = bundle["normalized_facts"][0]
    assert fact_boundary_observed(fact["effective_boundary"], observation)
    assert _fact_boundary_observed(fact, observation)


_MISMATCHED = [
    ("unknown_kind", {"kind": "SOMETHING_ELSE", "identity": "x", "start": None, "end": None}),
    (
        "snapshot_not_declared",
        {"kind": "SOURCE_SNAPSHOT", "identity": "SNAP-9999", "start": None, "end": None},
    ),
    (
        "snapshot_with_window",
        {
            "kind": "SOURCE_SNAPSHOT",
            "identity": "SNAP-0001",
            "start": "2026-08-30T08:00:00Z",
            "end": None,
        },
    ),
    (
        "interval_wrong_start",
        {
            "kind": "TIME_INTERVAL",
            "identity": "kernel",
            "start": "2020-01-01T00:00:00Z",
            "end": "2026-08-30T09:00:00Z",
        },
    ),
    (
        "interval_wrong_end",
        {
            "kind": "TIME_INTERVAL",
            "identity": "kernel",
            "start": "2026-08-30T08:00:00Z",
            "end": "2020-01-01T00:00:00Z",
        },
    ),
    ("revision_wrong_start", {"kind": "STATE_REVISION", "identity": "kernel", "start": 9, "end": 2}),
    ("revision_wrong_end", {"kind": "STATE_REVISION", "identity": "kernel", "start": 2, "end": 9}),
]


@pytest.mark.parametrize(
    "boundary", [case[1] for case in _MISMATCHED], ids=[case[0] for case in _MISMATCHED]
)
def test_mismatched_fact_boundary_is_rejected(boundary: dict[str, Any]) -> None:
    request = single_binding_request()
    observation = request["bindings"][0]["observation_bundle"]["observations"][-1]
    assert not fact_boundary_observed(boundary, observation)
    for fact in request["bindings"][0]["observation_bundle"]["facts"]:
        fact["effective_boundary"] = deepcopy(boundary)
        fact["fact_id"] = fact_identity(fact)
    with pytest.raises((BoundaryViolationError, DifferenceError)):
        derive_differences(request)


# --------------------------------------------------------------------------- #
# Finding 2: upstream identities are recomputed before they are trusted.
# --------------------------------------------------------------------------- #

_FACT_IDENTITY_INPUTS: list[tuple[str, Any]] = [
    ("value", "FORGED-VALUE"),
    ("subject", "kernel.other"),
    ("predicate", "exists@v1"),
    ("value_type", "INTEGER"),
    ("unit", "milliseconds"),
    ("project_id", "PRJ-9999"),
    ("normalization_profile", "FIXTURE-9.9"),
    ("effective_boundary", deepcopy(_INTERVAL)),
]


@pytest.mark.parametrize(
    ("field", "value"),
    _FACT_IDENTITY_INPUTS,
    ids=[case[0] for case in _FACT_IDENTITY_INPUTS],
)
def test_forged_fact_identity_input_fails_closed(field: str, value: Any) -> None:
    """A changed identity input with a retained fact_id must never be trusted."""

    request = single_binding_request()
    facts = request["bindings"][0]["observation_bundle"]["facts"]
    assert facts
    for fact in facts:
        assert fact[field] != value, "the mutation must actually change the payload"
        fact[field] = value
    with pytest.raises(DifferenceError):
        derive_differences(request)


def test_identity_valid_control_still_derives() -> None:
    """The same mutation with a recomputed identity is a different, valid Fact."""

    request = single_binding_request()
    for fact in request["bindings"][0]["observation_bundle"]["facts"]:
        fact["value"] = "STILL-NOT-READY"
        fact["fact_id"] = fact_identity(fact)
    # The binding and evaluation identities follow the Fact, so they are recomputed too.
    original = {
        item["binding_id"]: item
        for item in request["bindings"][0]["observation_bundle"]["bindings"]
    }
    assert original
    with pytest.raises(DifferenceError):
        # The bindings still name the old fact_id, so the bundle is now inconsistent.
        derive_differences(request)


def test_forged_binding_identity_fails_closed() -> None:
    request = single_binding_request()
    for binding in request["bindings"][0]["observation_bundle"]["bindings"]:
        binding["source_occurrence_id"] = "SOURCE-OCC-FORGED"
    with pytest.raises(IdentityCollisionError, match="Binding identity does not recompute"):
        derive_differences(request)


def test_forged_fact_evaluation_identity_fails_closed() -> None:
    request = single_binding_request()
    for evaluation in request["bindings"][0]["observation_bundle"]["fact_evaluations"]:
        evaluation["evaluation_revision"] = 7
    with pytest.raises(DifferenceError):
        derive_differences(request)


def test_upstream_identity_authorities_agree_with_the_auditor() -> None:
    from scripts.difference_contract_validator import _fact_id

    bundle = derive_differences(single_binding_request())
    for fact in bundle["normalized_facts"]:
        assert fact["fact_id"] == fact_identity(fact) == _fact_id(fact)
    for binding in bundle["fact_observation_bindings"]:
        assert binding["binding_id"] == binding_identity(binding)
    for evaluation in bundle["fact_evaluations"]:
        assert evaluation["evaluation_id"] == fact_evaluation_identity(evaluation)


# --------------------------------------------------------------------------- #
# Finding 3: a predecessor must carry a self-contained retained lineage.
# --------------------------------------------------------------------------- #


def _reobservation_with(predecessor: dict[str, Any]) -> dict[str, Any]:
    _, later_request = _PAIR
    request = deepcopy(later_request)
    request["bindings"][0]["predecessor"] = deepcopy(predecessor)
    return request


def _fresh_pair() -> tuple[dict[str, Any], dict[str, Any]]:
    baseline_request, later_request = reobservation_pair()
    baseline = derive_differences(baseline_request)
    return baseline, later_request


_PAIR: tuple[dict[str, Any], dict[str, Any]] = (None, None)  # type: ignore[assignment]


@pytest.fixture(autouse=True)
def _seed_pair() -> None:
    global _PAIR
    _PAIR = _fresh_pair()


def _predecessor(baseline: dict[str, Any], context: dict[str, Any] | None) -> dict[str, Any]:
    predecessor: dict[str, Any] = {
        "difference": baseline["differences"][0],
        "events": deepcopy(baseline["events"]),
    }
    if context is not None:
        predecessor["context"] = deepcopy(context)
    return predecessor


def test_predecessor_without_any_context_is_rejected() -> None:
    baseline, _ = _PAIR
    with pytest.raises(DifferenceError, match="does not resolve"):
        derive_differences(_reobservation_with(_predecessor(baseline, None)))


def test_predecessor_with_an_empty_context_is_rejected() -> None:
    baseline, _ = _PAIR
    with pytest.raises(DifferenceError, match="does not resolve"):
        derive_differences(_reobservation_with(_predecessor(baseline, {})))


@pytest.mark.parametrize("section", ["observations", "fact_observation_bindings"])
def test_predecessor_missing_a_referenced_section_is_rejected(section: str) -> None:
    """A section the retained lineage references must be carried, not silently dropped."""

    baseline, _ = _PAIR
    context = deepcopy(baseline)
    context[section] = []
    with pytest.raises(DifferenceError):
        derive_differences(_reobservation_with(_predecessor(baseline, context)))


def test_predecessor_with_a_forged_context_payload_is_rejected() -> None:
    """Same identity, different payload in the carried context must fail closed."""

    baseline, _ = _PAIR
    context = deepcopy(baseline)
    context["observations"][0]["status"] = "BLOCKED"
    with pytest.raises(IdentityCollisionError, match="same-ID different-payload"):
        derive_differences(_reobservation_with(_predecessor(baseline, context)))


def test_a_self_contained_predecessor_is_accepted() -> None:
    baseline, _ = _PAIR
    bundle = derive_differences(_reobservation_with(_predecessor(baseline, baseline)))
    assert validate_bundle(bundle) == []
    observations = {item["observation_id"] for item in bundle["observations"]}
    assert len(observations) == 2
    for event in bundle["events"]:
        for reference in event["observation_refs"]:
            assert reference["id"] in observations


def test_supersession_predecessor_must_also_be_self_contained() -> None:
    baseline, _ = _PAIR
    fingerprint = state_fingerprint("KNOWN")
    scope = observation_scope()
    changed = derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": observed_bundle(
                    scope, [raw_fact(value="DEGRADED")], fingerprint, state_revision=3
                ),
            }
        ],
        fingerprint,
        state_revision=3,
    )
    without = deepcopy(changed)
    without["bindings"][0]["predecessor"] = _predecessor(baseline, None)
    with pytest.raises(DifferenceError, match="does not resolve"):
        derive_differences(without)

    complete = deepcopy(changed)
    complete["bindings"][0]["predecessor"] = _predecessor(baseline, baseline)
    bundle = derive_differences(complete)
    assert validate_bundle(bundle) == []
    assert len(bundle["differences"]) == 2
