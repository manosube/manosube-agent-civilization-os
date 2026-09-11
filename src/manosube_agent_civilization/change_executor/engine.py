"""Pure record builders for Change Executor's own three record kinds (Phase 18, Issue #73):
``execution_intent``, ``execution_attempt``, and ``change_execution_receipt``.

Every function here performs no Store I/O of any kind, reads no clock, and trusts every input
it is given as already verified by its own caller (:mod:`~manosube_agent_civilization.
change_executor.route`) -- exactly the discipline ``change/engine.py``'s own module docstring
states for :func:`~manosube_agent_civilization.change.engine.derive_change`: "Change describes
an authorized mutation. It does not perform one." Each builder here computes and embeds its own
record's id and semantic fingerprint, and schema-validates the result against this package's own
canonical schema (``01_SCHEMA/change_executor/*.schema.json``) before returning it, the identical
"never let en engine emit a record its own schema would reject" discipline every other owner in
this repository already keeps.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from manosube_agent_civilization.difference.errors import DifferenceValidationError
from manosube_agent_civilization.difference.validation import validate_record as _validate_record

from .boundary import CHANGE_EXECUTOR_SCHEMA_BASE
from .errors import ChangeExecutorError
from .identity import (
    change_execution_receipt_semantic_fingerprint,
    execution_attempt_semantic_fingerprint,
    execution_intent_semantic_fingerprint,
    execution_mapping_slot_key,
)
from .types import EXECUTION_OUTCOMES, INDEPENDENT_REOBSERVATION_OUTCOMES, ROLLBACK_OUTCOMES

SCHEMA_VERSION = "0.1"


def _validate(record: dict[str, Any], schema_name: str, context: str) -> None:
    try:
        _validate_record(record, schema_name, base=CHANGE_EXECUTOR_SCHEMA_BASE)
    except DifferenceValidationError as error:
        raise ChangeExecutorError(f"{context}: {error}") from error


def build_execution_intent(
    *,
    project_id: str,
    change_ref: Mapping[str, str],
    execution_boundary_fingerprint: str,
    adapter_identity_fingerprint: str,
    claim_token: str,
    requested_at: str,
) -> dict[str, Any]:
    """Build one canonical ``execution_intent`` record. Its own id is the deterministic mapping
    slot :func:`~manosube_agent_civilization.change_executor.identity.
    execution_mapping_slot_key` computes from *change_ref*, *execution_boundary_fingerprint*,
    and *adapter_identity_fingerprint* alone -- so two distinct ``claim_token`` values for the
    identical ``(change, Boundary, adapter)`` triple always produce two records that collide at
    the identical Store id, which is the concurrency barrier this package's own idempotency
    contract is built on."""

    slot_key = execution_mapping_slot_key(
        change_ref["id"], execution_boundary_fingerprint, adapter_identity_fingerprint
    )
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "execution_intent_id": slot_key,
        "project_id": project_id,
        "change_ref": dict(change_ref),
        "execution_boundary_fingerprint": execution_boundary_fingerprint,
        "adapter_identity_fingerprint": adapter_identity_fingerprint,
        "claim_token": claim_token,
        "requested_at": requested_at,
        "execution_intent_semantic_fingerprint": "",
    }
    record["execution_intent_semantic_fingerprint"] = execution_intent_semantic_fingerprint(record)
    _validate(record, "execution_intent.schema.json", "generated execution_intent")
    return record


def build_execution_attempt(
    *,
    project_id: str,
    change_ref: Mapping[str, str],
    execution_boundary_fingerprint: str,
    adapter_identity_fingerprint: str,
    claim_token: str,
    requested_at: str,
    execution_intent_ref: Mapping[str, str],
    attempt_nonce: str,
    reobservation_request: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one canonical ``execution_attempt`` record, under the identical mapping-slot id its
    own ``execution_intent`` record already carries.

    *attempt_nonce* is a fresh, cryptographically random per-call token (``route.py``'s own
    ``secrets.token_hex(16)``, never caller-derivable from any other field) that makes two
    independently-built attempts for the identical slot genuinely different byte-for-byte, so the
    Store's own existing conflict-detection correctly refuses a second, genuinely concurrent
    attempt rather than treating it as an idempotent replay of the first (Phase 18 Issue #73
    review finding; see ``route.py``'s own module docstring, disclosed judgment call 8). It is an
    ordinary field of this record's own body, fully covered by
    ``execution_attempt_semantic_fingerprint`` like every other field -- it deliberately never
    participates in the deterministic mapping-slot id itself (:func:`execution_mapping_slot_key`,
    unchanged), which must stay a pure function of *change_ref*/*execution_boundary_fingerprint*/
    *adapter_identity_fingerprint* alone for replay/reconciliation detection to work at all.

    *reobservation_request* (P18-R2-F3, Structural Review Round 2) is embedded here, at
    attempt-commit time -- the identical ``change_execution_reobservation_request`` shape
    ``change_execution_receipt``'s own field already carries -- so that from the instant this
    attempt becomes durable, the durable record chain already preserves a typed re-observation
    obligation, and a caller resuming its own orphaned attempt (attempt committed, no receipt
    yet) has a genuine, already-committed fact to resolve a grounded terminal ``UNKNOWN`` receipt
    from, without a blind adapter retry (see ``route.py``'s own module docstring)."""

    slot_key = execution_mapping_slot_key(
        change_ref["id"], execution_boundary_fingerprint, adapter_identity_fingerprint
    )
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "execution_attempt_id": slot_key,
        "project_id": project_id,
        "change_ref": dict(change_ref),
        "execution_boundary_fingerprint": execution_boundary_fingerprint,
        "adapter_identity_fingerprint": adapter_identity_fingerprint,
        "claim_token": claim_token,
        "requested_at": requested_at,
        "execution_intent_ref": dict(execution_intent_ref),
        "attempt_nonce": attempt_nonce,
        "reobservation_request": deepcopy(dict(reobservation_request)),
        "execution_attempt_semantic_fingerprint": "",
    }
    record["execution_attempt_semantic_fingerprint"] = execution_attempt_semantic_fingerprint(
        record
    )
    _validate(record, "execution_attempt.schema.json", "generated execution_attempt")
    return record


