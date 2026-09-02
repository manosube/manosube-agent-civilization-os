"""A Next Observation Request's reason is bound to the status that requires it.

Covers the independent review finding on `2eae0b7`: a carried RETAINED event could point
at a request whose recomputed content address is valid but whose reason is
`REOPEN_REOBSERVATION`. The forward reference is outside event identity and the shared
helper did not compare reason against status, so producer and auditor both accepted forged
status provenance.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from scripts.difference_contract_validator import validate_bundle
from tests.difference_helpers import negative_claim, retained_status_predecessor

from manosube_agent_civilization.difference import DifferenceError, derive_differences
from manosube_agent_civilization.difference.canonical import content_address
from manosube_agent_civilization.difference.identity import lifecycle_event_id
from manosube_agent_civilization.difference.lifecycle import (
    NEXT_OBSERVATION_FORBIDDEN,
    NEXT_OBSERVATION_REASON,
    REQUIRES_NEXT_OBSERVATION,
    next_observation_binding_errors,
)

_REASONS = sorted(set(NEXT_OBSERVATION_REASON.values()))


def test_the_authority_covers_exactly_the_statuses_that_require_a_request() -> None:
    assert set(NEXT_OBSERVATION_REASON) == REQUIRES_NEXT_OBSERVATION == {
        "BLOCKED",
        "RETAINED",
        "REOPENED",
    }
    assert {"SUPERSEDED", "INVALIDATED"} == NEXT_OBSERVATION_FORBIDDEN
    assert set(NEXT_OBSERVATION_REASON.values()) == {
        "BLOCKER_REOBSERVATION",
        "RETAINED_REOBSERVATION",
        "REOPEN_REOBSERVATION",
    }


def _repoint(request: dict[str, Any], reason: str) -> dict[str, Any]:
    """Re-point the predecessor head at a request carrying *reason*, ids recomputed.

    Both the request's content address and the event's identity are recomputed, so neither
    identity rule can be what rejects the result -- only the status/reason binding can.
    """

    predecessor = request["bindings"][0]["predecessor"]
    carried = predecessor["context"]["next_observation_requests"][0]
    forged = deepcopy(carried)
    forged["reason_code"] = reason
    forged["observation_request_id"] = content_address(
        "OBS-REQ-", forged, "observation_request_id"
    )
    predecessor["context"]["next_observation_requests"] = [forged]
    event = predecessor["events"][-1]
    reference = {"kind": "next_observation_request", "id": forged["observation_request_id"]}
    event["next_observation_ref"] = deepcopy(reference)
    if event.get("blocker_resolution_condition") is not None:
        event["blocker_resolution_condition"]["verification_request_ref"] = deepcopy(reference)
    assert event["difference_event_id"] == lifecycle_event_id(event)
    return request


# --------------------------------------------------------------------------- #
# Every status that requires a request, against every reason.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("status", sorted(REQUIRES_NEXT_OBSERVATION))
@pytest.mark.parametrize("reason", _REASONS)
def test_every_status_accepts_only_its_own_reason(status: str, reason: str) -> None:
    _, request = retained_status_predecessor(status)
    _repoint(request, reason)

    if reason == NEXT_OBSERVATION_REASON[status]:
        bundle = derive_differences(request)
        appended = sorted(bundle["events"], key=lambda item: item["event_revision"])[-1]
        assert appended["to_status"] == status
        return

    with pytest.raises(DifferenceError, match="reason does not match status"):
        derive_differences(request)


def test_retained_pointing_at_a_reopen_reason_is_rejected() -> None:
    """The exact case the review named, with every identity recomputed."""

    _, request = retained_status_predecessor("RETAINED")
    _repoint(request, "REOPEN_REOBSERVATION")
    with pytest.raises(DifferenceError, match="RETAINED requires RETAINED_REOBSERVATION"):
        derive_differences(request)


@pytest.mark.parametrize("reason", ["RETAINED_REOBSERVATION", "BLOCKER_REOBSERVATION"])
def test_reopened_pointing_at_another_reason_is_rejected(reason: str) -> None:
    _, request = retained_status_predecessor("REOPENED")
    _repoint(request, reason)
    with pytest.raises(DifferenceError, match="REOPENED requires REOPEN_REOBSERVATION"):
        derive_differences(request)


@pytest.mark.parametrize("reason", ["RETAINED_REOBSERVATION", "REOPEN_REOBSERVATION"])
def test_blocked_pointing_at_a_non_blocker_reason_is_rejected(reason: str) -> None:
    _, request = retained_status_predecessor("BLOCKED")
    _repoint(request, reason)
    with pytest.raises(DifferenceError, match="BLOCKED requires BLOCKER_REOBSERVATION"):
        derive_differences(request)


# --------------------------------------------------------------------------- #
# Statuses that must not carry a request, and the ordinary routes.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("status", sorted(NEXT_OBSERVATION_FORBIDDEN))
def test_a_terminal_status_must_not_carry_a_request(status: str) -> None:
    """A settled Difference can never ask for a further observation."""

    _, request = retained_status_predecessor("BLOCKED")
    event = deepcopy(request["bindings"][0]["predecessor"]["events"][-1])
    event["to_status"] = status
    errors = next_observation_binding_errors(event, None, {}, {}, content_address)
    assert any("must not request a further observation" in message for message in errors)


def test_a_status_needing_no_request_and_carrying_none_is_accepted() -> None:
    _, request = retained_status_predecessor("OPEN")
    bundle = derive_differences(request)
    appended = sorted(bundle["events"], key=lambda item: item["event_revision"])[-1]
    assert appended["to_status"] == "OPEN"
    assert appended["next_observation_ref"] is None
    assert validate_bundle(bundle) == []


def test_the_ordinary_open_unresolved_route_still_gets_a_blocker_reason() -> None:
    from tests.difference_helpers import binding_request

    bundle = derive_differences(
        binding_request([], negative_claims=[negative_claim("NO_RESULT")])
    )
    assert len(bundle["next_observation_requests"]) == 1
    assert bundle["next_observation_requests"][0]["reason_code"] == "BLOCKER_REOBSERVATION"
    assert validate_bundle(bundle) == []


# --------------------------------------------------------------------------- #
# The rule is one object, and it holds on the valid routes.
# --------------------------------------------------------------------------- #


def test_the_engine_and_the_auditor_call_the_same_rule() -> None:
    import scripts.difference_contract_validator as validator

    from manosube_agent_civilization.difference import predecessor

    assert vars(validator)["next_observation_binding_errors"] is next_observation_binding_errors
    assert (
        vars(predecessor)["next_observation_binding_errors"] is next_observation_binding_errors
    )


@pytest.mark.parametrize("status", sorted(REQUIRES_NEXT_OBSERVATION))
def test_a_valid_status_specific_request_remains_cross_record_valid(status: str) -> None:
    _, request = retained_status_predecessor(status)
    bundle = derive_differences(request)
    appended = sorted(bundle["events"], key=lambda item: item["event_revision"])[-1]
    derived = [
        item
        for item in bundle["next_observation_requests"]
        if item["derived_from_event_ref"]["id"] == appended["difference_event_id"]
    ]
    assert len(derived) == 1
    assert derived[0]["reason_code"] == NEXT_OBSERVATION_REASON[status]
    if status in {"BLOCKED", "RETAINED"}:
        assert validate_bundle(bundle) == []
