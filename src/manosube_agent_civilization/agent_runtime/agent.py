"""The one non-persisted, non-authoritative Temporary Agent lifecycle (Phase 12, Issue #49).

``TemporaryAgent`` is an ephemeral, in-process holder of one already-verified ``BootContext``
-- never a second Boot, Store, Binding, Objective, Authority, Evidence, Change, or State
owner. It exists only in process memory: it creates no canonical record, schema, directory,
journal, manifest, cache, resume token, durable agent id, or long-term memory (frozen
semantic decision 4). Its own Python identity (``id(self)``) is not a persisted or canonical
identity -- nothing here mints or exposes one.

A live Agent exposes only the already deep-frozen ``BootContext`` :func:`~manosube_agent_
civilization.boot.boot_project` returned; it grants no Authority and cannot evaluate
Authority, create or execute a Change, observe an external system, or close a Difference
(frozen semantic decision 5). Release is local, idempotent, and zero-write; once released,
access to the Boot Context through this handle fails with :class:`AgentReleasedError`, and the
handle cannot be restarted or resumed (frozen semantic decision 6).

Structural Review Round 1 correction (P12-R1-F1): ``TemporaryAgent`` is necessarily a public
lifecycle type, but its constructor must not accept an arbitrary caller-supplied
``BootContext`` -- ``BootContext`` is itself publicly constructible, so a bare
``TemporaryAgent(fake_context)`` would otherwise let a caller fabricate an active Agent
without ever calling :func:`~manosube_agent_civilization.agent_runtime.route.
start_temporary_agent` or ``boot_project`` at all. ``__init__`` now requires the private
``_ROUTE_CONSTRUCTION_TOKEN`` singleton this module owns and never exports -- only ``route.py``
imports it -- and requires *boot_context* to already be a real ``BootContext`` instance; any
other caller, and any non-``BootContext`` payload, is refused with
:class:`AgentConstructionError` before anything is stored.
"""

from __future__ import annotations

from manosube_agent_civilization.boot import BootContext

from .errors import AgentConstructionError, AgentReleasedError


class _ConstructionToken:
    """A private marker type: the one singleton instance below, ``_ROUTE_CONSTRUCTION_TOKEN``,
    is never exported from this package, and only :mod:`~manosube_agent_civilization.
    agent_runtime.route` -- the one canonical ``start_temporary_agent`` route -- imports it.
    ``TemporaryAgent.__init__`` accepts nothing else as proof of canonical construction."""

    __slots__ = ()


_ROUTE_CONSTRUCTION_TOKEN = _ConstructionToken()


class TemporaryAgent:
    """One ephemeral lifecycle over an already-verified, immutable ``BootContext``.

    Constructible only by :func:`~manosube_agent_civilization.agent_runtime.route.
    start_temporary_agent` (Structural Review Round 1, P12-R1-F1) -- never directly, and never
    over a caller-supplied object that is not already a real ``BootContext``.
    """

    __slots__ = ("_boot_context", "_released")

    def __init__(self, boot_context: BootContext, *, _construction_token: object = None) -> None:
        if _construction_token is not _ROUTE_CONSTRUCTION_TOKEN:
            raise AgentConstructionError(
                "TemporaryAgent cannot be constructed directly -- use "
                "start_temporary_agent(store, project_id=..., project_binding_id=...), the "
                "one canonical route that verifies a Boot Context through boot_project(...) "
                "before any Agent is ever created"
            )
        if not isinstance(boot_context, BootContext):
            raise AgentConstructionError(
                f"TemporaryAgent requires an already-verified BootContext, not "
                f"{type(boot_context).__name__!r}"
            )
        self._boot_context = boot_context
        self._released = False

    @property
    def boot_context(self) -> BootContext:
        """The verified Boot Context this Agent holds, while active.

        Raises :class:`AgentReleasedError` once this Agent has been released."""

        if self._released:
            raise AgentReleasedError("this Temporary Agent has already been released")
        return self._boot_context

    def release(self) -> None:
        """Release this Agent's lifetime.

        Idempotent, local, and zero-write: calling this more than once, or on an Agent that
        never did anything else, has the identical effect and touches no Store."""

        self._released = True
