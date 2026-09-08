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

Structural Review Round 1 (Issue #62, P14-R1-F4/F6/F7) makes three corrections both adapters
now share:

- **F4, recoverable idempotency.** ``materialize`` now takes an explicit ``correlation_key``
  (the deterministic projection mapping key) and both adapters durably associate it with the
  artifact they create; ``find_by_correlation_key`` looks that artifact back up given only the
  key, so a caller whose own Store commit failed *after* a genuine external success (or whose
  process crashed before it ever saw ``materialize``'s own return value) can retry and
  converge on the *same* artifact, never a duplicate, by calling ``find_by_correlation_key``
  before ``materialize`` on every attempt -- including the very first.
- **F6, distinct failure classes.** ``observe`` now reports one of
  :data:`~manosube_agent_civilization.projection.types.OBSERVATION_OUTCOME_KINDS` instead of a
  bare ``exists`` boolean, so a permission failure or transport outage can never be reported
  as (and mistaken for) an authoritative absence.
- **F7, a real digest.** ``FakeGitHubAdapter`` now computes its own ``observed_content_fingerprint``
  with the identical :func:`~manosube_agent_civilization.projection.observable.
  expected_observable_fingerprint` route.py itself uses to compute what to expect -- a real
  SHA-256 over the closed observable projection, never a truncated relabeling of raw bytes.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import json
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

from .errors import ProjectionAdapterError
from .observable import ARTIFACT_KIND_TO_PROJECTION_KIND, expected_observable_fingerprint
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
        observation_outcome_override: str | None = None,
        observed_content_fingerprint_override: str | None = None,
    ) -> None:
        self.adapter_identity: Mapping[str, Any] = dict(
            adapter_identity or {"adapter": "fake_github_adapter", "version": "0.1"}
        )
        self._materialized: dict[tuple[str, str, str], dict[str, Any]] = {}
        self._by_correlation_key: dict[str, tuple[str, str, str]] = {}
        self._next_sequence = 1
        self._fail_materialize = fail_materialize
        self._fail_observe = fail_observe
        self._observation_outcome_override = observation_outcome_override
        self._observed_content_fingerprint_override = observed_content_fingerprint_override
        self.materialize_call_count = 0
        self.find_by_correlation_key_call_count = 0
        self.observe_call_count = 0

    def materialize(
        self,
        *,
        projection_kind: str,
        target_repository: Mapping[str, Any],
        payload: Mapping[str, Any],
        correlation_key: str,
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
        key = (owner, repo, external_id)
        self._materialized[key] = {
            "ref": deepcopy(ref),
            "payload": deepcopy(dict(payload)),
        }
        self._by_correlation_key[correlation_key] = key
        return ref

    def find_by_correlation_key(
        self,
        *,
        correlation_key: str,
        target_repository: Mapping[str, Any],
        projection_kind: str,
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any] | None:
        self.find_by_correlation_key_call_count += 1
        key = self._by_correlation_key.get(correlation_key)
        if key is None:
            return None
        record = self._materialized.get(key)
        if record is None:
            return None
        ref: Mapping[str, Any] = record["ref"]
        return deepcopy(ref)

    def observe(self, *, external_artifact_ref: Mapping[str, Any]) -> Mapping[str, Any]:
        self.observe_call_count += 1
        if self._fail_observe is not None:
            raise self._fail_observe

        if self._observation_outcome_override is not None:
            outcome = self._observation_outcome_override
        else:
            key = (
                external_artifact_ref["owner"],
                external_artifact_ref["repo"],
                external_artifact_ref["external_id"],
            )
            outcome = "FOUND" if key in self._materialized else "NOT_FOUND"

        if outcome != "FOUND":
            return {
                "observation_outcome": outcome,
                "observed_content_fingerprint": None,
                "observed_at": "2026-01-01T00:00:00Z",
            }

        content_fingerprint: str | None
        if self._observed_content_fingerprint_override is not None:
            content_fingerprint = self._observed_content_fingerprint_override
        else:
            key = (
                external_artifact_ref["owner"],
                external_artifact_ref["repo"],
                external_artifact_ref["external_id"],
            )
            record = self._materialized.get(key)
            projection_kind = ARTIFACT_KIND_TO_PROJECTION_KIND.get(
                external_artifact_ref["artifact_kind"]
            )
            content_fingerprint = (
                None
                if record is None or projection_kind is None
                else expected_observable_fingerprint(projection_kind, record["payload"])
            )
        return {
            "observation_outcome": "FOUND",
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

    **Correlation marker (F4).** For ``issue``/``pull_request`` artifacts, the correlation key
    is embedded as a hidden HTML-comment marker appended to the artifact's own ``body``, and
    :meth:`find_by_correlation_key` recovers it via GitHub's Search API (a full-text search
    scoped to the target repository). For ``check_run`` artifacts, GitHub's own Checks API
    already carries a purpose-built idempotency field, ``external_id`` -- the correlation key
    is passed there directly, and :meth:`find_by_correlation_key` lists check runs for the
    payload's own ``head_sha`` and matches on it.
    """

    _API_BASE = "https://api.github.com"
    _CORRELATION_MARKER = "<!-- manosube-projection-correlation-key: {key} -->"

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
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            return dict(json.loads(response.read().decode("utf-8")))

    def _write_request(
        self, method: str, path: str, *, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Like :meth:`_request`, but for a write (``materialize``) call: a transport or
        HTTP failure here is a genuine write failure, always raised
        (:class:`~.errors.ProjectionAdapterError`) rather than classified into an
        observation outcome -- there is no "did it happen" question for :meth:`observe` to
        answer differently."""

        try:
            return self._request(method, path, body=body)
        except urllib.error.URLError as error:
            raise ProjectionAdapterError(f"GitHub write failed: {method} {path}: {error}") from error

    def _classify_error(self, error: urllib.error.URLError) -> str:
        """Return one of ``NOT_FOUND``/``PERMISSION_DENIED``/``UNAVAILABLE`` for *error*
        (Structural Review Round 1, P14-R1-F6) -- never collapsed into a single generic
        failure. Only an authoritative HTTP 404 is ``NOT_FOUND``; every other HTTP status
        (403 permission/rate-limit, 5xx server failure, any other non-2xx) and every
        transport-level failure (DNS, TLS, timeout, connection reset -- a plain
        ``URLError`` with no ``.code``) is an outcome that does not establish absence."""

        if isinstance(error, urllib.error.HTTPError):
            if error.code == 404:
                return "NOT_FOUND"
            if error.code in (401, 403, 429):
                return "PERMISSION_DENIED"
            return "UNAVAILABLE"
        return "UNAVAILABLE"

    def materialize(
        self,
        *,
        projection_kind: str,
        target_repository: Mapping[str, Any],
        payload: Mapping[str, Any],
        correlation_key: str,
    ) -> Mapping[str, Any]:
        owner = target_repository["owner"]
        repo = target_repository["repo"]
        if projection_kind == "DIFFERENCE_ISSUE":
            marker = self._CORRELATION_MARKER.format(key=correlation_key)
            response = self._write_request(
                "POST",
                f"/repos/{owner}/{repo}/issues",
                body={
                    "title": payload["title"],
                    "body": f"{payload.get('body', '')}\n\n{marker}",
                },
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
            marker = self._CORRELATION_MARKER.format(key=correlation_key)
            response = self._write_request(
                "POST",
                f"/repos/{owner}/{repo}/pulls",
                body={
                    "title": payload["title"],
                    "head": payload["head_ref"],
                    "base": payload["base_ref"],
                    "body": f"{payload.get('body', '')}\n\n{marker}",
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
        if projection_kind == "EVIDENCE_ARTIFACT":
            response = self._write_request(
                "POST",
                f"/repos/{owner}/{repo}/check-runs",
                body={
                    "name": payload["name"],
                    "head_sha": payload["head_sha"],
                    "external_id": correlation_key,
                    "status": payload.get("status", "completed"),
                    "conclusion": payload.get("conclusion", "neutral"),
                    "output": payload.get("output", {}),
                },
            )
            return {
                "host": "github",
                "owner": owner,
                "repo": repo,
                "artifact_kind": "check_run",
                "external_id": str(response["id"]),
                "url": response.get("html_url", ""),
            }
        raise ProjectionAdapterError(
            f"RealGitHubAdapter does not materialize projection_kind={projection_kind!r}"
        )

    def find_by_correlation_key(
        self,
        *,
        correlation_key: str,
        target_repository: Mapping[str, Any],
        projection_kind: str,
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any] | None:
        owner = target_repository["owner"]
        repo = target_repository["repo"]
        if projection_kind in ("DIFFERENCE_ISSUE", "CHANGE_PULL_REQUEST"):
            marker = self._CORRELATION_MARKER.format(key=correlation_key)
            type_qualifier = "is:issue" if projection_kind == "DIFFERENCE_ISSUE" else "is:pr"
            query = f"repo:{owner}/{repo} {type_qualifier} {marker}"
            try:
                response = self._request("GET", f"/search/issues?q={urllib.parse.quote(query)}")
            except urllib.error.URLError:
                return None
            items = response.get("items", [])
            if not items:
                return None
            artifact_kind = "issue" if projection_kind == "DIFFERENCE_ISSUE" else "pull_request"
            match = items[0]
            return {
                "host": "github",
                "owner": owner,
                "repo": repo,
                "artifact_kind": artifact_kind,
                "external_id": str(match["number"]),
                "url": match["html_url"],
            }
        if projection_kind == "EVIDENCE_ARTIFACT":
            head_sha = payload["head_sha"]
            try:
                response = self._request(
                    "GET", f"/repos/{owner}/{repo}/commits/{head_sha}/check-runs"
                )
            except urllib.error.URLError:
                return None
            for run in response.get("check_runs", []):
                if run.get("external_id") == correlation_key:
                    return {
                        "host": "github",
                        "owner": owner,
                        "repo": repo,
                        "artifact_kind": "check_run",
                        "external_id": str(run["id"]),
                        "url": run.get("html_url", ""),
                    }
            return None
        raise ProjectionAdapterError(
            f"RealGitHubAdapter does not look up projection_kind={projection_kind!r}"
        )

    def observe(self, *, external_artifact_ref: Mapping[str, Any]) -> Mapping[str, Any]:
        owner = external_artifact_ref["owner"]
        repo = external_artifact_ref["repo"]
        external_id = external_artifact_ref["external_id"]
        artifact_kind = external_artifact_ref["artifact_kind"]
        path = {
            "issue": f"/repos/{owner}/{repo}/issues/{external_id}",
            "pull_request": f"/repos/{owner}/{repo}/pulls/{external_id}",
            "check_run": f"/repos/{owner}/{repo}/check-runs/{external_id}",
        }.get(artifact_kind)
        if path is None:
            raise ProjectionAdapterError(
                f"RealGitHubAdapter does not yet observe artifact_kind={artifact_kind!r}"
            )
        try:
            response = self._request("GET", path)
        except urllib.error.URLError as error:
            outcome = self._classify_error(error)
            return {
                "observation_outcome": outcome,
                "observed_content_fingerprint": None,
                "observed_at": "1970-01-01T00:00:00Z",
            }

        projection_kind = ARTIFACT_KIND_TO_PROJECTION_KIND.get(artifact_kind)
        if artifact_kind == "check_run":
            observed_payload = {
                "name": response.get("name"),
                "head_sha": response.get("head_sha"),
                "status": response.get("status"),
                "conclusion": response.get("conclusion"),
                "output": {
                    "title": (response.get("output") or {}).get("title"),
                    "summary": (response.get("output") or {}).get("summary"),
                },
            }
        else:
            observed_payload = {
                "title": response.get("title"),
                "body": response.get("body"),
                "head_ref": (response.get("head") or {}).get("ref"),
                "base_ref": (response.get("base") or {}).get("ref"),
            }
        content_fingerprint = (
            None
            if projection_kind is None
            else expected_observable_fingerprint(projection_kind, observed_payload)
        )
        return {
            "observation_outcome": "FOUND",
            "observed_content_fingerprint": content_fingerprint,
            "observed_at": response.get("updated_at", "1970-01-01T00:00:00Z"),
        }
