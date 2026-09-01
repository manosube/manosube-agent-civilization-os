"""A projection is canonical before it is read, not only before it is emitted.

Two rules decide whether a normalized projection is canonical: no bare array, and no
duplicate member in an `UNORDERED_SET`. Both were enforced, at different moments. Bare
arrays were rejected where each projection is produced; duplicates were rejected only while
*building an unsatisfied Difference*. A satisfied comparison returns before that, so the
same Target that the unsatisfied route refused was reported satisfied — and satisfaction is
the one outcome that emits no record for a later gate to catch.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from tests.difference_helpers import (
    PREDICATE_ID,
    derivation_request,
    negative_claim,
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


#: Every operator the canonical Target Predicate schema declares. Read from the schema
#: rather than listed, so an operator added later is covered without being remembered.
OPERATORS: list[str] = json.loads(
    (Path("01_SCHEMA/objective/target_predicate.schema.json")).read_text(encoding="utf-8")
)["properties"]["operator"]["enum"]


def test_the_operator_matrix_is_the_whole_declared_enum() -> None:
    assert set(OPERATORS) == {"equals", "not_equals", "contains", "exists", "all", "none"}


@pytest.mark.parametrize("operator", OPERATORS)
def test_no_operator_admits_a_duplicate_set_member(operator: str) -> None:
    """Satisfaction is decided per operator; canonicality is not decided by satisfaction.

    Including the operators that never consult ``expected_value`` at all, which is where a
    non-canonical identity input used to travel furthest.
    """

    with pytest.raises(DifferenceError, match="carries a duplicate unordered-set member"):
        derive_differences(
            _request(target_predicate(operator=operator, expected_value=DUPLICATE_SET), "READY")
        )


NESTED_DUPLICATE = {
    "collection_kind": "ORDERED_LIST",
    "members": [
        {
            "outer": {
                "collection_kind": "UNORDERED_SET",
                "members": [{"a": 1}, {"a": 1}],
            }
        }
    ],
}


@pytest.mark.parametrize("operator", OPERATORS)
def test_a_duplicate_nested_below_wrappers_is_found(operator: str) -> None:
    """The rule is recursive: a duplicate two wrappers deep is still a duplicate."""

    with pytest.raises(DifferenceError, match="carries a duplicate unordered-set member"):
        derive_differences(
            _request(
                target_predicate(operator=operator, expected_value=NESTED_DUPLICATE), "READY"
            )
        )


# --------------------------------------------------------------------------- #
# Ordering: a set is decided by member bytes, not by the order they arrive in
# --------------------------------------------------------------------------- #


def test_distinct_members_are_accepted_in_any_order() -> None:
    """Deterministic: two orderings of one set produce the same Difference identity."""

    forward = {"collection_kind": "UNORDERED_SET", "members": ["A", "B"]}
    reverse = {"collection_kind": "UNORDERED_SET", "members": ["B", "A"]}
    first = derive_differences(
        _request(target_predicate(expected_value=forward), "NOT-READY")
    )
    second = derive_differences(
        _request(target_predicate(expected_value=reverse), "NOT-READY")
    )
    assert [record["difference_id"] for record in first["differences"]] == [
        record["difference_id"] for record in second["differences"]
    ]
    assert (
        first["differences"][0]["normalized_target_state"]
        == second["differences"][0]["normalized_target_state"]
    )


# --------------------------------------------------------------------------- #
# The early-return matrix: no classification precedes rejection
# --------------------------------------------------------------------------- #


#: One observation shape per terminal outcome the derivation can reach for a binding. The
#: control test proves each is really reachable with a canonical Target; the matrix then
#: swaps in the non-canonical Target and requires rejection instead of that outcome.
ROUTES: dict[str, dict[str, Any]] = {
    "SATISFIED": {"facts": [raw_fact(value="READY")], "negatives": None},
    "DIFFERENCE": {"facts": [raw_fact(value="NOT-READY")], "negatives": None},
    "UNKNOWN": {"facts": [], "negatives": [negative_claim("NO_RESULT")]},
    "PROVEN_ABSENCE": {"facts": [], "negatives": [negative_claim("ABSENT")]},
    "EMPTY": {"facts": [], "negatives": [negative_claim("EMPTY")]},
}


def _route_request(route: dict[str, Any], predicate: dict[str, Any]) -> dict[str, Any]:
    fingerprint = state_fingerprint()
    scope = observation_scope()
    return derivation_request(
        objective_revision([predicate]),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": observed_bundle(
                    scope, route["facts"], fingerprint, negative_claims=route["negatives"]
                ),
            }
        ],
        fingerprint,
    )



@pytest.mark.parametrize("name", sorted(ROUTES))
def test_the_control_route_reaches_its_outcome(name: str) -> None:
    """The matrix is not vacuous: each route really is reachable with a canonical Target."""

    operator = "none" if name in {"PROVEN_ABSENCE", "EMPTY"} else "equals"
    predicate = target_predicate(operator=operator)
    bundle = derive_differences(_route_request(ROUTES[name], predicate))
    reached = bool(bundle["satisfied_target_predicates"]) or bool(bundle["differences"])
    assert reached, name


@pytest.mark.parametrize("name", sorted(ROUTES))
def test_no_route_classifies_a_non_canonical_target(name: str) -> None:
    """Satisfied, unknown, empty, proven-absence: none may precede the rejection."""

    operator = "none" if name in {"PROVEN_ABSENCE", "EMPTY"} else "equals"
    predicate = target_predicate(operator=operator, expected_value=DUPLICATE_SET)
    with pytest.raises(DifferenceError, match="carries a duplicate unordered-set member"):
        derive_differences(_route_request(ROUTES[name], predicate))


def test_the_target_is_validated_before_any_observation_is_read() -> None:
    """Ordering, read from the derivation itself, not inferred from the outcomes above."""

    source = Path(
        "src/manosube_agent_civilization/difference/engine.py"
    ).read_text(encoding="utf-8")
    body = source.split("def derive_differences(")[1]
    check = body.index('_reject_noncanonical(target, "normalized_target_state")')
    for later in ("_select_observation(", "_observed_projection(", "effective_boundary("):
        assert check < body.index(later), later


def test_a_bare_array_in_a_satisfied_target_still_fails_closed() -> None:
    """The rule that already ran here keeps running, through the same call."""

    with pytest.raises(DifferenceError, match="normalized_target_state"):
        derive_differences(
            _request(target_predicate(operator="exists", expected_value=["A", "B"]), "READY")
        )


def test_both_rules_are_stated_once_and_read_by_every_projection() -> None:
    """One helper, called at every projection site — not two rules in two places."""

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
