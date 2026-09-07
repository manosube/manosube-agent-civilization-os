# MANOSUBE Agent Civilization OS

## Canonical Roadmap — Phase 0 to Phase 22

```text
DOC_TYPE=CANONICAL_ROADMAP
DOCUMENT_ID=CANONICAL-ROADMAP-0001
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
STATUS=CANONICAL_ROADMAP
SOURCE_AUTHORITY_CLASS=HUMAN_RATIFIED_ROADMAP
HUMAN_AUTHORITY=SHUKOU
ROADMAP_SEQUENCE_COUNT=1
PHASE_COUNT=23
FIRST_PHASE=0_CONSTITUTION
FINAL_PHASE=22_V1_0
PHASE_RENUMBERING_BY_INFERENCE=false
PHASE_REOPENING_BY_INFERENCE=false
```

---

# 0. Purpose

本書は、MANOSUBE Agent Civilization OSを完成させる唯一のPhase順序を定める。

本書が所有するものは次である。

```text
Phase order
Phase dependency
Phase purpose
owned capability
required canonical output
Phase-specific Gate
explicit non-targets
deferred-work placement deadlines
v1.0 acceptance route
```

本書は現在の進捗、Issue、Pull Request、branch、commit SHA、test countまたはreview状態を所有しない。それらは`03_CURRENT_DEVELOPMENT_STATE.md`および`05_PHASE_ACCEPTANCE_LEDGER.md`に属する。

```text
ROADMAP
≠ CURRENT_STATUS

ROADMAP
≠ ACCEPTANCE_LEDGER

ROADMAP
≠ IMPLEMENTATION_INVENTORY
```

---

# 1. One completion sequence

```text
0  Constitution
↓
1  State
↓
2  Observation
↓
3  Difference
↓
4  Authority
↓
5  Change
↓
6  Evidence
↓
7  Reflow / Lineage
↓
8  Vertical Proof
↓
9  Binding
↓
10 Boot
↓
11 CLI
↓
12 Temporary Agent
↓
13 Independent Verification
↓
14 GitHub
↓
15 Runtime
↓
16 Multi-model
↓
17 URL Read-only
↓
18 Autonomous Change
↓
19 Multi-Agent
↓
20 Long-running Proof
↓
21 Comparative Benchmark
↓
22 v1.0
```

```text
ROADMAP_SEQUENCE_COUNT=1
PHASE_SKIPPING_ALLOWED=false
PARALLEL_PHASE_COMPLETION_ALLOWED=false
PREMATURE_ADAPTER_EXPANSION_ALLOWED=false
```

後段Phaseは、前段Phaseの実在するCanonical Outputを受け取らなければならない。

文書、schema、stub、mock、directoryまたはtest nameだけによる接続を認めない。

---

# 2. Universal Phase entry and exit

## 2.1 Entry condition

Phaseを開始するには、少なくとも次を満たす。

```text
PREDECESSOR_PHASE_ACCEPTED=true
PREDECESSOR_MERGE_RECEIPT_CONFIRMED=true
PREDECESSOR_AFTER_STATE_REOBSERVED=true
CURRENT_PHASE_DIFFERENCE_DEFINED=true
CURRENT_PHASE_BOUNDARY_DEFINED=true
IMPLEMENTATION_AUTHORITY_EXPLICIT=true
```

設計検討は前段完了前でも可能だが、後段実装の開始許可を意味しない。

```text
DESIGN_ALLOWED
≠ IMPLEMENTATION_ALLOWED
```

## 2.2 Exit condition

Phase完成は、次の連鎖を必要とする。

```text
OWNED_CAPABILITY_IMPLEMENTED=true
REAL_PREDECESSOR_CONNECTED=true
CANONICAL_OUTPUT_PRODUCED=true
REQUIRED_TESTS_PASS=true
CURRENT_ROUTE_BLOCKERS=0
REQUIRED_PHASE_GATES_PASS=true
COMPLETION_INFLATION=false
STRUCTURAL_REVIEW_PASS=true
MERGE_RECOMMENDED=true
SHUKOU_ACCEPTED=true
MERGE_RECEIPT_CONFIRMED=true
AFTER_STATE_REOBSERVED=true
```

```text
CONTRACT_PRESENT
≠ PHASE_COMPLETE

CODE_PRESENT
≠ PHASE_COMPLETE

TEST_PASS
≠ PHASE_COMPLETE

PR_MERGED
≠ PHASE_COMPLETE

AGENT_DONE
≠ PHASE_COMPLETE
```

## 2.3 Vertical progression rule

Phase exitを阻止できる追加作業は次に限る。

```text
CURRENT_ROUTE_BLOCKER
REQUIRED_PHASE_GATE
```

次は記録して保持するが、現在Phaseを無期限に継続させない。

```text
DEFERRED_NON_CLAIM
FOLLOW_ON_DIFFERENCE
FUTURE_OWNER_OBLIGATION
```

