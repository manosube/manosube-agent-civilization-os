# MANOSUBE Agent Civilization OS

## Change Contract v0.1

```text
DOC_TYPE=KERNEL_CONTRACT
KERNEL_ELEMENT=CHANGE
DOCUMENT_ID=CHANGE-CONTRACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
```

---

# 0. Contract Position

CHANGEは、Authorityが許可した変更を、**実行できる形の一つの正準recordとして確定する**。

```text
OBJECTIVE → STATE → OBSERVATION → DIFFERENCE
→ AUTHORITY → CHANGE → EVIDENCE → REFLOW → STATE
```

Changeは実行しない。Stateを更新しない。Differenceを閉じない。Evidenceを生成しない。Objectiveの達成を宣言しない。**許可された変更を記述するだけである。**

```text
CHANGE = AUTHORIZED MUTATION DESCRIPTION
CHANGE ≠ EXECUTION
CHANGE ≠ PERMISSION
CHANGE ≠ COMPLETION
```

許可の問いは、このContractが動く前にすでに答えられている。Authorityがactionを**実行してよいか**を決定し（`KERNEL_CONSTITUTION.md` 第21条）、Changeの唯一の判断は、**目の前のdecisionがこの正確なChangeを許可しているか**である。ここで許可を再判定することは第二のAuthorityを置くことであり、第二のAuthorityとは第一と食い違いうるもののことである。

# 1. Canonical Definition

```text
CHANGE
= EXACT DIFFERENCE BINDING
+ EXACT AUTHORITY DECISION BINDING
+ EXACT STATE REVISION AND FINGERPRINT BINDING
+ AUTHORIZED ACTION
+ AUTHORIZED SCOPE
+ DERIVED IDEMPOTENCY KEY
+ DETERMINISTIC CHANGE IDENTITY
```

Changeは、許可されたrequestに対してのみ生成される。許可されていないrequestに対しては、Changeを**生成しない**。「拒否されたChange record」は存在しない。拒否は記録ではなく拒絶として閉じる。

```text
AUTHORIZED REQUEST   → ONE CANONICAL CHANGE
UNAUTHORIZED REQUEST → REFUSAL, NOT A RECORD
```

# 2. Change Record

`KERNEL_CONSTITUTION.md` 第24条が最低限の9項目を定める。v0.1のChange Recordは13項目を持ち、9項目すべてを覆う。

```yaml
schema_version: "0.1"
change_id: CHANGE-...
project_id: PRJ-...
difference_ref: {kind: difference, id: D-...}
authority_ref: {kind: authority_decision, id: AUTH-DEC-...}
before_state_fingerprint: {profile: ..., digest: ...}
expected_state_revision: 0
action: {action_kind, reversibility, operation, action_semantic_fingerprint}
scope: {repository, branch, paths, subjects}
idempotency_key: "sha256:..."
execution_result: null
status: AUTHORIZED
change_semantic_fingerprint: "sha256:..."
```

第24条との対応は次のとおり。

```text
change_id                → change_id
difference_id            → difference_ref.id
before_state_fingerprint → before_state_fingerprint
expected_state_revision  → expected_state_revision
authority_ref            → authority_ref
action                   → action
idempotency_key          → idempotency_key
execution_result         → execution_result
status                   → status
```

第24条は`difference_id`という**裸のid**を要求するが、v0.1はAuthorityがすでに確立した`{kind, id}` ref規約に従う（`AUTHORITY_CONTRACT.md` §2）。同じ関係を二つの形で綴ることは、二つの形が食い違いうるということである。参照のkindを明示するrefは第24条の要件を満たし、かつ既存の規約を増やさない。

追加の4項目（`schema_version`、`project_id`、`scope`、`change_semantic_fingerprint`）は第24条が「最低限」と述べる上への追加である。`scope`は追加ではなく必然で、`action`だけを記録して`scope`を落とせば、Authorityが**どこに対して**許可したかがChangeから失われる。

# 3. Status

