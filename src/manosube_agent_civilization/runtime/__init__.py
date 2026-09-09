"""Phase 15, Issue #64: Bounded Runtime Observation and trusted runtime provisioning.

```text
KERNEL_ELEMENT=NONE_RUNTIME_ADAPTER
```

This package is **not** a ninth Kernel element (the Kernel is fixed at eight:
``KERNEL_ELEMENT_COUNT=8``, ``ONE_KERNEL_ELEMENT_PER_PACKAGE=true``). It is an adapter layer,
exactly as Boot, CLI, Agent Runtime, Independent Verification, and Projection already are,
observing an explicit, already-real runtime target under a closed Observation Boundary through
one deterministic Runtime Observation Envelope and one replaceable Runtime Adapter boundary --
never a second State, Difference, Authority, Evidence, Store, or Closure owner. It additionally
ships the Phase-14-deferred trusted runtime bootstrap that provisions a
:class:`~manosube_agent_civilization.projection.ProjectionExecutionCapability` from canonical
Store/Boot state.

```python
result = observe_runtime_target(
    store,
    project_id=project_id,
    project_binding_id=project_binding_id,
    target_identity={
        "provider": "local",
        "deployment_id": "widget-service",
        "instance_identity": "widget-service-1",
        "project_binding_ref": {"kind": "project_binding", "id": project_binding_id},
        "deployment_fingerprint": "sha256:...",
    },
    boundary={...},
    adapter=my_runtime_adapter,
    observed_at="2026-01-01T00:00:00Z",
)
result["envelope"]  # the canonical, committed Runtime Observation Envelope
result["receipt"]   # RuntimeObservationReceipt

evidence = route_runtime_observation_to_evidence(
    store, result["receipt"], project_id, evidence_request
)

capability = bootstrap_projection_execution_capability(
    store,
    project_id=project_id,
    project_binding_id=project_binding_id,
    github_projection_grant_refs=[...],
    github_projection_grant_declaration_refs=[...],
)
```

See ``10_RUNTIME/RUNTIME_INDEX.md`` for the full contract set.
"""

from .bootstrap import bootstrap_projection_execution_capability
from .errors import (
    RuntimeAdapterError,
    RuntimeEnvelopeIntegrityError,
    RuntimeObservationError,
    RuntimeRequirementError,
)
from .evidence_handoff import route_runtime_observation_to_evidence
from .route import observe_runtime_target
from .types import (
    RECEIPT_STATUSES,
    RUNTIME_ADAPTER_TRANSPORT_OUTCOMES,
    RUNTIME_OBSERVATION_METHODS,
    RUNTIME_OBSERVATION_OUTCOMES,
    RuntimeAdapter,
    RuntimeObservationReceipt,
)

__all__ = [
    "RECEIPT_STATUSES",
    "RUNTIME_ADAPTER_TRANSPORT_OUTCOMES",
    "RUNTIME_OBSERVATION_METHODS",
    "RUNTIME_OBSERVATION_OUTCOMES",
    "RuntimeAdapter",
    "RuntimeAdapterError",
    "RuntimeEnvelopeIntegrityError",
    "RuntimeObservationError",
    "RuntimeObservationReceipt",
    "RuntimeRequirementError",
    "bootstrap_projection_execution_capability",
    "observe_runtime_target",
    "route_runtime_observation_to_evidence",
]
