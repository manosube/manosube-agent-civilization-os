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

from collections.abc import Mapping
import os
from pathlib import Path
from typing import Any

import pytest
from tests.authority_helpers import action, derived_difference, rule, scope
from tests.change_helpers import route as change_route
from tests.evidence_helpers import observation_evidence_request
from tests.fixtures.product_binding import (
    bind_project_kwargs,
    genesis_records,
    sign_github_projection_grant_declaration,
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
    "separately frozen and re-confirmed."
)

#: The bounded test target this harness would use, once frozen -- read from the environment
#: so this file can never accidentally default to a real repository. Unset in every CI and
#: local environment this delivery runs in; its absence is itself part of why every
#: ``RealGitHubAdapter`` test below is skipped, not only the explicit ``pytest.mark.skip``
#: marker.
_V3_TARGET_REPOSITORY_ENV = "MANOSUBE_P14_V3_TARGET_REPOSITORY"
_V3_TOKEN_ENV = "MANOSUBE_P14_V3_GITHUB_TOKEN"  # noqa: S105 -- an env var *name*, not a secret


def _v3_authorized() -> bool:
    """Return whether a later, separate authorization has actually configured a bounded V3
    target -- always ``False`` in this delivery, checked explicitly rather than assumed, so a
    future round that *does* receive that authorization only needs to remove the
    ``pytest.mark.skip`` markers below, not rewrite this file's own gating logic."""

    return bool(os.environ.get(_V3_TARGET_REPOSITORY_ENV)) and bool(os.environ.get(_V3_TOKEN_ENV))


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
        **kwargs,
    )


def test_v3_authorization_is_not_yet_configured_in_this_environment() -> None:
    """The one assertion this file makes without being skipped for the *live* target: proves
    the gate itself is real, not merely a comment -- this delivery's own environment
    genuinely has no V3 target configured, so the ``RealGitHubAdapter`` tests below genuinely
    cannot run live here even if their skip markers were removed by mistake."""

    assert _v3_authorized() is False


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


@pytest.mark.skip(reason=_SKIP_REASON)
def test_v3_project_a_real_difference_to_a_github_issue(tmp_path: Path) -> None:
    """Would project one canonical Difference to a GitHub Issue projection -- Issue #62's own
    V3 requirement, item 1. See the module-level controlled-adapter test above for proof this
    exact harness body is mechanically complete and runs today; only the live network call
    (``RealGitHubAdapter``) is gated."""

    target_owner, target_repo = os.environ[_V3_TARGET_REPOSITORY_ENV].split("/")
    outcome = _run_vertical_proof(
        tmp_path,
        subject_kind="difference",
        projection_kind="DIFFERENCE_ISSUE",
        target_repository={"host": "github", "owner": target_owner, "repo": target_repo},
        projection_payload={
            "title": "MANOSUBE V3 proof -- Difference (do not merge)",
            "body": "harness",
        },
        adapter=RealGitHubAdapter(token=os.environ[_V3_TOKEN_ENV]),
    )
    assert outcome["receipt"].status == "VERIFIED"


@pytest.mark.skip(reason=_SKIP_REASON)
def test_v3_project_a_real_change_to_a_github_pull_request(tmp_path: Path) -> None:
    """Would project one canonical Change to a Pull Request projection -- Issue #62's own V3
    requirement, item 2. See the controlled-adapter test above for the identical, mechanically
    complete harness body."""

    target_owner, target_repo = os.environ[_V3_TARGET_REPOSITORY_ENV].split("/")
    outcome = _run_vertical_proof(
        tmp_path,
        subject_kind="change",
        projection_kind="CHANGE_PULL_REQUEST",
        target_repository={"host": "github", "owner": target_owner, "repo": target_repo},
        projection_payload={
            "title": "MANOSUBE V3 proof -- Change (do not merge)",
            "body": "harness",
            "head_ref": "agent/v3-harness",
            "base_ref": "main",
        },
        adapter=RealGitHubAdapter(token=os.environ[_V3_TOKEN_ENV]),
    )
    assert outcome["receipt"].status == "VERIFIED"


@pytest.mark.skip(reason=_SKIP_REASON)
def test_v3_project_a_real_evidence_item_to_a_github_artifact(tmp_path: Path) -> None:
    """Would project one canonical Evidence item to a check-run projection -- Issue #62's own
    V3 requirement, item 3. ``RealGitHubAdapter.materialize`` now implements the
    ``EVIDENCE_ARTIFACT`` path completely (Structural Review Round 1, P14-R1-F5) -- disclosed
    as implemented, not merely as a remaining gap."""

    target_owner, target_repo = os.environ[_V3_TARGET_REPOSITORY_ENV].split("/")
    outcome = _run_vertical_proof(
        tmp_path,
        subject_kind="observation_evidence",
        projection_kind="EVIDENCE_ARTIFACT",
        target_repository={"host": "github", "owner": target_owner, "repo": target_repo},
        projection_payload={
            "name": "MANOSUBE V3 proof (do not merge)",
            "head_sha": "a" * 40,
            "status": "completed",
            "conclusion": "neutral",
            "output": {"title": "MANOSUBE V3 proof", "summary": "harness"},
        },
        adapter=RealGitHubAdapter(token=os.environ[_V3_TOKEN_ENV]),
    )
    assert outcome["receipt"].status == "VERIFIED"
