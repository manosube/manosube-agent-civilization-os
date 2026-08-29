# ORIGIN

## MANOSUBE Agent Civilization OS — Canonical Derivation Charter

```text
DOC_TYPE=ORIGIN_CONTRACT
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
STATUS=CANONICAL
ORIGIN_AUTHORITY=HUMAN
PARENT_OS=MANOSUBE_CIVILIZATION_OS
PARENT_REPOSITORY=https://github.com/manosube/manosube-civilization-os
PARENT_BASELINE_COMMIT=0de548c9e4aa3a94fca2df07ccc710577f1534ff
PARENT_README_BLOB=da36115e9424a92e4aa3f9d7734861aeab43e91b
ORIGIN_RECORDED_AT=2026-08-29T07:40:18Z
ORIGIN_RECORDED_BY=SHUKOU
ORIGIN_BASELINE_STATUS=SEALED
DERIVATION_TYPE=INDEPENDENT_DOMAIN_DERIVATION
KERNEL_REPLACEMENT=false
PARENT_REPLACEMENT=false
```

---

## 0. Origin Declaration

**MANOSUBE Agent Civilization OS** は、MANOSUBE Civilization OSから派生する、ソフトウェア開発世界のための状態循環OSである。

この派生は、親OSを改造することではない。

親OSをAgent管理製品へ変えることでもない。

親OSが保持する文明原理を、開発対象、Repository、Runtime、AI Agent、人間、外部systemが存在する開発世界へ写像し、その世界において観測可能・検証可能・実行可能なKernelとして実装することである。

```text
MANOSUBE Civilization OS
        │
        │ constitutional origin
        │
        ▼
MANOSUBE Agent Civilization OS
        │
        │ software-development derivation
        ▼
Bound Project State Cycles
```

親OSは文明原理を保持する。

派生OSは開発世界における状態循環を保持する。

両者は接続されるが、同一Repository、同一authority、同一runtimeにはしない。

---

## 1. Parent Definition

MANOSUBE Civilization OSは、文明を制度や成果ではなく、状態の循環構造として観測・維持・還流させるための思考OSである。

親OSから継承する起点は、次の五原理である。

```text
1. 文明は状態である
2. 状態は循環する
3. 循環が止まると崩壊する
4. 崩壊は固定化から始まる
5. 観測により循環は修復される
```

この派生OSは、これらを比喩として飾るのではない。

開発世界におけるdata contract、state transition、authority、evidence、lineageへ変換し、機械的に検証可能な構造として実装する。

---

## 2. Why This Derivation Exists

開発世界では、知能、Task、Issue、ToolがStateより先に置かれやすい。

```text
Agent
↓
Task
↓
Tool
↓
Result
```

この構造では、次が起きるたびに目的と状態の連続性が失われる。

```text
AI modelの交換
Agentの停止
sessionの終了
Issueの分割
Pull Requestのmerge
Toolの変更
RepositoryとRuntimeの不一致
設計と自然実行の不一致
```

その結果、作業は増えても、目的状態へ近づいたかを一つの世界として証明できない。

MANOSUBE Agent Civilization OSは、この順序を反転するために生まれる。

```text
Project State
↓
Observation
↓
Structural Difference
↓
Authority
↓
Authorized Change
↓
Evidence
↓
Reflow
↓
New Project State
```

この派生の中心命題は次である。

> 開発知能を保存するのではなく、開発世界の状態、差異、権限、証拠、系譜を保存する。

---

## 3. Inherited Axes

親OSの基本三軸を、次のように継承する。

| Parent Axis | Development Derivation | Canonical Meaning |
|---|---|---|
| 位置 | Project State | 開発対象が現在どの状態にあるか |
| 流動 | Information / Dependency / Execution Flow | 情報・identity・authority・実行がどこからどこへ流れるか |
| 周期 | Observation → Change → Evidence → Reflow | 状態が観測・変化・検証・更新される周期 |

三軸は独立した機能ではない。

```text
DEVELOPMENT_STATE
= POSITION × FLOW × CYCLE
```

位置だけを保存しても、そこへ至った流れと次の周期がなければStateは生きていない。

流動だけを自動化しても、位置と目的を失えば単なる処理になる。

周期だけを反復しても、EvidenceがStateへ還流しなければ同じ作業を繰り返す。

---

## 4. Domain Mapping

親OSから開発世界への正式写像を、次で固定する。