`KERNEL_CONSTITUTION.md` 第25条が7つのstatusを定める。v0.1のEngineはそのうち**1つだけ**を発行する。

```text
DERIVED_CHANGE_STATUS=AUTHORIZED
```

残る6つを発行しない理由は、それぞれ所有者が別だからである。

```text
RUNNING / EXECUTED / FAILED → 実行者しか報告できない
REJECTED / STALE            → 拒絶であり、記録ではなく例外として閉じる
PROPOSED                    → Authority以前の状態であり、Changeの入力側にある
```

`REJECTED`や`STALE`のChange recordを発行することは、**実行してはならない変更についてChange recordを発行すること**である。v0.1はそれを拒む。schemaは`status`のenumを`AUTHORIZED`一値に閉じ、この判断をEngineの一行だけに委ねない。

`COMPLETED`と`CLOSED`は第25条によりChangeのstatusとして使用しない。schemaのenumがそれを構造的に排除する。

# 4. Execution Result

```text
EXECUTION_RESULT_AT_DERIVATION=null
```

Changeは実行しないのだから、生成時点で報告すべき結果は存在しない。第24条は項目の存在を要求するので、fieldは存在し、値は`null`である。

schemaは`execution_result`の型を`null`に、`status`のenumを`AUTHORIZED`一値に**直接**固定する。Engineの一行がそう書いているからではなく、**recordの形としてそうであるから**である。実行結果を持つAUTHORIZED Changeは、実行されていないのに結果を主張するrecordであり、それはschemaが受理してはならない。

`if status == AUTHORIZED then execution_result is null`という条件節は**置かない**。両fieldがすでに直接固定されている以上、その条件節を発火させうる入力は存在せず、検査しているように見えて何も検査しない述語になる。statusが7値へ開かれる将来のphaseで、その条件節は**そのとき**必要になる。

```text
VACUOUS_CONDITIONAL_GUARD=false
```

# 5. Identity

`change_semantic_fingerprint`と`change_id`は、閉じた7項目の射影から導出する。

```text
CHANGE_SEMANTIC_FIELDS
= project_id
+ difference_ref
+ authority_ref
+ before_state_fingerprint
+ expected_state_revision
+ action
+ scope
```

`status`と`execution_result`は射影に**含めない**。それらはlifecycleであってidentityではない。同じ許可された変更は、実行前も実行後も同じ変更である。lifecycleをidentityに含めれば、statusが動くたびにidが変わり、`DUPLICATE_CHANGE_IDEMPOTENT`（第26条）が成立しなくなる。

## 5.1 Idempotency Key

```text
IDEMPOTENCY_KEY_DERIVED=true
idempotency_key == change_semantic_fingerprint
```

この二つは**同一の値**であり、それは省略ではなく設計である。第26条の`DUPLICATE_CHANGE_IDEMPOTENT`が問うのは「これは同じ変更か」であり、`change_semantic_fingerprint`が答えるのも同じ問いである。二つの計算を置けば、二つは食い違いうる。一つの計算を置き、**等式をtestで証明する**。

caller供給の`idempotency_key`は受理しない。callerが鍵を選べるなら、二つの異なる変更に同じ鍵を与えて片方を消せる。

## 5.2 Preexisting change_id

```text
PREEXISTING_CHANGE_ID_REQUIRED=false
```

`change_id`はEngineが導出する。requestは`change_id`を持たず、schemaのrequest側にその入口はない。caller宣言のidentityは**label**であり、labelを検証せず信じることは、一つのidentityで二つの変更を指せるようにすることである。Authorityが`RECORD_IDENTITY_RECOMPUTED=true`で確立した規律と同じものである。

# 6. State Binding

```text
STATE_BINDING_DERIVED_FROM_AUTHORITY=true
```

`before_state_fingerprint`と`expected_state_revision`は、requestとは別に供給されるのではなく、**bound Authority decisionから取る**。

