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
STRUCTURAL_REVIEW_ROUNDS_APPLIED=2
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

```python
result = observe_url_source(
    store,
    project_id=project_id,
    project_binding_id=project_binding_id,
    source_identity=network.canonical_source_identity("https://example.org/status"),
    boundary={
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
    adapter=my_url_source_adapter,  # the one replaceable boundary
    observed_at="2026-09-10T00:00:01Z",
)
result["envelope"]  # the canonical, committed Envelope, or None (P17-C7/P17-R1-F1: only ever
                     # non-None when fetch_outcome == "OBSERVED" -- see §5)
result["receipt"]   # UrlSourceObservationReceipt (ephemeral, never committed itself)

evidence = route_url_observation_to_evidence(store, result["receipt"], project_id, request)
```

`network_scope` carries no `permit_loopback_test_hosts` field (Structural Review Round 1,
P17-R1-F3), and no adapter constructor carries one either any more (Structural Review Round 2,
P17-R2-F2, §10.2): the loopback exception is reachable only by importing the distinctly-named,
never-publicly-exported `route.observe_url_source_for_disposable_local_test` directly -- never
through any field or parameter reachable from public `observe_url_source`.

## 3. Frozen semantic decisions

1. **Read-only, no create-once-reuse-after side effect -- and no State mutation at all unless the
   fetch genuinely succeeded (Structural Review Round 1, P17-R1-F1).** Unlike Projection, this
   layer derives no intent/materialize-attempt claim pair -- observing the identical source under
   the identical Boundary twice is two independent facts about the world at two different
   instants, not a duplicate external artifact. `observe_url_source` commits exactly one new
   Envelope **only** when `fetch_outcome == "OBSERVED"`; every other outcome (all ten typed
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
  P17-R2-F1): one bounded UrlSourceAdapter.resolve_hop call per hop, handed deep-frozen copies
  it cannot mutate, reporting only a genuine DNS_FAILURE or a RESOLVED address -- never a safety
  verdict; the route alone then classifies that resolved address's own safety
  (network.require_safe_resolved_address) and binds it to its own (host, port) for the lifetime
  of this one fetch, refusing as BOUNDARY_REFUSED before any connection is attempted, either for
  an unsafe address or for a later hop resolving the identical (host, port) to a different
  address; only once the route has admitted an address does it call the adapter's own
  connect_hop with that exact admitted_address, and the route itself verifies the adapter's own
  connect_hop report names that same address back (else UrlBootAdapterError -- the adapter
  connected somewhere else); before following a redirect the route itself also re-validates the
  target's hostname against network_scope; every content-type/size/JSON/IDENTITY_MISMATCH
  classification is performed here, from the adapter's bounded per-hop facts alone (see §10.1)
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

### 5.1 The resolve-once-connect-to-that-address technique, route-owned since Structural Review Round 2 (P17-C5, P17-R2-F1)

Resolution and connection are two distinct, bounded adapter primitives, never one combined
adapter call. `network.resolve_hop_address` resolves a hop's host exactly once through a single
`socket.getaddrinfo` call and returns the address alone -- it classifies nothing.
`network.require_safe_resolved_address`, called by the route itself (never the adapter) on that
resolved address, refuses loopback/private/link-local/multicast/reserved/unspecified addresses
unless the route's own caller is the distinctly-named, never-publicly-exported
`observe_url_source_for_disposable_local_test` composition entry point (never Boundary data,
never an adapter constructor argument -- §10.2). Only once the route has admitted an address
does it call `network.connect_and_request_hop`, which connects a raw `http.client.HTTPConnection`
**directly to that route-admitted address**, wrapping TLS exactly once, against the real
hostname, when the scheme is `https` -- never re-resolving the hostname at connection time,
which is exactly the resolve-then-reconnect race a naive `urllib`-based fetcher would leave
open. The original hostname is still sent as the `Host` header (including a non-default port)
and, over HTTPS, as the TLS SNI/certificate verification name. See §10.1 for the full rationale
for splitting resolution and connection into two adapter-reportable stages.

