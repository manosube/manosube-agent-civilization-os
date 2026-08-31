# ADR-0001: Human–Agent Work Time Forecast

```text
DOC_TYPE=ORIGIN_AMENDMENT_DECISION
DOCUMENT_ID=ADR-0001-HUMAN-AGENT-WORK-TIME-FORECAST
STATUS=ACCEPTED
DECIDED_AT=2026-08-31
DECISION_AUTHORITY=HUMAN_CONSTITUTIONAL_AUTHORITY
ORIGIN_DIFFERENCE_ID=ORIGIN-DIFFERENCE-0001
PROTOCOL_REF=00_KERNEL/HUMAN_AGENT_WORK_COMMUNICATION.md
```

## Human constitutional approval

The repository owner explicitly directed that the Agent display an estimated work duration at the beginning of every substantive work unit, distinguish normal continuation from an error when work exceeds ten minutes, and encode that behavior into the OS specification.

This decision records that direction as Human Constitutional Approval. The Agent does not originate, broaden, or revoke that authority.

### Exact approval binding

```yaml
approval_id: APPROVAL-A9B8929A8452CDA34CA63536E6C457CB59F869DAC0BC04F1F7710AA8748EAEA4
change_id: KERNEL-CHANGE-0001
approved_state_fingerprint: sha256:d619fc0a563cdb0153af2dc78b4230c90ac83e328435702b39bad4a81c92bef3
approved_action_fingerprint: sha256:1d99e5088eacf91ab707a0df40e92f7140cdb464ab16974f81d72ae7d022d666
approved_by: github:manosube
approved_at: 2026-08-31T04:47:21Z
expires_at: null
scope: repository:manosube/manosube-agent-civilization-os;paths:ORIGIN.md,00_KERNEL/KERNEL_INDEX.md,00_KERNEL/HUMAN_AGENT_WORK_COMMUNICATION.md,docs/decisions/ADR-0001-HUMAN_AGENT_WORK_TIME_FORECAST.md
status: APPROVED
```

`approved_state_fingerprint` is SHA-256 over canonical JSON containing the repository, base commit `8a8d874c44b881374d319f1ccfd4b75192b3b65b`, and base tree `41ee6100753745f35db68dbdf67b7409c05fd36c`. `approved_action_fingerprint` is SHA-256 over canonical JSON containing `change_id`, the sorted affected paths, action `ADD_HUMAN_AGENT_WORK_TIME_FORECAST_PROTOCOL`, authority rank 4, and zero Kernel-element-count change. The approval ID is SHA-256 over the closed approval fields excluding `approval_id`.

## Explicit Origin Difference

```text
BEFORE:
The authority hierarchy defined no canonical human–Agent waiting-time communication contract.
Adapters, prompts, and sessions could omit forecasts or use inconsistent meanings for long waits and errors.

AFTER:
One cross-cutting protocol requires an honest forecast before substantive work, observable work states, ten-minute checkpoints, and re-estimation.
The protocol has one explicit authority rank below Human/Origin/Constitution and above implementation and execution surfaces.
```

The structural Difference is the absence of a stable human-visible time and status contract across interchangeable Agents, adapters, prompts, sessions, and tools.

## Before and after semantics

| Concern | Before | After |
| --- | --- | --- |
| Start notice | Optional and session-dependent | Forecast range required before substantive tool work |
| Ten-minute boundary | No canonical meaning | Status and re-estimation required |
| External latency | Could resemble failure | `EXTERNAL_REVIEW_WAIT` is distinct from `ERROR` |
| Human decision | Could resemble external wait | `BLOCKED` takes precedence |
| Unknown latency | Could force false precision | `不明` plus checkpoint is valid |
| Completion | Time report could be overread | Forecast is never Completion Evidence |

## Parent compatibility analysis

The parent MANOSUBE Civilization OS principles remain unchanged:

- civilization remains state;
- state remains cyclical;
- observation remains the means to detect and repair stopped cycles;
- Human Authority remains the source of constitutional intent.

The protocol only improves human visibility into the duration and state of an execution process. It does not alter the parent OS, its sealed baseline, its runtime independence, or its civilization principles.

```text
PARENT_PRINCIPLE_CHANGED=false
PARENT_BASELINE_CHANGED=false
PARENT_RUNTIME_DEPENDENCY_INTRODUCED=false
ORIGIN_COMPATIBILITY=PASS
```

