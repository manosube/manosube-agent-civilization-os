# MANOSUBE Agent Civilization OS

## State Metadata Contract v0.1

```text
DOC_TYPE=KERNEL_CONTRACT
KERNEL_ELEMENT=STATE
DOCUMENT_ID=STATE-METADATA-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
```

---

# 0. Definition

State Metadataは、Semantic Stateをいつ、どの境界・方法・sourceから生成し、どのblind spotを持つかを記録する非Semanticなprovenance層である。

```text
METADATA MAY DESCRIBE SEMANTIC STATE
METADATA MUST NOT REDEFINE SEMANTIC STATE
```

# 1. Logical Fields

最低限、次を表現可能にする。

```text
metadata_schema_version
serialization_version
created_at
observed_at
recorded_at
producer
observer
execution_context
source_snapshot_refs
observation_scope_refs
confidence
blind_spots
warnings
```

必須性は後続Schemaで固定するが、存在しない値を推測で補ってはならない。

# 2. Time Semantics

各timestampの意味を混同しない。

| Field | 意味 |
|---|---|
| `created_at` | State candidate生成完了時刻 |
| `observed_at` | 対象事実を観測した時刻またはbounded interval |
| `recorded_at` | canonical storeが記録した時刻 |

UTC、RFC 3339、明示offsetを使用し、naive local timeを禁止する。同じSemantic Stateの別時刻観測はfingerprintを変えない。

# 3. Producer and Observer

`producer`と`observer`は監査用identityである。Agent、model、tool、processを記録できるが、これらはAuthorityでもSemantic identityでもない。

```text
AGENT_IDENTITY ≠ STATE_IDENTITY
OBSERVER_IDENTITY ≠ CLAIM_TRUTH
PRODUCER_CAPABILITY ≠ AUTHORITY
```

# 4. Execution Context

Execution contextはsession、run、host、process、workspace等の一時情報を持てる。ただしsecret、credential、完全なenvironment dumpを保存してはならない。

Local absolute pathは原則として保存せず、必要ならboundary-relative pathまたはredacted referenceとする。

# 5. Source and Scope References

`source_snapshot_refs`は観測対象snapshotのimmutableまたはcontent-addressed referenceを持つ。Mutable URLやbranch名だけを完全なsnapshot identityとして扱わない。

`observation_scope_refs`は何を見たかだけでなく、何を見ていないかを追跡可能にする。scope不明のnegative claimを許可しない。

# 6. Confidence and Blind Spots

ConfidenceはEvidence強度を上書きしない補助情報である。数値またはlabelを使用する場合、そのscaleと算出規則をversion化する。

Blind spotは空欄で省略せず、次を区別する。

```text
NONE_KNOWN
KNOWN_BLIND_SPOTS_PRESENT
NOT_EVALUATED
```

`NONE_KNOWN`は完全性の証明ではない。

# 7. Fingerprint Exclusion

State Metadata全体はsemantic fingerprintの入力から除外する。

最低限、次の値が変化してもSemantic Stateが同じならfingerprintは変化しない。

```text
observed_at
recorded_at
producer
observer
agent_name
model_name
session_id
run_id
hostname
process_id
temporary_path
warning_order
```

# 8. Security and Redaction

Metadataへ次を保存してはならない。

```text
password
API token
private key
session cookie
authorization header
secret environment value
credential-bearing URL
```

Redaction後の値を使用する場合は、秘密を復元できない形式とし、`redaction_applied=true`を記録する。

# 9. Mutation Rule

Canonical State記録後にmetadataをin-place修正してはならない。訂正が必要な場合は、訂正recordまたは新しいState revisionをappendし、元recordを保持する。

Metadataだけの訂正はSemantic Stateを変更しないが、record identityとlineage上の訂正関係を保持する。

# 10. Acceptance

```text
METADATA_FIELDS_DEFINED=true
TIME_SEMANTICS_DISTINCT=true
PRODUCER_NOT_AUTHORITY=true
SCOPE_AND_BLIND_SPOTS_RECORDED=true
METADATA_EXCLUDED_FROM_SEMANTIC_FINGERPRINT=true
SECRET_METADATA_PROHIBITED=true
IN_PLACE_MUTATION_PROHIBITED=true
```

```text
STATE_METADATA_CONTRACT_DEFINED=true
STATE_METADATA_SCHEMA_IMPLEMENTED=false
STATE_METADATA_RUNTIME_PROVEN=false
```
