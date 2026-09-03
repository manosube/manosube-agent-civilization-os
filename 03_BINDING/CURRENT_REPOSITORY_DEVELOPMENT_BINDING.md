# MANOSUBE Agent Civilization OS

## Current-Repository Development Binding v0.2

```text
DOC_TYPE=REPOSITORY_BINDING
BINDING_SCOPE=CURRENT_REPOSITORY_DEVELOPMENT_OPERATION
DOCUMENT_ID=DEV-BINDING-0001
DECISION_ID=HUMAN-DECISION-CURRENT-REPOSITORY-OPERATING-BINDING-0002
SUPERSEDES=HUMAN-DECISION-CURRENT-REPOSITORY-OPERATING-BINDING-0001
DECISION_STATUS=RATIFIED
DECISION_AUTHORITY=SHUKOU
KERNEL_ELEMENT=none
SCHEMA_VERSION=0.2
STATUS=CANONICAL_DESIGN
```

---

# 0. Binding Position

このBindingは、`manosube/manosube-agent-civilization-os`を**構築する**四者を選択する。Kernelが何であるかは述べない。

```text
CHATGPT     = STRUCTURAL_ADVISOR AND STRUCTURAL REVIEWER
CLAUDE_CODE = IMPLEMENTATION_EXECUTOR
GITHUB      = HUMAN_INTENT_AND_WORK_STATE_SURFACE
SHUKOU      = FINAL ACCEPTANCE AND MERGE OPERATION AUTHORITY
```

`KERNEL_VERTICAL_WORK_UNIT_DELIVERY.md` §6は、observation／acceptance capabilityとexecution capabilityを**provider中立に**定義し、「いかなる名前付きprovider、API、version-control product、model、Agentもprotocol適合には不要である」と述べる。その中立性は正しく、維持される。

しかしcapabilityを定義することは、**このrepositoryで誰がそれを実装するかを選択すること**ではない。§6は選択を`Structural Advisor`へ委ねたが、その選択を記録する場所を持たなかった。

```text
CAPABILITY DEFINED       ≠ IMPLEMENTER SELECTED
IMPLEMENTER UNSELECTED   → ANY IMPLEMENTER MAY BE SUBSTITUTED
ANY IMPLEMENTER          → AN AUTOMATED REVIEWER ON THE CRITICAL PATH
```

この文書がその選択である。

# 1. What This Binding Is Not

```text
KERNEL_ELEMENT=none
```

このBindingはKernelの器官ではない。kernel loopに現れず、`RECORD_TYPES`に現れず、canonical schema registry（`01_SCHEMA/`）に現れない。**それはconformance testで証明され、ここで主張されるのではない。**

```text
UNIVERSAL_KERNEL_PROVIDER_NEUTRALITY_PRESERVED=true
FUTURE_AGENT_REPLACEABILITY_PRESERVED=true
CHATGPT_IS_A_KERNEL_ORGAN=false
CLAUDE_CODE_IS_A_KERNEL_ORGAN=false
GITHUB_IS_CANONICAL_KERNEL_STATE=false
```

policy artifactが`01_SCHEMA/`ではなく`03_BINDING/`にあるのは、この理由による。canonical schema registryへ登録すれば、名前付きproviderがKernel semanticsの一部になる。

# 2. Role Separation

```text
CHATGPT
= STRUCTURAL OBSERVATION
+ CURRENT/TARGET STATE
+ STRUCTURAL DIFFERENCE
+ ROADMAP
+ IMPLEMENTATION HANDOFF
+ STRUCTURAL REVIEW
+ MERGE READINESS RECOMMENDATION
− CODE AUTHORSHIP
− FINAL ACCEPTANCE DECISION
− MERGE OPERATION
− EXTERNAL FINDING ADOPTION

CLAUDE CODE
= IMPLEMENTATION
+ TEST EXECUTION
+ EXECUTOR SELF-REVIEW
+ PR PREPARATION
− STRUCTURAL AUTHORITY
− STRUCTURAL REVIEW
− MERGE READINESS RECOMMENDATION
− FINAL ACCEPTANCE DECISION
− MERGE OPERATION
− EXTERNAL FINDING ADOPTION
− AUTOMATED EXTERNAL REVIEW REQUEST

GITHUB
= HUMAN INTENT RECORD
+ WORK STATE SURFACE
+ COMMIT / PR / EVIDENCE RECEIPT SURFACE
− CANONICAL KERNEL STATE
− AUTHORITY
− STRUCTURAL REVIEW
− MERGE READINESS RECOMMENDATION
− FINAL ACCEPTANCE DECISION
− MERGE OPERATION
− COMPLETION

SHUKOU
= FINDING ADOPTION OR REJECTION
+ FINAL ACCEPTANCE DECISION
+ MERGE OPERATION
```

