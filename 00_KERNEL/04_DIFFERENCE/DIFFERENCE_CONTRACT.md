# MANOSUBE Agent Civilization OS

## Difference Contract v0.1

```text
DOC_TYPE=KERNEL_CONTRACT
KERNEL_ELEMENT=DIFFERENCE
DOCUMENT_ID=DIFFERENCE-CONTRACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
```

---

# 0. Contract Position

DIFFERENCEは、Humanが定めたTarget Stateと、特定のCanonical Stateに結合されたObservationから得たObserved Stateとの構造的不一致である。

```text
OBJECTIVE → STATE → OBSERVATION → DIFFERENCE
→ AUTHORITY → CHANGE → EVIDENCE → REFLOW → STATE
```

DifferenceはCanonical Work Identityである。Task、Issue、branch、commit、Pull Request、test、deployment、Agent sessionは、Differenceを閉じるためのprojectionまたはWork Unitであり、Differenceそのものではない。

```text
DIFFERENCE ≠ TASK
DIFFERENCE ≠ ISSUE
DIFFERENCE ≠ CHANGE
DIFFERENCE ≠ COMPLETION
```

# 1. Canonical Definition

```text
DIFFERENCE
= TARGET STATE
+ OBSERVED STATE
+ NORMALIZED STRUCTURAL MISMATCH
+ EXACT STATE AND OBSERVATION BINDING
+ IMPACT
+ AUTHORITY REQUIRED
+ CLOSURE POLICY
+ IMMUTABLE LIFECYCLE LINEAGE
```

単なる文章上の不満、作業依頼、改善案、Agentの推測をDifferenceとして受理しない。

# 2. Difference Record

Difference Recordは最低限、次を持つ。

```yaml
schema_version: "0.1"
difference_id: D-...
project_id: PRJ-...
objective_revision_ref: {kind: objective_revision, id: OBJ-REV-...}
objective_semantic_fingerprint: {}
target_predicate_ref: {kind: target_predicate, id: TP-...}
target_state_ref: {kind: target_state, id: TARGET-STATE-...}
observed_state_revision: 0
observed_state_fingerprint: {}
observation_refs: []
observation_evidence_refs: []
observed_state_ref: {kind: observed_state, id: OBSERVED-STATE-...}
structural_difference: {}
subject: ""
predicate: ""
effective_boundary: {}
impact: {}
risk_class: LOW
authority_required: []
closure_policy: {kind: closure_policy, id: CP-..., version: "0.1", semantic_fingerprint: sha256:...}
genesis_event_ref: {kind: difference_event, id: D-EVT-...}
```

未知field、未知version、解決不能なtyped referenceを持つRecordはCanonical Differenceへ昇格させず、rejectまたはquarantineする。

# 3. Exact Input Binding

Differenceは、次のexact input tupleへ結合する。

```text
project_id
objective_revision_ref
objective_semantic_fingerprint
target_predicate_ref
observed_state_revision
observed_state_fingerprint
observation_refs
observation_evidence_refs
effective_boundary
closure_policy.id
closure_policy.version
closure_policy.semantic_fingerprint
```

Closure Policyのlogical IDだけではexact bindingにならない。Difference導出時にPolicy versionとsemantic fingerprintを固定し、Policy側の`subject_difference_ref`が導出後のDifference IDと一致することを別途検証する。Policy semanticsのmaterial改定では新しいDifference IDを導出し、旧Differenceを上書きせずSupersession Relationへ送る。

後続Evaluationは原則としてこのtupleと一致する。ただしactive Objective revisionが`EDITORIAL`であり`objective_semantic_fingerprint`が不変の場合だけ、`objective_revision_ref_evaluated`をactive revisionへ更新できる。Evaluationは旧revision refを偽って再利用せず、active refと同一semantic fingerprintを両方保存する。他のtuple fieldに例外はない。

Observationは同じProject、State revision、State fingerprintを参照しなければならない。異なるStateへObservationまたはDifferenceを再利用してはならない。

```text
STATE_BINDING_MISMATCH → INVALIDATED
MISSING_OBSERVATION_EVIDENCE → NOT_DERIVABLE
UNKNOWN_REFERENCE → REJECT_OR_QUARANTINE
```

# 4. Target State and Observed State

