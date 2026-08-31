"""Unit proofs for the deterministic Difference Engine."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from tests.difference_helpers import (
    PREDICATE_ID,
    SUBJECT,
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
    SecurityRejectionError,
    UnsupportedProfileError,
    derive_differences,
)
from manosube_agent_civilization.difference.projection import (
    derive_comparison_and_mismatch,
    negative_knowledge_status,
    normalize_observed_state,
)
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

UNRESOLVED = ("UNKNOWN", "UNOBSERVED", "BLOCKED", "INCOMPLETE")


def _two_predicate_request() -> dict[str, Any]:
    fingerprint = state_fingerprint()
    first_scope = observation_scope(included=[SUBJECT], scope_id="OBS-SCOPE-0001")
    second_scope = observation_scope(
        included=["kernel.mode"], scope_id="OBS-SCOPE-0002", target_identity="TP-0002"
    )
    objective = objective_revision(
        [
            target_predicate(),
            target_predicate(
                subject="kernel.mode",
                expected_value="STRICT",
                predicate_id="TP-0002",
                observation_scope="kernel",
            ),
        ]
    )
    return derivation_request(
        objective,
        [
            {
                "target_predicate_id": "TP-0002",
                "observation_scope": second_scope,
                "observation_bundle": observed_bundle(
                    second_scope, [raw_fact(subject="kernel.mode", value="LOOSE")], fingerprint
                ),
            },
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": first_scope,
                "observation_bundle": observed_bundle(
                    first_scope, [raw_fact()], fingerprint
                ),
            },
        ],
        fingerprint,
    )


def test_one_unsatisfied_predicate_produces_one_stable_difference() -> None:
    bundle = derive_differences(single_binding_request())
    assert len(bundle["differences"]) == 1
    difference = bundle["differences"][0]
    assert difference["difference_id"].startswith("D-")
    assert difference["subject"] == SUBJECT
    assert difference["structural_difference"]["mismatch_kind"] == "VALUE_MISMATCH"
    assert difference["structural_difference"]["comparison_result"] == "NOT_SATISFIED"
    assert bundle["materialized_status"] == {difference["difference_id"]: "OPEN"}


def test_multiple_mismatches_are_deterministically_ordered() -> None:
    request = _two_predicate_request()
    reversed_request = deepcopy(request)
    reversed_request["bindings"].reverse()
    first = derive_differences(request)
    second = derive_differences(reversed_request)
    assert len(first["differences"]) == 2
    identities = [item["difference_id"] for item in first["differences"]]
    assert identities == sorted(identities)
    assert canonical_json_bytes(first) == canonical_json_bytes(second)


def test_same_canonical_input_produces_the_same_output_bytes() -> None:
    request = single_binding_request()
    assert canonical_json_bytes(derive_differences(deepcopy(request))) == canonical_json_bytes(
        derive_differences(deepcopy(request))
    )


def test_repeated_derivation_is_idempotent() -> None:
    request = single_binding_request()
    first = derive_differences(deepcopy(request))
    second = derive_differences(deepcopy(request))
    assert first == second
    assert first["differences"][0]["difference_id"] == second["differences"][0]["difference_id"]


def test_input_request_is_not_mutated() -> None:
    request = single_binding_request()
    before = canonical_json_bytes(request)
    derive_differences(request)
    assert canonical_json_bytes(request) == before


def test_satisfied_route_produces_a_deterministic_empty_difference_set() -> None:
    bundle = derive_differences(single_binding_request(value="READY"))
    assert bundle["differences"] == []
    assert bundle["events"] == []
    assert bundle["materialized_status"] == {}
    assert bundle["satisfied_target_predicates"] == [PREDICATE_ID]


def test_satisfied_route_does_not_declare_objective_completion() -> None:
    bundle = derive_differences(single_binding_request(value="READY"))
    # A bounded empty Difference set is not a Completion claim: no Closure Evaluation,
    # no candidate Completion record and no Claim or Invariant evaluation is produced.
    assert bundle["candidate_completion_records"] == []
    assert bundle["candidate_claim_evaluation_events"] == []
    assert bundle["invariant_evaluations"] == []
    assert bundle["evidence_sufficiency_results"] == []
    assert bundle["evaluations"] == []
    assert "objective_completion" not in bundle


def test_incomplete_scope_cannot_claim_satisfaction() -> None:
    fingerprint = state_fingerprint()
    scope = observation_scope()
    scope = observation_scope(scope_status="INCOMPLETE")
    bundle = observed_bundle(scope, [raw_fact(value="READY")], fingerprint)
    request = derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": bundle,
            }
        ],
        fingerprint,
    )
    # An incomplete evaluation scope can never reach a satisfied claim: the derivation
    # fails closed before any comparison result is projected.
    with pytest.raises(DifferenceError, match="cannot yield a KNOWN observed state"):
        derive_differences(request)


def test_incomplete_observation_does_not_become_a_normal_value_mismatch() -> None:
    fingerprint = state_fingerprint()
    scope = observation_scope()
    scope = observation_scope(scope_status="INCOMPLETE")
    bundle = observed_bundle(scope, [raw_fact()], fingerprint)
    assert bundle["observations"][-1]["status"] == "INCOMPLETE"
    request = derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": bundle,
            }
        ],
        fingerprint,
    )
    with pytest.raises(DifferenceError, match="cannot yield a KNOWN observed state"):
        derive_differences(request)


def test_conflicted_observation_fails_closed_into_an_unknown_comparison() -> None:
    fingerprint = state_fingerprint()
    scope = observation_scope()
    claim = {
        "subject": SUBJECT,
        "predicate": "equals@v1",
        "negative_status": "ABSENT",
        "effective_boundary": {
            "kind": "SOURCE_SNAPSHOT",
            "identity": "SNAP-0001",
            "start": None,
            "end": None,
        },
    }
    bundle = observed_bundle(scope, [raw_fact()], fingerprint, negative_claims=[claim])
    request = derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": bundle,
            }
        ],
        fingerprint,
    )
    derived = derive_differences(request)
    structural = derived["differences"][0]["structural_difference"]
    assert structural["mismatch_kind"] == "CONFLICT"
    assert structural["comparison_result"] == "UNKNOWN"
    assert structural["observed_knowledge_status"] == "CONFLICTED"
    assert len(derived["next_observation_requests"]) == 1
    assert derived["next_observation_requests"][0]["reason_code"] == "BLOCKER_REOBSERVATION"


def test_stale_observation_binding_fails_closed() -> None:
    fingerprint = state_fingerprint()
    scope = observation_scope()
    bundle = observed_bundle(scope, [raw_fact()], fingerprint, state_revision=9)
    request = derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": bundle,
            }
        ],
        fingerprint,
    )
    with pytest.raises(DifferenceError, match="stale Observation"):
        derive_differences(request)


@pytest.mark.parametrize("status", UNRESOLVED)
def test_unresolved_knowledge_is_never_satisfied(status: str) -> None:
    observed = normalize_observed_state(
        SUBJECT,
        {"objective_scope_name": "kernel"},
        {"kind": "OBSERVATION_SCOPE_BOUNDARY"},
        status,
        [],
    )
    comparison, mismatch = derive_comparison_and_mismatch(
        observed, {"operator": "equals", "expected_value": "READY", "expected_value_type": "STRING"}
    )
    assert comparison == "UNKNOWN"
    assert mismatch == "UNKNOWN"


def test_no_result_and_failed_map_to_unknown_not_to_absent_or_empty() -> None:
    assert negative_knowledge_status("NO_RESULT") == "UNKNOWN"
    assert negative_knowledge_status("FAILED") == "UNKNOWN"
    assert negative_knowledge_status("ABSENT") == "ABSENT"
    assert negative_knowledge_status("EMPTY") == "EMPTY"
    assert negative_knowledge_status("UNOBSERVED") == "UNOBSERVED"
    assert negative_knowledge_status("INVALID") == "REJECT_OR_QUARANTINE"


@pytest.mark.parametrize("status", ["ABSENT", "EMPTY", *UNRESOLVED])
def test_non_known_status_cannot_carry_observed_value_candidates(status: str) -> None:
    with pytest.raises(DifferenceError, match="must not carry observed value candidates"):
        normalize_observed_state(
            SUBJECT,
            {"objective_scope_name": "kernel"},
            {"kind": "OBSERVATION_SCOPE_BOUNDARY"},
            status,
            [{"value": "READY", "value_type": "STRING", "unit": None,
              "fact_predicate": "equals@v1", "effective_boundary": {}}],
        )


def test_absent_and_empty_are_not_satisfied_without_a_candidate() -> None:
    for status in ("ABSENT", "EMPTY"):
        observed = normalize_observed_state(
            SUBJECT, {"objective_scope_name": "kernel"},
            {"kind": "OBSERVATION_SCOPE_BOUNDARY"}, status, [],
        )
        comparison, mismatch = derive_comparison_and_mismatch(
            observed,
            {"operator": "equals", "expected_value": "READY", "expected_value_type": "STRING"},
        )
        assert comparison == "NOT_SATISFIED"
        assert mismatch == "MISSING"


def test_metadata_only_change_preserves_the_difference_identity() -> None:
    baseline = derive_differences(single_binding_request())
    request = single_binding_request()
    request["objective_revision"]["semantic_change_summary"] = "editorial rewording"
    request["objective_revision"]["recorded_at"] = "2026-08-31T23:59:59Z"
    request["risk_class"] = "HIGH"
    derived = derive_differences(request)
    assert (
        derived["differences"][0]["difference_id"]
        == baseline["differences"][0]["difference_id"]
    )


def test_material_target_change_produces_a_new_identity() -> None:
    baseline = derive_differences(single_binding_request())
    changed = derive_differences(single_binding_request(expected_value="LIVE"))
    assert (
        changed["differences"][0]["difference_id"]
        != baseline["differences"][0]["difference_id"]
    )


def test_boundary_change_produces_a_new_identity() -> None:
    baseline = derive_differences(single_binding_request())
    fingerprint = state_fingerprint()
    scope = observation_scope(scope_id="OBS-SCOPE-0009")
    request = derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": observed_bundle(scope, [raw_fact()], fingerprint),
            }
        ],
        fingerprint,
    )
    assert (
        derive_differences(request)["differences"][0]["difference_id"]
        != baseline["differences"][0]["difference_id"]
    )


def test_identity_collision_is_rejected() -> None:
    baseline = derive_differences(single_binding_request())
    difference = deepcopy(baseline["differences"][0])
    difference["structural_difference"]["target_value"] = "TAMPERED"
    request = single_binding_request()
    request["bindings"][0]["predecessor"] = {
        "difference": difference,
        "events": baseline["events"],
        "context": baseline,
    }
    with pytest.raises(DifferenceError, match="identity does not recompute"):
        derive_differences(request)


def test_same_identity_with_a_different_semantic_payload_is_rejected() -> None:
    baseline = derive_differences(single_binding_request())
    difference = deepcopy(baseline["differences"][0])
    difference["subject"] = "kernel.other"
    difference["difference_id"] = baseline["differences"][0]["difference_id"]
    request = single_binding_request()
    request["bindings"][0]["predecessor"] = {
        "difference": difference,
        "events": baseline["events"],
        "context": baseline,
    }
    with pytest.raises((IdentityCollisionError, DifferenceError)):
        derive_differences(request)


def test_invalid_predecessor_lineage_is_rejected() -> None:
    baseline = derive_differences(single_binding_request())
    events = deepcopy(baseline["events"])
    events[1]["previous_event_id"] = "D-EVT-" + "0" * 64
    request = single_binding_request()
    request["bindings"][0]["predecessor"] = {
        "difference": baseline["differences"][0],
        "events": events,
        "context": baseline,
    }
    with pytest.raises(DifferenceError, match="append-only chain"):
        derive_differences(request)


def test_secret_bearing_field_is_rejected() -> None:
    request = single_binding_request()
    request["bindings"][0]["api_token"] = "not-a-real-value"  # noqa: S105
    with pytest.raises(SecurityRejectionError, match="secret-bearing field"):
        derive_differences(request)


def test_secret_bearing_value_is_rejected() -> None:
    request = single_binding_request()
    request["objective_revision"]["statement"] = "use ghp_" + "a" * 36
    with pytest.raises(SecurityRejectionError, match="secret-bearing value"):
        derive_differences(request)


def test_moving_reference_is_rejected() -> None:
    request = single_binding_request()
    request["objective_revision"]["boundary_ref"] = {"kind": "objective_boundary", "id": "HEAD"}
    with pytest.raises(SecurityRejectionError, match="moving reference"):
        derive_differences(request)


def test_out_of_scope_subject_is_rejected() -> None:
    fingerprint = state_fingerprint()
    scope = observation_scope(included=["kernel.other"])
    request = derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": observed_bundle(
                    scope, [raw_fact(subject="kernel.other")], fingerprint
                ),
            }
        ],
        fingerprint,
    )
    with pytest.raises(BoundaryViolationError, match="outside the resolved Scope"):
        derive_differences(request)


def test_unknown_identity_profile_fails_closed() -> None:
    request = single_binding_request()
    request["identity_profile"] = "MANOSUBE-DIFFERENCE-SHA256-9.9"
    with pytest.raises(UnsupportedProfileError, match="identity_profile"):
        derive_differences(request)


def test_unknown_schema_version_fails_closed() -> None:
    request = single_binding_request()
    request["schema_version"] = "0.2"
    with pytest.raises(DifferenceError, match="unsupported schema_version"):
        derive_differences(request)


def test_malformed_observation_bundle_cannot_yield_a_difference() -> None:
    request = single_binding_request()
    request["bindings"][0]["observation_bundle"]["observations"][-1]["normalized_fact_refs"] = [
        {"kind": "normalized_fact", "id": "FACT-" + "0" * 64}
    ]
    with pytest.raises(DifferenceError, match="absent from the bundle"):
        derive_differences(request)


def test_predicate_absent_from_the_objective_is_rejected() -> None:
    request = single_binding_request()
    request["bindings"][0]["target_predicate_id"] = "TP-9999"
    with pytest.raises(DifferenceError, match="not declared by the Objective"):
        derive_differences(request)


def test_non_active_objective_revision_is_rejected() -> None:
    request = single_binding_request()
    request["objective_revision"]["status"] = "DRAFT"
    with pytest.raises(DifferenceError, match="ACTIVE Objective revision"):
        derive_differences(request)
