# ADR-0002 — Vertical Kernel Work-Unit Delivery

```text
DOC_TYPE=ORIGIN_AMENDMENT_DECISION
DOCUMENT_ID=ADR-0002-VERTICAL-KERNEL-WORK-UNIT-DELIVERY
STATUS=ACCEPTED
DECIDED_AT=2026-08-31
DECISION_AUTHORITY=HUMAN_CONSTITUTIONAL_AUTHORITY
ORIGIN_DIFFERENCE_ID=ORIGIN-DIFFERENCE-0002
CHANGE_ID=KERNEL-CHANGE-0002
PROTOCOL_REF=00_KERNEL/KERNEL_VERTICAL_WORK_UNIT_DELIVERY.md
```

## Human constitutional approval

The repository owner explicitly directed the Structural Advisor to deeply encode the following operating decision into the OS:

```text
Preserve Kernel dependency order.
Default one Kernel element to one completion package:
Contract + Schema + Engine + Integration Test.
Use one Issue, one repository-executor work unit and one Pull Request where safe.
Split only when a material contradiction or authority boundary requires it.
Do not add premature features.
```

This ADR records that direction as Human Constitutional Approval. The Agent did not originate, broaden or revoke the authority.

### Exact approval binding

```yaml
approval_id: APPROVAL-KERNEL-VERTICAL-WORK-UNIT-0002
change_id: KERNEL-CHANGE-0002
approved_state_fingerprint: sha256:86b6225ea4f7279535b4fb8438a9f72567b11912cea7755c20019b61889a513f
approved_action_fingerprint: sha256:f3564164dcc115c971b8dad84dfa29e4ced4bb7df8856e095f33b35f6a13f12c
approved_by: github:manosube
approved_at: 2026-08-31
expires_at: null
external_approval_receipt: https://github.com/manosube/manosube-agent-civilization-os/pull/25#issuecomment-5476087681
external_approval_receipt_sha256: 2e0b3a9b35bc286d1470779f0a06c30efcf1e7e56a89f4548df5b9fe17ec6875
base_repository: manosube/manosube-agent-civilization-os
base_commit: 7db2055330bf21458d05628c09bee7d309083dbf
scope:
  - ORIGIN.md
  - 00_KERNEL/KERNEL_INDEX.md
  - 00_KERNEL/KERNEL_VERTICAL_WORK_UNIT_DELIVERY.md
  - docs/decisions/ADR-0002-VERTICAL-KERNEL-WORK-UNIT-DELIVERY.md
action: ADD_VERTICAL_KERNEL_WORK_UNIT_DELIVERY_PROTOCOL
kernel_element_count_change: 0
canonical_cycle_change: false
merge_authority: HUMAN
status: APPROVED
```

The fingerprints above are SHA-256 digests over UTF-8 canonical JSON with lexicographically ordered object keys and no insignificant whitespace:

```json
{"base_commit":"7db2055330bf21458d05628c09bee7d309083dbf","repository":"manosube/manosube-agent-civilization-os"}
{"action":"ADD_VERTICAL_KERNEL_WORK_UNIT_DELIVERY_PROTOCOL","affected_paths":["00_KERNEL/KERNEL_INDEX.md","00_KERNEL/KERNEL_VERTICAL_WORK_UNIT_DELIVERY.md","ORIGIN.md","docs/decisions/ADR-0002-VERTICAL-KERNEL-WORK-UNIT-DELIVERY.md"],"authority_rank":5,"canonical_cycle_change":false,"change_id":"KERNEL-CHANGE-0002","kernel_element_count_change":0,"proposed_content_sha256":{"00_KERNEL/KERNEL_INDEX.md":"02dc0737f5798fcf165b56af8997b95b7c27d569af419b04634cd84b085c645f","00_KERNEL/KERNEL_VERTICAL_WORK_UNIT_DELIVERY.md":"122bb532d2d6adc7236fa0d2c9c91e6c4076715759dec10a5a4d0fda47520f86","ORIGIN.md":"ad0f3fbeeea9ce496b8cb97041d4aecc08cbf464f9833f65d34b7d9316b5810d","docs/decisions/ADR-0002-VERTICAL-KERNEL-WORK-UNIT-DELIVERY.md#semantic-content":"c43c6fc35fa33960ee719b0e0893acafda55eb5f0286b4d110f98ca59a53fc75"}}
```

