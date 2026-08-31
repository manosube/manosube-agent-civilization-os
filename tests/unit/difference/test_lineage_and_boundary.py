"""Unit proofs for predecessor lineage integrity and Negative Observation boundary.

Covers the four findings of the independent review of `49d52ab`:
recomputed predecessor event identity, self-contained equivalent re-observation,
bounded proven absence under the `none` operator, and full Negative Observation
boundary validation.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from tests.difference_helpers import (
    PREDICATE_ID,
    SUBJECT,
    binding_request,
    negative_claim,
    observation_scope,
    raw_fact,
    reobservation_pair,
    single_binding_request,
    target_predicate,
)

from manosube_agent_civilization.difference import (
    BoundaryViolationError,
    DifferenceError,
    derive_differences,
)
from manosube_agent_civilization.difference.identity import lifecycle_event_id
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes


def _baseline_with_predecessor() -> tuple[dict[str, Any], dict[str, Any]]:
    baseline_request, later_request = reobservation_pair()
    baseline = derive_differences(baseline_request)
    later_request["bindings"][0]["predecessor"] = {
        "difference": baseline["differences"][0],
        "events": deepcopy(baseline["events"]),
        "context": baseline,
    }
    return baseline, later_request


# --------------------------------------------------------------------------- #
# Finding 1: every predecessor event identity is recomputed.
# --------------------------------------------------------------------------- #

# Each case names an identity-bearing field of a lifecycle event.
_IDENTITY_FIELDS: list[tuple[str, Any]] = [
    ("reason_code", "TAMPERED_REASON"),
    ("event_kind", "OBSERVATION_BOUND"),
    ("to_status", "ACTIVE"),
    ("from_status", "OPEN"),
    ("state_revision_evaluated", 4242),
    (
        "observation_refs",
        [{"kind": "observation", "id": "OBS-INJECTED"}],
    ),
    (
        "evidence_refs",
        [{"kind": "observation_evidence", "id": "EVID-INJECTED"}],
    ),
    (
        "state_fingerprint_evaluated",
        {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "e" * 64},
    ),
]


@pytest.mark.parametrize(
    ("field", "value"), _IDENTITY_FIELDS, ids=[case[0] for case in _IDENTITY_FIELDS]
)
@pytest.mark.parametrize("revision", [0, 1], ids=["genesis", "head"])
def test_forged_predecessor_event_identity_is_rejected(
    field: str, value: Any, revision: int
) -> None:
    """A changed identity input with a retained event ID must never be accepted."""

    _, request = _baseline_with_predecessor()
    events = request["bindings"][0]["predecessor"]["events"]
    events[revision][field] = value
    # Any fail-closed rejection is correct here: schema, genesis and legality checks may
    # fire before the identity check. The invariant is that a forged event never enters
    # the returned lineage.
    with pytest.raises(DifferenceError):
        derive_differences(request)


@pytest.mark.parametrize("revision", [0, 1], ids=["genesis", "head"])
def test_identity_check_itself_rejects_a_forged_reason_code(revision: int) -> None:
    """A field that trips no other rule is still caught by identity recomputation."""

    _, request = _baseline_with_predecessor()
    events = request["bindings"][0]["predecessor"]["events"]
    events[revision]["reason_code"] = "TAMPERED_REASON"
    with pytest.raises(DifferenceError, match="identity does not recompute"):
        derive_differences(request)


def test_every_event_in_a_valid_chain_recomputes_to_its_identity() -> None:
    _, request = _baseline_with_predecessor()
    events = request["bindings"][0]["predecessor"]["events"]
    assert len(events) >= 2
    for event in events:
        assert event["difference_event_id"] == lifecycle_event_id(event)
    derive_differences(request)


def test_a_valid_multi_event_predecessor_chain_is_accepted() -> None:
    """The whole chain is validated, not only its head."""

    _, request = _baseline_with_predecessor()
    bundle = derive_differences(request)
    chain = sorted(bundle["events"], key=lambda item: item["event_revision"])
    assert [event["event_revision"] for event in chain] == [0, 1, 2]
    for event in chain:
        assert event["difference_event_id"] == lifecycle_event_id(event)


def test_forged_identity_in_the_middle_of_a_longer_chain_is_rejected() -> None:
    _, request = _baseline_with_predecessor()
    first = derive_differences(deepcopy(request))
    # Feed the three-event chain back as the predecessor of a further re-observation.
    request["bindings"][0]["predecessor"] = {
        "difference": first["differences"][0],
        "events": deepcopy(first["events"]),
        "context": first,
    }
    events = request["bindings"][0]["predecessor"]["events"]
    assert len(events) == 3
    events[1]["reason_code"] = "TAMPERED_MIDDLE"
    with pytest.raises(DifferenceError, match="identity does not recompute"):
        derive_differences(request)


# --------------------------------------------------------------------------- #
# Finding 2: equivalent re-observation keeps the retained lineage resolvable.
# --------------------------------------------------------------------------- #


def test_equivalent_reobservation_returns_a_self_contained_lineage() -> None:
    baseline, request = _baseline_with_predecessor()
    bundle = derive_differences(request)

    assert (
        bundle["differences"][0]["difference_id"]
        == baseline["differences"][0]["difference_id"]
    )
    observations = {item["observation_id"] for item in bundle["observations"]}
    facts = {item["fact_id"] for item in bundle["normalized_facts"]}
    bindings = {item["binding_id"] for item in bundle["fact_observation_bindings"]}
    evaluations = {item["evaluation_id"] for item in bundle["fact_evaluations"]}

    # Both the prior and the new Observation are present, so every retained event
    # reference resolves inside the returned bundle.
    assert len(observations) == 2
    for event in bundle["events"]:
        for reference in event["observation_refs"]:
            assert reference["id"] in observations
    for record in baseline["observations"]:
        assert record["observation_id"] in observations
    for record in baseline["normalized_facts"]:
        assert record["fact_id"] in facts
    for record in baseline["fact_observation_bindings"]:
        assert record["binding_id"] in bindings
    for record in baseline["fact_evaluations"]:
        assert record["evaluation_id"] in evaluations
    assert {item["closure_policy_id"] for item in baseline["policies"]} <= {
        item["closure_policy_id"] for item in bundle["policies"]
    }
    assert {item["scope_id"] for item in baseline["observation_scopes"]} <= {
        item["scope_id"] for item in bundle["observation_scopes"]
    }


def test_equivalent_reobservation_across_a_new_state_revision_keeps_identity() -> None:
    """The identity is preserved and the record itself is not rewritten.

    The new State revision is carried by the appended provenance event, never by
    replacing the predecessor's own immutable observed-State binding.
    """

    baseline, request = _baseline_with_predecessor()
    bundle = derive_differences(request)
    difference = bundle["differences"][0]
    predecessor = baseline["differences"][0]
    assert difference["difference_id"] == predecessor["difference_id"]
    assert canonical_json_bytes(difference) == canonical_json_bytes(predecessor)
    assert difference["observed_state_revision"] == predecessor["observed_state_revision"]

    appended = bundle["events"][-1]
    assert appended["event_kind"] == "OBSERVATION_BOUND"
    assert appended["state_revision_evaluated"] != predecessor["observed_state_revision"]
    assert bundle["supersession_relations"] == []
    assert bundle["materialized_status"] == baseline["materialized_status"]


# --------------------------------------------------------------------------- #
# Finding 3: bounded proven absence satisfies the `none` operator.
# --------------------------------------------------------------------------- #

_NONE_PREDICATE = target_predicate(operator="none", expected_value="READY")


@pytest.mark.parametrize("negative_status", ["ABSENT", "EMPTY"])
def test_bounded_proven_absence_satisfies_none(negative_status: str) -> None:
    bundle = derive_differences(
        binding_request(
            [],
            predicate=_NONE_PREDICATE,
            negative_claims=[negative_claim(negative_status)],
        )
    )
    assert bundle["differences"] == []
    assert bundle["events"] == []
    assert bundle["satisfied_target_predicates"] == [PREDICATE_ID]
    # A satisfied Target Predicate is not an Objective Completion claim.
    assert bundle["evaluations"] == []
    assert bundle["candidate_completion_records"] == []


@pytest.mark.parametrize("negative_status", ["NO_RESULT", "UNOBSERVED"])
def test_unresolved_absence_never_satisfies_none(negative_status: str) -> None:
    bundle = derive_differences(
        binding_request(
            [],
            predicate=_NONE_PREDICATE,
            negative_claims=[negative_claim(negative_status)],
        )
    )
    assert len(bundle["differences"]) == 1
    structural = bundle["differences"][0]["structural_difference"]
    assert structural["comparison_result"] == "UNKNOWN"
    assert structural["mismatch_kind"] == "UNKNOWN"
    assert bundle["satisfied_target_predicates"] == []


def test_none_with_a_matching_candidate_is_still_unexpected() -> None:
    bundle = derive_differences(
        binding_request([raw_fact(value="READY")], predicate=_NONE_PREDICATE)
    )
    structural = bundle["differences"][0]["structural_difference"]
    assert structural["comparison_result"] == "NOT_SATISFIED"
    assert structural["mismatch_kind"] == "UNEXPECTED"


@pytest.mark.parametrize("negative_status", ["ABSENT", "EMPTY"])
def test_bounded_absence_still_misses_a_positive_operator(negative_status: str) -> None:
    """Proven absence never becomes vacuous satisfaction of equals or all."""

    for operator in ("equals", "all", "exists"):
        bundle = derive_differences(
            binding_request(
                [],
                predicate=target_predicate(operator=operator, expected_value="READY"),
                negative_claims=[negative_claim(negative_status)],
            )
        )
        structural = bundle["differences"][0]["structural_difference"]
        assert structural["comparison_result"] == "NOT_SATISFIED"
        assert structural["mismatch_kind"] == "MISSING"


# --------------------------------------------------------------------------- #
# Finding 4: the full Negative Observation boundary is validated.
# --------------------------------------------------------------------------- #

_OTHER_SNAPSHOT = {"kind": "source_snapshot", "id": "SNAP-9999"}
_BOUNDARY_MUTATIONS: list[tuple[str, str, Any]] = [
    ("cross_project", "project_id", "PRJ-9999"),
    ("cross_scope", "scope_ref", {"kind": "observation_scope", "id": "OBS-SCOPE-9999"}),
    ("cross_method", "method_ref", {"kind": "observation_method", "id": "OBS-METHOD-9999"}),
    (
        "wrong_time_window",
        "time_boundary",
        {
            "observation_started_at": "2020-01-01T00:00:00Z",
            "observation_ended_at": "2020-01-01T00:01:00Z",
            "target_effective_start": "2020-01-01T00:00:00Z",
            "target_effective_end": "2020-01-01T00:01:00Z",
            "source_snapshot_time": "2020-01-01T00:00:30Z",
        },
    ),
    ("wrong_source_snapshot", "source_snapshot_refs", [_OTHER_SNAPSHOT]),
    (
        "effective_boundary_escape",
        "effective_boundary",
        {"kind": "SOURCE_SNAPSHOT", "identity": "SNAP-9999", "start": None, "end": None},
    ),
    (
        "unbounded_effective_window",
        "effective_boundary",
        {
            "kind": "SOURCE_SNAPSHOT",
            "identity": "SNAP-0001",
            "start": "2026-08-30T08:00:00Z",
            "end": None,
        },
    ),
]


@pytest.mark.parametrize(
    ("field", "value"),
    [(case[1], case[2]) for case in _BOUNDARY_MUTATIONS],
    ids=[case[0] for case in _BOUNDARY_MUTATIONS],
)
def test_negative_observation_outside_the_boundary_is_rejected(
    field: str, value: Any
) -> None:
    request = binding_request([], negative_claims=[negative_claim("ABSENT")])
    for negative in request["bindings"][0]["observation_bundle"]["negative_observations"]:
        negative[field] = value
    with pytest.raises(BoundaryViolationError):
        derive_differences(request)


def test_negative_observation_with_an_unknown_schema_version_is_rejected() -> None:
    """An unknown schema version fails closed at the shared upstream authority.

    ``schema_version`` is a ``const`` in the canonical Negative Observation schema, so the
    record is inadmissible upstream and never reaches the Difference Engine's own
    ``require_schema_version`` check, which is retained as defence in depth.
    """

    request = binding_request([], negative_claims=[negative_claim("ABSENT")])
    for negative in request["bindings"][0]["observation_bundle"]["negative_observations"]:
        negative["schema_version"] = "0.2"
    with pytest.raises(DifferenceError, match="not cross-record valid"):
        derive_differences(request)


def test_negative_observation_subject_outside_scope_is_rejected() -> None:
    request = binding_request([], negative_claims=[negative_claim("ABSENT")])
    binding = request["bindings"][0]
    binding["observation_scope"]["included_subjects"] = [SUBJECT]
    binding["observation_scope"]["excluded_subjects"] = [SUBJECT]
    with pytest.raises(BoundaryViolationError):
        derive_differences(request)


def test_conflict_route_also_validates_the_negative_boundary() -> None:
    """The boundary is checked even when positive Facts make the negatives optional."""

    request = binding_request([raw_fact()], negative_claims=[negative_claim("ABSENT")])
    for negative in request["bindings"][0]["observation_bundle"]["negative_observations"]:
        negative["project_id"] = "PRJ-9999"
    with pytest.raises(BoundaryViolationError, match="project_id"):
        derive_differences(request)


def test_valid_bounded_negative_observation_is_accepted() -> None:
    bundle = derive_differences(
        binding_request([], negative_claims=[negative_claim("ABSENT")])
    )
    difference = bundle["differences"][0]
    assert difference["normalized_observed_state"]["knowledge_status"] == "ABSENT"
    negative = bundle["negative_observations"][0]
    observation = bundle["observations"][0]
    assert negative["project_id"] == difference["project_id"]
    assert negative["scope_ref"] == observation["scope_ref"]
    assert negative["method_ref"] == observation["method_ref"]
    assert negative["time_boundary"] == observation["time_boundary"]
    assert negative["source_snapshot_refs"] == observation["source_snapshot_refs"]


def test_stale_observation_lineage_without_the_requested_state_is_rejected() -> None:
    request = single_binding_request()
    for observation in request["bindings"][0]["observation_bundle"]["observations"]:
        observation["state_revision_observed"] = 999
    with pytest.raises(DifferenceError, match="stale Observation"):
        derive_differences(request)


def test_observation_scope_mismatch_leaves_no_selectable_observation() -> None:
    request = single_binding_request()
    request["bindings"][0]["observation_scope"] = observation_scope(scope_id="OBS-SCOPE-0002")
    with pytest.raises(DifferenceError):
        derive_differences(request)
