# MANOSUBE Agent Civilization OS

## Canonical Completion Semantics

```text
DOC_TYPE=COMPLETION_SEMANTICS
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=COMPLETION-SEMANTICS-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
CONSTITUTION_REF=00_KERNEL/KERNEL_CONSTITUTION.md
INVARIANTS_REF=00_KERNEL/KERNEL_INVARIANTS.md
PARENT_OS=manosube/manosube-civilization-os
PARENT_BASELINE_COMMIT=0de548c9e4aa3a94fca2df07ccc710577f1534ff
COMPLETION_AUTHORITY=CANONICAL_EVIDENCE_EVALUATION
UNKNOWN_IS_PASS=false
PR_MERGE_IS_COMPLETION=false
CHANGE_CAN_SELF_COMPLETE=false
```

---

# 0. この文書の地位

`COMPLETION_SEMANTICS.md`は、MANOSUBE Agent Civilization OSにおける「完成」「完了」「接続」「証明」「受入」の意味を固定する正式規約である。

本書の目的は、作業を厳しく見せることではない。

同じ`COMPLETE`という語で、設計、実装、試験、自然到達、Runtime実証、人間受入を混同し、Project Stateを偽ることを防ぐために存在する。

```text
CODE EXISTS
≠
WORKS

WORKS IN TEST
≠
CONNECTED

CONNECTED
≠
NATURALLY REACHABLE

NATURALLY REACHABLE
≠
RUNTIME PROVEN

RUNTIME PROVEN
≠
OBJECTIVE COMPLETE
```

CompletionはAgentの感想、作業量、PR数、経過時間、期待では決まらない。

```text
COMPLETION
= TARGET CLAIM
+ OBSERVED STATE
+ SUFFICIENT EVIDENCE
+ CLOSURE POLICY
+ CANONICAL EVALUATION
+ ATOMIC REFLOW
```

---

# 1. Completionの対象を分離する

Completion Claimは、必ず対象種別を持つ。

```text
DOCUMENT_COMPLETION
CONTRACT_COMPLETION
IMPLEMENTATION_COMPLETION
CONNECTION_COMPLETION
DIFFERENCE_CLOSURE
OBJECTIVE_PREDICATE_COMPLETION
OBJECTIVE_COMPLETION
VERSION_COMPLETION
RELEASE_ACCEPTANCE
SYSTEM_COMPLETION
```

異なる対象のCompletionを相互に代用してはならない。

例：

```text
DOCUMENT_COMPLETION
≠ IMPLEMENTATION_COMPLETION

DIFFERENCE_CLOSURE
≠ OBJECTIVE_COMPLETION

VERSION_COMPLETION
≠ SYSTEM_COMPLETION

RELEASE TAG EXISTS
≠ RELEASE ACCEPTED
```

Completion Recordは最低限、次を持つ。

```yaml
completion_id: CMP-0001
subject_type: DIFFERENCE
subject_ref: D-0001
claim: CLOSED
target_state_ref: null
observed_state_ref: null
closure_policy_ref: null
required_evidence_refs: []
invariant_evaluation_refs: []
material_contradiction_refs: []
evaluation_status: UNKNOWN
evaluated_state_revision: null
evaluated_state_fingerprint: null
evaluated_at: null
reflow_transition_ref: null
```

---

# 2. Canonical Completion Ladder

状態の強さは、次の順で区別する。

```text
L0  UNDEFINED
L1  DESIGNED
L2  IMPLEMENTED
L3  STATICALLY_VERIFIED
L4  TEST_VERIFIED
L5  INTEGRATED
L6  CONNECTED
L7  NATURALLY_REACHABLE
L8  RUNTIME_PROVEN
L9  REPEATEDLY_PROVEN
L10 HUMAN_ACCEPTED
```

このLadderは単純な自動昇格列ではない。

上位Levelは、それ以前のClaimを暗黙に保証しない。対象Scope、Evidence、Identityが同じ場合に限り、Closure Policyが要求する下位条件を満たしたと評価できる。

## L0 — UNDEFINED

```text
定義、Target、Scope、Completion Policyのいずれかが存在しない。
```

L0の対象に対して、実装、完了、失敗を判定してはならない。

## L1 — DESIGNED

```text
意味、境界、契約、期待状態が文書またはSchemaとして定義されている。
```

必要Evidence：

```text
approved contract
defined target
defined scope
defined authority
```

L1はコードの存在を意味しない。

## L2 — IMPLEMENTED

