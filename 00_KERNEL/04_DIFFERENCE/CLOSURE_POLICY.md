# MANOSUBE Agent Civilization OS

## Difference Closure Policy v0.1

```text
DOC_TYPE=KERNEL_CONTRACT
KERNEL_ELEMENT=DIFFERENCE
DOCUMENT_ID=DIFFERENCE-CLOSURE-POLICY-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
```

---

# 0. Purpose

本Policyは、Difference ClosureをChange実行者の自己申告、test pass、PR merge、artifact存在から分離し、after-stateの独立再観測と十分なEvidenceを必須にする。

```text
DIFFERENCE CLOSED
= TARGET SATISFIED
+ AFTER STATE RE-OBSERVED
+ SUFFICIENT RESOLUTION EVIDENCE
+ NO MATERIAL CONTRADICTION
+ POLICY PASS
+ ATOMIC REFLOW
```

# 1. Closure Policy Record

Closure Policyはversioned immutable recordである。

```yaml
schema_version: "0.1"
closure_policy_id: CP-...
policy_version: "0.1"
subject_difference_ref: {kind: difference, id: D-...}
target_predicate_ref: {kind: target_predicate, id: TP-...}
required_observation_scope: null
minimum_evidence_level: E1
required_claims: []
required_invariants: []
allowed_terminal_states: [CLOSED, BLOCKED, RETAINED]
independent_verification_required: false
maximum_evidence_age: null
contradiction_policy: FAIL_CLOSED
reopen_conditions: [{kind: target_predicate, id: TP-REOPEN-...}]
```

`policy_semantic_fingerprint`は次のversioned profileで決定的に算出する。

```text
PROFILE=MANOSUBE-CLOSURE-POLICY-SHA256-0.1
DIGEST=SHA-256
TEXT_NORMALIZATION=UNICODE_NFC
SERIALIZATION=CANONICAL_JSON_UTF8
OBJECT_KEY_ORDER=LEXICOGRAPHIC
UNKNOWN_FIELDS=REJECT
UNORDERED_SETS=required_claims,required_invariants,allowed_terminal_states,reopen_conditions
SET_ORDER=CANONICAL_MEMBER_BYTES
DUPLICATE_SET_MEMBER=REJECT
```

Fingerprint inputのincluded fieldsを次へ固定する。

```text
target_predicate_ref
required_observation_scope
minimum_evidence_level
required_claims
required_invariants
allowed_terminal_states
independent_verification_required
maximum_evidence_age
contradiction_policy
reopen_conditions
```

循環を避けるため、次をfingerprint inputへ含めない。

```text
subject_difference_ref
closure_policy_id
policy_version
schema_version
serialization metadata
```

除外fieldは別のexact provenance bindingとして検証する。特に`subject_difference_ref`は、Policyを使用するDifference IDと一致しなければならない。

Conformance vectorsでは少なくとも、object key順序と上記unordered set順序を変えた同値Policyが同じfingerprintを生成すること、member変更・重複・未知fieldが同一扱いされないことを証明する。

`reopen_conditions`は新しい自由形式Condition recordではない。`01_OBJECTIVE/OBJECTIVE_CONTRACT.md`で定義されるversioned Target Predicateへのtyped referenceだけを許可する。各refのkindは`target_predicate`、IDは解決可能、predicate schema/versionは既知でなければならず、inline predicate、自由記述condition、unknown kindを拒否する。

PolicyはDifference導出時に固定する。実装失敗またはEvidence不足に合わせて弱化してはならない。

# 2. Closure Evaluation Record

