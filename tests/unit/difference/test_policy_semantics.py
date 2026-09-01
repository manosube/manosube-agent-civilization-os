"""A Closure Policy must recompute from its own content, and resolve against the Objective.

Two independent forgeries reached the returned bundle at `da3b0b1`:

* `_policy_identity` derived the Closure Policy ID from `policy_semantic_fingerprint` **as
  stored**, so a carried Policy whose required Claim was rewritten kept its identity and
  recomputed. Only the whole-bundle relational pass recomputed a Policy's semantics, and
  only for a Policy some lifecycle Evaluation cites -- a carried Policy nothing cites was
  never recomputed at all. The independent validator did object, which made the
  required-Claim rule an auditor-only rule.
* A reopen condition resolved its Objective revision and stopped there. `CLOSURE_POLICY.md`
  requires the condition's ID, revision **and** fingerprint to resolve exactly, so a
  predicate that did not exist in that revision, under any fingerprint, was accepted.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
from typing import Any

import pytest
import scripts.difference_contract_validator as validator_module
from scripts.difference_contract_validator import validate_bundle
from tests.difference_helpers import (
    PREDICATE_ID,
    derivation_request,
    negative_claim,
    objective_revision,
    observation_scope,
    observed_bundle,
    raw_fact,
    retained_status_predecessor,
    state_fingerprint,
    target_predicate,
)

from manosube_agent_civilization.difference import DifferenceError, derive_differences
from manosube_agent_civilization.difference.errors import SecurityRejectionError
from manosube_agent_civilization.difference.identity import (
    TARGET_PREDICATE_PROFILE,
    closure_policy_id,
    completion_claim_fingerprint,
    completion_claim_id,
    policy_semantic_fingerprint,
    target_predicate_fingerprint,
)
from manosube_agent_civilization.difference.policy import (
    closure_policy_semantic_errors,
    reopen_condition_provenance_errors,
)

CONTRACT = Path(__file__).resolve().parents[3] / "00_KERNEL/04_DIFFERENCE/CLOSURE_POLICY.md"


# --------------------------------------------------------------------------- #
# A carried Closure Policy that no lifecycle Evaluation cites
# --------------------------------------------------------------------------- #


def _descriptor() -> dict[str, Any]:
    return {
        "subject_type": "OBJECTIVE_REVISION",
        "subject_ref": {"kind": "objective_revision", "id": "OBJ-REV-0001"},
        "claim": {"predicate_satisfied": True},
        "target_state_ref": None,
    }


def _claim() -> dict[str, Any]:
    descriptor = _descriptor()
    return {
        "kind": "completion_claim",
        "id": completion_claim_id(descriptor),
        **descriptor,
        "claim_semantic_fingerprint": completion_claim_fingerprint(descriptor),
    }


def _seal(policy: dict[str, Any]) -> dict[str, Any]:
    """Recompute the Policy's stored digest and identity, as an honest producer would."""

    policy["policy_semantic_fingerprint"] = policy_semantic_fingerprint(policy)
    policy["closure_policy_id"] = closure_policy_id(
        policy["policy_semantic_fingerprint"], policy["subject_difference_ref"]["id"]
    )
    return policy


