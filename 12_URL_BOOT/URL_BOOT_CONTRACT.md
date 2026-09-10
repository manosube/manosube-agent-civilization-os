# Read-only URL Boot and Untrusted Content Boundary Contract (Phase 17, Issue #69)

```text
DOC_TYPE=URL_BOOT_CONTRACT
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=URL-BOOT-CONTRACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_URL_BOOT_ADAPTER
URL_BOOT_OWNER_COUNT=1
PUBLIC_URL_BOOT_ENTRY_POINT_COUNT=2
SIGNED_DEPLOYMENT_DECLARATION_CHAIN=false
DNS_REBINDING_PROTECTION=true
PER_HOP_REDIRECT_REAUTHORIZATION=true
CREDENTIAL_TRANSMISSION_PERMITTED=false
ROUTE_OWNED_REDIRECT_AND_CONTENT_CLASSIFICATION=true
ROUTE_OWNED_NETWORK_ADDRESS_ADMISSION=true
CROSS_HOP_RESOLUTION_DRIFT_BINDING=true
LOOPBACK_TEST_ALLOWANCE_DATA_DRIVEN=false
LOOPBACK_TEST_ALLOWANCE_ADAPTER_CONSTRUCTOR_ARGUMENT=false
BOOT_CONTEXT_INDEPENDENTLY_REVERIFIED_AT_HANDOFF=true
STRUCTURAL_REVIEW_ROUNDS_APPLIED=5
```

## 1. Position

This layer lets a URL be used as a bounded, read-only external observation source: a
deterministic URL Source Observation Envelope binding an explicit, requested source identity
and a closed fetch Boundary to what a real, bounded HTTP GET against it actually returned,
through a replaceable `UrlSourceAdapter`. It is **not** a ninth Kernel element (the Kernel is
fixed at eight: `KERNEL_ELEMENT_COUNT=8`, `ONE_KERNEL_ELEMENT_PER_PACKAGE=true`) -- an adapter
layer, exactly as Boot, CLI, Agent Runtime, Independent Verification, Projection, Runtime, and
Model Runtime already are. Fetched content is never a canonical source of State, Difference,
Change, Authority, Evidence, or a model invocation here -- it is an external, untrusted world
this layer observes under an explicit closed Boundary and hands off, unchanged, to the existing
Evidence owner (P17-C4).

```text
URL_BOOT_OWNER_COUNT=1
PUBLIC_URL_BOOT_ENTRY_POINT_COUNT=2
```

## 2. Public signature

Since Structural Review Round 4 (P17-R4-F2, §12.2), public `observe_url_source` is replaced by a
two-step trusted composition: `compose_url_source_observer` binds Store/Project/Binding/adapter
identity *once* and returns the request-facing observation closure itself, whose own call
signature carries only request data. Since Structural Review Round 5 (P17-R5-F1, §13.1),
composition takes *adapter_identity* -- already-realized plain data -- directly, never an adapter
*object*: there is no replaceable adapter boundary of any kind on production's own request path
any more, only inert configuration.

```python
observe = compose_url_source_observer(
    store,
    project_id=project_id,
    project_binding_id=project_binding_id,
    adapter_identity={"adapter": "my_url_source_adapter", "version": "0.1"},  # plain data only
)
result = observe(
    network.canonical_source_identity("https://example.org/status"),
    {
        "fetch_method": "HTTP_GET_BOUNDED",
        "network_scope": {
            "admitted_schemes": ["https"],
            "admitted_hosts": ["example.org"],
            "admitted_ports": [443],
        },
        "redirect_policy": {"max_redirects": 3},
        "timeout_seconds": 5,
        "max_response_bytes": 65536,
        "admitted_content_types": ["application/json"],
        "permitted_fields": ["status"],
        "time_window": {"issued_at": "...", "expires_at": "..."},
        "redaction_fields": [],
        "credentials_permitted": False,
    },
    "2026-09-10T00:00:01Z",
)
result["envelope"]  # the canonical, committed Envelope, or None (P17-C7/P17-R1-F1: only ever
                     # non-None when fetch_outcome == "OBSERVED" -- see §5)
result["receipt"]   # UrlSourceObservationReceipt (ephemeral, never committed itself)

evidence = route_url_observation_to_evidence(store, result["receipt"], project_id, request)
```

`network_scope` carries no `permit_loopback_test_hosts` field (Structural Review Round 1,
P17-R1-F3), and no adapter constructor carries one either any more (Structural Review Round 2,
P17-R2-F2, §10.2): the loopback exception is reachable only through this repository's own trusted,
non-shipped disposable-local-test composition (§11.2, further hardened by §12.2) -- never through
any field or parameter reachable from `compose_url_source_observer` or its returned closure.

## 3. Frozen semantic decisions

1. **Read-only, no create-once-reuse-after side effect -- and no State mutation at all unless the
   fetch genuinely succeeded (Structural Review Round 1, P17-R1-F1).** Unlike Projection, this
   layer derives no intent/materialize-attempt claim pair -- observing the identical source under
   the identical Boundary twice is two independent facts about the world at two different
   instants, not a duplicate external artifact. The closure `compose_url_source_observer` returns
   commits exactly one new Envelope **only** when `fetch_outcome == "OBSERVED"`; every other
   outcome (all ten typed
   failures) returns a bounded, purely ephemeral `UrlSourceObservationReceipt`
   (`url_source_observation_envelope_id=None`) with zero canonical State mutation and zero Store
   I/O of any kind -- `engine.py`'s own deriver refuses to be called for any other outcome, so
   this holds structurally, not merely by the route's own discipline (§5, §6.5).
2. **Deliberately simpler authority model than Runtime (disclosed, not a gap).** Runtime
   additionally resolves, authority-binds, and cryptographically verifies a Store-committed
   `runtime_deployment_declaration` before trusting a target's own claimed identity, because a
   runtime target is a live, potentially adversarial system a caller could otherwise impersonate
   by mere assertion. A URL source makes no equivalent trust claim about fetched content at all
   -- `SIGNED_DEPLOYMENT_DECLARATION_CHAIN=false`. What this layer verifies is Project/Human
   Authority freshness and network-scope containment; it never verifies that a URL "is" any
   particular deployment.
3. **Deliberately stronger network-safety layer than Runtime (disclosed departure, §6.1).**
   Runtime's own `network.py` is pure and I/O-free, and refuses every redirect outright rather
   than validating one. This package performs genuine per-hop redirect reauthorization
   (`PER_HOP_REDIRECT_REAUTHORIZATION=true`) and closes the DNS-rebinding time-of-check/
   time-of-use window (`DNS_REBINDING_PROTECTION=true`), which requires real, bounded DNS
   resolution -- something Phase 15 explicitly declined to do.
