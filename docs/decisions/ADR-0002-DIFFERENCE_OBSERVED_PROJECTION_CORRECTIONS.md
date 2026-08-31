# ADR-0002: Difference observed-projection and Evidence-channel corrections

```text
DOC_TYPE=SCHEMA_AND_CONTRACT_CORRECTION_DECISION
DOCUMENT_ID=ADR-0002-DIFFERENCE-OBSERVED-PROJECTION-CORRECTIONS
STATUS=ACCEPTED
DECIDED_AT=2026-08-31
DECISION_AUTHORITY=HUMAN_CONSTITUTIONAL_AUTHORITY
KERNEL_ELEMENT=DIFFERENCE
SCHEMA_VERSION=0.1
ORIGIN_ISSUE=24
SOURCE=IMPLEMENTATION_DISCOVERED_CONTRADICTION
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
```

## 0. Human constitutional approval

The repository owner, acting on Structural Advisor acceptance of Issue #24, directed that two
implementation-discovered contradictions be resolved as contract and schema authority
corrections inside the same vertical Difference package, with explicit migration and version
compatibility analysis, and without weakening Completion semantics or introducing a parallel
owner.

The Agent does not originate, broaden, or revoke that authority. This ADR records the
correction; it does not grant itself the right to make further contract changes.

## 1. Why a correction was required

Both defects made a route that the Kernel contracts explicitly declare canonical impossible to
represent. Neither could be fixed in the Engine alone: any Engine-only workaround would have had
to either emit a record that fails cross-record conformance, or keep rejecting a required route.

### Difference A — the pure-negative route was canonically unreachable

`DIFFERENCE_CONTRACT.md` §4 states that Observed State is projected from Normalized Facts **and
bounded Negative Observations**. The pure-negative route (no positive Fact) was therefore
intended to be canonical.

It was not reachable. `difference_contract_validator.validate_bundle` required, whenever no
positive Fact existed:

```text
{negative_observation.negative_evidence_refs} == {observation.observation_evidence_refs}
{negative_observation_evaluation.evidence_refs} ⊆ {observation.observation_evidence_refs}
```

The Observation Engine pins those two channels to different reference kinds
(`negative_evidence` and `observation_evidence`), and `common/reference.schema.json` makes
`kind` part of the reference identity. The two sets could therefore never be equal or nested,
so every bounded `UNKNOWN`, `ABSENT`, `EMPTY` and `UNOBSERVED` input was unrepresentable.

The root cause was a **conflation of two deliberately separate provenance channels**, not a
missing capability:

```text
observation_evidence_refs  = evidence that the Observation itself was performed
negative_evidence_refs     = bounded evidence proving the negative conclusion
```

### Difference B — distinct observed candidates sharing one value type were unrepresentable

`structural_difference.observed_values` and `observed_value_types` were duplicate-free
`UNORDERED_SET` wrappers, while the cross-record validator compared them against the
**per-candidate** lists derived from `normalized_observed_state.value_candidates`.

Two distinct candidates sharing a value type (or a value) therefore had no valid representation:
the set collapses them, and the collapsed set no longer equals the per-candidate list. Every
multi-candidate `all`, `none` and `exists` route with a repeated type was blocked, and any
implementation that deduplicated silently would have **under-reported the observed state**.

## 2. Decision

### A. Evidence channels are distinct and the Difference binds their exact union

```text
observation_evidence_refs
= observation.observation_evidence_refs
∪ contributing_negative_observations.negative_evidence_refs
```

- The union is **exact**: no missing reference, no unbound extra reference.
- A Negative Observation Evaluation's `evidence_refs` must be a subset of **its own**
  `negative_evidence_refs` channel, never of the Observation Evidence channel.
- `ABSENT` and `EMPTY` continue to require non-empty bounded Negative Evidence.
- `NO_RESULT`, `FAILED`, `UNKNOWN` and `UNOBSERVED` continue to map to `UNKNOWN` knowledge and
  are never promoted to proven absence.