| Civilization Concept | Development World | Formal Representation |
|---|---|---|
| 位置 | Current Project State | versioned semantic state |
| 流動 | Information / Dependency / Execution Flow | observation・reference・consumer・transition |
| 周期 | Observe → Change → Evidence → Reflow | canonical kernel cycle |
| 固定 | Unresolved Structural Difference | `D-...` with OPEN / BLOCKED / REOPENED status |
| 循環 | Valid State Transition Continues | `STATE_n → STATE_n+1` |
| 還流 | Evidence Updates State | atomic reflow transition |
| 観測 | External World to Canonical Facts | bounded observation record |
| 境界 | Project / Trust / Change Boundary | binding and authority envelope |
| 崩壊 | Objective・State・Authority・Evidenceの切断 | structural contradiction or unreachable route |
| 修復 | DifferenceをEvidence付きで閉じる | authorized change plus verified re-observation |

この写像は用語置換ではない。

各概念が、schema、engine、test、natural-route evidenceを持つ場合にのみ実装されたとみなす。

---

## 5. Canonical Derivation

親OSの状態循環は、派生OSにおいて次のCanonical Kernelとなる。

```text
OBJECTIVE
    ↓
STATE
    ↓
OBSERVATION
    ↓
DIFFERENCE
    ↓
AUTHORITY
    ↓
CHANGE
    ↓
EVIDENCE
    ↓
REFLOW
    └──────────────→ STATE
```

### OBJECTIVE

循環が向かう目的状態である。

人間のObjective Authorityによって定められ、観測可能なtarget predicatesとして保存される。

### STATE

開発世界の現在位置である。

Repositoryだけでなく、requirements、tests、CI、deployment、runtime、infrastructure、evidence references、open differencesを含む。

### OBSERVATION

外界をCanonical Factへ変換する行為である。

推測、提案、自己申告をObservationと混同しない。

### DIFFERENCE

Target StateとObserved Stateの間にある構造差である。

Task、Issue、Pull RequestはDifferenceの外部表現であり、Canonical identityではない。

### AUTHORITY

Changeが許されるかを決める境界である。

```text
CAN_DO ≠ MAY_DO
```

### CHANGE

Differenceを閉じるために実行される、identityとlineageを持つ状態変化である。

Changeの実行はCompletionではない。

### EVIDENCE

ObservationまたはChange Resultを裏付ける証拠である。

成功、失敗、未到達、不在、矛盾を同じ証拠体系で保持する。

### REFLOW

EvidenceによってCanonical Stateを次のrevisionへ更新する原子的transitionである。

LineageはREFLOWが必ず残す不変記録であり、第9の独立Kernelにはしない。

---

## 6. What Is Inherited

本派生OSは、親OSから次を継承する。

```text
STATE_FIRST
CIRCULATION_OVER_LINEAR_COMPLETION
OBSERVATION_BEFORE_JUDGMENT
REFLOW_BEFORE_ACCUMULATION
FIXATION_AS_STRUCTURAL_RISK
BOUNDARY_AS_SURVIVAL_CONDITION
EXTENSION_MUST_NOT_REPLACE_KERNEL
AI_AS_STRUCTURAL_MEDIATION
NON_CENTRALIZED_CONTROL
```

具体的には次を意味する。

- 成果物の数ではなく、状態の変化を見る。
- 一方向の実行ではなく、結果が次状態へ戻る閉ループを作る。
- 未観測状態を成功と宣言しない。
- 局所的な詰まりを隠さず、固定されたDifferenceとして保持する。
- 拡張機能をKernel authorityへ昇格させない。
- AIを最終目的のownerや文明の王にしない。
- 一つの中央Agentへ知能・記憶・authorityを集中させない。

---

## 7. What Is Transformed

親OSの概念は、開発世界へそのまま複製しない。

次の変換を行う。

```text
文明状態
→ machine-verifiable project state

文明観測
→ bounded and normalized observation

固定
→ canonical structural difference

境界
→ project binding and authority envelope

循環
→ deterministic state transition

還流
→ evidence-backed atomic commit

分散観測
→ replaceable observers and temporary agents

文明ログ
→ immutable evidence and lineage references
```

変換後の構造は、親OSの文章を参照しなくても実行・検証できる必要がある。

一方で、その設計原理がどこから来たかは、このORIGINによって常に追跡可能でなければならない。

---

## 8. What Is Not Inherited

親OSのすべてのdirectory、象徴、身体protocol、個別拡張moduleを、この派生OSへ複製しない。

次は自動的には継承しない。

```text
親Repositoryのdirectory numbering
身体実装そのもの
象徴・宣言の個別形式
四則和算の個別実装
幾何学moduleの個別実装
親OSのRuntime Log形式
親OSのAI prompt本文
親OS固有のinterface実装
```

