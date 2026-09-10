"""V3 (Issue #69): real bounded URL Boot vertical proof.

Runs the complete canonical route -- :func:`~manosube_agent_civilization.url_boot.route.
observe_url_source_for_disposable_local_test` through :class:`~manosube_agent_civilization.
url_boot.adapter.LocalHttpUrlSourceAdapter` -- against one real, disposable, local HTTP target
this test itself starts and stops (``127.0.0.1``, an ephemeral port). No VPS or cloud provider is
used or required (Issue #69's own explicit non-target). Proves at least one genuine positive
(``OBSERVED``), one genuine per-hop-reauthorized redirect follow, one genuine bounded negative
(``UNSUPPORTED_MEDIA_TYPE``), and one genuine unreachable-port failure (``CONNECTION_FAILURE``),
each a real network round trip over ``localhost`` through this package's own
``network.resolve_hop_address``/``network.connect_and_request_hop`` -- then hands the positive
receipt off to the existing Evidence owner.

Every real local target used here is loopback, so every observation in this file goes through
``observe_url_source_for_disposable_local_test`` -- the one, distinctly-named,
non-public-surface, trusted-composition-only entry point that allowance can ever be reached
through (Structural Review Round 1, P17-R1-F3, further corrected in Round 2, P17-R2-F2: no
adapter constructor argument exists for this any more at all; see ``route.py``'s own module
docstring). ``LocalHttpUrlSourceAdapter()`` itself now takes no loopback-related argument
whatsoever.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import ssl
import threading
from typing import Any

import pytest
from tests.evidence_helpers import change_free_verification_evidence_request
from tests.fixtures.url_boot_world import bound, boundary_for

from manosube_agent_civilization.url_boot import network as network_module
from manosube_agent_civilization.url_boot.adapter import LocalHttpUrlSourceAdapter
from manosube_agent_civilization.url_boot.evidence_handoff import (
    route_url_observation_to_evidence,
)
from manosube_agent_civilization.url_boot.network import canonical_source_identity
from manosube_agent_civilization.url_boot.route import observe_url_source_for_disposable_local_test


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

    outcome = observe_url_source_for_disposable_local_test(
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
    assert outcome["envelope"]["project_binding_ref"] == {
        "kind": "project_binding",
        "id": _world["project_binding_id"],
    }
    assert outcome["envelope"]["resolution_provenance"] == [
        {"host": host, "port": port, "resolved_address": "127.0.0.1"}
    ]
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
    assert evidence["verification_result_provenance"]["verification_boundary"][
        "project_binding_ref"
    ] == {"kind": "project_binding", "id": _world["project_binding_id"]}


def test_real_local_http_redirect_is_followed_and_reauthorized(
    _world: dict[str, Any], _local_http_target: tuple[str, int]
) -> None:
    host, port = _local_http_target
    source_identity = canonical_source_identity(f"http://{host}:{port}/redirect")
    boundary = boundary_for(admitted_hosts=[host], admitted_ports=[port])
    adapter = LocalHttpUrlSourceAdapter()

    outcome = observe_url_source_for_disposable_local_test(
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
    # P17-R1-F4: the identical host/port was resolved on both hops of this one fetch, and the
    # admitted resolution is recorded exactly once, not once per hop.
    assert outcome["envelope"]["resolution_provenance"] == [
        {"host": host, "port": port, "resolved_address": "127.0.0.1"}
    ]


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

        outcome = observe_url_source_for_disposable_local_test(
            _world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            source_identity=source_identity,
            boundary=boundary,
            adapter=adapter,
            observed_at="2026-09-10T00:00:01Z",
        )
        assert outcome["envelope"] is None
        assert outcome["receipt"].observations["fetch_outcome"] == "REDIRECT_REFUSED"
        assert outcome["receipt"].status == "FAILED"
        assert outcome["receipt"].url_source_observation_envelope_id is None
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

    outcome = observe_url_source_for_disposable_local_test(
        _world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        source_identity=source_identity,
        boundary=boundary,
        adapter=adapter,
        observed_at="2026-09-10T00:00:01Z",
    )
    assert outcome["envelope"] is None
    assert outcome["receipt"].observations["fetch_outcome"] == "UNSUPPORTED_MEDIA_TYPE"
    assert outcome["receipt"].status == "FAILED"


def test_real_local_http_oversized_response_is_refused_not_truncated_and_kept(
    _world: dict[str, Any], _local_http_target: tuple[str, int]
) -> None:
    host, port = _local_http_target
    source_identity = canonical_source_identity(f"http://{host}:{port}/oversized")
    boundary = boundary_for(admitted_hosts=[host], admitted_ports=[port], max_response_bytes=64)
    adapter = LocalHttpUrlSourceAdapter()

    outcome = observe_url_source_for_disposable_local_test(
        _world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        source_identity=source_identity,
        boundary=boundary,
        adapter=adapter,
        observed_at="2026-09-10T00:00:01Z",
    )
    assert outcome["envelope"] is None
    assert outcome["receipt"].observations["fetch_outcome"] == "OVERSIZED_RESPONSE"
    assert outcome["receipt"].status == "FAILED"


def test_real_local_http_unreachable_port_is_connection_failure(_world: dict[str, Any]) -> None:
    """A genuinely closed port is a real transport failure, classified honestly rather than
    folded into any other outcome."""

    source_identity = canonical_source_identity("http://127.0.0.1:1/status")
    boundary = boundary_for(admitted_hosts=["127.0.0.1"], admitted_ports=[1], timeout_seconds=2)
    adapter = LocalHttpUrlSourceAdapter()

    outcome = observe_url_source_for_disposable_local_test(
        _world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        source_identity=source_identity,
        boundary=boundary,
        adapter=adapter,
        observed_at="2026-09-10T00:00:01Z",
    )
    assert outcome["envelope"] is None
    assert outcome["receipt"].observations["fetch_outcome"] in ("CONNECTION_FAILURE", "TIMEOUT")
    assert outcome["receipt"].status == "UNAVAILABLE"


def test_real_local_http_host_header_carries_the_non_default_port(
    _world: dict[str, Any], _local_http_target: tuple[str, int]
) -> None:
    """Regression proof for a real review finding on this delivery's own PR (P1-R1-F2): a
    manually-built ``Host`` header that omits a non-default port is a real protocol violation an
    honest virtual-host target could reject or redirect on -- this asserts the header actually
    reaches the target as ``host:port``, not just ``host``."""

    host, _port = _local_http_target
    received_host_headers: list[str | None] = []

    class _HostCapturingHandler(BaseHTTPRequestHandler):
        def log_message(self, *args: Any) -> None:
            pass

        def do_GET(self) -> None:
            received_host_headers.append(self.headers.get("Host"))
            body = json.dumps({"status": "ok"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = HTTPServer((host, 0), _HostCapturingHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        capture_host, capture_port = server.server_address
        source_identity = canonical_source_identity(f"http://{capture_host}:{capture_port}/status")
        boundary = boundary_for(admitted_hosts=[capture_host], admitted_ports=[capture_port])
        adapter = LocalHttpUrlSourceAdapter()

        outcome = observe_url_source_for_disposable_local_test(
            _world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            source_identity=source_identity,
            boundary=boundary,
            adapter=adapter,
            observed_at="2026-09-10T00:00:01Z",
        )
        assert outcome["envelope"]["fetch_outcome"] == "OBSERVED"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert received_host_headers == [f"{capture_host}:{capture_port}"]


def _self_signed_cert(tmp_path: Path, *, hostname: str) -> tuple[str, str]:
    """Generate one throwaway self-signed certificate + key, written to *tmp_path*, for
    *hostname* -- via the stdlib ``cryptography``-free path: a minimal certificate built with
    Python's own ``ssl``/``secrets`` primitives is not available in the standard library, so this
    calls out to the local ``openssl`` binary, resolved once via ``shutil.which`` -- the identical
    fixed-executable discipline ``tests/contract/governance/test_merge_source_reflow.py``'s own
    ``_git`` helper already establishes for a test-only subprocess call."""

    import shutil
    import subprocess

    openssl = shutil.which("openssl")
    assert openssl is not None, "openssl executable not found on PATH"
    cert_path = str(tmp_path / "url_boot_https_test_cert.pem")
    key_path = str(tmp_path / "url_boot_https_test_key.pem")
    subprocess.run(  # noqa: S603 -- fixed openssl executable resolved via shutil.which above
        [
            openssl,
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-keyout",
            key_path,
            "-out",
            cert_path,
            "-days",
            "1",
            "-nodes",
            "-subj",
            f"/CN={hostname}",
            "-addext",
            f"subjectAltName=IP:{hostname}",
        ],
        check=True,
        capture_output=True,
    )
    return cert_path, key_path


def test_real_local_https_round_trip_succeeds_with_exactly_one_tls_wrap(
    tmp_path: Path, _world: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression proof for a real review finding on this delivery's own PR (P1-R1-F1): before
    the fix, ``fetch_one_hop`` opened an ``http.client.HTTPSConnection`` (whose own ``connect()``
    already performs a TLS handshake, verified against the *resolved address* rather than the
    real hostname) and then wrapped the result a second time -- so every genuine HTTPS
    observation failed as ``TLS_FAILURE`` before ever reaching a real target. This starts one
    real, disposable local HTTPS server (a throwaway self-signed certificate for ``127.0.0.1``)
    and proves a real TLS handshake plus a real HTTP response now completes successfully.

    Trusting this delivery's own throwaway test certificate (never a real Certificate Authority)
    is out of scope for what this proves -- the adapter's own ``ssl.create_default_context`` is
    swapped for a context that skips certificate-chain verification, isolating exactly the one
    property this test exists to prove: **one** TLS wrap happens, against the real hostname, and
    a real HTTP response is read back over it -- not that this package trusts an untrusted CA.
    """

    cert_path, key_path = _self_signed_cert(tmp_path, hostname="127.0.0.1")

    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: Any) -> None:
            pass

        def do_GET(self) -> None:
            body = json.dumps({"status": "ok"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = HTTPServer(("127.0.0.1", 0), _Handler)
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(certfile=cert_path, keyfile=key_path)
    server.socket = server_context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    real_create_default_context = ssl.create_default_context

    def _permissive_client_context(*args: Any, **kwargs: Any) -> ssl.SSLContext:
        # Trusting the CA itself is a stdlib/OS concern this package's own contract explicitly
        # disclaims (URL_BOOT_INDEX.md §5's own non-claim) -- only certificate-chain verification
        # is relaxed here, never SNI/hostname wiring, which stays exactly what
        # ``fetch_one_hop`` itself sets.
        context = real_create_default_context(*args, **kwargs)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context

    monkeypatch.setattr(network_module.ssl, "create_default_context", _permissive_client_context)

    try:
        host, port = server.server_address
        source_identity = canonical_source_identity(f"https://{host}:{port}/status")
        boundary = boundary_for(
            admitted_schemes=["https"], admitted_hosts=[host], admitted_ports=[port]
        )
        adapter = LocalHttpUrlSourceAdapter()

        outcome = observe_url_source_for_disposable_local_test(
            _world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            source_identity=source_identity,
            boundary=boundary,
            adapter=adapter,
            observed_at="2026-09-10T00:00:01Z",
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert outcome["envelope"]["fetch_outcome"] == "OBSERVED"
    assert outcome["envelope"]["observed_fields"] == {"status": "ok"}
    assert outcome["receipt"].status == "VERIFIED"
