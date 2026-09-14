"""Issue #22's own required adapter conformance proof.

**Disclosed scope decision.** Boot (:func:`~manosube_agent_civilization.boot.boot_project`) is
wrapped here exactly as a real caller would: the composition primitive
(:func:`~manosube_agent_civilization.work_time_transparency.adapters.with_work_time_coordination`)
calls the real, completely unmodified production entrypoint, against a real ``FileStateStore``.
The other seven adapters this vertical must eventually conform (CLI, Temporary Agent, Model
Runtime, Multi-Agent, Change Executor, Independent Verification, GitHub Projection) each carry
their own substantial precondition chain (Authority Rules, Execution Boundaries, Model Execution
Grants, kill switches, verifier selections, GitHub projection grants) that this bounded work unit
does not reconstruct wholesale for a UX/coordination-only concern -- doing so would risk eight
already-accepted, already-reviewed verticals for no correctness benefit to any of them (see
``adapters.py``'s own module docstring for why this package never imports or modifies their
route.py files at all). What *is* proved for all eight, here: the one shared composition
primitive behaves identically -- open before, terminal after, ``COMPLETED`` on success,
``FAILED_TERMINAL`` with the original exception re-raised on failure -- for every one of the
closed :data:`~manosube_agent_civilization.work_time_transparency.types.ADAPTER_KINDS`, using a
representative callable standing in for "one real adapter call" at the interface
:func:`with_work_time_coordination` actually composes against (an arbitrary zero-argument
callable) -- the identical technique this repository's own adapter *Protocol* boundaries
(``RuntimeAdapter``, ``GitHubAdapter``) are proved against before a specific implementation is
wired in. Wiring each of the remaining seven adapters' own route.py through this primitive, with
each domain's own full fixture world, is this delivery's own disclosed follow-up.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.fixtures.work_time_transparency_world import bound

from manosube_agent_civilization.boot import BootContext, boot_project
from manosube_agent_civilization.work_time_transparency.adapters import with_work_time_coordination
from manosube_agent_civilization.work_time_transparency.identity import (
    work_time_coordination_open_id,
    work_time_coordination_terminal_id,
)
from manosube_agent_civilization.work_time_transparency.types import ADAPTER_KINDS


def test_boot_the_one_real_unmodified_production_entrypoint_composes_end_to_end(
    tmp_path: Path,
) -> None:
    store, world = bound(tmp_path)
    project_id = world["project_id"]
    project_binding_id = world["project_binding_id"]

    def _perform() -> BootContext:
        return boot_project(store, project_id=project_id, project_binding_id=project_binding_id)

    open_record, terminal_record, boot_context = with_work_time_coordination(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        adapter_kind="BOOT",
        work_unit_ref={"kind": "boot_session", "id": "WORK-UNIT-ADAPTER-BOOT-1"},
        estimated_duration_lower_minutes=0,
        estimated_duration_upper_minutes=1,
        estimate_confidence="HIGH",
        major_steps=["boot"],
        next_progress_update_due_minutes=10,
        variability_factors="none",
        opened_at="2026-09-14T08:00:00Z",
        completed_at="2026-09-14T08:00:05Z",
        perform=_perform,
    )
    assert terminal_record["terminal_outcome"] == "COMPLETED"
    assert boot_context.project_id == project_id
    resolved_terminal = store.resolve_record(
        project_id,
        "work_time_coordination_terminal",
        terminal_record["work_time_coordination_terminal_id"],
    )
    assert resolved_terminal == terminal_record
    assert (
        store.resolve_record(
            project_id, "work_time_coordination_open", open_record["work_time_coordination_open_id"]
        )
        == open_record
    )


def test_a_failing_real_call_produces_a_failed_terminal_notice_and_the_original_exception_still_propagates(
    tmp_path: Path,
) -> None:
    store, world = bound(tmp_path)
    project_id = world["project_id"]
    project_binding_id = world["project_binding_id"]

    def _perform_and_fail() -> object:
        # A real, unmodified production call with a deliberately wrong project_binding_id --
        # boot_project itself refuses this; no work_time_transparency code fabricates the failure.
        return boot_project(store, project_id=project_id, project_binding_id="WRONG-BINDING-ID")

    with pytest.raises(Exception) as excinfo:
        with_work_time_coordination(
            store,
            project_id=project_id,
            project_binding_id=project_binding_id,
            adapter_kind="BOOT",
            work_unit_ref={"kind": "boot_session", "id": "WORK-UNIT-ADAPTER-BOOT-FAIL-1"},
            estimated_duration_lower_minutes=0,
            estimated_duration_upper_minutes=1,
            estimate_confidence="HIGH",
            major_steps=["boot"],
            next_progress_update_due_minutes=10,
            variability_factors="none",
            opened_at="2026-09-14T08:10:00Z",
            completed_at="2026-09-14T08:10:05Z",
            perform=_perform_and_fail,
        )
    original_exception_type = excinfo.type

    open_id = work_time_coordination_open_id(
        project_id, {"kind": "boot_session", "id": "WORK-UNIT-ADAPTER-BOOT-FAIL-1"}
    )
    terminal = store.resolve_record(
        project_id, "work_time_coordination_terminal", work_time_coordination_terminal_id(open_id)
    )
    assert terminal is not None
    assert terminal["terminal_outcome"] == "FAILED_TERMINAL"
    assert original_exception_type.__name__ in terminal["explanation"]


@pytest.mark.parametrize("adapter_kind", ADAPTER_KINDS)
def test_every_declared_adapter_kind_composes_uniformly_through_the_shared_primitive(
    tmp_path: Path, adapter_kind: str
) -> None:
    """Uniform semantics across every closed adapter kind -- Issue #22's own Kernel Placement
    requirement ("Adapter-specific UI may format the notice differently but must preserve the
    same fields and timing rules")."""

    store, world = bound(tmp_path)
    project_id = world["project_id"]
    project_binding_id = world["project_binding_id"]
    calls: list[str] = []

    def _perform() -> str:
        calls.append(adapter_kind)
        return f"{adapter_kind}-result"

    open_record, terminal_record, result = with_work_time_coordination(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        adapter_kind=adapter_kind,
        work_unit_ref={
            "kind": "cli_invocation",
            "id": f"WORK-UNIT-UNIFORM-{adapter_kind.replace('_', '-')}",
        },
        estimated_duration_lower_minutes=1,
        estimated_duration_upper_minutes=2,
        estimate_confidence="HIGH",
        major_steps=["run"],
        next_progress_update_due_minutes=10,
        variability_factors="none",
        opened_at="2026-09-14T09:00:00Z",
        completed_at="2026-09-14T09:00:01Z",
        perform=_perform,
    )
    assert result == f"{adapter_kind}-result"
    assert calls == [adapter_kind]
    assert open_record["adapter_kind"] == adapter_kind
    assert terminal_record["terminal_outcome"] == "COMPLETED"
