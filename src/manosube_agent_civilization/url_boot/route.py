"""The one public URL Boot route (Phase 17, Issue #69).

``URL_BOOT_OWNER_COUNT=1``, ``PUBLIC_URL_BOOT_ENTRY_POINT_COUNT=1`` (this module) ``+1``
(:mod:`~manosube_agent_civilization.url_boot.evidence_handoff`'s own single hand-off route).

The closure :func:`compose_url_source_observer` returns re-verifies Project/Human Authority
identity through the existing Boot owner (:func:`~manosube_agent_civilization.boot.boot_project`),
independently fingerprints an
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
- **P17-R2-F2 (non-substitutable loopback composition boundary), superseded in its own mechanism
  by Round 3 P17-R3-F2 below.** Round 1 moved ``permit_loopback_test_hosts`` to
  ``LocalHttpUrlSourceAdapter``'s own constructor, reasoning it was then reachable only by
  test-composition code -- Round 2 correctly identified that as merely *relocating* the identical
  caller-reachable switch one level earlier: that adapter is exported from this package's own
  public surface, so any caller able to supply the ``adapter`` argument to public
  :func:`observe_url_source` could still construct exactly that permissive object. Because
  P17-R2-F1 already moved *all* address-safety classification to this module alone, the adapter
  now carries no loopback-related parameter of any kind -- there is nothing left on it to be told
  to permit. Round 2 then bound the loopback exception to a second, distinctly-named function
  inside this module, ``observe_url_source_for_disposable_local_test``; Round 3 found that
  insufficient in turn (see P17-R3-F2 below) and removed that function -- this module's own
  :func:`_require_safe_resolved_address_permitting_loopback_only` classifier still exists, but is
  no longer bound to anything by any function defined in this module at all.
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

**Structural Review Round 3 (P17-R3-F1, P17-R3-F2), reviewed at Round 2's own corrected head and
reopening two of its three closed findings; P17-R2-F3 above is independently confirmed closed.**

- **P17-R3-F1 (route-owned connection, not merely route-owned address admission).** Round 2 moved
  address-safety classification to this module, but the actual connection was still made by the
  replaceable adapter's own ``connect_hop`` method, handed the exact admitted address and trusted
  to report which address it actually reached -- refused only when that report *disagreed* with
  what it was handed. That is an after-the-fact self-attestation, not a structural guarantee: a
  dishonest or buggy adapter implementation could connect anywhere it pleased and simply echo the
  admitted address back. :class:`~manosube_agent_civilization.url_boot.types.UrlSourceAdapter` no
  longer declares any connect-capable method at all -- ``connect_hop`` is removed from the
  Protocol entirely. The actual connection is now created and controlled exclusively by
  :func:`~manosube_agent_civilization.url_boot.network.perform_admitted_connection`, called
  *directly* by this module's own :func:`_perform_connection_via_trusted_network`, which both
  public entry points are permanently bound to. A replaceable adapter therefore has no call
  through which to substitute a different destination in either genuinely-networked path: not
  "the report is checked and refused if it disagrees" but "there is no report to check, because
  the adapter's own connect method does not exist on the Protocol, and neither public entry point
  ever asks for one". (This repository's own internal, fully deterministic route-logic test suite
  still needs *some* way to inject simulated per-hop connect facts; it reaches
  :func:`_perform_connection_via_adapter` by calling :func:`_observe_url_source_impl` directly --
  a path no production or disposable-local-test caller ever reaches.)
- **P17-R3-F2 (genuinely non-substitutable disposable-local-test composition).** Round 2 bound the
  loopback-permitting classifier inside a second, distinctly-named function in this very module,
  ``observe_url_source_for_disposable_local_test``, reasoning that omitting it from
  ``url_boot/__init__.py``'s own ``__all__`` made it unreachable. Round 3 correctly identified
  that reasoning as false: omitting a name from ``__all__`` is a documentation convention, not
  access control, and any caller able to import ``manosube_agent_civilization.url_boot.route`` --
  the identical module :func:`observe_url_source` itself lives in -- could import that exact name
  directly and reach the loopback exception with the same one-call ease public
  ``observe_url_source`` offers. That function is therefore removed outright. This module's own
  :func:`_require_safe_resolved_address_permitting_loopback_only` classifier still exists (nothing
  in this module can make a raw Python name in an importable module truly unreachable), but no
  function defined *in this module* ever binds it to anything any more. The one place it is bound
  to a request-facing operation is this repository's own trusted, non-shipped disposable-local-test
  composition, ``tests/fixtures/url_boot_local_test_authority.py`` -- a two-step factory-and-
  closure boundary, confirmed absent from the distributed wheel by ``pyproject.toml``'s own
  ``[tool.hatch.build.targets.wheel] packages`` declaration, whose own returned closure carries no
  Store/adapter/classifier parameter of any kind. See that module's own docstring for the complete
  rationale, including the disclosed limits of what a pure-Python boundary can and cannot enforce.

**Structural Review Round 4 (P17-R4-F1, P17-R4-F2), reviewed at Round 3's own corrected head and
reopening two of the two findings that head itself created (P17-R3-F1/F2, closed above, each
found to leave one further gap once acted on).**

- **P17-R4-F1 (route-owned resolution, not merely route-owned connection).** Round 3 removed
  every connect-capable method from the replaceable adapter, but left ``resolve_hop`` in place --
  a replaceable adapter's own DNS resolution still ran as arbitrary caller-supplied Python inside
  the genuine trusted pre-commit network path, with the same ambient socket/network authority as
  any other code in this process, before this route's own address-safety classification ever saw
  its result. A malicious ``resolve_hop`` could perform its own alternate-address I/O as a side
  effect regardless of what it *reported* back. :class:`~manosube_agent_civilization.url_boot.
  types.UrlSourceAdapter` no longer declares ``resolve_hop`` either -- it now declares no
  executable method of any kind, only the ``adapter_identity`` attribute. The one genuine DNS
  lookup is now created and controlled exclusively by :func:`~manosube_agent_civilization.
  url_boot.network.perform_resolution`, called *directly* by this module's own
  :func:`_perform_resolution_via_trusted_network`, which both public entry points are permanently
  bound to -- the exact mirror of P17-R3-F1's own connect-stage correction. A replaceable adapter
  therefore has no call through which to perform any network I/O at all in either genuinely-
  networked path: not "the report is checked and refused if it disagrees" but "there is no report
  to check, because neither resolve- nor connect-capable method exists on the Protocol, and
  neither public entry point ever asks for one." (This repository's own internal, fully
  deterministic route-logic test suite still needs *some* way to inject simulated resolve facts;
  it reaches :func:`_perform_resolution_via_adapter` by calling :func:`_observe_url_source_impl`
  directly -- a path no production or disposable-local-test caller ever reaches, identically to
  :func:`_perform_connection_via_adapter`.)
- **P17-R4-F2 (a genuine production composition boundary, and a non-shipped permissive
  classifier).** Round 3 required the disposable-local-test path to be a closure composed once,
  ahead of any request, over the Store/Project/Binding/adapter it is bound to -- but left public
  ``observe_url_source`` itself taking ``store``/``adapter`` directly on every call, which made
  production, not a caller who imported private names, the thing actually failing to be "a
  request-facing closure/capability composed before requests." Public ``observe_url_source`` is
  removed outright; :func:`compose_url_source_observer` is this module's sole production entry
  point, and the *only* function in this module callable with a caller-supplied Store/adapter that
  can ever reach genuine network I/O -- see its own docstring for the complete rationale. Round 4
  further found that ``route.py`` itself still shipped
  ``_require_safe_resolved_address_permitting_loopback_only``'s complete implementation, reachable
  by any caller able to import this module and recombine it with this module's own other private
  names -- omitting it from this module's own bindings (Round 3's own correction) closed *this*
  module's own ability to reach it, but not a caller's ability to import it directly and call it
  themselves. That classifier's entire body is therefore moved out of this shipped module
  entirely, into ``tests/fixtures/url_boot_local_test_authority.py`` -- this module now ships zero
  loopback-permitting classifier code of any kind, under any name. See that fixture module's own
  docstring for its own genuine, externally-held test-harness-authority requirement (never a
  naming convention, a scoping convention, or an ``isinstance`` check against a shipped class).

**Structural Review Round 5 (P17-R5-F1, P17-R5-F2), reviewed at Round 4's own corrected head and
reopening the two findings that head itself created (P17-R4-F1/F2, closed above, each found to
leave one further Python-execution-surface gap once acted on).**

- **P17-R5-F1 (genuinely inert adapter identity, not merely a method-free Protocol).** Round 4
  emptied the ``UrlSourceAdapter`` Protocol of every executable method, but
  :func:`compose_url_source_observer` still accepted an arbitrary caller-supplied *adapter*
  object and the request path still executed ``getattr(adapter, "adapter_identity", None)``
  followed by ``dict(declared_identity)`` -- a method-free Protocol constrains shape, never
  effects: a hostile ``adapter_identity`` implemented as a property/descriptor could perform its
  own network I/O from its own getter before ever returning a value, and a hostile custom
  ``Mapping`` could execute arbitrary code from its own ``__iter__``/``__getitem__``/``keys``
  during that ``dict(...)`` call. This module no longer accepts an adapter *object* at composition
  time at all: :func:`compose_url_source_observer` now takes *adapter_identity* directly, already-
  realized plain data, validated by :func:`_canonicalize_inert_adapter_identity` -- exact
  ``dict``/``list``/``str``/``int``/``float``/``bool``/``None`` types only, checked with
  ``type(x) is <builtin>`` rather than ``isinstance`` specifically so a ``dict``/``list``
  *subclass* is refused outright -- rebuilt into a genuinely fresh, frozen copy exactly once, at
  composition time, never per-request. No caller-supplied object, descriptor, property, custom
  ``Mapping``, iterator, container subclass, or callable of any kind is ever retained by, or
  executed from, the returned closure.
- **P17-R5-F2 (an externally issued local-test authority, and no shipped callable-injection
  engine).** Round 4's HMAC-based test-harness authority minted and verified from the identical
  in-module secret -- any caller able to import the composer could import the identical module's
  own mint function and produce valid authority for itself, the exact "authority relocation"
  pattern the adoption prohibits; a symmetric secret shared by issuer and verifier is not a
  genuine separation of the two roles. The disposable-local-test path now uses genuine Ed25519
  asymmetric signing (this repository's own established ``runtime/bootstrap.py`` trust-anchor
  idiom, reusing ``binding.signature.verify_ed25519_signature`` directly): the private key that
  ever mints a valid credential lives in one module,
  ``tests/fixtures/url_boot_local_test_issuer.py``; the public key that ever verifies one is a
  hardcoded literal constant in a second, genuinely separate module,
  ``tests/fixtures/url_boot_local_test_authority.py``, which imports nothing from the issuer and
  contains no mint function of its own. Separately, Round 4 left this module itself shipping a
  *generic*, callable-injecting orchestration function (the pre-Round-5
  ``_observe_url_source_impl``, accepting ``classify_resolved_address``/``perform_resolution``/
  ``perform_connection`` as ordinary parameters) -- a caller able to import that function plus this
  module's own genuine trusted-network resolver/connector could recombine them with an ordinary
  permissive ``lambda address: None`` and reconstruct the identical loopback-admitting path,
  using only shipped code. This module now ships only a fixed, non-parameterized production
  pipeline (:func:`_fetch_with_route_owned_redirects_production`,
  :func:`_observe_url_source_impl_production`) whose own classifier/resolver/connector calls are
  hardcoded, direct calls -- there is no function left in this module whose own parameter list
  accepts a classifier, resolver, or connector of any kind. The generic, dependency-injected form
  of this orchestration this repository's own internal deterministic test suite (and the
  disposable-local-test composition) still needs now lives entirely outside the shipped package,
  in ``tests/fixtures/url_boot_test_engine.py``.

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
→ route-owned, per-hop-reauthorized redirect loop -- one bounded single-hop resolution and one
  bounded single-hop connection per hop, both created and controlled exclusively by the trusted
  network layer (never any replaceable-adapter method, P17-R3-F1/P17-R4-F1), cross-hop
  DNS-resolution-drift binding, and every redirect/content/identity classification performed here
  alone
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
    perform_admitted_connection,
    perform_resolution,
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
    """The one network-address-safety classifier every closure :func:`compose_url_source_observer`
    returns is permanently, non-overridably bound to: loopback is always refused, with no
    parameter, field, or adapter substitution anywhere through which any caller could ever change
    that (P17-R2-F2). See this module's own docstring, "Structural Review Round 2 (P17-R2-F2)"."""

    require_safe_resolved_address(address, permit_loopback_test_hosts=False)


