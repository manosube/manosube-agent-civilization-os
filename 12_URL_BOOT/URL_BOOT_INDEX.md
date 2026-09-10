# Read-only URL Boot and Untrusted Content Boundary Index (Phase 17, Issue #69)

```text
DOC_TYPE=URL_BOOT_INDEX
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=URL-BOOT-INDEX-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_URL_BOOT_ADAPTER
CANONICAL_KERNEL_COUNT=1
URL_BOOT_OWNER_COUNT=1
PUBLIC_URL_BOOT_ENTRY_POINT_COUNT=2
SIGNED_DEPLOYMENT_DECLARATION_CHAIN=false
STRUCTURAL_REVIEW_ROUNDS_APPLIED=3
```

---

## 0. What this document is

This is the one entry point for the **Read-only URL Boot and Untrusted Content Boundary**
contract set -- the two documents under `12_URL_BOOT/` that define how a URL may be used as a
bounded, read-only external observation source without ever becoming a canonical source of
State, Difference, Change, Authority, Evidence, or a model invocation.

```text
1. URL_BOOT_INDEX.md      (this document)
2. URL_BOOT_CONTRACT.md   the two public entry points, their frozen semantics, the canonical
                           route, the disclosed judgment calls, the required proof layers, the
                           explicit non-claims, and Gate 17
```

The human objective this Phase serves, in the adopting authority's own terms:

```text
an explicit, closed fetch Boundary names exactly what may be reached and what may be kept
  → the route itself owns the entire redirect loop, one bounded single-hop transport call per
    hop, resolved exactly once per hop and bound to its own (host, port) for that fetch,
    connected to the exact address that resolution returned
    → the route itself classifies whatever came back into one of eleven closed outcomes -- an
      adapter can report only a bounded transport fact, never a content/identity verdict
      → OBSERVED only: the result is a canonical, committed URL Source Observation Envelope,
        binding the exact Project/Binding/Boot context it was made under
        → handed off, unchanged, to the existing Evidence owner
      → anything else: bounded, ephemeral, non-committed evidence -- zero canonical State
        mutation, never eligible for Evidence hand-off
```

---

## 1. This is not a ninth Kernel element

The Kernel is fixed at eight (`KERNEL_ELEMENT_COUNT=8`,
`ONE_KERNEL_ELEMENT_PER_PACKAGE=true`), and this package declares
`KERNEL_ELEMENT=NONE_URL_BOOT_ADAPTER` -- the same `none`-style convention Boot, the CLI, Agent
Runtime, Independent Verification, Projection, Runtime, and Model Runtime already use for their
own adapter layers.

What that means concretely: this layer validates no Project, restores no State, evaluates no
Change permission, judges no Evidence sufficiency, closes no Difference, mints no Authority, and
invokes no model. Each of those remains its existing owner's own, one-owner concern, and this
layer reaches every one of them only through that owner's own public surface.

---

## 2. This is not a second State, Difference, Authority, Evidence, Store, or Closure owner

| Existing owner | How this layer reaches it | What this layer never does |
|---|---|---|
| State / Store | `store.commit.commit_state_transition`, one call site | never calls `store.commit` directly, never writes a file, never builds a second persistence path |
| Boot | `boot_project`, one literal call site in `route.py` | never imports `boot_project` anywhere else in this package |
| Authority | not at all | never imports `authority`; mints no Authority Decision, resolves no grant |
| Change / Reflow | not at all | no module here imports either |
| Model Runtime | not at all | fetched content invokes no model, opens no Work Unit |
| Evidence | `derive_evidence`, one call site, in the Change-free position | never judges sufficiency, never supplies its own accepting provenance |

---

## 3. This is not a runtime-deployment identity chain, and not a general HTTP client

```text
SIGNED_DEPLOYMENT_DECLARATION_CHAIN=false
CREDENTIAL_TRANSMISSION_PERMITTED=false
```