```text
VERTICAL_ROUTE_EXTENSION_IS_THE_DEFAULT=true
HORIZONTAL_EXHAUSTION_IS_NOT_AN_IMPLICIT_PHASE_GATE=true
CURRENT_ROUTE_DEFECTS_MUST_CLOSE=true
```

---

# 3. Phase 0 — Constitution

## Purpose

親文明OSからの派生境界、Canonical Kernel、Authorityおよび禁止事項を固定する。

## Structural Difference

```text
PROJECT_INTENT_EXISTS
AND
DERIVATION_AND_KERNEL_BOUNDARIES_ARE_NOT_YET_BINDING
```

## Owned capability

```text
parent-OS preservation
one Kernel definition
Kernel scope
Human constitutional authority
adapter exclusion
self-change rules
```

## Canonical output

```text
ORIGIN
PROJECT_CONSTITUTION
KERNEL_CONSTITUTION
PARENT_OS_MAPPING
CONSTITUTIONAL_INVARIANTS
```

## Gate 0

```text
PARENT_OS_PRESERVED=true
DERIVATION_BOUNDARY_DEFINED=true
KERNEL_SCOPE_FIXED=true
ADAPTERS_EXCLUDED_FROM_KERNEL=true
CONSTITUTIONAL_CHANGE_REQUIRES_HUMAN=true
```

## Non-targets

```text
KERNEL_IMPLEMENTATION=false
ADAPTER_IMPLEMENTATION=false
AGENT_IMPLEMENTATION=false
```

---

# 4. Phase 1 — Canonical State

## Purpose

Agentより先に、Projectの現在位置を決定的・永続的・復元可能に表現する。

## Structural Difference

```text
OBJECTIVE_EXISTS
AND
PROJECT_STATE_HAS_NO_CANONICAL_REPRESENTATION
```

## Owned capability

```text
semantic state
state metadata
canonical serialization
semantic fingerprint
state identity
```

Canonical Stateは、少なくとも次の世界を区別可能でなければならない。

```text
objective
repository
requirements
code
tests
runtime
infrastructure
deployment
open differences
active changes
evidence references
authority references
lineage
```

## Canonical output

```text
serializable Project State
stable semantic fingerprint
reloadable State representation
```

## Gate 1

```text
STATE_SERIALIZABLE=true
STATE_RELOADABLE=true
STATE_FINGERPRINT_STABLE=true
SESSION_INDEPENDENT=true
MODEL_INDEPENDENT=true
CODE_AND_RUNTIME_STATE_SEPARABLE=true
```

## Non-targets

```text
WORLD_OBSERVATION=false
DIFFERENCE_DERIVATION=false
CHANGE_EXECUTION=false
```

---

# 5. Phase 2 — Observation

## Purpose

Boundary内の外界からObserved Factを取得し、raw factとnormalized factを分離してCanonical Stateへ接続する。

## First observation source

```text
LOCAL_GIT_REPOSITORY
```

## Observed scope

```text
commit
branch
working tree
files
configuration
tests
```

## Canonical output

```text
scoped Observation
raw-fact reference
normalized facts
observation provenance
```

## Gate 2

```text
OBSERVATION_REPEATABLE=true
RAW_AND_NORMALIZED_FACT_SEPARATED=true
OBSERVER_NOT_AUTHORITY=true
SAME_WORLD_SAME_FACT=true
NEGATIVE_OBSERVATION_BOUNDED=true
```

## Non-targets

```text
FIX_SELECTION=false
CHANGE_PROPOSAL=false
DIFFERENCE_CLOSURE=false
```

---

# 6. Phase 3 — Structural Difference

## Purpose

Taskではなく、Expected StateとObserved Stateの構造差をCanonicalに導出する。

```text
EXPECTED_STATE
− OBSERVED_STATE
= STRUCTURAL_DIFFERENCE
```

## Canonical output

```text
canonical Difference identity
expected-state reference
observed-state reference
Difference lifecycle state
supporting Evidence references
```

## Gate 3

```text
DIFFERENCE_CAN_EXIST_WITHOUT_ISSUE=true
DIFFERENCE_HAS_CANONICAL_ID=true
EXPECTED_AND_OBSERVED_SEPARATED=true
DIFFERENCE_EVIDENCE_LINKED=true
DERIVATION_DETERMINISTIC=true
```

## Non-targets

```text
GITHUB_ISSUE_REQUIRED=false
WORK_UNIT_IS_CANONICAL=false
AGENT_SELECTION=false
```

---

# 7. Phase 4 — Authority

## Purpose

Change前に、CapabilityとAuthorityを分離し、実行可否をCanonicalに決定する。

```text
CAN_DO
≠ MAY_DO
```

## Minimum authority levels

```text
AUTONOMOUS
HUMAN_APPROVAL_REQUIRED
PROHIBITED
```

## Canonical output

```text
Authority Rule
Authority Request
Authority Decision
Approval or prohibition lineage
```

## Gate 4

```text
CAPABILITY_AUTHORITY_SEPARATED=true
UNAUTHORIZED_CHANGE_BLOCKED=true
PROHIBITED_CHANGE_BLOCKED=true
HUMAN_APPROVAL_PATH_PROVEN=true
STALE_APPROVAL_REJECTED=true
```

