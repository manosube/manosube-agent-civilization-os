"""Cross-record conformance proofs for the deterministic Difference Engine.

Every generated record is validated against its canonical schema and against the
independent cross-record contract validator. The Engine's identity and supersession
results are compared against that independent auditor so that exactly one semantic
identity authority exists.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from scripts.difference_contract_validator import (
    _derive_comparison_and_mismatch,
    _difference_id,
    _supersession_reason_codes,
    apply_mutation,
    load_json,
    validate_bundle,
)
from tests.difference_helpers import (
    PREDICATE_ID,
    binding_request,
    derivation_request,
    negative_claim,
    objective_revision,
    observation_scope,
    observed_bundle,
    raw_fact,
    reobservation_pair,
    single_binding_request,
    state_fingerprint,
    target_predicate,
)

from manosube_agent_civilization.difference import (
    DifferenceValidationError,
    derive_differences,
)
from manosube_agent_civilization.difference.identity import lifecycle_event_id
from manosube_agent_civilization.difference.projection import derive_comparison_and_mismatch
from manosube_agent_civilization.difference.validation import validate_record
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = ROOT / "tests" / "contract" / "fixtures" / "difference"

_RECORD_SCHEMAS = {
    "differences": "difference.schema.json",
    "events": "difference_lifecycle_event.schema.json",
    "policies": "closure_policy.schema.json",
    "next_observation_requests": "next_observation_request.schema.json",
    "observation_methods": "observation_method.schema.json",
    "supersession_relations": "difference_supersession_relation.schema.json",
}


def _conflicted_request() -> dict[str, Any]:
    fingerprint = state_fingerprint()
    scope = observation_scope()
    claim = {
        "subject": "kernel.state",
        "predicate": "equals@v1",
        "negative_status": "ABSENT",
        "effective_boundary": {
            "kind": "SOURCE_SNAPSHOT",
            "identity": "SNAP-0001",
            "start": None,
            "end": None,
        },
    }
    return derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": observed_bundle(
                    scope, [raw_fact()], fingerprint, negative_claims=[claim]
                ),
            }
        ],
        fingerprint,
    )


def _pure_negative_request() -> dict[str, Any]:
    return binding_request([], negative_claims=[negative_claim("ABSENT")])


def _multi_candidate_request() -> dict[str, Any]:
    return binding_request(
        [raw_fact(value="FAIL"), raw_fact(value="BROKEN", predicate="exists@v1")],
        predicate=target_predicate(operator="all", expected_value="PASS"),
    )


def _supersession_bundle() -> dict[str, Any]:
    baseline = derive_differences(single_binding_request())
    fingerprint = state_fingerprint("KNOWN")
    scope = observation_scope()
    request = derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": observed_bundle(
                    scope, [raw_fact(value="DEGRADED")], fingerprint, state_revision=3
                ),
                "predecessor": {
                    "difference": baseline["differences"][0],
                    "events": baseline["events"],
                    "context": baseline,
                },
            }
        ],
        fingerprint,
        state_revision=3,
    )
    return derive_differences(request)


@pytest.mark.parametrize(
    "request_factory",
    [single_binding_request, _conflicted_request, _pure_negative_request, _multi_candidate_request],
    ids=["value_mismatch", "conflict", "pure_negative", "multi_candidate"],
)
def test_every_generated_record_is_schema_valid(request_factory: Any) -> None:
    bundle = derive_differences(request_factory())
    validated = 0
    for key, schema_name in _RECORD_SCHEMAS.items():
        for record in bundle[key]:
            validate_record(record, schema_name)
            validated += 1
    assert validated >= 4


@pytest.mark.parametrize(
    "request_factory",
    [single_binding_request, _conflicted_request, _pure_negative_request, _multi_candidate_request],
    ids=["value_mismatch", "conflict", "pure_negative", "multi_candidate"],
)
def test_generated_bundle_passes_cross_record_conformance(request_factory: Any) -> None:
    assert validate_bundle(derive_differences(request_factory())) == []


def test_engine_identity_equals_the_independent_contract_authority() -> None:
    bundle = derive_differences(single_binding_request())
    for difference in bundle["differences"]:
        assert difference["difference_id"] == _difference_id(difference)


def test_genesis_is_exactly_null_to_detected_at_revision_zero() -> None:
    bundle = derive_differences(single_binding_request())
    difference = bundle["differences"][0]
    genesis = next(
        event
        for event in bundle["events"]
        if event["difference_event_id"] == difference["genesis_event_ref"]["id"]
    )
    assert genesis["event_revision"] == 0
    assert genesis["previous_event_id"] is None
    assert genesis["from_status"] is None
    assert genesis["to_status"] == "DETECTED"
    assert genesis["event_kind"] == "TRANSITION"
    assert genesis["difference_id"] == difference["difference_id"]


def test_lifecycle_revisions_and_predecessors_are_exact() -> None:
    bundle = derive_differences(single_binding_request())
    chain = sorted(bundle["events"], key=lambda item: item["event_revision"])
    assert [event["event_revision"] for event in chain] == [0, 1]
    assert [(event["from_status"], event["to_status"]) for event in chain] == [
        (None, "DETECTED"),
        ("DETECTED", "OPEN"),
    ]
    assert chain[1]["previous_event_id"] == chain[0]["difference_event_id"]


def test_materialized_state_is_reconstructable_from_the_event_lineage() -> None:
    bundle = _supersession_bundle()
    reconstructed: dict[str, str] = {}
    for event in sorted(
        bundle["events"], key=lambda item: (item["difference_id"], item["event_revision"])
    ):
        reconstructed[event["difference_id"]] = event["to_status"]
    assert reconstructed == bundle["materialized_status"]
    assert set(reconstructed.values()) == {"OPEN", "SUPERSEDED"}


def test_difference_observation_binding_is_exact() -> None:
    bundle = derive_differences(single_binding_request())
    difference = bundle["differences"][0]
    observation = bundle["observations"][0]
    assert difference["observation_refs"] == [
        {"kind": "observation", "id": observation["observation_id"]}
    ]
    assert difference["observed_state_revision"] == observation["state_revision_observed"]
    assert difference["observed_state_fingerprint"] == observation["state_fingerprint_observed"]
    assert difference["observation_evidence_refs"] == observation["observation_evidence_refs"]
    assert (
        difference["objective_scope_binding"]["scope_ref"] == observation["scope_ref"]
    )
    assert (
        observation["target"]["target_identity"] == difference["target_predicate_ref"]["id"]
    )


def test_closure_policy_binding_is_exact() -> None:
    bundle = derive_differences(single_binding_request())
    difference = bundle["differences"][0]
    policy = bundle["policies"][0]
    reference = difference["closure_policy"]
    assert reference["id"] == policy["closure_policy_id"]
    assert reference["version"] == policy["policy_version"]
    assert reference["semantic_fingerprint"] == policy["policy_semantic_fingerprint"]
    assert policy["subject_difference_ref"] == {
        "kind": "difference",
        "id": difference["difference_id"],
    }
    assert policy["target_predicate_ref"] == difference["target_predicate_ref"]
    assert policy["contradiction_policy"] == "FAIL_CLOSED"


def test_supersession_is_bidirectional_and_append_only() -> None:
    bundle = _supersession_bundle()
    assert validate_bundle(bundle) == []
    assert len(bundle["supersession_relations"]) == 1
    relation = bundle["supersession_relations"][0]
    old_id = relation["old_difference_ref"]["id"]
    new_id = relation["new_difference_ref"]["id"]
    assert old_id != new_id
    assert {old_id, new_id} == {item["difference_id"] for item in bundle["differences"]}
    old_terminal = next(
        event
        for event in bundle["events"]
        if event["difference_event_id"] == relation["old_terminal_event_ref"]["id"]
    )
    new_genesis = next(
        event
        for event in bundle["events"]
        if event["difference_event_id"] == relation["new_genesis_event_ref"]["id"]
    )
    assert old_terminal["difference_id"] == old_id
    assert old_terminal["to_status"] == "SUPERSEDED"
    assert old_terminal["from_status"] == "OPEN"
    assert new_genesis["difference_id"] == new_id
    assert new_genesis["event_revision"] == 0
    old_chain = sorted(
        (event for event in bundle["events"] if event["difference_id"] == old_id),
        key=lambda item: item["event_revision"],
    )
    assert [event["event_revision"] for event in old_chain] == [0, 1, 2]


def test_supersession_reason_codes_match_the_independent_authority() -> None:
    bundle = _supersession_bundle()
    relation = bundle["supersession_relations"][0]
    index = {item["difference_id"]: item for item in bundle["differences"]}
    expected = _supersession_reason_codes(
        index[relation["old_difference_ref"]["id"]],
        index[relation["new_difference_ref"]["id"]],
    )
    assert set(relation["reason_codes"]) == expected
    assert relation["reason_codes"] == sorted(set(relation["reason_codes"]))
    assert relation["reason_codes"]


def test_equivalent_reobservation_appends_only_provenance() -> None:
    baseline_request, later_request = reobservation_pair()
    baseline = derive_differences(baseline_request)
    later_request["bindings"][0]["predecessor"] = {
        "difference": baseline["differences"][0],
        "events": baseline["events"],
        "context": baseline,
    }
    bundle = derive_differences(later_request)
    assert validate_bundle(bundle) == []
    assert (
        bundle["differences"][0]["difference_id"]
        == baseline["differences"][0]["difference_id"]
    )
    assert bundle["supersession_relations"] == []
    chain = sorted(bundle["events"], key=lambda item: item["event_revision"])
    assert [event["event_revision"] for event in chain] == [0, 1, 2]
    assert chain[2]["event_kind"] == "OBSERVATION_BOUND"
    assert chain[2]["from_status"] == chain[2]["to_status"] == "OPEN"
    assert chain[:2] == baseline["events"][:2]
    assert bundle["materialized_status"] == baseline["materialized_status"]


_MUTATIONS: list[tuple[str, list[str | int], Any]] = [
    ("tampered_difference_id", ["differences", 0, "difference_id"], "D-" + "0" * 64),
    ("tampered_subject", ["differences", 0, "subject"], "kernel.other"),
    (
        "tampered_mismatch_kind",
        ["differences", 0, "structural_difference", "mismatch_kind"],
        "MISSING",
    ),
    (
        "tampered_comparison_result",
        ["differences", 0, "structural_difference", "comparison_result"],
        "SATISFIED",
    ),
    (
        "tampered_target_value",
        ["differences", 0, "normalized_target_state", "expected_value"],
        "TAMPERED",
    ),
    ("tampered_genesis_revision", ["events", 0, "event_revision"], 3),
    ("tampered_genesis_status", ["events", 0, "to_status"], "OPEN"),
    ("tampered_event_predecessor", ["events", 1, "previous_event_id"], None),
    ("tampered_policy_fingerprint", ["policies", 0, "policy_semantic_fingerprint"], "sha256:" + "0" * 64),
    ("tampered_materialized_status_source", ["events", 1, "to_status"], "ACTIVE"),
    ("tampered_state_revision", ["differences", 0, "observed_state_revision"], 99),
    ("tampered_observation_ref", ["differences", 0, "observation_refs", 0, "id"], "OBS-MISSING"),
]


@pytest.mark.parametrize(
    "case", _MUTATIONS, ids=[case[0] for case in _MUTATIONS]
)
def test_no_invalid_mutation_escapes_cross_record_conformance(
    case: tuple[str, list[str | int], Any]
) -> None:
    _, path, value = case
    bundle = derive_differences(single_binding_request())
    mutated = apply_mutation(deepcopy(bundle), path, value)
    assert validate_bundle(mutated) != []


def test_objective_editorial_revision_preserves_the_difference_identity() -> None:
    baseline = derive_differences(single_binding_request())
    request = single_binding_request()
    request["objective_revision"]["change_reason"] = "editorial clarification"
    request["objective_revision"]["semantic_change_summary"] = "editorial only"
    request["objective_revision"]["recorded_at"] = "2026-08-31T10:00:00Z"
    request["objective_revision"]["human_authority_ref"] = {
        "kind": "human_authority",
        "id": "AUTH-0002",
    }
    derived = derive_differences(request)
    assert (
        derived["differences"][0]["difference_id"]
        == baseline["differences"][0]["difference_id"]
    )


def test_objective_semantic_change_produces_a_new_identity() -> None:
    baseline = derive_differences(single_binding_request())
    request = single_binding_request()
    request["objective_revision"]["statement"] = "The kernel reaches a different state."
    derived = derive_differences(request)
    assert (
        derived["differences"][0]["difference_id"]
        != baseline["differences"][0]["difference_id"]
    )


def test_target_predicate_change_produces_a_new_identity() -> None:
    baseline = derive_differences(single_binding_request())
    fingerprint = state_fingerprint()
    scope = observation_scope(target_identity="TP-0002")
    request = derivation_request(
        objective_revision([target_predicate(predicate_id="TP-0002")]),
        [
            {
                "target_predicate_id": "TP-0002",
                "observation_scope": scope,
                "observation_bundle": observed_bundle(scope, [raw_fact()], fingerprint),
            }
        ],
        fingerprint,
    )
    derived = derive_differences(request)
    assert (
        derived["differences"][0]["difference_id"]
        != baseline["differences"][0]["difference_id"]
    )


# --------------------------------------------------------------------------- #
# ADR-0002 corrections: canonical fixtures and their invalid mutation suites.
# --------------------------------------------------------------------------- #

_CANONICAL_FIXTURES = ["bundle", "negative_bundle", "multi_candidate_bundle"]


@pytest.mark.parametrize("stem", _CANONICAL_FIXTURES)
def test_canonical_fixture_passes_cross_record_conformance(stem: str) -> None:
    bundle = load_json(FIXTURE_ROOT / "valid" / f"{stem}.json")
    assert validate_bundle(bundle) == []


@pytest.mark.parametrize("stem", _CANONICAL_FIXTURES)
def test_canonical_fixture_records_are_schema_valid(stem: str) -> None:
    bundle = load_json(FIXTURE_ROOT / "valid" / f"{stem}.json")
    for key, schema_name in _RECORD_SCHEMAS.items():
        for record in bundle.get(key, []):
            validate_record(record, schema_name)


@pytest.mark.parametrize("stem", _CANONICAL_FIXTURES)
def test_no_invalid_fixture_case_escapes(stem: str) -> None:
    bundle = load_json(FIXTURE_ROOT / "valid" / f"{stem}.json")
    cases_path = FIXTURE_ROOT / "invalid" / f"{stem.replace('bundle', 'cases')}.json"
    cases = load_json(cases_path)
    assert cases, f"{stem} carries no invalid mutation cases"
    escapes = [
        case["name"]
        for case in cases
        if not validate_bundle(apply_mutation(bundle, case["path"], case["value"]))
    ]
    assert escapes == []


def test_observed_projection_rejects_the_superseded_unordered_set_shape() -> None:
    """A record still carrying the pre-ADR-0002 shape fails closed, never coerced."""

    bundle = derive_differences(_multi_candidate_request())
    difference = deepcopy(bundle["differences"][0])
    structural = difference["structural_difference"]
    structural["observed_values"]["collection_kind"] = "UNORDERED_SET"
    with pytest.raises(DifferenceValidationError):
        validate_record(difference, "difference.schema.json")

    difference = deepcopy(bundle["differences"][0])
    difference["structural_difference"]["observed_value_types"]["collection_kind"] = (
        "UNORDERED_SET"
    )
    with pytest.raises(DifferenceValidationError):
        validate_record(difference, "difference.schema.json")


def test_pure_negative_route_evidence_union_is_exact() -> None:
    bundle = derive_differences(_pure_negative_request())
    difference = bundle["differences"][0]
    observation = bundle["observations"][0]
    expected = {
        canonical_json_bytes(reference)
        for reference in observation["observation_evidence_refs"]
    } | {
        canonical_json_bytes(reference)
        for negative in bundle["negative_observations"]
        for reference in negative["negative_evidence_refs"]
    }
    assert {
        canonical_json_bytes(reference)
        for reference in difference["observation_evidence_refs"]
    } == expected
    assert validate_bundle(bundle) == []


def test_negative_evaluation_evidence_stays_in_its_own_channel() -> None:
    bundle = derive_differences(_pure_negative_request())
    negatives = {
        item["negative_observation_id"]: item for item in bundle["negative_observations"]
    }
    assert negatives
    for evaluation in bundle["negative_observation_evaluations"]:
        negative = negatives[evaluation["negative_observation_id"]]
        assert {canonical_json_bytes(r) for r in evaluation["evidence_refs"]} <= {
            canonical_json_bytes(r) for r in negative["negative_evidence_refs"]
        }


# --------------------------------------------------------------------------- #
# Independent-review findings: lineage identity, self-contained re-observation,
# bounded absence under `none`, and Negative Observation boundary.
# --------------------------------------------------------------------------- #


def test_engine_and_auditor_agree_on_every_comparison_route() -> None:
    """The Engine's mismatch derivation stays in lockstep with the independent auditor."""

    requests = [
        single_binding_request(),
        _conflicted_request(),
        _pure_negative_request(),
        _multi_candidate_request(),
        binding_request(
            [], predicate=target_predicate(operator="none", expected_value="READY"),
            negative_claims=[negative_claim("NO_RESULT")],
        ),
        binding_request([raw_fact(value="READY")],
                        predicate=target_predicate(operator="none", expected_value="READY")),
    ]
    for request in requests:
        bundle = derive_differences(request)
        assert validate_bundle(bundle) == []
        for difference in bundle["differences"]:
            comparison, mismatch = _derive_comparison_and_mismatch(
                difference["normalized_observed_state"],
                difference["normalized_target_state"],
            )
            assert difference["structural_difference"]["comparison_result"] == comparison
            assert difference["structural_difference"]["mismatch_kind"] == mismatch


