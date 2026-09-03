# Implementation Handoff Template

```text
TEMPLATE_TYPE=IMPLEMENTATION_HANDOFF
BINDING=DEV-BINDING-0001
EXECUTOR=CLAUDE_CODE
EXECUTOR_TERMINAL_STATE=READY_FOR_SHUKOU_REVIEW
ACCEPTANCE_OWNER=SHUKOU
MERGE_OWNER=SHUKOU
```

The Structural Advisor fills this in and hands it to the executor. It carries a Difference
and a boundary, and it does not carry an acceptance decision — there is no field for one.

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
READY_FOR_SHUKOU_REVIEW
```

It does not request an automated external review, and does not proceed to acceptance or
merge. Those states belong to SHUKOU alone.