```text
設計を満たすと主張する実装が存在する。
```

必要Evidence：

```text
implementation identity
source revision
contract mapping
```

L2は正しく動作することを意味しない。

## L3 — STATICALLY_VERIFIED

```text
Schema、型、構造、依存方向、禁止依存を静的に検証している。
```

必要Evidence：

```text
schema validation
type or structural verification
dependency boundary verification
```

L3は実行結果を意味しない。

## L4 — TEST_VERIFIED

```text
定義されたTest Scope内で期待結果を満たす。
```

必要Evidence：

```text
test identity
input identity
implementation identity
expected result
observed result
test scope
```

Mock、Fixture、Unit TestはそのScopeを超えたClaimを証明しない。

## L5 — INTEGRATED

```text
複数Componentが定義されたIntegration Environmentで協調動作する。
```

必要Evidence：

```text
component identities
integration input
producer output
consumer input
integration result
```

L5はNatural Routeまたは対象Runtimeを意味しない。

## L6 — CONNECTED

```text
同一identityを持つproducer outputが、代替物を介さず、次consumerに読まれ、次Canonical Artifactを生成する。
```

CONNECTEDの必要条件：

```text
previous output generated
same output consumed by next stage
identity preserved
canonical owner count = 1
no substitute artifact
no fallback authority
next canonical artifact generated
```

一つでも欠ければ、

```text
CONNECTED=false
```

である。

## L7 — NATURALLY_REACHABLE

```text
手動State編集、直接関数注入、Fixture置換、人工的な中間Artifact生成なしに、正式入口から対象状態へ到達する。
```

必要Evidence：

```text
natural entry identity
input lineage
all stage transitions
terminal artifact identity
no manual mutation attestation
```

## L8 — RUNTIME_PROVEN

```text
対象Runtimeの実Authority、Filesystem、Process、Network、Timing、Identity条件下で自然経路が実証されている。
```

Local Test、Container Test、Staging、Productionを同じRuntime Evidenceとして扱ってはならない。

## L9 — REPEATEDLY_PROVEN

```text
独立した複数回または複数Runtimeで、同一Claimが再現されている。
```

反復回数、独立性、期間、対象差異を明示する。

## L10 — HUMAN_ACCEPTED

```text
Human Authorityが、定義されたEvidenceと残存Differenceを確認し、対象Claimを受理している。
```

Human AcceptanceはEvidenceを置換しない。

```text
HUMAN_ACCEPTANCE
≠
TECHNICAL_PROOF
```

---

# 3. Evidence Levelとの対応

Completion LevelとEvidence Levelは同一ではない。

```text
E0 = 宣言のみ
E1 = 静的確認
E2 = 単体テスト
E3 = 統合テスト
E4 = 自然経路実行
E5 = 対象Runtime実証
E6 = 反復・独立Runtime実証
```

標準対応：

| Completion Level | 標準Minimum Evidence |
|---|---:|
| DESIGNED | E0 + approved contract |
| IMPLEMENTED | E1 |
| STATICALLY_VERIFIED | E1 |
| TEST_VERIFIED | E2 |
| INTEGRATED | E3 |
| CONNECTED | E3 + identity proof |
| NATURALLY_REACHABLE | E4 |
| RUNTIME_PROVEN | E5 |
| REPEATEDLY_PROVEN | E6 |
| HUMAN_ACCEPTED | required technical level + Human receipt |

Closure Policyは、対象Riskに応じてこれより強いEvidenceを要求できる。

Closure Policyは、この標準より弱いEvidenceで上位Claimを成立させてはならない。

---

# 4. Completion Evaluation Status

Completion Evaluationは次の状態を持つ。

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

意味：

| Status | 意味 |
|---|---|
| `NOT_EVALUATED` | 評価が行われていない |
| `EVALUATING` | 必要Evidenceを評価中 |
| `SATISFIED` | 対象State・Scope・Policyに対し完了条件を満たす |
| `NOT_SATISFIED` | 観測済みだが条件を満たさない |
| `BLOCKED` | 評価に必要なAuthority、Input、Runtime等が欠ける |
| `STALE` | EvidenceまたはStateが評価対象より古い |
| `CONTRADICTED` | Materialな矛盾が存在する |
| `REVOKED` | 以前の受理が無効化された |

`SATISFIED`だけがCompletion ClaimのCanonical採用候補である。

ただし、`SATISFIED`評価をStateへ反映するAtomic Reflowが完了するまでは、Canonical Completion Stateは変化しない。

---

