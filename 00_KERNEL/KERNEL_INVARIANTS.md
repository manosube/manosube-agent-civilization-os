# MANOSUBE Agent Civilization OS

## Canonical Kernel Invariants

```text
DOC_TYPE=KERNEL_INVARIANT_REGISTRY
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=KERNEL-INVARIANTS-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
CONSTITUTION_REF=00_KERNEL/KERNEL_CONSTITUTION.md
PARENT_OS=manosube/manosube-civilization-os
PARENT_BASELINE_COMMIT=0de548c9e4aa3a94fca2df07ccc710577f1534ff
CANONICAL_KERNEL_COUNT=1
CANONICAL_STATE_OWNER_COUNT=1
PARALLEL_CANONICAL_AUTHORITY=0
INVARIANT_FAILURE_POLICY=FAIL_CLOSED
```

---

# 0. この文書の地位

`KERNEL_INVARIANTS.md`は、Canonical Kernel Constitutionを実装・検証可能な不変条件へ変換する正式台帳である。

憲法が「何を守るか」を定めるのに対し、本書は次を固定する。

```text
何が常に真でなければならないか
何を観測すれば違反と判定できるか
どのEvidenceが必要か
どの段階で検証するか
違反時に何を停止するか
どの条件で復帰できるか
```

Invariantは推奨事項ではない。

一つでも満たされない場合、その対象State、Change、Evidence、Transition、ProjectionまたはCompletion ClaimをCanonicalとして受理してはならない。

```text
INVARIANT_RESULT=PASS
→ 次の評価へ進める

INVARIANT_RESULT=FAIL
→ REJECT / QUARANTINE / BLOCK

INVARIANT_RESULT=UNKNOWN
→ PASSにしない
```

---

# 1. InvariantのCanonical形式

各Invariantは次の意味を持つ。

```text
INVARIANT_ID
NAME
CLAIM
SCOPE
MUST_HOLD
VIOLATION
REQUIRED_EVIDENCE
VERIFICATION_STAGE
FAILURE_ACTION
RECOVERY_CONDITION
CONSTITUTION_REF
```

状態語彙は次に限定する。

```text
PASS
FAIL
UNKNOWN
UNOBSERVED
BLOCKED
NOT_APPLICABLE
```

`NOT_APPLICABLE`は、適用条件が機械的に偽である場合だけ使用できる。観測不足、実装不足、Evidence不足を`NOT_APPLICABLE`で隠してはならない。

---

# 2. Failure Semantics

Invariant違反はFail Closedで扱う。

```text
FAIL_CLOSED
= Canonical採用を拒否する
+ 違反Evidenceを保存する
+ 対象をQuarantineまたはBlockedへ遷移する
+ 既存Canonical Stateを保持する
+ 必要なStructural Differenceを生成する
```

Invariant違反時に禁止する処理：

```text
失敗したTransitionを再ラベルしてPASSにする
古いEvidenceで代用する
Fallback ArtifactをCanonicalへ昇格する
Completion Policyを弱める
Objectiveを変更する
違反記録を削除する
新しいParallel Ownerを作る
```

---

# 3. Supreme Invariant Set

次はすべてのSchema、Engine、Binding、Adapter、Agent、Verification、Applicationに優先する最高不変条件である。

