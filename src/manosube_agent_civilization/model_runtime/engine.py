"""The one Model Runtime record deriver (Phase 16, Issue #66).

```text
REAL, STORE-RESOLVED DIFFERENCE + BOUNDARY + AUTHORITY DECISION + LIVE PHASE 12 CONTRACT
→ CANONICAL, STATE-BOUND MODEL WORK UNIT
→ PROVIDER-NEUTRAL REQUEST IDENTITY (computable before any adapter exists)
→ REAL ADAPTER RESULT, INDEPENDENTLY BOUNDED AND RECLASSIFIED
→ CANONICAL MODEL EXECUTION ENVELOPE
→ CANONICAL MODEL SWAP / SESSION RECOVERY RECEIPT
```

This module builds and schema-validates canonical records from already-resolved, already-
verified inputs. It resolves nothing itself, calls no Store, no Boot, no Temporary Agent, no
Authority and no Adapter -- :mod:`~manosube_agent_civilization.model_runtime.route` owns every
one of those calls and is the only caller of the four ``derive_*`` functions below. This is the
identical "derivation is pure, resolution is the route's job" discipline every other Kernel
engine in this repository already keeps (compare
:func:`~manosube_agent_civilization.runtime.engine.derive_runtime_observation_envelope`).

**Evidence requirements are derived, never supplied.** :func:`canonical_evidence_requirements`
reads the *existing* Evidence owner's own closed request-key set
(:data:`~manosube_agent_civilization.evidence.engine.REQUIRED_REQUEST_KEYS`) and the ten
``verification_result_provenance`` fields ``evidence.schema.json`` itself requires. No caller
may state them, so there is no fourth Evidence request shape here and no way for a Work Unit to
claim an Evidence obligation the real Evidence owner does not actually impose.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from manosube_agent_civilization.difference.errors import DifferenceValidationError
from manosube_agent_civilization.difference.validation import (
    SCHEMA_BASE as CANONICAL_SCHEMA_BASE,
    validate_record as _validate_canonical_record,
    validate_subrecord as _validate_canonical_subrecord,
)
from manosube_agent_civilization.evidence.engine import (
    CHANGE_FREE_VERIFICATION_EVIDENCE,
    REQUIRED_REQUEST_KEYS as EVIDENCE_REQUIRED_REQUEST_KEYS,
)

from .errors import ModelRuntimeRequirementError
from .identity import (
    model_execution_envelope_id,
    model_execution_envelope_semantic_fingerprint,
    model_swap_receipt_id,
    model_swap_receipt_semantic_fingerprint,
    model_work_unit_id,
    model_work_unit_semantic_fingerprint,
    session_recovery_receipt_id,
    session_recovery_receipt_semantic_fingerprint,
)
from .types import MODEL_EXECUTION_OUTCOMES

MODEL_RUNTIME_SCHEMA_BASE = CANONICAL_SCHEMA_BASE + "model_runtime/"
#: Authority's own schema base, computed from the identical shared root
#: :data:`MODEL_RUNTIME_SCHEMA_BASE` above already uses, never a second literal and never
#: imported from :mod:`manosube_agent_civilization.authority.conformance` -- the identical
#: independent-computation-avoids-an-import-cycle reasoning that module's own
#: ``_BINDING_SCHEMA_BASE`` records.
AUTHORITY_SCHEMA_BASE = CANONICAL_SCHEMA_BASE + "authority/"
SCHEMA_VERSION = "0.1"

BOUNDARY_SCHEMA_NAME = "model_execution_boundary.schema.json"
WORK_UNIT_SCHEMA_NAME = "model_work_unit.schema.json"
ENVELOPE_SCHEMA_NAME = "model_execution_envelope.schema.json"
SWAP_RECEIPT_SCHEMA_NAME = "model_swap_receipt.schema.json"
RECOVERY_RECEIPT_SCHEMA_NAME = "session_recovery_receipt.schema.json"
DECISION_SCHEMA_NAME = "model_execution_decision.schema.json"

#: The identical ten fields ``evidence.schema.json``'s own ``verification_result_provenance``
#: requires -- see ``runtime/evidence_handoff.py``'s and ``projection/receipt_handoff.py``'s own
#: identical constants. Restated here rather than imported from either, for the identical
#: adapter-layer-decoupling reason those two modules already state for one another; the contract
#: test suite holds all three equal.
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


def canonical_evidence_requirements() -> dict[str, Any]:
    """The one Evidence-requirement projection a Model Work Unit may ever carry.

    Derived from the existing Evidence owner's own closed shapes, never stated by a caller and
    never invented here: the position is the already-ratified
    ``CHANGE_FREE_VERIFICATION_EVIDENCE`` one
    :mod:`~manosube_agent_civilization.model_runtime.evidence_handoff` actually produces, the
    request keys are exactly ``evidence.engine.REQUIRED_REQUEST_KEYS``, and the provenance
    fields are exactly :data:`REQUIRED_PROVENANCE_FIELDS`.
    """

    return {
        "evidence_position": CHANGE_FREE_VERIFICATION_EVIDENCE,
        "required_request_keys": sorted(EVIDENCE_REQUIRED_REQUEST_KEYS),
        "required_provenance_fields": list(REQUIRED_PROVENANCE_FIELDS),
    }


def _require_schema_valid_record(
    value: Any, schema_name: str, context: str, base: str = MODEL_RUNTIME_SCHEMA_BASE
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ModelRuntimeRequirementError(f"{context} must be an explicit mapping: {value!r}")
    body = dict(value)
    try:
        _validate_canonical_record(body, schema_name, base=base)
    except DifferenceValidationError as error:
        raise ModelRuntimeRequirementError(f"{context} is not schema-valid: {error}") from error
    return body


def require_valid_model_execution_decision(decision: Any) -> dict[str, Any]:
    """Return *decision* as a plain ``dict``, proved completely valid against the **Authority
    owner's own** canonical ``model_execution_decision.schema.json``.

    This package validates the record against the owning package's schema and never restates
    what a Model Execution Decision is: the decision itself is minted only by
    :func:`~manosube_agent_civilization.authority.evaluate_model_execution_authorization`, and
    this function exists so a *Store-resolved* one is never trusted on shape alone either.
    """

    return _require_schema_valid_record(
        decision,
        DECISION_SCHEMA_NAME,
        "resolved model_execution_decision",
        base=AUTHORITY_SCHEMA_BASE,
    )


def require_valid_model_execution_boundary(boundary: Any) -> dict[str, Any]:
    """Return *boundary* as a plain ``dict``, proved completely valid against the canonical
    ``model_execution_boundary.schema.json`` -- a Store-resolved record is never trusted on
    shape alone, exactly as no caller-supplied record ever is."""

    return _require_schema_valid_record(
        boundary, BOUNDARY_SCHEMA_NAME, "resolved model_execution_boundary"
    )


def require_valid_model_work_unit(work_unit: Any) -> dict[str, Any]:
    """Return *work_unit* as a plain ``dict``, proved completely valid against the canonical
    ``model_work_unit.schema.json``."""

    return _require_schema_valid_record(
        work_unit, WORK_UNIT_SCHEMA_NAME, "resolved model_work_unit"
    )


def require_valid_model_execution_envelope(envelope: Any) -> dict[str, Any]:
    """Return *envelope* as a plain ``dict``, proved completely valid against the canonical
    ``model_execution_envelope.schema.json``."""

    return _require_schema_valid_record(
        envelope, ENVELOPE_SCHEMA_NAME, "resolved model_execution_envelope"
    )


def require_valid_timestamp(value: Any, context: str) -> str:
    """Require *value* to be one canonical UTC ``Z``-suffixed timestamp, in exactly the grammar
    ``common/timestamp.schema.json`` declares -- proved *before* any adapter is reached, the
    identical P15-R1-F2 discipline :func:`~manosube_agent_civilization.runtime.engine.
    require_valid_timestamp` already establishes for its own package."""

    try:
        _validate_canonical_subrecord(
            value,
            WORK_UNIT_SCHEMA_NAME,
            "#/properties/opened_at",
            base=MODEL_RUNTIME_SCHEMA_BASE,
        )
    except DifferenceValidationError as error:
        raise ModelRuntimeRequirementError(
            f"{context} is not a canonical UTC timestamp: {value!r}"
        ) from error
    return str(value)


def require_valid_semantic_fingerprint(value: Any, context: str) -> dict[str, Any]:
    """Require *value* to be one canonical State semantic fingerprint object, in exactly the
    shape ``common/fingerprint.schema.json`` declares."""

    try:
        _validate_canonical_subrecord(
            value,
            WORK_UNIT_SCHEMA_NAME,
            "#/properties/opened_semantic_fingerprint",
            base=MODEL_RUNTIME_SCHEMA_BASE,
        )
    except DifferenceValidationError as error:
        raise ModelRuntimeRequirementError(
            f"{context} is not a canonical State semantic fingerprint: {value!r}"
        ) from error
    return dict(value)


def require_valid_adapter_identity(value: Any, context: str) -> dict[str, Any]:
    """Require *value* to be the complete, closed ``adapter_identity`` shape --
    exactly ``adapter``/``version``, both non-empty strings, no other property -- proved
    *before* :func:`~manosube_agent_civilization.model_runtime.route.
    model_execution_request_identity` is computed and before an adapter is ever reached
    (Structural Review Round 1, P16-R1-F3), the identical P15-R1-F2 discipline this module's
    own :func:`require_valid_timestamp` already establishes for its own package.

    An empty mapping, a missing ``adapter`` or ``version``, a wrong-typed one, or a forbidden
    extra field are every one of them a schema violation of
    ``model_execution_envelope.schema.json#/$defs/adapter_identity`` -- the identical closed
    shape :func:`derive_model_execution_envelope` itself commits an adapter's declared identity
    into -- so this reuses that one canonical projection rather than restating a second,
    possibly divergent, adapter-identity vocabulary here.
    """

    try:
        _validate_canonical_subrecord(
            value,
            ENVELOPE_SCHEMA_NAME,
            "#/$defs/adapter_identity",
            base=MODEL_RUNTIME_SCHEMA_BASE,
        )
    except DifferenceValidationError as error:
        raise ModelRuntimeRequirementError(
            f"{context} is not the canonical closed adapter_identity shape (exactly 'adapter' "
            f"and 'version', both non-empty strings, no other property): {value!r}"
        ) from error
    return dict(value)


def derive_model_work_unit(
    *,
    project_id: str,
    project_binding_ref: dict[str, Any],
    opened_state_revision: int,
    opened_semantic_fingerprint: dict[str, Any],
    difference_ref: dict[str, Any],
    required_capability: str,
    authority_ref: dict[str, Any],
    boundary_ref: dict[str, Any],
    opened_at: str,
) -> dict[str, Any]:
    """Return one canonical, schema-valid, content-addressed Model Work Unit record.

    Every argument must already be real: the Difference, the Boundary and the Authority Decision
    must already have been Store-resolved and independently re-verified by the caller, and the
    State snapshot must already have come from a genuine Boot through the Phase 12 Temporary
    Agent Execution Contract. This function performs no Store I/O of any kind, reaches no
    Adapter, and evaluates no Authority.

    ``evidence_requirements`` is **not** a parameter: it is derived, here, from the existing
    Evidence owner's own shapes (:func:`canonical_evidence_requirements`).
    """

    work_unit: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "project_binding_ref": dict(project_binding_ref),
        "opened_state_revision": opened_state_revision,
        "opened_semantic_fingerprint": dict(opened_semantic_fingerprint),
        "difference_ref": dict(difference_ref),
        "required_capability": required_capability,
        "authority_ref": dict(authority_ref),
        "boundary_ref": dict(boundary_ref),
        "evidence_requirements": canonical_evidence_requirements(),
        "opened_at": opened_at,
    }
    work_unit["model_work_unit_id"] = model_work_unit_id(work_unit)
    work_unit["model_work_unit_semantic_fingerprint"] = model_work_unit_semantic_fingerprint(
        work_unit
    )
    _validate_canonical_record(work_unit, WORK_UNIT_SCHEMA_NAME, base=MODEL_RUNTIME_SCHEMA_BASE)
    return work_unit


def derive_model_execution_envelope(
    *,
    project_id: str,
    project_binding_ref: dict[str, Any],
    model_work_unit_ref: dict[str, Any],
    model_execution_request_identity: str,
    executed_state_revision: int,
    executed_semantic_fingerprint: dict[str, Any],
    adapter_identity: dict[str, Any],
    executed_at: str,
    execution_outcome: str,
    normalized_candidate_kind: str | None,
    normalized_candidate: dict[str, Any] | None,
    normalized_candidate_fingerprint: str | None,
    difference_ref: dict[str, Any],
    required_capability: str,
    authority_ref: dict[str, Any],
    boundary_ref: dict[str, Any],
    evidence_requirements: dict[str, Any],
    human_authority_ref: dict[str, Any],
) -> dict[str, Any]:
    """Return one canonical, schema-valid Model Execution Envelope record.

    *execution_outcome* / *normalized_candidate* / *normalized_candidate_fingerprint* must
    already be the route's own independently-bounded and reclassified result, never an adapter's
    raw, untrusted report; *model_execution_request_identity* must already have been recomputed
    by the caller from the real resolved Work Unit and the real current State.
    """

    if execution_outcome not in MODEL_EXECUTION_OUTCOMES:
        raise ModelRuntimeRequirementError(
            f"execution_outcome is not a recognized outcome: {execution_outcome!r}"
        )

    envelope: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "project_binding_ref": dict(project_binding_ref),
        "model_work_unit_ref": dict(model_work_unit_ref),
        "model_execution_request_identity": model_execution_request_identity,
        "executed_state_revision": executed_state_revision,
        "executed_semantic_fingerprint": dict(executed_semantic_fingerprint),
        "adapter_identity": dict(adapter_identity),
        "executed_at": executed_at,
        "execution_outcome": execution_outcome,
        "normalized_candidate_kind": normalized_candidate_kind,
        "normalized_candidate": (
            None if normalized_candidate is None else dict(normalized_candidate)
        ),
        "normalized_candidate_fingerprint": normalized_candidate_fingerprint,
        "difference_ref": dict(difference_ref),
        "required_capability": required_capability,
        "authority_ref": dict(authority_ref),
        "boundary_ref": dict(boundary_ref),
        "evidence_requirements": dict(evidence_requirements),
        "human_authority_ref": dict(human_authority_ref),
    }
    envelope["model_execution_envelope_id"] = model_execution_envelope_id(envelope)
    envelope["model_execution_semantic_fingerprint"] = (
        model_execution_envelope_semantic_fingerprint(envelope)
    )
    _validate_canonical_record(envelope, ENVELOPE_SCHEMA_NAME, base=MODEL_RUNTIME_SCHEMA_BASE)
    return envelope


def derive_model_swap_receipt(
    *,
    project_id: str,
    project_binding_ref: dict[str, Any],
    model_work_unit_ref: dict[str, Any],
    predecessor_execution_ref: dict[str, Any],
    predecessor_adapter_identity: dict[str, Any],
    predecessor_state_revision: int,
    predecessor_semantic_fingerprint: dict[str, Any],
    successor_execution_ref: dict[str, Any],
    successor_adapter_identity: dict[str, Any],
    successor_state_revision: int,
    successor_semantic_fingerprint: dict[str, Any],
    difference_ref: dict[str, Any],
    required_capability: str,
    authority_ref: dict[str, Any],
    boundary_ref: dict[str, Any],
    evidence_requirements: dict[str, Any],
    recorded_at: str,
) -> dict[str, Any]:
    """Return one canonical, schema-valid Model Swap Receipt record.

    Both adapter identities must already have been read off the two real, Store-resolved
    Envelopes and proved genuinely different by the caller; every continuity field must already
    have been proved equal across both.
    """

    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "project_binding_ref": dict(project_binding_ref),
        "model_work_unit_ref": dict(model_work_unit_ref),
        "predecessor_execution_ref": dict(predecessor_execution_ref),
        "predecessor_adapter_identity": dict(predecessor_adapter_identity),
        "predecessor_state_revision": predecessor_state_revision,
        "predecessor_semantic_fingerprint": dict(predecessor_semantic_fingerprint),
        "successor_execution_ref": dict(successor_execution_ref),
        "successor_adapter_identity": dict(successor_adapter_identity),
        "successor_state_revision": successor_state_revision,
        "successor_semantic_fingerprint": dict(successor_semantic_fingerprint),
        "difference_ref": dict(difference_ref),
        "required_capability": required_capability,
        "authority_ref": dict(authority_ref),
        "boundary_ref": dict(boundary_ref),
        "evidence_requirements": dict(evidence_requirements),
        "recorded_at": recorded_at,
    }
    receipt["model_swap_receipt_id"] = model_swap_receipt_id(receipt)
    receipt["model_swap_receipt_semantic_fingerprint"] = model_swap_receipt_semantic_fingerprint(
        receipt
    )
    _validate_canonical_record(receipt, SWAP_RECEIPT_SCHEMA_NAME, base=MODEL_RUNTIME_SCHEMA_BASE)
    return receipt


def derive_session_recovery_receipt(
    *,
    project_id: str,
    project_binding_ref: dict[str, Any],
    model_work_unit_ref: dict[str, Any],
    recovered_state_revision: int,
    recovered_semantic_fingerprint: dict[str, Any],
    difference_ref: dict[str, Any],
    required_capability: str,
    authority_ref: dict[str, Any],
    boundary_ref: dict[str, Any],
    evidence_requirements: dict[str, Any],
    recovered_at: str,
) -> dict[str, Any]:
    """Return one canonical, schema-valid Session Recovery Receipt record.

    Every field must already have been re-resolved from the canonical Store and independently
    re-verified by the caller -- nothing here may be carried over in memory from the lost
    session, which is the entire point of the record (P16-C5).
    """

    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "project_binding_ref": dict(project_binding_ref),
        "model_work_unit_ref": dict(model_work_unit_ref),
        "recovered_state_revision": recovered_state_revision,
        "recovered_semantic_fingerprint": dict(recovered_semantic_fingerprint),
        "difference_ref": dict(difference_ref),
        "required_capability": required_capability,
        "authority_ref": dict(authority_ref),
        "boundary_ref": dict(boundary_ref),
        "evidence_requirements": dict(evidence_requirements),
        "recovered_at": recovered_at,
    }
    receipt["session_recovery_receipt_id"] = session_recovery_receipt_id(receipt)
    receipt["session_recovery_receipt_semantic_fingerprint"] = (
        session_recovery_receipt_semantic_fingerprint(receipt)
    )
    _validate_canonical_record(
        receipt, RECOVERY_RECEIPT_SCHEMA_NAME, base=MODEL_RUNTIME_SCHEMA_BASE
    )
    return receipt