## 2.1 三つを一語にしない

Decision 0001は`MERGE_DECISION`という一語で三つを覆っていた。Decision 0002はそれを分ける。

```text
MERGE_READINESS_RECOMMENDATION   owner=CHATGPT
FINAL_ACCEPTANCE_DECISION        owner=SHUKOU
MERGE_OPERATION                  owner=SHUKOU
```

構造参謀は「マージしてよく**見える**」と言える。「マージしてよい」と決めるのも、実際にマージするのも、Humanである。一語で三つを指す語彙は、推薦と権限を区別**できない**語彙であり、区別できないものは混同されたときに誰にも見えない。

`may`に名前が無い行為は、禁止一覧に無くても許可されない。**沈黙は許可ではない**——Authorityが未規定のactionに対して適用する規律（`AUTHORITY_CONTRACT.md` §1）と同じものである。

## 2.2 surfaceはsubjectではない

```text
OBSERVATION SURFACE = repository内容へどう到達するか
OBSERVATION SUBJECT = 誰がそれを検査し、結論を出すか

SURFACE != SUBJECT
SURFACE != ACCEPTANCE
```

GitHub APIは**観測手段**である。検査主体でも受入主体でもない。

```text
CHATGPT = GitHub APIを用いて構造観測・構造検査を行う主体
GITHUB  = 意思・作業・Evidence・receiptのsurface
SHUKOU  = 最終受入とマージ操作の主体
```

surfaceをsubjectとして読むことが、受入境界が失われる経路である。「そのsurfaceがacceptance capabilityを実装する」と書けば、受入を保持する者が誰もいなくなる。

```text
OBSERVATION_SUBJECT_DISTINCT_FROM_OBSERVATION_SURFACE=true
SURFACE_HOLDS_ACCEPTANCE=false
```

# 3. External Findings

すべての外部reviewer、bot、model、CI annotation、review comment、生成レポートは、次の状態で始まる。

```text
UNVERIFIED_EXTERNAL_OBSERVATION
```

```text
EXTERNAL FINDING
→ PRESENT TO SHUKOU
→ SHUKOU ADOPTS?
   YES → AUTHORIZED DIFFERENCE CANDIDATE
   NO / ABSENT → NO IMPLEMENTATION / NO BLOCK / NO PHASE REOPEN
```

明示的なShukou採用記録なしに、次のいずれにもなれない。

```text
STRUCTURAL_DIFFERENCE
IMPLEMENTATION_INSTRUCTION
PHASE_BLOCKER
ACCEPTANCE_FAILURE
NEW_WORK_UNIT
```

採用**ではない**もの。

```text
SILENCE
SEVERITY_LABEL
APPARENT_TECHNICAL_CORRECTNESS
COMPLETED_AUTOMATED_REVIEW
BOT_SELF_DESCRIPTION
```

技術的に正しいfindingも採用ではない。**正しさは誰が決めたかを置き換えない。**Phase 5のP1は技術的に正しかったが、正しさが採用の代わりになるなら、採用という段階は存在しないのと同じである。

## 3.1 採用記録の束縛

採用は、**その正確な観測**と**その正確な処分**に束縛される。

```text
adoption.authority      == SHUKOU
adoption.observation_id == finding.observation_id
adoption.disposition    == requested_disposition
```

束縛の無い採用は、後から別のfindingを下へ差し込める採用である。

## 3.2 過去のbot commentは遡って授権しない

```text
HISTORICAL_BOT_COMMENT_RETROACTIVELY_AUTHORIZES_WORK=false
```

# 4. Prohibited Route

```text
AUTOMATED_CODEX_REVIEW_TRIGGER_ALLOWED=false
CODEX_AS_ACCEPTANCE_GATE=false
CODEX_FINDING_AUTO_ADOPTION=false
CODEX_FINDING_AUTO_IMPLEMENTATION=false
```

このrepositoryの実行可能なhandoff経路とPR完了経路は、自動review triggerを**呼ばず、要求せず、待たず、推奨しない**。

# 5. Handoff State Machine

```text
IMPLEMENTATION_IN_PROGRESS
→ CLAUDE_CODE_IMPLEMENTATION_COMPLETE
→ EXECUTOR_SELF_REVIEW_COMPLETE
→ GITHUB_PR_READY
→ READY_FOR_STRUCTURAL_REVIEW     ← executorはここで停止する
→ STRUCTURAL_REVIEW_RUNNING       ← CHATGPT
→ STRUCTURAL_REVIEW_PASS
→ MERGE_RECOMMENDED               ← 推薦であって受入ではない
→ SHUKOU_ACCEPTED                 ← SHUKOU
→ SHUKOU_MERGED                   ← SHUKOU
```