```yaml
schema_version: "0.1"
closure_evaluation_id: D-CLOSE-EVAL-...
difference_id: D-...
difference_event_head_ref: {kind: difference_event, id: D-EVT-...}
target_predicate_ref: {kind: target_predicate, id: TP-...}
objective_revision_ref_evaluated: {kind: objective_revision, id: OBJ-REV-...}
objective_semantic_fingerprint_evaluated: {}
before_state_ref: {}
resolution_mode: CHANGE_BOUND
change_refs: []
after_state_ref: {}
after_observation_refs: []
change_result_evidence_refs: []
change_free_verification_evidence_refs: []
verification_independence_ref: null
evidence_sufficiency_ref: {}
invariant_evaluation_refs: []
required_claim_evaluation_refs: []
contradiction_refs: []
evaluated_state_revision: 0
evaluated_state_fingerprint: {}
evaluated_at: "2026-01-01T00:00:00Z"
evaluation_expires_at: null
policy_ref: {kind: closure_policy, id: CP-..., version: "0.1", semantic_fingerprint: sha256:...}
policy_version_evaluated: "0.1"
policy_semantic_fingerprint_evaluated: sha256:...
result: NOT_EVALUATED
failure_reasons: []
reflow_transition_ref: null
```

Evaluation resultは`COMPLETION_SEMANTICS.md`のCanonical Completion Evaluation Statusと完全に同じclosed enumとする。

```text
NOT_EVALUATED
EVALUATING
SATISFIED
NOT_SATISFIED
BLOCKED
STALE
CONTRADICTED
REVOKED
```

# 3. Mandatory Closure Gates

`SATISFIED`には次の全条件を要求する。

```text
G1  DIFFERENCE_ID_VALID
G2  DIFFERENCE_STATUS_VERIFYING
G3  OBJECTIVE_SEMANTIC_FINGERPRINT_EXACT
G4  TARGET_PREDICATE_EXACT
G5  BEFORE_STATE_EXACT
G6  RESOLUTION_MODE_BINDING_EXACT
G7  AFTER_STATE_NEWER_AND_EXACT
G8  INDEPENDENT_REOBSERVATION_PRESENT
G9  REQUIRED_OBSERVATION_SCOPE_EXACT
G10 OBSERVED_TARGET_SATISFIED
G11 RESOLUTION_EVIDENCE_PRESENT
G12 EVIDENCE_LEVEL_SUFFICIENT
G13 OBSERVATION_SCOPE_COMPLETE
G14 NO_BLOCKING_BLIND_SPOT
G15 NO_UNKNOWN_OR_UNOBSERVED_INPUT
G16 NO_FAILED_OR_INVALID_INPUT
G17 NO_UNRESOLVED_CONFLICT
G18 EVIDENCE_FRESHNESS_AND_BINDINGS_CURRENT
G19 INVARIANTS_PASS
G20 ATOMIC_REFLOW_PRECONDITIONS_PASS
G21 ALL_REQUIRED_CLAIMS_SATISFIED
G22 CLOSED_IS_ALLOWED_TERMINAL_STATE
```

一つでもfalseまたはunknownなら`SATISFIED`にしない。

`G3`はClosure Evaluation時点のactive `objective_revision_ref_evaluated`をexact provenanceとして保存し、その`objective_semantic_fingerprint_evaluated`がDifference identityに結合されたfingerprintと一致することを要求する。EDITORIAL revisionではrevision refの変更を許すがsemantic fingerprintの変更を許さない。semantic fingerprintが変わった場合はClosureせず、新しいDifference identityへsupersedeする。

`G6`と`G11`は`resolution_mode`により分岐する。

```text
CHANGE_BOUND
→ change_refs NON-EMPTY
→ exact before／after State binding
→ change_result_evidence_refs NON-EMPTY
→ change_free_verification_evidence_refs EMPTY

CHANGE_FREE
→ change_refs EMPTY
→ change_result_evidence_refs EMPTY
→ change_free_verification_evidence_refs NON-EMPTY
→ independent after-state Observation Evidence proves the Target directly
```

`CHANGE_FREE`はEvidence要件の免除ではない。`REOPENED → VERIFYING`など、変更を必要とせず新しい観測でTarget Satisfactionを再検証する経路でのみ使用し、Observation Evidence、scope completeness、Evidence Sufficiencyおよび全required claimsを通常どおり評価する。Changeが存在しないことを理由に`G11`を自動PASSさせてはならない。

