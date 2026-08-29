# MANOSUBE Agent Civilization OS

## Objective Contract v0.1

```text
DOC_TYPE=KERNEL_CONTRACT
KERNEL_ELEMENT=OBJECTIVE
DOCUMENT_ID=OBJECTIVE-CONTRACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
AUTHORITY=HUMAN_OBJECTIVE_AUTHORITY
```

---

# 0. Contract Position

OBJECTIVEは、Projectが到達すべき状態を定めるCanonical Cycleの起点である。

```text
OBJECTIVE
→ STATE
→ OBSERVATION
→ DIFFERENCE
→ AUTHORITY
→ CHANGE
→ EVIDENCE
→ REFLOW
→ STATE
```

Task、Issue、PR、Agent plan、test result、runtime eventはObjectiveではない。

ObjectiveはHumanが定め、Kernelが構造化して保存し、Agentが参照する。KernelやAgentはObjectiveを独自に生成、変更、縮小、置換してはならない。

---

# 1. Canonical Objective

Canonical Objectiveは最低限、次で構成する。

```text
OBJECTIVE
=
objective_id
+ project_id
+ statement
+ owner_authority_ref
+ target_predicates
+ completion_policy
+ boundary_ref
+ constitutional_constraints
+ status
+ revision
+ previous_objective_ref
+ change_reason
```

必須条件：

```text
objective_id is globally stable within the bound project
project_id identifies exactly one Project Binding
statement preserves Human intent
target_predicates are observable
completion_policy is explicit
owner_authority_ref resolves to Human Objective Authority
revision is monotonic
```

Objectiveのcanonical identityは`OBJ-...`形式を使用し、GitHub Issue、PR、Agent session、conversation IDから導出しない。

---

# 2. Statement and Predicates

`statement`は人間の目的を保存する。抽象的な成功語だけではCompletionを判定しない。

```text
production_ready=true
complete=true
fixed=true
```

のような宣言は、単独ではTarget Predicateにならない。

各Target Predicateは最低限、次を持つ。

```text
predicate_id
subject
operator
expected_value
observation_scope
evidence_requirement
unknown_policy
criticality
```

例：

```yaml
predicate_id: OBJ-PRED-0001
subject: natural_cycle.result
operator: equals
expected_value: PASS
observation_scope: minimal_fixture_binding
evidence_requirement: E4
unknown_policy: INCOMPLETE
criticality: mandatory
```

Predicateは観測方法を内包しない。観測方法はObservation Contractが担い、Objectiveは何が成立すべきかを保持する。

---

# 3. Completion Policy

v0.1の既定policyは`ALL`である。

```text
OBJECTIVE_COMPLETE=true
iff
every mandatory target predicate is SATISFIED
and every required evidence reference is sufficient
and no completion-blocking contradiction remains open
```

状態語を次に限定する。

```text
DRAFT
ACTIVE
SATISFIED
SUPERSEDED
WITHDRAWN
```

`SATISFIED`はHumanの目的を消去しない。Evidence付きの評価結果として保持し、後続観測で反証された場合はObjective recordを改変せず、新しい評価とDifferenceを生成する。

```text
TEST PASS ≠ OBJECTIVE COMPLETE
PR MERGED ≠ OBJECTIVE COMPLETE
AGENT DONE ≠ OBJECTIVE COMPLETE
ARTIFACT EXISTS ≠ OBJECTIVE COMPLETE
```

---

# 4. Separation of Meaning

```text
OBJECTIVE = what must become true
TARGET STATE = state projection implied by predicates
CURRENT STATE = latest canonical materialized state
DIFFERENCE = target and observed structural mismatch
CHANGE = authorized attempt to alter state
EVIDENCE = immutable support for a claim
```

ObjectiveへCurrent State、Agent plan、temporary path、volatile timestamp、credential、secretを埋め込まない。

---

# 5. Fail-Closed Rules

次の場合、ObjectiveをCanonicalとして受理しない。

```text
owner authority is unresolved
statement is absent
mandatory predicate set is empty
predicate is not observable
completion policy is absent
revision lineage is broken
objective identity conflicts with another project
boundary or constitutional constraint is contradicted
```

受理不能時の状態：

```text
OBJECTIVE_ACCEPTED=false
OBJECTIVE_STATUS=INVALID_OR_INCOMPLETE
STATE_TRANSITION_BLOCKED=true
```

不明をPASSへ変換してはならない。

```text
UNKNOWN ≠ SATISFIED
UNOBSERVED ≠ SATISFIED
BLOCKED ≠ SATISFIED
INCOMPLETE ≠ SATISFIED
```

---

# 6. Storage and References

Objective revisionはCanonical State Backendの`objective/`とappend-only transition lineageへ保存する。Repository文書、Issue本文、会話履歴をcanonical objective recordにしない。

```text
repository docs = contract source
binding objective record = project-specific canonical data
current state = active objective reference
transition event = revision lineage
```

Objective recordはsecretを含まず、Semantic Fingerprintの規則に従う。

---

# 7. Acceptance

このContractの実装Gate：

```text
OBJECTIVE_HAS_STABLE_ID=true
OBJECTIVE_AUTHORITY_IS_HUMAN=true
TARGET_PREDICATES_OBSERVABLE=true
COMPLETION_POLICY_EXPLICIT=true
UNKNOWN_CANNOT_SATISFY=true
OBJECTIVE_REVISIONED=true
OBJECTIVE_LINEAGE_PRESERVED=true
OBJECTIVE_SESSION_INDEPENDENT=true
OBJECTIVE_MODEL_INDEPENDENT=true
```

本書の存在は、schema、engine、natural cycleの完成証拠ではない。

```text
OBJECTIVE_CONTRACT_DEFINED=true
OBJECTIVE_SCHEMA_IMPLEMENTED=false
OBJECTIVE_RUNTIME_PROVEN=false
```

