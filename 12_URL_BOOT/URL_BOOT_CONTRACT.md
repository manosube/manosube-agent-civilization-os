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
STRUCTURAL_REVIEW_ROUNDS_APPLIED=0
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
            "permit_loopback_test_hosts": False,
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
result["envelope"]  # the canonical, committed URL Source Observation Envelope
result["receipt"]   # UrlSourceObservationReceipt (ephemeral, never committed)

evidence = route_url_observation_to_evidence(store, result["receipt"], project_id, request)
```

## 3. Frozen semantic decisions

1. **Read-only, no create-once-reuse-after side effect.** Unlike Projection, this layer derives
   no intent/materialize-attempt claim pair -- observing the identical source under the
   identical Boundary twice is two independent facts about the world at two different instants,
   not a duplicate external artifact. `observe_url_source` commits exactly one new Envelope per
   call.
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
4. **No route-level semantic reinterpretation of fetched content.** Unlike Runtime's own route,
   which independently computes `NEGATIVE`/`IDENTITY_MISMATCH` from a transport-level report,
   this route trusts the adapter's own honest, per-hop-reauthorized classification into one of
   the eleven closed `URL_FETCH_OUTCOMES` -- because P17-C4 forbids this layer from ever treating
   fetched *content* as meaningful on its own, and a route-level "this content looks wrong"
   judgment would be exactly that.
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
                                   this package produces.
```

There is no Human-declared deployment-identity record in this package (contrast §3.2): the
closed fetch Boundary is the only Human-declared input, and it is a caller-supplied, schema-
validated argument, never a Store-resolved record of its own.

## 5. Canonical route

```text
complete schema validation of the declared source identity and closed fetch Boundary
→ network-scope check on the requested source -- zero-call, before Boot or any adapter
→ real-instant time-window check -- refuses before any adapter call
→ real Project/Human Authority (Boot re-verification)
→ explicit source identity, fingerprinted (never trusted from a caller)
→ closed fetch Boundary, fingerprinted (never trusted from a caller)
→ deterministic source_request_identity (source + Boundary + issued_at) -- computable before
  the adapter is ever called
→ authority-freshness re-check -- refuses before the adapter
→ replaceable URL Source Adapter -- one bounded, per-hop-reauthorized transport call, handed
  deep-frozen copies it cannot mutate
→ independent field-boundary projection (any field outside permitted_fields is a refusal,
  never silently kept), redaction, and a defense-in-depth network-scope re-check of whatever
  effective source identity the adapter reports it actually reached
→ canonical URL Source Observation Envelope
→ authority-freshness re-check on every commit attempt
→ existing canonical persistence boundary (commit_state_transition)
→ bounded URL Source Observation Receipt → existing Evidence owner
```

### 5.1 The resolve-once-connect-to-that-address technique (P17-C5)

`network.fetch_one_hop` resolves a hop's host exactly once through a single
`socket.getaddrinfo` call, classifies the resolved address (refusing loopback/private/
link-local/multicast/reserved/unspecified unless the Boundary's own
`permit_loopback_test_hosts` explicitly admits loopback for a controlled local test target),
and connects a raw `http.client.HTTPConnection`/`HTTPSConnection` **directly to that resolved
address** -- never re-resolving the hostname at connection time, which is exactly the
resolve-then-reconnect race a naive `urllib`-based fetcher would leave open. The original
hostname is still sent as the `Host` header and, over HTTPS, as the TLS SNI/certificate
verification name.

### 5.2 Per-hop redirect reauthorization (P17-C5)

`LocalHttpUrlSourceAdapter` follows a redirect only after re-validating its own target's
hostname against the Boundary's own `network_scope` (`network.canonical_source_identity` +
`network.require_source_within_network_scope`), bounded at
`boundary.redirect_policy.max_redirects` hops. A redirect naming a host outside scope, or one
exceeding the hop bound, is reported as `REDIRECT_REFUSED` -- never silently followed and never
raised as an uncaught exception. The route itself additionally re-checks whatever *effective*
source identity the adapter reports it actually reached (defense in depth, neither site trusts
the other to be the only one).

## 6. Disclosed judgment calls

### 6.1 A genuinely impure `network.py`, and why

Runtime's own `network.py` is pure and I/O-free by design: Phase 15 explicitly declined to
resolve DNS at all, and refused every redirect outright rather than validating one. Phase 17's
own adopted contract requires the opposite -- genuine per-hop redirect reauthorization and
DNS-rebinding protection, which cannot be expressed correctly from outside the socket-opening
call. `network.py` is therefore the one module in this package permitted to import
`socket`/`http.client`/`ssl`/`ipaddress`; `adapter.py` additionally imports `socket`/`ssl`, but
only to classify the exception types `network.fetch_one_hop` itself lets escape -- it opens no
socket and wraps no TLS itself, proved by `tests/contract/url_boot/
test_url_boot_static_conformance.py`.

