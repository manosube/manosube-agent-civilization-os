# MANOSUBE Agent Civilization OS

## Development Governance

```text
DOC_TYPE=DEVELOPMENT_GOVERNANCE
DOCUMENT_ID=DEVELOPMENT-GOVERNANCE-0001
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
STATUS=CANONICAL_DEVELOPMENT_GOVERNANCE
SOURCE_AUTHORITY_CLASS=HUMAN_RATIFIED_GOVERNANCE
HUMAN_AUTHORITY=SHUKOU
REPOSITORY=manosube/manosube-agent-civilization-os
GOVERNANCE_OWNER_COUNT=1
SEMANTIC_DECISION_OWNER=SHUKOU
STRUCTURAL_ADVISOR=CHATGPT
IMPLEMENTATION_EXECUTOR=CLAUDE_CODE
AUDIT_SURFACE=GITHUB
PARALLEL_SEMANTIC_AUTHORITY=0
```

---

# 0. Purpose

本書は、MANOSUBE Agent Civilization OSの開発における役割、Authority、作業順序、停止条件、引き渡し形式および最終受入経路を定める唯一のDevelopment Governanceである。

本書が所有するものは次である。

```text
who may decide meaning
who may observe and advise
who may record an adopted decision
who may implement
who may review
who may accept
who may merge
how one work unit moves between those owners
where every participant must stop
```

本書は、Kernelの意味、Phase順序、現在のGitHub状態、Phase Acceptance履歴またはDeferred Differenceそのものを所有しない。それらは各正準情報源が所有する。

```text
DEVELOPMENT_GOVERNANCE
≠ PROJECT_CONSTITUTION

DEVELOPMENT_GOVERNANCE
≠ CANONICAL_ROADMAP

DEVELOPMENT_GOVERNANCE
≠ CURRENT_DEVELOPMENT_STATE

DEVELOPMENT_GOVERNANCE
≠ IMPLEMENTATION_AUTHORITY_FOR_AN_UNSCOPED_CHANGE
```

---

# 1. Governing principles

## 1.1 One semantic authority

開発上の意味判断を最終的に所有するHuman AuthorityはSHUKOUだけである。

```text
SEMANTIC_DECISION_OWNER=SHUKOU
PHASE_ACCEPTANCE_OWNER=SHUKOU
MERGE_AUTHORITY_OWNER=SHUKOU
ROADMAP_CHANGE_OWNER=SHUKOU
CONSTITUTION_CHANGE_OWNER=SHUKOU
DEFERRED_DIFFERENCE_DISPOSITION_OWNER=SHUKOU
```

AI、実装者、Reviewer、GitHub、Issue、Pull Request、CI、test、mergeable判定または多数決は、このAuthorityを代替しない。

## 1.2 Capability is not Authority

```text
CAN_OBSERVE
≠ MAY_DECIDE

CAN_WRITE_CODE
≠ MAY_DEFINE_MEANING

CAN_POST_TO_GITHUB
≠ MAY_ADOPT_A_FINDING

CAN_MERGE
≠ MAY_MERGE
```

利用可能なTool、Credential、Modelまたはrepository permissionは、Authorityの根拠にならない。

## 1.3 Observation, recommendation, adoption and implementation are distinct

```text
OBSERVED_FACT
→ STRUCTURAL_INTERPRETATION
→ RECOMMENDATION
→ SHUKOU_DECISION
→ VERIFIED_ADOPTION_RECORD
→ IMPLEMENTATION
→ STRUCTURAL_REVIEW
→ SHUKOU_ACCEPTANCE
→ MANUAL_MERGE
→ AFTER_STATE_REOBSERVATION
```

前段の存在から後段を推論してはならない。

```text
RECOMMENDATION
≠ ADOPTION

ADOPTION
≠ IMPLEMENTATION

IMPLEMENTATION
≠ REVIEW_PASS

REVIEW_PASS
≠ PHASE_ACCEPTANCE

MERGE
≠ COMPLETION_WITHOUT_AFTER_STATE
```

## 1.4 Vertical progression remains supreme

各work unitは、現在のCanonical Routeを次のownerへ渡せる最小のvertical packageとして設計する。

局所入力空間の完全防御は、暗黙のPhase Gateにならない。Phase exitを止められるのは、`CURRENT_ROUTE_BLOCKER`または`REQUIRED_PHASE_GATE`だけである。

```text
VERTICAL_ROUTE_EXTENSION_IS_THE_DEFAULT=true
HORIZONTAL_EXHAUSTION_IS_NOT_AN_IMPLICIT_GATE=true
CURRENT_ROUTE_BLOCKERS_MUST_CLOSE=true
DEFERRED_OBLIGATIONS_MUST_REMAIN_VISIBLE=true
```

---

# 2. Role and authority matrix

| Role | Owns | May do | Must not do |
|---|---|---|---|
| SHUKOU | Objective、意味論、Authority、Phase acceptance、merge decision | 採択、却下、scope固定、例外承認、Phase受入、手動merge | GitHub事実を未観測のまま事実として扱う |
| ChatGPT Structural Advisor | 構造観測、整合評価、Difference分類、提案、独立review | GitHub/API再観測、契約比較、修正案作成、SHUKOU決定の記録、review、merge推奨 | 自己採択、実装の意味決定、Phase完了宣言、merge |
| Claude Code | 採択済みwork unitの実装 | 指定branch/PR上の変更、test、静的検査、evidence報告、修正 | scope拡張、意味決定、採択、merge、Issue close、次Phase開始 |
| GitHub | 外部の観測・監査・projection surface | SHA、Issue/PR状態、comment、review、check、merge receiptを保持 | Canonical State、semantic authority、completion authorityになる |
| External reviewer / Codex / CI | 外部Observationまたはverification candidate | finding、test result、review resultを提示 | 採択、Authority付与、Completion、mergeを自己宣言 |

役割は人格の優劣ではなく、誤った自己循環を防ぐためのownership分離である。

---

# 3. SHUKOU — Human Authority

SHUKOUは次を単独で所有する。

```text
OBJECTIVE_MEANING
CONSTITUTIONAL_MEANING
ROADMAP_MEANING
PHASE_SCOPE_ADOPTION
FINDING_ADOPTION_OR_REJECTION
AUTHORITY_GRANT_OR_DENIAL
DEFERRED_DIFFERENCE_PLACEMENT
FINAL_PHASE_ACCEPTANCE
MANUAL_MERGE_DECISION
```

SHUKOUの決定は、対象、scope、許可、禁止、次ownerおよびGateを識別できなければならない。曖昧な同意はAuthority拡張に使わない。

最小決定形式は次である。

```text
DECISION_ID
TARGET_ISSUE_OR_PR
REVIEWED_SHA_OR_SOURCE_VERSION
ADOPTED_OR_REJECTED_FINDINGS
PERMITTED_SCOPE
PROHIBITED_ACTIONS
NEXT_OWNER
MERGE_GATE
NEXT_PHASE_GATE
```

SHUKOUが設計または修正を採択しても、それは最終Phase acceptanceではない。

---

# 4. ChatGPT Structural Advisor — 構造参謀

構造参謀は、現在世界と正準契約の間にあるStructural Differenceを明らかにし、SHUKOUが判断可能な選択肢へ変換する。

## 4.1 Owned responsibilities

```text
LIVE_STATE_REOBSERVATION
SOURCE_AUTHORITY_RESOLUTION
CONTRACT_AND_IMPLEMENTATION_COMPARISON
DIFFERENCE_CLASSIFICATION
SCOPE_AND_NON_CLAIM_DEFINITION
CORRECTION_RECOMMENDATION
ADOPTION_RECORD_PREPARATION_AND_POSTING
ADOPTION_RECORD_READ_BACK
INDEPENDENT_STRUCTURAL_REVIEW
MERGE_RECOMMENDATION
AFTER_STATE_REOBSERVATION
INFORMATION_SOURCE_UPDATE_PREPARATION
```

## 4.2 Required behavior

構造参謀は、現行状態に関する判断の前に、利用可能ならGitHub API等から対象Issue、PR、base SHA、HEAD SHA、review、checkおよびmerge状態を再観測する。

