"""Immutable, non-persisted Independent Verification value types (Phase 13, Issue #51).

None of the three dataclasses below is a canonical, schema-validated, persisted record --
unlike ``01_SCHEMA/evidence/evidence.schema.json`` or ``01_SCHEMA/difference/closure_policy.
schema.json``, no JSON Schema exists (or is added) for any of them, and none is ever written
to the Store. They exist only in process memory, exactly as
:class:`~manosube_agent_civilization.boot.context.BootContext` does, and for the identical
reason: creating a persisted schema for a per-call verification handshake would itself be a
second canonical record owner this Phase's frozen semantic decisions forbid (``NEW_EVIDENCE_
OWNER=false``, ``NEW_STORE_OWNER=false``).

Every nested ``Mapping``/``Sequence`` field is deep-frozen through the identical technique
``boot/context.py`` already uses (``MappingProxyType`` over a freshly built ``dict``, a fresh
``tuple`` for every list/tuple, recursively) -- duplicated here deliberately rather than
imported, so this package creates no dependency on Boot's own private helper and remains, as
Issue #51 requires, decoupled from every existing owner it reuses only by call, never by
import of implementation detail.

Structural Review Round 1 (P13-R1-F3): unlike ``boot/context.py``'s own ``_deep_freeze``,
this module's own copy fails closed on any leaf value that is neither a ``Mapping``, a
``Sequence``, nor a JSON-compatible immutable scalar -- a ``set`` or other mutable object is
refused (:class:`~manosube_agent_civilization.independent_verification.errors.
VerificationValueError`) rather than returned unfrozen. A value this layer reports as
``frozen`` is always either recursively immutable or was never accepted at all.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Protocol

from .errors import VerificationValueError

#: The complete, closed set of JSON-compatible immutable scalar types
#: :func:`_deep_freeze` ever returns unchanged. Every other leaf value -- a ``set``, a
#: custom mutable object, anything not already handled by the ``Mapping``/``Sequence``
#: branches above it -- is refused (Structural Review Round 1, P13-R1-F3) rather than
#: silently returned as a live, still-mutable alias into whatever a ``frozen`` value type
#: claims to own.
_IMMUTABLE_SCALAR_TYPES: tuple[type, ...] = (str, bytes, int, float, bool, type(None))


def _deep_freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return tuple(_deep_freeze(item) for item in value)
    if isinstance(value, _IMMUTABLE_SCALAR_TYPES):
        return value
    raise VerificationValueError(
        "refusing to deep-freeze an unsupported mutable value -- only Mapping, Sequence, "
        f"and JSON-compatible scalars are admitted: {value!r} ({type(value).__name__})"
    )


#: The four outcomes Issue #51 fixes for a :class:`VerificationResult`. ``VERIFIED`` is only
#: a result for the stated requirement -- it is not an Authority Decision, Evidence record,
#: Closure receipt, State transition, or Merge authorization (frozen semantic decision 7).
VERIFICATION_STATUSES: frozenset[str] = frozenset(
    {"VERIFIED", "FAILED", "INSUFFICIENT", "UNAVAILABLE"}
)

#: A :class:`VerifierSelection`'s own lifecycle, the identical vocabulary
#: ``authority/approval.py`` already uses for a Human approval's ``status`` -- SHUKOU declares
#: this explicitly; it is never derived from a clock this module reads (frozen semantic
#: decision 9: no hidden environment input, and no evaluation-instant parameter exists on
#: this Phase's public route for a clock comparison to use even if one were read).
SELECTION_STATUSES: frozenset[str] = frozenset({"ACTIVE", "REVOKED", "EXPIRED"})

#: The closed set of kinds a :class:`VerificationRequirement`'s own ``target_refs`` may name
#: -- exactly what Issue #51's target line fixes ("target Difference / Change / Evidence
#: references"), no wider. ``observation_evidence`` is the Evidence layer's own reference tag
#: (``evidence/engine.py``'s ``EVIDENCE_REFERENCE_KIND``); Difference and Change are never
#: Store-resolvable record kinds in this vertical (``reflow/reference_registry.py``'s own
#: documented classification), so only an ``observation_evidence`` target is ever resolved
#: against the Store here -- a ``difference``/``change`` target is validated for shape alone.
TARGET_REF_KINDS: frozenset[str] = frozenset({"difference", "change", "observation_evidence"})


@dataclass(frozen=True, slots=True)
class VerificationRequirement:
    """One explicit requirement that independent verification -- distinct from the
    implementation lineage that produced ``target_refs`` -- must be produced before
    implementation-lineage Evidence candidates alone may be treated as sufficient (frozen
    semantic decisions 1, 2, 5). Never inferred, never a blanket rule: one requirement names
    one explicit reason this specific verification is required.

    *required_conditions* is this requirement's own explicit statement of what independence/
    sufficiency it demands (e.g. a minimum distinctness or a required verifier class) --
    read and passed through by this Phase's route, never interpreted or weighed by it: what
    each condition *means* is for the requirement's own author (SHUKOU) and the verifier
    that receives it, not for this adapter to decide."""

    requirement_id: str
    project_id: str
    target_refs: tuple[Mapping[str, Any], ...]
    verification_boundary: Mapping[str, Any]
    required_conditions: Mapping[str, Any]
    selection_authority_ref: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "target_refs", tuple(_deep_freeze(dict(ref)) for ref in self.target_refs)
        )
        object.__setattr__(
            self, "verification_boundary", _deep_freeze(dict(self.verification_boundary))
        )
        object.__setattr__(
            self, "required_conditions", _deep_freeze(dict(self.required_conditions))
        )
        object.__setattr__(
            self, "selection_authority_ref", _deep_freeze(dict(self.selection_authority_ref))
        )


@dataclass(frozen=True, slots=True)
class VerifierSelection:
    """One SHUKOU-bound authorization of exactly one verifier, over exactly one requirement,
    within exactly the boundary that requirement itself declares (frozen semantic decision
    4). No automatic selection, fallback, or "only available reviewer" rule exists anywhere
    in this package -- a :class:`VerifierSelection` is always supplied by the caller, never
    constructed or defaulted here."""

    selection_id: str
    project_id: str
    requirement_id: str
    status: str
    selection_authority_ref: Mapping[str, Any]
    verifier_identity: Mapping[str, Any]
    permitted_boundary: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "selection_authority_ref", _deep_freeze(dict(self.selection_authority_ref))
        )
        object.__setattr__(self, "verifier_identity", _deep_freeze(dict(self.verifier_identity)))
        object.__setattr__(self, "permitted_boundary", _deep_freeze(dict(self.permitted_boundary)))


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """One immutable, non-persisted verification outcome.

    ``VerificationResult != Evidence record != Authority Decision != Closure receipt !=
    State transition != Merge authorization`` (Issue #51's own canonical-flow line). Nothing
    on this type writes anywhere; carrying an admissible verification result into existing
    Evidence-sufficiency semantics remains entirely the existing Evidence owner's own,
    separate concern (frozen semantic decision 6) -- this type is not itself that path, and
    this package implements no such path."""

    status: str
    requirement_id: str
    selection_id: str
    project_id: str
    target_refs: tuple[Mapping[str, Any], ...]
    verifier_identity: Mapping[str, Any]
    selection_authority_ref: Mapping[str, Any]
    verification_boundary: Mapping[str, Any]
    input_refs: tuple[Mapping[str, Any], ...]
    observations: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "target_refs", tuple(_deep_freeze(dict(ref)) for ref in self.target_refs)
        )
        object.__setattr__(self, "verifier_identity", _deep_freeze(dict(self.verifier_identity)))
        object.__setattr__(
            self, "selection_authority_ref", _deep_freeze(dict(self.selection_authority_ref))
        )
        object.__setattr__(
            self, "verification_boundary", _deep_freeze(dict(self.verification_boundary))
        )
        object.__setattr__(
            self, "input_refs", tuple(_deep_freeze(dict(ref)) for ref in self.input_refs)
        )
        object.__setattr__(self, "observations", _deep_freeze(dict(self.observations)))


class IndependentVerifier(Protocol):
    """One provider-neutral verification capability: explicit inputs in, one immutable
    outcome payload out (frozen semantic decision 3). No product, model, provider, or bot is
    selected by this Phase -- a deterministic test runner, a schema validator, a runtime
    observer, a distinct AI, or a Human review all implement this identical protocol. A
    Human verifier uses the same structure through an explicit Human-provided result; it
    must never be disguised as an automated verifier -- concretely, nothing in this
    protocol's shape lets an implementation claim automation, since ``verifier_identity`` is
    always the caller's own explicit, SHUKOU-authorized :class:`VerifierSelection` field,
    never inferred or labeled by this module.

    Structural Review Round 1 (P13-R1-F1): ``verifier_selection.verifier_identity`` is not
    merely a result label -- the callable actually invoked must declare, on itself, the
    identical identity SHUKOU selected. A conforming implementation therefore carries its
    own ``verifier_identity`` attribute (a plain ``Mapping``, not a method); the route
    :func:`~manosube_agent_civilization.independent_verification.route.
    run_independent_verification` calls checks this attribute against the supplied
    ``VerifierSelection`` -- exact match required -- *before* ever invoking the callable, and
    refuses (never calling it) on a mismatched, absent, or unreadable declared identity.
    """

    #: The identity/capability this callable itself claims to be -- checked against the
    #: caller's own ``VerifierSelection.verifier_identity`` before this callable is ever
    #: invoked. Never a method: a real attribute the route reads without calling anything.
    verifier_identity: Mapping[str, Any]

    def __call__(
        self, *, requirement: VerificationRequirement, selection: VerifierSelection
    ) -> Mapping[str, Any]:
        """Return exactly one verification outcome payload, called exactly once per
        :func:`~manosube_agent_civilization.independent_verification.route.
        run_independent_verification` invocation.

        The returned mapping must carry ``status`` (one of :data:`VERIFICATION_STATUSES`),
        ``input_refs`` (a list of explicit ``{"kind": ..., "id": ...}`` references naming
        what this verifier actually examined -- at least one, and not merely a repetition of
        *requirement*'s own ``target_refs``, unless *status* is ``UNAVAILABLE``), and
        ``observations`` (an explicit, JSON-shaped attestation candidate payload; never
        interpreted by the route that calls this protocol)."""
        ...