```text
NO_RESULT ≠ PROVEN_ABSENCE
UNOBSERVED ≠ PROVEN_ABSENCE
NEGATIVE_EVIDENCE ≠ OBSERVATION_EVIDENCE
```

### B. Observed candidates are projected as a lossless ordered list

`structural_difference.observed_values` and `observed_value_types` become `ORDERED_LIST`
wrappers whose member order is the canonical member order of
`normalized_observed_state.value_candidates`. Member *i* corresponds exactly to candidate *i*.

- Distinct candidates are preserved even when they share a value or a value type.
- The order is **derived**, not incidental: it comes from the canonical byte ordering of the
  candidate set, so reordering the source input does not change the Difference identity.
- `value_candidates` itself remains a duplicate-free `UNORDERED_SET` of full candidate
  projections (`value`, `value_type`, `unit`, `fact_predicate`, `effective_boundary`), so two
  candidates with an identical value and type remain distinct members.

## 3. Affected artifacts

```text
00_KERNEL/04_DIFFERENCE/DIFFERENCE_CONTRACT.md   §3, §4, §5
00_KERNEL/04_DIFFERENCE/DIFFERENCE_IDENTITY.md   §2
01_SCHEMA/difference/difference.schema.json      structural_difference projection
scripts/difference_contract_validator.py         cross-record conformance rules
src/manosube_agent_civilization/difference/      the single executable owner
tests/contract/fixtures/difference/              canonical conformance fixtures
```

No Kernel element was added or removed. `SCHEMA_COUNT` stays 33 and
`DIFFERENCE_SCHEMA_COUNT` stays 12; the schema change is confined to closed `$defs` inside the
existing Difference Record schema.

## 4. Version compatibility analysis

Both changes alter identity semantics and are therefore **breaking** under
`01_SCHEMA/VERSIONING_POLICY.md`, which classifies any change to required fields, enums,
normalization, identity, authority or fingerprint semantics as breaking:

```text
CHANGE_CLASS=BREAKING
COMPATIBLE_WITH_PRIOR_v0_1_RECORDS=false
SILENT_UPGRADE=false
COERCION=false
```

The correction is applied **in place at v0.1** rather than by promoting the schema ID to v0.2.
The governing facts:

```text
SCHEMA_INDEX.STATUS=CANONICAL_DESIGN
DIFFERENCE_CONTRACT.STATUS=CANONICAL_DESIGN
DIFFERENCE_ENGINE_IMPLEMENTED=false   (as recorded on main before Issue #24)
DIFFERENCE_IDENTITY_IMPLEMENTED=false (as recorded on main before Issue #24)
DIFFERENCE_RUNTIME_PROVEN=false
CANONICAL_DIFFERENCE_RECORDS_PERSISTED=0
```

v0.1 has never had an executing Difference Engine, so no canonical Difference Record has ever
been derived, persisted, or bound by any downstream owner. There is no deployed reader whose
interpretation could silently change, and no record whose identity could silently drift. A v0.2
ID would therefore version a design that was never realised, and would leave the v0.1 ID
permanently naming an unimplementable contract.

Reject-on-unknown remains intact: a record still carrying the previous `UNORDERED_SET` shape for
`observed_values` or `observed_value_types` now **fails closed** against
`difference.schema.json` rather than being coerced. This is the required behaviour under the
versioning policy's prohibition on silent upgrade.

## 5. Migration record

No canonical record migration is required, because no canonical Difference Record exists outside
this repository's own conformance fixtures. The affected artifacts and their before/after content
digests are:

```yaml
migration_id: SCHEMA-MIGRATION-0001
source_schema_id: https://schemas.manosube.org/agent-civilization-os/v0.1/difference/difference.schema.json
target_schema_id: https://schemas.manosube.org/agent-civilization-os/v0.1/difference/difference.schema.json
base_commit_sha: 7db2055330bf21458d05628c09bee7d309083dbf
canonical_records_migrated: 0
fixtures_regenerated: 1
tool: src/manosube_agent_civilization/difference (deterministic re-derivation)
failure_status: NONE
quarantined: 0
```

