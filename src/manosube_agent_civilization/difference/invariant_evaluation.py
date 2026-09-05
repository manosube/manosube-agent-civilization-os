"""Canonical Invariant Evaluation resolution -- owned by Difference (R4-F2, Phase 7
structural-review round 4).

``01_SCHEMA/difference/invariant_evaluation.schema.json`` exists in full, and
``CLOSURE_POLICY.md`` gives a complete ``MANOSUBE-RESOLVED-EVALUATION-RECORD-SHA256-0.1``
fingerprint profile for it (lines 611-622), shared with Completion Record. What
``CLOSURE_POLICY.md`` never states, unlike Completion Record's ``completion_id`` (line
672), is a content-address formula for ``evaluation_id`` itself -- round 3 of this
vertical's structural review escalated this exact gap rather than let it be silently
filled in, and round 4's adopted disposition settles it:
``INVARIANT_EVALUATION_ID_POLICY=CALLER_ASSIGNED_EXACT_LOOKUP_AND_RECOMPUTED_FINGERPRINT``.
``evaluation_id`` is a caller-assigned identifier, resolved by exact lookup in a
caller-supplied pool of full record bodies (the same "caller supplies the pool, this
vertical validates and persists it" pattern :mod:`~manosube_agent_civilization.reflow.claims`
already uses for ``candidate_claim_evaluation_event``), never independently re-derived from
content. What *is* independently verified is everything the frozen contract does specify:
the record's own schema, its recomputed fingerprint against the binding's declared
``evaluation_record_fingerprint``, and every field the binding itself asserts about the
underlying record.

**R6-F3 (Phase 7 structural-review round 6).** ``state_revision``/``state_fingerprint`` bind
a record to the base State it was evaluated against, but nothing before this bound it to the
specific after-state Candidate a real invariant application must have run over -- two
Candidates proposing wildly different semantic content from the same base State produced,
and could each accept, the identical record. ``candidate_id``/``candidate_semantic_fingerprint``
are added to the schema and checked here against the real ``after_state_candidate`` for
exactly this reason. They are deliberately *not* added to ``INVARIANT_EVALUATION_SCALARS``:
that list is ``CLOSURE_POLICY.md`` §3's frozen ``MANOSUBE-RESOLVED-EVALUATION-RECORD-
SHA256-0.1`` profile, and widening it would silently change every Invariant Evaluation's own
fingerprint domain out from under a contract that names the scalar list exactly. The same
precedent already exists on Completion Record's ``reflow_transition_ref``: present in the
schema, excluded from the closed projection, checked by its own field equality instead.

**R7-F1 (Phase 7 structural-review round 7).** Every check above verifies a record's own
*internal* self-consistency -- its fingerprint, its candidate binding, its State binding --
but none of it verified that the record's ``expected``/``observed``/``status`` actually
described anything real: a caller who declared ``status="PASS"`` with a correctly
recomputed fingerprint and binding passed regardless of what ``expected``/``observed``
said. :func:`resolve_invariant_evaluation` now also takes a *verification_context*
(:mod:`.invariant_verifiers`) and independently re-derives ``status`` via
:func:`~.invariant_verifiers.verify_invariant` -- the same function
:func:`build_invariant_evaluation` calls to produce a record in the first place -- and
requires the resolved record's own ``expected``/``observed``/``status``/``method``/
``remaining_differences``/``evidence_refs`` to equal exactly what that independent
derivation produces, not merely be internally coherent. A caller can no longer assemble a
self-consistent ``PASS`` record for an invariant the real verifier does not independently
confirm.
"""

from __future__ import annotations

import hashlib
from typing import Any

from .canonical import canonical_bytes, unordered_set
from .errors import DifferenceError
from .invariant_verifiers import VerificationContext, verify_invariant
from .validation import validate_record

_INVARIANT_EVALUATION_FINGERPRINT_DOMAIN = b"MANOSUBE:INVARIANT_EVALUATION:0.1:"

