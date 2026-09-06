"""Fail-closed Boot errors (Phase 10, Issue #45).

Boot reuses every existing domain's own typed errors for the checks that domain already
owns: :class:`~manosube_agent_civilization.binding.errors.BindingIdentityError` and
:class:`~manosube_agent_civilization.binding.errors.BindingValidationError` for Product
Binding identity/shape, and the Store's own
:class:`~manosube_agent_civilization.store.errors.CorruptStoreError`/
:class:`~manosube_agent_civilization.store.errors.StateNotFoundError`/
:class:`~manosube_agent_civilization.store.errors.BoundaryError` for Store-owned corruption,
uninitialized-project, and boundary violations -- ``boot_project`` never catches or rewraps
any of these; they propagate unchanged. The two errors below exist only for the cross-record
consistency checks Issue #45 assigns to Boot itself, which no other module already owns.
"""

from __future__ import annotations


class BootError(RuntimeError):
    """Base error: a Boot attempt could not restore a consistent, verified Boot Context."""


class BootNotFoundError(BootError):
    """A required Store-owned canonical reference (the requested Project Binding, or the
    Objective Revision/Authority Rule it names) does not resolve, or a caller-supplied
    identity is not a plain canonical identity string."""


class BootConsistencyError(BootError):
    """A cross-record invariant Issue #45 requires this route itself to check -- project,
    Objective, Authority, reference, or revision consistency across the accepted graph --
    does not hold."""
