"""Canonical Completion Record identity and resolution -- owned by Difference (R4-F2,
Phase 7 structural-review round 4).

``01_SCHEMA/difference/candidate_completion_record.schema.json`` exists in full, and
``00_KERNEL/04_DIFFERENCE/CLOSURE_POLICY.md`` gives a complete, closed-form profile for it:
the content-addressed ``completion_id`` (line 672), and the ``MANOSUBE-RESOLVED-EVALUATION-
RECORD-SHA256-0.1`` fingerprint it shares with Invariant Evaluation (lines 603-622). Round 3
of this vertical's structural review found the record itself was never built or resolved
anywhere; round 4's adopted disposition is explicit that Reflow does not become a second
owner for it -- Completion Record identity belongs here, in Difference, the same package
that already owns the completion Claim's own identity (:func:`.identity.completion_claim_id`).
Reflow (:mod:`manosube_agent_civilization.reflow.closure`) calls into this module to
*resolve* a claim binding's declared ``completion_record_ref`` against the one record its
own claim descriptor and Evaluation inputs imply; it never authors a second formula.
"""

from __future__ import annotations

import hashlib
from typing import Any

from .canonical import canonical_bytes, unordered_set
from .errors import DifferenceError
from .identity import completion_claim_id
from .validation import validate_record

_COMPLETION_RECORD_ID_DOMAIN = b"MANOSUBE:CANDIDATE_COMPLETION_RECORD:0.1:"
_COMPLETION_RECORD_FINGERPRINT_DOMAIN = b"MANOSUBE:COMPLETION_RECORD:0.1:"

#: ``COMPLETION_RECORD_SCALARS``, CLOSURE_POLICY.md line 603-606.
COMPLETION_RECORD_SCALARS: tuple[str, ...] = (
    "completion_id",
    "subject_type",
    "subject_ref",
    "claim",
    "target_state_ref",
    "observed_state_ref",
    "closure_policy_ref",
    "evaluation_status",
    "evaluated_state_revision",
    "evaluated_state_fingerprint",
    "evaluated_at",
)
#: ``COMPLETION_RECORD_UNORDERED_SETS``, CLOSURE_POLICY.md line 608-609.
COMPLETION_RECORD_UNORDERED_SET_FIELDS: tuple[str, ...] = (
    "required_evidence_refs",
    "invariant_evaluation_refs",
    "material_contradiction_refs",
)

#: The mandatory X-003 completion Claim CLOSURE_POLICY.md's text fixes as a closed-form
#: constant. Owned here, not Reflow, since it is Completion-domain content -- Reflow reads
#: :data:`MANDATORY_X003_CLAIM_REF`, it does not define the descriptor.
MANDATORY_X003_CLAIM_DESCRIPTOR: dict[str, Any] = {
    "subject_type": "CONTRACT_COMPLETION",
    "subject_ref": {"kind": "kernel_invariant", "id": "X-003"},
    "claim": {"AGENT_REQUIRED_FOR_KERNEL": False, "SESSION_INDEPENDENT": True},
    "target_state_ref": None,
}
MANDATORY_X003_CLAIM_ID: str = completion_claim_id(MANDATORY_X003_CLAIM_DESCRIPTOR)
MANDATORY_X003_CLAIM_REF: dict[str, str] = {
    "kind": "completion_claim",
    "id": MANDATORY_X003_CLAIM_ID,
}


