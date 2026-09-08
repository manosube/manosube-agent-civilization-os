"""Phase 14 (Issue #62), Structural Review Round 2 (P14-R2-F4/F4b): transport-level contract
fixtures for ``RealGitHubAdapter``, and the correlation-marker round-trip fix.

``RealGitHubAdapter`` is real, complete code that no test elsewhere in this repository invokes
against a live network -- ``tests/integration/projection/test_v3_real_github_vertical_proof.py``
marks every live-write assertion ``pytest.mark.skip``, citing
``V3_EXTERNAL_WRITE_ALLOWED_BY_THIS_COMMENT=false``. That boundary is about *authority to
write to a real repository*, not about whether this adapter's own request/response handling
can be proven correct at all: this module proves it, entirely offline, by monkeypatching
``urllib.request.urlopen`` with canned responses shaped exactly like real GitHub REST API
payloads (Issue/PR/Check-Run creation, lookup, and search) -- never a live call, never the V3
target-repository boundary this delivery does not freeze.

Covers: the write/read observable-fingerprint round-trip through a genuine materialize/observe
pair for ``DIFFERENCE_ISSUE``, ``CHANGE_PULL_REQUEST`` and ``EVIDENCE_ARTIFACT`` (proving F4's
correlation-marker fix specifically, plus a positive control that a real content change is
still detected); ``find_by_correlation_key``'s corrected fail-closed behavior on a genuine
lookup failure (F2, reused here since ``RealGitHubAdapter`` is the one adapter this fix
touches); and ``_classify_error``'s HTTP-status classification.
"""

from __future__ import annotations

from collections.abc import Callable
import json
from typing import Any
import urllib.error
import urllib.request

import pytest

from manosube_agent_civilization.projection.errors import ProjectionAdapterError
from manosube_agent_civilization.projection.github_adapter import RealGitHubAdapter
from manosube_agent_civilization.projection.observable import expected_observable_fingerprint

_OWNER = "acme"
_REPO = "widget"
_TARGET_REPOSITORY = {"host": "github", "owner": _OWNER, "repo": _REPO}
_TOKEN = "test-token-not-a-real-secret"  # noqa: S105


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


def _install_transport(
    monkeypatch: pytest.MonkeyPatch, handler: Callable[[str, str, dict[str, Any] | None], Any]
) -> list[tuple[str, str, dict[str, Any] | None]]:
    """Route every ``urlopen`` call this adapter makes through *handler*, recording
    ``(method, path, body)`` for each call and returning that call log. *handler* returns
    either a real-shaped response payload (dict) or raises ``urllib.error.URLError``/
    ``urllib.error.HTTPError`` to simulate a transport/HTTP failure -- the identical two
    outcomes a real ``urlopen`` call can produce."""

    calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def fake_urlopen(request: urllib.request.Request, timeout: int = 30) -> _FakeResponse:
        method = request.get_method()
        path = request.full_url[len("https://api.github.com") :]
        raw_data = request.data
        body = json.loads(raw_data.decode("utf-8")) if isinstance(raw_data, bytes) else None
        calls.append((method, path, body))
        result = handler(method, path, body)
        return _FakeResponse(result)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return calls


# ---------------------------------------------------------------------------
# F4: the correlation-marker write/read round-trip
# ---------------------------------------------------------------------------


