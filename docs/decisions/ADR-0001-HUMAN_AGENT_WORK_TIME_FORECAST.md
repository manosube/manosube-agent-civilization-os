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

## Acceptance

```text
HUMAN_CONSTITUTIONAL_APPROVAL=true
EXPLICIT_ORIGIN_DIFFERENCE=true
BEFORE_AND_AFTER_SEMANTICS=true
PARENT_COMPATIBILITY_ANALYSIS=true
NON_REPLACEMENT_PROOF=true
RECORDED_DECISION_LINEAGE=true
```