```text
K-001 CANONICAL_KERNEL_SINGLETON
K-002 CANONICAL_STATE_OWNER_SINGLETON
K-003 NO_PARALLEL_CANONICAL_AUTHORITY
K-004 CANONICAL_CYCLE_ORDER_PRESERVED

A-001 HUMAN_OWNS_OBJECTIVE
A-002 CAPABILITY_IS_NOT_AUTHORITY
A-003 AUTHORITY_PRECEDES_EXECUTION
A-004 PROHIBITION_OVERRIDES_CAPABILITY
A-005 APPROVAL_BOUND_TO_EXACT_CHANGE_AND_STATE

S-001 SEMANTIC_STATE_SEPARATED_FROM_METADATA
S-002 SEMANTIC_FINGERPRINT_DETERMINISTIC
S-003 VOLATILE_AND_SECRET_FIELDS_EXCLUDED
S-004 STATE_REVISION_MONOTONIC
S-005 CURRENT_STATE_RECONSTRUCTABLE

O-001 OBSERVATION_PRECEDES_DIFFERENCE
O-002 OBSERVATION_SCOPE_EXPLICIT
O-003 UNKNOWN_IS_NOT_PASS
O-004 NEGATIVE_CLAIM_BOUNDED

D-001 DIFFERENCE_IS_CANONICAL_WORK_IDENTITY
D-002 DIFFERENCE_DERIVED_FROM_TARGET_AND_OBSERVED_STATE
D-003 CHANGE_CANNOT_CLOSE_DIFFERENCE
D-004 REOBSERVATION_PRECEDES_CLOSURE

C-001 CHANGE_BOUND_TO_DIFFERENCE
C-002 CHANGE_BOUND_TO_BEFORE_STATE
C-003 STALE_CHANGE_REJECTED
C-004 DUPLICATE_CHANGE_IDEMPOTENT
C-005 PARTIAL_WRITE_NOT_CANONICAL

E-001 OBSERVATION_EVIDENCE_REQUIRED
E-002 CHANGE_RESULT_EVIDENCE_REQUIRED
E-003 EVIDENCE_IMMUTABLE
E-004 EVIDENCE_SUFFICIENCY_REQUIRED_FOR_CLOSURE
E-005 EVIDENCE_LEVEL_NOT_OVERSTATED

R-001 REFLOW_ATOMIC
R-002 LINEAGE_APPEND_ONLY
R-003 TRANSITION_CHAIN_CONTIGUOUS
R-004 CONTRADICTIONS_PRESERVED
R-005 FAILED_AND_BLOCKED_RESULTS_REFLOWED

B-001 PROJECT_BOUND_BEFORE_CHANGE
B-002 BOUND_CONTENT_NOT_AUTHORITY
B-003 BOUNDARY_ESCAPE_BLOCKED
B-004 SECRET_NOT_PERSISTED

X-001 ADAPTER_NOT_AUTHORITY
X-002 GITHUB_NOT_CANONICAL_STATE
X-003 AGENT_REPLACEABLE
X-004 CONVERSATION_AND_MEMORY_NOT_AUTHORITY

P-001 COMPLETION_LEVELS_NOT_COLLAPSED
P-002 CONNECTED_REQUIRES_IDENTITY_PRESERVATION
P-003 NATURAL_ROUTE_REQUIRED_FOR_V01
P-004 UNRESOLVED_CONTRADICTIONS_BLOCK_COMPLETION
```

---

# 4. Kernel Identity Invariants

## K-001 — CANONICAL_KERNEL_SINGLETON

```text
CLAIM:
Canonical Kernelは一つだけ存在する。

MUST_HOLD:
CANONICAL_KERNEL_COUNT=1

VIOLATION:
Adapter、Model、CLI、GitHub、RuntimeまたはProject固有の
独立Kernel semanticsまたはState Transition実装が存在する。

REQUIRED_EVIDENCE:
dependency graph
kernel entry-point inventory
state-transition implementation inventory

VERIFICATION_STAGE:
static / integration / release

FAILURE_ACTION:
release block
duplicate implementation quarantine
structural difference creation

RECOVERY_CONDITION:
独立実装を除去し、全入口が同一Kernelを呼ぶことを再検証する。
```

## K-002 — CANONICAL_STATE_OWNER_SINGLETON

```text
CLAIM:
同一Project StateのCanonical Ownerは一つである。

MUST_HOLD:
CANONICAL_STATE_OWNER_COUNT=1

VIOLATION:
Repository、GitHub、Adapter、Agent、Fixture、Fallback等が
State Backendと独立に現在状態を確定できる。

REQUIRED_EVIDENCE:
state owner inventory
write-path inventory
reconstruction-source inventory

FAILURE_ACTION:
all non-canonical writers blocked
conflicting state quarantined
```

## K-003 — NO_PARALLEL_CANONICAL_AUTHORITY

