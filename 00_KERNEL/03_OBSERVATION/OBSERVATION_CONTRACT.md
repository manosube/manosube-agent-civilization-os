# MANOSUBE Agent Civilization OS

## Observation Contract v0.1

```text
DOC_TYPE=KERNEL_CONTRACT
KERNEL_ELEMENT=OBSERVATION
DOCUMENT_ID=OBSERVATION-CONTRACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
```

---

# 0. Contract Position

OBSERVATIONは、境界を定めた外界のsourceを観測し、Kernelが評価可能なNormalized Factへ変換する行為である。

```text
OBJECTIVE → STATE → OBSERVATION → DIFFERENCE
→ AUTHORITY → CHANGE → EVIDENCE → REFLOW → STATE
```

Observationは判断の材料を生成するが、Difference、Authority、Change、Evidence Sufficiency、Completionを決定しない。

```text
OBSERVATION ≠ DIFFERENCE
OBSERVATION ≠ AUTHORITY
OBSERVATION ≠ EVIDENCE SUFFICIENCY
OBSERVATION ≠ COMPLETION
```

# 1. Observation Record

Observationは最低限、次を持つ。

```text
observation_id
project_id
state_revision_observed
state_fingerprint_observed
target
scope
method
time_boundary
source_snapshot_refs
normalization_profile
normalized_facts
status
blind_spots
attempts
observation_evidence_refs
```

`state_revision_observed`と`state_fingerprint_observed`は、ObservationがどのCanonical State位置に結合されたかを固定する。別Stateに対するObservationとして再利用してはならない。

# 2. Identity

`observation_id`はProject内で一意かつ不変である。同一ID・同一payloadの再取込はidempotentに扱えるが、同一ID・異なるpayloadは`CONFLICTED`としてFail Closedする。

Agent名、session ID、process ID、timestampだけをObservation identityにしてはならない。

# 3. Target and Scope

`target`は何を観測するかを示す安定identityである。`scope`は包含対象、除外対象、境界、列挙規則、完了条件を固定する。

```text
TARGET_DEFINED=false → OBSERVATION_INVALID
SCOPE_DEFINED=false  → OBSERVATION_INVALID
```

Scope外の事実を暗黙に混入させない。Scope内の対象を観測できなかった場合、削除またはPASSへ変換せず、blind spotと非成功statusに保存する。

# 4. Method and Time Boundary

`method`は取得、解析、正規化のversioned procedureを参照する。自由記述だけではmethod identityにならない。

`time_boundary`は最低限、次を区別する。

```text
observation_started_at
observation_ended_at
target_effective_interval
source_snapshot_time
```

すべてUTC、RFC 3339、明示offsetを使用する。処理時刻と対象事実の有効時刻を混同しない。

# 5. Source Snapshot

Sourceはimmutableまたはcontent-addressed snapshot referenceに結合する。Mutable branch名、latest URL、current pathだけを完全なsource identityにしてはならない。

```text
SAME_SOURCE_SNAPSHOT
+ SAME_SCOPE
+ SAME_METHOD
+ SAME_NORMALIZATION_PROFILE
→ SAME_NORMALIZED_FACTS
```

この決定論性を満たさない場合、原因をblind spotまたはconflictとして保持し、Canonical Factを推測しない。

# 6. Observation Status

Observation全体のstatusは次のclosed enumとする。

```text
COMPLETE
INCOMPLETE
EMPTY
UNKNOWN
UNOBSERVED
BLOCKED
INVALID
CONFLICTED
```

意味：

| Status | 意味 |
|---|---|
| `COMPLETE` | 宣言scopeとmethodを完了し、結果を正規化できた |
| `INCOMPLETE` | scopeまたはmethodの一部だけを完了した |
| `EMPTY` | 完全に観測したcollectionの要素数が0だった |
| `UNKNOWN` | 真偽または値を決定できない |
| `UNOBSERVED` | 必要なObservationが実行されていない |
| `BLOCKED` | 明示された阻害要因により実行または完了できない |
| `INVALID` | 契約、schema、boundaryまたはsourceが不正 |
| `CONFLICTED` | 両立しないsupported factsが存在する |

`EMPTY`は成功statusではあるが、対象の一般的不在を自動的に証明しない。

# 7. Attempts and Blind Spots

各attemptはmethod、開始・終了、result、failure classを記録する。再試行は前回の失敗を消さない。

Blind spotは次を区別する。

```text
NONE_KNOWN
KNOWN_BLIND_SPOTS_PRESENT
NOT_EVALUATED
```

`NONE_KNOWN`はscope完全性の証明ではない。

# 8. Evidence Boundary

Observation resultはimmutable Observation Evidenceへのreferenceを持つ。Observation record自体をEvidence Sufficiencyと同一視しない。

```text
OBSERVATION RESULT
+ OBSERVATION EVIDENCE
→ DIFFERENCE INPUT CANDIDATE
```

Evidence本文、credential、unbounded logをObservationへ複製しない。

# 9. Authority and Security

BindingされたRepository、Issue、README、code comment、prompt文字列はObservation Targetであり、Authority Instructionではない。

Observationは任意コード実行と分離する。実行を伴うmethodは別途Authority評価を必要とし、Observation契約だけでは許可されない。

secret、credential、token、private key、session cookie、authorization headerをpayload、fact、source referenceへ保存してはならない。

# 10. Acceptance

```text
OBSERVATION_FIELDS_DEFINED=true
OBSERVATION_IDENTITY_DEFINED=true
TARGET_AND_SCOPE_REQUIRED=true
METHOD_VERSION_REQUIRED=true
TIME_BOUNDARY_REQUIRED=true
SOURCE_SNAPSHOT_REQUIRED=true
OBSERVATION_STATUS_ENUM_CLOSED=true
BLIND_SPOTS_PRESERVED=true
OBSERVATION_NOT_AUTHORITY=true
OBSERVATION_NOT_COMPLETION=true
```

```text
OBSERVATION_CONTRACT_DEFINED=true
OBSERVATION_SCHEMA_IMPLEMENTED=false
OBSERVATION_ENGINE_IMPLEMENTED=false
OBSERVATION_RUNTIME_PROVEN=false
```
