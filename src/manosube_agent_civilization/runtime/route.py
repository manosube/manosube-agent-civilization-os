"""The one public Runtime Observation route (Phase 15, Issue #64).

``RUNTIME_OWNER_COUNT=1``, ``PUBLIC_RUNTIME_ENTRY_POINT_COUNT=1`` (this module) ``+1``
(:mod:`~manosube_agent_civilization.runtime.evidence_handoff`'s own single hand-off route).

``observe_runtime_target`` re-verifies Project/Human Authority identity through the existing
Boot owner (:func:`~manosube_agent_civilization.boot.boot_project`), independently fingerprints
an explicit runtime target identity and a closed Observation Boundary (never trusting either
from a caller beyond their declared shape), refuses an observation whose own request instant
falls outside the Boundary's own declared time window before ever reaching an adapter, calls
the one replaceable :class:`~manosube_agent_civilization.runtime.types.RuntimeAdapter` exactly
once, and independently reclassifies whatever transport-level facts it reports into the full,
closed outcome vocabulary -- ``NEGATIVE`` and ``IDENTITY_MISMATCH`` are computed here alone,
never accepted from the adapter's own report. It then derives and commits one canonical Runtime
Observation Envelope through the existing Store's own single sanctioned committer
(:func:`~manosube_agent_civilization.store.commit.commit_state_transition` -- the identical
primitive Reflow, Binding, and Projection already share) and returns an ephemeral, in-memory
:class:`~manosube_agent_civilization.runtime.types.RuntimeObservationReceipt`.

Read-only, so no create-once-reuse-after side effect exists to protect: unlike Projection,
this route derives no intent/materialize-attempt claim pair (see
:mod:`~manosube_agent_civilization.runtime.engine`'s own module docstring) and commits exactly
one new Envelope per call -- observing the identical target under the identical Boundary twice
is two independent facts, not a duplicate external artifact.

Canonical route (``10_RUNTIME/RUNTIME_CONTRACT.md`` §5):

```text
complete schema validation of the declared target identity and closed Observation Boundary
→ network-scope check -- the endpoint's own effective host must be inside allowed_hosts
→ real-instant time-window check -- refuses before any adapter call
→ real Project/Human Authority (Boot re-verification)
→ Store-anchored deployment identity (the declared deployment_fingerprint must equal a
  genuinely committed, independently identity-recomputed runtime_deployment_declaration)
→ explicit runtime target identity, fingerprinted (never trusted from a caller)
→ closed Observation Boundary, fingerprinted (never trusted from a caller)
→ deterministic observation_request_identity (target + Boundary + issued_at)
→ authority-freshness re-check -- refuses before the adapter if the Binding/Human Authority
  changed since this call's own initial Boot
→ replaceable Runtime Adapter -- one bounded transport call, handed deep-frozen copies it
  cannot mutate
→ independent field-boundary projection (any field outside permitted_fields is a refusal,
  never silently kept) and content/identity reclassification (NEGATIVE/IDENTITY_MISMATCH
  computed here, never accepted from the adapter's own report; redaction applied before any
  fingerprint or persistence)
→ canonical Runtime Observation Envelope
→ authority-freshness re-check on every commit attempt -- refuses to commit stale authority
→ existing canonical persistence boundary (commit_state_transition)
→ bounded Runtime Observation Receipt
```

**Structural Review Round 1 (P15-R1-F1/F2/F3/F5/F6).** Five of that round's six findings land
in this module: the closed Boundary is now proved complete against its own canonical schema
before Boot or any adapter is reached (F2), its declared endpoint is proved to fall inside its
own declared ``network_scope`` here rather than only inside whichever adapter happens to run
(F1, zero-call), its time window is compared as real UTC instants rather than as strings (F2),
the adapter receives deep-frozen structures and its reported fields are independently projected
back down to ``permitted_fields`` (F3), the authority-defining context is re-proved immediately
before the adapter call and again on every commit attempt (F5), and the declared
``deployment_fingerprint`` must now match a genuinely committed, Store-resolved
``runtime_deployment_declaration`` before the observed-vs-declared comparison means anything at
all (F6).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store.commit import commit_state_transition
from manosube_agent_civilization.store.errors import RecordConflictError, StaleStateError

from .engine import (
    RUNTIME_SCHEMA_BASE,
    derive_runtime_observation_envelope,
    require_valid_boundary,
    require_valid_deployment_declaration,
    require_valid_target_identity,
    require_valid_timestamp,
)
from .errors import (
    RuntimeAdapterError,
    RuntimeAuthorityFreshnessError,
    RuntimeEnvelopeIntegrityError,
    RuntimeRequirementError,
)
from .identity import (
    runtime_deployment_declaration_id,
    runtime_deployment_declaration_semantic_fingerprint,
    runtime_observation_boundary_fingerprint,
    runtime_observation_envelope_semantic_fingerprint,
    runtime_observation_request_identity,
    runtime_observed_content_fingerprint,
    runtime_target_fingerprint,
)
from .network import require_endpoint_within_network_scope
from .types import (
    RUNTIME_ADAPTER_TRANSPORT_OUTCOMES,
    RUNTIME_OUTCOME_TO_RECEIPT_STATUS,
    RuntimeAdapter,
    RuntimeObservationReceipt,
    deep_freeze,
)

_ENVELOPE_RECORD_KIND = "runtime_observation_envelope"
_DEPLOYMENT_DECLARATION_RECORD_KIND = "runtime_deployment_declaration"
#: The identical Compare-And-Swap retry bound Projection's own ``_claim_slot`` uses -- not a
#: timeout, not a backoff, bounded protection against genuine, ordinary contention from an
#: unrelated commit landing on this project between this route's own ``load_current`` and its
#: own ``commit``.
_MAX_COMMIT_RETRIES = 8

#: Exactly the fields of ``target_identity`` a canonical, Store-committed
#: ``runtime_deployment_declaration`` must independently restate for that declaration to be
#: the anchor for *this* target rather than a valid declaration replayed against a different
#: one (P15-R1-F6's own anti-replay control).
_DECLARATION_ANCHORED_TARGET_FIELDS: tuple[str, ...] = (
    "project_binding_ref",
    "provider",
    "deployment_id",
    "instance_identity",
    "deployment_fingerprint",
)


def _require_canonical_identity(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise RuntimeRequirementError(f"{name} must be a non-empty string identity: {value!r}")
    if "/" in value or "\\" in value or value.startswith("..") or "://" in value:
        raise RuntimeRequirementError(
            f"{name} must be a canonical identity, never a path/URL/locator: {value!r}"
        )
    return value


def _require_reference(value: Any, *, context: str, kind: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeRequirementError(f"{context} must be an explicit reference object: {value!r}")
    if value.get("kind") != kind:
        raise RuntimeRequirementError(f"{context} does not name kind={kind!r}: {value!r}")
    if not isinstance(value.get("id"), str) or not value["id"]:
        raise RuntimeRequirementError(f"{context} carries no readable id: {value!r}")
    return dict(value)


def _require_target_identity(value: Any, *, project_binding_id: str) -> dict[str, Any]:
    """Return *value* proved completely valid against the canonical
    ``$defs/target_identity`` shape (P15-R1-F2 -- the whole declared shape, never a hand-picked
    subset of it) and bound to the exact Project Binding this call itself re-verifies."""

    checked = require_valid_target_identity(value)
    project_binding_ref = _require_reference(
        checked.get("project_binding_ref"),
        context="target_identity.project_binding_ref",
        kind="project_binding",
    )
    _require_reference(
        checked.get("deployment_declaration_ref"),
        context="target_identity.deployment_declaration_ref",
        kind=_DEPLOYMENT_DECLARATION_RECORD_KIND,
    )
    # Substituted-Binding refusal (Issue #64 V4): a target declaring a different Project
    # Binding than the one this call itself re-verified through Boot must never be observed
    # under this project's own identity -- exactly the cross-project/cross-binding exact
    # reference-equality discipline every other owner in this repository already applies.
    if project_binding_ref["id"] != project_binding_id:
        raise RuntimeRequirementError(
            "target_identity.project_binding_ref does not name the requested "
            f"project_binding_id: {project_binding_ref['id']!r} != {project_binding_id!r}"
        )
    return checked


def _require_boundary(value: Any) -> dict[str, Any]:
    """Return *value* proved completely valid against the canonical ``$defs/boundary`` shape,
    with its declared endpoint proved to fall inside its own declared ``network_scope``.

    P15-R1-F1: the host-allowlist decision lives *here*, in the route's own Boundary
    validation, rather than only inside whichever adapter a caller happened to supply -- so a
    Boundary naming one allowed host and an endpoint on another refuses with the adapter never
    invoked at all (zero-call), structurally, for every adapter implementation that exists or
    will exist. ``adapter.py`` re-enforces the identical rule itself immediately before it
    opens a socket; neither site trusts the other to be the only one.
    """

    checked = require_valid_boundary(value)
    require_endpoint_within_network_scope(checked["endpoint"], checked["network_scope"])
    return checked


def _instant(value: str, context: str) -> datetime:
    """Parse one canonical UTC ``Z``-suffixed timestamp into a real, comparable instant.

    P15-R1-F2: string comparison is *not* sound over this schema's own timestamp grammar
    (``common/timestamp.schema.json`` admits an optional fractional part), and the failure is
    not merely cosmetic -- ``"2026-01-01T00:00:00.5Z" < "2026-01-01T00:00:00Z"`` is ``True``
    lexicographically (``.`` sorts below ``Z``) while being ``False`` chronologically, so a
    lexicographic window check *accepts* an observation half a second past a whole-second
    ``expires_at``, and *refuses* one half a second after a whole-second ``issued_at``. Both
    directions are wrong; only real instants compare correctly.
    """

    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise RuntimeRequirementError(
            f"{context} is not a readable UTC instant: {value!r}"
        ) from error
    if parsed.tzinfo is None:
        raise RuntimeRequirementError(f"{context} carries no UTC designator: {value!r}")
    return parsed


def _require_within_time_window(boundary: dict[str, Any], observed_at: str) -> None:
    """Refuse before any adapter call unless *observed_at* falls within the Boundary's own
    declared, genuinely ordered, closed time window -- compared as real UTC instants."""

    issued_at = _instant(boundary["time_window"]["issued_at"], "boundary.time_window.issued_at")
    expires_at = _instant(boundary["time_window"]["expires_at"], "boundary.time_window.expires_at")
    observed = _instant(observed_at, "observed_at")
    if not issued_at < expires_at:
        raise RuntimeRequirementError(
            "boundary.time_window is not a genuinely ordered window "
            f"({boundary['time_window']['issued_at']!r} .. "
            f"{boundary['time_window']['expires_at']!r}) -- refusing before any adapter call"
        )
    if not (issued_at <= observed <= expires_at):
        raise RuntimeRequirementError(
            f"observed_at {observed_at!r} falls outside the Boundary's own declared time "
            f"window [{boundary['time_window']['issued_at']!r}, "
            f"{boundary['time_window']['expires_at']!r}] -- refusing before any adapter call"
        )


def _project_to_permitted_fields(
    observed_fields: Mapping[str, Any], permitted_fields: list[str]
) -> dict[str, Any]:
    """Return *observed_fields* projected down to exactly *permitted_fields*, refusing any
    field the adapter reported that the closed Boundary never permitted.

    P15-R1-F3: the route previously handed the adapter's *entire* reported mapping straight
    into redaction and persistence, so a buggy or hostile replacement adapter could persist a
    field (a credential, a whole response body) the Boundary never admitted. A compliant
    adapter never reports an unpermitted field, so one that does is a genuine defect worth
    surfacing loudly (:class:`~manosube_agent_civilization.runtime.errors.RuntimeAdapterError`)
    rather than silently dropping and committing the rest as though nothing had happened.
    """

    extra = sorted(set(observed_fields) - set(permitted_fields))
    if extra:
        raise RuntimeAdapterError(
            "adapter.observe() reported field(s) outside the Boundary's own permitted_fields: "
            f"{extra} -- refusing rather than persist anything the Boundary never admitted"
        )
    return {field: observed_fields[field] for field in permitted_fields if field in observed_fields}


def _redact(observed_fields: Mapping[str, Any], redaction_fields: list[str]) -> dict[str, Any]:
    redacted = set(redaction_fields)
    return {
        field: ("<REDACTED>" if field in redacted else value)
        for field, value in observed_fields.items()
    }


def _authority_context(boot_context: Any) -> dict[str, Any]:
    """Return the closed projection of *boot_context* that defines *whose authority* this
    observation is being made under -- the Project Binding's own identity, the Human Authority
    it names, and that Authority's own declared signing key.

    Deliberately **not** ``state_revision``/``semantic_fingerprint`` (which is what Phase 14's
    own :func:`~manosube_agent_civilization.projection.execution.execution_context_still_current`
    compares, correctly, for a *bound, reused* capability): a Runtime Observation re-verifies
    Boot fresh on every call, so an ordinary unrelated commit landing between this call's own
    Boot and its own commit is not a reason to refuse anything -- it is exactly the harmless
    contention the bounded Compare-And-Swap retry already exists to absorb. Only a genuine
    change in *this* projection means the observation would otherwise reach a target, or
    commit a fact, under an authority that is no longer the one it was verified against
    (P15-R1-F5).
    """

    binding = boot_context.project_binding
    return {
        "project_binding_id": boot_context.project_binding_id,
        "human_authority_ref": boot_context.human_authority_ref,
        "human_authority_signing_key": binding.get("human_authority_signing_key"),
    }


def _boot_authority_context(store: Any, project_id: str, project_binding_id: str) -> Any:
    """The one literal ``boot_project`` call site in this module.

    Reached from three points in a single observation -- once to establish the authority this
    call runs under, once immediately before the adapter is reached, and once on every commit
    attempt (P15-R1-F5) -- so this package's own static conformance proof still sees exactly
    one Boot call site in ``route.py``, and no second, drifting way of restoring a project can
    ever appear beside it. Every ``boot_project`` failure propagates unchanged, exactly as it
    always has; this route calls the adapter zero times on any such rejection.
    """

    return boot_project(store, project_id=project_id, project_binding_id=project_binding_id)


def _require_unchanged_authority_context(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    expected: Mapping[str, Any],
    stage: str,
) -> None:
    """Re-Boot and require the authority-defining context to be identical to *expected*,
    raising :class:`~manosube_agent_civilization.runtime.errors.RuntimeAuthorityFreshnessError`
    otherwise (P15-R1-F5)."""

    fresh = _authority_context(_boot_authority_context(store, project_id, project_binding_id))
    if fresh != dict(expected):
        raise RuntimeAuthorityFreshnessError(
            "the Project Binding / Human Authority verified at this observation's own initial "
            f"Boot is no longer the one this Store reports -- refusing {stage} rather than "
            "act under, or commit, stale authority"
        )


def _resolve_deployment_declaration(
    store: Any, project_id: str, target_identity: Mapping[str, Any]
) -> dict[str, Any]:
    """Resolve, independently identity-recompute, and anchor the canonical deployment
    declaration *target_identity* names (P15-R1-F6).

    Before this correction, ``target_identity["deployment_fingerprint"]`` was an arbitrary
    caller string and ``observed_deployment_identity`` was read straight out of the target's
    own HTTP response -- comparing the two proved only that *the endpoint echoed the expected
    string*, which anyone controlling both the declaration and the endpoint can arrange. The
    declared side is now anchored to a genuinely pre-committed, content-addressed,
    Human-Authority-declared record resolved from the Store: the reference must resolve, the
    resolved record must be schema-valid, its own recomputed id/semantic fingerprint must equal
    its own declared values (tamper check -- the identical ``_resolve_*``-with-identity-
    reverification pattern ``bootstrap.py`` already applies to grants and declarations), and it
    must independently restate every one of this target's own identifying fields
    (:data:`_DECLARATION_ANCHORED_TARGET_FIELDS`), so a legitimately committed declaration for
    one target can never be replayed as the anchor for a different one.

    Every refusal here is a :class:`~manosube_agent_civilization.runtime.errors.
    RuntimeRequirementError`, never an ``IDENTITY_MISMATCH`` observation outcome: an
    ``IDENTITY_MISMATCH`` is a statement about what a genuinely reached target reported, and
    nothing has been reached at all at this point -- the *request itself* is not anchored, so
    there is no observation to classify and none is committed.
    """

    ref = _require_reference(
        target_identity.get("deployment_declaration_ref"),
        context="target_identity.deployment_declaration_ref",
        kind=_DEPLOYMENT_DECLARATION_RECORD_KIND,
    )
    resolved = store.resolve_record(project_id, _DEPLOYMENT_DECLARATION_RECORD_KIND, ref["id"])
    if resolved is None:
        raise RuntimeRequirementError(
            "target_identity.deployment_declaration_ref does not resolve to a committed "
            f"runtime_deployment_declaration for project {project_id!r}: {ref['id']!r} -- a "
            "declared deployment identity with no canonical record behind it is a caller "
            "string, not an independently verifiable fact"
        )
    declaration = require_valid_deployment_declaration(resolved)
    if runtime_deployment_declaration_id(declaration) != declaration.get(
        "runtime_deployment_declaration_id"
    ):
        raise RuntimeRequirementError(
            f"resolved runtime_deployment_declaration {ref['id']!r} own recomputed identity "
            "does not equal its own declared value -- refusing to trust it"
        )
    if runtime_deployment_declaration_semantic_fingerprint(declaration) != declaration.get(
        "runtime_deployment_declaration_semantic_fingerprint"
    ):
        raise RuntimeRequirementError(
            f"resolved runtime_deployment_declaration {ref['id']!r} own recomputed semantic "
            "fingerprint does not equal its own declared value -- refusing to trust it"
        )
    if declaration.get("project_id") != project_id:
        raise RuntimeRequirementError(
            "resolved runtime_deployment_declaration names a different project than the one "
            f"being observed: {declaration.get('project_id')!r} != {project_id!r}"
        )
    for field in _DECLARATION_ANCHORED_TARGET_FIELDS:
        if declaration.get(field) != target_identity.get(field):
            raise RuntimeRequirementError(
                f"resolved runtime_deployment_declaration {ref['id']!r} own {field} does not "
                f"equal target_identity.{field} -- a genuinely committed declaration for one "
                "target may never anchor a different one: "
                f"{declaration.get(field)!r} != {target_identity.get(field)!r}"
            )
    return declaration


def observe_runtime_target(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    target_identity: Mapping[str, Any],
    boundary: Mapping[str, Any],
    adapter: RuntimeAdapter,
    observed_at: str,
) -> dict[str, Any]:
    """Bounded-observe one explicit runtime target and return ``{"envelope": ...,
    "receipt": RuntimeObservationReceipt}``.

    *target_identity* and *boundary* must already be real, explicit, closed shapes -- this
    function fingerprints them itself (never trusting a caller-declared fingerprint), and
    requires *target_identity*'s own ``project_binding_ref`` to name *project_binding_id*
    exactly. *observed_at* is a required, caller-supplied instant (this route reads no clock,
    the identical discipline every other route in this repository already requires) that must
    fall within *boundary*'s own declared, closed time window -- an observation whose own
    instant already falls outside that window refuses before the adapter is ever called.

    See ``10_RUNTIME/RUNTIME_CONTRACT.md`` §5 for the full canonical route this function
    implements, step by step.
    """

    _require_canonical_identity("project_id", project_id)
    _require_canonical_identity("project_binding_id", project_binding_id)
    require_valid_timestamp(observed_at, "observed_at")

    checked_boundary = _require_boundary(boundary)
    checked_target_identity = _require_target_identity(
        target_identity, project_binding_id=project_binding_id
    )
    _require_within_time_window(checked_boundary, observed_at)

    # Project/Human Authority re-verification through the existing Boot owner -- this route
    # mints no Authority Decision of its own (Runtime Observation is bounded by the closed
    # Observation Boundary itself, never by a write-permission grant; see this delivery's own
    # disclosed judgment call in ``10_RUNTIME/RUNTIME_CONTRACT.md`` §4). Every
    # ``boot_project`` failure propagates unchanged; this route calls the adapter zero times
    # on any such rejection.
    boot_context = _boot_authority_context(store, project_id, project_binding_id)
    real_human_authority_ref = dict(boot_context.human_authority_ref)
    authority_context = _authority_context(boot_context)

    # Store-anchored deployment identity (P15-R1-F6) -- before the declared and observed
    # identities are ever compared, the *declared* one must itself be a genuinely committed,
    # independently identity-recomputed canonical fact rather than a caller string.
    _resolve_deployment_declaration(store, project_id, checked_target_identity)

    target_fingerprint = runtime_target_fingerprint(checked_target_identity)
    boundary_fingerprint = runtime_observation_boundary_fingerprint(checked_boundary)
    observation_request_identity = runtime_observation_request_identity(
        target_fingerprint, boundary_fingerprint, checked_boundary["time_window"]["issued_at"]
    )

    declared_identity = getattr(adapter, "adapter_identity", None)
    if not isinstance(declared_identity, Mapping):
        raise RuntimeAdapterError(
            "adapter does not declare a readable adapter_identity attribute -- an unstated "
            "or unverifiable identity may never observe on this route's behalf"
        )

    # Authority freshness at the adapter boundary (P15-R1-F5): everything above was verified
    # against the world as it stood at this call's own initial Boot. Re-prove that world is
    # still the one in force before anything external is reached at all -- a Binding/Authority
    # change lands here as a refusal with zero adapter calls, never as a target reached under
    # stale context.
    _require_unchanged_authority_context(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        expected=authority_context,
        stage="before the adapter is reached",
    )

    # The adapter receives deep-frozen, alias-free copies (P15-R1-F3): a replaceable adapter
    # could otherwise mutate the exact dict objects this route validated and then goes on to
    # fingerprint, persist, and attest to, so that what was committed would differ from what
    # was actually checked. Frozen structures make that impossible rather than merely
    # detectable, and the route keeps using its own ``checked_*`` copies for everything after
    # the call regardless of what the adapter did or echoed back.
    raw = adapter.observe(
        target_identity=deep_freeze(checked_target_identity),
        boundary=deep_freeze(checked_boundary),
    )
    if not isinstance(raw, Mapping):
        raise RuntimeAdapterError(f"adapter.observe() returned {raw!r}, not a mapping")
    transport_outcome = raw.get("transport_outcome")
    if transport_outcome not in RUNTIME_ADAPTER_TRANSPORT_OUTCOMES:
        raise RuntimeAdapterError(
            f"adapter.observe()'s own transport_outcome is not recognized: {transport_outcome!r}"
        )

    if transport_outcome == "OBSERVED":
        raw_observed_fields = raw.get("observed_fields")
        if not isinstance(raw_observed_fields, Mapping):
            raise RuntimeAdapterError(
                "adapter.observe() reported OBSERVED with no readable observed_fields: "
                f"{raw_observed_fields!r}"
            )
        observed_deployment_identity = raw.get("observed_deployment_identity")

        # Field-boundary projection first (P15-R1-F3), then redaction -- both before any
        # fingerprint or persistence. Issue #64's own V4 credential-leakage proof requires a
        # redacted field to never appear, in any form, in what this route fingerprints or
        # commits; P15-R1-F3 additionally requires a field the Boundary never permitted at all
        # to never get that far in the first place.
        observed_fields = _redact(
            _project_to_permitted_fields(raw_observed_fields, checked_boundary["permitted_fields"]),
            list(checked_boundary.get("redaction_fields", [])),
        )
        observed_content_fingerprint: str | None = runtime_observed_content_fingerprint(
            observed_fields
        )

        # Structural discipline (Issue #64 V2/V4): the adapter's own transport-level
        # ``OBSERVED`` report is never itself trusted as "this is genuinely the declared
        # target, and its content is genuinely positive" -- both are independently
        # recomputed/compared here, never accepted from the adapter's own say-so.
        if observed_deployment_identity != checked_target_identity["deployment_fingerprint"]:
            observation_outcome = "IDENTITY_MISMATCH"
        elif "expected_field" in checked_boundary and (
            observed_fields.get(checked_boundary["expected_field"])
            != checked_boundary.get("expected_value")
        ):
            observation_outcome = "NEGATIVE"
        else:
            observation_outcome = "OBSERVED"
    else:
        # A transport failure (NOT_FOUND/PERMISSION_DENIED/TIMEOUT/UNAVAILABLE/MALFORMED)
        # is committed exactly as the adapter honestly reported it -- never folded into
        # NEGATIVE, never promoted to OBSERVED, and never silently discarded as an absence
        # unless the adapter itself reported the one outcome that means that (NOT_FOUND).
        observation_outcome = transport_outcome
        observed_fields = None
        observed_content_fingerprint = None

    envelope = derive_runtime_observation_envelope(
        project_id=project_id,
        target_identity=checked_target_identity,
        target_fingerprint=target_fingerprint,
        boundary=checked_boundary,
        boundary_fingerprint=boundary_fingerprint,
        observation_request_identity=observation_request_identity,
        observed_at=observed_at,
        observation_outcome=observation_outcome,
        observed_fields=observed_fields,
        observed_content_fingerprint=observed_content_fingerprint,
        adapter_identity=dict(declared_identity),
        human_authority_ref=real_human_authority_ref,
    )

    _commit_envelope(
        store,
        project_id,
        envelope,
        observed_at,
        project_binding_id=project_binding_id,
        authority_context=authority_context,
    )

    receipt = RuntimeObservationReceipt(
        status=RUNTIME_OUTCOME_TO_RECEIPT_STATUS[observation_outcome],
        runtime_observation_envelope_id=envelope["runtime_observation_envelope_id"],
        project_id=project_id,
        target_identity=checked_target_identity,
        boundary=checked_boundary,
        adapter_identity=dict(declared_identity),
        human_authority_ref=real_human_authority_ref,
        input_refs=(dict(checked_target_identity["project_binding_ref"]),),
        observations={
            "observation_outcome": observation_outcome,
            "observed_content_fingerprint": observed_content_fingerprint,
            "observed_at": observed_at,
        },
    )
    return {"envelope": envelope, "receipt": receipt}


def _commit_envelope(
    store: Any,
    project_id: str,
    envelope: dict[str, Any],
    committed_at: str,
    *,
    project_binding_id: str,
    authority_context: Mapping[str, Any],
) -> None:
    """Durably persist *envelope* through the Store's own single sanctioned committer,
    bounded Compare-And-Swap retry against genuine, unrelated contention only (Issue #64 V4's
    own "unrelated Store mutation between calls still refuses/succeeds correctly" proof) --
    the identical discipline :func:`~manosube_agent_civilization.projection.route._claim_slot`
    already establishes.

    P15-R1-F5: the authority-defining context is re-proved on **every** attempt, not once
    before the loop -- a retry exists precisely because the Store moved underneath this call,
    and the whole point of the check is to distinguish a harmless unrelated commit (which
    bumps ``state_revision`` alone and must not block anything) from a genuine Binding/Human
    Authority change (which must refuse rather than commit an Envelope carrying now-stale
    ``human_authority_ref`` into newer State).

    A record already resolved at this exact (kind, id) is, by construction, byte-identical
    content (the id is a pure content address over the complete envelope) -- committing it
    again is a genuine idempotent replay, never a conflict; the Store's own same-key/
    identical-content acceptance is the entire mechanism this relies on. A ``RecordConflictError``
    here would mean a real hash collision or a genuine tamper between derivation and commit --
    refused, never silently retried.
    """

    envelope_id = envelope["runtime_observation_envelope_id"]
    if (
        runtime_observation_envelope_semantic_fingerprint(envelope)
        != envelope["runtime_observation_semantic_fingerprint"]
    ):
        raise RuntimeEnvelopeIntegrityError(
            "newly derived envelope's own recomputed semantic fingerprint does not equal its "
            "own declared value -- refusing to commit"
        )

    for _ in range(_MAX_COMMIT_RETRIES):
        _require_unchanged_authority_context(
            store,
            project_id=project_id,
            project_binding_id=project_binding_id,
            expected=authority_context,
            stage="to commit this Envelope",
        )
        current_state = store.load_current(project_id)
        transaction_id = f"TX-RUNTIME-OBSERVATION-{envelope_id}-{current_state['state_revision']}"
        next_state = dict(current_state)
        next_state["state_revision"] = current_state["state_revision"] + 1
        next_state["previous_state_fingerprint"] = current_state["semantic_fingerprint"]
        next_state["lineage_head_ref"] = {"kind": "state_transition", "id": transaction_id}
        next_state["semantic_fingerprint"] = fingerprint_project_state(next_state).as_dict()
        transition = {
            "schema_version": "0.1",
            "transaction_id": transaction_id,
            "event_type": "TRANSITION",
            "project_id": project_id,
            "from_revision": current_state["state_revision"],
            "to_revision": next_state["state_revision"],
            "before_fingerprint": current_state["semantic_fingerprint"],
            "after_fingerprint": next_state["semantic_fingerprint"],
            "after_state": next_state,
            "evidence_refs": [],
            "committed_at": committed_at,
        }
        try:
            commit_state_transition(
                store,
                project_id,
                current_state["state_revision"],
                current_state["semantic_fingerprint"],
                next_state,
                transition,
                records=[(_ENVELOPE_RECORD_KIND, envelope_id, envelope)],
            )
            return
        except RecordConflictError as error:
            raise RuntimeEnvelopeIntegrityError(
                f"a different record already occupies {_ENVELOPE_RECORD_KIND}/{envelope_id} "
                "with different content -- refusing rather than trust either"
            ) from error
        except StaleStateError:
            continue
    raise RuntimeRequirementError(
        f"could not durably commit {_ENVELOPE_RECORD_KIND}/{envelope_id} after "
        f"{_MAX_COMMIT_RETRIES} Compare-And-Swap retries -- sustained unrelated contention on "
        "this project's own State"
    )


__all__ = ["RUNTIME_SCHEMA_BASE", "observe_runtime_target"]