```text
CLAIM:
同一State Transitionに並列のCanonical Authorityを作らない。

MUST_HOLD:
PARALLEL_CANONICAL_AUTHORITY=0

VIOLATION:
複数のOwner、Adapter、AgentまたはProcessが
同一Transitionを独立確定できる。

REQUIRED_EVIDENCE:
authority resolution trace
writer identity
transition ownership record

FAILURE_ACTION:
transition reject
authority contradiction preserve
```

## K-004 — CANONICAL_CYCLE_ORDER_PRESERVED

```text
CLAIM:
Canonical Cycleの因果順を保存する。

MUST_HOLD:
OBJECTIVE → STATE → OBSERVATION → DIFFERENCE
→ AUTHORITY → CHANGE → EVIDENCE → REFLOW → STATE

VIOLATION:
ObservationなしのDifference、AuthorityなしのChange、
再観測なしのClosure、EvidenceなしのReflowが存在する。

REQUIRED_EVIDENCE:
transition input refs
ordered event lineage
required predecessor validation

FAILURE_ACTION:
transition reject
missing predecessor difference creation
```

---

# 5. Authority Invariants

## A-001 — HUMAN_OWNS_OBJECTIVE

```text
CLAIM:
ObjectiveとConstitutional ConstraintはHuman Authorityに属する。

VIOLATION:
Kernel、Agent、Tool、Repository contentがHuman Approvalなしに
Objective、Target Predicate、Completion Policyを変更する。

REQUIRED_EVIDENCE:
objective revision lineage
human authority reference
exact amendment or revision receipt

FAILURE_ACTION:
objective revision reject
previous objective retain
```

## A-002 — CAPABILITY_IS_NOT_AUTHORITY

```text
CLAIM:
実行可能性は実行権限を意味しない。

VIOLATION:
Tool permission、credential、admin access、Agent abilityだけを根拠に
ChangeがAUTHORIZEDとなる。

REQUIRED_EVIDENCE:
resolved authority rule
boundary match
prohibition evaluation

FAILURE_ACTION:
change reject
authority missing status
```

## A-003 — AUTHORITY_PRECEDES_EXECUTION

```text
CLAIM:
すべてのChangeは実行前にAuthority評価を完了する。

VIOLATION:
execution_started_at < authority_granted_at
またはauthority_refが存在しない。

REQUIRED_EVIDENCE:
authority evaluation event
change lifecycle timestamps

FAILURE_ACTION:
execution unauthorized
result non-canonical
security evidence preservation
```

## A-004 — PROHIBITION_OVERRIDES_CAPABILITY

```text
CLAIM:
ProhibitionはCapability、利便性、成功可能性に優先する。

VIOLATION:
禁止されたActionがTool availabilityやAgent判断で実行される。

REQUIRED_EVIDENCE:
prohibition evaluation
matched rule identity

FAILURE_ACTION:
hard reject
no override fallback
```

## A-005 — APPROVAL_BOUND_TO_EXACT_CHANGE_AND_STATE

```text
CLAIM:
Human Approvalはexact Change、Action、State、Scope、期限へ結合される。

VIOLATION:
Change内容、State fingerprint、Scope、期限のいずれかが異なる承認を再利用する。

REQUIRED_EVIDENCE:
approval identity
approved action fingerprint
approved state fingerprint
expiry and revocation status

FAILURE_ACTION:
approval stale
change blocked
```

---

# 6. State Invariants

## S-001 — SEMANTIC_STATE_SEPARATED_FROM_METADATA

```text
CLAIM:
Projectの意味状態と観測Metadataを分離する。

VIOLATION:
observed_at、observer、session等がSemantic Stateへ混入する。

REQUIRED_EVIDENCE:
schema validation
semantic/metadata field classification

FAILURE_ACTION:
state reject
schema violation quarantine
```

## S-002 — SEMANTIC_FINGERPRINT_DETERMINISTIC

```text
CLAIM:
同一schema version・同一Semantic Stateは常に同一Fingerprintを生成する。

MUST_HOLD:
HASH(A)=HASH(B) when canonical_semantic_state(A)=canonical_semantic_state(B)

REQUIRED_EVIDENCE:
canonical serialization vectors
repeated process test
cross-session test

FAILURE_ACTION:
state persistence block
release block
```

