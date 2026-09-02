"""The four findings, each as the case that produced it.

The generated inventory in ``tests/contract/difference/test_request_grammar_inventory.py``
proves the *class* is closed. These four prove the *instances* are, in the exact shape they
were reported, so a regression names the finding rather than a parametrised id -- and so the
two kinds of coverage stay independent. ADR-0022 §4 records why both are needed: the
enumeration only asks whether the producer raises, and the focused tests are what caught the
regression the enumeration could not see.

Three were reported against `5d9f407`. The fourth was found by the inventory itself, at a
location no fixture instantiated -- which is the whole argument for building the inventory
before writing any of these.
"""

from __future__ import annotations

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

from manosube_agent_civilization.difference import derive_differences
from manosube_agent_civilization.difference.errors import DifferenceError
from manosube_agent_civilization.difference.projection import normalize_objective_value


def _request(*, expected_value: Any = "READY") -> dict[str, Any]:
    fingerprint = state_fingerprint()
    scope = observation_scope()
    return derivation_request(
        objective_revision([target_predicate(expected_value=expected_value)]),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": observed_bundle(
                    scope,
                    [raw_fact(value="NOT-READY")],
                    fingerprint,
                    negative_claims=[negative_claim("NO_RESULT")],
                ),
            }
        ],
        fingerprint,
    )


# --------------------------------------------------------------------------- #
# Finding 1 -- a declared Closure Policy collection reached `sorted`
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("field", ["allowed_terminal_states", "required_invariants",
                                   "reopen_conditions", "required_claims"])
@pytest.mark.parametrize("supplied", [None, 7, "seven", {}, {"a": 1}])
def test_a_policy_set_supplied_as_a_non_collection_is_rejected(
    field: str, supplied: Any
) -> None:
    """It reached ``identity.policy_semantic_projection`` and raised out of ``sorted``.

    The requirements fragment is optional and the committed fixture supplies exactly one of
    its keys, so no mutation over that fixture could construct this case at all.
    """

    request = _request()
    request["bindings"][0]["closure_policy_requirements"] = {field: supplied}
    with pytest.raises(DifferenceError, match=f"Closure Policy {field}"):
        derive_differences(request)


@pytest.mark.parametrize("field", ["required_invariants", "reopen_conditions"])
@pytest.mark.parametrize("member", [None, 7, "seven", [], {}])
def test_a_policy_set_member_the_projection_cannot_read_is_rejected(
    field: str, member: Any
) -> None:
    """A guarded container and unguarded members is half a rule, which is D5's shape."""

    request = _request()
    request["bindings"][0]["closure_policy_requirements"] = {field: [member]}
    with pytest.raises(DifferenceError, match="Closure Policy"):
        derive_differences(request)


# --------------------------------------------------------------------------- #
# Finding 2 -- a domain-shaped `expected_value` reached a wrapper-tag membership test
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("tag", [[], {}, {"a": 1}, 7, None, True])
def test_a_typed_wrapper_whose_tag_is_not_a_tag_is_not_a_declared_wrapper(tag: Any) -> None:
    """``value["value_type"] in TYPED_SCALAR_WRAPPER_TYPES`` hashed whatever arrived.

    The contract's answer is not a rejection: any object that is not a *declared* wrapper is
    an ordinary structured value, compared whole. A tag that cannot be hashed names no
    declared wrapper, so it takes that branch -- and the derivation then answers on the
    merits rather than raising ``unhashable type`` out of the comparison.
    """

    request = _request(expected_value={"value_type": tag, "value": "READY"})
    try:
        derive_differences(request)
    except DifferenceError:
        return
    # Deriving is the correct outcome for a structured Target the Observation does not
    # match; what must never happen is a raw exception, which is what this asserts.


def test_a_declared_wrapper_is_still_unwrapped() -> None:
    """The guard narrows nothing: a real wrapper keeps its meaning, an imitation does not."""

    assert normalize_objective_value({"value_type": "DECIMAL", "value": "1.5"}) == ("1.5", "DECIMAL")
    # An object that merely resembles a wrapper is an ordinary structured value, compared
    # whole -- the rule the `STRUCTURED` category error broke, and the reason the guard is a
    # predicate rather than a rejection.
    imitation = {"value_type": [], "value": "READY"}
    assert normalize_objective_value(imitation) == (imitation, "STRUCTURED")


# --------------------------------------------------------------------------- #
# Finding 3 -- an optional `risk_class` reached a frozenset membership test
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("supplied", [[], {}, {"a": 1}, ["LOW"], 7, None, True])
def test_a_request_risk_class_that_cannot_be_a_tag_is_rejected(supplied: Any) -> None:
    """Absent from every committed fixture, so the sweep had no case for it to mutate."""

    request = _request()
    request["risk_class"] = supplied
    with pytest.raises(DifferenceError, match="requested risk class is not a canonical tag"):
        derive_differences(request)


@pytest.mark.parametrize("supplied", [[], {}, {"a": 1}, 7, None, True])
def test_a_binding_risk_class_that_cannot_be_a_tag_is_rejected(supplied: Any) -> None:
    """The per-binding override is a second route to the same membership test."""

    request = _request()
    request["bindings"][0]["risk_class"] = supplied
    with pytest.raises(DifferenceError, match="binding risk class is not a canonical tag"):
        derive_differences(request)


def test_a_readable_but_unknown_risk_class_keeps_its_own_diagnosis() -> None:
    """ADR-0013: admissibility and correctness are distinct obligations, and stay so."""

    request = _request()
    request["risk_class"] = "SEVEN"
    with pytest.raises(DifferenceError, match="unknown risk class: 'SEVEN'"):
        derive_differences(request)


# --------------------------------------------------------------------------- #
# Finding 4 -- found by the inventory, not by review
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("kind", [[], {}, {"a": 1}, 7, True])
def test_a_collection_wrapper_whose_kind_cannot_be_a_tag_is_rejected(kind: Any) -> None:
    """``canonical.reject_bare_arrays`` hashed ``collection_kind`` before checking it.

    This one was never reported. It is the same defect at a fifth location, and the
    generated inventory produced it on its first run -- which is the evidence that building
    the inventory before writing the fixes was the load-bearing step.
    """

    request = _request(expected_value={"collection_kind": kind, "items": []})
    with pytest.raises(DifferenceError, match="unknown collection_kind"):
        derive_differences(request)