4. **Route-owned redirect/content/identity classification (Structural Review Round 1,
   P17-R1-F2, superseding this delivery's own first design).** This package's first delivery gave
   the adapter one `fetch()` method that followed an entire redirect chain internally and
   reported only a final identity/hop-count/outcome, trusting that report directly -- a
   conforming-looking but dishonest adapter could therefore follow a disallowed intermediate hop,
   fabricate a hop count, or simply assert `IDENTITY_MISMATCH`/`BOUNDARY_REFUSED` outright, with
   no way for the route to catch it. The replaceable `UrlSourceAdapter` now exposes exactly one
   bounded, single-hop transport primitive (`fetch_one_hop`); the route itself owns the entire
   redirect loop, re-authorizing every redirect target against `network_scope` **before** ever
   calling the adapter for it, and performs every content-type/size/JSON/`IDENTITY_MISMATCH`
   classification itself, from the adapter's bounded per-hop facts alone (§5, §6.5). This is not
   a relaxation of P17-C4's own "fetched content is never meaningful on its own" rule -- content
   classification still never mints Authority, invokes a model, or executes a Change; it is only
   the *owner* of that classification that moved, from a replaceable adapter to this route.
5. **Every reference is resolved, schema-validated, identity-recomputed and re-bound on every
   call.** A Store-resolved record is never trusted on shape alone, and never trusted at all
   until its own recomputed identity and semantic fingerprint equal its own declared values --
   the three-way check (Store lookup key / declared identity / recomputed identity) applied from
   this package's own first delivery, the lesson Phase 16 Structural Review Round 2 (P16-R2-F1)
   had to add after the fact for `model_runtime`.
6. **Credentials are never transmitted.** `boundary.credentials_permitted` is schema-fixed to
   `false` (`CREDENTIAL_TRANSMISSION_PERMITTED=false`); a userinfo-bearing URL is refused before
   any resolution is attempted.
7. **This route reads no clock.** Every instant is a required, caller-supplied, canonically
   validated timestamp -- the identical discipline every other route in this repository keeps.
8. **One sanctioned committer, one Evidence deriver.** `commit_state_transition` and
   `derive_evidence` each have exactly one call site, in exactly one module. This layer never
   imports `authority`, `change`, `reflow`, `model_runtime`, `agent_runtime`, `projection`, or
   `independent_verification`.

## 4. Canonical owner

```text
url_boot/route.py             the one public observation route, the one Boot call site, the
                               one sanctioned commit
url_boot/evidence_handoff.py  the one Evidence hand-off (the one derive_evidence call)
url_boot/engine.py            pure derivation and schema validation; no I/O of any kind
url_boot/identity.py          four content-addressed identities
url_boot/types.py             closed vocabularies, the UrlSourceAdapter Protocol, the receipt
url_boot/adapter.py           the two controlled adapters
url_boot/network.py           URL parsing, network-scope enforcement, and the one safe
                               single-hop HTTP fetch primitive -- the only module in this
                               package permitted to open a socket
url_boot/errors.py            the typed refusal vocabulary
```

### 4.1 Canonical records

```text
url_source_observation_envelope   The committed URL Source Observation -- the only record kind
                                   this package produces, and only ever for fetch_outcome ==
                                   "OBSERVED" (P17-C7/P17-R1-F1). Carries project_binding_ref,
                                   boot_state_fingerprint, and boot_state_transition_ref (the
                                   exact Boot-observed context, P17-R1-F5, independently
                                   re-resolved and re-verified at Evidence handoff, P17-R2-F3)
                                   and resolution_provenance (the ordered, per-
                                   (host, port) DNS resolution this route admitted across every
                                   hop, P17-R1-F4) -- all identity-sensitive.
```

There is no Human-declared deployment-identity record in this package (contrast §3.2): the
closed fetch Boundary is the only Human-declared input, and it is a caller-supplied, schema-
validated argument, never a Store-resolved record of its own.

## 5. Canonical route

```text
complete schema validation of the declared source identity and closed fetch Boundary
→ network-scope check on the requested source -- zero-call, before Boot or any adapter
→ real-instant time-window check -- refuses before any adapter call
→ real Project/Human Authority (Boot re-verification) -- captures project_binding_ref,
  boot_state_fingerprint, and boot_state_transition_ref, the exact Boot-observed context
  (P17-R1-F5), independently re-resolved and re-verified at Evidence handoff (P17-R2-F3)
→ explicit source identity, fingerprinted (never trusted from a caller)
→ closed fetch Boundary, fingerprinted (never trusted from a caller)
→ deterministic source_request_identity (source + Boundary + issued_at) -- computable before
  the adapter is ever called
→ authority-freshness re-check -- refuses before the adapter
→ route-owned, per-hop-reauthorized redirect loop (P17-R1-F2/F4, Structural Review Round 2
  P17-R2-F1): one bounded resolve-stage call per hop, reporting only a genuine DNS_FAILURE or a
  RESOLVED address -- never a safety verdict -- created and controlled since Structural Review
  Round 4 (P17-R4-F1) by the trusted network layer itself (network.perform_resolution), never the
  replaceable adapter; the route alone then classifies that resolved address's own safety
  (network.require_safe_resolved_address) and binds it to its own (host, port) for the lifetime
  of this one fetch, refusing as BOUNDARY_REFUSED before any connection is attempted, either for
  an unsafe address or for a later hop resolving the identical (host, port) to a different
  address; only once the route has admitted an address does it invoke its own permanently-bound
  connection primitive with that exact admitted_address -- since Structural Review Round 3
  (P17-R3-F1), the trusted network layer itself creates and controls this connection
  (network.perform_admitted_connection), never the replaceable adapter, and the route itself
  verifies whatever the connection primitive reports names that same address back (else
  UrlBootRequirementError -- the connection would otherwise have reached somewhere else, see
  §11.1); before following a redirect the route itself also re-validates the target's hostname
  against network_scope; every content-type/size/JSON/IDENTITY_MISMATCH classification is
  performed here, from the connection primitive's bounded per-hop facts alone (see §10.1, §11.1,
  §12.1)
→ fetch_outcome != "OBSERVED": bounded, ephemeral, non-committed URL Source Observation
  Receipt -- zero State mutation, zero commit, zero Evidence-handoff eligibility (P17-C7/
  P17-R1-F1)
→ fetch_outcome == "OBSERVED" only: field-boundary projection + redaction, canonical URL Source
  Observation Envelope (binding project_binding_ref/boot_state_fingerprint/
  boot_state_transition_ref/resolution_provenance), authority-freshness re-check on every commit
  attempt, existing canonical persistence boundary (commit_state_transition), VERIFIED Receipt →
  existing Evidence owner, which independently re-resolves and re-verifies the referenced
  Project Binding and Boot state transition before any Evidence is derived (P17-R2-F3, §10.3)
```

### 5.1 The resolve-once-connect-to-that-address technique, route-owned since Structural Review Round 2 (P17-C5, P17-R2-F1), connection itself route-owned since Structural Review Round 3 (P17-R3-F1), resolution itself route-owned since Structural Review Round 4 (P17-R4-F1)

Neither resolution nor connection is an adapter primitive at all any more. Since Structural
Review Round 4 (P17-R4-F1, §12.1), `network.perform_resolution` -- called by the route itself,
never the replaceable adapter -- resolves a hop's host exactly once through a single
`network.resolve_hop_address`/`socket.getaddrinfo` call and returns the address alone; it
classifies nothing. `network.require_safe_resolved_address`, called by the route itself on that
resolved address, refuses loopback/private/link-local/multicast/reserved/unspecified addresses
unless the route's own caller is the distinctly-named `_require_safe_resolved_address_permitting_loopback_only`
classifier, which since Round 4 is no longer even defined inside this shipped package (§12.2) --
it lives entirely in this repository's own trusted, non-shipped test composition boundary (§11.2,
§12.2). Only once the route has admitted an address does it invoke
`network.perform_admitted_connection` (P17-R3-F1) -- the trusted network layer's own connection
primitive, called by the route itself, never by the replaceable adapter -- which wraps
`network.connect_and_request_hop` to connect a raw `http.client.HTTPConnection` **directly to
that route-admitted address**, wrapping TLS exactly once, against the real hostname, when the
scheme is `https` -- never re-resolving the hostname at connection time, which is exactly the
resolve-then-reconnect race a naive `urllib`-based fetcher would leave open. The original
hostname is still sent as the `Host` header (including a non-default port) and, over HTTPS, as
the TLS SNI/certificate verification name. See §10.1 for the rationale for splitting resolution
and connection into two stages, §11.1 for why the connection stage itself is no longer
adapter-reportable in production, and §12.1 for why the resolve stage no longer is either.

### 5.2 Route-owned per-hop redirect reauthorization and cross-hop resolution-drift binding (P17-C5, Structural Review Round 1 P17-R1-F2/F4, Structural Review Round 2 P17-R2-F1)

