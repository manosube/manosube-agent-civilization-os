"""Phase 17 (Issue #69) shared URL Boot test world.

Deliberately self-contained, the identical "each phase's own fixture module builds its own
``bound()`` from ``tests.fixtures.product_binding`` directly" discipline
``tests/fixtures/model_runtime_world.py``'s own module already keeps -- never importing another
phase's own fixture module.

This package's own authority model is deliberately simpler than Runtime's (no deployment
declaration, no root admission, no signing at all): :func:`bound` is therefore a plain binding,
with none of Runtime/Model-Runtime's own signing-key scaffolding.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.fixtures.product_binding import bind_project_kwargs, genesis_records
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.binding import bind_project
from manosube_agent_civilization.store import FileStateStore

DEFAULT_TIME_WINDOW: dict[str, str] = {
    "issued_at": "2026-09-10T00:00:00Z",
    "expires_at": "2026-09-10T00:05:00Z",
}


def bound(tmp_path: Path, *, subdir: str = "backend") -> tuple[FileStateStore, dict[str, Any]]:
    """One real ``FileStateStore`` with one real, genuinely bound project.

    *subdir* exists so a test can build a **second, entirely separate Store** under the same
    ``tmp_path`` -- needed for a cross-Store/cross-project substitution control.
    """

    store = FileStateStore(tmp_path / subdir, schema_root=SCHEMA_ROOT)
    kwargs = bind_project_kwargs()
    result = bind_project(
        store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
    )
    return store, {
        "project_id": kwargs["project_id"],
        "project_binding_id": result["project_binding_id"],
        "genesis_state": result["committed_state"],
    }


def boundary_for(
    *,
    admitted_schemes: list[str] | None = None,
    admitted_hosts: list[str] | None = None,
    admitted_ports: list[int] | None = None,
    max_redirects: int = 3,
    timeout_seconds: int = 5,
    max_response_bytes: int = 65536,
    admitted_content_types: list[str] | None = None,
    permitted_fields: list[str] | None = None,
    issued_at: str = DEFAULT_TIME_WINDOW["issued_at"],
    expires_at: str = DEFAULT_TIME_WINDOW["expires_at"],
    redaction_fields: list[str] | None = None,
    expected_field: str | None = None,
    expected_value: Any = None,
) -> dict[str, Any]:
    """One real, schema-valid, closed fetch Boundary.

    Carries no ``permit_loopback_test_hosts`` field at all, and never has since Structural
    Review Round 1 (P17-R1-F3) -- that allowance is now reachable only through this
    repository's own trusted, non-shipped, authority-gated disposable-local-test composition
    (``tests/fixtures/url_boot_local_test_authority.compose_disposable_local_test_observer``,
    Structural Review Round 3 P17-R3-F2, further hardened Round 4 P17-R4-F2), never through
    Boundary data, an adapter constructor, or any parameter of public
    ``compose_url_source_observer`` or its returned closure.
    """

    boundary: dict[str, Any] = {
        "fetch_method": "HTTP_GET_BOUNDED",
        "network_scope": {
            "admitted_schemes": list(
                admitted_schemes if admitted_schemes is not None else ["http"]
            ),
            "admitted_hosts": list(admitted_hosts if admitted_hosts is not None else ["127.0.0.1"]),
            "admitted_ports": list(admitted_ports if admitted_ports is not None else [80]),
        },
        "redirect_policy": {"max_redirects": max_redirects},
        "timeout_seconds": timeout_seconds,
        "max_response_bytes": max_response_bytes,
        "admitted_content_types": list(
            admitted_content_types if admitted_content_types is not None else ["application/json"]
        ),
        "permitted_fields": list(permitted_fields if permitted_fields is not None else ["status"]),
        "time_window": {"issued_at": issued_at, "expires_at": expires_at},
        "redaction_fields": list(redaction_fields if redaction_fields is not None else []),
        "credentials_permitted": False,
    }
    if expected_field is not None:
        boundary["expected_field"] = expected_field
        boundary["expected_value"] = expected_value
    return boundary


__all__ = ["DEFAULT_TIME_WINDOW", "bound", "boundary_for"]
