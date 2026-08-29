\# MANOSUBE Agent Civilization OS



\## Canonical Kernel Index



```text

DOC\_TYPE=KERNEL\_INDEX

SYSTEM=MANOSUBE\_AGENT\_CIVILIZATION\_OS

DOCUMENT\_ID=KERNEL-INDEX-0001

SCHEMA\_VERSION=0.1

STATUS=CANONICAL\_DESIGN

PARENT\_OS=manosube/manosube-civilization-os

PARENT\_BASELINE\_COMMIT=0de548c9e4aa3a94fca2df07ccc710577f1534ff

CANONICAL\_KERNEL\_COUNT=1

CANONICAL\_STATE\_OWNER\_COUNT=1

PARALLEL\_CANONICAL\_AUTHORITY=0

```



\---



\# 0. この文書の地位



`KERNEL\_INDEX.md`は、MANOSUBE Agent Civilization OSのCanonical Kernelを読み始めるための唯一の入口である。



これは単なる目次ではない。



本書は、次を固定する。



```text

Kernelに属するもの

Kernelに属さないもの

8要素の意味

8要素の依存順

各Contractの読込順

Human・Kernel・Agentのauthority境界

Canonical Stateとの関係

v0.1の実装境界

Kernel完成の判定条件

```



本書はKernelの実装そのものではなく、Kernelを誤って分割・拡張・置換しないための構造索引である。



```text

DOCUMENT\_EXISTS

≠

KERNEL\_IMPLEMENTED



KERNEL\_IMPLEMENTED

≠

KERNEL\_CONNECTED



TEST\_PASS

≠

NATURAL\_CYCLE\_PASS

```



本書の存在だけを、実装・接続・完成の証拠として扱ってはならない。



\---



\# 1. Kernelの定義



MANOSUBE Agent Civilization Kernelとは、



> 人間が定めた目的・境界・権限を保持し、開発対象の現在状態を観測し、目的状態との差異を導出し、許可された変化だけを通し、その結果を証拠として次の状態へ還流させる、単一の状態遷移核である。



Kernelの本体は、次の一循環だけである。



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



この循環を短縮、分岐、複製してはならない。



```text

CANONICAL\_KERNEL\_COUNT=1

```



入口、接続先、AI、Agent、Tool、Repository、Runtimeが増えても、Canonical Kernelは増えない。



\---



\# 2. 継承する文明原理



本Kernelは、親であるMANOSUBE Civilization OSの次の原理を、開発世界へ写像する。



```text

文明は状態である

状態は循環する

循環が止まると崩壊する

崩壊は固定化から始まる

観測により循環は修復される

```



開発世界における写像は次のとおりである。



| 文明OS | Agent Civilization OS                    |

| ---- | ---------------------------------------- |

| 位置   | Current Project State                    |

| 流動   | 情報・依存・実行の流れ                              |

| 周期   | Observation → Change → Evidence → Reflow |

| 固定   | 未解決のStructural Difference                |

| 循環   | Objectiveへ向かうState Transition            |

| 還流   | Evidenceによる次Stateの更新                     |



派生Kernelは親OSを複製しない。



```text

PARENT\_OS

= CONSTITUTIONAL\_ORIGIN



PARENT\_OS

≠ RUNTIME\_DEPENDENCY

≠ PACKAGE\_DEPENDENCY

≠ SECOND\_KERNEL

```



親の原理を継承し、開発世界に必要な状態契約だけを派生させる。



\---



\# 3. Kernelの中心



Kernelの中心は、次のいずれでもない。



```text

Agent

Task

Issue

Pull Request

Commit

Tool

Conversation

Prompt

Memory

GitHub

CLI

VPS

Cloud

```



唯一の中心は、



```text

PROJECT STATE

```



である。



AI、Agent、モデル、セッション、実行環境が停止・交換・消失しても、Canonical State、Evidence、Lineageから作業を再構成できなければならない。



> 知能を永続化するな。状態を永続化せよ。

> 仕事を管理するな。差異を閉じよ。



\---



\# 4. Kernelを構成する8要素



\## 4.1 OBJECTIVE



OBJECTIVEは、Projectが到達すべき目的状態を定義する。



HumanがObjective Authorityを持つ。



KernelやAgentは、Objectiveを独自に生成、変更、縮小、弱化してはならない。