The route -- never the replaceable adapter -- owns the entire redirect loop. Before calling its
own resolution/connection primitives for a redirect target, the route itself re-validates
that target's hostname against the Boundary's own `network_scope`
(`network.canonical_source_identity` + `network.require_source_within_network_scope`), bounded
at `boundary.redirect_policy.max_redirects` hops; a redirect naming a host outside scope, or one
exceeding the hop bound, refuses as `REDIRECT_REFUSED` -- never silently followed, and the
disallowed hop's own resolution/connection calls are never even reached (§6.5). The route
additionally binds each hop's own resolved address to its own `(host, port)` for the lifetime of
one fetch, checked immediately after resolution returns and before any connection is ever
attempted: a same-host redirect whose second hop resolves to a genuinely different public address
than its first refuses as `BOUNDARY_REFUSED` (§6.6) -- resolve-once-connect-to-that-address alone
closes only the single-hop DNS time-of-check/time-of-use window; this closes the cross-hop one.
The route also verifies, after every connection attempt, that the report names back the exact
`admitted_address` it was handed -- since Structural Review Round 3 (P17-R3-F1), this connection
is created by the trusted network layer itself, so this check now guards against a defect in
that trusted layer rather than a hostile adapter; a mismatch raises `UrlBootRequirementError`
rather than being trusted (§11.1).

## 6. Disclosed judgment calls

### 6.1 A genuinely impure `network.py`, and why

Runtime's own `network.py` is pure and I/O-free by design: Phase 15 explicitly declined to
resolve DNS at all, and refused every redirect outright rather than validating one. Phase 17's
own adopted contract requires the opposite -- genuine per-hop redirect reauthorization and
DNS-rebinding protection, which cannot be expressed correctly from outside the socket-opening
call. `network.py` is therefore the one module in this package permitted to import
`socket`/`http.client`/`ssl`/`ipaddress`. Since Structural Review Round 3 (P17-R3-F1), `adapter.py`
no longer imported `ssl` at all, because it no longer connected to anything; since Structural
Review Round 4 (P17-R4-F1, §12.1), it imports no network-opening surface at all any more --
`LocalHttpUrlSourceAdapter` is pure inert identity data, carrying no method of any kind, and its
own resolution/connection are performed exclusively by `network.py`, called directly by the
route. It opens no socket and wraps no TLS itself, proved by
`tests/contract/url_boot/test_url_boot_static_conformance.py`.

### 6.2 The closed eleven-member outcome vocabulary (P17-C7), and the two smaller per-hop vocabularies beneath it (P17-R1-F2, Structural Review Round 2 P17-R2-F1)

`URL_FETCH_OUTCOMES` was chosen to map one-to-one onto every outcome the adopted contract text
names by name: `OBSERVED`, `DNS_FAILURE`, `CONNECTION_FAILURE`, `TLS_FAILURE`, `TIMEOUT`,
`REDIRECT_REFUSED`, `OVERSIZED_RESPONSE`, `UNSUPPORTED_MEDIA_TYPE`, `MALFORMED`,
`IDENTITY_MISMATCH`, `BOUNDARY_REFUSED`. A complete, readable HTTP response whose status falls
outside 2xx/3xx has no member of its own in that list; the route itself classifies it as
`MALFORMED` (the response failed to honestly answer the bounded question asked), carrying the
real `response_status` alongside it so nothing about the real status code is lost. This is a
disclosed narrowing, not a silent one.