## Non-targets

```text
CHANGE_EXECUTION=false
AGENT_SELF_AUTHORIZATION=false
TOOL_AVAILABILITY_AS_AUTHORITY=false
```

---

# 8. Phase 5 — Change

## Purpose

Differenceに対するChangeを、before-state、Authority、action、scopeおよびlineageへ結合する。

## Canonical output

```text
Change identity
difference reference
before-state reference
Authority Decision reference
requested capability
action and scope
after-state observation requirement
```

## Gate 5

```text
CHANGE_HAS_BEFORE_STATE=true
CHANGE_HAS_AUTHORITY=true
CHANGE_HAS_LINEAGE=true
STALE_CHANGE_BLOCKED=true
CHANGE_CANNOT_SELF_DECLARE_COMPLETION=true
```

## Non-targets

```text
CHANGE_EQUALS_COMPLETION=false
EXECUTOR_IS_CLOSURE_OWNER=false
AUTONOMOUS_AGENT_REQUIRED=false
```

---

# 9. Phase 6 — Evidence

## Purpose

ObservationおよびChange Resultを、Completion判定に使用可能なEvidenceとしてCanonicalに表現する。

## Evidence classes

```text
SOURCE_EVIDENCE
OBSERVATION_EVIDENCE
TEST_EVIDENCE
STATE_EVIDENCE
CHANGE_RESULT_EVIDENCE
RUNTIME_EVIDENCE
NEGATIVE_EVIDENCE
```

## Canonical output

```text
content-addressed Evidence
claim and subject binding
scope and time binding
provenance
sufficiency evaluation input
```

## Gate 6

```text
CLAIM_WITHOUT_EVIDENCE_CANNOT_CLOSE=true
NEGATIVE_EVIDENCE_SUPPORTED=true
NEGATIVE_EVIDENCE_BOUNDED=true
AGENT_DONE_IS_NOT_EVIDENCE=true
CI_GREEN_IS_NOT_PROJECT_COMPLETE=true
CHANGE_RESULT_EVIDENCE_SUPPORTED=true
```

## Non-targets

```text
EVIDENCE_EQUALS_CLOSURE=false
PRODUCER_SELF_ATTESTATION_SUFFICIENT=false
```

---

# 10. Phase 7 — Reflow / Lineage

## Purpose

EvidenceをCanonical Stateへ原子的に還流し、State transitionとLineageを再構築可能にする。

```text
STATE_n
→ OBSERVATION
→ DIFFERENCE
→ AUTHORIZED_CHANGE
→ EVIDENCE
→ REFLOW
→ STATE_n+1
```

## Canonical output

```text
Reflow Decision
Difference lifecycle event
atomic transaction
State transition
append-only lineage
recovery evidence
```

## Gate 7

```text
STATE_TRANSITION_PROVEN=true
LINEAGE_COMPLETE=true
LINEAGE_RECONSTRUCTABLE=true
ROLLBACK_POINT_IDENTIFIABLE=true
REOBSERVATION_REQUIRED=true
ATOMIC_COMMIT_PROVEN=true
CRASH_RECOVERY_PROVEN=true
```

## Non-targets

```text
ADAPTER_DIRECT_STATE_WRITE=false
PARTIAL_TRANSITION_CANONICAL=false
```

---

# 11. Phase 8 — Vertical Proof

## Purpose

Phase 0〜7の実ownerを一本の自然経路へ接続し、AI、VPS、GitHub AdapterなしでCanonical Cycleが完結することを証明する。

## Required natural route

```text
OBJECTIVE
→ INITIAL_STATE
→ OBSERVATION
→ OBSERVATION_EVIDENCE
→ DIFFERENCE
→ AUTHORITY_DECISION
→ CHANGE
→ RE_OBSERVATION
→ CHANGE_RESULT_EVIDENCE
→ EVIDENCE_SUFFICIENCY
→ CLOSURE_EVALUATION
→ ATOMIC_REFLOW
→ NEW_STATE
→ RECONSTRUCTION
```

## Canonical output

```text
Vertical Proof terminal receipt
identity ledger
natural-cycle test evidence
negative-route evidence
fresh-process reconstruction proof
```

## Gate 8

```text
OBJECTIVE_TO_STATE=true
STATE_TO_OBSERVATION=true
OBSERVATION_TO_DIFFERENCE=true
DIFFERENCE_TO_AUTHORIZED_CHANGE=true
CHANGE_TO_REOBSERVATION=true
REOBSERVATION_TO_EVIDENCE=true
EVIDENCE_TO_REFLOW=true
REFLOW_TO_NEW_STATE=true
DIFFERENCE_CLOSE_PROVEN=true
ONE_FULL_NATURAL_CYCLE_PASS=true
```

## Non-targets

```text
AGENT_REQUIRED_FOR_KERNEL=false
GITHUB_REQUIRED_FOR_KERNEL=false
VPS_REQUIRED_FOR_KERNEL=false
FIXTURE_NAME_ALONE_IS_PROOF=false
```

