# MANOSUBE Agent Civilization OS

## Difference Lifecycle Contract v0.1

```text
DOC_TYPE=KERNEL_CONTRACT
KERNEL_ELEMENT=DIFFERENCE
DOCUMENT_ID=DIFFERENCE-LIFECYCLE-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
```

---

# 0. Purpose

本Contractは、Differenceの状態をclosed enumとappend-only transitionで固定し、作業開始、Change実行、test pass、PR mergeをClosureへ誤昇格させない。

# 1. Closed Status Enum

```text
DETECTED
OPEN
ACTIVE
VERIFYING
BLOCKED
RETAINED
CLOSED
REOPENED
SUPERSEDED
INVALIDATED
```

未知status、自由記述status、`COMPLETED`、`DONE`、`MERGED`、`DEPLOYED`をDifference statusとして使用しない。

# 2. Status Semantics

| Status | Canonical meaning |
|---|---|
| `DETECTED` | exact ObservationからMismatch candidateを導出したが、identityとcontract validationが未確定 |
| `OPEN` | valid Difference identityとして受理され、未解決である |
| `ACTIVE` | authorizedまたはauthorization待ちのWork Unitが結合され、解決処理が進行中 |
| `VERIFYING` | Change後、Observation Work後、または外部状態変化後の独立したafter-state検証とEvidence Sufficiency評価を待つ |
| `BLOCKED` | 明示された阻害要因により次の合法transitionへ進めない |
| `RETAINED` | 現時点では閉じず、Evidence付きで次周期へ保持する |
| `CLOSED` | Closure Policyを満たし、Atomic ReflowでCanonical closureが確定した |
| `REOPENED` | Closed後のObservation反証、Closure Evidence失効／provenance不正、material contradiction、またはPolicy reopen condition成立によりClosure Claimの再評価が必要 |
| `SUPERSEDED` | materialに異なる後継Differenceへidentityが置換された |
| `INVALIDATED` | input、identity、boundary、schemaまたはlineage不正によりCanonical claimを失った |

# 3. Legal Transitions

v0.1のlegal transitionを次で固定する。

| From | To | Minimum gate |
|---|---|---|
| `null` | `DETECTED` | genesis event、candidate input、derivation profileが存在 |
| `DETECTED` | `OPEN` | identity、schema、exact input bindingがvalid |
| `DETECTED` | `INVALIDATED` | invalid inputまたはidentity conflict |
| `OPEN` | `ACTIVE` | Work Unit bindingとAuthority requirementが明示済み |
| `OPEN` | `BLOCKED` | blocker Evidenceが存在 |
| `OPEN` | `RETAINED` | retain reasonとnext observationが存在 |
| `OPEN` | `SUPERSEDED` | validな双方向supersession |
| `ACTIVE` | `VERIFYING` | `CHANGE_BOUND`: Changeは`EXECUTED`かつafter-state Observation要求済み、または`CHANGE_FREE`: Observation Workにより新しいafter-state verification Evidenceが存在 |
| `ACTIVE` | `BLOCKED` | executionまたはauthority blockerが存在 |
| `ACTIVE` | `RETAINED` | unresolved mismatchを次周期へ保持 |
| `ACTIVE` | `SUPERSEDED` | validな双方向supersession |
| `VERIFYING` | `CLOSED` | Closure Evaluationが`SATISFIED`かつAtomic Reflow |
| `VERIFYING` | `ACTIVE` | mismatchが残り、追加のauthorized Changeが必要 |
| `VERIFYING` | `BLOCKED` | Evidence不足、観測不能、stale、conflict |
| `VERIFYING` | `RETAINED` |未解決状態をEvidence付きで次周期へ保持 |
| `VERIFYING` | `SUPERSEDED` | validな双方向supersession |
| `BLOCKED` | `OPEN` | blocker解消後、まだWork Unit未開始 |
| `BLOCKED` | `ACTIVE` | blocker解消後、合法なWork Unitを再開 |
| `BLOCKED` | `VERIFYING` | blocker解消後、検証を再開 |
| `BLOCKED` | `RETAINED` | blockerを保持して次周期へ送る |
| `BLOCKED` | `SUPERSEDED` | validな双方向supersession |
| `RETAINED` | `OPEN` | 新周期で再評価し未着手として再開 |
| `RETAINED` | `ACTIVE` | 継続Work Unitを再開 |
| `RETAINED` | `VERIFYING` | 新Evidenceで検証を再開 |
| `RETAINED` | `BLOCKED` | blockerが確認された |
| `RETAINED` | `SUPERSEDED` | validな双方向supersession |
| `CLOSED` | `REOPENED` | 後続Observationによる反証、Closure Evidenceの失効／provenance不正、material contradiction、またはPolicy reopen condition成立 |
| `CLOSED` | `SUPERSEDED` | `DIFFERENCE_IDENTITY.md`のmaterial identity inputが一つ以上変更され、validなSupersession Relationが存在 |
| `REOPENED` | `ACTIVE` | authorized resolutionを再開 |
| `REOPENED` | `VERIFYING` | Change不要で新Evidenceを再評価 |
| `REOPENED` | `BLOCKED` | 再解決が阻害された |
| `REOPENED` | `RETAINED` | 未解決で次周期へ保持 |
| `REOPENED` | `SUPERSEDED` | validな双方向supersession |
| `OPEN` | `INVALIDATED` | schema、identity、boundary、State bindingまたはlineage defectを後発見 |
| `ACTIVE` | `INVALIDATED` | schema、identity、boundary、State bindingまたはlineage defectを後発見 |
| `VERIFYING` | `INVALIDATED` | schema、identity、boundary、State bindingまたはlineage defectを後発見 |
| `BLOCKED` | `INVALIDATED` | schema、identity、boundary、State bindingまたはlineage defectを後発見 |
| `RETAINED` | `INVALIDATED` | schema、identity、boundary、State bindingまたはlineage defectを後発見 |
| `CLOSED` | `INVALIDATED` | accepted DifferenceまたはClosure lineageのintegrity defectを後発見 |
| `REOPENED` | `INVALIDATED` | schema、identity、boundary、State bindingまたはlineage defectを後発見 |

