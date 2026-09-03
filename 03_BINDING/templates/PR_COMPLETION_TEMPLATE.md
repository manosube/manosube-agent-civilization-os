# Pull Request Completion Template

```text
TEMPLATE_TYPE=PR_COMPLETION
BINDING=DEV-BINDING-0001
EXECUTOR=CLAUDE_CODE
EXECUTOR_TERMINAL_STATE=READY_FOR_STRUCTURAL_REVIEW
```

The executor fills this in when implementation and self-review are complete. It is the last
thing the executor does.

## Head

```text
PUSHED_HEAD=
BASE_SHA=
BRANCH=
MERGE_ALLOWED=false
```

## What changed

<!-- The bounded package, and nothing beyond it. -->

## Gates, by exit code

```text
pytest              EXIT=
schema validation   EXIT=
static analysis     baseline-relative, new findings on this surface:
clean worktree, local == origin
```

Report every gate by its exit code. A gate whose output is read for good news is not a gate.

## Explicit non-claims

<!-- What this work does NOT claim. Each `false` records a missing owner, not a defect. -->

## Handoff state

```text
CLAUDE_CODE_IMPLEMENTATION_COMPLETE=true
EXECUTOR_SELF_REVIEW_COMPLETE=true
GITHUB_PR_READY=true
READY_FOR_STRUCTURAL_REVIEW=true
STRUCTURAL_REVIEW=PENDING
MERGE_ALLOWED=false
```

The executor stops at `READY_FOR_STRUCTURAL_REVIEW`.

The Structural Advisor then reviews and returns one of:

```text
MERGE_RECOMMENDED | CORRECTION_REQUIRED | MORE_EVIDENCE_REQUIRED | BLOCKED | NOT_REVIEWED
```

`MERGE_RECOMMENDED` is a recommendation, not an acceptance. SHUKOU makes the final
acceptance decision and alone performs the merge operation.

No automated reviewer is invoked, required, waited for, or recommended by this route.
