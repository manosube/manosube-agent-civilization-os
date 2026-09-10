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
STRUCTURAL_REVIEW_ROUNDS_APPLIED=0
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
  → one bounded, per-hop-reauthorized HTTP GET, resolved exactly once per hop, connected to the
    exact address that resolution returned
    → whatever came back is classified honestly into one of eleven closed outcomes -- never
      reinterpreted as meaningful by this layer itself
      → the result is a canonical, committed URL Source Observation Envelope
        → handed off, unchanged, to the existing Evidence owner
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
package makes no equivalent claim about a URL: `IDENTITY_MISMATCH`/`BOUNDARY_REFUSED` are the
*adapter's own* honest, per-hop transport classification, never a route-computed verdict about
what fetched content means (`URL_BOOT_CONTRACT.md` §3.4).

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
                                   this package produces. No Human-declared deployment-identity
                                   record exists here (contrast Runtime); the closed fetch
                                   Boundary is the only Human-declared input, and it is a
                                   caller-supplied, schema-validated argument, never a
                                   Store-resolved record of its own.
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
URL_FETCH_METHODS       HTTP_GET_BOUNDED
URL_FETCH_OUTCOMES      OBSERVED, DNS_FAILURE, CONNECTION_FAILURE, TLS_FAILURE, TIMEOUT,
                        REDIRECT_REFUSED, OVERSIZED_RESPONSE, UNSUPPORTED_MEDIA_TYPE,
                        MALFORMED, IDENTITY_MISMATCH, BOUNDARY_REFUSED
RECEIPT_STATUSES        VERIFIED, FAILED, UNAVAILABLE
```

Every `URL_FETCH_OUTCOMES` member maps to exactly one `RECEIPT_STATUSES` member
(`URL_OUTCOME_TO_RECEIPT_STATUS`) -- the one shared classification both `route.py` and
`evidence_handoff.py` read, so neither module can disagree with the other about what a given
outcome means for Evidence.

---

## 5. Explicit non-claims

Restated here so the index and the contract cannot drift; `URL_BOOT_CONTRACT.md` §8 is the full
list.

- No signed deployment-declaration chain exists here; a URL Source Observation attests only to
  what a bounded fetch actually returned.
- Fetched content means nothing on its own -- no owner in this package's own call graph ever
  passes it to `eval`, a template engine, or a shell.
- No redirect is ever followed unbounded or unvalidated against the closed `network_scope`.
- This layer cannot mint Authority, invoke a model, execute a Change, or bypass Evidence -- it
  imports none of `authority`, `change`, `model_runtime`, or `reflow`.
- No credentials are ever transmitted; `credentials_permitted` is schema-fixed to `false`.
- This layer is not resistant to a hostile DNS server or a compromised certificate authority the
  caller's own environment already trusts -- what is proved is single-resolution,
  connect-to-that-exact-address discipline and real hostname-bound TLS verification, not that
  DNS or the CA system are themselves trustworthy inputs.

```text
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_17_COMPLETE=false
PHASE_18_ALLOWED=false
```
