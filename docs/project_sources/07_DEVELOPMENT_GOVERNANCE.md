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

# 9. Work-unit contract

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

# 10. Review contract

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

# 11. Phase acceptance and merge gate

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

# 12. Change of scope and changed world

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

# 13. Communication and time protocol

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

# 14. Failure and blocker handling

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

# 15. Information-source maintenance

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

# 16. Current repository-enforcement status

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

# 17. Governance change rule

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

# 18. Canonical governance invariants

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

# 19. Operational summary

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

# 20. Terminal declaration

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
