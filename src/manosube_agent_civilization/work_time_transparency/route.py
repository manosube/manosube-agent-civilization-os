"""Canonical Work Coordination entrypoints for the Human Wait-Time Transparency vertical
(Issue #22): ``open_work_time_coordination``, ``record_work_time_progress_update``, and
``record_work_time_terminal_notice``.

**This is not a Change Executor, not an Evidence producer, and not an Authority owner.** Every
record this module commits carries no ``human_authority_ref``/signature field (see the three
schemas under ``01_SCHEMA/work_time_transparency/``), is never passed to
``reflow()``/``commit_reflow``, and is never registered in
:data:`~manosube_agent_civilization.reflow.reference_registry.STORE_OWNED_REFERENCE_KINDS` --
structurally, not merely by convention, a ``work_time_coordination_*`` record cannot become
Difference/Evidence/Authority input (``tests/contract/work_time_transparency/test_work_time_
transparency_non_authority_boundary.py`` proves this against the real registry and real
engines).

``boot_project`` is called fresh on every one of this module's own public entrypoints, never
cached across calls -- the identical discipline ``change_executor/route.py`` and ``runtime/
route.py`` already keep, and for the identical reason: a cached ``BootContext`` from an earlier
call could silently authorize against a stale Project Binding if the bound project changed
underneath a long-lived caller between a coordination's own ``open`` and its later ``update``/
``terminal`` calls (TOCTOU).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store.commit import commit_state_transition
from manosube_agent_civilization.store.errors import RecordConflictError, StaleStateError

from .engine import (
    build_work_time_coordination_open,
    build_work_time_coordination_terminal,
    build_work_time_coordination_update,
)
from .errors import WorkTimeTransparencyValidationError

_MAX_COMMIT_RETRIES = 8


def _commit_records(
    store: Any,
    project_id: str,
    records: list[tuple[str, str, dict[str, Any]]],
    committed_at: str,
    *,
    transaction_prefix: str,
) -> dict[str, Any]:
    """The identical bounded Compare-And-Swap retry template ``change_executor/route.py``'s own
    ``_commit_records`` uses. A real identity/content conflict (:class:`RecordConflictError`) is
    never swallowed into a retry -- every call site below translates it into its own typed
    error."""

    for _ in range(_MAX_COMMIT_RETRIES):
        current_state = store.load_current(project_id)
        transaction_id = f"{transaction_prefix}-{current_state['state_revision']}"
        next_state = dict(current_state)
        next_state["state_revision"] = current_state["state_revision"] + 1
        next_state["previous_state_fingerprint"] = current_state["semantic_fingerprint"]
        next_state["lineage_head_ref"] = {"kind": "state_transition", "id": transaction_id}
        next_state["semantic_fingerprint"] = fingerprint_project_state(next_state).as_dict()
        transition = {
            "schema_version": "0.1",
            "transaction_id": transaction_id,
            "event_type": "TRANSITION",
            "project_id": project_id,
            "from_revision": current_state["state_revision"],
            "to_revision": next_state["state_revision"],
            "before_fingerprint": current_state["semantic_fingerprint"],
            "after_fingerprint": next_state["semantic_fingerprint"],
            "after_state": next_state,
            "evidence_refs": [],
            "committed_at": committed_at,
        }
        try:
            return commit_state_transition(
                store,
                project_id,
                current_state["state_revision"],
                current_state["semantic_fingerprint"],
                next_state,
                transition,
                records=records,
            )
        except RecordConflictError:
            raise
        except StaleStateError:
            continue
    raise WorkTimeTransparencyValidationError(
        f"could not durably commit under transaction prefix {transaction_prefix!r} after "
        f"{_MAX_COMMIT_RETRIES} Compare-And-Swap retries -- sustained unrelated contention on "
        "this project's own State"
    )


def open_work_time_coordination(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    work_unit_ref: Mapping[str, str],
    adapter_kind: str,
    estimated_duration_lower_minutes: int,
    estimated_duration_upper_minutes: int,
    estimate_confidence: str,
    major_steps: list[str],
    next_progress_update_due_minutes: int,
    variability_factors: str,
    opened_at: str,
) -> dict[str, Any]:
    """Issue #22's own "Required Start Notice", committed as one immutable ``work_time_
    coordination_open`` record. A retry with the identical *work_unit_ref* is idempotent (the
    identical id, the Store's own existing same-id-same-body replay tolerance); a second,
    differently-bodied open for the identical *work_unit_ref* collides and is refused
    (:class:`RecordConflictError`) -- a work unit is estimated exactly once."""

    boot_context = boot_project(store, project_id=project_id, project_binding_id=project_binding_id)
    project_binding_ref = {"kind": "project_binding", "id": boot_context.project_binding_id}
    record = build_work_time_coordination_open(
        project_id=project_id,
        project_binding_ref=project_binding_ref,
        work_unit_ref=work_unit_ref,
        adapter_kind=adapter_kind,
        estimated_duration_lower_minutes=estimated_duration_lower_minutes,
        estimated_duration_upper_minutes=estimated_duration_upper_minutes,
        estimate_confidence=estimate_confidence,
        major_steps=major_steps,
        next_progress_update_due_minutes=next_progress_update_due_minutes,
        variability_factors=variability_factors,
        opened_at=opened_at,
    )
    _commit_records(
        store,
        project_id,
        [("work_time_coordination_open", record["work_time_coordination_open_id"], record)],
        opened_at,
        transaction_prefix=f"WTC-OPEN-{record['work_time_coordination_open_id']}",
    )
    return record


def record_work_time_progress_update(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    open_ref: Mapping[str, str],
    predecessor_ref: Mapping[str, str],
    sequence_number: int,
    position_kind: str,
    current_position: str,
    material_result_or_blocker: str,
    is_material_reestimate: bool,
    remaining_duration_unknown: bool,
    revised_remaining_duration_lower_minutes: int | None,
    revised_remaining_duration_upper_minutes: int | None,
    human_action_required: bool,
    recorded_at: str,
) -> dict[str, Any]:
    """Issue #22's own "Progress Heartbeat" / "Estimate Revision" / "External Wait" sections,
    committed as one immutable ``work_time_coordination_update`` record chained to
    *predecessor_ref* (either the coordination's own ``open_ref`` for the first update, or the
    prior update for every later one). A retry at the identical *sequence_number* with the
    identical body is idempotent; a second, differently-bodied update at that sequence number
    collides and is refused -- exactly the required "conflicting update"/replay negative
    control."""

    boot_context = boot_project(store, project_id=project_id, project_binding_id=project_binding_id)
    project_binding_ref = {"kind": "project_binding", "id": boot_context.project_binding_id}
    record = build_work_time_coordination_update(
        project_id=project_id,
        project_binding_ref=project_binding_ref,
        open_ref=open_ref,
        predecessor_ref=predecessor_ref,
        sequence_number=sequence_number,
        position_kind=position_kind,
        current_position=current_position,
        material_result_or_blocker=material_result_or_blocker,
        is_material_reestimate=is_material_reestimate,
        remaining_duration_unknown=remaining_duration_unknown,
        revised_remaining_duration_lower_minutes=revised_remaining_duration_lower_minutes,
        revised_remaining_duration_upper_minutes=revised_remaining_duration_upper_minutes,
        human_action_required=human_action_required,
        recorded_at=recorded_at,
    )
    _commit_records(
        store,
        project_id,
        [("work_time_coordination_update", record["work_time_coordination_update_id"], record)],
        recorded_at,
        transaction_prefix=f"WTC-UPDATE-{record['work_time_coordination_update_id']}",
    )
    return record


def record_work_time_terminal_notice(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    open_ref: Mapping[str, str],
    predecessor_ref: Mapping[str, str],
    terminal_outcome: str,
    actual_elapsed_minutes: int,
    explanation: str,
    recorded_at: str,
) -> dict[str, Any]:
    """Issue #22's own "Terminal Notice": committed as the one immutable ``work_time_
    coordination_terminal`` record a coordination (named by *open_ref*) will ever admit --
    enforced by construction, since :func:`~manosube_agent_civilization.work_time_transparency.
    identity.work_time_coordination_terminal_id` is a pure function of ``open_ref.id`` alone. A
    second, differently-bodied terminal notice for the identical coordination collides and is
    refused, never silently admitted as a second terminal fact."""

    boot_context = boot_project(store, project_id=project_id, project_binding_id=project_binding_id)
    project_binding_ref = {"kind": "project_binding", "id": boot_context.project_binding_id}
    record = build_work_time_coordination_terminal(
        project_id=project_id,
        project_binding_ref=project_binding_ref,
        open_ref=open_ref,
        predecessor_ref=predecessor_ref,
        terminal_outcome=terminal_outcome,
        actual_elapsed_minutes=actual_elapsed_minutes,
        explanation=explanation,
        recorded_at=recorded_at,
    )
    _commit_records(
        store,
        project_id,
        [("work_time_coordination_terminal", record["work_time_coordination_terminal_id"], record)],
        recorded_at,
        transaction_prefix=f"WTC-TERMINAL-{record['work_time_coordination_terminal_id']}",
    )
    return record


__all__ = [
    "open_work_time_coordination",
    "record_work_time_progress_update",
    "record_work_time_terminal_notice",
]