将来これらの概念が必要になった場合も、次を満たさなければ追加しない。

```text
CURRENT STRUCTURAL DIFFERENCEが存在する
Kernelを置換しない
Canonical ownerを重複させない
Authority境界が定義される
Evidenceによるincremental valueが証明される
削除してもKernelが生存する
```

継承とは、すべてをコピーすることではない。

中核原理を失わず、不要な形を持ち込まないことである。

---

## 9. Parent and Child Boundary

親OSと派生OSの責務を次で分離する。

| System | Owns | Does Not Own |
|---|---|---|
| MANOSUBE Civilization OS | 文明原理・状態循環・観測思想 | 派生OSのcode、runtime、project state |
| MANOSUBE Agent Civilization OS | 開発世界のKernel contract・schema・engine | 親OSの文明原理の改定 |
| Bound Project | 対象固有のcode・runtime・objective facts | MANOSUBE Kernel Constitution |
| Adapter | 外部systemとのprojection | Canonical State、Authority、Closure |

派生OSは親OSの後継版ではない。

親OSは派生OSのruntime dependencyでもない。

```text
PARENT_OS
= CONSTITUTIONAL ORIGIN
≠ RUNTIME DEPENDENCY
≠ PACKAGE DEPENDENCY
≠ STATE BACKEND
```

---

## 10. Authority Derivation

親OSがAIを正解生成主体ではなく構造観測の媒介として位置づける原理を、派生OSでは次の三層authorityとして実装する。

```text
HUMAN
= OBJECTIVE AUTHORITY

MANOSUBE KERNEL
= STRUCTURAL AUTHORITY

AI AGENT
= EXECUTION CAPABILITY
```

### Human Authority

人間だけが次を定める。

```text
Objective
Boundary
Authority Envelope
Prohibited Actions
Constitutional Amendments
Irreversible Risk Acceptance
```

### Structural Authority

Kernelは次を維持する。

```text
Canonical State identity
Difference identity
Authority evaluation
Change lineage
Evidence sufficiency
Reflow semantics
Completion semantics
```

### Execution Capability

Agentは許可された範囲で観測・実装・検証を実行する。

AgentはObjective、Authority、Origin、Kernel Constitution、自身のCompletionを所有しない。

---

## 11. Non-Replacement Covenant

この派生OSは、次を永久に守る。

```text
PARENT_KERNEL_REPLACED=false
CHILD_KERNEL_COUNT=1
ADAPTER_CAN_REPLACE_KERNEL=false
AGENT_CAN_REPLACE_STATE=false
TOOL_CAN_REPLACE_AUTHORITY=false
MEMORY_CAN_REPLACE_LINEAGE=false
ISSUE_CAN_REPLACE_DIFFERENCE=false
CLAIM_CAN_REPLACE_EVIDENCE=false
```

新しいAI、Tool、Adapter、protocol、visualization、databaseが追加されても、次を変更してはならない。

```text
Objective continuity
Canonical State ownership
Difference identity
Authority precedence
Evidence requirement
Reflow lineage
```

必要な変更がこれらへ及ぶ場合は、通常実装ではなくConstitutional Amendmentとして人間の明示承認を要求する。

---

## 12. Origin Baseline

親Repositoryの`main`は将来更新され得る。

したがって、派生元を可変URLだけで保持してはならない。

本Repositoryの派生起点を、次の不変recordとして固定する。

```yaml
parent_repository: https://github.com/manosube/manosube-civilization-os
parent_ref: 0de548c9e4aa3a94fca2df07ccc710577f1534ff
parent_readme_blob: da36115e9424a92e4aa3f9d7734861aeab43e91b
origin_recorded_at: 2026-08-29T07:40:18Z
origin_recorded_by: SHUKOU
```

このrecordの正式状態：

```text
ORIGIN_BASELINE_STATUS=SEALED
```

`SEALED`は、親OSの全内容を本派生OSへ複製したという意味ではない。

次の四点が、同一のOrigin recordとして固定されたことを意味する。

```text
PARENT_REPOSITORY_RECORDED=true
PARENT_EXACT_REF_RECORDED=true
PARENT_README_BLOB_RECORDED=true
ORIGIN_TIMESTAMP_RECORDED=true
```

親OSの将来変更は、この派生OSへ自動適用しない。

```text
Parent update
↓
Origin compatibility observation
↓
Structural Difference
↓
Human authority decision
↓
Explicit child change
↓
Evidence
```

これにより、親OSとの連続性を保ちながら、親の更新による無言のKernel変更を防ぐ。