OBJECTIVEは抽象的な成功語ではなく、観測可能なTarget Predicateの集合として表現する。



```text

OBJECTIVE

=

STATEMENT

\+ TARGET PREDICATES

\+ COMPLETION POLICY

\+ HUMAN AUTHORITY

\+ REVISION LINEAGE

```



参照：



```text

01\_OBJECTIVE/

├── OBJECTIVE\_CONTRACT.md

├── OBJECTIVE\_AUTHORITY.md

└── OBJECTIVE\_REVISION.md

```



\---



\## 4.2 STATE



STATEは、Projectの現在位置を表す唯一のCanonical Viewである。



STATEは会話要約でも、作業報告でも、GitHub上のIssue集合でもない。



```text

STATE

=

SEMANTIC STATE

\+ METADATA

\+ EVIDENCE REFERENCES

\+ REVISION

\+ SEMANTIC FINGERPRINT

```



Semantic Fingerprintは、正規化されたSemantic Stateだけから決定的に生成する。



次をFingerprintへ含めてはならない。



```text

observed\_at

observer

Agent名

session ID

temporary path

serialization order

volatile log

credential

secret

```



参照：



```text

02\_STATE/

├── STATE\_CONTRACT.md

├── SEMANTIC\_STATE.md

├── STATE\_METADATA.md

├── CANONICAL\_SERIALIZATION.md

└── STATE\_FINGERPRINT.md

```



\---



\## 4.3 OBSERVATION



OBSERVATIONは、外界をKernelが評価可能なNormalized Factへ変換する。



Observationは事実の観測であり、完成判定でも変更権限でもない。



```text

OBSERVATION

=

TARGET

\+ SCOPE

\+ METHOD

\+ TIME BOUNDARY

\+ NORMALIZED FACTS

\+ BLIND SPOTS

\+ OBSERVATION EVIDENCE

```



観測できなかった対象をPASSとしてはならない。



```text

UNKNOWN

UNOBSERVED

BLOCKED

INCOMPLETE

```



を観測結果として保持する。



Negative Observationは、単なる検索失敗と区別しなければならない。



```text

NO\_RESULT

≠

PROVEN\_ABSENCE

```



参照：



```text

03\_OBSERVATION/

├── OBSERVATION\_CONTRACT.md

├── NORMALIZED\_FACT.md

├── OBSERVATION\_SCOPE.md

└── NEGATIVE\_OBSERVATION.md

```



\---



\## 4.4 DIFFERENCE



DIFFERENCEは、Target StateとObserved Stateの間に存在する構造的不一致である。



Task、Issue、PRより上位のCanonical Work Identityとして扱う。



```text

DIFFERENCE

=

DIFFERENCE\_ID

\+ TARGET STATE

\+ OBSERVED STATE

\+ STRUCTURAL DIFFERENCE

\+ IMPACT

\+ EVIDENCE REFERENCES

\+ AUTHORITY REQUIRED

\+ CLOSURE POLICY

```



Issue、branch、commit、PR、test、deploymentは、Differenceを閉じるための外部表現またはWork Unitである。



```text

DIFFERENCE

→ WORK UNITS

→ CHANGES

→ RE-OBSERVATION

→ EVIDENCE

→ CLOSURE EVALUATION

```



Changeが成功を報告しても、Differenceは自動的に閉じない。



参照：



```text

04\_DIFFERENCE/

├── DIFFERENCE\_CONTRACT.md

├── DIFFERENCE\_IDENTITY.md

├── DIFFERENCE\_LIFECYCLE.md

└── CLOSURE\_POLICY.md

```



\---



\## 4.5 AUTHORITY



AUTHORITYは、誰に実行能力があるかではなく、どのChangeが許可されているかを定義する。



```text

CAPABILITY

≠

AUTHORITY

```



Authorityは三層に分離する。



```text

HUMAN

= OBJECTIVE AUTHORITY

\+ CONSTITUTIONAL AUTHORITY

\+ IRREVERSIBLE RISK AUTHORITY



MANOSUBE KERNEL

= STRUCTURAL AUTHORITY

\+ AUTHORITY EVALUATION

\+ STATE TRANSITION ENFORCEMENT



AI AGENT

= EXECUTION CAPABILITY

```



Human Approvalは、抽象的な許可として保存してはならない。



承認は次へ正確に結合する。



