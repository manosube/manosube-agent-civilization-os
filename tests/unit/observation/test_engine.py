from __future__ import annotations

from copy import deepcopy

import pytest
from scripts.observation_contract_validator import validate_bundle

from manosube_agent_civilization.observation import (
    ObservationError,
    ObservationValidationError,
    ScopeViolationError,
    observe,
)
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
        "negative_evidence_refs": [{"kind": "negative_evidence", "id": "NEG-EVID-0001"}],
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
    after_request["prior_bundle"] = before
    after = observe(after_request)
    assert validate_bundle(after) == []
    assert {item["fact_id"] for item in before["facts"]} == {
        item["fact_id"] for item in after["facts"]
    }
    assert {item["binding_id"] for item in before["bindings"]}.isdisjoint(
        item["binding_id"] for item in after["bindings"] if item["state_revision_observed"] == 3
    )
    assert {item["evaluation_revision"] for item in after["fact_evaluations"]} == {0, 1}
    for fact_id in {item["fact_id"] for item in before["facts"]}:
        evaluations = sorted(
            (item for item in after["fact_evaluations"] if item["fact_id"] == fact_id),
            key=lambda item: item["evaluation_revision"],
        )
        assert evaluations[1]["previous_evaluation_id"] == evaluations[0]["evaluation_id"]


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
    request["collection_complete"] = False
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

    request["collection_complete"] = True
    negative = observe(request)["negative_observations"][0]
    assert negative["negative_status"] == "EMPTY"


def test_absent_requires_complete_bounded_gate() -> None:
    request = _request()
    request["source_occurrences"][0]["facts"] = []
    request["collection_complete"] = True
    request["scope"]["scope_status"] = "INCOMPLETE"
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

    request["scope"]["scope_status"] = "COMPLETE"
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


def test_negative_claim_outside_scope_fails_closed() -> None:
    request = _request()
    request["source_occurrences"][0]["facts"] = []
    request["negative_claims"] = [
        {
            "negative_status": "ABSENT",
            "subject": "fixture.secret",
            "predicate": "exists@v1",
            "effective_boundary": deepcopy(BOUNDARY),
        }
    ]
    with pytest.raises(ObservationError, match="Negative claim subject is outside scope"):
        observe(request)


def test_incomplete_scope_and_blocking_blind_spot_prevent_complete_status() -> None:
    request = _request()
    request["scope"]["scope_status"] = "INCOMPLETE"
    assert observe(request)["observations"][0]["status"] == "INCOMPLETE"

    request = _request()
    blind_spot = {
        "blind_spot_id": "BLIND-0001",
        "affected_subjects": ["fixture.enabled"],
        "reason": "bounded source unreadable",
        "impact": "BLOCKS_COMPLETION",
        "discovered_at": "2026-08-29T09:00:30Z",
        "resolvable": True,
        "required_follow_up": "repair source",
    }
    request["blind_spots"] = [blind_spot]
    assert observe(request)["observations"][0]["status"] == "INCOMPLETE"

    request["source_occurrences"][0]["facts"] = []
    request["negative_claims"] = [
        {
            "negative_status": "ABSENT",
            "subject": "fixture.enabled",
            "predicate": "exists@v1",
            "effective_boundary": deepcopy(BOUNDARY),
            "completion_evaluation": {
                "scope_complete": True,
                "method_complete": True,
                "required_attempts_completed": True,
                "no_blocking_blind_spot": True,
            },
        }
    ]
    with pytest.raises(ObservationError, match="absence gate"):
        observe(request)


def test_unordered_collection_has_stable_identity_and_rejects_duplicates() -> None:
    first = _request()
    first["source_occurrences"][0]["facts"] = [
        _fact("fixture.name", "members@v1", ["alpha", "beta"], "UNORDERED_COLLECTION")
    ]
    second = deepcopy(first)
    second["source_occurrences"][0]["facts"][0]["value"] = ["beta", "alpha"]
    assert observe(first)["facts"] == observe(second)["facts"]

    second["source_occurrences"][0]["facts"][0]["value"] = ["alpha", "alpha"]
    with pytest.raises(ObservationError, match="duplicate canonical members"):
        observe(second)


