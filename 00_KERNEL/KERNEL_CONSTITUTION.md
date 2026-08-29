# MANOSUBE Agent Civilization OS

## Canonical Kernel Constitution

```text
DOC_TYPE=KERNEL_CONSTITUTION
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=KERNEL-CONSTITUTION-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
PARENT_OS=manosube/manosube-civilization-os
PARENT_BASELINE_COMMIT=0de548c9e4aa3a94fca2df07ccc710577f1534ff
CONSTITUTIONAL_AUTHORITY=HUMAN
CANONICAL_KERNEL_COUNT=1
CANONICAL_STATE_OWNER_COUNT=1
PARALLEL_CANONICAL_AUTHORITY=0
```

---

# PREAMBLE — 前文

MANOSUBE Agent Civilization OSは、AIを増やすためのOSではない。

Taskを大量に処理するためのOSでも、GitHub、CLI、API、MCP、Cloud、VPSを一つに束ねるための統合基盤でもない。

本OSが守るものは、ただ一つである。

> 人間が定めた目的から、現在状態、観測、差異、権限、変化、証拠、還流へ至る循環を、入口・Agent・Tool・Sessionが交換されても失わせないこと。

親であるMANOSUBE Civilization OSは、次を原理とする。

```text
文明は状態である
状態は循環する
循環が止まると崩壊する
崩壊は固定化から始まる
観測により循環は修復される
```

本憲法は、この原理を開発世界へ写像し、Canonical Kernelの不変境界を定める。

```text
位置 = Current Project State
流動 = 情報・依存・実行の流れ
周期 = Observation → Change → Evidence → Reflow
固定 = 未解決のStructural Difference
循環 = Objectiveへ向かうState Transition
還流 = Evidenceによる次Stateの更新
```

本憲法は、実装上の都合、特定Agentの能力、外部サービスの制約、一時的な失敗に合わせて弱めてはならない。

---

# ARTICLE I — 唯一のKernel

## 第1条 Canonical Kernel

MANOSUBE Agent Civilization OSのCanonical Kernelは、一つだけ存在する。

```text
CANONICAL_KERNEL_COUNT=1
```

GitHub用、ChatGPT用、Claude用、Codex用、CLI用、VPS用、Cloud用の別Kernelを作ってはならない。

入口と実行器官が異なっても、内部のState、Identity、Authority、Evidence、Lineage、Completion Semanticsは同一でなければならない。

```text
ENTRY POINT
→ BOOT LOADER
→ CANONICAL KERNEL
→ CANONICAL PROJECT STATE
```

## 第2条 Canonical Cycle

Kernelの本体は、次の循環である。

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

この循環を省略、逆転、複製してはならない。

特に、次の短絡をCanonical Transitionとして認めない。

```text
TASK → CHANGE
ISSUE → COMPLETION
CHANGE → CLOSED
TEST PASS → OBJECTIVE COMPLETE
PR MERGED → RUNTIME PROVEN
AGENT REPORT → CANONICAL STATE
```

## 第3条 Kernelの非対象

次はKernelではない。

```text
Agent
Task
Issue
Pull Request
Commit
Tool
Prompt
Conversation
Memory
Adapter
User Interface
Runtime Provider
```

これらは交換可能なProjection、Capability、ProcessまたはExecution Surfaceであり、Kernelを置換できない。

---

# ARTICLE II — 人間・Kernel・Agent

## 第4条 Authorityの三層分離

Authorityは次の三層に分離する。

```text
HUMAN
= OBJECTIVE AUTHORITY
+ CONSTITUTIONAL AUTHORITY
+ IRREVERSIBLE RISK AUTHORITY

MANOSUBE KERNEL
= STRUCTURAL AUTHORITY
+ AUTHORITY EVALUATION
+ STATE TRANSITION ENFORCEMENT

AI AGENT
= EXECUTION CAPABILITY
```

## 第5条 Human Authority

人間だけが次を定める。

