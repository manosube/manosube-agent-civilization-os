"""P15-R1-F1: a real redirect to a disallowed host is never followed.

Structural Review Round 1 named two distinct network-scope escapes; the pure allowlist half is
proved in ``tests/unit/runtime/test_runtime_network_scope.py`` and
``tests/contract/runtime/test_runtime_boundary_enforcement.py``. This file proves the other
half against genuine sockets: ``LocalHttpRuntimeAdapter`` relied on ``urllib``'s own automatic
redirect handling, so a target inside the allowlist could answer ``302`` and the request would
silently continue to a host the Boundary never admitted -- the allowlist check, wherever it
lived, would have been satisfied by the *first* hop alone.

Two real, disposable local HTTP servers are started here (no VPS or cloud provider, Issue #64's
own explicit non-target):

- a **redirector** on ``127.0.0.1`` -- the one host the Boundary allows -- which answers every
  request with ``302`` pointing at the second server; and
- a **forbidden target** on ``localhost`` at a different port, which counts every request it
  ever receives.

``localhost`` and ``127.0.0.1`` are the identical machine but two different declared host
strings, and this package's network scope is deliberately an allowlist of *names*, never of
resolved addresses -- so the redirect genuinely reaches somewhere the Boundary did not admit,
while remaining entirely local. The control is the forbidden server's own request counter: it
must be exactly zero.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import threading
from typing import Any

import pytest
from tests.fixtures.runtime_world import bound, boundary_for, commit_target_identity

from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.runtime.adapter import LocalHttpRuntimeAdapter
from manosube_agent_civilization.runtime.errors import RuntimeRequirementError
from manosube_agent_civilization.runtime.route import observe_runtime_target

_DEPLOYMENT_FINGERPRINT = "sha256:" + "c" * 64

#: Mutable, module-level counters the two handler classes below write to -- a
#: ``BaseHTTPRequestHandler`` subclass is instantiated per request, so per-instance state
#: cannot be read back by the test.
_forbidden_hits: list[str] = []
_redirect_target: dict[str, str] = {}


class _ForbiddenTargetHandler(BaseHTTPRequestHandler):
    """The host the Boundary never admitted. Records every request it ever sees."""

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def do_GET(self) -> None:
        _forbidden_hits.append(self.path)
        body = json.dumps(
            {"status": "compromised", "deployment_fingerprint": _DEPLOYMENT_FINGERPRINT}
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class _RedirectorHandler(BaseHTTPRequestHandler):
    """An allowed host that answers 302 toward the forbidden one."""

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def do_GET(self) -> None:
        self.send_response(302)
        self.send_header("Location", _redirect_target["url"])
        self.send_header("Content-Length", "0")
        self.end_headers()


def _serve(handler: type[BaseHTTPRequestHandler]) -> Any:
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


@pytest.fixture
def _redirect_world(tmp_path: Path) -> Any:
    _forbidden_hits.clear()
    forbidden_server, forbidden_thread = _serve(_ForbiddenTargetHandler)
    redirector_server, redirector_thread = _serve(_RedirectorHandler)
    _redirect_target["url"] = f"http://localhost:{forbidden_server.server_address[1]}/health"

    store, ctx = bound(tmp_path)
    boot_context = boot_project(
        store, project_id=ctx["project_id"], project_binding_id=ctx["project_binding_id"]
    )
    target_identity = commit_target_identity(
        store,
        ctx["project_id"],
        ctx["project_binding_id"],
        dict(boot_context.human_authority_ref),
        deployment_fingerprint=_DEPLOYMENT_FINGERPRINT,
    )
    try:
        yield {
            "store": store,
            "project_id": ctx["project_id"],
            "project_binding_id": ctx["project_binding_id"],
            "target_identity": target_identity,
            "redirector_port": redirector_server.server_address[1],
            "forbidden_port": forbidden_server.server_address[1],
            "forbidden_url": _redirect_target["url"],
        }
    finally:
        for server, thread in (
            (redirector_server, redirector_thread),
            (forbidden_server, forbidden_thread),
        ):
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()


def test_a_real_redirect_to_a_disallowed_host_is_never_followed(
    _redirect_world: dict[str, Any],
) -> None:
    """The observation is a genuine network round trip to an allowed host that answers 302.
    The redirect must become an ordinary, honestly reported transport failure, and the
    forbidden server must never be contacted at all."""

    boundary = boundary_for(
        base_url=f"http://127.0.0.1:{_redirect_world['redirector_port']}",
        path="/health",
        permitted_fields=["status"],
        allowed_hosts=["127.0.0.1"],
        timeout_seconds=5,
    )
    outcome = observe_runtime_target(
        _redirect_world["store"],
        project_id=_redirect_world["project_id"],
        project_binding_id=_redirect_world["project_binding_id"],
        target_identity=_redirect_world["target_identity"],
        boundary=boundary,
        adapter=LocalHttpRuntimeAdapter(),
        observed_at="2026-01-01T00:30:00Z",
    )

    assert _forbidden_hits == [], (
        f"the redirect was followed to a host the Boundary never admitted: {_forbidden_hits}"
    )
    assert outcome["envelope"]["observation_outcome"] == "UNAVAILABLE"
    assert outcome["envelope"]["observed_fields"] is None
    assert outcome["receipt"].status == "UNAVAILABLE"
    # The compromised content the forbidden target would have served appears nowhere.
    assert "compromised" not in json.dumps(outcome["envelope"])


def test_the_forbidden_target_really_would_have_answered(
    _redirect_world: dict[str, Any],
) -> None:
    """The control for the control: pointed at it directly, with its own host allowed, the
    forbidden server answers a perfectly good ``OBSERVED`` observation. So the zero request
    count above is caused by the redirect never being followed, not by the second server being
    unreachable, misconfigured, or already stopped."""

    boundary = boundary_for(
        base_url=f"http://localhost:{_redirect_world['forbidden_port']}",
        path="/health",
        permitted_fields=["status"],
        allowed_hosts=["localhost"],
        timeout_seconds=5,
    )
    outcome = observe_runtime_target(
        _redirect_world["store"],
        project_id=_redirect_world["project_id"],
        project_binding_id=_redirect_world["project_binding_id"],
        target_identity=_redirect_world["target_identity"],
        boundary=boundary,
        adapter=LocalHttpRuntimeAdapter(),
        observed_at="2026-01-01T00:31:00Z",
    )
    assert _forbidden_hits == ["/health"]
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"
    assert outcome["envelope"]["observed_fields"] == {"status": "compromised"}


def test_the_adapter_itself_refuses_a_disallowed_host_even_when_called_directly(
    _redirect_world: dict[str, Any],
) -> None:
    """Defense in depth: the route already refuses a wrong-host Boundary before any adapter is
    called, but the adapter never assumes it was reached through that route. Called directly
    with a Boundary pointing outside its own declared scope, it refuses rather than connect."""

    boundary = boundary_for(
        base_url=f"http://localhost:{_redirect_world['forbidden_port']}",
        path="/health",
        permitted_fields=["status"],
        allowed_hosts=["127.0.0.1"],
    )
    with pytest.raises(RuntimeRequirementError):
        LocalHttpRuntimeAdapter().observe(
            target_identity=_redirect_world["target_identity"], boundary=boundary
        )
    assert _forbidden_hits == []