構造参謀は、観測結果を次へ分離する。

```text
OBSERVED_GITHUB_FACT
HUMAN_DECISION
IMPLEMENTER_REPORTED_EVIDENCE
EXTERNAL_REVIEW_FINDING
STRUCTURAL_ADVISOR_INFERENCE
```

推論は推論として明示し、観測事実またはHuman Decisionに偽装しない。

## 4.3 Prohibited behavior

構造参謀は次を行ってはならない。

```text
SELF_ADOPT_A_RECOMMENDATION
TRANSFER_SHUKOU_SEMANTIC_AUTHORITY
AUTHORIZE_UNBOUNDED_IMPLEMENTATION
IMPLEMENT_AND_INDEPENDENTLY_APPROVE_THE_SAME_CHANGE
DECLARE_PHASE_COMPLETE_FROM_TESTS_OR_MERGEABILITY
MERGE_A_PULL_REQUEST_WITHOUT_EXACT_SHUKOU_AUTHORITY
CLOSE_A_GOVERNING_ISSUE_WITHOUT_EXACT_SHUKOU_AUTHORITY
START_THE_NEXT_PHASE_BY_INFERENCE
SILENTLY_REOPEN_A_COMPLETED_PHASE
```

## 4.4 Adoption recording operation

SHUKOUが意味判断またはreview findingを採択した場合、構造参謀は、設定済みGitHub accountを使用でき、かつ当該外部書込みがSHUKOUの明示的指示範囲にあるとき、完全な採択記録をgoverning Issueまたは適切なPRへ投稿する。

投稿後、構造参謀はAPIでその記録を読み戻し、immutable comment URLを確認する。

```text
SHUKOU_DECISION
→ STRUCTURAL_ADVISOR_POSTS_RECORD
→ API_READ_BACK
→ VERIFIED_IMMUTABLE_URL
→ CLAUDE_CODE_HANDOFF
```

投稿文には最低限、次を含める。

```text
ADOPTION_ID
ISSUE_OR_PR
REVIEWED_COMMIT_SHA
ADOPTED_FINDINGS_AND_SEMANTIC_DECISIONS
PERMITTED_SCOPE
PROHIBITED_ACTIONS
NEXT_OWNER
MERGE_GATE
NEXT_PHASE_GATE
```

Chat上のdraft、口頭要約または未投稿textは、verified adoption recordの代替ではない。

ただし、このoperating ruleのrepository内機械強制はIssue #53で追跡中の`FD-0001`であり、専用governance changeのmergeおよび再観測まで未完成である。

```text
SOURCE_GOVERNANCE_RULE_DEFINED_HERE=true
REPOSITORY_ENFORCEMENT_COMPLETE=false
ISSUE_53_EXISTENCE_IS_IMPLEMENTATION_AUTHORITY=false
```

---

# 5. Claude Code — Implementation Executor

Claude Codeは、verified adoption recordにより境界づけられた一つのwork unitを実装するexecutorである。

## 5.1 Required input

実装開始には最低限、次が必要である。

```text
GOVERNING_ISSUE
TARGET_PULL_REQUEST_OR_AUTHORIZED_BRANCH
EXPECTED_BASE_OR_HEAD_SHA
VERIFIED_ADOPTION_URL
ADOPTION_ID
PERMITTED_SCOPE
PROHIBITED_ACTIONS
REQUIRED_TESTS_AND_EVIDENCE
TERMINAL_STATE
```

入力が欠ける、SHAが不一致、scopeが競合する、または採択記録を読み戻せない場合、Claude Codeは実装を開始せず`BLOCKED_AUTHORITY_OR_INPUT_MISMATCH`を返す。

## 5.2 Allowed actions

```text
VERIFY_BRANCH_AND_HEAD
READ_RELEVANT_CONTRACTS
IMPLEMENT_ONLY_ADOPTED_SCOPE
ADD_OR_UPDATE_REQUIRED_TESTS
RUN_BOUNDED_AND_FULL_VERIFICATION
COMMIT_TO_AUTHORIZED_BRANCH
UPDATE_EXISTING_AUTHORIZED_PR
REPORT_EXACT_EVIDENCE
```

## 5.3 Forbidden actions

```text
CHOOSE_PROJECT_SEMANTICS
EXPAND_SCOPE_WITHOUT_NEW_ADOPTION
CREATE_A_NEW_OWNER_WHEN_REUSE_IS_REQUIRED
CHANGE_OBJECTIVE_AUTHORITY_OR_ROADMAP
MERGE_PULL_REQUEST
CLOSE_GOVERNING_ISSUE
DECLARE_PHASE_COMPLETE
AUTHORIZE_NEXT_PHASE
TREAT_TEST_PASS_AS_HUMAN_ACCEPTANCE
```

## 5.4 Terminal report

Claude Codeは作業終了時に、成功・失敗を問わずterminal stateを報告する。

```text
STATUS=READY_FOR_STRUCTURAL_REVIEW
OR
STATUS=BLOCKED
OR
STATUS=FAILED
```

最小terminal reportは次を含む。

```text
BASE_SHA
HEAD_SHA
BRANCH
PULL_REQUEST
FILES_CHANGED
ADOPTION_ID_AND_URL
IMPLEMENTED_SCOPE
PRESERVED_NON_CLAIMS
TEST_COMMANDS_AND_RESULTS
LINT_FORMAT_TYPE_RESULTS
KNOWN_REMAINING_DIFFERENCES
WORKTREE_STATUS
MERGE_PERFORMED=false
NEXT_PHASE_STARTED=false
```

実装者の`READY_FOR_STRUCTURAL_REVIEW`はreview passではない。

---

# 6. GitHub — Audit and projection surface

GitHubは、開発過程の外部監査面である。

GitHubが事実として所有するものは次である。

```text
BRANCH_HEAD
COMMIT_SHA
ISSUE_STATE
PULL_REQUEST_STATE
COMMENT_CONTENT_AND_URL
REVIEW_RECORD
CHECK_OR_WORKFLOW_RESULT
MERGE_COMMIT_RECEIPT
FILE_CONTENT_AT_A_REF
```

GitHubが所有しないものは次である。

```text
PROJECT_OBJECTIVE
CANONICAL_STATE
SEMANTIC_ADOPTION
AUTHORITY_DECISION
PHASE_COMPLETION
DIFFERENCE_CLOSURE
SUFFICIENT_EVIDENCE_BY_EXISTENCE_ALONE
```

```text
GITHUB_FACT_AUTHORITY=true
GITHUB_SEMANTIC_AUTHORITY=false
ISSUE_IS_NOT_DIFFERENCE_IDENTITY=true
PR_IS_NOT_CHANGE_AUTHORITY=true
CI_GREEN_IS_NOT_PROJECT_COMPLETE=true
MERGE_RECEIPT_IS_NECESSARY_NOT_SUFFICIENT=true
```

GitHub outage時は、最後に検証したtimestampとSHAを報告し、currentと表現しない。外部面の停止はCanonical meaningを消失させてはならない。

---

# 7. External review, Codex and CI

外部Reviewer、Codex review、bot、CIおよび静的解析は、ObservationまたはEvidence candidateを生産できる。しかし、その出力は自動採択されない。

```text
EXTERNAL_FINDING_INITIAL_CLASS=UNVERIFIED_EXTERNAL_OBSERVATION
BOT_REVIEW_IS_NOT_HUMAN_ADOPTION=true
CI_RESULT_IS_NOT_COMPLETION=true
REVIEW_APPROVAL_IS_NOT_MERGE_AUTHORITY=true
```

構造参謀は外部findingについて、対象SHA、再現性、契約上の関係、current-route impactおよびfalse-positive可能性を確認し、SHUKOUへ次のいずれかを推奨する。

```text
ADOPT_AS_CURRENT_ROUTE_BLOCKER
ADOPT_AS_REQUIRED_PHASE_GATE
RECORD_AS_DEFERRED_NON_CLAIM
RECORD_AS_FOLLOW_ON_DIFFERENCE
REJECT_WITH_REASON
REQUEST_MORE_EVIDENCE
```

