# Identity-Preserving GitHub Projection Index (Phase 14, Issue #62)

```text
DOC_TYPE=PROJECTION_INDEX
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=PROJECTION-INDEX-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=NONE_PROJECTION_ADAPTER
CANONICAL_KERNEL_COUNT=1
PROJECTION_OWNER_COUNT=1
PUBLIC_PROJECTION_ENTRY_POINT_COUNT=1
```

---

## 0. What this document is

This is the one entry point for the **Identity-Preserving GitHub Projection** contract set --
the two documents under `09_PROJECTION/` that define how an already-real canonical
Difference/Change/Evidence subject is projected to a GitHub Issue/Pull Request/artifact
without losing identity or lineage, while GitHub itself remains a projection/audit surface
only, never canonical.

```text
1. PROJECTION_INDEX.md      (this document)
2. PROJECTION_CONTRACT.md   the one public route, its frozen semantics, and its negative
                             controls
```

Read `PROJECTION_CONTRACT.md` for the load-bearing design; this document only fixes this
layer's own position relative to the rest of the Kernel and to Boot, Store, Evidence, and
Independent Verification.

## 1. This is not a ninth Kernel element

`00_KERNEL/KERNEL_INDEX.md` §4 fixes exactly eight Kernel elements (Objective through
Reflow). Identity-Preserving GitHub Projection is not a ninth -- the same
`KERNEL_ELEMENT=none`-style convention Boot, the CLI, the Temporary Agent lifecycle, and
Independent Verification already use (here spelled `NONE_PROJECTION_ADAPTER`, since it is
specifically an outward projection of already-real canonical facts, never a persisted or
authoritative owner of any of them). It does not appear in `00_KERNEL/`'s own numbered
reading order, and it redefines no Kernel Contract's own semantics.

```text
KERNEL_ELEMENT=NONE_PROJECTION_ADAPTER
CANONICAL_KERNEL_COUNT=1
```

## 2. This is not a second State, Difference, Authority, Evidence, Store, or Closure owner

