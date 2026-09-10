"""The one public URL-Boot-Observation-to-Evidence handoff (Phase 17, Issue #69).

Reuses the identical, already-ratified Change-Free Verification Evidence position
(``evidence/engine.py``'s ``CHANGE_FREE_VERIFICATION_EVIDENCE``)
:mod:`~manosube_agent_civilization.runtime.evidence_handoff` already occupies for a bounded live
observation -- a bounded, read-only URL source observation confirming what an explicit source
currently reports is structurally the same kind of independent, Change-free confirmation, so this
module calls the identical existing owner
(:func:`~manosube_agent_civilization.evidence.derive_evidence`, called exactly once) rather than
adding a second Evidence, Observation, or Reflow owner.

**No re-fetch at handoff**, for the identical reason ``runtime/evidence_handoff.py``'s own module
docstring states for a live runtime target: corroboration here means resolving the real,
committed URL Source Observation Envelope this receipt claims from Store and requiring every one
of *receipt*'s own fields to exactly equal what that real, resolved Envelope actually recorded --
never a second live network call.

**Applied from the start, not corrected into later (Phase 16 Structural Review Round 2,
P16-R2-F1).** A Store lookup by a caller-claimed id, followed only by a semantic-fingerprint
check, cannot catch a resolved record whose own declared identity field was substituted after
commit: both ``url_source_observation_envelope_id`` and
``url_source_observation_semantic_fingerprint`` are themselves excluded from the projection each
one hashes (:data:`~manosube_agent_civilization.url_boot.identity.ENVELOPE_SEMANTIC_FIELDS`), so
a record whose declared identity field disagrees with the Store lookup key it was resolved under
-- with every other field genuine -- still recomputes a matching semantic fingerprint. This
module resolves through a three-way equality instead: the Store lookup key, the resolved record's
own declared ``url_source_observation_envelope_id``, and that identity independently recomputed
from the resolved record's own content, all three required equal before any field of the record
is ever trusted -- exactly the correction Phase 16's own
:func:`~manosube_agent_civilization.model_runtime.route.resolve_and_verify_committed_envelope`
had to be added for after the fact (see ``11_MODEL_RUNTIME/MODEL_RUNTIME_CONTRACT.md``'s own
Structural Review Round 2 section), applied here from this package's very first delivery instead.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from manosube_agent_civilization.evidence import derive_evidence

from .errors import UrlBootEnvelopeIntegrityError, UrlBootRequirementError
from .identity import (
    url_source_observation_envelope_id,
    url_source_observation_envelope_semantic_fingerprint,
)
from .types import URL_OUTCOME_TO_RECEIPT_STATUS, UrlSourceObservationReceipt

_ENVELOPE_RECORD_KIND = "url_source_observation_envelope"

#: The identical ten fields ``evidence.schema.json``'s own ``verification_result_provenance``
#: requires -- see ``runtime/evidence_handoff.py``'s own identical constant.
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
    :class:`~manosube_agent_civilization.url_boot.types.UrlSourceObservationReceipt`'s own deep
    freeze so a receipt field can be compared for genuine structural equality against the real,
    Store-resolved Envelope's own plain fields."""

    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(item) for item in value]
    return value


def resolve_and_verify_committed_envelope(
    store: Any, project_id: str, envelope_id: str
) -> dict[str, Any]:
    """Resolve the real, committed ``url_source_observation_envelope`` named by *envelope_id*
    under *project_id*, and require: same project, and its own identity and semantic fingerprint,
    independently recomputed from its own content, equal to its own declared values -- **and**
    equal to the Store lookup key itself (the three-way check this module's own docstring
    explains)."""

    resolved = store.resolve_record(project_id, _ENVELOPE_RECORD_KIND, envelope_id)
    if resolved is None:
        raise UrlBootRequirementError(
            "receipt names a url_source_observation_envelope_id that does not resolve under the "
            f"requested project {project_id!r} -- a receipt genuinely produced for a different "
            f"project cannot be relabelled as Evidence for this one: {envelope_id!r}"
        )
    if not isinstance(resolved, dict):
        raise UrlBootRequirementError(
            f"resolved url_source_observation_envelope is not a mapping: {resolved!r}"
        )
    envelope = dict(resolved)
    if envelope.get("project_id") != project_id:
        raise UrlBootRequirementError(
            "resolved url_source_observation_envelope names a different project than the one "
            f"being handed off: {envelope.get('project_id')!r} != {project_id!r}"
        )
    declared_id = envelope.get("url_source_observation_envelope_id")
    recomputed_id = url_source_observation_envelope_id(envelope)
    if envelope_id != declared_id or recomputed_id != declared_id:
        raise UrlBootEnvelopeIntegrityError(
            "resolved url_source_observation_envelope's own identity does not agree across the "
            f"Store lookup key, its own declared value, and its own recomputed value -- "
            f"lookup={envelope_id!r}, declared={declared_id!r}, recomputed={recomputed_id!r} -- "
            "refusing to trust a record whose own declared identity was substituted after commit"
        )
    if url_source_observation_envelope_semantic_fingerprint(envelope) != envelope.get(
        "url_source_observation_semantic_fingerprint"
    ):
        raise UrlBootEnvelopeIntegrityError(
            f"resolved url_source_observation_envelope {envelope_id!r} own recomputed semantic "
            "fingerprint does not equal its own declared value -- refusing to trust any of its "
            "fields"
        )
    return envelope