構造レビューは五つの結果のいずれかを返す。

```text
MERGE_RECOMMENDED
CORRECTION_REQUIRED
MORE_EVIDENCE_REQUIRED
BLOCKED
NOT_REVIEWED
```

`CORRECTION_REQUIRED`と`MORE_EVIDENCE_REQUIRED`は`IMPLEMENTATION_IN_PROGRESS`へ戻る。`SHUKOU_REJECTED`も戻る。拒絶は終端ではない。

```text
EXECUTOR_TERMINAL_STATE=READY_FOR_STRUCTURAL_REVIEW
HANDOFF_TERMINATES_AT_READY_FOR_STRUCTURAL_REVIEW=true
```

二つの順序が明示的に検査される。

```text
MERGE_RECOMMENDED は STRUCTURAL_REVIEW_PASS からのみ  → STRUCTURAL_REVIEW_SKIPPED
SHUKOU_MERGED     は SHUKOU_ACCEPTED からのみ         → MERGE_WITHOUT_FINAL_ACCEPTANCE
```

いずれも宣言済み遷移集合からすでに導かれるが、別個の理由コードを持つ。「宣言されていない」としか言わない拒否は、**どの段が飛ばされたか**を人に伝えない。

自動reviewerはこの経路に存在しない。挿入する状態が無い。

## 5.1 policyは記録であり、批准値はcodeが持つ

`03_BINDING/DEVELOPMENT_BINDING_POLICY.json`はHuman決定の**公開された記録**である。批准された値そのものは`development_binding.policy`が定数として保持し、loaderは記録が定数と完全一致することを要求する。

v0.1のloaderは`may`と`must_not`が「一意な文字列のlist」であることを検査し、**それが批准されたlistであることを検査しなかった**。したがってHuman専用actionを非HumanのHuman`may`へ移したpolicy fileはそのまま読み込まれ、evaluatorは`PERMITTED`と答えた。`human_only_states`を空にすることも同じ結果を生んだ——空listに対するloopは何も送出しない。

```text
SHAPE VALIDATED != CONTENT PINNED
```

Phase 5のP1と同じ欠陥である（`ADR-0027` §3.3）。ある場所で主張され、どこでも強制されていない規則と、それに似た検査が隙間に立っている。

いま固定されるもの。

```text
role capabilities
exact may / must_not sets
handoff state sequence
advisor-only state set
human-only state set
declared transition set
structural review owner
merge readiness recommendation owner
final acceptance owner
merge operation owner
external finding adoption authority
```

## 5.2 評価器は例外を投げない

JSONは文字列が来るべき場所へ配列やobjectを置ける。それらはhashableではないので、`frozenset`に対する所属検査は答えるのではなく`TypeError`を送出する。

```text
["CLAUDE_CODE"] in frozenset(...)  → TypeError
```

verdictを読む呼び手と例外を捕らえる呼び手は別の呼び手であり、前者が沈黙によって「許可」と告げられてはならない。したがって所属検査の前にscalar型を検査し、ill-typedな値は**verdict**として返る。

```text
RECORD_FIELD_IS_NOT_A_SCALAR → REFUSED
NO_EVALUATION_INPUT_RAISES=true
INSTALLED_WHEEL_GUARD_WORKS=true
DUPLICATE_MAINTAINED_COPY=false
OBSERVATION_SUBJECT_DISTINCT_FROM_OBSERVATION_SURFACE=true
SURFACE_HOLDS_ACCEPTANCE=false
```

# 6. Precedence

```text
1  HUMAN_RATIFIED_CURRENT_REPOSITORY_BINDING
2  AGENT_SYSTEM_PROMPT
3  AGENT_TOOL_DEFAULT_BEHAVIOUR
4  PULL_REQUEST_BODY_TEXT
5  EXTERNAL_BOT_COMMENT
6  CONVENIENCE
```

批准されたBindingは、Agentのprompt、tool既定動作、PR本文、bot comment、利便性のすべてに優先する。「統合の既定がそうなっている」「PR本文にそう書いてある」「botがそう言っている」「その方が速い」は、いずれもこのBindingを上書きしない。

Kernel semanticsについては`KERNEL_CONSTITUTION.md`が上位に留まる。このBindingが順位付けるのは、**このrepositoryの開発運用**における指示の出所であって、Kernelの意味論ではない。

# 7. Why A Document Was Not Enough

`KERNEL_VERTICAL_WORK_UNIT_DELIVERY.md` §6は正しく書かれていた。それでも事故は起きた。

