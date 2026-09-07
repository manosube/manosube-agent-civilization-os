# MANOSUBE Agent Civilization OS

## Historical Source Register

```text
DOC_TYPE=HISTORICAL_SOURCE_REGISTER
DOCUMENT_ID=HISTORICAL-SOURCE-REGISTER-0001
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
STATUS=CANONICAL_HISTORICAL_SOURCE_REGISTER
SOURCE_AUTHORITY_CLASS=HUMAN_GOVERNED_PROVENANCE_REGISTER
HUMAN_AUTHORITY=SHUKOU
TARGET_REPOSITORY=manosube/manosube-agent-civilization-os
REGISTERED_HISTORICAL_SOURCE_COUNT=4
HISTORICAL_LINEAGE_GROUP_COUNT=3
CANONICAL_AUTHORITY_GRANTED_BY_THIS_REGISTER=false
CURRENT_PHASE_AUTHORITY_GRANTED_BY_THIS_REGISTER=false
```

---

# 0. Purpose

本書は、MANOSUBE Agent Civilization OSの再構築以前に使われていた設計資料、ロードマップ、構造定義および開発契約を、削除せず、現在Authorityから分離して保存する唯一の履歴台帳である。

本書の目的は次である。

```text
preserve origin and design lineage
identify which source was superseded
state why its present authority ended
identify its canonical successor
preserve reusable concepts without restoring old authority
prevent formatted copies from becoming parallel truth
```

本書は、旧資料を「誤り」として廃棄するためのものではない。旧資料が果たした役割を保存しながら、現在の判断に使う正準ownerを一意にするためのものである。

```text
HISTORICAL
≠ FALSE

SUPERSEDED
≠ DELETED

REUSABLE_CONCEPT
≠ CURRENT_AUTHORITY

PROVENANCE
≠ PERMISSION
```

---

# 1. Canonical boundary

現在の情報源は次の一組だけである。

```text
00_SOURCE_AUTHORITY_INDEX.md
01_PROJECT_CONSTITUTION.md
02_CANONICAL_ROADMAP.md
03_CURRENT_DEVELOPMENT_STATE.md
04_REPOSITORY_ARCHITECTURE.md
05_PHASE_ACCEPTANCE_LEDGER.md
06_DEFERRED_DIFFERENCES.md
07_DEVELOPMENT_GOVERNANCE.md
99_HISTORICAL_SOURCE_REGISTER.md
```

本書に登録された旧資料は、このcurrent source setと並列のAuthorityを持たない。

```text
HISTORICAL_SOURCE_CANONICAL_AUTHORITY=false
HISTORICAL_SOURCE_CURRENT_PHASE_AUTHORITY=false
HISTORICAL_SOURCE_IMPLEMENTATION_AUTHORITY=false
HISTORICAL_SOURCE_MERGE_AUTHORITY=false
PARALLEL_INFORMATION_AUTHORITY=0
```

現在の意味、Phase、repository状態、architecture、acceptance、deferred workまたはdevelopment governanceを判断するときは、`00_SOURCE_AUTHORITY_INDEX.md`から読み始めなければならない。

---

# 2. Historical-source classes

| Class | Meaning | Present use |
|---|---|---|
| `SUPERSEDED_DESIGN_SOURCE` | 後継の正準文書へ責務が移管された設計資料 | 起源、設計理由、概念候補の確認 |
| `SUPERSEDED_ROADMAP_SOURCE` | 現在の0–22 Roadmap以前のversion-based工程 | 工程進化と旧期待の確認 |
| `SUPERSEDED_GOVERNANCE_SOURCE` | 現在の情報源分離以前の複合開発契約 | 役割・workflowの由来確認 |
| `FORMAT_DERIVATIVE` | 他資料を形式変換した同系統copy | 表現差・転記履歴の確認のみ |
| `ARCHIVED_OBSERVATION` | 過去時点のGitHubまたはruntime観測 | 当時の事実確認のみ |
| `REJECTED_PROPOSAL` | Human Authorityが明示的に不採択とした案 | 再発防止と判断理由の確認 |

