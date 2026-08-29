# MANOSUBE Agent Civilization OS

## Objective Revision Contract v0.1

```text
DOC_TYPE=KERNEL_REVISION_CONTRACT
KERNEL_ELEMENT=OBJECTIVE
DOCUMENT_ID=OBJECTIVE-REVISION-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
REVISION_AUTHORITY=HUMAN_OBJECTIVE_AUTHORITY
```

---

# 0. Revision Principle

Objectiveは変更できる。しかし、失敗した実装へ合わせて無言で書き換えてはならない。

```text
OBJECTIVE REVISION
≠ ORDINARY CHANGE
≠ STATE UPDATE
≠ DIFFERENCE CLOSURE
```

Revisionは旧Objectiveを破壊せず、新しいimmutable revisionを追加する。

---

# 1. Revision Record

各revisionは最低限、次を持つ。

```text
objective_revision_id
objective_id
revision
previous_objective_ref
base_semantic_fingerprint
statement
target_predicates
completion_policy
boundary_ref
constitutional_constraints
change_reason
semantic_change_summary
human_authority_ref
recorded_at
status
```

```text
objective_id remains stable
revision increases monotonically
objective_revision_id is immutable
previous_objective_ref points to the immediate predecessor
```

---

# 2. Revision Classes

```text
EDITORIAL
PREDICATE_ADD
PREDICATE_REMOVE
PREDICATE_MODIFY
COMPLETION_POLICY_CHANGE
BOUNDARY_CHANGE
CONSTRAINT_CHANGE
OBJECTIVE_REPLACEMENT
WITHDRAWAL
```

`EDITORIAL`はsemantic fingerprintを変えない表記修正だけに限定する。それ以外はSemantic Revisionである。

Predicateのrequired evidence level、operator、expected value、criticality、unknown policyの変更はすべてSemantic Revisionとして扱う。

---

# 3. Revision Procedure

```text
current objective restored
↓
revision proposal recorded
↓
semantic difference computed
↓
human authority verified
↓
base revision compared
↓
new revision validated
↓
revision event atomically appended
↓
current objective reference updated
↓
affected state and differences re-evaluated
```

Proposal、approval、commit、activationを一つの状態に圧縮しない。

```text
PROPOSED
AUTHORIZED
COMMITTED
REJECTED
STALE
```

---

# 4. Continuity and Non-Erasure

新revisionは旧revisionを削除、上書き、改竄しない。

保持するもの：

```text
before objective
proposed objective
semantic diff
human authority evidence
decision
resulting objective
affected predicates
affected open differences
```

旧Objective下で発生した失敗、BLOCKED、未到達、Evidence不足は、新Objectiveへ変わっても消去しない。

```text
OBJECTIVE_REVISED=true
HISTORICAL_FAILURE_REMOVED=false
```

---

# 5. Anti-Weakening Rule

次の目的でRevisionを使用してはならない。

```text
make a failing implementation appear complete
remove an inconvenient mandatory predicate
lower evidence requirements after failure
convert UNKNOWN or BLOCKED to acceptable
retroactively authorize an executed change
hide a constitutional contradiction
```

観測結果によりObjective自体の再考が必要になった場合は、Humanが理由と影響を明示してRevisionを承認する。観測事実は旧revisionのEvidenceとして保持する。

---

# 6. Re-evaluation

Semantic Revision後は、少なくとも次を再評価する。

```text
target state projection
open structural differences
active change authorization
existing approvals
completion claims
evidence sufficiency
next observation
```

旧Objectiveに結合されたapprovalは、新revisionへ自動継承しない。

```text
APPROVAL OBJECTIVE REVISION
= ACTIVE OBJECTIVE REVISION
→ approval may remain valid

otherwise
→ STALE APPROVAL
```

---

# 7. Recovery

Revision commit中に部分書込、fingerprint不一致、lineage断絶が発生した場合、新revisionをCanonicalとして採用しない。

```text
PARTIAL_REVISION_NOT_CANONICAL=true
PREVIOUS_OBJECTIVE_REMAINS_ACTIVE=true
FAILED_RECORD_QUARANTINED=true
```

Rollbackは履歴削除ではない。必要な場合は、旧semantic contentを持つ新revisionをHuman承認で追加する。

---

# 8. Acceptance

```text
OBJECTIVE_ID_STABLE_ACROSS_REVISIONS=true
OBJECTIVE_REVISION_MONOTONIC=true
OBJECTIVE_REVISION_APPEND_ONLY=true
SEMANTIC_DIFF_RECORDED=true
HUMAN_AUTHORITY_REQUIRED=true
STALE_REVISION_BLOCKED=true
HISTORICAL_FAILURE_PRESERVED=true
ACTIVE_DIFFERENCES_REEVALUATED=true
PARTIAL_REVISION_NOT_CANONICAL=true
```

本書はrevision engineの実装完了を宣言しない。

```text
OBJECTIVE_REVISION_CONTRACT_DEFINED=true
OBJECTIVE_REVISION_ENGINE_IMPLEMENTED=false
OBJECTIVE_CONTINUITY_PROVEN=false
```

