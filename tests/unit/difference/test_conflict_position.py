"""A status that asserts no conflict may not name one.

``NORMALIZED_FACT.md`` makes the latest contiguous evaluation the record of the current
support and conflict position, and ``NEGATIVE_OBSERVATION.md`` requires the two sides to
reference the same conflict pair. Both were enforced; the converse was not. An evaluation
appended to move a Fact *off* ``CONFLICTED`` could keep the conflict references of the
revision it replaced — schema conformance passed, because the canonical schema constrains
only the ``CONFLICTED`` direction; identity recomputed, because it is derived from subject
and revision alone; and the symmetry rule had nothing to compare against.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import pytest
from scripts.difference_contract_validator import validate_bundle
from tests.difference_helpers import (
    PREDICATE_ID,
    derivation_request,
    negative_claim,
    objective_revision,
    observation_scope,
    observed_bundle,
    raw_fact,
    state_fingerprint,
)

from manosube_agent_civilization.difference import DifferenceError, derive_differences
from manosube_agent_civilization.observation.identity import fact_evaluation_identity
from manosube_agent_civilization.observation.verification import (
    CONFLICT_REFERENCE_FIELDS,
    CONFLICT_STATUS,
    conflict_position_errors,
    observation_record_errors,
)

ROOT = Path(__file__).resolve().parents[3]
FACT_EVALUATION_SCHEMA = json.loads(
    (ROOT / "01_SCHEMA" / "observation" / "fact_evaluation.schema.json").read_text(
        encoding="utf-8"
    )
)
FACT_STATUSES = sorted(FACT_EVALUATION_SCHEMA["properties"]["evaluation_status"]["enum"])
NON_CONFLICTED = [status for status in FACT_STATUSES if status != CONFLICT_STATUS]


def _bundle(mutate: Any = None) -> dict[str, Any]:
    fingerprint = state_fingerprint()
    scope = observation_scope()
    bundle = observed_bundle(scope, [raw_fact(value="NOT-READY")], fingerprint)
    if mutate is not None:
        mutate(bundle)
    return bundle


def _request(bundle: dict[str, Any]) -> dict[str, Any]:
    fingerprint = state_fingerprint()
    return derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": observation_scope(),
                "observation_bundle": bundle,
            }
        ],
        fingerprint,
    )


def test_the_status_list_comes_from_the_schema() -> None:
    assert CONFLICT_STATUS in FACT_STATUSES
    assert NON_CONFLICTED and len(NON_CONFLICTED) == len(FACT_STATUSES) - 1
    assert set(CONFLICT_REFERENCE_FIELDS) == {"fact_evaluations", "negative_evaluations"}


def test_the_authority_is_shared_and_reached_through_the_record_verifier() -> None:
    """No second status table: every consumer reaches it through one verifier."""

    from manosube_agent_civilization.observation import verification

    source = Path(verification.__file__).read_text(encoding="utf-8")
    cross = source.split("def _cross_record_errors(")[1].split("\ndef ")[0]
    assert "conflict_position_errors(schema_valid)" in cross
    assert source.count("def conflict_position_errors(") == 1


@pytest.mark.parametrize("status", NON_CONFLICTED)
@pytest.mark.parametrize(
    "field", ["conflict_fact_refs", "conflict_negative_observation_refs"]
)
def test_a_non_conflicted_status_may_not_retain_conflict_references(
    status: str, field: str
) -> None:
    """The reviewed defect, across every non-conflicted status and both reference lists."""

    def mutate(bundle: dict[str, Any]) -> None:
        evaluation = bundle["fact_evaluations"][0]
        evaluation["evaluation_status"] = status
        kind = (
            "normalized_fact" if field == "conflict_fact_refs" else "negative_observation"
        )
        evaluation[field] = [{"kind": kind, "id": "NEG-STALE-0001"}]
        # The identity is recomputed, so no identity rule can be what rejects this.
        evaluation["evaluation_id"] = fact_evaluation_identity(evaluation)

    bundle = _bundle(mutate)
    assert any(
        "retains conflict references" in error
        for error in observation_record_errors(deepcopy(bundle))
    )
    with pytest.raises(DifferenceError, match="retains conflict references"):
        derive_differences(_request(bundle))


@pytest.mark.parametrize("status", NON_CONFLICTED)
def test_a_non_conflicted_status_with_empty_conflict_lists_is_accepted(status: str) -> None:
    """The rule rejects the contradiction, not the status."""

    def mutate(bundle: dict[str, Any]) -> None:
        evaluation = bundle["fact_evaluations"][0]
        evaluation["evaluation_status"] = status
        evaluation["evaluation_id"] = fact_evaluation_identity(evaluation)

    assert conflict_position_errors(_bundle(mutate)) == []


def test_conflicted_with_no_conflict_reference_fails_closed() -> None:
    """The other half of the rule, stated symmetrically."""

    errors = conflict_position_errors(
        {
            "fact_evaluations": [
                {
                    "evaluation_id": "FACT-EVAL-1",
                    "evaluation_status": CONFLICT_STATUS,
                    "conflict_fact_refs": [],
                    "conflict_negative_observation_refs": [],
                }
            ],
            "negative_evaluations": [],
        }
    )
    assert any("names no conflict" in error for error in errors), errors


def test_a_negative_evaluation_is_held_to_the_same_rule() -> None:
    errors = conflict_position_errors(
        {
            "fact_evaluations": [],
            "negative_evaluations": [
                {
                    "evaluation_id": "NEG-EVAL-1",
                    "evaluation_status": "ABSENT",
                    "conflict_fact_refs": [{"kind": "normalized_fact", "id": "FACT-1"}],
                }
            ],
        }
    )
    assert any("retains conflict references" in error for error in errors), errors


def test_a_genuine_conflict_lineage_is_unaffected() -> None:
    """The real CONFLICTED route the Observation Engine produces still passes."""

    fingerprint = state_fingerprint()
    scope = observation_scope()
    first = observed_bundle(
        scope, [], fingerprint, negative_claims=[negative_claim("ABSENT")]
    )
    later = observed_bundle(
        scope,
        [raw_fact(value="NOT-READY")],
        state_fingerprint("KNOWN"),
        state_revision=7,
        negative_claims=[negative_claim("ABSENT")],
        prior_bundle=first,
    )
    assert observation_record_errors(deepcopy(later)) == []
    statuses = {item["evaluation_status"] for item in later["negative_evaluations"]}
    assert CONFLICT_STATUS in statuses, statuses
    conflicted = [
        item for item in later["negative_evaluations"]
        if item["evaluation_status"] == CONFLICT_STATUS
    ]
    assert all(item["conflict_fact_refs"] for item in conflicted)


def test_the_control_route_stays_cross_record_valid() -> None:
    bundle = derive_differences(_request(_bundle()))
    assert validate_bundle(bundle) == []


@pytest.mark.parametrize(
    "payload",
    [
        {"fact_evaluations": [{}], "negative_evaluations": []},
        {"fact_evaluations": [None], "negative_evaluations": None},
        {},
        {"fact_evaluations": [{"evaluation_id": "E", "evaluation_status": "SUPPORTED"}],
         "negative_evaluations": []},
    ],
    ids=["bare", "hostile", "empty", "missing-lists"],
)
def test_the_rule_is_total_over_untrusted_input(payload: dict[str, Any]) -> None:
    assert isinstance(conflict_position_errors(payload), list)