def _perform_resolution_via_trusted_network(
    current_identity: Mapping[str, Any],
) -> Mapping[str, Any]:
    """The one resolve-stage primitive :func:`_fetch_with_route_owned_redirects_production` calls
    directly -- a hardcoded call, never a function-valued parameter (Structural Review Round 5,
    P17-R5-F2). The real DNS lookup is performed entirely by
    :func:`~manosube_agent_civilization.url_boot.network.perform_resolution`, the one trusted
    network-owned primitive. There is no replaceable-adapter capability anywhere in this call at
    all any more -- no adapter argument, no resolve-capable method to delegate to."""

    return perform_resolution(dict(current_identity))


def _perform_connection_via_trusted_network(
    current_identity: Mapping[str, Any], admitted_address: str, boundary: Mapping[str, Any]
) -> Mapping[str, Any]:
    """The one connect-stage primitive :func:`_fetch_with_route_owned_redirects_production` calls
    directly -- a hardcoded call, never a function-valued parameter (Structural Review Round 5,
    P17-R5-F2). The real connection is created and controlled entirely by
    :func:`~manosube_agent_civilization.url_boot.network.perform_admitted_connection`, the one
    trusted network-owned primitive, using only the exact *admitted_address* the route itself
    already resolved and classified."""

    return perform_admitted_connection(
        dict(current_identity), admitted_address=admitted_address, boundary=dict(boundary)
    )