def resolve_claim_descriptor(required_claim_ref: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    """Return the full seven-field Claim descriptor *required_claim_ref* names -- the
    mandatory X-003 constant, or a matching entry in the Policy's own ``required_claims``.
    Raises if the ref names neither: a Completion Record cannot be resolved for a Claim
    this Policy never declared and that is not the mandatory one.
    """

    if required_claim_ref.get("id") == MANDATORY_X003_CLAIM_ID:
        return MANDATORY_X003_CLAIM_DESCRIPTOR
    required_claims: list[dict[str, Any]] = policy["required_claims"]
    for item in required_claims:
        if item.get("id") == required_claim_ref.get("id"):
            return item
    raise DifferenceError(
        "required_claim_ref does not resolve to a descriptor this Policy declares: "
        f"{required_claim_ref.get('id')!r}"
    )


def _completion_record_closed_projection(record: dict[str, Any]) -> dict[str, Any]:
    projection: dict[str, Any] = {key: record[key] for key in COMPLETION_RECORD_SCALARS}
    for key in COMPLETION_RECORD_UNORDERED_SET_FIELDS:
        projection[key] = unordered_set(record[key]["members"])
    return projection


def completion_record_fingerprint(record: dict[str, Any]) -> str:
    """Return ``MANOSUBE-RESOLVED-EVALUATION-RECORD-SHA256-0.1``'s digest for a Completion
    Record. The closed projection includes ``completion_id`` but excludes the post-commit
    ``reflow_transition_ref`` -- CLOSURE_POLICY.md names that field's exclusion explicitly
    so a pre-promotion binding never circularly depends on the transition it is itself
    part of committing, and so setting it alone (the one field a real commit changes) never
    makes an otherwise-unchanged record look STALE.
    """

    digest = hashlib.sha256(
        _COMPLETION_RECORD_FINGERPRINT_DOMAIN
        + canonical_bytes(_completion_record_closed_projection(record))
    ).hexdigest()
    return "sha256:" + digest


def candidate_completion_record_id(record: dict[str, Any]) -> str:
    """Return the content-addressed ``completion_id`` CLOSURE_POLICY.md line 672 defines --
    the same closed projection the fingerprint uses, minus ``completion_id`` itself (an
    identity cannot be part of its own preimage) and ``reflow_transition_ref`` (excluded
    the same way the fingerprint excludes it). A different candidate, Policy, or evaluated
    State/time for the same stable Claim is a different id by construction.
    """

    projection = _completion_record_closed_projection(record)
    del projection["completion_id"]
    digest = hashlib.sha256(_COMPLETION_RECORD_ID_DOMAIN + canonical_bytes(projection)).hexdigest()
    return "CMP-" + digest.upper()


def build_completion_record(
    *,
    claim_descriptor: dict[str, Any],
    policy_ref: dict[str, Any],
    observed_state_ref: dict[str, Any],
    evaluated_state_revision: int,
    evaluated_state_fingerprint: dict[str, Any],
    evaluation_status: str,
    evaluated_at: str,
    required_evidence_refs: list[Any],
    invariant_evaluation_refs: list[Any],
    material_contradiction_refs: list[Any],
) -> dict[str, Any]:
    """Build the one canonical, schema-shaped Completion Record *claim_descriptor*'s
    evaluation implies, with its own content-addressed ``completion_id`` already set.

    ``subject_type``/``subject_ref``/``claim``/``target_state_ref`` are copied verbatim
    from *claim_descriptor* -- CLOSURE_POLICY.md defines ``claim_semantic_fingerprint``
    from exactly these four Completion Record fields, so they are the descriptor's own
    fields reused, not independently chosen.
    """

    record: dict[str, Any] = {
        "schema_version": "0.1",
        "completion_id": "",
        "subject_type": claim_descriptor["subject_type"],
        "subject_ref": claim_descriptor["subject_ref"],
        "claim": claim_descriptor["claim"],
        "target_state_ref": claim_descriptor["target_state_ref"],
        "observed_state_ref": observed_state_ref,
        "closure_policy_ref": policy_ref,
        "required_evidence_refs": unordered_set(required_evidence_refs),
        "invariant_evaluation_refs": unordered_set(invariant_evaluation_refs),
        "material_contradiction_refs": unordered_set(material_contradiction_refs),
        "evaluation_status": evaluation_status,
        "evaluated_state_revision": evaluated_state_revision,
        "evaluated_state_fingerprint": evaluated_state_fingerprint,
        "evaluated_at": evaluated_at,
        "reflow_transition_ref": None,
    }
    record["completion_id"] = candidate_completion_record_id(record)
    validate_record(record, "candidate_completion_record.schema.json")
    return record


def resolve_completion_record(
    binding: dict[str, Any],
    *,
    policy: dict[str, Any],
    observed_state_ref: dict[str, Any],
    evaluated_state_revision: int,
    evaluated_state_fingerprint: dict[str, Any],
    invariant_evaluation_refs: list[Any],
    material_contradiction_refs: list[Any],
) -> dict[str, Any]:
    """Resolve *binding*'s ``completion_record_ref`` against the one Completion Record its
    own Claim descriptor and this Evaluation's inputs imply, and verify the binding matches
    it exactly on identity and fingerprint -- fail closed rather than trust the binding's
    restatement of either.
    """

    claim_descriptor = resolve_claim_descriptor(binding["required_claim_ref"], policy)
    record = build_completion_record(
        claim_descriptor=claim_descriptor,
        policy_ref=binding["policy_ref"],
        observed_state_ref=observed_state_ref,
        evaluated_state_revision=evaluated_state_revision,
        evaluated_state_fingerprint=evaluated_state_fingerprint,
        evaluation_status=binding["evaluation_status"],
        evaluated_at=binding["evaluated_at"],
        required_evidence_refs=list(binding["evaluation_evidence_refs"].get("members", [])),
        invariant_evaluation_refs=invariant_evaluation_refs,
        material_contradiction_refs=material_contradiction_refs,
    )
    if binding["completion_record_ref"].get("id") != record["completion_id"]:
        raise DifferenceError(
            "binding's completion_record_ref does not resolve to the Completion Record its "
            "own claim descriptor and Evaluation inputs imply"
        )
    if binding["evaluation_record_fingerprint"] != completion_record_fingerprint(record):
        raise DifferenceError(
            "binding's evaluation_record_fingerprint does not match the resolved Completion "
            "Record's own recomputed fingerprint"
        )
    return record
