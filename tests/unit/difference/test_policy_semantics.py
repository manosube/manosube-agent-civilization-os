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
from manosube_agent_civilization.difference.errors import (
    IdentityCollisionError,
    SecurityRejectionError,
)
from manosube_agent_civilization.difference.identity import (
    POLICY_UNORDERED_SET_FIELDS,
    TARGET_PREDICATE_PROFILE,
    closure_policy_id,
    completion_claim_fingerprint,
    completion_claim_id,
    policy_semantic_fingerprint,
    policy_semantic_projection,
    target_predicate_fingerprint,
)
from manosube_agent_civilization.difference.policy import (
    CLAIM_SEMANTIC_FIELDS,
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
    """The gate's rejection is the owner's own first error, verbatim.

    The hook raises rather than returning errors, so each rule keeps its own exception
    type; what is asserted here is that the message the gate raises is the message the
    owner produced, which a second copy of the rule could not satisfy by accident.
    """

    from manosube_agent_civilization.difference.conformance import RECORD_TYPES

    hook = RECORD_TYPES["closure_policy"].semantics
    assert hook is not None
    _, forged = _carried(_forge_claim_id)
    expected = sorted(closure_policy_semantic_errors(forged, "policies[X]"))
    assert expected
    with pytest.raises(DifferenceError) as raised:
        hook(forged, "policies[X]")
    assert str(raised.value) == expected[0]


def test_every_objective_revision_route_rejects_an_ambiguous_predicate_id() -> None:
    """Not only the requested revision: the gate covers carried and emitted ones too."""

    from manosube_agent_civilization.difference.conformance import RECORD_TYPES

    hook = RECORD_TYPES["objective_revision"].semantics
    assert hook is not None
    revision = objective_revision()
    hook(revision, "objective_revisions[OBJ-REV-0001]")
    ambiguous = deepcopy(revision)
    second = deepcopy(ambiguous["target_predicates"][0])
    second["expected_value"] = "SOMETHING-ELSE"
    ambiguous["target_predicates"].append(second)
    with pytest.raises(
        IdentityCollisionError, match="two different Target Predicates under one identity"
    ):
        hook(ambiguous, "objective_revisions[OBJ-REV-0001]")


def _ambiguous_carried_revision(request: dict[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = request["bindings"][0]["predecessor"]["context"]
    base = deepcopy(context["objective_revisions"][0])
    ambiguous = deepcopy(base)
    ambiguous["objective_revision_id"] = "OBJ-REV-0002"
    ambiguous["revision"] = base["revision"] + 1
    ambiguous["previous_objective_ref"] = {
        "kind": "objective_revision", "id": base["objective_revision_id"]
    }
    ambiguous["change_reason"] = "ambiguous"
    second = deepcopy(base["target_predicates"][0])
    second["expected_value"] = "SOMETHING-ELSE"
    ambiguous["target_predicates"] = [deepcopy(base["target_predicates"][0]), second]
    context["objective_revisions"].append(ambiguous)
    revision: dict[str, Any] = ambiguous
    return revision


def test_an_ambiguous_carried_revision_nothing_points_at_fails_closed() -> None:
    """The route the reopen-condition rule alone would not have reached."""

    request, _ = _carried()
    ambiguous = _ambiguous_carried_revision(request)
    assert [p["predicate_id"] for p in ambiguous["target_predicates"]] == ["TP-0001", "TP-0001"]
    with pytest.raises(
        IdentityCollisionError, match="two different Target Predicates under one identity"
    ):
        derive_differences(request)


def test_reopen_provenance_indexes_through_the_identity_owner() -> None:
    """And the rule that reads a revision does not index it by comprehension.

    A comprehension keeps the *last* payload, so this rule would have resolved one
    interpretation of an ambiguous identity while another consumer resolved the other.
    """

    ambiguous = objective_revision()
    second = deepcopy(ambiguous["target_predicates"][0])
    second["expected_value"] = "SOMETHING-ELSE"
    ambiguous["target_predicates"].append(second)
    condition = _condition(PREDICATE_ID, target_predicate_fingerprint(second))
    errors = reopen_condition_provenance_errors(
        {"closure_policy_id": "CP-X", "reopen_conditions": [condition]},
        {"OBJ-REV-0001": ambiguous},
    )
    assert errors == [
        "reopen condition Objective revision is ambiguous: OBJ-REV-0001: "
        "Objective declares two different Target Predicates under one identity: TP-0001"
    ]


# --------------------------------------------------------------------------- #
# DUPLICATE_SET_MEMBER=REJECT, decided after the semantic projection
# --------------------------------------------------------------------------- #


def _invariant(commit: str, blob: str) -> dict[str, Any]:
    return {
        "kind": "kernel_invariant",
        "id": "X-003",
        "contract_source_ref": {
            "kind": "git_blob",
            "repository": "manosube/manosube-agent-civilization-os",
            "commit_sha": commit * 40,
            "path": "00_KERNEL/KERNEL_INVARIANTS.md",
            "blob_sha": blob * 40,
            "invariant_definition_sha256": "sha256:" + "c" * 64,
        },
    }


def test_the_unordered_set_fields_are_exactly_the_contract_profile() -> None:
    declared = _profile_fields("UNORDERED_SETS")
    assert set(declared) == set(POLICY_UNORDERED_SET_FIELDS)
    assert _profile_fields("DUPLICATE_SET_MEMBER") == ["REJECT"]


def test_two_invariants_differing_only_in_excluded_provenance_fail_closed() -> None:
    """`uniqueItems` cannot see this: the duplicate is created by the projection."""

    first, second = _invariant("a", "b"), _invariant("d", "e")
    assert first != second
    request = _reopen_request(
        _condition(PREDICATE_ID, target_predicate_fingerprint(target_predicate()))
    )
    request["closure_policy_requirements"]["required_invariants"] = [first, second]
    with pytest.raises(
        DifferenceError, match=r"duplicate member: .*\.required_invariants"
    ):
        derive_differences(request)


def test_two_invariants_differing_in_included_semantics_are_accepted() -> None:
    first = _invariant("a", "b")
    second = _invariant("a", "b")
    second["id"] = "X-004"
    request = _reopen_request(
        _condition(PREDICATE_ID, target_predicate_fingerprint(target_predicate()))
    )
    request["closure_policy_requirements"]["required_invariants"] = [first, second]
    bundle = derive_differences(request)
    assert len(bundle["policies"][0]["required_invariants"]) == 2
    assert validate_bundle(bundle) == []


def test_two_reopen_conditions_differing_only_in_excluded_provenance_fail_closed() -> None:
    """The Policy identity must not depend on set multiplicity."""

    request, policy = _carried()
    context = request["bindings"][0]["predecessor"]["context"]
    base = context["objective_revisions"][0]
    sibling = deepcopy(base)
    sibling["objective_revision_id"] = "OBJ-REV-0002"
    sibling["revision"] = base["revision"] + 1
    sibling["previous_objective_ref"] = {
        "kind": "objective_revision", "id": base["objective_revision_id"]
    }
    sibling["change_reason"] = "editorial"
    context["objective_revisions"].append(sibling)
    fingerprint = target_predicate_fingerprint(base["target_predicates"][0])
    identity = base["target_predicates"][0]["predicate_id"]
    policy["reopen_conditions"] = [
        {
            "kind": "target_predicate", "id": identity,
            "predicate_semantic_fingerprint": fingerprint,
            "objective_revision_ref": {
                "kind": "objective_revision", "id": base["objective_revision_id"]
            },
        },
        {
            "kind": "target_predicate", "id": identity,
            "predicate_semantic_fingerprint": fingerprint,
            "objective_revision_ref": {"kind": "objective_revision", "id": "OBJ-REV-0002"},
        },
    ]
    _seal(policy)
    with pytest.raises(DifferenceError, match=r"duplicate member: .*\.reopen_conditions"):
        derive_differences(request)


def test_the_requested_objective_rejects_an_ambiguous_predicate_id() -> None:
    """Both Objective routes, not only the carried one the finding named."""

    ambiguous = objective_revision()
    second = deepcopy(ambiguous["target_predicates"][0])
    second["expected_value"] = "SOMETHING-ELSE"
    ambiguous["target_predicates"].append(second)
    request = _reopen_request(
        _condition(PREDICATE_ID, target_predicate_fingerprint(target_predicate()))
    )
    request["objective_revision"] = ambiguous
    with pytest.raises(
        IdentityCollisionError, match="two different Target Predicates under one identity"
    ):
        derive_differences(request)


def test_a_duplicate_nested_below_a_claim_wrapper_fails_closed() -> None:
    """A required Claim's own payload is checked recursively, below its wrappers."""

    def mutate(policy: dict[str, Any]) -> None:
        claim = policy["required_claims"][0]
        # Two members that are equal only *after* their own inner set is canonically
        # ordered: the duplicate is two wrappers down and invisible to a shallow compare.
        claim["claim"] = {
            "values": {
                "collection_kind": "UNORDERED_SET",
                "members": [
                    {"collection_kind": "UNORDERED_SET", "members": [1, 2]},
                    {"collection_kind": "UNORDERED_SET", "members": [2, 1]},
                ],
            }
        }
        claim["claim_semantic_fingerprint"] = completion_claim_fingerprint(
            {key: claim[key] for key in CLAIM_SEMANTIC_FIELDS}
        )
        claim["id"] = completion_claim_id({key: claim[key] for key in CLAIM_SEMANTIC_FIELDS})
        _seal(policy)

    request, _ = _carried(mutate)
    with pytest.raises(
        DifferenceError, match="required Claim carries a duplicate set member"
    ):
        derive_differences(request)


def test_the_duplicate_authority_is_shared_with_the_recursive_walk() -> None:
    """One place decides set multiplicity, for both shapes of declared set."""

    from manosube_agent_civilization.difference import canonical

    assert canonical.has_duplicate_members([{"a": 1}, {"a": 1}])
    assert not canonical.has_duplicate_members([{"a": 1}, {"a": 2}])
    # The wrapper-declared shape reads the same function.
    assert canonical.has_recursive_set_duplicate(
        {"collection_kind": "UNORDERED_SET", "members": [{"a": 1}, {"a": 1}]}
    )
    source = Path(
        "src/manosube_agent_civilization/difference/canonical.py"
    ).read_text(encoding="utf-8")
    walk = source.split("def has_recursive_set_duplicate(")[1].split("\ndef ")[0]
    assert "has_duplicate_members(" in walk
    policy_source = Path(
        "src/manosube_agent_civilization/difference/policy.py"
    ).read_text(encoding="utf-8")
    rule = policy_source.split("def _duplicate_set_errors(")[1].split("\ndef ")[0]
    assert "has_duplicate_members(" in rule
    assert "len(set(" not in rule


def test_the_duplicate_rule_reads_the_digest_projection() -> None:
    """Not a hand-copied second projection: the same one the digest is computed over."""

    policy = {
        "target_predicate_ref": {"kind": "target_predicate", "id": PREDICATE_ID},
        "required_observation_scope": None,
        "minimum_evidence_level": "E1",
        "required_claims": [],
        "required_invariants": [_invariant("a", "b"), _invariant("d", "e")],
        "allowed_terminal_states": ["CLOSED"],
        "independent_verification_required": False,
        "maximum_evidence_age": None,
        "contradiction_policy": "FAIL_CLOSED",
        "reopen_conditions": [],
    }
    projection = policy_semantic_projection(policy)
    assert projection["required_invariants"][0] == projection["required_invariants"][1]
    assert any(
        "required_invariants" in error
        for error in closure_policy_semantic_errors(policy, "policies[X]")
    )


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
