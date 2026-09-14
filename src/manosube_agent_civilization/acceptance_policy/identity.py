"""Deterministic Acceptance Policy identities (FD-0004, Issue #80).

Canonical serialization has one owner in this repository -- ``state.canonicalize`` -- and this
module reads it rather than restating it, exactly as ``change/identity.py`` and
``authority/identity.py`` do. What is defined here is only *which payload* each record kind's
identity is computed over.
"""

from __future__ import annotations

import hashlib
from typing import Any

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

#: What an Acceptance Policy Clause *is*: its own closed structured fields, never the
#: ``statement``/``rationale`` prose those fields accompany as non-authoritative provenance.
CLAUSE_SEMANTIC_FIELDS: tuple[str, ...] = (
    "clause_id",
    "policy_class",
    "blocking_effect",
    "scope",
    "existed_in_original_contract",
)

#: What a Baseline *is*: which project/Issue it governs, where it was recorded, and its
#: complete, immutable, embedded clause set (FD4-C2 -- the original contract never changes
#: shape after genesis).
BASELINE_SEMANTIC_FIELDS: tuple[str, ...] = (
    "project_id",
    "governing_issue",
    "source_reference",
    "clauses",
)

#: P82-R1-F3: the baseline's own *identity* is deliberately narrower than its semantic
#: fingerprint -- a natural key over which work unit it is the genesis for, never its full
#: content. This is the same deliberate narrow-key exception ``multi_agent/identity.py``'s
#: own module docstring already documents for five of its six kinds: a narrow, natural-key id
#: is what makes "exactly one canonical genesis baseline per (project_id, governing_issue)" a
#: native Store behaviour rather than application-level bookkeeping. Two different baseline
#: bodies proposed for the identical work unit collide at the identical content-addressed
#: transaction id `route._commit_one_record` already derives from a record's own id, so the
#: Store's own manifest-identity check refuses the second one as a conflicting replay
#: (``ConflictingPolicyReplayError``) before any durable write -- no second schema, no second
#: locking primitive. The full content is still independently verified on every read via
#: :func:`baseline_semantic_fingerprint`, unchanged.
BASELINE_NATURAL_KEY_FIELDS: tuple[str, ...] = ("project_id", "governing_issue")

#: What a proposed Transition *is*: the exact operation on the exact clause, hash-linked to the
#: exact predecessor it extends, proposed by whom, from where, with what declared classification
#: -- deliberately excluding no lifecycle field, because a transition has none: it is either
#: this exact proposal or a different one, never the same proposal at a different "stage".
TRANSITION_SEMANTIC_FIELDS: tuple[str, ...] = (
    "project_id",
    "governing_issue",
    "baseline_ref",
    "clause_id",
    "policy_operation",
    "proposed_by",
    "prior_clause_binding",
    "proposed_clause",
    "declared_existed_in_original_contract",
    "policy_change_declared",
    "source_reference",
    "rollback_condition",
)

#: What an Adoption *is*: the exact SHUKOU decision binding one transition (or the baseline
#: genesis) into effect, from where, and when. ``decided_at`` is included -- unlike a Change's
#: excluded lifecycle timestamps -- because two textually-identical SHUKOU decisions recorded
#: at genuinely different times are two different Human acts, not the same one replayed.
#: P82-R2-F1: ``governance_adoption_record`` is part of the adoption's own identity -- two
#: adoptions that differ only in which real Governance Adoption Record backs them are two
#: different Human acts, never the same one replayed under a substituted record. P82-R3-F1:
#: ``project_binding_id`` is included too -- two adoptions differing only in which real
#: Project Binding's own trusted signing key vouches for them are likewise two different acts.
ADOPTION_SEMANTIC_FIELDS: tuple[str, ...] = (
    "project_id",
    "governing_issue",
    "adopted_ref",
    "decision_owner",
    "source_reference",
    "governance_adoption_record",
    "project_binding_id",
    "decided_at",
)