`G9`はafter-state Observationのeffective scopeをCanonical field `required_observation_scope`と照合する。

```text
required_observation_scope = null
→ additional scope constraintなし
→ ただしObservation自身のdefined scope、completion、blind spot gateは必須

required_observation_scope ≠ null
→ after-state Observation effective scopeとexact match必須
```

method、normalization profileおよびschema versionの追加制約が必要な場合は`required_claims`としてversioned identityを指定し、scope fieldへ暗黙に混在させない。単に独立したObservationが存在するだけでは満たさない。

`G21`はClosure Policyの`required_claims`を空集合として無視する規則ではない。各required claimについて、exact claim identity、evaluated State、Evidence references、Completion Evaluation statusを解決し、全件が`SATISFIED`であることを要求する。

```text
REQUIRED CLAIM NOT_EVALUATED → CLOSURE NOT SATISFIED
REQUIRED CLAIM EVALUATING → CLOSURE NOT SATISFIED
REQUIRED CLAIM NOT_SATISFIED → CLOSURE NOT SATISFIED
REQUIRED CLAIM BLOCKED / STALE / CONTRADICTED / REVOKED
→ CLOSURE NOT SATISFIED
```

`G19`はClosure Policyの`required_invariants`それぞれに対し、同一evaluated State revision／fingerprintへ結合されたexact `invariant_evaluation_refs`を要求する。未評価、欠落、stale、unknownまたはfailを一件でも含む場合は`SATISFIED`にしない。空集合の場合もKernel Mandatory Invariantsの評価を免除しない。

`G22`は`allowed_terminal_states`に`CLOSED`が明示されていることを要求する。`CLOSED`が許可されていないPolicyから`SATISFIED` closure candidateを生成してはならない。`BLOCKED`または`RETAINED`だけが許可される場合、対象statusへ遷移する評価を別途生成する。

`policy_ref`、`policy_version_evaluated`および`policy_semantic_fingerprint_evaluated`は、Difference Recordに固定されたPolicy ID／version／semantic fingerprintと同一Policyへexactに解決されなければならない。さらにPolicyの`subject_difference_ref`をDifference IDとexactに照合する。

Current Policyのversionだけが進みsemantic fingerprintが同一の場合、Difference-bound versionによるEvaluationを`STALE`にしない。Current Policyのsemantic fingerprintが異なる場合は旧Differenceを新identityへsupersedeし、旧bindingを新Policyへ読み替えない。

`G8`は常にChange resultから分離されたafter-state re-observationを要求する。加えて`independent_verification_required=true`の場合、`verification_independence_ref`を必須とし、verifier identity、process boundary、input snapshot、method、conflict-of-interest評価を解決してPolicyが定める独立性を証明する。`false`の場合もre-observation自体は免除しないが、別verifier identityまでは要求しない。

`G21`で使用した各Completion Evaluationは`required_claim_evaluation_refs`へexactに保存する。各refはclaim identity、evaluated State revision／fingerprint、Evidence refs、evaluation statusおよびevaluation revisionへ解決可能でなければならない。Atomic Reflow直前に全refがcurrentかつ`SATISFIED`であることを再検査し、`REVOKED`、`STALE`またはhead変更を一件でも検出した場合はClosure Evaluationを`STALE`または`REVOKED`として拒否する。

# 4. Independent Re-observation

Change result、command return code、test output、Agent reportはafter-state Observationの代替ではない。

```text
CHANGE EXECUTION RESULT
→ RE-OBSERVATION REQUEST
→ NORMALIZED AFTER FACTS
→ CHANGE RESULT EVIDENCE
→ CLOSURE EVALUATION
```

独立性とは、Change自身が自身の成功flagをClosure Predicateとして供給しないことを意味する。同じprocessが技術的に観測する場合でも、Observation method、input snapshot、result schema、Evidence identityをChange resultから分離する。

# 5. Evidence Sufficiency

