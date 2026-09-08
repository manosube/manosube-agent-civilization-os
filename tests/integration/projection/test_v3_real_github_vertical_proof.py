"""Phase 14 (Issue #62), V3: real GitHub vertical proof harness.

SHUKOU's own implementation adoption
(``ADOPT_P14_D001_PROJECTION_ENVELOPE_IMPLEMENTATION``, Issue #62) authorizes implementation,
local/controlled tests, and "preparation of the V3 proof harness" -- and, in the identical
comment, explicitly withholds authority to *execute* any of it against a live target:

```text
V3_REAL_GITHUB_PROOF_REQUIRED=true
V3_TARGET_REPOSITORY_NOT_YET_FROZEN=true
V3_EXTERNAL_WRITE_ALLOWED_BY_THIS_COMMENT=false
PRE_V3_EXACT_TARGET_AND_ARTIFACT_BOUNDARY_RECONFIRMATION_REQUIRED=true
```

Every test that would perform a live write is therefore ``pytest.mark.skip``, with that exact
citation as the skip reason -- the harness exists (it constructs a real
:class:`~manosube_agent_civilization.projection.github_adapter.RealGitHubAdapter` and a real
``project_to_github`` call, over a real bound Project), but no assertion in this file runs
against a live network until the exact target repository, artifact count, naming, cleanup, and
no-merge boundary are separately frozen and re-confirmed by a further SHUKOU decision.

Structural Review Round 1 (Issue #62, P14-R1-F5) requires this harness to be genuinely
executable, not merely prepared: :func:`_run_vertical_proof` is the one shared body every
projection kind's own test calls, parameterized only by which adapter it is given. Three
tests below (``test_v3_..._with_the_controlled_adapter``) call it with the controlled
:class:`~manosube_agent_civilization.projection.github_adapter.FakeGitHubAdapter` and are
**not** skipped -- they prove the identical harness logic (real Difference/Change/Evidence
subjects, real Authority Decision grants, real payloads) runs to completion today, for all
three projection kinds, with zero live network access. The three ``RealGitHubAdapter`` tests
call the exact same function; only the adapter and the skip differ.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import json
from pathlib import Path
from typing import Any
import urllib.request

import pytest
from tests.authority_helpers import action, derived_difference, rule, scope
from tests.change_helpers import route as change_route
from tests.evidence_helpers import observation_evidence_request
from tests.fixtures.product_binding import (
    bind_project_kwargs,
    genesis_records,
    sign_github_projection_grant_declaration,
)
from tests.fixtures.v3_target_configuration import (
    V3TargetConfiguration,
    load_v3_target_configuration,
    v3_live_write_authorized,
)
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.authority.identity import github_projection_grant_id
from manosube_agent_civilization.binding import bind_project, declare_github_projection_grant
from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.change import derive_change
from manosube_agent_civilization.change.identity import (
    change_id as compute_change_id,
    change_semantic_fingerprint,
)
from manosube_agent_civilization.difference.identity import difference_id as compute_difference_id
from manosube_agent_civilization.evidence import derive_evidence
from manosube_agent_civilization.evidence.identity import evidence_semantic_fingerprint
from manosube_agent_civilization.projection import (
    FakeGitHubAdapter,
    RealGitHubAdapter,
    project_to_github,
)
from manosube_agent_civilization.projection.identity import projection_payload_fingerprint
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import FileStateStore

_SKIP_REASON = (
    "V3_EXTERNAL_WRITE_ALLOWED_BY_THIS_COMMENT=false -- ADOPT_P14_D001_PROJECTION_ENVELOPE_"
    "IMPLEMENTATION (Issue #62) authorizes preparing this harness, not executing it against "
    "a live target, until the exact repository/artifact/cleanup/no-merge boundary is "
    "separately frozen and re-confirmed, and load_v3_target_configuration()/"
    "v3_live_write_authorized() are both re-checked at collection time on every run."
)

#: Which single ``artifact_kind`` :class:`~manosube_agent_civilization.projection.
#: github_adapter.RealGitHubAdapter` actually materializes for each ``projection_kind`` --
#: the identical mapping ``github_adapter.py``'s own ``materialize`` uses. Bound here so the
#: three real-adapter tests below can require their own artifact_kind be a member of the
#: frozen configuration's own ``authorized_artifact_kinds`` (Structural Review Round 4,
#: P14-R4-F3) before ever constructing a ``RealGitHubAdapter`` call.
_PROJECTION_KIND_TO_ARTIFACT_KIND: dict[str, str] = {
    "DIFFERENCE_ISSUE": "issue",
    "CHANGE_PULL_REQUEST": "pull_request",
    "EVIDENCE_ARTIFACT": "check_run",
}


def _require_authorized_artifact_kind(config: V3TargetConfiguration, projection_kind: str) -> None:
    """Refuse to proceed unless *projection_kind*'s own real artifact_kind is a member of
    *config*'s own ``authorized_artifact_kinds`` (Structural Review Round 4, P14-R4-F3) --
    binding the frozen boundary's own artifact-kind authorization into the harness itself,
    never left as a configuration-module-only check nothing downstream re-verifies."""

    artifact_kind = _PROJECTION_KIND_TO_ARTIFACT_KIND[projection_kind]
    if artifact_kind not in config.authorized_artifact_kinds:
        raise AssertionError(
            f"projection_kind {projection_kind!r} requires artifact_kind {artifact_kind!r}, "
            f"which is not among this frozen configuration's own authorized_artifact_kinds: "
            f"{sorted(config.authorized_artifact_kinds)}"
        )


def _v3_authorized() -> bool:
    """Return whether a later, separate authorization has actually configured a bounded,
    fully validated V3 target (Structural Review Round 3, P14-R3-F3) -- always ``False`` in
    this delivery, checked explicitly rather than assumed."""

    return load_v3_target_configuration() is not None


def _v3_live_authorized() -> bool:
    """Return whether the V3 harness's own real-adapter tests may actually run live
    (Structural Review Round 4, Issue #62, P14-R4-F3): a fail-closed runtime gate requiring
    *both* a fully validated, fully bound :class:`V3TargetConfiguration` *and* the wholly
    separate, independently-gated ``v3_live_write_authorized()`` boolean -- always ``False``
    in this delivery. This function, not a hardcoded ``pytest.mark.skip``, is what the three
    real-adapter tests below are gated on, so a later round that supplies both inputs via the
    environment activates them *without any source edit* to this file."""

    return _v3_authorized() and v3_live_write_authorized()


def _bound(tmp_path: Path) -> tuple[FileStateStore, dict[str, Any]]:
    store_root = tmp_path / "backend"
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
    kwargs = bind_project_kwargs()
    result = bind_project(
        store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
    )
    return store, {
        "project_id": kwargs["project_id"],
        "project_binding_id": result["project_binding_id"],
        "genesis_state": result["committed_state"],
    }


def _commit(
    store: FileStateStore,
    project_id: str,
    current_state: dict[str, Any],
    transaction_id: str,
    records: list[tuple[str, str, Mapping[str, Any]]],
) -> dict[str, Any]:
    successor = dict(current_state)
    successor["state_revision"] = current_state["state_revision"] + 1
    successor["previous_state_fingerprint"] = current_state["semantic_fingerprint"]
    successor["lineage_head_ref"] = {"kind": "state_transition", "id": transaction_id}
    successor["semantic_fingerprint"] = fingerprint_project_state(
        successor, schema_root=SCHEMA_ROOT
    ).as_dict()
    event = {
        "schema_version": "0.1",
        "transaction_id": transaction_id,
        "event_type": "TRANSITION",
        "project_id": project_id,
        "from_revision": current_state["state_revision"],
        "to_revision": successor["state_revision"],
        "before_fingerprint": current_state["semantic_fingerprint"],
        "after_fingerprint": successor["semantic_fingerprint"],
        "after_state": successor,
        "evidence_refs": [],
        "committed_at": "2026-09-08T00:00:00Z",
    }
    store.commit(
        project_id,
        current_state["state_revision"],
        current_state["semantic_fingerprint"],
        successor,
        event,
        records=records,
    )
    return successor


def _commit_grant(
    store: FileStateStore,
    project_id: str,
    human_authority_ref: dict[str, Any],
    current_state: dict[str, Any],
    transaction_id: str,
    *,
    subject_ref: dict[str, Any],
    subject_fingerprint: str,
    projection_kind: str,
    target_repository: dict[str, Any],
    payload_fingerprint: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    grant: dict[str, Any] = {
        "schema_version": "0.1",
        "github_projection_grant_id": "",
        "project_id": project_id,
        "subject_ref": dict(subject_ref),
        "subject_fingerprint": subject_fingerprint,
        "projection_kind": projection_kind,
        "target_repository": dict(target_repository),
        "payload_fingerprint": payload_fingerprint,
        "permitted_action": "MATERIALIZE_PROJECTION",
        "status": "ACTIVE",
        "granted_by": dict(human_authority_ref),
    }
    grant["github_projection_grant_id"] = github_projection_grant_id(grant)
    next_state = _commit(
        store,
        project_id,
        current_state,
        transaction_id,
        [("github_projection_grant", grant["github_projection_grant_id"], grant)],
    )
    return (
        {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]},
        next_state,
        grant,
    )


def _commit_declaration(
    store: FileStateStore,
    project_id: str,
    project_binding_id: str,
    human_authority_ref: dict[str, Any],
    grant: dict[str, Any],
) -> dict[str, Any]:
    """Declare and commit one real, genuinely Ed25519-signed ``github_projection_grant_
    declaration`` anchoring *grant*, through the real committing route (Structural Review
    Round 2, Issue #62, P14-R2-F1) -- a Store-resolved grant alone, with no matching signed
    Human declaration anchoring it, authorizes zero adapter calls."""

    grant_ref = {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]}
    signature = sign_github_projection_grant_declaration(
        project_id=project_id,
        project_binding_id=project_binding_id,
        grant_ref=grant_ref,
        declared_by=human_authority_ref,
        subject_ref=grant["subject_ref"],
        subject_fingerprint=grant["subject_fingerprint"],
        projection_kind=grant["projection_kind"],
        target_repository=grant["target_repository"],
        payload_fingerprint=grant["payload_fingerprint"],
        permitted_action=grant["permitted_action"],
        status="ACTIVE",
        declared_at="2026-09-08T00:00:00Z",
    )
    result = declare_github_projection_grant(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        grant_ref=grant_ref,
        status="ACTIVE",
        declared_at="2026-09-08T00:00:00Z",
        signature=signature,
        schema_root=SCHEMA_ROOT,
    )
    declaration = result["github_projection_grant_declaration"]
    return {
        "kind": "github_projection_grant_declaration",
        "id": declaration["github_projection_grant_declaration_id"],
    }


def _run_vertical_proof(
    tmp_path: Path,
    *,
    subject_kind: str,
    projection_kind: str,
    target_repository: dict[str, Any],
    projection_payload: dict[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    """Project one real canonical subject of *subject_kind* to GitHub via *adapter* and
    return the outcome -- the one shared body every projection-kind test below calls
    (Structural Review Round 1, P14-R1-F5). Builds a real, genuinely-committed
    ``github_projection_grant`` so the call reaches the adapter at all."""

    store, ctx = _bound(tmp_path)
    boot_context = boot_project(
        store, project_id=ctx["project_id"], project_binding_id=ctx["project_binding_id"]
    )
    human_authority_ref = dict(boot_context.human_authority_ref)
    current_state = ctx["genesis_state"]

    kwargs: dict[str, Any] = {}
    if subject_kind == "difference":
        difference = dict(derived_difference())
        difference["project_id"] = ctx["project_id"]
        difference["difference_id"] = compute_difference_id(difference)
        subject_ref = {"kind": "difference", "id": difference["difference_id"]}
        import hashlib

        subject_fingerprint = (
            "sha256:" + hashlib.sha256(difference["difference_id"].encode("utf-8")).hexdigest()
        )
        kwargs["subject_record"] = difference
    elif subject_kind == "change":
        difference = dict(derived_difference())
        difference["project_id"] = ctx["project_id"]
        difference["difference_id"] = compute_difference_id(difference)
        _authority_input, _decision, change_request = change_route(
            difference, action(), scope(), rules=[rule(ctx["project_id"])]
        )
        change = derive_change(change_request)
        subject_ref = {"kind": "change", "id": compute_change_id(change)}
        subject_fingerprint = change_semantic_fingerprint(change)
        kwargs["subject_record"] = change
    else:
        evidence = derive_evidence(observation_evidence_request())
        current_state = _commit(
            store,
            ctx["project_id"],
            current_state,
            "TX-V3-EVIDENCE-0001",
            [("observation_evidence", evidence["evidence_id"], evidence)],
        )
        subject_ref = {"kind": "observation_evidence", "id": evidence["evidence_id"]}
        subject_fingerprint = evidence_semantic_fingerprint(evidence)

    grant_ref, current_state, grant = _commit_grant(
        store,
        ctx["project_id"],
        human_authority_ref,
        current_state,
        "TX-V3-GRANT-0001",
        subject_ref=subject_ref,
        subject_fingerprint=subject_fingerprint,
        projection_kind=projection_kind,
        target_repository=target_repository,
        payload_fingerprint=projection_payload_fingerprint(dict(projection_payload)),
    )
    # Structural Review Round 2 (P14-R2-F1): the grant's own Store persistence is never itself
    # proof a Human declared it -- a real, genuinely signed declaration anchors it too.
    declaration_ref = _commit_declaration(
        store, ctx["project_id"], ctx["project_binding_id"], human_authority_ref, grant
    )

    return project_to_github(
        store,
        project_id=ctx["project_id"],
        project_binding_id=ctx["project_binding_id"],
        subject_ref=subject_ref,
        projection_kind=projection_kind,
        target_repository=target_repository,
        projection_payload=projection_payload,
        github_authority_ref=human_authority_ref,
        materialized_at="2026-09-08T00:00:01Z",
        adapter=adapter,
        github_projection_grant_refs=[grant_ref],
        github_projection_grant_declaration_refs=[declaration_ref],
        attempt_claim_token=f"PROJECTION-ATTEMPT-V3-{projection_kind.replace('_', '-')}",
        **kwargs,
    )


def test_v3_authorization_is_not_yet_configured_in_this_environment() -> None:
    """The one assertion this file makes without being skipped for the *live* target: proves
    the gate itself is real, not merely a comment -- this delivery's own environment
    genuinely has no fully validated V3 target configured and no live-write authority granted
    (Structural Review Round 4, P14-R4-F3: the two are independently checked), so the
    ``RealGitHubAdapter`` tests below genuinely cannot run live here even if their
    ``skipif`` markers were somehow bypassed by mistake."""

    assert _v3_authorized() is False
    assert load_v3_target_configuration() is None
    assert v3_live_write_authorized() is False
    assert _v3_live_authorized() is False


# ---------------------------------------------------------------------------
# Structural Review Round 4 (P14-R4-F3): the harness's own artifact-kind binding, exercised
# directly and entirely offline -- no Store, no adapter, no network.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("projection_kind", "excluded_kind"),
    [
        ("DIFFERENCE_ISSUE", "issue"),
        ("CHANGE_PULL_REQUEST", "pull_request"),
        ("EVIDENCE_ARTIFACT", "check_run"),
    ],
)
def test_require_authorized_artifact_kind_refuses_an_unauthorized_kind(
    projection_kind: str, excluded_kind: str
) -> None:
    narrow_config = V3TargetConfiguration(
        owner=_MOCK_CONFIG.owner,
        repo=_MOCK_CONFIG.repo,
        token=_MOCK_CONFIG.token,
        change_head_ref=_MOCK_CONFIG.change_head_ref,
        change_base_ref=_MOCK_CONFIG.change_base_ref,
        evidence_head_sha=_MOCK_CONFIG.evidence_head_sha,
        artifact_naming_prefix=_MOCK_CONFIG.artifact_naming_prefix,
        cleanup_confirmed=True,
        no_merge_confirmed=True,
        authorized_artifact_kinds=frozenset(
            {"issue", "pull_request", "check_run"} - {excluded_kind}
        ),
        authorized_artifact_count=_MOCK_CONFIG.authorized_artifact_count,
    )
    with pytest.raises(AssertionError):
        _require_authorized_artifact_kind(narrow_config, projection_kind)


def test_require_authorized_artifact_kind_accepts_the_authorized_kind() -> None:
    for projection_kind in ("DIFFERENCE_ISSUE", "CHANGE_PULL_REQUEST", "EVIDENCE_ARTIFACT"):
        _require_authorized_artifact_kind(_MOCK_CONFIG, projection_kind)


# ---------------------------------------------------------------------------
# Structural Review Round 1 (P14-R1-F5): the harness itself, proven executable today via the
# controlled adapter -- for all three projection kinds, never skipped.
# ---------------------------------------------------------------------------


def test_v3_harness_projects_a_real_difference_to_an_issue_with_the_controlled_adapter(
    tmp_path: Path,
) -> None:
    outcome = _run_vertical_proof(
        tmp_path,
        subject_kind="difference",
        projection_kind="DIFFERENCE_ISSUE",
        target_repository={"host": "github", "owner": "acme", "repo": "widget"},
        projection_payload={"title": "V3 harness (Difference)", "body": "harness"},
        adapter=FakeGitHubAdapter(),
    )
    assert outcome["receipt"].status == "VERIFIED"


def test_v3_harness_projects_a_real_change_to_a_pull_request_with_the_controlled_adapter(
    tmp_path: Path,
) -> None:
    outcome = _run_vertical_proof(
        tmp_path,
        subject_kind="change",
        projection_kind="CHANGE_PULL_REQUEST",
        target_repository={"host": "github", "owner": "acme", "repo": "widget"},
        projection_payload={
            "title": "V3 harness (Change)",
            "body": "harness",
            "head_ref": "agent/v3-harness",
            "base_ref": "main",
        },
        adapter=FakeGitHubAdapter(),
    )
    assert outcome["receipt"].status == "VERIFIED"


def test_v3_harness_projects_a_real_evidence_item_to_an_artifact_with_the_controlled_adapter(
    tmp_path: Path,
) -> None:
    outcome = _run_vertical_proof(
        tmp_path,
        subject_kind="observation_evidence",
        projection_kind="EVIDENCE_ARTIFACT",
        target_repository={"host": "github", "owner": "acme", "repo": "widget"},
        projection_payload={
            "name": "V3 harness (Evidence)",
            "head_sha": "a" * 40,
            "status": "completed",
            "conclusion": "neutral",
            "output": {"title": "V3 harness", "summary": "harness"},
        },
        adapter=FakeGitHubAdapter(),
    )
    assert outcome["receipt"].status == "VERIFIED"


# ---------------------------------------------------------------------------
# The identical harness, over the real adapter -- gated on live V3 authorization.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _v3_live_authorized(), reason=_SKIP_REASON)
def test_v3_project_a_real_difference_to_a_github_issue(tmp_path: Path) -> None:
    """Would project one canonical Difference to a GitHub Issue projection -- Issue #62's own
    V3 requirement, item 1. See the module-level controlled-adapter test above for proof this
    exact harness body is mechanically complete and runs today; only the live network call
    (``RealGitHubAdapter``) is gated.

    Structural Review Round 3 (P14-R3-F3): every value below now comes from the one
    validated :class:`~tests.fixtures.v3_target_configuration.V3TargetConfiguration`.
    Structural Review Round 4 (P14-R4-F3): the gate is now the fail-closed
    ``_v3_live_authorized()`` runtime check above, not a hardcoded ``pytest.mark.skip`` --
    setting the required environment variables in a later, genuinely authorized round
    activates this test with *no source edit* to this file at all."""

    config = load_v3_target_configuration()
    assert config is not None
    assert v3_live_write_authorized()
    _require_authorized_artifact_kind(config, "DIFFERENCE_ISSUE")
    outcome = _run_vertical_proof(
        tmp_path,
        subject_kind="difference",
        projection_kind="DIFFERENCE_ISSUE",
        target_repository=config.target_repository,
        projection_payload={
            "title": f"{config.artifact_naming_prefix} -- Difference",
            "body": "harness",
        },
        adapter=RealGitHubAdapter(token=config.token),
    )
    assert outcome["receipt"].status == "VERIFIED"


@pytest.mark.skipif(not _v3_live_authorized(), reason=_SKIP_REASON)
def test_v3_project_a_real_change_to_a_github_pull_request(tmp_path: Path) -> None:
    """Would project one canonical Change to a Pull Request projection -- Issue #62's own V3
    requirement, item 2. See the controlled-adapter test above for the identical, mechanically
    complete harness body.

    Structural Review Round 3 (P14-R3-F3): ``head_ref``/``base_ref`` are the configured
    target's own existing refs, never the impossible hardcoded ``"agent/v3-harness"``/
    ``"main"`` pair Round 2's structural review flagged -- a real Pull Request can only be
    opened against refs that already exist on the frozen target. Structural Review Round 4
    (P14-R4-F3): gated by ``_v3_live_authorized()``, activatable with no source edit."""

    config = load_v3_target_configuration()
    assert config is not None
    assert v3_live_write_authorized()
    _require_authorized_artifact_kind(config, "CHANGE_PULL_REQUEST")
    outcome = _run_vertical_proof(
        tmp_path,
        subject_kind="change",
        projection_kind="CHANGE_PULL_REQUEST",
        target_repository=config.target_repository,
        projection_payload={
            "title": f"{config.artifact_naming_prefix} -- Change",
            "body": "harness",
            "head_ref": config.change_head_ref,
            "base_ref": config.change_base_ref,
        },
        adapter=RealGitHubAdapter(token=config.token),
    )
    assert outcome["receipt"].status == "VERIFIED"


@pytest.mark.skipif(not _v3_live_authorized(), reason=_SKIP_REASON)
def test_v3_project_a_real_evidence_item_to_a_github_artifact(tmp_path: Path) -> None:
    """Would project one canonical Evidence item to a check-run projection -- Issue #62's own
    V3 requirement, item 3. ``RealGitHubAdapter.materialize`` now implements the
    ``EVIDENCE_ARTIFACT`` path completely (Structural Review Round 1, P14-R1-F5) -- disclosed
    as implemented, not merely as a remaining gap.

    Structural Review Round 3 (P14-R3-F3): ``head_sha`` is the configured target's own real
    commit SHA, never the synthetic ``"a" * 40`` placeholder Round 2's structural review
    flagged as certain to be rejected by the real Checks API. Structural Review Round 4
    (P14-R4-F3): gated by ``_v3_live_authorized()``, activatable with no source edit."""

    config = load_v3_target_configuration()
    assert config is not None
    assert v3_live_write_authorized()
    _require_authorized_artifact_kind(config, "EVIDENCE_ARTIFACT")
    outcome = _run_vertical_proof(
        tmp_path,
        subject_kind="observation_evidence",
        projection_kind="EVIDENCE_ARTIFACT",
        target_repository=config.target_repository,
        projection_payload={
            "name": config.artifact_naming_prefix,
            "head_sha": config.evidence_head_sha,
            "status": "completed",
            "conclusion": "neutral",
            "output": {"title": config.artifact_naming_prefix, "summary": "harness"},
        },
        adapter=RealGitHubAdapter(token=config.token),
    )
    assert outcome["receipt"].status == "VERIFIED"


# ---------------------------------------------------------------------------
# Structural Review Round 3 (P14-R3-F3): transport fixtures proving all three
# *configured* real-adapter routes are mechanically executable -- the identical
# ``_run_vertical_proof`` harness body, over a real ``RealGitHubAdapter``, driven by a
# synthetic but fully validated ``V3TargetConfiguration``, with ``urllib.request.urlopen``
# monkeypatched to canned GitHub-shaped responses. No live network access occurs -- none of
# these three tests carry ``pytest.mark.skip``.
# ---------------------------------------------------------------------------

_MOCK_CONFIG = V3TargetConfiguration(
    owner="acme",
    repo="widget",
    token="test-token-not-a-real-secret",  # noqa: S106
    change_head_ref="agent/frozen-v3-branch",
    change_base_ref="main",
    evidence_head_sha="0123456789abcdef0123456789abcdef01234567",
    artifact_naming_prefix="MANOSUBE V3 proof (do not merge)",
    cleanup_confirmed=True,
    no_merge_confirmed=True,
    authorized_artifact_kinds=frozenset({"issue", "pull_request", "check_run"}),
    authorized_artifact_count=3,
)


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
) -> None:
    """Route every ``urlopen`` call ``RealGitHubAdapter`` makes through *handler* -- the
    identical monkeypatching pattern ``test_real_github_adapter_transport.py`` already
    establishes, duplicated here (never imported) per this package's own per-file fixture
    convention, since this file's own purpose (proving the full harness end to end) is
    genuinely distinct from that file's own (proving the adapter alone)."""

    def fake_urlopen(request: urllib.request.Request, timeout: int = 30) -> _FakeResponse:
        method = request.get_method()
        path = request.full_url[len("https://api.github.com") :]
        raw_data = request.data
        body = json.loads(raw_data.decode("utf-8")) if isinstance(raw_data, bytes) else None
        return _FakeResponse(handler(method, path, body))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)


def test_v3_configured_real_adapter_projects_a_difference_to_an_issue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner, repo = _MOCK_CONFIG.owner, _MOCK_CONFIG.repo

    def handler(method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        if method == "GET" and path.startswith("/search/issues"):
            return {"items": []}
        if method == "POST" and path == f"/repos/{owner}/{repo}/issues":
            assert body is not None
            return {
                "number": 501,
                "html_url": f"https://github.com/{owner}/{repo}/issue/501",
                "title": body["title"],
                "body": body["body"],
                "updated_at": "2026-09-08T00:00:01Z",
            }
        if method == "GET" and path == f"/repos/{owner}/{repo}/issues/501":
            return {
                "title": f"{_MOCK_CONFIG.artifact_naming_prefix} -- Difference",
                "body": "harness\n\n<!-- manosube-projection-correlation-key: ignored -->",
                "updated_at": "2026-09-08T00:00:02Z",
            }
        raise AssertionError(f"unexpected call: {method} {path}")

    _install_transport(monkeypatch, handler)
    outcome = _run_vertical_proof(
        tmp_path,
        subject_kind="difference",
        projection_kind="DIFFERENCE_ISSUE",
        target_repository=_MOCK_CONFIG.target_repository,
        projection_payload={
            "title": f"{_MOCK_CONFIG.artifact_naming_prefix} -- Difference",
            "body": "harness",
        },
        adapter=RealGitHubAdapter(token=_MOCK_CONFIG.token),
    )
    assert outcome["receipt"].status == "VERIFIED"


def test_v3_configured_real_adapter_projects_a_change_to_a_pull_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner, repo = _MOCK_CONFIG.owner, _MOCK_CONFIG.repo

    def handler(method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        if method == "GET" and path.startswith("/search/issues"):
            return {"items": []}
        if method == "POST" and path == f"/repos/{owner}/{repo}/pulls":
            assert body is not None
            return {
                "number": 502,
                "html_url": f"https://github.com/{owner}/{repo}/pull_request/502",
                "title": body["title"],
                "body": body["body"],
                "head": {"ref": body["head"]},
                "base": {"ref": body["base"]},
                "updated_at": "2026-09-08T00:00:01Z",
            }
        if method == "GET" and path == f"/repos/{owner}/{repo}/pulls/502":
            return {
                "title": f"{_MOCK_CONFIG.artifact_naming_prefix} -- Change",
                "body": "harness\n\n<!-- manosube-projection-correlation-key: ignored -->",
                "head": {"ref": _MOCK_CONFIG.change_head_ref},
                "base": {"ref": _MOCK_CONFIG.change_base_ref},
                "updated_at": "2026-09-08T00:00:02Z",
            }
        raise AssertionError(f"unexpected call: {method} {path}")

    _install_transport(monkeypatch, handler)
    outcome = _run_vertical_proof(
        tmp_path,
        subject_kind="change",
        projection_kind="CHANGE_PULL_REQUEST",
        target_repository=_MOCK_CONFIG.target_repository,
        projection_payload={
            "title": f"{_MOCK_CONFIG.artifact_naming_prefix} -- Change",
            "body": "harness",
            "head_ref": _MOCK_CONFIG.change_head_ref,
            "base_ref": _MOCK_CONFIG.change_base_ref,
        },
        adapter=RealGitHubAdapter(token=_MOCK_CONFIG.token),
    )
    assert outcome["receipt"].status == "VERIFIED"


def test_v3_configured_real_adapter_projects_an_evidence_item_to_a_check_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner, repo = _MOCK_CONFIG.owner, _MOCK_CONFIG.repo
    head_sha = _MOCK_CONFIG.evidence_head_sha

    def handler(method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        if method == "GET" and path == f"/repos/{owner}/{repo}/commits/{head_sha}/check-runs":
            return {"check_runs": []}
        if method == "POST" and path == f"/repos/{owner}/{repo}/check-runs":
            assert body is not None
            return {
                "id": 503,
                "html_url": f"https://github.com/{owner}/{repo}/check_run/503",
                "name": body["name"],
                "head_sha": body["head_sha"],
                "status": body["status"],
                "conclusion": body["conclusion"],
                "output": body["output"],
                "updated_at": "2026-09-08T00:00:01Z",
            }
        if method == "GET" and path == f"/repos/{owner}/{repo}/check-runs/503":
            return {
                "name": _MOCK_CONFIG.artifact_naming_prefix,
                "head_sha": head_sha,
                "status": "completed",
                "conclusion": "neutral",
                "output": {"title": _MOCK_CONFIG.artifact_naming_prefix, "summary": "harness"},
                "updated_at": "2026-09-08T00:00:02Z",
            }
        raise AssertionError(f"unexpected call: {method} {path}")

    _install_transport(monkeypatch, handler)
    outcome = _run_vertical_proof(
        tmp_path,
        subject_kind="observation_evidence",
        projection_kind="EVIDENCE_ARTIFACT",
        target_repository=_MOCK_CONFIG.target_repository,
        projection_payload={
            "name": _MOCK_CONFIG.artifact_naming_prefix,
            "head_sha": head_sha,
            "status": "completed",
            "conclusion": "neutral",
            "output": {"title": _MOCK_CONFIG.artifact_naming_prefix, "summary": "harness"},
        },
        adapter=RealGitHubAdapter(token=_MOCK_CONFIG.token),
    )
    assert outcome["receipt"].status == "VERIFIED"
