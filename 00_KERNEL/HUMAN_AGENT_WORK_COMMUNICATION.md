# Human–Agent Work Communication Protocol

```text
DOC_TYPE=HUMAN_AGENT_WORK_COMMUNICATION_PROTOCOL
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=HUMAN-AGENT-WORK-COMMUNICATION-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
CONSTITUTIONAL_AUTHORITY=HUMAN
ESTIMATE_IS_FORECAST=true
ESTIMATE_IS_SLA=false
SILENT_LONG_RUNNING_WORK_PROHIBITED=true
```

---

## 1. Purpose

This protocol makes the human cost of waiting visible before an Agent begins substantive work. It lets the human decide whether to wait, continue another task, or intervene without mistaking normal work or an external wait for an error.

This is a cross-cutting human–Agent communication contract. It does not add a ninth Kernel element, transfer Human Authority, change a Difference, authorize a Change, or prove Completion.

Its authority rank is fixed by `ORIGIN.md`: it is subordinate to Human Objective / Constitutional Authority, `ORIGIN.md`, and `KERNEL_CONSTITUTION.md`; it is superior to the invariant registry, schemas, engine implementation, authority envelopes, adapters, Agent prompts, session instructions, and external work surfaces. A conflict MUST be resolved according to that hierarchy, never by silently weakening the higher-ranked contract.

---

## 2. Start-of-work forecast

Before the first substantive tool action of a work unit, the active Agent MUST display:

```text
予測作業時間: <lower bound>〜<upper bound>分
変動要因: <dominant uncertainty, if material>
```

The range MUST be an honest operational forecast based on the known scope, validation load, external dependencies, and review latency. It MUST NOT be presented as a promise or fabricated with false precision.

A response that can be completed immediately without substantive tools MAY omit the forecast.

When the initial upper bound exceeds ten minutes, the Agent MUST say so before work begins and identify the reason.

---

## 3. Observable work states

Long-running work MUST expose one of these states:

| State | Meaning |
| --- | --- |
| `WORK_RUNNING` | The Agent is actively inspecting, changing, or validating. |
| `EXTERNAL_REVIEW_WAIT` | Local work is ready and progress depends on an external review or service. |
| `BLOCKED` | Progress requires new authority, information, access, or a human decision. |
| `ERROR` | An actual failure prevents the current operation from continuing safely. |
| `COMPLETE` | The stated work unit and its required verification are complete. |

`EXTERNAL_REVIEW_WAIT` MUST NOT be reported as `ERROR`. A long duration alone MUST NOT be treated as proof of failure.

---

## 4. Mandatory re-estimation

The Agent MUST issue a concise status and revised forecast when any of the following occurs:

1. the initial upper bound is reached;
2. elapsed work reaches ten minutes without completion;
3. a review produces a new finding;
4. work changes from active execution to an external wait;
5. scope materially expands or contracts;
6. an actual blocker or error occurs.

The update MUST state the current work state, what changed, and a new time range. When the state is `EXTERNAL_REVIEW_WAIT`, `BLOCKED`, or `ERROR` and the remaining latency cannot be estimated honestly, `再予測: 不明` plus the next observation or recovery checkpoint satisfies this requirement. If work continues beyond ten minutes, further updates MUST occur at meaningful state changes and no less often than each additional ten-minute boundary.

---

## 5. External waits

When waiting for a review, build service, remote API, delegated machine approval, or other external system that requires no new human action, the Agent MUST report:

```text
状態: EXTERNAL_REVIEW_WAIT
完了済み: <locally completed evidence>
待機対象: <external dependency>
再予測: <range or explicitly unknown>
```

If external latency cannot be estimated honestly, the Agent MUST say `再予測: 不明` and provide the next observation checkpoint. It MUST NOT repeatedly claim that completion is imminent without new evidence.

When progress instead requires a new human decision, authorization, approval, or information, `BLOCKED` takes precedence over `EXTERNAL_REVIEW_WAIT`.

---

## 6. Error and blocker boundary

The Agent MUST report `ERROR` only when an operation has failed and safe continuation is not presently available. It MUST report `BLOCKED` when the next safe step requires human input, new authority, credentials, access, or a material scope decision.

Every `ERROR` or `BLOCKED` update MUST include:

- the failed or blocked operation;
- the evidence that distinguishes it from normal latency;
- completed work that remains valid;
- the smallest human decision or recovery action required.

---

## 7. Completion boundary

Time elapsed, a forecast being met, or an Agent progress report does not prove Completion.

```text
ESTIMATE_MET != WORK_COMPLETE
WORK_COMPLETE != DIFFERENCE_CLOSED
PR_MERGED != KERNEL_COMPLETE
```

`COMPLETE` may be reported only after the work unit's required validation and acceptance boundary are satisfied. Forecast history remains operational context and MUST NOT replace Evidence.

---

## 8. Minimum conformance

An Agent interaction conforms to this protocol only when all applicable conditions hold:

```text
START_FORECAST_PRESENT=true
FORECAST_RANGE_PRESENT=true
DOMINANT_UNCERTAINTY_DISCLOSED=true
TEN_MINUTE_CHECKPOINT_ENFORCED=true
OVERRUN_REESTIMATED=true
EXTERNAL_WAIT_DISTINGUISHED_FROM_ERROR=true
BLOCKER_DISTINGUISHED_FROM_ERROR=true
SILENT_LONG_RUNNING_WORK=false
FORECAST_USED_AS_COMPLETION_EVIDENCE=false
```

An interface or runtime MAY automate these notices, but automation MUST preserve the meanings and boundaries defined here.