```text
objective
boundary
authority envelope
prohibited actions
constitutional constraints
不可逆リスクの受容
```

KernelまたはAgentは、人間のObjectiveを独自に変更、縮小、置換、達成しやすい表現へ弱化してはならない。

## 第6条 Kernel Authority

Kernelは次を担う。

```text
Canonical Stateの維持
Observationの構造化
Structural Differenceの導出
Authority照合
Change Lineageの保存
Evidence評価
Closure評価
Atomic State Transition
Reflow
Contradictionの可視化
Completion判定
```

Kernelは人間のObjective Authorityを代行しない。

## 第7条 Agentの地位

Agentは、Differenceを閉じるために一時的に選択される能力の担体である。

```text
WORK UNIT
→ REQUIRED CAPABILITY
→ AVAILABLE AGENT
→ AUTHORIZED EXECUTION
→ EVIDENCE
→ AGENT RELEASE
```

Agentは恒久的な役職、Canonical State Owner、Authority Owner、Lineage Ownerにならない。

```text
CAPABILITY
≠
AUTHORITY
```

Agentが停止、交換、更新、消失しても、Project Stateから作業を再構成できなければならない。

---

# ARTICLE III — Objective

## 第8条 Objectiveの地位

Objectiveは全State Transitionの最上位基準である。

Task、Issue、Next Step、Agent PlanはObjectiveより上位に立たない。

```text
OBJECTIVE
→ TARGET STATE
→ CURRENT STATE
→ STRUCTURAL DIFFERENCE
→ NEXT AUTHORIZED CHANGE
```

## 第9条 Observable Predicate

Objectiveは、抽象的な成功語だけで完成判定してはならない。

```text
production_ready=true
complete=true
fixed=true
```

のような宣言は、それ自体ではTarget Stateを証明しない。

Objectiveは最低限、次を持つ。

```text
objective_id
statement
owner_authority
target_predicates
completion_policy
revision
previous_objective_ref
change_reason
```

Target Predicateは観測可能であり、期待値、比較演算、Evidence要件を持たなければならない。

## 第10条 Objective Continuity

Objectiveの変更は、通常のChangeと区別して履歴化する。

失敗、未到達、Evidence不足を隠すためにObjective、Target Predicate、Completion Policyを変更してはならない。

---

# ARTICLE IV — Canonical State

## 第11条 State中心原則

本OSの唯一の中心はProject Stateである。

```text
PROJECT STATE
```

Stateは最低限、次を参照または保持する。

```text
objective
boundary
authority
current_state
target_state
observations
structural_differences
authorized_changes
evidence references
lineage
decisions
runtime_state
unresolved_contradictions
reflow_state
```

> 知能を永続化するな。状態を永続化せよ。

## 第12条 Semantic StateとMetadata

Semantic Stateと揮発性Metadataを分離する。

```text
STATE
= SEMANTIC STATE
+ METADATA
+ EVIDENCE REFERENCES
+ REVISION
+ SEMANTIC FINGERPRINT
```

Semantic Fingerprintは、schema versionと正規化されたSemantic Stateだけから決定的に計算する。

次をFingerprintへ含めてはならない。

```text
observed_at
observer
Agent名
session ID
temporary path
serialization order
non-deterministic log
credential
secret
```

## 第13条 Canonical State Owner

同一Project StateのCanonical Ownerは一つである。

```text
CANONICAL_STATE_OWNER_COUNT=1
PARALLEL_CANONICAL_AUTHORITY=0
```

GitHub、Adapter、CLI、Agent、Conversation、Test Fixture、Fallback Artifactを第二State Authorityにしてはならない。

## 第14条 State Backend

Canonical StateはKernel Source Repositoryの内部へ保存しない。

```text
REPOSITORY
= KERNEL SOURCE
+ SCHEMA
+ CONTRACT
+ TEST SOURCE

STATE BACKEND
= PROJECT STATE
+ EVENTS
+ EVIDENCE
+ LINEAGE
+ APPROVALS
```

