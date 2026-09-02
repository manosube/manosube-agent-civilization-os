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

from datetime import datetime
from typing import Any

from .conformance import admit
from .errors import AuthorityError
from .scope import is_contained, require_scope

ACTIVE = "ACTIVE"
REVOKED = "REVOKED"
EXPIRED = "EXPIRED"
APPROVAL_STATUSES: frozenset[str] = frozenset({ACTIVE, REVOKED, EXPIRED})

def require_approval(value: Any, context: str) -> dict[str, Any]:
    """Return *value* once it is a canonical approval; reject it otherwise.

    Admission is the shared gate, not a local copy of it. The local copy is what let a
    record whose ``approved_by`` was merely ``{"kind": "human_authority"}`` -- no approver
    identity at all -- lower a decision to ``AUTONOMOUS``.
    """

    approval = admit(value, "approval", context)
    # The schema fixes the scope's *shape*; only this fixes that its members are enumerated
    # locations rather than expressions. An approval covering ``src/*`` would be an approval
    # whose extent depends on a filesystem this evaluator does not read.
    require_scope(approval["approved_scope"], f"{context} scope")
    return approval


def instant(value: str, context: str) -> datetime:
    """Parse an RFC 3339 timestamp into a comparable instant.

    Strings do not order chronologically. ``2026-06-01T00:00:00Z`` sorts *after*
    ``2026-06-01T00:00:00.5Z`` because ``Z`` exceeds ``.``, so a still-valid approval
    evaluated half a second before its expiry was reported outside its window. Fractional
    seconds and offsets are equivalent forms of the same instant, and only parsing sees that.
    """

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise AuthorityError(f"{context} is not an RFC 3339 timestamp: {value!r}") from error
    if parsed.tzinfo is None:
        # A naive timestamp names no instant. Guessing a zone here is how two evaluators
        # come to disagree about the same approval.
        raise AuthorityError(f"{context} carries no timezone: {value!r}")
    return parsed


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
    # The validity window is compared against a supplied time, never a clock read -- two
    # evaluations of the same request must agree, and a clock makes that impossible
    # (``APPROVAL_CONTRACT.md`` §7). The three timestamps are *parsed* before comparison;
    # see :func:`instant` for why lexicographic ordering is not chronological ordering.
    now = instant(evaluation_time, "evaluation time")
    opened = instant(str(approval["approved_at"]), "approval approved_at")
    closes = instant(str(approval["expires_at"]), "approval expires_at")
    if not (opened <= now <= closes):
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