## S-003 — VOLATILE_AND_SECRET_FIELDS_EXCLUDED

```text
CLAIM:
揮発値と秘密値をSemantic Fingerprintおよび公開Evidenceへ含めない。

VIOLATION:
timestamp、temporary path、Agent名、session ID、token、credential本文が
Fingerprint入力またはEvidence本文に含まれる。

REQUIRED_EVIDENCE:
canonicalization field audit
secret scanning result

FAILURE_ACTION:
artifact quarantine
secret incident procedure
```

## S-004 — STATE_REVISION_MONOTONIC

```text
CLAIM:
Canonical State revisionはTransitionごとに単調増加する。

MUST_HOLD:
resulting_revision = previous_revision + 1

VIOLATION:
revision reuse、skip、rollback overwrite、同一revision複数fingerprint。

REQUIRED_EVIDENCE:
transition lineage scan

FAILURE_ACTION:
transition chain invalid
reconstruction required
```

## S-005 — CURRENT_STATE_RECONSTRUCTABLE

```text
CLAIM:
Current Stateはappend-only lineageから決定的に再構築できる。

MUST_HOLD:
reconstruct(events).fingerprint = current_state.fingerprint

REQUIRED_EVIDENCE:
clean-backend reconstruction test
cross-session reload test

FAILURE_ACTION:
current state non-canonical
state backend blocked
recovery required
```

---

# 7. Observation Invariants

## O-001 — OBSERVATION_PRECEDES_DIFFERENCE

```text
CLAIM:
DifferenceはCurrent StateのObservationに基づいて導出する。

VIOLATION:
observation_refまたはobservation_evidence_refを持たないDifference。

FAILURE_ACTION:
difference reject
observation required
```

## O-002 — OBSERVATION_SCOPE_EXPLICIT

```text
CLAIM:
Observationは対象、範囲、方法、時間境界、死角を明示する。

VIOLATION:
scope不明のObservationを完全観測として使用する。

REQUIRED_EVIDENCE:
observation scope record
method identity
completion status

FAILURE_ACTION:
observation incomplete
claim strength capped
```

## O-003 — UNKNOWN_IS_NOT_PASS

```text
CLAIM:
UNKNOWN、UNOBSERVED、BLOCKED、INCOMPLETEをPASSへ変換しない。

VIOLATION:
観測不能をabsence、healthy、complete、connectedとして扱う。

FAILURE_ACTION:
completion claim reject
status restored to observed value
```

## O-004 — NEGATIVE_CLAIM_BOUNDED

```text
CLAIM:
Negative Claimは有限の観測条件へ結合される。

REQUIRED_FIELDS:
observation_scope
observation_start
observation_end
method
attempt_count
completion_status
known_blind_spots

VIOLATION:
検索0件だけで「存在しない」「一度も到達しない」と主張する。

FAILURE_ACTION:
negative claim reject
NO_RESULT status retain
```

---

# 8. Difference Invariants

## D-001 — DIFFERENCE_IS_CANONICAL_WORK_IDENTITY

```text
CLAIM:
Canonical Work IdentityはDifference IDである。

VIOLATION:
Issue、PR、Task、Agent sessionだけでWork Identityを保持する。

REQUIRED_EVIDENCE:
canonical difference record
projection identity mapping

FAILURE_ACTION:
work projection non-canonical
```

## D-002 — DIFFERENCE_DERIVED_FROM_TARGET_AND_OBSERVED_STATE

```text
CLAIM:
DifferenceはTarget StateとObserved Stateの明示的比較から導出される。

REQUIRED_FIELDS:
target_state_ref
observed_state_ref
structural_difference
impact
closure_policy

FAILURE_ACTION:
difference reject
```

## D-003 — CHANGE_CANNOT_CLOSE_DIFFERENCE

```text
CLAIM:
Change自身はDifferenceをCLOSEDへ遷移できない。

VIOLATION:
execution successまたはAgent reportが直接Closureを設定する。

FAILURE_ACTION:
closure reject
difference OPEN retain
```

## D-004 — REOBSERVATION_PRECEDES_CLOSURE