`FORMAT_DERIVATIVE`は独立した意味ownerとして数えない。内容差が見つかっても、新しい方または読みやすい方を自動採用してはならない。

---

# 3. Registration contract

各履歴資料は最低限、次を持つ。

```text
HISTORICAL_SOURCE_ID
TITLE
ORIGINAL_FILENAME
SOURCE_CLASS
STATUS
CONTENT_SHA256
SIZE_BYTES
LINE_COUNT
LINEAGE_GROUP
ORIGINAL_PURPOSE
SUPERSEDED_REASON
SUPERSEDED_BY
CANONICAL_AUTHORITY
CURRENT_PHASE_AUTHORITY
FUTURE_REUSE
PROHIBITED_USE
```

利用可能なら次も記録する。

```text
ORIGINAL_DATE
ORIGINAL_VERSION
ORIGINAL_URI_OR_FILE_ID
RELATED_GITHUB_ARTIFACTS
FORMAT_PARENT
HUMAN_DISPOSITION
```

hashは登録時に受領したfile bytesの同一性を示す。hash一致は意味の正しさ、現在性またはAuthorityを証明しない。

---

# 4. Master register

| ID | Historical source | Class | Lineage | Superseded by | Present authority |
|---|---|---|---|---|---:|
| `HS-0001` | `MANOSUBE_AGENT_CIVILIZATION_OS_DIRECTORY_CONSTITUTION.md` | `SUPERSEDED_DESIGN_SOURCE` | `DIR-CONSTITUTION-V0.1` | `01`, `02`, `04` | None |
| `HS-0002` | `完成ロードマップ.txt` | `SUPERSEDED_ROADMAP_SOURCE` | `VERSION-ROADMAP-PRE-0-22` | `02`, `06` | None |
| `HS-0003` | `Canonical-Directory-Constitution-v0.1.txt` | `FORMAT_DERIVATIVE` | `DIR-CONSTITUTION-V0.1` | `HS-0001`, then `01`, `02`, `04` | None |
| `HS-0004` | `#-MANOSUBE-Agent-Civilization-OS(2).txt` | `SUPERSEDED_GOVERNANCE_SOURCE` | `COMPOSITE-DEVELOPMENT-CONSTITUTION` | `00`, `02`, `03`, `05`, `06`, `07` | None |

表中の`01`等は、current source setの同番号文書を意味する。

---

# 5. HS-0001 — Canonical Directory Constitution v0.1

```text
HISTORICAL_SOURCE_ID=HS-0001
TITLE=MANOSUBE Agent Civilization OS — Canonical Directory Constitution v0.1
ORIGINAL_FILENAME=MANOSUBE_AGENT_CIVILIZATION_OS_DIRECTORY_CONSTITUTION.md
SOURCE_CLASS=SUPERSEDED_DESIGN_SOURCE
STATUS=SUPERSEDED_HISTORICAL_SOURCE
CONTENT_SHA256=ec1539fa7bc215324f546e9cbc4b2d6986796442baea6338a01c0e0fd1ce4c20
SIZE_BYTES=23087
LINE_COUNT=831
LINEAGE_GROUP=DIR-CONSTITUTION-V0.1
ORIGINAL_VERSION=v0.1
CANONICAL_AUTHORITY=false
CURRENT_PHASE_AUTHORITY=false
IMPLEMENTATION_AUTHORITY=false
```

## 5.1 Original purpose

この資料は、Repositoryを次の三世界に分離し、Kernelの因果順序、完全版target tree、Canonical State Backend、dependency direction、ID/reference規則、v0.1 acceptanceおよびadapter追加順序を一つの設計資料として定義した。

```text
KERNEL SOURCE WORLD
CANONICAL STATE WORLD
ADAPTER WORLD
```

また、中心cycleを次として保持した。

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

## 5.2 Superseded reason

この資料は設計起源として重要だが、次の異なるfact typeを一つの文書で所有していた。

```text
project constitution
roadmap and build order
as-built and target architecture
v0.1 acceptance expectation
future adapter sequence
```

