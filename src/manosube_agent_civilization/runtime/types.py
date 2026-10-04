"""Closed Runtime vocabularies and the Runtime Adapter Protocol (Phase 15, Issue #64).

Mirrors :mod:`manosube_agent_civilization.projection.types`'s own discipline exactly: closed
``frozenset`` vocabularies, a minimal ``Protocol`` a replaceable adapter must satisfy (a
declared ``adapter_identity`` attribute, checked before the adapter is ever called, plus one
bounded ``observe`` method), and one deep-frozen receipt dataclass carrying nothing an adapter
itself supplied unchecked.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Protocol

from .errors import RuntimeRequirementError

#: The observation methods this package implements end to end: a single bounded HTTP GET
#: against an explicit, closed endpoint, and a single bounded SSH command execution against an
#: explicit, closed probe identity (Issue #105, transport-independent runtime observation --
#: GitHub Actions and manual/unattended SSH are interchangeable *transports* for the same
#: canonical observation; this frozenset is the closed set of *methods* a :class:`RuntimeAdapter`
#: may be asked to perform, never a transport name itself). Extensible later (a further closed
#: literal, never an open string) exactly as :data:`~manosube_agent_civilization.projection.
#: types.PROJECTION_KINDS` started at three known values and stays closed.
RUNTIME_OBSERVATION_METHODS: frozenset[str] = frozenset({"HTTP_GET_BOUNDED", "SSH_EXEC_BOUNDED"})

#: The closed set of pinned, reviewed probe identities a ``SSH_EXEC_BOUNDED`` boundary's
#: ``endpoint.probe_identity`` may name. Each identity maps, through a fixed Python-side
#: table this package owns (never a caller-supplied command or path), to one exact remote
#: command this adapter will run -- deliberately parameterless: the probe script's own fixed,
#: reviewed configuration decides which diagnostic fields or log excerpt it returns, so no
#: caller-controlled path or argument ever reaches a remote shell. A path-parameterized probe
#: is a distinct, separately-reviewed future extension, not this one (disclosed judgment call,
#: Issue #105).
SSH_PROBE_IDENTITIES: frozenset[str] = frozenset(
    {"OS_HEALTH_SNAPSHOT_BOUNDED", "SOURCE_LOG_EXCERPT_BOUNDED"}
)

#: The one remote command each :data:`SSH_PROBE_IDENTITIES` member resolves to -- the single
#: source of truth :class:`~manosube_agent_civilization.runtime.adapter.SshRuntimeAdapter`
#: (the unattended/Actions path) and :mod:`~manosube_agent_civilization.runtime.network`'s
#: ``render_ssh_command_argv`` (the manual, Human-rendered path, Issue #105 Capability A) both
#: read, so the command a Human is shown and the command this package actually runs can never
#: silently diverge. Never built from a caller-supplied string -- each value is a literal this
#: package owns.
SSH_PROBE_REMOTE_COMMANDS: Mapping[str, str] = MappingProxyType(
    {
        "OS_HEALTH_SNAPSHOT_BOUNDED": (
            "python3 runtime_observation_probe.py OS_HEALTH_SNAPSHOT_BOUNDED"
        ),
        "SOURCE_LOG_EXCERPT_BOUNDED": (
            "python3 runtime_observation_probe.py SOURCE_LOG_EXCERPT_BOUNDED"
        ),
    }
)

#: The one pinned, expected SHA-256 content digest of ``scripts/runtime_observation_probe.py``
#: (PR #108 Structural Review Round 1, F3) -- a probe *name* identifies nothing about which
#: file actually ran; :class:`~manosube_agent_civilization.runtime.adapter.SshRuntimeAdapter`
#: compares every probe report's own self-reported ``probe_script_sha256`` against this exact
#: value and refuses the observation (``MALFORMED``) on any mismatch, so a same-named but
#: different script substituted on a target can never be silently accepted as the reviewed
#: artifact. Recomputed and asserted against the real file in
#: ``tests/contract/runtime/test_runtime_static_conformance.py`` -- a future edit to the probe
#: script that does not also update this constant fails that test loudly, which is the point:
#: this pin is deliberately brittle to drift rather than silently permissive.
SSH_PROBE_SCRIPT_SHA256 = "74c42ec41440ac82f46d839cf5db903bd85e4626a6015d0ed71c73f6291d3592"

#: The complete, closed outcome vocabulary a Runtime Observation may ever settle at -- the
#: canonical classification :func:`~manosube_agent_civilization.runtime.route.
#: observe_runtime_target` computes, independently of whatever an adapter itself claims.
#: ``NEGATIVE``/``IDENTITY_MISMATCH`` are never returned by an adapter directly (see
#: :data:`RUNTIME_ADAPTER_TRANSPORT_OUTCOMES`) -- both are route-level classifications made
#: only after independently recomputing content/identity fingerprints, never trusted from the
#: adapter's own say-so.
RUNTIME_OBSERVATION_OUTCOMES: frozenset[str] = frozenset(
    {
        "OBSERVED",
        "NEGATIVE",
        "NOT_FOUND",
        "PERMISSION_DENIED",
        "TIMEOUT",
        "UNAVAILABLE",
        "MALFORMED",
        "IDENTITY_MISMATCH",
    }
)

#: What a :class:`RuntimeAdapter` may honestly report from transport alone, before this
#: package's own independent content/identity re-verification -- a strict subset of
#: :data:`RUNTIME_OBSERVATION_OUTCOMES`. An adapter that reported ``NEGATIVE`` or
#: ``IDENTITY_MISMATCH`` itself would be self-authenticating its own semantic classification,
#: exactly the "treat runtime output as self-authenticating truth" failure Issue #64's own
#: required ownership boundary forbids.
RUNTIME_ADAPTER_TRANSPORT_OUTCOMES: frozenset[str] = frozenset(
    {"OBSERVED", "NOT_FOUND", "PERMISSION_DENIED", "TIMEOUT", "UNAVAILABLE", "MALFORMED"}
)

#: The Evidence owner's own closed verification status vocabulary (Independent Verification's
#: ``VERIFICATION_STATUSES``, reused verbatim here as the Runtime receipt's own ``status``
#: field, never a second, Runtime-only status vocabulary).
RECEIPT_STATUSES: frozenset[str] = frozenset({"VERIFIED", "FAILED", "INSUFFICIENT", "UNAVAILABLE"})

#: Every :data:`RUNTIME_OBSERVATION_OUTCOMES` member maps to exactly one :data:`RECEIPT_STATUSES`
#: member -- the one shared classification :mod:`~manosube_agent_civilization.runtime.route`
#: and :mod:`~manosube_agent_civilization.runtime.evidence_handoff` both read, so the two sites
#: can only ever disagree over a genuine content mismatch, never over mapping-table drift
#: between two independently maintained copies (the identical discipline
#: :func:`~manosube_agent_civilization.projection.observable.observe_and_classify` already
#: establishes as the one shared observe-and-classify body for Projection).
RUNTIME_OUTCOME_TO_RECEIPT_STATUS: dict[str, str] = {
    "OBSERVED": "VERIFIED",
    "NEGATIVE": "FAILED",
    "NOT_FOUND": "FAILED",
    "IDENTITY_MISMATCH": "FAILED",
    "PERMISSION_DENIED": "UNAVAILABLE",
    "TIMEOUT": "UNAVAILABLE",
    "UNAVAILABLE": "UNAVAILABLE",
    "MALFORMED": "UNAVAILABLE",
}


def deep_freeze(value: Any) -> Any:
    """Recursively rebuild *value* into an immutable, alias-free equivalent -- deliberately
    duplicated rather than imported from ``boot/context.py`` or ``projection/types.py``, the
    identical decoupling requirement each of those modules' own docstrings already states for
    one another.

    Package-public (Phase 15 Structural Review Round 1, P15-R1-F3) rather than module-private:
    :mod:`~manosube_agent_civilization.runtime.route` now hands the adapter deep-frozen copies
    of the exact ``target_identity``/``boundary`` it validated, so a replaceable adapter cannot
    mutate in place what the route goes on to fingerprint, persist, and attest to. That is the
    same guarantee this function already gave :class:`RuntimeObservationReceipt`, applied at
    the one other boundary in this package where a foreign implementation touches
    already-validated structures.
    """

    if isinstance(value, Mapping):
        return MappingProxyType({key: deep_freeze(item) for key, item in value.items()})
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return tuple(deep_freeze(item) for item in value)
    return value


class RuntimeAdapter(Protocol):
    """The one replaceable transport/probe boundary a Runtime Observation ever reaches through.

    An adapter never owns canonical State, decides Authority, determines Evidence sufficiency,
    closes a Difference, mutates Store internals, infers a target through network discovery, or
    classifies its own outcome as ``NEGATIVE``/``IDENTITY_MISMATCH`` -- it reports bounded
    transport facts alone; :mod:`~manosube_agent_civilization.runtime.route` is the sole owner
    of turning those facts into a canonical, independently-verified outcome.
    """

    adapter_identity: Mapping[str, Any]

    def observe(
        self, *, target_identity: Mapping[str, Any], boundary: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        """Return one bounded transport observation.

        Must return a mapping carrying ``transport_outcome`` (one of
        :data:`RUNTIME_ADAPTER_TRANSPORT_OUTCOMES`), ``observed_fields`` (a mapping bounded to
        ``boundary["permitted_fields"]``, or ``None`` when ``transport_outcome`` is not
        ``"OBSERVED"``/``"NOT_FOUND"``), and ``observed_deployment_identity`` (whatever raw
        identity marker the target itself reports, or ``None`` when unreachable/unreadable) --
        never a pre-computed fingerprint, and never a claimed match/mismatch against the
        declared *target_identity*: both are independently recomputed by the caller, never
        trusted from the adapter's own report.
        """
        ...


@dataclass(frozen=True, slots=True)
class RuntimeObservationReceipt:
    """One immutable Runtime Observation receipt -- the ephemeral, in-memory attestation
    :func:`~manosube_agent_civilization.runtime.route.observe_runtime_target` returns to its
    own caller, never itself a Store-committed record (the durable, content-addressed fact is
    the ``runtime_observation_envelope`` record; this receipt is threaded, unchanged, into
    :func:`~manosube_agent_civilization.runtime.evidence_handoff.
    route_runtime_observation_to_evidence`, exactly as :class:`~manosube_agent_civilization.
    projection.types.GitHubObservationReceipt` is never itself committed either)."""

    status: str
    runtime_observation_envelope_id: str
    project_id: str
    target_identity: Mapping[str, Any]
    boundary: Mapping[str, Any]
    adapter_identity: Mapping[str, Any]
    human_authority_ref: Mapping[str, Any]
    input_refs: tuple[Mapping[str, Any], ...]
    observations: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.status not in RECEIPT_STATUSES:
            raise RuntimeRequirementError(
                f"status is not a recognized receipt status: {self.status!r}"
            )
        if not isinstance(self.project_id, str) or not self.project_id:
            raise RuntimeRequirementError(
                f"project_id must be a non-empty string identity: {self.project_id!r}"
            )
        object.__setattr__(self, "target_identity", deep_freeze(self.target_identity))
        object.__setattr__(self, "boundary", deep_freeze(self.boundary))
        object.__setattr__(self, "adapter_identity", deep_freeze(self.adapter_identity))
        object.__setattr__(self, "human_authority_ref", deep_freeze(self.human_authority_ref))
        object.__setattr__(self, "input_refs", deep_freeze(tuple(self.input_refs)))
        object.__setattr__(self, "observations", deep_freeze(self.observations))
