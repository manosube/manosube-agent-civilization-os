"""V3 (Issue #64): real bounded runtime vertical proof.

Runs the complete canonical route -- :func:`~manosube_agent_civilization.runtime.route.
observe_runtime_target` through :class:`~manosube_agent_civilization.runtime.adapter.
LocalHttpRuntimeAdapter` -- against one real, disposable, local HTTP target this test itself
starts and stops (``127.0.0.1``, an ephemeral port). No VPS or cloud provider is used or
required (Issue #64's own explicit non-target). Proves at least one genuine positive
(``OBSERVED``) and one genuine bounded negative (``NOT_FOUND``) observation, each a real
network round trip over ``localhost`` through stdlib ``urllib``, then hands the positive
receipt off to the existing Evidence owner -- the "identity-preserving Runtime Evidence
through existing canonical owners" the Human Objective requires.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import threading
from typing import Any

import pytest
from tests.evidence_helpers import change_free_verification_evidence_request
from tests.fixtures.runtime_world import bound, boundary_for, target_identity_for

from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.runtime.adapter import LocalHttpRuntimeAdapter
from manosube_agent_civilization.runtime.evidence_handoff import (
    route_runtime_observation_to_evidence,
)
from manosube_agent_civilization.runtime.route import observe_runtime_target

_DEPLOYMENT_FINGERPRINT = "sha256:" + "b" * 64


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass  # keep test output quiet

    def do_GET(self) -> None:
        if self.path == "/health":
            body = json.dumps(
                {"status": "ok", "deployment_fingerprint": _DEPLOYMENT_FINGERPRINT}
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()


@pytest.fixture
def _local_http_target() -> Any:
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


@pytest.fixture
def _world(tmp_path: Path) -> dict[str, Any]:
    store, ctx = bound(tmp_path)
    boot_context = boot_project(
        store, project_id=ctx["project_id"], project_binding_id=ctx["project_binding_id"]
    )
    return {
        "store": store,
        "project_id": ctx["project_id"],
        "project_binding_id": ctx["project_binding_id"],
        "human_authority_ref": dict(boot_context.human_authority_ref),
    }


def test_real_local_http_positive_observation_reaches_verified_evidence(
    _world: dict[str, Any], _local_http_target: tuple[str, int]
) -> None:
    host, port = _local_http_target
    target_identity = target_identity_for(
        _world["project_binding_id"], deployment_fingerprint=_DEPLOYMENT_FINGERPRINT
    )
    boundary = boundary_for(
        base_url=f"http://{host}:{port}",
        path="/health",
        permitted_fields=["status"],
        allowed_hosts=[host],
    )
    adapter = LocalHttpRuntimeAdapter()

    outcome = observe_runtime_target(
        _world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        target_identity=target_identity,
        boundary=boundary,
        adapter=adapter,
        observed_at="2026-01-01T00:30:00Z",
    )

    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"
    assert outcome["envelope"]["observed_fields"] == {"status": "ok"}
    assert outcome["receipt"].status == "VERIFIED"

    resolved = _world["store"].resolve_record(
        _world["project_id"],
        "runtime_observation_envelope",
        outcome["envelope"]["runtime_observation_envelope_id"],
    )
    assert resolved == outcome["envelope"]

    evidence_request = change_free_verification_evidence_request(provenance=None)

    def _rebind_project(value: Any, old: str, new: str) -> Any:
        if isinstance(value, dict):
            return {key: _rebind_project(item, old, new) for key, item in value.items()}
        if isinstance(value, list):
            return [_rebind_project(item, old, new) for item in value]
        return new if value == old else value

    request = _rebind_project(evidence_request, "PRJ-0001", _world["project_id"])
    evidence = route_runtime_observation_to_evidence(
        _world["store"], outcome["receipt"], _world["project_id"], request
    )
    assert evidence["evidence_position"] == "CHANGE_FREE_VERIFICATION_EVIDENCE"
    assert evidence["verification_result_provenance"]["status"] == "VERIFIED"
    assert (
        evidence["verification_result_provenance"]["requirement_id"]
        == outcome["envelope"]["runtime_observation_envelope_id"]
    )


def test_real_local_http_bounded_negative_observation_is_a_genuine_not_found(
    _world: dict[str, Any], _local_http_target: tuple[str, int]
) -> None:
    host, port = _local_http_target
    target_identity = target_identity_for(
        _world["project_binding_id"], deployment_fingerprint=_DEPLOYMENT_FINGERPRINT
    )
    boundary = boundary_for(
        base_url=f"http://{host}:{port}",
        path="/does-not-exist",
        permitted_fields=["status"],
        allowed_hosts=[host],
    )
    adapter = LocalHttpRuntimeAdapter()

    outcome = observe_runtime_target(
        _world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        target_identity=target_identity,
        boundary=boundary,
        adapter=adapter,
        observed_at="2026-01-01T00:31:00Z",
    )

    assert outcome["envelope"]["observation_outcome"] == "NOT_FOUND"
    assert outcome["envelope"]["observed_fields"] is None
    assert outcome["receipt"].status == "FAILED"


def test_real_local_http_unreachable_port_is_unavailable_never_not_found(
    _world: dict[str, Any],
) -> None:
    """A genuinely closed port -- a connection failure, not an HTTP 404 -- must classify as
    ``UNAVAILABLE`` (a transport-level failure), never as the authoritative absence
    ``NOT_FOUND`` means."""

    target_identity = target_identity_for(
        _world["project_binding_id"], deployment_fingerprint=_DEPLOYMENT_FINGERPRINT
    )
    boundary = boundary_for(
        base_url="http://127.0.0.1:1",
        path="/health",
        permitted_fields=["status"],
        allowed_hosts=["127.0.0.1"],
        timeout_seconds=2,
    )
    adapter = LocalHttpRuntimeAdapter()

    outcome = observe_runtime_target(
        _world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        target_identity=target_identity,
        boundary=boundary,
        adapter=adapter,
        observed_at="2026-01-01T00:32:00Z",
    )

    assert outcome["envelope"]["observation_outcome"] in ("UNAVAILABLE", "TIMEOUT")
    assert outcome["receipt"].status == "UNAVAILABLE"
