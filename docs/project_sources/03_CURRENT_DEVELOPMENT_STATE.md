# MANOSUBE Agent Civilization OS

## Current Development State

```text
DOC_TYPE=CURRENT_DEVELOPMENT_STATE
DOCUMENT_ID=CURRENT-DEVELOPMENT-STATE-0001
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
STATUS=OBSERVED_CURRENT_STATE
SOURCE_AUTHORITY_CLASS=DATED_REPOSITORY_PROJECTION
HUMAN_AUTHORITY=SHUKOU
REPOSITORY=manosube/manosube-agent-civilization-os
DEFAULT_BRANCH=main
OBSERVED_AT_UTC=2026-09-07T10:42:45Z
COMPLETED_THROUGH_PHASE=12
CURRENT_PHASE=13_INDEPENDENT_VERIFICATION
CURRENT_PHASE_STATE=ROUND_3_DELIVERED_AWAITING_STRUCTURAL_REVIEW
PHASE_13_COMPLETE=false
PHASE_14_ALLOWED=false
```

**Bounded addendum (2026-09-07, R6-R1 companion update -- see §5.2 rows 5-9):** the header
block and sections 5-8 above/below this note still project the repository as of
`OBSERVED_AT_UTC` (Round 3 delivered). Rounds 4 through 6-R1 have since been adopted on
Issue #51 and are implemented on PR #52; §5.2's table records only the adoption lineage fact,
independently re-observed
via the GitHub API at the time of this edit. It does not re-run the full current-state
projection this document otherwise performs (PR head/commit/file counts, structural review
status, blocker table) -- that remains a separate, later full re-observation. This addendum
exists to satisfy `03_BINDING/MERGE_SOURCE_REFLOW_CONTRACT.md` section 2's own requirement:
a `kernel_surface` change must be paired with a `docs/project_sources/*.md` update in the same
diff, and `ADOPT_P13_R6_R1_EVIDENCE_OWNER_GLOBAL_PROVENANCE_ENFORCEMENT`'s own
`SOURCE_IMPACT_GATE_REQUIRED` clause names this obligation explicitly.

---

# 0. Purpose

本書は、MANOSUBE Agent Civilization OSの**現在の開発状態**を、指定時点のGitHub実在状態から投影する。

本書が所有するものは次である。

```text
current default-branch SHA
completed-through Phase
current Phase
active Issue and Pull Request
current implementation HEAD
adopted correction state
review and check observations
current-route blockers
next authorized action
stale status declarations
```

本書は、憲法、Phase順序、恒久的なAcceptance履歴、repository target構造またはDeferred Differenceの正準所有者ではない。

```text
CURRENT_STATE
≠ CONSTITUTION

CURRENT_STATE
≠ ROADMAP

CURRENT_STATE
≠ ACCEPTANCE_LEDGER

CURRENT_STATE
≠ LIVE_GITHUB
```

本書はdated projectionである。判断前に`OBSERVED_AT_UTC`を確認し、GitHub状態が変化していれば再観測して更新しなければならない。

---

# 1. Observation envelope

## 1.1 Observed surfaces

```text
GitHub repository metadata
default branch and latest merge commit
open Issues
Issue comments carrying SHUKOU adoption
open Pull Requests
Pull Request base and head SHAs
Pull Request review submissions and review threads
commit status observations
repository README on main
```

## 1.2 Evidence classes

本書では、GitHub上の記述を次の4種類に分離する。

| Class | Meaning | May prove completion alone? |
|---|---|---:|
| `OBSERVED_GITHUB_FACT` | state、SHA、URL、timestamp等のAPI観測値 | No |
| `HUMAN_ADOPTION_RECORD` | SHUKOUが明示的に採択した意味論・Authority | No |
| `IMPLEMENTER_REPORTED_EVIDENCE` | PR本文に記録されたtest、lint、worktree等 | No |
| `ACCEPTANCE_RECEIPT` | Human acceptance、merge receipt、after-state re-observationの連鎖 | Yes, required as a set |

```text
PR_BODY_CLAIM
≠ INDEPENDENT_OBSERVATION

MERGEABLE=true
≠ MERGE_ALLOWED=true

OPEN_PR
≠ ACTIVE_AUTHORITY

CODE_DELIVERED
≠ PHASE_COMPLETE
```

---

# 2. Executive current state

```text
PROJECT_STATUS=ACTIVE_DEVELOPMENT
COMPLETED_THROUGH_PHASE=12
CURRENT_PHASE=13_INDEPENDENT_VERIFICATION
CURRENT_PHASE_ISSUE=#51
CURRENT_PHASE_PR=#52
CURRENT_PHASE_STATE=ROUND_3_DELIVERED_AWAITING_STRUCTURAL_REVIEW

PHASE_12_TEMPORARY_AGENT_LIFECYCLE=COMPLETE
TEMPORARY_AGENT_EXECUTION_CONTRACT=DEFERRED_REMAINING_DIFFERENCE
PHASE_12_REOPENED=false

PHASE_13_COMPLETE=false
PHASE_14_ALLOWED=false
MERGE_RECOMMENDED=false
MERGE_ALLOWED=false
```

現在のOSはPhase 12まで受け入れ済みであり、Phase 13のIndependent Verificationを実装中である。

PR #52にはRound 1 correctionまでを含む実装HEADが存在する。しかし、そのHEADを対象とするRound 2のHuman adoptionが後から記録されており、Round 2 correctionはまだ新しいHEADとして配達されていない。

したがって、現在状態を次のいずれかとして表現してはならない。

```text
PHASE_13_COMPLETE=true
PHASE_13_AWAITING_ONLY_MERGE=true
PHASE_14_READY=true
INDEPENDENT_VERIFICATION_ACCEPTED=true
```

---

# 3. Default branch state

