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
from tests.change_helpers import change_request, decide, derived_difference

from manosube_agent_civilization.authority import (
    AUTONOMOUS,
    HUMAN_APPROVAL_REQUIRED,
    PROHIBITED,
)
from manosube_agent_civilization.authority.identity import change_intent_fingerprint
from manosube_agent_civilization.change import (
    AUTHORIZED,
    ChangeBoundaryViolationError,
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


def _autonomous(difference: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    """A rule-permitted AUTONOMOUS decision and the action and scope it bound."""

    requested, where = action(), scope()
    decision = decide(difference, requested, where, rules=[rule(difference["project_id"])])
    assert decision["decision"] == AUTONOMOUS
    return decision, requested, where


# --------------------------------------------------------------------------- #
# 1. an autonomous decision yields exactly one canonical Change
# --------------------------------------------------------------------------- #


def test_an_autonomous_decision_yields_one_canonical_change(difference: dict[str, Any]) -> None:
    decision, requested, where = _autonomous(difference)
    change = derive_change(change_request(difference, decision, requested, where))

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
    decision, requested, where = _autonomous(difference)
    request = change_request(difference, decision, requested, where)
    before = deepcopy(request)
    derive_change(request)
    assert request == before


# --------------------------------------------------------------------------- #
# 2. permission is read, never re-decided
# --------------------------------------------------------------------------- #


def test_a_decision_requiring_human_approval_yields_no_change(difference: dict[str, Any]) -> None:
    """Silence is not permission, and neither is 'close enough'."""

    requested, where = action(), scope()
    decision = decide(difference, requested, where, rules=[])
    assert decision["decision"] == HUMAN_APPROVAL_REQUIRED

    with pytest.raises(UnauthorizedChangeError) as raised:
        derive_change(change_request(difference, decision, requested, where))
    assert "HUMAN_APPROVAL_REQUIRED" in str(raised.value)


def test_a_prohibited_decision_yields_no_change(difference: dict[str, Any]) -> None:
    requested, where = action(), scope()
    decision = decide(
        difference,
        requested,
        where,
        rules=[rule(difference["project_id"])],
        prohibitions=[prohibition(difference["project_id"])],
    )
    assert decision["decision"] == PROHIBITED

    with pytest.raises(UnauthorizedChangeError) as raised:
        derive_change(change_request(difference, decision, requested, where))
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
    decision = decide(difference, requested, where, rules=[permissive])
    assert decision["decision"] == HUMAN_APPROVAL_REQUIRED

    with pytest.raises(UnauthorizedChangeError):
        derive_change(change_request(difference, decision, requested, where))


# --------------------------------------------------------------------------- #
# 3. an exact Human approval reaches Change, and its binding survives
# --------------------------------------------------------------------------- #


def test_an_exactly_approved_action_yields_a_change(difference: dict[str, Any]) -> None:
    requested, where = action("MERGE"), scope()
    granted = approval(difference, requested, where)
    decision = decide(difference, requested, where, approvals=[granted])
    assert decision["decision"] == AUTONOMOUS
    assert decision["approval_ref"] == {"kind": "approval", "id": granted["approval_id"]}

    change = derive_change(change_request(difference, decision, requested, where))
    assert change["status"] == AUTHORIZED
    assert change["action"]["action_kind"] == "MERGE"


def test_the_approvals_change_intent_still_binds_the_derived_change(
    difference: dict[str, Any]
) -> None:
    """``CHANGE_INTENT_FINGERPRINT_REMAINS_BINDING``: Change does not replace the binding.

    The approval bound one fingerprint over (action, scope). The derived Change carries the
    same action and the same scope, so the same fingerprint is still the one that authorizes
    it. v0.1 introduces no second, ``change_id``-based approval binding.
    """

    requested, where = action("DEPLOY_PRODUCTION"), scope()
    granted = approval(difference, requested, where)
    decision = decide(difference, requested, where, approvals=[granted])
    change = derive_change(change_request(difference, decision, requested, where))

    assert granted["change_intent_fingerprint"] == change_intent_fingerprint(
        change["action"], change["scope"]
    )


# --------------------------------------------------------------------------- #
# 4. the operation fingerprint obligation AUTHORITY_CONTRACT.md 7.2 left here
# --------------------------------------------------------------------------- #


def test_a_relabelled_operation_is_not_the_authorized_one(difference: dict[str, Any]) -> None:
    """Different bytes to the same file is a different operation, and is not permitted.

    The decision bound one complete operation. Presenting another under a request that is
    otherwise identical is refused before anything is derived from it.
    """

    approved = action("WRITE_FILE", operation={"path": "src/app.py", "bytes": "AAAA"})
    where = scope()
    decision = decide(difference, approved, where, rules=[rule(difference["project_id"])])
    assert decision["decision"] == AUTONOMOUS

    other = action("WRITE_FILE", operation={"path": "src/app.py", "bytes": "BBBB"})
    assert other["action_semantic_fingerprint"] != approved["action_semantic_fingerprint"]

    with pytest.raises(ChangeBoundaryViolationError):
        derive_change(change_request(difference, decision, other, where))


def test_a_caller_declared_action_fingerprint_is_not_believed(
    difference: dict[str, Any]
) -> None:
    """The digest is recomputed. A label that is believed lets one approval cover two operations."""

    approved, where = action(), scope()
    decision = decide(difference, approved, where, rules=[rule(difference["project_id"])])

    forged = deepcopy(approved)
    forged["operation"] = {"body": "something else entirely"}
    forged["action_semantic_fingerprint"] = approved["action_semantic_fingerprint"]

    with pytest.raises(ChangeError) as raised:
        derive_change(change_request(difference, decision, forged, where))
    assert "fingerprint does not match" in str(raised.value)


# --------------------------------------------------------------------------- #
# 5. exact binding: nothing may be relabelled between Authority and Change
# --------------------------------------------------------------------------- #


def test_a_decision_about_another_difference_does_not_authorize_this_one(
    difference: dict[str, Any]
) -> None:
    decision, requested, where = _autonomous(difference)
    other = deepcopy(difference)
    other["difference_id"] = "D-" + "0" * 64

    with pytest.raises(ChangeError):
        derive_change(change_request(other, decision, requested, where))


def test_a_scope_wider_than_the_authorized_one_is_refused(difference: dict[str, Any]) -> None:
    """The decision permitted one scope. Change may not widen it on the way through."""

    decision, requested, _ = _autonomous(difference)
    wider = scope(paths=["src/app.py", "src/lib.py"])

    with pytest.raises(ChangeBoundaryViolationError) as raised:
        derive_change(change_request(difference, decision, requested, wider))
    assert "scope" in str(raised.value)


def test_a_project_relabelled_request_is_refused(difference: dict[str, Any]) -> None:
    decision, requested, where = _autonomous(difference)
    request = change_request(difference, decision, requested, where, project_id="PRJ-9999")

    with pytest.raises(ChangeBoundaryViolationError):
        derive_change(request)


def test_a_relabelled_decision_address_is_recomputed_and_refused(
    difference: dict[str, Any]
) -> None:
    """The decision is a supplied record here. Its address is recomputed, not read."""

    decision, requested, where = _autonomous(difference)
    forged = deepcopy(decision)
    forged["authority_decision_id"] = "AUTH-DEC-" + "0" * 64

    with pytest.raises(ChangeError) as raised:
        derive_change(change_request(difference, forged, requested, where))
    assert "identity does not match" in str(raised.value)


def test_a_decision_whose_verdict_was_edited_is_refused(difference: dict[str, Any]) -> None:
    """Turning HUMAN_APPROVAL_REQUIRED into AUTONOMOUS by hand does not authorize anything.

    This edit is caught by the *schema* rather than by the fingerprint: an AUTONOMOUS
    decision citing neither a rule nor an approval is not a shape ``authority.schema.json``
    accepts. The refusal is earlier than the identity check, not weaker than it -- and
    asserting only that it is refused keeps this test honest about which gate did it.
    """

    requested, where = action(), scope()
    decision = decide(difference, requested, where, rules=[])
    assert decision["decision"] == HUMAN_APPROVAL_REQUIRED

    forged = deepcopy(decision)
    forged["decision"] = AUTONOMOUS

    with pytest.raises(ChangeValidationError):
        derive_change(change_request(difference, forged, requested, where))


def test_a_schema_valid_edit_is_still_caught_by_the_recomputed_fingerprint(
    difference: dict[str, Any]
) -> None:
    """The gate the previous test does not reach: an edit the schema cannot see.

    ``decision_reason_codes`` participates in the decision's meaning, so editing it leaves a
    record that is still schema-valid and no longer names itself. Only recomputation catches
    this, which is why the recomputation is not optional.
    """

    decision, requested, where = _autonomous(difference)
    forged = deepcopy(decision)
    forged["decision_reason_codes"] = ["APPROVAL_EXACT"]
    assert forged["decision_reason_codes"] != decision["decision_reason_codes"]

    with pytest.raises(ChangeError) as raised:
        derive_change(change_request(difference, forged, requested, where))
    assert "does not match" in str(raised.value)


# --------------------------------------------------------------------------- #
# 6. staleness: 26 blocks a Change bound to a State nobody evaluated
# --------------------------------------------------------------------------- #


def test_a_difference_observed_against_another_revision_is_stale(
    difference: dict[str, Any]
) -> None:
    decision, requested, where = _autonomous(difference)
    moved = deepcopy(difference)
    moved["observed_state_revision"] = difference["observed_state_revision"] + 1

    with pytest.raises(StaleChangeError) as raised:
        derive_change(change_request(moved, decision, requested, where))
    assert "revision" in str(raised.value)


def test_a_difference_observed_against_another_fingerprint_is_stale(
    difference: dict[str, Any]
) -> None:
    """Equal revisions, different content. The diagnostic must not read 'revision 2 vs 2'."""

    decision, requested, where = _autonomous(difference)
    moved = deepcopy(difference)
    moved["observed_state_fingerprint"] = dict(moved["observed_state_fingerprint"])
    moved["observed_state_fingerprint"]["digest"] = "0" * 64

    with pytest.raises(StaleChangeError) as raised:
        derive_change(change_request(moved, decision, requested, where))
    message = str(raised.value)
    assert "fingerprint" in message
    assert "revision" not in message


def test_the_state_binding_is_taken_from_the_decision(difference: dict[str, Any]) -> None:
    """``STATE_BINDING_DERIVED_FROM_AUTHORITY``: there is no second place to supply it."""

    decision, requested, where = _autonomous(difference)
    change = derive_change(change_request(difference, decision, requested, where))

    assert change["expected_state_revision"] == decision["evaluated_state_revision"]
    assert change["before_state_fingerprint"] == decision["evaluated_state_fingerprint"]


# --------------------------------------------------------------------------- #
# 7. identity and idempotency
# --------------------------------------------------------------------------- #


def test_the_same_authorized_change_derives_the_same_identity(
    difference: dict[str, Any]
) -> None:
    decision, requested, where = _autonomous(difference)
    first = derive_change(change_request(difference, decision, requested, where))
    second = derive_change(change_request(difference, decision, requested, where))

    assert first == second
    assert first["change_id"] == second["change_id"]
    assert first["idempotency_key"] == second["idempotency_key"]


def test_two_different_operations_do_not_share_one_identity(
    difference: dict[str, Any]
) -> None:
    where = scope()
    permitting = rule(difference["project_id"])
    changes = []
    for body in ("AAAA", "BBBB"):
        requested = action("WRITE_FILE", operation={"path": "src/app.py", "bytes": body})
        decision = decide(difference, requested, where, rules=[permitting])
        changes.append(derive_change(change_request(difference, decision, requested, where)))

    assert changes[0]["change_id"] != changes[1]["change_id"]
    assert changes[0]["idempotency_key"] != changes[1]["idempotency_key"]


def test_the_idempotency_key_is_the_semantic_fingerprint(difference: dict[str, Any]) -> None:
    """One computation answers 'is this the same change', not two that can drift apart."""

    decision, requested, where = _autonomous(difference)
    change = derive_change(change_request(difference, decision, requested, where))
    assert change["idempotency_key"] == change["change_semantic_fingerprint"]


# --------------------------------------------------------------------------- #
# 8. what Change never does
# --------------------------------------------------------------------------- #


def test_a_change_declares_no_after_state_no_closure_and_no_completion(
    difference: dict[str, Any]
) -> None:
    """24 forbids all three, and the record has no field in which to say them."""

    decision, requested, where = _autonomous(difference)
    change = derive_change(change_request(difference, decision, requested, where))

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

    decision, requested, where = _autonomous(difference)
    request = change_request(difference, decision, requested, where)
    request["note"] = "the human said this was fine"

    with pytest.raises(ChangeError) as raised:
        derive_change(request)
    assert "unknown keys" in str(raised.value)


def test_a_scope_naming_a_path_expression_is_refused(difference: dict[str, Any]) -> None:
    """An unresolved glob is not narrowed to something safe -- it is refused.

    ``authority.schema.json#/$defs/scope`` does not itself reject path expressions; the
    resolved-member check in ``authority.scope`` does, and ``derive_change`` runs it. The
    schema-level gap is recorded as a Phase 4 surface non-claim, not closed here.
    """

    decision, requested, _ = _autonomous(difference)
    for expression in ("src/**", "src/*.py", "../etc/passwd", "/etc/passwd"):
        with pytest.raises(ChangeError):
            derive_change(
                change_request(difference, decision, requested, scope(paths=[expression]))
            )


def test_a_permuted_request_derives_the_identical_change(difference: dict[str, Any]) -> None:
    """Key order is not meaning. Canonical serialization is what makes that true.

    Issue #31 §4 asks for input *permutation*, not only repetition: a request whose keys
    arrive in a different order is the same question, and an identity that moved with key
    order would be an identity of the serialization rather than of the change.
    """

    decision, requested, where = _autonomous(difference)
    straight = change_request(difference, decision, requested, where)

    permuted = {key: deepcopy(straight[key]) for key in reversed(list(straight))}
    permuted["authority_decision"] = {
        key: deepcopy(decision[key]) for key in reversed(list(decision))
    }
    permuted["requested_action"] = {
        key: deepcopy(requested[key]) for key in reversed(list(requested))
    }
    permuted["requested_scope"] = {key: deepcopy(where[key]) for key in reversed(list(where))}
    assert list(permuted) != list(straight)

    assert derive_change(permuted) == derive_change(straight)


def test_a_scope_repeating_one_member_is_refused(difference: dict[str, Any]) -> None:
    """A duplicated member makes a scope read as wider than the set it names."""

    decision, requested, _ = _autonomous(difference)
    repeated = scope(paths=["src/app.py", "src/app.py"])

    with pytest.raises(ChangeError):
        derive_change(change_request(difference, decision, requested, repeated))
