"""Issue #22's own required negative/replay/tamper matrix: "replay, stale-state, cross-work-unit
substitution, alias/TOCTOU, missing-heartbeat, late-heartbeat, and conflicting-terminal negative
controls."

Every control here is closed by the identical mechanism -- deterministic, narrow ids
(:mod:`manosube_agent_civilization.work_time_transparency.identity`) resolved through the
Store's own already-existing same-id-same-body replay tolerance and same-id-different-body
conflict refusal (:class:`~manosube_agent_civilization.store.errors.RecordConflictError`) --
never a bespoke mechanism this package invents for itself.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.fixtures.work_time_transparency_world import bound

from manosube_agent_civilization.store.errors import RecordConflictError
from manosube_agent_civilization.work_time_transparency.engine import is_heartbeat_overdue
from manosube_agent_civilization.work_time_transparency.route import (
    open_work_time_coordination,
    record_work_time_progress_update,
    record_work_time_terminal_notice,
)

WORK_UNIT_REF = {"kind": "change_executor_execution", "id": "WORK-UNIT-MATRIX-1"}
OTHER_WORK_UNIT_REF = {"kind": "change_executor_execution", "id": "WORK-UNIT-MATRIX-2"}


def _open(
    store: object, world: dict[str, Any], *, work_unit_ref: dict[str, str] = WORK_UNIT_REF
) -> dict[str, Any]:
    return open_work_time_coordination(
        store,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        work_unit_ref=work_unit_ref,
        adapter_kind="CHANGE_EXECUTOR",
        estimated_duration_lower_minutes=5,
        estimated_duration_upper_minutes=15,
        estimate_confidence="MEDIUM",
        major_steps=["step one"],
        next_progress_update_due_minutes=10,
        variability_factors="none",
        opened_at="2026-09-14T06:00:00Z",
    )


def test_replaying_the_identical_open_call_is_idempotent(tmp_path: Path) -> None:
    store, world = bound(tmp_path)
    first = _open(store, world)
    second = _open(store, world)
    assert first == second


def test_a_second_open_with_a_different_estimate_for_the_identical_work_unit_is_refused(
    tmp_path: Path,
) -> None:
    store, world = bound(tmp_path)
    _open(store, world)
    with pytest.raises(RecordConflictError):
        open_work_time_coordination(
            store,
            project_id=world["project_id"],
            project_binding_id=world["project_binding_id"],
            work_unit_ref=WORK_UNIT_REF,
            adapter_kind="CHANGE_EXECUTOR",
            estimated_duration_lower_minutes=99,
            estimated_duration_upper_minutes=100,
            estimate_confidence="LOW",
            major_steps=["a different plan"],
            next_progress_update_due_minutes=10,
            variability_factors="none",
            opened_at="2026-09-14T06:00:00Z",
        )


def test_two_distinct_work_units_produce_two_genuinely_distinct_coordinations(
    tmp_path: Path,
) -> None:
    store, world = bound(tmp_path)
    first = _open(store, world, work_unit_ref=WORK_UNIT_REF)
    second = _open(store, world, work_unit_ref=OTHER_WORK_UNIT_REF)
    assert first["work_time_coordination_open_id"] != second["work_time_coordination_open_id"]


def _open_ref(open_record: dict[str, Any]) -> dict[str, str]:
    return {
        "kind": "work_time_coordination_open",
        "id": open_record["work_time_coordination_open_id"],
    }


def _heartbeat_kwargs(
    world: dict[str, Any],
    open_ref: dict[str, str],
    predecessor_ref: dict[str, str],
    sequence_number: int,
    **overrides: object,
) -> dict[str, Any]:
    kwargs: dict[str, object] = {
        "project_id": world["project_id"],
        "project_binding_id": world["project_binding_id"],
        "open_ref": open_ref,
        "predecessor_ref": predecessor_ref,
        "sequence_number": sequence_number,
        "position_kind": "WORK_RUNNING",
        "current_position": "running",
        "material_result_or_blocker": "",
        "is_material_reestimate": False,
        "remaining_duration_unknown": False,
        "revised_remaining_duration_lower_minutes": 3,
        "revised_remaining_duration_upper_minutes": 8,
        "human_action_required": False,
        "recorded_at": "2026-09-14T06:10:00Z",
    }
    kwargs.update(overrides)
    return kwargs


def test_replaying_the_identical_update_at_the_same_sequence_number_is_idempotent(
    tmp_path: Path,
) -> None:
    store, world = bound(tmp_path)
    open_record = _open(store, world)
    open_ref = _open_ref(open_record)
    first = record_work_time_progress_update(
        store, **_heartbeat_kwargs(world, open_ref, open_ref, 1)
    )
    second = record_work_time_progress_update(
        store, **_heartbeat_kwargs(world, open_ref, open_ref, 1)
    )
    assert first == second


def test_a_conflicting_update_at_the_same_sequence_number_is_refused(tmp_path: Path) -> None:
    store, world = bound(tmp_path)
    open_record = _open(store, world)
    open_ref = _open_ref(open_record)
    record_work_time_progress_update(store, **_heartbeat_kwargs(world, open_ref, open_ref, 1))
    with pytest.raises(RecordConflictError):
        record_work_time_progress_update(
            store,
            **_heartbeat_kwargs(
                world, open_ref, open_ref, 1, current_position="a different position entirely"
            ),
        )


def test_a_second_distinct_terminal_notice_for_the_identical_coordination_is_refused(
    tmp_path: Path,
) -> None:
    store, world = bound(tmp_path)
    open_record = _open(store, world)
    open_ref = _open_ref(open_record)
    record_work_time_terminal_notice(
        store,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        open_ref=open_ref,
        predecessor_ref=open_ref,
        terminal_outcome="COMPLETED",
        actual_elapsed_minutes=5,
        explanation="",
        recorded_at="2026-09-14T06:05:00Z",
    )
    with pytest.raises(RecordConflictError):
        record_work_time_terminal_notice(
            store,
            project_id=world["project_id"],
            project_binding_id=world["project_binding_id"],
            open_ref=open_ref,
            predecessor_ref=open_ref,
            terminal_outcome="FAILED_TERMINAL",
            actual_elapsed_minutes=5,
            explanation="a conflicting second outcome for the identical coordination",
            recorded_at="2026-09-14T06:05:01Z",
        )


def test_replaying_the_identical_terminal_notice_is_idempotent(tmp_path: Path) -> None:
    store, world = bound(tmp_path)
    open_record = _open(store, world)
    open_ref = _open_ref(open_record)
    kwargs = {
        "project_id": world["project_id"],
        "project_binding_id": world["project_binding_id"],
        "open_ref": open_ref,
        "predecessor_ref": open_ref,
        "terminal_outcome": "COMPLETED",
        "actual_elapsed_minutes": 5,
        "explanation": "",
        "recorded_at": "2026-09-14T06:05:00Z",
    }
    first = record_work_time_terminal_notice(store, **kwargs)
    second = record_work_time_terminal_notice(store, **kwargs)
    assert first == second


def test_cross_project_substitution_a_coordination_opened_in_one_store_is_absent_from_another(
    tmp_path: Path,
) -> None:
    store_a, world_a = bound(tmp_path, subdir="project-a")
    store_b, world_b = bound(tmp_path, subdir="project-b")
    open_record = _open(store_a, world_a)
    open_id = open_record["work_time_coordination_open_id"]
    assert (
        store_a.resolve_record(world_a["project_id"], "work_time_coordination_open", open_id)
        is not None
    )
    assert (
        store_b.resolve_record(world_b["project_id"], "work_time_coordination_open", open_id)
        is None
    )


def test_a_late_heartbeat_past_its_own_due_deadline_is_still_accepted_and_recorded(
    tmp_path: Path,
) -> None:
    store, world = bound(tmp_path)
    open_record = _open(store, world)
    open_ref = _open_ref(open_record)
    late_update = record_work_time_progress_update(
        store,
        **_heartbeat_kwargs(
            world,
            open_ref,
            open_ref,
            1,
            recorded_at="2026-09-14T06:45:00Z",
            current_position="finally checking in, well past the 10-minute due mark",
        ),
    )
    assert late_update["recorded_at"] == "2026-09-14T06:45:00Z"
    assert is_heartbeat_overdue(
        opened_at_minutes=0, next_progress_update_due_minutes=10, now_minutes=45, has_update=False
    )
    assert not is_heartbeat_overdue(
        opened_at_minutes=0, next_progress_update_due_minutes=10, now_minutes=45, has_update=True
    )


def test_missing_heartbeat_a_terminal_notice_never_requires_any_update_to_have_been_recorded(
    tmp_path: Path,
) -> None:
    store, world = bound(tmp_path)
    open_record = _open(store, world)
    open_ref = _open_ref(open_record)
    terminal = record_work_time_terminal_notice(
        store,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        open_ref=open_ref,
        predecessor_ref=open_ref,
        terminal_outcome="FAILED_TERMINAL",
        actual_elapsed_minutes=60,
        explanation="crashed silently; no heartbeat was ever posted",
        recorded_at="2026-09-14T07:00:00Z",
    )
    assert terminal["terminal_outcome"] == "FAILED_TERMINAL"


def test_post_commit_tampering_a_hand_edited_record_no_longer_matches_its_own_stored_fingerprint(
    tmp_path: Path,
) -> None:
    store, world = bound(tmp_path)
    open_record = _open(store, world)
    resolved = store.resolve_record(
        world["project_id"],
        "work_time_coordination_open",
        open_record["work_time_coordination_open_id"],
    )
    assert resolved is not None
    tampered = dict(resolved)
    tampered["estimated_duration_upper_minutes"] = 999
    from manosube_agent_civilization.work_time_transparency.identity import (
        work_time_coordination_open_semantic_fingerprint,
    )

    assert (
        work_time_coordination_open_semantic_fingerprint(tampered)
        != resolved["work_time_coordination_open_semantic_fingerprint"]
    )
