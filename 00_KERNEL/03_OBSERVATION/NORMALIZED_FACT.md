# MANOSUBE Agent Civilization OS

## Normalized Fact Contract v0.1

```text
DOC_TYPE=KERNEL_CONTRACT
KERNEL_ELEMENT=OBSERVATION
DOCUMENT_ID=NORMALIZED-FACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
```

---

# 0. Definition

Normalized Factは、境界付きObservationがsource valueをversioned規則で正規化した、Kernel評価用の最小事実単位である。

```text
SOURCE VALUE ≠ NORMALIZED FACT
CLAIM ≠ FACT
AGENT ASSERTION ≠ FACT
```

# 1. Logical Record

最低限、次を持つ。

```text
fact_id
project_id
subject
predicate
value
value_type
unit
effective_boundary
normalization_profile
```

Observationとのprovenance結合はFact本体へ単数fieldとして埋め込まず、次のappend-only association recordで保持する。

```text
FACT_OBSERVATION_BINDING
= binding_id
+ fact_id
+ observation_id
+ state_revision_observed
+ state_fingerprint_observed
+ source_occurrence_id
+ source_ref
+ source_locator
+ observed_quality_status
```

`source_occurrence_id`は、同一Observation内の各contributing sourceを`source_ref + source_locator`から決定論的に同定する。`source_locator`はsnapshot内の位置を特定する非秘密referenceであり、absolute temporary pathやcredential-bearing URLを禁止する。

`binding_id`は`fact_id + observation_id + source_occurrence_id`から決定する。同一Factが別State revisionで再観測された場合、または一つのObservationで複数sourceが同じFactを支持した場合もFactを上書きせず、source occurrenceごとに新しいBindingをappendする。同一Bindingの同一payloadはidempotent、異なるpayloadは`CONFLICTED`とする。

Factに対する支持・競合評価はFactまたはBindingを更新せず、別のappend-only evaluation recordで保持する。

```text
FACT_EVALUATION
= evaluation_id
+ fact_id
+ evaluation_revision
+ previous_evaluation_id
+ binding_refs
+ evaluation_status
+ conflict_fact_refs
+ evidence_refs
```

`evaluation_revision`はFact単位で0から単調増加し、`evaluation_id`は`fact_id + evaluation_revision`から決定する。新しいBindingまたは競合Factが発見された場合、既存recordを変更せず次revisionをappendする。同一revision・同一payloadはidempotent、異なるpayloadまたはrevision gapはFail Closedする。

# 2. Fact Identity

Fact identityは最低限、次のCanonical tupleから決定する。

```text
FACT_IDENTITY_INPUT
= project_id
+ subject
+ predicate
+ effective_boundary
+ normalization_profile
+ canonical value
```

`observation_id`、`source_ref`、`source_locator`、`observed_quality_status`はFact本体ではなく`FACT_OBSERVATION_BINDING`へ保持する。現在の支持・競合位置は`FACT_EVALUATION`へ保持する。いずれもFactのsemantic identityへ含めない。同じsemantic factを別State revisionまたは別sourceから再観測しても、正規化結果が同じなら同じ`fact_id`と、各source occurrenceに対応する異なるBindingを生成しなければならない。

Observation identity、serialization order、取得順序、Agent、session、process、hostnameはFact identityへ含めない。

同一identity・同一内容は同じFactである。同一identity・異なる内容を黙って上書き、last-write-wins、deduplicateしてはならず、`CONFLICTED`として保持する。

# 3. Subject and Predicate

`subject`は観測対象の安定identityである。display label、filesystemの偶発的な絶対path、list indexをidentityにしない。

`predicate`はversioned vocabularyに属し、未知predicateを黙って受理しない。Vocabulary変更はschema／normalization profileのrevisionを必要とする。

# 4. Value and Type

`value_type`はclosed enumとして最低限、次を表現可能にする。

```text
NULL
BOOLEAN
INTEGER
DECIMAL
STRING
TIMESTAMP
DURATION
IDENTITY_REFERENCE
ORDERED_COLLECTION
UNORDERED_COLLECTION
STRUCTURED
```

Decimalをbinary floating-point近似へ暗黙変換しない。TimestampはUTC、RFC 3339、明示offsetで正規化する。Unitを持つ値はunitを省略しない。