```text
01_SCHEMA/difference/difference.schema.json
  before=sha256:ee9078dbe9914ad6581a004d646a244b41c47da587d16e1be37c402234e5f047
  after =sha256:447289d89b6f3f9eaa6991abd940746c916f345cc6e0537a19dd9b93398f2fbd

00_KERNEL/04_DIFFERENCE/DIFFERENCE_CONTRACT.md
  before=sha256:dd58bffe46adf982a672d700920d29de1c9c8d8e56e5cb7e31c0495ab9f11cb8
  after =sha256:ebbd81b63081260b1bb4916b043fce534ad2b51be22bdf8fc38909ad844cb3a8

00_KERNEL/04_DIFFERENCE/DIFFERENCE_IDENTITY.md
  before=sha256:a2b7f79eb165171e6afc8a05eecfb2dfedcbb3d0737f7498472bdeb09de47a89
  after =sha256:30661c705a390aebaf885a7103fb39a1c6a3bc84ac4e306c5d922389ae4ecc0b

tests/contract/fixtures/difference/valid/bundle.json
  before=sha256:8e636f919067aa55339cfc7b6eab1246f70cfedf9b39a53d7d413d8388dca9d9
  after =sha256:1708d97be606dab4965baf106d8b0d341e40da5ac40ec73d46da41d21e0853cc
```

The one regenerated fixture changed identity deterministically, because
`structural_difference` is an identity input. The change was applied by recomputing the identity
with the contract's own algorithm, not by hand:

```text
difference_id
  before=D-817F5C7C4F0C96B3C608CE835667147B60EC4456434614241627F0238A876F82
  after =D-0D9FDBF58A52616D3832892F8704158A3F6884DD9E3E62B1A3208021C3B7B257

observation_request_id
  before=OBS-REQ-9AA44949A191D7965941AEC662461EC8C40A5D4C229E2C97C424CD4DB056E5BD
  after =OBS-REQ-B8C37DF49C6AAB9A0BB165429484653576EAA821F83A74C901DF7885FF0837AC
```

## 6. What was deliberately not changed

```text
COMPLETION_SEMANTICS.md                unchanged
KERNEL_INVARIANTS.md                   unchanged
KERNEL_CONSTITUTION.md                 unchanged
01_SCHEMA/VERSIONING_POLICY.md         unchanged
01_SCHEMA/MIGRATION_POLICY.md          unchanged
closure policy contradiction_policy    still FAIL_CLOSED
allowed terminal states                unchanged
independent_verification_required      still false, still a const
```

No completion gate was relaxed. No mismatch kind, knowledge status, or comparison result was
added or removed. Both corrections **increase** what the contracts can faithfully represent and
**increase** what the validator rejects; neither makes any previously invalid record valid.

Newly rejected inputs that previously escaped or were unreachable:

```text
a Difference whose Evidence binding is not the exact union of both channels
a Negative Observation Evaluation citing evidence outside its own channel
an ABSENT or EMPTY conclusion with no bounded Negative Evidence
a NO_RESULT evaluation presented as a proven ABSENT observed state
an observed candidate silently dropped from the structural projection
an observed value or type list reordered away from candidate order
```

## 7. Acceptance

```text
PURE_NEGATIVE_ROUTE_REPRESENTABLE=true
NO_RESULT_NE_PROVEN_ABSENCE=true
EVIDENCE_PROVENANCE_EXACT=true
MULTI_CANDIDATE_SHARED_TYPE_REPRESENTABLE=true
OBSERVED_PROJECTION_LOSSLESS=true
OBSERVED_PROJECTION_ORDER_DETERMINISTIC=true
IDENTITY_STABLE_UNDER_SOURCE_REORDERING=true
CONTRACT_WEAKENED=false
COMPLETION_GATE_WEAKENED=false
PARALLEL_OWNER_CREATED=false
CANONICAL_RECORD_MIGRATION_REQUIRED=false
```

```text
DIFFERENCE_CONTRACT_CORRECTED=true
DIFFERENCE_SCHEMA_CORRECTED=true
DIFFERENCE_RUNTIME_PROVEN=false
KERNEL_V0_1_COMPLETE=false
```