State Backendは最低限、append-only transition eventsと、それから導出されるmaterialized current stateを持つ。

`current.json`だけを唯一の復元源にしてはならない。

---

# ARTICLE V — Observation

## 第15条 Observation First

Changeより前にCurrent Stateを観測する。

観測されていない仮定、会話上の記憶、古い報告、Agentの推測をCurrent Stateとして確定してはならない。

```text
OBSERVATION
= TARGET
+ SCOPE
+ METHOD
+ TIME BOUNDARY
+ NORMALIZED FACTS
+ KNOWN BLIND SPOTS
+ OBSERVATION EVIDENCE
```

## 第16条 状態語彙

次を区別する。

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

また、観測不能または未到達を、事実に応じて次で保持する。

```text
UNKNOWN
UNOBSERVED
BLOCKED
INCOMPLETE
FAILED
```

観測できない対象をPASSにしてはならない。

## 第17条 Negative Observation

単なる検索失敗を不存在の証明として扱わない。

```text
NO_RESULT
≠
PROVEN_ABSENCE
```

Negative Observationは、観測範囲、開始・終了時刻、方法、試行回数、完了性、既知の死角を持たなければならない。

---

# ARTICLE VI — Difference

## 第18条 Difference-First Operation

作業の最上位identityはTaskでもIssueでもない。

```text
DIFFERENCE_ID
```

Differenceは最低限、次を持つ。

```text
difference_id
target_state
observed_state
structural_difference
impact
evidence_refs
authority_required
closure_policy
status
```

## 第19条 外部Workとの関係

Issue、PR、commit、test、deploymentはDifferenceを閉じるための外部表現である。

```text
DIFFERENCE
→ WORK UNITS
→ CHANGES
→ RE-OBSERVATION
→ EVIDENCE
→ CLOSURE
```

Issue Close、PR Merge、code existence、test passだけではDifferenceを閉鎖しない。

## 第20条 Closure

Changeが`EXECUTED`になっても、DifferenceはOPENのままである。

独立した再観測、Change Result Evidence、Closure Policy評価を経て初めて、Differenceを`CLOSED`、`RETAINED`または`BLOCKED`へ遷移できる。

State Driftが再観測された場合は、定義された規則に基づいて新規Differenceを生成するか、既存Differenceを`REOPENED`へ遷移する。

---

# ARTICLE VII — Authority and Approval

## 第21条 Authority Check

すべてのChangeは実行前にAuthorityを照合する。

権限が不明、境界外、禁止対象、承認失効、不可逆リスク未受容の場合、Changeを実行してはならない。

## 第22条 Exact Approval Binding

Human Approvalは次へ正確に結合する。

```text
approval_id
change_id
approved_state_fingerprint
approved_action_fingerprint
approved_by
approved_at
expires_at
scope
status
```

次の場合、承認は無効である。

```text
Change内容が変わった
対象Stateが変わった
Scopeが変わった
期限が切れた
承認が撤回された
```

## 第23条 Prohibition Supremacy

禁止事項は、Agent能力、利便性、成功可能性、時間短縮、外部Toolの許可によって解除されない。

```text
TOOL CAN EXECUTE
≠
CHANGE IS AUTHORIZED
```

---

# ARTICLE VIII — Change

## 第24条 Change Identity

Changeは最低限、次を持つ。

```text
change_id
difference_id
before_state_fingerprint
expected_state_revision
authority_ref
action
idempotency_key
execution_result
status
```

Change自身が`after_state_fingerprint`、Difference Closure、Objective Completionを宣言してはならない。

## 第25条 Change Lifecycle

Changeのstatusは次に限定する。

```text
PROPOSED
AUTHORIZED
RUNNING
EXECUTED
FAILED
REJECTED
STALE
```

`COMPLETED`および`CLOSED`はChange自身のstatusとして使用しない。

## 第26条 Atomicity and CAS

