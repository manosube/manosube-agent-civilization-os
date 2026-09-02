"""Exactly one Next Observation Request is derived per appended event.

Covers the independent review finding on `f2b1d89`: an equivalent re-observation of an
unresolved Difference already at BLOCKED, RETAINED or REOPENED took two request-derivation
paths. The retained-status branch minted the status-specific request, then the
unresolved-mismatch branch minted a second one for the same event and overwrote the
status-specific reason code with the generic blocker reason.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from scripts.difference_contract_validator import validate_bundle
from tests.difference_helpers import (
    PREDICATE_ID,
    negative_claim,
    raw_fact,
    retained_status_predecessor,
    single_binding_request,
)

from manosube_agent_civilization.difference import DifferenceError, derive_differences
from manosube_agent_civilization.difference.lifecycle import NEXT_OBSERVATION_REASON
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

# An unresolved baseline: no positive Fact, a bounded NO_RESULT negative observation.
# NO_RESULT maps to UNKNOWN knowledge, so the mismatch is UNKNOWN and the route requires a
# further bounded observation -- which is exactly the collision the finding describes.
_UNRESOLVED: dict[str, Any] = {"facts": [], "negative_claims": [negative_claim("NO_RESULT")]}
# A conflicted baseline: a positive Fact contradicted by a bounded Negative Observation.
_CONFLICTED: dict[str, Any] = {
    "facts": [raw_fact()],
    "negative_claims": [negative_claim("CONFLICTED")],
}


def _appended(bundle: dict[str, Any]) -> dict[str, Any]:
    event: dict[str, Any] = sorted(
        bundle["events"], key=lambda item: item["event_revision"]
    )[-1]
    return event


def _derived_from(bundle: dict[str, Any], event: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        request
        for request in bundle["next_observation_requests"]
        if request["derived_from_event_ref"]["id"] == event["difference_event_id"]
    ]


@pytest.mark.parametrize("route", ["unresolved", "conflicted"])
@pytest.mark.parametrize("status", ["BLOCKED", "RETAINED", "REOPENED"])
def test_one_request_per_appended_event_with_its_own_reason(status: str, route: str) -> None:
    shape = _UNRESOLVED if route == "unresolved" else _CONFLICTED
    baseline, request = retained_status_predecessor(
        status,
        NEXT_OBSERVATION_REASON[status],
        negative_claims=shape["negative_claims"],
        facts=shape["facts"],
    )
    # The premise: the Difference really is on an unresolved or conflicted route.
    assert baseline["differences"][0]["structural_difference"]["mismatch_kind"] in {
        "UNKNOWN",
        "CONFLICT",
    }

    bundle = derive_differences(request)
    appended = _appended(bundle)
    assert appended["event_kind"] == "OBSERVATION_BOUND"
    assert appended["to_status"] == status

    derived = _derived_from(bundle, appended)
    assert len(derived) == 1
    assert derived[0]["reason_code"] == NEXT_OBSERVATION_REASON[status]
    assert appended["next_observation_ref"]["id"] == derived[0]["observation_request_id"]


@pytest.mark.parametrize("status", ["BLOCKED", "RETAINED", "REOPENED"])
def test_the_status_specific_reason_is_never_overwritten(status: str) -> None:
    _, request = retained_status_predecessor(
        status, NEXT_OBSERVATION_REASON[status], **_UNRESOLVED
    )
    bundle = derive_differences(request)
    appended = _appended(bundle)
    reasons = {item["reason_code"] for item in _derived_from(bundle, appended)}
    assert reasons == {NEXT_OBSERVATION_REASON[status]}


@pytest.mark.parametrize("status", ["BLOCKED", "RETAINED", "REOPENED"])
def test_no_event_carries_two_requests_and_no_request_id_repeats(status: str) -> None:
    _, request = retained_status_predecessor(
        status, NEXT_OBSERVATION_REASON[status], **_UNRESOLVED
    )
    bundle = derive_differences(request)
    identities = [
        item["observation_request_id"] for item in bundle["next_observation_requests"]
    ]
    assert len(identities) == len(set(identities))
    per_event: dict[str, int] = {}
    for item in bundle["next_observation_requests"]:
        source = item["derived_from_event_ref"]["id"]
        per_event[source] = per_event.get(source, 0) + 1
    assert max(per_event.values()) == 1


def test_a_blocked_retained_reobservation_stays_cross_record_valid() -> None:
    """BLOCKED is provable end to end; see the non-claim below for RETAINED/REOPENED."""

    _, request = retained_status_predecessor(
        "BLOCKED", NEXT_OBSERVATION_REASON["BLOCKED"], **_UNRESOLVED
    )
    bundle = derive_differences(request)
    assert validate_bundle(bundle) == []
    appended = _appended(bundle)
    condition = appended["blocker_resolution_condition"]
    assert condition is not None
    # The blocker's own verification request is the one request this event derived.
    assert (
        condition["verification_request_ref"]["id"]
        == appended["next_observation_ref"]["id"]
    )


def test_a_retained_reobservation_is_now_fully_cross_record_valid() -> None:
    """RETAINED became provable once its Closure Evaluation was made conformant.

    The predecessor's Closure Evaluation is caller-supplied later-phase provenance. Once
    the typed boundary began validating it against its canonical schema, the helper had to
    supply a conformant record -- and with one, the whole RETAINED lineage validates end
    to end. This property was previously recorded as unproven.
    """

    _, request = retained_status_predecessor(
        "RETAINED", NEXT_OBSERVATION_REASON["RETAINED"], **_UNRESOLVED
    )
    bundle = derive_differences(request)
    assert validate_bundle(bundle) == []
    appended = _appended(bundle)
    assert len(_derived_from(bundle, appended)) == 1
    assert _derived_from(bundle, appended)[0]["reason_code"] == "RETAINED_REOBSERVATION"


def test_reopened_carries_its_request_but_is_not_claimed_complete() -> None:
    """REOPENED remains unproven, and the test pins exactly what is left.

    A conformant REOPENED lineage additionally requires the Evidence sufficiency, candidate
    claim and candidate invariant bindings a CANDIDATE_CLOSURE evaluation must satisfy --
    later-phase machinery this Engine deliberately does not create. Every remaining message
    must name that Closure Evaluation or an upstream lifecycle event, and none may concern
    a Next Observation Request.
    """

    _, request = retained_status_predecessor(
        "REOPENED", NEXT_OBSERVATION_REASON["REOPENED"], **_UNRESOLVED
    )
    bundle = derive_differences(request)
    appended = _appended(bundle)
    assert len(_derived_from(bundle, appended)) == 1
    assert _derived_from(bundle, appended)[0]["reason_code"] == "REOPEN_REOBSERVATION"

    remaining = validate_bundle(bundle)
    assert remaining
    for message in remaining:
        subject = message.rsplit(": ", 1)[-1]
        assert subject.startswith(("D-CLOSE-EVAL-", "D-EVT-")), message
        assert "observation request" not in message.lower(), message
        assert "duplicate" not in message.lower(), message


# --------------------------------------------------------------------------- #
# The ordinary routes are unaffected.
# --------------------------------------------------------------------------- #


def test_an_open_unresolved_route_still_receives_exactly_one_request() -> None:
    from tests.difference_helpers import binding_request

    bundle = derive_differences(
        binding_request([], negative_claims=[negative_claim("NO_RESULT")])
    )
    assert len(bundle["next_observation_requests"]) == 1
    assert bundle["next_observation_requests"][0]["reason_code"] == "BLOCKER_REOBSERVATION"
    head = _appended(bundle)
    assert len(_derived_from(bundle, head)) == 1
    assert validate_bundle(bundle) == []


def test_a_resolved_route_receives_none() -> None:
    bundle = derive_differences(single_binding_request())
    assert bundle["differences"][0]["structural_difference"]["mismatch_kind"] == "VALUE_MISMATCH"
    assert bundle["next_observation_requests"] == []
    for event in bundle["events"]:
        assert event["next_observation_ref"] is None


def test_an_open_retained_reobservation_needs_no_request() -> None:
    _, request = retained_status_predecessor("OPEN")
    bundle = derive_differences(request)
    appended = _appended(bundle)
    assert appended["to_status"] == "OPEN"
    assert appended["next_observation_ref"] is None
    assert _derived_from(bundle, appended) == []


def test_the_route_stays_deterministic() -> None:
    _, request = retained_status_predecessor(
        "BLOCKED", NEXT_OBSERVATION_REASON["BLOCKED"], **_UNRESOLVED
    )
    assert canonical_json_bytes(derive_differences(deepcopy(request))) == canonical_json_bytes(
        derive_differences(deepcopy(request))
    )


def test_an_unresolved_route_without_a_method_projection_fails_closed() -> None:
    from tests.difference_helpers import binding_request

    request = binding_request([], negative_claims=[negative_claim("NO_RESULT")])
    request.pop("observation_method", None)
    with pytest.raises(DifferenceError, match="Observation Method projection"):
        derive_differences(request)


def test_the_predicate_under_test_is_the_one_the_helpers_build() -> None:
    _, request = retained_status_predecessor("BLOCKED", **_UNRESOLVED)
    assert request["bindings"][0]["target_predicate_id"] == PREDICATE_ID
