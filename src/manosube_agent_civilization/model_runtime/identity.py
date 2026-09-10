"""Deterministic Model Runtime identities (Phase 16, Issue #66).

Canonical serialization has one owner in this repository -- ``state.canonicalize`` -- and this
module reads it rather than restating it, exactly as every other owner's own ``identity.py``
already does.

Five distinct identities exist here, deliberately never conflated -- exactly the four Issue
#66's own V1 row names ("provider-neutral request, model result, model-swap receipt, and
recovery receipt"), plus the State-bound Work Unit identity all four of them ultimately hang
from:

- :func:`model_execution_boundary_id` / :func:`model_execution_boundary_semantic_fingerprint`
  -- *what the model's output may be used for*: the identity of the canonical, Store-committed,
  Human-declared Model Execution Boundary a Work Unit references.
- :func:`model_work_unit_id` / :func:`model_work_unit_semantic_fingerprint` -- *what work this
  is*: the identity of the canonical, Store-committed, immutable State-bound Work Unit. It
  covers the exact State snapshot it was opened against, the Difference it is about, the
  capability it requires, the Authority Decision that permitted it, the Boundary that bounds it
  and the Evidence requirements its eventual candidate must satisfy -- so two Agents resolving
  "the same Work Unit" are resolving the same *meaning*, not merely the same string.
- :func:`model_execution_request_identity` -- *what was asked, at this exact instant, of this
  exact adapter*: a pure function of the resolved Work Unit's own id, the current State
  revision/semantic fingerprint, and the adapter's own declared identity. Computable **before
  any adapter is reached**, independent of whatever result it later returns, and carrying zero
  provider-specific payload. This is P16-C1's provider-neutral execution binding, expressed as
  a value.
- :func:`model_execution_envelope_id` / :func:`model_execution_envelope_semantic_fingerprint`
  -- *what came back*: the identity of the committed fact. Follows the single-projection
  convention every other owner module already uses (see ``evidence/identity.py``): one canonical
  projection, hashed twice under two different prefixes/encodings, covering every semantically
  meaningful field including the outcome itself, so tampering any field is detectable
  independently of the record's own id.
- :func:`model_swap_receipt_id` / :func:`model_swap_receipt_semantic_fingerprint` and
  :func:`session_recovery_receipt_id` / :func:`session_recovery_receipt_semantic_fingerprint`
  -- *that continuity actually held*: the identities of the two committed continuity facts
  P16-C4 and P16-C5 require.

Every one of these projections is **closed and complete**: it is exactly the record minus its
own two digest fields, so every authority-bearing field (``authority_ref``), every reference
field (``difference_ref``, ``boundary_ref``, ``model_work_unit_ref``, the two execution refs,
``project_binding_ref``, ``human_authority_ref``), every State-binding field and every outcome
field participates in both digests. There is no field a record can carry that its own identity
does not see.
"""

from __future__ import annotations

import hashlib
from typing import Any

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

from .errors import ModelRuntimeRequirementError

#: Every field a Model Execution Boundary's own identity and semantic fingerprint are computed
#: over -- the complete record minus the two digest fields themselves.
BOUNDARY_SEMANTIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "project_binding_ref",
    "permitted_capability",
    "permitted_candidate_kinds",
    "permitted_candidate_fields",
    "declared_by",
    "declared_at",
)

#: Every field a Model Work Unit's own identity and semantic fingerprint are computed over --
#: the complete record minus the two digest fields themselves, so tampering *any* other field
#: (the State snapshot it was opened against, the Difference it is about, the capability it
#: requires, the Authority Decision that permitted it, the Boundary that bounds it, the Evidence
#: requirements it must satisfy, the owning project/binding, the instant it was opened) is
#: detectable by either digest.
WORK_UNIT_SEMANTIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "project_binding_ref",
    "opened_state_revision",
    "opened_semantic_fingerprint",
    "difference_ref",
    "required_capability",
    "authority_ref",
    "boundary_ref",
    "evidence_requirements",
    "opened_at",
)

