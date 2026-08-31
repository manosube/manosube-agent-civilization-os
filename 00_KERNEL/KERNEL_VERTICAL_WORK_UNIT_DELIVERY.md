# Kernel Vertical Work-Unit Delivery Protocol

```text
DOC_TYPE=KERNEL_DELIVERY_PROTOCOL
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=KERNEL-VERTICAL-WORK-UNIT-DELIVERY-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
CONSTITUTIONAL_AUTHORITY=HUMAN
CANONICAL_KERNEL_ELEMENT_ADDED=false
CANONICAL_CYCLE_CHANGED=false
COMPLETION_GATE_WEAKENED=false
```

---

## 1. Purpose

This protocol governs how implementation work is packaged while constructing or extending the single MANOSUBE Kernel.

Its purpose is to minimize avoidable handoffs, Issues, branches, Pull Requests and review latency without reversing Kernel dependency order, merging canonical responsibilities, weakening Evidence, or inflating Completion.

```text
FASTEST SAFE DELIVERY
=
PRESERVED DEPENDENCY ORDER
+ VERTICAL WORK UNIT
+ SINGLE CANONICAL OWNER
+ INCREMENTAL INTEGRATION PROOF
+ HUMAN REVIEW AT THE MERGE BOUNDARY
```

Speed is an operational objective subordinate to Objective continuity, Authority, Evidence sufficiency, Single Authority and Completion Semantics.

---

## 2. Default Work-Unit Shape

For one canonical Kernel element, the default implementation unit MUST include every layer needed to make that element executable and connected:

```text
CONTRACT
+ SCHEMA
+ ENGINE
+ UNIT TEST
+ CONTRACT TEST
+ PREDECESSOR INTEGRATION TEST
+ VALIDATION EVIDENCE
=
ONE VERTICAL COMPLETION PACKAGE
```

The default external projection is capability-neutral:

```text
ONE STRUCTURAL DIFFERENCE
→ ONE WORK-ITEM / DIFFERENCE PROJECTION
→ ONE IMPLEMENTATION LINEAGE
→ ONE CHANGE-REVIEW / ACCEPTANCE SURFACE
→ ONE HUMAN ACCEPTANCE DECISION
```

An Issue, branch and Pull Request are interchangeable implementations of those capabilities, not mandatory Kernel organs.

A Contract-only, Schema-only or Engine-only work unit is exceptional. It MUST NOT be chosen merely because smaller Pull Requests are easier to produce.

---

## 3. Dependency Order Is Immutable

Batching changes the width of a work unit, not Kernel order.

```text
DIFFERENCE
→ AUTHORITY
→ CHANGE
→ EVIDENCE
→ REFLOW
→ VERTICAL PROOF
```

An Agent MUST NOT accelerate delivery by:

- implementing Change before Authority semantics are executable;
- executing Change before an Authority decision;
- implementing Closure before Evidence Sufficiency;
- treating storage lineage as completed Reflow;
- building Boot, CLI, GitHub, Runtime or Agent adapters before the v0.1 Kernel natural cycle;
- weakening an earlier contract to make a later implementation pass.

```text
BATCHING_ALLOWED=true
DEPENDENCY_REVERSAL_ALLOWED=false
```

---

## 4. Progressive Vertical Proof

Every completed Kernel-element package MUST extend the real predecessor route by one canonical boundary.

```text
STATE
→ OBSERVATION
→ DIFFERENCE
→ AUTHORITY
→ CHANGE
→ RE-OBSERVATION
→ EVIDENCE
→ REFLOW
→ NEW STATE
```

Examples:

```text
Difference package:
State → Observation → Difference

Authority package:
State → Observation → Difference → Authority

Change package:
State → Observation → Difference → Authority → Change

Evidence package:
... → Change → Re-observation → Evidence

Reflow package:
... → Evidence → Reflow → New State
```

A package MUST use the real canonical predecessor owner. A hand-built substitute artifact may support focused tests but MUST NOT satisfy the required predecessor integration proof.

---

## 5. Permitted Split Conditions

A vertical package MAY be split only when at least one material condition is observed:

```text
CONSTITUTIONAL_DECISION_REQUIRED
UNRESOLVED_CONTRACT_CONTRADICTION
SCHEMA_MIGRATION_REQUIRED
SECURITY_BOUNDARY_CHANGE
IRREVERSIBLE_RISK
EXTERNAL_AUTHORITY_BLOCK
REVIEWABLE_SIZE_EXCEEDS_SAFE_VALIDATION_BOUNDARY
INDEPENDENT_PROOF_REQUIRES_SEPARATE_ENVIRONMENT
```

Every split MUST record:

```text
SPLIT_REASON
OBSERVED_EVIDENCE
BOUNDARY_OF_EACH_CHILD_UNIT
OWNER_COUNT
DEPENDENCY_ORDER
RECOMBINATION_GATE
IMPACT_ON_NATURAL_ROUTE
```

Convenience, Agent preference, context-window anxiety, anticipated review style, or an arbitrary line-count limit is not sufficient evidence for a split.

If no permitted split condition is observed:

```text
DEFAULT_DECISION=KEEP_VERTICAL_PACKAGE
```

---

## 6. Capability Selection

The Structural Advisor selects the execution surface from the actual work shape.

```text
REPOSITORY OBSERVATION / ACCEPTANCE CAPABILITY
= canonical repository observation
+ work-item / change-review / receipt inspection
+ bounded metadata or document projection
+ independent acceptance review

REPOSITORY EXECUTION CAPABILITY
= multi-file implementation
+ isolated change-line work
+ test execution
+ build and static analysis
+ self-review
+ change-review preparation
```

GitHub API and GitHub Pull Requests are one interchangeable implementation of the observation／acceptance capability. Claude Code or an equivalent repository executor is one interchangeable implementation of the execution capability. Git, another version-control surface, a local repository, or a future Adapter MAY provide equivalent capabilities when it preserves the same identity, Authority, Evidence and review semantics.

No named provider, API, version-control product, model or Agent is required for protocol conformance.

Selection is not a permanent Agent role and grants no additional Authority.

```text
TOOL_SELECTED
!= AUTHORITY_GRANTED

AGENT_CAPABLE
!= CHANGE_AUTHORIZED
```

For a non-trivial executable package, the preferred route is one complete repository-executor instruction covering observation, implementation, validation, self-review and change-review preparation. An independent repository observation／acceptance capability MUST inspect the result. In the current repository, GitHub API implements that capability; it remains replaceable and owns no canonical State, Authority or Completion semantics.

Merge, release, production deployment, constitutional weakening and irreversible risk remain subject to their explicit Human Authority boundaries.

---

## 7. Work-Item / Difference-Projection Requirements

Before implementation, the replaceable work-item / Difference-projection capability MUST define:

```text
CURRENT STATE
TARGET STATE
STRUCTURAL DIFFERENCE
CANONICAL INPUT
CANONICAL OUTPUT
SINGLE OWNER
IN-SCOPE CONTRACT / SCHEMA / ENGINE
PREDECESSOR ROUTE
AUTHORITY BOUNDARY
PROHIBITED OVERREACH
TEST MATRIX
ACCEPTANCE GATE
EXPLICIT NON-CLAIMS
CLOSURE MEANING
```

The projection MUST be sufficient for one executor to proceed from the bound repository state through a focused change-review / acceptance surface without repeated design handoffs.

A GitHub Issue is one interchangeable projection of the Difference. Its number is never the canonical Difference identity, and the absence of an Issue object does not make an equivalent work-item projection nonconforming.

---

## 8. Change-Review / Acceptance Boundary

One vertical package SHOULD produce one focused change-review / acceptance surface. A Pull Request is one interchangeable implementation.

That surface MUST report exact:

```text
BASE STATE IDENTITY
PROPOSED STATE IDENTITY
CHANGED FILES
OWNER COUNT
SCHEMA / TEST COUNTS
VALIDATION COMMANDS AND RETURN CODES
PREDECESSOR INTEGRATION RESULT
UNEXPECTED CHANGE COUNT
RESPONSIBILITY OVERREACH
EXPLICIT NON-CLAIMS
REMAINING DIFFERENCES
```

A change-review surface MUST NOT be enlarged with later Kernel elements or adapters merely to reduce future review-object count.

```text
ONE KERNEL ELEMENT PER PACKAGE=true
MULTIPLE LAYERS OF SAME ELEMENT=true
MULTIPLE FUTURE ELEMENTS PER PACKAGE=false
```

---

## 9. Independent Acceptance

Executor self-review is required but not sufficient.

For this protocol, `Structural Advisor` means the acceptance-review role, not a product name or permission label. Independence is conforming only when the acceptance observation lineage is distinct from the execution lineage and the acceptance reviewer did not author the proposed repository content under review.

```text
EXECUTION_LINEAGE_ID != ACCEPTANCE_LINEAGE_ID
ACCEPTANCE_REVIEWER_AUTHORED_PROPOSED_CONTENT=false
EXECUTOR_SELF_REVIEW_AS_ACCEPTANCE=false
```