`SUPERSEDED`と`INVALIDATED`はterminalである。`CLOSED`は反証により`REOPENED`できるため、歴史の終端ではない。

`CLOSED`、`BLOCKED`または`RETAINED`へ遷移する場合は、bound Closure Policyの`allowed_terminal_states`にto-statusが含まれ、exact Policy-bound Evaluationの`PROPOSED_TERMINAL_STATE_ALLOWED` gateがPASSでなければならない。Lifecycle表の個別minimum gateはこのPolicy gateを免除しない。

初回ClosureでもChangeを必須化しない。外部状態変化またはObservation WorkによりTargetが満たされた場合は、`OPEN → ACTIVE → VERIFYING`を通り、`ACTIVE → VERIFYING`の`CHANGE_FREE` gateを使用する。架空のChangeを生成してはならない。

# 4. Prohibited Transitions

上表にないtransitionはすべて禁止する。genesis eventは上表の`null → DETECTED`として扱い、通常transitionから暗黙に生成しない。特に次を禁止する。

```text
DETECTED → CLOSED
OPEN → CLOSED
ACTIVE → CLOSED
CHANGE EXECUTED → CLOSED
TEST PASS → CLOSED
PR MERGED → CLOSED
AGENT SUCCESS → CLOSED
BLOCKED → CLOSED
RETAINED → CLOSED
INVALIDATED → ANY
SUPERSEDED → ANY
```

# 5. Lifecycle Event

各transitionはappend-only eventとして保存する。

```yaml
schema_version: "0.1"
difference_event_id: D-EVT-...
difference_id: D-...
event_kind: TRANSITION
event_revision: 0
previous_event_id: null
from_status: null
to_status: DETECTED
state_revision_evaluated: 0
state_fingerprint_evaluated: {}
reason_code: DIFFERENCE_DERIVED
reason: ""
observation_refs: []
evidence_refs: []
authority_ref: null
change_refs: []
closure_evaluation_ref: null
reflow_transition_ref: null
next_observation_ref: null
reopen_trigger: null
reopen_condition_ref: null
reopen_condition_evaluation_ref: null
revoked_evidence_refs: []
invalid_evidence_refs: []
contradiction_evidence_refs: []
```

上記はclosed event shapeである。Reopen以外のeventでは全reopen-specific fieldをnullまたはemptyにする。`CLOSED → REOPENED`では`reopen_trigger`を第8節のclosed enumから必須指定し、同節のtrigger-specific表に従って各ref fieldの必須／任意／禁止を検証する。unknown fieldを拒否する。

`next_observation_ref`は、このContractが定義する次のclosed `NEXT_OBSERVATION_REQUEST` recordへのtyped referenceまたはnullである。