---

# 12. Phase 9 — Binding

## Purpose

実ProjectをMANOSUBEのObservation Spaceへ、Objective、Boundary、Authorityおよびsource identityを失わず結合する。

```text
install MANOSUBE into project
≠
bind project into MANOSUBE observation space
```

## Canonical output

```text
Project identity
Project Binding
Objective Revision reference
Boundary reference
Human Authority reference
Authority Policy reference
Observation Source references
genesis transaction receipt
```

## Gate 9

```text
PROJECT_IDENTITY_CANONICAL=true
BINDING_ATOMIC=true
BINDING_REPLAY_DETERMINISTIC=true
BOUNDARY_EXPLICIT=true
AUTHORITY_REFERENCE_RESOLVABLE=true
SECRET_VALUES_EXCLUDED=true
BOUND_PROJECT_RECONSTRUCTABLE=true
```

## Non-targets

```text
PROJECT_DISCOVERY_BY_CWD=false
BINDING_EQUALS_BOOT=false
GITHUB_BINDING_REQUIRED=false
```

---

# 13. Phase 10 — Boot

## Purpose

明示されたProject identity、Binding identityおよびStoreから、検証済みProject Contextを復元する唯一の入口を作る。

## Boot responsibility

```text
identify Project
verify Binding and Authority references
restore current State
```

Bootは推論、Difference修復、Change実行またはStore recoveryを行わない。

## Canonical output

```text
immutable verified Boot Context
```

## Gate 10

```text
BOOT_ENTRY_POINT_COUNT=1
PROJECT_BINDING_REVERIFIED=true
AUTHORITY_REFERENCE_REVERIFIED=true
STATE_RECONSTRUCTED_FROM_CANONICAL_STORE=true
BOOT_ZERO_WRITE=true
REPEATED_BOOT_DETERMINISTIC=true
CORRUPT_OR_PENDING_STORE_FAILS_CLOSED=true
```

## Non-targets

```text
AUTO_DISCOVERY=false
STORE_RECOVERY=false
CHANGE_EXECUTION=false
AGENT_CREATION=false
```

---

# 14. Phase 11 — CLI

## Purpose

既存Bootを、人間またはprocessが明示的に起動できる、交換可能でread-onlyなCLI projectionとして公開する。

## Canonical route

```text
explicit command arguments
→ existing Boot exactly once
→ canonical Boot Context projection
```

## Canonical output

```text
machine-readable Boot Context projection
typed machine-readable failure projection
process exit status
```

## Gate 11

```text
CLI_REMOVABLE_WITHOUT_KERNEL_DAMAGE=true
CLI_ONLY_PROJECTION=true
CLI_PUBLIC_ENTRY_POINT_COUNT=1
CLI_ZERO_STORE_WRITE=true
CLI_FRESH_PROCESS_PROVEN=true
CLI_FAILURE_TYPED_AND_NONZERO=true
CLI_TRACEBACK_NOT_PUBLIC=true
```

## Non-targets

```text
CLI_OWNS_BOOT=false
CLI_OWNS_STATE=false
CLI_CHANGE_COMMAND=false
CLI_OBSERVE_COMMAND_REQUIRED_BY_THIS_PHASE=false
```

---

# 15. Phase 12 — Temporary Agent Lifecycle

## Purpose

検証済みBoot Context上に、一時的、非永続、非AuthorityのAgent lifetimeを開始し、明示的に解放できるようにする。

## Canonical route

```text
explicit Store
+ Project identity
+ Binding identity
→ existing Boot exactly once
→ active Temporary Agent
→ read-only Boot Context access
→ explicit terminal release
```

## Owned capability

```text
temporary Agent lifecycle only
active versus released state only
```

## Canonical output

```text
non-persisted Temporary Agent handle
terminal local release result
```

## Gate 12

```text
PHASE_12_TEMPORARY_AGENT_LIFECYCLE=true
AGENT_STATELESS=true
AGENT_NON_PERSISTENT=true
AGENT_NON_AUTHORITATIVE=true
AGENT_STARTS_FROM_VERIFIED_BOOT_CONTEXT=true
AGENT_RELEASE_IDEMPOTENT=true
AGENT_RELEASE_TERMINAL=true
AGENT_LIFECYCLE_ZERO_STORE_WRITE=true
AGENT_PUBLIC_CONSTRUCTION_ROUTE_COUNT=1
SESSION_TERMINATION_STATE_SAFE=true
```

## Explicit non-targets

```text
MODEL_PROVIDER_IMPLEMENTED=false
PROMPT_EXECUTION_IMPLEMENTED=false
TOOL_EXECUTION_IMPLEMENTED=false
COMMAND_EXECUTION_IMPLEMENTED=false
CAPABILITY_SELECTION_IMPLEMENTED=false
WORK_UNIT_EXECUTION_IMPLEMENTED=false
EVIDENCE_CANDIDATE_OUTPUT_IMPLEMENTED=false
AGENT_RESUME_IMPLEMENTED=false
PERSISTENT_AGENT_MEMORY_IMPLEMENTED=false
```

