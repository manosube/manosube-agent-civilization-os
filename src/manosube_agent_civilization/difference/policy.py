"""The Closure Policy semantic conformance authority.

A Closure Policy is the only carried record that stores a digest of *its own content*.
Every other carried type either has no self-derived digest, or its digest is an input from
an element this phase does not own. That difference matters: a stored self-derived digest
is only worth what recomputing it proves, and until this module existed nothing recomputed
it. ``_policy_identity`` read ``policy_semantic_fingerprint`` straight off the record and
derived the Closure Policy ID from it, so a caller who altered a required Claim while
keeping the stored digest kept the ID as well -- the record recomputed, and the typed
boundary accepted it. The whole-bundle relational pass would have caught it, but only for a
Policy some lifecycle Evaluation cites; a carried Policy that nothing cites reached the
returned bundle untouched.

The independent contract validator held the required-Claim rule and the Engine did not,
which is exactly the auditor-only rule the contract forbids. Both now read this module, so
the producer cannot emit what the auditor rejects.

Two rules live here, and they are different in kind:

``closure_policy_semantic_errors``
    decides one Policy from its own content: the stored Policy digest and every embedded
    Claim identity and digest must recompute.

``reopen_condition_provenance_errors``
    is relational: ``CLOSURE_POLICY.md`` requires each reopen condition's predicate ID,
    Objective revision *and* fingerprint to resolve exactly, so the named predicate must
    really exist in the referenced Objective revision carrying the declared semantics.
    Reference closure alone proves only that the Objective revision is present.
"""

from __future__ import annotations

from typing import Any

from .canonical import canonical_bytes, has_recursive_set_duplicate
from .identity import (
    completion_claim_fingerprint,
    completion_claim_id,
    policy_semantic_fingerprint,
    target_predicate_fingerprint,
)

#: The closed Claim descriptor the digest is computed over, per ``CLOSURE_POLICY.md``.
CLAIM_SEMANTIC_FIELDS: tuple[str, ...] = (
    "subject_type",
    "subject_ref",
    "claim",
    "target_state_ref",
)


def _claim_errors(policy: dict[str, Any], where: str) -> list[str]:
    errors: list[str] = []
    seen: dict[str, bytes] = {}
    for claim in policy.get("required_claims", []) or []:
        if not isinstance(claim, dict):
            errors.append(f"required Claim is not an object: {where}")
            continue
        try:
            descriptor = {key: claim[key] for key in CLAIM_SEMANTIC_FIELDS}
        except KeyError as missing:
            errors.append(f"required Claim omits {missing.args[0]}: {where}")
            continue
        identity = claim.get("id")
        if claim.get("claim_semantic_fingerprint") != completion_claim_fingerprint(descriptor):
            errors.append(f"required Claim fingerprint does not recompute: {where}.{identity}")
        if identity != completion_claim_id(descriptor):
            errors.append(f"required Claim identity does not recompute: {where}.{identity}")
        if has_recursive_set_duplicate(descriptor):
            errors.append(f"required Claim carries a duplicate set member: {where}.{identity}")
        payload = canonical_bytes(claim)
        if isinstance(identity, str):
            previous = seen.get(identity)
            if previous is not None and previous != payload:
                errors.append(
                    f"required Claim identity carries two payloads: {where}.{identity}"
                )
            seen[identity] = payload
    return errors


def closure_policy_semantic_errors(policy: dict[str, Any], where: str) -> list[str]:
    """Return every way *policy* fails to recompute from its own content.

    The Policy digest is recomputed first: it is the value the Closure Policy ID is derived
    from, so trusting it as stored is what let a forged Policy keep its identity.

    Both callers -- the typed conformance gate and the independent validator -- have already
    established that *policy* is an object, so this reads it as one; every field *inside* it
    is read totally, because a record can be an object and still be incomplete.
    """

    errors = _claim_errors(policy, where)
    try:
        recomputed = policy_semantic_fingerprint(policy)
    except (KeyError, TypeError):
        return [*errors, f"Closure Policy is not complete enough to recompute: {where}"]
    if policy.get("policy_semantic_fingerprint") != recomputed:
        errors.append(f"Closure Policy fingerprint does not recompute: {where}")
    return errors


def reopen_condition_provenance_errors(
    policy: dict[str, Any], objective_revisions: dict[str, dict[str, Any]]
) -> list[str]:
    """Return every reopen condition that does not resolve against its Objective revision.

    *objective_revisions* is the bundle's own Objective revision index. A condition whose
    revision is absent is already reported by the reference closure gate, so it is not
    re-reported here; what this adds is the predicate itself -- present, and carrying the
    exact semantics the condition declares.
    """

    where = policy.get("closure_policy_id")
    errors: list[str] = []
    for condition in policy.get("reopen_conditions", []) or []:
        if not isinstance(condition, dict):
            continue
        reference = condition.get("objective_revision_ref")
        identity = reference.get("id") if isinstance(reference, dict) else None
        revision = objective_revisions.get(identity) if isinstance(identity, str) else None
        if revision is None:
            continue
        predicates = {
            predicate["predicate_id"]: predicate
            for predicate in revision.get("target_predicates", []) or []
            if isinstance(predicate, dict) and isinstance(predicate.get("predicate_id"), str)
        }
        predicate = predicates.get(condition.get("id"))
        if predicate is None:
            errors.append(
                "reopen condition names no predicate of its Objective revision: "
                f"{where}.reopen_conditions[{condition.get('id')}] -> {identity}"
            )
            continue
        if condition.get("predicate_semantic_fingerprint") != target_predicate_fingerprint(
            predicate
        ):
            errors.append(
                "reopen condition predicate fingerprint does not recompute: "
                f"{where}.reopen_conditions[{condition.get('id')}] -> {identity}"
            )
    return errors
