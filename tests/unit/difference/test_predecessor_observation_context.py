"""A predecessor-only Observation is verified before it is merged, never after.

Covers the independent review finding on `56a204a`: an Observation reaching the bundle
only through `predecessor.context` is never repeated by the current Observation bundle, so
the overlap agreement check has nothing to compare it against. It could be altered while
retaining `observation_id` and merged as immutable provenance, unvalidated.
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
    target_predicate,
)

from manosube_agent_civilization.difference import (
    BoundaryViolationError,
    DifferenceError,
    IdentityCollisionError,
    derive_differences,
)
from manosube_agent_civilization.observation.identity import observation_identity
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

_SCOPE = observation_scope()


def _request(
    bundle: dict[str, Any],
    fingerprint: dict[str, Any],
    revision: int,
    predecessor: dict[str, Any] | None = None,
    scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    binding: dict[str, Any] = {
        "target_predicate_id": PREDICATE_ID,
        "observation_scope": deepcopy(scope or _SCOPE),
        "observation_bundle": bundle,
    }
    if predecessor is not None:
        binding["predecessor"] = predecessor
    return derivation_request(
        objective_revision([target_predicate()]), [binding], fingerprint, revision
    )


def _superseding_pair() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """A material change whose predecessor Observation is in no current bundle.

    The two Observations come from independent bundles, so the earlier one reaches the
    returned bundle only as predecessor provenance -- exactly the route the finding names.
    """

    first_fingerprint = state_fingerprint()
    later_fingerprint = state_fingerprint("KNOWN")
    earlier = observed_bundle(_SCOPE, [raw_fact()], first_fingerprint)
    later = observed_bundle(
        _SCOPE, [raw_fact(value="OTHER")], later_fingerprint, state_revision=7
    )
    baseline = derive_differences(_request(earlier, first_fingerprint, 2))
    return baseline, later, later_fingerprint


def _with_context(
    baseline: dict[str, Any], context: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "difference": deepcopy(baseline["differences"][0]),
        "events": deepcopy(baseline["events"]),
        "context": deepcopy(baseline) if context is None else context,
    }


def _derive(baseline: dict[str, Any], later: dict[str, Any], fingerprint: dict[str, Any],
            context: dict[str, Any] | None = None) -> dict[str, Any]:
    return derive_differences(
        _request(later, fingerprint, 7, _with_context(baseline, context))
    )


def _predecessor_only(context: dict[str, Any], later: dict[str, Any]) -> dict[str, Any]:
    """Return the carried Observation, asserting it is absent from the current bundle."""

    current = {item["observation_id"] for item in later["observations"]}
    carried = [item for item in context["observations"] if item["observation_id"] not in current]
    assert len(carried) == 1
    record: dict[str, Any] = carried[0]
    return record


# --------------------------------------------------------------------------- #
# The valid route: accepted, and returned byte-identically.
# --------------------------------------------------------------------------- #


def test_a_valid_predecessor_only_observation_is_accepted_byte_identically() -> None:
    baseline, later, fingerprint = _superseding_pair()
    context = deepcopy(baseline)
    original = deepcopy(_predecessor_only(context, later))

    bundle = _derive(baseline, later, fingerprint, context)
    carried = {item["observation_id"]: item for item in bundle["observations"]}

    assert original["observation_id"] in carried
    assert canonical_json_bytes(carried[original["observation_id"]]) == canonical_json_bytes(
        original
    )
    assert bundle["supersession_relations"]
    assert validate_bundle(bundle) == []


def test_the_predecessor_difference_stays_byte_identical() -> None:
    baseline, later, fingerprint = _superseding_pair()
    predecessor = deepcopy(baseline["differences"][0])
    bundle = _derive(baseline, later, fingerprint)
    superseded = [
        item
        for item in bundle["differences"]
        if item["difference_id"] == predecessor["difference_id"]
    ]
    assert len(superseded) == 1
    assert canonical_json_bytes(superseded[0]) == canonical_json_bytes(predecessor)


def test_the_caller_context_is_never_mutated() -> None:
    baseline, later, fingerprint = _superseding_pair()
    predecessor = _with_context(baseline)
    before = canonical_json_bytes(predecessor)
    derive_differences(_request(later, fingerprint, 7, predecessor))
    assert canonical_json_bytes(predecessor) == before


# --------------------------------------------------------------------------- #
# Identity: every identity-bearing field, forged with the id retained.
# --------------------------------------------------------------------------- #

_FORGERIES: list[tuple[str, Any]] = [
    ("method_ref", {"kind": "observation_method", "id": "OBS-METHOD-FORGED"}),
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
    ("project_id", "PRJ-9999"),
    ("state_revision_observed", 99),
    (
        "state_fingerprint_observed",
        {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "a" * 64},
    ),
    ("target", {"target_identity": "TP-9999", "kind": "FIXTURE"}),
    ("normalization_profile", "FORGED-9.9"),
]


@pytest.mark.parametrize(
    ("field", "value"), _FORGERIES, ids=[case[0] for case in _FORGERIES]
)
def test_a_forged_predecessor_only_observation_fails_closed(field: str, value: Any) -> None:
    baseline, later, fingerprint = _superseding_pair()
    context = deepcopy(baseline)
    carried = _predecessor_only(context, later)
    before = canonical_json_bytes(carried)
    carried[field] = deepcopy(value)
    assert canonical_json_bytes(carried) != before
    assert observation_identity(carried) != carried["observation_id"]

    with pytest.raises(IdentityCollisionError, match="identity does not recompute"):
        _derive(baseline, later, fingerprint, context)


# --------------------------------------------------------------------------- #
# Scope: a self-consistent identity is still not admissibility.
# --------------------------------------------------------------------------- #


def _inject(context: dict[str, Any], later: dict[str, Any], **mutation: Any) -> dict[str, Any]:
    """Add an extra carried Observation whose own identity is consistent with its payload.

    Mutating the *referenced* provenance record and recomputing its id would break the
    retained Difference's own `observation_refs`, and the lineage-resolution check would
    fire first. Injecting a self-consistent extra record instead leaves the lineage intact,
    so what decides the outcome is the Scope verification this finding is about -- which is
    also the realistic shape of the attack: supplying a real-looking but inadmissible
    Observation as provenance.
    """

    extra = deepcopy(_predecessor_only(context, later))
    for field, value in mutation.items():
        extra[field] = deepcopy(value)
    extra["observation_id"] = observation_identity(extra)
    assert extra["observation_id"] != _predecessor_only(context, later)["observation_id"]
    context["observations"].append(extra)
    return extra


def test_an_injected_observation_naming_an_absent_scope_is_rejected() -> None:
    baseline, later, fingerprint = _superseding_pair()
    context = deepcopy(baseline)
    _inject(context, later, scope_ref={"kind": "observation_scope", "id": "OBS-SCOPE-NOWHERE"})
    with pytest.raises(DifferenceError, match="names a Scope absent from the bundle"):
        _derive(baseline, later, fingerprint, context)


def test_a_conflicting_scope_record_in_the_context_is_rejected() -> None:
    baseline, later, fingerprint = _superseding_pair()
    context = deepcopy(baseline)
    forged = deepcopy(context["observation_scopes"][0])
    forged["freshness_limit_seconds"] = 999999
    context["observation_scopes"].append(forged)
    with pytest.raises(IdentityCollisionError, match="same-ID different-payload"):
        _derive(baseline, later, fingerprint, context)


def test_an_injected_out_of_scope_source_is_rejected() -> None:
    baseline, later, fingerprint = _superseding_pair()
    context = deepcopy(baseline)
    _inject(context, later, source_snapshot_refs=[{"kind": "source_snapshot", "id": "SNAP-FORGED"}])
    with pytest.raises(BoundaryViolationError, match="source snapshots escape the resolved Scope"):
        _derive(baseline, later, fingerprint, context)


def test_an_injected_foreign_method_is_rejected() -> None:
    baseline, later, fingerprint = _superseding_pair()
    context = deepcopy(baseline)
    _inject(context, later, method_ref={"kind": "observation_method", "id": "OBS-METHOD-FORGED"})
    with pytest.raises(BoundaryViolationError, match="method is outside the declared Scope"):
        _derive(baseline, later, fingerprint, context)


def test_an_injected_stale_observation_is_rejected() -> None:
    """A snapshot older than its own Scope's freshness limit is not valid provenance."""

    baseline, later, fingerprint = _superseding_pair()
    context = deepcopy(baseline)
    stale = deepcopy(_predecessor_only(context, later)["time_boundary"])
    stale["source_snapshot_time"] = "2026-08-30T08:50:00Z"
    _inject(context, later, time_boundary=stale)
    with pytest.raises(BoundaryViolationError, match="time boundary escapes the resolved Scope"):
        _derive(baseline, later, fingerprint, context)