`project_to_github` never mints canonical Difference/Change/Evidence content, never evaluates
Evidence sufficiency, never evaluates a Closure Policy, never emits a Difference Lifecycle
Event or a Closure Evaluation, never evaluates a Change-permission Authority Decision, and
mutates the Store exactly once, through the existing Store's own single sanctioned committer
(`store.commit.commit_state_transition` -- the identical primitive Reflow and Binding already
share), and only to persist a genuinely new Projection Envelope. It resolves exactly one
Store-owned reference kind (`observation_evidence`) through the existing Store's own read-only
`resolve_record` -- the identical, already-established surface Boot and Independent
Verification already call -- calls the existing Boot owner's own `boot_project` exactly once
to independently re-verify the real Human Authority reference (the identical pattern
Independent Verification's own Structural Review Round 1, P13-R1-F2, already established),
and calls its one explicit `GitHubAdapter` at most twice per request (`materialize` at most
once, `observe` exactly once). `route_observation_receipt_to_evidence` calls the existing
Evidence owner's own public `derive_evidence` exactly once, over a caller-supplied,
already-real, Change-free request grounded in the existing Change-Free Verification Evidence
position -- never a second Evidence owner.

```text
PROJECTION_IS_A_SECOND_STATE_OWNER=false
PROJECTION_IS_A_SECOND_DIFFERENCE_OWNER=false
PROJECTION_IS_A_SECOND_AUTHORITY_OWNER=false
PROJECTION_IS_A_SECOND_EVIDENCE_OWNER=false
PROJECTION_IS_A_SECOND_STORE_OWNER=false
PROJECTION_IS_A_SECOND_CLOSURE_OWNER=false
GITHUB_IS_CANONICAL=false
GITHUB_IS_PROJECTION_AND_AUDIT_SURFACE_ONLY=true
PROJECTION_RESULT_IS_EVIDENCE=false
PROJECTION_RESULT_IS_AUTHORITY_DECISION=false
PROJECTION_RESULT_IS_CLOSURE_RECEIPT=false
PROJECTION_RESULT_IS_MERGE_AUTHORIZATION=false
```

## 3. This is not automatic merge, automatic closure, or a fixed adapter

No product, transport, or GitHub App identity is selected by this Phase. A `GitHubAdapter`
is always supplied by the caller; `project_to_github` never merges a Pull Request, never
closes a GitHub Issue, never closes a canonical Difference, and never selects, defaults,
infers, or falls back to an adapter implementation of its own.

```text
FIXED_ADAPTER_IMPLEMENTED=false
AUTOMATIC_MERGE_IMPLEMENTED=false
AUTOMATIC_GITHUB_ISSUE_CLOSE_IMPLEMENTED=false
AUTOMATIC_DIFFERENCE_CLOSURE_IMPLEMENTED=false
```

## 4. Canonical owner

```text
src/manosube_agent_civilization/projection/
├── __init__.py           public exports
├── errors.py              ProjectionError / ProjectionRequirementError /
│                           ConflictingProjectionPayloadError / ProjectionValueError /
│                           ProjectionAdapterError
├── types.py               vocab frozensets, GitHubAdapter Protocol,
│                           GitHubObservationReceipt -- immutable, non-persisted value types
├── identity.py             projection_mapping_key / projection_envelope_id /
│                           projection_envelope_semantic_fingerprint /
│                           projection_payload_fingerprint
├── engine.py               derive_projection_envelope -- pure, no Store/Boot/Adapter I/O
├── github_adapter.py       FakeGitHubAdapter (controlled, in-memory) and RealGitHubAdapter
│                           (stdlib urllib only) -- the two GitHubAdapter implementations
├── receipt_handoff.py      route_observation_receipt_to_evidence -- the one public
│                           GitHubObservationReceipt-to-Evidence handoff
└── route.py                project_to_github -- the one public projection route
```

No second Boot, Store, Binding, Evidence, Difference, Authority, or Reflow owner is created
anywhere in this package. `difference`, `reflow`, `binding`, and `authority` are never
imported by any module in this package (`difference.validation` is the one exception --
the shared canonical-schema-validator registry every owner module in this repository already
reuses, not a reuse of the Difference owner's own semantic engine). `evidence` is importable
only from `route.py` (read-only `evidence.identity.evidence_semantic_fingerprint`, to
recompute an `observation_evidence` subject's own real fingerprint) and
`receipt_handoff.py` (the one `derive_evidence` call). `boot` is importable only from
`route.py`, and only to call `boot_project` exactly once. A network/transport surface
(`urllib`) is importable only from `github_adapter.py` -- static conformance proves all of
this by AST walk, the identical technique
`tests/contract/independent_verification/test_independent_verification_static_conformance.py`
already uses.

## 5. Explicit non-claims

```text
PROJECTION_ENVELOPE_IMPLEMENTED=true
GITHUB_ADAPTER_BOUNDARY_IMPLEMENTED=true
REAL_GITHUB_ADAPTER_IMPLEMENTED=true
REAL_GITHUB_ADAPTER_EXECUTED_AGAINST_A_LIVE_TARGET=false
V3_EXTERNAL_WRITE_ALLOWED_BY_THIS_DELIVERY=false
GITHUB_ISSUE_CLOSE_IMPLEMENTED=false
GITHUB_PULL_REQUEST_MERGE_IMPLEMENTED=false
DIFFERENCE_CLOSURE_FROM_GITHUB_STATE_IMPLEMENTED=false
NEW_STATE_OWNER=false
NEW_EVIDENCE_OWNER=false
NEW_AUTHORITY_OWNER=false
NEW_STORE_OWNER=false
EVIDENCE_ARTIFACT_MATERIALIZE_IMPLEMENTED_ON_REAL_ADAPTER=false
DIFFERENCE_SUBJECT_FINGERPRINT_INDEPENDENTLY_RECONSTRUCTED=false
CHANGE_SUBJECT_FINGERPRINT_INDEPENDENTLY_RECONSTRUCTED=false
PHASE_14_COMPLETE=false
PHASE_15_ALLOWED=false
```
