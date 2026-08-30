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
+ observation_scope
+ effective_boundary
+ normalized_target_state
+ normalized_structural_difference
+ closure_policy_semantic_fingerprint
+ identity_profile
```

`normalized_target_state`、`normalized_observed_state`および`normalized_structural_difference`は自由形式objectではなく、実在するv0.1 Objective／Observation Schemaから次のprofileで導出するclosed projectionである。

```text
PROFILE=MANOSUBE-DIFFERENCE-NORMALIZATION-0.1
TARGET_SOURCE=01_SCHEMA/objective/target_predicate.schema.json
OBSERVED_SOURCE=State-bound Normalized Facts and bounded Negative Observations
UNKNOWN_FIELDS=REJECT
NESTED_COLLECTIONS=EXPLICIT_KIND_WRAPPER_ONLY
SOURCE_FACT_COLLECTION_ARRAYS=PROJECT_BY_VALUE_TYPE
OTHER_BARE_ARRAY=REJECT
TEXT_NORMALIZATION=UNICODE_NFC
NUMBER_PROFILE=JSON_INTEGER_OR_CANONICAL_DECIMAL_STRING
```

Target Predicateの既存fieldを改名せず次へexactに射影する。

```yaml
normalized_target_state:
  subject: natural_cycle.result
  operator: equals
  expected_value: PASS
  expected_value_type: STRING
  observation_scope: minimal_fixture_binding
  evidence_requirement: E4
  unknown_policy: INCOMPLETE
  criticality: mandatory
```

`operator`はsource schemaと同じ`equals | not_equals | contains | exists | all | none`だけ、`unknown_policy`は`INCOMPLETE`だけ、`evidence_requirement`は`E0..E6`、`criticality`は`mandatory | advisory`だけを許可する。変換表や大文字別名を作らない。`expected_value`のcollectionはexplicit wrapper必須である。

Targetの`expected_value_type`は次のtotal ruleで導出して`normalized_target_state`へ必須fieldとして追加する。

```text
JSON null    → NULL
JSON boolean → BOOLEAN
JSON integer → INTEGER
JSON string  → STRING
ordinary JSON object → STRUCTURED
{"value_type":"DECIMAL","value":"<canonical decimal>"} → DECIMAL
{"value_type":"TIMESTAMP","value":"<canonical UTC timestamp>"} → TIMESTAMP
{"value_type":"DURATION","value":"<canonical duration>"} → DURATION
{"value_type":"IDENTITY_REFERENCE","value":{...}} → IDENTITY_REFERENCE
{"collection_kind":"ORDERED_LIST","members":[...]} → ORDERED_COLLECTION
{"collection_kind":"UNORDERED_SET","members":[...]} → UNORDERED_COLLECTION
bare JSON array → REJECT
```

Reserved typed wrapperは上記exact fieldsだけを許可する。plain string `"1"`は常にSTRINGでありDECIMALへ推測変換しない。TargetにDECIMAL等を要求する場合はtyped wrapper必須である。 Normalization後はwrapperの`value_type`を`expected_value_type`へ、inner `value`を`expected_value`へ射影し、wrapper object自体を比較値にしない。primitiveとcollection wrapperも同様にtypeとcanonical inner valueへ分離する。比較はまずTarget／Observed typeをexact照合し、type一致後にinner canonical value bytesだけを比較する。

Objectiveの`observation_scope`文字列は推論せず、Difference導出入力に次のexact bindingを必須とする。

```yaml
objective_scope_binding:
  objective_scope_name: minimal_fixture_binding
  scope_ref: {kind: observation_scope, id: OBS-SCOPE-...}
  scope_schema_version: "0.1"
  resolved_scope_record_sha256: sha256:<64 lowercase hex>
```

`objective_scope_name`はTarget Predicateの`observation_scope`とexact一致し、scope ref／version／record digestはClosure Policy G9と同じresolved Scope projectionで検証する。binding欠落または不一致ならDifferenceを導出しない。

Observed sourceは、(1) same project／State binding、(2) FactまたはNegative Observationの`subject`がTarget `subject`とexact一致、(3) Observation `scope_ref`がobjective scope bindingとexact一致、の全条件で選択し、Factの`predicate`をTarget operatorの代用にしない。次のclosed projectionへ射影する。

```yaml
normalized_observed_state:
  subject: natural_cycle.result
  objective_scope_binding: {}
  effective_boundary:
    kind: OBSERVATION_SCOPE_BOUNDARY
    scope_ref: {kind: observation_scope, id: OBS-SCOPE-...}
    resolved_scope_record_sha256: sha256:...
    target_effective_window: {start: null, end: null}
    source_snapshot_refs: {collection_kind: UNORDERED_SET, members: []}
  knowledge_status: KNOWN
  value_candidates:
    collection_kind: UNORDERED_SET
    members:
      - value: PASS
        value_type: STRING
        unit: null
        fact_predicate: natural_cycle.result@v1
        effective_boundary: {}
