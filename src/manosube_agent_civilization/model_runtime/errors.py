"""Fail-closed Model Runtime errors (Phase 16, Issue #66).

Named ``ModelRuntimeError`` rather than shadowing any built-in, the identical convention every
other owner's own error base already keeps for its own domain name (compare
``RuntimeObservationError`` in :mod:`manosube_agent_civilization.runtime.errors`, deliberately
not ``RuntimeError``).

Each class below names a *different* failure, and none of them is ever converted into another
-- P16-C6's own requirement, applied to this package's raised vocabulary exactly as
:data:`~manosube_agent_civilization.model_runtime.types.MODEL_EXECUTION_OUTCOMES` applies it to
this package's returned one.
"""

from __future__ import annotations


class ModelRuntimeError(RuntimeError):
    """Base error: a model execution could not be opened, executed, resumed, or routed."""


class ModelRuntimeRequirementError(ModelRuntimeError):
    """A caller-supplied input, or a Store-resolved record, is malformed, missing, unresolvable,
    cross-project, or outside this package's own closed shape -- refused before any adapter call
    and with zero commits."""


class ModelRecordIntegrityError(ModelRuntimeError):
    """A resolved canonical record's own recomputed identity or semantic fingerprint does not
    equal its own declared value -- refuses to trust any of its fields (the identical
    domain-owned tamper check :class:`~manosube_agent_civilization.runtime.errors.
    RuntimeEnvelopeIntegrityError` already performs for a Runtime Observation Envelope)."""


class ModelAdapterError(ModelRuntimeError):
    """A :class:`~manosube_agent_civilization.model_runtime.types.ModelAdapter` returned a
    structurally unreadable result, claimed an outcome only this package's own route may
    compute, or reported a candidate field the Model Execution Boundary never permitted.

    Deliberately **never** the same thing as a ``MALFORMED`` execution outcome: a model that
    honestly reports it produced malformed output is a legitimate typed result (P16-C6), while
    an *adapter* whose own return value cannot be read at all, or which tries to widen its own
    Boundary or authorize itself, is a defect that must surface loudly rather than be persisted
    as any outcome at all.
    """


class ModelRuntimeStaleStateError(ModelRuntimeError):
    """The Canonical State this call's own Phase 12 Temporary Agent Execution Contract was
    established against is no longer the State this Store reports (P16-C5).

    Deliberately its own class, sibling to :class:`ModelRuntimeRequirementError` and
    :class:`ModelRecordIntegrityError` rather than a subclass of either -- the identical
    reasoning :class:`~manosube_agent_civilization.runtime.errors.
    RuntimeAuthorityFreshnessError` records for its own sibling class: a caller's input was not
    malformed (so it is not a requirement failure), and every resolved record is entirely
    self-consistent (so it is not an integrity failure). What changed is the *world underneath
    an already-valid request*, which a caller may legitimately retry against a freshly started
    Temporary Agent.
    """


class ModelRuntimeAuthorityFreshnessError(ModelRuntimeError):
    """The Human Authority this Work Unit's own Authority Decision was made under is no longer
    the one this Store's current Project Binding names -- refused at the adapter boundary, or at
    the commit boundary, rather than reaching a model with stale Authority or committing an
    Envelope carrying now-stale Authority (P16-C5)."""


class ModelReleasedAgentError(ModelRuntimeError):
    """The Phase 12 Temporary Agent supplied to this route is not a live one.

    A released Agent is not an execution contract: Phase 12's own frozen semantic decision 6
    states that a released handle cannot be restarted or resumed, so a route that accepted one
    would be executing under a contract that has already ended. Raised only after
    :class:`~manosube_agent_civilization.agent_runtime.errors.AgentReleasedError` has already
    been observed from the Agent's own handle -- Phase 12's error is never swallowed, it is
    chained.
    """
