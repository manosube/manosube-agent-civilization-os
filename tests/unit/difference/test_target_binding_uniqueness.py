"""A Target Predicate is satisfied or it is open, and it is bound once.

Two individually valid bindings naming one `target_predicate_id` were evaluated
independently. One bundle satisfied the predicate and returned before emitting anything;
the other derived a Difference. The returned bundle then listed that Target in
`satisfied_target_predicates` *and* carried an open Difference for it — a bundle asserting
both answers to the same question, which the independent validator did not catch either.

Two rules, at two levels, because either alone leaves the other open. The binding rule
removes the cause; the envelope rule makes the contradiction unemittable by any route,
including one that does not exist yet.
"""

from __future__ import annotations

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

from manosube_agent_civilization.difference import DifferenceError, derive_differences
from manosube_agent_civilization.difference.graph import relational_errors

SECOND_PREDICATE = "TP-0002"


def _binding(scope_id: str, value: str, predicate_id: str = PREDICATE_ID) -> dict[str, Any]:
    fingerprint = state_fingerprint()
    scope = observation_scope(scope_id=scope_id, target_identity=predicate_id)
    return {
        "target_predicate_id": predicate_id,
        "observation_scope": scope,
        "observation_bundle": observed_bundle(scope, [raw_fact(value=value)], fingerprint),
    }


def test_one_binding_per_target_still_derives() -> None:
    """The control: the rule rejects a duplicate, not an ordinary derivation."""

    fingerprint = state_fingerprint()
    bundle = derive_differences(
        derivation_request(
            objective_revision(),
            [_binding("OBS-SCOPE-0001", "NOT-READY")],
            fingerprint,
        )
    )
    assert len(bundle["differences"]) == 1
    assert validate_bundle(bundle) == []


def test_two_bindings_for_one_target_fail_closed() -> None:
    """The reported case: one satisfies, one mismatches, both are evaluated."""

    fingerprint = state_fingerprint()
    request = derivation_request(
        objective_revision(),
        [
            _binding("OBS-SCOPE-0001", "READY"),
            _binding("OBS-SCOPE-0002", "NOT-READY"),
        ],
        fingerprint,
    )
    with pytest.raises(DifferenceError, match="binds one Target Predicate twice: TP-0001"):
        derive_differences(request)


def test_two_bindings_agreeing_also_fail_closed() -> None:
    """The rule is about the binding, not about whether the two happen to agree."""

    fingerprint = state_fingerprint()
    request = derivation_request(
        objective_revision(),
        [
            _binding("OBS-SCOPE-0001", "NOT-READY"),
            _binding("OBS-SCOPE-0002", "NOT-READY"),
        ],
        fingerprint,
    )
    with pytest.raises(DifferenceError, match="binds one Target Predicate twice"):
        derive_differences(request)


def test_distinct_targets_are_unaffected() -> None:
    """Two bindings for two Targets is the ordinary multi-predicate derivation."""

    fingerprint = state_fingerprint()
    objective = objective_revision(
        [
            target_predicate(),
            target_predicate(predicate_id=SECOND_PREDICATE, expected_value="ALSO-READY"),
        ]
    )
    request = derivation_request(
        objective,
        [
            _binding("OBS-SCOPE-0001", "NOT-READY"),
            _binding("OBS-SCOPE-0002", "STILL-NOT-READY", predicate_id=SECOND_PREDICATE),
        ],
        fingerprint,
    )
    bundle = derive_differences(request)
    assert {
        record["target_predicate_ref"]["id"] for record in bundle["differences"]
    } == {PREDICATE_ID, SECOND_PREDICATE}


# --------------------------------------------------------------------------- #
# The envelope rule: unemittable by any route, not only by the one corrected
# --------------------------------------------------------------------------- #


def test_a_target_may_not_be_satisfied_and_open_at_once() -> None:
    errors = relational_errors(
        {
            "satisfied_target_predicates": [PREDICATE_ID],
            "differences": [
                {
                    "difference_id": "D-X",
                    "target_predicate_ref": {"kind": "target_predicate", "id": PREDICATE_ID},
                }
            ],
        }
    )
    assert errors == [
        f"Target Predicate is reported satisfied and open at once: {PREDICATE_ID}"
    ]


def test_the_envelope_rule_is_silent_on_a_consistent_bundle() -> None:
    """Satisfied and open sets that do not intersect are the ordinary case."""

    assert relational_errors(
        {
            "satisfied_target_predicates": [SECOND_PREDICATE],
            "differences": [
                {
                    "difference_id": "D-X",
                    "target_predicate_ref": {"kind": "target_predicate", "id": PREDICATE_ID},
                }
            ],
        }
    ) == []


@pytest.mark.parametrize("satisfied", [None, {}, "TP-0001", 7])
def test_the_envelope_rule_is_total_over_a_malformed_envelope(satisfied: Any) -> None:
    """It reads an untrusted bundle, so a non-list envelope is passed over, not raised on."""

    assert relational_errors(
        {
            "satisfied_target_predicates": satisfied,
            "differences": [
                {
                    "difference_id": "D-X",
                    "target_predicate_ref": {"kind": "target_predicate", "id": PREDICATE_ID},
                }
            ],
        }
    ) == []
