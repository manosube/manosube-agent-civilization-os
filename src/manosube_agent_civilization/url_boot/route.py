"""The one public URL Boot route (Phase 17, Issue #69).

``URL_BOOT_OWNER_COUNT=1``, ``PUBLIC_URL_BOOT_ENTRY_POINT_COUNT=1`` (this module) ``+1``
(:mod:`~manosube_agent_civilization.url_boot.evidence_handoff`'s own single hand-off route).

``observe_url_source`` re-verifies Project/Human Authority identity through the existing Boot
owner (:func:`~manosube_agent_civilization.boot.boot_project`), independently fingerprints an
explicit, fully decomposed source identity and a closed fetch Boundary (never trusting either
from a caller beyond their declared shape), refuses a source whose own hostname falls outside the
Boundary's own declared ``network_scope`` before Boot or any adapter is ever reached, owns the
entire bounded, per-hop-reauthorized redirect loop itself (never delegating it to the
replaceable :class:`~manosube_agent_civilization.url_boot.types.UrlSourceAdapter`), and derives
and commits one canonical URL Source Observation Envelope through the existing Store's own single
sanctioned committer (:func:`~manosube_agent_civilization.store.commit.commit_state_transition`)
-- but only when the fetch actually succeeded.

**Structural Review Round 1 (P17-R1-F1 through F5), applied on top of the three Codex findings
already closed at this delivery's initial head.** Six corrections land here, together:

- **P17-R1-F1 (zero State mutation on failure).** The first delivery derived and committed an
  Envelope for every one of the eleven :data:`~manosube_agent_civilization.url_boot.types.
  URL_FETCH_OUTCOMES`, including every typed failure -- directly contradicting P17-C7's own
  requirement that "no failed or refused fetch may mutate canonical State." This route now calls
  :func:`~manosube_agent_civilization.url_boot.engine.derive_url_source_observation_envelope` and
  :func:`_commit_envelope` for exactly one outcome, ``"OBSERVED"``; every other outcome returns a
  bounded, purely ephemeral :class:`~manosube_agent_civilization.url_boot.types.
  UrlSourceObservationReceipt` (``url_source_observation_envelope_id=None``, ``status`` ``FAILED``
  or ``UNAVAILABLE``) with zero Store I/O of any kind -- ``engine.py``'s own deriver refuses,
  structurally, to be called for any other outcome, so the invariant holds even if this route's
  own discipline were ever violated by a future edit.
- **P17-R1-F2 (route-owned redirect/boundary/identity authority).** The first delivery gave the
  adapter one ``fetch()`` method that followed an entire redirect chain internally and reported
  only the final identity/hop-count/outcome -- a conforming-looking but dishonest adapter could
  follow a disallowed intermediate hop, fabricate a hop count, or simply assert
  ``IDENTITY_MISMATCH``/``BOUNDARY_REFUSED`` outright, and the route had no way to catch it. The
  replaceable :class:`~manosube_agent_civilization.url_boot.types.UrlSourceAdapter` now exposes
  exactly one bounded, single-hop transport primitive
  (:meth:`~manosube_agent_civilization.url_boot.types.UrlSourceAdapter.fetch_one_hop`); this
  route owns the entire loop below, re-authorizing every redirect target against ``boundary``'s
  own ``network_scope`` itself before ever calling the adapter for it, and performing every
  content-type/size/JSON/``IDENTITY_MISMATCH`` classification itself, from the adapter's own
  bounded per-hop facts alone. There is no field left in the adapter's own report through which a
  hidden hop, a fabricated count, or an asserted classification could ever reach this route.
- **P17-R1-F3 (loopback test allowance is no longer caller-mintable).** ``permit_loopback_test_hosts``
  no longer exists anywhere in the closed Boundary schema -- a request-facing caller supplying
  Boundary *data* has no field through which to enable it, at all. The one place it can be set is
  a concrete adapter's own constructor (``LocalHttpUrlSourceAdapter(permit_loopback_test_hosts=
  True)``), a Python composition-time decision no request-facing caller who only ever supplies
  ``source_identity``/``boundary`` data can reach or substitute. See ``adapter.py``'s own module
  docstring.
- **P17-R1-F4 (cross-hop DNS resolution drift).** Each hop's own resolved address is now bound,
  once, to its own ``(host, port)`` for the lifetime of this one fetch: if a later hop resolves
  the *same* ``(host, port)`` to a *different* address than an earlier hop of this identical
  fetch already did, the whole fetch refuses as ``BOUNDARY_REFUSED`` -- the same outcome an
  unsafe resolved address itself produces, since both are "this resolved address is not one this
  route can trust." The admitted, per-``(host, port)`` resolution is what
  ``resolution_provenance`` persists on every successful Envelope.
- **P17-R1-F5 (exact Project/Binding/Boot context binding).** A committed Envelope now carries
  ``project_binding_ref`` and ``boot_state_fingerprint`` -- the exact Project Binding identity and
  Boot-observed State fingerprint this call's own Boot restored, both fully identity-sensitive
  (:data:`~manosube_agent_civilization.url_boot.identity.ENVELOPE_SEMANTIC_FIELDS`) -- so two
  Boot contexts that happen to share a Human Authority can never again produce indistinguishable
  provenance. :mod:`~manosube_agent_civilization.url_boot.evidence_handoff` re-verifies both
  fields against the real, resolved Envelope before handoff, never trusting a receipt's own claim.
- **P17-R1-F6** is a documentation-only correction (``docs/project_sources/
  03_CURRENT_DEVELOPMENT_STATE.md``'s own last-wins restatement) and touches no code in this
  module.

**Structural Review Round 2 (P17-R2-F1 through F3), reviewed at Round 1's own corrected head
and reopening three of its six closed findings.** Three further corrections land here:

- **P17-R2-F1 (route-owned network admission, not merely route-owned redirects).** Round 1 gave
  the adapter one ``fetch_one_hop`` that both resolved *and* classified *and* connected in one
  uninterruptible step -- the route re-authorized the requested *hostname* before calling the
  adapter, but the adapter's own resolution remained the sole authority for the *resolved
  address*'s own safety (it alone could assert ``BOUNDARY_REFUSED``), and its own connection
  step remained the sole authority for *which* address was actually reached. The replaceable
  :class:`~manosube_agent_civilization.url_boot.types.UrlSourceAdapter` now exposes two bounded
  primitives instead of one: :meth:`~manosube_agent_civilization.url_boot.types.UrlSourceAdapter.
  resolve_hop` reports only a genuine DNS lookup's own result, never a classification; this route
  alone classifies that resolved address's own safety
  (:func:`~manosube_agent_civilization.url_boot.network.require_safe_resolved_address`) and binds
  it as *this hop's one admitted address*, refusing as ``BOUNDARY_REFUSED`` itself when unsafe --
  an outcome that no longer exists anywhere in either adapter-reportable vocabulary
  (:data:`~manosube_agent_civilization.url_boot.types.URL_HOP_RESOLVE_OUTCOMES`,
  :data:`~manosube_agent_civilization.url_boot.types.URL_HOP_CONNECT_OUTCOMES`) at all, so an
  adapter has no field left through which to assert it. Only once the route has admitted an
  address does it call :meth:`~manosube_agent_civilization.url_boot.types.UrlSourceAdapter.
  connect_hop`, handing the adapter that *exact* admitted address (never a bare hostname to
  resolve a second time), and this route refuses (:class:`~manosube_agent_civilization.url_boot.
  errors.UrlBootAdapterError`) any report whose own ``resolved_address`` disagrees with the
  address it was handed -- an adapter can neither report a safe-looking address while connecting
  elsewhere, nor smuggle an unsafe address through as a successful ``RESPONSE``.
- **P17-R2-F2 (non-substitutable loopback composition boundary).** Round 1 moved
  ``permit_loopback_test_hosts`` to ``LocalHttpUrlSourceAdapter``'s own constructor, reasoning it
  was then reachable only by test-composition code -- Round 2 correctly identified that as merely
  *relocating* the identical caller-reachable switch one level earlier: that adapter is exported
  from this package's own public surface, so any caller able to supply the ``adapter`` argument
  to public :func:`observe_url_source` could still construct exactly that permissive object.
  Because P17-R2-F1 already moved *all* address-safety classification to this module alone, the
  adapter now carries no loopback-related parameter of any kind -- there is nothing left on it to
  be told to permit. The loopback decision instead lives exclusively in this module's own two
  permanently bound classifiers, :func:`_require_safe_resolved_address_production` (which
  :func:`observe_url_source` -- the only entry point this package's own public ``__init__.py``
  ever exports -- is unconditionally bound to) and
  :func:`_require_safe_resolved_address_permitting_loopback_only` (which only the distinctly-
  named, never-publicly-exported :func:`observe_url_source_for_disposable_local_test` is bound
  to). Neither public function's own parameter list carries a loopback-related argument at all --
  a caller cannot reach the exception by keyword, by position, or by substituting any adapter or
  Boundary value, because no parameter or field anywhere in this call graph decides it; only
  *which of the two distinctly-named functions you import and call* does, a composition-time
  choice made once, in this module's own source, never at request time from caller-supplied data.
- **P17-R2-F3 (resolvable exact Boot context at Evidence handoff).** Round 1's own
  ``boot_state_fingerprint`` closed *tampering* with the committed field (any recomputation
  mismatch fails the existing three-way envelope-identity check), but left Evidence handoff with
  no way to *independently re-derive* that fingerprint from this project's own real, canonical
  State history -- a bare fingerprint is not itself a reference anything can resolve. A committed
  Envelope now additionally carries ``boot_state_transition_ref``, the exact, Store-resolvable
  ``{"kind": "state_transition", "id": ...}`` reference to the committed transition (or, for a
  genesis-state Boot, the genesis event -- ``binding/route.py``'s own genesis-State enforcement
  requires ``lineage_head_ref`` to be ``null`` at genesis, so this route falls back to the one
  fixed, well-known genesis transaction identity in that case) that produced this exact
  Boot-observed State. :mod:`~manosube_agent_civilization.url_boot.evidence_handoff` now resolves
  that reference through the Store's own existing ``resolve_transaction`` surface and the
  referenced Project Binding through its own canonical identity owner *before* deriving any
  Evidence, refusing a self-consistent-but-uncorroborated Envelope whose claims do not actually
  reproduce from this project's own real, canonical history.

Canonical route (``12_URL_BOOT/URL_BOOT_CONTRACT.md`` §5):

```text
complete schema validation of the declared source identity and closed fetch Boundary
→ network-scope check on the requested source -- zero-call, before Boot or any adapter
→ real-instant time-window check -- refuses before any adapter call
→ real Project/Human Authority (Boot re-verification)
→ explicit source identity, fingerprinted (never trusted from a caller)
→ closed fetch Boundary, fingerprinted (never trusted from a caller)
→ deterministic source_request_identity (source + Boundary + issued_at)
→ authority-freshness re-check -- refuses before the adapter
→ route-owned, per-hop-reauthorized redirect loop -- one bounded single-hop adapter call per
  hop, cross-hop DNS-resolution-drift binding, and every redirect/content/identity
  classification performed here alone
→ OBSERVED only: canonical URL Source Observation Envelope, exact Boot-context binding,
  authority-freshness re-check on every commit attempt, existing canonical persistence boundary
  (commit_state_transition)
→ anything else: bounded, ephemeral, non-committed URL Source Observation Receipt -- zero State
  mutation, zero commit, zero Evidence-handoff eligibility
```
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import json
from typing import Any
from urllib.parse import urljoin

from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store.commit import commit_state_transition
from manosube_agent_civilization.store.errors import RecordConflictError, StaleStateError

from .engine import (
    URL_BOOT_SCHEMA_BASE,
    derive_url_source_observation_envelope,
    parse_utc_instant,
    require_valid_boundary,
    require_valid_source_identity,
    require_valid_timestamp,
)
from .errors import (
    UrlBootAdapterError,
    UrlBootAuthorityFreshnessError,
    UrlBootEnvelopeIntegrityError,
    UrlBootRequirementError,
)
from .identity import (
    url_boundary_fingerprint,
    url_observed_content_fingerprint,
    url_source_fingerprint,
    url_source_observation_envelope_semantic_fingerprint,
    url_source_request_identity,
)
from .network import (
    UnsafeResolvedAddressError,
    canonical_source_identity,
    require_safe_resolved_address,
    require_source_within_network_scope,
    source_url,
)
from .types import (
    RECEIPT_STATUSES,
    URL_FETCH_OUTCOMES,
    URL_HOP_CONNECT_OUTCOMES,
    URL_HOP_RESOLVE_OUTCOMES,
    URL_OUTCOME_TO_RECEIPT_STATUS,
    UrlSourceAdapter,
    UrlSourceObservationReceipt,
    deep_freeze,
)

_ENVELOPE_RECORD_KIND = "url_source_observation_envelope"
#: The identical Compare-And-Swap retry bound Runtime's own ``_commit_envelope`` uses -- bounded
#: protection against genuine, ordinary contention from an unrelated commit landing on this
#: project between this route's own ``load_current`` and its own ``commit``.
_MAX_COMMIT_RETRIES = 8

#: A single-hop connect-stage outcome that means no response was ever reached for that hop --
#: refused immediately, the whole fetch's own outcome (P17-R1-F2). ``BOUNDARY_REFUSED`` is
#: deliberately absent: it is never an adapter-reportable outcome at either stage (P17-R2-F1), so
#: it can never appear in a set an adapter's own report is validated against -- it is produced
#: only by this module's own ``_fetch_with_route_owned_redirects``, directly.
_HOP_CONNECT_FAILURE_OUTCOMES: frozenset[str] = frozenset(
    {"CONNECTION_FAILURE", "TLS_FAILURE", "TIMEOUT"}
)

#: The one genesis transaction identity every ``FileStateStore.initialize`` call stages and
#: promotes under (mirrors ``binding/route.py``'s own identically-named, identically-reasoned
#: module constant) -- read-only here, as the ``boot_state_transition_ref`` a Boot restored at
#: genesis (``state_revision == 0``, whose own ``lineage_head_ref`` is schema-required ``null``,
#: per ``binding/route.py``'s own genesis-State enforcement) resolves under, since no real
#: ``TRANSITION`` event exists yet to mint a ``lineage_head_ref`` from (P17-R2-F3).
_GENESIS_TRANSACTION_ID = "TX-GENESIS"


def _require_safe_resolved_address_production(address: str) -> None:
    """The one network-address-safety classifier every publicly exported ``observe_url_source``
    call is permanently, non-overridably bound to: loopback is always refused, with no
    parameter, field, or adapter substitution anywhere through which any caller could ever change
    that (P17-R2-F2). See this module's own docstring, "Structural Review Round 2 (P17-R2-F2)"."""

    require_safe_resolved_address(address, permit_loopback_test_hosts=False)