#: Every field a Model Execution Envelope's own identity and semantic fingerprint are computed
#: over -- the complete record minus the two digest fields themselves, the outcome and the
#: normalized candidate included.
ENVELOPE_SEMANTIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "project_binding_ref",
    "model_work_unit_ref",
    "model_execution_request_identity",
    "executed_state_revision",
    "executed_semantic_fingerprint",
    "adapter_identity",
    "executed_at",
    "execution_outcome",
    "normalized_candidate_kind",
    "normalized_candidate",
    "normalized_candidate_fingerprint",
    "difference_ref",
    "required_capability",
    "authority_ref",
    "boundary_ref",
    "evidence_requirements",
    "human_authority_ref",
)

#: Every field a Model Swap Receipt's own identity and semantic fingerprint are computed over.
#: Both adapters' identities and both Boot snapshots participate: a receipt that did not bind
#: *which two adapters* and *which two States* would be a claim about continuity rather than a
#: record of it.
SWAP_RECEIPT_SEMANTIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "project_binding_ref",
    "model_work_unit_ref",
    "predecessor_execution_ref",
    "predecessor_adapter_identity",
    "predecessor_state_revision",
    "predecessor_semantic_fingerprint",
    "successor_execution_ref",
    "successor_adapter_identity",
    "successor_state_revision",
    "successor_semantic_fingerprint",
    "difference_ref",
    "required_capability",
    "authority_ref",
    "boundary_ref",
    "evidence_requirements",
    "recorded_at",
)

#: Every field a Session Recovery Receipt's own identity and semantic fingerprint are computed
#: over.
RECOVERY_RECEIPT_SEMANTIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "project_binding_ref",
    "model_work_unit_ref",
    "recovered_state_revision",
    "recovered_semantic_fingerprint",
    "difference_ref",
    "required_capability",
    "authority_ref",
    "boundary_ref",
    "evidence_requirements",
    "recovered_at",
)


def _projection(
    record: dict[str, Any], fields: tuple[str, ...], record_kind: str
) -> dict[str, Any]:
    missing = [field for field in fields if field not in record]
    if missing:
        raise ModelRuntimeRequirementError(
            f"{record_kind} carries no readable {', '.join(missing)} -- its own identity cannot "
            "be recomputed"
        )
    return {field: record[field] for field in fields}


def _address(prefix: str, projection: dict[str, Any]) -> str:
    return prefix + hashlib.sha256(canonical_json_bytes(projection)).hexdigest().upper()


def _digest(projection: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json_bytes(projection)).hexdigest()


def model_execution_boundary_id(boundary: dict[str, Any]) -> str:
    """The content address of a canonical Model Execution Boundary."""

    return _address(
        "MODEL-EXECUTION-BOUNDARY-",
        _projection(boundary, BOUNDARY_SEMANTIC_FIELDS, "model_execution_boundary"),
    )


def model_execution_boundary_semantic_fingerprint(boundary: dict[str, Any]) -> str:
    """The digest of a canonical Model Execution Boundary's full meaning -- the identical
    projection :func:`model_execution_boundary_id` hashes."""

    return _digest(_projection(boundary, BOUNDARY_SEMANTIC_FIELDS, "model_execution_boundary"))


def model_work_unit_id(work_unit: dict[str, Any]) -> str:
    """The content address of a canonical State-bound Model Work Unit -- a pure function of the
    complete, real record content, never of a caller-declared value.

    This is what "the same Work Unit" means operationally across a model swap or a total session
    loss (P16-C4/P16-C5): Agent B resolves this exact address from the Store and independently
    recomputes it from the resolved body, so "same Work Unit" is a re-proved fact about content
    rather than a string both Agents happened to hold.
    """

    return _address(
        "MODEL-WORK-UNIT-", _projection(work_unit, WORK_UNIT_SEMANTIC_FIELDS, "model_work_unit")
    )


def model_work_unit_semantic_fingerprint(work_unit: dict[str, Any]) -> str:
    """The digest of a Model Work Unit's full meaning -- the identical projection
    :func:`model_work_unit_id` hashes, under the ``sha256:`` encoding every other owner's own
    semantic fingerprint already uses, so tampering any field is detectable independently of the
    record's own id."""

    return _digest(_projection(work_unit, WORK_UNIT_SEMANTIC_FIELDS, "model_work_unit"))