```text
CLAIM:
Closureより前にChange後の独立再観測が存在する。

REQUIRED_EVIDENCE:
after-observation ref
change-result evidence ref
closure evaluation ref

FAILURE_ACTION:
closure blocked
```

---

# 9. Change and Persistence Invariants

## C-001 — CHANGE_BOUND_TO_DIFFERENCE

```text
CLAIM:
すべてのChangeは一つ以上の有効なDifferenceへ結合される。

VIOLATION:
difference_refなしのConvenience Change、scope expansion、untracked mutation。

FAILURE_ACTION:
change reject
```

## C-002 — CHANGE_BOUND_TO_BEFORE_STATE

```text
CLAIM:
Changeはexact before state fingerprintとexpected revisionへ結合される。

REQUIRED_FIELDS:
before_state_fingerprint
expected_state_revision

FAILURE_ACTION:
change invalid
```

## C-003 — STALE_CHANGE_REJECTED

```text
CLAIM:
Expected revisionまたはfingerprintがCurrent Stateと異なるChangeを実行しない。

MUST_HOLD:
expected_revision = current_revision
expected_fingerprint = current_fingerprint

FAILURE_ACTION:
status=STALE
no mutation
re-observation required
```

## C-004 — DUPLICATE_CHANGE_IDEMPOTENT

```text
CLAIM:
同一idempotency keyの再実行は同一結果を返し、二重Transitionを生成しない。

REQUIRED_EVIDENCE:
duplicate execution test
transition count assertion

FAILURE_ACTION:
state backend block
```

## C-005 — PARTIAL_WRITE_NOT_CANONICAL

```text
CLAIM:
部分書込、未完了temp file、不正schema、不一致fingerprintをCanonicalとして読まない。

REQUIRED_EVIDENCE:
crash injection test
partial-write recovery test
quarantine receipt

FAILURE_ACTION:
artifact quarantine
previous canonical state retain
```

---

# 10. Evidence Invariants

## E-001 — OBSERVATION_EVIDENCE_REQUIRED

```text
CLAIM:
Observed StateとDifference ClaimはObservation Evidenceを持つ。

VIOLATION:
会話、推測、古い報告だけをObserved Stateの根拠にする。

FAILURE_ACTION:
claim unverified
difference not derivable
```

## E-002 — CHANGE_RESULT_EVIDENCE_REQUIRED

```text
CLAIM:
Change後のState Claimは再観測されたChange Result Evidenceを持つ。

VIOLATION:
execution return code、Agent success report、file existenceだけでAfter Stateを確定する。

FAILURE_ACTION:
after state unconfirmed
closure blocked
```

## E-003 — EVIDENCE_IMMUTABLE

```text
CLAIM:
受理済みEvidence本文は不変である。

VIOLATION:
既存Evidenceの上書き、削除、意味変更。

REQUIRED_EVIDENCE:
content fingerprint
append-only storage verification

FAILURE_ACTION:
evidence integrity incident
dependent claims invalidated
```

## E-004 — EVIDENCE_SUFFICIENCY_REQUIRED_FOR_CLOSURE

```text
CLAIM:
Difference ClosureはClosure Policyを満たすEvidenceを必要とする。

MUST_HOLD:
all required claims satisfied
minimum evidence level satisfied
age and scope constraints satisfied
independence requirement satisfied

FAILURE_ACTION:
difference OPEN or BLOCKED
```

## E-005 — EVIDENCE_LEVEL_NOT_OVERSTATED

```text
CLAIM:
Evidence Levelは実際のObservation Methodを超えない。

VIOLATION:
unit testをE4、mockをruntime proof、単発runtimeをE6として記録する。

FAILURE_ACTION:
evidence level corrected downward
dependent completion reevaluated
```

---

# 11. Reflow and Lineage Invariants

## R-001 — REFLOW_ATOMIC

```text
CLAIM:
Transition Event appendとCurrent State更新は単一の原子的Commitとして成立する。

VIOLATION:
eventだけ存在、current stateだけ更新、half-committed revision。

REQUIRED_EVIDENCE:
atomic commit integration test
crash boundary tests

FAILURE_ACTION:
commit reject or recover
partial output quarantine
```

