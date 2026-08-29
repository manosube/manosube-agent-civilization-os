# MANOSUBE Agent Civilization OS

## Semantic State Contract v0.1

```text
DOC_TYPE=KERNEL_CONTRACT
KERNEL_ELEMENT=STATE
DOCUMENT_ID=SEMANTIC-STATE-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
```

---

# 0. Definition

Semantic Stateは、Projectの意味上の現在位置だけを表す、Canonical Stateの決定論的部分である。

```text
SEMANTIC_STATE
= PROJECT_IDENTITY
+ OBJECTIVE_POSITION
+ DOMAIN_STATES
+ OPEN_DIFFERENCE_IDENTITIES
+ ACTIVE_CHANGE_IDENTITIES
+ AUTHORITY_POSITION
+ EVIDENCE_CLAIM_REFERENCES
+ LINEAGE_POSITION
```

観測時刻や実行者など、意味を変えない情報はState Metadataへ分離する。

# 1. Root Shape

Semantic Stateのlogical rootは次で固定する。

```text
project
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

後続Schemaはこの意味を狭めず、machine-verifiableな表現へ写像する。

# 2. Project and Objective Position

`project`は安定した`project_id`とbinding identityを持つ。display name、local checkout path、session workspaceをidentityにしてはならない。

`objective`はHumanが承認したexact `objective_revision_id`を参照し、そのrevisionに対する評価位置を持つ。StateはObjective本文を書き換えず、Objective Authorityを取得しない。

# 3. Domain State Form

各domain stateは最低限、次のlogical fieldsを持つ。

```text
status
claims
identity_refs
evidence_refs
blind_spots
```

`status`はknowledge stateであり、Completion Levelの代用ではない。`claims`は正規化されたassertionであり、自由記述の成功報告をCanonical truthにしない。

# 4. Domain Separation

各domainは独立して評価する。

| Domain | 表すもの | 表さないもの |
|---|---|---|
| repository | source snapshotと構造 | runtime到達性 |
| requirements | 要求の同定・充足位置 | Human受入 |
| code | 実装状態 | 接続・実運用 |
| tests | 検証結果とscope | 自然経路実証 |
| runtime | 対象Runtimeの観測状態 | source完成 |
| infrastructure | 実行基盤の状態 | deployment成功 |
| deployment | 配置状態 | Objective Completion |

一つのdomain claimから別domain claimを暗黙に生成してはならない。

# 5. Difference, Change, Evidence and Authority

`open_differences`と`active_changes`はCanonical identityの重複なし集合である。Issue番号、PR番号、branch名をCanonical identityにしない。

`evidence`はclaimとimmutable Evidence identityの結合を表す。Evidence本文またはvolatile logをSemantic Stateへ埋め込まない。

`authority`は現在Stateに適用されるauthority envelopeとapproval identityを表す。Capabilityまたはcredentialの存在をAuthorityへ昇格させない。

# 6. Knowledge Semantics

```text
KNOWN       = value and scope supported by evidence
UNKNOWN     = truth value cannot be determined
UNOBSERVED  = required observation was not performed
BLOCKED     = observation or evaluation could not proceed
INCOMPLETE  = required scope was only partially evaluated
ABSENT      = bounded observation proves nonexistence
EMPTY       = complete valid collection contains zero members
CONFLICTED  = incompatible supported claims coexist
```

禁止する同一視：

```text
UNKNOWN = PASS
UNOBSERVED = ABSENT
NO_RESULT = PROVEN_ABSENCE
EMPTY = MISSING
BLOCKED = FAILED
```

# 7. Collection Semantics

Semanticな集合は入力順序、filesystem走査順、API返却順へ依存してはならない。各要素は安定identityを持ち、正規化sort keyによって一意に並べる。

重複identityは黙ってdeduplicateせず、同一内容ならduplicate error、異なる内容なら`CONFLICTED`として扱う。

# 8. Excluded Fields

次はSemantic Stateへ含めない。

```text
observed_at
recorded_at
observer
agent_name
model_name
session_id
process_id
hostname
temporary_path
serialization_order
volatile_log
credential
secret
```

ただし時刻自体がProject domainの意味である場合、例えばdeployment effective timeやEvidenceのbounded intervalは、正規化されたdomain claimとして含められる。単なる処理時刻とは区別する。

# 9. Unknown Field Policy

未知のfield、未知のenum、未知のschema versionを無視してはならない。

```text
UNKNOWN_FIELD → REJECT_OR_QUARANTINE
UNKNOWN_ENUM  → REJECT_OR_MIGRATE_EXPLICITLY
UNKNOWN_VERSION → VERSION_NEGOTIATION_REQUIRED
```

# 10. Acceptance

```text
SEMANTIC_ROOT_DEFINED=true
REQUIRED_DOMAINS_DEFINED=true
DOMAIN_COMPLETION_NOT_COLLAPSED=true
KNOWLEDGE_STATES_DISTINCT=true
SET_ORDER_NON_SEMANTIC=true
VOLATILE_FIELDS_EXCLUDED=true
SECRET_FIELDS_EXCLUDED=true
```

```text
SEMANTIC_STATE_CONTRACT_DEFINED=true
SEMANTIC_STATE_SCHEMA_IMPLEMENTED=false
SEMANTIC_STATE_RUNTIME_PROVEN=false
```