State更新はCompare-And-Swapで保護する。

```text
CURRENT REVISION = EXPECTED REVISION
→ COMMIT MAY PROCEED

CURRENT REVISION ≠ EXPECTED REVISION
→ STALE CHANGE
```

次をKernel要件とする。

```text
ATOMIC_STATE_COMMIT=true
STALE_CHANGE_BLOCKED=true
DUPLICATE_CHANGE_IDEMPOTENT=true
PARTIAL_WRITE_NOT_CANONICAL=true
CRASH_RECOVERY_PROVEN=true
```

部分書込、schema不正、fingerprint不一致、revision不整合をCanonical Stateとして採用してはならない。

---

# ARTICLE IX — Evidence

## 第27条 Evidenceの二位置

Evidenceは二種類に分離する。

```text
OBSERVATION EVIDENCE
= before stateとDifferenceを裏付ける証拠

CHANGE RESULT EVIDENCE
= Change後の再観測結果を裏付ける証拠
```

Changeを行わないObservation Cycleでも、Observation Evidenceを正式に保存できなければならない。

## 第28条 Evidence Contract

Evidenceは最低限、次を持つ。

```text
evidence_id
timestamp
target
before_state
observation_method
change_identity
authority_used
after_state
expected_result
observed_result
status
artifact_references
lineage
remaining_differences
```

StateはEvidence本文を無制限に埋め込まず、不変Evidenceへの参照を保持する。

## 第29条 Evidence Strength

Evidence強度は次で表す。

```text
E0 = 宣言のみ
E1 = 静的確認
E2 = 単体テスト
E3 = 統合テスト
E4 = 自然経路実行
E5 = 対象Runtime実証
E6 = 反復・独立Runtime実証
```

高リスクStateを弱いEvidenceで完成扱いしてはならない。

## 第30条 Evidence Sufficiency

Difference Closureには、Differenceごとに明示されたClosure Policyを適用する。

```text
required_claims
minimum_evidence_level
independent_verification_required
max_evidence_age
observation_scope
```

Evidence要件を満たさない場合、DifferenceはOPENまたはBLOCKEDのまま保持する。

---

# ARTICLE X — Reflow and Lineage

## 第31条 Reflow

Reflowはログ保存ではない。

Evidenceによって次を更新するCanonical State Transitionである。

```text
current_state
difference status
confidence
authority history
decision lineage
next observation
next authorized change
completion state
```

失敗、EMPTY、BLOCKED、STALE、未到達も正式なEvidenceとして還流する。

## 第32条 Lineage

LINEAGEは第9のKernel要素ではない。

```text
LINEAGE
= REFLOWによって保存される
  State Transitionの不変記録
```

Transition Eventは最低限、次を持つ。

```text
previous_revision
previous_fingerprint
transition_type
input_refs
authority_ref
resulting_revision
resulting_fingerprint
committed_at
```

Lineageはappend-onlyであり、現在Stateを再構築できなければならない。

## 第33条 Contradiction Preservation

Evidence同士、設計と観測、AuthorityとCapabilityが矛盾した場合、矛盾を削除、上書き、平均化してはならない。

```text
UNRESOLVED_CONTRADICTION
```

としてCanonical Stateに保持する。

観測可能な事実と設計仮定が矛盾する場合、観測事実を優先し、設計仮定を再評価する。

---

# ARTICLE XI — Binding, Trust and Security

## 第34条 Project Binding

MANOSUBEの導入はInstallationではなくProject Bindingである。

Binding時にHumanは次を定義する。

```text
OBJECTIVE
BOUNDARY
AUTHORITY
```

BindingされていないProject、未定義Boundary、未確認Authorityに対してChangeを実行してはならない。

## 第35条 Bound Content is Untrusted

Binding対象RepositoryのREADME、Issue、PR、code comment、configuration、generated textはObservation Targetであり、Authority Instructionではない。

