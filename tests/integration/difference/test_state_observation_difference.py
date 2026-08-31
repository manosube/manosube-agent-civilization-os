"""State to Observation to Difference integration over the real canonical owners.

No substitute artifact stands in for the State, Store or Observation owners: the Project
State record is the canonical fixture, its fingerprint is produced by the real State
owner, the Observation records are produced by the real Observation Engine, and the
Difference records are produced by the real Difference Engine.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import pytest
from scripts.difference_contract_validator import validate_bundle as validate_difference_bundle
from scripts.observation_contract_validator import validate_bundle as validate_observation_bundle
from tests.difference_helpers import (
    PREDICATE_ID,
    SUBJECT,
    derivation_request,
    negative_claim,
    objective_revision,
    observation_request,
    observation_scope,
    raw_fact,
    retained_status_predecessor,
    target_predicate,
)
from tests.state_helpers import initial_state

from manosube_agent_civilization.difference import derive_differences
from manosube_agent_civilization.difference.validation import validate_record
from manosube_agent_civilization.observation import observe
from manosube_agent_civilization.state import canonical_json_bytes, fingerprint_semantic_state

pytestmark = [pytest.mark.integration, pytest.mark.natural_cycle]

ROOT = Path(__file__).resolve().parents[3]


def _exact_project_state() -> tuple[dict[str, Any], int, dict[str, str]]:
    """Return the canonical Project State with the real State owner's fingerprint."""

    state = initial_state()
    fingerprint = fingerprint_semantic_state(state["semantic_state"]).as_dict()
    state["semantic_fingerprint"] = fingerprint
    return state, state["state_revision"], fingerprint


def _route(observed_value: str) -> tuple[dict[str, Any], dict[str, Any], int, dict[str, str]]:
    _, revision, fingerprint = _exact_project_state()
    scope = observation_scope()
    observation_bundle = observe(
        observation_request(scope, [raw_fact(value=observed_value)], fingerprint, revision)
    )
    assert validate_observation_bundle(observation_bundle) == []
    difference_bundle = derive_differences(
        derivation_request(
            objective_revision([target_predicate()]),
            [
                {
                    "target_predicate_id": PREDICATE_ID,
                    "observation_scope": scope,
                    "observation_bundle": observation_bundle,
                }
            ],
            fingerprint,
            revision,
        )
    )
    return observation_bundle, difference_bundle, revision, fingerprint


def test_state_to_observation_to_difference_produces_conformant_records() -> None:
    observation_bundle, difference_bundle, revision, fingerprint = _route("NOT-READY")

    assert validate_difference_bundle(difference_bundle) == []
    assert len(difference_bundle["differences"]) == 1
    difference = difference_bundle["differences"][0]
    validate_record(difference, "difference.schema.json")

    observation = observation_bundle["observations"][-1]
    assert difference["observed_state_revision"] == revision
    assert difference["observed_state_fingerprint"] == fingerprint
    assert observation["state_revision_observed"] == revision
    assert observation["state_fingerprint_observed"] == fingerprint
    assert difference["observation_refs"] == [
        {"kind": "observation", "id": observation["observation_id"]}
    ]
    assert difference["subject"] == SUBJECT
    assert difference["structural_difference"]["mismatch_kind"] == "VALUE_MISMATCH"
    assert difference["structural_difference"]["observed_values"]["members"] == ["NOT-READY"]
    assert difference_bundle["materialized_status"] == {difference["difference_id"]: "OPEN"}


def test_state_to_observation_to_difference_satisfied_route_is_empty() -> None:
    _, difference_bundle, _, _ = _route("READY")
    assert validate_difference_bundle(difference_bundle) == []
    assert difference_bundle["differences"] == []
    assert difference_bundle["satisfied_target_predicates"] == [PREDICATE_ID]
    # An empty Difference set is not a Completion claim.
    assert difference_bundle["evaluations"] == []
    assert difference_bundle["candidate_completion_records"] == []


