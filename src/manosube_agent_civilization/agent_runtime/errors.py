"""Fail-closed Temporary Agent lifecycle errors (Phase 12, Issue #49).

This layer owns a typed error only for its own lifecycle boundary -- active versus released.
Every Boot/Binding/Store/Authority failure (missing Project/Binding, corrupted records or
current view, a pending transaction, a deleted or substituted recovery journal, and so on)
propagates its owning domain's own typed error unchanged; this module never catches or
reclassifies one (frozen semantic decision 7).
"""

from __future__ import annotations


class AgentRuntimeError(RuntimeError):
    """Base error: a Temporary Agent lifecycle operation could not proceed."""


class AgentReleasedError(AgentRuntimeError):
    """The Temporary Agent handle has already been released.

    Its Boot Context and lifecycle service are no longer accessible through this handle, and
    a released Agent cannot be restarted, resumed, used to restore, or used to recover a
    Store (frozen semantic decision 6)."""