## Deferred remaining Difference

```text
TEMPORARY_AGENT_LIFECYCLE
≠ TEMPORARY_AGENT_EXECUTION

TEMPORARY_AGENT_EXECUTION_CONTRACT
= DEFERRED_REMAINING_DIFFERENCE

PHASE_12_REOPENED=false
ROADMAP_RENUMBERED=false
```

詳細、block効果、placement authorityおよびclosure条件は`06_DEFERRED_DIFFERENCES.md`が所有する。

---

# 16. Phase 13 — Independent Verification

## Purpose

独立検証が必要なDifferenceについて、実装lineageと区別可能なverification lineageを生成できるようにする。

固定Reviewer Agentは作らない。Verifierは決定論的test runner、schema validator、runtime observer、異なるAIまたはHumanでよい。

## Canonical route

```text
explicit Verification Requirement
→ Human-authorized Verifier Selection
→ immutable verification Boundary
→ one explicit Verifier invocation
→ immutable Verification Result
→ existing Evidence owner
→ existing sufficiency and closure owners
```

## Owned capability

```text
verification requirement
verifier selection binding
verification boundary
verification-specific provenance
verification result normalization
```

## Canonical output

```text
VERIFIED
FAILED
INSUFFICIENT
UNAVAILABLE

as immutable Verification Result candidates
```

Verification Resultは、それ自体ではEvidence record、Authority Decision、Closure receipt、State transitionまたはmerge authorizationではない。

## Gate 13

```text
VERIFICATION_ONLY_WHEN_REQUIRED=true
IMPLEMENTER_NOT_CLOSURE_AUTHORITY=true
VERIFIER_SELECTION_HUMAN_AUTHORIZED=true
VERIFIER_IDENTITY_BOUND=true
VERIFICATION_BOUNDARY_IMMUTABLE=true
IMPLEMENTATION_INDISTINGUISHABLE_PROVENANCE_REJECTED=true
FAILURE_AND_INSUFFICIENCY_FAIL_CLOSED=true
VERIFICATION_RESULT_CANNOT_SELF_PERSIST=true
VERIFICATION_RESULT_CANNOT_SELF_CLOSE=true
```

## Non-targets

```text
FIXED_REVIEWER=false
SPECIFIC_MODEL_SELECTED=false
AUTOMATIC_VERIFIER_SELECTION=false
AUTOMATIC_CLOSURE=false
GITHUB_REVIEW_ADAPTER=false
```

---

# 17. Phase 14 — GitHub Adapter

## Purpose

Canonical Difference、ChangeおよびEvidenceを、identityを失わずGitHubへ投影し、GitHubの状態をCanonical Stateから分離する。

## Projection mapping

```text
Difference → Issue projection
Change → branch / commit / Pull Request projection
Evidence → check / review / artifact projection
```

## Canonical output

```text
projection envelope
canonical-to-GitHub identity mapping
GitHub observation receipts
idempotent projection result
```

## Gate 14

```text
GITHUB_NOT_CANONICAL=true
ISSUE_NOT_WORK_IDENTITY=true
PR_NOT_COMPLETION=true
GITHUB_AUTHORITY_EXPLICIT=true
PROJECTION_IDEMPOTENT=true
UNTRUSTED_GITHUB_CONTENT_NON_AUTHORITATIVE=true
GITHUB_OUTAGE_STATE_SAFE=true
```

## Non-targets

```text
GITHUB_AS_STATE_BACKEND=false
ISSUE_CREATES_DIFFERENCE=false
PR_MERGE_CLOSES_OBJECTIVE=false
BOT_FINDING_AUTO_ADOPTION=false
```

---

# 18. Phase 15 — Runtime Adapter

## Purpose

Repository、deploymentおよびruntimeの状態を分離し、実行世界をBoundary付きEvidenceとして観測する。

## Canonical route

```text
explicit runtime target identity
+ observation Boundary
+ time window
+ observation method
→ Runtime Observation
→ Runtime Evidence
→ existing Difference / Reflow owners
```

## Canonical output

```text
runtime target identity
bounded Runtime Observation
Runtime Evidence
negative Runtime Evidence when valid
```

## Gate 15

```text
CODE_RUNTIME_SEPARATED=true
DEPLOYED_IDENTITY_VERIFIED=true
BOUNDED_RUNTIME_OBSERVATION=true
NEGATIVE_EVIDENCE_SCOPED=true
RUNTIME_RECEIPT_REFLOWABLE=true
RUNTIME_NOT_REPOSITORY_DERIVED=true
```

## Non-targets

```text
VPS_REQUIRED=false
DEPLOYMENT_EQUALS_REACHABILITY=false
CI_GREEN_EQUALS_RUNTIME_COMPLETE=false
UNBOUNDED_NETWORK_DISCOVERY=false
```

---

# 19. Phase 16 — Multi-model Replaceability

## Purpose

Agentまたはmodelを交換しても、Canonical State、Authority、Difference、Evidence requirementおよび作業継続性を失わないことを証明する。

