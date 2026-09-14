"""Issue #22 natural-route proof: a real ``FileStateStore``, a real bound project, and the three
canonical entrypoints called exactly as a real caller would -- open, two heartbeats (one plain,
one material re-estimate), then a terminal notice -- proving the full coordination chain commits,
resolves, and validates end to end, not merely in isolated unit construction.

Structural Review Round 1 (P84-R1-F2/F3): ``is_material_reestimate`` is no longer a caller-
supplied argument to :func:`record_work_time_progress_update` -- it is derived server-side from
the resolved predecessor -- and ``actual_elapsed_minutes`` is no longer a caller-supplied
argument to :func:`record_work_time_terminal_notice` -- it is derived server-side from the
resolved open record's own ``opened_at`` and this call's own ``recorded_at``. Both derivations
are asserted below against the fixed, deterministic timestamps this test already uses.
"""

from __future__ import annotations

from pathlib import Path

from tests.fixtures.work_time_transparency_world import bound

from manosube_agent_civilization.work_time_transparency.route import (
    open_work_time_coordination,
    record_work_time_progress_update,
    record_work_time_terminal_notice,
)

WORK_UNIT_REF = {"kind": "change_executor_execution", "id": "WORK-UNIT-NATURAL-ROUTE-1"}


def test_the_full_open_heartbeat_reestimate_terminal_chain_commits_and_resolves(
    tmp_path: Path,
) -> None:
    store, world = bound(tmp_path)
    project_id = world["project_id"]
    project_binding_id = world["project_binding_id"]

    open_record = open_work_time_coordination(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        work_unit_ref=WORK_UNIT_REF,
        adapter_kind="CHANGE_EXECUTOR",
        estimated_duration_lower_minutes=5,
        estimated_duration_upper_minutes=15,
        estimate_confidence="MEDIUM",
        major_steps=["resolve boundary", "execute", "commit receipt"],
        next_progress_update_due_minutes=10,
        variability_factors="external filesystem latency",
        opened_at="2026-09-14T06:00:00Z",
    )
    open_ref = {
        "kind": "work_time_coordination_open",
        "id": open_record["work_time_coordination_open_id"],
    }
    resolved_open = store.resolve_record(project_id, "work_time_coordination_open", open_ref["id"])
    assert resolved_open == open_record

    heartbeat = record_work_time_progress_update(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        open_ref=open_ref,
        predecessor_ref=open_ref,
        sequence_number=1,
        position_kind="WORK_RUNNING",
        current_position="boundary resolved, executing",
        material_result_or_blocker="",
        remaining_duration_unknown=False,
        revised_remaining_duration_lower_minutes=3,
        revised_remaining_duration_upper_minutes=8,
        human_action_required=False,
        next_progress_update_due_minutes=20,
        recorded_at="2026-09-14T06:10:00Z",
    )
    heartbeat_ref = {
        "kind": "work_time_coordination_update",
        "id": heartbeat["work_time_coordination_update_id"],
    }
    assert (
        store.resolve_record(project_id, "work_time_coordination_update", heartbeat_ref["id"])
        == heartbeat
    )
    # revised remaining (3-8) vs the original estimate (5-15): both bounds moved by >= 5 --
    # derived server-side from the resolved open record, never a raw caller-supplied boolean.
    assert heartbeat["is_material_reestimate"] is True
    assert heartbeat["heartbeat_deadline_breached"] is False

    reestimate = record_work_time_progress_update(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        open_ref=open_ref,
        predecessor_ref=heartbeat_ref,
        sequence_number=2,
        position_kind="EXTERNAL_REVIEW_WAIT",
        current_position="waiting on external filesystem lock release",
        material_result_or_blocker="an unrelated process is holding a lock on the target path",
        remaining_duration_unknown=True,
        revised_remaining_duration_lower_minutes=None,
        revised_remaining_duration_upper_minutes=None,
        human_action_required=False,
        next_progress_update_due_minutes=27,
        recorded_at="2026-09-14T06:20:00Z",
    )
    reestimate_ref = {
        "kind": "work_time_coordination_update",
        "id": reestimate["work_time_coordination_update_id"],
    }
    assert reestimate["remaining_duration_unknown"] is True
    assert reestimate_ref["id"] != heartbeat_ref["id"]
    # a transition into "unknown remaining duration" is always material.
    assert reestimate["is_material_reestimate"] is True

    terminal = record_work_time_terminal_notice(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        open_ref=open_ref,
        predecessor_ref=reestimate_ref,
        terminal_outcome="COMPLETED",
        explanation="lock released, execution completed within the revised (unknown-then-bounded) window",
        recorded_at="2026-09-14T06:27:00Z",
    )
    assert (
        store.resolve_record(
            project_id,
            "work_time_coordination_terminal",
            terminal["work_time_coordination_terminal_id"],
        )
        == terminal
    )
    assert terminal["terminal_outcome"] == "COMPLETED"
    # derived from open.opened_at (06:00:00) and this call's own recorded_at (06:27:00).
    assert terminal["actual_elapsed_minutes"] == 27

    final_state = store.load_current(project_id)
    assert final_state["state_revision"] == world["genesis_state"]["state_revision"] + 4


def test_short_work_can_go_directly_from_open_to_terminal_with_zero_heartbeats(
    tmp_path: Path,
) -> None:
    store, world = bound(tmp_path)
    project_id = world["project_id"]
    project_binding_id = world["project_binding_id"]
    work_unit_ref = {"kind": "boot_session", "id": "WORK-UNIT-SHORT-1"}

    open_record = open_work_time_coordination(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        work_unit_ref=work_unit_ref,
        adapter_kind="BOOT",
        estimated_duration_lower_minutes=0,
        estimated_duration_upper_minutes=1,
        estimate_confidence="HIGH",
        major_steps=["boot"],
        next_progress_update_due_minutes=1,
        variability_factors="none",
        opened_at="2026-09-14T07:00:00Z",
    )
    open_ref = {
        "kind": "work_time_coordination_open",
        "id": open_record["work_time_coordination_open_id"],
    }

    terminal = record_work_time_terminal_notice(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        open_ref=open_ref,
        predecessor_ref=open_ref,
        terminal_outcome="COMPLETED",
        explanation="",
        recorded_at="2026-09-14T07:01:00Z",
    )
    assert terminal["predecessor_ref"] == open_ref
    assert terminal["actual_elapsed_minutes"] == 1
