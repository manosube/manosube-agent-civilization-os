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

from .conformance import admit, stored_instant, transient_instant
from .scope import is_contained, require_scope

ACTIVE = "ACTIVE"
REVOKED = "REVOKED"
EXPIRED = "EXPIRED"
APPROVAL_STATUSES: frozenset[str] = frozenset({ACTIVE, REVOKED, EXPIRED})

def refine_approval(approval: dict[str, Any], context: str) -> None:
    """What an approval must satisfy beyond admission.

    Admission is the shared gate, not a local copy of it. The local copy is what let a
    record whose ``approved_by`` was merely ``{"kind": "human_authority"}`` -- no approver
    identity at all -- lower a decision to ``AUTONOMOUS``.
    """

    # The schema fixes the scope's *shape*; only this fixes that its members are enumerated
    # locations rather than expressions. An approval covering ``src/*`` would be an approval
    # whose extent depends on a filesystem this evaluator does not read.
    require_scope(approval["approved_scope"], f"{context} scope")


def require_approval(value: Any, context: str) -> dict[str, Any]:
    """Return *value* once it is a canonical approval; reject it otherwise."""

    approval = admit(value, "approval", context)
    refine_approval(approval, context)
    return approval


def binding_mismatches(
    approval: dict[str, Any],
    *,
    project_id: str,
    difference_id: str,
    change_intent: str,
    action_fingerprint: str,
    requested_scope: dict[str, Any],
    state_revision: int,
    state_fingerprint: dict[str, Any],
    evaluation_time: str,
) -> list[str]:
    """Return every way this approval fails to *bind* this request; empty means it binds.

    Binding and exclusion are different questions, and folding them together is what let an
    exclusion be skipped entirely: an approval that binds this request and excludes this
    action was classified "unusable", so when a rule already granted ``AUTONOMOUS`` the
    approval was never consulted and its exclusion never applied. An approval may narrow
    authority even where another rule permits (``APPROVAL_CONTRACT.md`` §6), so *whether it
    binds* is answered here and *what it excludes* is answered by :func:`excludes_action`.

    Every binding is checked, not the first failing one, so a human re-approving sees the
    whole gap rather than discovering it one round at a time.
    """

    reasons: list[str] = []
    if approval["status"] != ACTIVE:
        reasons.append(f"APPROVAL_{approval['status']}")
    # The validity window is compared against a supplied time, never a clock read -- two
    # evaluations of the same request must agree, and a clock makes that impossible
    # (``APPROVAL_CONTRACT.md`` §7). The three timestamps are *parsed* before comparison;
    # see :func:`stored_instant` for why lexicographic ordering is not chronological ordering.
    # The window's own bounds are stored fields of this record and are admitted as such; the
    # evaluation time is supplied, so it is admitted by the transient grammar. Comparing them
    # is exact at every precision -- ``Instant`` never truncates a fraction.
    now = transient_instant(evaluation_time, "evaluation time")
    opened = stored_instant(str(approval["approved_at"]), "approval approved_at")
    closes = stored_instant(str(approval["expires_at"]), "approval expires_at")
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
    return sorted(reasons)


def excludes_action(approval: dict[str, Any], action_kind: str) -> bool:
    """Whether this approval explicitly withholds *action_kind*.

    An approval may narrow itself and may never widen (``APPROVAL_CONTRACT.md`` §6), so this
    is asked of every approval that *binds* the request -- independently of what any rule
    decided. A narrowing that only applies when a rule already required approval is not a
    narrowing; it is a coincidence.
    """

    return action_kind in approval["prohibited_actions"]
