# Implementation Handoff Template

```text
TEMPLATE_TYPE=IMPLEMENTATION_HANDOFF
BINDING=DEV-BINDING-0001
EXECUTOR=CLAUDE_CODE
EXECUTOR_TERMINAL_STATE=READY_FOR_STRUCTURAL_REVIEW
STRUCTURAL_REVIEW_OWNER=CHATGPT
MERGE_READINESS_RECOMMENDATION_OWNER=CHATGPT
FINAL_ACCEPTANCE_OWNER=SHUKOU
MERGE_OPERATION_OWNER=SHUKOU
```

The Structural Advisor fills this in and hands it to the executor. It carries a Difference
and a boundary. It does not carry a final acceptance decision — there is no field for one,
because the Advisor does not hold that decision.

## Work unit

```text
WORK_UNIT=
ISSUE=
BASE_BRANCH=main
BASE_SHA=
DELIVERY_SHAPE=ONE_ISSUE_ONE_BRANCH_ONE_PR
MERGE_ALLOWED=false
```

## Structural Difference

```text
CURRENT_STATE=
TARGET_STATE=
STRUCTURAL_DIFFERENCE=
```

## Required package

<!-- What must exist when this is done. One bounded vertical. -->

## Required validation

<!-- Every gate, reported by exit code. Never by reading output for good news. -->

## Adopted external findings

```text
ADOPTED_FINDING_COUNT=0
```

<!--
One block per finding, and only for findings SHUKOU has explicitly adopted. An
UNVERIFIED_EXTERNAL_OBSERVATION has no entry here and is not work.

ADOPTION_AUTHORITY=SHUKOU
OBSERVATION_ID=
DISPOSITION=
-->

## Prohibited

```text
MERGE=false
NEW_ISSUE=false
AUTOMATED_EXTERNAL_REVIEW_REQUEST=false
BOT_FINDING_AUTO_ADOPTION=false
```

## Termination

The executor stops here:

```text
READY_FOR_STRUCTURAL_REVIEW
```

It does not request an automated external review.

What follows is not the executor's:

```text
CHATGPT  → STRUCTURAL_REVIEW
         → MERGE_RECOMMENDED | CORRECTION_REQUIRED | MORE_EVIDENCE_REQUIRED
           | BLOCKED | NOT_REVIEWED

SHUKOU   → FINAL_ACCEPTANCE
         → MERGE_OPERATION
```

A merge readiness recommendation is the Advisor's. The acceptance decision and the merge
operation are the Human's. They are three separate things and no participant holds two of
them.
