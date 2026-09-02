# ADR-0008: Scope freshness restoration and carried-Observation verification

```text
DOC_TYPE=EXTRACTION_REGRESSION_AND_ENGINE_CONFORMANCE_CORRECTION
DOCUMENT_ID=ADR-0008-DIFFERENCE-SCOPE-FRESHNESS-AND-CARRIED-OBSERVATIONS
STATUS=ACCEPTED
DECIDED_AT=2026-08-31
DECISION_AUTHORITY=HUMAN_CONSTITUTIONAL_AUTHORITY
KERNEL_ELEMENT=DIFFERENCE
SCHEMA_VERSION=0.1
ORIGIN_ISSUE=24
PREDECESSOR_DECISION=ADR-0007
SOURCE=INDEPENDENT_REVIEW_OF_56a204a
KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
```

## 0. Position

An independent review of head `56a204a` raised two P1 findings. The first is a
**regression this work introduced**: extracting a predicate into a shared authority under
ADR-0007 silently dropped one of its conditions. The second is an **Engine conformance
defect** on a route the earlier corrections did not reach.

Both were reproduced against `56a204a` before any correction, in a git worktree whose
`src` was placed ahead of the editable install so the measured code was the committed
code — an earlier attempt at this comparison silently loaded the working tree instead, and
its results were discarded.

No Kernel contract text and no schema changed. No identity algorithm changed. Every
existing Difference and Observation identity is unchanged, and the Observation Engine's
output on the fresh, in-Scope route is **byte-identical** to `f2b1d89`, the last head
before the extraction.

```text
KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
EXISTING_DIFFERENCE_IDENTITIES_CHANGED=0
EXISTING_OBSERVATION_IDENTITIES_CHANGED=0
CANONICAL_RECORD_MIGRATION_REQUIRED=false
```

## 1. Finding 1 - the extraction dropped the canonical Scope freshness limit

**Defect.** ADR-0007 moved `_time_boundary_complete` out of `observation/engine.py` into
`observation/boundary.py::time_boundary_within_scope`. The move was performed by a text
slice and never diffed against its source, so one of the seven conditions did not travel:

```text
and (cutoff - snapshot).total_seconds() <= scope["freshness_limit_seconds"]
```

The freshness limit is not implied by the cutoff. A snapshot may precede the cutoff and
still be older than the Scope permits, so with the condition gone a stale source was
reported time-boundary complete.

**Reproduced at `56a204a`**, helper Scope with `freshness_limit_seconds = 300` and
`cutoff = 09:00:00Z`, snapshot at `08:50:00Z` — 600 seconds old:

```text
time_boundary_within_scope(...)                  True
negative completion gate                         ALL TRUE
bounded absence produced                         ABSENT
Difference derived                               1
independent Difference validator                 []
independent Observation validator                []
```

Both auditors accepted it. The review expected the Difference validator to reject it; it
does hold the freshness rule, but only behind `_observation_attempts_complete`, which the
plain derivation route never reaches. The producer/consumer drift was therefore real and
the outcome worse than reported: on this route nothing caught it.

**Correction.** The condition is restored in the single shared authority, and the
predicate's obligations are now stated in its own docstring so a future extraction cannot
lose one silently. Three further hardenings were applied while restoring it:

```text
timezone-aware instants required   a naive instant fails closed instead of comparing
                                   against an aware one, or silently against another naive
freshness limit type-checked       a missing, boolean or non-numeric limit fails closed
time_boundary lookup inside try    a missing time boundary fails closed
```

The independent validator's own derivation received the identical hardenings, so the two
agree across a 60-case parity matrix rather than by inspection.

**Related, and beyond restoration.** A stale snapshot still produced a `COMPLETE` positive
Observation — at `f2b1d89` and on `main` as well, so this was **not** part of the
regression: `_observation_status` had never consulted the time boundary. An Observation
whose window, snapshot instant or snapshot freshness falls outside its own resolved Scope
has not completely observed that Scope, so the status now degrades to `INCOMPLETE` and
every downstream gate that requires completeness fails closed. This is a tightening of the
Observation element's status rule, recorded here because it is a decision rather than a
restoration.

```text
after correction, same stale input
  time_boundary_within_scope        False
  positive Observation status       INCOMPLETE   (was COMPLETE)
  bounded absence                   rejected: "ABSENT requires a complete bounded absence gate"
  Difference derivation             rejected: "Observation time boundary escapes the resolved Scope"
  fresh in-Scope route              byte-identical to f2b1d89
```

## 2. The rest of the extraction, audited

The review asked for confirmation that the extraction preserved every pre-extraction
predicate, not only the reported line. Each piece moved under ADR-0006 and ADR-0007 was
diffed against its source:

```text
_time_boundary_complete -> time_boundary_within_scope   ONE CONDITION LOST (restored above)
_validate_records       -> observation_record_errors    complete; only intended additions
_schema_root/_validators -> observation/schemas.py      complete; adds an lru_cache
observation record assembly (identity restructure)      output byte-identical to f2b1d89
```

The freshness limit was the only loss.

## 3. Finding 2 - a predecessor-only Observation was merged unverified

**Defect.** ADR-0007 verified every Observation the current bundle supplies or the context
closure reaches. An Observation arriving **only** through `predecessor.context` is neither:
it is not repeated by the current Observation bundle, so
`_require_context_agrees_with_observation_lineage` — which compares payloads only where
both name the same record — has nothing to compare it against, and `_merge` carried it
into the returned bundle as immutable provenance without identity or Scope validation.