## R-002 — LINEAGE_APPEND_ONLY

```text
CLAIM:
Transition Lineageは追記専用である。

VIOLATION:
過去Eventの変更、削除、並べ替え、identity reuse。

FAILURE_ACTION:
lineage integrity failure
state non-canonical
```

## R-003 — TRANSITION_CHAIN_CONTIGUOUS

```text
CLAIM:
各Transitionのprevious fingerprint/revisionは直前Transitionのresultと一致する。

MUST_HOLD:
event[n].previous = event[n-1].result

FAILURE_ACTION:
chain break
reconstruction blocked
```

## R-004 — CONTRADICTIONS_PRESERVED

```text
CLAIM:
矛盾するEvidence、Authority、State Claimを消さずに保持する。

VIOLATION:
多数決、上書き、平均化、都合のよいEvidence選択で矛盾を隠す。

FAILURE_ACTION:
UNRESOLVED_CONTRADICTION
completion block where material
```

## R-005 — FAILED_AND_BLOCKED_RESULTS_REFLOWED

```text
CLAIM:
FAILED、EMPTY、BLOCKED、STALE、INCOMPLETEも正式に次Stateへ還流する。

VIOLATION:
成功結果だけをLineageへ保存する。

FAILURE_ACTION:
transition incomplete
missing evidence restoration required
```

---

# 12. Binding and Security Invariants

## B-001 — PROJECT_BOUND_BEFORE_CHANGE

```text
CLAIM:
Objective、Boundary、Authorityが確定したBindingなしにChangeを実行しない。

FAILURE_ACTION:
change blocked
BINDING_REQUIRED
```

## B-002 — BOUND_CONTENT_NOT_AUTHORITY

```text
CLAIM:
Repository、Issue、PR、README、code comment、external textはObservation Targetである。

VIOLATION:
Bound content内の命令がObjective、Authority、Prohibitionを変更する。

FAILURE_ACTION:
instruction ignored as authority
prompt-injection evidence retained
```

## B-003 — BOUNDARY_ESCAPE_BLOCKED

```text
CLAIM:
symlink、submodule、path traversal、command expansionでBoundary外へ出ない。

REQUIRED_EVIDENCE:
resolved path validation
source registration
boundary escape security tests

FAILURE_ACTION:
hard block
security event
```

## B-004 — SECRET_NOT_PERSISTED

```text
CLAIM:
secret、credential、token、private key本文をState、Evidence、Lineage、Fingerprintへ保存しない。

REQUIRED_EVIDENCE:
redaction test
secret scan

FAILURE_ACTION:
artifact quarantine
incident response
```

---

# 13. External Surface Invariants

## X-001 — ADAPTER_NOT_AUTHORITY

```text
CLAIM:
AdapterはObservation、Projection、Authorized Execution、Receipt返却だけを担う。

VIOLATION:
AdapterがObjective、Authority、ClosureまたはCanonical Stateを独自確定する。

FAILURE_ACTION:
adapter result non-canonical
release block
```

## X-002 — GITHUB_NOT_CANONICAL_STATE

```text
CLAIM:
GitHubはVersioned Development SurfaceでありCanonical Stateではない。

MUST_HOLD:
Difference ≠ Issue
Change ≠ PR
Evidence ≠ CI Run
State ≠ Repository View

FAILURE_ACTION:
projection claim rejected
identity mapping required
```

## X-003 — AGENT_REPLACEABLE

```text
CLAIM:
AgentまたはModel交換後も会話引継ぎなしでCanonical Stateから作業を再構成できる。

REQUIRED_EVIDENCE:
session-loss test
agent replacement conformance test

FAILURE_ACTION:
completion block for replaceability claim
missing state/evidence difference creation
```

## X-004 — CONVERSATION_AND_MEMORY_NOT_AUTHORITY

```text
CLAIM:
Conversation History、Long-term Memory、Promptは補助情報でありCanonical Authorityではない。

VIOLATION:
State Backendに存在しない会話上の決定だけでChangeまたはClosureを確定する。

FAILURE_ACTION:
claim unconfirmed
canonical recording required
```

