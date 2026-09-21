"""Closed vocabularies for the v1.0 Acceptance package (Issue #92,
`ADOPT_PHASE_22_V1_0_ACCEPTANCE`).

`GATE_22_PREDICATES` is the canonical roadmap's own twelve-predicate Gate 22 (Issue #92
section 4 / `02_CANONICAL_ROADMAP.md` section 25), preserved exactly -- this package never
adds, removes or renames a predicate.
"""

from __future__ import annotations

#: The twelve canonical Gate 22 predicates, in the exact order and spelling Issue #92
#: section 4 states them. No thirteenth predicate may be inferred, and none of these twelve
#: may be dropped.
GATE_22_PREDICATES: tuple[str, ...] = (
    "OBJECTIVE_CONTINUITY_PROVEN",
    "AGENT_REPLACEMENT_SAFE",
    "SESSION_LOSS_SAFE",
    "GITHUB_INDEPENDENCE",
    "RUNTIME_VERIFICATION",
    "AUTHORITY_ENFORCEMENT",
    "EVIDENCE_ONLY_COMPLETION",
    "STATE_LINEAGE_PRESERVATION",
    "LONG_RUNNING_PROOF_PASS",
    "COMPARATIVE_BENCHMARK_PASS",
    "THIRD_PARTY_REPRODUCTION_CONFIRMED",
    "ALL_V1_0_BLOCKING_DIFFERENCES_CLOSED",
)

#: A predicate's own three-valued mechanical verdict. `UNKNOWN` is a genuine third state
#: (Issue #92: `UNKNOWN_EQUALS_FALSE=false`, `UNKNOWN_EQUALS_TRUE=false`) -- e.g. the owning
#: evidence exists but its own recorded disposition has not yet been made by its Human
#: Authority, which this package must never infer on SHUKOU's behalf.
PREDICATE_VERDICTS: frozenset[str] = frozenset({"PASS", "FAIL", "UNKNOWN"})

#: A candidate v1.0-blocking Difference's own disposition, mechanically derived from
#: `06_DEFERRED_DIFFERENCES.md`'s own recorded `CLASSIFICATION`/`CURRENT_PHASE_BLOCKING_EFFECT`
#: fields (see `deferred_differences_register.py` and `blocking_differences.py`).
#: `REQUIRES_HUMAN_AUTHORITY_DISPOSITION` is used whenever the record's own already-recorded deadline
#: or milestone appears to have already elapsed without a recorded disposition -- this package
#: never resolves that gap itself (`06_DEFERRED_DIFFERENCES.md` section 1: "Missing placement
#: or deadline information must be expressed as unresolved Human decision. It must not be
#: inferred by an Agent").
DIFFERENCE_DISPOSITIONS: frozenset[str] = frozenset(
    {"NON_BLOCKING", "REQUIRES_HUMAN_AUTHORITY_DISPOSITION", "REGISTER_CONTENT_CONTRADICTION"}
)

#: Classification rows from `06_DEFERRED_DIFFERENCES.md` section 2 whose own "May block
#: current Phase?" column reads unconditional "No" -- a record carrying one of these
#: classifications is always `NON_BLOCKING` regardless of its `CURRENT_PHASE_BLOCKING_EFFECT`
#: field content.
UNCONDITIONALLY_NON_BLOCKING_CLASSIFICATIONS: frozenset[str] = frozenset(
    {"DEFERRED_DESIGN_CANDIDATE", "CANCELLED_BY_HUMAN_DECISION", "CLOSED_WITH_EVIDENCE"}
)

#: Classification rows whose own "May block current Phase?" column is conditional ("Only at
#: its recorded deadline" / "Only when that owner becomes current" / "Only under explicit
#: scheduling decision") -- for these, disposition depends on the record's own
#: `CURRENT_PHASE_BLOCKING_EFFECT` literal value and recorded deadlines.
CONDITIONALLY_BLOCKING_CLASSIFICATIONS: frozenset[str] = frozenset(
    {"DEFERRED_REMAINING_DIFFERENCE", "FUTURE_OWNER_OBLIGATION", "FOLLOW_ON_DIFFERENCE"}
)


__all__ = [
    "CONDITIONALLY_BLOCKING_CLASSIFICATIONS",
    "DIFFERENCE_DISPOSITIONS",
    "GATE_22_PREDICATES",
    "PREDICATE_VERDICTS",
    "UNCONDITIONALLY_NON_BLOCKING_CLASSIFICATIONS",
]