```yaml
schema_version: "0.1"
observation_request_id: OBS-REQ-...
record_kind: NEXT_OBSERVATION_REQUEST
difference_ref: {kind: difference, id: D-...}
derived_from_event_ref: {kind: difference_event, id: D-EVT-...}
state_revision_requested: 0
state_fingerprint_requested: {}
target_ref: {kind: target_predicate, id: TP-...}
scope_ref: {kind: observation_scope, id: OBS-SCOPE-...}
method_ref: {kind: observation_method, id: OBS-METHOD-...}
reason_code: BLOCKER_REOBSERVATION
```

`method_ref`は次のclosed、versioned immutable `OBSERVATION_METHOD` recordへ解決する。

```yaml
schema_version: "0.1"
record_kind: OBSERVATION_METHOD
observation_method_id: OBS-METHOD-...
method_profile: MANOSUBE-OBSERVATION-METHOD-SHA256-0.1
procedure_kind: CANONICAL_OBSERVER
procedure_ref: {kind: observer_procedure, id: PROC-..., version: "0.1", semantic_fingerprint: sha256:...}
normalization_profile: MANOSUBE-NORMALIZED-FACT-SHA256-0.1
input_contract_ref: {kind: schema, id: SCHEMA-...}
output_contract_refs:
  collection_kind: UNORDERED_SET
  members: []
execution_boundary_ref: {kind: execution_boundary, id: BOUNDARY-...}
```

Method ID inputは`schema_version`を含む上記recordから`observation_method_id`だけを除いたclosed payloadである。全refはimmutable version／semantic fingerprintまたはcontent addressへexactに解決する。inline command、shell text、ambient instruction、moving ref、unknown fieldを拒否する。

`output_contract_refs`はexplicit `UNORDERED_SET` wrapperであり、member canonical bytesで整列してduplicateを拒否する。bare array、`ORDERED_LIST`、unknown collection kindを拒否する。したがって同じ出力Contract集合の列挙順はMethod IDへ影響しない。

RequestとMethodのID algorithmを次で固定する。

```text
REQUEST_PROFILE=MANOSUBE-NEXT-OBSERVATION-REQUEST-SHA256-0.1
METHOD_PROFILE=MANOSUBE-OBSERVATION-METHOD-SHA256-0.1
DIGEST=SHA-256
SERIALIZATION=CANONICAL_JSON_UTF8
TEXT_NORMALIZATION=UNICODE_NFC
OBJECT_KEY_ORDER=LEXICOGRAPHIC
NUMBER_PROFILE=JSON_INTEGER_ONLY
UNKNOWN_FIELDS=REJECT
REQUEST_OUTPUT=OBS-REQ-<64 uppercase hexadecimal characters>
METHOD_OUTPUT=OBS-METHOD-<64 uppercase hexadecimal characters>
FINGERPRINT_OUTPUT=sha256:<64 lowercase hexadecimal characters>
```

Request／Method IDのSHA-256 digest bytesは、それぞれ`OBS-REQ-`／`OBS-METHOD-`にuppercase hexadecimalで連結してcommon identity schemaへ適合させる。semantic fingerprintを別途表す場合だけ`sha256:`＋lowercase hexadecimalを使用する。

Request ID inputは`schema_version + record_kind + difference_ref + derived_from_event_ref + state_revision_requested + state_fingerprint_requested + target_ref + scope_ref + method_ref + reason_code`である。Method ID inputは直前に定義したclosed payloadである。同一ID・同一payloadはidempotent、異なるpayloadはconflictとして拒否する。

Conformance vectorsは、object key順序変更によるID不変性、Unicode NFC同値性、各included field変更によるID変更、schema version変更によるID変更、unknown field／float／unresolved refのreject、既知request／method payloadに対する固定digestを含む。

各typed refはexactに解決でき、Difference、event head、State revision／fingerprint、Target、Scopeが相互に一致しなければならない。

`next_observation_ref`は`{kind: next_observation_request, id: OBS-REQ-...}`とする。to-statusが`BLOCKED`、`RETAINED`または`REOPENED`ならnon-nullを必須とする。その他transitionではPolicyが次観測を要求する場合だけnon-nullを許可する。unknown kind、解決不能ref、対象Difference／State不一致を拒否する。

Event revisionは0から連続し、predecessorはexactでなければならない。同一event ID・同一payloadはidempotent、異なるpayloadはconflictとして拒否する。

同じsemantic Differenceを再観測しstatusが変わらない場合、`TRANSITION`を偽造せず、次のstatus-preserving eventをappendする。