Since Structural Review Round 1, this eleven-member vocabulary is no longer what an adapter
itself ever reports. Since Structural Review Round 2, it is also no longer a single per-hop
vocabulary: `URL_HOP_RESOLVE_OUTCOMES` (`DNS_FAILURE`, `RESOLVED`) is the complete, closed
vocabulary the route's own resolve-stage primitive may return (since Structural Review Round 4,
P17-R4-F1, `network.perform_resolution` alone -- no longer a `resolve_hop` method any adapter
implementation could ever be asked to satisfy, §12.1), and `URL_HOP_CONNECT_OUTCOMES`
(`CONNECTION_FAILURE`, `TLS_FAILURE`, `TIMEOUT`, `RESPONSE`) is the complete, closed vocabulary
the route's own connection primitive may return -- `BOUNDARY_REFUSED` is a member of neither: it
is purely route-derived, from the route's own classification of a resolve-stage-reported address
and its own cross-hop resolution-drift check, never an outcome any adapter or connector may
assert (see §10.1, §11.1, and §12.1 for the full rationale). `REDIRECT_REFUSED`,
`OVERSIZED_RESPONSE`, `UNSUPPORTED_MEDIA_TYPE`, `MALFORMED`, `IDENTITY_MISMATCH`,
`BOUNDARY_REFUSED`, and `OBSERVED` are all route-*derived* classifications; since Structural
Review Round 4, a resolve-stage report that fails these checks is a `UrlBootRequirementError`
(mirroring Round 3's identical change for the connect stage below), because production's resolver
is the trusted network layer itself, not necessarily an "adapter" fault -- this repository's own
internal deterministic test composition (§11.1, §12.1) still exercises the identical checks by
delegating to a `resolve_hop`/`connect_hop`-bearing test double, so the checks themselves are
unchanged, only which exception class reports a production-path failure.

### 6.3 `project_binding_ref` and `human_authority_ref` are both the Evidence target's identity (superseded, Structural Review Round 1 P17-R1-F5)

This delivery's first version disclosed that `source_identity` carries no `project_binding_ref`
field the way Runtime's own `target_identity` does, and used `human_authority_ref` alone as the
Evidence hand-off's `target_refs`/`input_refs`. Structural Review Round 1 found this
insufficient on its own: two different Boot contexts sharing the same Human Authority produced
indistinguishable provenance. The committed Envelope now also carries `project_binding_ref` and
`boot_state_fingerprint` -- the exact Project Binding identity and Boot-observed State
fingerprint this call's own Boot restored, both fully identity-sensitive
(`ENVELOPE_SEMANTIC_FIELDS`) -- and `evidence_handoff.py` exposes both inside the constructed
`verification_result_provenance.verification_boundary`. `human_authority_ref` remains the one
reference actually placed in `target_refs`/`input_refs` (§6.3's own original judgment call still
holds for *that* field: a URL Source Observation has no separate canonical Difference/Change/
Evidence subject the way a Projection does); `project_binding_ref`/`boot_state_fingerprint` are
the additional, identity-sensitive exact-context binding P17-R1-F5 requires, integrity-checked
by the identical resolve-and-recompute discipline every other Envelope field already relies on
(§3.5) -- there is no second, separate check to add.

### 6.4 Redaction, bounded to permitted_fields, before any fingerprint

`_classify_terminal_response` in `route.py` builds `observed_fields` directly bounded to
`boundary.permitted_fields` while parsing a genuinely reached response's own JSON body -- a
field the response carries that `permitted_fields` never named is never even placed in the
dict, by construction, rather than placed and then refused. `_redact` then runs over that
already-bounded projection before `observed_content_fingerprint` is ever computed -- the
identical "bound, then redact, then fingerprint" order Runtime's own P15-R1-F3 correction
established, applied here directly at the one place (the route's own response classification)
that now builds `observed_fields` at all.

### 6.5 The loopback test allowance is a Python composition-time decision, never Boundary data (Structural Review Round 1 P17-R1-F3, superseded by Structural Review Round 2 P17-R2-F2 -- see §10.2 -- further superseded by Structural Review Round 3 P17-R3-F2 -- see §11.2 -- further superseded by Structural Review Round 4 P17-R4-F2 -- see §12.2)

This delivery's first version read `permit_loopback_test_hosts` out of the caller-supplied,
request-facing `boundary` data itself. That field no longer exists anywhere in the closed
Boundary schema (`network_scope`'s own `additionalProperties: false` refuses a caller who still
tries). Round 1 then moved this allowance to a concrete adapter's own constructor --
`LocalHttpUrlSourceAdapter(permit_loopback_test_hosts=True)` -- reasoning it was then only
reachable by test-composition code. Structural Review Round 2 correctly identified that
reasoning as merely relocating the same caller-reachable switch one level earlier:
`LocalHttpUrlSourceAdapter` is exported from this package's own public surface, so any caller
able to supply the `adapter` argument to public `observe_url_source` could still construct that
object with `permit_loopback_test_hosts=True`. `LocalHttpUrlSourceAdapter` now carries **no**
loopback-permitting parameter of any kind -- it no longer classifies a resolved address's own
safety at all (P17-R2-F1 already moved that decision to the route). The loopback decision now
lives exclusively in `route.py`'s own closed, non-substitutable composition boundary: two
permanently-bound classifier functions, reachable only through which of two distinctly-named
public entry points (`observe_url_source` vs. `observe_url_source_for_disposable_local_test`) a
caller imports and calls -- never a parameter, keyword, or sentinel value crossing either
function's own signature. See §10.2 for the full mechanism and rationale.

### 6.6 Route-owned redirect classification and cross-hop resolution-drift binding (Structural Review Round 1, P17-R1-F2/F4)

See §5.2 for the mechanism. The judgment call worth stating explicitly: this package's first
delivery trusted a replaceable adapter's own report of the *final* identity/hop-count/outcome
after it had already followed an entire redirect chain internally -- a conforming-looking but
dishonest adapter could follow a disallowed intermediate hop, fabricate a hop count, or assert
`IDENTITY_MISMATCH`/`BOUNDARY_REFUSED` directly, with nothing left for the route to check. Moving
the redirect loop, per-hop resolution-drift binding, and all content classification into the
route itself closes this by construction, not merely by adding more checks against the old
design: there is no field left in an adapter's own single-hop report through which a hidden hop,
a fabricated count, or an asserted classification could ever reach this route.

### 6.7 Zero canonical State mutation for a non-`OBSERVED` outcome is structural, not merely disciplined (Structural Review Round 1, P17-R1-F1)

This delivery's first version derived and committed an Envelope for every one of the eleven
outcomes, including every typed failure -- directly contradicting P17-C7's own "no failed or
refused fetch may mutate canonical State." `engine.py`'s own
`derive_url_source_observation_envelope` now refuses, itself, to be called for any
`fetch_outcome` other than `"OBSERVED"` (`UrlBootRequirementError`); `route.py` never calls it,
or `_commit_envelope`, for any other outcome. The invariant therefore holds even if some future
edit to `route.py` forgot its own discipline -- it is enforced at the one function that would
otherwise silently accept a caller's claim.

## 7. Required proof layers

```text
V1  deterministic identities        tests/unit/url_boot/test_url_boot_identity.py
                                       tests/unit/url_boot/test_url_boot_network_scope.py
V2  controlled adapter contract     tests/contract/url_boot/test_url_boot_adapter_contract.py
V3  real bounded vertical proof     tests/integration/url_boot/
                                       test_url_boot_local_http_vertical_proof.py
V4  failure / tamper matrix         tests/integration/url_boot/
                                       test_url_boot_failure_tamper_matrix.py
V5  Phase 16 continuity + static    tests/integration/url_boot/test_url_boot_kernel_continuity.py
                                       tests/contract/url_boot/test_url_boot_static_conformance.py
```

- **V1** proves every identity this delivery mints -- the source fingerprint, the Boundary
  fingerprint, the source-request identity, the observed-content fingerprint, and the Envelope
  they all compose into -- deterministic and collision-sensitive to every one of its own
  semantic fields, with a harness test pinning each projection to the real record body.
- **V2** proves all eleven `URL_FETCH_OUTCOMES` are reachable end to end through the real route
  and only `OBSERVED` commits (every other outcome returns `envelope=None` and an
  `envelope_id=None` receipt, P17-R1-F1), that the route fails closed on a malformed/
  out-of-vocabulary single-hop adapter report and on an adapter with no readable
  `adapter_identity`, that a field a response body carries beyond `permitted_fields` never
  reaches a committed Envelope, and that an adapter cannot assert a route-only classification
  (`IDENTITY_MISMATCH` and friends) directly in its own single-hop report (P17-R1-F2).
- **V3** proves at least one genuine positive (`OBSERVED`, binding `project_binding_ref` and a
  real `resolution_provenance`), one genuine per-hop-reauthorized redirect follow, one genuine
  redirect *escape refusal*, one genuine `UNSUPPORTED_MEDIA_TYPE`, one genuine
  `OVERSIZED_RESPONSE`, one genuine `CONNECTION_FAILURE`, one genuine HTTPS round trip (real TLS
  handshake against a throwaway local certificate), and the `Host` header's own non-default-port
  correctness -- each a real network round trip over `127.0.0.1` through this package's own
  `network.resolve_hop_address`/`network.connect_and_request_hop` (no VPS, no cloud target),
  reached only through the distinctly-named `observe_url_source_for_disposable_local_test`
  composition entry point (§10.2) -- then hands the positive receipt off to the existing
  Evidence owner.
- **V4** proves authority freshness (pre-adapter and pre-commit, plus a harmless-contention
  control), a genuine DNS-rebinding/loopback refusal by the default adapter, that Boundary
  *data* cannot enable loopback at all (schema refusal, P17-R1-F3), a deterministic cross-hop
  DNS-resolution-drift refusal (P17-R1-F4), zero-adapter-call refusal of userinfo/out-of-scope-
  host/port/scheme sources, a hidden disallowed intermediate redirect hop never reached at all
  (P17-R1-F2), an adapter unable to assert a route-only classification or a fabricated hop
  count, the three-way envelope-identity tamper check extended to `project_binding_ref`/
  `boot_state_fingerprint` (P17-R1-F5), cross-project relabeling refusal, hostile-looking
  fetched content stored as an inert, unexecuted string, and a zero-canonical-State-mutation
  proof (revision/fingerprint/lineage-head/record-absence all unchanged) for every one of the
  ten non-`OBSERVED` outcomes (P17-R1-F1).
- **V5** proves a genuine Phase 16 Model Runtime execution and a genuine URL Source Observation
  coexist in the identical Store/project without either disturbing the other's own records or
  State-tree pointers, plus this package's own static conformance (network-opening surfaces
  confined to `network.py`, no forbidden existing-owner imports, one Boot call site, one
  `derive_evidence` call site, no configuration/dynamic-execution/credential-looking surface).

## 8. Explicit non-claims

This delivery does **not** claim, and no test here asserts:

- that a URL "is" any particular deployment, service, or Human-declared identity. There is no
  signed deployment-declaration chain here (contrast Runtime); a URL Source Observation attests
  only to what a bounded fetch against an explicit source, under an explicit Boundary, actually
  returned.
- that fetched content means anything. `IDENTITY_MISMATCH` and the other route-derived
  classifications (§6.2) are never trusted from the adapter -- the route derives them itself,
  from bounded per-hop facts alone (P17-R1-F2) -- but content still means nothing beyond that
  classification: no owner in this package's own call graph ever passes a fetched field to
  `eval`, a template engine, or a shell (P17-C4 unchanged).
- that a redirect chain is ever followed unbounded, or that any redirect target is trusted
  before it is itself re-validated against the identical closed `network_scope` -- now
  performed by the route itself, before the disallowed hop's own `resolve_hop`/connection
  attempt are ever reached (P17-R1-F2).
- that this layer can mint Authority, invoke a model, execute a Change, or bypass Evidence. It
  imports none of `authority`, `change`, `model_runtime`, or `reflow`, and its own Evidence
  hand-off resolves a real, integrity-checked, committed Envelope before constructing any
  provenance at all -- and refuses outright for any receipt that does not name one
  (`status != "VERIFIED"`, P17-R1-F1).
- that credentials of any kind are ever transmitted. `credentials_permitted` is schema-fixed to
  `false`, and a userinfo-bearing URL is refused before any resolution is attempted.
- that this layer is resistant to a hostile *DNS server* the caller's own environment already
  trusts, or to a compromised TLS certificate authority. What is proved is that the address this
  package connects to is the exact address its own single, un-repeated resolution returned for
  each hop, that the identical `(host, port)` never resolves to two different addresses across
  the hops of one fetch (P17-R1-F4), and that TLS certificate verification runs against the real
  hostname -- not that DNS or the CA system themselves are trustworthy inputs, and not that DNS
  cannot legitimately change *between two separate, independent* fetches (only within one).
- that a failed or refused fetch is recorded anywhere durable at all. P17-C7/P17-R1-F1 requires
  the opposite: a non-`OBSERVED` outcome is bounded, ephemeral, in-memory evidence only, and
  cannot be handed off as Evidence (`route_url_observation_to_evidence` itself refuses any
  receipt whose `status != "VERIFIED"`) -- a caller that needs a durable record of a failure must
  derive and commit one through some other existing owner, never through this package.

## 9. Gate 17

```text
GATE_17_READ_ONLY_URL_BOOT
  V1_DETERMINISTIC_IDENTITIES=PASS
  V2_CONTROLLED_ADAPTER_CONTRACT=PASS
  V3_REAL_BOUNDED_VERTICAL_PROOF=PASS
  V4_FAILURE_TAMPER_MATRIX=PASS
  V5_PHASE_16_CONTINUITY=PASS
  STATIC_CONFORMANCE=PASS
  SCHEMA_VALIDATION=PASS
  MERGE_ALLOWED=false
  ISSUE_CLOSE_ALLOWED=false
  PHASE_17_COMPLETE=false
  PHASE_18_ALLOWED=false
```

## 10. Structural Review Round 2 (P17-R2-F1 through F3)

Reviewed at Round 1's own corrected head (`82a008a`), reopening three of its six closed
findings. All three land together, in `route.py`/`network.py`/`adapter.py`/`types.py`
(F1/F2) and `evidence_handoff.py`/`identity.py`/the Envelope schema (F3).

### 10.1 P17-R2-F1 -- route-owned network admission, not merely route-owned redirects

Round 1 (P17-R1-F2) moved redirect/content/identity classification to the route, but the
adapter's own single `fetch_one_hop` still resolved *and* classified an address's own safety
*and* connected, all in one uninterruptible step -- the route re-authorized only the requested
*hostname* against `network_scope` before calling the adapter; the *resolved address*'s own
safety, and *which* address was actually reached, remained solely the adapter's own word.

The replaceable `UrlSourceAdapter` now exposes two bounded primitives instead of one:
`resolve_hop` (reports a genuine DNS lookup's own result -- `DNS_FAILURE` or `RESOLVED` plus the
one address -- classifying nothing) and `connect_hop` (connects to *exactly* the route-admitted
address handed to it, reporting `CONNECTION_FAILURE`/`TLS_FAILURE`/`TIMEOUT`/`RESPONSE`). Neither
vocabulary (`URL_HOP_RESOLVE_OUTCOMES`, `URL_HOP_CONNECT_OUTCOMES`) contains `BOUNDARY_REFUSED`
at all any more -- it is derived by the route alone
(`network.require_safe_resolved_address`, called on the resolved address the route itself
already has, before any connection is attempted) and returned as `_hop_result("BOUNDARY_REFUSED",
...)`, never accepted from an adapter's own report. The route additionally requires
`connect_hop`'s own reported `resolved_address` to equal the exact address it was handed,
refusing (`UrlBootAdapterError`) any adapter that silently connected elsewhere.

Cross-hop DNS-resolution-drift binding (P17-R1-F4) now happens at the *resolve* stage, on the
route's own already-classified candidate address, before any connection for that hop is ever
attempted -- the identical `(host, port) -> resolved_address` binding as before, just moved one
step earlier in the loop.

### 10.2 P17-R2-F2 -- non-substitutable loopback composition boundary

Round 1 (P17-R1-F3) moved `permit_loopback_test_hosts` to `LocalHttpUrlSourceAdapter`'s own
constructor, reasoning it was then reachable only by test-composition code. Round 2 correctly
identified that as merely *relocating* the identical caller-reachable switch: that adapter class
is exported from this package's own public surface, so any caller able to supply the `adapter`
argument to public `observe_url_source` could still construct exactly that permissive object.

Because §10.1 already moved *all* address-safety classification to the route alone, the adapter
now carries no loopback-related parameter of any kind -- there is nothing left on it to be told
to permit. The loopback decision lives exclusively in `route.py`'s own two permanently bound
classifiers: `_require_safe_resolved_address_production` (loopback always refused; public
`observe_url_source` -- the only entry point `url_boot/__init__.py` ever exports -- is
unconditionally bound to it) and `_require_safe_resolved_address_permitting_loopback_only`
(loopback the one exception; bound only by the distinctly-named, never-publicly-exported
`route.observe_url_source_for_disposable_local_test`, this repository's own V3 local-HTTP test
suite's sole caller). Neither public function's own parameter list carries a loopback-related
argument at all -- no keyword, no positional slot, and no adapter substitution changes it; only
*which of the two distinctly-named functions is imported and called* does, a composition-time
choice made once in this module's own source, never at request time from caller-supplied data.
This is deliberately not a Python-private name, a caller-visible sentinel, or an `isinstance`
check: those inspect a value a caller could still supply; here there is no such value anywhere in
the public call graph to inspect.

### 10.3 P17-R2-F3 -- resolvable exact Boot context at Evidence handoff

Round 1's own `boot_state_fingerprint` (P17-R1-F5) closed *tampering* with the committed field --
any recomputation mismatch already fails the existing three-way envelope-identity check -- but
left Evidence handoff with no way to *independently re-derive* that fingerprint from this
project's own real, canonical State history. A bare fingerprint is not itself a Store-resolvable
reference, and (because `fingerprint_project_state` hashes only `semantic_state`, never
`state_revision`) is not even guaranteed distinct across two different real revisions that both
leave `semantic_state` untouched -- exactly what every URL Boot commit, by P17-C4's own design,
does.

A committed Envelope now additionally carries `boot_state_transition_ref`, the exact,
Store-resolvable `{"kind": "state_transition", "id": ...}` reference to the committed transition
(or, for a genesis-state Boot, the well-known genesis transaction identity -- `binding/route.py`'s
own genesis-State enforcement requires `lineage_head_ref` to be `null` at genesis, so no real
`TRANSITION` event exists yet to mint one from) that produced this exact Boot-observed State.

`evidence_handoff._reresolve_and_verify_boot_context` now runs after the existing three-way
envelope-self-consistency check and before `derive_evidence` is ever called: it re-resolves the
referenced Project Binding through its own canonical identity owner
(`binding.verify_project_binding_identity`) and requires its own `human_authority_ref` to agree
with the Envelope's; and it resolves `boot_state_transition_ref` through the Store's own existing
`resolve_transaction` surface, recomputes that transition's own `after_state`'s semantic
fingerprint, and requires it to equal both that transition's own declared `after_fingerprint` and
the Envelope's own declared `boot_state_fingerprint`. A self-consistent-but-copied Envelope (one
genuinely committed and unmodified, but handed off against a Store/world that cannot itself
corroborate its own claims) is refused here, never merely by re-hashing the Envelope's own
content again. Because the referenced transition is read from this project's own immutable,
append-only lineage log, any later, unrelated State advancement never invalidates this
re-verification.

## 11. Structural Review Round 3 (P17-R3-F1, P17-R3-F2)

Reviewed at Round 2's own corrected head (`91cf57f`). Two findings, both about *authority over
the network boundary itself*, distinct from Round 2's own subject (which classification vocabulary
governs an address's own safety): who is trusted to *create* the connection to an admitted
address at all, and who is trusted to authorize the one loopback exception that exists for this
repository's own disposable local-HTTP test.

### 11.1 P17-R3-F1 -- route-owned connection, not merely route-owned address admission

Round 2 (P17-R2-F1) moved address-safety classification to the route, but the replaceable
`UrlSourceAdapter`'s own `connect_hop` method still *created* the connection and reported its own
outcome -- a conforming-looking adapter could still open a socket to any address of its own
choosing and simply *claim*, in its own report, that it reached the route-admitted one. The route's
own post-connect check (§5.2) caught a *truthful* adapter naming a different address, but had no
way to catch a dishonest one that lied about which address it actually reached while returning a
fabricated, plausible-looking response.

`UrlSourceAdapter` no longer declares a `connect_hop` method at all -- only `resolve_hop` remains
(harmless on its own: the route independently classifies whatever address a resolve report names
*before* ever using it for anything, §10.1). The real connection is now created and controlled
exclusively by the trusted network layer: `network.perform_admitted_connection(source_identity,
*, admitted_address, boundary)` wraps `network.connect_and_request_hop`, converting the exception
types that call already let escape into the same typed `URL_HOP_CONNECT_OUTCOMES` vocabulary a
`connect_hop` report used to carry, so nothing about the two-stage hop shape (§5.1) changed from
the route's own point of view -- only *who* produces that report.

`route.py`'s internal `_fetch_with_route_owned_redirects`/`_observe_url_source_impl` now take a
required `perform_connection` parameter -- a callable of `(adapter, current_identity,
admitted_address, boundary) -> Mapping`, threaded exactly like §10.2's own `classify_resolved_address`
parameter: never a value any public-entry-point caller can supply, only a composition-time choice
made once in this module's own source. Two implementations exist. `_perform_connection_via_trusted_network`
ignores its own `adapter` argument entirely and calls `network.perform_admitted_connection`
directly -- this is the one permanently bound into public `observe_url_source`, and also the one
bound into the externally-authorized disposable-local-test composition (§11.2), so *every*
genuinely-networked entry point this package exposes, production or test, creates its own
connection through the identical trusted primitive, never through an adapter. `_perform_connection_via_adapter`
delegates to `adapter.connect_hop(...)` (a capability `FakeUrlSourceAdapter` still exposes, as a
non-Protocol extra, purely for this repository's own internal deterministic test suite) and is
used *only* by test code that calls `_observe_url_source_impl` directly -- never reachable from
either public entry point.

The required decisive control at this round's own head: a malicious adapter whose own
`connect_hop` is seeded to fabricate a plausible `RESPONSE` claiming the admitted address is
never even called by production `observe_url_source` -- its own call count remains exactly zero.
Alternate-address I/O by a hostile adapter is not merely detected after the fact; it is
structurally impossible, because the adapter is never given the opportunity to open a connection
of its own at all. A companion positive control confirmed `resolve_hop` *was* still reached
exactly once, so this was a true removal of one specific capability, not an accidental severing of
the adapter's whole role. A further decisive control confirmed public `observe_url_source`'s own
signature carried no `perform_connection` slot through which an alternate connector could ever be
substituted at request time -- the identical alternate-world-substitution discipline §10.2 already
established for the loopback classifier. (Structural Review Round 4, P17-R4-F1/F2, superseded
`observe_url_source` itself with `compose_url_source_observer` and folded `resolve_hop` into this
identical no-adapter-capability discipline; the current, still-green forms of these three controls
are `tests/contract/url_boot/test_url_boot_adapter_contract.py::
test_production_compose_url_source_observer_never_invokes_any_adapter_resolve_or_connect_method`,
`::test_production_compose_url_source_observer_still_reads_adapter_identity`, and
`tests/integration/url_boot/test_url_boot_failure_tamper_matrix.py::
test_compose_url_source_observer_refuses_a_perform_connection_or_resolution_keyword_argument` --
see §12.1/§12.2.)

Connect-stage validation failures in the route (a non-mapping report, an out-of-vocabulary
outcome, a `resolved_address` that disagrees with what was admitted, an unreadable
`response_status`) now raise `UrlBootRequirementError` rather than `UrlBootAdapterError`: since
production's connector is the trusted network layer itself, a failure there is no longer
necessarily an "adapter" fault. This repository's own internal deterministic test suite (calling
`_observe_url_source_impl` directly with `_perform_connection_via_adapter`) still exercises these
identical checks against a `connect_hop`-bearing test double, so the checks themselves, and their
test coverage, are unchanged -- only the exception class a production-path failure now reports.

### 11.2 P17-R3-F2 -- a genuinely non-substitutable disposable-local-test observer

Round 2 (P17-R2-F2) closed the loopback allowance's own *parameter surface* but still exposed it
through a second, distinctly-named public function, `route.observe_url_source_for_disposable_local_test`
-- reachable by any caller able to import `manosube_agent_civilization.url_boot.route` and read
its own source, since a plain Python module attribute is never truly private. Structural Review
Round 3 found this an incomplete closure: the *composition itself*, not merely the request-facing
parameter list, needed to be something a hostile or careless caller cannot substitute their way
into using in a production Boot.

`observe_url_source_for_disposable_local_test` is removed from `route.py` entirely.
`_require_safe_resolved_address_permitting_loopback_only` still exists as a name in that module
(Python cannot make a module-level name truly unreachable by import -- disclosed, not concealed)
but Round 3 leaves nothing defined in `route.py` itself that binds it to anything; the AST-based
static-conformance proof `test_route_never_binds_the_loopback_classifier_to_anything` confirms
this by walking `route.py`'s own source, not by grepping for the function's name.

The one place this repository's own disposable local-HTTP vertical proof can still observe
against `127.0.0.1` is a new file, `tests/fixtures/url_boot_local_test_authority.py` --
deliberately placed *outside* the shipped package. `pyproject.toml`'s own
`[tool.hatch.build.targets.wheel] packages = ["src/manosube_agent_civilization"]` confirms this
file is genuinely absent from the distributed wheel, present only in the sdist's own `/tests`
inclusion -- a real, checkable packaging fact, not merely an assertion. It exposes one function,
`compose_disposable_local_test_observer(store, *, project_id, project_binding_id, adapter) ->
Callable[[source_identity, boundary, observed_at], dict]`: a two-step factory-and-closure
boundary, mirroring the identical "a closure is not a class" idiom Runtime's own
`bootstrap.py` already established for Structural Review Round 5 (P15-R5-F1) -- composition
chooses and closes over the loopback-permitting authority (`_require_safe_resolved_address_permitting_loopback_only`,
`_perform_connection_via_trusted_network`) before the request boundary ever exists, so the
returned closure's own call signature carries none of `store`/`project_id`/`project_binding_id`/
`adapter`/classifier/connector -- only the genuinely request-facing `source_identity`/`boundary`/
`observed_at` a real fetch call needs. This is not a sentinel, an `isinstance` check, a Python
private name, or stack/module inspection: none of those defend against a caller who can read
source and import freely; a closure over values chosen once, at composition time, in code the
request path never touches, has no such value left in its own signature to inspect at all.

This boundary is explicitly disclosed as **not** the cryptographic capability security Runtime's
own Ed25519-anchored production authority provides (P15's own execution-authority chain) -- it is
a deliberate, disclosed, proportionate judgment call given the bounded blast radius: loopback-only
access to a disposable local server the same test process already has unmediated access to by
simply calling it directly. Pure Python offers no access-control primitive stronger than "this
value is not reachable from code that does not import this specific module" for a same-process,
same-privilege caller, and this package does not claim otherwise.

The required decisive controls: direct import of `route._require_safe_resolved_address_permitting_loopback_only`
or `route._perform_connection_via_trusted_network` by themselves yields no usable permissive
authority against public `observe_url_source` (its own binding is fixed at module load, never
request time -- §10.2, §11.1); a genuine disposable local-HTTP vertical succeeds only through
`compose_disposable_local_test_observer` (`tests/integration/url_boot/test_url_boot_local_http_vertical_proof.py`,
all 8 cases green); and every earlier zero-State-mutation, redirect, DNS-drift, provenance,
tamper, and Evidence preflight proof (§7, §10) remains green under the new API, proved by driving
this repository's own internal deterministic connector (`_perform_connection_via_adapter`)
directly through `_observe_url_source_impl`, the identical internal-test-composition pattern
`test_url_boot_kernel_continuity.py` already established for Round 2's own `classify_resolved_address`
parameter.

## 12. Structural Review Round 4 (P17-R4-F1, P17-R4-F2)

Reviewed at Round 3's own corrected head, reopening two findings that Round 3's own closure
created in turn: Round 3 closed connection-creation authority and the disposable-local-test
composition's own *request-facing* surface, but left the *resolution* stage and the *production*
composition's own request-facing surface each carrying the identical shape of gap Round 3 had
just closed everywhere else.

### 12.1 P17-R4-F1 -- route-owned resolution, not merely route-owned connection

Round 3 removed `connect_hop` from the replaceable `UrlSourceAdapter` Protocol entirely, but
`resolve_hop` remained -- a replaceable adapter's own DNS resolution still ran as arbitrary
caller-supplied Python inside the genuine trusted pre-commit network path, with the same ambient
socket/network authority as any other code in this process, before the route's own address-safety
classification ever saw its result. A conforming-looking `resolve_hop` implementation could
perform its own, entirely separate network I/O to any address at all as a side effect, then return
a safe-looking `RESOLVED` result naming the real requested host -- nothing checked what the
adapter's own code *did*, only what it *reported*, and a Protocol method's own name constrains
shape, never effects.

`UrlSourceAdapter` no longer declares `resolve_hop` either -- the Protocol now declares no
executable method of any kind, only the inert `adapter_identity` attribute. The one genuine DNS
lookup is now created and controlled exclusively by `network.perform_resolution`, called
*directly* by this module's own `_perform_resolution_via_trusted_network`, which both public entry
points are permanently bound to -- the exact mirror of §11.1's own connect-stage correction. A
replaceable adapter therefore has no call through which to perform any network I/O at all in
either genuinely-networked path: not "the report is checked and refused if it disagrees" but
"there is no report to check, because neither resolve- nor connect-capable method exists on the
Protocol, and neither public entry point ever asks for one." This repository's own internal,
fully deterministic route-logic test suite still needs some way to inject simulated resolve
facts; it reaches `_perform_resolution_via_adapter` by calling `_observe_url_source_impl` directly
-- a path no production or disposable-local-test caller ever reaches, identically to
`_perform_connection_via_adapter` (§11.1).

The required decisive control: a malicious adapter whose own `resolve_hop` is seeded to perform
alternate-address I/O and return a plausible `RESOLVED` result naming the real requested host is
never even called by production's own composition -- both its `resolve_hop` and `connect_hop`
call counts remain exactly zero
(`tests/contract/url_boot/test_url_boot_adapter_contract.py::test_production_compose_url_source_observer_never_invokes_any_adapter_resolve_or_connect_method`).
Because resolution is now genuinely performed by the trusted network layer against the *real*
requested host (a loopback address, in that decisive test's own world), the outcome is a fully
deterministic `BOUNDARY_REFUSED` -- a stronger, network-independent proof than Round 3's own
connect-only version of this control could offer, since the malicious adapter's claimed address is
never consulted at all. A companion positive control confirms the closure still reads the
adapter's own `adapter_identity`
(`test_production_compose_url_source_observer_still_reads_adapter_identity`), so this is a true
removal of one specific capability, not an accidental severing of the adapter's whole role.

Resolve-stage validation failures in the route now raise `UrlBootRequirementError` rather than
`UrlBootAdapterError` (§6.2), mirroring Round 3's identical change for the connect stage: since
production's resolver is the trusted network layer itself, a failure there is no longer
necessarily an "adapter" fault.

### 12.2 P17-R4-F2 -- a genuine production composition boundary, and a non-shipped permissive classifier

Round 3 (§11.2) required the disposable-local-test path to be a closure composed once, ahead of
any request, over the Store/Project/Binding/adapter it is bound to -- but left public
`observe_url_source` itself taking `store`/`adapter` (among others) directly, on every call, which
made *production*, not a caller who imported private names, the thing actually failing to be "a
request-facing closure/capability composed before requests" the adopted contract requires. Public
`observe_url_source` is removed outright. `compose_url_source_observer(store, *, project_id,
project_binding_id, adapter) -> Callable[[source_identity, boundary, observed_at], dict]` is this
module's sole production entry point -- the identical two-step factory-and-closure shape §11.2
already established for the disposable-local-test path, now applied to production itself. It
permanently binds the production classifier (`_require_safe_resolved_address_production`, loopback
always refused) and the trusted network resolver/connector
(`_perform_resolution_via_trusted_network`, `_perform_connection_via_trusted_network`) inside the
returned closure; the closure's own call signature carries only `(source_identity, boundary,
observed_at)` -- no Store, adapter, classifier, resolver, connector, policy flag, or
alternate-world substitution slot of any kind, and `compose_url_source_observer`'s own parameter
list carries none of those substitution slots either.

Round 4 further found that `route.py` itself still shipped
`_require_safe_resolved_address_permitting_loopback_only`'s complete implementation, merely
unbound from any request-facing operation by Round 3's own correction -- reachable by any caller
able to import `route.py` directly and recombine that classifier with `route.py`'s own other
private names (`_observe_url_source_impl`, `_perform_connection_via_trusted_network`,
`_perform_resolution_via_trusted_network`). Structural Review Round 4's own delivery-comment
demonstrated this reconstruction attack explicitly, naming those importable symbols. That
classifier's entire body is therefore moved out of this shipped module entirely, into
`tests/fixtures/url_boot_local_test_authority.py` (still confirmed absent from the distributed
wheel, §11.2's own packaging check unchanged) -- `route.py` now ships zero loopback-permitting
classifier code of any kind, under any name
(`tests/contract/url_boot/test_url_boot_static_conformance.py::test_route_py_ships_no_loopback_permitting_classifier_of_any_kind`).

The disposable-local-test composition is additionally hardened with a genuine, externally held
*test-harness authority*: `compose_disposable_local_test_observer` now requires a mandatory
`test_harness_authority: bytes` keyword, verified via `hmac.compare_digest` against a digest keyed
by a secret generated fresh, once, at the non-shipped fixture module's own import time -- a value
that exists nowhere in any shipped module -- before the closure is even constructed. A missing,
wrong-typed, or forged authority is refused (`UrlBootRequirementError`) before any DNS resolution
or network connection is ever attempted. This is explicitly, extensively disclosed in that
fixture module's own docstring as **not** full cryptographic capability security and **not**
defending against a same-process adversary who already possesses the test-suite source -- Python
offers no way to hide a value from same-process code that can import the module holding it -- only
as closing the specific wheel-only-recombination attack Round 4 demonstrated: a caller possessing
only the installed wheel has no ready-made permissive classifier, no ready-made composition wiring
it in, and no authority value to present, regardless of which private names are recombined.

The required decisive controls: a malicious adapter's `resolve_hop`/`connect_hop` are both never
invoked by production's own closure (§12.1's own decisive control, above); a missing, wrong-typed,
or forged `test_harness_authority` is refused before any network activity
(`tests/integration/url_boot/test_url_boot_local_http_vertical_proof.py::test_compose_disposable_local_test_observer_refuses_a_missing_test_harness_authority`,
`::test_compose_disposable_local_test_observer_refuses_a_wrong_typed_test_harness_authority`,
`::test_compose_disposable_local_test_observer_refuses_a_forged_test_harness_authority`, and
`::test_a_forged_test_harness_authority_never_reaches_the_adapter_at_all`, which proves composition
itself fails before even touching the adapter's own `adapter_identity`); neither
`compose_url_source_observer` nor its returned closure carries a loopback-permitting, classifier-,
resolver-, or connector-substitution slot of any kind, by keyword or position
(`tests/integration/url_boot/test_url_boot_failure_tamper_matrix.py::test_compose_url_source_observer_refuses_a_loopback_permitting_keyword_argument`,
`::test_the_returned_closure_refuses_a_loopback_permitting_keyword_argument`,
`::test_the_returned_closure_refuses_a_loopback_permitting_positional_argument`, and
`::test_compose_url_source_observer_refuses_a_perform_connection_or_resolution_keyword_argument`);
and every earlier zero-State-mutation, redirect, DNS-drift, provenance, tamper, and Evidence
preflight proof (§7, §10, §11) remains green under the new API.

`MERGE_ALLOWED`, `ISSUE_CLOSE_ALLOWED`, `PHASE_17_COMPLETE` and `PHASE_18_ALLOWED` are fixed at
`false` by the adopting authority and are not this document's to change.

## 13. Structural Review Round 5 (P17-R5-F1, P17-R5-F2)

Reviewed at Round 4's own corrected head, finding two further gaps Round 4's own closure left
open: production still accepted a replaceable adapter *object* (rather than plain data) at its
trusted composition boundary, and the shipped route still carried the generic, dependency-injected
orchestration a caller could recombine with the trusted network layer to reconstruct a
loopback-admitting path.

### 13.1 P17-R5-F1 -- inert `adapter_identity` data, not a replaceable adapter object

Round 4 (§12.1) removed every executable method from `UrlSourceAdapter`, so no replaceable
adapter's own code could ever run during a request -- but `compose_url_source_observer` still
accepted a conforming *object* and read its own `adapter_identity` attribute via `getattr` on
every single request. A hostile caller-supplied object -- a property that raises or mutates
canonical State the moment it is read, a custom `Mapping`/iterator/`dict`-subclass whose own
`__iter__`/`__getitem__`/`keys` execute arbitrary code -- could therefore still reach this route's
own trusted composition boundary and execute, repeatedly, on every request, even though it
declared no method the Protocol named.

`compose_url_source_observer(store, *, project_id, project_binding_id, adapter_identity: Any) ->
Callable[...]` now accepts *adapter_identity* directly, as already-realized data of any shape a
caller hands it, and validates and rebuilds it exactly once, at composition time, via
`route._canonicalize_inert_adapter_identity` -- a strict recursive validator accepting only the
closed set of builtin scalar/container types (`str`, `int`, `float`, `bool`, `None`, `dict`,
`list`), checked by exact `type(x) is <builtin>` rather than `isinstance` specifically so a
`dict`/`list` *subclass* is refused before any of its own overridden protocol methods ever runs.
The validator itself never calls `getattr` on the input or any of its nested contents -- only
`type(...)` (which never invokes user code) followed by the genuine `dict.items()`/`list`
iteration protocol on a value already confirmed to be an *exact* builtin `dict`/`list`. The
rebuilt, frozen result (`deep_freeze`, applied once by the composer itself) is captured in the
returned closure; there is no path back to the original caller-supplied value, and no per-request
re-validation or re-derivation of any kind.

The required decisive controls: a hostile object whose every attribute access, comparison, or
hash raises is refused before any of those hostile protocol methods ever runs, proved by the
refusal surfacing as the canonicalizer's own `UrlBootRequirementError`, never the object's own
exception
(`tests/contract/url_boot/test_url_boot_adapter_contract.py::test_compose_url_source_observer_refuses_a_hostile_property_object_before_any_access`);
a `dict` subclass overriding `items`/`keys`/`__iter__` is refused by the exact `type(x) is dict`
check before any override ever runs
(`::test_compose_url_source_observer_refuses_a_hostile_dict_subclass_before_any_iteration`,
`::test_compose_url_source_observer_refuses_a_hostile_list_subclass_nested_inside_a_plain_dict`);
a caller-defined object implementing the full `Mapping` protocol but genuinely not a `dict` is
refused identically, proving `isinstance` is never consulted
(`::test_compose_url_source_observer_refuses_a_custom_mapping_masquerading_as_a_dict`); closure-
capture inspection confirms the returned closure's own captured cells hold the frozen, rebuilt
copy, never the original object, and that mutating the original input after composition never
reaches a later request
(`::test_compose_url_source_observer_retains_no_reference_to_the_original_adapter_identity_object`);
and a genuine positive control confirms an ordinary `dict` still reaches the committed receipt
unchanged
(`::test_production_compose_url_source_observer_reads_a_plain_adapter_identity`). A non-`dict`
*adapter_identity* (`None`, a string, an int, a list) is refused identically wherever the internal
deterministic route-logic entry point is exercised directly
(`::test_the_route_refuses_a_non_dict_adapter_identity`).

### 13.2 P17-R5-F2 -- no shipped generic classifier/resolver/connector-injection surface; issuer/verifier-separated local-test authority

Every prior round narrowed *what a replaceable adapter could do*, but left the shipped `route.py`
itself holding a generic orchestration function (the pre-Round-5 `_observe_url_source_impl`)
accepting `classify_resolved_address`/`perform_resolution`/`perform_connection` as ordinary
function parameters. A caller able to import `route.py` directly could therefore call that
function with the genuine, shipped trusted-network resolver/connector *and* an ordinary permissive
`lambda address: None` as `classify_resolved_address`, reconstructing the exact
loopback-admitting path production's own classifier alone was supposed to close -- using only
shipped code, no isolation break, and no adapter object at all.

The shipped package now ships **only** a fixed, non-parameterized production pipeline
(`_fetch_with_route_owned_redirects_production`, `_observe_url_source_impl_production`) whose own
classifier/resolver/connector calls are hardcoded, direct calls by name -- there is no parameter
list anywhere in `route.py` through which a caller could ever substitute any of the three. The
*generic*, dependency-injected form of that identical orchestration -- the one this repository's
own internal deterministic route-logic test suite genuinely needs, to inject a controlled
`FakeUrlSourceAdapter`'s own simulated resolve/connect facts -- moves entirely into
`tests/fixtures/url_boot_test_engine.py`, confirmed absent from the distributed wheel by the
identical packaging fact §11.2 already established. That module also backs the disposable-local-
test composition itself, binding its own generic engine to the loopback-permitting classifier and
the *same* trusted network resolver/connector production uses (imported, never reimplemented).

The required decisive control, AST-based rather than a narrower name check: no function defined
anywhere in `route.py`'s own module source declares a parameter -- positional, keyword-only, or
otherwise -- named `classify_resolved_address`, `perform_resolution`, or `perform_connection`
(`tests/contract/url_boot/test_url_boot_static_conformance.py::test_route_py_ships_no_function_accepting_a_classifier_resolver_or_connector_callable`).
A caller attempting to reconstruct the reviewed reconstruction attack by calling shipped
internals with a no-op classifier therefore has no such parameter to pass one through at all --
there is no injection surface left to fail to reach, because the surface itself does not exist.

**Issuer/verifier separation for the disposable-local-test authority.** Round 4's own
`test_harness_authority` design (§12.2) kept the minting secret and the verifying logic in the
same non-shipped module -- anyone able to import that module could both mint and verify, so the
"genuine external authority" property rested entirely on the module's own non-shipped status, not
on any structural separation of roles. `tests/fixtures/url_boot_local_test_authority.py` now holds
**only** a hardcoded Ed25519 public-key hex literal and verifies a presented credential against it
via this repository's own established `binding.signature.verify_ed25519_signature` -- the
identical verifier `runtime/bootstrap.py`'s own production trust-anchor already uses. It holds no
private key, no minting function, and imports nothing from the one module that can mint a genuine
credential: `tests/fixtures/url_boot_local_test_issuer.py`, a deterministic, fixed, disclosed-
as-test-only Ed25519 keypair (`hashlib.sha256(<fixed descriptive string>).digest()` seeds
`Ed25519PrivateKey.from_private_bytes`, never `.generate()`) genuinely separate from -- and never
imported by -- the verifier module.

The required decisive controls: missing, wrong-shaped, or forged (wrong signature, wrong
algorithm, wrong `key_id`) credentials are all refused before any DNS resolution or network
connection is ever attempted
(`tests/integration/url_boot/test_url_boot_local_http_vertical_proof.py::test_compose_disposable_local_test_observer_refuses_a_missing_test_harness_authority`,
`::test_compose_disposable_local_test_observer_refuses_a_wrong_typed_test_harness_authority`,
`::test_compose_disposable_local_test_observer_refuses_a_forged_test_harness_authority`); a forged
authority is refused before *adapter_identity* is ever canonicalized, proving the authority check
runs first
(`::test_a_forged_test_harness_authority_never_reaches_adapter_identity_canonicalization`); a
genuine external-issuer positive control exercises the composition by importing the issuer module
directly, a genuinely separate file from the one it hands the resulting credential to (every
positive-route test in that file); and a non-vacuity control confirms the verifier's own hardcoded
public-key literal genuinely is the public half of the issuer's own private key, rather than the
two modules silently trusting two different keys
(`::test_the_verifiers_trusted_public_key_genuinely_matches_the_issuers_own_private_key`).

`MERGE_ALLOWED`, `ISSUE_CLOSE_ALLOWED`, `PHASE_17_COMPLETE` and `PHASE_18_ALLOWED` are fixed at
`false` by the adopting authority and are not this document's to change.