#: Exact built-in scalar types :func:`_canonicalize_inert_adapter_identity` ever accepts as a leaf
#: value -- deliberately checked by ``type(x) is <builtin>``, never ``isinstance`` (a ``bool`` is
#: an ``int`` subclass in Python, but ``type(True) is bool`` still distinguishes it correctly, and
#: an *attacker's* subclass of any of these -- one that overrides ``__eq__``/``__hash__``/
#: ``__repr__`` to execute code when later read, printed, or compared -- fails this same exact
#: check and is refused rather than silently accepted as "close enough").
_INERT_SCALAR_TYPES: tuple[type, ...] = (str, int, float, bool, type(None))


def _canonicalize_inert_adapter_identity(value: Any) -> dict[str, Any]:
    """Validate that *value* is genuinely closed, built-in plain data -- exact ``dict``/``list``/
    ``str``/``int``/``float``/``bool``/``None`` only, recursively -- then rebuild a genuinely
    fresh, alias-free copy from it (Structural Review Round 5, P17-R5-F1). Deliberately returns a
    plain, still-mutable ``dict`` rather than freezing it itself -- freezing (:func:`deep_freeze`)
    is each caller's own separate, explicit step, because :func:`deep_freeze` converts nested
    ``dict``/``list`` into ``MappingProxyType``/``tuple``, and *this* function's own validation
    only ever accepts exact ``dict``/``list`` -- calling it a second time on its own already-frozen
    output would spuriously refuse genuinely safe, already-validated data. Every caller that needs
    an immutable result (:func:`compose_url_source_observer` among them) freezes this function's
    own plain-dict return value itself, once, at its own composition time.

    This is this module's *only* point of contact with a caller-supplied adapter identity value.
    Every type check below is ``type(x) is <builtin>``, never ``isinstance`` -- specifically so a
    ``dict``/``list`` *subclass* (which could override ``__iter__``/``__getitem__``/``keys`` to
    execute arbitrary code the moment this function, or any later code, reads it) is refused
    outright, and so a property/descriptor never gets the chance to run in the first place: this
    function never calls ``getattr`` on *value* or any of its own nested contents at all, only
    ``type(...)`` (which never invokes user code) followed by the genuine ``dict.items()``/
    ``list`` iteration protocol on a value already confirmed to be an *exact* built-in
    ``dict``/``list``, never a caller-defined descendant of one."""

    def _canonicalize(node: Any, path: str) -> Any:
        node_type = type(node)
        if node_type in _INERT_SCALAR_TYPES:
            return node
        if node_type is dict:
            return {
                _canonicalize_key(key, path): _canonicalize(item, f"{path}.{key!r}")
                for key, item in node.items()
            }
        if node_type is list:
            return [_canonicalize(item, f"{path}[{index}]") for index, item in enumerate(node)]
        raise UrlBootRequirementError(
            f"adapter_identity{path} is not genuinely closed plain data -- exact type "
            f"{node_type!r} is not one of str/int/float/bool/None/dict/list; a Mapping "
            "subclass, iterator, descriptor, or any other caller-defined object is refused "
            "before it is ever read"
        )

    def _canonicalize_key(key: Any, path: str) -> str:
        if type(key) is not str:
            raise UrlBootRequirementError(
                f"adapter_identity{path} has a non-str key {key!r} ({type(key)!r})"
            )
        return key

    if type(value) is not dict:
        raise UrlBootRequirementError(
            f"adapter_identity must be a genuine dict, not {type(value)!r} -- an unstated or "
            "unverifiable identity may never observe on this route's behalf"
        )
    result: dict[str, Any] = _canonicalize(value, "")
    return result


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
        raise UrlBootRequirementError(
            f"the connect-stage primitive reported RESPONSE with an unreadable body: {body!r}"
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


def _fetch_with_route_owned_redirects_production(
    source_identity: Mapping[str, Any], boundary: Mapping[str, Any]
) -> dict[str, Any]:
    """Own the entire bounded, per-hop-reauthorized redirect loop (P17-R1-F2/F4, P17-R2-F1,
    P17-R3-F1/P17-R4-F1), *fixed* rather than dependency-injected (Structural Review Round 5,
    P17-R5-F2): every classifier/resolver/connector call below -- :func:`
    _require_safe_resolved_address_production`, :func:`_perform_resolution_via_trusted_network`,
    :func:`_perform_connection_via_trusted_network` -- is a direct, hardcoded call, never a
    function-valued parameter of any kind. There is no injection point here through which any
    caller, however they imported this module, could ever substitute a different classifier,
    resolver, or connector; the only way to change this function's own behavior is to edit this
    module's own source. (The pre-Round-5 design threaded caller-suppliable ``classify_resolved_
    address``/``perform_resolution``/``perform_connection`` callables through a single generic
    engine reused by production, the disposable-local-test path, and this repository's own
    internal deterministic test suite alike -- a caller able to import that generic engine plus
    this module's own genuine trusted network primitives could recombine them with an ordinary
    permissive lambda and reconstruct the exact loopback-admitting path this module's own
    production classifier alone was supposed to close. The generic, parameterized form of this
    loop now lives entirely outside the shipped package, in this repository's own non-shipped
    ``tests/fixtures/url_boot_test_engine.py`` -- see that module's own docstring.)

    Returns ``{"fetch_outcome", "effective_source_identity", "response_status",
    "redirect_hop_count", "observed_fields", "resolution_provenance"}`` -- the identical shape
    :func:`_observe_url_source_impl_production` derives an Envelope from (``fetch_outcome ==
    "OBSERVED"``) or returns as a bounded, ephemeral failure receipt (anything else).
    """

    network_scope = boundary["network_scope"]
    max_redirects = boundary["redirect_policy"]["max_redirects"]
    current_identity = dict(source_identity)
    resolution_bindings: dict[tuple[str, int], str] = {}
    resolution_provenance: list[dict[str, Any]] = []

    for hop in range(max_redirects + 1):
        resolve_raw = _perform_resolution_via_trusted_network(current_identity)
        if not isinstance(resolve_raw, Mapping):
            raise UrlBootRequirementError(
                f"the resolve-stage primitive returned {resolve_raw!r}, not a mapping"
            )
        resolve_outcome = resolve_raw.get("outcome")
        if resolve_outcome not in URL_HOP_RESOLVE_OUTCOMES:
            raise UrlBootRequirementError(
                f"the resolve-stage primitive's own outcome is not recognized: {resolve_outcome!r}"
            )
        if resolve_outcome == "DNS_FAILURE":
            return _hop_result("DNS_FAILURE", redirect_hop_count=hop)

        candidate_address = resolve_raw.get("resolved_address")
        if not isinstance(candidate_address, str) or not candidate_address:
            raise UrlBootRequirementError(
                "the resolve-stage primitive reported RESOLVED with no readable resolved_address"
            )

        # P17-R2-F1: the route alone classifies the resolved address's own safety -- a hardcoded
        # call, never a parameter (P17-R5-F2).
        try:
            _require_safe_resolved_address_production(candidate_address)
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

        # P17-R3-F1: the actual connection is created and controlled by a hardcoded call to the
        # trusted network layer alone -- never a parameter (P17-R5-F2).
        admitted_address = candidate_address
        connect_raw = _perform_connection_via_trusted_network(
            current_identity, admitted_address, boundary
        )
        if not isinstance(connect_raw, Mapping):
            raise UrlBootRequirementError(
                f"the connect-stage primitive returned {connect_raw!r}, not a mapping"
            )
        connect_outcome = connect_raw.get("outcome")
        if connect_outcome not in URL_HOP_CONNECT_OUTCOMES:
            raise UrlBootRequirementError(
                f"the connect-stage primitive's own outcome is not recognized: {connect_outcome!r}"
            )
        if connect_outcome in _HOP_CONNECT_FAILURE_OUTCOMES:
            return _hop_result(connect_outcome, redirect_hop_count=hop)

        # Defense in depth: the exact address actually connected to must equal the exact address
        # this route admitted -- holds by construction for the trusted network connector, retained
        # as an explicit, independently checked invariant rather than an assumption.
        if connect_raw.get("resolved_address") != admitted_address:
            raise UrlBootRequirementError(
                "the connect-stage primitive reported a resolved_address that does not equal "
                f"the exact address this route admitted for this hop: "
                f"{connect_raw.get('resolved_address')!r} != {admitted_address!r}"
            )

        raw = connect_raw
        status = raw.get("response_status")
        if not isinstance(status, int):
            raise UrlBootRequirementError(
                "the connect-stage primitive reported RESPONSE with an unreadable "
                f"response_status: {status!r}"
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


def _observe_url_source_impl_production(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    source_identity: Mapping[str, Any],
    boundary: Mapping[str, Any],
    adapter_identity: Mapping[str, Any],
    observed_at: str,
) -> dict[str, Any]:
    """The complete, fixed production observation implementation (Structural Review Round 5,
    P17-R5-F1/F2, Issue #69).

    Unlike every earlier round's version of this function, this one accepts no callable of any
    kind -- no classifier, resolver, or connector parameter exists on this signature at all. Every
    such decision is hardcoded inside :func:`_fetch_with_route_owned_redirects_production`, which
    this function calls unconditionally. There is no shipped surface, here or anywhere else in
    this module, through which a caller could substitute a different resolve/connect/classify
    mechanism -- the P17-R5-F2 requirement that shipped execution stay production-fixed.

    *adapter_identity* is not an adapter object. It is already-realized, already-canonicalized
    plain data -- the frozen result :func:`compose_url_source_observer` produced once, at
    composition time, by calling :func:`_canonicalize_inert_adapter_identity` on whatever value
    its own caller supplied. This function performs no attribute access on it (no ``getattr``, no
    ``.get`` beyond ordinary ``Mapping`` reads already proven safe by that canonicalization), and
    calls no method on it, because it never held a method to call in the first place
    (P17-R5-F1) -- the entire class of hostile-adapter-object risk (a property that raises or
    mutates State on read, a custom ``Mapping``/iterator/``dict`` subclass whose protocol methods
    execute arbitrary code, a callable masquerading as inert data) cannot reach this function at
    all, because nothing but the closed set of builtin scalar/container types the canonicalizer
    accepts ever survives to be passed in here.

    This repository's own internal deterministic route-logic test suite and disposable-local-test
    composition (``tests/fixtures/url_boot_test_engine.py``,
    ``tests/fixtures/url_boot_local_test_authority.py``) do not call this function -- they retain
    their own genuinely generic, dependency-injected sibling
    (``url_boot_test_engine.observe_url_source_for_internal_testing``), which lives entirely
    outside this package's own shipped surface.

    This function itself is never exported from this package's own public surface.

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

    _require_unchanged_authority_context(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        expected=authority_context,
        stage="before the adapter is reached",
    )

    fetch_result = _fetch_with_route_owned_redirects_production(
        checked_source_identity,
        checked_boundary,
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
            adapter_identity=adapter_identity,
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
        adapter_identity=dict(adapter_identity),
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
        adapter_identity=adapter_identity,
        human_authority_ref=real_human_authority_ref,
        input_refs=(dict(real_human_authority_ref),),
        observations={
            "fetch_outcome": "OBSERVED",
            "observed_content_fingerprint": observed_content_fingerprint,
            "retrieved_at": observed_at,
        },
    )
    return {"envelope": envelope, "receipt": receipt}


def compose_url_source_observer(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    adapter_identity: Any,
) -> Callable[[Mapping[str, Any], Mapping[str, Any], str], dict[str, Any]]:
    """The one public, trusted composition step for a genuinely-networked URL Boot observation
    (Structural Review Round 4, P17-R4-F2; Round 5, P17-R5-F1/F2).

    **Why this exists, replacing what used to be a single request-facing ``observe_url_source``
    function.** Round 3 already established that this package's disposable-local-test path must
    be a closure composed once, ahead of any request, over the Store/Project/Binding/adapter it is
    bound to -- never a plain function a request-facing caller invokes directly with those values
    as arguments. Round 4 found that this package's own *production* path had never been held to
    the identical discipline: public ``observe_url_source`` itself took ``store``/``adapter``
    (among others) directly, on every call, which made it -- not a caller who imported private
    names -- the thing actually failing to be "a request-facing closure/capability composed before
    requests" the adopted contract requires. This function is that composition step. It binds
    *store*, *project_id*, *project_binding_id*, and *adapter_identity* -- once -- and returns the
    request-facing observation operation itself, already closed over all four plus the production
    classifier (:func:`_require_safe_resolved_address_production`, loopback always refused,
    P17-R2-F2) and the trusted network resolver/connector
    (:func:`_perform_resolution_via_trusted_network`, :func:`_perform_connection_via_trusted_network`
    -- real resolution and connection are created and controlled entirely by the trusted network
    layer, never by an adapter object, P17-R3-F1/P17-R4-F1). Those two primitives, and the
    classifier, are no longer even parameters here (Round 5) -- :func:`_observe_url_source_impl_
    production` and :func:`_fetch_with_route_owned_redirects_production` call them directly by
    name, so there is no callable of any kind for this function's own body to thread through.

    **Round 5 (P17-R5-F1):** *adapter_identity* is no longer an adapter object at all -- Round 4
    still accepted one and read its own ``adapter_identity`` attribute via ``getattr`` on every
    request. Structural Review Round 5 found that this let a hostile caller-supplied object (a
    property that raises or mutates State on read, a custom ``Mapping``/iterator/``dict``
    subclass whose protocol methods execute arbitrary code on any attribute or item access) reach
    this route's own trusted composition boundary and execute during every single request, not
    merely once. This function now accepts *adapter_identity* as already-realized data of any
    shape a caller happens to hand it, and immediately canonicalizes it exactly once, here, via
    :func:`_canonicalize_inert_adapter_identity` -- a strict recursive validator that accepts only
    the closed set of builtin scalar/container types (``str``, ``int``, ``float``, ``bool``,
    ``None``, ``dict``, ``list``, checked by exact ``type(x) is ...`` identity rather than
    ``isinstance`` so that a hostile ``dict``/``list`` subclass is refused rather than silently
    accepted) and rebuilds a genuinely fresh, frozen structure from it, touching no attribute,
    property, or protocol method the input might have defined. The frozen result is captured once
    in this closure and reused, unchanged, for every request the returned closure ever serves --
    there is no per-request re-canonicalization, and no path back to the original caller-supplied
    value at all once this function returns.

    The returned closure's own call signature is exactly ``(source_identity, boundary,
    observed_at)`` -- the identical shape :func:`~manosube_agent_civilization.url_boot.
    route.compose_url_source_observer`'s own disposable-local-test counterpart already returns
    (see ``tests/fixtures/url_boot_local_test_authority.py``'s own module docstring). No Store, no
    adapter identity, no classifier, no resolver, no connector, no policy flag, and no
    alternate-world substitution input of any kind -- there is no keyword, no positional slot, and
    no attribute on the returned callable through which a caller could substitute a different
    Store, adapter identity, or trusted primitive after the fact. This function's own parameter
    list -- ``store``, ``project_id``, ``project_binding_id``, ``adapter_identity`` -- likewise
    carries no field, keyword, or positional slot through which any caller could ever inject an
    alternate classifier, resolver, or connector at composition time either.

    See :func:`_observe_url_source_impl_production` for the complete route the returned closure
    delegates to unchanged."""

    canonical_adapter_identity = deep_freeze(_canonicalize_inert_adapter_identity(adapter_identity))

    def observe(
        source_identity: Mapping[str, Any], boundary: Mapping[str, Any], observed_at: str
    ) -> dict[str, Any]:
        return _observe_url_source_impl_production(
            store,
            project_id=project_id,
            project_binding_id=project_binding_id,
            source_identity=source_identity,
            boundary=boundary,
            adapter_identity=canonical_adapter_identity,
            observed_at=observed_at,
        )

    return observe


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


__all__ = ["URL_BOOT_SCHEMA_BASE", "compose_url_source_observer"]
