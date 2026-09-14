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

**Structural Review Round 1 corrections (P84-R1-F2/F3/F5/F6).** Every caller-owned mutable input
is detached (deep-copied) as the literal first operation of every public entrypoint, before
``boot_project`` or any other call (P84-R1-F6) -- see :func:`_detach`. ``open_ref``/
``predecessor_ref`` are never trusted as caller-supplied record bodies: every continuation
resolves and verifies its own lineage from this project's own Store through
:mod:`~manosube_agent_civilization.work_time_transparency.verify`'s own canonical resolve-and-
verify boundary (P84-R1-F2/F5) before any record is built, and that whole resolve-verify-build
sequence runs fresh inside :func:`_commit_tip_dependent`'s own retry loop, so a concurrent writer
is corrected on retry rather than committed against a stale tip. ``is_material_reestimate`` and
``heartbeat_deadline_breached`` are never raw caller-supplied booleans -- both are derived here,
from the resolved canonical predecessor's own state, immediately before being embedded in a
built record (P84-R1-F3).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store.commit import commit_state_transition
from manosube_agent_civilization.store.errors import RecordConflictError, StaleStateError

from .clock import elapsed_minutes
from .engine import (
    build_work_time_coordination_open,
    build_work_time_coordination_terminal,
    build_work_time_coordination_update,
    is_heartbeat_overdue,
    is_material_reestimate,
)
from .errors import WorkTimeTransparencyLineageError, WorkTimeTransparencyValidationError
from .types import ADAPTER_KIND_TO_WORK_UNIT_REF_KIND
from .verify import (
    resolve_open,
    resolve_predecessor_at_sequence,
    resolve_terminal_if_exists,
    resolve_tip,
    verify_binding_congruity,
    verify_monotonic_continuation,
    verify_predecessor_matches,
)

_MAX_COMMIT_RETRIES = 8