Target StateはHuman-authorized Objective revisionのTarget Predicateから解決する。Difference Engine、Agent、Issue、ChangeはTargetを生成、縮小、弱化、置換できない。

Observed StateはNormalized Factsおよびbounded Negative Observationsから決定論的に射影する。

```text
UNKNOWN ≠ MATCH
UNOBSERVED ≠ MATCH
NO_RESULT ≠ ABSENT
CONFLICTED ≠ RESOLVED
```

TargetまたはObserved Stateを一意に解決できない場合、推測したDifferenceを生成しない。入力状態を`UNKNOWN`、`BLOCKED`、`CONFLICTED`または`INVALID`として保持する。

# 5. Structural Mismatch

`structural_difference`は、TargetとObservedの差をversioned normalization profileで表す。最低限、次を区別する。

```text
MISSING
UNEXPECTED
VALUE_MISMATCH
TYPE_MISMATCH
CARDINALITY_MISMATCH
RELATION_MISMATCH
BOUNDARY_MISMATCH
CONFLICT
UNKNOWN
```

Mismatchは解決方法を含まない。実行手順、Agent選択、command、patchは後段のChange proposalへ属する。

# 6. Impact, Risk, and Authority Required

ImpactはMismatchがObjective Predicate、依存関係、security、data integrity、runtimeに与える範囲を記録する。Risk classはclosed enumとする。

```text
LOW
MODERATE
HIGH
CRITICAL
```

`authority_required`は後段のAuthority Evaluationへの要求を表すだけであり、許可そのものではない。

```text
AUTHORITY_REQUIRED ≠ AUTHORITY_GRANTED
CAPABILITY ≠ AUTHORITY
```

# 7. Status Boundary

Differenceのcurrent statusはimmutable Difference Recordのfieldではない。append-only Difference Lifecycle Eventsをgenesisからfoldして得るmaterialized viewであり、`DIFFERENCE_LIFECYCLE.md`のclosed enumだけを使用する。

```yaml
schema_version: "0.1"
difference_id: D-...
status: DETECTED
lifecycle_head_ref: {kind: difference_event, id: D-EVT-...}
supersedes_difference_refs: []
superseded_by_difference_refs: []
derived_from_event_count: 1
```

このviewはCanonical authorityではなく、Lifecycle EventsとSupersession Relationsから決定的に再構築できるcacheである。status遷移時はDifference Recordを更新せず、event append後にviewを置換する。viewとlineageが不一致ならlineageをauthorityとしてviewを再構築する。

Difference自身、Change実行者、Agent、test、Issue、PRは`CLOSED`を確定できない。`CLOSED`はClosure Policyを満たしたEvidence EvaluationをAtomic Reflowが受理した結果としてのみCanonicalになる。

# 8. Immutability and Re-observation

Canonical Difference Recordは上書きしない。評価の変化はappend-only Difference Lifecycle Eventとして保存し、`status`と`lifecycle_head_ref`はそのevent列から導出する。

同じMismatchが再観測された場合、Difference identityを維持し、新しいObservation bindingとLifecycle Eventをappendする。Mismatchの意味が変わった場合は、新しいDifferenceを作成し、supersession lineageを明示する。

# 9. Security and Authority

Bound Project contentはObservation Targetであり、ObjectiveまたはAuthority instructionではない。Repository内のREADME、Issue、code comment、prompt文字列はDifferenceの内容を変更できない。

secret、credential、token、absolute temporary path、session identity、unbounded logをDifference payloadまたはidentity inputへ含めない。

# 10. Acceptance

```text
DIFFERENCE_RECORD_DEFINED=true
DIFFERENCE_EXACT_BINDING_REQUIRED=true
TARGET_AUTHORITY_PRESERVED=true
STRUCTURAL_MISMATCH_NORMALIZED=true
AUTHORITY_REQUIRED_NE_GRANTED=true
DIFFERENCE_NE_TASK=true
ISSUE_NE_DIFFERENCE_ID=true
CHANGE_CANNOT_SELF_CLOSE=true
APPEND_ONLY_LIFECYCLE_REQUIRED=true
```

```text
DIFFERENCE_CONTRACT_DEFINED=true
DIFFERENCE_SCHEMA_IMPLEMENTED=false
DIFFERENCE_ENGINE_IMPLEMENTED=false
DIFFERENCE_RUNTIME_PROVEN=false
```