Runtime's own `runtime_deployment_declaration` is a canonical, Human-Authority-signed,
Store-committed record a target's own claimed identity must match before it is trusted. This
package makes no equivalent claim about a URL. `IDENTITY_MISMATCH` and every other content-level
classification are route-derived, from bounded, single-hop transport facts alone (Structural
Review Round 1, P17-R1-F2) -- never accepted as a direct assertion from whatever reported them.
`BOUNDARY_REFUSED` is, since Structural Review Round 2 (P17-R2-F1), *also* route-derived -- the
replaceable adapter reports only a genuine DNS resolution result; since Structural Review Round 3
(P17-R3-F1), the genuine connection outcome is reported by the trusted network layer itself,
never the adapter, which no longer has any connection capability at all. The route alone
classifies a resolved address's own safety and detects cross-hop resolution drift, never
accepting either as an adapter-asserted outcome. See `URL_BOOT_CONTRACT.md`
§3.4/§6.2/§10.1/§11.1.

This is also not a general-purpose HTTP client: one bounded method
(`HTTP_GET_BOUNDED`), one closed content-type allowlist, one closed permitted-field projection,
a hard response-byte cap, a bounded redirect count, and a schema-fixed
`credentials_permitted: false`. A userinfo-bearing URL is refused before any resolution is
attempted.

---

## 4. Canonical owner

### 4.1 The two public entry points

```text
observe_url_source                 one bounded, per-hop-reauthorized HTTP GET against an
                                    explicit source, under an explicit closed fetch Boundary
route_url_observation_to_evidence  hand the receipt to the existing Evidence owner
```

### 4.2 The one canonical record

```text
url_source_observation_envelope   The committed URL Source Observation -- the only record kind
                                   this package produces, and only ever for fetch_outcome ==
                                   "OBSERVED" (P17-C7/P17-R1-F1: no failed or refused fetch ever
                                   commits one). No Human-declared deployment-identity record
                                   exists here (contrast Runtime); the closed fetch Boundary is
                                   the only Human-declared input, and it is a caller-supplied,
                                   schema-validated argument, never a Store-resolved record of
                                   its own. Carries project_binding_ref/boot_state_fingerprint/
                                   boot_state_transition_ref (the exact Boot-observed context,
                                   P17-R1-F5, independently re-resolved and re-verified at
                                   Evidence handoff, P17-R2-F3) and resolution_provenance (the
                                   admitted per-(host, port) DNS resolution across every hop,
                                   P17-R1-F4).
```

### 4.3 The four identities

```text
url_source_fingerprint                                  what was asked for / what was reached
url_boundary_fingerprint                                the closed fetch Boundary's own identity
url_source_request_identity                              source + Boundary + issued_at, computable
                                                          before the adapter is ever called
url_source_observation_envelope_id / _semantic_fingerprint   the committed fact
```

Every envelope projection is the complete record minus its own two digest fields, so every
outcome field, every reference field, and every identity field this record carries participates
in both digests. There is no field a record can carry that its own identity does not see.

### 4.4 The closed vocabularies

```text
URL_FETCH_METHODS         HTTP_GET_BOUNDED
URL_FETCH_OUTCOMES        OBSERVED, DNS_FAILURE, CONNECTION_FAILURE, TLS_FAILURE, TIMEOUT,
                          REDIRECT_REFUSED, OVERSIZED_RESPONSE, UNSUPPORTED_MEDIA_TYPE,
                          MALFORMED, IDENTITY_MISMATCH, BOUNDARY_REFUSED
URL_HOP_RESOLVE_OUTCOMES     DNS_FAILURE, RESOLVED -- what an adapter's own resolve_hop may
                          ever report (P17-R2-F1); the route alone classifies a RESOLVED
                          address's own safety, never accepting BOUNDARY_REFUSED as an
                          adapter-asserted outcome.
URL_HOP_CONNECT_OUTCOMES     CONNECTION_FAILURE, TLS_FAILURE, TIMEOUT, RESPONSE -- what the
                          route's own connection primitive, given the route's own admitted
                          address, may ever report. Since Structural Review Round 3 (P17-R3-F1),
                          this primitive is the trusted network layer itself
                          (network.perform_admitted_connection) in production, never the
                          replaceable adapter -- an adapter no longer has a connection
                          capability of any kind. Every other URL_FETCH_OUTCOMES member is
                          route-derived from a genuine RESPONSE.
RECEIPT_STATUSES          VERIFIED, FAILED, UNAVAILABLE
```

