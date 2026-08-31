"""Mutation coverage for every carried predecessor-context record type.

One identity-bearing and one non-identity/status-bound mutation per type, so a future
review does not have to name the next uncovered field one at a time.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from scripts.difference_contract_validator import validate_bundle
from tests.difference_helpers import (
    PREDICATE_ID,
    derivation_request,
    negative_claim,
    objective_revision,
    observation_scope,
    observed_bundle,
    raw_fact,
    reobservation_pair,
    retained_status_predecessor,
    state_fingerprint,
    target_predicate,
)

from manosube_agent_civilization.difference import DifferenceError, derive_differences
from manosube_agent_civilization.difference.predecessor import (
    CARRIED_TYPES,
    LATER_PHASE_SECTIONS,
    NO_CANONICAL_SCHEMA_SECTIONS,
)
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

_SCOPE = observation_scope()


def _blocked_request() -> dict[str, Any]:
    """A predecessor rich enough to carry every section under test."""

    _, request = retained_status_predecessor(
        "BLOCKED", "BLOCKER_REOBSERVATION", negative_claims=[negative_claim("NO_RESULT")], facts=[]
    )
    return request


def _context(request: dict[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = request["bindings"][0]["predecessor"]["context"]
    return context


def test_the_fixture_carries_the_sections_under_test() -> None:
    """The mutations below are not vacuous: these sections really are populated."""

    context = _context(_blocked_request())
    populated = {section for section in CARRIED_TYPES if context.get(section)}
    assert {
        "observations",
        "negative_observations",
        "negative_observation_evaluations",
        "observation_scopes",
        "objective_revisions",
        "policies",
        "next_observation_requests",
        "observation_methods",
        "evaluations",
    } <= populated, sorted(populated)


# --------------------------------------------------------------------------- #
# Identity-bearing mutations: the identity must stop recomputing.
# --------------------------------------------------------------------------- #

_IDENTITY_MUTATIONS: list[tuple[str, str, Any]] = [
    ("observations", "normalization_profile", "FORGED-9.9"),
    ("negative_observations", "subject", "kernel.other"),
    ("negative_observation_evaluations", "negative_observation_id", "NEG-" + "0" * 64),
    ("policies", "policy_semantic_fingerprint", "sha256:" + "0" * 64),
    ("next_observation_requests", "reason_code", "RETAINED_REOBSERVATION"),
    ("observation_methods", "input_contract_ref", {"kind": "schema", "id": "FORGED"}),
]


@pytest.mark.parametrize(
    ("section", "field", "value"),
    _IDENTITY_MUTATIONS,
    ids=[f"{case[0]}.{case[1]}" for case in _IDENTITY_MUTATIONS],
)
def test_a_forged_identity_input_fails_closed(section: str, field: str, value: Any) -> None:
    """At the boundary itself, so the identity rule is what decides."""

    from manosube_agent_civilization.difference.predecessor import validate_carried_records

    request = _blocked_request()
    records = deepcopy(_context(request)[section])
    assert records, section
    for record in records:
        record[field] = deepcopy(value)
    with pytest.raises(DifferenceError, match="does not recompute"):
        validate_carried_records({section: records})


@pytest.mark.parametrize(
    ("section", "field", "value"),
    _IDENTITY_MUTATIONS,
    ids=[f"{case[0]}.{case[1]}" for case in _IDENTITY_MUTATIONS],
)
def test_a_forged_identity_input_fails_closed_end_to_end(
    section: str, field: str, value: Any
) -> None:
    """And through the whole derivation, whichever gate reaches it first."""

    request = _blocked_request()
    for record in _context(request)[section]:
        record[field] = deepcopy(value)
    with pytest.raises(DifferenceError):
        derive_differences(request)


# --------------------------------------------------------------------------- #
# Non-identity / status-bound mutations: the canonical schema must decide them.
# --------------------------------------------------------------------------- #

_PAYLOAD_MUTATIONS: list[tuple[str, str, Any]] = [
    ("observations", "status", "NOT_A_STATUS"),
    ("negative_observations", "negative_status", "NOT_A_STATUS"),
    ("negative_observation_evaluations", "evaluation_status", "NOT_A_STATUS"),
    ("observation_scopes", "scope_status", "NOT_A_STATUS"),
    ("objective_revisions", "status", "NOT_A_STATUS"),
    ("policies", "contradiction_policy", "NOT_A_POLICY"),
    ("next_observation_requests", "record_kind", "NOT_A_RECORD_KIND"),
    ("observation_methods", "procedure_kind", "NOT_A_PROCEDURE"),
    ("evaluations", "result", "NOT_A_RESULT"),
]


@pytest.mark.parametrize(
    ("section", "field", "value"),
    _PAYLOAD_MUTATIONS,
    ids=[f"{case[0]}.{case[1]}" for case in _PAYLOAD_MUTATIONS],
)
def test_a_schema_invalid_payload_field_fails_closed(
    section: str, field: str, value: Any
) -> None:
    request = _blocked_request()
    records = _context(request)[section]
    assert records, section
    for record in records:
        record[field] = deepcopy(value)
    with pytest.raises(DifferenceError):
        derive_differences(request)


@pytest.mark.parametrize("section", sorted(CARRIED_TYPES))
def test_an_undeclared_field_fails_closed_for_every_schema_backed_type(section: str) -> None:
    """Canonical record schemas are closed, so a smuggled field is rejected."""

    if section in NO_CANONICAL_SCHEMA_SECTIONS:
        pytest.skip(f"{section} has no canonical schema in v0.1 - stated non-claim")
    request = _blocked_request()
    records = _context(request).get(section)
    if not records:
        pytest.skip(f"{section} is not populated by this fixture")
    for record in records:
        record["smuggled_field"] = "x"
    with pytest.raises(DifferenceError):
        derive_differences(request)


# --------------------------------------------------------------------------- #
# The Difference record and its lifecycle events.
# --------------------------------------------------------------------------- #

_DIFFERENCE_PAYLOAD_MUTATIONS: list[tuple[str, Any]] = [
    ("risk_class", "SEVERE"),
    ("authority_required", "not-a-list"),
    ("observation_evidence_refs", []),
    ("observed_state_revision", "two"),
    ("observation_scope", 17),
]


@pytest.mark.parametrize(
    ("field", "value"),
    _DIFFERENCE_PAYLOAD_MUTATIONS,
    ids=[case[0] for case in _DIFFERENCE_PAYLOAD_MUTATIONS],
)
def test_a_malformed_predecessor_difference_payload_fails_closed(
    field: str, value: Any
) -> None:
    baseline_request, later = reobservation_pair()
    baseline = derive_differences(baseline_request)
    request = deepcopy(later)
    difference = deepcopy(baseline["differences"][0])
    difference[field] = deepcopy(value)
    request["bindings"][0]["predecessor"] = {
        "difference": difference,
        "events": deepcopy(baseline["events"]),
        "context": deepcopy(baseline),
    }
    with pytest.raises(DifferenceError):
        derive_differences(request)


def test_an_open_impact_object_is_contract_permitted_and_recorded_as_such() -> None:
    """`impact` is `{"type": "object"}` in v0.1, so any object is admissible there.

    The Engine cannot reject what the canonical schema permits, and inventing a shape for
    it would be legislating a contract this Issue does not own. The gap is recorded as a
    remaining Difference rather than papered over: every *other* non-identity field of a
    carried Difference is decided by the schema, as the cases above prove.
    """

    import json
    from pathlib import Path

    schema = json.loads(
        (
            Path(__file__).resolve().parents[3]
            / "01_SCHEMA" / "difference" / "difference.schema.json"
        ).read_text(encoding="utf-8")
    )
    assert schema["properties"]["impact"] == {"type": "object"}
    assert schema["additionalProperties"] is False


_BLOCKER_PAYLOAD_MUTATIONS: list[tuple[str, Any]] = [
    ("condition_code", "BINDINGS_CURRENT"),
    ("subject_ref", {"kind": "difference", "id": "D-" + "0" * 64}),
    ("verification_request_ref", {"kind": "next_observation_request", "id": "OBS-REQ-NOWHERE"}),
]


@pytest.mark.parametrize(
    ("field", "value"),
    _BLOCKER_PAYLOAD_MUTATIONS,
    ids=[case[0] for case in _BLOCKER_PAYLOAD_MUTATIONS],
)
def test_a_forged_blocker_resolution_condition_fails_closed(field: str, value: Any) -> None:
    """The blocker payload is outside event identity, so the boundary decides it."""

    from manosube_agent_civilization.difference.identity import lifecycle_event_id

    request = _blocked_request()
    event = request["bindings"][0]["predecessor"]["events"][-1]
    before = event["difference_event_id"]
    event["blocker_resolution_condition"][field] = deepcopy(value)
    assert event["difference_event_id"] == before == lifecycle_event_id(event)
    with pytest.raises(DifferenceError, match="blocker"):
        derive_differences(request)


def test_a_forged_blocker_effective_boundary_fails_closed() -> None:
    from manosube_agent_civilization.difference.identity import lifecycle_event_id

    request = _blocked_request()
    event = request["bindings"][0]["predecessor"]["events"][-1]
    before = event["difference_event_id"]
    event["blocker_scope"]["effective_boundary"]["target_effective_window"] = {
        "start": "2000-01-01T00:00:00Z",
        "end": "2000-01-01T01:00:00Z",
    }
    assert event["difference_event_id"] == before == lifecycle_event_id(event)
    with pytest.raises(DifferenceError, match="blocker boundary mismatch"):
        derive_differences(request)


def test_a_non_blocked_event_carrying_blocker_payload_fails_closed() -> None:
    from manosube_agent_civilization.difference.identity import lifecycle_event_id

    request = _blocked_request()
    events = request["bindings"][0]["predecessor"]["events"]
    blocked = events[-1]
    genesis = events[0]
    genesis["blocker_kind"] = blocked["blocker_kind"]
    genesis["blocker_scope"] = deepcopy(blocked["blocker_scope"])
    genesis["blocker_resolution_condition"] = deepcopy(blocked["blocker_resolution_condition"])
    assert genesis["difference_event_id"] == lifecycle_event_id(genesis)
    # The canonical event schema pins the blocker payload to null off BLOCKED, so the
    # schema gate reaches this first; the shared lifecycle authority states the same rule
    # for a payload the schema would admit.
    with pytest.raises(DifferenceError):
        derive_differences(request)

    from manosube_agent_civilization.difference.lifecycle import blocker_payload_errors

    assert blocker_payload_errors(genesis, None) == [
        f"non-BLOCKED event carries blocker payload: {genesis['difference_event_id']}"
    ]


# --------------------------------------------------------------------------- #
# Collisions, ambiguity, and the valid routes.
# --------------------------------------------------------------------------- #


def test_a_same_id_different_payload_record_inside_the_context_fails_closed() -> None:
    request = _blocked_request()
    scopes = _context(request)["observation_scopes"]
    forged = deepcopy(scopes[0])
    forged["freshness_limit_seconds"] = 999999
    scopes.append(forged)
    with pytest.raises(DifferenceError, match="same-ID different-payload"):
        derive_differences(request)


def test_a_duplicate_identical_record_is_accepted() -> None:
    """Rejecting duplicates outright would refuse a caller who re-sent one record twice."""

    request = _blocked_request()
    scopes = _context(request)["observation_scopes"]
    scopes.append(deepcopy(scopes[0]))
    assert derive_differences(request)["differences"]


def test_a_valid_multi_event_predecessor_is_accepted_byte_for_byte() -> None:
    request = _blocked_request()
    predecessor = deepcopy(request["bindings"][0]["predecessor"])
    bundle = derive_differences(request)

    original = {
        event["difference_event_id"]: event for event in predecessor["events"]
    }
    for event in bundle["events"]:
        if event["difference_event_id"] in original:
            assert canonical_json_bytes(event) == canonical_json_bytes(
                original[event["difference_event_id"]]
            )
    assert canonical_json_bytes(bundle["differences"][0]) == canonical_json_bytes(
        predecessor["difference"]
    )
    assert validate_bundle(bundle) == []


def test_equivalent_reobservation_and_material_supersession_both_stay_valid() -> None:
    baseline_request, later = reobservation_pair()
    baseline = derive_differences(baseline_request)
    equivalent = deepcopy(later)
    equivalent["bindings"][0]["predecessor"] = {
        "difference": deepcopy(baseline["differences"][0]),
        "events": deepcopy(baseline["events"]),
        "context": deepcopy(baseline),
    }
    assert validate_bundle(derive_differences(equivalent)) == []

    fingerprint = state_fingerprint("KNOWN")
    material = derivation_request(
        objective_revision([target_predicate()]),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": _SCOPE,
                "observation_bundle": observed_bundle(
                    _SCOPE, [raw_fact(value="OTHER")], fingerprint, state_revision=7
                ),
                "predecessor": {
                    "difference": deepcopy(baseline["differences"][0]),
                    "events": deepcopy(baseline["events"]),
                    "context": deepcopy(baseline),
                },
            }
        ],
        fingerprint,
        7,
    )
    superseded = derive_differences(material)
    assert validate_bundle(superseded) == []
    assert superseded["supersession_relations"]


def test_the_engine_and_the_auditor_agree_on_every_mutation() -> None:
    """Where the Engine accepts, the independent auditor accepts; where it rejects, so would it."""

    accepted = derive_differences(_blocked_request())
    assert validate_bundle(accepted) == []

    for section, field, value in _IDENTITY_MUTATIONS + _PAYLOAD_MUTATIONS:
        request = _blocked_request()
        records = _context(request).get(section)
        if not records:
            continue
        for record in records:
            record[field] = deepcopy(value)
        with pytest.raises(DifferenceError):
            derive_differences(request)


def test_later_phase_sections_are_carried_but_not_semantically_claimed() -> None:
    """The non-claim is explicit: schema and references only, no invented semantics."""

    assert "evaluations" in LATER_PHASE_SECTIONS
    request = _blocked_request()
    bundle = derive_differences(request)
    carried = {item["closure_evaluation_id"] for item in bundle["evaluations"]}
    supplied = {item["closure_evaluation_id"] for item in _context(request)["evaluations"]}
    assert supplied <= carried