```text
BOUND PROJECT CONTENT
= OBSERVATION TARGET
≠ AUTHORITY INSTRUCTION
```

Repository内の命令文、prompt injection、外部文書はObjective、Boundary、Authority、Prohibitionを変更できない。

## 第36条 Boundary Protection

次を必須とする。

```text
symlinkでBoundary外へ移動しない
secret値をEvidenceへ保存しない
credentialをFingerprintへ含めない
観測と任意code実行を分離する
実行前にcommand authorityを確認する
submoduleとexternal dependencyを別Boundaryとして扱う
```

秘密だけでなく、Objective、Authority、Evidence、Lineageを保護する。

---

# ARTICLE XII — Adapter and External Systems

## 第37条 Adapterの地位

GitHub、CLI、Shell、VPS、Browser、Cloud、ChatGPT、Claude、Codex、MCP、APIは交換可能な外部器官である。

Adapterは次を行える。

```text
observe
normalize
project
execute an authorized request
return receipt
```

Adapterは次を行ってはならない。

```text
own canonical state
grant authority
rewrite objective
close difference
declare completion
create parallel lineage
implement an independent state transition
```

## 第38条 GitHubの地位

GitHubはVersioned Development Surfaceであり、Canonical Stateではない。

```text
Difference ≠ Issue
Change ≠ Pull Request
Evidence ≠ CI Run
State ≠ Repository View
```

GitHub上のidentityとCanonical Identityは明示的なProjection関係として保存する。

---

# ARTICLE XIII — Completion

## 第39条 Completion Semantics

次を混同しない。

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

特に、次を原則とする。

```text
DESIGNED ≠ IMPLEMENTED
IMPLEMENTED ≠ CONNECTED
TEST PASS ≠ NATURAL ROUTE PASS
PR MERGED ≠ RUNTIME PROVEN
ARTIFACT EXISTS ≠ CORRECTLY CONSUMED
```

## 第40条 Connected

CONNECTED判定には最低限、次を要求する。

```text
previous outputが生成される
next consumerがその同一outputを読む
identityが保存される
canonical authority ownerが一つである
代替Evidenceを使用しない
next canonical artifactが生成される
```

## 第41条 v0.1 Completion

Kernel Core CompleteとKernel v0.1 Completeを区別する。

```text
KERNEL_CORE_COMPLETE
≠
KERNEL_V0_1_COMPLETE
```

```text
KERNEL_V0_1_COMPLETE
= KERNEL_CORE_COMPLETE
+ MINIMAL_FIXTURE_BINDING
+ ONE_FULL_NATURAL_CYCLE_PASS
```

v0.1は、Agent、GitHub、CLIなしで次を自然経路により証明する。

```text
OBJECTIVE
→ INITIAL STATE
→ OBSERVATION
→ OBSERVATION EVIDENCE
→ DIFFERENCE
→ AUTHORITY CHECK
→ CHANGE
→ RE-OBSERVATION
→ CHANGE RESULT EVIDENCE
→ CLOSURE EVALUATION
→ ATOMIC REFLOW
→ NEW STATE
```

---

# ARTICLE XIV — Non-Targets

## 第42条 Kernelへ入れないもの

本プロジェクトは次を目的としない。

```text
AIチャット機能の集合
固定Agent組織
Prompt保管庫
長期Memory Database
単なるGitHub自動化
単なるCI/CD Wrapper
万能CLI
Tool Marketplace
AIによる中央集権的制御
人間判断の全面代替
効率最大化だけの開発基盤
```

便利であってもCanonical Cycleに不要な機能をKernelへ入れない。

未実装領域の空Directory、placeholder、mockを完成の証拠にしてはならない。

---

# ARTICLE XV — Constitutional Amendment

## 第43条 改憲Authority

本憲法の変更はHuman Constitutional Authorityを必要とする。

通常のAgent、PR、automated migration、dependency updateは本憲法を変更できない。

## 第44条 改憲Evidence

