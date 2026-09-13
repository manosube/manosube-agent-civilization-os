"""Phase 19, Issue #77: Multi-Agent Dynamic Execution.

```text
KERNEL_ELEMENT=NONE_MULTI_AGENT_ORCHESTRATION_ADAPTER
```

This package is **not** a ninth Kernel element (the Kernel is fixed at eight:
``KERNEL_ELEMENT_COUNT=8``, ``ONE_KERNEL_ELEMENT_PER_PACKAGE=true``). It is a bounded
orchestration layer over the existing Phase 12 Temporary Agent lifecycle and Phase 16 Model
Runtime execution contract, exactly as Boot, CLI, Agent Runtime, Independent Verification,
Projection, Runtime, Model Runtime, URL Boot and Change Executor already are. It proves one
thing and claims nothing else: **the canonical Difference and its required capabilities can
select 1, 2 or N temporary Agents, execute them independently with preserved provenance and
preserved disagreement, and release every one of them -- without minting a permanent Agent
organization, Authority, canonical State, Observation, or Evidence sufficiency.**

```python
opened = open_dynamic_execution_plan(
    store, agent,
    project_id=project_id, project_binding_id=project_binding_id,
    difference_ref={"kind": "difference", "id": difference_id},
    boundary_ref={"kind": "model_execution_boundary", "id": boundary_id},
    model_execution_grant_refs=[{"kind": "model_execution_grant", "id": grant_id}],
    adapter_identity={"adapter": "fake_model_adapter", "version": "0.1"},
    opened_at="2026-01-01T00:00:00Z",
    expires_at="2026-01-01T01:00:00Z",
)
executed = execute_dynamic_execution_plan(
    store, agent,
    project_id=project_id, project_binding_id=project_binding_id,
    plan_ref=opened["plan_ref"],
    model_adapter_factory=lambda: FakeModelAdapter(),
    executed_at="2026-01-01T00:05:00Z",
)
handed_off = route_orchestration_to_evidence(
    store, agent,
    project_id=project_id, project_binding_id=project_binding_id,
    plan_ref=opened["plan_ref"],
    evidence_request_template=evidence_request,
    completed_at="2026-01-01T00:06:00Z",
)
```

```text
MULTI_AGENT_OWNER_COUNT=1
PUBLIC_MULTI_AGENT_ENTRY_POINT_COUNT=3
SECOND_AGENT_LIFECYCLE_OWNER=false
PERMANENT_AGENT_ORGANIZATION=false
CONSENSUS_EQUALS_TRUTH=false
CANONICAL_STATE_OWNER_COUNT=1
CAPABILITY_VOCABULARY_SIZE=1
```

**Phase 12 is the Temporary Agent lifecycle, and this Phase does not touch it.**
``agent_runtime``'s own public surface is unchanged by this delivery, and no second Agent
lifecycle owner, persistent Agent memory, permanent Agent registry, standing organization,
hierarchy or hidden delegation graph exists here. Every Agent this package ever constructs is
temporary, stateless, non-authoritative and released before this package's own terminal receipt
can exist (P19-C3/P19-C8).

**Phase 16 is the execution contract, and this Phase reuses it end to end.**
``open_dynamic_execution_plan`` opens exactly one shared Model Work Unit per plan through the
existing :func:`~manosube_agent_civilization.model_runtime.open_model_work_unit` (the existing
Authority evaluator runs there, unchanged, exactly once); ``execute_dynamic_execution_plan``
executes every slot of that plan through the existing
:func:`~manosube_agent_civilization.model_runtime.execute_model_work_unit`. This package never
evaluates Authority itself and never mints a Change.

**Consensus is never truth.** A conflict set (P19-C6) preserves every disagreement, every
missing/failed/timed-out/cancelled attempt, and full membership -- no majority vote, confidence
average, or last-writer-wins ever collapses it. An Evidence-aggregation input (P19-C7) is
submitted to the existing Evidence/Independent Verification owners; it never marks anything
sufficient itself.

See ``14_MULTI_AGENT/MULTI_AGENT_CONTRACT.md`` and ``14_MULTI_AGENT/MULTI_AGENT_INDEX.md`` for
the full contract set.
"""

from .errors import (
    MultiAgentAuthorityFreshnessError,
    MultiAgentError,
    MultiAgentOverLimitError,
    MultiAgentRecordIntegrityError,
    MultiAgentReleasedAgentError,
    MultiAgentReleaseIncompleteError,
    MultiAgentReplayConflictError,
    MultiAgentRequirementError,
    MultiAgentSelectionError,
    MultiAgentStaleStateError,
    MultiAgentUnsupportedRequirementError,
)
from .evidence_handoff import route_orchestration_to_evidence
from .route import execute_dynamic_execution_plan, open_dynamic_execution_plan
from .selection import MAX_AGENT_SLOTS, RISK_CLASS_TO_SLOT_COUNT, select_agent_slots
from .types import (
    ABSENT_MEMBER_OUTCOMES,
    ACCEPTED_SLOT_OUTCOME,
    CONFLICT_MEMBER_KINDS,
    MULTI_AGENT_CAPABILITIES,
    MULTI_AGENT_SLOT_OUTCOMES,
    ORCHESTRATION_OUTCOMES,
    RELEASE_STATUSES,
)

#: The complete public entry-point count this package declares -- two routes
#: (:mod:`~manosube_agent_civilization.multi_agent.route`) plus one Evidence hand-off
#: (:mod:`~manosube_agent_civilization.multi_agent.evidence_handoff`). Stated as a value so a
#: fourth route cannot appear without this number moving.
PUBLIC_MULTI_AGENT_ENTRY_POINT_COUNT = 3

__all__ = [
    "ABSENT_MEMBER_OUTCOMES",
    "ACCEPTED_SLOT_OUTCOME",
    "CONFLICT_MEMBER_KINDS",
    "MAX_AGENT_SLOTS",
    "MULTI_AGENT_CAPABILITIES",
    "MULTI_AGENT_SLOT_OUTCOMES",
    "ORCHESTRATION_OUTCOMES",
    "PUBLIC_MULTI_AGENT_ENTRY_POINT_COUNT",
    "RELEASE_STATUSES",
    "RISK_CLASS_TO_SLOT_COUNT",
    "MultiAgentAuthorityFreshnessError",
    "MultiAgentError",
    "MultiAgentOverLimitError",
    "MultiAgentRecordIntegrityError",
    "MultiAgentReleaseIncompleteError",
    "MultiAgentReleasedAgentError",
    "MultiAgentReplayConflictError",
    "MultiAgentRequirementError",
    "MultiAgentSelectionError",
    "MultiAgentStaleStateError",
    "MultiAgentUnsupportedRequirementError",
    "execute_dynamic_execution_plan",
    "open_dynamic_execution_plan",
    "route_orchestration_to_evidence",
    "select_agent_slots",
]
