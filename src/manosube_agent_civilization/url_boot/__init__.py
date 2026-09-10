"""Phase 17, Issue #69: Read-only URL Boot and the Untrusted Content Boundary.

```text
KERNEL_ELEMENT=NONE_URL_BOOT_ADAPTER
```

This package is **not** a ninth Kernel element (the Kernel is fixed at eight:
``KERNEL_ELEMENT_COUNT=8``, ``ONE_KERNEL_ELEMENT_PER_PACKAGE=true``). It is an adapter layer,
exactly as Boot, CLI, Agent Runtime, Independent Verification, Projection, and Runtime already
are, letting a URL be used as a bounded, read-only external observation source through one
deterministic URL Source Observation Envelope and one replaceable URL Source Adapter boundary --
never a second State, Difference, Authority, Evidence, Store, or Closure owner, and never a
channel through which fetched content can mint Authority, invoke a model, execute a Change, or
bypass Evidence (P17-C4).

``URL_BOOT_OWNER_COUNT=1``, ``PUBLIC_URL_BOOT_ENTRY_POINT_COUNT=2``
(:func:`observe_url_source` ``+1`` :func:`route_url_observation_to_evidence`).

```python
result = observe_url_source(
    store,
    project_id=project_id,
    project_binding_id=project_binding_id,
    source_identity=network.canonical_source_identity("https://example.org/status"),
    boundary={
        "fetch_method": "HTTP_GET_BOUNDED",
        "network_scope": {
            "admitted_schemes": ["https"],
            "admitted_hosts": ["example.org"],
            "admitted_ports": [443],
        },
        "redirect_policy": {"max_redirects": 3},
        "timeout_seconds": 5.0,
        "max_response_bytes": 65536,
        "admitted_content_types": ["application/json"],
        "permitted_fields": ["status"],
        "time_window": {
            "issued_at": "2026-09-10T00:00:00Z",
            "expires_at": "2026-09-10T00:05:00Z",
        },
        "redaction_fields": [],
        "credentials_permitted": False,
    },
    adapter=LocalHttpUrlSourceAdapter(),
    observed_at="2026-09-10T00:00:01Z",
)
result["envelope"]  # the canonical, committed URL Source Observation Envelope, or None
                     # (P17-C7/P17-R1-F1: only ever non-None when fetch_outcome == "OBSERVED")
result["receipt"]   # UrlSourceObservationReceipt

evidence = route_url_observation_to_evidence(
    store, result["receipt"], project_id, evidence_request
)
```

A local-test-only fetch (``127.0.0.1``, an ephemeral port) requires
``LocalHttpUrlSourceAdapter(permit_loopback_test_hosts=True)`` -- a Python constructor argument
only test-composition code ever sets (P17-R1-F3); no field of ``boundary`` above can ever enable
it, and ``observe_url_source`` accepts no such field at all.

See ``12_URL_BOOT/URL_BOOT_CONTRACT.md`` and ``12_URL_BOOT/URL_BOOT_INDEX.md`` for the full
contract this package implements, its disclosed judgment calls, and its explicit non-claims.
"""

from .adapter import FakeUrlSourceAdapter, LocalHttpUrlSourceAdapter
from .errors import (
    UrlBootAdapterError,
    UrlBootAuthorityFreshnessError,
    UrlBootEnvelopeIntegrityError,
    UrlBootError,
    UrlBootRequirementError,
)
from .evidence_handoff import route_url_observation_to_evidence
from .route import observe_url_source
from .types import (
    RECEIPT_STATUSES,
    URL_FETCH_METHODS,
    URL_FETCH_OUTCOMES,
    URL_HOP_TRANSPORT_OUTCOMES,
    UrlSourceAdapter,
    UrlSourceObservationReceipt,
)

__all__ = [
    "RECEIPT_STATUSES",
    "URL_FETCH_METHODS",
    "URL_FETCH_OUTCOMES",
    "URL_HOP_TRANSPORT_OUTCOMES",
    "FakeUrlSourceAdapter",
    "LocalHttpUrlSourceAdapter",
    "UrlBootAdapterError",
    "UrlBootAuthorityFreshnessError",
    "UrlBootEnvelopeIntegrityError",
    "UrlBootError",
    "UrlBootRequirementError",
    "UrlSourceAdapter",
    "UrlSourceObservationReceipt",
    "observe_url_source",
    "route_url_observation_to_evidence",
]