Every `URL_FETCH_OUTCOMES` member maps to exactly one `RECEIPT_STATUSES` member
(`URL_OUTCOME_TO_RECEIPT_STATUS`) -- the one shared classification both `route.py` and
`evidence_handoff.py` read, so neither module can disagree with the other about what a given
outcome means for Evidence. Only `"OBSERVED"` (status `"VERIFIED"`) ever names a committed
Envelope; `route_url_observation_to_evidence` itself refuses any receipt whose own status is not
`"VERIFIED"` (P17-C7/P17-R1-F1).

---

## 5. Explicit non-claims

Restated here so the index and the contract cannot drift; `URL_BOOT_CONTRACT.md` §8 is the full
list.

- No signed deployment-declaration chain exists here; a URL Source Observation attests only to
  what a bounded fetch actually returned.
- Fetched content means nothing on its own -- no owner in this package's own call graph ever
  passes it to `eval`, a template engine, or a shell. Content classification (`IDENTITY_MISMATCH`
  and friends) is route-derived from bounded facts, never an adapter's own assertion
  (P17-R1-F2).
- No redirect is ever followed unbounded or unvalidated against the closed `network_scope` --
  the route itself re-validates every redirect target before the adapter is ever reached for it,
  so a disallowed intermediate hop is never even called (P17-R1-F2).
- This layer cannot mint Authority, invoke a model, execute a Change, or bypass Evidence -- it
  imports none of `authority`, `change`, `model_runtime`, or `reflow`.
- No credentials are ever transmitted; `credentials_permitted` is schema-fixed to `false`.
- This layer is not resistant to a hostile DNS server or a compromised certificate authority the
  caller's own environment already trusts -- what is proved is single-resolution,
  connect-to-that-exact-address discipline per hop, that the identical `(host, port)` never
  resolves to two different addresses within one fetch (P17-R1-F4), and real hostname-bound TLS
  verification -- not that DNS or the CA system are themselves trustworthy inputs.
- A failed or refused fetch is never recorded anywhere durable; it is bounded, ephemeral,
  in-memory evidence only, and can never be handed off as Evidence (P17-C7/P17-R1-F1).
- No caller who only supplies `source_identity`/`boundary`/`adapter` to public
  `observe_url_source` can ever enable a loopback fetch (P17-R1-F3, P17-R2-F2) -- no field, no
  keyword, no positional argument, and no adapter constructor argument reaches it any more; the
  one exception lives behind a composition boundary (`compose_disposable_local_test_observer`,
  P17-R3-F2) that this repository no longer even ships -- it is confirmed absent from the
  distributed wheel (`tests/fixtures/`, sdist-only), so no production install carries it at all.
- A replaceable adapter has no capability to create a network connection of any kind, and
  therefore no way to fabricate a plausible response while claiming to have reached the
  route-admitted address -- since Structural Review Round 3 (P17-R3-F1), the trusted network
  layer itself creates every real connection this package ever makes, in both public entry
  points; an adapter's own `resolve_hop` reports an address, nothing more.
- A genuinely self-consistent, genuinely committed Envelope is not itself sufficient corroboration
  for Evidence -- its referenced Project Binding and historical Boot-observed State are
  independently re-resolved through this Store's own real, canonical history before any Evidence
  is derived (P17-R2-F3); a copied-but-uncorroborated Envelope is refused even though its own
  content hash is genuine.

```text
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_17_COMPLETE=false
PHASE_18_ALLOWED=false
```