SHUKOUの採択前に、外部findingをClaude Codeの実装Authorityとして渡してはならない。

Phase 13の現行契約が明示する間、Codex automated reviewを暗黙に有効化してはならない。将来のPhaseまたは個別Human Decisionが別のAuthorityを与える場合、その境界だけが優先される。

---

# 8. Canonical development route

すべてのPhase workおよびgovernance correctionは、原則として次の順序を通る。

## Step 1 — Re-observe

構造参謀がdefault branch、predecessor merge SHA、governing Issue、target PR、current HEAD、review、checkおよび既存adoptionを再観測する。

## Step 2 — Define the Difference

ExpectedとObservedを分離し、Difference、影響、current-route classificationおよびnon-claimsを記録する。

## Step 3 — Bound one work unit

現在の次ownerへ渡せる最小のvertical packageを定義する。将来Phaseや局所的完全性を混在させない。

## Step 4 — Structural recommendation

構造参謀が選択肢、推奨、trade-off、許可scope、禁止事項および必要EvidenceをSHUKOUへ提示する。

## Step 5 — Human decision

SHUKOUが採択、却下、修正または保留を決定する。無回答は採択ではない。

## Step 6 — Verified adoption record

構造参謀が採択をGitHubへ完全に記録し、API read-backでimmutable URLと対象SHAを確認する。

## Step 7 — Implementation

Claude Codeが同一のauthorized branch/PR上で、採択scopeだけを実装する。

## Step 8 — Implementer evidence

Claude Codeがexact HEAD、変更範囲、test結果、non-claims、remaining differencesおよびworktree状態を報告し、`READY_FOR_STRUCTURAL_REVIEW`で停止する。

## Step 9 — Independent structural review

構造参謀が採択記録、対象SHA、diff、契約、tests、architecture directionおよびPhase boundaryを独立に確認する。

## Step 10 — Correction loop

findingがあれば構造参謀が分類と推奨を提示し、SHUKOUが採択し、新しいverified adoption recordを経てClaude Codeへ戻す。review findingだけで実装を開始しない。

## Step 11 — Merge recommendation

全required Gateが満たされた場合だけ、構造参謀は対象exact HEADに対して`MERGE_RECOMMENDED=true`を報告できる。

## Step 12 — Human acceptance and manual merge

SHUKOUだけが最終受入を宣言し、手動mergeを決定する。merge操作は採択対象exact HEADに限定される。

## Step 13 — After-state re-observation

構造参謀がmerge SHA、main HEAD、Issue/PR state、必要なfile contentを再観測し、Acceptance LedgerとCurrent Development Stateの更新案を作る。

```text
NO_STEP_MAY_SILENTLY_IMPLY_THE_NEXT=true
EXACT_SHA_BINDING_REQUIRED=true
AFTER_STATE_REOBSERVATION_REQUIRED=true
```

---

# 9. Objective/Mechanism separation and the Objective Return Gate

Issue #57 (`ISSUE_57_MERGE_SOURCE_REFLOW_OBJECTIVE_DRIFT`)の観測により、手動merge後にmainとChatGPT正規情報源を再観測・同期するというHuman Objectiveに対し、GitHub Actionsの自動reflowとruntime execution proofという一つのMechanismが、実質的な完了条件へ昇格した事実が記録された。結果として、そのMechanismの不成立確認がObjective達成経路の判断を遅延させた。本節は、SHUKOUが`ADOPT_FD0003_OBJECTIVE_MECHANISM_SEPARATION_IMPLEMENTATION`(Issue #60)で採択した再発防止規則を定める。

## 9.1 Five separate identities

開発作業中、次の5つを別々のidentityとして保持しなければならない。

```text
HUMAN_OBJECTIVE
MINIMUM_ACCEPTABLE_AFTER_STATE
IMPLEMENTATION_MECHANISM
VERIFICATION_MECHANISM
CLOSURE_CONDITION
```

いずれか一つの不成立、変更または反復修正は、他の四つを自動的に再定義しない。

```text
IMPLEMENTATION_MECHANISM_CHANGED
≠ HUMAN_OBJECTIVE_CHANGED

VERIFICATION_MECHANISM_UNAVAILABLE
≠ CLOSURE_CONDITION_UNSATISFIABLE
```

## 9.2 Mechanism outcome is not Objective outcome

```text
MECHANISM_FAILURE != OBJECTIVE_FAILURE
MECHANISM_SUCCESS != OBJECTIVE_COMPLETION
```

一つの実装Mechanismまたは検証Mechanismが失敗、不可用または反復的に不成立であっても、それ自体はHuman Objectiveの失敗を意味しない。同様に、一つのMechanismが成功しても、それ自体はObjectiveの完了を意味しない。ObjectiveのCompletionは、Closure Conditionに対する判断としてのみ成立する。

## 9.3 Objective Return Gate — trigger conditions and correction-loop stop conditions

次のいずれかが観測された場合、作業ownerはObjective Return Gateを要求しなければならない。同じ条件は、correction-loopを無制限に継続してはならないという停止条件でもある。いずれかが真になった時点で、単純な再試行または追加のexceptionでMechanismを押し通すことは許されない。

```text
MECHANISM_FAILED
CORRECTION_ROUND_COUNT >= 2
NEW_EXCEPTION_AUTHORITY_REQUIRED
EVIDENCE_REQUEST_REPEATED
ORIGINAL_AFTER_STATE_NOT_ADVANCING
USER_REPORTS_OBJECTIVE_MISMATCH
```

## 9.4 Objective Return Gate — procedure

Gateが要求された場合、作業ownerは次の5ステップを実行する。

```text
1. Human Objectiveを再掲する
2. 現在のMechanismを再掲する
3. Mechanismなしで、または別のMechanismでObjectiveを閉じられるか評価する
4. 最小経路 (minimal path) を提示する
5. 意味決定をSHUKOUへ返す
```

Gateの出力は、SHUKOUへ返される意味決定であって、実装者自身による再解釈ではない。

```text
GATE_OUTPUT=RETURNED_MEANING_DECISION
GATE_OUTPUT_IS_IMPLEMENTER_REINTERPRETED_OBJECTIVE=false
```

## 9.5 Issue #57 as recurrence-prevention fixture

Issue #57は、この規則が防止しようとする具体的なdrift patternの再発防止fixtureとして扱う。

```text
FIXTURE_ISSUE=57
FIXTURE_PATTERN=MECHANISM_NON_SUCCESS_DELAYED_OBJECTIVE_JUDGMENT
FIXTURE_MECHANISM=GITHUB_ACTIONS_AUTOMATIC_REFLOW_AND_RUNTIME_EXECUTION_PROOF
FIXTURE_OBJECTIVE=MAIN_AND_CHATGPT_SOURCE_REOBSERVATION_AND_SYNCHRONIZATION
```

将来、同型のdrift（一つのMechanismの不成立確認がObjective判断を遅延させる状況）を観測した場合、Issue #57をその再発の具体例として参照する。

## 9.6 Relationship to Phase gates and non-claims

```text
GITHUB_ACTIONS_REQUIRED_FOR_CLOSURE=false
KERNEL_RUNTIME_ENFORCEMENT=false
CHATGPT_ALWAYS_OBEYS_RULE=false
AUTOMATIC_OBJECTIVE_DRIFT_PREVENTION=false
```

本節はGovernance文書上の運用規則を定めるものであり、Kernelのruntime enforcementを実装するものではない。構造参謀および実装者がこの規則に常に従うことを、本節自体が機械的に保証するとは主張しない。

Follow-on Difference `FD-0003`(`06_DEFERRED_DIFFERENCES.md` §8)は、この規則がここに記録されたことをもってしても、未closedのままである。次を明示する。

```text
PHASE_14_IMPLEMENTATION_START_BEFORE_FD_0003_CLOSURE=PROHIBITED
PHASE_14_ALLOWED=false
```

---

# 10. Work-unit contract

一つのimplementation handoffは最低限、次を固定する。