# 5. Difference Lifecycle and Closure

DifferenceのLifecycle：

```text
DETECTED
→ OPEN
→ ACTIVE
→ VERIFYING
→ CLOSED
```

分岐状態：

```text
BLOCKED
RETAINED
REOPENED
SUPERSEDED
INVALIDATED
```

## DETECTED

Observationから候補差異が検出されたが、Difference IdentityとPolicyが未確定。

## OPEN

Target State、Observed State、Structural Difference、Impact、Authority Required、Closure Policyが確定している。

## ACTIVE

一つ以上のAuthorized ChangeまたはObservation Workが進行中。

## VERIFYING

Change後の再観測とEvidence Sufficiencyを評価中。

## CLOSED

次のすべてを満たす。

```text
target claim identified
after state independently observed
required claims satisfied
minimum evidence level satisfied
scope satisfied
evidence age valid
independence requirement satisfied
mandatory invariants PASS
material contradictions = 0
closure evaluation = SATISFIED
atomic reflow committed
```

## BLOCKED

Differenceは存在するが、必要Authority、Input、Runtime、Human Decision等が不足し、閉鎖作業を進められない。

BLOCKEDはCLOSEDではない。FAILEDとも限らない。

## RETAINED

観測結果としてDifferenceが残ることが正当であり、現在のAuthorityまたはObjectiveの下で変更対象にしない。

RETAINEDは隠蔽ではない。理由、Authority、再評価条件を持つ。

## REOPENED

CLOSED後にState Drift、Evidence Invalidity、Regressionまたは新しい矛盾が観測された。

## SUPERSEDED

Objective RevisionまたはDifference再構成によって、別Differenceが正式に責務を継承した。

古いDifferenceのLineageは削除しない。

## INVALIDATED

観測またはIdentityが不正で、Difference自体が成立しなかった。

実装失敗を`INVALIDATED`で消してはならない。

---

# 6. Change Completionは禁止する

Changeは次のLifecycleを持つ。

```text
PROPOSED
AUTHORIZED
RUNNING
EXECUTED
FAILED
REJECTED
STALE
```

Changeに`COMPLETED`または`CLOSED`を設定してはならない。

```text
CHANGE EXECUTED
≠
DIFFERENCE CLOSED
```

`EXECUTED`が意味するのは、定義されたActionが実行され、Execution Resultが保存されたことだけである。

Execution Resultの成功はAfter Stateを確定しない。

```text
CHANGE
→ EXECUTED
→ RE-OBSERVATION
→ CHANGE RESULT EVIDENCE
→ CLOSURE EVALUATION
→ DIFFERENCE CLOSED / RETAINED / BLOCKED
```

---

# 7. Closure Policy

すべてのDifferenceは、Change実装前にClosure Policyを持つ。

```yaml
closure_policy_id: CP-0001
difference_id: D-0001
required_claims: []
minimum_evidence_level: E3
required_observation_scope: null
independent_verification_required: false
maximum_evidence_age: null
required_invariants: []
allowed_terminal_states:
  - CLOSED
  - BLOCKED
  - RETAINED
reopen_conditions: []
```

Closure Policyの後付け変更は履歴化する。

失敗、Evidence不足、未到達へ合わせてPolicyを弱めてはならない。

次を禁止する。

```text
test failed
→ remove required test

runtime unreachable
→ lower required evidence from E5 to E2

identity mismatch
→ accept substitute artifact

contradiction found
→ delete contradiction requirement
```

---

# 8. Objective Predicate Completion

Objectiveは複数のTarget Predicateから構成される。

各Predicateを独立評価する。

```text
PREDICATE_STATUS
= UNDEFINED
+ NOT_EVALUATED
+ SATISFIED
+ NOT_SATISFIED
+ BLOCKED
+ STALE
+ CONTRADICTED
```

Predicate Completionには次を要求する。

```text
predicate identity
operator
expected value or expected reference
observed value
observation scope
evidence refs
minimum evidence level
evaluation state fingerprint
```

抽象語による自己参照を禁止する。

```text
expected: complete
observed: complete
```

だけではPredicateを満たさない。

---

# 9. Objective Completion

Objective Completionは、Completion Policyに従ってPredicateを集約する。

標準Mode：

```text
ALL
ANY
QUORUM
CUSTOM_DECLARED_POLICY
```

v0.1の標準は`ALL`である。

```text
OBJECTIVE_COMPLETE=true
```

には最低限、次を要求する。