実装がPhase 12以降へ進んだ後、一つの資料だけでは、固定原則、現在実在する構造、将来targetおよびPhase履歴を安全に分離できなくなった。そのため責務をcurrent source setへ分割した。

## 5.3 Canonical successors

| Historical responsibility | Current owner |
|---|---|
| Parent OS、Kernel、不変条件 | `01_PROJECT_CONSTITUTION.md` |
| 0–22 Phase順序とGate | `02_CANONICAL_ROADMAP.md` |
| as-built / target repository構造 | `04_REPOSITORY_ARCHITECTURE.md` |
| accepted Phase evidence | `05_PHASE_ACCEPTANCE_LEDGER.md` |
| remaining work | `06_DEFERRED_DIFFERENCES.md` |

## 5.4 Future reuse

再利用可能なのは次である。

```text
three-world separation rationale
Kernel causal directory ordering
dependency-direction rationale
ID and Reference design history
original target-tree intent
adapter replaceability rationale
```

再利用する場合は、current source ownerとlive repositoryを照合し、新しいDifferenceまたはproposalとして扱う。

## 5.5 Prohibited use

```text
MAY_NOT_OVERRIDE_CURRENT_ARCHITECTURE=true
MAY_NOT_DECLARE_MISSING_TARGET_DIRECTORY_A_DEFECT_BY_ITSELF=true
MAY_NOT_RENUMBER_PHASES=true
MAY_NOT_REOPEN_V0_1_OR_COMPLETED_PHASES=true
MAY_NOT_AUTHORIZE_FUTURE_ADAPTER_IMPLEMENTATION=true
```

---

# 6. HS-0002 — v0.2以降 完成ロードマップ確定版

```text
HISTORICAL_SOURCE_ID=HS-0002
TITLE=MANOSUBE Agent Civilization OS — v0.2以降 完成ロードマップ確定版
ORIGINAL_FILENAME=完成ロードマップ.txt
SOURCE_CLASS=SUPERSEDED_ROADMAP_SOURCE
STATUS=SUPERSEDED_HISTORICAL_SOURCE
CONTENT_SHA256=06b2036c2de30607254fe87f8cf413ebc23c2977303ce76385cacd33c9731515
SIZE_BYTES=15861
LINE_COUNT=975
LINEAGE_GROUP=VERSION-ROADMAP-PRE-0-22
CANONICAL_AUTHORITY=false
CURRENT_PHASE_AUTHORITY=false
IMPLEMENTATION_AUTHORITY=false
```

## 6.1 Original purpose

この資料は、v0.1からv1.0までをversion milestoneとして配列した初期完成工程である。

```text
v0.1 Canonical Kernel
v0.2 Local Operation
v0.3 GitHub Projection
v0.4 Runtime Observation
v0.5 Temporary Agent Runtime
v0.6 Independent Verification
v0.7 Multi-Model Replaceability
v0.8 Bounded Autonomous Change
v0.9 Dynamic Multi-Agent
v1.0 Objective Continuity
```

各versionで一つのStructural Differenceを閉じ、自然経路を証明してから次へ進むというvertical progressionの前身を保存している。

## 6.2 Superseded reason

実際の開発では、version単位より細かな0–22 Phase sequenceがHuman Decisionとして固定された。また、Binding、Boot、CLI、URL Read-only、Long-running ProofおよびComparative Benchmark等を独立Phaseとして扱う必要が生じた。

旧version名と現在Phase番号の一対一対応を推論すると、Phase 12 lifecycleとdeferred execution contractのような実際の受入境界を破壊するため、旧ロードマップはcurrent schedule authorityを失った。

## 6.3 Canonical successors

```text
PHASE_ORDER_OWNER=02_CANONICAL_ROADMAP.md
CURRENT_PHASE_OWNER=03_CURRENT_DEVELOPMENT_STATE.md
PHASE_ACCEPTANCE_OWNER=05_PHASE_ACCEPTANCE_LEDGER.md
UNFINISHED_EXPECTATION_OWNER=06_DEFERRED_DIFFERENCES.md
```