def model_execution_request_identity(
    *,
    model_work_unit_id_value: str,
    state_revision: int,
    semantic_fingerprint: dict[str, Any],
    adapter_identity: dict[str, Any],
) -> str:
    """The stable identity of *this exact provider-neutral execution request* (P16-C1).

    A pure function of *which Work Unit* (and therefore, transitively and verifiably, which
    State revision it was opened against, which Difference it is about, which capability it
    requires, which Authority Decision permitted it, which Boundary bounds it and which Evidence
    requirements it must satisfy -- all of which participate in
    :func:`model_work_unit_id`'s own closed projection), *against which current State*, and
    *through which adapter*. Computable before the adapter is ever called, independent of
    whatever result it later returns.

    What is deliberately **absent** is as load-bearing as what is present: no provider payload,
    no prompt text, no chat transcript, no model memory, no provider session id, and no
    provider-specific field of any kind participates -- there is no parameter through which one
    could arrive. Swapping the adapter changes this identity; swapping the *provider behind* an
    otherwise identically-identified adapter does not, which is exactly the replaceability the
    proposal asks to prove.
    """

    payload = {
        "model_work_unit_id": model_work_unit_id_value,
        "state_revision": state_revision,
        "semantic_fingerprint": semantic_fingerprint,
        "adapter_identity": adapter_identity,
    }
    return _address("MODEL-EXECUTION-REQUEST-", payload)


def model_execution_envelope_id(envelope: dict[str, Any]) -> str:
    """The content address of a Model Execution Envelope -- a pure function of the complete,
    real record content (outcome and normalized candidate included), never of a caller-declared
    value."""

    return _address(
        "MODEL-EXECUTION-",
        _projection(envelope, ENVELOPE_SEMANTIC_FIELDS, "model_execution_envelope"),
    )


def model_execution_envelope_semantic_fingerprint(envelope: dict[str, Any]) -> str:
    """The digest of a Model Execution Envelope's full meaning -- the identical projection
    :func:`model_execution_envelope_id` hashes."""

    return _digest(_projection(envelope, ENVELOPE_SEMANTIC_FIELDS, "model_execution_envelope"))


def model_swap_receipt_id(receipt: dict[str, Any]) -> str:
    """The content address of a Model Swap Receipt."""

    return _address(
        "MODEL-SWAP-", _projection(receipt, SWAP_RECEIPT_SEMANTIC_FIELDS, "model_swap_receipt")
    )


def model_swap_receipt_semantic_fingerprint(receipt: dict[str, Any]) -> str:
    """The digest of a Model Swap Receipt's full meaning -- the identical projection
    :func:`model_swap_receipt_id` hashes."""

    return _digest(_projection(receipt, SWAP_RECEIPT_SEMANTIC_FIELDS, "model_swap_receipt"))


def session_recovery_receipt_id(receipt: dict[str, Any]) -> str:
    """The content address of a Session Recovery Receipt."""

    return _address(
        "MODEL-SESSION-RECOVERY-",
        _projection(receipt, RECOVERY_RECEIPT_SEMANTIC_FIELDS, "session_recovery_receipt"),
    )


def session_recovery_receipt_semantic_fingerprint(receipt: dict[str, Any]) -> str:
    """The digest of a Session Recovery Receipt's full meaning -- the identical projection
    :func:`session_recovery_receipt_id` hashes."""

    return _digest(
        _projection(receipt, RECOVERY_RECEIPT_SEMANTIC_FIELDS, "session_recovery_receipt")
    )


def model_candidate_fingerprint(normalized_candidate: dict[str, Any]) -> str:
    """The derived-not-trusted fingerprint of a route's own already-Boundary-projected
    normalized candidate alone -- computed only over what
    :mod:`~manosube_agent_civilization.model_runtime.route` has already bounded to the Model
    Execution Boundary's own ``permitted_candidate_fields``, never over an adapter's raw,
    untrusted report directly."""

    return "sha256:" + hashlib.sha256(canonical_json_bytes(normalized_candidate)).hexdigest()
