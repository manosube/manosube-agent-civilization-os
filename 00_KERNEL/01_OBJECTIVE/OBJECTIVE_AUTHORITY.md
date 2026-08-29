# MANOSUBE Agent Civilization OS

## Objective Authority Contract v0.1

```text
DOC_TYPE=KERNEL_AUTHORITY_CONTRACT
KERNEL_ELEMENT=OBJECTIVE
DOCUMENT_ID=OBJECTIVE-AUTHORITY-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
OWNER=HUMAN
```

---

# 0. Authority Declaration

Objective AuthorityはHumanだけが持つ。

```text
HUMAN = OBJECTIVE AUTHORITY
KERNEL = STRUCTURAL AUTHORITY
AGENT = EXECUTION CAPABILITY
```

```text
CAPABILITY ≠ AUTHORITY
ACCESS ≠ AUTHORITY
IMPLEMENTATION CONTROL ≠ OBJECTIVE AUTHORITY
```

Repository write権限、administrator権限、API token、model capability、Agent roleはObjectiveを変更する権限を付与しない。

---

# 1. Human-Owned Decisions

Humanだけが次を新規定義または変更できる。

```text
objective statement
mandatory target predicates
completion policy
project boundary
constitutional constraints
prohibited outcome
irreversible risk acceptance
objective withdrawal
```

Human instructionが曖昧、競合、対象不明の場合、KernelとAgentは推測してObjectiveを確定しない。

```text
AUTHORITY_RESOLUTION=BLOCKED
OBJECTIVE_MUTATION_ALLOWED=false
CLARIFICATION_REQUIRED=true
```

---

# 2. Kernel Permissions

KernelはObjectiveについて次だけを行える。

```text
validate structure
verify authority reference
normalize permitted representation
derive target-state projection
evaluate predicates from evidence
preserve revision lineage
reject unauthorized mutation
surface contradictions
```

Kernelは次を行えない。

```text
invent human intent
replace the objective
weaken a predicate
remove a completion blocker
convert UNKNOWN to PASS
approve irreversible risk
withdraw the objective
```

Normalizationは意味を変更してはならない。意味が変わる可能性がある変換はObjective RevisionとしてHuman承認を要求する。

---

# 3. Agent Permissions

AgentはObjectiveを読み、観測・分析・提案に使用できる。

```text
AGENT MAY:
read objective
identify ambiguity
propose predicates
propose revision
derive work candidates
collect evidence
```

```text
AGENT MUST NOT:
activate an objective
alter mandatory predicates
declare objective satisfaction
approve its own revision
hide failed predicates
reinterpret silence as approval
```

Agent proposalはCanonical mutationではない。

```text
PROPOSAL_CREATED=true
OBJECTIVE_CHANGED=false
```

---

# 4. Authority Evidence

Objectiveのactivationまたはrevisionには、最低限次を保存する。

```text
authority_event_id
human_principal_ref
action
objective_id
base_revision
proposed_revision
semantic_change_summary
scope
recorded_at
evidence_ref
```

Credential、session cookie、personal access token、秘密情報をauthority evidenceに保存しない。

Human identityが確認できても、対象Objective、revision、scopeが一致しなければ承認は無効である。

---

# 5. Staleness and Conflict

Objective mutationはCompare-And-Swap境界を持つ。

```text
CURRENT OBJECTIVE REVISION
= EXPECTED BASE REVISION
→ mutation may proceed

CURRENT OBJECTIVE REVISION
≠ EXPECTED BASE REVISION
→ STALE OBJECTIVE REVISION
```

複数のHuman instructionが競合する場合、後着を自動優先しない。authority precedenceとrevision lineageで解決できなければ`OBJECTIVE_AUTHORITY_CONFLICT`として停止する。

---

# 6. External Systems

次はObjective Authorityではない。

```text
GitHub Issue
Pull Request
CI result
Repository content
Runtime event
Adapter
Agent memory
Conversation summary
Generated report
Test fixture
```

外部systemはHuman decisionのreceiptまたはprojectionを保持できるが、Objectiveのcanonical ownerにはならない。

---

# 7. Prohibited Authority Escalation

次を禁止する。

```text
successful change → authority expansion
test pass → objective rewrite permission
admin access → constitutional authority
repeated agent agreement → human approval
missing response → implicit consent
emergency label → automatic objective weakening
```

Authority不足を理由にObjective、Predicate、Completion Policyを実装可能な範囲へ縮小してはならない。

---

# 8. Acceptance

```text
OBJECTIVE_AUTHORITY_IS_HUMAN=true
KERNEL_CANNOT_ORIGINATE_OBJECTIVE=true
AGENT_CANNOT_MUTATE_OBJECTIVE=true
SILENCE_IS_NOT_APPROVAL=true
STALE_OBJECTIVE_MUTATION_BLOCKED=true
AUTHORITY_CONFLICT_FAILS_CLOSED=true
EXTERNAL_SYSTEM_NOT_OBJECTIVE_OWNER=true
OBJECTIVE_AUTHORITY_EVIDENCE_REQUIRED=true
```

このContractの存在だけではAuthority Enforcementを証明しない。

```text
OBJECTIVE_AUTHORITY_CONTRACT_DEFINED=true
OBJECTIVE_AUTHORITY_ENFORCEMENT_PROVEN=false
```