## 6.4 Future reuse

```text
version-release naming history
original difference-per-release reasoning
natural-route acceptance concepts
early adapter sequencing rationale
original Temporary Agent execution expectation
original Independent Verification expectation
```

特に、旧v0.5に含まれたAgent execution expectationは、現在のPhase 12を再オープンする根拠ではない。必要な残存義務は`DD-0001 TEMPORARY_AGENT_EXECUTION_CONTRACT`として`06_DEFERRED_DIFFERENCES.md`が所有する。

## 6.5 Prohibited use

```text
MAY_NOT_REPLACE_PHASE_0_TO_22=true
MAY_NOT_MAP_VERSION_TO_PHASE_COMPLETION_BY_INFERENCE=true
MAY_NOT_DECLARE_PHASE_12_INCOMPLETE=true
MAY_NOT_START_A_FUTURE_PHASE=true
MAY_NOT_ACT_AS_RELEASE_AUTHORITY=true
```

---

# 7. HS-0003 — Canonical Directory Constitution v0.1 plain-text derivative

```text
HISTORICAL_SOURCE_ID=HS-0003
TITLE=MANOSUBE Agent Civilization OS — Canonical Directory Constitution v0.1
ORIGINAL_FILENAME=Canonical-Directory-Constitution-v0.1.txt
SOURCE_CLASS=FORMAT_DERIVATIVE
STATUS=SUPERSEDED_HISTORICAL_SOURCE
CONTENT_SHA256=2c5300bd506639654bddd254f402f16ac8448fbc9d480ec599be2559095c089b
SIZE_BYTES=22524
LINE_COUNT=873
LINEAGE_GROUP=DIR-CONSTITUTION-V0.1
FORMAT_PARENT=HS-0001
CANONICAL_AUTHORITY=false
CURRENT_PHASE_AUTHORITY=false
INDEPENDENT_SEMANTIC_AUTHORITY=false
```

## 7.1 Relationship to HS-0001

この資料は、HS-0001と同じCanonical Directory Constitution v0.1系譜をplain-text形式で保持する。byte-identicalではなく、Markdown記号や空行等のformat差を含むためhashは異なる。

```text
BYTE_IDENTICAL_TO_HS_0001=false
SAME_DESIGN_LINEAGE=true
SEPARATE_CANONICAL_SOURCE=false
FORMAT_CHANGE_CREATES_AUTHORITY=false
```

## 7.2 Superseded reason

同じ意味系譜のformatted copyが独立Authorityとして残ると、表現差が意味差と誤認され、parallel constitutionが生じる。したがってHS-0003はformat derivativeとしてのみ保存する。

## 7.3 Canonical successors

HS-0001と同じく、現在の意味は次へ分割された。

```text
01_PROJECT_CONSTITUTION.md
02_CANONICAL_ROADMAP.md
04_REPOSITORY_ARCHITECTURE.md
05_PHASE_ACCEPTANCE_LEDGER.md
06_DEFERRED_DIFFERENCES.md
```

## 7.4 Future reuse

```text
plain-text recovery copy
format-difference comparison
historical wording recovery
transcription audit
```

## 7.5 Prohibited use

```text
MAY_NOT_RESOLVE_A_CONFLICT_AGAINST_HS_0001_BY_NEWNESS=true
MAY_NOT_CREATE_A_SECOND_DIRECTORY_CONSTITUTION=true
MAY_NOT_OVERRIDE_CURRENT_SOURCE_SET=true
MAY_NOT_BE_USED_AS_CURRENT_ARCHITECTURE_SNAPSHOT=true
```

---

# 8. HS-0004 — Composite Project Development Constitution