#: ``INVARIANT_EVALUATION_SCALARS``, CLOSURE_POLICY.md line 611-614.
INVARIANT_EVALUATION_SCALARS: tuple[str, ...] = (
    "evaluation_id",
    "invariant_id",
    "subject_ref",
    "state_revision",
    "state_fingerprint",
    "verification_stage",
    "method",
    "expected",
    "observed",
    "status",
    "evaluated_at",
    "evaluator_capability",
    "authority_ref",
)
#: ``INVARIANT_EVALUATION_UNORDERED_SETS``, CLOSURE_POLICY.md line 616-617.
INVARIANT_EVALUATION_UNORDERED_SET_FIELDS: tuple[str, ...] = (
    "evidence_refs",
    "remaining_differences",
)


def _invariant_evaluation_closed_projection(record: dict[str, Any]) -> dict[str, Any]:
    projection: dict[str, Any] = {key: record[key] for key in INVARIANT_EVALUATION_SCALARS}
    for key in INVARIANT_EVALUATION_UNORDERED_SET_FIELDS:
        projection[key] = unordered_set(record[key]["members"])
    return projection


def invariant_evaluation_fingerprint(record: dict[str, Any]) -> str:
    """Return ``MANOSUBE-RESOLVED-EVALUATION-RECORD-SHA256-0.1``'s digest for one Invariant
    Evaluation record -- domain-separated from :func:`.completion.completion_record_fingerprint`
    by its own record-kind domain bytes even though both share the same closed-projection
    profile shape.
    """

    digest = hashlib.sha256(
        _INVARIANT_EVALUATION_FINGERPRINT_DOMAIN
        + canonical_bytes(_invariant_evaluation_closed_projection(record))
    ).hexdigest()
    return "sha256:" + digest


#: The one fixed ``method`` and empty ``evidence_refs``/``remaining_differences`` every R7-F1
#: verifier produces -- see :func:`build_invariant_evaluation`'s own docstring for why these
#: are fixed constants rather than caller-suppliable values.
STRUCTURAL_CHECK_METHOD = "STRUCTURAL_CHECK"


def _expected_fields(
    invariant_id: str, context: VerificationContext
) -> tuple[str, dict[str, Any], dict[str, Any], list[dict[str, str]]]:
    """Return ``(status, expected, observed, evidence_refs)`` -- the one real,
    independently-derived verdict :func:`~.invariant_verifiers.verify_invariant` computes
    for *invariant_id* from *context*, projected into the record shape
    ``KERNEL_INVARIANTS.md`` §17 fixes. ``evidence_refs`` (R8-F1 item 4) is the real,
    already Difference/State/Candidate-bound Evidence reference set that genuinely grounds
    a ``PASS`` -- never a caller-suppliable, always-empty placeholder.
    """

    status, evidence_refs = verify_invariant(invariant_id, context)
    expected = {"invariant_id": invariant_id, "result": "PASS"}
    observed = {"invariant_id": invariant_id, "result": status}
    return status, expected, observed, evidence_refs


