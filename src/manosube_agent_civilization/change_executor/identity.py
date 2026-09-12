"""Deterministic Change Executor identities (Phase 18, Issue #73).

Canonical serialization has one owner in this repository -- ``state.canonicalize`` -- and this
module reads it rather than restating it, exactly as ``change/identity.py`` and
``authority/identity.py`` already do. What is defined here is only *which payload* each Change
Executor identity is computed over, and the one deterministic mapping-slot key the idempotency
state machine in :mod:`~manosube_agent_civilization.change_executor.route` is built on.

**Disclosed judgment call: the mapping slot IS the shared record id for all three record
kinds.** The task description that seeded this package asked for an ``execution_mapping_slot_
key`` that "becomes the record id both the intent and attempt records share", and separately
asked for id/fingerprint functions for all three kinds "following the exact ``sha256:``+hex /
``EXEC-INTENT-``+64-hex-uppercase / etc. convention ``change/identity.py`` uses" (i.e., a full
content address over each record's own complete semantic-field projection, per kind). Those two
requirements are in tension: a full content address over ``execution_intent``'s own semantic
fields would vary with ``claim_token``, so two different callers' intents for the identical
``(change, Boundary, adapter)`` would *not* collide at one Store ``(kind, id)`` slot -- which is
exactly the collision the whole mapping-slot mechanism exists to produce (a second concurrent
attempt with a different ``claim_token`` must collide and be refused, never silently coexist
under a different id). This module resolves the tension in favor of the mechanically load-bearing
requirement: :func:`execution_mapping_slot_key` is a *narrower* projection -- ``change_id``,
``execution_boundary_fingerprint``, and ``adapter_identity_fingerprint`` alone, deliberately
excluding ``claim_token`` -- and that one value is used, verbatim, as the Store id of the
``execution_intent`` record, the ``execution_attempt`` record, *and* the terminal
``change_execution_receipt`` record for that slot (the ``execution_receipt`` record kind is keyed
by ``execution_request_id``, which is itself always exactly the slot key -- see
:data:`CHANGE_EXECUTION_RECEIPT_SEMANTIC_FIELDS`'s own docstring below). This is what lets
``route.py`` resolve "does an intent/attempt/receipt already exist for this exact slot" with one
direct ``resolve_record`` call per kind, with no secondary index. Each kind's own broader content
(including ``claim_token``) is still fully tamper-checked, separately, through that kind's own
``*_semantic_fingerprint`` function below -- the ``sha256:``+hex convention is kept in full for
fingerprints; it is only the record *id* that is the coarser slot key rather than a full content
address, for every one of the three related kinds.
"""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from typing import Any

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

#: What an ``execution_intent`` (and, identically, an ``execution_attempt``) record *is*: which
#: project, which Change, under which Boundary and adapter identity, claimed by whom, and when.
#: ``claim_token`` and ``requested_at`` deliberately participate here (full tamper detection)
#: even though they are excluded from :func:`execution_mapping_slot_key` itself (see this
#: module's own docstring).
EXECUTION_INTENT_SEMANTIC_FIELDS: tuple[str, ...] = (
    "project_id",
    "change_ref",
    "execution_boundary_fingerprint",
    "adapter_identity_fingerprint",
    "claim_token",
    "requested_at",
)