### 5.2 Route-owned per-hop redirect reauthorization and cross-hop resolution-drift binding (P17-C5, Structural Review Round 1 P17-R1-F2/F4, Structural Review Round 2 P17-R2-F1)

The route -- never the replaceable adapter -- owns the entire redirect loop. Before calling
`resolve_hop`/`connect_hop` for a redirect target, the route itself re-validates that target's
hostname against the Boundary's own `network_scope` (`network.canonical_source_identity` +
`network.require_source_within_network_scope`), bounded at
`boundary.redirect_policy.max_redirects` hops; a redirect naming a host outside scope, or one
exceeding the hop bound, refuses as `REDIRECT_REFUSED` -- never silently followed, and the
disallowed hop's own `resolve_hop`/`connect_hop` are never even called (§6.5). The route
additionally binds each hop's own resolved address to its own `(host, port)` for the lifetime of
one fetch, checked immediately after `resolve_hop` returns and before `connect_hop` is ever
called: a same-host redirect whose second hop resolves to a genuinely different public address
than its first refuses as `BOUNDARY_REFUSED` (§6.6) -- resolve-once-connect-to-that-address alone
closes only the single-hop DNS time-of-check/time-of-use window; this closes the cross-hop one.
The route also verifies, after every `connect_hop` call, that the adapter's own report names
back the exact `admitted_address` it was handed -- an adapter that connected to a different
address raises `UrlBootAdapterError` rather than being trusted (§10.1).

## 6. Disclosed judgment calls

### 6.1 A genuinely impure `network.py`, and why

Runtime's own `network.py` is pure and I/O-free by design: Phase 15 explicitly declined to
resolve DNS at all, and refused every redirect outright rather than validating one. Phase 17's
own adopted contract requires the opposite -- genuine per-hop redirect reauthorization and
DNS-rebinding protection, which cannot be expressed correctly from outside the socket-opening
call. `network.py` is therefore the one module in this package permitted to import
`socket`/`http.client`/`ssl`/`ipaddress`; `adapter.py` additionally imports `socket`/`ssl`, but
only to classify the exception types `network.resolve_hop_address`/`network.
connect_and_request_hop` themselves let escape -- it opens no socket and wraps no TLS itself,
proved by `tests/contract/url_boot/test_url_boot_static_conformance.py`.

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
vocabulary `UrlSourceAdapter.resolve_hop` may return, and `URL_HOP_CONNECT_OUTCOMES`
(`CONNECTION_FAILURE`, `TLS_FAILURE`, `TIMEOUT`, `RESPONSE`) is the complete, closed vocabulary
`UrlSourceAdapter.connect_hop` may return -- `BOUNDARY_REFUSED` is a member of neither: it is
purely route-derived, from the route's own classification of a `resolve_hop`-reported address
and its own cross-hop resolution-drift check, never an outcome any adapter may assert (see
§10.1 for the full rationale). `REDIRECT_REFUSED`, `OVERSIZED_RESPONSE`,
`UNSUPPORTED_MEDIA_TYPE`, `MALFORMED`, `IDENTITY_MISMATCH`, `BOUNDARY_REFUSED`, and `OBSERVED`
are all route-*derived* classifications; an adapter naming one of them directly in its own
`resolve_hop`/`connect_hop` report is a malformed report (`UrlBootAdapterError`), never a
shortcut.

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

### 6.5 The loopback test allowance is a Python composition-time decision, never Boundary data (Structural Review Round 1 P17-R1-F3, superseded by Structural Review Round 2 P17-R2-F2 -- see §10.2)

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
  performed by the route itself, before the disallowed hop's own `resolve_hop`/`connect_hop` are
  ever called (P17-R1-F2).
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

`MERGE_ALLOWED`, `ISSUE_CLOSE_ALLOWED`, `PHASE_17_COMPLETE` and `PHASE_18_ALLOWED` are fixed at
`false` by the adopting authority and are not this document's to change.