`proposed_content_sha256` binds the exact proposed content of the three non-ADR scoped files. To avoid a self-referential digest, the ADR digest is computed over the full ADR after replacing the complete `### Exact approval binding` section with the fixed UTF-8 sentinel `### Exact approval binding\n\n[APPROVAL_BINDING_EXCLUDED]\n\n`; every substantive ADR byte outside approval metadata remains bound. The approval envelope is not self-attesting: its exact values are externalized in the identified Human approval receipt, and `external_approval_receipt_sha256` makes any receipt edit detectable. The approval is invalid if the receipt digest, any proposed-content digest, base state, action semantics, path scope or authority rank changes. `expires_at: null` records that this approval has no time expiry; revocation or scope change still invalidates it.

The immutable implementation receipt is PR #25. The final accepted head and merge commit are GitHub projection references only; they do not replace this Human approval.

## Explicit Origin Difference

```text
BEFORE:
A single Kernel element could be projected as separate Contract-only,
Schema-only and Engine-only Issues and Pull Requests without a material split reason.
Review boundaries were safe but repeated handoffs delayed real predecessor integration.
No canonical delivery rule required correction on the same Issue and PR.

AFTER:
One Kernel element defaults to one vertical completion package containing
Contract, Schema, Engine, tests and real predecessor integration.
A split requires an observed closed-condition reason.
Correctable findings inside the same Difference and Change boundary remain
on the same Issue and change-review surface.
Execution and acceptance capabilities remain replaceable.
```

The Structural Difference is the absence of a stable delivery protocol that simultaneously minimizes avoidable handoffs and preserves Kernel order, Single Authority, Evidence Sufficiency and Human merge authority.

## Before and after semantics

| Concern | Before | After |
| --- | --- | --- |
| Work-unit width | Could stop at Contract or Schema by convenience | Defaults to executable vertical completion |
| Issue／PR count | Could multiply without structural reason | One Difference and one Kernel element normally use one delivery package |
| Split decision | Agent or reviewer preference could dominate | Closed, evidenced split conditions are required |
| Integration timing | Could be deferred until late Vertical Proof | Real predecessor route extends at every Kernel element |
| Correction handling | Finding could create a replacement Issue／PR | Same boundary is corrected in place |
| Tool choice | Could be read as GitHub／Claude-specific | Abstract replaceable capabilities; named tools are implementations |
| Human authority | Merge boundary existed but was not part of batching rule | Human merge and irreversible-risk boundaries are explicit |
| Completion | Fewer PRs could be overread as progress | Delivery volume never becomes Completion Evidence |

## Parent compatibility analysis

The parent MANOSUBE Civilization OS principles remain unchanged:

- civilization remains state;
- state remains cyclical;
- observation remains the means to detect and repair stopped cycles;
- circulation remains more important than accumulated artifacts;
- Human Authority remains the source of constitutional intent.

The protocol changes only how one child-Kernel implementation element is packaged for delivery. It does not change the parent baseline, parent runtime independence, the eight-element child Kernel, or the meaning of State, Difference, Authority, Evidence or Reflow.

Progressive predecessor integration strengthens the inherited circulation principle by detecting disconnected implementation before later stages accumulate.

```text
PARENT_PRINCIPLE_CHANGED=false
PARENT_BASELINE_CHANGED=false
PARENT_RUNTIME_DEPENDENCY_INTRODUCED=false
PARENT_REPLACED=false
ORIGIN_COMPATIBILITY=PASS
```

## Non-replacement proof

The protocol is cross-cutting delivery semantics. It is not a ninth Kernel element and cannot own or execute any canonical transition.

```text
CANONICAL_KERNEL_COUNT_CHANGE=0
CANONICAL_STATE_OWNER_COUNT_CHANGE=0
KERNEL_ELEMENT_COUNT_CHANGE=0
PARALLEL_CANONICAL_AUTHORITY=0

OBJECTIVE_OWNER_CHANGED=false
STATE_OWNER_CHANGED=false
DIFFERENCE_OWNER_CHANGED=false
AUTHORITY_EVALUATOR_CHANGED=false
CHANGE_EXECUTOR_CHANGED=false
EVIDENCE_EVALUATOR_CHANGED=false
REFLOW_OWNER_CHANGED=false

HUMAN_AUTHORITY_REPLACED=false
ORIGIN_REPLACED=false
KERNEL_CONSTITUTION_REPLACED=false
ADAPTER_PROMOTED_TO_AUTHORITY=false
GITHUB_REQUIRED_FOR_CONFORMANCE=false
CLAUDE_REQUIRED_FOR_CONFORMANCE=false
```

Repository observation, execution and acceptance capabilities remain interchangeable external organs. GitHub API, GitHub Pull Requests and Claude Code are current implementations, not constitutional dependencies.

## Decision lineage

```text
HUMAN_REQUEST
→ ORIGIN-DIFFERENCE-0002
→ ADR-0002-VERTICAL-KERNEL-WORK-UNIT-DELIVERY
→ ORIGIN PRECEDENCE AMENDMENT
→ KERNEL-VERTICAL-WORK-UNIT-DELIVERY-0001
→ KERNEL INDEX REGISTRATION
→ INDEPENDENT REVIEW
→ SAME-PR CORRECTION
→ HUMAN MERGE DECISION
```