Evidence levelは`07_EVIDENCE/EVIDENCE_LEVELS.md`が定めるE0–E6に従う。要求level未満のEvidenceを件数で補ってはならない。

```text
EVIDENCE COUNT ≠ EVIDENCE STRENGTH
TEST PASS ≠ RUNTIME PROVEN
DECLARATION ≠ OBSERVATION EVIDENCE
```

Negative Evidenceはscope、期間、method、attempt count、completion、blind spotを持たなければならない。

# 6. Fail-Closed Mapping

| Observed condition | Closure result |
|---|---|
| Target satisfied and all gates pass | `SATISFIED` candidate |
| Targetを観測したが満たさない | `NOT_SATISFIED` |
| Targetは満たすがEvidenceが欠落または要求level未満 | `NOT_SATISFIED` |
| Policy `required_invariants`がfail | `NOT_SATISFIED` |
| Kernel Mandatory InvariantがPASS以外 | `BLOCKED` |
| required claimが`NOT_SATISFIED` | `NOT_SATISFIED` |
| `CLOSED`がallowed terminal stateに含まれない | `NOT_SATISFIED` |
| 評価がまだ実行されていない | `NOT_EVALUATED` |
| 必要Evidenceを評価中 | `EVALUATING` |
| Truthを決定するInputまたはObservationが不足 | `BLOCKED` |
| required invariantまたはclaimが未評価／評価中 | `BLOCKED`または`EVALUATING` |
| Observation or Authority path blocked | `BLOCKED` |
| State、Change、Approval、Evidence binding is stale | `STALE` |
| Policy、required claim evaluation、invariant evaluationのhead不一致 | `STALE` |
| Positive／NegativeまたはMaterial Evidence conflict | `CONTRADICTED` |
| 以前受理した評価またはClosureの前提が無効化 | `REVOKED` |
| 初回評価時にschema、identity、boundary、lineageがinvalid | `NOT_SATISFIED` |

`EMPTY`は対象collectionのcomplete enumerationが証明された場合だけTarget Satisfactionへ使用できる。`NO_RESULT`、`FAILED`、`INCOMPLETE`をabsenceまたはmatchへ昇格させない。

# 7. Atomic Closure

Closure Evaluationの`SATISFIED`だけではDifferenceはまだ`CLOSED`ではない。

```text
CLOSURE EVALUATION SATISFIED
+ CURRENT REVISION = EXPECTED REVISION
+ ATOMIC STATE TRANSITION
+ LINEAGE APPEND
+ MATERIALIZED STATE UPDATE
→ DIFFERENCE CLOSED
```

Compare-And-Swap失敗、partial write、lineage append失敗、current state不整合の場合、ClosureをCanonicalとして受理しない。

# 8. Staleness

Closure Evaluationは`evaluated_at`をtimezone-aware UTC timestampとして保存し、`maximum_evidence_age`を評価時点とAtomic Reflow commit直前の双方で強制する。

```text
maximum_evidence_age = null
→ Policyによる追加のage上限なし
→ evaluation_expires_at = null

maximum_evidence_age ≠ null
→ 0 <= evaluated_at - evidence_observed_at <= maximum_evidence_age
→ timezone-aware timestamp必須
→ evaluation_expires_at = oldest_required_evidence_observed_at + maximum_evidence_age
→ age不明、future-dated Evidence、timestamp不正、上限超過はG18=false
```

複数Evidenceを使う場合は、Closure Claimに必要な全Evidenceがage predicateを満たさなければならない。古いEvidenceを新しいEvidenceの件数で補ってはならない。上限超過は`STALE`とし、`SATISFIED`を返さない。

Atomic Reflowはcommit clockをtimezone-aware UTCとして取得し、`evaluation_expires_at`がnon-nullなら次を再検証する。

```text
commit_at <= evaluation_expires_at
```

commit前にexpiryへ到達したEvaluationは、他のbindingが変化していなくても`STALE`である。再観測・再評価なしにcommitしてはならない。

次のいずれかがEvaluation後に変わった場合、未commitのClosure Evaluationは`STALE`である。