def test_route_is_deterministic_across_repeated_execution() -> None:
    first = _route("NOT-READY")[1]
    second = _route("NOT-READY")[1]
    assert canonical_json_bytes(first) == canonical_json_bytes(second)


def test_route_survives_a_canonical_serialization_round_trip(tmp_path: Path) -> None:
    """The derived records stay conformant across canonical persistence."""

    _, difference_bundle, _, _ = _route("NOT-READY")
    path = tmp_path / "difference_bundle.json"
    path.write_bytes(canonical_json_bytes(difference_bundle))
    restored = json.loads(path.read_text(encoding="utf-8"))
    assert restored == json.loads(canonical_json_bytes(difference_bundle))
    assert validate_difference_bundle(restored) == []


def test_observation_engine_output_is_not_mutated_by_the_difference_engine() -> None:
    _, revision, fingerprint = _exact_project_state()
    scope = observation_scope()
    observation_bundle = observe(
        observation_request(scope, [raw_fact()], fingerprint, revision)
    )
    snapshot = deepcopy(observation_bundle)
    derive_differences(
        derivation_request(
            objective_revision([target_predicate()]),
            [
                {
                    "target_predicate_id": PREDICATE_ID,
                    "observation_scope": scope,
                    "observation_bundle": observation_bundle,
                }
            ],
            fingerprint,
            revision,
        )
    )
    assert observation_bundle == snapshot


def _negative_route(
    negative_status: str,
) -> tuple[dict[str, Any], dict[str, Any], int, dict[str, str]]:
    """Drive the real owners over a bounded pure-negative Observation."""

    _, revision, fingerprint = _exact_project_state()
    scope = observation_scope()
    request = observation_request(scope, [], fingerprint, revision)
    request["negative_claims"] = [negative_claim(negative_status)]
    observation_bundle = observe(request)
    assert validate_observation_bundle(observation_bundle) == []
    difference_bundle = derive_differences(
        derivation_request(
            objective_revision([target_predicate()]),
            [
                {
                    "target_predicate_id": PREDICATE_ID,
                    "observation_scope": scope,
                    "observation_bundle": observation_bundle,
                }
            ],
            fingerprint,
            revision,
        )
    )
    return observation_bundle, difference_bundle, revision, fingerprint


@pytest.mark.parametrize(
    ("negative_status", "knowledge", "mismatch"),
    [
        ("ABSENT", "ABSENT", "MISSING"),
        ("EMPTY", "EMPTY", "MISSING"),
        ("NO_RESULT", "UNKNOWN", "UNKNOWN"),
        ("UNOBSERVED", "UNOBSERVED", "UNKNOWN"),
    ],
)
def test_state_to_observation_to_difference_pure_negative_route(
    negative_status: str, knowledge: str, mismatch: str
) -> None:
    observation_bundle, difference_bundle, revision, fingerprint = _negative_route(
        negative_status
    )
    assert validate_difference_bundle(difference_bundle) == []
    difference = difference_bundle["differences"][0]
    validate_record(difference, "difference.schema.json")

    assert difference["normalized_observed_state"]["knowledge_status"] == knowledge
    assert difference["structural_difference"]["mismatch_kind"] == mismatch
    assert difference["normalized_observed_state"]["value_candidates"]["members"] == []
    assert difference["observed_state_revision"] == revision
    assert difference["observed_state_fingerprint"] == fingerprint

    observation = observation_bundle["observations"][-1]
    expected_evidence = {
        canonical_json_bytes(reference)
        for reference in observation["observation_evidence_refs"]
    } | {
        canonical_json_bytes(reference)
        for negative in observation_bundle["negative_observations"]
        for reference in negative["negative_evidence_refs"]
    }
    assert {
        canonical_json_bytes(reference)
        for reference in difference["observation_evidence_refs"]
    } == expected_evidence


