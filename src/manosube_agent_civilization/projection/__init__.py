"""Phase 14, Issue #62: Identity-preserving GitHub projection.

```text
KERNEL_ELEMENT=NONE_PROJECTION_ADAPTER
```

This package is **not** a ninth Kernel element (the Kernel is fixed at eight:
``KERNEL_ELEMENT_COUNT=8``, ``ONE_KERNEL_ELEMENT_PER_PACKAGE=true``). It is an adapter layer,
exactly as Boot, CLI, Agent Runtime, and Independent Verification already are, projecting
already-real canonical Difference/Change/Evidence subjects to GitHub through one deterministic
Projection Envelope and one explicit GitHub Adapter boundary -- never a second State,
Difference, Authority, Evidence, Store, or Closure owner.

```python
result = project_to_github(
    store,
    project_id=project_id,
    project_binding_id=project_binding_id,
    subject_ref={"kind": "observation_evidence", "id": evidence_id},
    projection_kind="EVIDENCE_ARTIFACT",
    target_repository={"host": "github", "owner": "acme", "repo": "widget"},
    projection_payload={"title": "...", "body": "..."},
    github_authority_ref=human_authority_ref,
    materialized_at="2026-01-01T00:00:00Z",
    adapter=my_adapter,
)
result["envelope"]  # the canonical, committed Projection Envelope
result["receipt"]   # GitHubObservationReceipt
result["reused"]    # bool

evidence = route_observation_receipt_to_evidence(result["receipt"], project_id, evidence_request)
```

See ``09_PROJECTION/PROJECTION_INDEX.md`` for the full contract set.
"""

from .errors import (
    ConflictingProjectionPayloadError,
    ProjectionAdapterError,
    ProjectionError,
    ProjectionRequirementError,
    ProjectionValueError,
)
from .github_adapter import FakeGitHubAdapter, RealGitHubAdapter
from .receipt_handoff import route_observation_receipt_to_evidence
from .route import project_to_github
from .types import (
    ARTIFACT_KINDS,
    PROJECTION_KINDS,
    RECEIPT_STATUSES,
    SUBJECT_REF_KINDS,
    GitHubAdapter,
    GitHubObservationReceipt,
)

__all__ = [
    "ARTIFACT_KINDS",
    "PROJECTION_KINDS",
    "RECEIPT_STATUSES",
    "SUBJECT_REF_KINDS",
    "ConflictingProjectionPayloadError",
    "FakeGitHubAdapter",
    "GitHubAdapter",
    "GitHubObservationReceipt",
    "ProjectionAdapterError",
    "ProjectionError",
    "ProjectionRequirementError",
    "ProjectionValueError",
    "RealGitHubAdapter",
    "project_to_github",
    "route_observation_receipt_to_evidence",
]