```text

APPROVAL

→ EXACT CHANGE

→ EXACT ACTION FINGERPRINT

→ EXACT STATE FINGERPRINT

→ EXACT SCOPE

→ EXPIRY

```



対象State、Change内容、Scope、期限が変わった承認は無効である。



参照：



```text

05\_AUTHORITY/

├── AUTHORITY\_CONTRACT.md

├── AUTHORITY\_LEVELS.md

├── CAPABILITY\_AUTHORITY\_SEPARATION.md

├── APPROVAL\_CONTRACT.md

└── PROHIBITION\_CONTRACT.md

```



\---



\## 4.6 CHANGE



CHANGEは、一つ以上のDifferenceを閉じるために提案・許可・実行される、境界付きの状態変更である。



Changeは自分自身の成功や、DifferenceのClosureを確定できない。



```text

CHANGE STATUS

=

PROPOSED

AUTHORIZED

RUNNING

EXECUTED

FAILED

REJECTED

STALE

```



`COMPLETED`および`CLOSED`は、Change自身のstatusとして使用しない。



Changeは最低限、次を保持する。



```text

change\_id

difference\_id

before\_state\_fingerprint

expected\_state\_revision

authority\_ref

action

idempotency\_key

execution\_result

status

```



更新はCompare-And-Swapにより保護する。



```text

CURRENT REVISION

=

EXPECTED REVISION

→ COMMIT MAY PROCEED



CURRENT REVISION

≠

EXPECTED REVISION

→ STALE CHANGE

```



参照：



```text

06\_CHANGE/

├── CHANGE\_CONTRACT.md

├── CHANGE\_LIFECYCLE.md

├── IDEMPOTENCY\_CONTRACT.md

└── STALE\_CHANGE\_POLICY.md

```



\---



\## 4.7 EVIDENCE



EVIDENCEは、Observation、Change Result、Closure Claimを支える不変の検証記録である。



Evidenceは二つの生成位置を持つ。



```text

OBSERVATION EVIDENCE

= before stateとDifferenceを支える



CHANGE RESULT EVIDENCE

= Change後の再観測結果を支える

```



Negative Evidenceは、観測範囲、観測期間、方法、試行回数、完了性、既知の死角を持たなければならない。



Evidence強度：



```text

E0 = 宣言

E1 = 静的確認

E2 = 単体テスト

E3 = 統合テスト

E4 = 自然経路実行

E5 = 対象Runtime実証

E6 = 反復・独立Runtime実証

```



高リスクClaimを弱いEvidenceで確定してはならない。



参照：



```text

07\_EVIDENCE/

├── EVIDENCE\_CONTRACT.md

├── OBSERVATION\_EVIDENCE.md

├── CHANGE\_RESULT\_EVIDENCE.md

├── NEGATIVE\_EVIDENCE.md

├── EVIDENCE\_LEVELS.md

└── EVIDENCE\_SUFFICIENCY.md

```



\---



\## 4.8 REFLOW



REFLOWは、Evidenceを保存するだけの終端処理ではない。



Evidenceを評価し、次のCanonical Stateを原子的に確定し、次周期へ接続するState Transitionである。



```text

REFLOW

=

EVIDENCE EVALUATION

\+ CLOSURE EVALUATION

\+ ATOMIC STATE TRANSITION

\+ LINEAGE APPEND

\+ MATERIALIZED STATE UPDATE

\+ NEXT OBSERVATION DERIVATION

```



LINEAGEは第9のKernel要素ではない。



```text

LINEAGE

=

REFLOWによって保存される

STATE TRANSITIONの不変記録

```



失敗、EMPTY、BLOCKED、STALE、未到達も正式なEvidenceとして還流する。



参照：



```text

08\_REFLOW/

├── REFLOW\_CONTRACT.md

├── STATE\_TRANSITION.md

├── LINEAGE\_INVARIANT.md

├── ATOMIC\_COMMIT.md

└── RECOVERY\_CONTRACT.md

```



\---



\# 5. Canonical Cycleの厳密な実行順



概念上のKernelは8要素である。



実行上は、Evidenceの生成位置と再観測を明示するため、次の順序を使用する。