**Reproduced at `56a204a`** on a material-change supersession whose predecessor Observation
comes from an independent earlier bundle:

```text
predecessor-only Observation, method_ref forged, observation_id retained
  identity recomputes                False
  merged into the returned bundle    True
  carried method_ref                 OBS-METHOD-FORGED
  independent Difference validator   []
```

**Correction.** One verification pass, `_validate_carried_observations`, runs once before
the bundle is finalised, over **every** Observation the bundle carries — the bound one,
every one the closure reached, and predecessor-only provenance alike. It is the single
owner of the property *every Observation in a returned bundle is verified*:

```text
scope_ref present and resolvable        else "has no resolvable Scope reference"
Scope record present in the bundle      else "names a Scope absent from the bundle"
Scope record schema-valid and self-naming
_validate_observation_boundary(observation, its own Scope, project_id)
  -> identity recomputation, schema version, project, Scope reference,
     declared method, exact source set, time boundary incl. freshness
observation_record_errors over the whole carried record set
```

Each Observation is verified against **the Scope it itself claims**, resolved from the
canonical records in the returned bundle — not against the current derivation's Scope. A
superseded Difference may legitimately have been observed under a different Scope; demanding
the current one would have made that canonical route unrepresentable, the failure mode
ADR-0002 and ADR-0005 both record.

Ambiguous Scope resolution cannot arise: Scopes are merged by id through the same
fail-closed rule, so two records sharing an id with different payloads are rejected before
resolution. Nothing is rewritten or repaired — a carried record that does not pass is a
forgery or an incomplete lineage, and either fails closed. Valid provenance, including the
superseded Difference itself, is returned byte-identically.

## 4. Proofs added

```text
tests/contract/difference/test_time_boundary_authority.py       34 cases
  - snapshot exactly at the freshness limit accepted; one second beyond rejected
  - fresh pre-cutoff and at-cutoff snapshots accepted
  - a zero freshness limit admits only the cutoff instant
  - 15 boundary violations rejected: after cutoff, beyond the observed interval,
    before the effective window, reversed and escaping windows, unparseable, naive,
    null and numeric instants, missing fields, missing time boundary
  - 5 malformed Scopes and a Scope missing a window fail closed
  - a 60-case parity matrix: the shared authority and the independent validator return
    the same verdict on every case, and the matrix exercises both verdicts
  - a regression test naming all seven obligations and the Scope contract's own
    time-boundary vocabulary
  - end to end: a stale snapshot yields INCOMPLETE, no bounded absence and no Difference,
    while a fresh one still yields COMPLETE

tests/unit/difference/test_predecessor_observation_context.py   24 cases
  - a valid predecessor-only Observation is accepted and returned byte-identically,
    and the superseded Difference stays byte-identical
  - the caller's context is never mutated
  - 8 identity-bearing fields forged with the id retained, each asserting the payload
    really changed and the identity really broke
  - an injected self-consistent record naming an absent Scope, carrying out-of-scope
    sources, a foreign method, a stale snapshot, another project, or a malformed Scope
    reference is rejected
  - a conflicting Scope record and a same-ID/different-payload record are rejected
  - an admissible extra provenance Observation is accepted and returned byte-identically
  - a transitively reached Observation is verified
  - the returned lineage is self-contained, cross-record valid and deterministic

tests/contract/difference/test_lifecycle_authority.py
  - exactly one carried-Observation verification pass, running before finalisation
  - every returned Observation recomputes and resolves its own Scope
```

## 5. Acceptance

```text
SCOPE_FRESHNESS_ENFORCED=true
TIME_BOUNDARY_AUTHORITY_COUNT=1
TIME_BOUNDARY_PARITY_PROVEN=true
TIME_BOUNDARY_ARITHMETIC_FAILS_CLOSED=true
NAIVE_INSTANT_REJECTED=true
STALE_SNAPSHOT_CANNOT_REACH_COMPLETE=true
STALE_SNAPSHOT_CANNOT_REACH_BOUNDED_ABSENCE=true
STALE_SNAPSHOT_CANNOT_REACH_A_DIFFERENCE=true
EXTRACTION_AUDITED_AGAINST_SOURCE=true
FRESH_ROUTE_BYTE_IDENTICAL_TO_PRE_EXTRACTION=true

CARRIED_OBSERVATION_VERIFICATION_PASS_COUNT=1
PREDECESSOR_ONLY_OBSERVATION_VERIFIED=true
CARRIED_OBSERVATION_SCOPE_RESOLVED=true
ABSENT_SCOPE_REJECTED=true
AMBIGUOUS_SCOPE_REJECTED=true
OUT_OF_SCOPE_CARRIED_SOURCE_REJECTED=true
PREDECESSOR_RECORDS_NEVER_REPAIRED=true
VALID_PROVENANCE_BYTE_IDENTICAL=true

KERNEL_CONTRACT_FILES_CHANGED=0
SCHEMA_FILES_CHANGED=0
IDENTITY_ALGORITHM_CHANGED=false
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
CLOSURE_EVALUATION_IMPLEMENTED=false
REFLOW_IMPLEMENTED=false
```

```text
DIFFERENCE_RUNTIME_PROVEN=false
KERNEL_V0_1_COMPLETE=false
```

## 6. What this ADR does not claim

The Observation status tightening in section 1 changes when an Observation reports
`COMPLETE` or `EMPTY`. It is a tightening: no input that previously failed now passes.
No Completion gate was relaxed, no enum changed, and Objective Completion remains a later
owner's responsibility.