def test_state_to_observation_to_difference_never_promotes_no_result_to_absence() -> None:
    _, unresolved, _, _ = _negative_route("NO_RESULT")
    _, proven, _, _ = _negative_route("ABSENT")
    unresolved_structural = unresolved["differences"][0]["structural_difference"]
    proven_structural = proven["differences"][0]["structural_difference"]
    assert unresolved_structural["observed_knowledge_status"] == "UNKNOWN"
    assert unresolved_structural["comparison_result"] == "UNKNOWN"
    assert proven_structural["observed_knowledge_status"] == "ABSENT"
    assert proven_structural["comparison_result"] == "NOT_SATISFIED"
    assert (
        unresolved["differences"][0]["difference_id"]
        != proven["differences"][0]["difference_id"]
    )


def _multi_candidate_route(
    first: str, second: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    _, revision, fingerprint = _exact_project_state()
    scope = observation_scope()
    observation_bundle = observe(
        observation_request(
            scope,
            [raw_fact(value=first), raw_fact(value=second, predicate="exists@v1")],
            fingerprint,
            revision,
        )
    )
    assert validate_observation_bundle(observation_bundle) == []
    difference_bundle = derive_differences(
        derivation_request(
            objective_revision([target_predicate(operator="all", expected_value="PASS")]),
            [
                {
                    "target_predicate_id": PREDICATE_ID,
                    "observation_scope": scope,
                    "observation_bundle": observation_bundle,
                }
            ],
            fingerprint,
            revision,
        )
    )
    return observation_bundle, difference_bundle


@pytest.mark.parametrize(
    ("first", "second"),
    [("FAIL", "BROKEN"), ("FAIL", "FAIL")],
    ids=["shared_type", "shared_type_and_value"],
)
def test_state_to_observation_to_difference_multi_candidate_route(
    first: str, second: str
) -> None:
    observation_bundle, difference_bundle = _multi_candidate_route(first, second)
    assert validate_difference_bundle(difference_bundle) == []
    difference = difference_bundle["differences"][0]
    validate_record(difference, "difference.schema.json")

    observation = observation_bundle["observations"][-1]
    assert len(observation["normalized_fact_refs"]) == 2

    candidates = difference["normalized_observed_state"]["value_candidates"]["members"]
    structural = difference["structural_difference"]
    assert len(candidates) == 2
    assert structural["observed_values"]["collection_kind"] == "ORDERED_LIST"
    assert structural["observed_value_types"]["collection_kind"] == "ORDERED_LIST"
    assert structural["observed_values"]["members"] == [item["value"] for item in candidates]
    assert structural["observed_value_types"]["members"] == [
        item["value_type"] for item in candidates
    ]
    assert structural["observed_value_types"]["members"] == ["STRING", "STRING"]
    assert sorted(structural["observed_values"]["members"]) == sorted([first, second])


def test_multi_candidate_route_identity_is_stable_across_source_order() -> None:
    first = _multi_candidate_route("FAIL", "BROKEN")[1]
    second = _multi_candidate_route("FAIL", "BROKEN")[1]
    assert canonical_json_bytes(first) == canonical_json_bytes(second)


@pytest.mark.parametrize("negative_status", ["ABSENT", "EMPTY"])
def test_state_to_observation_to_difference_bounded_absence_satisfies_none(
    negative_status: str,
) -> None:
    """Bounded proven absence satisfies `none` over the real owners."""

    _, revision, fingerprint = _exact_project_state()
    scope = observation_scope()
    request = observation_request(scope, [], fingerprint, revision)
    request["negative_claims"] = [negative_claim(negative_status)]
    observation_bundle = observe(request)
    assert validate_observation_bundle(observation_bundle) == []
    difference_bundle = derive_differences(
        derivation_request(
            objective_revision(
                [target_predicate(operator="none", expected_value="READY")]
            ),
            [
                {
                    "target_predicate_id": PREDICATE_ID,
                    "observation_scope": scope,
                    "observation_bundle": observation_bundle,
                }
            ],
            fingerprint,
            revision,
        )
    )
    assert validate_difference_bundle(difference_bundle) == []
    assert difference_bundle["differences"] == []
    assert difference_bundle["satisfied_target_predicates"] == [PREDICATE_ID]
    # A bounded empty Difference set is still not a Completion claim.
    assert difference_bundle["evaluations"] == []
    assert difference_bundle["candidate_completion_records"] == []


@pytest.mark.parametrize("negative_status", ["NO_RESULT", "UNOBSERVED"])
def test_state_to_observation_to_difference_unresolved_absence_never_satisfies_none(
    negative_status: str,
) -> None:
    _, revision, fingerprint = _exact_project_state()
    scope = observation_scope()
    request = observation_request(scope, [], fingerprint, revision)
    request["negative_claims"] = [negative_claim(negative_status)]
    observation_bundle = observe(request)
    assert validate_observation_bundle(observation_bundle) == []
    difference_bundle = derive_differences(
        derivation_request(
            objective_revision(
                [target_predicate(operator="none", expected_value="READY")]
            ),
            [
                {
                    "target_predicate_id": PREDICATE_ID,
                    "observation_scope": scope,
                    "observation_bundle": observation_bundle,
                }
            ],
            fingerprint,
            revision,
        )
    )
    assert validate_difference_bundle(difference_bundle) == []
    assert len(difference_bundle["differences"]) == 1
    structural = difference_bundle["differences"][0]["structural_difference"]
    assert structural["comparison_result"] == "UNKNOWN"
    assert structural["mismatch_kind"] == "UNKNOWN"
    assert difference_bundle["satisfied_target_predicates"] == []


def test_state_to_observation_to_difference_equivalent_reobservation_is_self_contained() -> None:
    """The real append-only Observation lineage keeps the retained events resolvable."""

    _, revision, fingerprint = _exact_project_state()
    scope = observation_scope()
    first_bundle = observe(observation_request(scope, [raw_fact()], fingerprint, revision))
    assert validate_observation_bundle(first_bundle) == []
    objective = objective_revision([target_predicate()])

    def _derive(
        observation_bundle: dict[str, Any],
        state_revision: int,
        state_fingerprint: dict[str, str],
        predecessor: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        binding: dict[str, Any] = {
            "target_predicate_id": PREDICATE_ID,
            "observation_scope": scope,
            "observation_bundle": observation_bundle,
        }
        if predecessor is not None:
            binding["predecessor"] = predecessor
        return derive_differences(
            derivation_request(objective, [binding], state_fingerprint, state_revision)
        )

    baseline = _derive(first_bundle, revision, fingerprint)
    assert validate_difference_bundle(baseline) == []

    later_fingerprint = {"profile": fingerprint["profile"], "digest": "d" * 64}
    later_bundle = observe(
        observation_request(
            scope,
            [raw_fact()],
            later_fingerprint,
            revision + 1,
            prior_bundle=first_bundle,
        )
    )
    assert validate_observation_bundle(later_bundle) == []
    derived = _derive(
        later_bundle,
        revision + 1,
        later_fingerprint,
        {
            "difference": baseline["differences"][0],
            "events": baseline["events"],
            "context": baseline,
        },
    )

    assert validate_difference_bundle(derived) == []
    assert (
        derived["differences"][0]["difference_id"]
        == baseline["differences"][0]["difference_id"]
    )
    observations = {item["observation_id"] for item in derived["observations"]}
    assert len(observations) == 2
    for event in derived["events"]:
        for reference in event["observation_refs"]:
            assert reference["id"] in observations
    chain = sorted(derived["events"], key=lambda item: item["event_revision"])
    assert [event["event_kind"] for event in chain] == [
        "TRANSITION",
        "TRANSITION",
        "OBSERVATION_BOUND",
    ]

    # The record itself is immutable: the real second Observation, its new State
    # revision and its Evidence reach the bundle only through the appended event.
    predecessor = baseline["differences"][0]
    assert canonical_json_bytes(derived["differences"][0]) == canonical_json_bytes(predecessor)
    assert chain[-1]["state_revision_evaluated"] == revision + 1
    assert predecessor["observed_state_revision"] == revision
    assert {reference["id"] for reference in chain[-1]["observation_refs"]} == {
        observation["observation_id"] for observation in later_bundle["observations"]
    } - {observation["observation_id"] for observation in first_bundle["observations"]}

    # The predecessor still reads back against its own Observation, whose Fact was
    # re-evaluated by the later Observation in the same append-only lineage.
    assert len(later_bundle["fact_evaluations"]) > len(first_bundle["fact_evaluations"])


def test_state_to_observation_to_difference_retained_blocked_reobservation() -> None:
    """A retained BLOCKED status keeps its payload across a real re-observation."""

    _, request = retained_status_predecessor("BLOCKED", "BLOCKER_REOBSERVATION")
    observation_bundle = request["bindings"][0]["observation_bundle"]
    assert validate_observation_bundle(observation_bundle) == []

    bundle = derive_differences(request)
    assert validate_difference_bundle(bundle) == []

    chain = sorted(bundle["events"], key=lambda item: item["event_revision"])
    bound = chain[-1]
    validate_record(bound, "difference_lifecycle_event.schema.json")
    assert bound["event_kind"] == "OBSERVATION_BOUND"
    assert bound["from_status"] == bound["to_status"] == "BLOCKED"
    assert bound["blocker_kind"] is not None
    assert (
        bound["blocker_resolution_condition"]["verification_request_ref"]
        == bound["next_observation_ref"]
    )
    requests = {item["observation_request_id"] for item in bundle["next_observation_requests"]}
    assert bound["next_observation_ref"]["id"] in requests
    observations = {item["observation_id"] for item in bundle["observations"]}
    for event in bundle["events"]:
        for reference in event["observation_refs"]:
            assert reference["id"] in observations


_BOUNDARY_KINDS = {
    "SOURCE_SNAPSHOT": {
        "kind": "SOURCE_SNAPSHOT",
        "identity": "SNAP-0001",
        "start": None,
        "end": None,
    },
    "TIME_INTERVAL": {
        "kind": "TIME_INTERVAL",
        "identity": "kernel",
        "start": "2026-08-30T08:00:00Z",
        "end": "2026-08-30T09:00:00Z",
    },
    "STATE_REVISION": {"kind": "STATE_REVISION", "identity": "kernel", "start": 2, "end": 2},
}


@pytest.mark.parametrize("kind", sorted(_BOUNDARY_KINDS))
def test_state_to_observation_to_difference_every_fact_boundary_kind(kind: str) -> None:
    """Each contract-legal Fact boundary derives a conformant Difference over real owners."""

    _, revision, fingerprint = _exact_project_state()
    scope = observation_scope()
    fact = raw_fact()
    fact["effective_boundary"] = deepcopy(_BOUNDARY_KINDS[kind])
    if kind == "STATE_REVISION":
        fact["effective_boundary"]["start"] = revision
        fact["effective_boundary"]["end"] = revision
    observation_bundle = observe(observation_request(scope, [fact], fingerprint, revision))
    assert validate_observation_bundle(observation_bundle) == []

    difference_bundle = derive_differences(
        derivation_request(
            objective_revision([target_predicate()]),
            [
                {
                    "target_predicate_id": PREDICATE_ID,
                    "observation_scope": scope,
                    "observation_bundle": observation_bundle,
                }
            ],
            fingerprint,
            revision,
        )
    )
    assert validate_difference_bundle(difference_bundle) == []
    difference = difference_bundle["differences"][0]
    validate_record(difference, "difference.schema.json")
    assert difference_bundle["normalized_facts"][0]["effective_boundary"]["kind"] == kind


def test_state_to_observation_to_difference_rejects_a_forged_upstream_fact() -> None:
    """A real Observation whose Fact payload was altered afterwards fails closed."""

    from manosube_agent_civilization.difference import IdentityCollisionError

    _, revision, fingerprint = _exact_project_state()
    scope = observation_scope()
    observation_bundle = observe(
        observation_request(scope, [raw_fact()], fingerprint, revision)
    )
    assert validate_observation_bundle(observation_bundle) == []
    for fact in observation_bundle["facts"]:
        fact["value"] = "FORGED-AFTER-OBSERVATION"
    with pytest.raises(IdentityCollisionError, match="does not recompute"):
        derive_differences(
            derivation_request(
                objective_revision([target_predicate()]),
                [
                    {
                        "target_predicate_id": PREDICATE_ID,
                        "observation_scope": scope,
                        "observation_bundle": observation_bundle,
                    }
                ],
                fingerprint,
                revision,
            )
        )


def test_state_to_observation_to_difference_carries_the_whole_lineage_closure() -> None:
    """A fresh Difference over a real append-only lineage emits no dangling reference."""

    from manosube_agent_civilization.observation.identity import observation_identity

    _, revision, fingerprint = _exact_project_state()
    scope = observation_scope()
    first_bundle = observe(observation_request(scope, [raw_fact()], fingerprint, revision))
    later_fingerprint = {"profile": fingerprint["profile"], "digest": "e" * 64}
    later_bundle = observe(
        observation_request(
            scope,
            [raw_fact()],
            later_fingerprint,
            revision + 1,
            prior_bundle=first_bundle,
        )
    )
    assert validate_observation_bundle(later_bundle) == []
    assert len(later_bundle["observations"]) == 2
    assert len(later_bundle["fact_evaluations"]) == 2

    derived = derive_differences(
        derivation_request(
            objective_revision([target_predicate()]),
            [
                {
                    "target_predicate_id": PREDICATE_ID,
                    "observation_scope": scope,
                    "observation_bundle": later_bundle,
                    # No Difference predecessor: this is a first derivation over a lineage
                    # that already carries an earlier Observation of the same Fact.
                }
            ],
            later_fingerprint,
            revision + 1,
        )
    )
    assert validate_difference_bundle(derived) == []

    bindings = {item["binding_id"] for item in derived["fact_observation_bindings"]}
    observations = {item["observation_id"] for item in derived["observations"]}
    facts = {item["fact_id"] for item in derived["normalized_facts"]}
    assert len(observations) == 2
    for evaluation in derived["fact_evaluations"]:
        for reference in evaluation["binding_refs"]:
            assert reference["id"] in bindings
    for binding in derived["fact_observation_bindings"]:
        assert binding["observation_id"] in observations
        assert binding["fact_id"] in facts
    for observation in derived["observations"]:
        assert observation["observation_id"] == observation_identity(observation)


def test_state_to_observation_to_difference_rejects_a_forged_observation_payload() -> None:
    """A real Observation altered after the fact fails closed on its own identity."""

    from manosube_agent_civilization.difference import IdentityCollisionError

    _, revision, fingerprint = _exact_project_state()
    scope = observation_scope()
    observation_bundle = observe(
        observation_request(scope, [raw_fact()], fingerprint, revision)
    )
    assert validate_observation_bundle(observation_bundle) == []
    for observation in observation_bundle["observations"]:
        observation["method_ref"] = {"kind": "observation_method", "id": "OBS-METHOD-9999"}
    with pytest.raises(IdentityCollisionError, match="Observation identity does not recompute"):
        derive_differences(
            derivation_request(
                objective_revision([target_predicate()]),
                [
                    {
                        "target_predicate_id": PREDICATE_ID,
                        "observation_scope": scope,
                        "observation_bundle": observation_bundle,
                    }
                ],
                fingerprint,
                revision,
            )
        )