```text
Objective revision
Target Predicate
Difference lifecycle head
before or after State revision
State fingerprint
Change identity or result
Authority or Approval binding
Evidence set
Closure Policy semantic fingerprint（version-only変更かつsemantic fingerprint同一の場合を除く）
```

Stale Evaluationを再利用せず、最新Stateから再観測・再評価する。

# 9. Reopen Policy

同じsemantic identity boundary内で、`CLOSED`後のObservationがTarget不一致を示した場合、またはClosureに使用したEvidenceの失効・provenance不正・material contradictionがObservationの有無にかかわらず判明した場合、Differenceを`REOPENED`へ遷移させる。

加えて、Closure Policyの`reopen_conditions`が参照するTarget Predicate集合を評価する。いずれかがexact current State／Evidence上で`SATISFIED`になった場合は同じ`CLOSED → REOPENED`経路を使用し、`POLICY_REOPEN_CONDITION_SATISFIED`、triggered Target Predicate ref、Completion Evaluation refおよび評価EvidenceをReopen Eventへ保存する。未知condition、評価不能、stale inputをtrueまたはfalseへ推測せず、fail closedで再観測へ送る。

Reopenは旧Closureを削除しない。次をappendする。

```text
reopen event
contradicting observation refs
contradicting evidence refs
invalidated closure evidence refs
affected closure evaluation ref
new State revision and fingerprint
next required observation
```

Objective、Target、effective boundaryまたはnormalized mismatch semanticsがmaterialに変更された場合は、旧Differenceを`SUPERSEDED`とし、新しいDifference identityとappend-only Supersession Relationを導出する。Boundary変更を旧Differenceの`REOPENED`として扱わない。

# 10. Non-Authorities

次はClosure authorityではない。

```text
Agent report
Issue close
PR merge
commit exists
CI success
test pass
artifact exists
deployment succeeded
Change status EXECUTED
human informal statement
```

HumanはObjectiveとconstitutional authorityを持つが、Evidenceなしの手動flagでKernel invariantを迂回しない。Risk acceptanceはTarget Satisfactionの代替ではない。

# 11. Acceptance

```text
CLOSURE_GATES_CLOSED=true
REOBSERVATION_REQUIRED=true
CHANGE_BOUND_RESULT_EVIDENCE_REQUIRED=true
CHANGE_FREE_VERIFICATION_EVIDENCE_REQUIRED=true
RESOLUTION_MODE_EVIDENCE_EXCLUSIVE=true
EVIDENCE_SUFFICIENCY_REQUIRED=true
MAXIMUM_EVIDENCE_AGE_ENFORCED=true
EVALUATION_TIMESTAMP_RECORDED=true
EVIDENCE_AGE_RECHECKED_AT_REFLOW=true
FUTURE_DATED_EVIDENCE_REJECTED=true
REQUIRED_INVARIANTS_BOUND=true
ALLOWED_TERMINAL_STATES_ENFORCED=true
POLICY_VERSION_EXACT=true
REQUIRED_CLAIM_EVALUATIONS_BOUND=true
POLICY_SEMANTIC_FINGERPRINT_DETERMINISTIC=true
VERSION_ONLY_POLICY_UPDATE_CLOSABLE=true
INDEPENDENT_VERIFICATION_SETTING_ENFORCED=true
REOPEN_CONDITIONS_ENFORCED=true
UNKNOWN_IS_PASS=false
NO_RESULT_NE_PROVEN_ABSENCE=true
CHANGE_CANNOT_SELF_CLOSE=true
PR_MERGE_IS_COMPLETION=false
STALE_CLOSURE_BLOCKED=true
ATOMIC_REFLOW_REQUIRED=true
REOPEN_POLICY_DEFINED=true
```

```text
DIFFERENCE_CLOSURE_POLICY_DEFINED=true
CLOSURE_EVALUATOR_IMPLEMENTED=false
ATOMIC_DIFFERENCE_CLOSURE_PROVEN=false
```
