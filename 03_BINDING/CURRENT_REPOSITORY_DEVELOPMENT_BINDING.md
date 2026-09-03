# MANOSUBE Agent Civilization OS

## Current-Repository Development Binding v0.1

```text
DOC_TYPE=REPOSITORY_BINDING
BINDING_SCOPE=CURRENT_REPOSITORY_DEVELOPMENT_OPERATION
DOCUMENT_ID=DEV-BINDING-0001
DECISION_ID=HUMAN-DECISION-CURRENT-REPOSITORY-OPERATING-BINDING-0001
DECISION_STATUS=RATIFIED
DECISION_AUTHORITY=SHUKOU
KERNEL_ELEMENT=none
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
```

---

# 0. Binding Position

このBindingは、`manosube/manosube-agent-civilization-os`を**構築する**四者を選択する。Kernelが何であるかは述べない。

```text
CHATGPT     = STRUCTURAL_ADVISOR
CLAUDE_CODE = IMPLEMENTATION_EXECUTOR
GITHUB      = HUMAN_INTENT_AND_WORK_STATE_SURFACE
SHUKOU      = ACCEPTANCE AND MERGE AUTHORITY
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
− CODE AUTHORSHIP
− ACCEPTANCE DECISION
− MERGE DECISION
− EXTERNAL FINDING ADOPTION

CLAUDE CODE
= IMPLEMENTATION
+ TEST EXECUTION
+ EXECUTOR SELF-REVIEW
+ PR PREPARATION
− STRUCTURAL AUTHORITY
− ACCEPTANCE DECISION
− MERGE
− EXTERNAL FINDING ADOPTION
− AUTOMATED EXTERNAL REVIEW REQUEST

GITHUB
= HUMAN INTENT RECORD
+ WORK STATE SURFACE
+ COMMIT / PR / EVIDENCE RECEIPT SURFACE
− CANONICAL KERNEL STATE
− AUTHORITY
− COMPLETION

SHUKOU
= FINDING ADOPTION OR REJECTION
+ ACCEPTANCE CHECK
+ APPROVAL
+ MERGE
```

`may`に名前が無い行為は、禁止一覧に無くても許可されない。**沈黙は許可ではない**——Authorityが未規定のactionに対して適用する規律（`AUTHORITY_CONTRACT.md` §1）と同じものである。

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
→ READY_FOR_SHUKOU_REVIEW        ← executorはここで停止する
→ SHUKOU_CHECK
→ SHUKOU_ACCEPTED | SHUKOU_REJECTED
→ SHUKOU_MERGED
```

```text
EXECUTOR_TERMINAL_STATE=READY_FOR_SHUKOU_REVIEW
HANDOFF_TERMINATES_AT_READY_FOR_SHUKOU_REVIEW=true
```

`READY_FOR_SHUKOU_REVIEW`以降の状態へは、`SHUKOU`以外の誰も遷移できない。この性質は**policyの読み込み時**に検査される。executorへmerge遷移を与えるよう編集されたpolicy fileは、参照される前に拒まれる。

自動reviewerはこの経路に存在しない。挿入する状態が無い。

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
EXTERNAL_FINDING_DEFAULT_UNVERIFIED=true
EXPLICIT_SHUKOU_ADOPTION_REQUIRED=true
BOT_FINDING_AUTO_ADOPTION=false
BOT_FINDING_AUTO_IMPLEMENTATION=false
AUTOMATED_CODEX_REVIEW_TRIGGER_ALLOWED=false
CODEX_REVIEW_TRIGGER_ALLOWED=false
HANDOFF_TERMINATES_AT_READY_FOR_SHUKOU_REVIEW=true
INCIDENT_REGRESSION_PROVEN=true
HUMAN_MERGE_BOUNDARY_PRESERVED=true
KERNEL_PROVIDER_NEUTRALITY_PRESERVED=true
UNIVERSAL_KERNEL_PROVIDER_NEUTRALITY_PRESERVED=true
```

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