```

`knowledge_status`は`KNOWN | ABSENT | EMPTY | UNKNOWN | UNOBSERVED | BLOCKED | INCOMPLETE | CONFLICTED`のclosed enumである。Negative Observationはcanonical State Mappingをexact適用し、`NO_RESULT→UNKNOWN`、`FAILED→UNKNOWN`（failure Evidenceは保持）、`INVALID→REJECT_OR_QUARANTINE`、その他は同名statusへ写像する。`INVALID`からnormalized observed stateまたはDifferenceを生成しない。`value_candidates`はduplicate-free unordered setで、各memberをNormalized Factの既存fieldから射影する。Fact `value_type=ORDERED_COLLECTION`のschema-valid bare arrayは`ORDERED_LIST` wrapperへ順序を保持して変換し、`UNORDERED_COLLECTION`は各memberを再帰canonicalizeして整列・duplicate reject後に`UNORDERED_SET` wrapperへ変換する。この二つだけがsource wire arrayからidentity wrapperへの許可されたprojectionである。STRUCTURED value内の未宣言bare array、value_type不一致、unknown nested collectionはrejectする。Negative Observationはvalueを捏造しない。

最後にTarget operatorをObserved projectionへ適用し、次の全field必須projectionを生成する。

```yaml
normalized_structural_difference:
  mismatch_kind: VALUE_MISMATCH
  observed_knowledge_status: KNOWN
  target_value: PASS
  observed_values: {collection_kind: UNORDERED_SET, members: []}
  target_value_type: STRING
  observed_value_types: {collection_kind: UNORDERED_SET, members: []}
  target_cardinality: null
  observed_cardinality: null
  comparison_result: NOT_EQUAL
  comparison_profile: MANOSUBE-DIFFERENCE-COMPARISON-0.1
```

`mismatch_kind`は`MISSING | UNEXPECTED | VALUE_MISMATCH | TYPE_MISMATCH | CARDINALITY_MISMATCH | RELATION_MISMATCH | BOUNDARY_MISMATCH | CONFLICT | UNKNOWN`、`comparison_result`は`EQUAL | NOT_EQUAL | SATISFIED | NOT_SATISFIED | UNKNOWN`のclosed enumである。非該当fieldも省略せず`null`またはempty explicit setへ固定する。

導出順は、exact Target解決 → objective scope binding検証 → closed effective boundary生成 → State-bound observed input選択 → canonical Negative status mapping → conflict／knowledge評価 → source operatorのtotal evaluation → type → cardinality → relation → value → closed mismatch projection、の一つだけである。

`effective_boundary`はpositive Factのboundaryを直接流用せず、resolved Scope、Target effective window、Observation source snapshot setから生成する上記closed projectionである。positive／negativeの双方で必須とし、scope／window／snapshot集合のいずれかが異なれば別boundaryである。source snapshotsはcanonical member bytes順のduplicate-free unordered setとする。

Operator評価を次へ固定する。

```text
equals
→ distinct canonical candidate value exactly 1
→ that value == expected_value

not_equals
→ distinct canonical candidate value exactly 1
→ that value != expected_value

contains
→ distinct candidate exactly 1 and candidate is collection
→ expected_value canonical bytes is a member

exists
→ bounded scope complete and candidate count >= 1

all
→ bounded scope complete and candidate count >= 1
→ every distinct candidate value == expected_value

none
→ bounded scope complete
→ no distinct candidate value == expected_value
```

`equals`、`not_equals`、`contains`でdistinct candidateが0件ならNOT_SATISFIED、2件以上なら`CONFLICT + CONFLICTED`とする。`all`のempty setはNOT_SATISFIEDでありvacuous truthを禁止する。`none`だけはempty setでSATISFIEDになり得るが、Scope completeとbounded Negative Evidenceが必須である。UNKNOWN、UNOBSERVED、BLOCKED、INCOMPLETE、CONFLICTEDまたは不完全Scopeでは全operatorをSATISFIEDにしない。

Mismatch kindは次の上から最初に一致するruleだけで決定する。

```text
1 INVALID source
  → REJECT_OR_QUARANTINE; Differenceを生成しない

2 scope／window／snapshot boundary不一致
  → BOUNDARY_MISMATCH

3 CONFLICTED knowledge、またはsingle-value operatorでdistinct candidates > 1
  → CONFLICT

4 UNKNOWN／UNOBSERVED／BLOCKED／INCOMPLETE knowledge
  → UNKNOWN

5 Target typeとObserved type不一致
  → TYPE_MISMATCH

6 candidates = 0 and operator in equals|not_equals|contains|exists|all
  → MISSING

7 contains applied to non-collection candidate
  → TYPE_MISMATCH

8 contains comparison NOT_SATISFIED
  → RELATION_MISMATCH

9 none comparison NOT_SATISFIED
  → UNEXPECTED

10 equals|not_equals|all comparison NOT_SATISFIED
  → VALUE_MISMATCH

11 comparison SATISFIED
  → Differenceを生成しない
```

`CARDINALITY_MISMATCH`はv0.1 Target Predicate operator集合にcardinality operatorが存在しないため、このprofileから生成してはならない。将来のTarget schema versionが明示的cardinality operatorを追加した場合だけprofile version更新で有効化する。未到達condition、複数ruleの恣意選択、下位ruleによる上位rule上書きを禁止する。

Conformance vectorsは全6 source operator、全mismatch kind、unknown／conflicted入力、scope binding mismatch、type／cardinality precedence、ordered／unordered collection、bare array、duplicate set、unknown fieldおよび固定digestを含む。

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
