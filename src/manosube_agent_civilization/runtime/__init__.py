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
        # the canonical, already-committed record this target's own declared
        # deployment_fingerprint must match (Round 1, P15-R1-F6) -- and which must also be
        # ACTIVE, name the Human Authority this call's own Boot restores, and carry that
        # Authority's own genuine Ed25519 signature (Round 2, P15-R2-F2)
        "deployment_declaration_ref": {
            "kind": "runtime_deployment_declaration",
            "id": runtime_deployment_declaration_id_value,
        },
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
```

``bootstrap_projection_execution_capability(trusted_runtime_root, *, github_projection_grant_
refs, github_projection_grant_declaration_refs)`` is deliberately **not** shown as runnable
example code here. Structural Review Round 2 (P15-R2-F1) deleted the public
``provision_trusted_runtime_root`` factory Round 1 had shipped: it accepted exactly the
caller-controlled Store/Project/Binding tuple the correction existed to stop an untrusted
surface from selecting, so moving those three arguments one call earlier changed the API's
shape rather than control of the trust decision. No function anywhere in this shipped package
now takes a caller-supplied store/project/binding and returns a
:class:`~manosube_agent_civilization.runtime.bootstrap.TrustedRuntimeRoot`, and no shipped
module constructs one at all (proved by an AST walk over the installed package in
``tests/contract/runtime/test_runtime_static_conformance.py``).

The capability route therefore has, in this Phase, **no production-legitimate way to obtain its
own first argument**; it is exercised only by tests, through an explicitly test-confined issuer
(``tests/fixtures/runtime_world.py``'s own ``test_only_trusted_runtime_root``), pending a future,
separately authorized Phase's real deployment composition boundary. Stated exactly: that proves
*no shipped minting path exists*, not that a live path resists an attacker at runtime -- there
is no live path yet to resist one. See ``10_RUNTIME/RUNTIME_CONTRACT.md`` §11.

See ``10_RUNTIME/RUNTIME_INDEX.md`` for the full contract set.
"""

from .bootstrap import TrustedRuntimeRoot, bootstrap_projection_execution_capability
from .errors import (
    RuntimeAdapterError,
    RuntimeAuthorityFreshnessError,
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
    "RuntimeAuthorityFreshnessError",
    "RuntimeEnvelopeIntegrityError",
    "RuntimeObservationError",
    "RuntimeObservationReceipt",
    "RuntimeRequirementError",
    "TrustedRuntimeRoot",
    "bootstrap_projection_execution_capability",
    "observe_runtime_target",
    "route_runtime_observation_to_evidence",
]
