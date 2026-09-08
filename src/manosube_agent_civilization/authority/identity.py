"""Deterministic Authority identities.

Canonical serialization has one owner in this repository -- ``state.canonicalize`` -- and
this module reads it rather than restating it. What is defined here is only *which payload*
each Authority identity is computed over, which is the part that belongs to Authority.

Every identity excludes its own identity field, so a record's address is a function of its
meaning and not of a value someone chose to put in it.
"""

from __future__ import annotations

import hashlib
from typing import Any

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

from .scope import canonical_scope

#: The digest that binds a decision to its inputs -- **including which inputs governed it**.
#:
#: The provenance references were absent from this list once, and the consequence was not
#: cosmetic: two distinct prohibitions both yielding ``PROHIBITION_MATCHED`` produced one
#: decision identity over two different payloads. A content address that ignores part of its
#: own record is not an address; it is a collision waiting for the two records that differ
#: only where it does not look. Which rule permitted, which approval was used and which
#: prohibitions matched are all part of what the decision *is*.
#:
#: An approval that *withheld* the action is provenance too. Two different approvals could
#: otherwise narrow the same request to the same level with the same reason code and produce
#: one identity, which is the collision this list was extended to close in the first place.
#:
#: Still excluded, and deliberately: evaluation timestamps, Agent and session identity, input
#: ordering. Two evaluations of the same question must land on the same identity.
DECISION_SEMANTIC_FIELDS: tuple[str, ...] = (
    "project_id",
    "difference_ref",
    "requested_action",
    "requested_scope",
    "evaluated_state_revision",
    "evaluated_state_fingerprint",
    "resolved_rule_ref",
    "approval_ref",
    "excluding_approval_refs",
    "prohibition_refs",
    "decision",
    "decision_reason_codes",
)

#: What a Human approval is *about*: the action and the scope it covers. This is the binding
#: ``KERNEL_CONSTITUTION.md`` 第22条 calls ``change_id``, expressed without requiring a Change
#: record that v0.1 Phase 4 does not yet produce -- see ``APPROVAL_CONTRACT.md`` §2.
CHANGE_INTENT_FIELDS: tuple[str, ...] = ("action", "scope")


