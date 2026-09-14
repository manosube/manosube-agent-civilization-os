"""Issue #22's own required negative/replay/tamper matrix: "replay, stale-state, cross-work-unit
substitution, alias/TOCTOU, missing-heartbeat, late-heartbeat, and conflicting-terminal negative
controls."

Every identity-collision control here is closed by the identical mechanism -- deterministic,
narrow ids (:mod:`manosube_agent_civilization.work_time_transparency.identity`) resolved through
the Store's own already-existing same-id-same-body replay tolerance and same-id-different-body
conflict refusal (:class:`~manosube_agent_civilization.store.errors.RecordConflictError`) --
never a bespoke mechanism this package invents for itself.

Structural Review Round 1 (P84-R1-F2/F5) additionally requires every lineage-integrity control
(nonexistent open, cross-project/cross-coordination predecessor, skipped/reordered/forked
sequence, terminal-before-open, update-after-terminal, non-monotonic time, wrong-kind reference)
to be refused *through the real public route boundary* --
:mod:`~manosube_agent_civilization.work_time_transparency.route`'s own resolve-and-verify
sequence -- raising :class:`~manosube_agent_civilization.work_time_transparency.errors.
WorkTimeTransparencyLineageError`, never merely observed by a test recomputing a fingerprint or
checking Store presence/absence itself.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.fixtures.work_time_transparency_world import bound

from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.store.errors import RecordConflictError
from manosube_agent_civilization.work_time_transparency.engine import is_heartbeat_overdue
from manosube_agent_civilization.work_time_transparency.errors import (
    WorkTimeTransparencyLineageError,
    WorkTimeTransparencyValidationError,
)
import manosube_agent_civilization.work_time_transparency.route as route_module
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


def _update_ref(update_record: dict[str, Any]) -> dict[str, str]:
    return {
        "kind": "work_time_coordination_update",
        "id": update_record["work_time_coordination_update_id"],
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
        "remaining_duration_unknown": False,
        "revised_remaining_duration_lower_minutes": 3,
        "revised_remaining_duration_upper_minutes": 8,
        "human_action_required": False,
        "next_progress_update_due_minutes": 20,
        "recorded_at": "2026-09-14T06:10:00Z",
    }
    kwargs.update(overrides)
    return kwargs


def _terminal_kwargs(
    world: dict[str, Any],
    open_ref: dict[str, str],
    predecessor_ref: dict[str, str],
    **overrides: object,
) -> dict[str, Any]:
    kwargs: dict[str, object] = {
        "project_id": world["project_id"],
        "project_binding_id": world["project_binding_id"],
        "open_ref": open_ref,
        "predecessor_ref": predecessor_ref,
        "terminal_outcome": "COMPLETED",
        "explanation": "",
        "recorded_at": "2026-09-14T06:05:00Z",
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
    record_work_time_terminal_notice(store, **_terminal_kwargs(world, open_ref, open_ref))
    with pytest.raises(RecordConflictError):
        record_work_time_terminal_notice(
            store,
            **_terminal_kwargs(
                world,
                open_ref,
                open_ref,
                terminal_outcome="FAILED_TERMINAL",
                explanation="a conflicting second outcome for the identical coordination",
                recorded_at="2026-09-14T06:05:01Z",
            ),
        )


def test_replaying_the_identical_terminal_notice_is_idempotent(tmp_path: Path) -> None:
    store, world = bound(tmp_path)
    open_record = _open(store, world)
    open_ref = _open_ref(open_record)
    kwargs = _terminal_kwargs(world, open_ref, open_ref)
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


def test_a_predecessor_ref_computed_under_a_different_project_id_is_refused_through_the_real_boundary(
    tmp_path: Path,
) -> None:
    """A predecessor id computed under a foreign ``project_id`` can never equal this
    coordination's own genuinely-resolved predecessor -- proven directly (not merely via two
    Store instances that happen to share identical ``project_id`` text, which
    ``test_cross_project_substitution_a_coordination_opened_in_one_store_is_absent_from_another``
    already covers as a Store-instance-isolation property)."""

    from manosube_agent_civilization.work_time_transparency.identity import (
        work_time_coordination_open_id,
    )

    store, world = bound(tmp_path)
    open_record = _open(store, world)
    open_ref = _open_ref(open_record)
    foreign_id = work_time_coordination_open_id("PROJECT-ENTIRELY-DIFFERENT", WORK_UNIT_REF)
    foreign_ref = {"kind": "work_time_coordination_open", "id": foreign_id}
    with pytest.raises(WorkTimeTransparencyLineageError):
        record_work_time_progress_update(
            store, **_heartbeat_kwargs(world, open_ref, foreign_ref, 1)
        )


def test_a_predecessor_ref_from_a_different_coordination_is_refused_through_the_real_boundary(
    tmp_path: Path,
) -> None:
    store, world = bound(tmp_path)
    first = _open(store, world, work_unit_ref=WORK_UNIT_REF)
    second = _open(store, world, work_unit_ref=OTHER_WORK_UNIT_REF)
    with pytest.raises(WorkTimeTransparencyLineageError):
        record_work_time_progress_update(
            store, **_heartbeat_kwargs(world, _open_ref(first), _open_ref(second), 1)
        )


def test_a_skipped_sequence_number_is_refused_through_the_real_boundary(tmp_path: Path) -> None:
    store, world = bound(tmp_path)
    open_record = _open(store, world)
    open_ref = _open_ref(open_record)
    with pytest.raises(WorkTimeTransparencyLineageError):
        record_work_time_progress_update(store, **_heartbeat_kwargs(world, open_ref, open_ref, 2))


def test_a_forked_predecessor_off_a_stale_tip_is_refused_through_the_real_boundary(
    tmp_path: Path,
) -> None:
    store, world = bound(tmp_path)
    open_record = _open(store, world)
    open_ref = _open_ref(open_record)
    first_update = record_work_time_progress_update(
        store, **_heartbeat_kwargs(world, open_ref, open_ref, 1)
    )
    first_ref = _update_ref(first_update)
    record_work_time_progress_update(
        store,
        **_heartbeat_kwargs(
            world,
            open_ref,
            first_ref,
            2,
            next_progress_update_due_minutes=30,
            recorded_at="2026-09-14T06:20:00Z",
        ),
    )
    # the live tip is now sequence 2; forking a third update off the now-stale sequence-1
    # predecessor must be refused, never silently accepted as a second branch.
    with pytest.raises(WorkTimeTransparencyLineageError):
        record_work_time_progress_update(
            store,
            **_heartbeat_kwargs(world, open_ref, first_ref, 3, recorded_at="2026-09-14T06:25:00Z"),
        )


def test_terminal_before_open_is_refused_through_the_real_boundary(tmp_path: Path) -> None:
    store, world = bound(tmp_path)
    fabricated_open_ref = {"kind": "work_time_coordination_open", "id": "WTC-OPEN-" + "0" * 64}
    with pytest.raises(WorkTimeTransparencyLineageError):
        record_work_time_terminal_notice(
            store, **_terminal_kwargs(world, fabricated_open_ref, fabricated_open_ref)
        )


def test_update_after_terminal_is_refused_through_the_real_boundary(tmp_path: Path) -> None:
    store, world = bound(tmp_path)
    open_record = _open(store, world)
    open_ref = _open_ref(open_record)
    record_work_time_terminal_notice(store, **_terminal_kwargs(world, open_ref, open_ref))
    with pytest.raises(WorkTimeTransparencyLineageError):
        record_work_time_progress_update(store, **_heartbeat_kwargs(world, open_ref, open_ref, 1))


def test_a_non_monotonic_update_time_is_refused_through_the_real_boundary(tmp_path: Path) -> None:
    store, world = bound(tmp_path)
    open_record = _open(store, world)
    open_ref = _open_ref(open_record)
    with pytest.raises(WorkTimeTransparencyLineageError):
        record_work_time_progress_update(
            store,
            **_heartbeat_kwargs(world, open_ref, open_ref, 1, recorded_at="2026-09-14T05:59:00Z"),
        )


def test_a_non_monotonic_terminal_time_is_refused_through_the_real_boundary(
    tmp_path: Path,
) -> None:
    store, world = bound(tmp_path)
    open_record = _open(store, world)
    open_ref = _open_ref(open_record)
    with pytest.raises(WorkTimeTransparencyLineageError):
        record_work_time_terminal_notice(
            store,
            **_terminal_kwargs(world, open_ref, open_ref, recorded_at="2026-09-14T05:59:00Z"),
        )


def test_a_wrong_kind_predecessor_ref_is_refused_through_the_real_boundary(
    tmp_path: Path,
) -> None:
    store, world = bound(tmp_path)
    open_record = _open(store, world)
    open_ref = _open_ref(open_record)
    bogus_ref = {"kind": "work_time_coordination_terminal", "id": open_ref["id"]}
    with pytest.raises(WorkTimeTransparencyLineageError):
        record_work_time_progress_update(store, **_heartbeat_kwargs(world, open_ref, bogus_ref, 1))


def test_a_late_heartbeat_past_its_own_due_deadline_is_still_accepted_and_recorded_but_marked_breached(
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
            next_progress_update_due_minutes=50,
            current_position="finally checking in, well past the 10-minute due mark",
        ),
    )
    assert late_update["recorded_at"] == "2026-09-14T06:45:00Z"
    assert late_update["heartbeat_deadline_breached"] is True
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
        **_terminal_kwargs(
            world,
            open_ref,
            open_ref,
            terminal_outcome="FAILED_TERMINAL",
            explanation="crashed silently; no heartbeat was ever posted",
            recorded_at="2026-09-14T07:00:00Z",
        ),
    )
    assert terminal["terminal_outcome"] == "FAILED_TERMINAL"
    assert terminal["actual_elapsed_minutes"] == 60
    assert terminal["heartbeat_deadline_breached"] is True


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


def test_a_tampered_predecessor_ref_id_substituted_for_a_real_foreign_record_is_refused(
    tmp_path: Path,
) -> None:
    """ID substitution through the real public boundary: *predecessor_ref* names a real,
    genuinely-committed record -- just not this coordination's own tip -- so it cannot be
    accepted merely because it resolves to *something* real (Structural Review Round 1,
    P84-R1-F5)."""

    store, world = bound(tmp_path)
    victim = _open(store, world, work_unit_ref=WORK_UNIT_REF)
    attacker_open = _open(store, world, work_unit_ref=OTHER_WORK_UNIT_REF)
    with pytest.raises(WorkTimeTransparencyLineageError):
        record_work_time_terminal_notice(
            store, **_terminal_kwargs(world, _open_ref(victim), _open_ref(attacker_open))
        )


# --- Structural Review Round 1 (P84-R1-F6) ---------------------------------------------------- #


def test_an_adapter_kind_bound_to_the_wrong_work_unit_ref_kind_is_refused(tmp_path: Path) -> None:
    """An adapter cannot open a coordination under a foreign work-unit kind -- ``CHANGE_EXECUTOR``
    requires ``work_unit_ref.kind == "change_executor_execution"``, never ``"boot_session"``, even
    though ``boot_session`` is itself a real, closed ``WORK_UNIT_REF_KINDS`` member (P84-R1-F6)."""

    store, world = bound(tmp_path)
    before_revision = store.load_current(world["project_id"])["state_revision"]
    with pytest.raises(WorkTimeTransparencyValidationError):
        open_work_time_coordination(
            store,
            project_id=world["project_id"],
            project_binding_id=world["project_binding_id"],
            work_unit_ref={"kind": "boot_session", "id": "WORK-UNIT-MISMATCHED-KIND-1"},
            adapter_kind="CHANGE_EXECUTOR",
            estimated_duration_lower_minutes=5,
            estimated_duration_upper_minutes=15,
            estimate_confidence="MEDIUM",
            major_steps=["step one"],
            next_progress_update_due_minutes=10,
            variability_factors="none",
            opened_at="2026-09-14T06:00:00Z",
        )
    assert store.load_current(world["project_id"])["state_revision"] == before_revision


def test_mutating_caller_owned_inputs_while_boot_project_runs_never_reaches_the_committed_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``_detach(...)`` runs as the literal first operation of ``open_work_time_coordination``,
    before ``boot_project(...)`` is ever called (P84-R1-F6). Proven here by making
    ``boot_project`` itself -- while it runs -- mutate the caller's own, still-referenced
    ``work_unit_ref``/``major_steps`` objects: since a detached (deep-copied) snapshot was already
    taken before ``boot_project`` was reached, the committed record reflects only the pre-mutation
    values, never the mutation that happened during Boot."""

    store, world = bound(tmp_path)
    work_unit_ref = {"kind": "change_executor_execution", "id": "WORK-UNIT-MUTATION-ORIGINAL-1"}
    major_steps = ["original step"]
    real_boot_project = boot_project

    def _mutating_boot_project(*args: Any, **kwargs: Any) -> Any:
        work_unit_ref["id"] = "MUTATED-DURING-BOOT"
        major_steps.append("mutated during boot")
        return real_boot_project(*args, **kwargs)

    monkeypatch.setattr(route_module, "boot_project", _mutating_boot_project)

    record = open_work_time_coordination(
        store,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        work_unit_ref=work_unit_ref,
        adapter_kind="CHANGE_EXECUTOR",
        estimated_duration_lower_minutes=5,
        estimated_duration_upper_minutes=15,
        estimate_confidence="MEDIUM",
        major_steps=major_steps,
        next_progress_update_due_minutes=10,
        variability_factors="none",
        opened_at="2026-09-14T06:00:00Z",
    )

    # the caller's own objects genuinely were mutated in place by boot_project...
    assert work_unit_ref["id"] == "MUTATED-DURING-BOOT"
    assert major_steps == ["original step", "mutated during boot"]
    # ...but the committed record reflects only what was true before boot_project ever ran.
    assert record["work_unit_ref"] == {
        "kind": "change_executor_execution",
        "id": "WORK-UNIT-MUTATION-ORIGINAL-1",
    }
    assert record["major_steps"] == ["original step"]
    resolved = store.resolve_record(
        world["project_id"],
        "work_time_coordination_open",
        record["work_time_coordination_open_id"],
    )
    assert resolved == record