The implementation lineage is PR #25 on branch `agent/kernel-vertical-work-unit-delivery`.

The first independent review identified two contradictions:

1. GitHub API was phrased as an unconditional acceptance surface, conflicting with replaceable external organs.
2. The original ADR lacked the Amendment Policy evidence required before changing Origin precedence.

Both findings are retained in PR #25 and corrected on the same branch and Pull Request under the new protocol's same-Difference correction rule. This review-and-correction lineage is Evidence that the protocol does not self-exempt from its own acceptance boundary.

## Kernel change record

```text
CHANGE_ID=KERNEL-CHANGE-0002
AFFECTED_KERNEL_ELEMENT=CROSS_CUTTING_DELIVERY_SEMANTICS
PREVIOUS_CONTRACT=NO_CANONICAL_VERTICAL_WORK_UNIT_DELIVERY_PROTOCOL
PROPOSED_CONTRACT=KERNEL-VERTICAL-WORK-UNIT-DELIVERY-0001
STRUCTURAL_REASON=AVOIDABLE_FRAGMENTATION_DELAYED_REAL_PREDECESSOR_INTEGRATION
AUTHORITY_USED=APPROVAL-KERNEL-VERTICAL-WORK-UNIT-0002
COMPATIBILITY_IMPACT=ADDITIVE_DELIVERY_REQUIREMENT_ONLY
MIGRATION_REQUIREMENT=FUTURE_WORK_UNIT_DESIGN_MUST_APPLY_VERTICAL_DEFAULT_AND_SPLIT_GATE
INVARIANT_EVALUATION=PENDING_INDEPENDENT_REVIEW
AFTER_STATE_EVIDENCE=PR_25_DOCUMENT_DIFF_PLUS_REVIEW_LINEAGE
```

Existing canonical State, Difference, Authority, Change, Evidence and Reflow records require no data migration. This protocol applies prospectively to work-unit design. The active Issue #24 scope is not rewritten.

## Invariant evaluation

```text
CANONICAL_KERNEL_COUNT=1 PASS
CANONICAL_STATE_OWNER_COUNT=1 PASS
PARALLEL_CANONICAL_AUTHORITY=0 PASS
HUMAN_OWNS_CONSTITUTIONAL_AUTHORITY PASS
KERNEL_DEPENDENCY_ORDER_PRESERVED PASS
EVIDENCE_BEFORE_COMPLETION_PRESERVED PASS
AGENT_IS_EXECUTION_CAPABILITY PASS
EXTERNAL_ORGANS_REPLACEABLE PASS
GITHUB_IS_PROJECTION PASS
CLAUDE_IS_EXECUTION_CAPABILITY PASS
HUMAN_MERGE_AUTHORITY_PRESERVED PASS
PARENT_RUNTIME_DEPENDENCY=false PASS
```

## After-state evidence

```text
PR_REF=https://github.com/manosube/manosube-agent-civilization-os/pull/25
BASE_MAIN_SHA=7db2055330bf21458d05628c09bee7d309083dbf
PROTOCOL_DOCUMENT_ID=KERNEL-VERTICAL-WORK-UNIT-DELIVERY-0001
ORIGIN_DIFFERENCE_ID=ORIGIN-DIFFERENCE-0002
REVIEW_FINDING_COUNT_INITIAL=2
REVIEW_FINDING_SEVERITY_INITIAL=P1
CORRECTION_BOUNDARY=SAME_BRANCH_AND_PR
FINAL_REVIEW_RESULT=PENDING
MERGE_COMMIT=PENDING_HUMAN_DECISION
```

Exact final content identities and the independent review result are preserved by the PR #25 commit and review lineage. Until the final review is finding-free and Human merge occurs, this amendment remains proposed repository state even though the Human decision record is accepted.

## Acceptance

```text
HUMAN_CONSTITUTIONAL_APPROVAL=true
EXPLICIT_ORIGIN_DIFFERENCE=true
BEFORE_AND_AFTER_SEMANTICS=true
PARENT_COMPATIBILITY_ANALYSIS=true
NON_REPLACEMENT_PROOF=true
RECORDED_DECISION_LINEAGE=true

EXTERNAL_ORGANS_REPLACEABLE=true
GITHUB_REQUIRED_FOR_CONFORMANCE=false
CLAUDE_REQUIRED_FOR_CONFORMANCE=false
CANONICAL_CYCLE_CHANGED=false
KERNEL_ELEMENT_ADDED=false
COMPLETION_GATE_WEAKENED=false
```