def _carried(mutate: Any = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a request carrying an extra Policy, and that Policy, after *mutate*."""

    _, request = retained_status_predecessor(
        "BLOCKED",
        "BLOCKER_REOBSERVATION",
        negative_claims=[negative_claim("NO_RESULT")],
        facts=[],
    )
    context = request["bindings"][0]["predecessor"]["context"]
    extra = _seal({**deepcopy(context["policies"][0]), "required_claims": [_claim()]})
    if mutate is not None:
        mutate(extra)
    context["policies"].append(extra)
    return request, extra


def test_the_extra_policy_is_cited_by_nothing() -> None:
    """The route under test is real: no Evaluation names this Policy.

    That is what made the relational pass -- which recomputes a Policy's semantics only
    where an Evaluation cites it -- unable to see the forgery.
    """

    request, extra = _carried()
    bundle = derive_differences(request)
    identity = extra["closure_policy_id"]
    assert identity in {policy["closure_policy_id"] for policy in bundle["policies"]}
    assert identity not in {
        evaluation["policy_ref"]["id"] for evaluation in bundle.get("evaluations", []) or []
    }
    assert identity not in {
        difference["closure_policy"]["id"] for difference in bundle["differences"]
    }


def test_the_honest_extra_policy_is_accepted() -> None:
    request, extra = _carried()
    bundle = derive_differences(request)
    assert extra["closure_policy_id"] in {
        policy["closure_policy_id"] for policy in bundle["policies"]
    }
    assert validate_bundle(bundle) == []


def _forge_claim_id(policy: dict[str, Any]) -> None:
    policy["required_claims"][0]["id"] = "CLAIM-" + "0" * 64


def test_a_rewritten_claim_under_a_retained_digest_fails_closed() -> None:
    """The reported forgery: keep the stored digest and the ID, rewrite the Claim."""

    request, _ = _carried(_forge_claim_id)
    with pytest.raises(DifferenceError, match="Closure Policy fingerprint does not recompute"):
        derive_differences(request)


def test_a_rewritten_claim_under_a_recomputed_digest_fails_closed() -> None:
    """And the harder forgery: recompute the digest and the ID around the rewritten Claim.

    Recomputing the Policy digest alone would accept this, because the Policy really is
    self-consistent. What it is not is consistent with the Claim's own semantics.
    """

    def mutate(policy: dict[str, Any]) -> None:
        _forge_claim_id(policy)
        _seal(policy)

    request, _ = _carried(mutate)
    with pytest.raises(DifferenceError, match="required Claim identity does not recompute"):
        derive_differences(request)


def test_a_rewritten_claim_fingerprint_fails_closed() -> None:
    def mutate(policy: dict[str, Any]) -> None:
        policy["required_claims"][0]["claim_semantic_fingerprint"] = "sha256:" + "0" * 64
        _seal(policy)

    request, _ = _carried(mutate)
    with pytest.raises(DifferenceError, match="required Claim fingerprint does not recompute"):
        derive_differences(request)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("minimum_evidence_level", "E3"),
        ("allowed_terminal_states", ["CLOSED"]),
        ("maximum_evidence_age", 604800),
    ],
)
def test_a_retained_digest_over_altered_requirements_fails_closed(field: str, value: Any) -> None:
    """Any semantic field, not only the Claims: the stored digest must recompute."""

    def mutate(policy: dict[str, Any]) -> None:
        policy[field] = value

    request, _ = _carried(mutate)
    with pytest.raises(DifferenceError, match="Closure Policy fingerprint does not recompute"):
        derive_differences(request)


def test_two_payloads_under_one_claim_identity_fail_closed() -> None:
    def mutate(policy: dict[str, Any]) -> None:
        second = deepcopy(policy["required_claims"][0])
        second["claim"] = {"predicate_satisfied": False}
        policy["required_claims"].append(second)
        _seal(policy)

    request, _ = _carried(mutate)
    with pytest.raises(DifferenceError, match="required Claim"):
        derive_differences(request)


# --------------------------------------------------------------------------- #
# Reopen-condition provenance
# --------------------------------------------------------------------------- #


def _reopen_request(condition: dict[str, Any]) -> dict[str, Any]:
    fingerprint = state_fingerprint()
    scope = observation_scope()
    request = derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": observed_bundle(
                    scope, [raw_fact(value="NOT-READY")], fingerprint
                ),
            }
        ],
        fingerprint,
    )
    request["closure_policy_requirements"] = {
        "minimum_evidence_level": "E1",
        "reopen_conditions": [condition],
    }
    return request


def _condition(identity: str, fingerprint: str) -> dict[str, Any]:
    return {
        "kind": "target_predicate",
        "id": identity,
        "predicate_semantic_fingerprint": fingerprint,
        "objective_revision_ref": {"kind": "objective_revision", "id": "OBJ-REV-0001"},
    }


def test_a_reopen_predicate_absent_from_the_objective_fails_closed() -> None:
    request = _reopen_request(_condition("TP-ABSENT-0001", "sha256:" + "b" * 64))
    with pytest.raises(
        DifferenceError, match="names no predicate of its Objective revision"
    ):
        derive_differences(request)


def test_a_forged_reopen_predicate_fingerprint_fails_closed() -> None:
    request = _reopen_request(_condition(PREDICATE_ID, "sha256:" + "b" * 64))
    with pytest.raises(
        DifferenceError, match="reopen condition predicate fingerprint does not recompute"
    ):
        derive_differences(request)


def test_the_resolving_reopen_condition_is_accepted() -> None:
    request = _reopen_request(
        _condition(PREDICATE_ID, target_predicate_fingerprint(target_predicate()))
    )
    bundle = derive_differences(request)
    assert validate_bundle(bundle) == []


def test_an_unresolvable_revision_is_left_to_the_closure_gate() -> None:
    """This rule does not restate reference closure; it adds to it."""

    condition = _condition(PREDICATE_ID, "sha256:" + "b" * 64)
    condition["objective_revision_ref"]["id"] = "OBJ-REV-ABSENT"
    assert reopen_condition_provenance_errors({"reopen_conditions": [condition]}, {}) == []
    with pytest.raises(DifferenceError, match="objective_revisions:OBJ-REV-ABSENT"):
        derive_differences(_reopen_request(condition))


# --------------------------------------------------------------------------- #
# The Target Predicate fingerprint profile
# --------------------------------------------------------------------------- #


def _profile_fields(name: str) -> list[str]:
    block = CONTRACT.read_text(encoding="utf-8")
    assert TARGET_PREDICATE_PROFILE in block
    match = re.search(rf"^{name}=(.+)$", block, re.MULTILINE)
    assert match is not None, name
    return match.group(1).strip().split(",")


def test_the_included_fields_are_exactly_the_contract_profile() -> None:
    predicate = target_predicate()
    included = _profile_fields("INCLUDED_FIELDS")
    excluded = _profile_fields("EXCLUDED_FIELDS")
    assert set(included) <= set(predicate)
    assert set(included).isdisjoint(excluded)
    # And nothing outside the profile reaches the digest: every remaining predicate field
    # is an excluded one.
    assert set(predicate) - set(included) <= set(excluded)


@pytest.mark.parametrize("field", ["subject", "operator", "expected_value", "criticality"])
def test_the_digest_changes_with_every_included_field(field: str) -> None:
    baseline = target_predicate_fingerprint(target_predicate())
    altered = target_predicate()
    altered[field] = "advisory" if field == "criticality" else "CHANGED"
    assert target_predicate_fingerprint(altered) != baseline


def test_the_digest_ignores_the_predicate_id() -> None:
    baseline = target_predicate_fingerprint(target_predicate())
    renamed = target_predicate(predicate_id="TP-RENAMED-0001")
    assert target_predicate_fingerprint(renamed) == baseline


# --------------------------------------------------------------------------- #
# One owner: the producer's gate and the auditor read the same rules
# --------------------------------------------------------------------------- #


def test_the_auditor_holds_no_policy_rule_of_its_own() -> None:
    assert (
        vars(validator_module)["closure_policy_semantic_errors"]
        is closure_policy_semantic_errors
    )
    assert (
        vars(validator_module)["reopen_condition_provenance_errors"]
        is reopen_condition_provenance_errors
    )


def test_the_conformance_gate_reads_the_same_owner() -> None:
    from manosube_agent_civilization.difference.conformance import RECORD_TYPES

    assert RECORD_TYPES["closure_policy"].semantics is closure_policy_semantic_errors


# --------------------------------------------------------------------------- #
# The fragment the emitted sweep could not see
# --------------------------------------------------------------------------- #


def _satisfied_request() -> dict[str, Any]:
    fingerprint = state_fingerprint()
    scope = observation_scope()
    return derivation_request(
        objective_revision(),
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


_MOVING = {
    "minimum_evidence_level": "E1",
    "reopen_conditions": [
        {
            "kind": "target_predicate",
            "id": PREDICATE_ID,
            "predicate_semantic_fingerprint": "sha256:" + "b" * 64,
            "objective_revision_ref": {"kind": "objective_revision", "id": "HEAD"},
        }
    ],
}


def test_a_satisfied_derivation_emits_no_policy() -> None:
    """The premise: there is no output record for the emitted sweep to read."""

    bundle = derive_differences(_satisfied_request())
    assert bundle["satisfied_target_predicates"] == [PREDICATE_ID]
    assert bundle.get("policies", []) == []


@pytest.mark.parametrize("route", ["request", "binding"])
def test_a_moving_reference_in_the_policy_fragment_fails_closed(route: str) -> None:
    request = _satisfied_request()
    if route == "request":
        request["closure_policy_requirements"] = deepcopy(_MOVING)
    else:
        request["bindings"][0]["closure_policy_requirements"] = deepcopy(_MOVING)
    with pytest.raises(SecurityRejectionError, match="moving reference 'HEAD'"):
        derive_differences(request)