```yaml
event_kind: OBSERVATION_BOUND
from_status: OPEN
to_status: OPEN
observation_refs: [{kind: observation, id: OBS-...}]
evidence_refs: [{kind: observation_evidence, id: EVID-...}]
reason_code: EQUIVALENT_DIFFERENCE_REOBSERVED
```

`OBSERVATION_BOUND`では`from_status`と`to_status`がcurrent statusと同一でなければならない。これはLifecycle transitionではなくprovenance appendであり、第3節のlegal transition表によるstatus変更を発生させない。`DETECTED`、`OPEN`、`ACTIVE`、`VERIFYING`、`BLOCKED`、`RETAINED`、`REOPENED`で使用できる。

`CLOSED`、`SUPERSEDED`、`INVALIDATED`には`OBSERVATION_BOUND`をappendしない。`CLOSED`後に同じsemantic mismatchが再観測された場合は、必ず`CLOSED → REOPENED` transitionをappendする。これにより反証されたClosureをstatus-preserving eventで隠すことを禁止する。

# 6. Transition Authority

Lifecycle Engineはtransitionの構造的妥当性を評価するが、Human Authorityを生成しない。

`ACTIVE`へのtransitionは必要Authorityが解決されていることを意味しない。実行前に後段のAuthority Engineがexact Changeを評価する。

`CLOSED`へのtransition authorityはAtomic Reflowだけが持つ。

# 7. Blocked and Retained

`BLOCKED`は失敗の隠蔽ではない。最低限、blocker kind、scope、Evidence、解消条件、next observationを持つ。

`RETAINED`は完成でも放棄でもない。Mismatchを未解決のまま次のCanonical Stateへ還流する正式状態である。

# 8. Reopen

Reopenは旧Closure Eventを削除または書換えない。すべての新Eventはtrigger kindと対象Closure Evaluation refを持ち、trigger固有fieldを次のとおり要求する。

| Trigger | Required refs | Forbidden refs |
|---|---|---|
| `OBSERVATION_CONTRADICTION` | observation refs、contradicting Evidence refs | reopen condition refs |
| `CLOSURE_EVIDENCE_REVOKED` | revoked closure Evidence refs | reopen condition refs。observation refsは発見provenanceとしてoptional |
| `CLOSURE_EVIDENCE_INVALID` | invalid closure Evidence refs | reopen condition refs。observation refsは発見provenanceとしてoptional |
| `MATERIAL_CONTRADICTION` | contradiction Evidence refs | reopen condition refs |
| `POLICY_REOPEN_CONDITION_SATISFIED` | reopen condition ref、current Completion Evaluation ref、そのevaluation Evidence refs | invalidated／revoked closure Evidence refs |

```text
REOPEN_TRIGGER
= OBSERVATION_CONTRADICTION
| CLOSURE_EVIDENCE_REVOKED
| CLOSURE_EVIDENCE_INVALID
| MATERIAL_CONTRADICTION
| POLICY_REOPEN_CONDITION_SATISFIED
```

`POLICY_REOPEN_CONDITION_SATISFIED`では`reopen_condition_ref`をexact Target Predicate refとして、`reopen_condition_evaluation_ref`をそのcurrent Completion Evaluationとして必須にする。他のtriggerでは両fieldをnullにし、triggerとpayloadの不一致を拒否する。

```text
CLOSED HISTORY PRESERVED=true
CURRENT STATUS=REOPENED
```

# 9. Supersession and Invalidation

Supersessionは「古いIssueを閉じる」操作ではない。新旧Differenceのsemantic identityと双方向lineageを検証した場合だけ受理する。

InvalidationはDifferenceが解決したことを意味しない。不正なCanonical claimを除外する処理であり、必要ならvalid inputから新しいDifferenceを導出する。

# 10. Acceptance

```text
DIFFERENCE_STATUS_ENUM_CLOSED=true
LEGAL_TRANSITIONS_EXPLICIT=true
ILLEGAL_TRANSITIONS_FAIL_CLOSED=true
LIFECYCLE_APPEND_ONLY=true
EVENT_REVISION_CONTIGUOUS=true
BLOCKED_PRESERVED=true
RETAINED_NE_CLOSED=true
CLOSED_REOPENABLE=true
ATOMIC_REFLOW_OWNS_CLOSURE=true
```

```text
DIFFERENCE_LIFECYCLE_DEFINED=true
DIFFERENCE_LIFECYCLE_IMPLEMENTED=false
DIFFERENCE_LIFECYCLE_RUNTIME_PROVEN=false
```