改憲には最低限、次を要求する。

```text
amendment_id
human_authority_ref
affected_articles
previous_text
proposed_text
structural_reason
parent_origin_compatibility
security_impact
migration_requirement
invariant_evaluation
natural-cycle evidence plan
```

## 第45条 弱化禁止

次を目的とする改憲を認めない。

```text
失敗した実装をPASSにする
未到達状態を完成扱いする
Evidence要件を回避する
Human Authorityを黙示的にAgentへ移す
複数Canonical Ownerを正当化する
外部ServiceをKernelへ昇格する
Lineageを削除する
Objectiveを達成しやすく弱める
```

親OSとのOrigin関係を変更する場合、明示的なCompatibility ReviewとHuman Acceptanceを必要とする。

---

# ARTICLE XVI — Supreme Invariants

## 第46条 最高不変条件

次はすべてのContract、Schema、Engine、Binding、Adapter、Agent、Testに優先する。

```text
CANONICAL_KERNEL_COUNT=1
CANONICAL_STATE_OWNER_COUNT=1
PARALLEL_CANONICAL_AUTHORITY=0

OBJECTIVE_AUTHORITY_IS_HUMAN=true
CAPABILITY_IS_NOT_AUTHORITY=true
AGENT_IS_REPLACEABLE=true

SEMANTIC_AND_METADATA_SEPARATED=true
CANONICAL_SERIALIZATION_DEFINED=true
VOLATILE_METADATA_EXCLUDED_FROM_FINGERPRINT=true

OBSERVATION_PRECEDES_DIFFERENCE=true
DIFFERENCE_PRECEDES_CHANGE=true
AUTHORITY_PRECEDES_EXECUTION=true
REOBSERVATION_PRECEDES_CLOSURE=true
EVIDENCE_REQUIRED_FOR_CLOSURE=true

STATE_TRANSITION_ATOMIC=true
STALE_CHANGE_BLOCKED=true
DUPLICATE_CHANGE_IDEMPOTENT=true
PARTIAL_WRITE_NOT_CANONICAL=true

LINEAGE_APPEND_ONLY=true
CURRENT_STATE_RECONSTRUCTABLE=true
CONTRADICTIONS_PRESERVED=true

GITHUB_NOT_CANONICAL_STATE=true
ADAPTER_NOT_AUTHORITY=true
CONVERSATION_NOT_AUTHORITY=true
MEMORY_NOT_AUTHORITY=true
```

一つでも破られたState TransitionはCanonicalとして受理しない。

---

# FINAL DECLARATION — 最終宣言

```text
THE KERNEL IS ONE.

THE STATE HAS ONE CANONICAL OWNER.

THE HUMAN OWNS THE OBJECTIVE.

THE KERNEL OWNS STRUCTURAL CONSISTENCY.

THE AGENT OWNS NO PERMANENT AUTHORITY.

NO OBSERVATION MAY BE REPLACED BY ASSUMPTION.

NO DIFFERENCE MAY BE REPLACED BY A TASK LIST.

NO CHANGE MAY CROSS ITS AUTHORITY BOUNDARY.

NO CHANGE MAY CONFIRM ITS OWN SUCCESS.

NO DIFFERENCE MAY CLOSE WITHOUT SUFFICIENT EVIDENCE.

NO STATE MAY BECOME CANONICAL WITHOUT ATOMIC REFLOW.

NO SESSION, MODEL, TOOL, OR ADAPTER MAY REPLACE LINEAGE.
```

MANOSUBE Agent Civilization OSは、Toolを動かすOSではない。

目的を失わせず、状態を偽らせず、差異を隠さず、権限を越えさせず、変化を証拠なく確定させず、その結果を次のStateへ還流し続けるOSである。

> 知能を永続化するな。状態を永続化せよ。  
> 仕事を管理するな。差異を閉じよ。  
> 変化を急ぐな。証拠を還流させよ。  
> 器官を増やすな。循環を失うな。