```text
all required predicates SATISFIED
predicate evidence current
mandatory invariants PASS
no material unresolved contradiction
no required predicate BLOCKED
no required predicate STALE
objective revision unchanged
completion evaluation SATISFIED
atomic reflow committed
```

HumanはObjectiveを所有するが、Evidenceなしで技術的PredicateをSATISFIEDへ変更しない。

Humanは、Evidenceと残存Differenceを確認してObjective Completionを受け入れることができる。

---

# 10. Version Completion

Versionは機能数、commit数、経過日数では完成しない。

```text
VERSION COMPLETE
= VERSION TARGET DIFFERENCE CLOSED
+ REQUIRED CAPABILITIES PROVEN
+ NATURAL ROUTE PASS
+ MANDATORY INVARIANTS PASS
+ RELEASE EVIDENCE COMPLETE
+ NO MATERIAL UNRESOLVED CONTRADICTION
```

Version Completion Record：

```yaml
version: 0.1.0
target_difference_refs: []
required_capability_claims: []
required_natural_route_refs: []
required_invariant_evaluations: []
release_evidence_refs: []
unresolved_material_contradictions: []
status: NOT_EVALUATED
accepted_by_human: false
```

## v0.1

```text
KERNEL_V0_1_COMPLETE
= KERNEL_CORE_COMPLETE
+ MINIMAL_FIXTURE_BINDING
+ ONE_FULL_NATURAL_CYCLE_PASS
```

v0.1 Natural Cycle：

```text
OBJECTIVE
→ INITIAL STATE
→ OBSERVATION
→ OBSERVATION EVIDENCE
→ DIFFERENCE
→ AUTHORITY CHECK
→ CHANGE
→ RE-OBSERVATION
→ CHANGE RESULT EVIDENCE
→ CLOSURE EVALUATION
→ ATOMIC REFLOW
→ NEW STATE
```

次ではv0.1完成にならない。

```text
documents complete
schemas exist
unit tests pass
mock cycle pass
state manually edited
GitHub repository published
release tag created
```

## v0.2以降

```text
ONE VERSION
= ONE STRUCTURAL CAPABILITY
+ ONE NATURAL PROOF
```

無関係な機能、将来Adapter、placeholderをVersion Completionへ混ぜない。

---

# 11. Release Acceptance

Version CompletionとRelease操作を分離する。

```text
VERSION COMPLETE
→ RELEASE CANDIDATE
→ RELEASE VERIFICATION
→ HUMAN ACCEPTANCE WHEN REQUIRED
→ RELEASED
```

Release Status：

```text
NOT_READY
CANDIDATE
VERIFYING
READY
RELEASED
REJECTED
REVOKED
```

Tag、Package、GitHub Releaseの存在はRelease Acceptanceではない。

Release後に重大なInvariant違反、Evidence改竄、Regressionが確認された場合、Release Acceptanceを`REVOKED`へ遷移し、Lineageを保持する。

---

# 12. System Completion

MANOSUBE Agent Civilization OSのv1.0 System Completionは、次のすべてを要求する。

```text
CANONICAL_KERNEL_COUNT=1
CANONICAL_STATE_OWNER_COUNT=1
PARALLEL_CANONICAL_AUTHORITY=0

OBJECTIVE_CONTINUITY_PROVEN=true
STATE_RECONSTRUCTION_PROVEN=true
DIFFERENCE_DERIVATION_PROVEN=true
AUTHORITY_ENFORCEMENT_PROVEN=true
CHANGE_LINEAGE_PROVEN=true
INDEPENDENT_EVIDENCE_PROVEN=true
EVIDENCE_REFLOW_PROVEN=true

GITHUB_REPLACEABLE=true
CLI_REPLACEABLE=true
AGENT_REPLACEABLE=true
MODEL_REPLACEABLE=true
SESSION_LOSS_SAFE=true

CODE_RUNTIME_SEPARATED=true
HUMAN_ONLY_AUTHORITY_PRESERVED=true
BOUNDED_AUTONOMY_PROVEN=true
DYNAMIC_MULTI_AGENT_PROVEN=true

OBJECTIVE_TO_TERMINAL_NATURAL_PASS=true
UNRESOLVED_STRUCTURAL_CONTRADICTIONS=0
```

```text
MANOSUBE_AGENT_CIVILIZATION_OS_COMPLETE=true
```

は、上記Claimが対象Scopeと必要Evidence Levelで全て成立し、Human Acceptanceを必要とする最終Gateが通過した場合だけ宣言できる。

---

