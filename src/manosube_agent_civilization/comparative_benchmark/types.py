"""Closed vocabularies for the Comparative Benchmark package (Issue #89,
`ADOPT_PHASE_21_COMPARATIVE_BENCHMARK`).

`COMPARISON_GROUP_ROLES` is the one frozen present/absent axis Gate 21 itself requires
(`SAME_AGENT_COMPARISON_REQUIRED=true`, `MANOSUBE_PRESENT_AND_ABSENT_REQUIRED=true`).
`TASK_OUTCOMES` is a closed, totality-checked per-task vocabulary mirroring Phase 20's own
`FAILURES_NOT_EXCLUDED_FROM_DATASET`/`UNKNOWN_NE_ZERO`/`REFUSAL_NE_SYSTEM_FAILURE`/
`RETAINED_NE_CLOSED` discipline (Issue #89 section 5) -- a `REFUSED`/`RETAINED_INCOMPLETE`/
`FAILED`/`TIMED_OUT` outcome is never dropped from a result bundle's own raw events, and
never silently folded into `COMPLETED_VERIFIED` or into each other.
"""

from __future__ import annotations

#: The two roles every comparison group is exactly one of -- "same-Agent comparison" is the
#: structural fact that a `MANOSUBE_PRESENT` group and every `MANOSUBE_ABSENT` group in one
#: protocol freeze never share a `mechanism_identity` (see `engine.build_protocol_freeze`'s
#: own fail-closed disjointness check), never a claim this package merely asserts.
COMPARISON_GROUP_ROLES: frozenset[str] = frozenset({"MANOSUBE_PRESENT", "MANOSUBE_ABSENT"})

#: The closed, totality-checked per-task outcome vocabulary a comparison-group runner may
#: report -- exactly the five Issue #89 section 5 names, no sixth.
TASK_OUTCOMES: frozenset[str] = frozenset(
    {"COMPLETED_VERIFIED", "REFUSED", "RETAINED_INCOMPLETE", "FAILED", "TIMED_OUT"}
)

#: A reproduction receipt's own closed agreement vocabulary -- `INCOMPARABLE` is a genuine
#: third outcome, never silently folded into `DIVERGENT` (a reproducer that cannot compare a
#: result is not the same fact as one that compared it and found disagreement).
REPRODUCTION_AGREEMENTS: frozenset[str] = frozenset({"MATCH", "DIVERGENT", "INCOMPARABLE"})


__all__ = ["COMPARISON_GROUP_ROLES", "REPRODUCTION_AGREEMENTS", "TASK_OUTCOMES"]