def test_positive_positive_conflict_is_not_supported() -> None:
    request = _request()
    request["source_occurrences"][0]["facts"].append(
        _fact("fixture.enabled", "equals@v1", False, "BOOLEAN")
    )
    bundle = observe(request)
    enabled = [
        item
        for item in bundle["fact_evaluations"]
        if next(f for f in bundle["facts"] if f["fact_id"] == item["fact_id"])["subject"]
        == "fixture.enabled"
    ]
    assert len(enabled) == 2
    assert all(item["evaluation_status"] == "CONFLICTED" for item in enabled)
    assert all(item["conflict_fact_refs"] for item in enabled)
    assert bundle["observations"][0]["status"] == "CONFLICTED"


def test_prior_fact_negative_conflict_appends_history() -> None:
    before = observe(_request())
    request = _request()
    request["state_revision_observed"] = 3
    request["state_fingerprint_observed"]["digest"] = "b" * 64
    request["source_occurrences"][0]["facts"] = []
    request["collection_complete"] = True
    request["prior_bundle"] = before
    request["negative_claims"] = [
        {
            "negative_status": "ABSENT",
            "subject": "fixture.enabled",
            "predicate": "equals@v1",
            "effective_boundary": deepcopy(BOUNDARY),
        }
    ]
    after = observe(request)
    enabled_id = next(
        item["fact_id"] for item in before["facts"] if item["subject"] == "fixture.enabled"
    )
    evaluations = sorted(
        (item for item in after["fact_evaluations"] if item["fact_id"] == enabled_id),
        key=lambda item: item["evaluation_revision"],
    )
    assert evaluations[0] == next(
        item for item in before["fact_evaluations"] if item["fact_id"] == enabled_id
    )
    assert evaluations[-1]["evaluation_status"] == "CONFLICTED"
    assert len(evaluations) == 2


def test_scope_source_method_attempt_and_time_must_match() -> None:
    request = _request()
    request["scope"]["source_snapshot_refs"][0]["id"] = "SNAP-OTHER"
    with pytest.raises(ObservationError, match="sources must exactly match"):
        observe(request)

    request = _request()
    request["attempts"][0]["method_ref"]["id"] = "METHOD-OTHER"
    with pytest.raises(ObservationError, match="undeclared method"):
        observe(request)

    request = _request()
    request["time_boundary"]["observation_started_at"] = "2026-08-29T09:02:00Z"
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


def test_exact_retry_is_idempotent_and_partial_quality_is_incomplete() -> None:
    first = observe(_request())
    retry = _request()
    retry["prior_bundle"] = first
    assert observe(retry) == first

    request = _request()
    request["source_occurrences"][0]["outcome"] = "PARTIAL"
    bundle = observe(request)
    assert bundle["observations"][0]["status"] == "INCOMPLETE"
    assert all(item["observed_quality_status"] == "INCOMPLETE" for item in bundle["bindings"])


def test_corrupt_prior_bundle_fails_closed() -> None:
    prior = observe(_request())
    prior["fact_evaluations"][0]["evaluation_revision"] = 2
    request = _request()
    request["state_revision_observed"] = 3
    request["state_fingerprint_observed"]["digest"] = "b" * 64
    request["prior_bundle"] = prior
    with pytest.raises(ObservationValidationError, match="revision gap"):
        observe(request)


def test_new_fact_conflicts_with_prior_negative_on_both_sides() -> None:
    initial = _request()
    initial["source_occurrences"][0]["facts"] = []
    initial["collection_complete"] = True
    initial["negative_claims"] = [
        {
            "negative_status": "ABSENT",
            "subject": "fixture.enabled",
            "predicate": "equals@v1",
            "effective_boundary": deepcopy(BOUNDARY),
        }
    ]
    before = observe(initial)
    request = _request()
    request["state_revision_observed"] = 3
    request["state_fingerprint_observed"]["digest"] = "b" * 64
    request["prior_bundle"] = before
    after = observe(request)
    assert after["observations"][-1]["status"] == "CONFLICTED"
    assert after["fact_evaluations"][-2]["evaluation_status"] == "CONFLICTED"
    assert after["negative_evaluations"][-1]["evaluation_status"] == "CONFLICTED"


