from __future__ import annotations

from copy import deepcopy

import pytest
from scripts.observation_contract_validator import validate_bundle

from manosube_agent_civilization.observation import ObservationError, ScopeViolationError, observe
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

FINGERPRINT = {
    "profile": "MANOSUBE-STATE-SHA256-0.1",
    "digest": "a" * 64,
}
BOUNDARY = {
    "kind": "SOURCE_SNAPSHOT",
    "identity": "SNAP-0001",
    "start": None,
    "end": None,
}


def _fact(subject: str, predicate: str, value: object, value_type: str) -> dict[str, object]:
    return {
        "subject": subject,
        "predicate": predicate,
        "value": value,
        "value_type": value_type,
        "unit": None,
        "effective_boundary": deepcopy(BOUNDARY),
    }


def _request() -> dict[str, object]:
    return {
        "project_id": "PRJ-0001",
        "state_revision_observed": 2,
        "state_fingerprint_observed": deepcopy(FINGERPRINT),
        "target_identity": "TARGET-0001",
        "target_kind": "FIXTURE",
        "scope": {
            "schema_version": "0.1",
            "scope_id": "SCOPE-0001",
            "project_id": "PRJ-0001",
            "target_identity": "TARGET-0001",
            "included_subjects": ["fixture.enabled", "fixture.name"],
            "excluded_subjects": ["fixture.secret"],
            "boundary_root": "/fixture",
            "path_policy": {
                "relative_locators_only": True,
                "symlink_escape": "BLOCK",
                "submodule_traversal": "DECLARED_ONLY",
                "mount_escape": "BLOCK",
                "credential_paths": "EXCLUDE",
            },
            "observation_window": {
                "start": "2026-08-29T09:00:00Z",
                "end": "2026-08-29T09:01:00Z",
            },
            "target_effective_window": {
                "start": "2026-08-29T08:00:00Z",
                "end": "2026-08-29T09:00:00Z",
            },
            "freshness_limit_seconds": 300,
            "cutoff": "2026-08-29T09:00:00Z",
            "source_snapshot_refs": [{"kind": "source_snapshot", "id": "SNAP-0001"}],
            "enumeration_rule": {"kind": "enumeration_rule", "id": "ENUM-0001"},
            "completion_predicate": {"kind": "completion_predicate", "id": "COMPLETE-0001"},
            "method_ref": {"kind": "observation_method", "id": "METHOD-0001"},
            "attempt_policy": {"max_attempts": 1, "timeout_seconds": 60, "retry_on": []},
            "blind_spots": [],
            "scope_status": "COMPLETE",
        },
        "method_ref": {"kind": "observation_method", "id": "METHOD-0001"},
        "time_boundary": {
            "observation_started_at": "2026-08-29T09:00:00Z",
            "observation_ended_at": "2026-08-29T09:01:00Z",
            "target_effective_start": "2026-08-29T08:00:00Z",
            "target_effective_end": "2026-08-29T09:00:00Z",
            "source_snapshot_time": "2026-08-29T08:59:00Z",
        },
        "source_snapshot_refs": [{"kind": "source_snapshot", "id": "SNAP-0001"}],
        "normalization_profile": "FIXTURE-0.1",
        "source_occurrences": [
            {
                "source_ref": {"kind": "source_snapshot", "id": "SNAP-0001"},
                "source_locator": "data/fixture.json",
                "facts": [
                    _fact("fixture.enabled", "equals@v1", True, "BOOLEAN"),
                    _fact("fixture.name", "equals@v1", "alpha", "STRING"),
                ],
            }
        ],
        "attempts": [
            {
                "attempt_id": "ATTEMPT-0001",
                "method_ref": {"kind": "observation_method", "id": "METHOD-0001"},
                "started_at": "2026-08-29T09:00:00Z",
                "ended_at": "2026-08-29T09:01:00Z",
                "result": "COMPLETE",
                "failure_class": None,
            }
        ],
        "blind_spots": [],
        "observation_evidence_refs": [{"kind": "observation_evidence", "id": "EVID-0001"}],
        "negative_claims": [],
    }


def test_one_occurrence_produces_multiple_facts_without_collision() -> None:
    bundle = observe(_request())
    assert validate_bundle(bundle) == []
    assert len(bundle["facts"]) == 2
    assert len(bundle["bindings"]) == 2
    assert len({item["source_occurrence_id"] for item in bundle["bindings"]}) == 1
    assert len({item["binding_id"] for item in bundle["bindings"]}) == 2


def test_ordering_does_not_change_semantic_output() -> None:
    first = _request()
    second = deepcopy(first)
    second["source_occurrences"][0]["facts"].reverse()
    assert canonical_json_bytes(observe(first)) == canonical_json_bytes(observe(second))


def test_reobservation_preserves_facts_and_appends_state_bound_provenance() -> None:
    before = observe(_request())
    after_request = _request()
    after_request["state_revision_observed"] = 3
    after_request["state_fingerprint_observed"] = {
        "profile": "MANOSUBE-STATE-SHA256-0.1",
        "digest": "b" * 64,
    }
    after = observe(after_request)
    assert {item["fact_id"] for item in before["facts"]} == {
        item["fact_id"] for item in after["facts"]
    }
    assert {item["binding_id"] for item in before["bindings"]}.isdisjoint(
        item["binding_id"] for item in after["bindings"]
    )


