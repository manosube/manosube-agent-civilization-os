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
| This correction round's own commits | branch `agent/issue-64-phase15-runtime-adapter` 上、reviewed HEAD `1e1fc98d` の直上に積まれた新規commitのみ。history rewrite（amend / rebase / force-push）は行っていない。新規branchも新規PRも作成していない。 |

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