def test_cross_revision_positive_conflict_is_bidirectional() -> None:
    before = observe(_request())
    request = _request()
    request["state_revision_observed"] = 3
    request["state_fingerprint_observed"]["digest"] = "b" * 64
    request["source_occurrences"][0]["facts"][0]["value"] = False
    request["prior_bundle"] = before
    after = observe(request)
    enabled = [item for item in after["facts"] if item["subject"] == "fixture.enabled"]
    latest = []
    for fact in enabled:
        latest.append(
            max(
                (e for e in after["fact_evaluations"] if e["fact_id"] == fact["fact_id"]),
                key=lambda e: e["evaluation_revision"],
            )
        )
    assert all(item["evaluation_status"] == "CONFLICTED" for item in latest)
    assert all(item["conflict_fact_refs"] for item in latest)


def test_changed_negative_retry_is_rejected() -> None:
    request = _request()
    request["source_occurrences"][0]["facts"] = []
    first = observe(request)
    request["prior_bundle"] = first
    request["negative_claims"] = [
        {
            "negative_status": "ABSENT",
            "subject": "fixture.enabled",
            "predicate": "exists@v1",
            "effective_boundary": deepcopy(BOUNDARY),
        }
    ]
    with pytest.raises(ObservationError, match=r"absence gate|non-identical retry"):
        observe(request)


def test_cutoff_and_freshness_block_absence() -> None:
    request = _request()
    request["source_occurrences"][0]["facts"] = []
    request["time_boundary"]["source_snapshot_time"] = "2026-08-29T08:50:00Z"
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


def test_binding_must_match_referenced_observation_state() -> None:
    prior = observe(_request())
    prior["bindings"][0]["state_revision_observed"] = 99
    request = _request()
    request["state_revision_observed"] = 3
    request["state_fingerprint_observed"]["digest"] = "b" * 64
    request["prior_bundle"] = prior
    with pytest.raises(ObservationValidationError, match="binding State mismatch"):
        observe(request)


def test_conflicted_retry_is_idempotent() -> None:
    request = _request()
    request["source_occurrences"][0]["facts"].append(
        _fact("fixture.enabled", "equals@v1", False, "BOOLEAN")
    )
    first = observe(request)
    request["prior_bundle"] = first
    assert observe(request) == first


def test_attempt_must_fall_inside_observation_window_for_absence() -> None:
    request = _request()
    request["source_occurrences"][0]["facts"] = []
    request["attempts"][0]["started_at"] = "2026-08-29T08:00:00Z"
    request["attempts"][0]["ended_at"] = "2026-08-29T08:01:00Z"
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


def test_empty_is_evaluated_at_claim_coordinate() -> None:
    request = _request()
    request["collection_complete"] = True
    request["negative_claims"] = [
        {
            "negative_status": "EMPTY",
            "subject": "fixture.name",
            "predicate": "members@v1",
            "effective_boundary": deepcopy(BOUNDARY),
        }
    ]
    negative = observe(request)["negative_observations"][0]
    assert negative["completion_evaluation"]["zero_valid_members"] is True


def test_evaluation_without_owner_fails_closed() -> None:
    prior = observe(_request())
    prior["fact_evaluations"][0]["fact_id"] = "FACT-MISSING"
    request = _request()
    request["state_revision_observed"] = 3
    request["state_fingerprint_observed"]["digest"] = "b" * 64
    request["prior_bundle"] = prior
    with pytest.raises(ObservationValidationError, match="missing Fact"):
        observe(request)