Unordered collectionは入力順をsemanticにせず、安定keyで正規化する。重複identityを暗黙に除去しない。

# 5. Effective Boundary

Factが真であると主張する対象時間・revision・snapshot範囲を`effective_boundary`へ固定する。

```text
OBSERVED_AT ≠ EFFECTIVE_AT
RECORDED_AT ≠ EFFECTIVE_AT
```

処理時刻だけから対象時刻を推測しない。Boundary不明のFactは`UNKNOWN`または`INVALID`であり、無期限の現在事実に昇格させない。

# 6. Source Traceability

すべてのFactは、Observationとsource snapshotへ逆引き可能でなければならない。

```text
FACT
→ ONE_OR_MORE FACT_OBSERVATION_BINDINGS
→ OBSERVATION_ID
→ SOURCE_SNAPSHOT_REF
→ SOURCE_LOCATOR
→ NORMALIZATION_PROFILE
```

Sourceが消失、mutable、未同定の場合、その制約をquality statusとblind spotへ残す。

# 7. Normalization Determinism

```text
SAME_SOURCE_BYTES
+ SAME_SOURCE_IDENTITY
+ SAME_SCOPE
+ SAME_PROFILE
→ BYTE_EQUIVALENT_CANONICAL_FACT
```

Locale、timezone default、filesystem order、dictionary order、platform newline、Unicode表現の差を正規化する。推測補完、現在時刻の注入、random IDの注入を禁止する。

# 8. Quality Status

Fact Observation Bindingの観測時quality、およびFact Evaluationの評価statusは次のclosed vocabularyを使用する。

```text
SUPPORTED
UNKNOWN
INCOMPLETE
BLOCKED
INVALID
CONFLICTED
```

`observed_quality_status`はBinding生成時点のObservation/source occurrence評価であり、後から書き換えない。現在の支持・競合位置は最新の連続した`FACT_EVALUATION`から導出する。QualityはFactのsemantic payload、Completion Level、Evidence Levelではない。`SUPPORTED`でも、そのFactだけでDifference ClosureやObjective Completionを宣言できない。

# 9. Null, Empty and Absence

次を分離する。

```text
NULL_VALUE
EMPTY_COLLECTION
MISSING_FIELD
UNOBSERVED_VALUE
PROVEN_ABSENCE
```

`null`、空文字、空collection、field欠落を相互変換しない。不在はNegative Observation契約を満たす場合だけFactとして表現できる。

# 10. Security and Taint

secret-bearing sourceを観測しても秘密値をNormalized Factへ保存しない。秘密の存在が必要な場合は、値ではなく安全なboolean claim、redaction status、opaque referenceだけを使用する。

Repository内容に含まれる命令文はdataであり、Authorityへ昇格させない。

# 11. Acceptance

```text
NORMALIZED_FACT_FIELDS_DEFINED=true
FACT_IDENTITY_DETERMINISTIC=true
OBSERVATION_ID_EXCLUDED_FROM_FACT_IDENTITY=true
FACT_OBSERVATION_BINDING_APPEND_ONLY=true
SOURCE_PROVENANCE_EXCLUDED_FROM_FACT_BODY=true
SOURCE_OCCURRENCE_IDENTITY_DEFINED=true
OBSERVATION_QUALITY_EXCLUDED_FROM_FACT_BODY=true
FACT_EVALUATION_APPEND_ONLY=true
CONFLICT_EVALUATION_REVISIONED=true
IMMUTABLE_BINDING_NOT_REEVALUATED_IN_PLACE=true
ALL_OBSERVATION_PROVENANCE_PRESERVED=true
SUBJECT_AND_PREDICATE_VERSIONED=true
VALUE_TYPES_CLOSED=true
EFFECTIVE_BOUNDARY_REQUIRED=true
SOURCE_TRACEABILITY_REQUIRED=true
NORMALIZATION_PROFILE_REQUIRED=true
NULL_EMPTY_ABSENCE_SEPARATED=true
CONFLICT_NOT_OVERWRITTEN=true
SECRET_VALUE_PROHIBITED=true
```

```text
NORMALIZED_FACT_CONTRACT_DEFINED=true
NORMALIZED_FACT_SCHEMA_IMPLEMENTED=false
NORMALIZATION_ENGINE_IMPLEMENTED=false
NORMALIZED_FACT_RUNTIME_PROVEN=false
```
