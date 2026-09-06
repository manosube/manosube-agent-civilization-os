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
"""

from __future__ import annotations

from typing import Any

from manosube_agent_civilization.boot import boot_project

from .agent import TemporaryAgent, _ActiveTemporaryAgent


def start_temporary_agent(
    store: Any, *, project_id: str, project_binding_id: str
) -> TemporaryAgent:
    """Start one active Temporary Agent over *store*'s already-bound Project.

    See ``07_AGENT_RUNTIME/AGENT_RUNTIME_CONTRACT.md`` §5 for the full canonical route this
    function implements.
    """

    boot_context = boot_project(store, project_id=project_id, project_binding_id=project_binding_id)
    return _ActiveTemporaryAgent(boot_context)