@pytest.mark.parametrize("negative_status", ["ABSENT", "EMPTY"])
def test_bounded_absence_satisfies_none_in_both_authorities(negative_status: str) -> None:
    observed = {
        "subject": "kernel.state",
        "objective_scope_binding": {},
        "effective_boundary": {},
        "knowledge_status": negative_status,
        "value_candidates": {"collection_kind": "UNORDERED_SET", "members": []},
    }
    target = {
        "operator": "none",
        "expected_value": "READY",
        "expected_value_type": "STRING",
    }
    assert _derive_comparison_and_mismatch(observed, target) == ("SATISFIED", None)
    assert derive_comparison_and_mismatch(observed, target) == ("SATISFIED", None)


@pytest.mark.parametrize("knowledge", ["UNKNOWN", "UNOBSERVED", "BLOCKED", "INCOMPLETE"])
def test_unresolved_knowledge_never_satisfies_none_in_either_authority(
    knowledge: str,
) -> None:
    observed = {
        "subject": "kernel.state",
        "objective_scope_binding": {},
        "effective_boundary": {},
        "knowledge_status": knowledge,
        "value_candidates": {"collection_kind": "UNORDERED_SET", "members": []},
    }
    target = {
        "operator": "none",
        "expected_value": "READY",
        "expected_value_type": "STRING",
    }
    assert _derive_comparison_and_mismatch(observed, target) == ("UNKNOWN", "UNKNOWN")
    assert derive_comparison_and_mismatch(observed, target) == ("UNKNOWN", "UNKNOWN")