```text
HISTORICAL_SOURCE_ID=HS-0004
TITLE=完成工程・開発体制・役割分離・マージ判定に関する正式プロジェクト契約
ORIGINAL_FILENAME=#-MANOSUBE-Agent-Civilization-OS(2).txt
SOURCE_CLASS=SUPERSEDED_GOVERNANCE_SOURCE
STATUS=SUPERSEDED_HISTORICAL_SOURCE
CONTENT_SHA256=8c50783157c7fb97a2a28e34869e57e45c7677ee072e26ffdad9d5c3c7e441e9
SIZE_BYTES=33049
LINE_COUNT=1321
LINEAGE_GROUP=COMPOSITE-DEVELOPMENT-CONSTITUTION
ORIGINAL_STATUS=HUMAN_RATIFIED
CANONICAL_AUTHORITY=false
CURRENT_PHASE_AUTHORITY=false
IMPLEMENTATION_AUTHORITY=false
```

## 8.1 Original purpose

この資料は、完成工程、開発体制、役割分離、Issue作成、Claude Code handoff、GitHub、構造review、merge readiness、external finding、Codex review、作業時間表示、Phase移行および再発防止を一つの正式プロジェクト契約にまとめた。

主要な役割分離は現在にも継承されている。

```text
SHUKOU=FINAL_ACCEPTANCE_AND_MERGE_AUTHORITY
CHATGPT=STRUCTURAL_ADVISOR
CLAUDE_CODE=IMPLEMENTATION_EXECUTOR
GITHUB=AUDIT_AND_RECEIPT_SURFACE
```

## 8.2 Superseded reason

この資料は重要なHuman-ratified lineageだが、次の異なるauthority domainを同時に所有していた。

```text
source priority
roadmap
current phase
development governance
acceptance semantics
external finding handling
time communication
phase transition history
```

開発の進行により、current factとfixed governanceの更新頻度が分離した。また、GitHub live fact、Human meaning、Phase receiptおよびDeferred Differenceを別ownerへ分ける必要が生じた。

このため、その意味は破棄されず、current source setへ正規化・分割された。

## 8.3 Canonical successors

| Historical responsibility | Current owner |
|---|---|
| 情報源優先順位と競合解決 | `00_SOURCE_AUTHORITY_INDEX.md` |
| 0–22完成工程 | `02_CANONICAL_ROADMAP.md` |
| 現在PhaseとGitHub状態 | `03_CURRENT_DEVELOPMENT_STATE.md` |
| Phase受入・merge receipt | `05_PHASE_ACCEPTANCE_LEDGER.md` |
| 未完了義務・follow-on | `06_DEFERRED_DIFFERENCES.md` |
| SHUKOU・構造参謀・Claude Code・GitHubの役割 | `07_DEVELOPMENT_GOVERNANCE.md` |

## 8.4 Future reuse

```text
original Human-ratified role lineage
Issue construction checklist
Claude Code instruction structure
merge-readiness vocabulary
external-finding adoption boundary
Codex-review boundary history
work-time and progress communication rationale
one-work-unit development flow
```

再利用時は、現在の`07_DEVELOPMENT_GOVERNANCE.md`と比較し、失われた期待があれば新しいDifferenceとして提示する。旧文面をそのまま実装命令として渡してはならない。

## 8.5 Prohibited use

```text
MAY_NOT_OVERRIDE_07_DEVELOPMENT_GOVERNANCE=true
MAY_NOT_AUTHORIZE_IMPLEMENTATION_BY_ITSELF=true
MAY_NOT_DEFINE_CURRENT_PHASE=true
MAY_NOT_DECLARE_MERGE_READY=true
MAY_NOT_TRIGGER_CODEX_REVIEW=true
MAY_NOT_DECLARE_PHASE_COMPLETE=true
MAY_NOT_REOPEN_COMPLETED_PHASE=true
```

---

# 9. Supersession map