The execution and acceptance capabilities MAY be supplied by the same vendor or application only when their agent/session/action lineages are separately identifiable and the acceptance lineage receives the repository result as an independent observation. A Human who directly performs the acceptance inspection also satisfies the distinct acceptance boundary. A renamed executor self-review does not.

The acceptance evidence MUST record both lineage identities, the reviewed proposed-state identity and the independence result. If distinct lineage cannot be evidenced, acceptance fails closed.

Before Human acceptance, the Structural Advisor MUST independently inspect:

- exact base and proposed-state identity;
- changed-file boundary;
- single-owner preservation;
- contract／schema／engine consistency;
- real predecessor integration;
- invalid and negative routes;
- test and build evidence;
- absence of Completion inflation;
- remaining Differences.

The Structural Advisor MAY request a correction on the same implementation lineage and change-review surface. A correctable finding SHOULD NOT automatically create a new work item or replacement review surface.

```text
SAME_DIFFERENCE
+ SAME_CHANGE_BOUNDARY
+ CORRECTABLE_FINDING
→ SAME_WORK_ITEM_AND_REVIEW_SURFACE_CORRECTION
```

A new work item is required only when a distinct Structural Difference, authority boundary or constitutional decision is discovered. GitHub Issues and Pull Requests remain permitted current-repository implementations.

---

## 10. No Premature Expansion

Until Kernel v0.1 natural-cycle acceptance passes, the following are outside the active delivery route:

```text
BOOT
CLI
TEMPORARY AGENT
INDEPENDENT AGENT VERIFICATION
GITHUB ADAPTER
RUNTIME ADAPTER
MULTI-MODEL
URL READ-ONLY
AUTONOMOUS CHANGE
MULTI-AGENT
```

Their directories, placeholders and speculative abstractions MUST NOT be added merely to appear complete.

---

## 11. Completion Boundary

Batching does not alter Completion Semantics.

```text
CONTRACT PRESENT
!= ENGINE IMPLEMENTED

ENGINE IMPLEMENTED
!= PREDECESSOR CONNECTED

TEST PASS
!= NATURAL ROUTE PASS

PULL REQUEST MERGED
!= DIFFERENCE CLOSED

FEWER PULL REQUESTS
!= MORE COMPLETE
```

A vertical package is complete only when its own Acceptance Gate passes. A Kernel element being complete does not imply Kernel v0.1 is complete.

---

## 12. Required Decision Algorithm

Before creating or splitting work, the Structural Advisor MUST apply:

```text
1. Identify the current Structural Difference.
2. Identify the next canonical Kernel element only.
3. Determine all Contract, Schema, Engine and Integration layers required
   to make that element executable.
4. Check whether a permitted split condition is evidenced.
5. If no split condition exists, keep one vertical completion package.
6. Select the execution capability appropriate to the package.
7. Preserve Human merge and irreversible-risk boundaries.
8. Extend the predecessor natural route by exactly one Kernel boundary.
9. Independently inspect the resulting change through the replaceable repository change-review / acceptance capability; a Pull Request is one interchangeable implementation.
10. Reflow the observed result; do not infer Completion from work volume.
```

---

## 13. Minimum Conformance

```text
ONE_KERNEL_ELEMENT_PER_PACKAGE=true
CONTRACT_SCHEMA_ENGINE_INTEGRATION_DEFAULT=true
DEPENDENCY_ORDER_PRESERVED=true
PERMITTED_SPLIT_CONDITION_REQUIRED=true
SPLIT_REASON_EVIDENCED=true
PREDECESSOR_OWNER_REAL=true
NATURAL_ROUTE_EXTENDED_INCREMENTALLY=true
TOOL_SELECTION_NE_AUTHORITY=true
HUMAN_MERGE_BOUNDARY_PRESERVED=true
SAME_DIFFERENCE_CORRECTED_IN_PLACE=true
ACCEPTANCE_LINEAGE_DISTINCT=true
EXECUTOR_SELF_REVIEW_AS_ACCEPTANCE=false
PREMATURE_ADAPTER_EXPANSION=false
COMPLETION_INFLATION=false
```

---

## 14. Current v0.1 Application

After the active Difference Engine package, the default route is:

```text
AUTHORITY
= Contract + Schema + Engine + predecessor integration

CHANGE
= Contract + Schema + Engine + predecessor integration

EVIDENCE
= Contract + Schema + Engine + predecessor integration

REFLOW
= Contract + Schema + Engine + predecessor integration

MINIMAL FIXTURE BINDING
→ ONE FULL NATURAL CYCLE
→ CRASH / REPLAY / SESSION-LOSS VERTICAL PROOF
→ v0.1.0
```

This route may change only through observed Difference and applicable Authority. It MUST NOT change merely because an Agent prefers a different implementation order.