# 13. EMPTY, SAFE ZERO, NO-CHANGE

変化が発生しなかったことは、必ずしも失敗ではない。

次を区別する。

```text
EMPTY
= 定義された観測範囲で対象候補が正当に0件

SAFE_ZERO
= AuthorityまたはSafety Policyに従い、Changeを0件とする正当な終端

NO_CHANGE_REQUIRED
= Observed StateがTarget Stateと一致し、Differenceが存在しない

NO_RESULT
= 結果を取得できなかった

BLOCKED
= 必要条件不足により評価またはChangeが進められない

FAILED
= 定義された処理が期待結果を満たさなかった
```

EMPTY、SAFE_ZERO、NO_CHANGE_REQUIREDをCompletionとして受理するには、その状態を定義したPolicy、完全なObservation Scope、NegativeまたはTerminal Evidenceが必要である。

```text
ZERO OUTPUT
≠
EMPTY PROVEN
```

---

# 14. UNKNOWN and Unobserved

次を絶対原則とする。

```text
UNKNOWN_IS_PASS=false
UNOBSERVED_IS_PASS=false
BLOCKED_IS_COMPLETE=false
INCOMPLETE_IS_CONNECTED=false
```

Evidenceがない場合、最も正確な状態語を保持する。

```text
UNKNOWN
UNOBSERVED
INCOMPLETE
BLOCKED
```

「おそらく成功」「コード上は到達可能」「設計上は接続済み」をCanonical Completionへ変換してはならない。

---

# 15. Staleness

Completion Claimは永続的な真理ではない。

Evidenceは次に結合される。

```text
subject identity
state fingerprint
implementation revision
runtime identity
observation scope
observed time
```

次の場合、Completion Evaluationを`STALE`として再評価する。

```text
subject implementation changed
state fingerprint changed
objective revision changed
closure policy changed
runtime identity changed
evidence age exceeded
dependency affecting claim changed
```

無関係な変更はCompletionを自動失効させない。影響分析とLineageを保存する。

---

# 16. Reopen and Revocation

過去にCLOSEDまたはCOMPLETEであっても、次が観測された場合は再評価する。

```text
regression
state drift
evidence invalidation
identity mismatch
security incident
invariant violation
material contradiction
objective revision
```

Difference：

```text
CLOSED → REOPENED
```

Completion Evaluation：

```text
SATISFIED → STALE / CONTRADICTED / REVOKED
```

Release：

```text
RELEASED → REVOKED
```

過去の成功Evidenceは削除しない。以前は成立していたことと、現在は成立しないことの両方をLineageに保存する。

---

# 17. Contradictions

Material Contradictionが存在する場合、Completionを宣言してはならない。

Materialとは、対象Claimの真偽、Authority、Identity、Evidence Sufficiency、Runtime到達性、State Reconstructionに影響する矛盾である。

```text
UNRESOLVED_MATERIAL_CONTRADICTIONS > 0
→ COMPLETION_BLOCKED
```

非Materialな矛盾も削除せず保存する。ただし、対象Completionへの影響評価を明示する。

Agent同士の多数決、平均、最新発言の優先によって矛盾を解消してはならない。

---

# 18. Prohibited Completion Shortcuts

次を禁止する。

```text
Issue closed
→ Difference closed

PR merged
→ Change verified

CI green
→ Natural route passed

Artifact exists
→ Correctly consumed

Function callable
→ Runtime reachable

Agent says success
→ After state confirmed

No error log
→ Success proven

No search result
→ Absence proven

Manual fixture pass
→ Production pass

Human approval
→ Technical evidence satisfied

Large amount of work
→ Objective progress
```

これらはEvidenceの一部になり得るが、Completionを単独で確定しない。

---

# 19. Canonical Evaluation Algorithm

Completion Evaluationは次の順序で行う。

```text
1. subject identityを確定
2. target claimを確定
3. applicable completion policyを確定
4. evaluation対象State revision/fingerprintを固定
5. required predicatesを列挙
6. required evidenceを解決
7. evidence identity・scope・age・levelを検証
8. mandatory invariantsを評価
9. material contradictionsを評価
10. observed stateとtarget stateを比較
11. SATISFIED / NOT_SATISFIED / BLOCKED / STALE / CONTRADICTEDを決定
12. evaluation evidenceを保存
13. Authorityを照合
14. Atomic ReflowでCanonical Stateへ反映
```

Pseudo-rule：

