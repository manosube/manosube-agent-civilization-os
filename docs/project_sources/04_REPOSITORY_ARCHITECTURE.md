# MANOSUBE Agent Civilization OS

## Repository Architecture — As-built and Target

```text
DOC_TYPE=REPOSITORY_ARCHITECTURE
DOCUMENT_ID=REPOSITORY-ARCHITECTURE-0001
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
STATUS=DATED_ARCHITECTURE_PROJECTION
SOURCE_AUTHORITY_CLASS=OBSERVED_AS_BUILT_PLUS_HUMAN_RATIFIED_TARGET
HUMAN_AUTHORITY=SHUKOU
REPOSITORY=manosube/manosube-agent-civilization-os
DEFAULT_BRANCH=main
OBSERVED_AT_UTC=2026-09-07T10:42:45Z
AS_BUILT_REF=1d41f7d1e79441249382be07e8d8dbed618331c8
IN_FLIGHT_REF=46975506299ada4cc5708b559d7de734cb05236f
AS_BUILT_TREE_COMPLETE=true
TARGET_TREE_IS_NOT_IMPLEMENTATION_EVIDENCE=true
```

---

# 0. Purpose

本書は、MANOSUBE Agent Civilization OSのrepository architectureを、次の二つのviewに分離して記録する。

```text
AS_BUILT_ARCHITECTURE
= specified repository refに実在するfile、directory、packageおよびdependency surface

TARGET_ARCHITECTURE
= Human-ratified ConstitutionとCanonical Roadmapが要求する責務、境界および依存方向
```

本書は、directory名を完成の代理指標にしない。

```text
DIRECTORY_PRESENT
≠ CAPABILITY_IMPLEMENTED

TARGET_DIRECTORY_LISTED
≠ DIRECTORY_PRESENT

TEST_DIRECTORY_PRESENT
≠ PHASE_ACCEPTED

EQUIVALENT_PLACEMENT
≠ CONSTITUTIONAL_VIOLATION
```

現在Phase、Issue、Pull Request、review、test countおよびmerge permissionは、`03_CURRENT_DEVELOPMENT_STATE.md`が所有する。Phaseごとの恒久的な受入履歴は、`05_PHASE_ACCEPTANCE_LEDGER.md`が所有する。

---

# 1. Observation boundary

## 1.1 Accepted as-built ref

