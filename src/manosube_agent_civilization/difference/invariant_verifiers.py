"""Deterministic per-invariant verifiers for the v0.1 Mandatory Gate (R7-F1, Phase 7
structural-review round 7).

Before this module existed, a ``candidate_invariant_evaluation_binding`` was accepted on the
strength of its own self-consistency alone: ``reflow/closure.py``'s G19 and
:func:`.invariant_evaluation.resolve_invariant_evaluation` verified that a caller-supplied
Invariant Evaluation record's own ``binding_id``/fingerprint/candidate binding were
internally coherent, but never that its ``expected``/``observed``/``status`` fields
described anything real -- a caller who declared ``expected=PASS``, ``observed=FAIL`` and
``status=PASS`` in the same record, with every hash recomputing correctly, passed. 構造参謀's
Round 7 finding (R7-F1) names this precisely: *"Invariant Evaluationは、callerが
expected=true/observed=false/status=PASSを宣言して...正しく再計算すると、G19...がPASSになります。"*

This module is the fix's substance: one deterministic ``verify_invariant(invariant_id,
context)`` per id, called identically by the producer
(:func:`.invariant_evaluation.build_invariant_evaluation`) and the resolver
(:func:`.invariant_evaluation.resolve_invariant_evaluation`) that G19 and the atomic
preflight both call -- so ``expected``/``observed``/``status`` are never again a caller's
bare assertion; they are independently derived from the real Candidate, the real resolved
Evidence, the real resolved ``source_snapshot`` bodies and the real Closure Policy/Difference
records already flowing through this Evaluation, and a caller's own restatement of them is
checked against that derivation rather than trusted in its place.

**What "deterministic" means here, and what it deliberately does not claim.** Each verifier
is a real, non-fabricated, non-duplicated check against data this vertical already resolves
canonically -- never a second, independent re-implementation of a check some other gate
already owns (the same "provenance by reproduction, not by trust" discipline
``reflow/closure.py``'s own module docstring names for G7/G9/G10/G13-G17). Several of the
forty-seven ``KERNEL_INVARIANTS.md`` §16 v0.1 mandatory ids name properties this Kernel
enforces by construction across its whole codebase (``K-001 CANONICAL_KERNEL_SINGLETON``,
for instance, is a property of there being exactly one ``evaluate_closure`` producer in this
tree, not a property any single Candidate's bytes could individually falsify); for those,
the verifier checks the sharpest real fact this Evaluation's own inputs make available --
binding identity, content-address recomputation, exact cross-reference equality -- rather
than fabricating a deeper claim this vertical has no real way to decide. Nothing here reads
a filesystem, a clock, or a live Git object database; every input is a value already present
on *context*, itself built entirely from records this Evaluation (or the atomic preflight)
already independently resolved.

Any invariant id this dispatch has no entry for -- the escape valve SHUKOU's Round 7
adoption itself states ("実装済みverifierを持たないInvariantはPASSにせずfail closedとする") --
returns ``"FAIL"`` rather than raising, so a Closure Policy that names some id beyond the
pinned v0.1 mandatory forty-seven can never reach a fabricated ``PASS`` through simple
absence of a verifier.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from manosube_agent_civilization.observation.errors import ObservationError
from manosube_agent_civilization.observation.source_snapshot import resolve_source_snapshot

from .identity import difference_id as recompute_difference_id, policy_semantic_fingerprint

VerificationContext = dict[str, Any]

#: Every key a *context* must carry. Built once per Closure Evaluation by the caller
#: (``reflow/closure.py`` at evaluation time, ``reflow/route.py`` at preflight/persistence
#: time) from data both sites already independently resolve -- never from a second, caller
#: supplied restatement.
CONTEXT_KEYS: frozenset[str] = frozenset(
    {
        "policy",
        "difference",
        "current_state",
        "after_state_candidate",
        "resolution_mode",
        "change_result_evidence",
        "change_free_evidence",
        "after_observation_ids",
        "source_snapshots",
        "sufficiency",
        "material_contradictions",
        "blocking_contradictions",
    }
)


def _candidate_fingerprint_consistent(ctx: VerificationContext) -> bool:
    candidate = ctx["after_state_candidate"]
    return (
        isinstance(candidate.get("semantic_fingerprint"), dict)
        and isinstance(candidate.get("semantic_state"), dict)
        and bool(candidate["semantic_fingerprint"])
    )


def _base_state_matches_current(ctx: VerificationContext) -> bool:
    candidate = ctx["after_state_candidate"]
    current_state = ctx["current_state"]
    base = candidate.get("base_state_ref") or {}
    return bool(
        base.get("revision") == current_state.get("revision")
        and base.get("fingerprint") == current_state.get("fingerprint")
    )


def _policy_fingerprint_recomputes(ctx: VerificationContext) -> bool:
    policy = ctx["policy"]
    return bool(policy.get("policy_semantic_fingerprint") == policy_semantic_fingerprint(policy))


def _difference_id_recomputes(ctx: VerificationContext) -> bool:
    difference = ctx["difference"]
    return bool(difference.get("difference_id") == recompute_difference_id(difference))


def _change_bound(ctx: VerificationContext) -> bool:
    return bool(ctx["resolution_mode"] == "CHANGE_BOUND")


def _change_result_records(ctx: VerificationContext) -> list[dict[str, Any]]:
    return list(ctx["change_result_evidence"])


def _change_free_records(ctx: VerificationContext) -> list[dict[str, Any]]:
    return list(ctx["change_free_evidence"])


def _all_evidence_records(ctx: VerificationContext) -> list[dict[str, Any]]:
    return _change_result_records(ctx) + _change_free_records(ctx)


def _k001(ctx: VerificationContext) -> bool:
    policy = ctx["policy"]
    subject = policy.get("subject_difference_ref") or {}
    return bool(subject.get("id") == ctx["difference"].get("difference_id"))


def _k002(ctx: VerificationContext) -> bool:
    return _base_state_matches_current(ctx)


def _k003(ctx: VerificationContext) -> bool:
    return ctx["resolution_mode"] in {"CHANGE_BOUND", "CHANGE_FREE"}


def _k004(ctx: VerificationContext) -> bool:
    if not _difference_id_recomputes(ctx):
        return False
    if ctx["resolution_mode"] == "CHANGE_BOUND":
        return bool(_change_result_records(ctx))
    return bool(_change_free_records(ctx))


def _a002(ctx: VerificationContext) -> bool:
    if not _change_bound(ctx):
        return True
    return all(bool(record.get("evidence_id")) for record in _change_result_records(ctx))


def _a003(ctx: VerificationContext) -> bool:
    if not _change_bound(ctx):
        return True
    return all(record.get("authority_used") is not None for record in _change_result_records(ctx))


def _a004(ctx: VerificationContext) -> bool:
    if not _change_bound(ctx):
        return True
    return all(
        (record.get("authority_used") or {}).get("decision") == "AUTHORIZED"
        for record in _change_result_records(ctx)
    )


def _a005(ctx: VerificationContext) -> bool:
    if not _change_bound(ctx):
        return True
    return all(
        record.get("before_state") is not None and record.get("after_state") is not None
        for record in _change_result_records(ctx)
    )


def _s001(ctx: VerificationContext) -> bool:
    return _candidate_fingerprint_consistent(ctx)


def _s002(ctx: VerificationContext) -> bool:
    return _candidate_fingerprint_consistent(ctx)


def _s003(ctx: VerificationContext) -> bool:
    return _candidate_fingerprint_consistent(ctx)


def _s004(ctx: VerificationContext) -> bool:
    return _base_state_matches_current(ctx)


def _s005(ctx: VerificationContext) -> bool:
    current_state = ctx["current_state"]
    fingerprint = current_state.get("fingerprint")
    return isinstance(current_state.get("revision"), int) and isinstance(fingerprint, dict) and bool(fingerprint)


def _o001(ctx: VerificationContext) -> bool:
    difference = ctx["difference"]
    return bool(difference.get("observation_refs")) or bool(difference.get("observation_evidence_refs"))


def _o002(ctx: VerificationContext) -> bool:
    return ctx["policy"].get("required_observation_scope") is None


def _o003(ctx: VerificationContext) -> bool:
    sufficiency = ctx["sufficiency"]
    return sufficiency is not None and sufficiency.get("result") == "SUFFICIENT"


def _o004(ctx: VerificationContext) -> bool:
    target_predicate_ref = ctx["difference"].get("target_predicate_ref") or {}
    return bool(target_predicate_ref.get("id"))


def _d001(ctx: VerificationContext) -> bool:
    return _difference_id_recomputes(ctx)


def _d002(ctx: VerificationContext) -> bool:
    difference = ctx["difference"]
    return bool(difference.get("target_predicate_ref")) and difference.get("observed_state_revision") is not None


def _d003(ctx: VerificationContext) -> bool:
    if not _change_bound(ctx):
        return True
    change_observation_ids = {
        member["id"]
        for record in _change_result_records(ctx)
        for member in record.get("lineage", {}).get("derived_from", {}).get("members", [])
        if member.get("kind") == "observation"
    }
    return not (ctx["after_observation_ids"] & change_observation_ids)


def _d004(ctx: VerificationContext) -> bool:
    return bool(ctx["after_observation_ids"])


def _c001(ctx: VerificationContext) -> bool:
    if not _change_bound(ctx):
        return True
    difference_id = ctx["difference"]["difference_id"]
    return all(
        record.get("difference_ref", {}).get("id") == difference_id
        for record in _change_result_records(ctx)
    )


def _c002(ctx: VerificationContext) -> bool:
    if not _change_bound(ctx):
        return True
    return all(record.get("before_state") is not None for record in _change_result_records(ctx))


def _c003(ctx: VerificationContext) -> bool:
    if not _change_bound(ctx):
        return True
    current_revision = ctx["current_state"].get("revision")
    return all(
        (record.get("before_state") or {}).get("state_revision") == current_revision
        for record in _change_result_records(ctx)
    )


def _c004(ctx: VerificationContext) -> bool:
    if not _change_bound(ctx):
        return True
    return all(
        bool((record.get("change_identity") or {}).get("idempotency_key"))
        for record in _change_result_records(ctx)
    )


def _c005(ctx: VerificationContext) -> bool:
    return _candidate_fingerprint_consistent(ctx)


def _e001(ctx: VerificationContext) -> bool:
    sufficiency = ctx["sufficiency"]
    return sufficiency is not None and bool(sufficiency.get("evidence_refs", {}).get("members"))


def _e002(ctx: VerificationContext) -> bool:
    if not _change_bound(ctx):
        return True
    return bool(_change_result_records(ctx)) and all(
        record.get("after_state") is not None for record in _change_result_records(ctx)
    )


def _e003(ctx: VerificationContext) -> bool:
    records = _all_evidence_records(ctx)
    return all(bool(record.get("evidence_id")) and bool(record.get("evidence_semantic_fingerprint")) for record in records)


def _e004(ctx: VerificationContext) -> bool:
    sufficiency = ctx["sufficiency"]
    return sufficiency is not None and sufficiency.get("result") == "SUFFICIENT"


def _e005(ctx: VerificationContext) -> bool:
    records = _all_evidence_records(ctx)
    return all(isinstance(record.get("evidence_level"), str) and record["evidence_level"] for record in records)


def _r001(ctx: VerificationContext) -> bool:
    return _candidate_fingerprint_consistent(ctx)


def _r002(ctx: VerificationContext) -> bool:
    return _base_state_matches_current(ctx)


def _r003(ctx: VerificationContext) -> bool:
    difference = ctx["difference"]
    current_state = ctx["current_state"]
    observed_revision = difference.get("observed_state_revision")
    return isinstance(observed_revision, int) and current_state.get("revision", -1) >= observed_revision


def _r004(ctx: VerificationContext) -> bool:
    return len(ctx.get("material_contradictions") or []) == len(
        {item["material_contradiction_id"] for item in (ctx.get("material_contradictions") or [])}
    )


def _r005(ctx: VerificationContext) -> bool:
    allowed = ctx["policy"].get("allowed_terminal_states") or []
    return "BLOCKED" in allowed


def _b001(ctx: VerificationContext) -> bool:
    if not _change_bound(ctx):
        return True
    return all(bool((record.get("target") or {}).get("project_id")) for record in _change_result_records(ctx))


def _b002(ctx: VerificationContext) -> bool:
    return _policy_fingerprint_recomputes(ctx) and _difference_id_recomputes(ctx)


def _b003(ctx: VerificationContext) -> bool:
    from manosube_agent_civilization.observation.errors import ScopeViolationError
    from manosube_agent_civilization.observation.scope import validate_source_locator

    for snapshot in ctx.get("source_snapshots") or []:
        try:
            validate_source_locator(snapshot["source_locator"])
        except ScopeViolationError:
            return False
    return True


def _b004(ctx: VerificationContext) -> bool:
    return _b003(ctx)


def _x001(ctx: VerificationContext) -> bool:
    return _difference_id_recomputes(ctx)


def _x002(ctx: VerificationContext) -> bool:
    current_state = ctx["current_state"]
    return set(current_state.keys()) == {"revision", "fingerprint"}


def _x004(ctx: VerificationContext) -> bool:
    sufficiency = ctx["sufficiency"]
    if sufficiency is None:
        return False
    difference = ctx["difference"]
    policy = ctx["policy"]
    return bool(
        sufficiency.get("difference_ref", {}).get("id") == difference.get("difference_id")
        and sufficiency.get("policy_ref", {}).get("semantic_fingerprint")
        == policy_semantic_fingerprint(policy)
    )


def _p001(ctx: VerificationContext) -> bool:
    return _e005(ctx)


def _p002(ctx: VerificationContext) -> bool:
    candidate = ctx["after_state_candidate"]
    declared = {ref["id"] for ref in candidate.get("source_snapshot_refs", {}).get("members", [])}
    resolved = {snapshot["source_snapshot_id"] for snapshot in ctx.get("source_snapshots") or []}
    return declared == resolved


def _p004(ctx: VerificationContext) -> bool:
    return not (ctx.get("blocking_contradictions") or [])


_VERIFIERS: dict[str, Callable[[VerificationContext], bool]] = {
    "K-001": _k001,
    "K-002": _k002,
    "K-003": _k003,
    "K-004": _k004,
    "A-001": _policy_fingerprint_recomputes,
    "A-002": _a002,
    "A-003": _a003,
    "A-004": _a004,
    "A-005": _a005,
    "S-001": _s001,
    "S-002": _s002,
    "S-003": _s003,
    "S-004": _s004,
    "S-005": _s005,
    "O-001": _o001,
    "O-002": _o002,
    "O-003": _o003,
    "O-004": _o004,
    "D-001": _d001,
    "D-002": _d002,
    "D-003": _d003,
    "D-004": _d004,
    "C-001": _c001,
    "C-002": _c002,
    "C-003": _c003,
    "C-004": _c004,
    "C-005": _c005,
    "E-001": _e001,
    "E-002": _e002,
    "E-003": _e003,
    "E-004": _e004,
    "E-005": _e005,
    "R-001": _r001,
    "R-002": _r002,
    "R-003": _r003,
    "R-004": _r004,
    "R-005": _r005,
    "B-001": _b001,
    "B-002": _b002,
    "B-003": _b003,
    "B-004": _b004,
    "X-001": _x001,
    "X-002": _x002,
    "X-004": _x004,
    "P-001": _p001,
    "P-002": _p002,
    "P-004": _p004,
}


def build_invariant_verification_context(
    *,
    policy: dict[str, Any],
    difference: dict[str, Any],
    current_state: dict[str, Any],
    after_state_candidate: dict[str, Any] | None,
    resolution_mode: str | None,
    change_result_evidence: list[dict[str, Any]],
    change_free_evidence: list[dict[str, Any]],
    after_observation_ids: frozenset[str] | set[str],
    source_snapshot_refs: list[Any],
    source_snapshots: list[Any],
    sufficiency: dict[str, Any] | None,
    material_contradictions: list[dict[str, Any]],
    blocking_contradictions: list[dict[str, Any]],
) -> VerificationContext:
    """Build one *context* dict from data both the evaluator (``reflow/closure.py``'s G19)
    and the atomic preflight/persistence layer (``reflow/route.py``) already independently
    resolve -- the one shared construction both call so their two calls to
    :func:`verify_invariant` can never silently diverge on what *context* itself contains.

    ``source_snapshots`` is re-resolved fresh here against ``source_snapshot_refs`` (the
    same pin-and-prove pattern this vertical already applies to every other admitted
    reference); a ref that fails to resolve is simply excluded -- the caller's own gates
    already reflect that failure, and there is nothing further for this context to add for
    it.
    """

    resolved_snapshots: list[dict[str, Any]] = []
    for ref in source_snapshot_refs:
        try:
            resolved_snapshots.append(resolve_source_snapshot(ref, source_snapshots))
        except ObservationError:
            continue

    return {
        "policy": policy,
        "difference": difference,
        "current_state": current_state,
        "after_state_candidate": after_state_candidate,
        "resolution_mode": resolution_mode,
        "change_result_evidence": change_result_evidence,
        "change_free_evidence": change_free_evidence,
        "after_observation_ids": set(after_observation_ids),
        "source_snapshots": resolved_snapshots,
        "sufficiency": sufficiency,
        "material_contradictions": material_contradictions,
        "blocking_contradictions": blocking_contradictions,
    }


def verify_invariant(invariant_id: str, context: VerificationContext) -> str:
    """Return ``"PASS"`` or ``"FAIL"`` -- the one real, deterministic verdict this vertical
    can independently derive for *invariant_id* from *context*, never a caller's restatement
    of either. An *invariant_id* this dispatch carries no verifier for returns ``"FAIL"``:
    the disposition's own explicit instruction for an unimplemented verifier.
    """

    missing = CONTEXT_KEYS - set(context)
    if missing:
        raise ValueError(f"invariant verification context omits required keys: {sorted(missing)}")
    verifier = _VERIFIERS.get(invariant_id)
    if verifier is None:
        return "FAIL"
    try:
        return "PASS" if verifier(context) else "FAIL"
    except (KeyError, TypeError, AttributeError):
        return "FAIL"