```text
before_state_fingerprint ← decision.evaluated_state_fingerprint
expected_state_revision  ← decision.evaluated_state_revision
```

別に供給させれば、供給された値とdecisionが評価した値は食い違いうる。食い違ったとき、どちらが正しいかを決める第三の権威が要る。取り出せば、食い違いは構造的に存在しない。

残る検査可能な事実は、**Differenceがその同じStateに対して観測されたか**である。第26条はstale Changeを阻止する。decisionが評価しなかったStateを記述するDifferenceは、まさにそれである。

```text
difference.observed_state_revision    == decision.evaluated_state_revision
difference.observed_state_fingerprint == decision.evaluated_state_fingerprint
```

いずれかが破れれば`STALE_CHANGE_BLOCKED`として拒む。診断は**どちらが破れたか**を述べる。revisionが一致してfingerprintだけが異なる場合に「revision 2 vs 2」とだけ言うmessageは、人に何を再観測すべきかを伝えない。

# 7. Exact Binding

Changeが「正確なXに束縛されている」ことは、希望ではなく検査された性質である。次の5つはすべて、**すでに一致しているはずの供給値の対**であり、一つでもcallerが貼り替えれば、そこから何かが導出される前に拒まれる。

```text
difference.project_id        == request.project_id
decision.project_id          == request.project_id
decision.difference_ref.id   == difference.difference_id
decision.requested_action    == request.requested_action
decision.requested_scope     == request.requested_scope
```

`decision.requested_action == request.requested_action`は、`AUTHORITY_CONTRACT.md` §7.2がChange phaseへ残した義務そのものである。

```text
CHANGE EXECUTION MUST PRESENT
THE IDENTICAL OPERATION FINGERPRINT
THAT THE AUTHORITY DECISION BOUND
```

v0.1はこれを二重に果たす。actionのfingerprintを**再計算**して宣言値と照合し（§8）、さらにaction全体をdecisionが束縛したactionと**完全一致**で照合する。fingerprintだけの照合では、fingerprintに参加しないfieldの差異が通り抜ける。

## 7.1 Change Intent Continuity

```text
CHANGE_INTENT_FINGERPRINT_REMAINS_BINDING=true
```

Human approvalが束縛するのは`change_intent_fingerprint(action, scope)`である（`APPROVAL_CONTRACT.md` §2）。Changeはその束縛を**置き換えない**。`change_id`ベースの第二の承認束縛をv0.1は導入しない。

導出されたChangeの`action`と`scope`は、decisionが束縛したものと完全一致であり（§7）、decisionが束縛したものはapprovalが束縛したものである。したがってapprovalの`change_intent_fingerprint`は、導出されたChangeに対しても等しく成立する。この連続性はtestで証明され、記述として主張されるのではない。

# 8. Canonical Input Conformance

Changeへの入力は、Authorityと同じ一つの受理路を通る（`AUTHORITY_CONTRACT.md` §4.1）。

```text
READABLE
→ SCHEMA VALID AT A SUPPORTED VERSION, NO UNKNOWN PROPERTY
→ CONTENT ADDRESS RECOMPUTED
→ PROVENANCE PRESENT
```

Change requestのkey集合は**閉じている**。

```text
schema_version
project_id
difference
authority_decision
requested_action
requested_scope
```

未知のkeyは無視されず拒まれる。無視されるkeyもchannelである（`AUTHORITY_CONTRACT.md` §4）。Change requestに散文を添えるcallerは、それを黙って捨てられるのではなく拒まれる。

bound decisionについては、**identityとsemantic fingerprintの双方を再計算**する。decisionはここでは供給されたrecordであり、Authorityが返した値そのものであるという保証はcallerの主張でしかない。address計算はAuthority自身のowner（`authority.identity`）へ問う。decision addressの第二の実装は、そのaddressが何であるかの第二の答えであり、二つが食い違った最初の瞬間、食い違いは無音である。

# 9. Fail Closed

