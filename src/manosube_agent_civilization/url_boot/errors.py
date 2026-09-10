"""The closed error vocabulary for URL Boot (Phase 17, Issue #69).

Mirrors :mod:`manosube_agent_civilization.runtime.errors`'s own discipline exactly: a base
class named after this package's own domain (never shadowing a builtin), one refusal class for
malformed/missing caller input refused before any adapter is reached, one integrity class for a
Store-resolved record whose own recomputed identity disagrees with its declared value, one
adapter-defect class distinct from any legitimate typed fetch outcome, and one freshness class
for an authority-defining context that changed underneath an already-open request.
"""

from __future__ import annotations


class UrlBootError(RuntimeError):
    """Base class for every error this package raises."""


class UrlBootRequirementError(UrlBootError):
    """Caller input (source identity, Boundary, request shape) was malformed, missing, or
    refused by the closed fetch Boundary -- raised before any adapter is ever reached."""


class UrlBootEnvelopeIntegrityError(UrlBootError):
    """A Store-resolved ``url_source_observation_envelope`` record's own recomputed identity or
    semantic fingerprint does not equal its own declared value -- refusing to trust any of its
    fields."""


class UrlBootAdapterError(UrlBootError):
    """A URL Source Adapter returned a structurally unreadable, out-of-vocabulary, or otherwise
    defective report -- distinct from any legitimate typed :data:`~manosube_agent_civilization.
    url_boot.types.URL_FETCH_OUTCOMES` member, which is an honest transport fact, not a defect."""


class UrlBootAuthorityFreshnessError(UrlBootError):
    """The Project Binding / Human Authority / signing key this call runs under no longer
    equals the one the caller's live Boot context was established under -- a stale authority
    context is refused, with zero adapter calls, before an adapter is ever reached."""
