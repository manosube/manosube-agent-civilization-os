"""The natural route: Objective + State + Observation -> Difference -> Authority -> Change.

Every Difference here is produced by ``derive_differences`` and every decision by
``evaluate_authority``; nothing is hand-assembled around either producer, so a decision
Authority would never emit cannot make a Change test pass.

Change describes an authorized mutation and stops. None of these tests executes an
operation, updates State, closes a Difference or emits Evidence -- and the absence of any
such assertion is itself the point: there is no API here through which that could happen.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from tests.authority_helpers import action, approval, prohibition, rule, scope
from tests.change_helpers import change_request, derived_difference, route

from manosube_agent_civilization.authority import (
    AUTONOMOUS,
    HUMAN_APPROVAL_REQUIRED,
    PROHIBITED,
)
from manosube_agent_civilization.authority.identity import change_intent_fingerprint
from manosube_agent_civilization.change import (
    AUTHORIZED,
    AuthorityProvenanceError,
    ChangeError,
    ChangeValidationError,
    StaleChangeError,
    UnauthorizedChangeError,
    derive_change,
)

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def difference() -> dict[str, Any]:
    return derived_difference()


def _autonomous(difference: dict[str, Any]) -> tuple[Any, ...]:
    """A rule-permitted AUTONOMOUS decision, its Authority input and its Change request."""

    requested, where = action(), scope()
    authority_input, decision, request = route(
        difference, requested, where, rules=[rule(difference["project_id"])]
    )
    assert decision["decision"] == AUTONOMOUS
    return authority_input, decision, request, requested, where


# --------------------------------------------------------------------------- #
# 1. an autonomous decision yields exactly one canonical Change
# --------------------------------------------------------------------------- #


def test_an_autonomous_decision_yields_one_canonical_change(difference: dict[str, Any]) -> None:
    _, decision, request, _, _ = _autonomous(difference)
    change = derive_change(request)

    assert change["status"] == AUTHORIZED
    assert change["execution_result"] is None
    assert change["change_id"].startswith("CHANGE-")
    assert change["project_id"] == difference["project_id"]
    assert change["difference_ref"] == {"kind": "difference", "id": difference["difference_id"]}
    assert change["authority_ref"] == {
        "kind": "authority_decision",
        "id": decision["authority_decision_id"],
    }
    # The action and the scope are the ones the decision bound, not a re-derivation of them.
    assert change["action"] == decision["requested_action"]
    assert change["scope"] == decision["requested_scope"]


def test_change_derivation_never_mutates_its_request(difference: dict[str, Any]) -> None:
    _, _, request, _, _ = _autonomous(difference)
    before = deepcopy(request)
    derive_change(request)
    assert request == before


# --------------------------------------------------------------------------- #
# 2. provenance: a decision the canonical evaluator did not produce
# --------------------------------------------------------------------------- #
#
# The P1 this vertical shipped with, and the regression that keeps it closed. Each case
# below builds a decision that is *internally perfect* -- schema-valid, correctly addressed,
# semantic fingerprint recomputed -- and is refused anyway, because internal agreement is
# what those digests measure and it is not provenance.


def _self_consistent(genuine: dict[str, Any], **edits: Any) -> dict[str, Any]:
    """A decision edited and then re-hashed into perfect internal agreement.

    This is the forger's whole capability: ``decision_id`` and
    ``decision_semantic_fingerprint`` are public pure functions, so anyone can do this.
    """

    from manosube_agent_civilization.authority.identity import (
        decision_id,
        decision_semantic_fingerprint,
    )

    forged = deepcopy(genuine)
    forged.update(deepcopy(edits))
    forged["decision_semantic_fingerprint"] = decision_semantic_fingerprint(forged)
    forged["authority_decision_id"] = decision_id(forged)
    return forged


def test_a_synthetic_autonomous_decision_citing_a_nonexistent_rule_is_refused(
    difference: dict[str, Any]
) -> None:
    """The exact case the independent review found.

    The caller never calls ``evaluate_authority``. It assembles an AUTONOMOUS decision for a
    Human-only action, cites a rule that exists nowhere in the repository, and re-hashes the
    record into internal agreement. Before the repair this produced an AUTHORIZED Change to
    MERGE.
    """

    requested, where = action("MERGE"), scope()
    # No rule and no approval: the canonical evaluator answers HUMAN_APPROVAL_REQUIRED here.
    authority_input, honest, _ = route(difference, requested, where, rules=[])
    assert honest["decision"] == HUMAN_APPROVAL_REQUIRED

    forged = _self_consistent(
        honest,
        decision=AUTONOMOUS,
        decision_reason_codes=["RULE_PERMITS_AUTONOMOUS"],
        resolved_rule_ref={"kind": "authority_rule", "id": "AUTH-RULE-" + "A" * 64},
    )
    # It is internally flawless.
    from manosube_agent_civilization.authority.identity import decision_id

    assert forged["authority_decision_id"] == decision_id(forged)

    with pytest.raises(AuthorityProvenanceError) as raised:
        derive_change(change_request(authority_input, forged))
    assert "canonical evaluator" in str(raised.value)


def test_a_forged_approval_reference_is_refused(difference: dict[str, Any]) -> None:
    """Citing an approval that was never granted does not resolve a Human-only floor."""

    requested, where = action("DEPLOY_PRODUCTION"), scope()
    authority_input, honest, _ = route(difference, requested, where, rules=[])
    forged = _self_consistent(
        honest,
        decision=AUTONOMOUS,
        decision_reason_codes=["APPROVAL_EXACT"],
        approval_ref={"kind": "approval", "id": "APPROVAL-" + "B" * 64},
    )

    with pytest.raises(AuthorityProvenanceError):
        derive_change(change_request(authority_input, forged))


def test_a_prohibited_decision_relabelled_autonomous_is_refused(
    difference: dict[str, Any]
) -> None:
    requested, where = action(), scope()
    authority_input, honest, _ = route(
        difference,
        requested,
        where,
        rules=[rule(difference["project_id"])],
        prohibitions=[prohibition(difference["project_id"])],
    )
    assert honest["decision"] == PROHIBITED

    # Schema-valid on purpose: an AUTONOMOUS decision must cite a rule or an approval, so a
    # forgery that omits both is caught by the schema and never reaches the provenance gate.
    # This one cites a well-formed rule that simply does not exist, which is the case only
    # reproduction can refuse.
    forged = _self_consistent(
        honest,
        decision=AUTONOMOUS,
        decision_reason_codes=["RULE_PERMITS_AUTONOMOUS"],
        prohibition_refs=[],
        resolved_rule_ref={"kind": "authority_rule", "id": "AUTH-RULE-" + "C" * 64},
    )
    with pytest.raises(AuthorityProvenanceError):
        derive_change(change_request(authority_input, forged))


def test_an_honest_decision_for_other_inputs_does_not_authorize_these(
    difference: dict[str, Any]
) -> None:
    """A genuine decision, produced by the evaluator -- about something else.

    Provenance is not "some evaluator produced this at some point". It is "the evaluator
    produces *this* from *these* inputs", so a real decision moved onto another request is
    refused exactly as a synthetic one is.
    """

    permitting = rule(difference["project_id"])
    _, elsewhere, _ = route(
        difference,
        action("WRITE_FILE", operation={"path": "src/app.py", "bytes": "AAAA"}),
        scope(),
        rules=[permitting],
    )
    assert elsewhere["decision"] == AUTONOMOUS

    here, _, _ = route(
        difference,
        action("WRITE_FILE", operation={"path": "src/app.py", "bytes": "BBBB"}),
        scope(),
        rules=[permitting],
    )

    with pytest.raises(AuthorityProvenanceError):
        derive_change(change_request(here, elsewhere))


def test_a_decision_edited_below_its_own_address_is_refused(
    difference: dict[str, Any]
) -> None:
    """Whole-record comparison, not address comparison.

    An address is a digest over a *projection*, so two records can agree on every field the
    address covers and still differ. Comparing only addresses would let that through.
    """

    authority_input, decision, _, _, _ = _autonomous(difference)
    tampered = deepcopy(decision)
    tampered["schema_version"] = "0.1 "

    with pytest.raises(ChangeError):
        derive_change(change_request(authority_input, tampered))


def test_the_decision_is_a_claim_and_never_the_source_of_the_change(
    difference: dict[str, Any]
) -> None:
    """The Change is built from the reproduced decision, so a claim cannot steer it.

    Every field is read from what the evaluator returned. There is no path by which a
    caller-supplied value reaches the emitted record.
    """

    _, decision, request, _, _ = _autonomous(difference)
    change = derive_change(request)

    assert change["action"] == decision["requested_action"]
    assert change["scope"] == decision["requested_scope"]
    assert change["project_id"] == decision["project_id"]
    assert change["expected_state_revision"] == decision["evaluated_state_revision"]
    assert change["before_state_fingerprint"] == decision["evaluated_state_fingerprint"]
    assert change["authority_ref"]["id"] == decision["authority_decision_id"]


# --------------------------------------------------------------------------- #
# 3. permission is read, never re-decided
# --------------------------------------------------------------------------- #


def test_a_decision_requiring_human_approval_yields_no_change(difference: dict[str, Any]) -> None:
    """Silence is not permission, and neither is 'close enough'."""

    requested, where = action(), scope()
    _, decision, request = route(difference, requested, where, rules=[])
    assert decision["decision"] == HUMAN_APPROVAL_REQUIRED

    with pytest.raises(UnauthorizedChangeError) as raised:
        derive_change(request)
    assert "HUMAN_APPROVAL_REQUIRED" in str(raised.value)


def test_a_prohibited_decision_yields_no_change(difference: dict[str, Any]) -> None:
    requested, where = action(), scope()
    _, decision, request = route(
        difference,
        requested,
        where,
        rules=[rule(difference["project_id"])],
        prohibitions=[prohibition(difference["project_id"])],
    )
    assert decision["decision"] == PROHIBITED

    with pytest.raises(UnauthorizedChangeError) as raised:
        derive_change(request)
    assert "PROHIBITED" in str(raised.value)


@pytest.mark.parametrize(
    "human_only",
    ["MERGE", "DEPLOY_PRODUCTION", "CHANGE_CREDENTIAL", "CHANGE_SECURITY_POLICY", "RELEASE"],
)
def test_a_human_only_action_without_approval_yields_no_change(
    difference: dict[str, Any], human_only: str
) -> None:
    """A rule saying AUTONOMOUS does not lower a Human-only floor, and Change does not either."""

    requested, where = action(human_only), scope()
    permissive = rule(difference["project_id"], action_kinds=[human_only], decision=AUTONOMOUS)
    _, decision, request = route(difference, requested, where, rules=[permissive])
    assert decision["decision"] == HUMAN_APPROVAL_REQUIRED

    with pytest.raises(UnauthorizedChangeError):
        derive_change(request)


# --------------------------------------------------------------------------- #
# 4. an exact Human approval reaches Change, and its binding survives
# --------------------------------------------------------------------------- #


def test_an_exactly_approved_action_yields_a_change(difference: dict[str, Any]) -> None:
    requested, where = action("MERGE"), scope()
    granted = approval(difference, requested, where)
    _, decision, request = route(difference, requested, where, approvals=[granted])
    assert decision["decision"] == AUTONOMOUS
    assert decision["approval_ref"] == {"kind": "approval", "id": granted["approval_id"]}

    change = derive_change(request)
    assert change["status"] == AUTHORIZED
    assert change["action"]["action_kind"] == "MERGE"


def test_the_approvals_change_intent_still_binds_the_derived_change(
    difference: dict[str, Any]
) -> None:
    """``CHANGE_INTENT_FINGERPRINT_REMAINS_BINDING``: Change does not replace the binding."""

    requested, where = action("DEPLOY_PRODUCTION"), scope()
    granted = approval(difference, requested, where)
    _, _, request = route(difference, requested, where, approvals=[granted])
    change = derive_change(request)

    assert granted["change_intent_fingerprint"] == change_intent_fingerprint(
        change["action"], change["scope"]
    )


# --------------------------------------------------------------------------- #
# 5. the operation fingerprint obligation AUTHORITY_CONTRACT.md 7.2 left here
# --------------------------------------------------------------------------- #


def test_a_relabelled_operation_is_not_the_authorized_one(difference: dict[str, Any]) -> None:
    """Different bytes to the same file is a different operation, and is not permitted."""

    permitting = rule(difference["project_id"])
    approved = action("WRITE_FILE", operation={"path": "src/app.py", "bytes": "AAAA"})
    other = action("WRITE_FILE", operation={"path": "src/app.py", "bytes": "BBBB"})
    assert other["action_semantic_fingerprint"] != approved["action_semantic_fingerprint"]

    _, decision, _ = route(difference, approved, scope(), rules=[permitting])
    swapped, _, _ = route(difference, other, scope(), rules=[permitting])

    with pytest.raises(AuthorityProvenanceError):
        derive_change(change_request(swapped, decision))


def test_a_caller_declared_action_fingerprint_is_not_believed(
    difference: dict[str, Any]
) -> None:
    """The digest is recomputed by Authority, on the inputs Change hands it."""

    approved, where = action(), scope()
    forged_action = deepcopy(approved)
    forged_action["operation"] = {"body": "something else entirely"}
    forged_action["action_semantic_fingerprint"] = approved["action_semantic_fingerprint"]

    authority_input, decision, _ = route(
        difference, approved, where, rules=[rule(difference["project_id"])]
    )
    tampered = deepcopy(authority_input)
    tampered["requested_action"] = forged_action

    with pytest.raises(ChangeError) as raised:
        derive_change(
            {
                "schema_version": "0.1",
                "authority_request": tampered,
                "authority_decision": decision,
            }
        )
    assert "fingerprint" in str(raised.value)


# --------------------------------------------------------------------------- #
# 6. staleness: 26 blocks a Change bound to a State nobody evaluated
# --------------------------------------------------------------------------- #


def test_a_difference_observed_against_another_revision_is_stale(
    difference: dict[str, Any]
) -> None:
    """Authority detects it; Change keeps the word 26 uses for it."""

    requested, where = action(), scope()
    authority_input, _, _ = route(
        difference, requested, where, rules=[rule(difference["project_id"])]
    )
    stale = deepcopy(authority_input)
    stale["current_state_revision"] = difference["observed_state_revision"] + 1

    with pytest.raises(StaleChangeError) as raised:
        derive_change({"schema_version": "0.1", "authority_request": stale, "authority_decision": {}})
    assert "revision" in str(raised.value)


def test_a_difference_observed_against_another_fingerprint_is_stale(
    difference: dict[str, Any]
) -> None:
    """Equal revisions, different content. The diagnostic must not read 'revision 2 vs 2'."""

    requested, where = action(), scope()
    authority_input, _, _ = route(
        difference, requested, where, rules=[rule(difference["project_id"])]
    )
    stale = deepcopy(authority_input)
    stale["current_state_fingerprint"] = dict(stale["current_state_fingerprint"])
    stale["current_state_fingerprint"]["digest"] = "0" * 64

    with pytest.raises(StaleChangeError) as raised:
        derive_change({"schema_version": "0.1", "authority_request": stale, "authority_decision": {}})
    message = str(raised.value)
    assert "fingerprint" in message
    assert "revision" not in message


def test_the_state_binding_is_taken_from_the_decision(difference: dict[str, Any]) -> None:
    """``STATE_BINDING_DERIVED_FROM_AUTHORITY``: there is no second place to supply it."""

    _, decision, request, _, _ = _autonomous(difference)
    change = derive_change(request)

    assert change["expected_state_revision"] == decision["evaluated_state_revision"]
    assert change["before_state_fingerprint"] == decision["evaluated_state_fingerprint"]


# --------------------------------------------------------------------------- #
# 7. identity and idempotency
# --------------------------------------------------------------------------- #


def test_the_same_authorized_change_derives_the_same_identity(
    difference: dict[str, Any]
) -> None:
    _, _, request, _, _ = _autonomous(difference)
    first = derive_change(deepcopy(request))
    second = derive_change(deepcopy(request))

    assert first == second
    assert first["change_id"] == second["change_id"]
    assert first["idempotency_key"] == second["idempotency_key"]


def test_two_different_operations_do_not_share_one_identity(
    difference: dict[str, Any]
) -> None:
    permitting = rule(difference["project_id"])
    changes = []
    for body in ("AAAA", "BBBB"):
        requested = action("WRITE_FILE", operation={"path": "src/app.py", "bytes": body})
        _, _, request = route(difference, requested, scope(), rules=[permitting])
        changes.append(derive_change(request))

    assert changes[0]["change_id"] != changes[1]["change_id"]
    assert changes[0]["idempotency_key"] != changes[1]["idempotency_key"]


def test_the_idempotency_key_is_the_semantic_fingerprint(difference: dict[str, Any]) -> None:
    """One computation answers 'is this the same change', not two that can drift apart."""

    _, _, request, _, _ = _autonomous(difference)
    change = derive_change(request)
    assert change["idempotency_key"] == change["change_semantic_fingerprint"]


def test_a_permuted_request_derives_the_identical_change(difference: dict[str, Any]) -> None:
    """Key order is not meaning. Canonical serialization is what makes that true."""

    authority_input, decision, request, _, _ = _autonomous(difference)
    permuted = {
        "schema_version": "0.1",
        "authority_request": {
            key: deepcopy(authority_input[key]) for key in reversed(list(authority_input))
        },
        "authority_decision": {key: deepcopy(decision[key]) for key in reversed(list(decision))},
    }
    assert list(permuted["authority_request"]) != list(authority_input)

    assert derive_change(permuted) == derive_change(request)


# --------------------------------------------------------------------------- #
# 8. what Change never does
# --------------------------------------------------------------------------- #


def test_a_change_declares_no_after_state_no_closure_and_no_completion(
    difference: dict[str, Any]
) -> None:
    """24 forbids all three, and the record has no field in which to say them."""

    _, _, request, _, _ = _autonomous(difference)
    change = derive_change(request)

    for forbidden in (
        "after_state_fingerprint",
        "after_state_revision",
        "closes_difference",
        "difference_closure",
        "objective_completed",
        "completion",
        "evidence_ref",
    ):
        assert forbidden not in change


def test_a_change_request_carrying_prose_is_refused(difference: dict[str, Any]) -> None:
    """An ignored key is still a channel. It is refused rather than quietly dropped."""

    _, _, request, _, _ = _autonomous(difference)
    request["note"] = "the human said this was fine"

    with pytest.raises(ChangeError) as raised:
        derive_change(request)
    assert "unknown keys" in str(raised.value)


def test_a_scope_naming_a_path_expression_is_refused(difference: dict[str, Any]) -> None:
    """An unresolved glob is not narrowed to something safe -- it is refused.

    ``authority.schema.json#/$defs/scope`` does not itself reject path expressions; the
    resolved-member check in ``authority.scope`` does, and it now runs inside the canonical
    evaluator Change calls. The schema-level gap is recorded as a Phase 4 surface non-claim.
    """

    requested = action()
    for expression in ("src/**", "src/*.py", "../etc/passwd", "/etc/passwd"):
        authority_input, _, _ = route(
            difference,
            requested,
            scope(),
            rules=[rule(difference["project_id"])],
        )
        authority_input["requested_scope"] = scope(paths=[expression])
        with pytest.raises(ChangeError):
            derive_change(
                {
                    "schema_version": "0.1",
                    "authority_request": authority_input,
                    "authority_decision": {},
                }
            )


def test_a_scope_repeating_one_member_is_refused(difference: dict[str, Any]) -> None:
    """A duplicated member makes a scope read as wider than the set it names."""

    authority_input, _, _ = route(
        difference, action(), scope(), rules=[rule(difference["project_id"])]
    )
    authority_input["requested_scope"] = scope(paths=["src/app.py", "src/app.py"])

    with pytest.raises(ChangeError):
        derive_change(
            {
                "schema_version": "0.1",
                "authority_request": authority_input,
                "authority_decision": {},
            }
        )


def test_a_malformed_claim_is_refused_before_it_is_compared(
    difference: dict[str, Any]
) -> None:
    """A claim that is not a well-formed decision gets a diagnostic about its shape."""

    authority_input, _, _, _, _ = _autonomous(difference)

    with pytest.raises(ChangeValidationError):
        derive_change(
            {
                "schema_version": "0.1",
                "authority_request": authority_input,
                "authority_decision": {
                    "schema_version": "0.1",
                    "authority_decision_id": "AUTH-DEC-" + "0" * 64,
                },
            }
        )