| Current source | Historical inputs absorbed or separated | What the current source owns now |
|---|---|---|
| `00_SOURCE_AUTHORITY_INDEX.md` | HS-0004の旧priority・role ordering | 情報源入口、fact-type owner、競合解決 |
| `01_PROJECT_CONSTITUTION.md` | HS-0001/HS-0003のKernel・parent・invariants | OS目的、Kernel、不変条件、親OS関係 |
| `02_CANONICAL_ROADMAP.md` | HS-0001/HS-0002/HS-0003/HS-0004の工程 | 唯一の0–22 Phase順序とGate |
| `03_CURRENT_DEVELOPMENT_STATE.md` | HS-0004のcurrent-position記述 | dated current-state projection |
| `04_REPOSITORY_ARCHITECTURE.md` | HS-0001/HS-0003のtarget tree | as-builtとtargetの分離 |
| `05_PHASE_ACCEPTANCE_LEDGER.md` | 旧資料内のacceptance期待 | Human acceptanceとmerge receipt履歴 |
| `06_DEFERRED_DIFFERENCES.md` | 旧期待のうち未実装だが保持すべきもの | Deferred、follow-on、future-owner obligation |
| `07_DEVELOPMENT_GOVERNANCE.md` | HS-0004の開発体制・review・merge手順 | 現在のrole、Authority、work route |
| `99_HISTORICAL_SOURCE_REGISTER.md` | HS-0001〜HS-0004 | provenanceと再利用境界 |

このmapは、current文書が旧資料の全文章を逐語的に継承したと主張しない。責務の現在ownerを示す。

---

# 10. Use protocol

履歴資料を参照する場合は、次の順序を守る。

```text
1. IDENTIFY_THE_HISTORICAL_SOURCE_ID
2. VERIFY_FILENAME_AND_CONTENT_HASH_WHEN_BYTES_MATTER
3. IDENTIFY_THE_QUESTION_TYPE
4. LOCATE_THE_CURRENT_CANONICAL_OWNER
5. COMPARE_HISTORICAL_EXPECTATION_WITH_CURRENT_TRUTH
6. CLASSIFY_ANY_UNPRESERVED_EXPECTATION
7. ESCALATE_SEMANTIC_DECISION_TO_SHUKOU
8. RECORD_ADOPTED_REMAINING_WORK_IN_06_IF_REQUIRED
9. NEVER_EXECUTE_FROM_THE_HISTORICAL_SOURCE_ALONE
```

許される参照例：

```text
Why was Adapter separated from Kernel?
→ Read HS-0001 for rationale
→ Confirm current rule in 01 and 04

Was real Agent execution originally expected near Temporary Agent?
→ Read HS-0002
→ Confirm Phase 12 acceptance in 05
→ Confirm remaining obligation DD-0001 in 06

Why does Claude Code stop before merge?
→ Read HS-0004 for lineage
→ Apply current rule from 07
```

禁止される参照例：

```text
Old roadmap says v0.5 includes execution
→ therefore reopen Phase 12

Old target tree contains a directory
→ therefore current repository is defective

Old governance says an action is permitted
→ therefore execute it now
```

---

# 11. Conflict handling

履歴資料とcurrent sourceが競合する場合、current sourceがそのfact typeのownerとして優先される。ただし、矛盾を黙って消さず、次を判断する。

```text
TYPOGRAPHICAL_DIFFERENCE
FORMAT_DIFFERENCE
INTENT_PRESERVED_ELSEWHERE
KNOWN_DEFERRED_DIFFERENCE
UNREGISTERED_REMAINING_EXPECTATION
EXPLICITLY_REJECTED_OR_SUPERSEDED_DECISION
AMBIGUOUS_REQUIRES_SHUKOU
```

未保存の重要期待が見つかった場合、それを直接current documentへ混入させない。構造参謀がDifferenceとして提示し、SHUKOUが採否とplacementを決定する。

```text
HISTORICAL_CONFLICT
≠ AUTOMATIC_ROADMAP_CHANGE

HISTORICAL_OMISSION
≠ AUTOMATIC_CURRENT_PHASE_BLOCKER

SHUKOU_DECISION_REQUIRED_FOR_MEANING_CHANGE=true
```

---

# 12. Format-copy rule

同じ内容をMarkdown、plain text、PDF、conversation exportまたは別filenameへ変換しても、新しいAuthorityは生まれない。