## Required proof

```text
Agent A starts from Canonical State
→ bounded work occurs
→ session ends
→ Agent B starts from Canonical State
→ no conversation handoff
→ work continues under the same Authority and Difference
```

## Canonical output

```text
provider-neutral model contract
model adapter boundary
model-swap proof receipt
session-loss recovery receipt
```

## Deferred execution decision boundary

Phase 16の設計開始前に、`TEMPORARY_AGENT_EXECUTION_CONTRACT`の正式配置をSHUKOUが決定しなければならない。

最初の実model Agent executionより前に、少なくとも次を閉じる。

```text
State-bound Work Unit input
Difference reference
required capability
Authority reference and check
Boundary reference
Evidence requirements
normalized Evidence candidates
Agent cannot self-close
```

この要件はPhase 16へ自動的に編入されることを意味しない。配置決定はHuman Authorityに属する。

```text
PLACEMENT_DECISION_REQUIRED_BEFORE_PHASE_16_DESIGN=true
EXECUTION_CONTRACT_REQUIRED_BEFORE_FIRST_REAL_MODEL_AGENT_EXECUTION=true
PLACEMENT_BY_INFERENCE=false
```

## Gate 16

```text
MODEL_SWAP_SAFE=true
SESSION_LOSS_SAFE=true
NO_CONVERSATION_HANDOFF_REQUIRED=true
MODEL_OUTPUT_NON_AUTHORITATIVE=true
CANONICAL_STATE_UNCHANGED_BY_PROVIDER_SWAP=true
NO_PROVIDER_SPECIFIC_KERNEL_DEPENDENCY=true
```

## Non-targets

```text
BEST_MODEL_SELECTION=false
PROVIDER_LOCK_IN=false
MODEL_MEMORY_AS_STATE=false
AUTONOMOUS_CHANGE=false
```

---

# 20. Phase 17 — Read-only URL Boot

## Purpose

URLを入口として外部情報をread-only Authorityで観測し、同一Kernelへ接続する。

これは別製品ではない。

```text
KERNEL
+ READ_ONLY_AUTHORITY
+ URL_SOURCE_ADAPTER
```

## Canonical output

```text
URL source identity
bounded fetched Observation
provenance and retrieval time
untrusted-content classification
read-only Boot projection
```

## Gate 17

```text
URL_CONTENT_NON_AUTHORITATIVE=true
READ_ONLY_AUTHORITY_ENFORCED=true
PROMPT_INJECTION_CANNOT_CREATE_AUTHORITY=true
FETCH_BOUNDARY_EXPLICIT=true
NETWORK_FAILURE_STATE_SAFE=true
URL_ENTRY_USES_EXISTING_KERNEL=true
```

## Non-targets

```text
URL_CHANGE_EXECUTION=false
WEB_CONTENT_AS_HUMAN_DECISION=false
SEPARATE_URL_KERNEL=false
```

---

# 21. Phase 18 — Controlled Autonomous Change

## Purpose

明示的に限定されたlow-risk Boundary内で、Authority確認済みChangeを自律実行できるようにする。

## Initial autonomous scope

```text
documentation
tests
isolated source
low-risk configuration
```

## Human approval or prohibited scope

```text
production
credentials
billing
security policy
Objective
Authority
Kernel Constitution
completion semantics
```

## Canonical output

```text
authorized execution receipt
performed Change result
Evidence candidates
re-observation request
```

## Gate 18

```text
AUTONOMY_BOUNDARY_EXPLICIT=true
AUTHORITY_CHECK_BEFORE_EXECUTION=true
PROHIBITED_SCOPE_BLOCKED=true
STALE_AUTHORITY_BLOCKED=true
EXECUTION_IDEMPOTENCY_DEFINED=true
AGENT_CANNOT_SELF_CLOSE=true
REOBSERVATION_REQUIRED=true
HUMAN_KILL_SWITCH_PROVEN=true
```

## Non-targets

```text
UNBOUNDED_AUTONOMY=false
PRODUCTION_AUTONOMY_BY_DEFAULT=false
CREDENTIAL_MUTATION_BY_DEFAULT=false
```

---

# 22. Phase 19 — Multi-Agent Dynamic Execution

## Purpose

DifferenceとRequired Capabilityに応じて、一時的な1、2またはN Agentを選択し、ObservationとEvidenceを混同せず統合する。

常設Agent組織は作らない。

```text
Difference
→ required capabilities
→ 1 / 2 / N temporary Agents
→ independent outputs
→ Evidence-based State decision
→ all Agents released
```

## Canonical output

```text
dynamic execution plan
Agent-specific provenance
conflict representation
Evidence aggregation input
release receipts
```

## Gate 19

```text
AGENT_COUNT_DIFFERENCE_DERIVED=true
MULTI_AGENT_NOT_PERMANENT_ORGANIZATION=true
EACH_AGENT_OUTPUT_HAS_PROVENANCE=true
CONSENSUS_NOT_TRUTH=true
CONFLICT_NOT_SILENTLY_COLLAPSED=true
CANONICAL_STATE_OWNER_COUNT=1
ALL_TEMPORARY_AGENTS_RELEASED=true
```