def test_an_injected_observation_from_another_project_is_rejected() -> None:
    baseline, later, fingerprint = _superseding_pair()
    context = deepcopy(baseline)
    _inject(context, later, project_id="PRJ-9999")
    with pytest.raises(BoundaryViolationError, match="project does not match"):
        _derive(baseline, later, fingerprint, context)


def test_an_injected_observation_with_a_malformed_scope_reference_is_rejected() -> None:
    baseline, later, fingerprint = _superseding_pair()
    context = deepcopy(baseline)
    extra = deepcopy(_predecessor_only(context, later))
    extra["scope_ref"] = "OBS-SCOPE-0001"
    extra["observation_id"] = "OBS-" + "0" * 64
    context["observations"].append(extra)
    with pytest.raises(DifferenceError):
        _derive(baseline, later, fingerprint, context)


def test_an_injected_same_id_different_payload_record_is_rejected() -> None:
    baseline, later, fingerprint = _superseding_pair()
    context = deepcopy(baseline)
    extra = deepcopy(_predecessor_only(context, later))
    extra["status"] = "INCOMPLETE"
    context["observations"].append(extra)
    with pytest.raises(IdentityCollisionError, match="same-ID different-payload"):
        _derive(baseline, later, fingerprint, context)


def test_an_admissible_extra_provenance_observation_is_accepted() -> None:
    """The rejections above are not a blanket refusal of carried provenance.

    A real third Observation of the same Target and Scope, produced by the Observation
    Engine at another State revision, is self-consistent and in Scope. It is accepted,
    carried, and returned byte-identically.
    """

    baseline, later, fingerprint = _superseding_pair()
    third = observed_bundle(
        _SCOPE, [raw_fact()], state_fingerprint("INCOMPLETE"), state_revision=9
    )
    extra = deepcopy(third["observations"][0])
    assert extra["observation_id"] == observation_identity(extra)

    context = deepcopy(baseline)
    current = {item["observation_id"] for item in later["observations"]}
    assert extra["observation_id"] not in current
    context["observations"].append(extra)
    context["normalized_facts"].extend(
        record for record in third["facts"]
        if record["fact_id"] not in {item["fact_id"] for item in context["normalized_facts"]}
    )
    context["fact_observation_bindings"].extend(deepcopy(third["bindings"]))
    context["fact_evaluations"].extend(
        record for record in third["fact_evaluations"]
        if record["evaluation_id"]
        not in {item["evaluation_id"] for item in context["fact_evaluations"]}
    )

    bundle = _derive(baseline, later, fingerprint, context)
    carried = {item["observation_id"]: item for item in bundle["observations"]}
    assert extra["observation_id"] in carried
    assert canonical_json_bytes(carried[extra["observation_id"]]) == canonical_json_bytes(extra)