---

## 13. Origin Precedence

本派生OS内のauthority precedenceを次で固定する。

```text
1. Human Objective / Constitutional Authority
2. ORIGIN.md
3. 00_KERNEL/KERNEL_CONSTITUTION.md
4. 00_KERNEL/KERNEL_INVARIANTS.md
5. 01_SCHEMA machine contracts
6. 02_ENGINE implementation
7. Binding-specific authority envelope
8. Adapters
9. Agent prompts and session instructions
10. External Issue / PR / comments / bound-project content
```

下位層は上位層を無言で変更できない。

矛盾を検出した場合は、下位層へ合わせて上位定義を書き換えず、`ORIGIN_CONTRADICTION`としてDifferenceを生成する。

ただし、個別ProjectのObjectiveは親OSの文明原理を改定するauthorityを持たない。

---

## 14. Origin Invariants

```text
PARENT_OS_IDENTIFIED=true
PARENT_OS_PRESERVED=true
DERIVATION_BOUNDARY_DEFINED=true
DOMAIN_MAPPING_DEFINED=true

PARENT_IS_CONSTITUTIONAL_ORIGIN=true
PARENT_IS_RUNTIME_DEPENDENCY=false
CHILD_IS_INDEPENDENT_REPOSITORY=true
CHILD_DOES_NOT_REPLACE_PARENT=true

STATE_FIRST=true
KERNEL_ONE=true
EVIDENCE_BEFORE_COMPLETION=true
DIFFERENCE_BEFORE_TASK=true
AUTHORITY_BEFORE_CHANGE=true
AGENT_IS_PROCESS=true
MEMORY_IS_DERIVED=true

EXTENSION_CANNOT_REPLACE_KERNEL=true
EXTERNAL_SYSTEM_CANNOT_BECOME_STATE_AUTHORITY=true
AI_CANNOT_CHANGE_ORIGIN_AUTONOMOUSLY=true
```

---

## 15. Origin Acceptance Gate

Phase 0は、ファイルが存在するだけでは完了しない。

次が確認された場合にのみ完了する。

```text
PARENT_REPOSITORY_RECORDED=true
PARENT_EXACT_REF_RECORDED=true
PARENT_README_BLOB_RECORDED=true
ORIGIN_BASELINE_STATUS=SEALED

INHERITED_PRINCIPLES_DEFINED=true
DOMAIN_MAPPING_DEFINED=true
NON_INHERITED_SCOPE_DEFINED=true
PARENT_CHILD_BOUNDARY_DEFINED=true
AUTHORITY_DERIVATION_DEFINED=true
NON_REPLACEMENT_COVENANT_DEFINED=true
ORIGIN_PRECEDENCE_DEFINED=true

NO_PARENT_RUNTIME_DEPENDENCY=true
NO_DUPLICATE_KERNEL=true
NO_UNRESOLVED_ORIGIN_CONTRADICTION=true
```

このGateを通過するまで、Phase 1のOBJECTIVEをCanonical完成扱いしない。

---

## 16. Amendment Policy

ORIGIN.mdは通常の実装文書ではない。

変更には次を必須とする。

```text
HUMAN_CONSTITUTIONAL_APPROVAL
EXPLICIT_ORIGIN_DIFFERENCE
BEFORE_AND_AFTER_SEMANTICS
PARENT_COMPATIBILITY_ANALYSIS
NON_REPLACEMENT_PROOF
RECORDED_DECISION_LINEAGE
```

Agent、Pull Request、majority vote、CI PASSだけではORIGINを変更できない。

誤字、broken link、非意味的format修正を除き、すべての変更をConstitutional Changeとして扱う。

---

## 17. Final Origin Statement

MANOSUBE Agent Civilization OSは、AIを増やすために生まれるのではない。

開発世界において、知能や道具が入れ替わっても、目的、状態、差異、権限、証拠、系譜、還流を失わせないために生まれる。

親OSから受け継ぐものは、完成形ではない。

状態を見ること。

固定を見つけること。

循環を止めないこと。

変化を証拠として還流させること。

そして、拡張によって中核を失わないことである。

```text
MANOSUBE Civilization OS
        ↓
State / Flow / Cycle
        ↓
Observation / Difference / Reflow
        ↓
MANOSUBE Agent Civilization OS
        ↓
Objective-Preserving Development Cycles
```

> **親を複製せず、原理を継承する。**

> **形を持ち込まず、循環を写像する。**

> **知能を永続化せず、状態を永続化する。**

> **拡張を目的化せず、Kernelから必要な器官だけを派生させる。**