| Field | Observed value |
|---|---|
| Repository | [`manosube/manosube-agent-civilization-os`](https://github.com/manosube/manosube-agent-civilization-os) |
| Visibility | Public |
| Default branch | `main` |
| Current accepted base | `1d41f7d1e79441249382be07e8d8dbed618331c8` |
| Base meaning | Merge commit of PR #58; Merge Source Reflow governance (Issue #57) |
| Commit statuses observed | None registered |

```text
MAIN_ACCEPTED_BASE_SHA=1d41f7d1e79441249382be07e8d8dbed618331c8
MAIN_PHASE_12_RECEIPT=true
MAIN_PHASE_13_CODE=false
```

Phase 0からPhase 12までの個別Issue、PR、merge SHA、EvidenceおよびHuman acceptanceは、`05_PHASE_ACCEPTANCE_LEDGER.md`が所有する。本書は現在地を示すために「Phase 12まで完了」を投影するが、その履歴を複製しない。

---

# 4. Completed-through capability boundary

| Phase range | Current status | Boundary |
|---|---|---|
| 0–8 | Accepted before current observation | Canonical Kernel cycle and natural vertical proof |
| 9 | Accepted before current observation | Project Binding |
| 10 | Accepted before current observation | Boot restores project, authority and state context |
| 11 | Accepted before current observation | Removable CLI projection |
| 12 | Accepted at PR #50 merge | Temporary Agent lifecycle: safe start, lifecycle transition and release |
| 13 | In progress | Independent Verification over canonical Evidence |

Phase 12の完成範囲はlifecycleであり、実モデルAgentによるChange execution全体ではない。

```text
TEMPORARY_AGENT_CAN_BE_STARTED_AND_RELEASED_SAFELY=true
TEMPORARY_AGENT_CAN_EXECUTE_REAL_MODEL_WORK=false
TEMPORARY_AGENT_EXECUTION_CONTRACT_DEFERRED=true
```

Agent Execution Contractは、モデル非依存の実行入力、Capability選択、Authority照合およびEvidence candidate正規化を扱うDeferred Remaining Differenceである。Phase 12を再オープンせず、最初の実Agent/model adapter投入前、遅くともPhase 16設計時までに配置を正式決定する。

---

# 5. Current Phase work unit

## 5.1 Issue #51

| Field | Observed value |
|---|---|
| Issue | [#51 — Phase 13 Independent Verification over canonical Evidence](https://github.com/manosube/manosube-agent-civilization-os/issues/51) |
| State | Open |
| Phase | 13 — Independent Verification |
| Base required | `main@36b06d88cf779d9f04b79e41022b42d1f3d47510` |
| Implementation owner | Claude Code |
| Structural review owner | ChatGPT Structural Advisor |
| Acceptance owner | SHUKOU |
| Phase 14 permission | `false` |

Issue本文に残る初期の`DESIGNED_AWAITING_HUMAN_ADOPTION`または`IMPLEMENTATION_ALLOWED=false`は、後続の明示的なSHUKOU adoptionにより現在状態ではない。Issue本文だけを読んで実装Authorityを判断してはならない。

## 5.2 Human adoption lineage

| Order | Adoption | Reviewed target | Effect |
|---:|---|---|---|
| 1 | [`ADOPT_PHASE_13_INDEPENDENT_VERIFICATION`](https://github.com/manosube/manosube-agent-civilization-os/issues/51#issuecomment-5562611201) | `main@36b06d8…` | Initial Phase 13 implementation authorized |
| 2 | [`ADOPT_P13_R1_VERIFIER_BINDING_CANONICAL_SELECTION_AND_DEEP_IMMUTABILITY`](https://github.com/manosube/manosube-agent-civilization-os/issues/51#issuecomment-5562869144) | PR #52 head `5d071a3…` | Round 1 minimal forward correction authorized |
| 3 | [`ADOPT_P13_R2_CANONICAL_SELECTION_EVIDENCE_HANDOFF_AND_UNAVAILABLE_PROVENANCE`](https://github.com/manosube/manosube-agent-civilization-os/issues/51#issuecomment-5563356966) | PR #52 head `4697550…` | Round 2 minimal forward correction authorized |
| 4 | [`ADOPT_P13_R3_AUTHORITY_OWNED_VERIFIER_SELECTION_DECISION`](https://github.com/manosube/manosube-agent-civilization-os/issues/51#issuecomment-5563790496) | PR #52 head `becc1c7…` | Round 3 minimal forward correction authorized |
| 5 | [`ADOPT_P13_R4_CANONICAL_GRANT_PROVENANCE_BINDING`](https://github.com/manosube/manosube-agent-civilization-os/issues/51#issuecomment-5570217097) | PR #52 head `2be9645…` | Round 4 minimal forward correction authorized (P13-R3-F2, Authority Provenance Bypass) |
| 6 | [`ADOPT_P13_R5_CANONICAL_HUMAN_GRANT_DECLARATION_ANCHOR`](https://github.com/manosube/manosube-agent-civilization-os/issues/51#issuecomment-5571089236) | PR #52 head `7119ffd…` | Round 5 minimal forward correction authorized (canonical Human Grant Declaration anchor) |
| 7 | [`ADOPT_P13_R5_R1_SIGNED_HUMAN_DECLARATION_AND_SINGLE_COMMITTER`](https://github.com/manosube/manosube-agent-civilization-os/issues/51#issuecomment-5571758907) | PR #52 head `a392df6…` | Round 5-R1 minimal forward correction authorized (signed declaration anchor + single shared committer) |
| 8 | [`ADOPT_P13_R6_PROVENANCE_COMPLETE_EVIDENCE_HANDOFF`](https://github.com/manosube/manosube-agent-civilization-os/issues/51#issuecomment-5572707862) | PR #52 head `dbb769c…` | Round 6 minimal forward correction authorized (provenance-complete Evidence handoff) |
| 9 | [`ADOPT_P13_R6_R1_EVIDENCE_OWNER_GLOBAL_PROVENANCE_ENFORCEMENT`](https://github.com/manosube/manosube-agent-civilization-os/issues/51#issuecomment-5573559225) | PR #52 head `0d7f4a6…`; `main@e931743…` | Round 6-R1 minimal forward correction authorized (global Evidence-owner provenance enforcement, reverses Round 6's handoff-only layering; also requires main reintegration and this source-impact-gate correction) |

Rows 5-9 were independently re-observed via the GitHub API (`issue_read.get_comments`,
Issue #51) at the time of this addendum; each `Reviewed target` head SHA is the adoption
comment's own `REVIEWED_HEAD`, taken verbatim from the comment body. None of Rounds 4-6-R1
has yet had an independent 構造参謀 structural-review pass recorded against its own
delivered head on Issue #51 -- the same open condition §7.1 already records for Round 3's
own successor heads, now extended through Round 6-R1's own delivered head.

Round 2 adoptionは三つの意味論を凍結する。

```text
P13_R2_F1=VERIFIER_SELECTION_MUST_RESOLVE_THROUGH_CANONICAL_AUTHORITY_OWNER
P13_R2_F2=VERIFICATION_RESULT_MUST_HANDOFF_TO_EXISTING_EVIDENCE_OWNER
P13_R2_F3=UNAVAILABLE_REQUIRES_DISTINGUISHABLE_PROVENANCE
```

Round 3 adoptionは、既存Authority ownerを拡張した一つのVerifier Selection Decision surfaceを凍結する（P13-R2-F1をnarrowingではなくresolveする位置づけ）。

```text
P13_R3_F1=AUTHORITY_OWNED_VERIFIER_SELECTION_DECISION_REQUIRED
```

2026-09-07T10:42:45Z時点の独立GitHub API再観測（`ADOPT_MSR_R3_COMPLETE_PROJECTION_REFRESH`、Issue #57）によれば、PR #52はRound 3実装後、自己発見のcorrectionによりさらに先へ進んでいる。この事実はIMPLEMENTER_REPORTED_EVIDENCEとしてPR #52本文が報告するものであり、`OBSERVED_GITHUB_FACT`（head SHA、commit数、changed files数）を除き、構造参謀による独立再観測は未実施である。

```text
PR_52_ROUND_3_INITIAL_HEAD=b09a684
PR_52_SELF_CAUGHT_CORRECTION_HEAD=2be9645
PR_52_SELF_CAUGHT_CORRECTION_STRUCTURALLY_REVIEWED=false
```

---

# 6. Pull Request #52 state

| Field | Observed value |
|---|---|
| Pull Request | [#52 — Phase 13: Independent Verification over canonical Evidence](https://github.com/manosube/manosube-agent-civilization-os/pull/52) |
| State | Open |
| Draft | No |
| Merged | No |
| GitHub mergeable observation | `true` (`mergeable_state=clean`) |
| Base | `main@36b06d88cf779d9f04b79e41022b42d1f3d47510` |
| Head branch | `agent/issue-51-independent-verification` |
| Delivered head | `2be9645cdfafb48e6f30ac968938fd15fb87717d` |
| Commits | 5 |
| Changed files | 22 |
| Additions / deletions | `4026 / 22` |
| Last observed PR update | `2026-09-07T02:38:04Z` |

GitHub APIが未マージPRへ返す`merge_commit_sha`候補はmerge receiptではない。本書はそれをaccepted SHAとして記録しない。

## 6.1 Implementer-reported verification

PR本文は現HEAD `2be9645…`について次を報告している（2026-09-07T10:42:45Z、Issue #57の独立GitHub API再観測時点）。

```text
INDEPENDENT_VERIFICATION_TARGETED_SUITE=91 passed (19 static + 72 integration, Round 3 included)
AUTHORITY_VERIFIER_SELECTION_TARGETED_SUITE=50 passed (new, Round 3)
AUTHORITY_VERIFIER_SELECTION_INPUT_TOTALITY_SUITE=283 passed (new, Round 3 self-caught correction)
COMBINED_TARGETED_SUITE=3645 passed (independent_verification + authority + adjacent, post-correction)
FULL_SUITE=18837 passed, 0 failed, 11 skipped (post-correction, per PR body)
RUFF_CHECK=178 repo-wide errors -- matches baseline exactly, 0 net new (per PR body)
RUFF_FORMAT=113 repo-wide files would be reformatted (baseline 114); every new/touched file format-clean (per PR body)
MYPY=217 repo-wide errors -- matches baseline exactly, 0 net new (per PR body)
SCHEMA_VALIDATION=PASS (49 schemas total, 6 Authority schemas -- 2 new, per PR body)
WORKTREE_CLEAN=true (per PR body)
```

これは重要な`IMPLEMENTER_REPORTED_EVIDENCE`であり、Round 2とRound 3双方のcorrectionを含むが、本書はそれらの試験結果自体を独立再実行していない。Human acceptanceまたはmerge receiptでもない。

```text
REPORTED_TESTS_PASS=true
ROUND_2_CORRECTION_INCLUDED=true
ROUND_3_CORRECTION_INCLUDED=true
CURRENT_HEAD_ACCEPTED=false
CURRENT_HEAD_INDEPENDENTLY_RETESTED_BY_THIS_DOCUMENT=false
```

**Bounded addendum (2026-09-08, Phase 14 companion update -- see §15 below):** sections 2-9
and 14 above still project the repository as of the original `OBSERVED_AT_UTC`
(Phase 13, Round 3 delivered, PR #52 open). §15 below independently re-observes, via local
`git log` against `origin/main`, that PR #52 (Phase 13, Issue #51) has since merged and Phase
13 is complete, that PR #61 (FD-0003, Issue #60) has also since merged, and that Phase 14
(Identity-Preserving GitHub Projection, Issue #62) is now the current Phase, SHUKOU-adopted
under `ADOPT_P14_D001_PROJECTION_ENVELOPE_IMPLEMENTATION`. It does not re-run the full
current-state projection sections 2-9 and 14 otherwise perform (PR head/commit/file counts,
structural review status, blocker table) for either Phase 13's own closing state or Phase 14's
own opening state -- that remains a separate, later full re-observation. This addendum exists
to satisfy `03_BINDING/MERGE_SOURCE_REFLOW_CONTRACT.md` section 2's own requirement: a
`kernel_surface` change (this delivery's own `src/manosube_agent_civilization/projection/` and
`01_SCHEMA/projection/` additions) must be paired with a `docs/project_sources/*.md` update in
the same diff.

---

# 7. Review and check state

## 7.1 Structural review

最新の構造review採択はRound 3（[`ADOPT_P13_R3_AUTHORITY_OWNED_VERIFIER_SELECTION_DECISION`](https://github.com/manosube/manosube-agent-civilization-os/issues/51#issuecomment-5563790496)）であり、対象headは`becc1c7d…`であった。実装はその後`b09a684…`へ配達され、自己発見のcorrectionにより現HEAD `2be9645c…`へ到達した。`b09a684…`・`2be9645c…`のいずれについても、構造参謀による独立構造reviewはまだIssue #51に記録されていない。

```text
CURRENT_HEAD_STRUCTURAL_FINDINGS_ADOPTED=true (最新採択対象head: becc1c7d…, Round 3)
CURRENT_HEAD_STRUCTURAL_REVIEW_PASS=false (現HEAD 2be9645c…は未review)
NEXT_STRUCTURAL_REVIEW_REQUIRED_AFTER_NEW_HEAD=true
```

## 7.2 GitHub Codex review observation

PR #52には、旧HEAD `5d071a30a03581d067002d98fb496db43ca06f77`を対象としたCodex reviewが一件存在する。

| Finding | Severity | Current thread observation |
|---|---:|---|
| Callback must bind to selected verifier | P1 | Unresolved |
| Claimed selection Authority must be canonically validated | P1 | Unresolved |
| Unsupported mutable values must fail closed | P2 | Unresolved; line outdated |

この外部reviewは有用な観測であるが、Issue #51の正式Authorityではない。初期adoptionは`CODEX_REVIEW_TRIGGER_ALLOWED=false`を固定しており、新しいCodex reviewを要求してはならない。

```text
CODEX_REVIEWED_HEAD=5d071a30a03581d067002d98fb496db43ca06f77
CURRENT_PR_HEAD=2be9645cdfafb48e6f30ac968938fd15fb87717d
CURRENT_HEAD_EXTERNAL_REVIEW=false
OPEN_REVIEW_THREAD_COUNT=3
EXTERNAL_REVIEW_IS_COMPLETION_GATE=false
```

## 7.3 Commit checks

現HEADおよびaccepted main baseに、GitHub commit statusは観測されていない。

```text
GITHUB_STATUS_RECEIPT_PRESENT=false
PR_BODY_TEST_REPORT_PRESENT=true
```

CI statusが存在しないことはtest failureを意味しない。同時に、PR本文のtest報告をGitHub CI receiptへ読み替えてもならない。

---

# 8. Current-route blockers

Phase 13 exitまでのblockerは次である。2026-09-07T10:42:45Z時点の独立GitHub API再観測（`ADOPT_MSR_R3_COMPLETE_PROJECTION_REFRESH`、Issue #57）により、PR #52はcommit数2→5・changed files 8→22という`OBSERVED_GITHUB_FACT`を伴ってRound 2およびRound 3のforward correction、さらに1件の自己発見correctionまでpushされていることを確認した。この観測によりP13-B01は「pushされたか」という closure condition自体は満たすが、pushされた内容の正しさは引き続きIMPLEMENTER_REPORTED_EVIDENCEに留まり、構造参謀による独立再観測を経ていない。

| ID | Classification | Blocker | Closure condition | Status |
|---|---|---|---|---|
| `P13-B01` | `CURRENT_ROUTE_BLOCKER` | Round 2の採択済み3要件が現HEADに未実装 | 同一branch・同一PRへminimal forward correctionをpush | Closed（`OBSERVED_GITHUB_FACT`: push確認済み。Round 3・自己発見correctionまで確認） |
| `P13-B02` | `REQUIRED_PHASE_GATE` | Round 3後の新HEAD（`2be9645c…`、自己発見correction含む）に対する構造review passがない | 構造参謀が新HEADを独立再観測し、blocker 0を確認 | Open |
| `P13-B03` | `REQUIRED_PHASE_GATE` | SHUKOU acceptanceがない | SHUKOUが明示的にPhase 13を受入 | Open |
| `P13-B04` | `REQUIRED_PHASE_GATE` | merge receiptとafter-state re-observationがない | PR #52 merge SHAを確認し、mainを再観測 | Open |

```text
CURRENT_ROUTE_BLOCKER_COUNT=4
OPEN_ROUTE_BLOCKER_COUNT=3
PHASE_13_EXIT_ALLOWED=false
```

Round 2 implementationが既存Authority ownerの不足により不可能な場合、Claude Codeは代替owner、registry、token、cacheまたは隠れたstateを発明してはならない。停止して不足surfaceを報告し、Human Decisionを待つ。

---

# 9. Next authorized action

2026-09-07T10:42:45Z時点の独立GitHub API再観測（Issue #57のbounded refresh）によれば、`OBSERVED_GITHUB_FACT`としてRound 2 correction・Round 3 correction・自己発見correctionはいずれも既にpush済みである（現HEAD `2be9645c…`）。したがって`APPLY_ADOPTED_PHASE_13_ROUND_2_CORRECTIONS`は完了済みの投影であり、現在の正規の次作業は次の一つに更新する。

```text
NEXT_ACTION=STRUCTURAL_REVIEW_OF_CURRENT_HEAD
NEXT_IMPLEMENTATION_OWNER=NONE_PENDING_ON_ISSUE_51
NEXT_REVIEW_OWNER=CHATGPT_STRUCTURAL_ADVISOR
REVIEW_TARGET_HEAD=2be9645cdfafb48e6f30ac968938fd15fb87717d
NEW_BRANCH_ALLOWED=false
NEW_PR_ALLOWED=false
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_14_ALLOWED=false
EXTERNAL_REVIEW_REQUEST_ALLOWED=false
```

この`NEXT_ACTION`はPR #52本文自身の停止宣言（`READY_FOR_STRUCTURAL_REVIEW`、Claude Codeはmerge・close・Phase 14着手をしない）をOBSERVED_GITHUB_FACTとして反映したものであり、Phase 13の受入や完了を決定するものではない。

配達後の順序は次である。

```text
Claude Code pushes Round 2/Round 3/self-caught corrections (already observed complete)
→ records delivered HEAD and verification report (already observed complete)
→ stops (already observed complete)
→ ChatGPT Structural Advisor re-observes the new HEAD (pending)
→ closes or retains Phase 13 blockers (pending)
→ SHUKOU decides acceptance (pending)
→ authorized Human merge (pending)
→ main merge receipt is observed (pending)
→ after-state is re-observed (pending)
→ Phase 13 may be recorded complete (pending)
```

---

# 10. Other open repository work

## 10.1 Governance Issue #53 and related, separate governance work (Issue #57)

2026-09-07T10:42:45Z時点の独立GitHub API再観測（`ADOPT_MSR_R3_COMPLETE_PROJECTION_REFRESH`、Issue #57）により、Issue #53は既にclosed（completed）であり、関連するIssue #57系列の governance PRのうち2件がmergeされていることを確認した。これらはいずれもPhase 13/Issue #51/PR #52とは別系列の governance-only 作業であり、Phase 13自身の open・未受入状態には影響しない。

| Item | State | Detail |
|---|---|---|
| Issue #53 | **Closed (completed)** | [PR #56](https://github.com/manosube/manosube-agent-civilization-os/pull/56) により2026-09-07T07:04:20Zにmerge、Issueは同時刻にclose |
| PR #56 | **Merged** | merged_at=2026-09-07T07:04:20Z |
| Issue #57 | Open | Merge Source Reflow governance (未受入) |
| PR #58 | **Merged** | merged_at=2026-09-07T09:24:09Z（Issue #57への貢献の一部；Issue #57自体はまだopen） |
| PR #59 | Open | 本Issue #57系列の現在の実装PR；SHUKOU acceptance・manual mergeは未付与 |
| Issue #51 | Open | 未受入（Phase 13） |
| PR #52 | Open | 未受入（Phase 13、head `2be9645c…`、詳細はセクション5-9） |

```text
ISSUE_53_MERGED_CLOSED=true
PR_56_MERGED=true
PR_58_MERGED=true
ISSUE_57_STILL_OPEN=true
PR_59_STILL_OPEN_NOT_ACCEPTED=true
ISSUE_51_STILL_OPEN_NOT_ACCEPTED=true
PR_52_STILL_OPEN_NOT_ACCEPTED=true
```

Issue #53が採用した役割分離は次のとおりである。

```text
SEMANTIC_DECISION_OWNER=SHUKOU
ADOPTION_RECORDING_OPERATOR=CHATGPT_STRUCTURAL_ADVISOR
IMPLEMENTATION_EXECUTOR=CLAUDE_CODE
GITHUB_AUDIT_SURFACE=GITHUB
```

Issue #53はPR #56のmergeにより実装済み・closed済みである。Issue #53自体はPR #52への変更Authorityではなく、この事実の投影もPR #52自体を変更しない。

## 10.2 Deferred PR #27

| Field | Value |
|---|---|
| Pull Request | [#27 — Claude Code PR handoff boot loader](https://github.com/manosube/manosube-agent-civilization-os/pull/27) |
| State | Open |
| Classification | `DEFERRED_DESIGN_PROTOTYPE_DO_NOT_MERGE` |
| Current Phase blocker | No |

PR #27がopenであることを、現在Phaseの並行実装許可、Phase 13 completion、またはmerge permissionとして扱ってはならない。

---

# 11. Known status inconsistencies

repository `README.md`のmain版は次を表示している。

```text
PROJECT_STATUS=KERNEL_V0_1_CONSTRUCTION
現在は Kernel v0.1構築段階
```

しかしaccepted mainはPhase 12まで到達しており、このStatus節は現状投影として陳腐化している。

```text
README_CORE_DEFINITION_USABLE=true
README_CURRENT_STATUS_STALE=true
README_MAY_OVERRIDE_THIS_FILE=false
```

READMEの更新要否は現在Phase 13のscopeを拡張して決めてはならない。独立したbounded changeまたは次の適切なdocumentation work unitとして扱う。

`ADOPT_MSR_FULL_SOURCE_SNAPSHOT_REFRESH_FOR_PR58`（Issue #57）の時点では、独立GitHub API再観測によりPR #52のheadが本書のセクション5-9が投影していた`46975506…`（Round 2 adopted, awaiting implementation）を超えて進行していることが判明していたが、その完全な再投影はそのbounded refresh自身のscope外として意図的に据え置かれていた。`ADOPT_MSR_R3_COMPLETE_PROJECTION_REFRESH`（Issue #57、同じくPR #59向け）はその据え置きを明示的に解消する追加adoptionであり、セクション5-9・10.1は本書のこの版で現在のOBSERVED_AT_UTC時点のOBSERVED_GITHUB_FACTへ再投影済みである。

```text
PR_52_SECTIONS_5_TO_9_REPROJECTED_AT_THIS_OBSERVED_AT_UTC=true
PR_52_REPROJECTION_IS_OBSERVED_GITHUB_FACT_ONLY=true
PR_52_REPROJECTION_DOES_NOT_ACCEPT_PHASE_13_OR_CLOSE_BLOCKERS_BEYOND_THE_OBSERVED_PUSH=true
```

---

# 12. Information-source reconstruction state

本書作成時点で、再構築中の情報源は次の状態である。

| File | State |
|---|---|
| `00_SOURCE_AUTHORITY_INDEX.md` | Complete |
| `01_PROJECT_CONSTITUTION.md` | Complete |
| `02_CANONICAL_ROADMAP.md` | Complete |
| `03_CURRENT_DEVELOPMENT_STATE.md` | This projection |
| `04_REPOSITORY_ARCHITECTURE.md` | Not yet reconstructed |
| `05_PHASE_ACCEPTANCE_LEDGER.md` | Not yet reconstructed |
| `06_DEFERRED_DIFFERENCES.md` | Not yet reconstructed |
| `07_DEVELOPMENT_GOVERNANCE.md` | Not yet reconstructed |
| `99_HISTORICAL_SOURCE_REGISTER.md` | Not yet reconstructed |

未作成の後続sourceが所有する事実を、本書が恒久的に代行してはならない。本書中の関連要約は現在地の理解に必要な最小投影であり、後続owner完成後に競合を再確認する。

---

# 13. Update triggers

本書は少なくとも次の場合に再観測し、更新する。

```text
PR_52_HEAD_CHANGED
ISSUE_51_HUMAN_DECISION_ADDED
PHASE_13_REVIEW_RESULT_CHANGED
PR_52_MERGED_OR_CLOSED
MAIN_SHA_CHANGED_BY_PHASE_WORK
PHASE_TRANSITION_OCCURRED
CURRENT_ROUTE_BLOCKER_CHANGED
NEXT_AUTHORIZED_OWNER_OR_ACTION_CHANGED
```

更新時には、古いSHA、test count、review stateまたは次作業を黙って残してはならない。

```text
LIVE_REOBSERVATION_REQUIRED=true
OBSERVATION_TIMESTAMP_REQUIRED=true
STALE_SHA_MUST_NOT_DIRECT_IMPLEMENTATION=true
```

---

# 14. Current state receipt

```text
OBSERVED_AT_UTC=2026-09-07T10:42:45Z
DEFAULT_BRANCH=main
MAIN_ACCEPTED_BASE_SHA=1d41f7d1e79441249382be07e8d8dbed618331c8

COMPLETED_THROUGH_PHASE=12
CURRENT_PHASE=13_INDEPENDENT_VERIFICATION
CURRENT_ISSUE=51
CURRENT_PR=52
CURRENT_PR_HEAD=2be9645cdfafb48e6f30ac968938fd15fb87717d
LATEST_HUMAN_ADOPTION=ADOPT_P13_R3_AUTHORITY_OWNED_VERIFIER_SELECTION_DECISION

CURRENT_PHASE_STATE=ROUND_3_DELIVERED_AWAITING_STRUCTURAL_REVIEW
PHASE_13_COMPLETE=false
PHASE_14_ALLOWED=false
MERGE_ALLOWED=false

NEXT_IMPLEMENTATION_OWNER=CLAUDE_CODE
NEXT_REVIEW_OWNER=CHATGPT_STRUCTURAL_ADVISOR
NEXT_ACCEPTANCE_OWNER=SHUKOU
```

本receiptは永続的なPhase acceptanceではない。GitHub状態が変化した時点で再観測対象となる、現在状態のfingerprintである。

---

# 15. Phase 14 bounded addendum (Identity-Preserving GitHub Projection, Issue #62)

本節は、セクション2-9・14が投影する`OBSERVED_AT_UTC`（Phase 13、PR #52 open）以降にrepositoryへ生じた変化のうち、local `git log`によりorigin/mainへ対して独立再観測できた`OBSERVED_GITHUB_FACT`のみを追記する、bounded addendumである。セクション2-9・14自身の全面再投影ではない。

```text
ADDENDUM_OBSERVED_AT_UTC=2026-09-08
ADDENDUM_OBSERVATION_METHOD=LOCAL_GIT_LOG_AGAINST_ORIGIN_MAIN
```

| Field | Observed value |
|---|---|
| Current `origin/main` HEAD | [`7fc597356330a0d1da7a334ef20cd913b74154de`](https://github.com/manosube/manosube-agent-civilization-os/commit/7fc597356330a0d1da7a334ef20cd913b74154de) |
| PR #52 (Phase 13, Issue #51) | **Merged** — merge commit `657f8b4` |
| PR #61 (FD-0003 Objective/Mechanism separation, Issue #60) | **Merged** — merge commit `7fc5973` |
| Governing Issue, current Phase | [#62 — Phase 14: Identity-Preserving GitHub Projection](https://github.com/manosube/manosube-agent-civilization-os/issues/62) |
| SHUKOU implementation adoption | [`ADOPT_P14_D001_PROJECTION_ENVELOPE_IMPLEMENTATION`](https://github.com/manosube/manosube-agent-civilization-os/issues/62#issuecomment-5578028316) |
| Adoption's own reviewed main SHA | `7fc597356330a0d1da7a334ef20cd913b74154de` (identical to the current `origin/main` HEAD observed above) |
| Dedicated implementation branch | `agent/issue-62-phase14-github-projection` |
| Dedicated Pull Request | Not yet opened at the time of this addendum |

```text
PHASE_13_MERGED=true
PHASE_13_MERGE_COMMIT=657f8b4
PHASE_13_COMPLETE=true
COMPLETED_THROUGH_PHASE=13
CURRENT_PHASE=14_IDENTITY_PRESERVING_GITHUB_PROJECTION
CURRENT_PHASE_ISSUE=62
CURRENT_PHASE_STATE=LOCAL_IMPLEMENTATION_IN_PROGRESS_NO_PR_YET
PHASE_14_ALLOWED=true
PHASE_14_COMPLETE=false
PHASE_15_ALLOWED=false
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
```

`ADOPT_P14_D001_PROJECTION_ENVELOPE_IMPLEMENTATION`が要求する実装範囲は`09_PROJECTION/PROJECTION_INDEX.md`・`09_PROJECTION/PROJECTION_CONTRACT.md`が所有する。SHUKOU自身が固定した終端は次のとおりであり、本addendumもこれを変更しない。

```text
STATUS=READY_FOR_STRUCTURAL_REVIEW (delivery-terminal, not yet reached at the time of this
                                     addendum)
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_14_COMPLETE=false
PHASE_15_ALLOWED=false
```

本addendumは、`05_PHASE_ACCEPTANCE_LEDGER.md`が所有するPhase 13の恒久的なacceptance receipt（merge SHA、Human acceptance record、after-state re-observation）を代行しない。それは同ledgerの別途更新の対象であり、本書は現在地を示すための最小限の`OBSERVED_GITHUB_FACT`のみを記録する。

---

# 16. Phase 15 bounded addendum (Bounded Runtime Observation and Trusted Runtime Provisioning, Issue #64)

本節は、セクション2-9・14-15が投影する`OBSERVED_AT_UTC`（Phase 14、PR #63）以降にrepositoryへ生じた変化のうち、local `git log`によりorigin/mainへ対して独立再観測できた`OBSERVED_GITHUB_FACT`のみを追記する、bounded addendumである。セクション2-9・14-15自身の全面再投影ではない。

```text
ADDENDUM_OBSERVED_AT_UTC=2026-09-09
ADDENDUM_OBSERVATION_METHOD=LOCAL_GIT_LOG_AGAINST_ORIGIN_MAIN
```

| Field | Observed value |
|---|---|
| Current `origin/main` HEAD | [`149492e7fd094a424a40b840dd4dcb564f012461`](https://github.com/manosube/manosube-agent-civilization-os/commit/149492e7fd094a424a40b840dd4dcb564f012461) |
| PR #63 (Phase 14, Issue #62) | **Merged** — merge commit `149492e` |
| Governing Issue, current Phase | [#64 — Phase 15: Bounded Runtime Observation and Trusted Runtime Provisioning](https://github.com/manosube/manosube-agent-civilization-os/issues/64) |
| SHUKOU implementation adoption | [`ADOPT_P15_D001_BOUNDED_RUNTIME_OBSERVATION_AND_TRUSTED_PROVISIONING`](https://github.com/manosube/manosube-agent-civilization-os/issues/64#issuecomment-5593903656) |
| Adoption's own reviewed main SHA | `149492e7fd094a424a40b840dd4dcb564f012461` (identical to the current `origin/main` HEAD observed above) |
| Dedicated implementation branch | `agent/issue-64-phase15-runtime-adapter` |
| Dedicated Pull Request | Not yet opened at the time of this addendum |

```text
PHASE_14_MERGED=true
PHASE_14_MERGE_COMMIT=149492e
PHASE_14_COMPLETE=true
COMPLETED_THROUGH_PHASE=14
CURRENT_PHASE=15_BOUNDED_RUNTIME_OBSERVATION_AND_TRUSTED_PROVISIONING
CURRENT_PHASE_ISSUE=64
CURRENT_PHASE_STATE=LOCAL_IMPLEMENTATION_IN_PROGRESS_NO_PR_YET
PHASE_15_ALLOWED=true
PHASE_15_COMPLETE=false
PHASE_16_ALLOWED=false
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
```

`ADOPT_P15_D001_BOUNDED_RUNTIME_OBSERVATION_AND_TRUSTED_PROVISIONING`が要求する実装範囲は`10_RUNTIME/RUNTIME_INDEX.md`・`10_RUNTIME/RUNTIME_CONTRACT.md`が所有する。SHUKOU自身が固定した終端は次のとおりであり、本addendumもこれを変更しない。

```text
STATUS=READY_FOR_STRUCTURAL_REVIEW (delivery-terminal, not yet reached at the time of this
                                     addendum)
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_15_COMPLETE=false
PHASE_16_ALLOWED=false
LIVE_EXTERNAL_WRITE_AUTHORITY=false
REMOTE_COMMAND_EXECUTION_AUTHORITY=false
RUNTIME_CREDENTIAL_USE_AUTHORITY=false
```

本addendumは、`05_PHASE_ACCEPTANCE_LEDGER.md`が所有するPhase 14の恒久的なacceptance receipt（merge SHA、Human acceptance record、after-state re-observation）を代行しない。それは同ledgerの別途更新の対象であり、本書は現在地を示すための最小限の`OBSERVED_GITHUB_FACT`のみを記録する。

---

# 17. Phase 15 Structural Review Round 1 correction addendum (P15-R1-F1 .. P15-R1-F6, Issue #64 / PR #65)

本節は、セクション16のaddendum記録時点（`CURRENT_PHASE_STATE=LOCAL_IMPLEMENTATION_IN_PROGRESS_NO_PR_YET`）以降にrepositoryへ生じた変化のうち、local `git log`とPR #65自身のReview commentにより独立再観測できた`OBSERVED_GITHUB_FACT`のみを追記する、bounded addendumである。セクション16自身の全面再投影ではない。

```text
ADDENDUM_OBSERVED_AT_UTC=2026-09-09
ADDENDUM_OBSERVATION_METHOD=LOCAL_GIT_LOG_AND_PR_65_REVIEW_COMMENT
```

| Field | Observed value |
|---|---|
| Dedicated Pull Request | [#65](https://github.com/manosube/manosube-agent-civilization-os/pull/65) — **open**, not merged |
| PR #65 reviewed HEAD (Structural Review Round 1 の対象) | `116a25d59130c5e64ced9e665bc2b839182de06a` |
| Structural Review Round 1 | [PR #65 comment 5594701920](https://github.com/manosube/manosube-agent-civilization-os/pull/65#issuecomment-5594701920) — 6 findings (P15-R1-F1 .. P15-R1-F6) |
| SHUKOU adoption | 同comment（Human Authority `manosube`）により採択済 |
| This correction round's own commits | branch `agent/issue-64-phase15-runtime-adapter` 上、reviewed HEAD `116a25d5` の直上に積まれた新規commitのみ（history rewriteなし）。`36424c7`（六findingsのcode + regression tests）、`82a4024`（contract/index/development-state記録、本addendumを含む）、[`645acdb`](https://github.com/manosube/manosube-agent-civilization-os/commit/645acdbacea28048ddf6cd956ae719c23172b313)（public docstring記録）、および本行を確定させるcommit自身。 |

採択された6件の構造的findingと、その閉鎖範囲：

```text
P15-R1-F1  network scope not enforced / redirect followed
           → route.py 側の Boundary 検証で allowed_hosts を強制（zero-call）、
             adapter.py が独立に再強制、redirect は一切追跡しない
P15-R1-F2  malformed Boundary reached the adapter / time window compared as strings
           → target_identity と boundary の完全なschema検証を Boot・adapter 到達前に実施、
             time window は実UTC instant として比較
P15-R1-F3  adapter could escape permitted_fields / mutate validated inputs
           → adapter へは deep-frozen copy を渡し、observed_fields は route 自身が
             permitted_fields へ独立射影（超過fieldは RuntimeAdapterError）
P15-R1-F4  bootstrap accepted a caller-selected Authority world
           → TrustedRuntimeRoot / provision_trusted_runtime_root による二段階provisioning。
             bootstrap_projection_execution_capability から store/project_id/
             project_binding_id parameter を完全に除去
P15-R1-F5  stale Binding/Authority could cross the adapter boundary or be committed
           → adapter 呼び出し直前と、全commit試行ごとに authority freshness を再証明
P15-R1-F6  deployed identity verification was circular
           → 新canonical record kind runtime_deployment_declaration により、
             declared deployment_fingerprint を Store 解決可能な正準record へ係留
```

実装範囲の所有は変わらず`10_RUNTIME/RUNTIME_INDEX.md`・`10_RUNTIME/RUNTIME_CONTRACT.md`にある（本correction roundは`RUNTIME_CONTRACT.md`にsection 10、`RUNTIME_INDEX.md`にsection 4.1を追加した）。canonical schema総数は57から58へ増加し、`scripts/validate_schemas.py`の宣言済count もそれに合わせて更新されている。

SHUKOU自身が固定した終端は変わらず、本addendumもこれを変更しない。

```text
CURRENT_PHASE=15_BOUNDED_RUNTIME_OBSERVATION_AND_TRUSTED_PROVISIONING
CURRENT_PHASE_ISSUE=64
CURRENT_PHASE_STATE=STRUCTURAL_REVIEW_ROUND_1_CORRECTIONS_DELIVERED_PR_OPEN
STRUCTURAL_REVIEW_ROUNDS_APPLIED=1
STRUCTURAL_REVIEW_ROUND_1_FINDINGS_CLOSED=6
NEW_BRANCH=false
NEW_PR=false
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_15_COMPLETE=false
PHASE_16_ALLOWED=false
LIVE_EXTERNAL_WRITE_AUTHORITY=false
REMOTE_COMMAND_EXECUTION_AUTHORITY=false
RUNTIME_CREDENTIAL_USE_AUTHORITY=false
```

本addendumは`05_PHASE_ACCEPTANCE_LEDGER.md`が所有するacceptance receiptを代行しない。またPR #65自身のmergeやIssue #64のcloseを主張しない — どちらもSHUKOUの別途決定の対象であり、本correction roundはstructural findingsの閉鎖のみを行う。

---

# 18. Phase 15 Structural Review Round 2 correction addendum (P15-R2-F1 / P15-R2-F2, Issue #64 / PR #65)

本節は、セクション17のaddendum記録時点（`CURRENT_PHASE_STATE=STRUCTURAL_REVIEW_ROUND_1_CORRECTIONS_DELIVERED_PR_OPEN`）以降にrepositoryへ生じた変化のうち、local `git log`とPR #65自身のReview commentにより独立再観測できた`OBSERVED_GITHUB_FACT`のみを追記する、bounded addendumである。セクション16・17の全面再投影ではない。

```text
ADDENDUM_OBSERVED_AT_UTC=2026-09-09
ADDENDUM_OBSERVATION_METHOD=LOCAL_GIT_LOG_AND_PR_65_REVIEW_COMMENT
```

| Field | Observed value |
|---|---|
| Dedicated Pull Request | [#65](https://github.com/manosube/manosube-agent-civilization-os/pull/65) — **open**, not merged |
| PR #65 reviewed HEAD (Structural Review Round 2 の対象) | `e840f0970d1cd7df0f7cbfaf6fe9b809be0ca01e` |
| Structural Review Round 2 | [PR #65 comment 5595591851](https://github.com/manosube/manosube-agent-civilization-os/pull/65#issuecomment-5595591851) — 2 findings (P15-R2-F1, P15-R2-F2) |
| SHUKOU adoption | 同comment（Human Authority `manosube`）により採択済 |
| Round 1 findings の Round 2 自身による処分 | `P15_R1_F1_CLOSED=true`, `P15_R1_F2_CLOSED=true`, `P15_R1_F3_CLOSED=true`, `P15_R1_F5_CLOSED=true`。`P15_R1_F4` と `P15_R1_F6` のみ reopen され、それぞれ `P15-R2-F1` / `P15-R2-F2` として再採番された。 |
| This correction round's own commits | branch `agent/issue-64-phase15-runtime-adapter` 上、reviewed HEAD `e840f097` の直上に積まれた新規commitのみ。history rewrite（amend / rebase / force-push）は行っていない。新規branchも新規PRも作成していない。 |

採択された2件の構造的findingと、その閉鎖範囲：

```text
P15-R2-F1  public provisioning factory still turned any caller-selected Store into a
           "trusted" root（Round 1 の P15-R1-F4 が factory を一段手前へ移しただけであり、
           trust decision の制御そのものは移っていなかった）
           → shipped `src/` から provision_trusted_runtime_root を削除。同名・同形の関数を
             別名で再導入することもしない。TrustedRuntimeRoot 型と module-private sentinel
             は保持（型自体は問題ではなく、公開 minting 関数のみが問題だった）。
             唯一の issuer は tests/fixtures/runtime_world.py::test_only_trusted_runtime_root
             であり、shipped package からは構造的に到達不能。
             installed package 全 .py への AST walk により、TrustedRuntimeRoot(...) の
             call site が dataclass 自身の class body 以外に存在しないこと、削除された
             factory 名がいかなる code position にも現れないこと、TrustedRuntimeRoot を
             返す public callable が存在しないことを機械的に証明。
P15-R2-F2  the deployment declaration was unsigned and unbound to the Boot-verified
           Human Authority
           → runtime_deployment_declaration.schema.json に必須 status
             （ACTIVE/REVOKED）と必須 Ed25519 signature を追加（github_projection_grant_
             declaration.schema.json と同一の $def 形状を再利用）。
             runtime_deployment_declaration_signing_payload を追加し、content address /
             semantic fingerprint / 署名対象を単一の導出へ統合。
             route._resolve_deployment_declaration は、status=ACTIVE、当該呼び出し自身の
             Boot が復元した Human Authority との一致、および同 Boot が現行 Project Binding
             から復元した human_authority_signing_key に対する署名検証を要求する。
             いずれの拒否も adapter 呼び出し前・commit ゼロ。
```

`P15-R2-F1` が証明する範囲は、以下のとおり明示的に限定される（誇張しない）。

```text
SHIPPED_TRUSTED_RUNTIME_ROOT_MINTING_PATH_EXISTS=false   （証明済）
LIVE_PATH_ADVERSARIAL_RESISTANCE_PROVEN=false            （未証明・主張しない）
LIVE_DEPLOYMENT_COMPOSITION_BOUNDARY_EXISTS=false
```

本repositoryには Runtime に接続された live deployment / CLI / agent-runtime composition boundary が現時点で存在しない（Phase 16+ は未認可）。したがって本roundが確立したのは「この Phase の shipped code には root を mint する経路が一切存在しない」という事実であり、「live path が実行時に攻撃者へ耐える」という主張ではない。将来のPhaseが実際の deployment composition boundary を接続した時点で、その boundary 自身に対する独立の control が別途必要になる。

`P15-R2-F2` は、`RUNTIME_CONTRACT.md` section 10.6 が「adopted finding F6 が要求していないため意図的に追加しない」として開示していた事項を、明示的に逆転して採択する。すなわち **正当な Human Authority re-binding は、それ以前に発行された deployment declaration を新規observationに対して無効化する**（silent carry-forward は存在しない）。`RUNTIME_CREDENTIAL_USE_AUTHORITY` は `false` のまま：本packageはprivate keyを保持せず、署名を生成せず、key server にも到達しない — 検証のみを行い、参照する鍵は実在のBoot復元済 Project Binding が既に保持する public key に限られる。

実装範囲の所有は変わらず`10_RUNTIME/RUNTIME_INDEX.md`・`10_RUNTIME/RUNTIME_CONTRACT.md`にある（本correction roundは`RUNTIME_CONTRACT.md`にsection 11、`RUNTIME_INDEX.md`にsection 4.2を追加した）。canonical schema総数は`58`のまま変化しない — 本roundは既存schema fileへfieldを追加しただけであり、新規schema fileを追加していないため、`scripts/validate_schemas.py`の宣言済countは意図的に据え置かれている。

SHUKOU自身が固定した終端は変わらず、本addendumもこれを変更しない。

```text
CURRENT_PHASE=15_BOUNDED_RUNTIME_OBSERVATION_AND_TRUSTED_PROVISIONING
CURRENT_PHASE_ISSUE=64
CURRENT_PHASE_STATE=STRUCTURAL_REVIEW_ROUND_2_CORRECTIONS_DELIVERED_PR_OPEN
STRUCTURAL_REVIEW_ROUNDS_APPLIED=2
STRUCTURAL_REVIEW_ROUND_1_FINDINGS_CLOSED=6
STRUCTURAL_REVIEW_ROUND_2_FINDINGS_CLOSED=2
NEW_BRANCH=false
NEW_PR=false
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_15_COMPLETE=false
PHASE_16_ALLOWED=false
LIVE_EXTERNAL_WRITE_AUTHORITY=false
REMOTE_COMMAND_EXECUTION_AUTHORITY=false
RUNTIME_CREDENTIAL_USE_AUTHORITY=false
```

本addendumは`05_PHASE_ACCEPTANCE_LEDGER.md`が所有するacceptance receiptを代行しない。またPR #65自身のmergeやIssue #64のcloseを主張しない — どちらもSHUKOUの別途決定の対象であり、本correction roundはstructural findingsの閉鎖のみを行う。

---

# 19. Phase 15 Structural Review Round 3 correction addendum (P15-R3-F1 / P15-R3-F2, Issue #64 / PR #65)

本節は、セクション18のaddendum記録時点（`CURRENT_PHASE_STATE=STRUCTURAL_REVIEW_ROUND_2_CORRECTIONS_DELIVERED_PR_OPEN`）以降にrepositoryへ生じた変化のうち、local `git log`とPR #65自身のReview commentにより独立再観測できた`OBSERVED_GITHUB_FACT`のみを追記する、bounded addendumである。セクション16・17・18の全面再投影ではない。

```text
ADDENDUM_OBSERVED_AT_UTC=2026-09-09
ADDENDUM_OBSERVATION_METHOD=LOCAL_GIT_LOG_AND_PR_65_REVIEW_COMMENT
```

| Field | Observed value |
|---|---|
| Dedicated Pull Request | [#65](https://github.com/manosube/manosube-agent-civilization-os/pull/65) — **open**, not merged |
| PR #65 reviewed HEAD (Structural Review Round 3 の対象) | `1e1fc98d80a9f06eb713889146f10eafc9f387ed` |
| Structural Review Round 3 | [PR #65 comment 5596247475](https://github.com/manosube/manosube-agent-civilization-os/pull/65#issuecomment-5596247475) — 2 findings (P15-R3-F1, P15-R3-F2) |
| SHUKOU adoption | 同comment（Human Authority `manosube`）により採択済 |
| Round 1/2 findings の Round 3 自身による処分 | `P15_R1_F1_CLOSED=true`, `P15_R1_F2_CLOSED=true`, `P15_R1_F3_CLOSED=true`, `P15_R1_F5_CLOSED=true`, `P15_R2_F2_SIGNATURE_AND_BOOT_BINDING_CLOSED=true`。`P15-R2-F1` と `P15-R2-F2` の残余のみ reopen され、それぞれ `P15-R3-F1` / `P15-R3-F2` として再採番された。 |
| This correction round's own commits | branch `agent/issue-64-phase15-runtime-adapter` 上、reviewed HEAD `1e1fc98d` の直上に積まれた新規commitのみ。`03c4d28`（二findingsのcode + schema + regression tests + schema count）、`3e9ddde`（contract section 12 / index section 4.3 / 本addendum）、および本行を確定させるcommit自身。history rewrite（amend / rebase / force-push）は行っていない。新規branchも新規PRも作成していない。 |

採択された2件の構造的findingと、その閉鎖範囲：

```text
P15-R3-F1  the trusted root had no legitimate shipped issuer, and its "private" sentinel was
           not actually unreachable
           （Round 2 は factory を削除した上で「実発行は将来Phaseへ委ねる」と結論したが、
             Issue #64 は本production provisioning boundary を本Phase自身に割り当てている。
             かつ module-private sentinel は access control ではなく、shipped module を
             import できる任意の caller が同一の構築を再現できた。両方向で不十分。）
           → 新canonical record kind runtime_root_admission を追加（
             01_SCHEMA/runtime/runtime_root_admission.schema.json、content-addressed・
             immutable・Store-committed・署名付き）。
             runtime/identity.py に runtime_root_admission_signing_payload /
             runtime_root_admission_id / runtime_root_admission_semantic_fingerprint を追加
             （content address・semantic fingerprint・署名対象を単一導出へ統合、既存の
             deployment declaration と同一規約）。
             runtime/root_admission.py に verify_runtime_root_admission_signature を追加。
             binding.signature.verify_ed25519_signature を再実装せず合成する点は
             deployment_declaration.py と同一。ただし引数は Store 解決の signing_key ではなく
             **caller供給の trust_anchor_public_key_hex** である。
             bootstrap_projection_execution_capability 自身に admission check を内蔵（Boot直後、
             grant/declaration解決前、evaluate_projection_authorization 到達前）。解決・
             identity再計算・status=ACTIVE・project_id/project_binding_ref完全一致・
             外部anchorによる署名検証のすべてを要求し、いずれの拒否も adapter 呼び出しゼロ・
             authorization評価ゼロ。
```

`P15-R3-F1` の中核的な構造転換は次のとおりであり、**Round 2 の撤回ではない**。

```text
BEFORE (Round 1 / Round 2)   TrustedRuntimeRoot を「保持していること」が adapter 到達の
                             十分条件だった。ゆえに全ての問いが「誰が mint してよいか」に
                             帰着し、それは shipped library 関数が答えられない問いだった。

AFTER  (Round 3)             TrustedRuntimeRoot の保持は**それ自体では何の権限も与えない**。
                             実際に adapter access を gate するのは
                             bootstrap_projection_execution_capability 内部の
                             admission-record + external-anchor check であり、root の
                             出自にかかわらず**毎回**再実行される。
```

したがって `TrustedRuntimeRoot` の公開constructorを復活させても、それは trust decision ではない（型が capability でなくなったため）。sentinel は「移設」ではなく「削除」した — 何の権限も与えない値に偽の private gate を残すことは、本roundが指摘した錯覚そのものを温存するため。**Round 2 自身の機械的事実は一つも弱められておらず、静的検証も従来どおり主張し続けている**：

```text
provision_trusted_runtime_root は shipped file のいかなる code position にも現れない   （不変）
TrustedRuntimeRoot を返す public callable は存在しない                                （不変）
TrustedRuntimeRoot を構築する shipped module は存在しない                             （不変）
```

```text
P15-R3-F2  the deployment declaration had no validity window, and revocation was not
           effective
           （record は immutable かつ content-addressed であるため、status="REVOKED" の
             新recordを発行しても、元の ACTIVE record は自身のidを保ったまま個別解決可能で
             あり続ける。Round 2 の "revoked" test は「別途構築された REVOKED record が
             拒否される」ことしか証明しておらず、「既に発行済の ACTIVE declaration を
             実際に revoke できる」ことは一度も証明していなかった。）
           → runtime_deployment_declaration.schema.json に必須 valid_from / valid_until を
             追加し、両者を DEPLOYMENT_DECLARATION_SEMANTIC_FIELDS へ含めた（content address
             と Human Authority 署名の双方が validity window を覆うため、署名後の再日付は
             identity と署名の両方を破壊する）。route は両者を実UTC instant として解析し、
             valid_from <= observed_at <= valid_until（両端含む）を要求する。
           → 実効的なrevocation/supersession を、canonical な Store 解決 current-pointer に
             よって実装：semantic_state.runtime.claims[<target_key>] -> declaration_id。
             <target_key> は project_binding_ref / provider / deployment_id /
             instance_identity の4fieldから導出する決定的キー（deployment_fingerprint は
             意図的に除外 — rotation が supersede ではなく fork してしまうため）。
             新module runtime/deployment_registry.py の
             commit_runtime_deployment_declaration が、record commit と pointer 更新を
             **単一の commit_state_transition** で原子的に行う。
           → route._resolve_deployment_declaration は、既存の全checkに加えて validity window と
             pointer 一致を要求する。pointer 未設定、または別idを指している場合は拒否
             （presented declaration 自身の内容・署名・window がすべて個別には正当であっても）。
             さらに pointer は**全commit試行ごと**に再検証され、resolution後・Envelope commit前に
             起きた supersession は commit 拒否となる（P15-R1-F5 が確立した per-attempt 規律の
             再利用であり、第二の並行機構は導入していない）。
```

`semantic_state` については、**canonical schema の変更を一切行っていない**。`01_SCHEMA/state/semantic_state.schema.json` は既に `runtime` domain（`$defs/domain`）とその `claims`（`{string: scalar}` の開いたmap）を採択済であり、Phase 15 は本roundまで `runtime` domain へ一度も書き込んでいなかった。`deployment_registry` は `semantic_state` を deep-copy し、単一 domain の `claims` に単一キーを設定するだけで、当該domainの `status`/`identity_refs`/`evidence_refs`/`blind_spots` も他の全domainも byte-identical に持ち越す。Store への書き込みは従来どおり単一の sanctioned committer（`store.commit.commit_state_transition`）経由であり、本layerは依然として第二の State owner ではない。

canonical schema総数は `58` から `59` へ増加した（新規file は `runtime_root_admission.schema.json` の1件のみ。`valid_from`/`valid_until` は既存fileへのfield追加であり、新規fileではない）。`scripts/validate_schemas.py` の宣言済countもそれに合わせて更新した。

`P15-R3-F1` が証明する範囲と、しない範囲は、Round 2 と同様に明示的に限定される（誇張しない）。

```text
PRODUCTION_LEGITIMATE_PROVISIONING_MECHANISM_SHIPPED=true      （証明済）
RUNTIME_ROOT_ADMISSION_VERIFIED_AGAINST_AN_EXTERNALLY_SUPPLIED_ANCHOR=true （証明済）
LIVE_DEPLOYMENT_ENTRYPOINT_INVOKES_THE_MECHANISM=false         （未実装・主張しない）
LIVE_PATH_ADVERSARIAL_RESISTANCE_PROVEN=false                  （未証明・主張しない）
```

本repositoryには Runtime に接続された live deployment / CLI / agent-runtime entrypoint が現時点で存在しない（Phase 16+ は未認可）。ただし Round 2 との差は決定的である：Round 2 の限界は「そもそも root を正当に取得する経路が存在しない」という**機構自体の欠陥**であったのに対し、本roundの残余は「本repository内にその機構を呼び出す entrypoint がまだ無い」という**後続Phaseの日程上の事実**にすぎない。`trust_anchor_public_key_hex` は shipped source にhardcodeされておらず（installed runtime package 全 `.py` に対する 64-hex 文字列定数のAST走査で機械的に証明）、deployment/composition-time configuration からのみ供給される。`RUNTIME_CREDENTIAL_USE_AUTHORITY` は `false` のまま：本packageは private key を保持せず、署名を生成せず、key server・環境変数・network のいずれにも到達しない — 検証のみを行う。

実装範囲の所有は変わらず`10_RUNTIME/RUNTIME_INDEX.md`・`10_RUNTIME/RUNTIME_CONTRACT.md`にある（本correction roundは`RUNTIME_CONTRACT.md`にsection 12、`RUNTIME_INDEX.md`にsection 4.3を追加した）。

SHUKOU自身が固定した終端は変わらず、本addendumもこれを変更しない。

```text
CURRENT_PHASE=15_BOUNDED_RUNTIME_OBSERVATION_AND_TRUSTED_PROVISIONING
CURRENT_PHASE_ISSUE=64
CURRENT_PHASE_STATE=STRUCTURAL_REVIEW_ROUND_3_CORRECTIONS_DELIVERED_PR_OPEN
STRUCTURAL_REVIEW_ROUNDS_APPLIED=3
STRUCTURAL_REVIEW_ROUND_1_FINDINGS_CLOSED=6
STRUCTURAL_REVIEW_ROUND_2_FINDINGS_CLOSED=2
STRUCTURAL_REVIEW_ROUND_3_FINDINGS_CLOSED=2
CANONICAL_SCHEMA_COUNT=59
NEW_BRANCH=false
NEW_PR=false
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_15_COMPLETE=false
PHASE_16_ALLOWED=false
LIVE_EXTERNAL_WRITE_AUTHORITY=false
REMOTE_COMMAND_EXECUTION_AUTHORITY=false
RUNTIME_CREDENTIAL_USE_AUTHORITY=false
```

本addendumは`05_PHASE_ACCEPTANCE_LEDGER.md`が所有するacceptance receiptを代行しない。またPR #65自身のmergeやIssue #64のcloseを主張しない — どちらもSHUKOUの別途決定の対象であり、本correction roundはstructural findingsの閉鎖のみを行う。

# 20. Phase 15 Structural Review Round 4 correction addendum (P15-R4-F1 / P15-R4-F2, Issue #64 / PR #65)

本節は、セクション19のaddendum記録時点（`CURRENT_PHASE_STATE=STRUCTURAL_REVIEW_ROUND_3_CORRECTIONS_DELIVERED_PR_OPEN`）以降にrepositoryへ生じた変化のうち、local `git log`とPR #65 / Issue #64自身のReview commentにより独立再観測できた`OBSERVED_GITHUB_FACT`のみを追記する、bounded addendumである。セクション16・17・18・19の全面再投影ではない。

```text
ADDENDUM_OBSERVED_AT_UTC=2026-09-09
ADDENDUM_OBSERVATION_METHOD=LOCAL_GIT_LOG_AND_PR_65_ISSUE_64_REVIEW_COMMENTS
```

| Field | Observed value |
|---|---|
| Dedicated Pull Request | [#65](https://github.com/manosube/manosube-agent-civilization-os/pull/65) — **open**, not merged |
| PR #65 reviewed HEAD (Structural Review Round 4 の対象) | `2c4e0c5ab11b6b9268f356a955c5acd98c47e0df` |
| Structural Review Round 4 | [PR #65 comment 5597994951](https://github.com/manosube/manosube-agent-civilization-os/pull/65#issuecomment-5597994951) — 2 findings (P15-R4-F1, P15-R4-F2) |
| SHUKOU adoption | [Issue #64 comment 5598042604](https://github.com/manosube/manosube-agent-civilization-os/issues/64#issuecomment-5598042604)（Human Authority `manosube`）により、契約本文が verbatim で採択済 |
| Round 1/2/3 findings の Round 4 自身による処分 | `P15_R1_F1_CLOSED=true`, `P15_R1_F2_CLOSED=true`, `P15_R1_F3_CLOSED=true`, `P15_R1_F5_CLOSED=true`, `P15_R1_F6_CLOSED=true`, `P15_R2_F2_SIGNATURE_AND_BOOT_BINDING_CLOSED=true`, `P15_R3_F2_VALIDITY_WINDOW_HALF_CLOSED=true`。`P15-R3-F1` と `P15-R3-F2` の残余のみ reopen され、それぞれ `P15-R4-F1` / `P15-R4-F2` として再採番された。 |
| This correction round's own commits | branch `agent/issue-64-phase15-runtime-adapter` 上、reviewed HEAD `2c4e0c5a` の直上に積まれた新規commitのみ。`116298e`（二findingsのcode + schema + regression tests + schema count comment）、`88c6ef9`（contract section 13 / index section 4.4 / 本addendum）、および本行を確定させるcommit自身。history rewrite（amend / rebase / force-push）は行っていない。新規branchも新規PRも作成していない。 |

Round 4 の Review 自身が明示したとおり、**同一のtrust-boundary semantic classがRound 1〜4にわたって再発している**。その再発の系列は次のとおりであり、本roundの補正の形を決定している。

```text
ROUND 1   trust decision が PARAMETER LIST        -> TYPE へ置換
ROUND 2   trust decision が PUBLIC FACTORY        -> PRIVATE SENTINEL へ置換
ROUND 3   trust decision が TYPE の保有           -> 署名付き admission record ＋
                                                    **caller供給**の anchor へ置換
ROUND 4   trust decision が依然 PARAMETER のまま   -> OWNERSHIP BOUNDARY へ置換。
          （caller が admission と anchor の両方を    決定する値は composition step が所有し、
            供給できたため、matching attacker        request-facing signature には
            anchor を伴う自己整合的 alternate        それらの parameter が**存在しない**）
            world が全checkを通過した）
```

採択された2件の構造的findingと、その閉鎖範囲：

```text
P15-R4-F1  the trust anchor was still a parameter of the REQUEST-FACING call
           → provisioning を2つの所有された半分に分割した。
             compose_trusted_runtime_deployment_authority(store, *, project_id,
             project_binding_id, runtime_root_admission_ref, trust_anchor_public_key_hex)
             が唯一の shipped trusted-composition entry point であり、canonical Store handle・
             project_id・project_binding_id・root-admission selection・configured anchor の
             すべてを所有する。request boundary が存在するより前に一度だけ実行される。
             bootstrap_projection_execution_capability(deployment_authority, *,
             github_projection_grant_refs, github_projection_grant_declaration_refs) は
             既に束縛済の opaque な RuntimeDeploymentAuthority のみを消費する。
             store / project_id / project_binding_id / runtime_root_admission_ref /
             trust_anchor_public_key_hex の5parameterは「検証される」のではなく
             **存在しない**（inspect.signature による静的証明）。
           → RuntimeDeploymentAuthority は frozen/slots の opaque capability。Store・
             admission body・raw anchor のいずれについても public accessor を持たず
             （dir() の public 名は空）、__repr__ は何も露出せず、raw anchor は composition
             時点で**破棄**される（composed instance から到達可能な全stringを走査して
             anchor hex が存在しないことを機械的に証明）。束縛するのは Store・project・
             Binding・admitted admission id・その generation のみ。
           → TrustedRuntimeRoot は削除。Round 2/3 が主張し得た静的事実（当該型を返す
             shipped callable が無い／構築する shipped module が無い）は、より強い形へ
             置換された：**当該名は shipped tree のいかなる code position にも存在しない**。
             削除済の Round 1 minting factory も従来どおり名前ごと不在。
           → root admission 自身にも lifecycle を与えた（Review が明示した
             "must not repeat the declaration-currency defect below" への対応）。
             runtime_root_admission.schema.json に必須 generation / predecessor_ref を追加し、
             ROOT_ADMISSION_SEMANTIC_FIELDS へ含めた（content address・semantic fingerprint・
             trust anchor 署名のすべてが当該2fieldを覆う）。
             semantic_state.runtime.claims["ROOT-ADMISSION:<project_binding_id>"] を
             current-admission pointer とし、新module runtime/admission_registry.py の
             commit_runtime_root_admission のみがこれを動かす。composition は提示された
             reference が pointer の現在値と完全一致することを要求するため、rotation /
             revocation 後の admission は自身の reference で replay できない。
```

```text
P15-R4-F2  the declaration pointer was freely re-pointable in BOTH directions
           （Round 3 は pointer を導入したが、declaration が「何を置換するか」を述べる
             ことを要求していなかった。したがって A(ACTIVE) -> B(REVOKED) の後に
             ancestor A を replay すると pointer は A へ戻り、revoke 済 target が
             静かに un-revoke された。並行する2つの rotation も、Store が最後に見た
             順序へ任意に畳み込まれた。）
           → runtime_deployment_declaration.schema.json に必須 generation /
             predecessor_ref を追加し、DEPLOYMENT_DECLARATION_SEMANTIC_FIELDS へ含めた。
             successor は「自分がどの head を置換するか」を Human Authority 署名の内側で
             述べる signed statement となる。
           → genesis（generation=0 / predecessor_ref=null、chain が空のときのみ、かつ
             ACTIVE 必須）／successor（generation=current+1 かつ predecessor_ref が
             pointer の現在値と完全一致）／rotation（ACTIVE successor）／revocation
             （REVOKED successor、当該chainに対して**終端**）／replay（pointer が既に
             指す record の再提示は idempotent no-op、transition ではない）。
             REVOKED 終端後は successor も ancestor replay も永久に不許可。
           → 規則は runtime/transition_chain.py という**単一の共有機構**に存在し、
             declaration chain と root-admission chain の双方が MonotonicChainSpec 経由で
             これを parameterize する。規則の二重実装は行っていない。副次的事実として、
             deployment_registry.py は commit_state_transition を呼ばなくなり、当該call site
             は transition_chain.py へ移った。よって chain 種別が2つに増えたにもかかわらず、
             本package内の commit_state_transition call site は依然として2つ（route.py と
             transition_chain.py）である。
           → committer は fresh Boot と Human Authority 署名検証を行うようになった。
             Round 3 の committer は「route 側が再検証するので二重化は drift を生む」として
             意図的に省略していたが、その前提（committer には gate すべき transition
             legality が無い）を本roundが除去したため、前提ごと更新された。
             observe_runtime_target 側の独立した再検証は一切弱められていない。
           → 並行 successor の敗者は retry せず fail closed する。敗者の
             predecessor_ref / generation は特定の先行 head に対して**署名済**であり、
             新しい head へ向け直すには新しい payload に対する新しい署名が必要で、
             それは Human Authority（admission の場合は trust anchor）にしか作れない。
             一方、当該chainの pointer が動いていない無関係な contention は従来どおり
             bounded CAS retry で吸収される（P15-R1-F5 が確立した許容を非退行で維持）。
```

`semantic_state` については、Round 3 と同様に**canonical schema の変更を一切行っていない**。root-admission pointer は Round 3 が確立したのと同一の `semantic_state.runtime.claims` map に、構造的に区別された key namespace（`ROOT-ADMISSION:<project_binding_id>`）で置かれる。declaration target key は `RUNTIME-DEPLOYMENT-TARGET-` ＋ 64桁の `[0-9A-F]` であり、その prefix にも alphabet にも `":"` は現れ得ないため、両key空間の非交差は sampling ではなく alphabet 自体に対する証明として与えられている。

canonical schema総数は `59` のまま変化していない（本roundは新規fileを追加せず、既存2fileへ必須fieldを追加しただけである）。`scripts/validate_schemas.py` の宣言済countはdisk上の実数と照合の上、据え置きを明記した。

`P15-R4-F1` が証明する範囲と、しない範囲は、従来どおり明示的に限定される（誇張しない）。

```text
REQUEST_FACING_SIGNATURE_CAN_NAME_NO_TRUST_DECIDING_VALUE=true          （証明済）
ALTERNATE_WORLD_WITH_ITS_MATCHING_ANCHOR_IS_UNSUBSTITUTABLE=true        （証明済、
                                                                         adapter/network 呼び出し
                                                                         ゼロ・authorization 評価
                                                                         ゼロ）
ROTATED_OR_REVOKED_ADMISSION_CANNOT_BE_REPLAYED=true                    （証明済）
RAW_ANCHOR_ABSENT_FROM_THE_COMPOSED_AUTHORITY=true                      （証明済）
AUTHORITY_COMPOSED_BEFORE_A_ROTATION_IS_RETROACTIVELY_REVOKED=false     （設計上そうであり、
                                                                         主張しない）
TARGET_EPOCH_REACTIVATION_MECHANISM_BUILT=false                         （本round範囲外・
                                                                         主張しない）
LIVE_DEPLOYMENT_ENTRYPOINT_INVOKES_THE_MECHANISM=false                  （未実装・主張しない）
```

最後から3行目は本roundの開示済 judgment call である。採択契約自身が anchor を "closed over afterward"・"absent from every request-facing execution signature" と規定しており、per-request の再検証を排除している。したがって composition 済 authority は cached credential と同じ振る舞いをし、rotation / revocation は**次回の composition** を拘束する。これは推測に委ねず、専用の control（`test_an_authority_composed_before_a_rotation_remains_usable_by_its_holder`）として証明されている。

実装範囲の所有は変わらず`10_RUNTIME/RUNTIME_INDEX.md`・`10_RUNTIME/RUNTIME_CONTRACT.md`にある（本correction roundは`RUNTIME_CONTRACT.md`にsection 13、`RUNTIME_INDEX.md`にsection 4.4を追加した）。

SHUKOU自身が固定した終端は変わらず、本addendumもこれを変更しない。

```text
CURRENT_PHASE=15_BOUNDED_RUNTIME_OBSERVATION_AND_TRUSTED_PROVISIONING
CURRENT_PHASE_ISSUE=64
CURRENT_PHASE_STATE=STRUCTURAL_REVIEW_ROUND_4_CORRECTIONS_DELIVERED_PR_OPEN
STRUCTURAL_REVIEW_ROUNDS_APPLIED=4
STRUCTURAL_REVIEW_ROUND_1_FINDINGS_CLOSED=6
STRUCTURAL_REVIEW_ROUND_2_FINDINGS_CLOSED=2
STRUCTURAL_REVIEW_ROUND_3_FINDINGS_CLOSED=2
STRUCTURAL_REVIEW_ROUND_4_FINDINGS_CLOSED=2
CANONICAL_SCHEMA_COUNT=59
NEW_SCHEMA_FILES_ADDED_THIS_ROUND=0
NEW_BRANCH=false
NEW_PR=false
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_15_COMPLETE=false
PHASE_16_ALLOWED=false
LIVE_EXTERNAL_WRITE_AUTHORITY=false
REMOTE_COMMAND_EXECUTION_AUTHORITY=false
RUNTIME_CREDENTIAL_USE_AUTHORITY=false
```

本addendumは`05_PHASE_ACCEPTANCE_LEDGER.md`が所有するacceptance receiptを代行しない。またPR #65自身のmergeやIssue #64のcloseを主張しない — どちらもSHUKOUの別途決定の対象であり、本correction roundはstructural findingsの閉鎖のみを行う。

# 21. Phase 15 Structural Review Round 5 correction addendum (P15-R5-F1 / P15-R5-F2 / P15-R5-F3, Issue #64 / PR #65)

本節は、セクション20のaddendum記録時点（`CURRENT_PHASE_STATE=STRUCTURAL_REVIEW_ROUND_4_CORRECTIONS_DELIVERED_PR_OPEN`）以降にrepositoryへ生じた変化のうち、local `git log`とPR #65 / Issue #64自身のReview commentにより独立再観測できた`OBSERVED_GITHUB_FACT`のみを追記する、bounded addendumである。セクション16〜20の全面再投影ではない。

```text
ADDENDUM_OBSERVED_AT_UTC=2026-09-09
ADDENDUM_OBSERVATION_METHOD=LOCAL_GIT_LOG_AND_PR_65_ISSUE_64_REVIEW_COMMENTS
```

| Field | Observed value |
|---|---|
| Dedicated Pull Request | [#65](https://github.com/manosube/manosube-agent-civilization-os/pull/65) — **open**, not merged |
| PR #65 reviewed HEAD (Structural Review Round 5 の対象) | `fd6ec1429443437c0c85e9f29144250506b61051` |
| SHUKOU adoption | Issue #64 上の `ADOPT_P15_R5_BOUND_BOOTSTRAP_SERVICE_AND_CURRENT_ADMISSION_RECHECK`（Human Authority `manosube`）により、契約本文が verbatim で採択済 |
| Round 4 findings の Round 5 自身による処分 | `P15_R4_F2_CLOSED=true`（monotonic signed transition chain は変更なし）。`P15-R4-F1` のみ reopen され `P15-R5-F1` として再採番、さらに `P15-R5-F2`（current admission recheck）と `P15-R5-F3`（declaration commit 時の instant 比較）が新規に採択された。 |
| This correction round's own commits | branch `agent/issue-64-phase15-runtime-adapter` 上、reviewed HEAD `fd6ec142` の直上に積まれた新規commitのみ。history rewrite（amend / rebase / force-push）は行っていない。新規branchも新規PRも作成していない。 |

Round 4 の Review が名指しした「同一のtrust-boundary semantic classの再発」系列は、Round 5 でもう一段進む。

```text
ROUND 4   trust decision は OWNERSHIP BOUNDARY へ置換されたが、その boundary は
          public constructor を持つ public dataclass（RuntimeDeploymentAuthority）に
          担われており、request-facing 側の防御は isinstance check のみだった
ROUND 5   -> boundary を CLOSURE へ置換。composition が request-facing operation 自身を
             返し、その operation には public constructor が存在しない
```

採択された3件の構造的findingと、その閉鎖範囲：

```text
P15-R5-F1  the ownership boundary was carried by a PUBLIC DATACLASS with a PUBLIC CONSTRUCTOR
           （Round 4 は store / project_id / project_binding_id /
             runtime_root_admission_ref / trust_anchor_public_key_hex の5parameterを
             request-facing signature から除去したが、その代わりに6番目の
             world-bearing parameter である deployment_authority を導入した。
             RuntimeDeploymentAuthority は public な frozen dataclass であり、
             public constructor を持つため、moduleをimportできる任意のcallerが
             alternate Store/Project/Binding 上で自前のinstanceを構築し、
             isinstance check を正面から通過させることができた。）
           → RuntimeDeploymentAuthority を**削除**し、
             compose_trusted_runtime_deployment_authority(store, *, project_id,
             project_binding_id, runtime_root_admission_ref, trust_anchor_public_key_hex)
             が request-facing operation **そのもの**を返すようにした。
             返される callable は composition の call frame 内で定義された closure であり、
             canonical Store・project_id・project_binding_id・admitted admission の
             id / generation を closure cell に保持する。
             closure は class ではないため public constructor が存在せず、
             等価な operation を fabricate する手段が無い。working な bootstrap を
             得る唯一の方法は composition を呼ぶことであり、そこには Round 4 と同一の
             anchor-signature / currency admission gate（_require_currently_admitted、
             無変更）が存在する。
           → request-facing signature の parameter は keyword-only 2個のみ
             （github_projection_grant_refs / github_projection_grant_declaration_refs）。
             deployment_authority / store / project_id / project_binding_id /
             runtime_root_admission_ref / trust_anchor_public_key_hex の6名は
             「検証される」のではなく**存在しない**（AST と、composition が実際に返した
             object 自身に対する inspect.signature の双方で証明）。
           → 削除は Round 2（minting factory）・Round 4（TrustedRuntimeRoot）と同一の
             precedent に従う。静的事実も同一の強さで置換された：
             **RuntimeDeploymentAuthority という名は shipped tree のいかなる code position
             にも存在しない**。加えて bootstrap_projection_execution_capability は
             module-level 名としても存在せず、shipped tree 全体で当該名の def は
             ちょうど1つ、composition entry point の内部に nested されている。
           → 開示済 scope：本 control は *call shape と obtainability* に対するものであり、
             in-process memory に対するものではない。既に function object を保持している
             code が自身の __closure__ cell を書き換えることを Python は禁止できない
             （Round 4 の frozen dataclass に対する object.__setattr__ が禁止できなかったのと
             同様）。証明されるのは、いかなる *call* も alternate world を名指せないこと、
             および、いかなる *public constructor* も等価な service を作れないことである。
```

```text
P15-R5-F2  an already-composed authority minted NEW capabilities from a superseded admission
           （Round 4 は「anchor は closed over afterward」という採択契約の文言から、
             composition 済 authority は cached credential として振る舞い、rotation /
             revocation は**次回の composition**のみを拘束すると開示していた。
             しかし当該文言が拘束するのは *anchor* であって、admission の *currency* では
             ない。両者は異なる問いである。）
           → request-facing call ごとに _require_bound_admission_still_current を実行し、
             canonical Store の current-admission pointer を新規に読み直す。
             採択text が列挙する4要件を、いずれも個別に実装した：
             (1) pointer が composition 時に捕捉した admission id を依然として指すこと、
             (2) 解決された current admission の generation が捕捉値と完全一致すること、
             (3) current admission が依然 ACTIVE であること、
             (4) 当該 Project / Binding を依然として restate していること。
             content-addressed record では (1) が (2)〜(4) を含意し得るが、採択text が
             4件を列挙している以上、論理的に等価な部分集合ではなく列挙どおりに実装した。
           → 本 recheck は raw trust anchor を必要としない。admission は composition 時点で
             暗号的に admit 済であり、pointer を動かせるのは anchor-signature-gated な
             commit_runtime_root_admission のみである。したがって anchor は依然として
             composition で一度だけ検証され、request-facing signature には現れない
             （Round 4 の §13.5 item 1 は**否定ではなく限定**された）。
           → recheck は grant resolution より前・authorization 評価より前に走るため、
             rotation / revocation 後の old service からの新規発行は
             adapter 呼び出し0・network 呼び出し0・authorization 評価0で拒否される。
           → 既発行の downstream capability は**遡及的に失効しない**（採択text 自身の
             限定）。専用の control が、A が current なうちに capability を発行して
             controlled adapter で実際に動作させ、その後 rotate し、当該 object と
             bound context が無変更であること、および同一 service が新規発行を
             拒否することを証明する。
             なお、当該 capability が rotation **後に execute できるか**は本 round の
             問いではない。Phase 14 自身の execution_context_still_current が、関係の
             有無を問わずあらゆる State transition の後に execution を拒否する
             既存機構であり、rotation commit も無関係な commit と同様にこれを踏む。
```

```text
P15-R5-F3  the declaration committer ordered its validity window LEXICOGRAPHICALLY
           （_require_declaration_shape_and_signature は valid_from / valid_until を
             生の文字列として `valid_from > valid_until` で比較していた。canonical
             timestamp grammar は optional な fractional part を許し、`.` は `Z` より
             小さくソートされるため、辞書順と時系列順は実際に食い違う。
             結果として両方向に誤っていた：
               valid_from="...T00:00:00Z"  valid_until="...T00:00:00.5Z"
                   実在する0.5秒のwindow            → 辞書順では**拒否**され、誤り
               valid_from="...T00:00:00.5Z" valid_until="...T00:00:00Z"
                   反転したwindow                    → 辞書順では**受理**され、誤り）
           → 既存の parser を再利用した。route.py の private `_instant` を無変更のまま
             engine.parse_utc_instant へ移し、route.py と deployment_registry.py の
             双方がこれを読む。採択契約が明示的に禁じる「第二の timestamp grammar」も
             「Runtime 固有の time owner」も新設していない。
           → committer は依然として clock を読まない。宣言された2つの bound を互いに
             順序付けるだけであり、後続の任意の instant に対する in-window 判定は
             observe_runtime_target 自身の問いのまま変更されていない。
           → 一意性は静的に証明される：本package で datetime を import する module は
             ちょうど1つ、fromisoformat を呼ぶ function は shipped tree 全体でちょうど1つ、
             それが engine.parse_utc_instant である。
```

Round 4 が閉じた work は本roundで一切退行していない。`transition_chain.py`・`admission_registry.py`・`identity.py`・`01_SCHEMA/` はいずれも無変更であり、monotonic signed generation / predecessor_ref chain、ancestor replay / generation skip / concurrent successor / terminal REVOKED の拒否、root-admission chain と pointer 機構、closed network allowlist / redirect boundary、pre-adapter schema validation、immutable/isolated adapter inputs、Boot / Human Authority freshness、signed deployment declaration と validity-window observation、Runtime-to-Evidence provenance、Phase 14 capability continuity は、すべて従来どおり green である。

canonical schema総数は `59` のまま変化していない（本roundは schema file を追加も変更もしていない）。

`P15-R5-F1`／`P15-R5-F2` が証明する範囲と、しない範囲は、従来どおり明示的に限定される（誇張しない）。

```text
REQUEST_FACING_OPERATION_HAS_NO_PUBLIC_CONSTRUCTOR=true                （証明済）
ATTACKER_AUTHORITY_CANNOT_BE_SUPPLIED_TO_THE_CANONICAL_OPERATION=true  （証明済、
                                                                        adapter / network 呼び出し
                                                                        ゼロ・authorization 評価
                                                                        ゼロ）
ROTATED_OR_REVOKED_SERVICE_ISSUES_NO_NEW_CAPABILITY=true               （証明済）
FRESH_COMPOSITION_AT_THE_CURRENT_ADMISSION_SUCCEEDS=true               （証明済）
ALREADY_ISSUED_CAPABILITIES_RETROACTIVELY_REVOKED=false                （採択text自身の限定・
                                                                        主張しない）
CLOSURE_CELLS_ARE_UNWRITABLE_BY_IN_PROCESS_CODE=false                  （Pythonでは不可能・
                                                                        開示済・主張しない）
TARGET_EPOCH_REACTIVATION_MECHANISM_BUILT=false                        （本round範囲外・
                                                                        主張しない）
LIVE_DEPLOYMENT_ENTRYPOINT_INVOKES_THE_MECHANISM=false                 （未実装・主張しない）
```

実装範囲の所有は変わらず`10_RUNTIME/RUNTIME_INDEX.md`・`10_RUNTIME/RUNTIME_CONTRACT.md`にある（本correction roundは`RUNTIME_CONTRACT.md`にsection 14、`RUNTIME_INDEX.md`にsection 4.5を追加した）。

SHUKOU自身が固定した終端は変わらず、本addendumもこれを変更しない。

```text
CURRENT_PHASE=15_BOUNDED_RUNTIME_OBSERVATION_AND_TRUSTED_PROVISIONING
CURRENT_PHASE_ISSUE=64
CURRENT_PHASE_STATE=STRUCTURAL_REVIEW_ROUND_5_CORRECTIONS_DELIVERED_PR_OPEN
STRUCTURAL_REVIEW_ROUNDS_APPLIED=5
STRUCTURAL_REVIEW_ROUND_1_FINDINGS_CLOSED=6
STRUCTURAL_REVIEW_ROUND_2_FINDINGS_CLOSED=2
STRUCTURAL_REVIEW_ROUND_3_FINDINGS_CLOSED=2
STRUCTURAL_REVIEW_ROUND_4_FINDINGS_CLOSED=2
STRUCTURAL_REVIEW_ROUND_5_FINDINGS_CLOSED=3
CANONICAL_SCHEMA_COUNT=59
NEW_SCHEMA_FILES_ADDED_THIS_ROUND=0
NEW_BRANCH=false
NEW_PR=false
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_15_COMPLETE=false
PHASE_16_ALLOWED=false
LIVE_EXTERNAL_WRITE_AUTHORITY=false
REMOTE_COMMAND_EXECUTION_AUTHORITY=false
RUNTIME_CREDENTIAL_USE_AUTHORITY=false
```

本addendumは`05_PHASE_ACCEPTANCE_LEDGER.md`が所有するacceptance receiptを代行しない。またPR #65自身のmergeやIssue #64のcloseを主張しない — どちらもSHUKOUの別途決定の対象であり、本correction roundはstructural findingsの閉鎖のみを行う。

# 22. Phase 15 Structural Review Round 6 correction addendum (P15-R6-F1, Issue #64 / PR #65)

本節は、セクション21のaddendum記録時点（`CURRENT_PHASE_STATE=STRUCTURAL_REVIEW_ROUND_5_CORRECTIONS_DELIVERED_PR_OPEN`）以降にrepositoryへ生じた変化のうち、local `git log`とPR #65 / Issue #64自身のReview commentにより独立再観測できた`OBSERVED_GITHUB_FACT`のみを追記する、bounded addendumである。セクション16〜21の全面再投影ではない。

```text
ADDENDUM_OBSERVED_AT_UTC=2026-09-09
ADDENDUM_OBSERVATION_METHOD=LOCAL_GIT_LOG_AND_PR_65_ISSUE_64_REVIEW_COMMENTS
```

| Field | Observed value |
|---|---|
| Dedicated Pull Request | [#65](https://github.com/manosube/manosube-agent-civilization-os/pull/65) — **open**, not merged |
| PR #65 reviewed HEAD (Structural Review Round 6 の対象) | `2cad6b5de77a6aa56fa34d26b559522c7db53f5e` |
| SHUKOU adoption | Issue #64 上の `ADOPT_P15_R6_FINAL_ADMISSION_INTEGRITY_AND_PRE_ISSUANCE_BARRIER`（Human Authority `manosube`）により、`ADOPTED_FINDING=P15-R6-F1` が verbatim で採択済 |
| Round 5 findings の Round 6 自身による処分 | `P15_R5_F1_CLOSED=true`（closure が担う ownership boundary は無変更）、`P15_R5_F3_CLOSED=true`（instant ordering は無変更）。`P15-R5-F2` のみ reopen され `P15-R6-F1` として再採番された。 |
| This correction round's own commits | branch `agent/issue-64-phase15-runtime-adapter` 上、reviewed HEAD `2cad6b5d` の直上に積まれた新規commitのみ。history rewrite（amend / rebase / force-push）は行っていない。新規branchも新規PRも作成していない。 |

Round 4・Round 5 の Review が名指しした「同一のtrust-boundary semantic classの再発」系列は、Round 6 でもう一段進む。

```text
ROUND 5   trust decision の boundary は CLOSURE へ置換され、per-call の
          current-admission recheck が導入されたが、その recheck は request の
          **先頭で一度だけ**走り、かつ resolved record が**自分自身について申告した
          field**しか読んでいなかった
ROUND 6   -> recheck を TWO BARRIERS 化し、composition 時に捕捉した
             IMMUTABLE COMMITMENT（id / generation / semantic fingerprint）に対して、
             resolved body から**独立に再計算した** identity と fingerprint の
             完全一致を要求する
```

採択された構造的findingと、その閉鎖範囲：

```text
P15-R6-F1  the per-call admission barrier ran ONCE and never re-established RESOLVED-RECORD
           INTEGRITY
           （2つの独立に再現可能な counterexample を持つ。）

           (1) POST-CHECK ROTATION / REVOCATION RACE
               request-facing closure は先頭で _require_bound_admission_still_current を
               一度だけ実行し、その後 grant / declaration / subject の解決と Authority
               評価を行い、最後に**同一の初期 Boot snapshot**から
               ProjectionExecutionCapability を構築して返していた。第二の admission
               barrier は存在しなかった。したがって canonical な rotation / revocation が
               初回 check の後・capability 構築の前に commit された場合、old service は
               自身の bound admission が current でなくなった後に新規 capability を
               依然として発行していた。これは「rotation / revocation は *new capability
               issuance* を阻止する」という採択条件そのものへの違反である。

           (2) RESOLVED-RECORD INTEGRITY IS NOT RE-ESTABLISHED
               per-call helper は resolved record を schema 検証したうえで
               generation / status / project_id / project_binding_ref の4点のみを
               検査していた。runtime_root_admission_id も semantic fingerprint も
               resolved body から**再計算していない**し、composition 時に admit した
               record と re-resolve した body を**比較してもいない**。
               結果として、current id の下での Store-level substitution
               （predecessor_ref / declared_at / signature を改変しつつ
                 generation / status / project / binding はそのまま）は
               per-call gate を通過し得た。composition が証明したのは ORIGINAL record
               であり、per-call recheck は「現在 resolve される body が依然として同一の
               record であること」を一度も再証明していなかった。特定 field の読み値が
               従来どおりであることしか確認していなかった。

           → 採択された forward correction（Round 5 の closure boundary と timestamp
             owner は無変更）：
             1. composition 時に、anchor 検証済 admission への immutable canonical
                commitment を捕捉する。id と generation だけでなく、独立に再計算された
                semantic fingerprint も含む（bound_semantic_fingerprint）。
             2. 各 request で、Store 解決後に current admission の identity と semantic
                fingerprint を独立に再計算し、捕捉済 commitment との**完全一致**を要求
                する。resolved body 自身の自己申告 field との比較ではない
                （改ざんされた body は自身の改ざん内容に整合する id / fingerprint を
                  自己申告でき、自己比較は自明に通過してしまうため）。
             3. 全ての grant / declaration / subject 解決と Authority 評価の**後**、
                capability の構築・返却の**直前**に、再度 Boot し、
                identity + fingerprint + generation + status + project / binding の
                **全6要件**を再実行する（部分集合ではない）。
             4. 返却する ProjectionExecutionContext の state_revision /
                semantic_fingerprint を、初回 Boot ではなくこの FINAL Boot から構築する。
             5. deterministic control を追加する（rotation / revocation の
                barrier 間着弾、current-id body substitution、無変更 admission の
                positive control）。
             6. Round 5 で閉じた request signature を維持する。Store / Project /
                Binding / admission / anchor / 代替 authority object の再出現なし、
                いかなる新規 public request parameter も追加しない。

           → 6要件の検査順序（本round自身の judgment call、開示済）：
             1. pointer が composition 時に捕捉した admission id を依然として指すこと
             2. resolved current admission の generation が捕捉値と完全一致すること
             3. current admission が依然 ACTIVE であること
             4. 当該 Project / Binding を依然として restate していること
             5. resolved body から再計算した identity が捕捉値と一致すること      【新規】
             6. resolved body から再計算した semantic fingerprint が一致すること  【新規】
             5・6 を最後に置くのは _require_currently_admitted 自身が currency check を
             最後に置くのと同一の理由による。2〜4 に違反する body は必ず 5 にも違反する
             ため、5 を先に置くと 2〜4 の全ての拒否が単一の識別不能な「identity
             mismatch」へ収束し、各 control が主張する内容を証明しなくなる。

           → 開示済 judgment call：FINAL Boot へ移すのは **State snapshot のみ**である。
             human_authority_ref / human_authority_signing_key、および そこから導かれる
             decisions / authorities / context 自身の github_authority_ref は、従来どおり
             **初回 Boot** を source とする。それらは Authority 評価が実際に走った対象で
             あり、返却される capability が正当に代表する内容そのものである。事後に
             later Boot から再導出すると、2つの Boot の間に Human Authority の re-binding が
             発生した場合、「実際に authorize された内容」と「context が authorize されたと
             主張する内容」が食い違う — 本roundが閉じようとしている defect より厳密に
             悪い defect になる。採択text の item 4 が名指すのは
             state_revision / semantic_fingerprint であり、移動するのはそれだけである。
```

本roundが変更した shipped file は `src/manosube_agent_civilization/runtime/bootstrap.py` **ただ1つ**である。`admission_registry.py`・`transition_chain.py`・`identity.py`・`engine.py`・`route.py`・`deployment_registry.py`・`__init__.py`・`01_SCHEMA/` はいずれも無変更であり、Round 1〜5 が閉じた work は本roundで一切退行していない。monotonic signed generation / predecessor_ref chain、ancestor replay / generation skip / concurrent successor / terminal REVOKED の拒否、closure が担う ownership boundary、closed network allowlist / redirect boundary、single instant-parsing owner、Runtime-to-Evidence provenance、Phase 14 capability continuity は、すべて従来どおり green である。

canonical schema総数は `59` のまま変化していない（本roundは schema file を追加も変更もしていない）。

`P15-R6-F1` が証明する範囲と、しない範囲は、従来どおり明示的に限定される（誇張しない）。

```text
ROTATION_LANDING_BETWEEN_THE_TWO_BARRIERS_ISSUES_A_CAPABILITY=false     （証明済、実際に
                                                                         shipped committer で
                                                                         successor を commit した
                                                                         real race）
REVOCATION_LANDING_BETWEEN_THE_TWO_BARRIERS_ISSUES_A_CAPABILITY=false   （証明済）
CURRENT_ID_BODY_SUBSTITUTION_ISSUES_A_CAPABILITY=false                  （証明済、authorization
                                                                         評価0・adapter 呼び出し0）
UNCHANGED_CURRENT_ADMISSION_STILL_ISSUES_A_WORKING_CAPABILITY=true      （証明済、controlled
                                                                         FakeGitHubAdapter まで到達）
ISSUED_CONTEXT_STATE_SNAPSHOT_SOURCED_FROM_FINAL_BOOT=true              （証明済）
ISSUED_CONTEXT_AUTHORITY_BINDING_SOURCED_FROM_INITIAL_BOOT=true         （意図的・開示済）
ALREADY_ISSUED_CAPABILITIES_RETROACTIVELY_REVOKED=false                 （採択text自身の限定・
                                                                         主張しない）
CLOSURE_CELLS_ARE_UNWRITABLE_BY_IN_PROCESS_CODE=false                   （Pythonでは不可能・
                                                                         開示済・主張しない）
TARGET_EPOCH_REACTIVATION_MECHANISM_BUILT=false                         （本round範囲外・
                                                                         主張しない）
LIVE_DEPLOYMENT_ENTRYPOINT_INVOKES_THE_MECHANISM=false                  （未実装・主張しない）
```

実装範囲の所有は変わらず`10_RUNTIME/RUNTIME_INDEX.md`・`10_RUNTIME/RUNTIME_CONTRACT.md`にある（本correction roundは`RUNTIME_CONTRACT.md`にsection 15、`RUNTIME_INDEX.md`にsection 4.6を追加した）。

SHUKOU自身が固定した終端は変わらず、本addendumもこれを変更しない。

```text
CURRENT_PHASE=15_BOUNDED_RUNTIME_OBSERVATION_AND_TRUSTED_PROVISIONING
CURRENT_PHASE_ISSUE=64
CURRENT_PHASE_STATE=STRUCTURAL_REVIEW_ROUND_6_CORRECTIONS_DELIVERED_PR_OPEN
STRUCTURAL_REVIEW_ROUNDS_APPLIED=6
STRUCTURAL_REVIEW_ROUND_1_FINDINGS_CLOSED=6
STRUCTURAL_REVIEW_ROUND_2_FINDINGS_CLOSED=2
STRUCTURAL_REVIEW_ROUND_3_FINDINGS_CLOSED=2
STRUCTURAL_REVIEW_ROUND_4_FINDINGS_CLOSED=2
STRUCTURAL_REVIEW_ROUND_5_FINDINGS_CLOSED=3
STRUCTURAL_REVIEW_ROUND_6_FINDINGS_CLOSED=1
SHIPPED_FILES_CHANGED_THIS_ROUND=1
CANONICAL_SCHEMA_COUNT=59
NEW_SCHEMA_FILES_ADDED_THIS_ROUND=0
NEW_BRANCH=false
NEW_PR=false
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_15_COMPLETE=false
PHASE_16_ALLOWED=false
LIVE_EXTERNAL_WRITE_AUTHORITY=false
REMOTE_COMMAND_EXECUTION_AUTHORITY=false
RUNTIME_CREDENTIAL_USE_AUTHORITY=false
```

本addendumは`05_PHASE_ACCEPTANCE_LEDGER.md`が所有するacceptance receiptを代行しない。またPR #65自身のmergeやIssue #64のcloseを主張しない — どちらもSHUKOUの別途決定の対象であり、本correction roundはstructural findingsの閉鎖のみを行う。

# 23. Phase 15 Structural Review Round 7 correction addendum (P15-R7-F1, Issue #64 / PR #65)

本節は、セクション22のaddendum記録時点（`CURRENT_PHASE_STATE=STRUCTURAL_REVIEW_ROUND_6_CORRECTIONS_DELIVERED_PR_OPEN`）以降にrepositoryへ生じた変化のうち、local `git log`とPR #65 / Issue #64自身のReview commentにより独立再観測できた`OBSERVED_GITHUB_FACT`のみを追記する、bounded addendumである。セクション16〜22の全面再投影ではない。

```text
ADDENDUM_OBSERVED_AT_UTC=2026-09-09
ADDENDUM_OBSERVATION_METHOD=LOCAL_GIT_LOG_AND_PR_65_ISSUE_64_REVIEW_COMMENTS
```

| Field | Observed value |
|---|---|
| Dedicated Pull Request | [#65](https://github.com/manosube/manosube-agent-civilization-os/pull/65) — **open**, not merged |
| PR #65 reviewed HEAD (Structural Review Round 7 の対象) | `d3df34feeb19f39bc558335f3020310d266e150b` |
| SHUKOU adoption | Issue #64 上の `ADOPT_P15_R7_EXACT_FULL_ADMISSION_RECORD_COMMITMENT`（Human Authority `manosube`）により、`ADOPTED_FINDING=P15-R7-F1` が verbatim で採択済 |
| Round 6 findings の Round 7 自身による処分 | `P15_R6_F1_TWO_BARRIER_PLACEMENT_CLOSED=true`（two barriers / pre-issuance placement / final Boot snapshot は無変更）。reopen された finding はなく、Round 6 が閉じた barrier が**何を証明するか**の範囲のみが `P15-R7-F1` として新規に採択された。 |
| This correction round's own commits | branch `agent/issue-64-phase15-runtime-adapter` 上、reviewed HEAD `d3df34fe` の直上に積まれた新規commitのみ。history rewrite（amend / rebase / force-push）は行っていない。新規branchも新規PRも作成していない。 |

Round 4〜Round 6 の Review が名指しした「同一のtrust-boundary semantic classの再発」系列は、Round 7 で最後の面へ到達する。

```text
ROUND 6   per-call recheck は TWO BARRIERS 化され、resolved body から独立に
          再計算した identity / semantic fingerprint を composition 時の
          commitment と照合するようになった
ROUND 7   -> しかしその2つの再計算はいずれも ROOT_ADMISSION_SEMANTIC_FIELDS の
             hash であり、当該 projection は record 自身の declared id /
             declared semantic fingerprint / signature block を**意図的に除外**
             している。therefore commitment を EXACT FULL RECORD へ拡張し、
             id と fingerprint については declared == recomputed == bound の
             three-way 一致を要求する
```

採択された構造的findingと、その閉鎖範囲：

```text
P15-R7-F1  the per-call barriers committed to a PROJECTION of the record, and that projection
           excludes exactly the fields a Store-level substitution could still move
           （3つの独立に再現可能な counterexample を持つ。）

           bound_admission_id と bound_semantic_fingerprint は**いずれも**
           ROOT_ADMISSION_SEMANTIC_FIELDS の hash である。当該 projection は
           record 自身の3 field を意図的に除外している。除外理由は各々正当である：

               runtime_root_admission_id                    identity は自分自身を
                                                            対象に計算できない
               runtime_root_admission_semantic_fingerprint  同上
               signature (algorithm / key_id / value)       signature は自分自身の
                                                            value を covered できない

           各 barrier は recomputed_id / recomputed_fingerprint を body の semantic
           fields から再計算し、composition 時の bound 値とのみ比較していた。resolved
           body 自身が**申告している** runtime_root_admission_id /
           runtime_root_admission_semantic_fingerprint が当該再計算値と一致するかは
           一度も検査しておらず、resolved body の signature（あるいは full-record
           commitment）を composition 時に捕捉した何かと比較してもいなかった。

           結果として、以下のいずれか**1つだけ**を変更する Store-level substitution は
           （semantic field を全て byte-identical に保つため）両 barrier を素通りした：

               (1) declared runtime_root_admission_id のみを別の schema-valid 文字列へ
               (2) declared runtime_root_admission_semantic_fingerprint のみを同様に
               (3) signature.value（または signature.key_id）のみを schema-valid な
                   形状のまま別値へ

           3例いずれも require_valid_root_admission は通過（shape のみ）、
           semantic fields から再計算した id / fingerprint は bound 値と一致、
           generation / status / project / binding も無変更 — Round 6 までの全 check が
           通過し、composition が anchor 検証した「その record そのもの」ではなくなった
           record から capability が発行され得た。

           → 採択された forward correction（Round 5 の closure boundary、Round 6 の
             two-barrier placement、transition-chain mechanism はいずれも無変更。
             既存の3 cell は削除も置換もせず、4つ目を**追加**する）：
             1. composition 時に、EXACT FULL / schema-valid / anchor-verified な
                admission record への immutable commitment を捕捉する
                （bound_full_record_commitment）。既存の bound_admission_id /
                bound_generation / bound_semantic_fingerprint は全て維持する。
             2. 各 barrier で3要件を追加する：
                - resolved record の **declared** id が **recomputed** id と一致し、
                  かつ両者が **bound** id と一致すること（three-way。Round 6 は
                  recomputed-vs-bound のみ）
                - declared semantic fingerprint についても同一の three-way 一致
                - signature.algorithm / signature.key_id / signature.value を含む
                  exact full-record commitment が composition 時の値と一致すること
             3. full-record commitment は本repositoryの canonical serialization owner
                （`state.canonicalize.canonical_json_bytes`）を再利用する。第二の
                serialization mechanism は導入しない。raw trust anchor は retain も
                reintroduce もしない。
             4. isolated control を追加する（declared id のみ / declared semantic
                fingerprint のみ / signature.value のみ / signature.key_id のみ）。
                各々 Authority 評価**前**に refuse し、adapter / network 呼び出しは0。
             5. Round 6 の control（declared_at semantic-field substitution、
                mid-request rotation / revocation、unchanged-positive、final-Boot
                snapshot）は一切削除も弱化もしない。
             6. Round 5 で閉じた request signature を維持する。いかなる新規 public
                request parameter も追加しない。

           → 9要件の検査順序（本round自身の judgment call、開示済）：
             1〜6 は Round 6 のまま（pointer / generation / status / project・binding /
             recomputed id / recomputed fingerprint）。追加分は最後に置く：
             7. declared id == recomputed id（かつ両者 == bound id）      【新規】
             8. declared fingerprint == recomputed fingerprint（同上）    【新規】
             9. exact full-record commitment == composition 時の値        【新規】
             9 を最後に置くのは §15.1 が既に述べた ordering rationale の延長である。
             9 は本 function 中で最も広い check であり、5〜8 のいずれかに違反する body は
             必ず 9 にも違反する。9 を先に置くと全ての拒否が単一の識別不能な
             「full-record commitment mismatch」へ収束し、7・8 は自身の理由で拒否する
             機会を永久に失う。最後に置くことで、9 は「semantic field も declared id も
             declared fingerprint も全て無変更で、signature だけが差し替えられた body」
             という、より狭い check では観測不能な唯一のケースによって isolate される。

           → 開示済 judgment call：7・8 の three-way 一致は、Round 6 が正当に退けた
             self-comparison ではない。Round 6 の指摘（改ざんされた body は自身の改ざん
             内容に整合する id / fingerprint を自己申告でき、自己比較は自明に通過する）は
             正しく、だからこそ 5・6 は **bound** 値を anchor とし続ける。7・8 はそれを
             弱めない：bound 値は依然として等式連鎖の anchor であり、declared field を
             連鎖に加えることは通過条件を**狭める**方向にしか働かない。
             `declared == recomputed == bound` は `recomputed == bound` より厳に強く、
             代替ではない。
```

本roundが変更した shipped file は `src/manosube_agent_civilization/runtime/bootstrap.py` **ただ1つ**である。`admission_registry.py`・`transition_chain.py`・`identity.py`・`engine.py`・`route.py`・`deployment_registry.py`・`__init__.py`・`01_SCHEMA/` はいずれも無変更であり、Round 1〜6 が閉じた work は本roundで一切退行していない。特に `identity.py` の `ROOT_ADMISSION_SEMANTIC_FIELDS` とその3 field の除外は**意図的に維持**している — 除外理由自体は正当であり、本roundが行うのは「除外された field に対して別の commitment を持たせる」ことであって、projection の定義を変えることではない。

canonical schema総数は `59` のまま変化していない（本roundは schema file を追加も変更もしていない）。

`P15-R7-F1` が証明する範囲と、しない範囲は、従来どおり明示的に限定される（誇張しない）。

```text
DECLARED_ID_SUBSTITUTION_ISSUES_A_CAPABILITY=false                      （証明済、isolated
                                                                         control、authorization
                                                                         評価0・adapter 呼び出し0）
DECLARED_SEMANTIC_FINGERPRINT_SUBSTITUTION_ISSUES_A_CAPABILITY=false    （証明済、同上）
SIGNATURE_VALUE_SUBSTITUTION_ISSUES_A_CAPABILITY=false                  （証明済、同上。
                                                                         full-record commitment
                                                                         が実働していることを
                                                                         証明する control）
SIGNATURE_KEY_ID_SUBSTITUTION_ISSUES_A_CAPABILITY=false                 （証明済、同上）
FULL_RECORD_COMMITMENT_USES_THE_ONE_CANONICAL_SERIALIZATION_OWNER=true  （証明済、static
                                                                         conformance）
SECOND_SERIALIZATION_MECHANISM_INTRODUCED=false                         （証明済）
FULL_RECORD_COMMITMENT_RETAINS_A_RAW_TRUST_ANCHOR=false                 （証明済。record は
                                                                         signature を持つが
                                                                         key は持たない）
PER_CALL_SIGNATURE_REVERIFICATION_AGAINST_THE_ANCHOR=false              （意図的・開示済。
                                                                         anchor は composition
                                                                         で一度だけ consume され
                                                                         破棄される。9 が証明する
                                                                         のは「signature が有効か」
                                                                         ではなく「record が
                                                                         composition が証明した
                                                                         その record のままか」）
UNCHANGED_CURRENT_ADMISSION_STILL_ISSUES_A_WORKING_CAPABILITY=true      （証明済、controlled
                                                                         FakeGitHubAdapter まで到達）
ROUND_6_TWO_BARRIER_PLACEMENT_CHANGED=false                             （無変更）
ROUND_5_CLOSURE_BOUNDARY_CHANGED=false                                  （無変更）
ALREADY_ISSUED_CAPABILITIES_RETROACTIVELY_REVOKED=false                 （採択text自身の限定・
                                                                         主張しない）
CLOSURE_CELLS_ARE_UNWRITABLE_BY_IN_PROCESS_CODE=false                   （Pythonでは不可能・
                                                                         開示済・主張しない）
LIVE_DEPLOYMENT_ENTRYPOINT_INVOKES_THE_MECHANISM=false                  （未実装・主張しない）
```

実装範囲の所有は変わらず`10_RUNTIME/RUNTIME_INDEX.md`・`10_RUNTIME/RUNTIME_CONTRACT.md`にある（本correction roundは`RUNTIME_CONTRACT.md`にsection 16、`RUNTIME_INDEX.md`にsection 4.7を追加した）。

SHUKOU自身が固定した終端は変わらず、本addendumもこれを変更しない。

```text
CURRENT_PHASE=15_BOUNDED_RUNTIME_OBSERVATION_AND_TRUSTED_PROVISIONING
CURRENT_PHASE_ISSUE=64
CURRENT_PHASE_STATE=STRUCTURAL_REVIEW_ROUND_7_CORRECTIONS_DELIVERED_PR_OPEN
STRUCTURAL_REVIEW_ROUNDS_APPLIED=7
STRUCTURAL_REVIEW_ROUND_1_FINDINGS_CLOSED=6
STRUCTURAL_REVIEW_ROUND_2_FINDINGS_CLOSED=2
STRUCTURAL_REVIEW_ROUND_3_FINDINGS_CLOSED=2
STRUCTURAL_REVIEW_ROUND_4_FINDINGS_CLOSED=2
STRUCTURAL_REVIEW_ROUND_5_FINDINGS_CLOSED=3
STRUCTURAL_REVIEW_ROUND_6_FINDINGS_CLOSED=1
STRUCTURAL_REVIEW_ROUND_7_FINDINGS_CLOSED=1
SHIPPED_FILES_CHANGED_THIS_ROUND=1
CANONICAL_SCHEMA_COUNT=59
NEW_SCHEMA_FILES_ADDED_THIS_ROUND=0
NEW_BRANCH=false
NEW_PR=false
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_15_COMPLETE=false
PHASE_16_ALLOWED=false
LIVE_EXTERNAL_WRITE_AUTHORITY=false
REMOTE_COMMAND_EXECUTION_AUTHORITY=false
RUNTIME_CREDENTIAL_USE_AUTHORITY=false
```

本addendumは`05_PHASE_ACCEPTANCE_LEDGER.md`が所有するacceptance receiptを代行しない。またPR #65自身のmergeやIssue #64のcloseを主張しない — どちらもSHUKOUの別途決定の対象であり、本correction roundはstructural findingsの閉鎖のみを行う。

---

# 24. Phase 16 bounded addendum (Multi-Model Replaceability and Phase 12 Execution Continuity, Issue #66)

本節は、セクション23のaddendum記録時点以降にrepositoryへ生じた変化のうち、local `git log`とIssue #66自身のadoption commentにより独立再観測できた`OBSERVED_GITHUB_FACT`のみを追記する、bounded addendumである。セクション16〜23の全面再投影ではない。

```text
ADDENDUM_OBSERVED_AT_UTC=2026-09-10
ADDENDUM_OBSERVATION_METHOD=LOCAL_GIT_LOG_AGAINST_ORIGIN_MAIN_AND_ISSUE_66_ADOPTION
```

| Field | Observed value |
|---|---|
| Current `origin/main` HEAD | `94f067ba6acb4e4459ef3ecd15d6c8c1332e1db7` |
| PR #65 (Phase 15, Issue #64) | **Merged** — merge commit `94f067b` |
| Governing Issue, current Phase | [#66 — Phase 16: Multi-Model Replaceability and Phase 12 Execution Continuity](https://github.com/manosube/manosube-agent-civilization-os/issues/66) |
| SHUKOU implementation adoption | `ADOPT_P16_D001_MULTI_MODEL_REPLACEABILITY_AND_PHASE12_EXECUTION_CONTINUITY` |
| Adoption's own reviewed main SHA | `94f067ba6acb4e4459ef3ecd15d6c8c1332e1db7` (identical to the `origin/main` HEAD observed above) |
| Dedicated implementation branch | `agent/issue-66-phase16-multi-model-replaceability` |
| Dedicated Pull Request | Opened against `main`, per the adoption's own `NEW_PR=true` / `PULL_REQUEST_TARGET=main` |

**Correction to this addendum's own prior text.** An earlier revision of this section stated
that the adoption comment (`issuecomment-5610016955`) had been "corrected" to `NEW_PR=false` and
that no PR would be opened for that reason. That statement was false: the adoption comment, read
directly and in full from the GitHub API, carries exactly one version of the branch/PR policy —
`NEW_BRANCH=true` / `BRANCH=agent/issue-66-phase16-multi-model-replaceability` / `NEW_PR=true` /
`PULL_REQUEST_TARGET=main` — and closes with "Claude Code may now implement on the named new
branch and open one dedicated PR." No comment on Issue #66 revises or supersedes it. The correct
reading is simply that the implementing delegate pushed the branch without opening the PR itself,
so that PR creation happens only after the reviewing session has independently re-verified the
delivered HEAD — never that the adoption withdrew its own `NEW_PR=true` authorization.

```text
PHASE_15_MERGED=true
PHASE_15_MERGE_COMMIT=94f067b
PHASE_15_COMPLETE=true
COMPLETED_THROUGH_PHASE=15
CURRENT_PHASE=16_MULTI_MODEL_REPLACEABILITY_AND_PHASE12_EXECUTION_CONTINUITY
CURRENT_PHASE_ISSUE=66
CURRENT_PHASE_STATE=IMPLEMENTATION_DELIVERED_PR_OPENED_AWAITING_STRUCTURAL_REVIEW
PHASE_16_ALLOWED=true
PHASE_16_COMPLETE=false
PHASE_17_ALLOWED=false
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
```

`ADOPT_P16_D001_...`が要求する実装範囲は`11_MODEL_RUNTIME/MODEL_RUNTIME_INDEX.md`・`11_MODEL_RUNTIME/MODEL_RUNTIME_CONTRACT.md`が所有する。人間目的は次の一点である。

```text
Agent / model / provider は、Canonical State・Authority・Difference・Boundary・Evidence
requirements・resumable work continuity のいずれも失うことなく置換できる
```

本deliveryが実装したcontract項目と、その閉鎖手段：

```text
P16-C1  provider-neutral execution binding
        一つのrequest/response境界が、exact State revision + semantic fingerprint /
        State-bound Work Unit identity / 同一 Difference reference / required capability /
        explicit Authority reference AND decision / applicable Boundary reference /
        Evidence requirements / Phase 12 Temporary Agent Execution Contract identity を
        すべて束ねる。provider payload・chat transcript・model memory・provider session id が
        到達しうるkeyは一つも存在しない。

P16-C2  replaceable Model Adapter
        `ModelAdapter` Protocol 一つ。実装は二つで、互いにbase classもhelperも
        module-level stateも共有しない（seeded-world 型と request-derived 型）。
        provider SDK importは shipped tree 全体でゼロ（AST走査で証明）。

P16-C3  non-authoritative model output
        accepting classification `CANDIDATE_ACCEPTED` は adapter 語彙に存在しない。
        route は adapter result から**厳密に3 key**しか読まず、しかも文字列literalではなく
        `MODEL_ADAPTER_RESULT_KEYS` 経由で読む。したがって model による
        Authority mint / Evidence 生成 / Difference closure / Change commit /
        Boundary 拡張は「拒否される」のではなく「call shape が存在しない」。
        `adapter.py` は Store / Boot / Agent Runtime / Authority / Evidence /
        Difference / Change のいずれもimportしない。

P16-C4  model-swap continuity
        Agent A が停止し、Agent B が Store-resolved canonical records のみから再開する。
        session境界を越える値は Work Unit の content address 一つ（plain string）だけ。
        conversation handoff / model memory / provider-local session は、要求もされず
        受理もされない — routeのsignatureにそれらが到達しうるparameterが無い。

P16-C5  session-loss recovery
        完全なsession喪失が canonical Store のみから復旧される。stale State /
        substituted references / cross-project / cross-Store / wrong-Difference /
        wrong-Authority / wrong-Boundary / wrong-State-revision は、いずれも
        adapter呼び出しの**前**に、それぞれ固有のtyped errorで拒否される。

P16-C6  typed outcomes and bounded failure
        7つのcanonical outcome。うち6つが非受理で、それぞれ固有のreceipt statusへ写る。
        いずれのfailureもsuccess / closure / authoritative absenceへは変換されない。

P16-C7  first real-model execution barrier
        controlled adapterのみを出荷。live credential / real-provider call /
        remote command execution / autonomous change はいずれも本deliveryの外。
```

Authority統合について本deliveryが公開した判断（adopted textが両案を許した箇所）：

```text
採用 = 既存 `authority` package への narrowly-scoped extension
       `evaluate_model_execution_authorization`

理由 = `evaluate_authority` は唯一の *Change-permission* evaluator であり、その closed
       request shape は difference record / requested_action(action_kind・reversibility・
       opaque operation payload) / requested_scope / rules・prohibitions・approvals /
       current_state_revision・fingerprint を要求し、AUTONOMOUS / HUMAN_APPROVAL_REQUIRED /
       PROHIBITED を返す。Phase 16 が問うのは *capability-grant* の問いであり、requested
       action も reversibility も scope containment も rule/approval precedence も持たない。
       強引に通せば action_kind を発明することになり、未知だが well-formed な kind は
       capability decision ではなく HUMAN_APPROVAL_REQUIRED へ fail closed する。
       これは P13-R3-F1（verifier selection）と P14-R1-F1（projection authorization）が
       各々記録したのと同一の理由であり、本件はその第三例である。第二のAuthority ownerは
       作られていない。
```

```text
MODEL_RUNTIME_OWNER_COUNT=1
PUBLIC_MODEL_RUNTIME_ENTRY_POINT_COUNT=5
MODEL_EXECUTION_AUTHORIZATION_ENTRY_POINT_COUNT=1
SECOND_EXECUTION_CONTRACT=false
AGENT_RUNTIME_FILES_CHANGED=0
PROVIDER_SDK_DEPENDENCY_COUNT=0
CANONICAL_SCHEMA_COUNT=66
NEW_SCHEMA_FILES_ADDED_THIS_PHASE=7
NEW_BRANCH=true
NEW_PR=true
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_16_COMPLETE=false
PHASE_17_ALLOWED=false
LIVE_PROVIDER_CREDENTIAL_USE=false
REMOTE_COMMAND_EXECUTION_AUTHORITY=false
AUTONOMOUS_CHANGE_AUTHORITY=false
```

`07_AGENT_RUNTIME/`（Phase 12 Temporary Agent Execution Contract）とその実装
`src/manosube_agent_civilization/agent_runtime/` は、本Phaseにより**一切変更されていない**
（`AGENT_RUNTIME_FILES_CHANGED=0`）。model_runtime は `boot_project` をimportせず、Bootへは
Phase 12自身のroute経由でのみ、literal call site一箇所から到達する。

本addendumは、`05_PHASE_ACCEPTANCE_LEDGER.md`が所有するPhase 15の恒久的なacceptance receipt（merge SHA、Human acceptance record、after-state re-observation）を代行しない。それは同ledgerの別途更新の対象であり、本書は現在地を示すための最小限の`OBSERVED_GITHUB_FACT`のみを記録する。またPR作成・merge・Issue closeのいずれも主張しない — いずれもSHUKOUの別途決定の対象である。

---

# 25. Phase 16 Structural Review Round 1 bounded addendum (Issue #66, PR #67)

本節は、構造参謀によるStructural Review Round 1と、SHUKOUによるその採択を、独立再観測できた事実のみ記録するbounded addendumである。

```text
ADDENDUM_OBSERVED_AT_UTC=2026-09-10
ADOPTION_ID=ADOPT_P16_R1_EVIDENCE_AND_ADAPTER_BOUNDARY_CORRECTION
GOVERNING_ISSUE=#66
TARGET_PR=#67
REVIEWED_HEAD=b1e3c3eaf6631639b699dad7d90dc9e39ae1e085
ADOPTED_FINDINGS=P16-R1-F1,P16-R1-F2,P16-R1-F3
IMPLEMENTATION_TARGET=EXISTING_BRANCH_AND_PR_67_ONLY
NEW_BRANCH=false
NEW_PR=false
```

3件の対応内容：

```text
P16-R1-F1  route_model_execution_to_evidence が execution_outcome != CANDIDATE_ACCEPTED の
           committed Envelope を derive_evidence へ渡す前に拒否するようになった。
           MODEL_OUTCOME_TO_RECEIPT_STATUS 経由（リテラル文字列 "CANDIDATE_ACCEPTED" を
           再度書かない）で判定する。

P16-R1-F2  derive_evidence が返す Evidence 自身の difference_ref が、Store-resolved
           Envelope の difference_ref と厳密に一致することを、Evidence owner呼び出し後に
           要求するようになった。一致しないevidence_request（同一project内の別Difference
           への再derivation）は拒否される。

P16-R1-F3  execute_model_work_unit が adapter.adapter_identity の完全な閉じた形状
           （adapter/versionの2フィールドのみ、両方非空文字列）を、request identity計算前・
           adapter呼び出し前に検証するようになった。model_runtime/engine.py の新規
           require_valid_adapter_identity が、既存の model_execution_envelope.schema.json
           の adapter_identity 定義を再利用する。
```

`07_AGENT_RUNTIME/`・既存canonical owner・既に受理されたPhase 16の境界・既存のpositive
model-swap/session-loss proofsは、いずれも変更されていない。

```text
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_16_COMPLETE=false
PHASE_17_ALLOWED=false
```

---

# 27. Phase 16 post-merge acceptance observation

本節は、PR #67の手動merge後にGitHub `main`を再観測した現在地である。GitHub Actions
またはworkflowの成否をPhase acceptanceのAuthorityとして使用しない。受入根拠は、SHUKOUの
exact-HEAD merge決定、merge receipt、構造レビューで閉じたfinding、および実装者が返した検証
Evidenceである。

```text
OBSERVED_AT_UTC=2026-09-10T05:53:55Z
CURRENT_PHASE=16_MULTI_MODEL_REPLACEABILITY
GOVERNING_ISSUE=#66
MERGED_PR=#67
ACCEPTED_PR_HEAD=c906f8a4b56c5fec03108873814499e363d68948
PHASE_16_MERGE_SHA=8bc9d0e7a3784b658f8b523361904552f089b3c6
MERGE_PARENT_MAIN=94f067ba6acb4e4459ef3ecd15d6c8c1332e1db7
MERGE_PARENT_DELIVERY=c906f8a4b56c5fec03108873814499e363d68948

PR_67_STATE=MERGED
CURRENT_ROUTE_BLOCKERS=0
STRUCTURAL_FINDINGS_OPEN=0
PHASE_16_COMPLETE=true
ISSUE_66_CLOSE_ALLOWED=true
PHASE_17_ALLOWED=true
PHASE_17_IMPLEMENTATION_ALLOWED=false
NEXT_OWNER=SHUKOU
```

Phase 16は、Phase 12 Temporary Agent Execution Contractを第二契約で置換せずに、provider-neutral
Model Adapter、State/Difference/Authority/Boundaryに拘束されたWork Unit、非権威的なEvidence
candidate、model-swap continuity、Store-only session recovery、およびbounded failureを追加した。
Round 1・2で発見されたEvidence handoffとadapter boundaryのfindingは、accepted head上で閉鎖済みで
ある。

Phase 17は開始可能だが、自動開始ではない。`8bc9d0e7...`を明示baseとするPhase 17専用Issueと
SHUKOUの実装採択が別途必要である。

---

# 26. Phase 16 Structural Review Round 2 bounded addendum (Issue #66, PR #67)

本節は、構造参謀によるStructural Review Round 2と、SHUKOUによるその採択を、独立再観測できた事実のみ記録するbounded addendumである。

```text
ADDENDUM_OBSERVED_AT_UTC=2026-09-10
ADOPTION_ID=ADOPT_P16_R2_CANONICAL_ENVELOPE_AND_PREFLIGHT_DIFFERENCE_HANDOFF
GOVERNING_ISSUE=#66
TARGET_PR=#67
REVIEWED_HEAD=8b5ebcb40bf906c4dbc979e57b791dcd8f6d768e
ADOPTED_FINDINGS=P16-R2-F1,P16-R2-F2
IMPLEMENTATION_TARGET=EXISTING_BRANCH_AND_PR_67_ONLY
NEW_BRANCH=false
NEW_PR=false
```

2件の対応内容：

```text
P16-R2-F1  route_model_execution_to_evidence が Envelope をStore解決する際、
           execution/swap/recovery route が既に使う正準Envelope受理
           （schema検証、宣言identityと再計算identityとStore lookup keyの三者一致、
           semantic fingerprintの再計算一致）を共有するようになった。以前はfingerprint
           のみ検証していたため、宣言された model_execution_envelope_id 自身（自己参照
           フィールドとしてfingerprint計算対象から除外されている）が commit 後に
           差し替えられた記録は、他の全フィールドが本物であれば検出されなかった。
           model_runtime/route.py の新規 resolve_and_verify_committed_envelope が、
           execution/swap/recovery とEvidence handoffの双方から共有される唯一の
           canonical Envelope resolverとなった。

P16-R2-F2  evidence_request 自身の canonical Difference を、既存の Observation/Difference
           owner経由で derive_evidence 呼び出し前に再現し、Store-resolved Envelope の
           difference_ref と比較するようになった（preflight）。Round 1の事後チェック
           （derive_evidence呼び出し後の一致検証）は、defense in depthとしてそのまま
           保持される。evidence/engine.py の新規 derive_request_difference が、
           derive_evidence 自身が内部で行う同一の Observation→Difference 再現を
           一箇所に集約し、Evidence自身とmodel_runtimeの両方から呼ばれる。
```

`07_AGENT_RUNTIME/`・既存canonical owner・既に受理されたPhase 16およびRound 1の境界・既存の
positive model-swap/session-loss proofsは、いずれも変更されていない。

```text
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_16_COMPLETE=false
PHASE_17_ALLOWED=false
```

---

# 27. Phase 17 implementation-delivery bounded addendum (Issue #69)

本節はClaude Codeが記録するbounded addendumであり、構造参謀による審査結果でもSHUKOUによる採択
記録でもない。`MERGE_SOURCE_REFLOW_CONTRACT.md`の要求するsource_document paired updateを、
`src/`配下の新規kernel_surface変更（`src/manosube_agent_civilization/url_boot/`）に対応付ける
ためだけの、最小限の事実記録である。

```text
ADDENDUM_OBSERVED_AT_UTC=2026-09-10
GOVERNING_ISSUE=#69
BASE_SHA=aee9b669f8bf15626fe162f196cf12338a4ff0da
BRANCH=agent/issue-69-phase17-read-only-url-boot
IMPLEMENTATION_TARGET=NEW_BRANCH_AND_NEW_PR
AUTHOR=CLAUDE_CODE
REVIEW_STATE=NOT_YET_STRUCTURALLY_REVIEWED
```

追加されたas-built ownerは `12_URL_BOOT/`（`URL_BOOT_INDEX.md`・`URL_BOOT_CONTRACT.md`）、
`src/manosube_agent_civilization/url_boot/`（`route.py`・`evidence_handoff.py`・`engine.py`・
`identity.py`・`types.py`・`adapter.py`・`network.py`・`errors.py`）、および
`01_SCHEMA/url_boot/url_source_observation_envelope.schema.json` 1件である。既存の
State・Difference・Authority・Change・Evidence・Reflow・Binding・Boot・Model Runtimeの
いずれのownerも置換・変更しない。`network.py`のみが`socket`/`http.client`/`ssl`/`ipaddress`を
importできる唯一のモジュールであり、DNS-rebinding防止のため単一解決・解決先アドレス直接接続を
行う（Runtime自身の`network.py`がI/O-freeである設計からの意図的な乖離であり、`URL_BOOT_CONTRACT.md`
§6.1に開示済み）。

```text
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_17_COMPLETE=false
PHASE_18_ALLOWED=false
```

---

# 28. Phase 17 Structural Review Round 1 bounded addendum (Issue #69, PR #71) -- current-state restatement

本節はClaude Codeが記録するbounded addendumであり、構造参謀による審査結果でもSHUKOUによる採択
記録そのものでもない。セクション27の記録以降、構造参謀によるStructural Review Round 1
（`P17-R1-F1`〜`P17-R1-F6`）とSHUKOUによるその採択（Issue #69コメント
`https://github.com/manosube/manosube-agent-civilization-os/issues/69#issuecomment-5615258933`、
`ADOPTION_ID=ADOPT_P17_R1_ROUTE_OWNED_FETCH_SAFETY_AND_EXACT_BOOT_PROVENANCE`）を独立GitHub API
再観測で確認した上で、この既存PR #71ブランチ上に実装した是正内容を記録する。

このrepositoryの"last-occurrence extraction convention"の要求に従い、本節は以降で
`CURRENT_PHASE`/`CURRENT_PR`/`CURRENT_PHASE_STATE`の**最終的な**再投影となる -- 本節より前の
どの節の同名フィールドよりも新しい現在地として扱われるべきであり、セクション27自身を含め、以前の
記録を置換・撤回するものではない（それぞれ自身の記録時点における事実として保持される）。

```text
ADDENDUM_OBSERVED_AT_UTC=2026-09-10
CURRENT_PHASE=17_READ_ONLY_URL_BOOT_AND_UNTRUSTED_CONTENT_BOUNDARY
CURRENT_PHASE_ISSUE=69
CURRENT_PR=71
CURRENT_PHASE_STATE=STRUCTURAL_REVIEW_ROUND_1_CORRECTIONS_DELIVERED_PR_OPEN
GOVERNING_ISSUE=#69
TARGET_PR=#71
BASE_SHA=aee9b669f8bf15626fe162f196cf12338a4ff0da
BRANCH=agent/issue-69-phase17-read-only-url-boot
REVIEWED_HEAD=82a008aa406d60cc9e9b0027b8e1e1fd4046c12f
ADOPTION_ID=ADOPT_P17_R1_ROUTE_OWNED_FETCH_SAFETY_AND_EXACT_BOOT_PROVENANCE
ADOPTED_FINDINGS=P17-R1-F1,P17-R1-F2,P17-R1-F3,P17-R1-F4,P17-R1-F5,P17-R1-F6
IMPLEMENTATION_TARGET=EXISTING_BRANCH_AND_PR_71_ONLY
NEW_BRANCH=false
NEW_PR=false
AUTHOR=CLAUDE_CODE
REVIEW_STATE=STRUCTURAL_REVIEW_ROUND_1_CORRECTIONS_DELIVERED_AWAITING_ROUND_2
```

6件の是正内容の要約：

```text
P17-R1-F1  失敗/拒否されたfetchは、もはや一切canonical Stateを変更しない。engine.py自身の
           derive_url_source_observation_envelopeが、fetch_outcome != "OBSERVED"での呼び出し
           自体を拒否するようになった。route.pyはOBSERVED以外の10種の結果すべてについて、
           envelope=None・url_source_observation_envelope_id=Noneのephemeralなreceiptのみを
           返し、commit_state_transitionを一切呼ばない。

P17-R1-F2  redirect/content/identityの分類は、もはや置換可能なadapterからの主張を信頼しない。
           UrlSourceAdapter Protocolは単一hopのbounded transport primitive
           （fetch_one_hop、URL_HOP_TRANSPORT_OUTCOMESの6要素のみ報告可能）のみを公開し、
           redirectループ全体・content-type/size/JSON/IDENTITY_MISMATCH判定はすべてroute.py
           自身が、adapterのbounded per-hop factsのみから行う。隠されたscope外の中間hopは
           route自身のnetwork_scope再検証により一度も到達されない。

P17-R1-F3  loopback test allowanceは、もはやcaller供給のBoundaryデータでは設定不可能。
           01_SCHEMA/url_boot/url_source_observation_envelope.schema.jsonのnetwork_scopeから
           permit_loopback_test_hostsフィールド自体を削除した（additionalProperties:false）。
           設定できる唯一の場所はLocalHttpUrlSourceAdapter自身のconstructor引数
           （permit_loopback_test_hosts、defaultはFalse）であり、request-facing callerが
           source_identity/boundaryデータのみで到達できる経路は存在しない。

P17-R1-F4  同一fetch内でのcross-hop DNS解決driftを検出・拒否する。route.py自身が各hopの
           resolved addressを(host, port)ごとに束縛し、同一(host, port)が別のアドレスに
           解決された場合はBOUNDARY_REFUSEDとして拒否する。成功した観測は
           resolution_provenance（このfetchで採用された(host, port, resolved_address)の
           順序付き記録）をEnvelopeに保持する。

P17-R1-F5  成功して委託されたEnvelopeは、正確なProject/Binding/Boot contextを拘束する。
           project_binding_ref（Boot時に検証されたProject Binding参照）と
           boot_state_fingerprint（Boot観測時点のState fingerprint）を新たにEnvelopeへ追加し、
           両方ともENVELOPE_SEMANTIC_FIELDSに含め、identity-sensitiveとした。
           evidence_handoff.pyは既存の三者一致・semantic fingerprint再計算チェックにより、
           これら2フィールドも自動的にtamper検出対象となる。

P17-R1-F6  本節自身が、この是正の対象である。
```

追加でCodex自動レビューにより発見・修正された3件（前回commit `82a008a`で対応済み、PR #71の
review threadで解決記録済み）も含め、修正はPR #71の唯一のブランチ上、新規PR無しで行われた。

既存の`State`・`Difference`・`Authority`・`Change`・`Evidence`・`Reflow`・`Binding`・`Boot`・
`Model Runtime`のいずれのownerも置換・変更しない。schema変更（`network_scope`から
`permit_loopback_test_hosts`削除、`project_binding_ref`/`boot_state_fingerprint`/
`resolution_provenance`追加、`fetch_outcome`を`"OBSERVED"`固定へ縮小）は
`01_SCHEMA/url_boot/url_source_observation_envelope.schema.json` 1件のみで、schema総数は
67のまま変わらない。

```text
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_17_COMPLETE=false
PHASE_18_ALLOWED=false
NEXT_OWNER=STRUCTURAL_ADVISOR
```

# 29. Phase 17 Structural Review Round 2 bounded addendum (Issue #69, PR #71) -- current-state restatement

本節はClaude Codeが記録するbounded addendumであり、構造参謀による審査結果でもSHUKOUによる採択
記録そのものでもない。セクション28の記録以降、構造参謀によるStructural Review Round 2
（Round 1の6件中3件を再オープンした`P17-R2-F1`〜`P17-R2-F3`）とSHUKOUによるその採択（Issue #69
コメント
`https://github.com/manosube/manosube-agent-civilization-os/issues/69#issuecomment-5616043346`、
`ADOPTION_ID=ADOPT_P17_R2_ROUTE_OWNED_NETWORK_ADMISSION_AND_RESOLVABLE_BOOT_CONTEXT`）を独立
GitHub API再観測で確認した上で、この既存PR #71ブランチ上に実装した是正内容を記録する。

このrepositoryの"last-occurrence extraction convention"の要求に従い、本節は以降で
`CURRENT_PHASE`/`CURRENT_PR`/`CURRENT_PHASE_STATE`の**最終的な**再投影となる -- 本節より前の
どの節の同名フィールドよりも新しい現在地として扱われるべきであり、セクション28自身を含め、以前の
記録を置換・撤回するものではない（それぞれ自身の記録時点における事実として保持される）。

```text
ADDENDUM_OBSERVED_AT_UTC=2026-09-10
CURRENT_PHASE=17_READ_ONLY_URL_BOOT_AND_UNTRUSTED_CONTENT_BOUNDARY
CURRENT_PHASE_ISSUE=69
CURRENT_PR=71
CURRENT_PHASE_STATE=STRUCTURAL_REVIEW_ROUND_2_CORRECTIONS_DELIVERED_PR_OPEN
GOVERNING_ISSUE=#69
TARGET_PR=#71
BASE_SHA=aee9b669f8bf15626fe162f196cf12338a4ff0da
BRANCH=agent/issue-69-phase17-read-only-url-boot
REVIEWED_HEAD=fe199718c87da54b6649e12a2f3b439993cf95b9
ADOPTION_ID=ADOPT_P17_R2_ROUTE_OWNED_NETWORK_ADMISSION_AND_RESOLVABLE_BOOT_CONTEXT
ADOPTED_FINDINGS=P17-R2-F1,P17-R2-F2,P17-R2-F3
IMPLEMENTATION_TARGET=EXISTING_BRANCH_AND_PR_71_ONLY
NEW_BRANCH=false
NEW_PR=false
AUTHOR=CLAUDE_CODE
REVIEW_STATE=STRUCTURAL_REVIEW_ROUND_2_CORRECTIONS_DELIVERED_AWAITING_ROUND_3
```

3件の是正内容の要約：

```text
P17-R2-F1  Round 1はredirect/content/identityの分類をrouteへ移したが、adapter自身の単一
           fetch_one_hopは依然としてresolveと安全性分類と接続を1つの不可分な操作の中で行って
           おり、resolveされたアドレス自身の安全性と実際に接続された先はadapter自身の申告の
           ままだった。UrlSourceAdapter Protocolを2つのbounded primitiveへ分割した:
           resolve_hop（DNS_FAILUREまたはRESOLVED+アドレスのみを報告し、何も分類しない）と
           connect_hop（route admittedアドレスへ正確に接続し、CONNECTION_FAILURE/
           TLS_FAILURE/TIMEOUT/RESPONSEのみを報告する）。BOUNDARY_REFUSEDはどちらの
           vocabulary（URL_HOP_RESOLVE_OUTCOMES/URL_HOP_CONNECT_OUTCOMES）にも存在せず、
           route自身がnetwork.require_safe_resolved_addressにより、接続を試みる前に
           resolveされたアドレスを分類する。routeはさらにconnect_hopが報告するresolved_
           addressがroute自身の渡したadmitted_addressと正確に一致することを要求し、
           一致しないadapterをUrlBootAdapterErrorとして拒否する。cross-hop DNS解決drift
           束縛（P17-R1-F4）はresolve段階、接続前へ移動した。

P17-R2-F2  Round 1はpermit_loopback_test_hostsをLocalHttpUrlSourceAdapter自身のconstructor
           引数へ移したが、そのadapterクラス自体がこのpackageの公開surfaceからexportされて
           いるため、公開observe_url_sourceへadapter引数を渡せる呼び出し元は誰でも
           permit_loopback_test_hosts=Trueのまま同じ許容adapterを構築できた -- 単に同じ
           到達可能なswitchを一段階前へ移しただけだった。P17-R2-F1によりaddress安全性分類が
           route側へ完全に移ったため、LocalHttpUrlSourceAdapterはもはやloopback関連の
           constructor引数を一切持たない。loopback判断はroute.py自身の2つの恒久的に束縛
           された分類関数の内側にのみ存在する:
           _require_safe_resolved_address_production（loopback常に拒否、唯一の公開
           observe_url_sourceへ無条件に束縛）と
           _require_safe_resolved_address_permitting_loopback_only（loopbackのみが例外、
           url_boot/__init__.pyから一切exportされない、別名の
           observe_url_source_for_disposable_local_testからのみ到達可能）。どちらの公開
           関数のsignatureにもloopback関連のkeyword/positional引数は一切存在しない --
           どちらの関数がimport・呼び出されるかというcomposition時点の選択のみが結果を
           決める。

P17-R2-F3  Round 1のboot_state_fingerprint（P17-R1-F5）はフィールド自体の改竄検出は
           閉じたが、Evidence handoffがこのprojectの実canonical State履歴から独立して
           そのfingerprintを再導出する手段を持たなかった。さらにfingerprint_project_state
           はsemantic_stateのみをhashし、state_revisionを一切含めないため、URL Boot commit
           のようにsemantic_stateへ一切触れない2つの異なる正当なrevisionが同一の
           boot_state_fingerprintを持ちうることが判明した -- fingerprintだけでは
           revisionを区別できない。Envelopeへboot_state_transition_ref
           （{"kind": "state_transition", "id": ...}、genesis Bootの場合は
           binding/route.py自身のgenesis規約に倣うTX-GENESIS）を新たに追加し、
           evidence_handoff._reresolve_and_verify_boot_contextが既存の三者一致チェック後・
           derive_evidence呼び出し前に、(a) project_binding_refをStore自身の
           resolve_record経由で再解決しbinding.verify_project_binding_identityで検証、
           (b) boot_state_transition_refをStore自身の既存resolve_transaction surface
           経由で解決し、その遷移のafter_stateから再計算したfingerprintがその遷移自身の
           after_fingerprintとEnvelope自身のboot_state_fingerprintの両方に一致することを
           要求する。自己無矛盾だがStore/worldがその主張を裏付けられないEnvelope
           （コピーされたが改竄されていないEnvelope）はここで拒否される。
```

修正はPR #71の唯一のブランチ上、新規PR無しで行われた。既存の`State`・`Difference`・
`Authority`・`Change`・`Evidence`・`Reflow`・`Binding`・`Boot`・`Model Runtime`のいずれの
ownerも置換・変更しない。schema変更（`boot_state_transition_ref`の追加）は
`01_SCHEMA/url_boot/url_source_observation_envelope.schema.json` 1件のみ。

```text
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_17_COMPLETE=false
PHASE_18_ALLOWED=false
NEXT_OWNER=STRUCTURAL_ADVISOR
```

# 30. Phase 17 Structural Review Round 3 bounded addendum (Issue #69, PR #71) -- current-state restatement

本節はClaude Codeが記録するbounded addendumであり、構造参謀による審査結果でもSHUKOUによる採択
記録そのものでもない。セクション29の記録以降、構造参謀によるStructural Review Round 3
（`P17-R3-F1`, `P17-R3-F2`）とSHUKOUによるその採択（Issue #69コメント
`https://github.com/manosube/manosube-agent-civilization-os/issues/69#issuecomment-5616711879`、
`ADOPTION_ID=ADOPT_P17_R3_ROUTE_OWNED_CONNECTION_AND_NON_SUBSTITUTABLE_LOCAL_TEST_COMPOSITION`）を
独立GitHub API再観測で確認した上で、この既存PR #71ブランチ上に実装した是正内容を記録する。

このrepositoryの"last-occurrence extraction convention"の要求に従い、本節は以降で
`CURRENT_PHASE`/`CURRENT_PR`/`CURRENT_PHASE_STATE`の**最終的な**再投影となる -- 本節より前の
どの節の同名フィールドよりも新しい現在地として扱われるべきであり、セクション29自身を含め、以前の
記録を置換・撤回するものではない（それぞれ自身の記録時点における事実として保持される）。

```text
ADDENDUM_OBSERVED_AT_UTC=2026-09-10
CURRENT_PHASE=17_READ_ONLY_URL_BOOT_AND_UNTRUSTED_CONTENT_BOUNDARY
CURRENT_PHASE_ISSUE=69
CURRENT_PR=71
CURRENT_PHASE_STATE=STRUCTURAL_REVIEW_ROUND_3_CORRECTIONS_DELIVERED_PR_OPEN
GOVERNING_ISSUE=#69
TARGET_PR=#71
BASE_SHA=aee9b669f8bf15626fe162f196cf12338a4ff0da
BRANCH=agent/issue-69-phase17-read-only-url-boot
REVIEWED_HEAD=91cf57fa885f899decf78374ed38e441aca5e135
ADOPTION_ID=ADOPT_P17_R3_ROUTE_OWNED_CONNECTION_AND_NON_SUBSTITUTABLE_LOCAL_TEST_COMPOSITION
ADOPTED_FINDINGS=P17-R3-F1,P17-R3-F2
IMPLEMENTATION_TARGET=EXISTING_BRANCH_AND_PR_71_ONLY
NEW_BRANCH=false
NEW_PR=false
AUTHOR=CLAUDE_CODE
REVIEW_STATE=STRUCTURAL_REVIEW_ROUND_3_CORRECTIONS_DELIVERED_AWAITING_ROUND_4
```

2件の是正内容の要約：

```text
P17-R3-F1  Round 2はaddress安全性分類をrouteへ移したが、置換可能なUrlSourceAdapter自身の
           connect_hopが依然として接続そのものを作成し、その結果を自ら報告していた --
           adapterが正直であればroute自身の事後照合（報告されたresolved_addressがroute
           admittedアドレスと一致するか）で捕捉できたが、悪意あるadapterが実際には別の
           アドレスへ接続しながら、admittedアドレスへ到達したと偽って報告し、もっともらしい
           偽のresponseを返すことを妨げる手段が無かった。UrlSourceAdapter Protocolから
           connect_hopメソッドを完全に削除した（resolve_hopのみが残る -- route自身が
           resolve結果を利用する前に独立して安全性分類するため、これ単体では無害）。実際の
           接続はtrusted network layer自身が排他的に作成・制御する:
           network.perform_admitted_connection(source_identity, *, admitted_address,
           boundary)がnetwork.connect_and_request_hopをラップし、typedなURL_HOP_
           CONNECT_OUTCOMES vocabularyへ変換する。route.py内部のperform_connection
           parameter（既存のclassify_resolved_addressパターンと同一のcomposition時点束縛）
           経由で、公開observe_url_sourceは_perform_connection_via_trusted_network
           （adapter引数を完全に無視し、network.perform_admitted_connectionへ直接委譲）
           へ恒久的に束縛される。悪意あるadapterのconnect_hopが尤もらしいRESPONSEを偽装
           するよう仕込まれていても、公開observe_url_sourceから一度も呼び出されないことを
           呼び出し回数ゼロで証明する decisive test を追加した
           （test_production_observe_url_source_never_reaches_any_adapter_connect_method）。
           connect段階の検証失敗は、production側の接続主体がもはや"adapter"ではないため、
           UrlBootAdapterErrorからUrlBootRequirementErrorへ変更した。

P17-R3-F2  Round 2はloopback許容のparameter surfaceを閉じたが、route.observe_url_source_
           for_disposable_local_testという別名の第二公開関数を通じて、この許容そのものは
           依然として到達可能だった -- Pythonのモジュール属性は真にprivateにはできないため、
           route.pyをimportして読める呼び出し元なら誰でも到達できた。この関数をroute.py
           から完全に削除した。_require_safe_resolved_address_permitting_loopback_only
           という名前自体はroute.py内に残るが（Pythonはモジュールレベル名を真に到達不能には
           できないため、これは秘匿ではなく開示された事実である）、route.py自身が定義する
           どの関数もこれを何にも束縛しない。この repository が出荷する package の外側 --
           tests/fixtures/url_boot_local_test_authority.py -- に新設した
           compose_disposable_local_test_observer(store, *, project_id,
           project_binding_id, adapter)が、唯一残る到達経路である。pyproject.tomlの
           [tool.hatch.build.targets.wheel] packagesが
           ["src/manosube_agent_civilization"]のみを列挙していることにより、この
           ファイルが配布wheelから実際に欠落していることを確認済み（sdistの/tests同梱
           にのみ存在）。runtime/bootstrap.py自身が確立したStructural Review Round 5
           （P15-R5-F1）の"closureはclassではない"という idiom と同一の two-step
           factory-and-closure boundary を採用し、返されるclosureのcall signature自体には
           store/project_id/project_binding_id/adapter/classifier/connectorのいずれも
           含まれず、真にrequest-facingなsource_identity/boundary/observed_atのみを持つ。
           これはRuntimeのEd25519基盤production authorityが提供する暗号学的capability
           securityでは**ない**ことを明示的に開示する -- disposable local serverへの
           loopback限定アクセスという限定的blast radiusを踏まえた、意図的で開示された
           比例的判断である。
```

修正はPR #71の唯一のブランチ上、新規PR無しで行われた。既存の`State`・`Difference`・
`Authority`・`Change`・`Evidence`・`Reflow`・`Binding`・`Boot`・`Model Runtime`のいずれの
ownerも置換・変更しない。schema変更は無し（`UrlSourceAdapter` Protocolと`route.py`の関数surface
のみの変更であり、`url_source_observation_envelope.schema.json`は変更していない）。

```text
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_17_COMPLETE=false
PHASE_18_ALLOWED=false
NEXT_OWNER=STRUCTURAL_ADVISOR
```

# 31. Phase 17 Structural Review Round 4 bounded addendum (Issue #69, PR #71) -- current-state restatement

本節はClaude Codeが記録するbounded addendumであり、構造参謀による審査結果でもSHUKOUによる採択
記録そのものでもない。セクション30の記録以降、構造参謀によるStructural Review Round 4
（`P17-R4-F1`, `P17-R4-F2`）とSHUKOUによるその採択（Issue #69コメント
`https://github.com/manosube/manosube-agent-civilization-os/issues/69#issuecomment-5617420900`、
`ADOPTION_ID=ADOPT_P17_R4_NO_AMBIENT_ADAPTER_NETWORK_AND_TRUE_COMPOSITION_BOUNDARY`）を
独立GitHub API再観測で確認した上で、この既存PR #71ブランチ上に実装した是正内容を記録する。

このrepositoryの"last-occurrence extraction convention"の要求に従い、本節は以降で
`CURRENT_PHASE`/`CURRENT_PR`/`CURRENT_PHASE_STATE`の**最終的な**再投影となる -- 本節より前の
どの節の同名フィールドよりも新しい現在地として扱われるべきであり、セクション30自身を含め、以前の
記録を置換・撤回するものではない（それぞれ自身の記録時点における事実として保持される）。

```text
ADDENDUM_OBSERVED_AT_UTC=2026-09-10
CURRENT_PHASE=17_READ_ONLY_URL_BOOT_AND_UNTRUSTED_CONTENT_BOUNDARY
CURRENT_PHASE_ISSUE=69
CURRENT_PR=71
CURRENT_PHASE_STATE=STRUCTURAL_REVIEW_ROUND_4_CORRECTIONS_DELIVERED_PR_OPEN
GOVERNING_ISSUE=#69
TARGET_PR=#71
BASE_SHA=aee9b669f8bf15626fe162f196cf12338a4ff0da
BRANCH=agent/issue-69-phase17-read-only-url-boot
REVIEWED_HEAD=ca7857d674b7bb7be413793a20eb9a91def162d3
ADOPTION_ID=ADOPT_P17_R4_NO_AMBIENT_ADAPTER_NETWORK_AND_TRUE_COMPOSITION_BOUNDARY
ADOPTED_FINDINGS=P17-R4-F1,P17-R4-F2
IMPLEMENTATION_TARGET=EXISTING_BRANCH_AND_PR_71_ONLY
NEW_BRANCH=false
NEW_PR=false
AUTHOR=CLAUDE_CODE
REVIEW_STATE=STRUCTURAL_REVIEW_ROUND_4_CORRECTIONS_DELIVERED_AWAITING_ROUND_5
```

2件の是正内容の要約：

```text
P17-R4-F1  Round 3はconnect_hopをProtocolから削除したが、resolve_hopは残った -- 置換可能な
           adapter自身のDNS解決が、genuineなtrusted pre-commit network path内で依然として
           任意のcaller供給Pythonコードとして実行されており、route自身のaddress安全性分類が
           その結果を見る前に、adapter自身のresolve_hop実装が別アドレスへの独立したI/Oを
           副作用として行い得た -- 何を"報告した"かだけが検査され、実際に何を"した"かは
           検査されなかった。UrlSourceAdapter Protocolはもはや一切の実行可能メソッドを
           宣言しない（adapter_identity属性のみ）。唯一のDNS解決は
           network.perform_resolution が排他的に作成・制御し、route.py自身の
           _perform_resolution_via_trusted_network から直接呼び出される -- Round 3の
           connect段階是正の正確な鏡像。悪意あるadapterのresolve_hopが別アドレスへの
           I/Oを行い、requestされた本物のhostを騙るもっともらしいRESOLVED結果を返すよう
           仕込まれていても、productionのcompose_url_source_observerが返すclosureから
           一度もresolve_hop/connect_hopいずれも呼び出されないことを、両方の呼び出し
           回数ゼロで証明するdecisive testを追加した
           （test_production_compose_url_source_observer_never_invokes_any_adapter_
           resolve_or_connect_method）。resolve段階の検証失敗は、production側の
           解決主体がもはや"adapter"ではないため、UrlBootAdapterErrorから
           UrlBootRequirementErrorへ変更した（Round 3のconnect段階と同一の変更）。

P17-R4-F2  Round 3はdisposable-local-test経路をrequest前に一度だけcomposeされるclosureに
           したが、公開observe_url_source自身は毎回のcall で store/adapter を直接受け取る
           plain関数のままであり、これはproductionこそが"requestより前にcomposeされた
           request-facing closure/capability"要件を満たしていない当のものであった --
           private名をimportする呼び出し元ではなく。公開observe_url_sourceを完全に削除し、
           compose_url_source_observer(store, *, project_id, project_binding_id, adapter)を
           この module の唯一のproduction entry pointとした -- Round 3が
           disposable-local-test経路に既に確立した two-step factory-and-closure 形状を
           production自身へ適用したもの。さらにRound 4は、route.pyが依然として
           _require_safe_resolved_address_permitting_loopback_only の完全な実装を
           出荷しており、route.pyをimportできる呼び出し元なら誰でもこのclassifierを
           route.pyの他のprivate名（_observe_url_source_impl,
           _perform_connection_via_trusted_network,
           _perform_resolution_via_trusted_network）と再結合できることを発見した --
           Structural Review Round 4自身のdelivery-commentがこれら3つのimportable
           symbolを名指しして、この再構成攻撃を明示的に実演した。このclassifierの実装
           全体をshipped moduleから完全に除去し、tests/fixtures/
           url_boot_local_test_authority.py -- 出荷wheelから確認済みで欠落 -- へ移動
           した。route.pyはもはや、いかなる名前のloopback許容classifierコードも一切
           出荷しない。disposable-local-test compositionにはさらに、genuineで外部保持
           のtest-harness authorityを追加した:
           compose_disposable_local_test_observerは必須のtest_harness_authority: bytes
           キーワードを要求するようになり、closureが構築されるより前に
           hmac.compare_digestで検証される -- そのdigestは、shipされるいかなる
           moduleにも存在しない秘密鍵から、非出荷fixture module自身のimport時点で
           一度だけ新たに生成される。欠落・型不一致・偽造されたauthorityは、いかなる
           DNS解決・network接続よりも前に拒否される（UrlBootRequirementError）。これは
           完全な暗号学的capability securityでは**なく**、既にtest-suiteのsourceを
           保持している同一プロセス内の攻撃者からは防御しないことを、そのfixture
           module自身のdocstringで明示的かつ詳細に開示している -- Round 4が実演した
           特定のwheel-only再構成攻撃を閉じるものに過ぎない、という誠実な非請求である。
```

修正はPR #71の唯一のブランチ上、新規PR無しで行われた。既存の`State`・`Difference`・
`Authority`・`Change`・`Evidence`・`Reflow`・`Binding`・`Boot`・`Model Runtime`のいずれの
ownerも置換・変更しない。schema変更は無し（`UrlSourceAdapter` Protocol、`route.py`の関数
surface、および非出荷test fixtureのみの変更であり、`url_source_observation_envelope.schema.json`
は変更していない）。

```text
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_17_COMPLETE=false
PHASE_18_ALLOWED=false
NEXT_OWNER=STRUCTURAL_ADVISOR
```

# 32. Phase 17 Structural Review Round 5 bounded addendum (Issue #69, PR #71) -- current-state restatement

本節はClaude Codeが記録するbounded addendumであり、構造参謀による審査結果でもSHUKOUによる採択
記録そのものでもない。セクション31の記録以降、構造参謀によるStructural Review Round 5
（`P17-R5-F1`, `P17-R5-F2`、PR #71コメント
`https://github.com/manosube/manosube-agent-civilization-os/pull/71#issuecomment-5618489491`）と
SHUKOUによるその採択（Issue #69コメント
`https://github.com/manosube/manosube-agent-civilization-os/issues/69#issuecomment-5618521865`、
`ADOPTION_ID=ADOPT_P17_R5_INERT_ADAPTER_DATA_AND_EXTERNAL_LOCAL_TEST_AUTHORITY`、
誤記訂正コメント
`https://github.com/manosube/manosube-agent-civilization-os/issues/69#issuecomment-5618524457`が
実質的なフィールドを変更していないことも確認済み）を独立GitHub API再観測で確認した上で、この
既存PR #71ブランチ上に実装した是正内容を記録する。

このrepositoryの"last-occurrence extraction convention"の要求に従い、本節は以降で
`CURRENT_PHASE`/`CURRENT_PR`/`CURRENT_PHASE_STATE`の**最終的な**再投影となる -- 本節より前の
どの節の同名フィールドよりも新しい現在地として扱われるべきであり、セクション31自身を含め、以前の
記録を置換・撤回するものではない（それぞれ自身の記録時点における事実として保持される）。

```text
ADDENDUM_OBSERVED_AT_UTC=2026-09-10
CURRENT_PHASE=17_READ_ONLY_URL_BOOT_AND_UNTRUSTED_CONTENT_BOUNDARY
CURRENT_PHASE_ISSUE=69
CURRENT_PR=71
CURRENT_PHASE_STATE=STRUCTURAL_REVIEW_ROUND_5_CORRECTIONS_DELIVERED_PR_OPEN
GOVERNING_ISSUE=#69
TARGET_PR=#71
BASE_SHA=aee9b669f8bf15626fe162f196cf12338a4ff0da
BRANCH=agent/issue-69-phase17-read-only-url-boot
REVIEWED_HEAD=aba7c3e1af83adffa579de08a38829a366e2660a
ADOPTION_ID=ADOPT_P17_R5_INERT_ADAPTER_DATA_AND_EXTERNAL_LOCAL_TEST_AUTHORITY
ADOPTED_FINDINGS=P17-R5-F1,P17-R5-F2
IMPLEMENTATION_TARGET=EXISTING_BRANCH_AND_PR_71_ONLY
NEW_BRANCH=false
NEW_PR=false
AUTHOR=CLAUDE_CODE
REVIEW_STATE=STRUCTURAL_REVIEW_ROUND_5_CORRECTIONS_DELIVERED_AWAITING_ROUND_6
```

2件の是正内容の要約：

```text
P17-R5-F1  Round 4はUrlSourceAdapter Protocolから一切の実行可能メソッドを除去したが、
           productionのcompose_url_source_observerは依然としてadapter"オブジェクト"を
           受け取り、毎回のrequestごとにgetattrでその own adapter_identity属性を読んで
           いた -- 悪意あるcaller供給objectが（読み取り時に例外を投げる、あるいは
           Stateを変異させるproperty、または __iter__/__getitem__/keys を上書きした
           custom Mapping/iterator/dict subclassが）このrouteのtrusted composition
           boundaryへ到達し、Protocolが一切のmethodを宣言していないにもかかわらず、
           request毎に繰り返し実行され得た。compose_url_source_observerは now
           adapter_identity を直接受け取るようになり -- 既にrealizeされたplain data
           として -- composition時点で一度だけ検証・再構築される
           （route._canonicalize_inert_adapter_identity）。この検証器はexact
           type(x) is dict/list等のみを許容し isinstance を一切使わない -- dict/list
           subclassが上書きした __iter__/__getitem__/keys を、それが一度でも実行される
           前に拒否するためである。frozen化された結果はclosure内に一度だけcaptureされ、
           元のcaller供給objectへの参照は一切残らない。敵対的property/descriptor/
           Mapping/iterator/subclassがゼロ実行で拒否されること、closure captureの
           検査により元のobjectへの参照が残らないこと、compositionより後の元object
           変異が後続のrequestに一切反映されないことを証明するdecisive testを追加した。

P17-R5-F2  route.pyは依然として、classify_resolved_address/perform_resolution/
           perform_connectionを通常の関数引数として受け取るgeneric な orchestration
           関数（Round 5以前のObserve_url_source_impl）を出荷していた -- route.pyを
           直接importできるcallerであれば、この関数を genuine な shipped
           trusted-network resolver/connector と、単なる permissive lambda
           （classify_resolved_address として）を組み合わせて呼び出すことで、
           production自身のclassifierだけが閉じているはずのloopback許容pathを、
           shipped codeのみ・isolation破りなし・adapter objectなしで再構築できた。
           shipped packageは今や、classifier/resolver/connectorのいずれも hardcoded
           な直接呼び出しに置き換えた fixed・非parameterize な production pipeline
           （_fetch_with_route_owned_redirects_production,
           _observe_url_source_impl_production）のみを出荷する -- route.py内のいかなる
           関数も、この3つのいずれかの名前のparameterを一切宣言しない（AST-based
           decisive testで証明）。この repository 自身の internal deterministic
           test suiteが真に必要とするgenericなorchestrationは
           tests/fixtures/url_boot_test_engine.py -- 出荷wheelから確認済みで欠落 --
           へ完全に移動した。さらに、disposable-local-test authorityをissuer/verifier
           分離した: url_boot_local_test_authority.pyは now hardcoded な Ed25519
           公開鍵hex literalのみを保持し、binding.signature.verify_ed25519_signature
           （runtime/bootstrap.py自身のtrust-anchorが既に使用しているものと同一）で
           検証する -- 秘密鍵もmint関数も保持せず、genuineな credential を mint
           できる唯一のmodule tests/fixtures/url_boot_local_test_issuer.py を
           importしない（決定的・固定・test専用と開示されたEd25519 keypair、
           Ed25519PrivateKey.generate()ではなく
           hashlib.sha256(<固定文字列>).digest()がseed）。欠落・型不一致・偽造
           （誤ったsignature/algorithm/key_id）credentialがいかなるDNS解決・
           network接続よりも前に拒否されること、偽造authorityがadapter_identityの
           canonicalizationより前に拒否されること（authority検証が先に実行される
           ことの証明）、genuineな外部issuerによるpositive control、verifier自身の
           hardcoded公開鍵literalがissuer自身の秘密鍵の公開半分と genuinely 一致する
           ことを証明するnon-vacuity controlを追加した。
```

修正はPR #71の唯一のブランチ上、新規PR無しで行われた。既存の`State`・`Difference`・
`Authority`・`Change`・`Evidence`・`Reflow`・`Binding`・`Boot`・`Model Runtime`のいずれの
ownerも置換・変更しない。schema変更は無し（`route.py`の関数surface、`UrlSourceAdapter`
Protocol/`adapter.py`のdocstring、および非出荷test fixtureのみの変更であり、
`url_source_observation_envelope.schema.json`は変更していない）。

```text
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_17_COMPLETE=false
PHASE_18_ALLOWED=false
NEXT_OWNER=STRUCTURAL_ADVISOR
```

---

# 33. Phase 17 post-merge acceptance observation

本節は、PR #71のSHUKOU手動merge後にGitHub `main`を再観測した現在地である。GitHub Actions
またはworkflowの成否をPhase acceptanceのAuthorityとして使用しない。受入根拠は、Round 6で
exact delivery HEADに対して記録された構造レビューPASS、SHUKOUの手動merge、merge commitの
両parent、merge後mainの再観測、および同一merged treeに対する独立した限定再検証である。

```text
OBSERVED_AT_UTC=2026-09-10T14:17:21Z
CURRENT_PHASE=17_READ_ONLY_URL_BOOT_AND_UNTRUSTED_CONTENT_BOUNDARY
CURRENT_PHASE_STATE=POST_MERGE_ACCEPTED_AWAITING_ISSUE_CLOSE
CURRENT_PHASE_ISSUE=69
CURRENT_PR=NONE
GOVERNING_ISSUE=#69
MERGED_PR=#71
ACCEPTED_PR_HEAD=727b4649280f74763e88307c20355b3c9626b9a1
PHASE_17_MERGE_SHA=faed2e0fc8caa4977cf831f67d2fe0c6d2976427
MERGE_PARENT_MAIN=aee9b669f8bf15626fe162f196cf12338a4ff0da
MERGE_PARENT_DELIVERY=727b4649280f74763e88307c20355b3c9626b9a1

PR_71_STATE=MERGED
MERGED_EXACT_REVIEWED_HEAD=true
STRUCTURAL_REVIEW_ROUND_6=PASS
STRUCTURAL_FINDINGS_OPEN=0
PHASE_17_COMPLETE=true
ISSUE_69_CLOSE_ALLOWED=true
PHASE_18_ALLOWED=true
PHASE_18_IMPLEMENTATION_ALLOWED=false
NEXT_OWNER=SHUKOU
```

Phase 17は、明示されたURL source identityとclosed read-only Boundaryの下で、redirectごとの
再認可、route-owned DNS/network admission、bounded transport outcome、untrusted-contentの
非権威性、exact Project/Binding/Boot provenance、および既存Evidence ownerへのhandoffを追加した。
既存のState、Observation、Difference、Authority、Change、Evidence、Reflow、Binding、Boot、
Runtime、Model Runtimeのownerは置換されず、URL contentはAuthority、Change、Difference closure、
model/tool executionまたはState mutationを生成できない。

同一merged treeに対する限定再検証では、URL Boot unit/contract/integration suiteが149件PASSし、
schema 67件、State Engine、State Store、Observation contract、Difference contractの各validatorが
PASSした。マージ直後の`Merge source post-merge reflow`と`Source freshness drift detection`は
いずれもGitHub上でfailureだが、両jobはrunner名が空でstep countが0のまま終了しており、workflow
内部の検証処理またはsource writeが実行された証拠はない。この失敗はPhase 17実装の不合格証拠には
使用せず、自動source reflowが成立しなかった観測として保持する。

Phase 18は次のroadmap work unitとして定義可能になったが、自動的な実装Authorityは生じない。
Issue #69のcloseとPhase 18のObjective/Boundary/Authorityを持つ専用IssueおよびSHUKOU採択は、
本source-sync PRの手動mergeとその結果mainの再観測後に分離して行う。

---

# 34. Phase 18 implementation-delivery bounded addendum (Issue #73)

本節はClaude Codeが記録するbounded addendumであり、構造参謀による審査結果でもSHUKOUによる採択
記録そのものでもない。`MERGE_SOURCE_REFLOW_CONTRACT.md`の要求するsource_document paired
updateを、`src/`および`01_SCHEMA/`配下の新規kernel_surface変更
（`src/manosube_agent_civilization/change_executor/`、`01_SCHEMA/change_executor/`）に
対応付けるためだけの、最小限の事実記録である。

Issue #73「Controlled Autonomous Change」のSHUKOU採択（Issue #73コメント
`https://github.com/manosube/manosube-agent-civilization-os/issues/73#issuecomment-5620526355`、
`ADOPTION_ID=ADOPT_P18_CONTROLLED_AUTONOMOUS_CHANGE`、構造参謀API read-back receipt
`https://github.com/manosube/manosube-agent-civilization-os/issues/73#issuecomment-5620533870`）
を独立GitHub API再観測で確認し、`main`の実HEADが採択記録の`AUTHORIZED_TARGET_SHA`と一致する
ことを確認した上で、新規branch上に実装した内容を記録する。

```text
ADDENDUM_OBSERVED_AT_UTC=2026-09-10
GOVERNING_ISSUE=#73
BASE_SHA=120cddbddd12e86cb8a233b90a69fe60a24b42c5
BRANCH=agent/issue-73-phase18-controlled-autonomous-change
IMPLEMENTATION_TARGET=NEW_BRANCH_AND_NEW_PR
ADOPTION_ID=ADOPT_P18_CONTROLLED_AUTONOMOUS_CHANGE
AUTHOR=CLAUDE_CODE
REVIEW_STATE=NOT_YET_STRUCTURALLY_REVIEWED
```

追加されたas-built ownerは `13_CHANGE_EXECUTOR/`（`CHANGE_EXECUTOR_INDEX.md`・
`CHANGE_EXECUTOR_CONTRACT.md`）、`src/manosube_agent_civilization/change_executor/`
（`route.py`・`boundary.py`・`kill_switch.py`・`adapter.py`・`engine.py`・`identity.py`・
`types.py`・`errors.py`・`evidence_handoff.py`・`__init__.py`の10モジュール）、
`01_SCHEMA/change_executor/`（`execution_boundary`・`execution_intent`・`execution_attempt`・
`execution_receipt`・`change_executor_kill_switch`の5schema、schema総数67→72）である。
`scripts/validate_schemas.py`自身のasserted schema countも67から72へ更新した。既存の
State・Difference・Authority・Change・Evidence・Reflow・Binding・Boot・Runtime・Model
Runtime・URL Bootのいずれのownerも置換・変更しない -- `change_executor`は既にAUTHORIZED
状態のcanonical Changeを、closed low-risk Execution Boundary内でのみ実行し、immutableな
`change_execution_receipt`を1件生成した上で停止する adapter layer であり、Authorityを
生成せず、canonical Stateの意味的内容を自身の新規record kind以外変更せず、causalityを
証明せず、十分なEvidenceを確立せず、Differenceをcloseせず、completionを宣言しない --
既存のEvidence/Observation/Reflow ownerへhandoffするのみである。

Human-controlled kill switch（`change_executor_kill_switch`、署名付きmonotonic
ACTIVE/REVOKED chain）は、実行のたびに2回（Boot前と、唯一のadapter呼び出し直前）fresh
resolve・signature再検証される。Production adapterは1つのみ（`ControlledFilesystemAdapter`
-- disposable worktree上のbounded filesystem write/delete）であり、GitHub push/merge、
deployment、認証情報、任意shell/subprocess/networkのいずれも一切実行しない。

targeted test suite（`tests/unit/change_executor/`・`tests/contract/change_executor/`・
`tests/integration/change_executor/`、9 test files + 2 fixture modules）は161件PASS、0
skip、0 failで独立に検証済み。実装過程でtest suite自身が発見した1件の genuine defect
（idempotency-slot resolutionがstalenessチェックより後に実行されていたため、最初の成功
実行以降、同一claim_tokenでの通常replayがstaleとして誤って拒否されていた）は、
`route.py`自身のdocstring disclosed judgment call 5として開示の上、この同一commit内で
修正済みである。

```text
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_18_COMPLETE=false
PHASE_19_ALLOWED=false
```

# 35. Phase 18 Structural Review Round 1 bounded addendum (Issue #73, PR #74) -- current-state restatement

本節はClaude Codeが記録するbounded addendumであり、構造参謀による審査結果でもSHUKOUによる採択
記録そのものでもない。セクション34の記録以降、この同一PR #74ブランチ上でGitHub Codex自動
レビューにより発見された3件の追加是正（`worktree_root`のcomposition-time bindingの欠如、
`execution_intent`/`execution_attempt`commit間のcrash recovery gap、2並行callerによる
`adapter.execute`二重呼び出しrace）が実装され、targeted test suiteが161件から167件へ拡張された
（commit `2010f05`）。この167-test状態自体はセクション34の記録時点では未記録のまま今日に至って
いたため、本節は先にその事実を記録した上で、続けて構造参謀によるStructural Review Round 1
（`P18-R1-F1`〜`P18-R1-F6`）とSHUKOUによるその採択（PR #74コメント
`https://github.com/manosube/manosube-agent-civilization-os/pull/74#issuecomment-5626622213`、
`ADOPTION_ID=ADOPT_P18_R1_STRUCTURAL_CORRECTIONS`）を独立GitHub API再観測で確認した上で、この
既存PR #74ブランチ上に実装した是正内容を記録する。

このrepositoryの"last-occurrence extraction convention"の要求に従い、本節は以降で
`CURRENT_PHASE`/`CURRENT_PR`/`CURRENT_PHASE_STATE`の**最終的な**再投影となる -- 本節より前の
どの節の同名フィールドよりも新しい現在地として扱われるべきであり、セクション34自身を含め、以前の
記録を置換・撤回するものではない（それぞれ自身の記録時点における事実として保持される）。

```text
ADDENDUM_OBSERVED_AT_UTC=2026-09-10
CURRENT_PHASE=18_CONTROLLED_AUTONOMOUS_CHANGE
CURRENT_PHASE_ISSUE=73
CURRENT_PR=74
CURRENT_PHASE_STATE=STRUCTURAL_REVIEW_ROUND_1_CORRECTIONS_DELIVERED_PR_OPEN
GOVERNING_ISSUE=#73
TARGET_PR=#74
BASE_SHA=2010f05
BRANCH=agent/issue-73-phase18-controlled-autonomous-change
REVIEWED_HEAD=2010f05
ADOPTION_ID=ADOPT_P18_R1_STRUCTURAL_CORRECTIONS
ADOPTED_FINDINGS=P18-R1-F1,P18-R1-F2,P18-R1-F3,P18-R1-F4,P18-R1-F5,P18-R1-F6
IMPLEMENTATION_TARGET=EXISTING_BRANCH_AND_PR_74_ONLY
NEW_BRANCH=false
NEW_PR=false
FINAL_HEAD_SHA=4b47eb50a9869e6ca4ea9751295a61ab2a030e31
AUTHOR=CLAUDE_CODE
REVIEW_STATE=STRUCTURAL_REVIEW_ROUND_1_CORRECTIONS_DELIVERED_AWAITING_ROUND_2
```

6件の是正内容の要約：

```text
P18-R1-F1  独立after-state再観測がVERIFIEDを条件付ける。evidence_handoff.pyは、これまで
           receipt自身の自己申告outcome=="SUCCEEDED"を直接VERIFIEDへ写像していた -- adapter
           自身の自己申告事実を独立に再確認することなく、executorが自身の成功報告をEvidenceへ
           自己格上げしていた。新規reobservation.pyが、書き込まれたファイルの実際のon-disk内容
           を、要求されたcontent_utf8のSHA-256digestと独立に比較する（adapter自身の報告する
           bytes_written/files_writtenは一切信用しない）。この結果はreceipt自身に
           independent_after_state_observationとして埋め込まれ（schema必須、semantic
           fingerprint対象）、evidence_handoff.pyはreceipt自身のoutcome=="SUCCEEDED"に加えて
           この観測結果自身のoutcome=="MATCHED"を要求した上でなければVERIFIEDを導出しない。
           一致しないSUCCEEDED主張は新規closed outcome member REOBSERVATION_MISMATCHへ
           再分類される。

P18-R1-F2  staleness checkの「blanket resuming skip」を、正確なpost-intent-successor checkへ
           置き換えた。crash-interrupted intentをresumeする呼び出しは、もはや無条件にstaleness
           checkを skipしない -- state_revisionが厳密にexpected_state_revision + 1であること、
           かつchain-link fingerprint（previous_state_fingerprint）がbefore_state_fingerprint
           と厳密に一致することを要求する。さらに、唯一のadapter呼び出しの直前に、
           final pre-effect State barrierを新設した -- 現在のStateを再取得し、この呼び出し
           自身のintent+attempt commitが実際に生成したrevisionと厳密に一致することを要求する。
           不一致は adapter呼び出しゼロのままStaleExecutionInputErrorとして拒否する。

P18-R1-F3  worktree_rootを、closed Execution Boundary自身の内部にある必須schema-validated
           fieldへ移動した（前round独自のcomposition-time parameterから）。
           execution_boundary_fingerprintは既にcanonical boundary dict全体をhashするため、
           worktree_rootは自動的にBoundary fingerprint -- ひいてはmapping-slot key -- に
           参加するようになった。異なるworktree_rootへbindされた2つのcomposed executorは、
           構造的に異なるBoundary fingerprint/mapping slotを持つことになり、cross-root/
           cross-worktreeのslotまたはreceipt substitutionはこのpackage自身のidentity scheme
           内で構造的に不可能となった。

P18-R1-F4  execution_attemptが既にcommit済みとなった後に到達する、あらゆるpathが、正確に1件の
           terminal receiptをcommitするようになった -- adapter自身のraiseと、structurally
           invalidなadapter reportという、これまでこのpatternに従っていなかった2つのpathを
           含む。両者とも、outcome="UNKNOWN"のterminal receiptをcommitするようになった
           （bare exceptionではなく）-- これは既存のEXECUTION_OUTCOMES memberであり、"we do
           not know what happened"という安全で正直なdefaultである。

P18-R1-F5  idempotency-slot resolutionが、time-window/kill-switch checkpoint #1のより前にも
           実行されるようになった（前roundでは、Boot/stalenessのより前にのみ実行されていた）。
           3つのslot-resolution outcome（terminal replay、semantic reuse、terminal-claim-
           mismatch、reconciliation-required）のいずれも、Boot・commit・adapter呼び出しへは
           一切進まないため、これらは admission checkを一切必要としない -- 新しい副作用を
           authorizeするためだけに存在するcheckの後ろにread-onlyのreturnをgateすることこそが
           欠陥そのものであった。

P18-R1-F6  本節自身が、この是正の対象である。
```

修正はPR #74の唯一のブランチ上、新規PR無しで行われた。既存の`State`・`Difference`・
`Authority`・`Change`・`Evidence`・`Reflow`・`Binding`・`Boot`・`Runtime`・`Model Runtime`・
`URL Boot`のいずれのownerも置換・変更しない。schema変更は`01_SCHEMA/change_executor/
execution_boundary.schema.json`（`worktree_root`をrequiredへ追加）と`01_SCHEMA/change_executor/
execution_receipt.schema.json`（`independent_after_state_observation`をrequiredへ追加、
`outcome` enumへ`REOBSERVATION_MISMATCH`を追加）の2件のみで、schema総数は72のまま変わらない
（新規schema fileの追加ではなく、既存2 schemaへのfield追加のため）。新規moduleとして
`src/manosube_agent_civilization/change_executor/reobservation.py`が1件追加された。

targeted test suite（`tests/unit/change_executor/`・`tests/contract/change_executor/`・
`tests/integration/change_executor/`、10 test files + 2 fixture modules -- 新規file
`test_change_executor_independent_reobservation.py`を1件追加）は182件PASS、0 skip、0 failで
独立に検証済み（167件から+15件）。full repository test suiteも独立に再実行し、既知の
pre-existing failure（`tests/contract/governance/test_source_freshness_drift_detection.py`
配下の7件、`origin/main`の clean baseline上で既に確認済みのもの）を除き、全件PASSで検証済み
（正確な最終件数は本節自身の記録時点で得られた実測値を用いる -- 検証セッション自身のログを参照）。

```text
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_18_COMPLETE=false
PHASE_19_ALLOWED=false
NEXT_OWNER=STRUCTURAL_ADVISOR
```

# 36. Phase 18 Structural Review Round 2 bounded addendum (Issue #73, PR #74) -- current-state restatement

本節はClaude Codeが記録するbounded addendumであり、構造参謀による審査結果でもSHUKOUによる採択
記録そのものでもない。セクション35の記録以降、構造参謀によるStructural Review Round 2
（`P18-R2-F1`〜`P18-R2-F4`）とSHUKOUによるその採択（PR #74コメント
`https://github.com/manosube/manosube-agent-civilization-os/pull/74#issuecomment-5628140572`、
`ADOPTION_ID=ADOPT_P18_R2_STRUCTURAL_CORRECTIONS`）をGitHub API + `git rev-parse`による独立
再観測で確認した上で、この既存PR #74ブランチ（新規branch・新規PR無し）上に実装した是正内容を
記録する。Round 1の既存2件のclosed finding（P18-R1-F2の post-intent-successor check、および
idempotency-slot resolutionのordering）は、本round自身のいずれの変更によっても退行していない
-- それぞれの既存testは無変更のまま引き続きPASSしている。

このrepositoryの"last-occurrence extraction convention"の要求に従い、本節は以降で
`CURRENT_PHASE`/`CURRENT_PR`/`CURRENT_PHASE_STATE`の**最終的な**再投影となる -- 本節より前の
どの節の同名フィールドよりも新しい現在地として扱われるべきであり、セクション35自身を含め、以前の
記録を置換・撤回するものではない（それぞれ自身の記録時点における事実として保持される）。

```text
ADDENDUM_OBSERVED_AT_UTC=2026-09-11
CURRENT_PHASE=18_CONTROLLED_AUTONOMOUS_CHANGE
CURRENT_PHASE_ISSUE=73
CURRENT_PR=74
CURRENT_PHASE_STATE=STRUCTURAL_REVIEW_ROUND_2_CORRECTIONS_DELIVERED_PR_OPEN
GOVERNING_ISSUE=#73
TARGET_PR=#74
BASE_SHA=85bd43fbf4619d6ae9f765c76441dd5ea94bbdff
BRANCH=agent/issue-73-phase18-controlled-autonomous-change
REVIEWED_HEAD=85bd43fbf4619d6ae9f765c76441dd5ea94bbdff
ADOPTION_ID=ADOPT_P18_R2_STRUCTURAL_CORRECTIONS
ADOPTED_FINDINGS=P18-R2-F1,P18-R2-F2,P18-R2-F3,P18-R2-F4
IMPLEMENTATION_TARGET=EXISTING_BRANCH_AND_PR_74_ONLY
NEW_BRANCH=false
NEW_PR=false
AUTHOR=CLAUDE_CODE
REVIEW_STATE=STRUCTURAL_REVIEW_ROUND_2_CORRECTIONS_DELIVERED_AWAITING_FURTHER_REVIEW
```

**この節自身の governance-fields は、セクション35自身の `FINAL_HEAD_SHA` が抱えていた欠陥を、
遡ってセクション35自身を書き換えることなく、修正する。** あるコミットは、原理的に、自分自身の
SHAを自分自身の内容の中に事前に記録することができない -- セクション35の `FINAL_HEAD_SHA=
4b47eb50a9869e6ca4ea9751295a61ab2a030e31` は、実際には、その直後にpushされた真に最終的な
delivery head（`85bd43fbf4619d6ae9f765c76441dd5ea94bbdff`、独立GitHub API検証で確認済み、
PR #74コメント `https://github.com/manosube/manosube-agent-civilization-os/pull/74#issuecomment-5628140572`
参照）ではなく、その直前の親コミット（自分自身の実装コミット）を記録していた -- これは
`P18-R2-F4`自身が名指しした、まさにこの欠陥の実例である。本節はこの同じ構造的欠陥を繰り返さない
ために、単一の`FINAL_HEAD_SHA`フィールドを、意図的に区別された2つのフィールドへ置き換える：

```text
IMPLEMENTATION_COMMIT_SHA=5ac16e569a5b2ece45dd23536ad8952d81d3c1fa
DELIVERY_HEAD_OBSERVABLE_VIA=EXTERNAL_RETURN_EVIDENCE_COMMENT_ON_PR_74
```

`IMPLEMENTATION_COMMIT_SHA`は、この本節自身のRound 2是正（コード変更 + このdocument自身の
変更）を実際にlandするコミット自身のSHAであり、そのコミットが実在するようになった時点で初めて
判明する値である -- 本節は当初、意図的にplaceholderトークン`<IMPLEMENTATION_COMMIT_SHA>`のまま
記録された。その後、この値は、実コミットが存在するようになった時点で、小さな genuine な
separate follow-up commit `7c0457e`によって埋められた（直前roundの`85bd43f`自身のfollow-up
commitがセクション35のplaceholderを埋めたのと正確に同じ手続き）-- 上記の
`IMPLEMENTATION_COMMIT_SHA=5ac16e569a5b2ece45dd23536ad8952d81d3c1fa`は、その埋められた後の
実値そのものである。`DELIVERY_HEAD_OBSERVABLE_VIA`は、
「あるコミットは自分自身のSHAを自分自身の中に記録できない」という単純な事実を明示的に記録する
フィールドである -- 真に外部から観測可能な最終delivery headは、この document自身の内部にでは
なく、push後にPR #74自身へ投稿されるreturn-evidence commentの中に記録される。この2フィールド
モデルは、セクション35自身の`FINAL_HEAD_SHA`が示した欠陥を、遡及的にセクション35自身を書き換え
ることなく、今後のroundに向けて修正するものである。

4件の是正内容の要約：

```text
P18-R2-F1  executor-local filesystem re-readがreceipt自身に埋め込まれているだけでは、
           Round 1で採択された独立の after-state Observation/Independent Verification結果には
           ならない -- executorが自身のreceiptを自ら格上げする事実を製造してはならない。
           evidence_handoff.route_change_execution_to_evidenceが自ら、SECONDの、genuinely
           independentな、handoff-time限定の再読み取りを実行し（route.py自身の execution-time
           reobservationとは完全に別物、別時点）、既存のObservation owner（observation.
           engine.observe()、evidence.derive_evidenceの内部呼び出し経由 -- caller供給の
           Observation recordを一切信用しない）を通じて実体のあるObservationを生成する。
           receipt自身のoutcome=="SUCCEEDED"かつこのSECOND re-readが不一致の場合はVERIFIEDを
           拒否する。receipt自身のindependent_after_state_observationへの防御的チェックは
           残すが、それはVERIFIEDをgateしなくなった。

P18-R2-F2  worktree_rootがBoundary fingerprint/mapping slotへ参加することは必要条件だが十分
           条件ではない -- 実際にbindされたworktreeが、Boundary自身が認可したrepository・
           branch/worktree identityであることを検証しない限り、compositionはfail closed
           しなければならない。boundary.validate_execution_boundaryが、純粋なlocal `.git`
           metadataファイル読み取りのみで（subprocess・network呼び出し無し）、
           worktree_root自身の実際のgit checkout identity（HEADのbranch、origin remoteの
           repository slug）を、Boundary自身が宣言するrepository/branchと厳密一致するよう
           要求する。detached HEADはbranch identityを証明できないためfail closedする。

P18-R2-F3  execution_attemptが durableになった瞬間から、durable record chainは既に、typed
           re-observation obligationと non-success/UNKNOWN unresolved stateを保持していな
           ければならない。execution_attempt自身が、commit時点でreobservation_requestを
           durably embedするようになった（新規schema-required field、semantic fingerprint
           対象）。さらに、この exact caller（同一claim_token）が自身のorphaned attempt
           （attempt commit済み、receipt未だ無し）をresumeする場合、これまでの perpetual
           ExecutionReconciliationRequiredErrorではなく、その埋め込み済みreobservation_
           requestから直接、grounded terminal UNKNOWN receiptへ解決するようになった --
           adapter呼び出しゼロ（adapterは既に実行済みかもしれず、再呼び出しはreal duplicate
           mutationのriskを負う）。異なるclaim_tokenに対する既存の
           ExecutionReconciliationRequiredErrorは無変更のまま残る。

P18-R2-F4  canonical current-state fieldは、事実として自己参照的であってはならない。親/
           correction commitを、最終的にdeliverされたheadとしてlabelしてはならない。本節
           自身がこの原則を、セクション35自身の`FINAL_HEAD_SHA`の欠陥を修正する形で実践する
           （このaddendum自身のIMPLEMENTATION_COMMIT_SHA/DELIVERY_HEAD_OBSERVABLE_VIA、上記
           参照）。
```

修正はPR #74の唯一の既存ブランチ上、新規branch・新規PR無しで行われた。既存の`State`・
`Difference`・`Authority`・`Change`・`Evidence`・`Reflow`・`Binding`・`Boot`・`Runtime`・
`Model Runtime`・`URL Boot`のいずれのownerも置換・変更しない。schema変更は
`01_SCHEMA/change_executor/execution_attempt.schema.json`（`reobservation_request`を
requiredへ追加）の1件のみで、schema総数は72のまま変わらない（新規schema fileの追加ではなく、
既存schemaへのfield追加のため）。新規moduleの追加は無し -- 既存module
（`route.py`・`boundary.py`・`evidence_handoff.py`・`engine.py`・`identity.py`）自身への
是正のみである。

targeted test suite（`tests/unit/change_executor/`・`tests/contract/change_executor/`・
`tests/integration/change_executor/`、11 test files + 2 fixture modules -- 新規file
`test_change_executor_worktree_git_identity.py`を1件追加）は197件PASS、0 skip、0 failで
独立に検証済み（182件から+15件）。full repository test suiteも独立に再実行し、既知の
pre-existing failure（`tests/contract/governance/test_source_freshness_drift_detection.py`
配下の7件、この作業開始以前から`origin/main`上で既に確認済みのもの、本packageとは無関係）を
除き、全件PASSで検証済み（正確な最終件数は本節自身の記録時点で得られた実測値を用いる --
検証セッション自身のログを参照）。

```text
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
PHASE_18_COMPLETE=false
PHASE_19_ALLOWED=false
NEXT_OWNER=STRUCTURAL_ADVISOR
```