## Non-replacement proof

The protocol does not become a Kernel element, State owner, Authority evaluator, Difference owner, Change executor, Evidence evaluator, or Reflow owner.

```text
CANONICAL_KERNEL_COUNT_CHANGE=0
CANONICAL_STATE_OWNER_COUNT_CHANGE=0
KERNEL_ELEMENT_COUNT_CHANGE=0
PARALLEL_CANONICAL_AUTHORITY=0
HUMAN_AUTHORITY_REPLACED=false
ORIGIN_REPLACED=false
KERNEL_CONSTITUTION_REPLACED=false
```

## Decision lineage

```text
HUMAN_REQUEST
→ ORIGIN-DIFFERENCE-0001
→ ADR-0001-HUMAN-AGENT-WORK-TIME-FORECAST
→ ORIGIN PRECEDENCE AMENDMENT
→ HUMAN-AGENT-WORK-COMMUNICATION-0001
→ KERNEL INDEX REGISTRATION
→ REVIEW AND MERGE
```

The implementation lineage is PR #23 on branch `agent/human-agent-work-time-forecast`. The exact accepted commit and merge commit are recorded by GitHub when the PR is merged; neither the PR nor its CI substitutes for the Human Constitutional Approval recorded above.

## Kernel change record

```text
CHANGE_ID=KERNEL-CHANGE-0001
AFFECTED_KERNEL_ELEMENT=CROSS_CUTTING_HUMAN_AGENT_COMMUNICATION
PREVIOUS_CONTRACT=NO_CANONICAL_WORK_TIME_FORECAST_PROTOCOL
PROPOSED_CONTRACT=HUMAN-AGENT-WORK-COMMUNICATION-0001
STRUCTURAL_REASON=HUMAN_WAITING_TIME_AND_WORK_STATE_WERE_NOT_VISIBLE_OR_STABLE
AUTHORITY_USED=APPROVAL-A9B8929A8452CDA34CA63536E6C457CB59F869DAC0BC04F1F7710AA8748EAEA4
COMPATIBILITY_IMPACT=ADDITIVE_COMMUNICATION_REQUIREMENT_ONLY
MIGRATION_REQUIREMENT=ADAPTERS_PROMPTS_AND_SESSIONS_MUST_EMIT_THE_PROTOCOL_NOTICES
INVARIANT_EVALUATION=PASS
AFTER_STATE_EVIDENCE=DOCUMENT_DIGESTS_PLUS_FINDING_ZERO_REVIEW
```

Existing canonical records, schemas, identities, State revisions, Difference lifecycles, and Authority decisions require no data migration. Execution surfaces must add the forecast and status notices before substantive work; an execution surface that cannot do so is nonconforming but does not rewrite canonical State.

### Invariant evaluation

```text
CANONICAL_KERNEL_COUNT=1 PASS
CANONICAL_STATE_OWNER_COUNT=1 PASS
PARALLEL_CANONICAL_AUTHORITY=0 PASS
HUMAN_OWNS_CONSTITUTIONAL_AUTHORITY PASS
AGENT_IS_EXECUTION_CAPABILITY PASS
ESTIMATE_IS_COMPLETION_EVIDENCE=false PASS
PARENT_RUNTIME_DEPENDENCY=false PASS
```

### After-state evidence

```text
00_KERNEL/HUMAN_AGENT_WORK_COMMUNICATION.md sha256:994af09285dd32b86335503466b09f9f4efbbf2046a715c1fffab456d6cf2666
00_KERNEL/KERNEL_INDEX.md sha256:a166c3d1a1ac7648d39346885ddbe696859e2b27d093d2511189c96abc176f14
ORIGIN.md sha256:fc824d909d956cf86425c0ca24f2b4bc5167c88a70aad4db0b15b865fcfae8c0
```

The final exact after-state commit and independent review result are appended to the immutable GitHub PR #23 lineage. If any listed document changes after this record, the digest mismatch invalidates this evidence and requires a new approval or a non-semantic correction determination.

## Acceptance

```text
HUMAN_CONSTITUTIONAL_APPROVAL=true
EXPLICIT_ORIGIN_DIFFERENCE=true
BEFORE_AND_AFTER_SEMANTICS=true
PARENT_COMPATIBILITY_ANALYSIS=true
NON_REPLACEMENT_PROOF=true
RECORDED_DECISION_LINEAGE=true
```