def _require_safe_resolved_address_permitting_loopback_only(address: str) -> None:
    """The one network-address-safety classifier :func:`observe_url_source_for_disposable_local_
    test` is permanently bound to -- loopback is the *only* exception ever admitted; every other
    unsafe address class (private/link-local/multicast/reserved) is still refused exactly as in
    production. Reachable only by importing this module's own distinctly-named, non-public-
    surface test entry point directly -- never through any parameter of public
    ``observe_url_source`` (P17-R2-F2)."""

    require_safe_resolved_address(address, permit_loopback_test_hosts=True)


def _require_canonical_identity(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise UrlBootRequirementError(f"{name} must be a non-empty string identity: {value!r}")
    if "/" in value or "\\" in value or value.startswith("..") or "://" in value:
        raise UrlBootRequirementError(
            f"{name} must be a canonical identity, never a path/URL/locator: {value!r}"
        )
    return value


def _require_within_time_window(boundary: dict[str, Any], observed_at: str) -> None:
    """Refuse before any adapter call unless *observed_at* falls within the Boundary's own
    declared, genuinely ordered, closed time window -- compared as real UTC instants, the
    identical discipline ``runtime/route.py``'s own ``_require_within_time_window`` applies."""

    issued_at = parse_utc_instant(
        boundary["time_window"]["issued_at"], "boundary.time_window.issued_at"
    )
    expires_at = parse_utc_instant(
        boundary["time_window"]["expires_at"], "boundary.time_window.expires_at"
    )
    observed = parse_utc_instant(observed_at, "observed_at")
    if not issued_at < expires_at:
        raise UrlBootRequirementError(
            "boundary.time_window is not a genuinely ordered window "
            f"({boundary['time_window']['issued_at']!r} .. "
            f"{boundary['time_window']['expires_at']!r}) -- refusing before any adapter call"
        )
    if not (issued_at <= observed <= expires_at):
        raise UrlBootRequirementError(
            f"retrieved_at {observed_at!r} falls outside the Boundary's own declared time "
            f"window [{boundary['time_window']['issued_at']!r}, "
            f"{boundary['time_window']['expires_at']!r}] -- refusing before any adapter call"
        )


def _redact(observed_fields: Mapping[str, Any], redaction_fields: list[str]) -> dict[str, Any]:
    redacted = set(redaction_fields)
    return {
        field: ("<REDACTED>" if field in redacted else value)
        for field, value in observed_fields.items()
    }


def _authority_context(boot_context: Any) -> dict[str, Any]:
    """Return the closed projection of *boot_context* that defines *whose authority* this
    observation is being made under -- the identical discipline
    ``runtime/route.py``'s own ``_authority_context`` establishes, applied here even though this
    package resolves no signed declaration: a Binding/Human Authority change between this call's
    own initial Boot and its own commit must still refuse rather than commit silently."""

    binding = boot_context.project_binding
    return {
        "project_binding_id": boot_context.project_binding_id,
        "human_authority_ref": boot_context.human_authority_ref,
        "human_authority_signing_key": binding.get("human_authority_signing_key"),
    }


def _boot_authority_context(store: Any, project_id: str, project_binding_id: str) -> Any:
    """The one literal ``boot_project`` call site in this module -- reached twice in a single
    observation (once to establish the authority this call runs under, once on every commit
    attempt), the identical discipline ``runtime/route.py`` already established."""

    return boot_project(store, project_id=project_id, project_binding_id=project_binding_id)


def _require_unchanged_authority_context(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    expected: Mapping[str, Any],
    stage: str,
) -> None:
    fresh = _authority_context(_boot_authority_context(store, project_id, project_binding_id))
    if fresh != dict(expected):
        raise UrlBootAuthorityFreshnessError(
            "the Project Binding / Human Authority verified at this observation's own initial "
            f"Boot is no longer the one this Store reports -- refusing {stage} rather than act "
            "under, or commit, stale authority"
        )


def _resolve_redirect_target(
    current_identity: Mapping[str, Any], redirect_location: str
) -> dict[str, Any] | None:
    """Return the canonical, fully decomposed identity a redirect Location header names,
    resolved against *current_identity*'s own URL -- ``None`` when the target is not a readable
    ``http``/``https`` URL at all (P17-R1-F2: this route trusts no field the adapter reports as
    already being that identity; it recomputes it itself from the raw header value alone)."""

    target_url = urljoin(source_url(current_identity), redirect_location)
    try:
        return canonical_source_identity(target_url)
    except UrlBootRequirementError:
        return None


def _hop_result(
    fetch_outcome: str,
    *,
    effective_source_identity: dict[str, Any] | None = None,
    response_status: int | None = None,
    redirect_hop_count: int,
    observed_fields: dict[str, Any] | None = None,
    resolution_provenance: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "fetch_outcome": fetch_outcome,
        "effective_source_identity": effective_source_identity,
        "response_status": response_status,
        "redirect_hop_count": redirect_hop_count,
        "observed_fields": observed_fields,
        "resolution_provenance": resolution_provenance or [],
    }


def _classify_terminal_response(
    raw: Mapping[str, Any],
    effective_identity: dict[str, Any],
    hop: int,
    status: int,
    *,
    boundary: Mapping[str, Any],
    resolution_provenance: list[dict[str, Any]],
) -> dict[str, Any]:
    """Classify one genuinely reached, non-redirect HTTP response into its final
    :data:`~manosube_agent_civilization.url_boot.types.URL_FETCH_OUTCOMES` member -- entirely
    from the adapter's own bounded per-hop facts, never accepted from the adapter as an assertion
    (P17-R1-F2)."""

    if raw.get("oversized"):
        return _hop_result(
            "OVERSIZED_RESPONSE",
            effective_source_identity=effective_identity,
            response_status=status,
            redirect_hop_count=hop,
        )

    admitted_content_types = {value.lower() for value in boundary["admitted_content_types"]}
    if raw.get("content_type") not in admitted_content_types:
        return _hop_result(
            "UNSUPPORTED_MEDIA_TYPE",
            effective_source_identity=effective_identity,
            response_status=status,
            redirect_hop_count=hop,
        )

    body = raw.get("body")
    if not isinstance(body, bytes | bytearray):
        raise UrlBootAdapterError(
            f"adapter.fetch_one_hop() reported RESPONSE with an unreadable body: {body!r}"
        )
    try:
        parsed = json.loads(bytes(body).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _hop_result(
            "MALFORMED",
            effective_source_identity=effective_identity,
            response_status=status,
            redirect_hop_count=hop,
        )
    if not isinstance(parsed, dict) or not (200 <= status < 300):
        return _hop_result(
            "MALFORMED",
            effective_source_identity=effective_identity,
            response_status=status,
            redirect_hop_count=hop,
        )

    expected_field = boundary.get("expected_field")
    if expected_field is not None and parsed.get(expected_field) != boundary.get("expected_value"):
        return _hop_result(
            "IDENTITY_MISMATCH",
            effective_source_identity=effective_identity,
            response_status=status,
            redirect_hop_count=hop,
        )

    permitted_fields = list(boundary["permitted_fields"])
    observed_fields = {field: parsed[field] for field in permitted_fields if field in parsed}
    return _hop_result(
        "OBSERVED",
        effective_source_identity=effective_identity,
        response_status=status,
        redirect_hop_count=hop,
        observed_fields=observed_fields,
        resolution_provenance=resolution_provenance,
    )


def _fetch_with_route_owned_redirects(
    adapter: UrlSourceAdapter,
    source_identity: Mapping[str, Any],
    boundary: Mapping[str, Any],
    *,
    classify_resolved_address: Callable[[str], None],
) -> dict[str, Any]:
    """Own the entire bounded, per-hop-reauthorized redirect loop (P17-R1-F2/F4, P17-R2-F1):
    calls the replaceable adapter's own bounded single-hop resolve/connect primitives exactly
    once each per hop, re-authorizes every redirect target against *boundary*'s own
    ``network_scope`` itself before ever reaching the adapter for it, independently classifies
    every resolved address's own safety itself via *classify_resolved_address* (never asking the
    adapter, and never accepting an adapter-asserted ``BOUNDARY_REFUSED`` -- P17-R2-F1), binds
    each hop's own admitted address to its own ``(host, port)`` for the lifetime of this one
    fetch and refuses on any later drift, requires the adapter's own ``connect_hop`` to report
    having connected to *exactly* the address this route admitted, and performs every
    content-type/size/JSON/``IDENTITY_MISMATCH`` classification itself.

    *classify_resolved_address* is a callable of one positional ``str`` argument, raising
    :class:`~manosube_agent_civilization.url_boot.network.UnsafeResolvedAddressError` for an
    unsafe address and returning ``None`` for a safe one -- always one of this module's own two
    permanently bound classifiers (production or the disposable-local-test-only exception),
    never a value any caller of :func:`observe_url_source` can supply (P17-R2-F2).

    Returns ``{"fetch_outcome", "effective_source_identity", "response_status",
    "redirect_hop_count", "observed_fields", "resolution_provenance"}`` -- the identical shape
    :func:`_observe_url_source_impl` itself now derives an Envelope from (``fetch_outcome ==
    "OBSERVED"``) or returns as a bounded, ephemeral failure receipt (anything else).
    """

    network_scope = boundary["network_scope"]
    max_redirects = boundary["redirect_policy"]["max_redirects"]
    current_identity = dict(source_identity)
    resolution_bindings: dict[tuple[str, int], str] = {}
    resolution_provenance: list[dict[str, Any]] = []

    for hop in range(max_redirects + 1):
        resolve_raw = adapter.resolve_hop(source_identity=deep_freeze(current_identity))
        if not isinstance(resolve_raw, Mapping):
            raise UrlBootAdapterError(
                f"adapter.resolve_hop() returned {resolve_raw!r}, not a mapping"
            )
        resolve_outcome = resolve_raw.get("outcome")
        if resolve_outcome not in URL_HOP_RESOLVE_OUTCOMES:
            raise UrlBootAdapterError(
                f"adapter.resolve_hop()'s own outcome is not recognized: {resolve_outcome!r}"
            )
        if resolve_outcome == "DNS_FAILURE":
            return _hop_result("DNS_FAILURE", redirect_hop_count=hop)

        candidate_address = resolve_raw.get("resolved_address")
        if not isinstance(candidate_address, str) or not candidate_address:
            raise UrlBootAdapterError(
                "adapter.resolve_hop() reported RESOLVED with no readable resolved_address"
            )

        # P17-R2-F1: the route alone classifies the resolved address's own safety -- never the
        # adapter, and never a route-only outcome an adapter's own report could ever assert.
        try:
            classify_resolved_address(candidate_address)
        except UnsafeResolvedAddressError:
            return _hop_result("BOUNDARY_REFUSED", redirect_hop_count=hop)

        host_port_key = (current_identity["host"], current_identity["port"])
        bound_address = resolution_bindings.get(host_port_key)
        if bound_address is None:
            resolution_bindings[host_port_key] = candidate_address
            resolution_provenance.append(
                {
                    "host": current_identity["host"],
                    "port": current_identity["port"],
                    "resolved_address": candidate_address,
                }
            )
        elif bound_address != candidate_address:
            # P17-R1-F4: the identical host/port this one fetch already resolved once now
            # resolves to a *different* address -- DNS/resolution drift within one fetch, never
            # trusted, regardless of what this hop's own response otherwise says.
            return _hop_result("BOUNDARY_REFUSED", redirect_hop_count=hop)

        admitted_address = candidate_address
        connect_raw = adapter.connect_hop(
            source_identity=deep_freeze(current_identity),
            boundary=deep_freeze(boundary),
            admitted_address=admitted_address,
        )
        if not isinstance(connect_raw, Mapping):
            raise UrlBootAdapterError(
                f"adapter.connect_hop() returned {connect_raw!r}, not a mapping"
            )
        connect_outcome = connect_raw.get("outcome")
        if connect_outcome not in URL_HOP_CONNECT_OUTCOMES:
            raise UrlBootAdapterError(
                f"adapter.connect_hop()'s own outcome is not recognized: {connect_outcome!r}"
            )
        if connect_outcome in _HOP_CONNECT_FAILURE_OUTCOMES:
            return _hop_result(connect_outcome, redirect_hop_count=hop)

        # P17-R2-F1: the adapter must have connected to *exactly* the address this route
        # admitted -- never re-resolved, never substituted, never a different address entirely.
        if connect_raw.get("resolved_address") != admitted_address:
            raise UrlBootAdapterError(
                "adapter.connect_hop() reported a resolved_address that does not equal the "
                f"exact address this route admitted for this hop: "
                f"{connect_raw.get('resolved_address')!r} != {admitted_address!r}"
            )

        raw = connect_raw
        status = raw.get("response_status")
        if not isinstance(status, int):
            raise UrlBootAdapterError(
                "adapter.connect_hop() reported RESPONSE with an unreadable response_status: "
                f"{status!r}"
            )
        redirect_location = raw.get("redirect_location")

        if redirect_location is not None and 300 <= status < 400:
            if hop == max_redirects:
                return _hop_result(
                    "REDIRECT_REFUSED", response_status=status, redirect_hop_count=hop
                )
            next_identity = _resolve_redirect_target(current_identity, redirect_location)
            if next_identity is None:
                return _hop_result(
                    "REDIRECT_REFUSED", response_status=status, redirect_hop_count=hop
                )
            try:
                require_source_within_network_scope(next_identity, network_scope)
            except UrlBootRequirementError:
                return _hop_result(
                    "REDIRECT_REFUSED", response_status=status, redirect_hop_count=hop
                )
            current_identity = next_identity
            continue

        return _classify_terminal_response(
            raw,
            current_identity,
            hop,
            status,
            boundary=boundary,
            resolution_provenance=resolution_provenance,
        )

    return _hop_result("REDIRECT_REFUSED", redirect_hop_count=max_redirects)


def _observe_url_source_impl(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    source_identity: Mapping[str, Any],
    boundary: Mapping[str, Any],
    adapter: UrlSourceAdapter,
    observed_at: str,
    classify_resolved_address: Callable[[str], None],
) -> dict[str, Any]:
    """The complete ``observe_url_source`` implementation, closed over no network-address-safety
    policy of its own -- *classify_resolved_address* is supplied entirely by this function's own
    two callers (:func:`observe_url_source`, permanently bound to the production classifier, and
    :func:`observe_url_source_for_disposable_local_test`, permanently bound to the
    loopback-permitting one), never by anything reaching this function from outside this module
    (P17-R2-F2). This function itself is never exported from this package's own public surface.

    Returns ``{"envelope": dict | None, "receipt": UrlSourceObservationReceipt}``.

    ``envelope`` is ``None`` for every outcome except ``"OBSERVED"`` (P17-C7/P17-R1-F1): a failed
    or refused fetch mutates no canonical State and commits no record at all, and its own
    ``receipt`` names no envelope id.

    *source_identity* and *boundary* must already be real, explicit, closed shapes -- this
    function proves each completely valid against its own canonical schema before Boot or any
    adapter is reached, and fingerprints them itself (never trusting a caller-declared
    fingerprint). *observed_at* is a required, caller-supplied instant (this route reads no
    clock) that must fall within *boundary*'s own declared, closed time window, compared as real
    UTC instants.

    Zero-call refusals (before any adapter is ever reached, and before Boot for the first):

    - *source_identity*'s own hostname must be inside *boundary*'s own declared
      ``network_scope`` (P17-C1/P17-C5);
    - the Project Binding / Human Authority verified at this call's own initial Boot must still
      be the ones the Store reports -- re-proved again on every commit attempt.
    """

    _require_canonical_identity("project_id", project_id)
    _require_canonical_identity("project_binding_id", project_binding_id)
    require_valid_timestamp(observed_at, "observed_at")

    checked_source_identity = require_valid_source_identity(source_identity)
    checked_boundary = require_valid_boundary(boundary)
    require_source_within_network_scope(checked_source_identity, checked_boundary["network_scope"])
    _require_within_time_window(checked_boundary, observed_at)

    boot_context = _boot_authority_context(store, project_id, project_binding_id)
    real_human_authority_ref = dict(boot_context.human_authority_ref)
    authority_context = _authority_context(boot_context)
    # P17-R1-F5: the exact Boot-restored Binding identity and Boot-observed State fingerprint --
    # captured here, once, at this call's own initial Boot, exactly like every other real fact
    # this route commits.
    real_project_binding_ref = {"kind": "project_binding", "id": project_binding_id}
    real_boot_state_fingerprint = dict(boot_context.current_state["semantic_fingerprint"])
    # P17-R2-F3: the exact, Store-resolvable reference to the transition (or, at genesis, the
    # genesis event) that produced this exact Boot-observed State -- a bare fingerprint alone
    # names no revision Evidence handoff could ever reconstruct and re-verify against later,
    # after further unrelated State transitions have advanced this project's own current State
    # well past it.
    real_boot_lineage_head_ref = boot_context.current_state.get("lineage_head_ref")
    real_boot_state_transition_ref = (
        dict(real_boot_lineage_head_ref)
        if real_boot_lineage_head_ref is not None
        else {"kind": "state_transition", "id": _GENESIS_TRANSACTION_ID}
    )

    requested_source_fingerprint = url_source_fingerprint(checked_source_identity)
    boundary_fingerprint = url_boundary_fingerprint(checked_boundary)
    source_request_identity = url_source_request_identity(
        requested_source_fingerprint,
        boundary_fingerprint,
        checked_boundary["time_window"]["issued_at"],
    )

    declared_identity = getattr(adapter, "adapter_identity", None)
    if not isinstance(declared_identity, Mapping):
        raise UrlBootAdapterError(
            "adapter does not declare a readable adapter_identity attribute -- an unstated or "
            "unverifiable identity may never observe on this route's behalf"
        )

    _require_unchanged_authority_context(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        expected=authority_context,
        stage="before the adapter is reached",
    )

    fetch_result = _fetch_with_route_owned_redirects(
        adapter,
        checked_source_identity,
        checked_boundary,
        classify_resolved_address=classify_resolved_address,
    )
    fetch_outcome = fetch_result["fetch_outcome"]
    if fetch_outcome not in URL_FETCH_OUTCOMES:
        raise UrlBootAdapterError(f"unrecognized derived fetch_outcome: {fetch_outcome!r}")
    status = URL_OUTCOME_TO_RECEIPT_STATUS[fetch_outcome]
    if status not in RECEIPT_STATUSES:
        raise UrlBootAdapterError(f"unrecognized receipt status derived from outcome: {status!r}")

    if fetch_outcome != "OBSERVED":
        # P17-C7/P17-R1-F1: no failed or refused fetch ever reaches derive/commit -- purely
        # ephemeral, in-memory evidence, zero Store I/O.
        receipt = UrlSourceObservationReceipt(
            status=status,
            url_source_observation_envelope_id=None,
            project_id=project_id,
            requested_source_identity=checked_source_identity,
            boundary=checked_boundary,
            adapter_identity=dict(declared_identity),
            human_authority_ref=real_human_authority_ref,
            input_refs=(dict(real_human_authority_ref),),
            observations={
                "fetch_outcome": fetch_outcome,
                "observed_content_fingerprint": None,
                "retrieved_at": observed_at,
            },
        )
        return {"envelope": None, "receipt": receipt}

    effective_source_identity = fetch_result["effective_source_identity"]
    effective_source_fingerprint = url_source_fingerprint(effective_source_identity)
    observed_fields = _redact(
        fetch_result["observed_fields"], list(checked_boundary.get("redaction_fields", []))
    )
    observed_content_fingerprint = url_observed_content_fingerprint(observed_fields)

    envelope = derive_url_source_observation_envelope(
        project_id=project_id,
        project_binding_ref=real_project_binding_ref,
        boot_state_fingerprint=real_boot_state_fingerprint,
        boot_state_transition_ref=real_boot_state_transition_ref,
        requested_source_identity=checked_source_identity,
        requested_source_fingerprint=requested_source_fingerprint,
        effective_source_identity=effective_source_identity,
        effective_source_fingerprint=effective_source_fingerprint,
        boundary=checked_boundary,
        boundary_fingerprint=boundary_fingerprint,
        source_request_identity=source_request_identity,
        retrieved_at=observed_at,
        fetch_outcome=fetch_outcome,
        response_status=fetch_result["response_status"],
        redirect_hop_count=fetch_result["redirect_hop_count"],
        resolution_provenance=fetch_result["resolution_provenance"],
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

    receipt = UrlSourceObservationReceipt(
        status="VERIFIED",
        url_source_observation_envelope_id=envelope["url_source_observation_envelope_id"],
        project_id=project_id,
        requested_source_identity=checked_source_identity,
        boundary=checked_boundary,
        adapter_identity=dict(declared_identity),
        human_authority_ref=real_human_authority_ref,
        input_refs=(dict(real_human_authority_ref),),
        observations={
            "fetch_outcome": "OBSERVED",
            "observed_content_fingerprint": observed_content_fingerprint,
            "retrieved_at": observed_at,
        },
    )
    return {"envelope": envelope, "receipt": receipt}


def observe_url_source(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    source_identity: Mapping[str, Any],
    boundary: Mapping[str, Any],
    adapter: UrlSourceAdapter,
    observed_at: str,
) -> dict[str, Any]:
    """The one public, request-facing URL Boot entry point -- permanently, non-overridably bound
    to :func:`_require_safe_resolved_address_production` (P17-R2-F2): loopback is always
    refused, and this function's own complete parameter list -- ``store``, ``project_id``,
    ``project_binding_id``, ``source_identity``, ``boundary``, ``adapter``, ``observed_at`` --
    carries no field, keyword, or positional slot through which any caller could ever change
    that. See :func:`_observe_url_source_impl` for the complete route this delegates to
    unchanged."""

    return _observe_url_source_impl(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        source_identity=source_identity,
        boundary=boundary,
        adapter=adapter,
        observed_at=observed_at,
        classify_resolved_address=_require_safe_resolved_address_production,
    )


def observe_url_source_for_disposable_local_test(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    source_identity: Mapping[str, Any],
    boundary: Mapping[str, Any],
    adapter: UrlSourceAdapter,
    observed_at: str,
) -> dict[str, Any]:
    """The one, distinctly-named, trusted-composition-only entry point this repository's own V3
    local-HTTP vertical-proof test suite calls to observe a disposable local test target on
    loopback (Structural Review Round 2, P17-R2-F2).

    Never exported from ``url_boot/__init__.py``'s own public surface -- reachable only by
    importing this exact name directly from this module's own path
    (``manosube_agent_civilization.url_boot.route``), never through public ``observe_url_source``
    or through any value supplied to any of *its* parameters, and never through any field of
    ``boundary`` or any constructor argument of ``adapter``: neither carries, or has ever carried
    since Round 1, a loopback-permitting field or parameter of any kind. This function's own
    identical parameter list carries none either -- the loopback exception is not a parameter
    anywhere in this call graph; it is the one fact distinguishing *which function you import and
    call*, decided once, at this module's own definition time, by
    :func:`_require_safe_resolved_address_permitting_loopback_only` being the literal value
    closed over here -- never a boolean, a sentinel, a Python-private name relied on as the
    actual enforcement, or an ``isinstance`` check inspecting anything a caller supplied.

    Still refuses every address class this project's own network-safety contract refuses except
    the one loopback exception (private/link-local/multicast/reserved all remain refused
    identically to production), so even a caller who somehow reached this function cannot use it
    to reach anything beyond a disposable local test target."""

    return _observe_url_source_impl(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        source_identity=source_identity,
        boundary=boundary,
        adapter=adapter,
        observed_at=observed_at,
        classify_resolved_address=_require_safe_resolved_address_permitting_loopback_only,
    )


def _commit_envelope(
    store: Any,
    project_id: str,
    envelope: dict[str, Any],
    committed_at: str,
    *,
    project_binding_id: str,
    authority_context: Mapping[str, Any],
) -> None:
    """Durably persist *envelope* through the Store's own single sanctioned committer, bounded
    Compare-And-Swap retry against genuine, unrelated contention only -- the identical discipline
    ``runtime/route.py``'s own ``_commit_envelope`` already establishes."""

    envelope_id = envelope["url_source_observation_envelope_id"]
    if (
        url_source_observation_envelope_semantic_fingerprint(envelope)
        != envelope["url_source_observation_semantic_fingerprint"]
    ):
        raise UrlBootEnvelopeIntegrityError(
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
        transaction_id = (
            f"TX-URL-SOURCE-OBSERVATION-{envelope_id}-{current_state['state_revision']}"
        )
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
            raise UrlBootEnvelopeIntegrityError(
                f"a different record already occupies {_ENVELOPE_RECORD_KIND}/{envelope_id} "
                "with different content -- refusing rather than trust either"
            ) from error
        except StaleStateError:
            continue
    raise UrlBootRequirementError(
        f"could not durably commit {_ENVELOPE_RECORD_KIND}/{envelope_id} after "
        f"{_MAX_COMMIT_RETRIES} Compare-And-Swap retries -- sustained unrelated contention on "
        "this project's own State"
    )


__all__ = ["URL_BOOT_SCHEMA_BASE", "observe_url_source"]