```text
FORMATTED_COPY_DOES_NOT_CREATE_NEW_AUTHORITY=true
RENAMED_COPY_DOES_NOT_CREATE_NEW_AUTHORITY=true
LONGER_COPY_DOES_NOT_WIN=true
NEWER_FILE_TIMESTAMP_DOES_NOT_WIN=true
MODEL_PREFERENCE_DOES_NOT_WIN=true
```

format copyに実質的な文言差がある場合は、同一資料と推定せず、diffを記録する。Human adoptionが確認できない追加文はhistorical proposalとして扱う。

---

# 13. Preservation rule

登録済み履歴資料は、security、privacy、licenseまたは明示的Human Decisionによる理由がない限り削除しない。

推奨保存形は次である。

```text
historical_sources/
  HS-0001__MANOSUBE_AGENT_CIVILIZATION_OS_DIRECTORY_CONSTITUTION.md
  HS-0002__COMPLETION_ROADMAP.txt
  HS-0003__CANONICAL_DIRECTORY_CONSTITUTION_V0_1.txt
  HS-0004__PROJECT_DEVELOPMENT_CONSTITUTION.txt
```

実際の保存pathはrepository architecture ownerに従う。本書はdirectory作成またはfile移動を単独でAuthorizeしない。

保存時は可能な限り次を保持する。

```text
original bytes
original filename
content hash
source date if known
origin URI if known
supersession record
```

---

# 14. Adding a historical source

旧資料を追加する場合、構造参謀が分類案を作り、SHUKOUがclassificationとsupersession meaningを受け入れる。

追加条件は次である。

```text
SOURCE_BYTES_OR_IMMUTABLE_REFERENCE_AVAILABLE=true
HASH_RECORDED_WHEN_BYTES_AVAILABLE=true
ORIGINAL_PURPOSE_IDENTIFIED=true
CURRENT_OWNER_IDENTIFIED=true
SUPERSEDED_REASON_STATED=true
FUTURE_REUSE_STATED=true
PROHIBITED_USE_STATED=true
SHUKOU_CLASSIFICATION_ACCEPTED=true
```

単なる古いcommit、closed Issue、merged PRまたはreview commentをすべて本書へ列挙しない。それらはGitHub lineageまたは`05_PHASE_ACCEPTANCE_LEDGER.md`で十分な場合がある。

本書へ登録するのは、current sourceと混同される可能性がある、独立資料として再利用価値がある、またはsupersessionを明示しないとparallel truthを生むものに限る。

---

# 15. Restoring historical content

履歴内容をcurrent governanceへ戻す行為は、復元ではなく新しいChangeである。

```text
HISTORICAL_CONTENT_SELECTED
→ CURRENT_OWNER_IDENTIFIED
→ EXPECTED_AND_OBSERVED_SEPARATED
→ STRUCTURAL_DIFFERENCE_RECORDED
→ SHUKOU_DECISION
→ AUTHORIZED_CHANGE
→ REVIEW
→ ACCEPTANCE
→ AFTER_STATE_REOBSERVATION
```

次の条件を満たしても自動復活しない。

```text
ORIGINAL_STATUS_WAS_CANONICAL
ORIGINAL_STATUS_WAS_HUMAN_RATIFIED
THE_OLD_TEXT_IS_MORE_DETAILED
THE_OLD_TEXT_PREDATES_THE_CURRENT_SOURCE
THE_CURRENT_SOURCE_OMITS_A_PARAGRAPH
```

過去のAuthorityは、現在の明示的supersessionによって終了している。再採択には現在のSHUKOU Decisionが必要である。

---

# 16. Relation to Deferred Differences

履歴資料に未実装期待が書かれていても、その存在だけではDeferred Differenceにならない。

```text
HISTORICAL_EXPECTATION
≠ ACTIVE_DEFERRED_DIFFERENCE
```

Deferred Differenceとして現在効力を持つには、`06_DEFERRED_DIFFERENCES.md`に、identity、expected state、observed state、lineage、deadline、ownerおよびclosure conditionが記録されていなければならない。

現在確認済みの代表的な橋渡しは次である。

