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
Event or a Closure Evaluation, and mutates the Store exactly once, through the existing
Store's own single sanctioned committer (`store.commit.commit_state_transition` -- the
identical primitive Reflow and Binding already share), and only to persist a genuinely new
Projection Envelope. It resolves the one Store-owned subject reference kind
(`observation_evidence`) through the existing Store's own read-only `resolve_record` -- the
identical, already-established surface Boot and Independent Verification already call -- and
admits a `difference`/`change` subject from the caller-supplied real record body, independently
schema-validated and identity-recomputed through the existing Difference/Change owners' own
identity functions, never Store-resolved by this package itself (Structural Review Round 1,
P14-R1-F2, since neither is a Store-owned record kind in this vertical). It calls the existing
Boot owner's own `boot_project` exactly once to independently re-verify the real Human
Authority reference (the identical pattern Independent Verification's own Structural Review
Round 1, P13-R1-F2, already established), and it does evaluate one Authority Decision -- not a
Change-permission one, but a `github_projection_grant`-bound `evaluate_projection_authorization`
(Structural Review Round 1, P14-R1-F1, an extension of the existing Authority owner, never a
new one) gating every projection operation. It calls its one explicit `GitHubAdapter` at most
three times per request (`find_by_correlation_key` at most once, `materialize` at most once,
`observe` exactly once). `route_observation_receipt_to_evidence` calls the existing Evidence
owner's own public `derive_evidence` exactly once, over a caller-supplied, already-real,
Change-free request grounded in the existing Change-Free Verification Evidence position --
never a second Evidence owner.

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
├── observable.py           expected_observable_projection / expected_observable_fingerprint
│                           (Structural Review Round 1, P14-R1-F3/F7)
├── engine.py               derive_projection_envelope -- pure, no Store/Boot/Adapter I/O
├── github_adapter.py       FakeGitHubAdapter (controlled, in-memory) and RealGitHubAdapter
│                           (stdlib urllib only) -- the two GitHubAdapter implementations
├── receipt_handoff.py      route_observation_receipt_to_evidence -- the one public
│                           GitHubObservationReceipt-to-Evidence handoff
└── route.py                project_to_github -- the one public projection route

src/manosube_agent_civilization/authority/
└── projection_authorization.py   evaluate_projection_authorization (Structural Review
                                    Round 1, P14-R1-F1) -- an extension of the existing
                                    Authority owner, not a new one
```

No second Boot, Store, Binding, Evidence, Difference, Authority, or Reflow owner is created
anywhere in this package. `reflow`, `binding`, and `independent_verification` are never
imported by any module in this package. `difference`/`change` are importable only from
`route.py`, and only for their own read-only identity/fingerprint functions
(`difference.identity`/`change.identity`) -- never `difference.engine`, `difference.graph`, or
`change.engine` (Structural Review Round 1, P14-R1-F2); `difference.validation` remains the
one shared canonical-schema-validator exception every owner module in this repository already
reuses, not a reuse of the Difference owner's own semantic engine. `evidence` is importable
only from `route.py` (read-only `evidence.identity.evidence_semantic_fingerprint`, to
recompute an `observation_evidence` subject's own real fingerprint) and
`receipt_handoff.py` (the one `derive_evidence` call). `boot` is importable only from
`route.py`, and only to call `boot_project` exactly once. `authority` is importable only from
`route.py`, and only to call `evaluate_projection_authorization` exactly once (Structural
Review Round 1, P14-R1-F1). A network/transport surface (`urllib`) is importable only from
`github_adapter.py` -- static conformance proves all of this by AST walk, the identical
technique
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
EVIDENCE_ARTIFACT_MATERIALIZE_IMPLEMENTED_ON_REAL_ADAPTER=true
DIFFERENCE_SUBJECT_FINGERPRINT_INDEPENDENTLY_RECONSTRUCTED=true
CHANGE_SUBJECT_FINGERPRINT_INDEPENDENTLY_RECONSTRUCTED=true
GITHUB_PROJECTION_AUTHORITY_DECISION_IMPLEMENTED=true
RECOVERABLE_IDEMPOTENCY_ACROSS_EXTERNAL_WRITE_BOUNDARY_IMPLEMENTED=true
TYPED_OBSERVATION_OUTCOMES_IMPLEMENTED=true
GENUINE_SHA256_OBSERVABLE_FINGERPRINT_IMPLEMENTED=true
CROSS_PROJECT_RECEIPT_RELABELING_REFUSED=true
SIGNED_HUMAN_DECLARATION_ANCHOR_FOR_GITHUB_PROJECTION_GRANT_IMPLEMENTED=true
ATOMIC_RECOVERABLE_PROJECTION_CLAIM_STATE_MACHINE_IMPLEMENTED=true
RECEIPT_HANDOFF_INDEPENDENTLY_RESOLVED_AGAINST_COMMITTED_ENVELOPE=true
EXTERNAL_ARTIFACT_LOCATOR_GRAMMAR_VALIDATED=true
CORRELATION_MARKER_ROUND_TRIP_FIXED=true
TRANSPORT_LEVEL_GITHUB_CONTRACT_FIXTURES_IMPLEMENTED=true
V3_TARGET_BOUND_CONFIGURATION_IMPLEMENTED=true
EXPLICIT_CLAIM_TOKEN_INDEPENDENT_OF_TIMESTAMP_IMPLEMENTED=true
RECEIPT_HANDOFF_INDEPENDENTLY_RE_OBSERVED_NEVER_TRUSTED_FROM_RECEIPT=true
V3_CONFIGURATION_CONTRACT_VALIDATED_ZERO_NETWORK_ACCESS=true
TERMINAL_CLAIM_TOKEN_BOUND_TO_ENVELOPE_IMPLEMENTED=true
SAME_ATTEMPT_RETRY_SEPARATED_FROM_SEMANTIC_REUSE_IMPLEMENTED=true
RECEIPT_ATTESTATION_EXACT_MATCH_REQUIRED_BEFORE_VERIFIED_EVIDENCE=true
V3_LIVE_ADAPTER_TESTS_GATED_BY_RUNTIME_CHECK_NOT_UNCONDITIONAL_SKIP=true
V3_ARTIFACT_KINDS_AND_COUNT_AND_CLEANUP_AND_NO_MERGE_BOUND_AS_CONFIGURATION_FIELDS=true
PHASE_14_COMPLETE=false
PHASE_15_ALLOWED=false
```