#: An ``execution_attempt`` restates everything its own ``execution_intent`` does, plus the
#: exact reference to that intent record, plus ``attempt_nonce`` -- a fresh, per-call random
#: token (never derived from any other field) that makes two independently-built attempts for the
#: identical mapping slot genuinely different byte-for-byte, so the Store's own existing
#: same-``(kind, id)``-different-body conflict detection correctly refuses a second, genuinely
#: concurrent attempt rather than silently treating it as an idempotent replay of the first
#: (Phase 18 Issue #73 review finding; ``route.py``'s own module docstring, disclosed judgment
#: call 8). It is an ordinary semantic field like any other here -- fully tamper-checked by this
#: kind's own fingerprint -- and deliberately never participates in
#: :func:`execution_mapping_slot_key`/:func:`execution_attempt_id` below, which must stay a pure
#: function of exactly *change_ref*/*execution_boundary_fingerprint*/*adapter_identity_fingerprint*
#: for replay/reconciliation detection to keep working at all.
#: ``reobservation_request`` (P18-R2-F3, Structural Review Round 2) is embedded here, at
#: attempt-commit time, rather than only recomputed later once a terminal receipt is built --
#: closing the gap where a caller resuming its own orphaned attempt (attempt committed, no
#: receipt yet, identical claim_token -- a genuine crash, or a final-barrier refusal) had no
#: durably-committed re-observation obligation to resolve against without either a blind retry
#: or a permanent ``ExecutionReconciliationRequiredError``. It is deterministic content (built
#: from the frozen Boundary/Change/execution_instant this call already has, never caller-random),
#: so it belongs in the semantic fingerprint exactly like every other attempt field -- a caller
#: could not silently swap it out from under an already-committed attempt.
#: ``attempt_status`` (P18-R3-F3A, Structural Review Round 3) is a fixed constant
#: (``"DURABLE_UNRESOLVED_NON_SUCCESS"``) every ``execution_attempt`` carries from the instant it
#: becomes durable -- the record's own declared vocabulary naming its own typed unresolved/
#: non-success state explicitly, not merely reconstructible externally from the bare absence of
#: a receipt. It is fingerprint-covered like every other field here, so it is tamper-evident too.
EXECUTION_ATTEMPT_SEMANTIC_FIELDS: tuple[str, ...] = (
    *EXECUTION_INTENT_SEMANTIC_FIELDS,
    "execution_intent_ref",
    "attempt_nonce",
    "attempt_status",
    "reobservation_request",
)

#: What a ``change_execution_receipt`` *is*, for tamper-detection purposes -- every field of the
#: adopted receipt contract except its own declared ``change_execution_receipt_id`` and its own
#: declared ``change_execution_receipt_semantic_fingerprint`` (an identity/fingerprint cannot be
#: computed over itself, the identical exclusion every other owner's own semantic-fields tuple
#: states) **and** except ``execution_request_id`` -- which this package's own design makes
#: *always* exactly equal to ``change_execution_receipt_id`` (the shared mapping-slot key), so
#: including it here would be including the record's own identity under a second name, the
#: identical reason ``change/identity.py``'s own ``CHANGE_SEMANTIC_FIELDS`` excludes
#: ``idempotency_key`` (itself always exactly ``change_semantic_fingerprint``).
CHANGE_EXECUTION_RECEIPT_SEMANTIC_FIELDS: tuple[str, ...] = (
    "change_ref",
    "idempotency_key",
    "authority_ref",
    "project_id",
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
)


def _projection(record: Mapping[str, Any], fields: tuple[str, ...], *, kind: str) -> dict[str, Any]:
    missing = [field for field in fields if field not in record]
    if missing:
        raise KeyError(
            f"{kind} carries no readable {', '.join(missing)} -- its own identity cannot be recomputed"
        )
    return {field: record[field] for field in fields}


def execution_mapping_slot_key(
    change_id: str, execution_boundary_fingerprint: str, adapter_identity_fingerprint: str
) -> str:
    """The one deterministic mapping-slot key the idempotency state machine is built on: a pure
    function of exactly *which Change*, under exactly *which Boundary*, executed by exactly
    *which adapter identity* -- deliberately excluding ``claim_token`` and any instant, so two
    distinct callers proposing the identical ``(change, Boundary, adapter)`` triple always
    collide at the identical slot, and only a genuinely distinct triple ever produces a distinct
    one. Used, verbatim, as the Store ``(kind, id)`` identity of the ``execution_intent``, the
    ``execution_attempt``, and the terminal ``change_execution_receipt`` for that slot."""

    payload = {
        "change_id": change_id,
        "execution_boundary_fingerprint": execution_boundary_fingerprint,
        "adapter_identity_fingerprint": adapter_identity_fingerprint,
    }
    return "EXEC-SLOT-" + hashlib.sha256(canonical_json_bytes(payload)).hexdigest().upper()


