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

#: The digest that binds a decision to its inputs -- **including which inputs governed it**.
#:
#: The provenance references were absent from this list once, and the consequence was not
#: cosmetic: two distinct prohibitions both yielding ``PROHIBITION_MATCHED`` produced one
#: decision identity over two different payloads. A content address that ignores part of its
#: own record is not an address; it is a collision waiting for the two records that differ
#: only where it does not look. Which rule permitted, which approval was used and which
#: prohibitions matched are all part of what the decision *is*.
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

    return _digest({key: value for key, value in action.items() if key != "action_semantic_fingerprint"})


def change_intent_fingerprint(action: dict[str, Any], scope: dict[str, Any]) -> str:
    """The digest an approval binds: exactly this action, over exactly this scope."""

    return _digest({"action": action_fingerprint(action), "scope": scope})


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
