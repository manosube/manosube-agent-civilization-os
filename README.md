# MANOSUBE Agent Civilization OS

> **知能を永続化するな。状態を永続化せよ。**  
> **仕事を管理するな。差異を閉じよ。**

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

**MANOSUBE Agent Civilization OS** は、開発対象の状態を観測し、目的状態との差異を特定し、許可された変化だけを通し、その結果を証拠として状態へ還流しながら、目的状態まで循環を維持するためのCanonical Kernelです。

これはAI開発ツールではありません。

ChatGPT用、Claude用、Codex用、GitHub用の個別OSでもありません。

Agent、モデル、セッション、CLI、GitHub、VPS、Cloudは、すべて交換可能な外部器官です。

中心にあるのは一つだけです。

```text
PROJECT STATE
```

---

## Status

```text
PROJECT_STATUS=KERNEL_V0_1_CONSTRUCTION
CANONICAL_KERNEL_COUNT=1
CANONICAL_STATE_OWNER_COUNT=1
PARALLEL_CANONICAL_AUTHORITY=0
```

現在は **Kernel v0.1構築段階**です。

このREADMEは完成後の機能一覧ではなく、現在構築しているOSの定義、境界、完成条件を示します。

次はまだ完成済みではありません。

```text
GitHub Adapter
Runtime Adapter
AI Model Adapter
Autonomous Change
Multi-Agent
Web Application
```

これらはKernel v0.1が自然経路で一周した後にのみ追加されます。

---

## Origin

