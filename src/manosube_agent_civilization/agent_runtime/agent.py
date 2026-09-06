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
"""

from __future__ import annotations

from manosube_agent_civilization.boot import BootContext

from .errors import AgentReleasedError


class TemporaryAgent:
    """One ephemeral lifecycle over an already-verified, immutable ``BootContext``."""

    __slots__ = ("_boot_context", "_released")

    def __init__(self, boot_context: BootContext) -> None:
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
