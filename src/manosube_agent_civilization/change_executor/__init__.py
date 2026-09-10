"""Phase 18, Issue #73: Controlled Autonomous Change execution.

```text
KERNEL_ELEMENT=NONE_EXECUTION_ADAPTER
```

This package is **not** a ninth Kernel element (the Kernel is fixed at eight:
``KERNEL_ELEMENT_COUNT=8``, ``ONE_KERNEL_ELEMENT_PER_PACKAGE=true``). It is an adapter layer,
exactly as Boot, CLI, Agent Runtime, Independent Verification, Projection, Runtime, and URL Boot
already are: it lets an already-authorized canonical Change be autonomously *executed*, only
inside an explicit, closed, low-risk Execution Boundary, producing one immutable execution
receipt -- and then stops. It creates no Authority, updates no canonical State's semantic
content beyond its own three new record kinds (``execution_intent``, ``execution_attempt``,
``change_execution_receipt``) and its own kill switch chain (``change_executor_kill_switch``),
proves no causality, establishes no sufficient Evidence, closes no Difference, and declares no
completion -- it hands off to the existing Evidence/Observation/Reflow owners
(:mod:`~manosube_agent_civilization.change_executor.evidence_handoff`) rather than becoming a
new owner of any of them.

``CHANGE_EXECUTOR_OWNER_COUNT=1``, ``PUBLIC_CHANGE_EXECUTOR_ENTRY_POINT_COUNT=2``
(:func:`~manosube_agent_civilization.change_executor.route.compose_change_executor` ``+1``
:func:`~manosube_agent_civilization.change_executor.evidence_handoff.
route_change_execution_to_evidence`).

This package never pushes or merges to GitHub, never deploys, never uses a live credential, and
never runs arbitrary shell/subprocess/network I/O of any kind -- the only production adapter it
ships is :class:`~manosube_agent_civilization.change_executor.adapter.
ControlledFilesystemAdapter`, a bounded filesystem/worktree writer confined to a disposable,
low-risk target (documentation, tests, isolated source, and low-risk configuration file kinds
only -- see :data:`~manosube_agent_civilization.change_executor.boundary.
PERMITTED_ACTION_KINDS`).

```python
from manosube_agent_civilization.change_executor import (
    ControlledFilesystemAdapter,
    compose_change_executor,
    commit_change_executor_kill_switch,
)

execute = compose_change_executor(
    store,
    project_id=project_id,
    project_binding_id=project_binding_id,
    execution_boundary={...},  # a closed Execution Boundary -- see boundary.py
    adapter_identity={"kind": "controlled_filesystem_adapter", "version": "0.1"},
    adapter=ControlledFilesystemAdapter(executor_identity="controlled_filesystem_adapter", executor_version="0.1"),
    kill_switch_trust_anchor_public_key_hex=configured_trust_anchor,
)

result = execute(
    change_id,
    claim_token="...",
    execution_instant="2026-09-10T00:00:01Z",
    worktree_root="/path/to/an/admitted/disposable/worktree",
)
result["receipt"]  # the immutable change_execution_receipt
```

See each submodule's own docstring for its own disclosed judgment calls; ``route.py``'s own
docstring in particular states the ones with the widest structural consequence.
"""

from .adapter import ControlledFilesystemAdapter
from .boundary import (
    CHANGE_EXECUTOR_SCHEMA_BASE,
    PERMITTED_ACTION_KINDS,
    REQUIRED_BOUNDARY_KEYS,
    ROLLBACK_POLICIES,
    canonicalize_inert_data,
    deep_freeze,
    execution_boundary_fingerprint,
    path_is_admitted,
    validate_execution_boundary,
)
from .errors import (
    ChangeExecutorError,
    ExecutionAdapterError,
    ExecutionAuthorityProvenanceError,
    ExecutionBoundaryError,
    ExecutionConcurrentClaimError,
    ExecutionKillSwitchError,
    ExecutionReceiptIntegrityError,
    ExecutionReconciliationRequiredError,
    ExecutionTerminalClaimMismatchError,
    StaleExecutionInputError,
)
from .evidence_handoff import route_change_execution_to_evidence
from .identity import execution_mapping_slot_key
from .kill_switch import (
    KILL_SWITCH_RECORD_KIND,
    commit_change_executor_kill_switch,
    resolve_current_kill_switch,
)
from .route import compose_change_executor
from .types import EXECUTION_OUTCOMES, ROLLBACK_OUTCOMES, ChangeExecutorAdapter

__all__ = [
    "CHANGE_EXECUTOR_SCHEMA_BASE",
    "EXECUTION_OUTCOMES",
    "KILL_SWITCH_RECORD_KIND",
    "PERMITTED_ACTION_KINDS",
    "REQUIRED_BOUNDARY_KEYS",
    "ROLLBACK_OUTCOMES",
    "ROLLBACK_POLICIES",
    "ChangeExecutorAdapter",
    "ChangeExecutorError",
    "ControlledFilesystemAdapter",
    "ExecutionAdapterError",
    "ExecutionAuthorityProvenanceError",
    "ExecutionBoundaryError",
    "ExecutionConcurrentClaimError",
    "ExecutionKillSwitchError",
    "ExecutionReceiptIntegrityError",
    "ExecutionReconciliationRequiredError",
    "ExecutionTerminalClaimMismatchError",
    "StaleExecutionInputError",
    "canonicalize_inert_data",
    "commit_change_executor_kill_switch",
    "compose_change_executor",
    "deep_freeze",
    "execution_boundary_fingerprint",
    "execution_mapping_slot_key",
    "path_is_admitted",
    "resolve_current_kill_switch",
    "route_change_execution_to_evidence",
    "validate_execution_boundary",
]
