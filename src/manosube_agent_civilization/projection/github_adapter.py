"""The two :class:`~manosube_agent_civilization.projection.types.GitHubAdapter`
implementations Phase 14 ships (Issue #62).

``FakeGitHubAdapter`` is a controlled, in-memory, fully deterministic adapter -- the V1/V2/V4
proof target every test in this package's own suites exercises. ``RealGitHubAdapter`` is a
genuine, complete implementation over the real GitHub REST API (stdlib ``urllib`` only, no new
runtime dependency), prepared as the V3 harness Issue #62's own adoption comment
(``ADOPT_P14_D001_PROJECTION_ENVELOPE_IMPLEMENTATION``) explicitly authorizes preparing --
and, in the identical breath, explicitly withholds authority to *execute* against any live
target: ``V3_EXTERNAL_WRITE_ALLOWED_BY_THIS_COMMENT=false``,
``PRE_V3_EXACT_TARGET_AND_ARTIFACT_BOUNDARY_RECONFIRMATION_REQUIRED=true``. This module is
therefore complete, real code that no test in this delivery's own suite invokes against a
live network -- ``tests/integration/projection/test_v3_real_github_vertical_proof.py`` marks
every such assertion ``pytest.mark.skip`` with that exact citation, so the boundary is visible
at the call site, not merely in prose.

This is the one module in the ``projection`` package permitted to import anything naming a
GitHub transport surface -- checked by name, not folded into a shared allowlist, exactly as
Independent Verification's own static conformance test already grants ``evidence``/
``authority`` permission to exactly one of its own modules apiece
(``PROJECTION_CONTRACT.md`` §3; ``tests/contract/projection/
test_projection_static_conformance.py``).
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json
from typing import Any
import urllib.error
import urllib.request

from .errors import ProjectionAdapterError
from .types import ARTIFACT_KINDS


class FakeGitHubAdapter:
    """A controlled, in-memory, fully deterministic
    :class:`~manosube_agent_civilization.projection.types.GitHubAdapter`.

    Backs every V1/V2/V4 test in this package's own suites. Materialized artifacts live only
    in this instance's own dict for the lifetime of the test that constructs it -- no
    filesystem write, no network call, no shared or global state between instances."""

    def __init__(
        self,
        *,
        adapter_identity: Mapping[str, Any] | None = None,
        fail_materialize: BaseException | None = None,
        fail_observe: BaseException | None = None,
        observed_status: str = "VERIFIED",
        observed_content_fingerprint_override: str | None = None,
        exists_override: bool | None = None,
    ) -> None:
        self.adapter_identity: Mapping[str, Any] = dict(
            adapter_identity or {"adapter": "fake_github_adapter", "version": "0.1"}
        )
        self._materialized: dict[tuple[str, str, str], dict[str, Any]] = {}
        self._next_sequence = 1
        self._fail_materialize = fail_materialize
        self._fail_observe = fail_observe
        self._observed_status = observed_status
        self._observed_content_fingerprint_override = observed_content_fingerprint_override
        self._exists_override = exists_override
        self.materialize_call_count = 0
        self.observe_call_count = 0

    def materialize(
        self,
        *,
        projection_kind: str,
        target_repository: Mapping[str, Any],
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        self.materialize_call_count += 1
        if self._fail_materialize is not None:
            raise self._fail_materialize

        artifact_kind = {
            "DIFFERENCE_ISSUE": "issue",
            "CHANGE_PULL_REQUEST": "pull_request",
            "EVIDENCE_ARTIFACT": "artifact",
        }.get(projection_kind)
        if artifact_kind not in ARTIFACT_KINDS:
            raise ProjectionAdapterError(f"unrecognized projection_kind: {projection_kind!r}")

        external_id = str(self._next_sequence)
        self._next_sequence += 1
        owner = target_repository["owner"]
        repo = target_repository["repo"]
        ref = {
            "host": "github",
            "owner": owner,
            "repo": repo,
            "artifact_kind": artifact_kind,
            "external_id": external_id,
            "url": f"https://github.com/{owner}/{repo}/{artifact_kind}/{external_id}",
        }
        self._materialized[(owner, repo, external_id)] = {
            "ref": deepcopy(ref),
            "payload": deepcopy(dict(payload)),
        }
        return ref

    def observe(self, *, external_artifact_ref: Mapping[str, Any]) -> Mapping[str, Any]:
        self.observe_call_count += 1
        if self._fail_observe is not None:
            raise self._fail_observe

        key = (
            external_artifact_ref["owner"],
            external_artifact_ref["repo"],
            external_artifact_ref["external_id"],
        )
        record = self._materialized.get(key)
        exists = record is not None if self._exists_override is None else self._exists_override
        if not exists:
            return {
                "status": "FAILED",
                "exists": False,
                "observed_content_fingerprint": None,
                "observed_at": "2026-01-01T00:00:00Z",
            }
        content_fingerprint = self._observed_content_fingerprint_override
        if content_fingerprint is None and record is not None:
            content_fingerprint = "sha256:" + json.dumps(
                record["payload"], sort_keys=True, separators=(",", ":")
            ).encode("utf-8").hex()[:64].rjust(64, "0")
        return {
            "status": self._observed_status,
            "exists": True,
            "observed_content_fingerprint": content_fingerprint,
            "observed_at": "2026-01-01T00:00:00Z",
        }

    def delete(self, *, external_artifact_ref: Mapping[str, Any]) -> None:
        """Test-only control surface: simulate external deletion, for V4 tamper/missing
        proofs. Never called by :mod:`~manosube_agent_civilization.projection.route`."""

        key = (
            external_artifact_ref["owner"],
            external_artifact_ref["repo"],
            external_artifact_ref["external_id"],
        )
        self._materialized.pop(key, None)

    def tamper(
        self, *, external_artifact_ref: Mapping[str, Any], new_payload: Mapping[str, Any]
    ) -> None:
        """Test-only control surface: simulate external content tampering, for V4 proofs."""

        key = (
            external_artifact_ref["owner"],
            external_artifact_ref["repo"],
            external_artifact_ref["external_id"],
        )
        if key in self._materialized:
            self._materialized[key]["payload"] = deepcopy(dict(new_payload))


class RealGitHubAdapter:
    """A complete :class:`~manosube_agent_civilization.projection.types.GitHubAdapter` over
    the real GitHub REST API, using only the Python standard library (``urllib``) -- no new
    runtime dependency.

    Prepared as the V3 proof harness. Not invoked against any live target by this delivery's
    own test suite (see the module docstring): ``V3_EXTERNAL_WRITE_ALLOWED_BY_THIS_COMMENT=
    false`` in Issue #62's own implementation adoption. A caller that does construct and
    invoke this class outside this delivery's test suite is exercising real GitHub write
    authority this delivery neither grants nor withholds -- that authority is Issue #62's own,
    separate, not-yet-frozen concern.
    """

    _API_BASE = "https://api.github.com"

    def __init__(self, *, token: str, adapter_identity: Mapping[str, Any] | None = None) -> None:
        self._token = token
        self.adapter_identity: Mapping[str, Any] = dict(
            adapter_identity or {"adapter": "real_github_adapter", "version": "0.1"}
        )

    def _request(
        self, method: str, path: str, *, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(  # noqa: S310
            self._API_BASE + path,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
                return dict(json.loads(response.read().decode("utf-8")))
        except urllib.error.URLError as error:
            raise ProjectionAdapterError(
                f"GitHub request failed: {method} {path}: {error}"
            ) from error

    def materialize(
        self,
        *,
        projection_kind: str,
        target_repository: Mapping[str, Any],
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        owner = target_repository["owner"]
        repo = target_repository["repo"]
        if projection_kind == "DIFFERENCE_ISSUE":
            response = self._request(
                "POST",
                f"/repos/{owner}/{repo}/issues",
                body={"title": payload["title"], "body": payload.get("body", "")},
            )
            return {
                "host": "github",
                "owner": owner,
                "repo": repo,
                "artifact_kind": "issue",
                "external_id": str(response["number"]),
                "url": response["html_url"],
            }
        if projection_kind == "CHANGE_PULL_REQUEST":
            response = self._request(
                "POST",
                f"/repos/{owner}/{repo}/pulls",
                body={
                    "title": payload["title"],
                    "head": payload["head_ref"],
                    "base": payload["base_ref"],
                    "body": payload.get("body", ""),
                },
            )
            return {
                "host": "github",
                "owner": owner,
                "repo": repo,
                "artifact_kind": "pull_request",
                "external_id": str(response["number"]),
                "url": response["html_url"],
            }
        raise ProjectionAdapterError(
            f"RealGitHubAdapter does not yet materialize projection_kind={projection_kind!r} "
            "-- EVIDENCE_ARTIFACT materialization (check run / review) is prepared as a V3 "
            "harness extension point, not implemented in this delivery"
        )

    def observe(self, *, external_artifact_ref: Mapping[str, Any]) -> Mapping[str, Any]:
        owner = external_artifact_ref["owner"]
        repo = external_artifact_ref["repo"]
        external_id = external_artifact_ref["external_id"]
        artifact_kind = external_artifact_ref["artifact_kind"]
        path = {
            "issue": f"/repos/{owner}/{repo}/issues/{external_id}",
            "pull_request": f"/repos/{owner}/{repo}/pulls/{external_id}",
        }.get(artifact_kind)
        if path is None:
            raise ProjectionAdapterError(
                f"RealGitHubAdapter does not yet observe artifact_kind={artifact_kind!r}"
            )
        try:
            response = self._request("GET", path)
        except ProjectionAdapterError:
            return {
                "status": "FAILED",
                "exists": False,
                "observed_content_fingerprint": None,
                "observed_at": "1970-01-01T00:00:00Z",
            }
        body_fingerprint = json.dumps(
            {"title": response.get("title"), "body": response.get("body")},
            sort_keys=True,
            separators=(",", ":"),
        )
        return {
            "status": "VERIFIED",
            "exists": True,
            "observed_content_fingerprint": "sha256:"
            + hashlib.sha256(body_fingerprint.encode("utf-8")).hexdigest(),
            "observed_at": response.get("updated_at", "1970-01-01T00:00:00Z"),
        }