### 6.2 The closed eleven-member outcome vocabulary (P17-C7)

`URL_FETCH_OUTCOMES` was chosen to map one-to-one onto every outcome the adopted contract text
names by name: `OBSERVED`, `DNS_FAILURE`, `CONNECTION_FAILURE`, `TLS_FAILURE`, `TIMEOUT`,
`REDIRECT_REFUSED`, `OVERSIZED_RESPONSE`, `UNSUPPORTED_MEDIA_TYPE`, `MALFORMED`,
`IDENTITY_MISMATCH`, `BOUNDARY_REFUSED`. A complete, readable HTTP response whose status falls
outside 2xx/3xx has no member of its own in that list; `LocalHttpUrlSourceAdapter` reports it as
`MALFORMED` (the response failed to honestly answer the bounded question asked), carrying the
real `response_status` alongside it so nothing about the real status code is lost. This is a
disclosed narrowing, not a silent one.

### 6.3 `human_authority_ref`, not a fabricated `project_binding_ref`, is the Evidence target

Runtime's own `target_identity` carries a `project_binding_ref` field of its own, which its
Evidence hand-off uses as `target_refs`/`input_refs`. This package's `source_identity` is a
generic URL decomposition (scheme/host/port/path/query/fragment) with no such field, and the
committed Envelope itself carries no `project_binding_ref` either -- so `evidence_handoff.py`
uses `human_authority_ref`, the one existing-owner reference the Envelope actually stores,
mirroring the identical "no separate canonical Difference/Change/Evidence subject" judgment call
Runtime's own hand-off already makes for its own target's owning Binding.

### 6.4 Redaction, then field-boundary projection, both before any fingerprint

`_project_to_permitted_fields` runs before `_redact` in `route.py`, and both run before
`observed_content_fingerprint` is ever computed -- the identical order Runtime's own P15-R1-F3
correction established. A field the Boundary never permitted at all is a refusal
(`UrlBootAdapterError`), never silently dropped; a field the Boundary marked for redaction is
replaced with `"<REDACTED>"` before it is ever hashed or persisted.

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
  and commit correctly, that the route fails closed on a malformed/out-of-vocabulary adapter
  report and on a field the Boundary never permitted, and that a redirect-hop count exceeding
  the Boundary's own bound is refused.
- **V3** proves at least one genuine positive (`OBSERVED`), one genuine per-hop-reauthorized
  redirect follow, one genuine redirect *escape refusal*, one genuine `UNSUPPORTED_MEDIA_TYPE`,
  one genuine `OVERSIZED_RESPONSE`, and one genuine `CONNECTION_FAILURE` -- each a real network
  round trip over `127.0.0.1` through this package's own `network.fetch_one_hop` (no VPS, no
  cloud target) -- then hands the positive receipt off to the existing Evidence owner.
- **V4** proves authority freshness (pre-adapter and pre-commit, plus a harmless-contention
  control), a genuine DNS-rebinding/loopback refusal, zero-adapter-call refusal of userinfo/
  out-of-scope-host/port/scheme sources, the three-way envelope-identity tamper check (applied
  from this package's own start, per §3.5), cross-project relabeling refusal, and that hostile-
  looking fetched content is stored as an inert, unexecuted string.
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
- that fetched content means anything. `IDENTITY_MISMATCH`/`BOUNDARY_REFUSED` are the adapter's
  own honest transport-layer classification, never a route-computed judgment about content
  (§3.4); no owner in this package's own call graph ever passes a fetched field to `eval`, a
  template engine, or a shell.
- that a redirect chain is ever followed unbounded, or that any redirect target is trusted
  before it is itself re-validated against the identical closed `network_scope`.
- that this layer can mint Authority, invoke a model, execute a Change, or bypass Evidence. It
  imports none of `authority`, `change`, `model_runtime`, or `reflow`, and its own Evidence
  hand-off resolves a real, integrity-checked, committed Envelope before constructing any
  provenance at all.
- that credentials of any kind are ever transmitted. `credentials_permitted` is schema-fixed to
  `false`, and a userinfo-bearing URL is refused before any resolution is attempted.
- that this layer is resistant to a hostile *DNS server* the caller's own environment already
  trusts, or to a compromised TLS certificate authority. What is proved is that the address this
  package connects to is the exact address its own single, un-repeated resolution returned, and
  that TLS certificate verification runs against the real hostname -- not that DNS or the CA
  system themselves are trustworthy inputs.

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

`MERGE_ALLOWED`, `ISSUE_CLOSE_ALLOWED`, `PHASE_17_COMPLETE` and `PHASE_18_ALLOWED` are fixed at
`false` by the adopting authority and are not this document's to change.