```text
if subject is undefined:
    NOT_EVALUATED
elif policy is missing:
    BLOCKED
elif evidence is missing or insufficient:
    NOT_SATISFIED
elif evidence is stale:
    STALE
elif material contradiction exists:
    CONTRADICTED
elif mandatory invariant is not PASS:
    BLOCKED
elif observed state does not satisfy target:
    NOT_SATISFIED
else:
    SATISFIED
```

`SATISFIED`後にAtomic Reflowが失敗した場合、Canonical Completion Stateは変更しない。

---

# 20. v0.1 Mandatory Completion Gate

```text
KERNEL_CORE_COMPLETE=true
MINIMAL_FIXTURE_BINDING=true
ONE_FULL_NATURAL_CYCLE_PASS=true

STATE_SERIALIZABLE=true
STATE_RELOADABLE=true
STATE_DETERMINISTIC=true
STATE_REVISIONED=true
SEMANTIC_FINGERPRINT_STABLE=true
VOLATILE_METADATA_EXCLUDED=true
SCHEMA_VERSIONED=true

ATOMIC_COMMIT_PROVEN=true
STALE_UPDATE_BLOCKED=true
DUPLICATE_CHANGE_IDEMPOTENT=true
PARTIAL_WRITE_NOT_CANONICAL=true
CRASH_RECOVERY_PROVEN=true

OBJECTIVE_AUTHORITY_ENFORCED=true
PROHIBITED_CHANGE_BLOCKED=true
STALE_APPROVAL_REJECTED=true
CHANGE_CANNOT_SELF_CLOSE=true

OBSERVATION_EVIDENCE_PROVEN=true
CHANGE_RESULT_EVIDENCE_PROVEN=true
NEGATIVE_EVIDENCE_BOUNDED=true
EVIDENCE_REQUIRED_FOR_CLOSE=true

LINEAGE_APPEND_ONLY=true
STATE_RECONSTRUCTABLE=true
SESSION_INDEPENDENT=true
AGENT_REQUIRED_FOR_KERNEL=false

ALL_V01_MANDATORY_INVARIANTS=PASS
UNRESOLVED_MATERIAL_CONTRADICTIONS=0
```

全てが同一release candidate、同一State lineage、同一Natural Cycle Evidenceへ接続していなければならない。

過去の別実装、別Fixture、別StateからPASSを寄せ集めてはならない。

---

# 21. Human-Facing Status

Humanへ状態を表示する場合、単独の進捗率だけをCompletionとして提示しない。

最低限、次を示す。

```text
SUBJECT
TARGET CLAIM
CURRENT PROVEN LEVEL
EVIDENCE LEVEL
EVALUATION STATUS
OPEN DIFFERENCES
BLOCKERS
MATERIAL CONTRADICTIONS
NEXT AUTHORIZED CHANGE
HUMAN ACTION REQUIRED
```

推奨表示：

```text
Subject: Kernel v0.1
Target: ONE_FULL_NATURAL_CYCLE_PASS
Current proven level: TEST_VERIFIED
Evidence: E2
Status: NOT_SATISFIED
Open difference: D-CYCLE-001
Blocker: after-state re-observation not connected
Human action: None
```

「ほぼ完成」「実質完成」「コード上は完成」のような非Canonical表現をCompletion Stateとして使用しない。

---

# 22. Final Completion Declaration

```text
DESIGNED IS NOT IMPLEMENTED.

IMPLEMENTED IS NOT VERIFIED.

VERIFIED IN TEST IS NOT CONNECTED.

CONNECTED IS NOT NATURALLY REACHABLE.

NATURALLY REACHABLE IS NOT RUNTIME PROVEN.

RUNTIME PROVEN IS NOT OBJECTIVE COMPLETE.

CHANGE EXECUTED IS NOT DIFFERENCE CLOSED.

DIFFERENCE CLOSED IS NOT SYSTEM COMPLETE.

UNKNOWN IS NEVER PASS.

NO CLAIM OUTLIVES ITS IDENTITY, SCOPE, STATE, OR EVIDENCE.

NO COMPLETION BECOMES CANONICAL WITHOUT ATOMIC REFLOW.
```

完成とは、作業が止まることではない。

Target StateとObserved Stateの差異が、定義されたScopeにおいて、十分なEvidenceによって閉じられ、その判定がCanonical Stateへ還流された状態である。

> 完了を宣言するな。完了を証明せよ。  
> 証明を飾るな。ScopeとIdentityを保存せよ。  
> 成功だけを残すな。失敗と矛盾も還流せよ。  
> そして、次のStateから再び観測せよ。
