"""Phase 16, Issue #66: Multi-model replaceability and Phase 12 execution continuity.

```text
KERNEL_ELEMENT=NONE_MODEL_RUNTIME_ADAPTER
```

This package is **not** a ninth Kernel element (the Kernel is fixed at eight:
``KERNEL_ELEMENT_COUNT=8``, ``ONE_KERNEL_ELEMENT_PER_PACKAGE=true``). It is an adapter layer,
exactly as Boot, CLI, Agent Runtime, Independent Verification, Projection and Runtime already
are. It proves one thing and claims nothing else: **an Agent, a model, or a provider can be
replaced without losing Canonical State, Authority, Difference, Boundary, Evidence requirements,
or resumable work continuity.** The model and the provider are never a State, Authority,
Difference, Evidence, Change, Reflow, Binding, Boot, Runtime, or Closure owner here.

```python
# ---- AGENT A -------------------------------------------------------------------------------
agent_a = start_temporary_agent(store, project_id=..., project_binding_id=...)
opened = open_model_work_unit(
    store,
    agent_a,
    project_id=project_id,
    project_binding_id=project_binding_id,
    difference_ref={"kind": "difference", "id": difference_id},
    required_capability="PROPOSE_EVIDENCE_CANDIDATE",
    boundary_ref={"kind": "model_execution_boundary", "id": boundary_id},
    model_execution_grant_refs=[{"kind": "model_execution_grant", "id": grant_id}],
    opened_at="2026-01-01T00:00:00Z",
)
first = execute_model_work_unit(
    store,
    agent_a,
    project_id=project_id,
    project_binding_id=project_binding_id,
    model_work_unit_ref=opened["model_work_unit_ref"],
    adapter=adapter_x,
    executed_at="2026-01-01T00:01:00Z",
)
agent_a.release()  # the session ends here; nothing below reads anything it held

# ---- AGENT B -- a different process, a different Agent, a different Adapter ----------------
# No conversation handoff, no model memory, no provider session id: the ONLY thing that
# crosses the boundary is the Work Unit's own content address, resolved from the Store.
agent_b = start_temporary_agent(store, project_id=..., project_binding_id=...)
recovered = recover_model_execution_session(
    store,
    agent_b,
    project_id=project_id,
    project_binding_id=project_binding_id,
    model_work_unit_ref={"kind": "model_work_unit", "id": model_work_unit_id_value},
    recovered_at="2026-01-01T00:02:00Z",
)
second = execute_model_work_unit(
    store,
    agent_b,
    project_id=project_id,
    project_binding_id=project_binding_id,
    model_work_unit_ref=recovered["session_recovery_receipt"]["model_work_unit_ref"],
    adapter=adapter_y,  # a genuinely different Model Adapter
    executed_at="2026-01-01T00:03:00Z",
)
swap = record_model_swap(
    store,
    agent_b,
    project_id=project_id,
    project_binding_id=project_binding_id,
    model_work_unit_ref=recovered["session_recovery_receipt"]["model_work_unit_ref"],
    predecessor_execution_ref={
        "kind": "model_execution_envelope",
        "id": first["envelope"]["model_execution_envelope_id"],
    },
    successor_execution_ref={
        "kind": "model_execution_envelope",
        "id": second["envelope"]["model_execution_envelope_id"],
    },
    recorded_at="2026-01-01T00:04:00Z",
)

# ---- THE CANDIDATE REACHES THE EXISTING EVIDENCE OWNER, AS A CANDIDATE ---------------------
evidence = route_model_execution_to_evidence(
    store, second["receipt"], project_id, evidence_request
)
```

```text
MODEL_RUNTIME_OWNER_COUNT=1
PUBLIC_MODEL_RUNTIME_ENTRY_POINT_COUNT=5
SECOND_EXECUTION_CONTRACT=false
PROVIDER_SDK_DEPENDENCY_COUNT=0
LIVE_PROVIDER_CREDENTIAL_USE=false
REMOTE_COMMAND_EXECUTION=false
```

**Phase 12 is the execution contract, and this Phase does not touch it.** ``agent_runtime``'s
own public surface -- ``TemporaryAgent``, ``start_temporary_agent``, ``release`` -- is unchanged
by this delivery, and no second execution contract, contract record, contract schema, durable
agent identity, or Boot wrapper exists here. This package never imports ``boot_project``: it
reaches Boot only through Phase 12's own route, at exactly one literal call site.

**What a model may and may not do here.** Model output is an untrusted candidate. It may propose
observations or Evidence candidates; it can neither mutate Canonical State, mint Authority,
declare a Difference closed, commit Change, self-accept its own Evidence, nor widen its own
Boundary or capability -- and none of those is merely refused at runtime: ``adapter.py`` imports
no Store, Boot, Agent Runtime, Authority, Evidence, Difference or Change module at all, and the
route reads exactly three keys back out of an adapter's own result.

See ``11_MODEL_RUNTIME/MODEL_RUNTIME_CONTRACT.md`` and ``11_MODEL_RUNTIME/MODEL_RUNTIME_INDEX.md``
for the full contract set.
"""

from .adapter import FakeModelAdapter, RequestDerivedModelAdapter
from .errors import (
    ModelAdapterError,
    ModelRecordIntegrityError,
    ModelReleasedAgentError,
    ModelRuntimeAuthorityFreshnessError,
    ModelRuntimeError,
    ModelRuntimeRequirementError,
    ModelRuntimeStaleStateError,
)
from .evidence_handoff import route_model_execution_to_evidence
from .route import (
    execute_model_work_unit,
    open_model_work_unit,
    record_model_swap,
    recover_model_execution_session,
)
from .types import (
    MODEL_ADAPTER_OUTCOMES,
    MODEL_CANDIDATE_KINDS,
    MODEL_EXECUTION_CAPABILITIES,
    MODEL_EXECUTION_OUTCOMES,
    RECEIPT_STATUSES,
    ModelAdapter,
    ModelExecutionReceipt,
)

#: The complete public entry-point count this package declares -- four routes
#: (:mod:`~manosube_agent_civilization.model_runtime.route`) plus one Evidence hand-off
#: (:mod:`~manosube_agent_civilization.model_runtime.evidence_handoff`). Stated as a value so a
#: fifth route cannot appear without this number moving, exactly as
#: ``PUBLIC_RUNTIME_ENTRY_POINT_COUNT`` and ``PUBLIC_AGENT_START_ENTRY_POINT_COUNT`` already are
#: for their own packages.
PUBLIC_MODEL_RUNTIME_ENTRY_POINT_COUNT = 5

__all__ = [
    "MODEL_ADAPTER_OUTCOMES",
    "MODEL_CANDIDATE_KINDS",
    "MODEL_EXECUTION_CAPABILITIES",
    "MODEL_EXECUTION_OUTCOMES",
    "PUBLIC_MODEL_RUNTIME_ENTRY_POINT_COUNT",
    "RECEIPT_STATUSES",
    "FakeModelAdapter",
    "ModelAdapter",
    "ModelAdapterError",
    "ModelExecutionReceipt",
    "ModelRecordIntegrityError",
    "ModelReleasedAgentError",
    "ModelRuntimeAuthorityFreshnessError",
    "ModelRuntimeError",
    "ModelRuntimeRequirementError",
    "ModelRuntimeStaleStateError",
    "RequestDerivedModelAdapter",
    "execute_model_work_unit",
    "open_model_work_unit",
    "record_model_swap",
    "recover_model_execution_session",
    "route_model_execution_to_evidence",
]
