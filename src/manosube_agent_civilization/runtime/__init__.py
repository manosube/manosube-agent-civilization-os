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

The trusted runtime bootstrap, in one owned composition step that *returns* the request-facing
operation already bound to its world (Structural Review Round 5, P15-R5-F1):

```python
# ---- TRUSTED DEPLOYMENT COMPOSITION -- runs once, before any request boundary exists. -------
# This is the only place a raw trust anchor is ever named, and the only shipped path to a
# working request-facing bootstrap at all. It owns the Store handle, the Project, the Project
# Binding, the root-admission selection, and the configured anchor -- and closes over every one
# of them before returning.
bootstrap = compose_trusted_runtime_deployment_authority(
    store,
    project_id=project_id,
    project_binding_id=project_binding_id,
    # Must be the admission this Project Binding's own chain pointer CURRENTLY names -- a
    # rotated or revoked one cannot be replayed through its own still-resolvable reference.
    runtime_root_admission_ref={
        "kind": "runtime_root_admission",
        "id": runtime_root_admission_id_value,
    },
    # Deployment configuration. Never read from the Store being admitted, never derived from
    # anything on the request path, never a constant baked into shipped source.
    trust_anchor_public_key_hex=deployment_configured_trust_anchor_public_key_hex,
)

# ---- REQUEST-FACING BOOTSTRAP -- the returned callable itself. -------------------------------
# Its signature carries ONLY these two operation-scoped keyword arguments. There is no
# deployment_authority / store / project_id / project_binding_id / runtime_root_admission_ref /
# trust_anchor_public_key_hex parameter, and no object to substitute in place of one either:
# the world lives in this callable's own closure, written once by the composition call above.
# Every call additionally rechecks, freshly, that the admission it was composed against is still
# this Project Binding's own current one (P15-R5-F2).
capability = bootstrap(
    github_projection_grant_refs=[...],
    github_projection_grant_declaration_refs=[...],
)
```

**Why the shape.** Round 1 shipped a public ``provision_trusted_runtime_root`` factory; Round 2
(P15-R2-F1) deleted it; Round 3 (P15-R3-F1) made possession of a trust root confer nothing and
required a canonical, anchor-signed ``runtime_root_admission`` on every call. Round 4 found that
the same defect had been *moved* rather than closed: the anchor and the admission reference were
still **parameters of the request-facing call**, so a caller could present a complete, internally
self-consistent alternate world together with the matching attacker anchor and pass every check;
its correction was an ownership boundary carried by an opaque ``RuntimeDeploymentAuthority``
value. Round 5 (P15-R5-F1) found *that* still open in one respect: the authority was an ordinary
public dataclass with an ordinary public constructor, so a caller could build their own over an
alternate world and hand it to the free request-facing function, which only checked its type.
An ``isinstance`` check, a sentinel, a leading-underscore field or an opaque ``repr`` are all
ruled out as trust controls, so the type is **deleted** and the request-facing operation is now a
genuine closure: it has no public constructor, and the only way to obtain a working one is to
call the composition step, which is exactly where the anchor-signature and currency gate lives.
``TrustedRuntimeRoot`` and ``RuntimeDeploymentAuthority`` are both removed rather than kept
beside their replacements; every earlier round's static facts survive in strictly stronger form
(the deleted factory is still absent by name, and both removed type names are now absent from
shipped code entirely).

Issuing, rotating, and revoking either chain goes through one canonical committer each, and both
parameterize the *same* shared monotonic-chain mechanism
(:mod:`~manosube_agent_civilization.runtime.transition_chain`) rather than restating a rule of
their own. Each commits the immutable record **and** moves that chain's own pointer inside
``semantic_state.runtime.claims`` in a single atomic State transition:

```python
result = commit_runtime_deployment_declaration(
    store, project_id, declaration, committed_at="2026-09-09T00:00:00Z"
)
result["runtime_deployment_declaration_ref"]  # what a target_identity then references

admitted = commit_runtime_root_admission(
    store,
    project_id,
    admission,
    trust_anchor_public_key_hex=deployment_configured_trust_anchor_public_key_hex,
    committed_at="2026-09-09T00:00:00Z",
)
admitted["runtime_root_admission_ref"]  # what a composition then references
```

Both are **monotonic**: a genesis record declares ``generation=0``/``predecessor_ref=null`` and
is admitted only into an empty chain, and every later record must declare the exact predecessor
it replaces and exactly one greater generation -- both signed, so neither can be re-aimed after
the fact. A ``REVOKED`` head is terminal: no successor and no ancestor replay is ever admitted
for that chain again. Replaying the already-current record is an idempotent no-op rather than a
transition, and two successors racing from the same head resolve to at most one winner, with the
loser failing closed rather than silently re-aiming its own already-signed body.

These are canonical committers, not routes: ``PUBLIC_RUNTIME_ENTRY_POINT_COUNT`` is still ``3``.

See ``10_RUNTIME/RUNTIME_CONTRACT.md`` §13 and ``10_RUNTIME/RUNTIME_INDEX.md`` for the full
contract set.
"""

from .admission_registry import commit_runtime_root_admission
from .bootstrap import compose_trusted_runtime_deployment_authority
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
    "commit_runtime_deployment_declaration",
    "commit_runtime_root_admission",
    "compose_trusted_runtime_deployment_authority",
    "observe_runtime_target",
    "route_runtime_observation_to_evidence",
]