def test_issue_materialize_then_observe_round_trips_without_marker_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A genuine, untampered ``DIFFERENCE_ISSUE`` materialize/observe pair must agree: the
    marker ``materialize`` embeds in ``body`` must not leak into the fingerprint ``observe``
    reports, or a successful real materialization would immediately observe as a mismatch
    against the caller's own committed (marker-free) payload -- the exact P14-R2-F4 bug."""

    payload = {"title": "A real Difference Issue", "body": "The actual committed prose."}
    correlation_key = "PROJECTION-" + "A" * 64
    store: dict[str, Any] = {}

    def handler(method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        if method == "POST" and path == f"/repos/{_OWNER}/{_REPO}/issues":
            assert body is not None
            store["body"] = body["body"]
            store["title"] = body["title"]
            return {
                "id": 900001,
                "number": 42,
                "html_url": f"https://github.com/{_OWNER}/{_REPO}/issues/42",
                "title": body["title"],
                "body": body["body"],
                "state": "open",
                "updated_at": "2026-01-01T00:00:00Z",
            }
        if method == "GET" and path == f"/repos/{_OWNER}/{_REPO}/issues/42":
            return {
                "number": 42,
                "html_url": f"https://github.com/{_OWNER}/{_REPO}/issues/42",
                "title": store["title"],
                "body": store["body"],
                "head": None,
                "base": None,
                "updated_at": "2026-01-01T00:05:00Z",
            }
        raise AssertionError(f"unexpected call: {method} {path}")

    _install_transport(monkeypatch, handler)
    adapter = RealGitHubAdapter(token=_TOKEN)

    artifact_ref = adapter.materialize(
        projection_kind="DIFFERENCE_ISSUE",
        target_repository=_TARGET_REPOSITORY,
        payload=payload,
        correlation_key=correlation_key,
    )
    assert artifact_ref["artifact_kind"] == "issue"
    assert artifact_ref["external_id"] == "42"
    # The materialized body on GitHub's own side genuinely carries the marker -- this is not
    # itself the bug; the bug is failing to account for it when computing the observed
    # fingerprint.
    assert correlation_key in store["body"]

    observation = adapter.observe(external_artifact_ref=artifact_ref)
    assert observation["observation_outcome"] == "FOUND"
    expected_fingerprint = expected_observable_fingerprint("DIFFERENCE_ISSUE", payload)
    assert observation["observed_content_fingerprint"] == expected_fingerprint


def test_pull_request_materialize_then_observe_round_trips_without_marker_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "title": "A real Change Pull Request",
        "body": "The actual committed prose.",
        "head_ref": "agent/change-branch",
        "base_ref": "main",
    }
    correlation_key = "PROJECTION-" + "B" * 64
    store: dict[str, Any] = {}

    def handler(method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        if method == "POST" and path == f"/repos/{_OWNER}/{_REPO}/pulls":
            assert body is not None
            store["body"] = body["body"]
            store["title"] = body["title"]
            store["head"] = body["head"]
            store["base"] = body["base"]
            return {
                "id": 900002,
                "number": 7,
                "html_url": f"https://github.com/{_OWNER}/{_REPO}/pull/7",
                "title": body["title"],
                "body": body["body"],
                "head": {"ref": body["head"]},
                "base": {"ref": body["base"]},
                "updated_at": "2026-01-01T00:00:00Z",
            }
        if method == "GET" and path == f"/repos/{_OWNER}/{_REPO}/pulls/7":
            return {
                "number": 7,
                "html_url": f"https://github.com/{_OWNER}/{_REPO}/pull/7",
                "title": store["title"],
                "body": store["body"],
                "head": {"ref": store["head"]},
                "base": {"ref": store["base"]},
                "updated_at": "2026-01-01T00:05:00Z",
            }
        raise AssertionError(f"unexpected call: {method} {path}")

    _install_transport(monkeypatch, handler)
    adapter = RealGitHubAdapter(token=_TOKEN)

    artifact_ref = adapter.materialize(
        projection_kind="CHANGE_PULL_REQUEST",
        target_repository=_TARGET_REPOSITORY,
        payload=payload,
        correlation_key=correlation_key,
    )
    assert artifact_ref["artifact_kind"] == "pull_request"
    assert correlation_key in store["body"]

    observation = adapter.observe(external_artifact_ref=artifact_ref)
    assert observation["observation_outcome"] == "FOUND"
    expected_fingerprint = expected_observable_fingerprint("CHANGE_PULL_REQUEST", payload)
    assert observation["observed_content_fingerprint"] == expected_fingerprint


def test_check_run_materialize_then_observe_round_trips(monkeypatch: pytest.MonkeyPatch) -> None:
    """``EVIDENCE_ARTIFACT``/``check_run`` carries no body-embedded marker at all (GitHub's own
    ``external_id`` field is used instead), so this is the pre-existing correct case -- kept
    here as the contrast that proves F4's fix is specific to the marker-carrying kinds and
    does not disturb the kind that never needed it."""

    payload = {
        "name": "MANOSUBE Evidence Check",
        "head_sha": "f" * 40,
        "status": "completed",
        "conclusion": "neutral",
        "output": {"title": "Evidence artifact", "summary": "hello"},
    }
    correlation_key = "PROJECTION-" + "C" * 64
    store: dict[str, Any] = {}

    def handler(method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        if method == "POST" and path == f"/repos/{_OWNER}/{_REPO}/check-runs":
            assert body is not None
            store.update(body)
            return {
                "id": 555,
                "html_url": f"https://github.com/{_OWNER}/{_REPO}/runs/555",
                "name": body["name"],
                "head_sha": body["head_sha"],
                "status": body["status"],
                "conclusion": body["conclusion"],
                "output": body["output"],
                "external_id": body["external_id"],
                "updated_at": "2026-01-01T00:00:00Z",
            }
        if method == "GET" and path == f"/repos/{_OWNER}/{_REPO}/check-runs/555":
            return {
                "name": store["name"],
                "head_sha": store["head_sha"],
                "status": store["status"],
                "conclusion": store["conclusion"],
                "output": store["output"],
                "updated_at": "2026-01-01T00:05:00Z",
            }
        raise AssertionError(f"unexpected call: {method} {path}")

    _install_transport(monkeypatch, handler)
    adapter = RealGitHubAdapter(token=_TOKEN)

    artifact_ref = adapter.materialize(
        projection_kind="EVIDENCE_ARTIFACT",
        target_repository=_TARGET_REPOSITORY,
        payload=payload,
        correlation_key=correlation_key,
    )
    assert artifact_ref["artifact_kind"] == "check_run"
    assert store["external_id"] == correlation_key

    observation = adapter.observe(external_artifact_ref=artifact_ref)
    assert observation["observation_outcome"] == "FOUND"
    expected_fingerprint = expected_observable_fingerprint("EVIDENCE_ARTIFACT", payload)
    assert observation["observed_content_fingerprint"] == expected_fingerprint


def test_tampered_issue_body_is_still_detected_after_marker_stripping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The marker-stripping fix must never hide genuine tampering: a real prose change on
    GitHub's own side, alongside the identical marker, must still fingerprint-mismatch."""

    payload = {"title": "A real Difference Issue", "body": "The actual committed prose."}
    correlation_key = "PROJECTION-" + "D" * 64

    def handler(method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        if method == "POST" and path == f"/repos/{_OWNER}/{_REPO}/issues":
            assert body is not None
            return {
                "number": 43,
                "html_url": f"https://github.com/{_OWNER}/{_REPO}/issues/43",
                "title": body["title"],
                "body": body["body"],
                "updated_at": "2026-01-01T00:00:00Z",
            }
        if method == "GET" and path == f"/repos/{_OWNER}/{_REPO}/issues/43":
            marker = f"<!-- manosube-projection-correlation-key: {correlation_key} -->"
            return {
                "number": 43,
                "html_url": f"https://github.com/{_OWNER}/{_REPO}/issues/43",
                "title": payload["title"],
                "body": f"TAMPERED CONTENT, not what was committed\n\n{marker}",
                "updated_at": "2026-01-01T00:05:00Z",
            }
        raise AssertionError(f"unexpected call: {method} {path}")

    _install_transport(monkeypatch, handler)
    adapter = RealGitHubAdapter(token=_TOKEN)
    artifact_ref = adapter.materialize(
        projection_kind="DIFFERENCE_ISSUE",
        target_repository=_TARGET_REPOSITORY,
        payload=payload,
        correlation_key=correlation_key,
    )
    observation = adapter.observe(external_artifact_ref=artifact_ref)
    expected_fingerprint = expected_observable_fingerprint("DIFFERENCE_ISSUE", payload)
    assert observation["observed_content_fingerprint"] != expected_fingerprint


# ---------------------------------------------------------------------------
# F2 (reused here): find_by_correlation_key fails closed on a genuine lookup failure
# ---------------------------------------------------------------------------


def test_find_by_correlation_key_raises_on_search_transport_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        raise urllib.error.URLError("simulated DNS failure")

    _install_transport(monkeypatch, handler)
    adapter = RealGitHubAdapter(token=_TOKEN)

    with pytest.raises(ProjectionAdapterError):
        adapter.find_by_correlation_key(
            correlation_key="PROJECTION-" + "E" * 64,
            target_repository=_TARGET_REPOSITORY,
            projection_kind="DIFFERENCE_ISSUE",
            payload={"title": "x", "body": "y"},
        )


def test_find_by_correlation_key_check_run_raises_on_search_transport_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        raise urllib.error.URLError("simulated DNS failure")

    _install_transport(monkeypatch, handler)
    adapter = RealGitHubAdapter(token=_TOKEN)

    with pytest.raises(ProjectionAdapterError):
        adapter.find_by_correlation_key(
            correlation_key="PROJECTION-" + "F" * 64,
            target_repository=_TARGET_REPOSITORY,
            projection_kind="EVIDENCE_ARTIFACT",
            payload={"head_sha": "a" * 40},
        )


def test_find_by_correlation_key_returns_none_on_genuine_empty_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A real, successful, empty search result is still a confirmed "not found" -- F2's own
    fix distinguishes this from a lookup *failure*, it does not eliminate the "not found"
    case entirely."""

    def handler(method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        assert method == "GET"
        return {"total_count": 0, "items": []}

    _install_transport(monkeypatch, handler)
    adapter = RealGitHubAdapter(token=_TOKEN)

    result = adapter.find_by_correlation_key(
        correlation_key="PROJECTION-" + "0" * 64,
        target_repository=_TARGET_REPOSITORY,
        projection_kind="DIFFERENCE_ISSUE",
        payload={"title": "x", "body": "y"},
    )
    assert result is None


def test_find_by_correlation_key_finds_a_real_search_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        assert method == "GET"
        assert path.startswith("/search/issues?q=")
        return {
            "total_count": 1,
            "items": [
                {
                    "number": 99,
                    "html_url": f"https://github.com/{_OWNER}/{_REPO}/pull/99",
                }
            ],
        }

    _install_transport(monkeypatch, handler)
    adapter = RealGitHubAdapter(token=_TOKEN)

    result = adapter.find_by_correlation_key(
        correlation_key="PROJECTION-" + "1" * 64,
        target_repository=_TARGET_REPOSITORY,
        projection_kind="CHANGE_PULL_REQUEST",
        payload={"title": "x", "body": "y"},
    )
    assert result == {
        "host": "github",
        "owner": _OWNER,
        "repo": _REPO,
        "artifact_kind": "pull_request",
        "external_id": "99",
        "url": f"https://github.com/{_OWNER}/{_REPO}/pull/99",
    }


# ---------------------------------------------------------------------------
# _classify_error: HTTP-status classification (Structural Review Round 1, P14-R1-F6)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (404, "NOT_FOUND"),
        (401, "PERMISSION_DENIED"),
        (403, "PERMISSION_DENIED"),
        (429, "PERMISSION_DENIED"),
        (500, "UNAVAILABLE"),
        (503, "UNAVAILABLE"),
    ],
)
def test_observe_classifies_http_errors(
    monkeypatch: pytest.MonkeyPatch, status: int, expected: str
) -> None:
    def fake_urlopen(request: urllib.request.Request, timeout: int = 30) -> _FakeResponse:
        raise urllib.error.HTTPError(request.full_url, status, "error", {}, None)  # type: ignore[arg-type]

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    adapter = RealGitHubAdapter(token=_TOKEN)

    observation = adapter.observe(
        external_artifact_ref={
            "host": "github",
            "owner": _OWNER,
            "repo": _REPO,
            "artifact_kind": "issue",
            "external_id": "1",
            "url": f"https://github.com/{_OWNER}/{_REPO}/issues/1",
        }
    )
    assert observation["observation_outcome"] == expected
    assert observation["observed_content_fingerprint"] is None


def test_observe_transport_failure_with_no_http_status_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request: urllib.request.Request, timeout: int = 30) -> _FakeResponse:
        raise urllib.error.URLError("simulated connection reset")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    adapter = RealGitHubAdapter(token=_TOKEN)

    observation = adapter.observe(
        external_artifact_ref={
            "host": "github",
            "owner": _OWNER,
            "repo": _REPO,
            "artifact_kind": "issue",
            "external_id": "1",
            "url": f"https://github.com/{_OWNER}/{_REPO}/issues/1",
        }
    )
    assert observation["observation_outcome"] == "UNAVAILABLE"


def test_materialize_write_failure_raises_projection_adapter_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request: urllib.request.Request, timeout: int = 30) -> _FakeResponse:
        raise urllib.error.URLError("simulated write failure")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    adapter = RealGitHubAdapter(token=_TOKEN)

    with pytest.raises(ProjectionAdapterError):
        adapter.materialize(
            projection_kind="DIFFERENCE_ISSUE",
            target_repository=_TARGET_REPOSITORY,
            payload={"title": "x", "body": "y"},
            correlation_key="PROJECTION-" + "2" * 64,
        )
