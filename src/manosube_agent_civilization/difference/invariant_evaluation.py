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
"""

from __future__ import annotations

import hashlib
from typing import Any

from .canonical import canonical_bytes, unordered_set
from .errors import DifferenceError
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


def resolve_invariant_evaluation(
    binding: dict[str, Any],
    pool: list[dict[str, Any]],
    *,
    base_state_ref: dict[str, Any],
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
      the current one.
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
    if record["state_revision"] != base_state_ref["revision"]:
        raise DifferenceError("resolved invariant_evaluation's state_revision does not match the evaluated State")
    if record["state_fingerprint"] != base_state_ref["fingerprint"]:
        raise DifferenceError("resolved invariant_evaluation's state_fingerprint does not match the evaluated State")
    return record