def execution_intent_semantic_fingerprint(record: Mapping[str, Any]) -> str:
    """The digest of an ``execution_intent`` record's own complete meaning, including
    ``claim_token`` and ``requested_at``."""

    projection = _projection(record, EXECUTION_INTENT_SEMANTIC_FIELDS, kind="execution_intent")
    return "sha256:" + hashlib.sha256(canonical_json_bytes(projection)).hexdigest()


def execution_intent_id(record: Mapping[str, Any]) -> str:
    """The mapping-slot identity an ``execution_intent`` record's own declared id must equal --
    recomputed from the record's own ``change_ref``/``execution_boundary_fingerprint``/
    ``adapter_identity_fingerprint`` fields alone (never from ``claim_token``, which the
    semantic fingerprint above still fully covers)."""

    return execution_mapping_slot_key(
        record["change_ref"]["id"],
        record["execution_boundary_fingerprint"],
        record["adapter_identity_fingerprint"],
    )


def execution_attempt_semantic_fingerprint(record: Mapping[str, Any]) -> str:
    """The digest of an ``execution_attempt`` record's own complete meaning."""

    projection = _projection(record, EXECUTION_ATTEMPT_SEMANTIC_FIELDS, kind="execution_attempt")
    return "sha256:" + hashlib.sha256(canonical_json_bytes(projection)).hexdigest()


def execution_attempt_id(record: Mapping[str, Any]) -> str:
    """The identical mapping-slot identity :func:`execution_intent_id` computes, recomputed from
    an ``execution_attempt`` record's own fields."""

    return execution_mapping_slot_key(
        record["change_ref"]["id"],
        record["execution_boundary_fingerprint"],
        record["adapter_identity_fingerprint"],
    )


def change_execution_receipt_semantic_fingerprint(record: Mapping[str, Any]) -> str:
    """The digest of a ``change_execution_receipt`` record's own complete meaning."""

    projection = _projection(
        record, CHANGE_EXECUTION_RECEIPT_SEMANTIC_FIELDS, kind="change_execution_receipt"
    )
    return "sha256:" + hashlib.sha256(canonical_json_bytes(projection)).hexdigest()


def change_execution_receipt_id(record: Mapping[str, Any]) -> str:
    """A ``change_execution_receipt``'s own declared identity is, by this package's own design,
    always exactly its own ``execution_request_id`` -- the shared mapping-slot key this receipt,
    its originating ``execution_attempt``, and its originating ``execution_intent`` all carry
    under the identical id (see this module's own docstring). This function asserts exactly
    that structural equality; it does not independently re-derive the slot key from the
    receipt's own other fields, because the receipt does not itself restate every input the slot
    key is a function of (in particular, no bare ``adapter_identity_fingerprint``). A caller that
    already knows the expected slot key -- every call site in ``route.py`` does, having computed
    it itself before ever resolving a receipt -- compares against that directly instead."""

    value = record["execution_request_id"]
    if type(value) is not str:
        raise KeyError(f"execution_request_id must be a string, got {type(value)!r}")
    return value


__all__ = [
    "CHANGE_EXECUTION_RECEIPT_SEMANTIC_FIELDS",
    "EXECUTION_ATTEMPT_SEMANTIC_FIELDS",
    "EXECUTION_INTENT_SEMANTIC_FIELDS",
    "change_execution_receipt_id",
    "change_execution_receipt_semantic_fingerprint",
    "execution_attempt_id",
    "execution_attempt_semantic_fingerprint",
    "execution_intent_id",
    "execution_intent_semantic_fingerprint",
    "execution_mapping_slot_key",
]