def test_negative_boundary_and_evidence_are_enforced() -> None:
    request = _request()
    request["source_occurrences"][0]["facts"] = []
    request["collection_complete"] = True
    request["negative_claims"] = [
        {
            "negative_status": "ABSENT",
            "subject": "fixture.enabled",
            "predicate": "exists@v1",
            "effective_boundary": {
                **deepcopy(BOUNDARY),
                "identity": "SNAP-OTHER",
            },
        }
    ]
    with pytest.raises(ObservationError, match="boundary was not observed"):
        observe(request)

    request["negative_claims"][0]["effective_boundary"] = deepcopy(BOUNDARY)
    request["negative_evidence_refs"] = []
    with pytest.raises(ObservationError, match="negative Evidence"):
        observe(request)


def test_negative_reason_change_is_not_an_idempotent_retry() -> None:
    request = _request()
    request["source_occurrences"][0]["facts"] = []
    request["collection_complete"] = True
    request["negative_claims"] = [
        {
            "negative_status": "ABSENT",
            "subject": "fixture.enabled",
            "predicate": "exists@v1",
            "effective_boundary": deepcopy(BOUNDARY),
            "reason": "first bounded conclusion",
        }
    ]
    first = observe(request)
    request["prior_bundle"] = first
    request["negative_claims"][0]["reason"] = "changed conclusion"
    with pytest.raises(ObservationError, match="non-identical retry"):
        observe(request)


@pytest.mark.parametrize(
    ("value_type", "value"),
    [("BOOLEAN", "false"), ("NULL", 0), ("INTEGER", True), ("TIMESTAMP", "not-time")],
)
def test_fact_value_must_conform_to_declared_type(value_type: str, value: object) -> None:
    request = _request()
    request["source_occurrences"][0]["facts"] = [
        _fact("fixture.enabled", "equals@v1", value, value_type)
    ]
    with pytest.raises(ObservationError, match="declared type"):
        observe(request)


def test_fact_payload_is_unicode_canonicalized() -> None:
    first = _request()
    first["source_occurrences"][0]["facts"] = [
        _fact("fixture.name", "equals@v1", "é", "STRING")
    ]
    second = deepcopy(first)
    second["source_occurrences"][0]["facts"][0]["value"] = "e\u0301"
    assert observe(first)["facts"] == observe(second)["facts"]


def test_historical_retry_is_independent_of_later_conflicts() -> None:
    original_request = _request()
    revision_two = observe(original_request)
    later = _request()
    later["state_revision_observed"] = 3
    later["state_fingerprint_observed"]["digest"] = "b" * 64
    later["source_occurrences"][0]["facts"][0]["value"] = False
    later["prior_bundle"] = revision_two
    history = observe(later)
    retry = deepcopy(original_request)
    retry["prior_bundle"] = history
    assert observe(retry) == history


def test_fact_boundary_must_be_observed() -> None:
    request = _request()
    request["source_occurrences"][0]["facts"][0]["effective_boundary"]["identity"] = (
        "SNAP-OTHER"
    )
    with pytest.raises(ObservationError, match="Fact effective boundary was not observed"):
        observe(request)


def test_empty_requires_successful_observation() -> None:
    request = _request()
    request["source_occurrences"][0]["facts"] = []
    request["source_occurrences"][0]["outcome"] = "FAILED"
    request["attempts"][0]["result"] = "FAILED"
    request["attempts"][0]["failure_class"] = "PARSER_FAILURE"
    request["collection_complete"] = True
    request["negative_claims"] = [
        {
            "negative_status": "EMPTY",
            "subject": "fixture.name",
            "predicate": "members@v1",
            "effective_boundary": deepcopy(BOUNDARY),
        }
    ]
    with pytest.raises(ObservationError, match="zero-member"):
        observe(request)


def test_positive_negative_conflict_retry_is_idempotent() -> None:
    request = _request()
    request["negative_claims"] = [
        {
            "negative_status": "ABSENT",
            "subject": "fixture.enabled",
            "predicate": "equals@v1",
            "effective_boundary": deepcopy(BOUNDARY),
        }
    ]
    first = observe(request)
    request["prior_bundle"] = first
    assert observe(request) == first
