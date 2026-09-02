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

#: The digest that binds a decision to its inputs. Excluded from it: evaluation timestamps,
#: rule and prohibition *identities* (their content is what matters), and anything derived
#: from a session, an Agent or a clock. Two evaluations of the same question must land on
#: the same identity or the record is not canonical.
DECISION_SEMANTIC_FIELDS: tuple[str, ...] = (
    "project_id",
    "difference_ref",
    "requested_action",
    "requested_scope",
    "evaluated_state_revision",
    "evaluated_state_fingerprint",
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
    """The digest of a requested action, excluding the fingerprint field itself."""

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
