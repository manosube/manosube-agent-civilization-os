"""A projection is canonical before it is read, not only before it is emitted.

Two rules decide whether a normalized projection is canonical: no bare array, and no
duplicate member in an `UNORDERED_SET`. Both were enforced, at different moments. Bare
arrays were rejected where each projection is produced; duplicates were rejected only while
*building an unsatisfied Difference*. A satisfied comparison returns before that, so the
same Target that the unsatisfied route refused was reported satisfied — and satisfaction is
the one outcome that emits no record for a later gate to catch.
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

DUPLICATE_SET = {"collection_kind": "UNORDERED_SET", "members": ["A", "A"]}
DISTINCT_SET = {"collection_kind": "UNORDERED_SET", "members": ["A", "B"]}


def _request(predicate: dict[str, Any], observed: Any) -> dict[str, Any]:
    fingerprint = state_fingerprint()
    scope = observation_scope()
    return derivation_request(
        objective_revision([predicate]),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": observed_bundle(
                    scope, [raw_fact(value=observed)], fingerprint
                ),
            }
        ],
        fingerprint,
    )


def test_the_satisfied_route_is_the_route_under_test() -> None:
    """A canonical `exists` Target over the same shape really is satisfied."""

    bundle = derive_differences(
        _request(target_predicate(operator="exists", expected_value=DISTINCT_SET), "READY")
    )
    assert bundle["satisfied_target_predicates"] == [PREDICATE_ID]
    assert bundle.get("differences", []) == []


def test_a_duplicate_set_member_in_a_satisfied_target_fails_closed() -> None:
    with pytest.raises(
        DifferenceError, match="normalized_target_state carries a duplicate unordered-set member"
    ):
        derive_differences(
            _request(target_predicate(operator="exists", expected_value=DUPLICATE_SET), "READY")
        )


def test_the_unsatisfied_route_rejects_the_same_target() -> None:
    """The asymmetry this closes: one Target, two answers, decided by satisfaction."""

    with pytest.raises(
        DifferenceError, match="normalized_target_state carries a duplicate unordered-set member"
    ):
        derive_differences(
            _request(
                target_predicate(operator="equals", expected_value=DUPLICATE_SET), "NOT-READY"
            )
        )


@pytest.mark.parametrize("operator", ["exists", "equals", "contains", "not_equals"])
def test_no_operator_admits_a_duplicate_set_member(operator: str) -> None:
    """Satisfaction is decided per operator; canonicality is not decided by satisfaction."""

    with pytest.raises(DifferenceError, match="carries a duplicate unordered-set member"):
        derive_differences(
            _request(target_predicate(operator=operator, expected_value=DUPLICATE_SET), "READY")
        )


def test_a_bare_array_in_a_satisfied_target_still_fails_closed() -> None:
    """The rule that already ran here keeps running, through the same call."""

    with pytest.raises(DifferenceError, match="normalized_target_state"):
        derive_differences(
            _request(target_predicate(operator="exists", expected_value=["A", "B"]), "READY")
        )


def test_both_rules_are_stated_once_and_read_by_every_projection() -> None:
    """One helper, called at every projection site — not two rules in two places."""

    from pathlib import Path

    source = Path(
        "src/manosube_agent_civilization/difference/engine.py"
    ).read_text(encoding="utf-8")
    body = source.split("def derive_differences(")[1]
    assert body.count("_reject_noncanonical(") >= 3
    # And no projection is checked by a bare call to either underlying rule.
    assert "reject_bare_arrays(target," not in body
    assert "reject_bare_arrays(observed," not in body
    assert "reject_bare_arrays(structural," not in body
    assert "has_recursive_set_duplicate(difference[" not in body