| Historical expectation | Current record |
|---|---|
| Temporary AgentがDifference/Capability/Authority/Evidence candidateを伴い実作業する | `DD-0001 TEMPORARY_AGENT_EXECUTION_CONTRACT` |
| 旧Difference auditorのD2 adversarial totality | `DD-0002 DIFFERENCE_AUDITOR_ADVERSARIAL_TOTALITY_D2` |
| Claude Code PR handoff boot loader proposal | `DC-0001 CLAUDE_CODE_PR_HANDOFF_BOOT_LOADER` |
| Structural Advisor adoption-recording enforcement | `FD-0001 STRUCTURAL_ADVISOR_ADOPTION_RECORDING_GOVERNANCE` |

この表は`06`の内容を複製するものではない。詳細、status、deadlineおよびclosure authorityは必ず`06_DEFERRED_DIFFERENCES.md`を読む。

---

# 17. Update authority

本書の更新案は構造参謀が作成できる。次を意味する更新はSHUKOUの受入を必要とする。

```text
SOURCE_SUPERSEDED
SOURCE_RESTORED
SOURCE_CLASS_CHANGED
CANONICAL_SUCCESSOR_CHANGED
FUTURE_REUSE_SCOPE_CHANGED
HISTORICAL_SOURCE_REMOVED
```

実装者、Modelまたは自動整理処理は、filename、更新日、類似度またはcontent lengthだけでclassificationを変更してはならない。

```text
REGISTER_PREPARATION_OWNER=STRUCTURAL_ADVISOR
CLASSIFICATION_ACCEPTANCE_OWNER=SHUKOU
AUTOMATIC_SUPERSESSION_ALLOWED=false
AUTOMATIC_RESTORATION_ALLOWED=false
```

---

# 18. Machine-readable summary

```text
CURRENT_SOURCE_SET_COUNT=9
REGISTERED_HISTORICAL_SOURCE_COUNT=4
HISTORICAL_LINEAGE_GROUP_COUNT=3

HS_0001_CLASS=SUPERSEDED_DESIGN_SOURCE
HS_0001_LINEAGE=DIR_CONSTITUTION_V0_1
HS_0001_CANONICAL_AUTHORITY=false

HS_0002_CLASS=SUPERSEDED_ROADMAP_SOURCE
HS_0002_LINEAGE=VERSION_ROADMAP_PRE_0_22
HS_0002_CANONICAL_AUTHORITY=false

HS_0003_CLASS=FORMAT_DERIVATIVE
HS_0003_PARENT=HS_0001
HS_0003_CANONICAL_AUTHORITY=false

HS_0004_CLASS=SUPERSEDED_GOVERNANCE_SOURCE
HS_0004_LINEAGE=COMPOSITE_DEVELOPMENT_CONSTITUTION
HS_0004_CANONICAL_AUTHORITY=false

HISTORICAL_SOURCES_PRESERVED=true
HISTORICAL_SOURCES_DELETED=false
FORMATTED_COPY_CREATES_AUTHORITY=false
CURRENT_SOURCE_OWNERSHIP_PRESERVED=true
PARALLEL_INFORMATION_AUTHORITY=0
```

---

# 19. Terminal declaration

```text
HISTORICAL_PROVENANCE_REGISTERED=true
SUPERSEDED_SOURCES_IDENTIFIED=true
SUPERSESSION_REASONS_DEFINED=true
CANONICAL_SUCCESSORS_IDENTIFIED=true
FUTURE_REUSE_BOUNDARIES_DEFINED=true
PROHIBITED_USES_DEFINED=true
FORMAT_DUPLICATION_NEUTRALIZED=true
DEFERRED_DIFFERENCE_BOUNDARY_PRESERVED=true
HUMAN_RESTORATION_AUTHORITY_PRESERVED=true
```

旧資料は、MANOSUBE Agent Civilization OSがどのように現在の構造へ到達したかを証明するLineageである。

旧資料は現在を支配しない。しかし、現在が過去のどの判断から形成されたかを失わせない。
