# ADR-0026 — Vertical Progression over Local Exhaustion

```text
STATUS=PROPOSED
DECISION_DATE=2026-09-03
HUMAN_CONSTITUTIONAL_AUTHORITY=SHUKOU
CANONICAL_CYCLE_CHANGED=false
COMPLETION_GATE_WEAKENED=false
```

## Context

Phase 3 proved that strong local validation can expand into an unbounded second objective:
defending every possible input and validator path before extending the canonical route. That work
can improve a component while delaying the only v0.1 proof that integrates all components.

The governing Objective remains one natural cycle:

```text
OBJECTIVE → STATE → OBSERVATION → DIFFERENCE → AUTHORITY → CHANGE
→ RE-OBSERVATION → EVIDENCE → REFLOW → NEW STATE
```

## Decision

The Kernel now distinguishes required Phase correctness from unbounded local hardening.

A Phase exits when its owned capability is proven, its real predecessor is connected, it produces
the next owner's canonical input, and no current-Phase blocker remains. Additional hardening is
classified and preserved as a non-claim, follow-on Difference, or future-owner obligation.

The following are not implicit Phase gates:

- arbitrary-input totality;
- exhaustion of possible mutations;
- validator correctness outside the current owner;
- implementation of future Phase semantics;
- absence of all possible future review findings.

This does not authorize known route defects. Authority bypasses, identity corruption, raw
exceptions on the public route, silent acceptance, duplicate canonical ownership, and failure to
produce the next owner's input remain blockers.

## Consequences

```text
VERTICAL_ROUTE_EXTENSION_IS_THE_DEFAULT=true
LOCAL_HARDENING_MAY_CONTINUE_WITHOUT_BOUND=false
DEFERRED_OBLIGATIONS_PRESERVED=true
CURRENT_ROUTE_BLOCKERS_MUST_CLOSE=true
PHASE_EXIT_REQUIRES_NEXT_OWNER_INPUT=true
```

This amendment narrows where a proof obligation belongs. It does not weaken Authority, Evidence,
Closure, or Natural Route requirements.