def test_equivalent_reobservation_bundle_is_cross_record_valid_and_self_contained() -> None:
    baseline_request, later_request = reobservation_pair()
    baseline = derive_differences(baseline_request)
    later_request["bindings"][0]["predecessor"] = {
        "difference": baseline["differences"][0],
        "events": baseline["events"],
        "context": baseline,
    }
    bundle = derive_differences(later_request)
    assert validate_bundle(bundle) == []
    observations = {item["observation_id"] for item in bundle["observations"]}
    assert len(observations) == 2
    for event in bundle["events"]:
        for reference in event["observation_refs"]:
            assert reference["id"] in observations
    genesis_id = bundle["differences"][0]["genesis_event_ref"]["id"]
    genesis = next(
        event for event in bundle["events"] if event["difference_event_id"] == genesis_id
    )
    assert genesis["event_revision"] == 0
    for reference in genesis["observation_refs"]:
        assert reference["id"] in observations


def test_every_returned_event_identity_recomputes() -> None:
    baseline_request, later_request = reobservation_pair()
    baseline = derive_differences(baseline_request)
    later_request["bindings"][0]["predecessor"] = {
        "difference": baseline["differences"][0],
        "events": baseline["events"],
        "context": baseline,
    }
    for bundle in (baseline, derive_differences(later_request), _supersession_bundle()):
        for event in bundle["events"]:
            assert event["difference_event_id"] == lifecycle_event_id(event)
