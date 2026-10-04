"""Issue #105: the same canonical semantics hold across both observation methods.

Runs the complete canonical route -- :func:`~manosube_agent_civilization.runtime.route.
observe_runtime_target` -- twice against the identical kind of stable target fact, once through
:class:`~manosube_agent_civilization.runtime.adapter.LocalHttpRuntimeAdapter` (``HTTP_GET_BOUNDED``,
a genuine local network round trip over one disposable HTTP server this test itself starts and
stops -- the existing V3 discipline) and once through :class:`~manosube_agent_civilization.
runtime.adapter.SshRuntimeAdapter` (``SSH_EXEC_BOUNDED``, with ``subprocess.run`` mocked to
return exactly the stdout ``scripts/runtime_observation_probe.py`` itself emits).

**Evidence provenance, stated plainly**: the HTTP-transport proof here is a real transport --
an actual socket, an actual HTTP response, parsed by the real adapter. The SSH-transport proof
is a mocked subprocess call, never a real SSH connection -- no ``ssh``/``sshd`` binary is
available in this environment (confirmed via ``which``) and installing one would itself be a
machine/service modification outside this delivery's authorized scope. That specific real-SSH
vertical proof is reported pending elsewhere (the PR's own evidence section), not claimed here.

What this file actually proves, and the only thing it needs mocked evidence for: the route's own
outcome classification, receipt status, and Evidence hand-off are already fully transport-
agnostic -- nothing downstream of ``adapter.observe()`` reads ``observation_method`` at all, so a
positive observation, a transport failure, and the Evidence it hands off are structurally
identical whichever of the two methods produced them.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import threading
from typing import Any
from unittest.mock import patch

import pytest
from tests.evidence_helpers import change_free_verification_evidence_request
from tests.fixtures.runtime_world import (
    bound,
    boundary_for,
    commit_target_identity,
    ssh_boundary_for,
)

from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.runtime.adapter import LocalHttpRuntimeAdapter, SshRuntimeAdapter
from manosube_agent_civilization.runtime.evidence_handoff import (
    route_runtime_observation_to_evidence,
)
from manosube_agent_civilization.runtime.route import observe_runtime_target

_DEPLOYMENT_FINGERPRINT = "sha256:" + "c" * 64


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass  # keep test output quiet

    def do_GET(self) -> None:
        if self.path == "/health":
            body = json.dumps(
                {"hostname": "vps1", "deployment_fingerprint": _DEPLOYMENT_FINGERPRINT}
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


def _rebind_project(value: Any, old: str, new: str) -> Any:
    if isinstance(value, dict):
        return {key: _rebind_project(item, old, new) for key, item in value.items()}
    if isinstance(value, list):
        return [_rebind_project(item, old, new) for item in value]
    return new if value == old else value


def _assert_observed_and_handed_off_to_evidence(
    world: dict[str, Any], outcome: dict[str, Any]
) -> None:
    """The one shared assertion both transports must satisfy identically -- the structural
    proof this whole file exists for."""

    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"
    assert outcome["envelope"]["observed_fields"] == {"hostname": "vps1"}
    assert outcome["receipt"].status == "VERIFIED"

    resolved = world["store"].resolve_record(
        world["project_id"],
        "runtime_observation_envelope",
        outcome["envelope"]["runtime_observation_envelope_id"],
    )
    assert resolved == outcome["envelope"]

    evidence_request = change_free_verification_evidence_request(provenance=None)
    request = _rebind_project(evidence_request, "PRJ-0001", world["project_id"])
    evidence = route_runtime_observation_to_evidence(
        world["store"], outcome["receipt"], world["project_id"], request
    )
    assert evidence["evidence_position"] == "CHANGE_FREE_VERIFICATION_EVIDENCE"
    assert evidence["verification_result_provenance"]["status"] == "VERIFIED"
    assert (
        evidence["verification_result_provenance"]["requirement_id"]
        == outcome["envelope"]["runtime_observation_envelope_id"]
    )


def test_http_transport_reaches_observed_and_verified_evidence(
    _world: dict[str, Any], _local_http_target: tuple[str, int]
) -> None:
    host, port = _local_http_target
    target_identity = commit_target_identity(
        _world["store"],
        _world["project_id"],
        _world["project_binding_id"],
        _world["human_authority_ref"],
        deployment_fingerprint=_DEPLOYMENT_FINGERPRINT,
    )
    boundary = boundary_for(
        base_url=f"http://{host}:{port}",
        path="/health",
        permitted_fields=["hostname"],
        allowed_hosts=[host],
    )
    outcome = observe_runtime_target(
        _world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        target_identity=target_identity,
        boundary=boundary,
        adapter=LocalHttpRuntimeAdapter(),
        observed_at="2026-01-01T00:30:00Z",
    )
    _assert_observed_and_handed_off_to_evidence(_world, outcome)


def test_ssh_transport_reaches_observed_and_verified_evidence_through_a_mocked_subprocess(
    _world: dict[str, Any],
) -> None:
    """The SSH sibling of the test above, over the identical shared assertion. ``subprocess.run``
    is mocked to return exactly the one closed JSON line
    ``scripts/runtime_observation_probe.py`` itself prints -- this proves the route/adapter
    pipeline's own handling of that contract, not a real network/SSH transport."""

    target_identity = commit_target_identity(
        _world["store"],
        _world["project_id"],
        _world["project_binding_id"],
        _world["human_authority_ref"],
        deployment_fingerprint=_DEPLOYMENT_FINGERPRINT,
    )
    boundary = ssh_boundary_for(permitted_fields=["hostname"])
    probe_report = {
        "ok": True,
        "fields": {"hostname": "vps1", "uptime_seconds": 12345.0, "os_release": "Debian"},
        "deployment_identity": _DEPLOYMENT_FINGERPRINT,
        "reason": None,
    }
    with patch("manosube_agent_civilization.runtime.adapter.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps(probe_report) + "\n"
        mock_run.return_value.stderr = ""
        outcome = observe_runtime_target(
            _world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            target_identity=target_identity,
            boundary=boundary,
            adapter=SshRuntimeAdapter(),
            observed_at="2026-01-01T00:30:00Z",
        )
    assert mock_run.call_count == 1
    _assert_observed_and_handed_off_to_evidence(_world, outcome)


@pytest.mark.parametrize(
    ("make_adapter", "make_boundary"),
    [
        (
            lambda: LocalHttpRuntimeAdapter(),
            lambda: boundary_for(base_url="http://127.0.0.1:1", path="/health", timeout_seconds=2),
        ),
    ],
)
def test_a_genuinely_unreachable_http_target_is_unavailable_never_not_found(
    _world: dict[str, Any], make_adapter: Any, make_boundary: Any
) -> None:
    """The transport-failure sibling of the positive proof above, kept in this same file because
    it is the identical cross-transport claim: a transport-level failure must classify
    identically regardless of which observation method produced it. The HTTP half is a real
    closed port; the SSH half of the identical claim is proved
    ``test_ssh_transport_failure_never_becomes_a_false_not_found`` below, via a mocked
    connection-refused ``subprocess.run`` result."""

    target_identity = commit_target_identity(
        _world["store"],
        _world["project_id"],
        _world["project_binding_id"],
        _world["human_authority_ref"],
        deployment_fingerprint=_DEPLOYMENT_FINGERPRINT,
    )
    outcome = observe_runtime_target(
        _world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        target_identity=target_identity,
        boundary=make_boundary(),
        adapter=make_adapter(),
        observed_at="2026-01-01T00:31:00Z",
    )
    assert outcome["envelope"]["observation_outcome"] in ("UNAVAILABLE", "TIMEOUT")
    assert outcome["envelope"]["observation_outcome"] != "NOT_FOUND"
    assert outcome["receipt"].status == "UNAVAILABLE"


def test_ssh_transport_failure_never_becomes_a_false_not_found(_world: dict[str, Any]) -> None:
    """A genuine ``ssh`` connection failure (exit 255, no parseable probe report, no
    "permission denied" text) must classify as ``UNAVAILABLE`` -- never the authoritative
    absence ``NOT_FOUND`` means -- the identical claim the HTTP-side closed-port test above
    proves, through the SSH adapter's own distinct failure path."""

    target_identity = commit_target_identity(
        _world["store"],
        _world["project_id"],
        _world["project_binding_id"],
        _world["human_authority_ref"],
        deployment_fingerprint=_DEPLOYMENT_FINGERPRINT,
    )
    boundary = ssh_boundary_for(permitted_fields=["hostname"])
    with patch("manosube_agent_civilization.runtime.adapter.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 255
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "ssh: connect to host 127.0.0.1 port 22: Connection refused"
        outcome = observe_runtime_target(
            _world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            target_identity=target_identity,
            boundary=boundary,
            adapter=SshRuntimeAdapter(),
            observed_at="2026-01-01T00:31:00Z",
        )
    assert outcome["envelope"]["observation_outcome"] == "UNAVAILABLE"
    assert outcome["receipt"].status == "UNAVAILABLE"