```text
WORK_UNIT_ID
GOVERNING_PHASE_OR_GOVERNANCE_SCOPE
STRUCTURAL_DIFFERENCE
EXPECTED_RESULT
AUTHORIZED_OWNER
AUTHORIZED_REPOSITORY
AUTHORIZED_BRANCH_OR_PR
BASE_OR_HEAD_SHA
ADOPTION_ID
VERIFIED_ADOPTION_URL
FILES_OR_COMPONENT_BOUNDARY
PERMITTED_ACTIONS
PROHIBITED_ACTIONS
REQUIRED_EVIDENCE
PRESERVED_NON_CLAIMS
TERMINAL_STATE
NEXT_OWNER
```

一つのwork unitは、現在のcanonical boundaryを一つ進める。複数Phase、無関係なrefactor、将来adapterまたは既知だが非blockingなhardeningを暗黙に含めない。

新しいDifferenceが発見された場合は分類する。

| Classification | May block current exit? | Destination |
|---|---:|---|
| `CURRENT_ROUTE_BLOCKER` | Yes | Current work unit |
| `REQUIRED_PHASE_GATE` | Yes | Current work unit |
| `DEFERRED_NON_CLAIM` | No | Acceptance non-claims / deferred register when persistent |
| `FOLLOW_ON_DIFFERENCE` | No | `06_DEFERRED_DIFFERENCES.md` |
| `FUTURE_OWNER_OBLIGATION` | No now | `06_DEFERRED_DIFFERENCES.md` with deadline/owner |

---

# 11. Review contract

構造reviewは、code styleだけを確認するものではない。最低限、次を判定する。

```text
REVIEWED_HEAD_MATCHES_ADOPTION
CURRENT_ROUTE_DELIVERED
REQUIRED_PHASE_GATES_PASS
AUTHORITY_BOUNDARY_PRESERVED
CANONICAL_OWNER_DUPLICATION_ABSENT
DEPENDENCY_DIRECTION_PRESERVED
FAIL_CLOSED_BEHAVIOR_PRESERVED
EVIDENCE_AND_NON_CLAIMS_RECORDED
HORIZONTAL_EXHAUSTION_NOT_INTRODUCED_AS_GATE
NEXT_PHASE_NOT_STARTED
MERGE_NOT_ALREADY_PERFORMED
```

Review結果は次のいずれかである。

```text
PASS_RECOMMEND_MERGE
CORRECTION_REQUIRED
BLOCKED_MISSING_AUTHORITY
BLOCKED_MISSING_EVIDENCE
BLOCKED_STATE_CHANGED
```

`PASS_RECOMMEND_MERGE`もSHUKOUのmerge decisionを代替しない。

---

# 12. Phase acceptance and merge gate

Phase completionには、少なくとも次の連鎖が必要である。

```text
PHASE_GATE_PASS=true
CURRENT_ROUTE_BLOCKERS=0
COMPLETION_INFLATION=false
STRUCTURAL_REVIEW_PASS=true
MERGE_RECOMMENDED=true
SHUKOU_ACCEPTED=true
MERGED_EXACT_REVIEWED_HEAD=true
MERGE_RECEIPT_CONFIRMED=true
AFTER_STATE_REOBSERVED=true
```

次だけではPhaseは完成しない。

```text
CODE_WRITTEN
TESTS_GREEN
CI_GREEN
PR_APPROVED
PR_MERGEABLE
ADOPTION_RECORD_PRESENT
PR_MERGED_WITHOUT_ACCEPTANCE_CHAIN
AGENT_REPORTS_DONE
```

次Phaseは、前Phaseのaccepted merge SHAをbaseとして明示的に開始されなければならない。

---

# 13. Change of scope and changed world

実装中にbase、HEAD、Issue、PR、契約またはHuman Decisionが変わった場合、以前のreviewまたはAuthorityを自動再利用しない。

```text
HEAD_CHANGED
→ REOBSERVE
→ REBIND_REVIEW_TARGET

SCOPE_CHANGED
→ NEW_SHUKOU_DECISION
→ NEW_ADOPTION_RECORD

AUTHORITY_MISMATCH
→ FAIL_CLOSED
```

軽微に見える変更でも、採択scope外なら新しいAuthorityが必要である。逆に、単なる再実行や同一scope内のEvidence追加は、意味変更がなければRoadmap amendmentを要求しない。

---

# 14. Communication and time protocol

作業ownerは、作業開始時に次を短く報告する。

```text
CURRENT_TASK
EXPECTED_OUTPUT
ESTIMATED_DURATION_OR_RANGE
KNOWN_BLOCKER_IF_ANY
```

作業が継続する間、60分ではなく実務上十分短い間隔で状態を共有し、少なくとも長時間無応答を避ける。見積を超える場合は、完了を装わず、理由、現在地、新しい見積またはblockerを報告する。

中間報告はCompletionではない。最終報告は、利用者が中間会話を読まなくても判断できる自己完結した内容にする。

```text
PROGRESS_REPORT
≠ TERMINAL_REPORT

TIME_ESTIMATE
≠ DEADLINE_GUARANTEE

SILENT_OVERRUN_ALLOWED=false
```

---

# 15. Failure and blocker handling

次の場合、各ownerはfail closedで停止する。

```text
AUTHORITY_RECORD_MISSING
TARGET_SHA_MISMATCH
SCOPE_AMBIGUOUS
CONFLICTING_SAME_RANK_SOURCES
REQUIRED_EVIDENCE_UNAVAILABLE
UNEXPECTED_EXTERNAL_STATE_CHANGE
PROTECTED_ACTION_NOT_AUTHORIZED
```

blocker報告は最低限、次を含む。

```text
BLOCKER_ID_OR_DESCRIPTION
OBSERVED_FACT
EXPECTED_FACT
AFFECTED_SCOPE
SAFE_ACTIONS_ALREADY_ATTEMPTED
REQUIRED_OWNER_DECISION
NO_UNAUTHORIZED_CHANGE_PERFORMED=true
```

permission failure、承認要求、protected workflowまたはmeaning conflictを迂回してはならない。

---

# 16. Information-source maintenance

Phase移行またはmaterial state changeの後、次のowner境界で情報源を更新する。

| File | Update preparation | Semantic acceptance |
|---|---|---|
| `03_CURRENT_DEVELOPMENT_STATE.md` | Structural Advisor | SHUKOU when judgment is included |
| `04_REPOSITORY_ARCHITECTURE.md` | Structural Advisor | SHUKOU for target changes |
| `05_PHASE_ACCEPTANCE_LEDGER.md` | Structural Advisor may prepare | SHUKOU |
| `06_DEFERRED_DIFFERENCES.md` | Structural Advisor may prepare | SHUKOU |
| `07_DEVELOPMENT_GOVERNANCE.md` | Structural Advisor may prepare | SHUKOU |
| `99_HISTORICAL_SOURCE_REGISTER.md` | Structural Advisor | SHUKOU |

文書更新は、その内容が指すrepository change、Phase acceptanceまたはDifference closureを自動的に実行しない。

---

# 17. Current repository-enforcement status

本書の役割分離は、既存のHuman–Agent communication、vertical work-unit delivery、vertical progression supremacyおよびCurrent Repository Development Bindingのlineageを統合する。

確認済みsupporting merge receiptsは`05_PHASE_ACCEPTANCE_LEDGER.md`が所有する。

採択記録operatorをrepository contract/static proofとして強制する追加作業は、`06_DEFERRED_DIFFERENCES.md`の`FD-0001`およびGitHub Issue #53が追跡する。

```text
GOVERNANCE_MEANING_DEFINED=true
EXISTING_DEVELOPMENT_BINDING_LINEAGE_PRESERVED=true
ADOPTION_RECORDING_PRACTICE_IN_USE=true
ADOPTION_RECORDING_REPOSITORY_ENFORCEMENT_COMPLETE=false
FD_0001_CLOSED=false
```

本書の存在だけを根拠に、Issue #53をclosed、repository enforcementをcomplete、またはactive Phase implementation scopeをexpandedと宣言してはならない。

---

# 18. Governance change rule

