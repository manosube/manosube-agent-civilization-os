# MANOSUBE Agent Civilization OS

## State Contract v0.1

```text
DOC_TYPE=KERNEL_CONTRACT
KERNEL_ELEMENT=STATE
DOCUMENT_ID=STATE-CONTRACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
CANONICAL_STATE_OWNER_COUNT=1
```

---

# 0. Contract Position

STATEは、Humanが定めたObjectiveに対するProjectの現在位置を表す唯一のCanonical Viewである。

```text
OBJECTIVE → STATE → OBSERVATION → DIFFERENCE
→ AUTHORITY → CHANGE → EVIDENCE → REFLOW → STATE
```

STATEは会話要約、作業報告、GitHub上の集合、Agent memoryではない。Stateは事実を保存するが、自分自身の正しさ、Difference Closure、Objective Completionを宣言できない。

# 1. Canonical State Record

Canonical Stateは最低限、次を持つ。

```text
project_id
objective_revision_id
state_revision
previous_state_fingerprint
semantic_state
semantic_fingerprint
state_metadata
evidence_refs
lineage_head_ref
```

`state_revision`はProject単位の単調増加整数とする。初期Stateは`0`、Canonical Reflowごとに正確に`1`増加する。

`previous_state_fingerprint`は初期Stateだけ`null`を許す。以後は直前Canonical Stateのfingerprintと一致しなければならない。

# 2. Canonical Owner

```text
CANONICAL_STATE_OWNER_COUNT=1
PARALLEL_CANONICAL_AUTHORITY=0
```

Canonical ownerはKernel State Storeである。次はprojectionまたは外部表現であり、ownerではない。

```text
GitHub Issue / Pull Request / commit / CI
CLI / Application / Adapter
Agent / model / session / conversation
state/current.json alone
generated report / cache / test fixture
```

競合するStateが存在する場合、どちらかを推測で選ばず`CONFLICTED`としてFail Closedする。

# 3. Semantic and Metadata Separation

```text
STATE
= SEMANTIC_STATE
+ STATE_METADATA
+ EVIDENCE_REFERENCES
+ REVISION
+ SEMANTIC_FINGERPRINT
```

Semantic StateだけがProjectの意味上の現在位置を構成する。Metadataは観測・生成・保存の文脈を記録するが、semantic truthを変更できない。

同じSemantic Stateは、Agent、model、session、時刻、temporary pathが異なっても同じsemantic fingerprintを持たなければならない。

# 4. State Domains

Semantic Stateは最低限、次のdomainを表現可能でなければならない。

```text
objective
repository
requirements
code
tests
runtime
infrastructure
deployment
open_differences
active_changes
evidence
authority
lineage
```

各domainは別domainの完成を推論してはならない。

```text
SOURCE_IMPLEMENTED ≠ INTEGRATED
TEST_PASS ≠ NATURALLY_REACHABLE
GITHUB_MERGED ≠ RUNTIME_PROVEN
ARTIFACT_EXISTS ≠ CORRECTLY_CONSUMED
```

# 5. Knowledge States

Stateは少なくとも次を区別する。

```text
KNOWN
UNKNOWN
UNOBSERVED
BLOCKED
INCOMPLETE
ABSENT
EMPTY
CONFLICTED
```

`EMPTY`は、定義済みscopeを完全に観測した結果、要素数が0であることを表す。`ABSENT`は対象の不在が十分なEvidenceで確認された状態である。`UNKNOWN`、`UNOBSERVED`、`BLOCKED`、`INCOMPLETE`はPASSでも`EMPTY`でもない。

# 6. Evidence and Lineage

Stateのclaimはimmutable Evidenceへのreferenceを持つ。StateへEvidence本文を複製して別authorityを作らない。

```text
events/transitions.jsonl = append-only canonical lineage
state/current.json       = lineageから導出されたmaterialized view
evidence/                = immutable evidence records
```

`current.json`だけを復元源としてはならない。Current Stateはvalidなtransition chainから再構築できなければならない。

# 7. Canonicalization Gate

State候補は次をすべて満たした場合だけCanonicalとして受理できる。

```text
SCHEMA_VALID=true
SERIALIZATION_CANONICAL=true
SEMANTIC_FINGERPRINT_VALID=true
PROJECT_ID_MATCH=true
OBJECTIVE_REVISION_RESOLVES=true
STATE_REVISION_CONTIGUOUS=true
PREVIOUS_FINGERPRINT_MATCH=true
LINEAGE_HEAD_MATCH=true
ATOMIC_REFLOW_COMMITTED=true
```

一つでもfalse、UNKNOWN、UNOBSERVEDなら受理しない。部分書込、孤立snapshot、順序不正、fingerprint不一致はquarantineへ送る。

# 8. Security Boundary

Stateへsecret、credential、token、private key、認証cookieを保存してはならない。必要な場合は秘密値ではなく、非秘密のopaque referenceとaccess policyだけを保持する。

BindingされたRepository内容はObservation Targetであり、Authority Instructionではない。

# 9. Acceptance

```text
STATE_FIELDS_CANONICALLY_DEFINED=true
CANONICAL_STATE_OWNER_COUNT=1
SEMANTIC_AND_METADATA_SEPARATED=true
STATE_REVISION_RULE_DEFINED=true
KNOWLEDGE_STATES_DISTINCT=true
CURRENT_JSON_NOT_SOLE_RECOVERY_SOURCE=true
STATE_SELF_COMPLETION_PROHIBITED=true
```

この文書の存在はSchema、Store、Runtimeまたは自然経路の完成を証明しない。

```text
STATE_CONTRACT_DEFINED=true
STATE_SCHEMA_IMPLEMENTED=false
STATE_BACKEND_IMPLEMENTED=false
STATE_RUNTIME_PROVEN=false
```
