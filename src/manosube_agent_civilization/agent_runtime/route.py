"""The one public Temporary Agent start route (Phase 12, Issue #49).

``AGENT_RUNTIME_OWNER_COUNT=1``, ``PUBLIC_AGENT_START_ENTRY_POINT_COUNT=1``.

``start_temporary_agent`` restores an already-bound Project's Boot Context through the
existing Phase 10 Boot owner (:func:`~manosube_agent_civilization.boot.boot_project`), exactly
once, and wraps it in one ephemeral, non-persisted :class:`~manosube_agent_civilization.
agent_runtime.agent.TemporaryAgent` handle. This route creates no second Boot, Store, Binding,
Objective, Authority, or reference-resolution owner: it never calls ``FileStateStore.
initialize``, ``.commit``, ``.recover``, or ``.load_current``, never calls ``bind_project``,
and never calls ``FileStateStore.reconstruct`` directly -- current State restoration remains
entirely Boot's own concern, reached only through ``boot_project``.

Every Boot/Binding/Store/Authority failure -- missing Project/Binding, a tampered persisted
record, a malformed or divergent current view, a pending transaction, a deleted or
substituted recovery journal -- propagates its own typed error unchanged; this route neither
catches nor reclassifies it (frozen semantic decision 7), and produces no ``TemporaryAgent``
and no Store mutation on any such rejection.

This is the only module that ever imports :class:`~manosube_agent_civilization.agent_runtime.
agent._ActiveTemporaryAgent` (Structural Review Round 2, P12-R2-F1): the public
``TemporaryAgent`` interface itself cannot be instantiated directly (it is an ``abc.ABC`` with
no concrete implementation), so this route -- immediately after its own single
``boot_project`` call -- is the only place in this package that ever produces an active Agent.

**Structural Review Round 2 (P84-R2-F1/F4, ``ADOPT_P84_PROJECT_STATE_ORTHOGONAL_COORDINATION_
REBIND``).** The whole body is composed inside :func:`~manosube_agent_civilization.
work_time_transparency.adapters.with_work_time_coordination`, through the Store's own
orthogonal coordination ledger -- never through ``commit_state_transition``, so this route
still cannot mutate or authorize canonical Project State. There is no adapter call to report
progress against (``boot_project`` alone is fast and local), so no in-flight
:class:`~manosube_agent_civilization.work_time_transparency.adapters.ProgressReporter.report`
call is made here -- the open/terminal wrap alone satisfies the mandatory composition
requirement.
"""

from __future__ import annotations

from collections.abc import Callable
import hashlib
from typing import Any

from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.work_time_transparency.adapters import (
    ProgressReporter,
    with_work_time_coordination,
)
from manosube_agent_civilization.work_time_transparency.clock import default_clock

from .agent import TemporaryAgent, _ActiveTemporaryAgent


def _start_temporary_agent_body(
    store: Any, *, project_id: str, project_binding_id: str, reporter: ProgressReporter
) -> TemporaryAgent:
    boot_context = boot_project(store, project_id=project_id, project_binding_id=project_binding_id)
    return _ActiveTemporaryAgent(boot_context)


def start_temporary_agent(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    estimated_duration_lower_minutes: int = 0,
    estimated_duration_upper_minutes: int = 2,
    estimate_confidence: str = "HIGH",
    major_steps: list[str] | None = None,
    next_progress_update_due_minutes: int = 5,
    variability_factors: str = "none",
    work_time_coordination_clock: Callable[[], str] = default_clock,
) -> TemporaryAgent:
    """Start one active Temporary Agent over *store*'s already-bound Project.

    See ``07_AGENT_RUNTIME/AGENT_RUNTIME_CONTRACT.md`` §5 for the full canonical route this
    function implements.

    Structural Review Round 2 (P84-R2-F1/F4): this whole call is composed inside
    :func:`~manosube_agent_civilization.work_time_transparency.adapters.
    with_work_time_coordination` -- every normal invocation, a refusal included, durably commits
    a Work Coordination timing record chain, never a Project State mutation. ``work_unit_ref``
    is content-addressed from *project_id*, *project_binding_id*, and one real clock reading
    taken before the coordination opens. The new ``estimated_duration_*``/
    ``estimate_confidence``/``major_steps``/``next_progress_update_due_minutes``/
    ``variability_factors``/``work_time_coordination_clock`` parameters are all optional, each
    defaulting to this route's own canonical estimate, so every existing caller's own call
    syntax remains valid unchanged.
    """

    def _perform(reporter: ProgressReporter) -> TemporaryAgent:
        return _start_temporary_agent_body(
            store,
            project_id=project_id,
            project_binding_id=project_binding_id,
            reporter=reporter,
        )

    _attempt_marker = work_time_coordination_clock()
    _work_unit_id = (
        "AGENT-"
        + hashlib.sha256(f"{project_id}|{project_binding_id}|{_attempt_marker}".encode())
        .hexdigest()
        .upper()
    )

    _open_record, _terminal_record, result = with_work_time_coordination(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        adapter_kind="TEMPORARY_AGENT",
        work_unit_ref={"kind": "temporary_agent_session", "id": _work_unit_id},
        estimated_duration_lower_minutes=estimated_duration_lower_minutes,
        estimated_duration_upper_minutes=estimated_duration_upper_minutes,
        estimate_confidence=estimate_confidence,
        major_steps=major_steps or ["start_temporary_agent"],
        next_progress_update_due_minutes=next_progress_update_due_minutes,
        variability_factors=variability_factors,
        perform=_perform,
        clock=work_time_coordination_clock,
    )
    return result
