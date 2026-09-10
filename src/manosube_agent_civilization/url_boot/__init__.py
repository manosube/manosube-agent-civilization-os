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
(:func:`compose_url_source_observer` ``+1`` :func:`route_url_observation_to_evidence`).

**Structural Review Round 4 (P17-R4-F2) note.** Public ``observe_url_source`` -- a plain
function taking ``store``/``adapter`` directly on every call -- is replaced by
:func:`compose_url_source_observer`, a trusted composition step binding
Store/Project/Binding/adapter *once* and returning the request-facing observation closure
itself, whose own call signature carries only request data (``source_identity``, ``boundary``,
``observed_at``). See that function's own docstring for the full rationale.

```python
observe = compose_url_source_observer(
    store,
    project_id=project_id,
    project_binding_id=project_binding_id,
    adapter=LocalHttpUrlSourceAdapter(),
)
result = observe(
    network.canonical_source_identity("https://example.org/status"),
    {
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
    "2026-09-10T00:00:01Z",
)
result["envelope"]  # the canonical, committed URL Source Observation Envelope, or None
                     # (P17-C7/P17-R1-F1: only ever non-None when fetch_outcome == "OBSERVED")
result["receipt"]   # UrlSourceObservationReceipt

evidence = route_url_observation_to_evidence(
    store, result["receipt"], project_id, evidence_request
)
```

A local-test-only fetch (``127.0.0.1``, an ephemeral port) requires this repository's own
trusted, non-shipped disposable-local-test composition boundary,
``tests/fixtures/url_boot_local_test_authority.py`` -- never reachable through any field of
``boundary``, any constructor argument of ``adapter``, or any parameter of
``compose_url_source_observer`` or its returned closure (P17-R1-F3, corrected in Round 2,
P17-R2-F2, again in Round 3, P17-R3-F2, and again in Round 4, P17-R4-F2: this package ships no
loopback-permitting classifier of any kind -- the disposable-local-test composition lives
entirely outside this shipped package, requires a genuine externally held test-harness
authority, and its own request-facing observer is a closure returned from trusted composition,
never a directly-importable function taking Store/adapter/classifier arguments of its own).

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
from .route import compose_url_source_observer
from .types import (
    RECEIPT_STATUSES,
    URL_FETCH_METHODS,
    URL_FETCH_OUTCOMES,
    URL_HOP_CONNECT_OUTCOMES,
    URL_HOP_RESOLVE_OUTCOMES,
    URL_HOP_TRANSPORT_OUTCOMES,
    UrlSourceAdapter,
    UrlSourceObservationReceipt,
)

__all__ = [
    "RECEIPT_STATUSES",
    "URL_FETCH_METHODS",
    "URL_FETCH_OUTCOMES",
    "URL_HOP_CONNECT_OUTCOMES",
    "URL_HOP_RESOLVE_OUTCOMES",
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
    "compose_url_source_observer",
    "route_url_observation_to_evidence",
]
