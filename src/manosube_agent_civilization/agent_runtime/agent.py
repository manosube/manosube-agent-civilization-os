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

Structural Review Round 2 correction (P12-R2-F1): Round 1's fix required a private
"construction token" argument -- but that token was just an importable module attribute, so
it proved no real provenance: a caller could import it directly, construct a public
``BootContext`` directly, and hand both to ``TemporaryAgent(...)`` without ``boot_project``
ever running. An importable value is not a construction boundary, and this module makes no
claim that it is.

``TemporaryAgent`` is now the public *interface* -- an ``abc.ABC`` declaring only
``boot_context`` and ``release`` as abstract members, with no ``__init__`` of its own and no
way to construct one directly: ``TemporaryAgent(...)`` always raises Python's own
``TypeError`` for an abstract class, regardless of what arguments are supplied. The concrete
implementation, :class:`_ActiveTemporaryAgent`, is never exported from this package; only
:func:`~manosube_agent_civilization.agent_runtime.route.start_temporary_agent` -- after its
one successful ``boot_project`` call -- ever instantiates it, and returns it typed as the
public ``TemporaryAgent`` interface.

This is a public-API and ownership boundary, not a claim that hostile code running in the
same Python process, deliberately importing this private module and subclassing or
monkeypatching around it, is somehow cryptographically sandboxed -- no mechanism in Python
achieves that, and this module does not pretend otherwise. What this boundary actually
guarantees: every ordinary caller going through this package's public, documented surface
(``TemporaryAgent`` the type, ``start_temporary_agent`` the function) cannot obtain an active
Agent except by way of a real ``boot_project`` call.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from manosube_agent_civilization.boot import BootContext

from .errors import AgentReleasedError


class TemporaryAgent(ABC):
    """The one public, read-only Temporary Agent lifecycle interface.

    Not directly instantiable: this class declares no concrete implementation, only the two
    abstract members below, so ``TemporaryAgent(...)`` always raises ``TypeError`` regardless
    of what is passed to it. The only way to obtain an instance of this interface is
    :func:`~manosube_agent_civilization.agent_runtime.route.start_temporary_agent`.
    """

    @property
    @abstractmethod
    def boot_context(self) -> BootContext:
        """The verified Boot Context this Agent holds, while active.

        Raises :class:`AgentReleasedError` once this Agent has been released."""

        raise NotImplementedError

    @abstractmethod
    def release(self) -> None:
        """Release this Agent's lifetime.

        Idempotent, local, and zero-write: calling this more than once, or on an Agent that
        never did anything else, has the identical effect and touches no Store."""

        raise NotImplementedError


class _ActiveTemporaryAgent(TemporaryAgent):
    """The one private concrete implementation of :class:`TemporaryAgent`.

    Never exported from this package. Only :func:`~manosube_agent_civilization.agent_runtime.
    route.start_temporary_agent` ever constructs one, immediately after its own single
    ``boot_project`` call -- this class itself performs no verification of *boot_context* at
    all, and trusts its caller entirely, exactly as a private implementation detail should.
    """

    __slots__ = ("_boot_context", "_released")

    def __init__(self, boot_context: BootContext) -> None:
        self._boot_context = boot_context
        self._released = False

    @property
    def boot_context(self) -> BootContext:
        if self._released:
            raise AgentReleasedError("this Temporary Agent has already been released")
        return self._boot_context

    def release(self) -> None:
        self._released = True
