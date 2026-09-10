"""V3 (Issue #69): real bounded URL Boot vertical proof.

Runs the complete canonical route -- :func:`~manosube_agent_civilization.url_boot.route.
observe_url_source` through :class:`~manosube_agent_civilization.url_boot.adapter.
LocalHttpUrlSourceAdapter` -- against one real, disposable, local HTTP target this test itself
starts and stops (``127.0.0.1``, an ephemeral port). No VPS or cloud provider is used or required
(Issue #69's own explicit non-target). Proves at least one genuine positive (``OBSERVED``), one
genuine per-hop-reauthorized redirect follow, one genuine bounded negative
(``UNSUPPORTED_MEDIA_TYPE``), and one genuine unreachable-port failure (``CONNECTION_FAILURE``),
each a real network round trip over ``localhost`` through this package's own
``network.fetch_one_hop`` -- then hands the positive receipt off to the existing Evidence owner.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import threading
from typing import Any

import pytest
from tests.evidence_helpers import change_free_verification_evidence_request
from tests.fixtures.url_boot_world import bound, boundary_for

from manosube_agent_civilization.url_boot.adapter import LocalHttpUrlSourceAdapter
from manosube_agent_civilization.url_boot.evidence_handoff import (
    route_url_observation_to_evidence,
)
from manosube_agent_civilization.url_boot.network import canonical_source_identity
from manosube_agent_civilization.url_boot.route import observe_url_source


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass  # keep test output quiet

    def do_GET(self) -> None:
        if self.path == "/status":
            body = json.dumps({"status": "ok", "secret": "leak"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/status")
            self.end_headers()
        elif self.path == "/text":
            body = b"plain text, not json"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/oversized":
            body = json.dumps({"status": "x" * 4096}).encode("utf-8")
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
    return {
        "store": store,
        "project_id": ctx["project_id"],
        "project_binding_id": ctx["project_binding_id"],
    }


def _rebind_project(value: Any, old: str, new: str) -> Any:
    if isinstance(value, dict):
        return {key: _rebind_project(item, old, new) for key, item in value.items()}
    if isinstance(value, list):
        return [_rebind_project(item, old, new) for item in value]
    return new if value == old else value


def test_real_local_http_positive_observation_reaches_verified_evidence(
    _world: dict[str, Any], _local_http_target: tuple[str, int]
) -> None:
    host, port = _local_http_target
    source_identity = canonical_source_identity(f"http://{host}:{port}/status")
    boundary = boundary_for(admitted_hosts=[host], admitted_ports=[port])
    adapter = LocalHttpUrlSourceAdapter()

    outcome = observe_url_source(
        _world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        source_identity=source_identity,
        boundary=boundary,
        adapter=adapter,
        observed_at="2026-09-10T00:00:01Z",
    )

    assert outcome["envelope"]["fetch_outcome"] == "OBSERVED"
    assert outcome["envelope"]["observed_fields"] == {"status": "ok"}
    assert "secret" not in outcome["envelope"]["observed_fields"]
    assert outcome["receipt"].status == "VERIFIED"

    resolved = _world["store"].resolve_record(
        _world["project_id"],
        "url_source_observation_envelope",
        outcome["envelope"]["url_source_observation_envelope_id"],
    )
    assert resolved == outcome["envelope"]

    request = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", _world["project_id"]
    )
    evidence = route_url_observation_to_evidence(
        _world["store"], outcome["receipt"], _world["project_id"], request
    )
    assert evidence["evidence_position"] == "CHANGE_FREE_VERIFICATION_EVIDENCE"
    assert evidence["verification_result_provenance"]["status"] == "VERIFIED"
    assert (
        evidence["verification_result_provenance"]["requirement_id"]
        == outcome["envelope"]["url_source_observation_envelope_id"]
    )


def test_real_local_http_redirect_is_followed_and_reauthorized(
    _world: dict[str, Any], _local_http_target: tuple[str, int]
) -> None:
    host, port = _local_http_target
    source_identity = canonical_source_identity(f"http://{host}:{port}/redirect")
    boundary = boundary_for(admitted_hosts=[host], admitted_ports=[port])
    adapter = LocalHttpUrlSourceAdapter()

    outcome = observe_url_source(
        _world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        source_identity=source_identity,
        boundary=boundary,
        adapter=adapter,
        observed_at="2026-09-10T00:00:01Z",
    )

    assert outcome["envelope"]["fetch_outcome"] == "OBSERVED"
    assert outcome["envelope"]["redirect_hop_count"] == 1
    assert outcome["envelope"]["effective_source_identity"]["path"] == "/status"
    assert outcome["envelope"]["requested_source_identity"]["path"] == "/redirect"


def test_a_redirect_to_a_host_outside_scope_is_refused_not_followed(
    _world: dict[str, Any], _local_http_target: tuple[str, int]
) -> None:
    """The escaping redirect itself is never actually reached -- ``network_scope`` re-checks
    the redirect target's *hostname* before any second hop is attempted (P17-C5)."""

    class _EscapingHandler(BaseHTTPRequestHandler):
        def log_message(self, *args: Any) -> None:
            pass

        def do_GET(self) -> None:
            self.send_response(302)
            self.send_header("Location", "http://evil.example/status")
            self.end_headers()

    server = HTTPServer(("127.0.0.1", 0), _EscapingHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        source_identity = canonical_source_identity(f"http://{host}:{port}/redirect")
        boundary = boundary_for(admitted_hosts=[host], admitted_ports=[port])
        adapter = LocalHttpUrlSourceAdapter()

        outcome = observe_url_source(
            _world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            source_identity=source_identity,
            boundary=boundary,
            adapter=adapter,
            observed_at="2026-09-10T00:00:01Z",
        )
        assert outcome["envelope"]["fetch_outcome"] == "REDIRECT_REFUSED"
        assert outcome["receipt"].status == "FAILED"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_real_local_http_wrong_content_type_is_a_genuine_unsupported_media_type(
    _world: dict[str, Any], _local_http_target: tuple[str, int]
) -> None:
    host, port = _local_http_target
    source_identity = canonical_source_identity(f"http://{host}:{port}/text")
    boundary = boundary_for(admitted_hosts=[host], admitted_ports=[port])
    adapter = LocalHttpUrlSourceAdapter()

    outcome = observe_url_source(
        _world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        source_identity=source_identity,
        boundary=boundary,
        adapter=adapter,
        observed_at="2026-09-10T00:00:01Z",
    )
    assert outcome["envelope"]["fetch_outcome"] == "UNSUPPORTED_MEDIA_TYPE"
    assert outcome["envelope"]["observed_fields"] is None
    assert outcome["receipt"].status == "FAILED"


def test_real_local_http_oversized_response_is_refused_not_truncated_and_kept(
    _world: dict[str, Any], _local_http_target: tuple[str, int]
) -> None:
    host, port = _local_http_target
    source_identity = canonical_source_identity(f"http://{host}:{port}/oversized")
    boundary = boundary_for(admitted_hosts=[host], admitted_ports=[port], max_response_bytes=64)
    adapter = LocalHttpUrlSourceAdapter()

    outcome = observe_url_source(
        _world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        source_identity=source_identity,
        boundary=boundary,
        adapter=adapter,
        observed_at="2026-09-10T00:00:01Z",
    )
    assert outcome["envelope"]["fetch_outcome"] == "OVERSIZED_RESPONSE"
    assert outcome["envelope"]["observed_fields"] is None
    assert outcome["receipt"].status == "FAILED"


def test_real_local_http_unreachable_port_is_connection_failure(_world: dict[str, Any]) -> None:
    """A genuinely closed port is a real transport failure, classified honestly rather than
    folded into any other outcome."""

    source_identity = canonical_source_identity("http://127.0.0.1:1/status")
    boundary = boundary_for(admitted_hosts=["127.0.0.1"], admitted_ports=[1], timeout_seconds=2)
    adapter = LocalHttpUrlSourceAdapter()

    outcome = observe_url_source(
        _world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        source_identity=source_identity,
        boundary=boundary,
        adapter=adapter,
        observed_at="2026-09-10T00:00:01Z",
    )
    assert outcome["envelope"]["fetch_outcome"] in ("CONNECTION_FAILURE", "TIMEOUT")
    assert outcome["receipt"].status == "UNAVAILABLE"