def build_change_execution_receipt(
    *,
    execution_request_id: str,
    change_ref: Mapping[str, str],
    idempotency_key: str,
    authority_ref: Mapping[str, str],
    project_id: str,
    project_binding_ref: Mapping[str, str],
    boot_state_fingerprint: Mapping[str, str],
    execution_boundary_fingerprint: str,
    executor_identity: str,
    executor_version: str,
    target: Mapping[str, Any],
    operation: Mapping[str, Any],
    execution_started_at: str,
    execution_ended_at: str,
    outcome: str,
    performed_result_fingerprint: str,
    performed_result_summary: Mapping[str, Any],
    rollback_outcome: str | None,
    claim_token: str,
    reobservation_request: Mapping[str, Any],
    independent_after_state_observation: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one canonical, immutable ``change_execution_receipt`` record -- the sole durable
    fact this package ever commits about one execution attempt's own terminal outcome.

    ``change_execution_receipt_id`` and ``execution_request_id`` are, by this package's own
    design, always exactly *execution_request_id* itself (see
    :mod:`~manosube_agent_civilization.change_executor.identity`'s own module docstring): the
    shared mapping-slot key this receipt, its originating ``execution_attempt``, and its
    originating ``execution_intent`` all carry under the identical id.

    ``reobservation_request`` is embedded directly in this record, never committed as a
    separate Store-owned reference-target kind -- a disclosed judgment call: this package hands
    off to the existing Evidence/Observation/Reflow owners rather than becoming a new reference-
    target kind those owners' own existing reference-closure registries would need to learn
    about. A typed request for independent Observation is preserved without inventing a fourth
    thing for the rest of the Kernel to resolve.

    ``independent_after_state_observation`` (P18-R1-F1, Structural Review Round 1) is the result
    of this package's own genuine, independent, read-only re-read of the actual resulting
    filesystem state (:func:`~manosube_agent_civilization.change_executor.reobservation.
    independently_reobserve`), embedded directly in this record so it becomes a durable,
    immutable, tamper-checked fact of the receipt itself -- never a transient value discarded
    once ``execute()`` returns. It is what ``evidence_handoff.py`` now requires, in addition to
    ``outcome == "SUCCEEDED"``, before deriving Evidence's own ``VERIFIED`` status.
    """

    if outcome not in EXECUTION_OUTCOMES:
        raise ChangeExecutorError(
            f"outcome is not a recognized EXECUTION_OUTCOMES member: {outcome!r}"
        )
    if rollback_outcome is not None and rollback_outcome not in ROLLBACK_OUTCOMES:
        raise ChangeExecutorError(
            f"rollback_outcome is not a recognized ROLLBACK_OUTCOMES member: {rollback_outcome!r}"
        )
    if (
        not isinstance(independent_after_state_observation, Mapping)
        or independent_after_state_observation.get("outcome")
        not in INDEPENDENT_REOBSERVATION_OUTCOMES
    ):
        raise ChangeExecutorError(
            "independent_after_state_observation must be a mapping whose own outcome is a "
            "recognized INDEPENDENT_REOBSERVATION_OUTCOMES member: "
            f"{independent_after_state_observation!r}"
        )

    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "change_execution_receipt_id": execution_request_id,
        "execution_request_id": execution_request_id,
        "change_ref": dict(change_ref),
        "idempotency_key": idempotency_key,
        "authority_ref": dict(authority_ref),
        "project_id": project_id,
        "project_binding_ref": dict(project_binding_ref),
        "boot_state_fingerprint": dict(boot_state_fingerprint),
        "execution_boundary_fingerprint": execution_boundary_fingerprint,
        "executor_identity": executor_identity,
        "executor_version": executor_version,
        "target": dict(target),
        "operation": deepcopy(dict(operation)),
        "execution_started_at": execution_started_at,
        "execution_ended_at": execution_ended_at,
        "outcome": outcome,
        "performed_result_fingerprint": performed_result_fingerprint,
        "performed_result_summary": deepcopy(dict(performed_result_summary)),
        "rollback_outcome": rollback_outcome,
        "claim_token": claim_token,
        "reobservation_request": deepcopy(dict(reobservation_request)),
        "independent_after_state_observation": deepcopy(dict(independent_after_state_observation)),
        "change_execution_receipt_semantic_fingerprint": "",
    }
    record["change_execution_receipt_semantic_fingerprint"] = (
        change_execution_receipt_semantic_fingerprint(record)
    )
    _validate(record, "execution_receipt.schema.json", "generated change_execution_receipt")
    return record


__all__ = [
    "SCHEMA_VERSION",
    "build_change_execution_receipt",
    "build_execution_attempt",
    "build_execution_intent",
]