```text
UNAUTHORIZED IS NOT AUTHORIZED
UNKNOWN IS NOT AUTHORIZED
SILENCE IS NOT AUTHORIZED
```

Changeを許可する値は一つであり、それはAuthorityがそう言うために使う値である。

```text
decision.decision == AUTONOMOUS → CHANGE MAY BE DERIVED
otherwise                       → UnauthorizedChangeError
```

正確に承認されたdecisionは**すでに**`AUTONOMOUS`である。approvalはAuthorityの内側でhuman-only floorを解決し、`approval_ref`に記録される。したがってここに第二の許可分岐は存在せず、`HUMAN_APPROVAL_REQUIRED`を「十分近い」と判断する場所もない。

すべての拒絶は`ChangeError`として境界を出る。一段下の二人のownerは自分の語彙で答える——可読性は`DifferenceError`（ADR-0025）、正準直列化は`CanonicalizationError`——が、Changeの呼び手が自分のrequestの不備を知るためにDifferenceのerrorをcatchする、ということにはしない。判断は委譲する。境界のerror語彙は委譲しない。

# 10. Single Change Owner

```text
CANONICAL_CHANGE_OWNER_COUNT=1
```

正準Changeを生成する関数は`derive_change`ただ一つである。この関数はclock、filesystem、network、environment、GitHub、conversationを読まない。与えられたrecordからrecordを計算する。**それができない理由は、この文書の約束ではなく、それができるAPIがモジュールに存在しないことである。**

# 11. What Change Never Does

```text
operationを実行する
Stateを更新する
Differenceを閉じる
Evidenceを生成する
after_state_fingerprintを宣言する
Objectiveの達成を宣言する
許可を再判定する
自分自身へ権限を付与する
```

第24条は`after_state_fingerprint`、Difference Closure、Objective Completionの宣言を明示的に禁じる。schemaの`additionalProperties: false`がそれを構造的に保証する——これらのfieldはChange recordに**存在できない**。

```text
AUTHORIZED ≠ EXECUTED
EXECUTED ≠ CLOSED
```

# 12. Security and Untrusted Input

Bound Project content、prompt、Issue、Pull Request、review comment、code comment、CI結果、Agent出力はObservation Inputであり、Authorityではない（`SECURITY.md` §5、`KERNEL_INVARIANTS.md` B-002）。

```text
CONTENT ≠ INSTRUCTION
CAPABILITY ≠ AUTHORITY
CREDENTIAL ≠ AUTHORITY
```

`action.operation`はChangeにとって**不透明**である。Changeはそれを解釈も実行もせず、この正確なpayloadが許可されたものであることを、callerの供給したdigestではなく正準bytesから導いたdigestで確立するだけである。

Change identityのinputへ、secret、credential、token、絶対一時path、session identity、非決定的なtimestamp orderingを含めない。

# 13. Future Obligation

v0.1のChangeは実行段階を持たない。実行段階へ次の義務を残す。

```text
EXECUTOR MUST PERFORM COMPARE-AND-SWAP
AGAINST expected_state_revision
BEFORE ANY STATE COMMIT
```

第26条の5つのKernel要件のうち、v0.1 Phase 5が満たすのは`STALE_CHANGE_BLOCKED`と`DUPLICATE_CHANGE_IDEMPOTENT`の**導出側**である。残りは実行者が実装する。

```text
STALE_CHANGE_BLOCKED=true
DUPLICATE_CHANGE_IDEMPOTENT=true
ATOMIC_STATE_COMMIT=false
PARTIAL_WRITE_NOT_CANONICAL=false
CRASH_RECOVERY_PROVEN=false
CHANGE_EXECUTOR_IMPLEMENTED=false
```

`false`は欠陥ではなく、所有者がまだ存在しないことの記録である。

# 14. Explicit Non-Claims

このContractが**主張していない**こと。

