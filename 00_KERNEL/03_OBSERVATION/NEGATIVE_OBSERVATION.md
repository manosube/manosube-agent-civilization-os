# MANOSUBE Agent Civilization OS

## Negative Observation Contract v0.1

```text
DOC_TYPE=KERNEL_CONTRACT
KERNEL_ELEMENT=OBSERVATION
DOCUMENT_ID=NEGATIVE-OBSERVATION-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
```

---

# 0. Definition

Negative Observationは、期待した結果を得られなかった事実、または明示scope内で対象の不在を確認した事実を、誇張せず保存する契約である。

```text
NO_RESULT ≠ PROVEN_ABSENCE
SEARCH_FAILURE ≠ PROVEN_ABSENCE
TIMEOUT ≠ PROVEN_ABSENCE
UNOBSERVED ≠ ABSENT
```

# 1. Logical Record

最低限、次を持つ。

```text
negative_observation_id
observation_id
project_id
target_identity
subject
predicate
effective_boundary
negative_status
scope_ref
method_ref
time_boundary
source_snapshot_refs
attempt_refs
completion_evaluation
blind_spot_refs
negative_evidence_refs
positive_fact_refs
conclusion
```

# 2. Negative Status

Negative statusは次のclosed enumとする。

```text
ABSENT
EMPTY
NO_RESULT
UNKNOWN
UNOBSERVED
BLOCKED
INCOMPLETE
FAILED
INVALID
CONFLICTED
```

意味：

| Status | 意味 |
|---|---|
| `ABSENT` | bounded scope内の不在が十分に確認された |
| `EMPTY` | complete collectionの要素数が0だった |
| `NO_RESULT` | methodが結果を返さなかったが理由は確定しない |
| `UNKNOWN` | 真偽を決定できない |
| `UNOBSERVED` | 必要な観測を実行していない |
| `BLOCKED` | 阻害要因により観測できない |
| `INCOMPLETE` | scopeまたはmethodが部分完了 |
| `FAILED` | methodを実行したが正常なObservation resultを生成できなかった |
| `INVALID` | 入力、boundary、methodまたはrecordが不正 |
| `CONFLICTED` | 不在と存在を支持する両立不能な事実がある |

# 3. Proven Absence Gate

`ABSENT`は次をすべて満たす場合だけ宣言できる。

```text
PROVEN_ABSENCE
iff
TARGET_DEFINED
and SCOPE_COMPLETE
and METHOD_COMPLETE
and TIME_BOUNDARY_COMPLETE
and SOURCE_SNAPSHOTS_IDENTIFIED
and REQUIRED_ATTEMPTS_COMPLETED
and NO_BLOCKING_BLIND_SPOT
and NO_CONFLICTING_POSITIVE_FACT
and NEGATIVE_EVIDENCE_REFERENCED
```

一つでもfalse、UNKNOWN、UNOBSERVEDなら`ABSENT`を禁止する。

# 4. No Result

`NO_RESULT`はmethod outputの記録であり、world stateの結論ではない。

合法な原因例：

```text
TARGET_ABSENT
SOURCE_EMPTY
QUERY_MISMATCH
PERMISSION_DENIED
TIMEOUT
SOURCE_UNAVAILABLE
PARSER_FAILURE
SCOPE_MISMATCH
UNKNOWN_CAUSE
```

原因が確定しない限り`UNKNOWN`を保持する。便利なdefaultとして`ABSENT`へ変換しない。

# 5. Empty Collection

`EMPTY`は、定義済みcollection scopeを完全に列挙し、validな要素数が0であった状態である。

```text
EMPTY_COLLECTION
requires
COLLECTION_DEFINED
+ ENUMERATION_COMPLETE
+ ZERO_VALID_MEMBERS
+ NO_BLOCKING_BLIND_SPOT
```

File missing、field missing、parser failure、permission failureをEMPTYにしない。

# 6. Attempts and Time

Negative claimは観測期間、試行回数、各method resultを保持する。

```text
attempt_count
first_attempt_at
last_attempt_at
attempt_results
termination_reason
```

単一時点の不在を永久不在へ拡張しない。対象の変化速度に対してfreshnessを評価する。

# 7. Blind Spots and Conflicts

不在結論へ影響するblind spotがある場合、statusは`INCOMPLETE`、`BLOCKED`または`UNKNOWN`である。

Positive FactとNegative Observationが同じ`subject`、`predicate`、`effective_boundary`で競合する場合、どちらかを消さず`CONFLICTED`としてDifference入力へ送る。これら三つをclaim coordinateとし、`target_identity`や`time_boundary`から暗黙推論しない。対応するPositive Factは`positive_fact_refs`で明示する。

# 8. Evidence Boundary

Negative Evidenceは少なくともscope、期間、method、attempt、completion、blind spotを検証可能にする。

```text
NEGATIVE CLAIM WITHOUT BOUNDED EVIDENCE
→ CANNOT CLOSE DIFFERENCE
```

Negative Observation自身はEvidence Sufficiencyを決定しない。

# 9. State Mapping

Observation statusからState knowledge statusへの写像は明示的に行う。

| Negative Observation | State候補 |
|---|---|
| `ABSENT` | `ABSENT` |
| `EMPTY` | `EMPTY` |
| `NO_RESULT` | `UNKNOWN` |
| `UNKNOWN` | `UNKNOWN` |
| `UNOBSERVED` | `UNOBSERVED` |
| `BLOCKED` | `BLOCKED` |
| `INCOMPLETE` | `INCOMPLETE` |
| `FAILED` | `UNKNOWN`（failure自体はEvidenceへ保持） |
| `INVALID` | State候補にせず`REJECT_OR_QUARANTINE` |
| `CONFLICTED` | `CONFLICTED` |

この写像はStateを直接更新しない。Canonical Stateへの反映はEvidence評価後のAtomic Reflowだけが行う。

`INVALID`は合法な検証結果ではあるが、合法なCanonical State claimではない。推測で別statusへ変換せず、原recordとreasonを保持してrejectまたはquarantineする。

# 10. Acceptance

```text
NEGATIVE_STATUS_ENUM_CLOSED=true
NEGATIVE_CLAIM_COORDINATES_REQUIRED=true
NO_RESULT_NE_PROVEN_ABSENCE=true
UNOBSERVED_NE_ABSENT=true
TIMEOUT_NE_ABSENT=true
EMPTY_NE_MISSING=true
PROVEN_ABSENCE_GATE_DEFINED=true
NEGATIVE_OBSERVATION_BOUNDED=true
ATTEMPTS_AND_TIME_RECORDED=true
BLIND_SPOT_BLOCKS_ABSENCE=true
NEGATIVE_OBSERVATION_NOT_EVIDENCE_SUFFICIENCY=true
NEGATIVE_OBSERVATION_NOT_STATE_TRANSITION=true
INVALID_NEGATIVE_OBSERVATION_QUARANTINED=true
```

```text
NEGATIVE_OBSERVATION_CONTRACT_DEFINED=true
NEGATIVE_OBSERVATION_SCHEMA_IMPLEMENTED=false
NEGATIVE_OBSERVATION_ENGINE_IMPLEMENTED=false
NEGATIVE_OBSERVATION_RUNTIME_PROVEN=false
```