@pytest.mark.parametrize(
    "locator",
    ["/absolute/path", "../escape.json", "https://example.invalid/data", "data/token.json"],
)
def test_source_boundary_escape_fails_closed(locator: str) -> None:
    request = _request()
    request["source_occurrences"][0]["source_locator"] = locator
    with pytest.raises(ScopeViolationError):
        observe(request)


def test_scope_exclusion_fails_closed() -> None:
    request = _request()
    request["source_occurrences"][0]["facts"][0]["subject"] = "fixture.secret"
    with pytest.raises(ObservationError, match="outside scope"):
        observe(request)


def test_failed_attempt_is_never_empty_or_absent() -> None:
    request = _request()
    request["source_occurrences"][0]["facts"] = []
    request["source_occurrences"][0]["outcome"] = "FAILED"
    request["attempts"][0]["result"] = "FAILED"
    request["attempts"][0]["failure_class"] = "PARSER_FAILURE"
    assert observe(request)["observations"][0]["status"] == "FAILED"


def test_no_result_is_unknown_not_absent() -> None:
    request = _request()
    request["source_occurrences"][0]["facts"] = []
    request["negative_claims"] = [
        {
            "negative_status": "NO_RESULT",
            "subject": "fixture.enabled",
            "predicate": "exists@v1",
            "effective_boundary": deepcopy(BOUNDARY),
        }
    ]
    negative = observe(request)["negative_observations"][0]
    assert negative["conclusion"]["state_candidate"] == "UNKNOWN"


def test_empty_requires_complete_enumeration() -> None:
    request = _request()
    request["source_occurrences"][0]["facts"] = []
    request["collection_complete"] = True
    request["negative_claims"] = [
        {
            "negative_status": "EMPTY",
            "subject": "fixture.enabled",
            "predicate": "members@v1",
            "effective_boundary": deepcopy(BOUNDARY),
        }
    ]
    with pytest.raises(ObservationError, match="zero-member"):
        observe(request)

    request["negative_claims"][0]["completion_evaluation"] = {
        "scope_complete": True,
        "method_complete": True,
        "required_attempts_completed": True,
        "no_blocking_blind_spot": True,
        "collection_defined": True,
        "enumeration_complete": True,
        "zero_valid_members": True,
    }
    negative = observe(request)["negative_observations"][0]
    assert negative["negative_status"] == "EMPTY"


def test_absent_requires_complete_bounded_gate() -> None:
    request = _request()
    request["source_occurrences"][0]["facts"] = []
    request["negative_claims"] = [
        {
            "negative_status": "ABSENT",
            "subject": "fixture.enabled",
            "predicate": "exists@v1",
            "effective_boundary": deepcopy(BOUNDARY),
        }
    ]
    with pytest.raises(ObservationError, match="absence gate"):
        observe(request)

    request["negative_claims"][0]["completion_evaluation"] = {
        "scope_complete": True,
        "method_complete": True,
        "required_attempts_completed": True,
        "no_blocking_blind_spot": True,
    }
    negative = observe(request)["negative_observations"][0]
    assert negative["negative_status"] == "ABSENT"


def test_positive_negative_conflict_is_bidirectional() -> None:
    request = _request()
    request["negative_claims"] = [
        {
            "negative_status": "ABSENT",
            "subject": "fixture.enabled",
            "predicate": "equals@v1",
            "effective_boundary": deepcopy(BOUNDARY),
        }
    ]
    bundle = observe(request)
    negative = bundle["negative_evaluations"][0]
    fact = next(
        item
        for item in bundle["fact_evaluations"]
        if item["fact_id"] == negative["conflict_fact_refs"][0]["id"]
    )
    assert negative["evaluation_status"] == "CONFLICTED"
    assert fact["evaluation_status"] == "CONFLICTED"
    assert bundle["observations"][0]["status"] == "CONFLICTED"
    assert (
        fact["conflict_negative_observation_refs"][0]["id"] == negative["negative_observation_id"]
    )


def test_unknown_profile_and_invalid_state_binding_fail_closed() -> None:
    request = _request()
    request["normalization_profile"] = "UNKNOWN-9.9"
    with pytest.raises(ObservationError, match="unsupported normalization profile"):
        observe(request)
    request = _request()
    request["state_revision_observed"] = -1
    with pytest.raises(ObservationError, match="State revision"):
        observe(request)


def test_wrong_reference_kind_and_undeclared_source_fail_closed() -> None:
    request = _request()
    request["method_ref"]["kind"] = "evidence"
    with pytest.raises(ObservationError, match="reference kind mismatch"):
        observe(request)

    request = _request()
    request["source_occurrences"][0]["source_ref"]["id"] = "SNAP-UNDECLARED"
    with pytest.raises(ObservationError, match="not declared"):
        observe(request)