## Non-targets

```text
CONSENSUS_EQUALS_EVIDENCE=false
AGENT_MAJORITY_CREATES_AUTHORITY=false
PERMANENT_AGENT_HIERARCHY=false
```

---

# 23. Phase 20 — Long-running Project Proof

## Purpose

小さなfixtureではなく、長期間の実Projectで多数のDifferenceを連続処理し、停止、再開、Agent交換およびruntime到達を証明する。

## Proof scale

```text
10
30
50
100

sequential Structural Differences
```

## Required metrics

```text
false completion rate
human intervention count
human re-explanation count
rework count
runtime reachability
state reconstruction success
session-loss recovery success
agent-swap success
authority violation count
evidence completeness
time to structural closure
```

## Canonical output

```text
versioned benchmark corpus
long-running lineage
failure and recovery receipts
metric dataset
reproduction procedure
```

## Gate 20

```text
LONG_RUNNING_STATE_CONTINUITY_PROVEN=true
STATE_RECONSTRUCTION_REPEATABLE=true
SESSION_LOSS_RECOVERY_PROVEN=true
AGENT_SWAP_REPEATEDLY_PROVEN=true
RUNTIME_REACHABILITY_MEASURED=true
AUTHORITY_VIOLATIONS_RECORDED=true
FAILURES_NOT_EXCLUDED_FROM_DATASET=true
```

## Non-targets

```text
ONLY_SUCCESSFUL_RUNS_REPORTED=false
ONE_DEMO_EQUALS_LONG_RUNNING_PROOF=false
```

---

# 24. Phase 21 — Comparative Benchmark

## Purpose

同じAgent、同じProject群、同じBoundaryおよび比較可能なAuthority条件で、MANOSUBE有無による差を第三者が再現できる形で測定する。

## Comparison groups

```text
Codex alone
Claude Code alone
existing agent framework
MANOSUBE + the same Agent
```

特定製品名はbenchmark実施時の実在対象へ置換または追加できるが、比較原則は変えない。

## What MANOSUBE must prove

```text
fewer false completions
better long-term state retention
more successful runtime arrival
less human re-explanation
less rework
safe Agent replacement
fewer Authority violations
more complete Evidence
```

## Canonical output

```text
public benchmark protocol
frozen task corpus
environment manifest
raw results
analysis procedure
reproduction instructions
third-party reproduction receipts
```

## Gate 21

```text
SAME_AGENT_COMPARISON_AVAILABLE=true
CONTROL_GROUPS_DEFINED=true
METRICS_PREDECLARED=true
RAW_RESULTS_PUBLIC=true
FAILURES_INCLUDED=true
THIRD_PARTY_REPRODUCIBLE=true
CLAIMS_BOUNDED_BY_EVIDENCE=true
```

## Non-targets

```text
MOST_CODE_WRITTEN_AS_PRIMARY_METRIC=false
SELF_REPORTED_SUPERIORITY_SUFFICIENT=false
CHERRY_PICKED_SUCCESS_ONLY=false
```

---

# 25. Phase 22 — v1.0 Acceptance

## Purpose

HumanがObjective、Boundary、Authorityを与えた後、MANOSUBEがCanonical Stateを保ちながらObjective Stateまで循環を継続できることを最終受入する。

## Required v1.0 route

```text
Human gives
OBJECTIVE
BOUNDARY
AUTHORITY

↓

MANOSUBE reconstructs STATE

↓

OBSERVES reality

↓

detects STRUCTURAL DIFFERENCE

↓

determines REQUIRED CAPABILITY

↓

selects TEMPORARY AGENT

↓

checks AUTHORITY

↓

performs CHANGE

↓

collects EVIDENCE

↓

REFLOWS into canonical STATE

↓

REOBSERVES

↓

closes or retains DIFFERENCE

↓

continues until OBJECTIVE STATE
```

## Gate 22

```text
OBJECTIVE_CONTINUITY_PROVEN=true
AGENT_REPLACEMENT_SAFE=true
SESSION_LOSS_SAFE=true
GITHUB_INDEPENDENCE=true
RUNTIME_VERIFICATION=true
AUTHORITY_ENFORCEMENT=true
EVIDENCE_ONLY_COMPLETION=true
STATE_LINEAGE_PRESERVATION=true
LONG_RUNNING_PROOF_PASS=true
COMPARATIVE_BENCHMARK_PASS=true
THIRD_PARTY_REPRODUCTION_CONFIRMED=true
ALL_V1_0_BLOCKING_DIFFERENCES_CLOSED=true
```

## Final declaration

```text
MANOSUBE_AGENT_CIVILIZATION_OS_V1_0=true
```

この宣言はHuman Acceptance、release receiptおよびafter-state observationなしに発行してはならない。

---

# 26. Deferred Difference rule

完了済みPhaseの狭いcapabilityと、過去設計が想定した広いcapabilityの間に差が残る場合、次の原則を適用する。