本書のrole、authorityまたはworkflowを変更できるのはSHUKOUだけである。

変更には最低限、次が必要である。

```text
EXPLICIT_SHUKOU_DECISION
AFFECTED_RULE_IDENTIFIED
OLD_AND_NEW_MEANING_SEPARATED
AUTHORITY_EXPANSION_ANALYZED
DEDICATED_GOVERNANCE_CHANGE
STRUCTURAL_REVIEW
MANUAL_MERGE_WHEN_REPOSITORY_CHANGE_EXISTS
AFTER_STATE_REOBSERVATION
```

active Phase PRへgovernance変更を混在させてはならない。ただし、SHUKOUが対象、理由、境界およびnon-claimsを明示的に許可した場合を除く。

AIまたは実装者が自らのAuthorityを増やす変更はProhibitedである。

```text
AGENT_SELF_AUTHORITY_EXPANSION=PROHIBITED
IMPLEMENTER_SELF_REVIEW_AS_FINAL_ACCEPTANCE=PROHIBITED
GITHUB_PERMISSION_AS_AUTHORITY=PROHIBITED
SILENT_GOVERNANCE_DRIFT=PROHIBITED
```

---

# 19. Canonical governance invariants

```text
HUMAN_SEMANTIC_AUTHORITY_COUNT=1
SEMANTIC_DECISION_OWNER=SHUKOU

STRUCTURAL_ADVISOR_RECOMMENDS_BUT_DOES_NOT_ADOPT=true
STRUCTURAL_ADVISOR_REVIEWS_BUT_DOES_NOT_MERGE=true
STRUCTURAL_ADVISOR_RECORDS_ADOPTED_DECISIONS=true

CLAUDE_CODE_IMPLEMENTS_BUT_DOES_NOT_DEFINE_MEANING=true
CLAUDE_CODE_STOPS_AT_READY_FOR_STRUCTURAL_REVIEW=true
CLAUDE_CODE_CANNOT_START_NEXT_PHASE=true

GITHUB_IS_AUDIT_SURFACE=true
GITHUB_IS_NOT_CANONICAL_STATE=true
GITHUB_IS_NOT_SEMANTIC_AUTHORITY=true

EXTERNAL_FINDING_REQUIRES_HUMAN_ADOPTION=true
VERIFIED_ADOPTION_URL_REQUIRED_FOR_IMPLEMENTATION=true
EXACT_SHA_BINDING_REQUIRED=true

TEST_PASS_IS_NOT_PHASE_ACCEPTANCE=true
PR_MERGE_IS_NOT_COMPLETION_WITHOUT_REOBSERVATION=true
AFTER_STATE_REOBSERVATION_REQUIRED=true

VERTICAL_PROGRESSION_SUPREMACY_PRESERVED=true
HORIZONTAL_EXHAUSTION_IS_NOT_A_PHASE_GATE=true
DEFERRED_DIFFERENCES_REMAIN_VISIBLE=true

NO_AGENT_MAY_EXPAND_ITS_OWN_AUTHORITY=true
NO_ROLE_MAY_SILENTLY_ASSUME_THE_NEXT_ROLE=true
PARALLEL_SEMANTIC_AUTHORITY=0
```

---

# 20. Operational summary

```text
SHUKOU
  decides meaning and Authority

ChatGPT Structural Advisor
  observes, compares, recommends, records adopted decisions, verifies records, reviews

Claude Code
  implements only the verified adopted work unit and reports evidence

GitHub
  preserves observable receipts and projections

SHUKOU
  accepts and manually merges

Structural Advisor
  re-observes the after-state and prepares source updates
```

この順序は、特定のModelを恒久的な役職にするためではない。現在のDevelopment Bindingにおけるparticipant assignmentである。将来participantが交換されても、意味判断、実装、独立review、acceptanceおよびauditのownership分離は維持されなければならない。

---

# 21. Terminal declaration

```text
DEVELOPMENT_GOVERNANCE_DEFINED=true
SEMANTIC_AUTHORITY_PRESERVED=true
ROLE_BOUNDARIES_DEFINED=true
ADOPTION_HANDOFF_DEFINED=true
IMPLEMENTATION_TERMINAL_STATE_DEFINED=true
STRUCTURAL_REVIEW_PATH_DEFINED=true
HUMAN_ACCEPTANCE_AND_MANUAL_MERGE_PRESERVED=true
AFTER_STATE_REOBSERVATION_REQUIRED=true
VERTICAL_PROGRESSION_PRESERVED=true
REPOSITORY_ENFORCEMENT_GAP_PRESERVED_AS_FD_0001=true
```

本書は開発のAuthority経路を定める。個別work unitの実装Authority、Phase completion、merge receiptまたはDeferred Difference closureを単独では宣言しない。

---

# 22. Copilot Development Binding proposal (Issue #102)

