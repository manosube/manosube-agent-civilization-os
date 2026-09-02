"""Whether a supplied Human approval actually covers this exact request.

An approval is not consulted for what it permits in general. It is checked against the one
request in front of it, on every binding it carries, and a single mismatch makes it
unusable. The function below returns *why* it is unusable rather than a bare boolean,
because a caller told only "no" cannot tell a human what to re-approve.

Nothing here infers an approval. Authorship, a mention, a review, a comment and a
conversation are not approvals (``CAPABILITY_AUTHORITY_SEPARATION.md`` §2); an approval is
a record or it is absent.
"""

from __future__ import annotations

from typing import Any

from manosube_agent_civilization.difference.admissibility import (
    require_collection,
    require_object,
    require_scalar_tag,
)

from .errors import AuthorityError
from .scope import is_contained, require_scope

ACTIVE = "ACTIVE"
REVOKED = "REVOKED"
EXPIRED = "EXPIRED"
APPROVAL_STATUSES: frozenset[str] = frozenset({ACTIVE, REVOKED, EXPIRED})

_REQUIRED_KEYS: tuple[str, ...] = (
    "schema_version",
    "approval_id",
    "project_id",
    "difference_ref",
    "change_intent_fingerprint",
    "approved_state_revision",
    "approved_state_fingerprint",
    "approved_action_fingerprint",
    "approved_scope",
    "prohibited_actions",
    "approved_by",
    "approved_at",
    "expires_at",
    "status",
)


def require_approval(value: Any, context: str) -> dict[str, Any]:
    """Return *value* once it can be read as an approval; reject it otherwise."""

    approval = require_object(value, context)
    for key in _REQUIRED_KEYS:
        if key not in approval:
            raise AuthorityError(f"{context} omits a required key: {key}")
    require_scalar_tag(approval["project_id"], f"{context} project")
    require_scalar_tag(approval["change_intent_fingerprint"], f"{context} change intent")
    require_scalar_tag(approval["approved_action_fingerprint"], f"{context} action fingerprint")
    require_scalar_tag(approval["approved_at"], f"{context} approved_at")
    require_scalar_tag(approval["expires_at"], f"{context} expires_at")
    status = require_scalar_tag(approval["status"], f"{context} status")
    if status not in APPROVAL_STATUSES:
        raise AuthorityError(f"{context} declares an unknown approval status: {status!r}")
    require_object(approval["difference_ref"], f"{context} difference reference")
    require_object(approval["approved_state_fingerprint"], f"{context} state fingerprint")
    require_scope(approval["approved_scope"], f"{context} scope")
    prohibited = require_collection(approval["prohibited_actions"], f"{context} prohibited actions")
    for position, action_kind in enumerate(prohibited):
        require_scalar_tag(action_kind, f"{context} prohibited_actions[{position}]")
    approver = require_object(approval["approved_by"], f"{context} approver")
    if approver.get("kind") != "human_authority":
        raise AuthorityError(
            f"{context} approver is not a Human Authority reference: {approver.get('kind')!r}"
        )
    return approval


def unusable_reasons(
    approval: dict[str, Any],
    *,
    project_id: str,
    difference_id: str,
    change_intent: str,
    action_fingerprint: str,
    action_kind: str,
    requested_scope: dict[str, Any],
    state_revision: int,
    state_fingerprint: dict[str, Any],
    evaluation_time: str,
) -> list[str]:
    """Return every reason this approval does not cover this request; empty means it does.

    Every binding is checked, not the first failing one, so a human re-approving sees the
    whole gap rather than discovering it one round at a time.
    """

    reasons: list[str] = []
    if approval["status"] != ACTIVE:
        reasons.append(f"APPROVAL_{approval['status']}")
    # The validity window is compared against a supplied time, never a clock read. Two
    # evaluations of the same request must agree, and a clock makes that impossible --
    # ``APPROVAL_CONTRACT.md`` §7.
    if not (str(approval["approved_at"]) <= evaluation_time <= str(approval["expires_at"])):
        reasons.append("APPROVAL_OUTSIDE_VALIDITY_WINDOW")
    if approval["project_id"] != project_id:
        reasons.append("APPROVAL_PROJECT_MISMATCH")
    if approval["difference_ref"].get("id") != difference_id:
        reasons.append("APPROVAL_DIFFERENCE_MISMATCH")
    if approval["change_intent_fingerprint"] != change_intent:
        reasons.append("APPROVAL_CHANGE_INTENT_MISMATCH")
    if approval["approved_action_fingerprint"] != action_fingerprint:
        reasons.append("APPROVAL_ACTION_FINGERPRINT_MISMATCH")
    if approval["approved_state_revision"] != state_revision:
        reasons.append("APPROVAL_STATE_REVISION_STALE")
    if approval["approved_state_fingerprint"] != state_fingerprint:
        reasons.append("APPROVAL_STATE_FINGERPRINT_STALE")
    if not is_contained(requested_scope, approval["approved_scope"]):
        reasons.append("APPROVAL_SCOPE_WIDENED")
    if action_kind in approval["prohibited_actions"]:
        # An approval may narrow itself. It may never widen -- ``APPROVAL_CONTRACT.md`` §6.
        reasons.append("APPROVAL_EXCLUDES_ACTION")
    return sorted(reasons)
