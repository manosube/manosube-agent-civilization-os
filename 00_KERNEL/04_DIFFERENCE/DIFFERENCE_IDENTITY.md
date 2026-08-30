# MANOSUBE Agent Civilization OS

## Difference Identity Contract v0.1

```text
DOC_TYPE=KERNEL_CONTRACT
KERNEL_ELEMENT=DIFFERENCE
DOCUMENT_ID=DIFFERENCE-IDENTITY-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
```

---

# 0. Purpose

本Contractは、同じStructural DifferenceがAgent、session、Observation回数、GitHub表現の変化によって別仕事へ分裂することを防ぐ。

```text
SAME SEMANTIC DIFFERENCE → SAME DIFFERENCE ID
MATERIALLY DIFFERENT DIFFERENCE → DIFFERENT ID OR EXPLICIT SUPERSESSION
```

# 1. Identity Profile

v0.1のidentity profileを次で固定する。

```text
PROFILE=MANOSUBE-DIFFERENCE-SHA256-0.1
DIGEST=SHA-256
TEXT_NORMALIZATION=UNICODE_NFC
SERIALIZATION=CANONICAL_JSON_UTF8
KEY_ORDER=LEXICOGRAPHIC
UNKNOWN_FIELDS=REJECT
COLLECTION_REPRESENTATION=EXPLICIT_KIND_WRAPPER
BARE_ARRAY=REJECT
```

`difference_id`の形式は次とする。

```text
D-<UPPERCASE_SHA256_HEX>
```

# 2. Semantic Identity Input

Identity inputは次のsemantic tupleだけで構成する。

```text
DIFFERENCE_IDENTITY_INPUT
= project_id
+ objective_semantic_fingerprint
+ target_predicate_ref
+ subject
+ predicate
+ effective_boundary
+ normalized_target_state
+ normalized_structural_difference
+ closure_policy_semantic_fingerprint
+ identity_profile
```

`normalized_target_state`と`normalized_structural_difference`は自由形式objectではなく、次のprofileで導出するclosed projectionである。

```text
PROFILE=MANOSUBE-DIFFERENCE-NORMALIZATION-0.1
TARGET_SOURCE=resolved Target Predicate
OBSERVED_SOURCE=State-bound Normalized Facts and bounded Negative Observations
UNKNOWN_FIELDS=REJECT
NESTED_COLLECTIONS=EXPLICIT_KIND_WRAPPER_ONLY
BARE_ARRAY=REJECT
TEXT_NORMALIZATION=UNICODE_NFC
NUMBER_PROFILE=JSON_INTEGER_OR_CANONICAL_DECIMAL_STRING
```

Target Predicateから次をexactに射影する。

```yaml
normalized_target_state:
  subject: <canonical subject>
  predicate: <canonical predicate>
  operator: EQUALS
  expected_value: <recursive canonical value>
  expected_value_type: STRING
  effective_boundary: <recursive canonical value or null>
  unknown_policy: FAIL_CLOSED
```

`operator`は`EQUALS | NOT_EQUALS | PRESENT | ABSENT | EMPTY | CONTAINS | EXCLUDES | CARDINALITY_EQUALS | RELATION_HOLDS`、`expected_value_type`は`NULL | BOOLEAN | INTEGER | DECIMAL_STRING | STRING | OBJECT | COLLECTION | REFERENCE`のclosed enumである。Operatorが値を取らない場合も`expected_value=null`をexactに保持する。Target Predicateに必要fieldが欠落、operator不明、型不一致または未定義collection semanticsがあればDifferenceを導出しない。

Observed sourceを同じsubject／predicate／effective boundaryへ絞り、競合解決後に次をexactに射影する。

```yaml
normalized_structural_difference:
  mismatch_kind: VALUE_MISMATCH
  observed_knowledge_status: KNOWN
  target_value: <normalized_target_state.expected_value>
  target_value_type: STRING
  observed_value: <recursive canonical value or null>
  observed_value_type: STRING
  target_cardinality: null
  observed_cardinality: null
  expected_relation: null
  observed_relation: null
  boundary_match: true
  comparison_profile: MANOSUBE-DIFFERENCE-COMPARISON-0.1
```

`mismatch_kind`は`MISSING | UNEXPECTED | VALUE_MISMATCH | TYPE_MISMATCH | CARDINALITY_MISMATCH | RELATION_MISMATCH | BOUNDARY_MISMATCH | CONFLICT | UNKNOWN`、`observed_knowledge_status`は`KNOWN | ABSENT | EMPTY | UNKNOWN | UNOBSERVED | BLOCKED | FAILED | INVALID | CONFLICTED`のclosed enumである。全fieldを必須とし、非該当fieldは省略せず`null`へ固定する。