SHUKOU requested a Kernel-compatible, interchangeable Copilot executor on
2026-10-01 JST. The direct request is recorded by the Structural Advisor in
[Issue #102](https://github.com/manosube/manosube-agent-civilization-os/issues/102)
with its observed base `391378d8aeb784a62cd2bc93d96538443c754a2d`.
The design is in `03_BINDING/COPILOT_PARTICIPATION.md`; repository guidance is
in `.github/copilot-instructions.md`.

This is a dedicated **proposal**, not a new active participant assignment.
`CURRENT_REPOSITORY_DEVELOPMENT_BINDING.md` and the pinned v0.2 machine policy
continue to select Claude Code and prohibit automated external review requests.
The proposed provider selection must evolve those existing owners and preserve
Human finding adoption, independent structural review, final acceptance and manual
merge. It must not create a second Kernel, Product Binding genesis or evaluator.

```text
COPILOT_DESIGN_STATUS=PREPARED_PENDING_INDEPENDENT_REVIEW_AND_HUMAN_ACCEPTANCE
COPILOT_EXECUTABLE_ADMISSION_IMPLEMENTED=false
COPILOT_RUNTIME_WORK_UNIT_PROVEN=false
CURRENT_BINDING_SUPERSEDED_BY_THIS_APPENDIX=false
COPILOT_REVIEW_AUTO_ENABLED=false
COPILOT_FINDING_AUTO_ADOPTION=false
ISSUE_102_CLOSE_ALLOWED=false
```

Claude Code is the next code implementation owner after the exact design is
accepted and a verified work-unit handoff is recorded. Instructions alone do not
authorize Copilot implementation or close the tracked Difference.

---

# 23. Copilot Development Binding machine-policy implementation (Issue #102, Decision 0003)

SHUKOU accepted the §22 design (PR #103 merged as `e2d686e6`) and recorded a
formal implementation handoff to Claude Code
([Issue #102 comment 5921931690](https://github.com/manosube/manosube-agent-civilization-os/issues/102#issuecomment-5921931690)).
This section records the resulting machine-policy revision: `GITHUB_COPILOT`
is now a second name eligible to hold the implementation executor capability,
alongside `CLAUDE_CODE`, with the identical `may`/`must_not` sets and handoff
transitions. The ratified decision superseding §22's referenced v0.2 policy is
`HUMAN-DECISION-CURRENT-REPOSITORY-OPERATING-BINDING-0003`
(`03_BINDING/DEVELOPMENT_BINDING_POLICY.json`, `policy_version=0.3`).

Eligibility is not execution authority. A new, separate gate --
`development_binding.executor_selection` -- evaluates whether a specific,
SHUKOU-granted, read-back-verified selection record binds one eligible
provider to one exact work unit, repository, branch and base/head SHA. Absent
such a record, `CLAUDE_CODE` remains the default and continues operating
exactly as it did before this Decision. Independent structural review,
SHUKOU's finding adoption, final acceptance and manual merge are unchanged and
apply identically to Copilot's output. Automated external review requests
remain prohibited by default.

```text
GOVERNING_ISSUE=#102
MACHINE_POLICY_REVISION_DECISION_ID=HUMAN-DECISION-CURRENT-REPOSITORY-OPERATING-BINDING-0003
GITHUB_COPILOT_ELIGIBLE_EXECUTOR=true
ELIGIBLE_PROVIDER_MEMBERSHIP_IS_NOT_EXECUTION_AUTHORITY=true
EXECUTOR_SELECTION_RECORD_REQUIRED_FOR_NON_DEFAULT_PROVIDER=true
CLAUDE_CODE_REMAINS_DEFAULT_EXECUTOR_PROVIDER=true
STRUCTURAL_REVIEW_AND_FINAL_ACCEPTANCE_OWNERSHIP_UNCHANGED=true
COPILOT_RUNTIME_WORK_UNIT_PROVEN=false
ISSUE_102_CLOSE_ALLOWED=false
```

This machine-policy revision does not itself prove a real, authorized Copilot
work unit was executed. That observation, its independent structural review,
and SHUKOU's disposition are the remaining Difference this section does not
close.

# 24. Copilot Development Binding closure reflow (Issue #102/#106, PR #104/#107)

This section records, as an independently GitHub-API-verified after-state
reflow, what §23 above left open. Its author (Claude Code, under the separate
Issue #105 implementation handoff below) did not perform the merge, the trial,
or the closure recorded here -- each fact was independently re-fetched from
the live GitHub API (issue/PR state, author, association, exact SHAs) before
being recorded, never taken from a relayed report alone.

PR #104 (§23's own implementation) was manually merged by SHUKOU at
`c8f7cecd13e32133e183df8b2131859c524207b1`. SHUKOU then formally adopted one
real, narrowly scoped Copilot work unit
(`ADOPTION_ID=ADOPT_I102_REAL_COPILOT_TRIAL_1`, [Issue #102 comment
5974753116](https://github.com/manosube/manosube-agent-civilization-os/issues/102#issuecomment-5974753116),
author `manosube`/`OWNER`): exactly one additional parametrized negative-control
case (an internal-CR unsafe path, `"tests\r/outside.py"`) in the existing
`test_development_binding_conformance.py` suite, no other file. GitHub cloud
Copilot assignment was unavailable (no license on this account); execution ran
instead through the local Copilot CLI (`GITHUB_COPILOT_CLI_1.0.91`) under
SHUKOU's own direct commit/push, with PR preparation and structural review by
the Structural Advisor. The result, PR #107, was independently re-fetched by
this section's author directly from the GitHub API: `merged=true`,
`merged_by=manosube`, `merged_at=2026-10-04T01:22:28Z`, base
`c8f7cecd13e32133e183df8b2131859c524207b1`, head
`57e6e0a3a955437abc0b3a6004180aa866ac94b5`, `additions=1`, `changed_files=1`
-- exactly matching the scope SHUKOU adopted.

After independent structural review, SHUKOU accepted and manually merged
PR #107 at `6e32bc7b3fddada77f8bcc75656e0453768a9a42`, then recorded the
closure reflow ([Issue #102 comment
5975381943](https://github.com/manosube/manosube-agent-civilization-os/issues/102#issuecomment-5975381943),
author `manosube`/`OWNER`). This section's author independently re-fetched
Issue #102 itself and confirmed `state=closed`, `state_reason=completed`,
`closed_by=manosube`, `closed_at=2026-10-04T01:26:34Z`.

```text
GOVERNING_ISSUE=#102
EXECUTION_TASK_ISSUE=#106
PR_104_MERGE_SHA=c8f7cecd13e32133e183df8b2131859c524207b1
REAL_TRIAL_ADOPTION_ID=ADOPT_I102_REAL_COPILOT_TRIAL_1
SELECTED_EXECUTOR_PROVIDER=GITHUB_COPILOT
EXECUTION_SURFACE=LOCAL_COPILOT_CLI
COMMIT_PUSH_OPERATOR=SHUKOU
PR_107_MERGED=true
PR_107_MERGE_SHA=6e32bc7b3fddada77f8bcc75656e0453768a9a42
ACCEPTED_MAIN_SHA=6e32bc7b3fddada77f8bcc75656e0453768a9a42
ISSUE_102_STATE=CLOSED
ISSUE_102_CLOSED_BY=manosube
COPILOT_RUNTIME_WORK_UNIT_PROVEN=true
ISSUE_102_CLOSE_ALLOWED=true
ISSUE_102_CLOSE_PERFORMED_BY=manosube
EXECUTOR_WORK_UNIT_RELEASED=true
NEW_EXECUTOR_AUTHORITY_GRANTED_BY_THIS_SECTION=false
GITHUB_API_INDEPENDENT_READBACK_PERFORMED_BY=CLAUDE_CODE
```

`COPILOT_RUNTIME_WORK_UNIT_PROVEN` and `ISSUE_102_CLOSE_ALLOWED` above
supersede §23's own stale `false` projections for exactly this fact; §23's
historical text is otherwise preserved unedited, per this document's own
append-only convention. The released work-unit selection grants no standing
executor authority: a future Copilot (or Claude Code) work unit still
requires its own explicit scope/base/head selection.

# 25. Issue #105 transport-independent runtime observation — implementation handoff record

SHUKOU formally adopted Issue #105
(`ADOPTION_ID=ADOPT_I105_ACTIONS_INDEPENDENT_AB_UNATTENDED_OBSERVATION`,
[comment 5975681963](https://github.com/manosube/manosube-agent-civilization-os/issues/105#issuecomment-5975681963),
author `manosube`/`OWNER`) and recorded an implementation handoff to Claude
Code ([comment 5975690640](https://github.com/manosube/manosube-agent-civilization-os/issues/105#issuecomment-5975690640),
author `manosube`/`OWNER`). Both were independently re-fetched from the GitHub
API before implementation began, confirming author, association, exact body,
and that `REVIEWED_MAIN_SHA`/`AUTHORIZED_BASE_MAIN` both equal
`6e32bc7b3fddada77f8bcc75656e0453768a9a42` -- the exact SHA
`agent/issue-105-runtime-observation-transports` branches from.

This is a Runtime-layer capability extension (a second, equally bounded
observation method plus a Human-ratified-grant-gated transport-selection
layer in front of the existing canonical route), not a `development_binding`
executor-eligibility change -- `GITHUB_COPILOT`/`CLAUDE_CODE` eligibility,
`executor_selection`, and every invariant §19-§24 above record are unchanged
by it. It is recorded here only because the adopted implementation handoff
itself names this file as part of the permitted, append-only project-source
inventory for this work unit.

```text
GOVERNING_ISSUE=#105
ADOPTION_ID=ADOPT_I105_ACTIONS_INDEPENDENT_AB_UNATTENDED_OBSERVATION
ADOPTION_COMMENT=5975681963
HANDOFF_COMMENT=5975690640
ADOPTION_HANDOFF_AUTHOR=manosube (OWNER)
AUTHORIZED_BASE_MAIN=6e32bc7b3fddada77f8bcc75656e0453768a9a42
DELIVERY_BRANCH=agent/issue-105-runtime-observation-transports
DEVELOPMENT_BINDING_POLICY_VERSION_CHANGED=false
EXECUTOR_ELIGIBILITY_CHANGED=false
MERGE_PERFORMED=false
ISSUE_105_CLOSE_PERFORMED=false
STOP_CONDITION=READY_FOR_STRUCTURAL_REVIEW
```

Full technical detail lives in `10_RUNTIME/RUNTIME_CONTRACT.md` §17 and
`docs/runtime_observation_transports.md`; this section records only that the
work unit was formally adopted, independently verified, and implemented under
that adoption -- not its design, which is this repository's Runtime owner's,
not Development Governance's, to state.

# 26. Issue #105 PR #108 Structural Review Round 1 correction — governance scope supplement

Independent structural review of PR #108
([comment 5978408215](https://github.com/manosube/manosube-agent-civilization-os/pull/108#issuecomment-5978408215))
found, among six other findings, a real regression this delivery's own new
workflow file caused in `tests/contract/governance/
test_merge_source_reflow_workflows.py` (F6), and that `10_RUNTIME/
RUNTIME_INDEX.md` had been edited outside the original handoff's own exact
permitted-file inventory (also F6). SHUKOU adopted both corrections
(`ADOPTION_ID=ADOPT_I105_PR108_SR1_F1_F6_E1`, [comment
5978467672](https://github.com/manosube/manosube-agent-civilization-os/pull/108#issuecomment-5978467672),
author `manosube`/`OWNER`), explicitly supplementing the correction handoff's
own permitted-file inventory with exactly those two paths. This section's
author independently re-fetched that comment and the correction handoff
([comment 5978475200](https://github.com/manosube/manosube-agent-civilization-os/pull/108#issuecomment-5978475200))
before acting on either.

```text
GOVERNING_ISSUE=#105
TARGET_PR=#108
ADOPTION_ID=ADOPT_I105_PR108_SR1_F1_F6_E1
SCOPE_SUPPLEMENT_PATHS=tests/contract/governance/test_merge_source_reflow_workflows.py,10_RUNTIME/RUNTIME_INDEX.md
GOVERNANCE_WORKFLOW_ENUMERATION_TEST_FIXED=true
RUNTIME_INDEX_PRIOR_SCOPE_GAP_DISCLOSED=true
DEVELOPMENT_BINDING_POLICY_VERSION_CHANGED=false
EXECUTOR_ELIGIBILITY_CHANGED=false
```

This is a Runtime-layer implementation correction with one narrow,
self-contained governance-surface touchpoint (a test file's own closed
workflow-filename enumeration); it does not change
`development_binding`'s own policy, eligibility, or any invariant §19–§25
above record.

# 27. Decision 0004 (Issue #109): a bounded, non-default-active Codex technical reviewer

SHUKOU adopted a concrete design binding Codex as a bounded technical
reviewer only ([adoption comment
6016745931](https://github.com/manosube/manosube-agent-civilization-os/issues/109#issuecomment-6016745931),
`ADOPTION_ID=ADOPT_I109_BOUNDED_WSL_CODEX_TECHNICAL_REVIEW_20261006`), then
issued the limited implementation handoff this section records
([comment
6017544351](https://github.com/manosube/manosube-agent-civilization-os/issues/109#issuecomment-6017544351)).
Unlike every prior entry in this file, this change **does** change
`development_binding`'s own ratified policy version -- `DEVELOPMENT_BINDING_
POLICY_VERSION_CHANGED=true` below is the honest exception to this file's
own running convention, not an oversight of it.

`03_BINDING/DEVELOPMENT_BINDING_POLICY.json` moved from `policy_version=0.3`
(Decision 0003) to `policy_version=0.4` (Decision 0004). The change adds
exactly one new, disjoint role (`CODEX`, capability
`BOUNDED_TECHNICAL_REVIEWER`, one action
`BOUNDED_TECHNICAL_REVIEW`) and the new top-level fields
`bounded_technical_reviewer`/`bounded_technical_review_action`/
`bounded_review_grant_authority`/`bounded_review_activation_default`/
`bounded_review_numeric_limits`/`bounded_review_additional_spending_
ceiling`. Every field §19-§26 above already governs --
`EXECUTOR_PROVIDERS`, `executor_provider_default`,
`executor_provider_selection_authority`, `automated_review_trigger_allowed`,
and `prohibited_automated_review_triggers` -- is unchanged by value; `CODEX`
is never added to `EXECUTOR_PROVIDERS`, and the native/unconditional
automated-review-trigger prohibition this file's own governance scope
already covers remains exactly as it was.

```text
GOVERNING_ISSUE=#109
ADOPTION_ID=ADOPT_I109_BOUNDED_WSL_CODEX_TECHNICAL_REVIEW_20261006
HANDOFF_COMMENT=6017544351
ADOPTION_HANDOFF_AUTHOR=manosube (OWNER)
AUTHORIZED_START_HEAD=b83fb6a0ee90ad48ddac8f2d1f1ed00bcaf8eb2b
DELIVERY_BRANCH=agent/issue-109-bounded-codex-technical-review
DEVELOPMENT_BINDING_POLICY_VERSION_CHANGED=true
DEVELOPMENT_BINDING_POLICY_VERSION=0.3->0.4
EXECUTOR_ELIGIBILITY_CHANGED=false
NEW_DISJOINT_ROLE_ADDED=CODEX
AUTOMATED_REVIEW_TRIGGER_PROHIBITION_UNCHANGED=true
ACTIVATION_DEFAULT=false
REAL_CODEX_MODEL_REQUEST_ALLOWED=false
MERGE_PERFORMED=false
ISSUE_109_CLOSE_PERFORMED=false
STOP_CONDITION=READY_FOR_STRUCTURAL_REVIEW
```

Full technical detail lives in `docs/decisions/ADR-0032-BOUNDED_TECHNICAL_
REVIEW_IS_NOT_ACCEPTANCE.md` and `docs/bounded_technical_review.md`; this
section records only that the policy version change was formally adopted,
independently verified, and implemented under that adoption, and that it
narrows to exactly the fields named above.

## 27.1 PR #112 Structural Review corrections (Rounds 1-3)

Three independent Structural Review rounds against the Draft PR this Decision opened
(`#112`) found P1 defects in the implementation above and were formally adopted and
corrected on the same delivery branch, without ever widening `development_binding`'s own
ratified policy version beyond `0.4` again. No round changes any field this section's
own `GOVERNING_ISSUE=#109` block names; all three are implementation corrections to the
code this Decision already authorized, not a further policy change.

```text
ROUND_1_ADOPTION_ID=ADOPT_I109_PR112_SR1_F1_F5_E1_20261007
ROUND_1_REVIEW_COMMENT=6019024445
ROUND_1_CORRECTION_HEAD=9e61b3f562643ece89290a50719a3a73af48aae9
ROUND_2_ADOPTION_ID=ADOPT_I109_PR112_SR2_F1_F6_E1_20261007
ROUND_2_REVIEW_COMMENT=6021757577
ROUND_2_REVIEWED_HEAD=9e61b3f562643ece89290a50719a3a73af48aae9
ROUND_3_ADOPTION_ID=ADOPT_I109_PR112_SR3_F1_F5_E1_20261007
ROUND_3_REVIEW_COMMENT=6030487245
ROUND_3_REVIEWED_HEAD=bab627cb2a4827f22f9b64e70c188fe4fbc7da32
DEVELOPMENT_BINDING_POLICY_VERSION_CHANGED=false
MERGE_PERFORMED=false
ISSUE_109_CLOSE_PERFORMED=false
STOP_CONDITION=READY_FOR_STRUCTURAL_REVIEW
```

Full finding-by-finding detail lives in `docs/bounded_technical_review.md`§§11,13,14 and
`docs/project_sources/03_CURRENT_DEVELOPMENT_STATE.md`§§99.3,99.4,99.5; this section records
only the governance-relevant fact that all three rounds were formally adopted, independently
re-verified against the GitHub record before correction began, and left this Decision's
own ratified policy fields unchanged. §99.5 also carries an append-only correction to a
factual mis-description of Round 1's own verification scope that had appeared in both the
PR body and `docs/bounded_technical_review.md`§13 since Round 2.

## 27.2 PR #112 Structural Review Round 4 correction

A fourth independent Structural Review round against the same Draft PR (`#112`) found five
further P1 defects, formally adopted and corrected on the same delivery branch, without
widening `development_binding`'s own ratified policy version beyond `0.4`. This round's own
independent review also withdrew Round 3's own E1 (an erroneous demand for a nonexistent
`tests/unit/independent_verification` suite) as a reviewer error; the adoption record
explicitly excludes that withdrawn E1 from this round's adopted findings. No finding changes
any field this section's own `GOVERNING_ISSUE=#109` block names; all five are implementation
corrections to code this Decision already authorized, not a further policy change.

```text
ROUND_4_ADOPTION_ID=ADOPT_I109_PR112_SR4_F1_F5_20261007
ROUND_4_REVIEW_COMMENT=6032479337
ROUND_4_REVIEWED_HEAD=5a33e4b58aa3dd008a48ccf4e476d6bffddba8f9
ROUND_4_WITHDRAWN_E1=true
DEVELOPMENT_BINDING_POLICY_VERSION_CHANGED=false
MERGE_PERFORMED=false
ISSUE_109_CLOSE_PERFORMED=false
STOP_CONDITION=READY_FOR_STRUCTURAL_REVIEW
```

Full finding-by-finding detail lives in `docs/bounded_technical_review.md`§15 and
`docs/project_sources/03_CURRENT_DEVELOPMENT_STATE.md`§99.6; this section records only the
governance-relevant fact that this round was formally adopted, independently re-verified
against the GitHub record before correction began, explicitly excluded the withdrawn E1, and
left this Decision's own ratified policy fields unchanged.

## 27.3 PR #112 Structural Review Round 5 correction

A fifth independent Structural Review round against the same Draft PR (`#112`) found five
further P1 defects, formally adopted and corrected on the same delivery branch, without
widening `development_binding`'s own ratified policy version beyond `0.4`. This round's own
independent review framed every finding as an SR4 completion check -- unfinished portions of
the already-adopted SR4 scope, never new architecture or a widened boundary; the Objective
Return Gate (§9.3) triggered given the repeated correction, with the objective remaining
bounded post-implementation technical review and native GitHub review as the primary reuse
path, never a new mechanism. No finding changes any field this section's own
`GOVERNING_ISSUE=#109` block names; all five are implementation corrections to code this
Decision already authorized, not a further policy change.

```text
ROUND_5_ADOPTION_ID=ADOPT_I109_PR112_SR5_F1_F5_20261007
ROUND_5_REVIEW_COMMENT=6034603745
ROUND_5_REVIEWED_HEAD=a265892a6e82dbdeafb7fe88566c54e2f549cb58
DEVELOPMENT_BINDING_POLICY_VERSION_CHANGED=false
MERGE_PERFORMED=false
ISSUE_109_CLOSE_PERFORMED=false
STOP_CONDITION=READY_FOR_STRUCTURAL_REVIEW
```

## 27.4 PR #112 Structural Review Round 6 correction

A sixth independent Structural Review round against the same Draft PR (`#112`) found four
further P1 defects, formally adopted and corrected on the same delivery branch, without
widening `development_binding`'s own ratified policy version beyond `0.4`. This round's own
independent review again framed every finding as an SR5 completion check -- remaining
portions of the already-adopted SR5 scope, never new owners or a widened mechanism; the
Objective Return Gate (§9.3) remained applicable given the repeated correction, with the
objective remaining bounded post-implementation technical review and native GitHub review as
the primary reuse path, Human acceptance/merge kept separate, additional spending held at
0円. No finding changes any field this section's own `GOVERNING_ISSUE=#109` block names; all
four are implementation corrections to code this Decision already authorized, not a further
policy change. F4 did not deliver the reviewer's first-offered option (a complete, consolidated
filesystem boundary) -- it delivered the reviewer's explicitly-sanctioned second option (treat
the incomplete boundary as unavailable and refuse local dispatch before send, falling back to
the already-delivered `REUSE_NATIVE_ONLY` path), which this section records accurately rather
than overclaiming the former.

```text
ROUND_6_ADOPTION_ID=ADOPT_I109_PR112_SR6_F1_F4_20261007
ROUND_6_REVIEW_COMMENT=6036263982
ROUND_6_ADOPTION_COMMENT=6036280369
ROUND_6_HANDOFF_COMMENT=6036300862
ROUND_6_REVIEWED_HEAD=6d4aca7457b1aaca202d7fe39efb6c5949aafa5a
DEVELOPMENT_BINDING_POLICY_VERSION_CHANGED=false
MERGE_PERFORMED=false
ISSUE_109_CLOSE_PERFORMED=false
STOP_CONDITION=READY_FOR_STRUCTURAL_REVIEW
```

Full finding-by-finding detail lives in `docs/bounded_technical_review.md`§17 and
`docs/project_sources/03_CURRENT_DEVELOPMENT_STATE.md`§99.8; this section records only the
governance-relevant fact that this round was formally adopted, independently re-verified
against the GitHub record before correction began, and left this Decision's own ratified
policy fields unchanged.

Full finding-by-finding detail lives in `docs/bounded_technical_review.md`§16 and
`docs/project_sources/03_CURRENT_DEVELOPMENT_STATE.md`§99.7; this section records only the
governance-relevant fact that this round was formally adopted, independently re-verified
against the GitHub record before correction began, and left this Decision's own ratified
policy fields unchanged.

## 27.5 PR #112 Structural Review Round 7 correction

A seventh independent Structural Review round against the same Draft PR (`#112`) found three
further P1 defects, formally adopted and corrected on the same delivery branch, without
widening `development_binding`'s own ratified policy version beyond `0.4`. This round's own
independent review again framed every finding as an SR6 completion check -- remaining
portions of the already-adopted SR6 scope, never new owners or a widened mechanism; the
formal adoption itself was recorded as SHUKOU's own direct human decision in a ChatGPT
session, not an independent AI adoption -- the Structural Advisor's own comment records that
Human decision rather than making one of its own. No finding changes any field this section's
own `GOVERNING_ISSUE=#109` block names; all three are implementation corrections to code this
Decision already authorized, not a further policy change.

```text
ROUND_7_ADOPTION_ID=ADOPT_I109_PR112_SR7_F1_F3_20261008
ROUND_7_REVIEW_COMMENT=6037312445
ROUND_7_ADOPTION_COMMENT=6048971998
ROUND_7_HANDOFF_COMMENT=6048980699
ROUND_7_REVIEWED_HEAD=3243a268fd7f53562b2a9bea3b332f3a19ba7a66
DEVELOPMENT_BINDING_POLICY_VERSION_CHANGED=false
MERGE_PERFORMED=false
ISSUE_109_CLOSE_PERFORMED=false
STOP_CONDITION=READY_FOR_STRUCTURAL_REVIEW
```

Full finding-by-finding detail lives in `docs/bounded_technical_review.md`§18 and
`docs/project_sources/03_CURRENT_DEVELOPMENT_STATE.md`§99.9; this section records only the
governance-relevant fact that this round was formally adopted, independently re-verified
against the GitHub record before correction began, and left this Decision's own ratified
policy fields unchanged.

## 27.6 PR #112 Structural Review Round 8 correction

An eighth independent Structural Review round against the same Draft PR (`#112`) found three
further P1 defects, formally adopted and corrected on the same delivery branch, without
widening `development_binding`'s own ratified policy version beyond `0.4`. This round's own
independent review again framed every finding as an SR7 completion check -- residual portions
of the already-adopted SR7 scope, never new owners or a widened mechanism. No finding changes
any field this section's own `GOVERNING_ISSUE=#109` block names; all three are implementation
corrections to code this Decision already authorized, not a further policy change. The net
effect of this round is that a real local review process launch, and the external/CLI
outcome-recording route's own `CONFIRMED_CANCELLATION` label, are now genuinely,
unconditionally unavailable through every surface this delivery's code exposes -- the
Objective Return Gate's own sanctioned minimal path ("native GitHub review reuse remains
primary; unsupported local production launch can remain unavailable, and unprovable unknown
outcomes remain retained... Refusal without caller exceptions is an acceptable correction
outcome").

```text
ROUND_8_ADOPTION_ID=ADOPT_I109_PR112_SR8_F1_F3_20261008
ROUND_8_REVIEW_COMMENT=6050757530
ROUND_8_ADOPTION_COMMENT=6050838453
ROUND_8_HANDOFF_COMMENT=6050848323
ROUND_8_REVIEWED_HEAD=8df72921ef75cf99222a3a7e492ac444f010bf88
DEVELOPMENT_BINDING_POLICY_VERSION_CHANGED=false
MERGE_PERFORMED=false
ISSUE_109_CLOSE_PERFORMED=false
STOP_CONDITION=READY_FOR_STRUCTURAL_REVIEW
```

Full finding-by-finding detail lives in `docs/bounded_technical_review.md`§19 and
`docs/project_sources/03_CURRENT_DEVELOPMENT_STATE.md`§99.10; this section records only the
governance-relevant fact that this round was formally adopted, independently re-verified
against the GitHub record before correction began, and left this Decision's own ratified
policy fields unchanged.