---

# 14. Completion Invariants

## P-001 — COMPLETION_LEVELS_NOT_COLLAPSED

```text
CLAIM:
次の状態を独立に保持する。

DESIGNED
IMPLEMENTED
STATICALLY_VERIFIED
TEST_VERIFIED
INTEGRATED
NATURALLY_REACHABLE
RUNTIME_PROVEN
HUMAN_ACCEPTED

VIOLATION:
下位状態から上位状態を自動推定する。

FAILURE_ACTION:
completion status corrected to strongest proven level
```

## P-002 — CONNECTED_REQUIRES_IDENTITY_PRESERVATION

```text
CLAIM:
CONNECTEDは同一identityのproducer-consumer接続を要求する。

MUST_HOLD:
previous output generated
same output consumed by next stage
identity preserved
canonical owner count = 1
no substitute evidence
next canonical artifact generated

FAILURE_ACTION:
CONNECTED=false
first broken edge recorded
```

## P-003 — NATURAL_ROUTE_REQUIRED_FOR_V01

```text
CLAIM:
Kernel v0.1完成にはMinimal Fixture Binding上の自然一周が必要である。

MUST_HOLD:
OBJECTIVE
→ STATE
→ OBSERVATION
→ OBSERVATION EVIDENCE
→ DIFFERENCE
→ AUTHORITY
→ CHANGE
→ RE-OBSERVATION
→ CHANGE RESULT EVIDENCE
→ CLOSURE EVALUATION
→ ATOMIC REFLOW
→ NEW STATE

VIOLATION:
文書、mock、unit test、手動State編集だけでv0.1 COMPLETEを宣言する。

FAILURE_ACTION:
KERNEL_V0_1_COMPLETE=false
```

## P-004 — UNRESOLVED_CONTRADICTIONS_BLOCK_COMPLETION

```text
CLAIM:
Completion Claimに影響する未解決矛盾が0件である。

MUST_HOLD:
UNRESOLVED_MATERIAL_CONTRADICTIONS=0

FAILURE_ACTION:
completion blocked
contradiction remains visible
```

---

# 15. Verification Matrix

| Invariant Class | Static | Unit | Integration | Natural Cycle | Runtime | Release |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Kernel Identity | ✓ |  | ✓ | ✓ |  | ✓ |
| Authority | ✓ | ✓ | ✓ | ✓ | 必要時 | ✓ |
| State | ✓ | ✓ | ✓ | ✓ |  | ✓ |
| Observation | ✓ | ✓ | ✓ | ✓ | v0.4以降 | ✓ |
| Difference | ✓ | ✓ | ✓ | ✓ |  | ✓ |
| Change | ✓ | ✓ | ✓ | ✓ | 必要時 | ✓ |
| Evidence | ✓ | ✓ | ✓ | ✓ | v0.4以降 | ✓ |
| Reflow / Lineage | ✓ | ✓ | ✓ | ✓ |  | ✓ |
| Binding / Security | ✓ | ✓ | ✓ | ✓ | v0.4以降 | ✓ |
| External Surface | ✓ | ✓ | ✓ | v0.3以降 | v0.4以降 | ✓ |
| Completion | ✓ |  | ✓ | ✓ | 対象Version依存 | ✓ |

空欄は検証不要を意味する。`UNKNOWN`を意味しない。

---

# 16. v0.1 Mandatory Gate

v0.1では、少なくとも次を機械検証する。

```text
K-001 PASS
K-002 PASS
K-003 PASS
K-004 PASS

A-001 PASS
A-002 PASS
A-003 PASS
A-004 PASS
A-005 PASS

S-001 PASS
S-002 PASS
S-003 PASS
S-004 PASS
S-005 PASS

O-001 PASS
O-002 PASS
O-003 PASS
O-004 PASS

D-001 PASS
D-002 PASS
D-003 PASS
D-004 PASS

C-001 PASS
C-002 PASS
C-003 PASS
C-004 PASS
C-005 PASS

E-001 PASS
E-002 PASS
E-003 PASS
E-004 PASS
E-005 PASS

R-001 PASS
R-002 PASS
R-003 PASS
R-004 PASS
R-005 PASS

B-001 PASS
B-002 PASS
B-003 PASS
B-004 PASS

X-001 PASS
X-002 PASS
X-004 PASS

P-001 PASS
P-002 PASS
P-003 PASS
P-004 PASS
```

