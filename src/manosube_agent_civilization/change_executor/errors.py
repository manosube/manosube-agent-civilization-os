"""The closed error vocabulary for Change Executor (Phase 18, Issue #73).

Mirrors :mod:`manosube_agent_civilization.url_boot.errors`'s own discipline exactly: a base
class named after this package's own domain (never shadowing a builtin), and one narrow
subclass per distinct refusal reason this package's own route can ever raise. Every exception
that leaves :mod:`~manosube_agent_civilization.change_executor.route` is one of these -- a raw
``KeyError``/``TypeError`` from a malformed input is caught at the boundary and re-raised as the
appropriate one of these instead (see that module's own docstring).
"""

from __future__ import annotations


class ChangeExecutorError(RuntimeError):
    """Base class for every error this package raises."""


class ExecutionBoundaryError(ChangeExecutorError):
    """The supplied Execution Boundary, or the adapter identity accompanying it, is malformed,
    unsafe, or not genuinely closed plain data -- refused at composition time, before any
    request-facing operation can even be obtained."""


class ExecutionAuthorityProvenanceError(ChangeExecutorError):
    """The resolved Change, or the Authority Decision it names, does not match its own
    recomputed identity or semantic fingerprint; the reproduced decision is not ``AUTONOMOUS``;
    the Change's own ``action.action_kind`` is not a member of the bound Boundary's
    ``permitted_action_kinds``, or is itself one of :data:`~manosube_agent_civilization.
    authority.levels.HUMAN_ONLY_ACTION_KINDS`; or the Change's own ``scope`` is not entirely
    admitted by the bound Boundary -- refused before any Store commit and before any adapter is
    ever reached."""


class StaleExecutionInputError(ChangeExecutorError):
    """The Change's own ``before_state_fingerprint``/``expected_state_revision`` no longer
    equals the freshly Booted current State -- refused before any Store commit and before any
    adapter is ever reached."""


class ExecutionKillSwitchError(ChangeExecutorError):
    """The human kill switch for this project is missing, unresolvable, tampered, or not
    ``ACTIVE`` -- refused closed, with zero adapter calls, at whichever of the two checkpoints
    this call reached (before any Store commit, or immediately before the one adapter call)."""


class ExecutionConcurrentClaimError(ChangeExecutorError):
    """A different, genuinely concurrent execution attempt already holds -- or is racing for --
    this exact mapping slot (the same Change, Boundary, and adapter identity) under a different
    ``claim_token``. Never silently retried into an attempt or an adapter call."""


class ExecutionReconciliationRequiredError(ChangeExecutorError):
    """A committed ``execution_attempt`` already exists for this mapping slot and no terminal
    ``execution_receipt`` exists yet -- the true outcome of a prior attempt (which may already
    have called the adapter) is genuinely unknown. Refused rather than risk a duplicate real
    mutation; never guessed, never silently retried."""


class ExecutionTerminalClaimMismatchError(ChangeExecutorError):
    """A terminal ``execution_receipt`` already exists for this mapping slot, under a different
    ``claim_token`` than the one this caller supplied, and the caller did not explicitly pass
    ``permit_semantic_reuse=True``."""


class ExecutionReceiptIntegrityError(ChangeExecutorError):
    """A Store-resolved ``execution_intent``, ``execution_attempt``, ``execution_receipt``, or
    ``change_executor_kill_switch`` record's own recomputed identity or semantic fingerprint
    does not equal its own declared value -- refusing to trust any of its fields."""


class ExecutionAdapterError(ChangeExecutorError):
    """The bound :class:`~manosube_agent_civilization.change_executor.types.
    ChangeExecutorAdapter` itself refused, or returned a report that cannot be trusted as a
    result -- structurally unreadable, or naming a file outside the exact operation this route
    admitted -- distinct from any legitimate typed :data:`~manosube_agent_civilization.
    change_executor.types.EXECUTION_OUTCOMES` member, which is an honest, bounded fact, not a
    defect."""
