"""Fail-closed Runtime errors (Phase 15, Issue #64).

Named ``RuntimeObservationError`` rather than ``RuntimeError`` throughout this package's own
error hierarchy -- deliberately never shadowing Python's own built-in ``RuntimeError``, which
every other owner's own error base already avoids doing for its own domain name (compare
``ProjectionError``, not ``ProjectionRuntimeError``, in :mod:`manosube_agent_civilization.
projection.errors`).
"""

from __future__ import annotations


class RuntimeObservationError(RuntimeError):
    """Base error: a Runtime Observation could not be produced, resolved, or routed."""


class RuntimeRequirementError(RuntimeObservationError):
    """A caller-supplied input to this package's own public route is malformed, missing, or
    outside its own closed shape -- refused before any adapter call."""


class RuntimeEnvelopeIntegrityError(RuntimeObservationError):
    """A resolved Runtime Observation Envelope's own recomputed semantic fingerprint does not
    equal its own declared value -- refuses to trust any of its fields (the identical
    domain-owned tamper check :class:`~manosube_agent_civilization.projection.errors.
    ProjectionEnvelopeIntegrityError` already performs for a Projection Envelope)."""


class RuntimeAdapterError(RuntimeObservationError):
    """A :class:`~manosube_agent_civilization.runtime.types.RuntimeAdapter` returned a
    malformed or unreadable outcome -- never itself a transport-level ``MALFORMED``
    observation outcome, which is a legitimate typed result, not a raised error."""


class RuntimeAuthorityFreshnessError(RuntimeObservationError):
    """The authority-defining context (Project Binding identity / Human Authority reference /
    Human Authority signing key) observed at this call's own initial Boot is no longer the one
    the Store reports -- refused at the adapter boundary, or at the commit boundary, rather
    than reaching a target with stale context or committing an Envelope carrying now-stale
    authority (Phase 15 Structural Review Round 1, P15-R1-F5).

    Deliberately its own class, sibling to :class:`RuntimeRequirementError` and
    :class:`RuntimeEnvelopeIntegrityError` rather than a subclass of either: a caller's input
    was not malformed (so it is not a requirement failure), and the derived Envelope's own
    content is entirely self-consistent (so it is not an integrity failure) -- what changed is
    the *world underneath an already-valid request*, which a caller may legitimately retry
    against the new authority and which neither existing class names honestly.
    """
