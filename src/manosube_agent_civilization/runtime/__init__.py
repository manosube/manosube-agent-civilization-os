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

The trusted runtime bootstrap (Structural Review Round 3, P15-R3-F1):

```python
capability = bootstrap_projection_execution_capability(
    # An ordinary, public, frozen value naming WHICH world is in play. Constructing one is
    # unrestricted and confers nothing by itself -- see below.
    TrustedRuntimeRoot(store, project_id, project_binding_id),
    # The canonical, Store-committed, ACTIVE runtime_root_admission record admitting exactly
    # this project and this Project Binding.
    runtime_root_admission_ref={
        "kind": "runtime_root_admission",
        "id": runtime_root_admission_id_value,
    },
    # Supplied by the DEPLOYMENT/COMPOSITION boundary itself, from its own configuration --
    # never read from the Store being admitted, never derived from anything on the request
    # path, and never a constant baked into shipped source.
    trust_anchor_public_key_hex=deployment_configured_trust_anchor_public_key_hex,
    github_projection_grant_refs=[...],
    github_projection_grant_declaration_refs=[...],
)
```

**Possessing a ``TrustedRuntimeRoot`` grants nothing.** Round 1 shipped a public
``provision_trusted_runtime_root`` factory; Round 2 (P15-R2-F1) deleted it, correctly finding
that it relocated the trust decision rather than removing it, and left construction behind a
module-private sentinel. Round 3 (P15-R3-F1) found that sentinel to be a naming convention
rather than a control -- any caller able to import the module could read it -- and found the
framing itself wrong: while holding a root was *sufficient* to reach an adapter, "who may mint
one?" was a question no library-level trick could close.

The boundary therefore moved off the type. ``bootstrap_projection_execution_capability`` admits
a root **only** against a canonical ``runtime_root_admission`` record verified against an
externally supplied trust anchor, re-checked on every call, before any grant resolution and
before any authorization evaluation. Since the type is no longer a capability, its construction
is public again -- and Round 2's own mechanical facts still hold unchanged: the deleted factory
is not reintroduced under any name, no shipped function returns a ``TrustedRuntimeRoot``, and no
shipped module constructs one (all three still proved by an AST walk over the installed package
in ``tests/contract/runtime/test_runtime_static_conformance.py``).

Issuing, rotating, and revoking a deployment declaration (Structural Review Round 3,
P15-R3-F2) goes through one canonical committer, which commits the immutable record **and**
moves this target's own current-declaration pointer
(``semantic_state.runtime.claims[<target_key>]``) in a single atomic State transition:

```python
result = commit_runtime_deployment_declaration(
    store, project_id, declaration, committed_at="2026-09-09T00:00:00Z"
)
result["runtime_deployment_declaration_ref"]  # what a target_identity then references
```

Issuing **any** new declaration for the same target through this path -- a rotation
(``status="ACTIVE"``) or a revocation (``status="REVOKED"``) -- atomically supersedes whatever
the pointer named before, so a superseded declaration stops anchoring observations even though
its own record remains immutable, resolvable, signature-valid, and inside its own validity
window. That is what makes revocation genuinely effective rather than merely declared. This is
a canonical committer, not a fourth route: ``PUBLIC_RUNTIME_ENTRY_POINT_COUNT`` is still ``3``.

See ``10_RUNTIME/RUNTIME_CONTRACT.md`` §12 and ``10_RUNTIME/RUNTIME_INDEX.md`` for the full
contract set.
"""

from .bootstrap import TrustedRuntimeRoot, bootstrap_projection_execution_capability
from .deployment_registry import commit_runtime_deployment_declaration
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
    "commit_runtime_deployment_declaration",
    "observe_runtime_target",
    "route_runtime_observation_to_evidence",
]