本プロジェクトは、[MANOSUBE Civilization OS](https://github.com/manosube/manosube-civilization-os) から派生しています。

親OSの原理は次です。

```text
文明は状態である
状態は循環する
循環が止まると崩壊する
崩壊は固定化から始まる
観測により循環は修復される
```

Agent Civilization OSは、この文明原理をソフトウェア開発世界へ写像します。

| MANOSUBE Civilization OS | Development World |
|---|---|
| 位置 | Current Project State |
| 流動 | Information / Dependency / Execution Flow |
| 周期 | Observation → Change → Evidence → Reflow |
| 固定 | Unresolved Structural Difference |
| 循環 | Valid State Transition Continues |
| 還流 | Evidence Updates Canonical State |

親OSは文明原理を保持します。

本派生OSは、その中核を置換せず、開発世界における状態循環として実装します。

---

## Why This Exists

一般的な開発管理は、Task、Issue、Agent、Toolを中心に組み立てられます。

```text
Agent
↓
Task
↓
Tool
```

この構造では、Agentが変わる、セッションが終わる、Issueが分割される、ツールが停止するたびに、目的と現在状態の連続性が失われやすくなります。

MANOSUBEは逆から設計します。

```text
Project State
↓
Structural Difference
↓
Required Capability
↓
Authorized Change
↓
Evidence
↓
New Project State
```

Agentは仕事のownerではありません。

Agentは、観測されたDifferenceを閉じるために一時的に割り当てられる能力の担体です。

```text
Difference発生
↓
Required Capability決定
↓
Temporary Agent起動
↓
Observation / Change
↓
Evidence
↓
Stateへ還流
↓
Agent終了
```

Agentが消えても、State、Difference、Authority、Evidence、Lineageは残ります。

---

## The Canonical Kernel

Kernelは次の8要素だけで構成されます。

### 1. OBJECTIVE

人間が定める目的と、観測可能なTarget Stateです。

Objectiveは「改善する」のようなお願い文ではなく、Evidenceによって到達判定できるpredicateの集合として保持されます。

### 2. STATE

開発対象の現在世界です。

コードだけでなく、requirements、tests、CI、deployment、runtime、infrastructure、open differencesを一つのProject Stateとして扱います。

### 3. OBSERVATION

外界から事実を取り込む入口です。

Observationは判断ではありません。同じsource snapshotとschemaに対して、同じCanonical Factを生成しなければなりません。

### 4. DIFFERENCE

Target StateとObserved Stateの構造差です。

TaskやGitHub Issueではなく、`D-...`がCanonical Work Identityになります。

### 5. AUTHORITY

Changeを実行してよいかを決める境界です。

```text
CAN_DO ≠ MAY_DO
```

能力があってもAuthorityがなければ実行できません。

### 6. CHANGE

Differenceを閉じるために実行された、identityを持つ状態変化です。

Changeの実行は成功や完成を意味しません。

### 7. EVIDENCE

ObservationとChange Resultを裏付ける証拠です。

成功だけでなく、失敗、不在、未到達、BLOCKEDもEvidenceとして保持します。

### 8. REFLOW

Evidenceを次のCanonical Stateへ原子的に反映するState Transitionです。

REFLOWはログ保存ではありません。State、Difference status、confidence、decision、next observationを更新する循環です。

`LINEAGE`は第9のKernel段階ではありません。

```text
LINEAGE
= REFLOWが必ず残すState Transitionの不変記録
```

---

## Three Worlds, One OS

本プロジェクトは三つの世界を混同しません。

```text
I. KERNEL SOURCE WORLD
   憲法・schema・決定論的engine

II. CANONICAL STATE WORLD
    Projectごとのstate・event・evidence・lineage

III. ADAPTER WORLD
     GitHub・CLI・VPS・Cloud・AI等の外部器官
```

### Kernel Source

Gitでversion管理されるOS本体です。

### Canonical State Backend

BindingされたProjectの状態を保持します。Repository source treeとは分離されます。

```text
append-only transition events
+
materialized current state
```

`current state`だけを唯一の復元源にはしません。

### Adapters

Kernelへ外界を接続します。

AdapterはKernelを呼び出せますが、独自のCanonical State、Authority、Difference Closureを所有できません。

---

## Authority

権限は三層に分離されます。

```text
HUMAN
= OBJECTIVE AUTHORITY

MANOSUBE KERNEL
= STRUCTURAL AUTHORITY

AI AGENT
= EXECUTION CAPABILITY
```

### Human

人間は次を決定します。

```text
Objective
Boundary
Authority Envelope
Prohibited Actions
Constitutional Constraints
Irreversible Risk Acceptance
```

### MANOSUBE Kernel

Kernelは次を維持します。

```text
Canonical State
Difference Identity
Authority Evaluation
Change Lineage
Evidence Sufficiency
State Transition
Completion Semantics
```

### AI Agent

AIは許可された範囲で、観測・分析・実装・テスト・検証を担います。

AIはObjective、Authority、Kernel Constitution、Closure Policyを勝手に変更できません。

---

## Evidence Before Completion

MANOSUBEでは、次を厳密に分離します。

```text
DESIGNED
IMPLEMENTED
STATICALLY_VERIFIED
TEST_VERIFIED
INTEGRATED
NATURALLY_REACHABLE
RUNTIME_PROVEN
HUMAN_ACCEPTED
```

特に、次は同じではありません。

```text
DESIGNED ≠ IMPLEMENTED
IMPLEMENTED ≠ CONNECTED
TEST_PASS ≠ NATURAL_ROUTE_PASS
PR_MERGED ≠ RUNTIME_PROVEN
ARTIFACT_EXISTS ≠ CORRECTLY_CONSUMED
```

Differenceは、Change実行者の自己申告では閉じません。

```text
Expected State
=
Observed State
+
Sufficient Evidence
```

がClosure Policyによって確認された場合だけ、`CLOSED`になります。

Negative Evidenceにも観測範囲、期間、方法、試行回数、blind spotが必要です。

```text
NO_RESULT ≠ PROVEN_ABSENCE
```

---

## State Integrity

Canonical Stateは、単なるJSONファイルではありません。

v0.1では最低限、次を証明します。

```text
Canonical Serialization
Semantic Fingerprint
Schema Versioning
State Revision
Atomic Commit
Compare-And-Swap
Idempotency
Stale Change Rejection
Crash Recovery
Lineage Reconstruction
```

`observed_at`、Agent名、session ID、一時pathなどのvolatile metadataはsemantic fingerprintへ含めません。

同じsemantic stateは、別セッション・別Agentでも同じfingerprintを生成します。

---

## Repository Architecture

```text
manosube-agent-civilization-os/
├── README.md
├── ORIGIN.md
├── SECURITY.md
├── 00_KERNEL/      # Constitution and invariants
├── 01_SCHEMA/      # Machine-verifiable contracts
├── 02_ENGINE/      # Deterministic state transitions
├── 03_BINDING/     # Project, boundary and trust contracts
├── tests/          # Proof, not decoration
├── examples/       # Minimal canonical cycles
└── docs/           # Architecture and decisions
```

将来の拡張面：

```text
04_BOOT
05_OBSERVER
06_CAPABILITY
07_AGENT_RUNTIME
08_VERIFICATION
09_ADAPTER
10_APPLICATION
```

これらは最初から空directoryとして量産しません。必要なPhaseへ到達したときだけ追加します。

完全なauthority mapは `MANOSUBE_AGENT_CIVILIZATION_OS_DIRECTORY_CONSTITUTION.md` に定義します。

---

## Kernel v0.1

v0.1の目的は、便利なCLIやAgentを作ることではありません。

Agentなし、GitHub Adapterなし、CLIなしで、Sample Projectに対するCanonical Cycleを一周させることです。

```text
HUMAN-DEFINED FIXTURE
↓
OBJECTIVE / BOUNDARY / AUTHORITY
↓
MINIMAL FIXTURE BINDING
↓
STATE_0001
↓
OBSERVATION + OBSERVATION EVIDENCE
↓
DIFFERENCE D-0001
↓
AUTHORITY EVALUATION
↓
CHANGE C-0001
↓
RE-OBSERVATION + CHANGE RESULT EVIDENCE
↓
ATOMIC REFLOW
↓
STATE_0002
↓
D-0001 CLOSED
```

### v0.1 Completion Gates

```text
ORIGIN_DEFINED=true
PARENT_OS_PRESERVED=true
KERNEL_BOUNDARY_DEFINED=true

STATE_SERIALIZABLE=true
STATE_RELOADABLE=true
STATE_DETERMINISTIC=true
SEMANTIC_FINGERPRINT_STABLE=true
VOLATILE_METADATA_EXCLUDED=true
SCHEMA_VERSIONED=true

STATE_REVISIONED=true
ATOMIC_COMMIT_PROVEN=true
STALE_UPDATE_BLOCKED=true
DUPLICATE_CHANGE_IDEMPOTENT=true
PARTIAL_WRITE_NOT_CANONICAL=true
CRASH_RECOVERY_PROVEN=true

CAN_DO_NE_MAY_DO=true
PROHIBITED_CHANGE_BLOCKED=true
STALE_APPROVAL_REJECTED=true

OBSERVATION_EVIDENCE_SUPPORTED=true
CHANGE_RESULT_EVIDENCE_SUPPORTED=true
NEGATIVE_EVIDENCE_BOUNDED=true
CLAIM_WITHOUT_EVIDENCE_CANNOT_CLOSE=true

STATE_N_TO_STATE_N_PLUS_1_PROVEN=true
LINEAGE_RECONSTRUCTABLE=true
SESSION_LOSS_SAFE=true
AGENT_REQUIRED_FOR_KERNEL=false
ONE_FULL_NATURAL_CYCLE_PASS=true
```

すべてのGateが自然経路でPASSした時点で、`v0.1.0`として公開します。

---

## Roadmap

| Version | Completion Boundary |
|---|---|
| `v0.1` | Canonical Kernel natural cycle |
| `v0.2` | Local Binding / Boot / CLI |
| `v0.3` | GitHub Projection |
| `v0.4` | Runtime Observation |
| `v0.5` | Temporary Agent Runtime |
| `v0.6` | Independent Verification |
| `v0.7` | Multi-Model Replaceability |
| `v0.8` | Bounded Autonomous Change |
| `v0.9` | Dynamic Multi-Agent |
| `v1.0` | Objective Continuity closed loop |

開発順序は逆転させません。

```text
Kernel
↓
Local Operation
↓
GitHub
↓
Runtime
↓
Temporary Agent
↓
Independent Verification
↓
Model Replaceability
↓
Bounded Autonomy
↓
Dynamic Multi-Agent
```

各Versionは、機能数ではなく一つのStructural Capabilityと一つのNatural Proofで完成します。

---

## GitHub Is a Projection Surface

GitHubは重要な共有・version管理面ですが、Canonical Stateではありません。

| MANOSUBE | GitHub Projection |
|---|---|
| Difference | Issue |
| Change | branch / commit / Pull Request |
| Evidence | check / review / artifact reference |
| Decision | approval / review reference |
| State | repository snapshot reference |

```text
Issue number ≠ Difference ID
Pull Request number ≠ Change ID
CI run ID ≠ Evidence ID
```

GitHubが停止しても、MANOSUBEのCanonical StateとLineageは再構築可能でなければなりません。

---

## What This Project Will Not Become

```text
AI chat collection
Permanent agent organization
Prompt library
Long-term conversation memory
GitHub automation wrapper
CI/CD wrapper
Universal CLI
Agent marketplace
Centralized AI controller
Human judgment replacement
Feature collection without a canonical kernel
```

便利でもCanonical Cycleに必要でないものをKernelへ入れません。

---

## Structural Invariants

```text
ONE_KERNEL=true
ONE_CANONICAL_STATE_OWNER=true
PARALLEL_AUTHORITY=false

AGENT_IS_PROCESS=true
GITHUB_IS_PROJECTION=true
APPLICATION_IS_READ_MODEL=true

CAN_DO_NE_MAY_DO=true
CHANGE_NE_COMPLETION=true
CLAIM_NE_EVIDENCE=true
NO_RESULT_NE_PROVEN_ABSENCE=true

STATE_SURVIVES_AGENT_LOSS=true
STATE_SURVIVES_SESSION_LOSS=true
STATE_SURVIVES_TOOL_REPLACEMENT=true
```

---

## Development Rule

すべての設計・変更・Pull Requestについて、次を確認します。

```text
これはKernelか、Adapterか
Canonical ownerは一つか
Target StateとObserved Stateを分離したか
DifferenceはEvidenceへ接続されているか
CapabilityとAuthorityを混同していないか
ChangeをCompletionと誤認していないか
Change後に独立した再観測があるか
StateはAgentやsessionから再構築可能か
外部systemを外してもKernelが生存するか
```

一つでも原則違反、authority重複、Evidence欠落、Canonical State汚染があれば、変更を完成扱いしません。

---

## Security and Trust

BindingされたRepositoryの内容は観測対象であり、Authority instructionではありません。

```text
BOUND PROJECT CONTENT
= OBSERVATION TARGET
≠ AUTHORITY INSTRUCTION
```

Repository内のREADME、Issue、code comment、prompt文字列は、ObjectiveやAuthorityを変更できません。

また、次をKernel境界として扱います。

```text
secretをEvidenceへ保存しない
credentialをfingerprintへ含めない
symlinkでBoundary外へ移動しない
観測と任意コード実行を分離する
command実行前にAuthorityを照合する
submoduleと外部dependencyを別Boundaryとして扱う
```

---

## For Humans

人間が最初に与えるものは、細かなTask一覧ではありません。

```text
OBJECTIVE
BOUNDARY
AUTHORITY
```

その後、MANOSUBEがProject Stateを観測し、Differenceを導出します。

人間はすべての作業を逐次操作する必要がなくなります。

同時に、AIが目的・権限・憲法を勝手に変更することもできません。

---

## For AI

このRepositoryを扱うAIは、最初に次を確認してください。

```text
1. Objective
2. Boundary
3. Authority
4. Current State
5. Active Differences
6. Existing Evidence
7. State Revision and Fingerprint
```

作業報告では、作業量より状態変化を先に示してください。

```text
CONFIRMED
INFERRED
UNOBSERVED
BLOCKED
FAILED
COMPLETED
```

を区別し、Evidenceなしに成功を宣言しないでください。

---

## Final Principle

MANOSUBE Agent Civilization OSの価値は、多くのAIを動かせることではありません。

```text
AIが入れ替わっても
Toolが入れ替わっても
Sessionが消えても
Issueが変わっても
実装方法が変わっても

Objective
State
Difference
Authority
Evidence
Lineage
Reflow

が失われないこと
```

にあります。

> **知能を永続化するな。状態を永続化せよ。**

> **仕事を管理するな。差異を閉じよ。**

> **Agentを信頼するな。Evidenceを接続せよ。**

> **機能を増やすな。Kernelから必要な器官を派生させよ。**