導出順は、(1) exact Target Predicate解決、(2) subject／predicate／boundary一致するObservation入力選択、(3) positive／negative conflict評価、(4)型比較、(5)cardinality比較、(6)relation比較、(7)value比較、(8)上記closed projection生成、の一つだけである。先に成立したfailure／mismatch categoryを採用し、後段へ進まない。複数Factが一意値へ収束しない場合は`CONFLICT + CONFLICTED`、観測不能は対応するknowledge statusと`UNKNOWN`を生成し、推測値を入れない。

Conformance vectorsは少なくとも、同一Target／Observed入力のkey順序不変性、unordered set順序不変性、ordered list順序変更、各operator、全mismatch kind、unknown／conflicted入力、type／cardinality precedence、bare array、duplicate set member、unknown fieldを含む。異なる実装が同じsource recordsから同じ二projection bytesとDifference IDを生成する固定digest vectorを公開する。

`objective_revision_ref`はexact provenance bindingとしてDifference Recordへ保持するが、identity inputには含めない。Objectiveの`EDITORIAL` revisionはsemantic fingerprintが不変であるため、同じTargetとMismatchのDifference IDを維持する。

Target value、Objective semantics、Mismatchの意味またはClosure Policy payloadが変わればidentityは変わる。Observed valueはMismatchへ正規化された範囲だけidentityへ反映する。

Closure Policyのlogical IDやversion文字列ではなく、closure requirementsだけから算出した`policy_semantic_fingerprint`をidentity inputへ含める。fingerprint inputから`subject_difference_ref`、`closure_policy_id`、`policy_version`、schema metadataを除外するため、Difference IDとの循環依存は生じない。

同じMismatchでもPolicy semanticsがmaterialに変われば新しいDifference IDを導出し、旧DifferenceとのSupersession Relationをappendする。versionだけが変わりPolicy semanticsが同一ならDifference IDは維持し、Difference-bound旧versionによる評価をcurrent semantic fingerprintとの一致確認後も許可する。version-only更新を理由に旧bindingをstale化せず、self-supersessionも生成しない。

# 3. Excluded Inputs

次をidentity inputへ含めてはならない。

```text
observed_at
observer
Agent name
model name
session ID
process ID
temporary path
serialization order
Observation ID
Evidence ID
State revision
State fingerprint
Issue number
branch name
commit SHA
Pull Request number
Change ID
approval ID
volatile log
credential
secret
```

これらはprovenanceまたはmetadataとして保存できるが、semantic identityを変えてはならない。

# 4. Canonicalization

Identity生成前に、tuple全体をCanonical Stateと同じ原則で正規化する。

```text
1. schemaで未知fieldを拒否
2. UnicodeをNFCへ正規化
3. numberをcanonical numberへ正規化
4. unordered collectionをcanonical member bytesで整列
5. duplicate semantic memberを拒否
6. object keyを辞書順へ整列
7. UTF-8 canonical JSON bytesへserialize
8. SHA-256 digestを生成
9. D- prefixを付与
```

`normalized_target_state`と`normalized_structural_difference`内のcollectionは、入れ子を含め次のclosed wrapperのいずれかで表現する。bare JSON arrayはidentity inputとして拒否する。

```json
{"collection_kind":"ORDERED_LIST","members":[]}
{"collection_kind":"UNORDERED_SET","members":[]}
```

`ORDERED_LIST`はmember順をsemanticとして保持する。`UNORDERED_SET`は各memberを再帰的にcanonicalizeしたbytesで整列し、duplicate canonical memberを拒否する。未知kind、kind欠落、同一wrapper内の追加fieldを拒否する。

Conformance vectorsは、ordered member交換でIDが変わること、unordered member交換でIDが不変であること、nested collectionでも同じ規則が再帰適用されること、bare arrayとduplicate set memberがrejectされることを含む。

NaN、Infinity、曖昧なlocal time、credential-bearing locator、schema外valueはFail Closedする。

# 5. Stability Across Re-observation

同一Objective semantic fingerprint、Target Predicate、boundary、normalized mismatchを再観測した場合、ObjectiveのEDITORIAL revision、Observation ID、State revision、Evidenceが変わっても同じ`difference_id`を生成する。

```text
REOBSERVATION
→ SAME DIFFERENCE ID
→ APPEND OBSERVATION BINDING
→ APPEND OBSERVATION_BOUND EVENT
```

新しいObservationを得るたびにDifference Recordを複製してはならない。

# 6. New Identity and Supersession

次のいずれかがmaterially変わった場合、新しいDifference identityを生成する。