```text

HUMAN OBJECTIVE / BOUNDARY / AUTHORITY

↓

CURRENT STATE RESTORATION

↓

OBSERVATION

↓

OBSERVATION EVIDENCE

↓

STRUCTURAL DIFFERENCE

↓

AUTHORITY EVALUATION

↓

AUTHORIZED CHANGE

↓

EXECUTION RESULT

↓

RE-OBSERVATION

↓

CHANGE RESULT EVIDENCE

↓

EVIDENCE SUFFICIENCY EVALUATION

↓

DIFFERENCE CLOSURE EVALUATION

↓

ATOMIC REFLOW

↓

LINEAGE APPEND

↓

NEW CANONICAL STATE

↓

NEXT OBSERVATION

```



この順序を飛び越えてはならない。



特に、次を禁止する。



```text

CHANGE → CLOSED

TEST PASS → OBJECTIVE COMPLETE

PR MERGED → RUNTIME PROVEN

ARTIFACT EXISTS → CONNECTED

AGENT REPORTS SUCCESS → AFTER STATE CONFIRMED

```



\---



\# 6. Kernel文書の読込順



\## 6.1 最小読込



Kernelの意味を把握する場合は、次の順序で読む。



```text

1\. KERNEL\_INDEX.md

2\. KERNEL\_CONSTITUTION.md

3\. KERNEL\_INVARIANTS.md

4\. COMPLETION\_SEMANTICS.md

```



\## 6.2 完全読込



設計、実装、検証、変更を行う場合は、次の順序で読む。



```text

1\. KERNEL\_INDEX.md

2\. KERNEL\_CONSTITUTION.md

3\. KERNEL\_INVARIANTS.md

4\. COMPLETION\_SEMANTICS.md



5\. 01\_OBJECTIVE/

6\. 02\_STATE/

7\. 03\_OBSERVATION/

8\. 04\_DIFFERENCE/

9\. 05\_AUTHORITY/

10\. 06\_CHANGE/

11\. 07\_EVIDENCE/

12\. 08\_REFLOW/

```



後段のContractは前段の意味を上書きできない。



```text

REFLOW cannot redefine EVIDENCE

EVIDENCE cannot grant AUTHORITY

CHANGE cannot redefine DIFFERENCE

DIFFERENCE cannot alter OBJECTIVE

AGENT cannot alter KERNEL CONSTITUTION

```



\---



\# 7. Kernelと三世界の境界



MANOSUBE Agent Civilization OSは、次の三世界を分離する。



```text

I. KERNEL SOURCE WORLD

&#x20;  Constitution

&#x20;  Contract

&#x20;  Schema

&#x20;  Deterministic Engine

&#x20;  Verification Source



II. CANONICAL STATE WORLD

&#x20;   Objective Revisions

&#x20;   Current State

&#x20;   Transition Events

&#x20;   Observations

&#x20;   Differences

&#x20;   Changes

&#x20;   Evidence

&#x20;   Approvals

&#x20;   Lineage



III. ADAPTER WORLD

&#x20;    GitHub

&#x20;    CLI

&#x20;    Shell

&#x20;    VPS

&#x20;    Browser

&#x20;    Cloud

&#x20;    ChatGPT

&#x20;    Claude

&#x20;    Codex

```



RepositoryはKernel Sourceを保存する。



Canonical StateはRepository source treeの内部へ保存しない。



Adapterは外界との入出力を担うが、Kernelの意味論、Authority、Closure、State Transitionを独自実装してはならない。



```text

ADAPTER MAY:

observe

normalize

project

execute authorized request

return receipt



ADAPTER MUST NOT:

own canonical state

grant authority

close difference

rewrite objective

declare completion

create parallel lineage

```



\---



\# 8. Canonical Stateの保存原則



Canonical State Backendは、Git管理外または明示された外部State Backendへ保存する。



最低構造：



```text

projects/<project\_id>/

├── binding/

├── objective/

├── state/

├── events/

├── observations/

├── differences/

├── changes/

├── evidence/

├── approvals/

├── projections/

├── locks/

└── quarantine/

```



Authorityは次のように分離する。



```text

events/transitions.jsonl

= append-only canonical lineage



state/current.json

= lineageから導出されたmaterialized view



evidence/

= immutable evidence records



quarantine/

= schema不正、部分書込、identity不整合の隔離

```



`current.json`だけを唯一の復元源にしてはならない。



部分書込、schema不正、fingerprint不一致、revision不整合をCanonical Stateとして採用してはならない。



\---



\# 9. Single Authority Rule



同一のCanonical StateまたはState Transitionに複数ownerを作らない。