def _detach(value: Any) -> Any:
    """Deep-copy any caller-owned mapping/list/tuple so a caller mutating its own object after
    passing it into a public entrypoint can never change what gets committed (Structural Review
    Round 1, P84-R1-F6). Called as the literal first operation on every mutable parameter of
    every public entrypoint below, before ``boot_project`` or any other call."""

    if isinstance(value, Mapping):
        return {key: _detach(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_detach(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_detach(item) for item in value)
    return value


def _new_transaction(
    current_state: dict[str, Any], project_id: str, transaction_id: str, committed_at: str
) -> tuple[dict[str, Any], dict[str, Any]]:
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
    return next_state, transition


def _commit_records(
    store: Any,
    project_id: str,
    records: list[tuple[str, str, dict[str, Any]]],
    committed_at: str,
    *,
    transaction_prefix: str,
) -> dict[str, Any]:
    """The bounded Compare-And-Swap retry template ``change_executor/route.py``'s own
    ``_commit_records`` uses, for records whose content does not depend on this project's own
    live tip (``open_work_time_coordination`` alone -- an open record's content is a pure
    function of its own caller-supplied inputs, not of anything already committed)."""

    for _ in range(_MAX_COMMIT_RETRIES):
        current_state = store.load_current(project_id)
        transaction_id = f"{transaction_prefix}-{current_state['state_revision']}"
        next_state, transition = _new_transaction(
            current_state, project_id, transaction_id, committed_at
        )
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


def _commit_tip_dependent(
    store: Any,
    project_id: str,
    committed_at: str,
    *,
    transaction_prefix: str,
    build: Callable[[], tuple[str, str, dict[str, Any]]],
) -> dict[str, Any]:
    """The identical retry template as :func:`_commit_records`, except *build* -- the whole
    resolve-lineage/verify/derive/build sequence for a Work Coordination Update or Terminal
    Notice -- is called fresh at the top of every attempt, after re-reading this project's own
    current committed State. A concurrent writer that lands between one attempt's own lineage
    resolution and its commit is therefore corrected on the next retry (which re-resolves the
    live tip against the now-current State) rather than committed against a stale tip
    (Structural Review Round 1, P84-R1-F2). A genuine lineage/validation refusal raised by
    *build* itself (not a Compare-And-Swap staleness) always propagates immediately -- it is
    never retried, since re-resolving the identical current State would only reproduce the
    identical refusal."""

    for _ in range(_MAX_COMMIT_RETRIES):
        current_state = store.load_current(project_id)
        kind, record_id, record = build()
        transaction_id = f"{transaction_prefix}-{current_state['state_revision']}"
        next_state, transition = _new_transaction(
            current_state, project_id, transaction_id, committed_at
        )
        try:
            commit_state_transition(
                store,
                project_id,
                current_state["state_revision"],
                current_state["semantic_fingerprint"],
                next_state,
                transition,
                records=[(kind, record_id, record)],
            )
            return record
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
    (:class:`RecordConflictError`) -- a work unit is estimated exactly once.

    *adapter_kind* must name the one canonical :data:`~manosube_agent_civilization.
    work_time_transparency.types.ADAPTER_KIND_TO_WORK_UNIT_REF_KIND`-mapped ``work_unit_ref``
    kind -- an adapter cannot open a coordination under a foreign work-unit kind (Structural
    Review Round 1, P84-R1-F6)."""

    work_unit_ref = _detach(work_unit_ref)
    major_steps = _detach(major_steps)

    if adapter_kind not in ADAPTER_KIND_TO_WORK_UNIT_REF_KIND:
        raise WorkTimeTransparencyValidationError(f"unrecognized adapter_kind: {adapter_kind!r}")
    expected_work_unit_kind = ADAPTER_KIND_TO_WORK_UNIT_REF_KIND[adapter_kind]
    if work_unit_ref.get("kind") != expected_work_unit_kind:
        raise WorkTimeTransparencyValidationError(
            f"adapter_kind {adapter_kind!r} requires work_unit_ref.kind == "
            f"{expected_work_unit_kind!r}, got {work_unit_ref.get('kind')!r}"
        )

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
    remaining_duration_unknown: bool,
    revised_remaining_duration_lower_minutes: int | None,
    revised_remaining_duration_upper_minutes: int | None,
    human_action_required: bool,
    next_progress_update_due_minutes: int,
    recorded_at: str,
) -> dict[str, Any]:
    """Issue #22's own "Progress Heartbeat" / "Estimate Revision" / "External Wait" sections,
    committed as one immutable ``work_time_coordination_update`` record chained to
    *predecessor_ref*. A retry at the identical *sequence_number* with the identical body is
    idempotent; a second, differently-bodied update at that sequence number collides and is
    refused.

    Unlike the pre-Round-1 signature, this function no longer accepts ``is_material_reestimate``
    from the caller at all: it resolves *open_ref* and the record that genuinely sits at
    ``sequence_number - 1`` in this coordination's own Store-committed chain, verifies
    *predecessor_ref* names exactly that record (refusing a skipped, reordered, forked, cross-
    coordination, or cross-project predecessor), verifies *recorded_at* is not before that
    record's own time, and only then derives ``is_material_reestimate``/
    ``heartbeat_deadline_breached`` from its canonical state before building the record
    (Structural Review Round 1, P84-R1-F2/F3/F5)."""

    open_ref = _detach(open_ref)
    predecessor_ref = _detach(predecessor_ref)

    boot_context = boot_project(store, project_id=project_id, project_binding_id=project_binding_id)
    project_binding_ref = {"kind": "project_binding", "id": boot_context.project_binding_id}

    def _resolve_verify_and_build() -> tuple[str, str, dict[str, Any]]:
        open_record = resolve_open(store, project_id, open_ref)
        verify_binding_congruity(
            open_record=open_record, project_binding_id=boot_context.project_binding_id
        )
        open_id = open_record["work_time_coordination_open_id"]
        if resolve_terminal_if_exists(store, project_id, open_id) is not None:
            raise WorkTimeTransparencyLineageError(
                f"coordination {open_id!r} already has a terminal notice -- update-after-"
                "terminal refused"
            )

        expected_predecessor = resolve_predecessor_at_sequence(
            store, project_id, open_record, sequence_number
        )
        verify_predecessor_matches(
            predecessor_ref=predecessor_ref, expected_record=expected_predecessor
        )
        verify_monotonic_continuation(
            expected_record=expected_predecessor, new_recorded_at=recorded_at
        )

        if sequence_number == 1:
            previous_remaining_lower = open_record["estimated_duration_lower_minutes"]
            previous_remaining_upper = open_record["estimated_duration_upper_minutes"]
            previous_position_kind: str | None = None
            previous_due_minutes = open_record["next_progress_update_due_minutes"]
        else:
            previous_remaining_lower = (
                None
                if expected_predecessor["remaining_duration_unknown"]
                else expected_predecessor["revised_remaining_duration_lower_minutes"]
            )
            previous_remaining_upper = (
                None
                if expected_predecessor["remaining_duration_unknown"]
                else expected_predecessor["revised_remaining_duration_upper_minutes"]
            )
            previous_position_kind = expected_predecessor["position_kind"]
            previous_due_minutes = expected_predecessor["next_progress_update_due_minutes"]

        new_blocking_dependency = position_kind == "BLOCKED" and previous_position_kind != "BLOCKED"
        derived_is_material_reestimate = is_material_reestimate(
            previous_remaining_lower_minutes=previous_remaining_lower,
            previous_remaining_upper_minutes=previous_remaining_upper,
            new_remaining_lower_minutes=(
                None if remaining_duration_unknown else revised_remaining_duration_lower_minutes
            ),
            new_remaining_upper_minutes=(
                None if remaining_duration_unknown else revised_remaining_duration_upper_minutes
            ),
            new_blocking_dependency=new_blocking_dependency,
        )

        elapsed_since_open = elapsed_minutes(open_record["opened_at"], recorded_at)
        # Unlike is_heartbeat_overdue's own read-side semantics (designed to ask "has any update
        # arrived by the deadline", which is vacuously false once an update *is* arriving), this
        # is a direct write-time comparison: did *this* update's own recorded_at land after the
        # deadline its own predecessor declared?
        heartbeat_deadline_breached = elapsed_since_open > previous_due_minutes
        if next_progress_update_due_minutes - elapsed_since_open > 10:
            raise WorkTimeTransparencyValidationError(
                "next_progress_update_due_minutes must be at most 10 minutes after this "
                "update's own elapsed-since-open time (Structural Review Round 1 P84-R1-F3)"
            )

        record = build_work_time_coordination_update(
            project_id=project_id,
            project_binding_ref=project_binding_ref,
            open_ref=open_ref,
            predecessor_ref=predecessor_ref,
            sequence_number=sequence_number,
            position_kind=position_kind,
            current_position=current_position,
            material_result_or_blocker=material_result_or_blocker,
            is_material_reestimate=derived_is_material_reestimate,
            remaining_duration_unknown=remaining_duration_unknown,
            revised_remaining_duration_lower_minutes=revised_remaining_duration_lower_minutes,
            revised_remaining_duration_upper_minutes=revised_remaining_duration_upper_minutes,
            human_action_required=human_action_required,
            next_progress_update_due_minutes=next_progress_update_due_minutes,
            heartbeat_deadline_breached=heartbeat_deadline_breached,
            recorded_at=recorded_at,
        )
        return (
            "work_time_coordination_update",
            record["work_time_coordination_update_id"],
            record,
        )

    return _commit_tip_dependent(
        store,
        project_id,
        recorded_at,
        transaction_prefix=f"WTC-UPDATE-{open_ref['id']}-{sequence_number}",
        build=_resolve_verify_and_build,
    )


def record_work_time_terminal_notice(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    open_ref: Mapping[str, str],
    predecessor_ref: Mapping[str, str],
    terminal_outcome: str,
    explanation: str,
    recorded_at: str,
) -> dict[str, Any]:
    """Issue #22's own "Terminal Notice": committed as the one immutable ``work_time_
    coordination_terminal`` record a coordination (named by *open_ref*) will ever admit --
    enforced by construction, since :func:`~manosube_agent_civilization.work_time_transparency.
    identity.work_time_coordination_terminal_id` is a pure function of ``open_ref.id`` alone. A
    second, differently-bodied terminal notice for the identical coordination collides and is
    refused, never silently admitted as a second terminal fact.

    Unlike the pre-Round-1 signature, this function no longer accepts ``actual_elapsed_minutes``
    from the caller: it is always derived from the resolved open record's own ``opened_at`` and
    this call's own *recorded_at* (Structural Review Round 1, P84-R1-F2/F4) -- a caller can no
    longer assert an elapsed time inconsistent with the coordination's own canonical timestamps.
    *predecessor_ref* is resolved and verified to be this coordination's own real live tip,
    exactly as :func:`record_work_time_progress_update` requires."""

    open_ref = _detach(open_ref)
    predecessor_ref = _detach(predecessor_ref)

    boot_context = boot_project(store, project_id=project_id, project_binding_id=project_binding_id)
    project_binding_ref = {"kind": "project_binding", "id": boot_context.project_binding_id}

    def _resolve_verify_and_build() -> tuple[str, str, dict[str, Any]]:
        open_record = resolve_open(store, project_id, open_ref)
        verify_binding_congruity(
            open_record=open_record, project_binding_id=boot_context.project_binding_id
        )
        tip_record, tip_sequence = resolve_tip(store, project_id, open_record)
        verify_predecessor_matches(predecessor_ref=predecessor_ref, expected_record=tip_record)
        verify_monotonic_continuation(expected_record=tip_record, new_recorded_at=recorded_at)

        previous_due_minutes = (
            open_record["next_progress_update_due_minutes"]
            if tip_sequence == 0
            else tip_record["next_progress_update_due_minutes"]
        )
        elapsed_since_open = elapsed_minutes(open_record["opened_at"], recorded_at)
        heartbeat_deadline_breached = is_heartbeat_overdue(
            opened_at_minutes=0,
            next_progress_update_due_minutes=previous_due_minutes,
            now_minutes=elapsed_since_open,
            has_update=tip_sequence >= 1,
        )

        record = build_work_time_coordination_terminal(
            project_id=project_id,
            project_binding_ref=project_binding_ref,
            open_ref=open_ref,
            predecessor_ref=predecessor_ref,
            terminal_outcome=terminal_outcome,
            actual_elapsed_minutes=elapsed_since_open,
            heartbeat_deadline_breached=heartbeat_deadline_breached,
            explanation=explanation,
            recorded_at=recorded_at,
        )
        return (
            "work_time_coordination_terminal",
            record["work_time_coordination_terminal_id"],
            record,
        )

    return _commit_tip_dependent(
        store,
        project_id,
        recorded_at,
        transaction_prefix=f"WTC-TERMINAL-{open_ref['id']}",
        build=_resolve_verify_and_build,
    )


__all__ = [
    "open_work_time_coordination",
    "record_work_time_progress_update",
    "record_work_time_terminal_notice",
]