The last five lines before the Round 2 additions above record Structural Review Round 1's own
corrections (Issue #62, `ADOPT_P14_R1_CANONICAL_AUTHORITY_SUBJECT_AND_RECOVERABLE_PROJECTION`)
-- see `PROJECTION_CONTRACT.md` §3 items 13-17 for the full frozen semantics each one fixes.
The seven `..._IMPLEMENTED`/`..._FIXED`/`..._VALIDATED` lines after those record Structural
Review Round 2's own corrections (`ADOPT_P14_R2_SIGNED_AUTHORITY_ATOMIC_PROJECTION_AND_REAL_
V3`) -- see `PROJECTION_CONTRACT.md` §10 for the full detail each one fixes.
`V3_TARGET_BOUND_CONFIGURATION_IMPLEMENTED` was `false` at the end of Round 2, disclosed as a
deliberately-unclosed item; it is now `true`. The three lines immediately above it record
Structural Review Round 3's own corrections
(`ADOPT_P14_R3_UNIQUE_CLAIM_ATTESTED_RECEIPT_AND_CONFIGURABLE_V3`) -- see
`PROJECTION_CONTRACT.md` §11 for the full detail each one fixes, including a correction to
Round 2's own mistaken belief that its F2 (atomic claims) and F3 (receipt corroboration) were
already fully closed. `V3_LIVE_EXTERNAL_WRITE_AUTHORITY=false` still holds, unchanged by any
of this: `V3_TARGET_BOUND_CONFIGURATION_IMPLEMENTED=true` closes the *configuration*
requirement only, never live-write authorization.
The five lines immediately above `PHASE_14_COMPLETE` record Structural Review Round 4's own
corrections (`ADOPT_P14_R4_TERMINAL_CLAIM_ATTESTED_RECEIPT_AND_SOURCE_EDIT_FREE_V3`) -- see
`PROJECTION_CONTRACT.md` §12 for the full detail each one fixes, including a correction to
Round 3's own mistaken belief that its F1 (claim ownership), F2 (receipt corroboration), and
F3 (V3 configuration) were already fully closed. `V3_LIVE_ADAPTER_TESTS_GATED_BY_RUNTIME_
CHECK_NOT_UNCONDITIONAL_SKIP=true` and `V3_LIVE_EXTERNAL_WRITE_AUTHORITY=false` both hold
together, unchanged by any of this: the real-adapter tests are now gated by a fail-closed
runtime check reading the environment rather than a hardcoded skip, but that gate still
evaluates `False` in this delivery -- no live write occurs.
`PHASE_14_COMPLETE` and `PHASE_15_ALLOWED` remain `false`: these correction rounds close their
own respective structural findings, not Phase 14 itself, which still awaits a separate SHUKOU
decision.