def build_invariant_evaluation(
    invariant_id: str,
    context: VerificationContext,
    *,
    evaluation_id: str,
    subject_ref: dict[str, Any],
    state_revision: int,
    state_fingerprint: dict[str, Any],
    candidate_id: str,
    candidate_semantic_fingerprint: dict[str, Any],
    verification_stage: str,
    evaluated_at: str,
    evaluator_capability: str | None = None,
    authority_ref: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return one canonical, schema-valid Invariant Evaluation record for *invariant_id*
    (R7-F1) -- the producer :func:`resolve_invariant_evaluation` itself now demands every
    resolved record agree with.

    ``expected``/``observed``/``status``/``method``/``evidence_refs``/
    ``remaining_differences`` are never parameters here: they are exactly what
    :func:`~.invariant_verifiers.verify_invariant` independently derives from *context*,
    the same real Candidate/Evidence/Policy/Difference data already flowing through this
    Evaluation -- not a caller's restatement of them (``evidence_refs`` real and non-empty
    per R8-F1 item 4 wherever a real resolved Evidence record actually grounds the
    verdict; ``remaining_differences`` stays empty -- this vertical produces no such
    record for any invariant). ``evaluation_id`` stays caller-assigned (R4-F2's
    ``INVARIANT_EVALUATION_ID_POLICY``; no content-address formula for it exists in
    ``CLOSURE_POLICY.md``), and ``method`` is fixed to :data:`STRUCTURAL_CHECK_METHOD` for
    every id: every verifier here is a deterministic structural check against already-
    canonicalized data, never an empirical runtime observation, so there is exactly one true
    value for this field and it is not a caller's to vary.
    """

    status, expected, observed, evidence_refs = _expected_fields(invariant_id, context)
    return {
        "schema_version": "0.1",
        "evaluation_id": evaluation_id,
        "invariant_id": invariant_id,
        "subject_ref": subject_ref,
        "state_revision": state_revision,
        "state_fingerprint": state_fingerprint,
        "candidate_id": candidate_id,
        "candidate_semantic_fingerprint": candidate_semantic_fingerprint,
        "verification_stage": verification_stage,
        "method": STRUCTURAL_CHECK_METHOD,
        "expected": expected,
        "observed": observed,
        "status": status,
        "evaluated_at": evaluated_at,
        "evaluator_capability": evaluator_capability,
        "authority_ref": authority_ref,
        "evidence_refs": {"collection_kind": "UNORDERED_SET", "members": list(evidence_refs)},
        "remaining_differences": {"collection_kind": "UNORDERED_SET", "members": []},
    }


def resolve_invariant_evaluation(
    binding: dict[str, Any],
    pool: list[dict[str, Any]],
    *,
    base_state_ref: dict[str, Any],
    after_state_candidate: dict[str, Any],
    verification_context: VerificationContext,
) -> dict[str, Any]:
    """Resolve *binding*'s ``invariant_evaluation_ref`` against *pool* -- the caller-supplied
    Invariant Evaluation records for this Evaluation -- by exact id, then verify every field
    the binding asserts about the underlying record, failing closed on any mismatch:

    * the resolved record is schema-valid;
    * its own ``evaluation_id`` equals the ref's ``id`` exactly (self-consistency: a caller
      cannot supply a record under one id and reference it by another);
    * its recomputed fingerprint equals the binding's ``evaluation_record_fingerprint``;
    * its ``invariant_id``/``status``/``evidence_refs``/``evaluated_at`` match the binding's
      own ``invariant_ref.id``/``evaluation_result``/``evaluation_evidence_refs``/
      ``evaluated_at`` exactly;
    * its ``state_revision``/``state_fingerprint`` match *base_state_ref* exactly -- the
      same "evaluated State" binding R2-F8 already requires of Claim bindings, applied here
      so an Invariant Evaluation from a stale or foreign State can never back a binding for
      the current one;
    * its ``candidate_id``/``candidate_semantic_fingerprint`` match *after_state_candidate*
      exactly (R6-F3) -- ``state_revision``/``state_fingerprint`` alone only bind a record to
      the base State an invariant was evaluated from, never to which specific proposed
      Candidate it was actually applied against; two Candidates from the same base State can
      otherwise share an identical, wrongly-reused record.
    * its ``expected``/``observed``/``status``/``method``/``evidence_refs``/
      ``remaining_differences`` equal exactly what
      :func:`~.invariant_verifiers.verify_invariant` independently re-derives from
      *verification_context* (R7-F1) -- a caller can no longer declare ``status="PASS"``
      while what actually happened does not support it; the real check the invariant's own
      ``CLAIM`` names must independently agree, not merely be internally self-consistent.
    """

    ref_id = binding["invariant_evaluation_ref"].get("id")
    record = next((item for item in pool if item.get("evaluation_id") == ref_id), None)
    if record is None:
        raise DifferenceError(
            f"binding's invariant_evaluation_ref does not resolve to any supplied record: {ref_id!r}"
        )
    validate_record(record, "invariant_evaluation.schema.json")
    if record["evaluation_id"] != ref_id:
        raise DifferenceError("resolved invariant_evaluation record's own evaluation_id does not match its ref")
    if binding["evaluation_record_fingerprint"] != invariant_evaluation_fingerprint(record):
        raise DifferenceError(
            "binding's evaluation_record_fingerprint does not match the resolved "
            "invariant_evaluation record's own recomputed fingerprint"
        )
    if record["invariant_id"] != binding["invariant_ref"]["id"]:
        raise DifferenceError("resolved invariant_evaluation's invariant_id does not match the binding")
    if record["status"] != binding["evaluation_result"]:
        raise DifferenceError("resolved invariant_evaluation's status does not match the binding's evaluation_result")
    if record["evaluated_at"] != binding["evaluated_at"]:
        raise DifferenceError("resolved invariant_evaluation's evaluated_at does not match the binding")
    if unordered_set(record["evidence_refs"]["members"]) != unordered_set(
        binding["evaluation_evidence_refs"].get("members", [])
    ):
        raise DifferenceError("resolved invariant_evaluation's evidence_refs does not match the binding")
    if record["candidate_id"] != after_state_candidate["candidate_id"]:
        raise DifferenceError("resolved invariant_evaluation's candidate_id does not match the real Candidate")
    if record["candidate_semantic_fingerprint"] != after_state_candidate["semantic_fingerprint"]:
        raise DifferenceError(
            "resolved invariant_evaluation's candidate_semantic_fingerprint does not match the "
            "real Candidate"
        )
    if record["state_revision"] != base_state_ref["revision"]:
        raise DifferenceError("resolved invariant_evaluation's state_revision does not match the evaluated State")
    if record["state_fingerprint"] != base_state_ref["fingerprint"]:
        raise DifferenceError("resolved invariant_evaluation's state_fingerprint does not match the evaluated State")

    # R7-F1: independently re-derive expected/observed/status/method/evidence_refs/
    # remaining_differences from verification_context and require the resolved record's own
    # fields to equal exactly what that real, deterministic check produces -- a caller can no
    # longer merely assert a self-consistent PASS record. R8-F1 item 4: evidence_refs is now
    # the real, already Difference/State/Candidate-bound Evidence set (drawn from the same
    # change_result_evidence/change_free_evidence/Sufficiency data verification_context
    # itself carries) that genuinely grounds a PASS -- not always required empty.
    real_status, real_expected, real_observed, real_evidence_refs = _expected_fields(
        binding["invariant_ref"]["id"], verification_context
    )
    if record["method"] != STRUCTURAL_CHECK_METHOD:
        raise DifferenceError("resolved invariant_evaluation's method is not the real verification method")
    if record["expected"] != real_expected:
        raise DifferenceError("resolved invariant_evaluation's expected does not match the real verification")
    if record["observed"] != real_observed:
        raise DifferenceError("resolved invariant_evaluation's observed does not match the real verification")
    if record["status"] != real_status or real_status != "PASS":
        raise DifferenceError(
            f"resolved invariant_evaluation's status does not independently verify as PASS: {real_status!r}"
        )
    if unordered_set(record["evidence_refs"]["members"]) != unordered_set(real_evidence_refs):
        raise DifferenceError(
            "resolved invariant_evaluation's evidence_refs does not match the real, "
            "independently-resolved Evidence grounding this verdict"
        )
    if record["remaining_differences"]["members"]:
        raise DifferenceError(
            "resolved invariant_evaluation declares remaining_differences this vertical has "
            "no real body to resolve for -- fail closed rather than accept an unresolvable "
            "reference"
        )
    return record
