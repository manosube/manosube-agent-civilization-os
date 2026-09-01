"""A canonical value is payload, everywhere: never unwrapped, never scanned as a reference.

Two findings met here. A Target whose literal business value was shaped like a typed
wrapper had its outer object discarded, so a Fact carrying only the inner object satisfied
the Target and suppressed the required Difference. And a schema-valid ``STRUCTURED`` Fact
value such as ``{"kind": "widget", "id": "HEAD"}`` was classified as a moving reference by
a whole-request shape scan. ``IDENTITY_REFERENCE`` is a declared canonical value type, so a
value may legitimately *be* reference-shaped; only a declared reference location is one.
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
    state_fingerprint,
    target_predicate,
)

from manosube_agent_civilization.difference import derive_differences
from manosube_agent_civilization.difference.errors import SecurityRejectionError
from manosube_agent_civilization.difference.projection import TYPED_SCALAR_WRAPPER_TYPES

STRUCTURED_LITERAL = {"value_type": "STRUCTURED", "value": {"a": 1}}


def _request(expected: Any, observed: Any, value_type: str = "STRUCTURED") -> dict[str, Any]:
    fingerprint = state_fingerprint()
    scope = observation_scope()
    bundle = observed_bundle(
        scope, [raw_fact(value=observed, value_type=value_type)], fingerprint
    )
    return derivation_request(
        objective_revision([target_predicate(expected_value=expected)]),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": bundle,
            }
        ],
        fingerprint,
    )


# --------------------------------------------------------------------------- #
# A structured Target is compared whole
# --------------------------------------------------------------------------- #


def test_a_fact_carrying_only_the_inner_object_does_not_satisfy_the_target() -> None:
    """The reviewed defect: the outer object was discarded and the Difference suppressed."""

    bundle = derive_differences(_request(STRUCTURED_LITERAL, {"a": 1}))
    assert bundle["satisfied_target_predicates"] == []
    assert len(bundle["differences"]) == 1
    target = bundle["differences"][0]["normalized_target_state"]
    assert target["expected_value"] == STRUCTURED_LITERAL
    assert target["expected_value_type"] == "STRUCTURED"
    assert validate_bundle(bundle) == []


def test_the_exact_full_structured_object_satisfies_the_target() -> None:
    bundle = derive_differences(_request(STRUCTURED_LITERAL, deepcopy(STRUCTURED_LITERAL)))
    assert bundle["satisfied_target_predicates"] == [PREDICATE_ID]
    assert bundle["differences"] == []


def test_a_nested_wrapper_shaped_business_object_stays_intact() -> None:
    nested = {"outer": {"value_type": "DECIMAL", "value": "1"}, "n": 2}
    bundle = derive_differences(_request(nested, {"outer": {"value_type": "DECIMAL"}}))
    target = bundle["differences"][0]["normalized_target_state"]
    assert target["expected_value"] == nested
    assert target["expected_value_type"] == "STRUCTURED"


@pytest.mark.parametrize(
    ("expected", "observed", "value_type"),
    [
        (None, "present", "STRING"),
        (True, False, "BOOLEAN"),
        (7, 8, "INTEGER"),
        ("READY", "NOT-READY", "STRING"),
        ({"kind": "widget", "id": "A"}, {"kind": "widget", "id": "B"}, "STRUCTURED"),
        (
            {"collection_kind": "ORDERED_LIST", "members": ["a"]},
            ["b"],
            "ORDERED_COLLECTION",
        ),
    ],
    ids=["null", "boolean", "integer", "string", "identity-shaped", "ordered-collection"],
)
def test_every_ordinary_value_shape_still_derives_a_difference(
    expected: Any, observed: Any, value_type: str
) -> None:
    bundle = derive_differences(_request(expected, observed, value_type))
    assert len(bundle["differences"]) == 1
    assert validate_bundle(bundle) == []


#: A canonical inner value and a differing observed value for each declared wrapper.
_WRAPPER_CASES: dict[str, tuple[Any, Any, str]] = {
    "DECIMAL": ("1.5", "2.5", "DECIMAL"),
    "TIMESTAMP": ("2026-08-30T09:00:00Z", "2026-08-30T10:00:00Z", "TIMESTAMP"),
    "DURATION": ("PT1S", "PT2S", "DURATION"),
    "IDENTITY_REFERENCE": (
        {"kind": "widget", "id": "W-1"},
        {"kind": "widget", "id": "W-2"},
        "IDENTITY_REFERENCE",
    ),
}


def test_the_wrapper_case_table_covers_every_declared_wrapper() -> None:
    assert set(_WRAPPER_CASES) == set(TYPED_SCALAR_WRAPPER_TYPES)


@pytest.mark.parametrize("wrapper", sorted(TYPED_SCALAR_WRAPPER_TYPES))
def test_every_declared_scalar_wrapper_still_unwraps_end_to_end(wrapper: str) -> None:
    inner, observed, value_type = _WRAPPER_CASES[wrapper]
    bundle = derive_differences(
        _request({"value_type": wrapper, "value": inner}, observed, value_type)
    )
    target = bundle["differences"][0]["normalized_target_state"]
    assert target["expected_value_type"] == wrapper
    assert target["expected_value"] == inner


def test_the_projection_is_deterministic() -> None:
    first = derive_differences(_request(STRUCTURED_LITERAL, {"a": 1}))
    second = derive_differences(_request(STRUCTURED_LITERAL, {"a": 1}))
    assert first == second


# --------------------------------------------------------------------------- #
# A reference-shaped value is never scanned as a reference
# --------------------------------------------------------------------------- #


MOVING = {"kind": "widget", "id": "HEAD"}


def test_a_moving_reference_shaped_value_is_ordinary_payload() -> None:
    """The reviewed defect: this raised SecurityRejectionError."""

    bundle = derive_differences(_request({"kind": "widget", "id": "OTHER"}, MOVING))
    assert len(bundle["differences"]) == 1
    observed = bundle["differences"][0]["normalized_observed_state"]
    assert observed["value_candidates"]["members"][0]["value"] == MOVING
    assert validate_bundle(bundle) == []


@pytest.mark.parametrize(
    "identity", ["HEAD", "LATEST", "CURRENT", "main", "refs-heads-x", "thing@latest"]
)
def test_every_moving_identity_is_still_payload_inside_a_value(identity: str) -> None:
    value = {"kind": "widget", "id": identity}
    bundle = derive_differences(_request({"kind": "widget", "id": "PINNED"}, value))
    assert len(bundle["differences"]) == 1


def test_a_moving_reference_in_a_declared_location_is_still_rejected() -> None:
    """The security rule is intact where the contract declares a reference."""

    request = _request({"kind": "widget", "id": "OTHER"}, MOVING)
    request["objective_revision"]["human_authority_ref"] = {
        "kind": "human_authority",
        "id": "HEAD",
    }
    with pytest.raises(SecurityRejectionError, match="moving reference"):
        derive_differences(request)


def test_a_moving_reference_in_a_carried_observation_is_still_rejected() -> None:
    request = _request({"kind": "widget", "id": "OTHER"}, MOVING)
    observation = request["bindings"][0]["observation_bundle"]["observations"][0]
    observation["observation_evidence_refs"] = [
        {"kind": "observation_evidence", "id": "LATEST"}
    ]
    with pytest.raises(SecurityRejectionError, match="moving reference"):
        derive_differences(request)


def test_a_moving_reference_in_the_requested_scope_is_still_rejected() -> None:
    request = _request({"kind": "widget", "id": "OTHER"}, MOVING)
    request["bindings"][0]["observation_scope"]["source_snapshot_refs"] = [
        {"kind": "source_snapshot", "id": "HEAD"}
    ]
    with pytest.raises(SecurityRejectionError, match="moving reference"):
        derive_differences(request)
