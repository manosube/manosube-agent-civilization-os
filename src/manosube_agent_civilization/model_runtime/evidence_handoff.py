"""The one public Model-Execution-to-Evidence handoff (Phase 16, Issue #66).

Reuses the identical, already-ratified Change-Free Verification Evidence position
(``evidence/engine.py``'s ``CHANGE_FREE_VERIFICATION_EVIDENCE``) that Projection's own
:mod:`~manosube_agent_civilization.projection.receipt_handoff` and Runtime's own
:mod:`~manosube_agent_civilization.runtime.evidence_handoff` already occupy -- a normalized,
bounded model candidate is structurally the same kind of independent, Change-free confirmation
proposal, so this module calls the identical existing owner
(:func:`~manosube_agent_civilization.evidence.derive_evidence`, called exactly once) rather than
adding a second Evidence, Observation, Reflow or Closure owner.

**This is where P16-C3's "cannot self-accept its own Evidence" actually lands.** A model's
output reaches Evidence only as an *Evidence candidate*: this module resolves the real,
committed ``model_execution_envelope`` from the Store through the identical canonical Envelope
admission execution/swap/recovery already apply
(:func:`~manosube_agent_civilization.model_runtime.route.resolve_and_verify_committed_envelope`,
Structural Review Round 2, P16-R2-F1) -- never trusting the caller-held
:class:`~manosube_agent_civilization.model_runtime.types.ModelExecutionReceipt`, which remains a
publicly constructible dataclass -- requires every one of the receipt's own fields to exactly
equal what that real Envelope actually recorded, preflights the request's own canonical
Difference through the existing Observation/Difference owners before the existing Evidence owner
is ever called (P16-R2-F2), and then constructs ``verification_result_provenance`` **itself**,
from the resolved Envelope alone. The adapter's own identity is recorded as the
``verifier_identity`` -- an honest statement of who produced the candidate -- and decides
nothing: whether the request is admissible Evidence at all is answered by the existing Evidence
owner's own Change-free position, unchanged, and this module refuses to return a record whose
provenance it cannot itself confirm afterwards.

**No re-execution at handoff (deliberate, disclosed).** Projection's own handoff re-observes the
live external artifact; this one does not, for the identical reason Runtime's own handoff states
for itself and one more of its own: a model invocation is not idempotent, so "re-running the
model to check the receipt" would compare two genuinely different candidates and would silently
redefine "this receipt is genuine" into "the model would say the same thing again", which is
neither what Issue #66 asks Evidence to attest to nor something a replaceable adapter could ever
guarantee. Corroboration here means Store resolution and exact field equality against the real,
committed fact -- never a second model call.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from manosube_agent_civilization.evidence import derive_evidence, derive_request_difference

from .engine import REQUIRED_PROVENANCE_FIELDS
from .errors import ModelRuntimeRequirementError
from .route import DIFFERENCE_RECORD_KIND, resolve_and_verify_committed_envelope
from .types import MODEL_OUTCOME_TO_RECEIPT_STATUS, ModelExecutionReceipt


def _plain(value: Any) -> Any:
    """Recursively rebuild *value* as plain ``dict``/``list``/scalar -- undoes
    :class:`~manosube_agent_civilization.model_runtime.types.ModelExecutionReceipt`'s own deep
    freeze (``MappingProxyType``/``tuple``) so a receipt field can be compared for genuine
    structural equality against the real, Store-resolved Envelope's own plain ``dict``/``list``
    fields, which a bare ``!=`` would otherwise report as unequal on container type alone."""

    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(item) for item in value]
    return value


def _reference_set(refs: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    members: list[dict[str, Any]] = []
    for ref in refs:
        member = dict(ref)
        if member not in members:
            members.append(member)
    members.sort(key=lambda ref: (str(ref.get("kind", "")), str(ref.get("id", ""))))
    return {"collection_kind": "UNORDERED_SET", "members": members}


def _construct_provenance(envelope: Mapping[str, Any], project_id: str) -> dict[str, Any]:
    """The one deterministic ``verification_result_provenance`` projection this handoff derives
    -- entirely from the real, resolved, integrity-checked Envelope, never from any field a
    caller-constructed receipt merely claims.

    *target_refs*/*input_refs* name the real Difference this work is about **and** the State-bound
    Work Unit it was executed under. Unlike a Runtime Observation, a model execution genuinely
    has a canonical Difference subject -- naming it is what makes this candidate attributable to
    the work it was authorized for, rather than to the Project Binding at large.
    """

    refs = (dict(envelope["difference_ref"]), dict(envelope["model_work_unit_ref"]))
    observations = {
        "execution_outcome": envelope["execution_outcome"],
        "normalized_candidate_kind": envelope["normalized_candidate_kind"],
        "normalized_candidate_fingerprint": envelope["normalized_candidate_fingerprint"],
        "executed_at": envelope["executed_at"],
    }
    provenance = {
        "status": MODEL_OUTCOME_TO_RECEIPT_STATUS[envelope["execution_outcome"]],
        "requirement_id": envelope["model_execution_envelope_id"],
        "selection_id": envelope["model_execution_envelope_id"],
        "project_id": project_id,
        "target_refs": _reference_set(refs),
        # An honest statement of *who produced the candidate*, and nothing more: the adapter
        # decides no sufficiency here, and this record is not accepted because it names itself.
        "verifier_identity": dict(envelope["adapter_identity"]),
        "selection_authority_ref": dict(envelope["human_authority_ref"]),
        "verification_boundary": {
            "boundary_ref": dict(envelope["boundary_ref"]),
            "required_capability": envelope["required_capability"],
            "authority_ref": dict(envelope["authority_ref"]),
            "evidence_requirements": dict(envelope["evidence_requirements"]),
        },
        "input_refs": _reference_set(refs),
        "observations": observations,
    }
    if set(provenance) != set(REQUIRED_PROVENANCE_FIELDS):
        raise ModelRuntimeRequirementError(
            "constructed verification_result_provenance does not carry exactly the required "
            f"field set: {sorted(provenance)} != {sorted(REQUIRED_PROVENANCE_FIELDS)}"
        )
    return provenance


def route_model_execution_to_evidence(
    store: Any,
    receipt: ModelExecutionReceipt,
    project_id: str,
    evidence_request: Mapping[str, Any],
) -> dict[str, Any]:
    """Hand *receipt* off to the existing Evidence owner and return the one canonical Evidence
    record it derives from *evidence_request*.

    *evidence_request* must already be a real, Change-free,
    ``verification_observation_request``-grounded Evidence request. This function fabricates none
    of that; it only constructs and injects ``verification_result_provenance``, and re-verifies
    the derived record actually carries exactly that provenance before returning it.

    Every :class:`~manosube_agent_civilization.evidence.errors.EvidenceError` the existing owner
    itself raises propagates unchanged -- this module never catches, reclassifies, or works
    around a refusal by the real Evidence owner.
    """

    if not isinstance(receipt, ModelExecutionReceipt):
        raise ModelRuntimeRequirementError(
            f"receipt must be a ModelExecutionReceipt instance, not {type(receipt)!r}"
        )
    # Structural Review Round 2, P16-R2-F1: the identical canonical Envelope admission
    # execution/swap/recovery already apply -- schema-valid, and its own identity and semantic
    # fingerprint independently recomputed from its own content equal to both its own declared
    # values and the Store lookup key -- shared here rather than reimplemented as a divergent,
    # partial check (this route previously verified only the semantic fingerprint, which the
    # declared identity field is itself excluded from, so a Store record whose declared identity
    # was substituted after commit, with every other field genuine, passed it undetected).
    envelope = resolve_and_verify_committed_envelope(
        store, project_id, receipt.model_execution_envelope_id
    )
    if receipt.project_id != project_id or envelope["project_id"] != project_id:
        raise ModelRuntimeRequirementError(
            "receipt's own originating project_id does not match the requested project_id -- a "
            f"receipt cannot be relabelled across projects: {receipt.project_id!r}, "
            f"envelope={envelope['project_id']!r}, requested={project_id!r}"
        )

    # Structural Review Round 1, P16-R1-F1: a model execution that did not produce an accepted
    # candidate is never handed to the existing Evidence owner. Every one of the six
    # non-accepting outcomes -- UNAVAILABLE, REFUSED, MALFORMED, TIMEOUT, CANCELLED,
    # INCOMPLETE_EVIDENCE -- is refused here, before ``derive_evidence`` is ever reached, so
    # recording an outcome only inside ``verification_result_provenance.status`` (which
    # Evidence's own sufficiency evaluator never reads) can never let a failed execution become
    # sufficient Evidence through this route's own top-level ``status``.
    #
    # Checked through the one shared outcome-to-status mapping rather than a literal
    # ``"CANDIDATE_ACCEPTED"`` comparison here: that string is deliberately confined to
    # ``route.py``'s own normalizer and ``types.py``'s own vocabulary declaration (this
    # package's own static conformance suite proves the confinement), and
    # ``MODEL_OUTCOME_TO_RECEIPT_STATUS`` already proves exactly one outcome maps to
    # ``"VERIFIED"`` -- so this reads as "not the one outcome that is Evidence-eligible" without
    # restating that outcome's own name a second time.
    if MODEL_OUTCOME_TO_RECEIPT_STATUS.get(envelope["execution_outcome"]) != "VERIFIED":
        raise ModelRuntimeRequirementError(
            f"resolved Envelope {receipt.model_execution_envelope_id!r} own execution_outcome "
            f"({envelope['execution_outcome']!r}) is not the one outcome the existing Evidence "
            "owner's own VERIFIED status maps from -- a model execution that did not produce "
            "an accepted candidate is never handed to the existing Evidence owner"
        )
    if (
        envelope["normalized_candidate_kind"] is None
        or envelope["normalized_candidate"] is None
        or envelope["normalized_candidate_fingerprint"] is None
    ):
        raise ModelRuntimeRequirementError(
            f"resolved Envelope {receipt.model_execution_envelope_id!r} declares "
            "execution_outcome=CANDIDATE_ACCEPTED but carries no complete normalized "
            "candidate -- refusing to hand an incomplete accepted candidate to the existing "
            "Evidence owner"
        )

    # Complete receipt attestation required, the identical discipline Projection's own Round 4
    # (P14-R4-F2) established and Runtime reuses: every one of the receipt's own
    # Evidence-relevant fields must exactly equal the real, resolved Envelope's own content
    # before any Evidence is derived. A receipt forged in any single field, even with every
    # other field genuine, refuses here.
    for receipt_field, envelope_field in (
        ("model_work_unit_ref", "model_work_unit_ref"),
        ("adapter_identity", "adapter_identity"),
        ("difference_ref", "difference_ref"),
        ("authority_ref", "authority_ref"),
        ("boundary_ref", "boundary_ref"),
        ("evidence_requirements", "evidence_requirements"),
        ("human_authority_ref", "human_authority_ref"),
    ):
        if _plain(getattr(receipt, receipt_field)) != envelope[envelope_field]:
            raise ModelRuntimeRequirementError(
                f"receipt's own {receipt_field} does not match the real, committed Envelope's "
                f"{envelope_field}"
            )
    if receipt.required_capability != envelope["required_capability"]:
        raise ModelRuntimeRequirementError(
            "receipt's own required_capability does not match the real, committed Envelope's: "
            f"{receipt.required_capability!r} != {envelope['required_capability']!r}"
        )
    expected_observations = {
        "execution_outcome": envelope["execution_outcome"],
        "normalized_candidate_fingerprint": envelope["normalized_candidate_fingerprint"],
        "executed_at": envelope["executed_at"],
    }
    if _plain(receipt.observations) != expected_observations:
        raise ModelRuntimeRequirementError(
            "receipt's own observations do not match the real, committed Envelope's own recorded "
            f"execution: {_plain(receipt.observations)!r} != {expected_observations!r}"
        )
    expected_status = MODEL_OUTCOME_TO_RECEIPT_STATUS[envelope["execution_outcome"]]
    if receipt.status != expected_status:
        raise ModelRuntimeRequirementError(
            "receipt's own status does not equal the outcome-derived status: "
            f"{receipt.status!r} != {expected_status!r}"
        )
    expected_input_refs = [
        dict(envelope["difference_ref"]),
        dict(envelope["model_work_unit_ref"]),
    ]
    if _plain(receipt.input_refs) != expected_input_refs:
        raise ModelRuntimeRequirementError(
            "receipt's own input_refs do not equal the expected input refs derived from the "
            f"real, committed Envelope: {_plain(receipt.input_refs)!r} != {expected_input_refs!r}"
        )

    if not isinstance(evidence_request, Mapping):
        raise ModelRuntimeRequirementError(
            f"evidence_request must be an explicit mapping, not {type(evidence_request)!r}"
        )
    if evidence_request.get("change_request") is not None:
        raise ModelRuntimeRequirementError(
            "evidence_request must be Change-free -- a model execution never executes or grounds "
            "a Change"
        )
    if evidence_request.get("post_change_observation_request") is not None:
        raise ModelRuntimeRequirementError(
            "evidence_request must carry no post_change_observation_request -- a model execution "
            "never grounds a Change result"
        )
    if evidence_request.get("verification_observation_request") is None:
        raise ModelRuntimeRequirementError(
            "evidence_request must carry a verification_observation_request -- the one Evidence "
            "position (Change-Free Verification Evidence) this handoff produces"
        )
    if evidence_request.get("verification_result_provenance") is not None:
        raise ModelRuntimeRequirementError(
            "evidence_request must not already carry a verification_result_provenance -- this "
            "handoff constructs it from the real, resolved Envelope itself, so a model's own "
            "output can never supply the provenance that would accept it"
        )

    # Structural Review Round 2, P16-R2-F2: the request's own canonical Difference is
    # reproduced through the existing Observation/Difference owners -- the identical
    # reproduction ``derive_evidence`` itself performs internally, factored once as
    # :func:`~manosube_agent_civilization.evidence.derive_request_difference` -- and compared
    # against the real, resolved Envelope's own ``difference_ref`` *before* the existing
    # Evidence owner is ever called. Round 1's own equality check refused a same-project
    # Difference-A-execution-paired-with-Difference-B request only after ``derive_evidence`` had
    # already run; this preflight is what makes that refusal a zero-call one, and the Round 1
    # check itself is kept below, unchanged, as defense in depth.
    preflight_difference = derive_request_difference(evidence_request)
    preflight_difference_ref = {
        "kind": DIFFERENCE_RECORD_KIND,
        "id": preflight_difference["difference_id"],
    }
    if preflight_difference_ref != envelope["difference_ref"]:
        raise ModelRuntimeRequirementError(
            "the evidence_request's own canonical Difference, reproduced through the existing "
            f"Observation/Difference owners before any Evidence is derived, is not the "
            f"Difference this model execution was actually about: {preflight_difference_ref!r} "
            f"!= {envelope['difference_ref']!r} -- an evidence_request may not silently rebind "
            "a model's already-executed work from one Difference to another"
        )

    provenance = _construct_provenance(envelope, project_id)
    request = dict(evidence_request)
    request["verification_result_provenance"] = provenance

    evidence = derive_evidence(request)

    # Structural Review Round 1, P16-R1-F2: the Evidence owner derives its own record's
    # top-level ``difference_ref`` from *this request's own* ``difference_request`` (Evidence's
    # own re-observation-and-derivation, never a caller-supplied reference) -- which is exactly
    # what lets a caller execute a Work Unit bound to Difference A, then hand this route an
    # otherwise-valid *evidence_request* whose own ``difference_request`` re-derives Difference
    # B in the same project. Requiring exact equality against the real, resolved Envelope's own
    # ``difference_ref`` here is what refuses that silent rebinding before any Evidence record
    # is ever returned to a caller who could act on it -- retained as defense in depth alongside
    # the preflight above (Structural Review Round 2, P16-R2-F2).
    if evidence["difference_ref"] != envelope["difference_ref"]:
        raise ModelRuntimeRequirementError(
            "the derived Evidence record names a different Difference than the one this model "
            f"execution was actually about: {evidence['difference_ref']!r} != "
            f"{envelope['difference_ref']!r} -- an evidence_request may not silently rebind a "
            "model's already-executed work from one Difference to another"
        )

    if evidence["verification_result_provenance"] != provenance:
        raise ModelRuntimeRequirementError(
            "the derived Evidence record's own verification_result_provenance does not exactly "
            "equal the one this handoff constructed from the real Envelope -- refusing to return "
            "a record whose provenance this handoff cannot confirm"
        )
    if evidence["target"]["project_id"] != project_id:
        raise ModelRuntimeRequirementError(
            "the derived Evidence record names a different project than requested: "
            f"{evidence['target']['project_id']!r} != {project_id!r}"
        )

    return evidence


__all__ = ["route_model_execution_to_evidence"]
