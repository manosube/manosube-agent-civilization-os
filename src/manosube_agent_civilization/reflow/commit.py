"""Atomic State commit, via the existing Store -- never a second persistence owner.

``store.file_store.FileStateStore`` already implements Compare-And-Swap, idempotent
transaction replay, transaction-conflict rejection, staged atomic commit and crash
recovery. This module builds the two records that ``FileStateStore.commit`` takes --
the successor ``project_state`` and the ``state_transition`` lineage event that carries
it -- and calls the Store. It mints nothing the Store does not already validate, and it
persists nothing outside the Store's own files.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from manosube_agent_civilization.state.fingerprint import fingerprint_semantic_state

from .errors import ReflowValidationError

SCHEMA_VERSION = "0.1"


def build_state_transition(
    *,
    before_project_state: dict[str, Any],
    next_semantic_state: dict[str, Any],
    transaction_id: str,
    evidence_refs: list[Any],
    reflow_instant: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return ``(next_project_state, state_transition_event)``, both unvalidated.

    Neither record is schema-checked here: ``FileStateStore.commit`` re-derives and checks
    both (``_validate_state``, ``_verify_event``) before writing anything, and duplicating
    that check here would be a second, driftable copy of the one the Store already owns.
    """

    before = before_project_state
    next_fingerprint = fingerprint_semantic_state(next_semantic_state).as_dict()

    next_state_metadata = deepcopy(before["state_metadata"])
    next_state_metadata["recorded_at"] = reflow_instant

    next_project_state: dict[str, Any] = {
        "schema_version": before["schema_version"],
        "project_id": before["project_id"],
        "objective_revision_id": before["objective_revision_id"],
        "state_revision": before["state_revision"] + 1,
        "previous_state_fingerprint": before["semantic_fingerprint"],
        "semantic_state": next_semantic_state,
        "semantic_fingerprint": next_fingerprint,
        "state_metadata": next_state_metadata,
        "evidence_refs": list(evidence_refs),
        "lineage_head_ref": {"kind": "state_transition", "id": transaction_id},
    }

    state_transition_event: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "transaction_id": transaction_id,
        "event_type": "TRANSITION",
        "project_id": before["project_id"],
        "from_revision": before["state_revision"],
        "to_revision": next_project_state["state_revision"],
        "before_fingerprint": before["semantic_fingerprint"],
        "after_fingerprint": next_fingerprint,
        "after_state": next_project_state,
        "evidence_refs": list(evidence_refs),
        "committed_at": reflow_instant,
    }

    return next_project_state, state_transition_event


def commit_reflow(
    store: Any,
    *,
    project_id: str,
    before_project_state: dict[str, Any],
    next_semantic_state: dict[str, Any],
    transaction_id: str,
    evidence_refs: list[Any],
    reflow_instant: str,
    fault: Any | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the successor State and commit it atomically. Returns ``(state, ref)``.

    *fault* is passed straight through to ``FileStateStore.commit`` -- it exists only so
    a crash-recovery test can inject a ``SimulatedCrash`` at one of the Store's own
    ``STAGES`` and prove this module's commit survives it exactly as
    ``store/file_store.py``'s own tests already prove the Store itself does. Production
    callers never pass it.

    *ref* is ``{"kind": "state_transition", "id": transaction_id}`` -- the exact reference
    a Difference lifecycle event's ``reflow_transition_ref`` and this same ``project_state``
    document's own ``lineage_head_ref`` both name, so the two agree on which single
    committed transition authorized the transition by construction, not by convention.

    Idempotent by the Store's own contract: replaying the identical *transaction_id* with
    identical canonical inputs returns the same committed State rather than erroring, and a
    different payload under the same *transaction_id* raises
    ``TransactionConflictError`` -- both are the Store's behavior, not this function's.
    """

    if before_project_state["project_id"] != project_id:
        raise ReflowValidationError("before_project_state belongs to a different project")

    next_project_state, event = build_state_transition(
        before_project_state=before_project_state,
        next_semantic_state=next_semantic_state,
        transaction_id=transaction_id,
        evidence_refs=evidence_refs,
        reflow_instant=reflow_instant,
    )
    committed = store.commit(
        project_id,
        before_project_state["state_revision"],
        before_project_state["semantic_fingerprint"],
        next_project_state,
        event,
        fault=fault,
    )
    return committed, {"kind": "state_transition", "id": transaction_id}