def _digest(payload: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _address(prefix: str, payload: Any) -> str:
    return prefix + hashlib.sha256(canonical_json_bytes(payload)).hexdigest().upper()


def action_fingerprint(action: dict[str, Any]) -> str:
    """The digest of a requested action, over its **complete** operation.

    The action kind, the reversibility and the *operation payload* all participate. Without
    the payload, two operations differing only in what they write -- different bytes to the
    same file -- shared one fingerprint, so an approval for one authorized the other. An
    approval that cannot tell those apart is not binding an operation; it is binding a
    category.

    The payload is **opaque** here. Authority never interprets or executes it; it only
    establishes that this exact payload is the one that was approved, by deriving the digest
    from canonical bytes rather than trusting any digest the caller supplied.
    """

    return _digest(
        {key: value for key, value in action.items() if key != "action_semantic_fingerprint"}
    )


def change_intent_fingerprint(action: dict[str, Any], scope: dict[str, Any]) -> str:
    """The digest an approval binds: exactly this action, over exactly this scope.

    The scope is put in canonical form first, by :func:`authority.scope.canonical_scope` and
    not by any sorting of its own -- normalization has one owner and this reuses it.

    Without that, an approval granted over ``["b", "a"]`` did not bind a request naming
    ``["a", "b"]``: the same members, the same permission, a different digest. An approval
    that cannot recognise its own scope written in another order is an approval a human
    granted and the evaluator cannot find.
    """

    return _digest({"action": action_fingerprint(action), "scope": canonical_scope(scope)})


def decision_semantic_fingerprint(decision: dict[str, Any]) -> str:
    """The digest of a decision's meaning."""

    return _digest({field: decision[field] for field in DECISION_SEMANTIC_FIELDS})


def decision_id(decision: dict[str, Any]) -> str:
    """The content address of an Authority Decision."""

    return _address("AUTH-DEC-", {field: decision[field] for field in DECISION_SEMANTIC_FIELDS})


def rule_id(rule: dict[str, Any]) -> str:
    return _address(
        "AUTH-RULE-", {key: value for key, value in rule.items() if key != "authority_rule_id"}
    )


def prohibition_id(prohibition: dict[str, Any]) -> str:
    return _address(
        "PROHIBIT-", {key: value for key, value in prohibition.items() if key != "prohibition_id"}
    )


def approval_id(approval: dict[str, Any]) -> str:
    return _address(
        "APPROVAL-", {key: value for key, value in approval.items() if key != "approval_id"}
    )


#: What one Verifier Selection Decision *is* (Structural Review Round 3, P13-R3-F1): every
#: field this decision binds together, so two decisions differing in any one of them are two
#: decisions and not one. ``grant_ref``/``excluding_grant_refs`` participate for the identical
#: reason ``approval_ref``/``excluding_approval_refs`` do above -- which grant was used, and
#: which grant *withheld* the selection, are both part of what the decision means.
#: ``declaration_ref`` (Structural Review Round 5, P13-R5) participates for the same reason:
#: which Human Grant Declaration anchored the used grant is itself part of what the decision
#: means, not merely a detail of how it was reached.
VERIFIER_SELECTION_DECISION_SEMANTIC_FIELDS: tuple[str, ...] = (
    "project_id",
    "requirement_id",
    "selection_id",
    "verifier_identity",
    "permitted_boundary",
    "selection_status",
    "selection_authority_ref",
    "grant_ref",
    "excluding_grant_refs",
    "declaration_ref",
    "decision",
    "decision_reason_codes",
)


def verifier_selection_grant_id(grant: dict[str, Any]) -> str:
    return _address(
        "VSEL-GRANT-",
        {key: value for key, value in grant.items() if key != "verifier_selection_grant_id"},
    )


def verifier_selection_decision_semantic_fingerprint(decision: dict[str, Any]) -> str:
    """The digest of a Verifier Selection Decision's meaning."""

    return _digest(
        {field: decision[field] for field in VERIFIER_SELECTION_DECISION_SEMANTIC_FIELDS}
    )


def verifier_selection_decision_id(decision: dict[str, Any]) -> str:
    """The content address of a Verifier Selection Decision."""

    return _address(
        "VSEL-DEC-",
        {field: decision[field] for field in VERIFIER_SELECTION_DECISION_SEMANTIC_FIELDS},
    )


#: What a GitHub Projection Decision's meaning is bound to (Phase 14, Structural Review
#: Round 1, P14-R1-F1) -- the identical "bind every field a caller could otherwise vary
#: independently" discipline :data:`VERIFIER_SELECTION_DECISION_SEMANTIC_FIELDS` already
#: applies, over Projection's own operation-scoping fields instead of Independent
#: Verification's.
GITHUB_PROJECTION_DECISION_SEMANTIC_FIELDS: tuple[str, ...] = (
    "project_id",
    "subject_ref",
    "subject_fingerprint",
    "projection_kind",
    "target_repository",
    "payload_fingerprint",
    "permitted_action",
    "selection_authority_ref",
    "grant_ref",
    "excluding_grant_refs",
    "decision",
    "decision_reason_codes",
)


def github_projection_grant_id(grant: dict[str, Any]) -> str:
    return _address(
        "GH-PROJ-GRANT-",
        {key: value for key, value in grant.items() if key != "github_projection_grant_id"},
    )


def github_projection_decision_semantic_fingerprint(decision: dict[str, Any]) -> str:
    """The digest of a GitHub Projection Decision's meaning."""

    return _digest(
        {field: decision[field] for field in GITHUB_PROJECTION_DECISION_SEMANTIC_FIELDS}
    )


def github_projection_decision_id(decision: dict[str, Any]) -> str:
    """The content address of a GitHub Projection Decision."""

    return _address(
        "GH-PROJ-DEC-",
        {field: decision[field] for field in GITHUB_PROJECTION_DECISION_SEMANTIC_FIELDS},
    )