`X-003 AGENT_REPLACEABLE`はv0.1ではAgentを使用しないため、次の限定Claimで検証する。

```text
AGENT_REQUIRED_FOR_KERNEL=false
SESSION_INDEPENDENT=true
```

正式なMulti-Model Agent Replaceabilityはv0.7で自然証明する。

---

# 17. Invariant Evaluation Record

各検証結果は最低限、次で保存する。

```yaml
evaluation_id: INV-EVAL-0001
invariant_id: K-001
subject_ref: null
state_revision: null
state_fingerprint: null
verification_stage: STATIC
method: null
expected: PASS
observed: null
status: UNKNOWN
evidence_refs: []
evaluated_at: null
evaluator_capability: null
authority_ref: null
remaining_differences: []
```

Evaluator名やAgent名はMetadataであり、Invariantの真偽を決めない。

評価結果の`PASS`は、参照Evidenceが存在し、対象Scopeが完全で、検証方法がInvariantに適合する場合だけ許可する。

---

# 18. Release Rule

Version Release前に、そのVersionへ適用される全Mandatory Invariantを再評価する。

```text
ALL_MANDATORY_INVARIANTS=PASS
AND
NO_REQUIRED_INVARIANT=UNKNOWN
AND
NO_REQUIRED_INVARIANT=UNOBSERVED
AND
NO_MATERIAL_CONTRADICTION
→ RELEASE MAY PROCEED
```

それ以外は、

```text
RELEASE_BLOCKED
```

である。

過去VersionのPASSを、変更後VersionのPASSとして無条件に再利用してはならない。影響を受けたInvariantは、新しいState、Change、Schema、Engineに対して再評価する。

---

# 19. Amendment Rule

Invariantの追加、削除、弱化、Failure Action変更はConstitutional Changeとして扱う。

必要条件：

```text
HUMAN_CONSTITUTIONAL_AUTHORITY
STRUCTURAL_REASON
AFFECTED_CONSTITUTION_ARTICLES
COMPATIBILITY_ANALYSIS
SECURITY_IMPACT
MIGRATION_PLAN
UPDATED_TESTS
NATURAL_CYCLE_EVIDENCE_PLAN
```

次を目的とした変更を禁止する。

```text
失敗をPASSに変える
UNKNOWNをPASSに変える
Evidence要件を外す
自然経路をmockで代替する
Human AuthorityをAgentへ移す
Parallel Canonical Ownerを許可する
Lineageを書換可能にする
```

---

# 20. Final Invariant Declaration

```text
ONE KERNEL.
ONE CANONICAL STATE OWNER.
NO PARALLEL AUTHORITY.

OBJECTIVE BEFORE WORK.
OBSERVATION BEFORE DIFFERENCE.
DIFFERENCE BEFORE CHANGE.
AUTHORITY BEFORE EXECUTION.
RE-OBSERVATION BEFORE CLOSURE.
EVIDENCE BEFORE REFLOW.

NO UNKNOWN IS PASS.
NO CAPABILITY IS AUTHORITY.
NO CHANGE CONFIRMS ITSELF.
NO PARTIAL WRITE IS CANONICAL.
NO ADAPTER OWNS THE STATE.
NO CONVERSATION REPLACES LINEAGE.

EVERY FAILURE REMAINS EVIDENCE.
EVERY CONTRADICTION REMAINS VISIBLE.
EVERY CANONICAL STATE IS RECONSTRUCTABLE.
```

Invariantは、Kernelを硬直させるために存在しない。

Kernelが変化の中で同一性を失わず、失敗を隠さず、権限を越えず、証拠によって次のStateへ還流し続けるために存在する。

> 守るべきものを曖昧にするな。  
> 観測できないものをPASSにするな。  
> 変化したものを証拠なく確定するな。  
> 循環を守り、固定を見つけ、差異を閉じよ。