def _reference_set(refs: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    members = [dict(ref) for ref in refs]
    members.sort(key=lambda ref: (ref.get("kind", ""), ref.get("id", "")))
    return {"collection_kind": "UNORDERED_SET", "members": members}


def _construct_provenance(envelope: Mapping[str, Any], project_id: str) -> dict[str, Any]:
    """Return the one, deterministic ``verification_result_provenance`` projection this handoff
    derives -- entirely from the real, resolved, integrity-checked Envelope, never from any field
    a caller-constructed :class:`~.types.UrlSourceObservationReceipt` merely claims.

    *target_refs*/*input_refs* name the Human Authority the real, committed Envelope itself
    records (Issue #69's own disclosed judgment call, the identical one
    ``runtime/evidence_handoff.py`` already makes for its own target's owning Project Binding: a
    URL Source Observation has no separate canonical Difference/Change/Evidence subject the way a
    Projection does, and unlike Runtime's own ``target_identity``, this package's
    ``source_identity`` carries no ``project_binding_ref`` field of its own -- ``human_authority_ref``
    is the one existing-owner reference the Envelope actually stores)."""

    refs = (dict(envelope["human_authority_ref"]),)
    observations = {
        "fetch_outcome": envelope["fetch_outcome"],
        "observed_content_fingerprint": envelope["observed_content_fingerprint"],
        "retrieved_at": envelope["retrieved_at"],
    }
    provenance = {
        "status": URL_OUTCOME_TO_RECEIPT_STATUS[envelope["fetch_outcome"]],
        "requirement_id": envelope["url_source_observation_envelope_id"],
        "selection_id": envelope["url_source_observation_envelope_id"],
        "project_id": project_id,
        "target_refs": _reference_set(refs),
        "verifier_identity": dict(envelope["adapter_identity"]),
        "selection_authority_ref": dict(envelope["human_authority_ref"]),
        "verification_boundary": {
            "requested_source_identity": dict(envelope["requested_source_identity"]),
            "boundary": dict(envelope["boundary"]),
            # P17-R1-F5: the exact Project Binding / Boot-observed State identity this
            # committed Envelope was made under -- resolved and integrity-checked, alongside
            # every other field, by the three-way + semantic-fingerprint check
            # ``resolve_and_verify_committed_envelope`` already performs above (both fields
            # participate in ``ENVELOPE_SEMANTIC_FIELDS``, so a tampered value here fails that
            # check before this function is ever reached).
            "project_binding_ref": dict(envelope["project_binding_ref"]),
            "boot_state_fingerprint": dict(envelope["boot_state_fingerprint"]),
        },
        "input_refs": _reference_set(refs),
        "observations": observations,
    }
    if set(provenance) != set(REQUIRED_PROVENANCE_FIELDS):
        raise UrlBootRequirementError(
            "constructed verification_result_provenance does not carry exactly the required "
            f"field set: {sorted(provenance)} != {sorted(REQUIRED_PROVENANCE_FIELDS)}"
        )
    return provenance


def route_url_observation_to_evidence(
    store: Any,
    receipt: UrlSourceObservationReceipt,
    project_id: str,
    evidence_request: Mapping[str, Any],
) -> dict[str, Any]:
    """Hand *receipt* off to the existing Evidence owner and return the one canonical Evidence
    record it derives from *evidence_request*.

    *evidence_request* must already be a real, Change-free,
    ``verification_observation_request``-grounded Evidence request. This function fabricates
    none of that; it only constructs and injects ``verification_result_provenance``, and
    re-verifies the derived record actually carries exactly that provenance before returning it.

    Every :class:`~manosube_agent_civilization.evidence.errors.EvidenceError` the existing owner
    itself raises propagates unchanged.
    """

    if not isinstance(receipt, UrlSourceObservationReceipt):
        raise UrlBootRequirementError(
            f"receipt must be a UrlSourceObservationReceipt instance, not {type(receipt)!r}"
        )
    if receipt.project_id != project_id:
        raise UrlBootRequirementError(
            "receipt's own originating project_id does not match the requested project_id -- a "
            f"receipt cannot be relabelled across projects: {receipt.project_id!r} != "
            f"{project_id!r}"
        )
    if receipt.status != "VERIFIED" or receipt.url_source_observation_envelope_id is None:
        # P17-C7/P17-R1-F1: a failed or refused fetch commits no url_source_observation_envelope
        # record at all -- there is nothing durable this handoff could ever resolve or
        # corroborate, so it is refused here rather than deriving Evidence from an
        # unverifiable, caller-claimed receipt.
        raise UrlBootRequirementError(
            f"receipt's own status is {receipt.status!r}, not 'VERIFIED' -- only a genuinely "
            "committed OBSERVED result names a real url_source_observation_envelope, and only "
            "that can ever be handed off as Evidence"
        )

    envelope = resolve_and_verify_committed_envelope(
        store, project_id, receipt.url_source_observation_envelope_id
    )

    # Complete receipt attestation required, the identical discipline
    # ``runtime/evidence_handoff.py`` already establishes: every one of receipt's own
    # Evidence-relevant fields must exactly equal the real, resolved Envelope's own content
    # before any Evidence is derived. A receipt forged in any single field, even with every
    # other field genuine, refuses here.
    if _plain(receipt.requested_source_identity) != envelope["requested_source_identity"]:
        raise UrlBootRequirementError(
            "receipt's own requested_source_identity does not match the real, committed "
            "Envelope's requested_source_identity"
        )
    if _plain(receipt.boundary) != envelope["boundary"]:
        raise UrlBootRequirementError(
            "receipt's own boundary does not match the real, committed Envelope's boundary"
        )
    if _plain(receipt.adapter_identity) != envelope["adapter_identity"]:
        raise UrlBootRequirementError(
            "receipt's own adapter_identity does not match the real, committed Envelope's "
            "adapter_identity"
        )
    if _plain(receipt.human_authority_ref) != envelope["human_authority_ref"]:
        raise UrlBootRequirementError(
            "receipt's own human_authority_ref does not match the real, committed Envelope's "
            "human_authority_ref"
        )
    expected_observations = {
        "fetch_outcome": envelope["fetch_outcome"],
        "observed_content_fingerprint": envelope["observed_content_fingerprint"],
        "retrieved_at": envelope["retrieved_at"],
    }
    if _plain(receipt.observations) != expected_observations:
        raise UrlBootRequirementError(
            "receipt's own observations do not match the real, committed Envelope's own "
            f"recorded observation: {_plain(receipt.observations)!r} != {expected_observations!r}"
        )
    expected_status = URL_OUTCOME_TO_RECEIPT_STATUS[envelope["fetch_outcome"]]
    if receipt.status != expected_status:
        raise UrlBootRequirementError(
            f"receipt's own status does not equal the outcome-derived status: "
            f"{receipt.status!r} != {expected_status!r}"
        )
    expected_input_refs = [dict(envelope["human_authority_ref"])]
    actual_input_refs = _plain(receipt.input_refs)
    if actual_input_refs != expected_input_refs:
        raise UrlBootRequirementError(
            "receipt's own input_refs do not equal the expected input refs derived from the "
            f"real, committed Envelope: {actual_input_refs!r} != {expected_input_refs!r}"
        )

    if not isinstance(evidence_request, Mapping):
        raise UrlBootRequirementError(
            f"evidence_request must be an explicit mapping, not {type(evidence_request)!r}"
        )
    if evidence_request.get("change_request") is not None:
        raise UrlBootRequirementError(
            "evidence_request must be Change-free -- a URL Source Observation Receipt never "
            "executes or grounds a Change"
        )
    if evidence_request.get("post_change_observation_request") is not None:
        raise UrlBootRequirementError(
            "evidence_request must carry no post_change_observation_request -- a URL Source "
            "Observation Receipt never grounds a Change result"
        )
    if evidence_request.get("verification_observation_request") is None:
        raise UrlBootRequirementError(
            "evidence_request must carry a verification_observation_request -- the one Evidence "
            "position (Change-Free Verification Evidence) this handoff produces"
        )
    if evidence_request.get("verification_result_provenance") is not None:
        raise UrlBootRequirementError(
            "evidence_request must not already carry a verification_result_provenance -- this "
            "handoff constructs it from the real, resolved Envelope itself"
        )

    provenance = _construct_provenance(envelope, project_id)
    request = dict(evidence_request)
    request["verification_result_provenance"] = provenance

    evidence = derive_evidence(request)

    if evidence["verification_result_provenance"] != provenance:
        raise UrlBootRequirementError(
            "the derived Evidence record's own verification_result_provenance does not exactly "
            "equal the one this handoff constructed from the real Envelope -- refusing to "
            "return a record whose provenance this handoff cannot confirm"
        )
    if evidence["target"]["project_id"] != project_id:
        raise UrlBootRequirementError(
            "the derived Evidence record names a different project than requested: "
            f"{evidence['target']['project_id']!r} != {project_id!r}"
        )

    return evidence


__all__ = ["resolve_and_verify_committed_envelope", "route_url_observation_to_evidence"]