```text

OWNER\_COUNT=1

PARALLEL\_CANONICAL\_AUTHORITY=0

```



新しいownerを作る前に、既存のCanonical Ownerを探索する。



既存ownerが切断されている場合は、代替ownerを追加するのではなく、原則としてCanonical Routeを再接続する。



次を第二authorityにしてはならない。



```text

GitHub Issue

Pull Request

CI Result

Adapter

CLI

Agent

Conversation

Memory

Test Fixture

Fallback Artifact

Generated Report

```



\---



\# 10. Kernel Invariants



Kernelは、少なくとも次を常に満たさなければならない。



```text

CANONICAL\_KERNEL\_COUNT=1

CANONICAL\_STATE\_OWNER\_COUNT=1

PARALLEL\_CANONICAL\_AUTHORITY=0



OBJECTIVE\_AUTHORITY\_IS\_HUMAN=true

CAPABILITY\_IS\_NOT\_AUTHORITY=true

AGENT\_IS\_REPLACEABLE=true



SEMANTIC\_AND\_METADATA\_SEPARATED=true

FINGERPRINT\_EXCLUDES\_VOLATILE\_FIELDS=true

CANONICAL\_SERIALIZATION\_DEFINED=true

STATE\_REVISIONED=true



STATE\_TRANSITION\_ATOMIC=true

STALE\_CHANGE\_BLOCKED=true

DUPLICATE\_CHANGE\_IDEMPOTENT=true

PARTIAL\_WRITE\_NOT\_CANONICAL=true

CRASH\_RECOVERY\_POSSIBLE=true



OBSERVATION\_EVIDENCE\_REQUIRED=true

CHANGE\_RESULT\_EVIDENCE\_REQUIRED=true

NEGATIVE\_EVIDENCE\_BOUNDED=true

CHANGE\_CANNOT\_SELF\_CLOSE=true



LINEAGE\_APPEND\_ONLY=true

CURRENT\_STATE\_RECONSTRUCTABLE=true

GITHUB\_NOT\_CANONICAL\_STATE=true

ADAPTER\_NOT\_AUTHORITY=true

```



一つでも破られた場合、そのState TransitionはCanonicalとして受理しない。



\---



\# 11. v0.1におけるKernel境界



v0.1では、Agent、GitHub、CLI、VPSを必要とせず、Minimal Fixture Binding上でCanonical Cycleを一周させる。



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



v0.1に含むもの：



```text

Kernel Constitution

Objective Contract

Versioned State Schema

Canonical Serialization

Semantic Fingerprint

Observation Contract

Difference Identity

Authority Evaluation

Change Lifecycle

Evidence Sufficiency

Atomic State Store

Compare-And-Swap

Idempotency

Crash Recovery

Minimal Fixture Binding

One Full Natural Cycle Test

```



v0.1に含めないもの：



```text

User-facing CLI

GitHub Adapter

GitHub Issue Projection

Runtime Adapter

VPS Operation

ChatGPT Agent Runtime

Claude Agent Runtime

Codex Agent Runtime

Autonomous Change

Dynamic Multi-Agent

Web Application

Production Deployment

```



未実装領域のdirectoryやplaceholderを作成し、完成済みに見せてはならない。



\---



\# 12. Kernel v0.1 Completion Gate



Kernel Coreの完成と、Kernel v0.1の完成を区別する。



```text

KERNEL\_CORE\_COMPLETE

≠

KERNEL\_V0\_1\_COMPLETE

```



正式なv0.1完成条件：



```text

KERNEL\_V0\_1\_COMPLETE

=

KERNEL\_CORE\_COMPLETE

\+ MINIMAL\_FIXTURE\_BINDING

\+ ONE\_FULL\_NATURAL\_CYCLE\_PASS

```



Acceptance Gate：