```text
project
Objective semantic fingerprint
Target Predicate
subject or predicate
effective boundary
Target State semantics
Mismatch kind or semantic content
Closure Policy semantic fingerprint
identity profile
```

旧Differenceとの意味上の連続性がある場合、append-onlyなSupersession Relationで双方向関係を記録する。

```yaml
schema_version: "0.1"
supersession_relation_id: D-SUP-...
old_difference_ref: {kind: difference, id: D-OLD...}
new_difference_ref: {kind: difference, id: D-NEW...}
old_terminal_event_ref: {kind: difference_event, id: D-EVT-...}
new_genesis_event_ref: {kind: difference_event, id: D-EVT-...}
reason_codes: [TARGET_CHANGED, MISMATCH_SEMANTICS_CHANGED]
evidence_refs: []
```

`reason_codes`はnon-empty unordered setであり、canonical member bytes順に保存する。closed enumを次へ固定する。

```text
PROJECT_CHANGED
OBJECTIVE_SEMANTICS_CHANGED
TARGET_PREDICATE_CHANGED
SUBJECT_OR_PREDICATE_CHANGED
BOUNDARY_CHANGED
TARGET_STATE_SEMANTICS_CHANGED
MISMATCH_SEMANTICS_CHANGED
CLOSURE_POLICY_SEMANTICS_CHANGED
IDENTITY_PROFILE_CHANGED
```

materialに変わった全identity inputに対応するcodeを過不足なく含める。singular `reason_code`、複合曖昧code、unknown code、空集合、duplicateを拒否する。

Relationは両Differenceと双方のLifecycle Eventから解決可能でなければならない。Canonical Difference Recordを上書きせず、materialized viewの`superseded_by`と`supersedes`をRelationから導出する。

片方向、循環、自己参照、存在しないDifferenceへのsupersessionは拒否する。同一Relation ID・同一payloadはidempotent、異なるpayloadはcollisionとして拒否する。

# 7. Idempotency and Collision

```text
SAME DIFFERENCE ID + SAME IMMUTABLE SEMANTIC IDENTITY PAYLOAD
→ IDEMPOTENT ACCEPT

SAME DIFFERENCE ID + DIFFERENT IMMUTABLE SEMANTIC IDENTITY PAYLOAD
→ IDENTITY COLLISION
→ REJECT OR QUARANTINE
```

Collision比較の対象は第2節のimmutable semantic identity inputだけである。Observation bindings、State revision、Evidence references、status、Lifecycle Event、Supersession Relationなどのappend-only provenanceは比較対象から除外する。

したがって、同じidentityに新しいre-observation provenanceをappendすることはcollisionではない。ただし、同じprovenance event IDに異なるpayloadを与えた場合はprovenance collisionとして拒否する。

Identity Collision時に後着payloadで上書きしない。新しいIDを任意生成して衝突を隠さない。

# 8. Identity versus Instance State

Difference identityとDifference lifecycle stateを分離する。

```text
IDENTITY
= 何が構造的に異なるか

LIFECYCLE
= 現在どの評価段階にあるか
```

status、priority、assignee、attempt count、last observed time、Evidence levelはidentityへ含めない。

# 9. Acceptance Vectors

最低限、次のconformance vectorを要求する。

```text
KEY_ORDER_CHANGED → SAME ID
UNICODE_EQUIVALENT → SAME ID
OBSERVATION_CHANGED_SEMANTICS_SAME → SAME ID
STATE_REVISION_CHANGED_SEMANTICS_SAME → SAME ID
ISSUE_NUMBER_CHANGED → SAME ID
TARGET_CHANGED → DIFFERENT ID
OBJECTIVE_EDITORIAL_REVISION_CHANGED → SAME ID
OBJECTIVE_SEMANTIC_FINGERPRINT_CHANGED → DIFFERENT ID
BOUNDARY_CHANGED → DIFFERENT ID
MISMATCH_CHANGED → DIFFERENT ID
SAME_ID_DIFFERENT_SEMANTIC_IDENTITY_PAYLOAD → REJECT
SAME_ID_NEW_REOBSERVATION_PROVENANCE → APPEND
```

# 10. Acceptance

```text
DIFFERENCE_IDENTITY_PROFILE_DEFINED=true
SEMANTIC_INPUT_CLOSED=true
VOLATILE_INPUTS_EXCLUDED=true
REOBSERVATION_ID_STABLE=true
SUPERSESSION_BIDIRECTIONAL=true
DUPLICATE_IDEMPOTENT=true
COLLISION_FAIL_CLOSED=true
```

```text
DIFFERENCE_IDENTITY_DEFINED=true
DIFFERENCE_IDENTITY_IMPLEMENTED=false
DIFFERENCE_IDENTITY_RUNTIME_PROVEN=false
```