#: P82-R3-F1: the exact fields a genuine Human Authority signature over one Acceptance Policy
#: adoption must cover -- binding the signature to the precise policy target it authorizes
#: (``adopted_ref``, whose own content-addressed id already transitively binds the exact
#: policy operation/body identity of the baseline-or-transition it names), the exact work unit
#: (``governing_issue``), the exact project, the exact claimed decision_owner, and the exact
#: recorded comment/reviewed/authorized-target identity this adoption's own Governance
#: Adoption Record claims -- so a signature genuinely produced for one policy target can never
#: verify for a substituted one (a different ``adopted_ref``, a different work unit, or a
#: different claimed comment/head) even when the rest of the record is byte-identical.
GOVERNANCE_ADOPTION_AUTHORITY_SIGNING_FIELDS: tuple[str, ...] = (
    "project_id",
    "governing_issue",
    "adopted_ref",
    "decision_owner",
    "comment_url",
    "reviewed_sha",
    "authorized_target_sha",
)


def governance_adoption_authority_signing_payload(binding: dict[str, Any]) -> bytes:
    """The exact canonical bytes a genuine Human Authority signature over one Acceptance
    Policy adoption must cover -- see :data:`GOVERNANCE_ADOPTION_AUTHORITY_SIGNING_FIELDS`.
    *binding* is assembled by the verifier itself from already-validated fields (this
    adoption's own call arguments plus its own Governance Adoption Record's own declared
    ``comment_url``/``reviewed_sha``/``authorized_target_sha``), never a caller-supplied
    restatement of them."""

    return canonical_json_bytes(
        {field: binding[field] for field in GOVERNANCE_ADOPTION_AUTHORITY_SIGNING_FIELDS}
    )


#: What a derived Effective View *is*: the resolved snapshot itself, plus exactly which
#: Adoptions were folded to produce it -- so two views computed from a differently-ordered or
#: differently-scoped Adoption set are provably different, and a replay that folds the identical
#: Adoption set in the identical order is provably the same view (FD4-C9's replay-determinism
#: requirement).
EFFECTIVE_VIEW_SEMANTIC_FIELDS: tuple[str, ...] = (
    "project_id",
    "governing_issue",
    "baseline_ref",
    "effective_clauses",
    "folded_adoption_refs",
)

#: What an Impact Preview *is*: the exact before/after/blocker-delta projection a candidate
#: transition would produce, bound to the work units it names.
IMPACT_PREVIEW_SEMANTIC_FIELDS: tuple[str, ...] = (
    "project_id",
    "governing_issue",
    "before_policy",
    "proposed_change",
    "after_policy",
    "new_blockers",
    "removed_blockers",
    "affected_work_units",
    "rollback_condition",
)


def _semantic_projection(body: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: body[field] for field in fields}


def _semantic_fingerprint(body: dict[str, Any], fields: tuple[str, ...]) -> str:
    return (
        "sha256:"
        + hashlib.sha256(canonical_json_bytes(_semantic_projection(body, fields))).hexdigest()
    )


def _record_id(body: dict[str, Any], fields: tuple[str, ...], prefix: str) -> str:
    return (
        prefix
        + hashlib.sha256(canonical_json_bytes(_semantic_projection(body, fields)))
        .hexdigest()
        .upper()
    )


def baseline_semantic_fingerprint(baseline: dict[str, Any]) -> str:
    return _semantic_fingerprint(baseline, BASELINE_SEMANTIC_FIELDS)


def baseline_id(baseline: dict[str, Any]) -> str:
    return _record_id(baseline, BASELINE_NATURAL_KEY_FIELDS, "AP-BASE-")


def transition_semantic_fingerprint(transition: dict[str, Any]) -> str:
    return _semantic_fingerprint(transition, TRANSITION_SEMANTIC_FIELDS)


def transition_id(transition: dict[str, Any]) -> str:
    return _record_id(transition, TRANSITION_SEMANTIC_FIELDS, "AP-TRANS-")


def adoption_semantic_fingerprint(adoption: dict[str, Any]) -> str:
    return _semantic_fingerprint(adoption, ADOPTION_SEMANTIC_FIELDS)


def adoption_id(adoption: dict[str, Any]) -> str:
    return _record_id(adoption, ADOPTION_SEMANTIC_FIELDS, "AP-ADOPT-")


def effective_view_semantic_fingerprint(view: dict[str, Any]) -> str:
    return _semantic_fingerprint(view, EFFECTIVE_VIEW_SEMANTIC_FIELDS)


def impact_preview_semantic_fingerprint(preview: dict[str, Any]) -> str:
    return _semantic_fingerprint(preview, IMPACT_PREVIEW_SEMANTIC_FIELDS)
