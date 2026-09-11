"""The one public Change Execution receipt-to-Evidence hand-off (Phase 18, Issue #73).

Reuses the identical, already-ratified Change-Free Verification Evidence position
(``evidence/engine.py``'s ``CHANGE_FREE_VERIFICATION_EVIDENCE``)
:mod:`~manosube_agent_civilization.url_boot.evidence_handoff` and
:mod:`~manosube_agent_civilization.runtime.evidence_handoff` both already occupy for their own
bounded, Change-free confirmations -- a completed, bounded, low-risk filesystem execution's own
terminal receipt is structurally the identical kind of independent, Change-free confirmation
input, so this module calls the identical existing owner
(:func:`~manosube_agent_civilization.evidence.derive_evidence`, called exactly once) rather than
adding a second Evidence, Observation, or Reflow owner. This package never itself declares an
Evidence record sufficient, never closes a Difference, and never itself decides completion --
that is exactly the boundary this hand-off exists to respect.

**No re-execution at hand-off.** Corroboration here means resolving the real, committed
``execution_receipt`` this hand-off is given and requiring every one of its own caller-passed
fields to exactly equal what that real, resolved record actually recorded -- never a second
adapter call, and never trusting the caller-passed *receipt* dict directly (the identical
"resolve the real record, never the caller's claim about it" discipline both sibling hand-off
modules already establish).

**``VERIFIED`` requires independent re-observation agreement, not merely a self-reported
``SUCCEEDED`` (P18-R1-F1, Structural Review Round 1).** Before this correction, this module
mapped ``receipt["outcome"] == "SUCCEEDED"`` directly to ``status = "VERIFIED"``, using the
receipt's own ``executor_identity``/``executor_version`` as ``verifier_identity`` -- the executor
self-promoting its own success report into Evidence, with no independent check that the written
files' actual on-disk content matched what was requested. :func:`_construct_provenance` now
additionally requires the resolved receipt's own embedded ``independent_after_state_observation``
(:mod:`~manosube_agent_civilization.change_executor.reobservation`, committed as part of the
receipt itself by ``route.py``) to carry ``outcome == "MATCHED"`` before deriving ``VERIFIED`` --
and, since ``route.py`` itself already refuses to ever commit a ``SUCCEEDED``-outcome receipt
whose own independent re-observation disagrees, a receipt reaching this module with
``outcome == "SUCCEEDED"`` but a disagreeing ``independent_after_state_observation`` should be
structurally unreachable; this module asserts that defensively (raises
:class:`~manosube_agent_civilization.change_executor.errors.ChangeExecutorError`) rather than
silently deriving ``VERIFIED`` for it regardless.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from manosube_agent_civilization.evidence import derive_evidence

from .errors import ChangeExecutorError, ExecutionReceiptIntegrityError
from .identity import change_execution_receipt_id, change_execution_receipt_semantic_fingerprint

_RECEIPT_RECORD_KIND = "execution_receipt"

#: The identical ten fields ``evidence.schema.json``'s own ``verification_result_provenance``
#: requires -- see ``url_boot/evidence_handoff.py``'s own identical constant.
REQUIRED_PROVENANCE_FIELDS: tuple[str, ...] = (
    "status",
    "requirement_id",
    "selection_id",
    "project_id",
    "target_refs",
    "verifier_identity",
    "selection_authority_ref",
    "verification_boundary",
    "input_refs",
    "observations",
)

#: Every :data:`~manosube_agent_civilization.change_executor.types.EXECUTION_OUTCOMES` member
#: maps to exactly one of Evidence's own ``verification_result_provenance.status`` vocabulary
#: members (``VERIFIED``/``FAILED``/``INSUFFICIENT``/``UNAVAILABLE``) -- the one shared
#: classification this module reads.
_OUTCOME_TO_PROVENANCE_STATUS: dict[str, str] = {
    "SUCCEEDED": "VERIFIED",
    "REFUSED": "FAILED",
    "BOUNDARY_VIOLATION": "FAILED",
    "STALE_AUTHORITY": "FAILED",
    "TARGET_DRIFT": "FAILED",
    "KILL_SWITCH_STOPPED": "FAILED",
    "TIMEOUT": "UNAVAILABLE",
    "ADAPTER_FAILURE": "FAILED",
    "PARTIAL_MUTATION": "INSUFFICIENT",
    "ROLLBACK_SUCCEEDED": "INSUFFICIENT",
    "ROLLBACK_FAILED": "FAILED",
    "UNKNOWN": "UNAVAILABLE",
    "REOBSERVATION_MISMATCH": "FAILED",
}


def resolve_and_verify_committed_receipt(
    store: Any, project_id: str, change_execution_receipt_id_value: str
) -> dict[str, Any]:
    """Resolve the real, committed ``execution_receipt`` named by
    *change_execution_receipt_id_value* under *project_id*, and require: same project, and its
    own identity and semantic fingerprint, independently recomputed from its own content, equal
    to its own declared values -- **and** equal to the Store lookup key itself (the three-way
    check every sibling hand-off module already applies)."""

    resolved = store.resolve_record(
        project_id, _RECEIPT_RECORD_KIND, change_execution_receipt_id_value
    )
    if resolved is None or not isinstance(resolved, dict):
        raise ExecutionReceiptIntegrityError(
            "change_execution_receipt_id does not resolve to a committed execution_receipt for "
            f"project {project_id!r}: {change_execution_receipt_id_value!r}"
        )
    receipt = dict(resolved)
    if receipt.get("project_id") != project_id:
        raise ExecutionReceiptIntegrityError(
            "resolved execution_receipt names a different project than the one being handed "
            f"off: {receipt.get('project_id')!r} != {project_id!r}"
        )
    declared_id = receipt.get("change_execution_receipt_id")
    recomputed_id = change_execution_receipt_id(receipt)
    if change_execution_receipt_id_value != declared_id or recomputed_id != declared_id:
        raise ExecutionReceiptIntegrityError(
            "resolved execution_receipt's own identity does not agree across the Store lookup "
            f"key, its own declared value, and its own recomputed value -- "
            f"lookup={change_execution_receipt_id_value!r}, declared={declared_id!r}, "
            f"recomputed={recomputed_id!r}"
        )
    if change_execution_receipt_semantic_fingerprint(receipt) != receipt.get(
        "change_execution_receipt_semantic_fingerprint"
    ):
        raise ExecutionReceiptIntegrityError(
            f"resolved execution_receipt {change_execution_receipt_id_value!r} own recomputed "
            "semantic fingerprint does not equal its own declared value -- refusing to trust "
            "any of its fields"
        )
    return receipt


def _reference_set(refs: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    members = [dict(ref) for ref in refs]
    members.sort(key=lambda ref: (ref.get("kind", ""), ref.get("id", "")))
    return {"collection_kind": "UNORDERED_SET", "members": members}


def _construct_provenance(receipt: Mapping[str, Any], project_id: str) -> dict[str, Any]:
    """Return the one, deterministic ``verification_result_provenance`` projection this hand-off
    derives -- entirely from the real, resolved, integrity-checked receipt, never from any field
    a caller-constructed receipt dict merely claims.

    ``status`` is derived from ``receipt["outcome"]`` alone (:data:`_OUTCOME_TO_PROVENANCE_
    STATUS`), **except** that a receipt claiming ``outcome == "SUCCEEDED"`` whose own embedded
    ``independent_after_state_observation`` does not itself carry ``outcome == "MATCHED"`` is
    refused outright rather than derived as ``VERIFIED`` -- this should be structurally
    unreachable (``route.py`` itself never commits such a combination), so reaching it here means
    something upstream is broken, and this module fails closed rather than silently trust a
    self-reported ``SUCCEEDED`` it cannot itself independently confirm (P18-R1-F1, Structural
    Review Round 1). ``verifier_identity`` still names ``executor_identity``/``executor_version``
    -- the identical, honest framing this package already used before this correction: this
    package's own re-read code (:mod:`~manosube_agent_civilization.change_executor.
    reobservation`), not the adapter, is what actually performed the confirming independent
    observation, and that re-read is itself executed, and its own result committed, under this
    same executor identity/version -- the field names what performed and confirmed the work, not
    merely what the adapter self-reported."""

    if (
        receipt["outcome"] == "SUCCEEDED"
        and receipt["independent_after_state_observation"].get("outcome") != "MATCHED"
    ):
        raise ChangeExecutorError(
            "resolved execution_receipt claims outcome=SUCCEEDED but its own embedded "
            "independent_after_state_observation does not agree (outcome="
            f"{receipt['independent_after_state_observation'].get('outcome')!r}) -- refusing to "
            "derive VERIFIED for a self-reported success this package cannot itself independently "
            "confirm; route.py should never commit this combination, so reaching this check means "
            "something upstream is broken"
        )

    receipt_ref = {"kind": _RECEIPT_RECORD_KIND, "id": receipt["change_execution_receipt_id"]}
    refs = (dict(receipt["change_ref"]), receipt_ref)
    slot_key = receipt["execution_request_id"]
    observations = {
        "outcome": receipt["outcome"],
        "performed_result_summary": dict(receipt["performed_result_summary"]),
        "performed_result_fingerprint": receipt["performed_result_fingerprint"],
        "rollback_outcome": receipt["rollback_outcome"],
        "execution_started_at": receipt["execution_started_at"],
        "execution_ended_at": receipt["execution_ended_at"],
        "independent_after_state_observation": dict(receipt["independent_after_state_observation"]),
    }
    provenance = {
        "status": _OUTCOME_TO_PROVENANCE_STATUS[receipt["outcome"]],
        "requirement_id": slot_key,
        "selection_id": slot_key,
        "project_id": project_id,
        "target_refs": _reference_set(refs),
        "verifier_identity": {
            "executor_identity": receipt["executor_identity"],
            "executor_version": receipt["executor_version"],
        },
        "selection_authority_ref": dict(receipt["authority_ref"]),
        "verification_boundary": {
            "execution_boundary_fingerprint": receipt["execution_boundary_fingerprint"],
            "target": dict(receipt["target"]),
            "operation": dict(receipt["operation"]),
        },
        "input_refs": _reference_set(refs),
        "observations": observations,
    }
    if set(provenance) != set(REQUIRED_PROVENANCE_FIELDS):
        raise ChangeExecutorError(
            "constructed verification_result_provenance does not carry exactly the required "
            f"field set: {sorted(provenance)} != {sorted(REQUIRED_PROVENANCE_FIELDS)}"
        )
    return provenance


def route_change_execution_to_evidence(
    store: Any, receipt: Mapping[str, Any], project_id: str, evidence_request: Mapping[str, Any]
) -> dict[str, Any]:
    """Hand *receipt* off to the existing Evidence owner and return the one canonical Evidence
    record it derives from *evidence_request*.

    *receipt* is never trusted directly: this function resolves the real, committed
    ``execution_receipt`` its own ``change_execution_receipt_id`` names, and requires every field
    of the passed-in *receipt* to exactly equal the corresponding field of that resolved record
    before deriving anything.

    *evidence_request* must already be a real, Change-free,
    ``verification_observation_request``-grounded Evidence request (see
    :mod:`manosube_agent_civilization.evidence.engine` for its own real, complete request shape,
    which this function follows exactly). This function fabricates none of that; it only
    constructs and injects ``verification_result_provenance``, and re-verifies the derived record
    actually carries exactly that provenance before returning it.

    Every :class:`~manosube_agent_civilization.evidence.errors.EvidenceError` the existing owner
    itself raises propagates unchanged.
    """

    if not isinstance(receipt, Mapping):
        raise ChangeExecutorError(f"receipt must be a mapping, not {type(receipt)!r}")
    receipt_id = receipt.get("change_execution_receipt_id")
    if not isinstance(receipt_id, str) or not receipt_id:
        raise ChangeExecutorError("receipt carries no readable change_execution_receipt_id")
    if receipt.get("project_id") != project_id:
        raise ChangeExecutorError(
            "receipt's own originating project_id does not match the requested project_id -- a "
            f"receipt cannot be relabelled across projects: {receipt.get('project_id')!r} != "
            f"{project_id!r}"
        )

    resolved = resolve_and_verify_committed_receipt(store, project_id, receipt_id)

    # Complete receipt attestation required, the identical discipline both sibling hand-off
    # modules already establish: every one of *receipt*'s own Evidence-relevant fields must
    # exactly equal the real, resolved receipt's own content before any Evidence is derived. A
    # receipt forged in any single field, even with every other field genuine, refuses here.
    for field in (
        "execution_request_id",
        "change_ref",
        "idempotency_key",
        "authority_ref",
        "project_binding_ref",
        "boot_state_fingerprint",
        "execution_boundary_fingerprint",
        "executor_identity",
        "executor_version",
        "target",
        "operation",
        "execution_started_at",
        "execution_ended_at",
        "outcome",
        "performed_result_fingerprint",
        "performed_result_summary",
        "rollback_outcome",
        "claim_token",
        "reobservation_request",
        "independent_after_state_observation",
    ):
        if dict(receipt).get(field) != resolved.get(field):
            raise ChangeExecutorError(
                f"receipt's own {field} does not match the real, committed execution_receipt's "
                f"own {field}"
            )

    if not isinstance(evidence_request, Mapping):
        raise ChangeExecutorError(
            f"evidence_request must be an explicit mapping, not {type(evidence_request)!r}"
        )
    if evidence_request.get("change_request") is not None:
        raise ChangeExecutorError(
            "evidence_request must be Change-free -- a Change Execution receipt never executes "
            "or grounds a new Change"
        )
    if evidence_request.get("post_change_observation_request") is not None:
        raise ChangeExecutorError(
            "evidence_request must carry no post_change_observation_request -- a Change "
            "Execution receipt never grounds a Change result"
        )
    if evidence_request.get("verification_observation_request") is None:
        raise ChangeExecutorError(
            "evidence_request must carry a verification_observation_request -- the one Evidence "
            "position (Change-Free Verification Evidence) this hand-off produces"
        )
    if evidence_request.get("verification_result_provenance") is not None:
        raise ChangeExecutorError(
            "evidence_request must not already carry a verification_result_provenance -- this "
            "hand-off constructs it from the real, resolved execution_receipt itself"
        )

    provenance = _construct_provenance(resolved, project_id)
    request = dict(evidence_request)
    request["verification_result_provenance"] = provenance

    evidence = derive_evidence(request)

    if evidence["verification_result_provenance"] != provenance:
        raise ChangeExecutorError(
            "the derived Evidence record's own verification_result_provenance does not exactly "
            "equal the one this hand-off constructed from the real execution_receipt -- refusing "
            "to return a record whose provenance this hand-off cannot confirm"
        )
    if evidence["target"]["project_id"] != project_id:
        raise ChangeExecutorError(
            "the derived Evidence record names a different project than requested: "
            f"{evidence['target']['project_id']!r} != {project_id!r}"
        )

    return evidence


__all__ = [
    "REQUIRED_PROVENANCE_FIELDS",
    "resolve_and_verify_committed_receipt",
    "route_change_execution_to_evidence",
]