```text

CANONICAL\_KERNEL\_COUNT=1

CANONICAL\_STATE\_OWNER\_COUNT=1

PARALLEL\_CANONICAL\_AUTHORITY=0



STATE\_SERIALIZABLE=true

STATE\_RELOADABLE=true

STATE\_DETERMINISTIC=true

STATE\_REVISIONED=true

SEMANTIC\_FINGERPRINT\_STABLE=true

VOLATILE\_METADATA\_EXCLUDED=true

SCHEMA\_VERSIONED=true



ATOMIC\_COMMIT\_PROVEN=true

STALE\_UPDATE\_BLOCKED=true

DUPLICATE\_CHANGE\_IDEMPOTENT=true

PARTIAL\_WRITE\_NOT\_CANONICAL=true

CRASH\_RECOVERY\_PROVEN=true



OBJECTIVE\_AUTHORITY\_ENFORCED=true

PROHIBITED\_CHANGE\_BLOCKED=true

STALE\_APPROVAL\_REJECTED=true

CHANGE\_CANNOT\_SELF\_CLOSE=true



OBSERVATION\_EVIDENCE\_PROVEN=true

CHANGE\_RESULT\_EVIDENCE\_PROVEN=true

NEGATIVE\_EVIDENCE\_BOUNDED=true

EVIDENCE\_REQUIRED\_FOR\_CLOSE=true



LINEAGE\_APPEND\_ONLY=true

STATE\_RECONSTRUCTABLE=true

SESSION\_INDEPENDENT=true

AGENT\_INDEPENDENT=true



ONE\_FULL\_NATURAL\_CYCLE\_PASS=true

UNRESOLVED\_KERNEL\_CONTRADICTIONS=0

```



設計文書、mock、単体テスト、ファイルの存在だけでは、このGateを通過できない。



\---



\# 13. Kernelを変更する場合



Kernel文書またはKernel semanticsを変更する場合、通常の機能変更より強いEvidenceを要求する。



最低限、次を明示する。



```text

CHANGE\_ID

AFFECTED\_KERNEL\_ELEMENT

PREVIOUS\_CONTRACT

PROPOSED\_CONTRACT

STRUCTURAL\_REASON

AUTHORITY\_USED

COMPATIBILITY IMPACT

MIGRATION REQUIREMENT

INVARIANT EVALUATION

AFTER-STATE EVIDENCE

```



次はHuman Constitutional Authorityを必要とする。



```text

Canonical Cycleの変更

Kernel要素の追加・削除

Human Authorityの縮小

Single Authority Ruleの変更

Evidence Sufficiencyの弱化

Completion Gateの弱化

Parent Originの変更

Security Constitutionの変更

```



失敗した実装へ合わせるために、Kernel Contract、Objective、Closure Policy、Evidence基準を弱めてはならない。



\---



\# 14. Kernelの完成とは何か



Kernelの完成とは、文書が揃うことでも、コードが存在することでもない。



次が同一Kernel上で自然に接続されることである。



```text

Human defines Objective / Boundary / Authority

↓

Project is bound

↓

Current State is restored

↓

World is observed

↓

Observation Evidence is preserved

↓

Structural Difference is derived

↓

Authority is evaluated

↓

Only Authorized Change is executed

↓

After State is independently observed

↓

Change Result Evidence is evaluated

↓

Difference is closed, retained, or blocked

↓

State Transition is atomically committed

↓

Lineage is preserved

↓

Updated State produces the next cycle

```



最終的なKernel判定は、次で固定する。



```text

DESIGN\_COMPLETE

≠

IMPLEMENTATION\_COMPLETE



IMPLEMENTATION\_COMPLETE

≠

NATURAL\_ROUTE\_COMPLETE



NATURAL\_ROUTE\_COMPLETE

≠

OBJECTIVE\_COMPLETE

```



Kernelは、AIに仕事をさせるための装置ではない。



Kernelは、



> 目的を失わせず、状態を偽らせず、権限を越えさせず、変化を証拠なく確定させず、未解決の差異を次の状態へ正しく還流させるための構造である。



\---



\# 15. Final Canonical Declaration



```text

THE KERNEL IS ONE.



THE STATE HAS ONE CANONICAL OWNER.



THE HUMAN OWNS THE OBJECTIVE.



THE KERNEL OWNS STRUCTURAL CONSISTENCY.



THE AGENT OWNS NO PERMANENT AUTHORITY.



NO CHANGE IS COMPLETE WITHOUT RE-OBSERVATION.



NO DIFFERENCE IS CLOSED WITHOUT SUFFICIENT EVIDENCE.



NO STATE IS CANONICAL WITHOUT ATOMIC REFLOW.



NO SESSION, MODEL, TOOL, OR ADAPTER MAY REPLACE LINEAGE.



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



> 知能を永続化するな。状態を永続化せよ。

> 仕事を管理するな。差異を閉じよ。

> 変化を急ぐな。証拠を還流させよ。

> 器官を増やすな。循環を失うな。