```text
PHASE_ACCEPTANCE_IS_PRESERVED=true
REMAINING_DIFFERENCE_IS_PRESERVED=true
SILENT_COMPLETION_INFLATION=false
SILENT_PHASE_REOPENING=false
SILENT_PHASE_RENUMBERING=false
```

Deferred Differenceは`06_DEFERRED_DIFFERENCES.md`へ記録する。

各recordは少なくとも次を持つ。

```text
difference_id
originating expectation
expected state
observed state
current status
current blocking effect
placement decision deadline
implementation deadline
placement authority
closure evidence requirement
```

DeferralはDifferenceの消滅ではない。

```text
DEFERRED
≠ CLOSED

NON_BLOCKING_NOW
≠ NON_BLOCKING_FOREVER
```

---

# 27. Roadmap change rule

本Roadmapの次の変更には、SHUKOUの明示的なHuman Decisionが必要である。

```text
Phase order
Phase number
Phase purpose
Phase dependency
Phase-owned capability
Phase-specific Gate
v1.0 acceptance condition
deferred-work placement deadline
```

変更記録は次を明示する。

```text
affected section
before meaning
after meaning
reason
Human authority record
compatibility effect
effective version or repository commit
```

次はRoadmapを変更できない。

```text
Agent proposal
conversation convenience
Issue title
Pull Request scope
merged implementation
test result
review finding
tool availability
provider limitation
README wording
historical roadmap
```

```text
NO_ISSUE_MAY_RENUMBER_THE_ROADMAP=true
NO_PR_MAY_REDEFINE_A_PHASE_BY_IMPLICATION=true
NO_IMPLEMENTATION_MAY_CREATE_RETROACTIVE_AUTHORITY=true
```

---

# 28. Relationship to other information sources

| Information | Owner document |
|---|---|
| Source priority and conflict handling | `00_SOURCE_AUTHORITY_INDEX.md` |
| OS purpose and immutable principles | `01_PROJECT_CONSTITUTION.md` |
| Phase order, meaning, dependency, Gate | `02_CANONICAL_ROADMAP.md` |
| Current Phase and live repository state | `03_CURRENT_DEVELOPMENT_STATE.md` |
| As-built and target architecture | `04_REPOSITORY_ARCHITECTURE.md` |
| Human Phase acceptance and merge receipts | `05_PHASE_ACCEPTANCE_LEDGER.md` |
| Deferred remaining work | `06_DEFERRED_DIFFERENCES.md` |
| Development roles and operating procedure | `07_DEVELOPMENT_GOVERNANCE.md` |
| Superseded design provenance | `99_HISTORICAL_SOURCE_REGISTER.md` |

本書へcurrent Phase、current PR、current SHAまたはcurrent test countを追記してはならない。

```text
ROADMAP_CONTAINS_CURRENT_PHASE=false
ROADMAP_CONTAINS_CURRENT_PR=false
ROADMAP_CONTAINS_VOLATILE_SHA=false
ROADMAP_CONTAINS_CURRENT_TEST_COUNT=false
```

---

# 29. Final roadmap invariants

```text
THE_ROADMAP_IS_ONE.

THE_PHASE_ORDER_IS_FIXED BY HUMAN AUTHORITY.

EACH_PHASE_CLOSES ONE BOUNDED STRUCTURAL CAPABILITY.

EACH_PHASE_RECEIVES THE REAL OUTPUT OF ITS PREDECESSOR.

NO_PHASE_COMPLETES THROUGH DOCUMENTS, TESTS, OR MERGE ALONE.

NO_PHASE_IS_REOPENED OR RENUMBERED BY INFERENCE.

DEFERRED WORK REMAINS VISIBLE WITHOUT COMPLETION INFLATION.

VERTICAL PROGRESSION TAKES PRIORITY OVER UNBOUNDED LOCAL EXHAUSTION.

CURRENT PUBLIC ROUTE DEFECTS REMAIN BLOCKERS.

THE KERNEL REMAINS INDEPENDENT OF AGENT, MODEL, GITHUB, CLI, VPS, AND RUNTIME PROVIDERS.

V1.0 IS ACCEPTED ONLY AFTER LONG-RUNNING AND COMPARATIVE THIRD-PARTY PROOF.
```

```text
ROADMAP_SEQUENCE_COUNT=1
PHASE_COUNT=23
DEPENDENCY_ORDER_PRESERVED=true
PHASE_SKIPPING_ALLOWED=false
PHASE_RENUMBERING_BY_INFERENCE=false
PHASE_REOPENING_BY_INFERENCE=false
HORIZONTAL_EXHAUSTION_IS_NOT_AN_IMPLICIT_PHASE_GATE=true
CURRENT_ROUTE_BLOCKERS_MUST_CLOSE=true
DEFERRED_DIFFERENCES_MUST_REMAIN_VISIBLE=true
HUMAN_ROADMAP_AUTHORITY_PRESERVED=true
```

> Complete the truth-bearing route first. Expand its organs only after the preceding reality can reach them.