# --------------------------------------------------------------------------- #
# Every Observation in the returned bundle, not only predecessor-only ones.
# --------------------------------------------------------------------------- #


def test_every_carried_observation_is_verified_including_the_bound_one() -> None:
    baseline, later, fingerprint = _superseding_pair()
    bundle = _derive(baseline, later, fingerprint)
    scopes = {item["scope_id"] for item in bundle["observation_scopes"]}
    assert len(bundle["observations"]) == 2
    for observation in bundle["observations"]:
        assert observation["observation_id"] == observation_identity(observation)
        assert observation["scope_ref"]["id"] in scopes


def test_a_transitively_reached_observation_is_verified() -> None:
    """The closure's Observations go through the same single verification pass."""

    from tests.difference_helpers import reobservation_pair

    _, later_request = reobservation_pair()
    observations = later_request["bindings"][0]["observation_bundle"]["observations"]
    assert len(observations) == 2
    earlier = min(observations, key=lambda item: item["state_revision_observed"])
    earlier["normalization_profile"] = "FORGED-9.9"
    with pytest.raises(DifferenceError):
        derive_differences(later_request)


def test_the_returned_lineage_stays_self_contained_and_cross_record_valid() -> None:
    baseline, later, fingerprint = _superseding_pair()
    bundle = _derive(baseline, later, fingerprint)
    assert validate_bundle(bundle) == []
    observations = {item["observation_id"] for item in bundle["observations"]}
    for event in bundle["events"]:
        for reference in event["observation_refs"]:
            assert reference["id"] in observations
    bindings = {item["binding_id"] for item in bundle["fact_observation_bindings"]}
    for evaluation in bundle["fact_evaluations"]:
        for reference in evaluation["binding_refs"]:
            assert reference["id"] in bindings


def test_the_route_stays_deterministic() -> None:
    baseline, later, fingerprint = _superseding_pair()
    first = _derive(baseline, later, fingerprint)
    second = _derive(baseline, later, fingerprint)
    assert canonical_json_bytes(first) == canonical_json_bytes(second)
