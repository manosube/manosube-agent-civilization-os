"""Fail-closed Multi-Agent Dynamic Execution errors (Phase 19, Issue #77).

One base error named after this package (mirroring ``ModelRuntimeError``/
``RuntimeObservationError``, deliberately not ``RuntimeError`` itself), plus narrow subclasses
per distinct refusal reason this package's own :mod:`~manosube_agent_civilization.multi_agent.
route` and :mod:`~manosube_agent_civilization.multi_agent.selection` raise. Every class below
names a *different* failure, and none of them is ever converted into another -- the identical
discipline :mod:`~manosube_agent_civilization.model_runtime.errors` already keeps for its own
raised vocabulary.
"""

from __future__ import annotations


class MultiAgentError(RuntimeError):
    """Base error: a dynamic execution plan could not be opened, executed, aggregated, or
    routed to Evidence."""


class MultiAgentRequirementError(MultiAgentError):
    """A caller-supplied input, or a Store-resolved record, is malformed, missing,
    unresolvable, cross-project, or outside this package's own closed shape -- refused before
    any Agent is constructed and with zero commits."""


class MultiAgentRecordIntegrityError(MultiAgentError):
    """A resolved canonical record's own recomputed identity or semantic fingerprint does not
    equal its own declared value -- refuses to trust any of its fields (the identical
    domain-owned tamper check :class:`~manosube_agent_civilization.model_runtime.errors.
    ModelRecordIntegrityError` already performs for its own records)."""


class MultiAgentSelectionError(MultiAgentError):
    """P19-C1's own refusal base: the canonical Difference and its required capabilities did
    not admit a bounded, total slot selection. Never raised for a caller-preferred count --
    caller preference has no parameter through which it could reach
    :func:`~manosube_agent_civilization.multi_agent.selection.select_agent_slots` at all."""


class MultiAgentUnsupportedRequirementError(MultiAgentSelectionError):
    """The resolved Difference's own ``risk_class``, or the system-wide capability vocabulary
    this delivery selects from, is unknown, unsupported, or ambiguous -- refused before any
    slot is ever computed."""


class MultiAgentOverLimitError(MultiAgentSelectionError):
    """The selection would exceed :data:`~manosube_agent_civilization.multi_agent.selection.
    MAX_AGENT_SLOTS`, this delivery's own closed maximum concurrency/count. Unreachable through
    the shipped :data:`~manosube_agent_civilization.multi_agent.selection.
    RISK_CLASS_TO_SLOT_COUNT` mapping alone (every mapped value is within the bound by
    construction) -- retained as a decisive, always-checked defensive gate rather than an
    unenforced assumption, exactly the discipline this delivery's own contract requires."""


class MultiAgentStaleStateError(MultiAgentError):
    """The Canonical State this call's own Phase 12 Temporary Agent Execution Contract was
    established against is no longer the State this Store reports (the identical sibling
    :class:`~manosube_agent_civilization.model_runtime.errors.ModelRuntimeStaleStateError`
    already is to :class:`MultiAgentRequirementError`/:class:`MultiAgentRecordIntegrityError`:
    a caller's input was not malformed and every resolved record is self-consistent -- what
    changed is the world underneath an already-valid request)."""


class MultiAgentAuthorityFreshnessError(MultiAgentError):
    """The Human Authority this plan's own reproduced Authority Decision was made under is no
    longer the one this Store's current Project Binding names."""


class MultiAgentReleasedAgentError(MultiAgentError):
    """The Temporary Agent supplied to this route -- either the caller's own coordinator-liveness
    proof, or one this package constructed for a single slot -- is not a live one."""


class MultiAgentReleaseIncompleteError(MultiAgentError):
    """One or more constructed temporary Agents for this plan do not carry a release receipt
    whose own ``release_status`` is ``RELEASED`` (P19-C8). The Evidence-aggregation input is
    refused/unconstructable while this holds -- there is no way to reach a clean terminal
    orchestration receipt with a leaked or failed-release Agent outstanding."""


class MultiAgentReplayConflictError(MultiAgentError):
    """A plan, slot, or attempt identity was reused with genuinely different content -- a
    Store-detected content collision (:class:`~manosube_agent_civilization.store.errors.
    RecordConflictError`) at what this package's own narrow, natural-key identity scheme
    intends to be a single-writer slot. Never silently retried and never resolved by picking
    either side."""


class MultiAgentPlanSelectionMismatchError(MultiAgentError):
    """Structural Review Round 3, P19-R3-F2: the resolved plan's own declared slot selection
    (``slots``/``capability_selection_fingerprint``) does not equal what
    :func:`~manosube_agent_civilization.multi_agent.selection.select_agent_slots` independently
    recomputes today from the plan's own ``difference_ref`` -- refused before any slot's own
    Agent is constructed, any adapter is reached, or any new Store mutation is made.

    A plan's own content-addressed identity and semantic-fingerprint checks alone only prove
    internal self-consistency -- that its own declared fields agree with each other -- never
    that those declared fields were honestly *derived* from the named Difference in the first
    place. A plan committed by some route other than :func:`~manosube_agent_civilization.
    multi_agent.route.open_dynamic_execution_plan` (which always calls ``select_agent_slots``
    itself) could declare a self-consistent but forged selection -- for example, silently
    narrowing a ``HIGH`` risk Difference's own required two slots down to one -- and this check
    is what refuses it at the one place every execution attempt must pass through.
    """


class MultiAgentPlanExpiredError(MultiAgentError):
    """Structural Review Round 1, P19-R1-F5: this call's own *executed_at* is at or past the
    plan's own recorded ``expires_at`` or ``execution_bounds.deadline_at`` -- refused before any
    slot's own Agent is constructed, any adapter is reached, or any new Store mutation is made
    for this call. The identical fail-closed discipline :class:`~manosube_agent_civilization.
    reflow.errors.StaleReflowError` already applies to a Closure Evaluation's own
    ``evaluation_expires_at`` (G18): a validity window recorded on an immutable record is
    honoured, never merely stored and never read."""
