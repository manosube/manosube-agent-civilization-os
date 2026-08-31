"""Proofs for lifecycle legality and status-preserving provenance appends.

Covers the independent review findings on `9004df7`: illegal predecessor transitions,
supersession from every legal predecessor state, and the payload a retained status still
requires on a status-preserving `OBSERVATION_BOUND` event.
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
    reobservation_pair,
    retained_status_predecessor,
    state_fingerprint,
)

from manosube_agent_civilization.difference import DifferenceError, derive_differences
from manosube_agent_civilization.difference.identity import lifecycle_event_id
from manosube_agent_civilization.difference.lifecycle import (
    LEGAL_TRANSITIONS,
    NEXT_OBSERVATION_REASON,
    legal_supersession_sources,
)
from manosube_agent_civilization.difference.validation import validate_record

_STATUSES = [
    "DETECTED",
    "OPEN",
    "ACTIVE",
    "VERIFYING",
    "BLOCKED",
    "RETAINED",
    "CLOSED",
    "REOPENED",
    "SUPERSEDED",
    "INVALIDATED",
]


def _material_change_request() -> dict[str, Any]:
    """Return a materially different derivation request over the real owners."""

    fingerprint = state_fingerprint("KNOWN")
    scope = observation_scope()
    return derivation_request(
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


def _predecessor_events(request: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = request["bindings"][0]["predecessor"]["events"]
    return events


def _with_predecessor() -> tuple[dict[str, Any], dict[str, Any]]:
    baseline_request, later_request = reobservation_pair()
    baseline = derive_differences(baseline_request)
    later_request["bindings"][0]["predecessor"] = {
        "difference": baseline["differences"][0],
        "events": deepcopy(baseline["events"]),
        "context": baseline,
    }
    return baseline, later_request


# --------------------------------------------------------------------------- #
# Illegal predecessor transitions are rejected by the single lifecycle authority.
# --------------------------------------------------------------------------- #

_ILLEGAL = [
    ("DETECTED", "VERIFYING"),
    ("DETECTED", "CLOSED"),
    ("DETECTED", "ACTIVE"),
    ("OPEN", "CLOSED"),
    ("OPEN", "VERIFYING"),
    ("OPEN", "REOPENED"),
]


@pytest.mark.parametrize(("source", "target"), _ILLEGAL, ids=[f"{a}_to_{b}" for a, b in _ILLEGAL])
def test_illegal_predecessor_transition_is_rejected(source: str, target: str) -> None:
    assert (source, target) not in LEGAL_TRANSITIONS
    _, request = _with_predecessor()
    events = _predecessor_events(request)
    events[1]["from_status"] = source
    events[1]["to_status"] = target
    events[0]["to_status"] = source
    events[0]["difference_event_id"] = lifecycle_event_id(events[0])
    events[1]["previous_event_id"] = events[0]["difference_event_id"]
    events[1]["difference_event_id"] = lifecycle_event_id(events[1])
    with pytest.raises(DifferenceError):
        derive_differences(request)


def test_status_continuity_break_is_rejected() -> None:
    _, request = _with_predecessor()
    events = _predecessor_events(request)
    events[1]["from_status"] = "BLOCKED"
    events[1]["difference_event_id"] = lifecycle_event_id(events[1])
    with pytest.raises(DifferenceError, match=r"status continuity|illegal lifecycle transition"):
        derive_differences(request)


def test_predecessor_observation_bound_event_may_not_mutate_status() -> None:
    _, request = _with_predecessor()
    events = _predecessor_events(request)
    events[1]["event_kind"] = "OBSERVATION_BOUND"
    events[1]["difference_event_id"] = lifecycle_event_id(events[1])
    with pytest.raises(DifferenceError, match=r"mutates status|schema-invalid"):
        derive_differences(request)


# --------------------------------------------------------------------------- #
# Supersession is permitted from every legal predecessor state, and only those.
# --------------------------------------------------------------------------- #


def test_legal_supersession_sources_come_from_the_single_authority() -> None:
    assert legal_supersession_sources() == {
        source for source, target in LEGAL_TRANSITIONS if target == "SUPERSEDED" and source
    }
    assert legal_supersession_sources() == {
        "OPEN",
        "ACTIVE",
        "VERIFYING",
        "BLOCKED",
        "RETAINED",
        "CLOSED",
        "REOPENED",
    }


@pytest.mark.parametrize("source", sorted(legal_supersession_sources()))
def test_material_change_supersedes_from_every_legal_source(source: str) -> None:
    """A material identity change is processable from any legally supersedable state."""

    _, seeded = retained_status_predecessor(source, "BLOCKER_REOBSERVATION")
    predecessor = seeded["bindings"][0]["predecessor"]
    difference = predecessor["difference"]
    changed = _material_change_request()
    changed["observation_method"] = seeded["observation_method"]
    changed["bindings"][0]["predecessor"] = predecessor
    try:
        bundle = derive_differences(changed)
    except DifferenceError as error:  # pragma: no cover - surfaced as a test failure
        pytest.fail(f"supersession from {source} was rejected: {error}")
    relation = bundle["supersession_relations"][0]
    terminal_event = next(
        event
        for event in bundle["events"]
        if event["difference_event_id"] == relation["old_terminal_event_ref"]["id"]
    )
    assert terminal_event["from_status"] == source
    assert terminal_event["to_status"] == "SUPERSEDED"
    assert bundle["materialized_status"][difference["difference_id"]] == "SUPERSEDED"


@pytest.mark.parametrize(
    "source", sorted(set(_STATUSES) - legal_supersession_sources() - {"DETECTED"})
)
def test_supersession_from_a_prohibited_source_is_rejected(source: str) -> None:
    assert (source, "SUPERSEDED") not in LEGAL_TRANSITIONS
    _, seeded = retained_status_predecessor("OPEN", "BLOCKER_REOBSERVATION")
    predecessor = seeded["bindings"][0]["predecessor"]
    events = deepcopy(predecessor["events"])
    head = events[-1]
    terminal = deepcopy(head)
    terminal.update(
        {
            "event_revision": head["event_revision"] + 1,
            "previous_event_id": head["difference_event_id"],
            "from_status": head["to_status"],
            "to_status": source,
            "reason_code": "UPSTREAM_OWNER_TRANSITION",
        }
    )
    terminal["difference_event_id"] = lifecycle_event_id(terminal)
    events.append(terminal)
    changed = _material_change_request()
    changed["bindings"][0]["predecessor"] = {
        "difference": predecessor["difference"],
        "events": events,
        "context": predecessor["context"],
    }
    with pytest.raises(DifferenceError):
        derive_differences(changed)


# --------------------------------------------------------------------------- #
# A status-preserving append carries everything its retained status requires.
# --------------------------------------------------------------------------- #


def test_retained_blocked_reobservation_is_cross_record_valid() -> None:
    _, request = retained_status_predecessor("BLOCKED", "BLOCKER_REOBSERVATION")
    bundle = derive_differences(request)
    assert validate_bundle(bundle) == []

    chain = sorted(bundle["events"], key=lambda item: item["event_revision"])
    bound = chain[-1]
    assert bound["event_kind"] == "OBSERVATION_BOUND"
    assert bound["from_status"] == bound["to_status"] == "BLOCKED"
    assert bound["blocker_kind"] == "OBSERVATION_PATH"
    assert bound["blocker_scope"] is not None
    assert bound["blocker_resolution_condition"] is not None
    assert bound["next_observation_ref"] is not None
    # The verification request is re-derived against this event, never copied.
    assert (
        bound["blocker_resolution_condition"]["verification_request_ref"]
        == bound["next_observation_ref"]
    )
    assert (
        bound["blocker_scope"]["effective_boundary"]
        == bundle["differences"][0]["effective_boundary"]
    )
    requests = {item["observation_request_id"]: item for item in bundle["next_observation_requests"]}
    fresh = requests[bound["next_observation_ref"]["id"]]
    assert fresh["derived_from_event_ref"]["id"] == bound["difference_event_id"]
    assert fresh["reason_code"] == "BLOCKER_REOBSERVATION"
    # The predecessor's own request is carried forward, not discarded.
    assert len(requests) == 2
    assert bundle["evaluations"], "the predecessor Closure Evaluation must be carried forward"


@pytest.mark.parametrize(
    ("status", "reason"),
    [("RETAINED", "RETAINED_REOBSERVATION"), ("REOPENED", "REOPEN_REOBSERVATION")],
)
def test_retained_status_append_carries_its_required_next_observation(
    status: str, reason: str
) -> None:
    """RETAINED and REOPENED keep their required Next Observation Request.

    Full cross-record validity of these two predecessors additionally requires Closure
    Evaluation modes and Reflow records owned by later phases, which this Engine never
    creates. The event, its payload and its request are proven here.
    """

    _, request = retained_status_predecessor(status, reason)
    bundle = derive_differences(request)
    chain = sorted(bundle["events"], key=lambda item: item["event_revision"])
    bound = chain[-1]
    validate_record(bound, "difference_lifecycle_event.schema.json")
    assert bound["event_kind"] == "OBSERVATION_BOUND"
    assert bound["from_status"] == bound["to_status"] == status
    assert bound["next_observation_ref"] is not None
    assert bound["blocker_kind"] is None
    requests = {item["observation_request_id"]: item for item in bundle["next_observation_requests"]}
    fresh = requests[bound["next_observation_ref"]["id"]]
    assert fresh["reason_code"] == reason == NEXT_OBSERVATION_REASON[status]
    assert fresh["derived_from_event_ref"]["id"] == bound["difference_event_id"]


def test_open_reobservation_needs_no_next_observation_reference() -> None:
    _, request = _with_predecessor()
    bundle = derive_differences(request)
    bound = sorted(bundle["events"], key=lambda item: item["event_revision"])[-1]
    assert bound["to_status"] == "OPEN"
    assert bound["next_observation_ref"] is None
    assert bound["blocker_kind"] is None


def test_missing_blocker_payload_on_a_blocked_predecessor_fails_closed() -> None:
    _, request = retained_status_predecessor("BLOCKED", "BLOCKER_REOBSERVATION")
    events = _predecessor_events(request)
    events[-1]["blocker_kind"] = None
    events[-1]["difference_event_id"] = lifecycle_event_id(events[-1])
    with pytest.raises(DifferenceError):
        derive_differences(request)


def test_a_predecessor_blocker_boundary_that_contradicts_its_difference_is_rejected() -> None:
    """The blocker payload is outside event identity, so the boundary decides it.

    This lineage was previously accepted and only reported by the independent auditor
    afterwards; the typed predecessor boundary now rejects it before anything is copied.
    """

    _, request = retained_status_predecessor("BLOCKED", "BLOCKER_REOBSERVATION")
    events = _predecessor_events(request)
    stale = {
        "kind": "OBSERVATION_SCOPE_BOUNDARY",
        "scope_ref": {"kind": "observation_scope", "id": "OBS-SCOPE-STALE"},
        "resolved_scope_record_sha256": "sha256:" + "0" * 64,
        "target_effective_window": {"start": None, "end": None},
        "source_snapshot_refs": {"collection_kind": "UNORDERED_SET", "members": []},
    }
    events[-1]["blocker_scope"]["effective_boundary"] = stale
    events[-1]["difference_event_id"] = lifecycle_event_id(events[-1])
    with pytest.raises(DifferenceError, match="blocker boundary mismatch"):
        derive_differences(request)


def test_the_appended_blocker_boundary_is_rederived_from_the_current_difference() -> None:
    """On the valid route the append builds its boundary, it never copies one."""

    _, request = retained_status_predecessor("BLOCKED", "BLOCKER_REOBSERVATION")
    bundle = derive_differences(request)
    bound = sorted(bundle["events"], key=lambda item: item["event_revision"])[-1]
    assert bound["event_kind"] == "OBSERVATION_BOUND"
    assert (
        bound["blocker_scope"]["effective_boundary"]
        == bundle["differences"][0]["effective_boundary"]
    )
    assert validate_bundle(bundle) == []


def test_stale_forward_reference_is_never_copied() -> None:
    """The retained event must not reuse the predecessor's own request reference."""

    _, request = retained_status_predecessor("BLOCKED", "BLOCKER_REOBSERVATION")
    predecessor_request = request["bindings"][0]["predecessor"]["context"][
        "next_observation_requests"
    ][0]["observation_request_id"]
    bundle = derive_differences(request)
    bound = sorted(bundle["events"], key=lambda item: item["event_revision"])[-1]
    assert bound["next_observation_ref"]["id"] != predecessor_request