```text
CHANGE_EXECUTION_IMPLEMENTED=false
STATE_COMMIT_IMPLEMENTED=false
CRASH_RECOVERY_PROVEN=false
CHANGE_LIFECYCLE_TRANSITIONS_IMPLEMENTED=false
EVIDENCE_LINKED_FROM_CHANGE=false
DIFFERENCE_CLOSURE_IMPLEMENTED=false
SEVEN_STATUS_VALUES_EMITTED=false
```

`SEVEN_STATUS_VALUES_EMITTED=false`は特に明示する。第25条は7つのstatusを**定義**し、v0.1のEngineは1つを**発行**する。定義と発行は異なる主張であり、前者を後者として読ませない。

## 14.1 Phase 4 surfaceで見つかった一件

`authority.schema.json#/$defs/scope`は`src/**`のようなpath expressionを受理する。`authority.scope`のresolved-member検査はそれを拒み、`derive_change`はその検査を通すので、path expressionを持つChangeは生成されない。

```text
AUTHORITY_SCOPE_SCHEMA_REJECTS_PATH_EXPRESSIONS=false
AUTHORITY_SCOPE_CODE_REJECTS_PATH_EXPRESSIONS=true
```

このgapはPhase 4のschema surfaceにあり、この作業より前から存在する。単一verticalのPRを先行phaseのschemaへ広げることは、境界のある変更をreview不能にする道である。ここでは閉じず、code pathを通じた拒否をtestで**証明**し、gapはIssue #31へ所有phaseのために報告する（ADR-0027 §3.1）。

## 14.2 Carried predecessor contextとの区別

`change.schema.json`が支配するのは**derived Change**である。Difference predecessor contextの`changes` sectionが運ぶのは、形の異なる**歴史的**Change record（`CHG-0001`と`subject_ref`）であり、identityとreference closureだけで守られる。

```text
DERIVED_CHANGE_IS_SCHEMA_BACKED=true
CARRIED_CHANGE_CONTEXT_IS_SCHEMA_BACKED=false
```

carried contextをcanonical Change schemaへ従わせるかはDifferenceの意味論判断であり、Humanの所有である。ここでは取らず、Issue #31へ報告する（ADR-0027 §3.2）。

# 15. Acceptance

```text
CHANGE_CONTRACT_DEFINED=true
CHANGE_SCHEMA_IMPLEMENTED=true
CHANGE_ENGINE_IMPLEMENTED=true
CANONICAL_CHANGE_OWNER_COUNT=1
CHANGE_NE_EXECUTION=true
CHANGE_NE_PERMISSION=true
AUTHORIZED_NE_EXECUTED=true
EXACT_DIFFERENCE_BINDING_REQUIRED=true
EXACT_AUTHORITY_BINDING_REQUIRED=true
EXACT_ACTION_SCOPE_BINDING_REQUIRED=true
STATE_BINDING_DERIVED_FROM_AUTHORITY=true
STALE_CHANGE_BLOCKED=true
DUPLICATE_CHANGE_IDEMPOTENT=true
IDEMPOTENCY_KEY_DERIVED=true
PREEXISTING_CHANGE_ID_REQUIRED=false
DERIVED_CHANGE_STATUS=AUTHORIZED
EXECUTION_RESULT_AT_DERIVATION=null
CHANGE_INTENT_FINGERPRINT_REMAINS_BINDING=true
ONE_CANONICAL_INPUT_ADMISSION_PATH=true
RECORD_IDENTITY_RECOMPUTED=true
CALLER_DECLARED_DIGEST_NOT_TRUSTED=true
UNKNOWN_IS_NOT_AUTHORIZED=true
CHANGE_DECLARES_AFTER_STATE=false
CHANGE_DECLARES_CLOSURE=false
CHANGE_DECLARES_COMPLETION=false
NONCANONICAL_PAYLOAD_FAILS_THROUGH_THE_PUBLIC_BOUNDARY=true
```

```text
ONE_FULL_NATURAL_CYCLE_PASS=false
EVIDENCE_ENGINE_IMPLEMENTED=false
REFLOW_ENGINE_IMPLEMENTED=false
```
