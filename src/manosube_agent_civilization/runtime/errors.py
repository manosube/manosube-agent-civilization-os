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