| Field | Observed value |
|---|---|
| Repository | [`manosube/manosube-agent-civilization-os`](https://github.com/manosube/manosube-agent-civilization-os) |
| Default branch | `main` |
| Observed commit | [`1d41f7d1e79441249382be07e8d8dbed618331c8`](https://github.com/manosube/manosube-agent-civilization-os/commit/1d41f7d1e79441249382be07e8d8dbed618331c8) |
| Tree traversal | Recursive and untruncated |
| Tree entries | 547 |
| Blob entries | 443 |
| Directory entries | 104 |

```text
AS_BUILT_MEANS=EXISTS_ON_ACCEPTED_MAIN_REF
AS_BUILT_DOES_NOT_INCLUDE=OPEN_PR_CONTENT
```

## 1.2 In-flight architecture overlay

Phase 13のopen PR #52は、accepted mainとは別viewとして観測する。

| Field | Observed value |
|---|---|
| Pull Request | [#52](https://github.com/manosube/manosube-agent-civilization-os/pull/52) |
| Head | [`46975506299ada4cc5708b559d7de734cb05236f`](https://github.com/manosube/manosube-agent-civilization-os/commit/46975506299ada4cc5708b559d7de734cb05236f) |
| Tree traversal | Recursive and untruncated |
| Tree entries | 528 |
| Blob entries | 424 |
| Directory entries | 104 |
| Relationship to main | Additive overlay; no removed paths observed |

```text
IN_FLIGHT_ARCHITECTURE
≠ AS_BUILT_ACCEPTED_ARCHITECTURE

OPEN_PR_PATH
≠ MERGED_PATH
```

---

# 2. Three-world architecture

Repositoryの形は、憲法が定める三つのworldを支えなければならない。

| World | Responsibility | Repository expression |
|---|---|---|
| Kernel Source World | Constitution、schema、contract、deterministic engine、verification | repository source tree |
| Canonical State World | BindingされたProjectのState、Difference、Change、Evidence、Lineage | one Store ownerを通じたproject-local persistent state |
| Adapter World | Kernelと外界の交換可能な接続 | later adapters and projections |

```text
KERNEL_SOURCE_WORLD
≠ CANONICAL_STATE_WORLD
≠ ADAPTER_WORLD
```

OS sourceと対象Projectの実データも分離する。

```text
MANOSUBE_REPOSITORY
= OS source, contracts, schemas, engines, tests

BOUND_PROJECT/.manosube/
= project civilization state
```

Runtime dataをrepository source directoryへ直接蓄積することはtarget architectureではない。

---

# 3. Accepted main — root as-built tree

```text
manosube-agent-civilization-os/
├── .gitignore
├── 00_KERNEL/
├── 01_SCHEMA/
├── 02_ENGINE/
├── 03_BINDING/
├── 04_BOOT/
├── 05_CLI/
├── 07_AGENT_RUNTIME/
├── docs/
├── examples/
├── scripts/
├── src/
├── tests/
├── LICENSE
├── NOTICE.md
├── ORIGIN.md
├── README.md
├── SECURITY.md
└── pyproject.toml
```

Root番号はPhase番号そのものではなく、repository上の責務配置である。番号の欠番、同名でない配置、または将来rootが未作成であることだけから、Phase failureを推論してはならない。

```text
ROOT_NUMBER
≠ PHASE_NUMBER

DIRECTORY_SEQUENCE
≠ ROADMAP_SEQUENCE
```

---

# 4. As-built responsibility map

| Root | Observed responsibility | Status |
|---|---|---|
| `00_KERNEL/` | Canonical contracts、Constitution、Invariants、Completion semantics、Vertical Proof | Implemented documentation surface |
| `01_SCHEMA/` | Canonical JSON schemas and schema policy | Implemented |
| `02_ENGINE/` | Historical/scaffold engine directories; most contain `.gitkeep` | Present scaffold, not implementation owner |
| `03_BINDING/` | Binding contracts、policy、template and trust boundary | Implemented contract surface |
| `04_BOOT/` | Boot contract and index | Implemented contract surface |
| `05_CLI/` | CLI contract and index | Implemented contract surface |
| `07_AGENT_RUNTIME/` | Temporary Agent lifecycle contract and index | Implemented contract surface |
| `docs/decisions/` | ADR lineage | Implemented decision record surface |
| `examples/01_minimal_kernel_cycle/` | Minimal project / vertical demonstration material | Implemented example surface |
| `scripts/` | Repository validators and verification helpers | Implemented support surface |
| `src/manosube_agent_civilization/` | Executable Python owners | Implemented through accepted Phase 12 |
| `tests/` | Contract、unit、integration、natural-cycle proofs | Implemented verification surface |

## 4.1 Important placement interpretation

`02_ENGINE/` is not the executable engine owner on accepted main. Executable implementation resides under `src/manosube_agent_civilization/`.

```text
02_ENGINE_DIRECTORY_PRESENT=true
02_ENGINE_EXECUTABLE_OWNER=false
PYTHON_EXECUTABLE_OWNER=src/manosube_agent_civilization
CLASSIFICATION=RATIFIED_EQUIVALENT_PLACEMENT
```

The scaffold must not be mistaken for a second engine or parallel owner.

---

# 5. Kernel as-built architecture

```text
00_KERNEL/
├── 01_OBJECTIVE/
├── 02_STATE/
├── 03_OBSERVATION/
├── 04_DIFFERENCE/
├── 05_AUTHORITY/
├── 06_CHANGE/
├── 07_EVIDENCE/
├── 08_REFLOW/
├── KERNEL_CONSTITUTION.md
├── KERNEL_INDEX.md
├── KERNEL_INVARIANTS.md
├── COMPLETION_SEMANTICS.md
├── HUMAN_AGENT_WORK_COMMUNICATION.md
├── KERNEL_VERTICAL_WORK_UNIT_DELIVERY.md
└── VERTICAL_PROOF_CONTRACT.md
```

Kernelの因果順序は保持されている。

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

`09_LINEAGE/`という独立rootはaccepted mainに存在しない。LineageはState、Difference、ReflowおよびStoreのcontract/schema/implementationへ分散せず、各owner間の正規参照として実装されている。

```text
DEDICATED_LINEAGE_DIRECTORY_PRESENT=false
LINEAGE_CAPABILITY_ABSENT=false
CLASSIFICATION=RATIFIED_EQUIVALENT_PLACEMENT
```

---

# 6. Schema as-built architecture

```text
01_SCHEMA/
├── common/
├── objective/
├── state/
├── observation/
├── difference/
├── authority/
├── change/
├── evidence/
├── reflow/
├── binding/
├── SCHEMA_INDEX.md
├── MIGRATION_POLICY.md
└── VERSIONING_POLICY.md
```

Schemaは実装とは別責務だが、Canonical meaning、identity、fingerprint、Authority、Evidence sufficiency、Lineageまたはreconstructionへ影響する変更は、単なるdirectory changeではない。

```text
SCHEMA_CHANGE_MAY_REQUIRE_HUMAN_DECISION=true
SCHEMA_DIRECTORY_IS_NOT_CANONICAL_STATE_STORE=true
```

---

# 7. Executable package as-built architecture

```text
src/manosube_agent_civilization/
├── state/
├── observation/
├── difference/
├── authority/
├── change/
├── evidence/
├── reflow/
├── store/
├── binding/
├── boot/
├── cli/
├── agent_runtime/
├── development_binding/
├── topology.py
├── __init__.py
└── py.typed
```

## 7.1 Package ownership

| Package | Primary responsibility |
|---|---|
| `state` | Canonicalization and fingerprint |
| `observation` | Boundary、scope、source snapshot、normalization and observation |
| `difference` | Difference identity、derivation、lifecycle、completion and closure policy evaluation |
| `authority` | Rules、approval、prohibition、scope and deterministic decision |
| `change` | Authorized Change identity and construction |
| `evidence` | Evidence identity、construction、levels and sufficiency |
| `reflow` | Closure route、atomic transition composition、reopen and lineage |
| `store` | Sole persistent file-store interface and atomic write ownership |
| `binding` | Project admission、boundary、identity and canonical binding route |
| `boot` | Project、Authority and State restoration into verified Boot context |
| `cli` | Removable CLI projection |
| `agent_runtime` | Temporary Agent lifecycle only |
| `development_binding` | Current repository development-role and command policy evaluation |
| `topology.py` | Architectural topology validation surface |

## 7.2 Canonical owner boundary

```text
CANONICAL_STATE_OWNER_COUNT=1
PERSISTENCE_OWNER=store

DIFFERENCE_COMPLETION_OWNER=difference
AUTHORITY_DECISION_OWNER=authority
EVIDENCE_SUFFICIENCY_OWNER=evidence
STATE_TRANSITION_COMPOSITION_OWNER=reflow
```

Packages may compose existing owners but must not duplicate them.

---

# 8. Test architecture

```text
tests/
├── contract/
├── unit/
├── integration/
├── natural_cycle/
├── fixtures/
└── shared helper modules
```

| Test layer | Architectural purpose |
|---|---|
| `contract/` | Static contract、schema、token and public-surface conformance |
| `unit/` | Owner-local deterministic behavior and rejection proofs |
| `integration/` | Real predecessor-to-owner route connection |
| `natural_cycle/` | Full canonical cycle and reconstruction proof |
| `fixtures/` | Explicit bounded worlds and immutable test inputs |

```text
CONTRACT_TEST
≠ VERTICAL_PROOF

UNIT_TEST
≠ REAL_OWNER_CONNECTION

TEST_COUNT
≠ ARCHITECTURAL_COMPLETION
```

The architecture requires vertical progression over local input-space exhaustion. Tests may harden an owner, but only a current-route blocker or required Phase Gate may prevent progression.

---

# 9. Phase 13 in-flight overlay

PR #52 adds the following paths over accepted main:

```text
08_VERIFICATION/
├── VERIFICATION_CONTRACT.md
└── VERIFICATION_INDEX.md

src/manosube_agent_civilization/independent_verification/
├── __init__.py
├── errors.py
├── route.py
└── types.py

tests/contract/independent_verification/
└── test_independent_verification_static_conformance.py

tests/integration/independent_verification/
└── test_run_independent_verification.py
```

No removed paths and no modified blob paths were observed between accepted main and the current PR tree; existing parent directory tree objects naturally have changed tree SHAs.

```text
IN_FLIGHT_ADDED_PATH_COUNT=12
IN_FLIGHT_ADDED_DIRECTORY_COUNT=4
IN_FLIGHT_ADDED_BLOB_COUNT=8
IN_FLIGHT_REMOVED_PATH_COUNT=0
IN_FLIGHT_MODIFIED_BLOB_COUNT=0
```

This overlay is not yet accepted as-built architecture.

さらに、Round 2で採択された次のarchitecture connections are not proven at this head:

```text
CANONICAL_VERIFIER_SELECTION_AUTHORITY_BINDING
VERIFICATION_RESULT_TO_EXISTING_EVIDENCE_OWNER_HANDOFF
UNAVAILABLE_WITH_DISTINGUISHABLE_PROVENANCE
```

Classification:

```text
CURRENT_PHASE_13_OVERLAY=IN_FLIGHT_NOT_ACCEPTED
ROUND_2_CONNECTION_GAPS=CURRENT_ROUTE_BLOCKER
```

---

# 10. Target responsibility architecture

Target architectureは、特定の未来directory名ではなく、交換不可能な責務と交換可能な器官の境界として固定する。

```text
Governance and Human meaning
        ↓
Policy and Constitution
        ↓
Canonical Kernel owners
        ↓
Binding and Runtime composition
        ↓
Temporary capability
        ↓
Adapters and Projections
        ↓
External World
```

Code dependencyは、外側から内側へ向かう。

```text
ADAPTER → KERNEL CONTRACT
INTERFACE → BOOT / KERNEL ROUTE
AGENT RUNTIME → VERIFIED BOOT CONTEXT
PROJECTION → CANONICAL IDENTITY
```

次は禁止する。

```text
KERNEL → GITHUB ADAPTER
KERNEL → MODEL PROVIDER
KERNEL → CLI
KERNEL → VPS
KERNEL → WEB UI
KERNEL → AGENT MEMORY
```

---

# 11. Target capability placement by roadmap

Future targetはPhase orderに従い、Phase開始前にdirectoryを先回りしてCanonical化しない。

| Phase | Target responsibility | Current architecture state |
|---:|---|---|
| 13 | Independent Verification adapter into existing Evidence owner | In-flight at PR #52; not accepted |
| 14 | GitHub observation/projection adapter | Absent by design |
| 15 | Runtime observation adapter | Absent by design |
| 16 | Replaceable model adapters | Absent by design |
| 17 | Read-only URL boot interface | Absent by design |
| 18 | Controlled autonomous Change execution | Absent by design |
| 19 | Dynamic multi-Agent execution | Absent by design |
| 20 | Long-running proof harness and metrics | Absent by design |
| 21 | Comparative benchmark harness | Absent by design |
| 22 | v1.0 acceptance and release surface | Absent by design |

```text
ABSENT_FUTURE_ADAPTER
≠ CURRENT_DEFECT

PREMATURE_DIRECTORY_CREATION
≠ PROGRESS
```

Exact directory names and numeric prefixes for Phase 14 onward require the bounded design work of the relevant Phase. This document must not pre-authorize them.

---

# 12. Target external-organ architecture

The following responsibilities remain replaceable organs:

| Organ | May do | May not own |
|---|---|---|
| Local repository observer | Observe bounded repository facts | Authority or completion |
| GitHub adapter | Project canonical records to Issues/PRs/checks and observe GitHub | Canonical identity or State |
| Runtime adapter | Observe bounded deployed/runtime reality | Repository-derived runtime truth |
| Model adapter | Invoke a selected model within explicit input/authority | State、Authority、Evidence sufficiency |
| CLI | Present and invoke existing routes | Kernel semantics |
| URL read-only boot | Restore and project under read-only Authority | Change permission |
| Human projection | Render status and request decisions | Silent Human adoption |

No adapter outage may destroy Canonical State.

---

# 13. Target bound-project state tree

Conceptual target:

```text
bound-project/
└── .manosube/
    ├── BINDING.json
    ├── OBJECTIVE.json
    ├── BOUNDARY.json
    ├── AUTHORITY.json
    ├── STATE/
    ├── DIFFERENCE/
    ├── CHANGE/
    ├── EVIDENCE/
    ├── LINEAGE/
    └── RUNTIME/
```

This is a responsibility projection, not a requirement that the FileStateStore expose this exact physical directory arrangement. Physical persistence may use manifests、content-addressed records and atomic transaction structures, provided:

```text
CANONICAL_STATE_OWNER_COUNT=1
STATE_RELOADABLE=true
LINEAGE_RECONSTRUCTABLE=true
ATOMIC_VISIBILITY=true
RECOVERY_FAILS_CLOSED=true
ADAPTER_CANNOT_WRITE_DIRECTLY=true
```

Therefore the conceptual tree and physical Store layout may differ without contradiction.

---

# 14. As-built to target classification

| Observed difference | Classification | Reason |
|---|---|---|
| Executable code is under `src/`, not `02_ENGINE/` | `RATIFIED_EQUIVALENT_PLACEMENT` | Standard Python package is the sole executable owner |
| No dedicated `09_LINEAGE/` root | `RATIFIED_EQUIVALENT_PLACEMENT` | Lineage is owned across State/Reflow/Store contracts and records |
| No top-level `WORLD/` package | `RATIFIED_EQUIVALENT_PLACEMENT` | Repository world enters through Observation and Binding boundaries |
| Phase 12 lacks real Agent execution | `DEFERRED_REMAINING_DIFFERENCE` | Lifecycle complete; execution contract explicitly deferred |
| Phase 13 paths exist only in PR #52 | `CURRENT_ROUTE_BLOCKER` until accepted | Open PR cannot become accepted architecture by existence |
| Phase 14+ adapter roots are absent | `DEFERRED_REMAINING_DIFFERENCE` by roadmap | Not yet authorized implementation scope |
| Old proposed names differ from current names | `HISTORICAL_NAME_ONLY` | Responsibility and owner identity govern, not historical spelling |

No `UNRESOLVED_STRUCTURAL_CONTRADICTION` is declared in accepted main by this observation.

```text
UNRESOLVED_STRUCTURAL_CONTRADICTION_COUNT=0
```

This non-claim does not clear Phase 13 blockers recorded in `03_CURRENT_DEVELOPMENT_STATE.md`.

---

# 15. Architecture invariants

```text
KERNEL_HAS_NO_MODEL_DEPENDENCY
KERNEL_HAS_NO_GITHUB_DEPENDENCY
KERNEL_HAS_NO_VPS_DEPENDENCY
KERNEL_HAS_NO_CLI_DEPENDENCY
KERNEL_HAS_NO_WEB_UI_DEPENDENCY

AGENT_IS_NOT_STATE
ISSUE_IS_NOT_DIFFERENCE
PR_IS_NOT_CHANGE_AUTHORITY
CI_PASS_IS_NOT_COMPLETION
MEMORY_IS_NOT_CANONICAL_TRUTH

EVERY_CHANGE_HAS_AUTHORITY
EVERY_CLOSURE_HAS_SUFFICIENT_EVIDENCE
EVERY_COMPLETION_REQUIRES_REOBSERVATION
EVERY_STATE_TRANSITION_HAS_LINEAGE
```

Architecture tests should guard forbidden dependencies and duplicate owners. They must not freeze harmless filenames or prevent ratified equivalent placement.

---

# 16. Import and ownership rules

## 16.1 Allowed direction

```text
outer adapter or interface
→ public Kernel / Boot / Binding contract
→ deterministic owner
→ sole Store interface
```

## 16.2 Forbidden direction

```text
kernel imports provider-specific model
kernel imports GitHub client
kernel imports VPS/runtime provider
kernel imports CLI renderer
adapter mutates Store internals
agent creates Authority
projection closes Difference
verifier persists its own Evidence
second component creates parallel State registry
```

## 16.3 Composition rule

Cross-owner orchestration must pass canonical references and typed values. It must not infer identity from cwd、environment、conversation、branch name、Issue number or provider metadata.

---

# 17. Architecture change control

The following changes require explicit Human approval:

```text
KERNEL_BOUNDARY_CHANGE
CANONICAL_OWNER_CHANGE
DEPENDENCY_DIRECTION_CHANGE
AUTHORITY_OWNER_CHANGE
COMPLETION_OWNER_CHANGE
STORE_OWNER_CHANGE
TARGET_RESPONSIBILITY_CHANGE
PHASE_TO_ARCHITECTURE_MAPPING_CHANGE
```

The following may be implementation-level changes when semantics remain unchanged:

```text
internal module split
private helper relocation
test file reorganization
ratified equivalent placement
non-semantic filename correction
```

An Agent、PR or existing directory cannot ratify its own architectural expansion.

---

# 18. Update procedure

This file must be updated when:

```text
accepted main tree materially changes
new Phase architecture is merged and re-observed
package ownership changes
canonical dependency direction changes
target responsibility changes by Human Decision
an equivalent placement is newly ratified
an unresolved structural contradiction is found or closed
```

Each update must record:

```text
OBSERVED_AT_UTC
AS_BUILT_REF
recursive tree completeness
material added / removed / moved owners
classification of every as-built / target difference
Human decision when target architecture changes
```

---

# 19. Architecture receipt

```text
OBSERVED_AT_UTC=2026-09-07T10:42:45Z
AS_BUILT_REF=1d41f7d1e79441249382be07e8d8dbed618331c8
AS_BUILT_TREE_ENTRY_COUNT=547
AS_BUILT_BLOB_COUNT=443
AS_BUILT_DIRECTORY_COUNT=104
AS_BUILT_TREE_TRUNCATED=false

IN_FLIGHT_REF=46975506299ada4cc5708b559d7de734cb05236f
IN_FLIGHT_TREE_ENTRY_COUNT=528
IN_FLIGHT_BLOB_COUNT=424
IN_FLIGHT_DIRECTORY_COUNT=104
IN_FLIGHT_TREE_TRUNCATED=false

EXECUTABLE_OWNER_ROOT=src/manosube_agent_civilization
CANONICAL_STATE_OWNER_COUNT=1
KERNEL_DEPENDENCY_ON_EXTERNAL_ADAPTERS=false

PHASE_13_OVERLAY_ACCEPTED=false
PHASE_14_PLUS_IMPLEMENTED=false
TEMPORARY_AGENT_EXECUTION_CONTRACT=DEFERRED_REMAINING_DIFFERENCE
UNRESOLVED_STRUCTURAL_CONTRADICTION_COUNT=0
```

This receipt proves only the observed architecture of the specified refs and the stated target mapping. It does not prove Phase acceptance, runtime behavior, test success, or Objective completion.

---

# 20. Accepted architecture through Phase 16

```text
OBSERVED_AT_UTC=2026-09-10T05:53:55Z
AS_BUILT_REF=8bc9d0e7a3784b658f8b523361904552f089b3c6
AS_BUILT_TREE_ENTRY_COUNT=684
AS_BUILT_BLOB_COUNT=558
AS_BUILT_DIRECTORY_COUNT=126
AS_BUILT_TREE_TRUNCATED=false

ACCEPTED_PHASE_RANGE=0..16
PHASE_13_INDEPENDENT_VERIFICATION_ACCEPTED=true
PHASE_14_GITHUB_PROJECTION_ACCEPTED=true
PHASE_15_RUNTIME_ACCEPTED=true
PHASE_16_MODEL_RUNTIME_ACCEPTED=true
PHASE_17_IMPLEMENTED=false
```

Phase 16で追加されたas-built ownerは `11_MODEL_RUNTIME/`、
`src/manosube_agent_civilization/model_runtime/`、7件のModel Runtime/Authority schema、および既存
Authority/Evidence ownerへの限定拡張である。`07_AGENT_RUNTIME/` と
`src/manosube_agent_civilization/agent_runtime/` はPhase 12のTemporary Agent Execution Contractを
引き続き所有し、Phase 16は第二のexecution-contract ownerを作らない。

```text
TEMPORARY_AGENT_EXECUTION_CONTRACT_OWNER=PHASE_12_TEMPORARY_AGENT
MODEL_RUNTIME_ROLE=CONSUMER_AND_PROVIDER_NEUTRAL_ADAPTER_BINDING
SECOND_EXECUTION_CONTRACT=false
MODEL_OUTPUT_IS_AUTHORITY=false
MODEL_OUTPUT_IS_EVIDENCE=false
LIVE_PROVIDER_CREDENTIAL_USE=false
AUTONOMOUS_CHANGE=false
CANONICAL_STATE_OWNER_COUNT=1
```

Phase 13からPhase 16までに追加されたIndependent Verification、GitHub Projection、Runtime、Model
Runtimeは、State、Observation、Difference、Authority、Change、Evidence、Reflow、Binding、Bootの
既存ownerを置換しない。各adapterは外部境界であり、Kernelの正準StateまたはHuman Authorityには
ならない。

---

# 21. Accepted architecture through Phase 17

```text
OBSERVED_AT_UTC=2026-09-10T14:17:21Z
AS_BUILT_REF=faed2e0fc8caa4977cf831f67d2fe0c6d2976427
AS_BUILT_TREE_ENTRY_COUNT=713
AS_BUILT_BLOB_COUNT=581
AS_BUILT_DIRECTORY_COUNT=132
AS_BUILT_TREE_TRUNCATED=false

ACCEPTED_PHASE_RANGE=0..17
PHASE_17_URL_BOOT_ACCEPTED=true
PHASE_18_AUTONOMOUS_CHANGE_IMPLEMENTED=false
```

Phase 17で追加されたas-built surfaceは、`12_URL_BOOT/`、
`src/manosube_agent_civilization/url_boot/`、
`01_SCHEMA/url_boot/url_source_observation_envelope.schema.json`、および既存source-impact mappingへの
限定的な登録である。URL Bootは独立Kernel、browser agent、crawler、一般HTTP clientまたは
Change executorではない。

```text
URL_BOOT_ROLE=BOUNDED_READ_ONLY_EXTERNAL_OBSERVATION_ADAPTER
URL_CONTENT_IS_AUTHORITY=false
URL_CONTENT_CAN_MUTATE_STATE=false
URL_CONTENT_CAN_EXECUTE_CHANGE=false
REDIRECT_REAUTHORIZED_EACH_HOP=true
NETWORK_ADMISSION_ROUTE_OWNED=true
FAILED_OR_REFUSED_FETCH_COMMITS_STATE=false
EXACT_BINDING_BOOT_PROVENANCE_REQUIRED=true
SEPARATE_URL_KERNEL=false
SECOND_OBSERVATION_OWNER=false
SECOND_EVIDENCE_OWNER=false
SECOND_AUTHORITY_OWNER=false
CANONICAL_STATE_OWNER_COUNT=1
PARALLEL_CANONICAL_AUTHORITY=0
AUTONOMOUS_CHANGE=false
```

production compositionはcaller-supplied adapter objectまたはclassifier/resolver/connector callableを
保持しない。adapter identityはcomposition時にexact built-in plain dataとして一度だけ検証・
再構築・freezeされ、production routeのDNS解決、address分類および接続はfixed shipped pathが所有する。
loopbackを許すdisposable local verticalは非出荷test fixtureに隔離され、issuerとverifierはEd25519で
分離される。これらはPhase 17のread-only observation Boundaryを成立させるが、Phase 18の
Autonomous Change権限または実装を先取りしない。

---

# 22. Accepted architecture through Phase 18

```text
OBSERVED_AT_UTC=2026-09-11T09:47:55Z
AS_BUILT_REF=91128e332138bb23466bf0f43a9f633cd646e891
AS_BUILT_TREE_ENTRY_COUNT=749
AS_BUILT_BLOB_COUNT=611
AS_BUILT_DIRECTORY_COUNT=138
AS_BUILT_TREE_TRUNCATED=false

ACCEPTED_PHASE_RANGE=0..18
PHASE_18_CONTROLLED_AUTONOMOUS_CHANGE_ACCEPTED=true
PHASE_19_MULTI_AGENT_IMPLEMENTED=false
```

Phase 18で追加されたas-built surfaceは、`13_CHANGE_EXECUTOR/`、
`src/manosube_agent_civilization/change_executor/`、
`01_SCHEMA/change_executor/`の5 schema、および既存static/source-impact mappingへの限定的な登録である。
Change Executorは既にAuthority確認済みのcanonical Changeを、composition時に固定・検証されたclosed
Boundaryとadapter identityの下で実行するadapter layerであり、Kernel elementではない。

```text
CHANGE_EXECUTOR_ROLE=BOUNDED_AUTHORIZED_CHANGE_EXECUTION_ADAPTER
CHANGE_EXECUTOR_OWNER_COUNT=1
AUTONOMY_BOUNDARY_EXPLICIT=true
AUTHORITY_CHECK_BEFORE_EXECUTION=true
PROHIBITED_SCOPE_BLOCKED=true
STALE_AUTHORITY_BLOCKED=true
EXECUTION_IDEMPOTENCY_DEFINED=true
AGENT_CANNOT_SELF_CLOSE=true
REOBSERVATION_REQUIRED=true
HUMAN_KILL_SWITCH_PROVEN=true
SECOND_STATE_OWNER=false
SECOND_OBSERVATION_OWNER=false
SECOND_EVIDENCE_OWNER=false
SECOND_AUTHORITY_OWNER=false
SECOND_REFLOW_OWNER=false
CANONICAL_STATE_OWNER_COUNT=1
PARALLEL_CANONICAL_AUTHORITY=0
```

production adapterはcaller-supplied disposable worktreeに限定されたfilesystem write/deleteだけを扱い、
GitHub push/merge、deployment、credential、billing、security policy、Objective、Authority、Kernel
Constitution、completion semantics、任意shell/subprocess/networkまたはproduction mutationを許可しない。
intent、attempt、terminal receiptおよびkill-switch chainはChange Executor固有のexecution記録であり、
既存canonical State、Observation、EvidenceまたはReflow ownerを置換しない。

Phase 19のdynamic multi-agent selection、Agent-specific provenance、conflict representation、Evidence
aggregation inputおよびrelease receiptは、このaccepted architectureには未実装である。
