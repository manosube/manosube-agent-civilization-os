"""A typed Target wrapper declares a canonical value, and only its shape was checked.

`DIFFERENCE_IDENTITY.md` declares the reserved wrapper's inner value as a *canonical*
decimal, UTC timestamp, duration or identity reference, and says the inner value is
projected into `expected_value`. The projection trusted the type tag: a Target declaring
`2026-08-30T09:00:00+01:00` names the same instant as a Fact the Observation element
normalises to `2026-08-30T08:00:00Z`, and did not equal it.

The route it escaped by is the one ADR-0016 §2b named: a satisfied comparison emits no
record, so the emitted-Difference schema — which does constrain these patterns — never sees
it. Under an operator that consults `expected_value`, the same Target was already rejected
by that schema, late and with a generated-schema message.
"""

from __future__ import annotations

from typing import Any

import pytest
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

from manosube_agent_civilization.difference import DifferenceError, derive_differences
from manosube_agent_civilization.difference.projection import (
    TYPED_SCALAR_WRAPPER_TYPES,
    reject_noncanonical_typed_value,
)
from manosube_agent_civilization.observation.normalization import canonical_value

NON_CANONICAL: dict[str, Any] = {
    "TIMESTAMP": "2026-08-30T09:00:00+01:00",
    "DECIMAL": "not-a-number",
    "DURATION": "NOT-A-DURATION",
    "IDENTITY_REFERENCE": {"kind": "widget", "id": "W1", "extra": 1},
}
CANONICAL: dict[str, Any] = {
    "TIMESTAMP": "2026-08-30T08:00:00Z",
    "DECIMAL": "1.5",
    "DURATION": "PT1H",
    "IDENTITY_REFERENCE": {"kind": "widget", "id": "W1"},
}


def _request(expected: Any, operator: str = "exists") -> dict[str, Any]:
    fingerprint = state_fingerprint()
    scope = observation_scope()
    return derivation_request(
        objective_revision([target_predicate(operator=operator, expected_value=expected)]),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": observed_bundle(
                    scope, [raw_fact(value="READY")], fingerprint
                ),
            }
        ],
        fingerprint,
    )


def test_the_wrapper_set_is_the_one_under_test() -> None:
    assert set(NON_CANONICAL) == set(CANONICAL) == set(TYPED_SCALAR_WRAPPER_TYPES)


@pytest.mark.parametrize("value_type", sorted(CANONICAL))
def test_a_canonical_typed_target_is_accepted(value_type: str) -> None:
    """The control: each wrapper's canonical form still derives."""

    bundle = derive_differences(
        _request({"value_type": value_type, "value": CANONICAL[value_type]})
    )
    assert bundle["satisfied_target_predicates"] == [PREDICATE_ID]


@pytest.mark.parametrize("value_type", sorted(NON_CANONICAL))
def test_a_noncanonical_typed_target_fails_closed(value_type: str) -> None:
    with pytest.raises(DifferenceError, match=f"declared {value_type}|canonical {value_type}"):
        derive_differences(
            _request({"value_type": value_type, "value": NON_CANONICAL[value_type]})
        )


def test_the_satisfied_route_is_where_it_escaped() -> None:
    """The premise: this operator emits no record for the output schema to reject."""

    bundle = derive_differences(_request({"value_type": "TIMESTAMP", "value": CANONICAL["TIMESTAMP"]}))
    assert bundle["satisfied_target_predicates"] == [PREDICATE_ID]
    assert bundle.get("differences", []) == []
    assert bundle.get("policies", []) == []


def test_the_same_instant_no_longer_reads_as_a_mismatch() -> None:
    """A non-UTC Target naming the observed instant is rejected, not silently unequal."""

    fingerprint = state_fingerprint()
    scope = observation_scope()
    fact = raw_fact(value="2026-08-30T08:00:00Z")
    fact["value_type"] = "TIMESTAMP"
    request = derivation_request(
        objective_revision(
            [
                target_predicate(
                    operator="equals",
                    expected_value={
                        "value_type": "TIMESTAMP", "value": "2026-08-30T09:00:00+01:00"
                    },
                )
            ]
        ),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": observed_bundle(scope, [fact], fingerprint),
            }
        ],
        fingerprint,
    )
    with pytest.raises(DifferenceError, match="canonical TIMESTAMP form"):
        derive_differences(request)


# --------------------------------------------------------------------------- #
# One canonical-value authority, and the Target is never rewritten by it
# --------------------------------------------------------------------------- #


def test_the_rule_reads_the_observation_elements_authority() -> None:
    """The Observation element defines a canonical value; this phase states no second one."""

    assert canonical_value("2026-08-30T09:00:00+01:00", "TIMESTAMP") == "2026-08-30T08:00:00Z"
    for value_type, value in CANONICAL.items():
        assert canonical_value(value, value_type) == value


def test_a_canonical_target_is_left_exactly_as_declared() -> None:
    """The rule compares; it does not substitute.

    Canonicalising the Target would silently change what the Human Objective says, and it
    is an identity input: every Difference identity derived from it would move.
    """

    for value_type, value in CANONICAL.items():
        reject_noncanonical_typed_value(value, value_type)
    bundle = derive_differences(
        _request({"value_type": "DECIMAL", "value": CANONICAL["DECIMAL"]}, operator="equals")
    )
    difference = bundle["differences"][0]
    assert difference["normalized_target_state"]["expected_value"] == CANONICAL["DECIMAL"]
    assert difference["normalized_target_state"]["expected_value_type"] == "DECIMAL"


def test_an_untyped_value_is_untouched() -> None:
    """Only a declared wrapper type is subject to this rule."""

    for value in ("2026-08-30T09:00:00+01:00", "not-a-number", 7, None, {"a": 1}):
        reject_noncanonical_typed_value(value, "STRING" if isinstance(value, str) else "STRUCTURED")
