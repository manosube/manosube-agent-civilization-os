"""The one public Runtime-Observation-to-Evidence handoff (Phase 15, Issue #64).

Reuses the identical, already-ratified Change-Free Verification Evidence position
(``evidence/engine.py``'s ``CHANGE_FREE_VERIFICATION_EVIDENCE``) Projection's own
:mod:`~manosube_agent_civilization.projection.receipt_handoff` already occupies -- a bounded
runtime observation confirming what an explicit target currently reports is structurally the
same kind of independent, Change-free confirmation, so this module calls the identical existing
owner (:func:`~manosube_agent_civilization.evidence.derive_evidence`, called exactly once)
rather than adding a second Evidence, Observation, or Reflow owner.

**No re-observation at handoff (deliberate divergence from Projection, disclosed).** Projection's
own ``receipt_handoff.py`` independently re-observes the *live* external artifact at handoff
time, because a genuine GitHub artifact is expected to remain stable between materialization and
handoff, and a fresh re-observation is exactly what corroborates that a forged receipt cannot
fake. A live runtime target may legitimately change between the original observation and a
later handoff -- re-observing here would either produce a spurious mismatch against a target
that has since, legitimately, changed, or silently redefine "this receipt is genuine" to mean
"the target still looks like this *right now*", which is not what Issue #64 asks Evidence to
attest to. Corroboration here instead means: resolve the real, committed Runtime Observation
Envelope this receipt claims from Store, verify its own recomputed semantic fingerprint against
its own declared value (tamper detection), and require every one of *receipt*'s own fields to
exactly equal what that real, resolved Envelope actually recorded -- never a second live network
call.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from manosube_agent_civilization.evidence import derive_evidence

from .errors import RuntimeEnvelopeIntegrityError, RuntimeRequirementError
from .identity import runtime_observation_envelope_semantic_fingerprint
from .types import RUNTIME_OUTCOME_TO_RECEIPT_STATUS, RuntimeObservationReceipt

_ENVELOPE_RECORD_KIND = "runtime_observation_envelope"

#: The identical ten fields ``evidence.schema.json``'s own ``verification_result_provenance``
#: requires -- see ``projection/receipt_handoff.py``'s own identical constant.
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


def _plain(value: Any) -> Any:
    """Recursively rebuild *value* as plain ``dict``/``list``/scalar -- undoes
    :class:`~manosube_agent_civilization.runtime.types.RuntimeObservationReceipt`'s own deep
    freeze (``MappingProxyType``/``tuple``) so a receipt field can be compared for genuine
    structural equality against the real, Store-resolved Envelope's own plain ``dict``/``list``
    fields, which a bare ``!=`` would otherwise report as unequal on container type alone."""

    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(item) for item in value]
    return value


def _reference_set(refs: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    members = [dict(ref) for ref in refs]
    members.sort(key=lambda ref: (ref.get("kind", ""), ref.get("id", "")))
    return {"collection_kind": "UNORDERED_SET", "members": members}


def _construct_provenance(envelope: Mapping[str, Any], project_id: str) -> dict[str, Any]:
    """Return the one, deterministic ``verification_result_provenance`` projection this
    handoff derives -- entirely from the real, resolved, integrity-checked Envelope, never
    from any field a caller-constructed :class:`~.types.RuntimeObservationReceipt` merely
    claims.

    *target_refs*/*input_refs* name the target's own owning Project Binding (Issue #64's own
    disclosed judgment call: a Runtime Observation has no separate canonical Difference/
    Change/Evidence subject the way a Projection does -- the Project Binding the target
    declares itself bound to is the one existing-owner reference this position can genuinely
    attest observed content *about*)."""

    project_binding_ref = dict(envelope["target_identity"]["project_binding_ref"])
    refs = (project_binding_ref,)
    observations = {
        "observation_outcome": envelope["observation_outcome"],
        "observed_content_fingerprint": envelope["observed_content_fingerprint"],
        "observed_at": envelope["observed_at"],
    }
    provenance = {
        "status": RUNTIME_OUTCOME_TO_RECEIPT_STATUS[envelope["observation_outcome"]],
        "requirement_id": envelope["runtime_observation_envelope_id"],
        "selection_id": envelope["runtime_observation_envelope_id"],
        "project_id": project_id,
        "target_refs": _reference_set(refs),
        "verifier_identity": dict(envelope["adapter_identity"]),
        "selection_authority_ref": dict(envelope["human_authority_ref"]),
        "verification_boundary": {
            "target_identity": dict(envelope["target_identity"]),
            "boundary": dict(envelope["boundary"]),
        },
        "input_refs": _reference_set(refs),
        "observations": observations,
    }
    if set(provenance) != set(REQUIRED_PROVENANCE_FIELDS):
        raise RuntimeRequirementError(
            "constructed verification_result_provenance does not carry exactly the required "
            f"field set: {sorted(provenance)} != {sorted(REQUIRED_PROVENANCE_FIELDS)}"
        )
    return provenance


def route_runtime_observation_to_evidence(
    store: Any,
    receipt: RuntimeObservationReceipt,
    project_id: str,
    evidence_request: Mapping[str, Any],
) -> dict[str, Any]:
    """Hand *receipt* off to the existing Evidence owner and return the one canonical Evidence
    record it derives from *evidence_request*.

    *evidence_request* must already be a real, Change-free,
    ``verification_observation_request``-grounded Evidence request. This function fabricates
    none of that; it only constructs and injects ``verification_result_provenance``, and
    re-verifies the derived record actually carries exactly that provenance before returning
    it.

    **Independent Store resolution, never a trusted receipt.** Resolving only the real,
    committed Envelope this receipt claims (never trusting *receipt* itself, which remains a
    publicly constructible dataclass) proves what was genuinely observed and committed --
    exactly the discipline Projection's own Structural Review Round 2/3 already established
    (``projection/receipt_handoff.py``'s own module docstring), adapted here to require every
    one of *receipt*'s own fields to equal the resolved Envelope's own real content instead of
    a fresh re-observation (see this module's own docstring for why).

    Every :class:`~manosube_agent_civilization.evidence.errors.EvidenceError` the existing
    owner itself raises propagates unchanged.
    """

    if not isinstance(receipt, RuntimeObservationReceipt):
        raise RuntimeRequirementError(
            f"receipt must be a RuntimeObservationReceipt instance, not {type(receipt)!r}"
        )
    envelope = store.resolve_record(
        project_id, _ENVELOPE_RECORD_KIND, receipt.runtime_observation_envelope_id
    )
    if envelope is None:
        raise RuntimeRequirementError(
            "receipt names a runtime_observation_envelope_id that does not resolve under the "
            f"requested project {project_id!r} -- a receipt genuinely produced for a "
            "different project cannot be relabelled as Evidence for this one: "
            f"{receipt.runtime_observation_envelope_id!r}"
        )
    if runtime_observation_envelope_semantic_fingerprint(envelope) != envelope.get(
        "runtime_observation_semantic_fingerprint"
    ):
        raise RuntimeEnvelopeIntegrityError(
            f"resolved Envelope {receipt.runtime_observation_envelope_id!r} own recomputed "
            "semantic fingerprint does not equal its own declared value -- refusing to trust "
            "any of its fields"
        )
    if receipt.project_id != project_id or envelope["project_id"] != project_id:
        raise RuntimeRequirementError(
            "receipt's own originating project_id does not match the requested project_id -- "
            f"a receipt cannot be relabelled across projects: {receipt.project_id!r}, "
            f"envelope={envelope['project_id']!r}, requested={project_id!r}"
        )

    # Complete receipt attestation required, the identical discipline Projection's own
    # Structural Review Round 4 (P14-R4-F2) established: every one of receipt's own
    # Evidence-relevant fields must exactly equal the real, resolved Envelope's own content
    # before any Evidence is derived. A receipt forged in any single field, even with every
    # other field genuine, refuses here.
    if _plain(receipt.target_identity) != envelope["target_identity"]:
        raise RuntimeRequirementError(
            "receipt's own target_identity does not match the real, committed Envelope's "
            "target_identity"
        )
    if _plain(receipt.boundary) != envelope["boundary"]:
        raise RuntimeRequirementError(
            "receipt's own boundary does not match the real, committed Envelope's boundary"
        )
    if _plain(receipt.adapter_identity) != envelope["adapter_identity"]:
        raise RuntimeRequirementError(
            "receipt's own adapter_identity does not match the real, committed Envelope's "
            "adapter_identity"
        )
    if _plain(receipt.human_authority_ref) != envelope["human_authority_ref"]:
        raise RuntimeRequirementError(
            "receipt's own human_authority_ref does not match the real, committed Envelope's "
            "human_authority_ref"
        )
    expected_observations = {
        "observation_outcome": envelope["observation_outcome"],
        "observed_content_fingerprint": envelope["observed_content_fingerprint"],
        "observed_at": envelope["observed_at"],
    }
    if _plain(receipt.observations) != expected_observations:
        raise RuntimeRequirementError(
            "receipt's own observations do not match the real, committed Envelope's own "
            f"recorded observation: {_plain(receipt.observations)!r} != {expected_observations!r}"
        )
    expected_status = RUNTIME_OUTCOME_TO_RECEIPT_STATUS[envelope["observation_outcome"]]
    if receipt.status != expected_status:
        raise RuntimeRequirementError(
            f"receipt's own status does not equal the outcome-derived status: "
            f"{receipt.status!r} != {expected_status!r}"
        )
    expected_input_refs = [dict(envelope["target_identity"]["project_binding_ref"])]
    actual_input_refs = _plain(receipt.input_refs)
    if actual_input_refs != expected_input_refs:
        raise RuntimeRequirementError(
            "receipt's own input_refs do not equal the expected input refs derived from the "
            f"real, committed Envelope: {actual_input_refs!r} != {expected_input_refs!r}"
        )

    if not isinstance(evidence_request, Mapping):
        raise RuntimeRequirementError(
            f"evidence_request must be an explicit mapping, not {type(evidence_request)!r}"
        )
    if evidence_request.get("change_request") is not None:
        raise RuntimeRequirementError(
            "evidence_request must be Change-free -- a Runtime Observation Receipt never "
            "executes or grounds a Change"
        )
    if evidence_request.get("post_change_observation_request") is not None:
        raise RuntimeRequirementError(
            "evidence_request must carry no post_change_observation_request -- a Runtime "
            "Observation Receipt never grounds a Change result"
        )
    if evidence_request.get("verification_observation_request") is None:
        raise RuntimeRequirementError(
            "evidence_request must carry a verification_observation_request -- the one "
            "Evidence position (Change-Free Verification Evidence) this handoff produces"
        )
    if evidence_request.get("verification_result_provenance") is not None:
        raise RuntimeRequirementError(
            "evidence_request must not already carry a verification_result_provenance -- "
            "this handoff constructs it from the real, resolved Envelope itself"
        )

    provenance = _construct_provenance(envelope, project_id)
    request = dict(evidence_request)
    request["verification_result_provenance"] = provenance

    evidence = derive_evidence(request)

    if evidence["verification_result_provenance"] != provenance:
        raise RuntimeRequirementError(
            "the derived Evidence record's own verification_result_provenance does not "
            "exactly equal the one this handoff constructed from the real Envelope -- "
            "refusing to return a record whose provenance this handoff cannot confirm"
        )
    if evidence["target"]["project_id"] != project_id:
        raise RuntimeRequirementError(
            "the derived Evidence record names a different project than requested: "
            f"{evidence['target']['project_id']!r} != {project_id!r}"
        )

    return evidence


__all__ = ["route_runtime_observation_to_evidence"]