```text
A RULE DESCRIBED   = 読む者が従うことを期待する
A RULE EVALUATED   = 従わない記録が拒まれる
```

したがってこのBindingは述語として実装される（`development_binding.evaluation`）。conformance testは文字列の存在ではなく、**代表的なhandoff／acceptance記録を評価し、禁止遷移が拒まれることを証明する**。

```text
DOCUMENT_ONLY_ENFORCEMENT=false
PHRASE_MATCH_ONLY_TEST=false
RECORD_EVALUATION_REQUIRED=true
```

# 8. Acceptance

```text
HUMAN_DECISION_RECORDED=true
CURRENT_REPOSITORY_DEVELOPMENT_BINDING_IMPLEMENTED=true
CURRENT_REPOSITORY_ROLE_MAP_CLOSED=true
CHATGPT_STRUCTURAL_ADVISOR_FIXED=true
CHATGPT_STRUCTURAL_ADVISOR_ONLY=true
CLAUDE_CODE_EXECUTOR_FIXED=true
CLAUDE_CODE_IMPLEMENTER_ONLY=true
GITHUB_INTENT_SURFACE_FIXED=true
GITHUB_INTENT_AND_RECEIPT_SURFACE_ONLY=true
SHUKOU_ACCEPTANCE_OWNER_FIXED=true
SHUKOU_SOLE_ACCEPTANCE_AND_MERGE_OWNER=true
STRUCTURAL_REVIEW_OWNER_FIXED=true
MERGE_READINESS_RECOMMENDATION_OWNER_FIXED=true
FINAL_ACCEPTANCE_OWNER_FIXED=true
MERGE_OPERATION_OWNER_FIXED=true
AMBIGUOUS_MERGE_DECISION_RETAINED=false
RATIFIED_POLICY_PINNED_NOT_ONLY_SHAPE_VALIDATED=true
NO_EVALUATION_INPUT_RAISES=true
INSTALLED_WHEEL_GUARD_WORKS=true
DUPLICATE_MAINTAINED_COPY=false
OBSERVATION_SUBJECT_DISTINCT_FROM_OBSERVATION_SURFACE=true
SURFACE_HOLDS_ACCEPTANCE=false
EXTERNAL_FINDING_DEFAULT_UNVERIFIED=true
EXPLICIT_SHUKOU_ADOPTION_REQUIRED=true
BOT_FINDING_AUTO_ADOPTION=false
BOT_FINDING_AUTO_IMPLEMENTATION=false
AUTOMATED_CODEX_REVIEW_TRIGGER_ALLOWED=false
CODEX_REVIEW_TRIGGER_ALLOWED=false
HANDOFF_TERMINATES_AT_READY_FOR_STRUCTURAL_REVIEW=true
INCIDENT_REGRESSION_PROVEN=true
HUMAN_MERGE_BOUNDARY_PRESERVED=true
KERNEL_PROVIDER_NEUTRALITY_PRESERVED=true
UNIVERSAL_KERNEL_PROVIDER_NEUTRALITY_PRESERVED=true
```

## 8.1 guardはinstall後も動く

正本は`03_BINDING/DEVELOPMENT_BINDING_POLICY.json`ただ一つである。`pyproject.toml`の`force-include`が、build時にその同じfileをpackage内へ写す。ディスク上に維持すべき第二のfileは存在しない。

```text
SOURCE_CHECKOUT  → 03_BINDING の正本を直接読む
INSTALLED_WHEEL  → package内のresourceを読む
DUPLICATE_MAINTAINED_COPY=false
INSTALLED_WHEEL_GUARD_WORKS=true
```

修正前、`evaluate()`はrepository相対のpathを解決し、installされた環境では存在しなかった。fail closedではあった——許可ではなく拒否として落ちた——が、**答えられなかった**。source checkoutでしか動かないguardは、packageがpackageとして使われた瞬間に存在しなくなるguardである。

# 9. Explicit Non-Claims

```text
KERNEL_SEMANTICS_MODIFIED=false
CHANGE_EVIDENCE_REFLOW_SEMANTICS_MODIFIED=false
GITHUB_ADAPTER_IMPLEMENTED=false
AGENT_ADAPTER_IMPLEMENTED=false
RUNTIME_ENFORCEMENT_IMPLEMENTED=false
```

`RUNTIME_ENFORCEMENT_IMPLEMENTED=false`は特に明示する。このBindingは記録を評価する。Agentがこの評価器を呼ばずに行動することを、Bindingは**物理的に阻止しない**。強制の所有者はRuntimeであり、v0.1にRuntimeは無い。

境界を主張より狭く述べるのは、Phase 5のP1が教えたことである——主張が実装より広いとき、その差は主張した者にも見えない。
