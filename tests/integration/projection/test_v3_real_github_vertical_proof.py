"""Phase 14 (Issue #62), V3: real GitHub vertical proof harness.

SHUKOU's own implementation adoption
(``ADOPT_P14_D001_PROJECTION_ENVELOPE_IMPLEMENTATION``, Issue #62) authorizes implementation,
local/controlled tests, and "preparation of the V3 proof harness" -- and, in the identical
comment, explicitly withholds authority to execute any of it against a live target:

```text
V3_REAL_GITHUB_PROOF_REQUIRED=true
V3_TARGET_REPOSITORY_NOT_YET_FROZEN=true
V3_EXTERNAL_WRITE_ALLOWED_BY_THIS_COMMENT=false
PRE_V3_EXACT_TARGET_AND_ARTIFACT_BOUNDARY_RECONFIRMATION_REQUIRED=true
```

Every test below is therefore ``pytest.mark.skip``, with that exact citation as the skip
reason -- the harness exists (it constructs a real
:class:`~manosube_agent_civilization.projection.github_adapter.RealGitHubAdapter` and a real
``project_to_github`` call, over a real bound Project, exactly as
``test_project_to_github.py``'s own V2 suite does against the controlled
:class:`~manosube_agent_civilization.projection.github_adapter.FakeGitHubAdapter`), but no
assertion in this file runs, and no live GitHub artifact is created, until the exact target
repository, artifact count, naming, cleanup, and no-merge boundary are separately frozen and
re-confirmed by a further SHUKOU decision. This file's own presence is the disclosed
acknowledgement of that boundary, not a silent narrowing of it: a structural reviewer can see
exactly what V3 will prove and exactly why it does not run yet, in one place.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from tests.evidence_helpers import observation_evidence_request
from tests.fixtures.product_binding import bind_project_kwargs, genesis_records
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.binding import bind_project
from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.evidence import derive_evidence
from manosube_agent_civilization.projection import RealGitHubAdapter, project_to_github
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
#: local environment this delivery runs in; its absence is itself part of why every test
#: below is skipped, not only the explicit ``pytest.mark.skip`` marker.
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


def test_v3_authorization_is_not_yet_configured_in_this_environment() -> None:
    """The one assertion this file makes without being skipped: proves the gate itself is
    real, not merely a comment -- this delivery's own environment genuinely has no V3 target
    configured, so the harness below genuinely cannot run here even if the skip marker were
    removed by mistake."""

    assert _v3_authorized() is False


@pytest.mark.skip(reason=_SKIP_REASON)
def test_v3_project_a_real_difference_to_a_github_issue(tmp_path: Path) -> None:
    """Would project one canonical Difference to a GitHub Issue projection, then re-observe
    it and prove round-trip correspondence to the exact canonical identity and lineage --
    Issue #62's own V3 requirement, item 1. Left unimplemented beyond the harness shape below
    (a real ``difference`` subject requires a real materialized Difference record this
    delivery's own fixture world does not yet build) until V3 is actually authorized to run,
    since implementing the full assertion body now would be effort spent on a proof no CI or
    reviewer can actually execute or verify today."""

    raise NotImplementedError(
        "V3 Difference-to-Issue vertical proof body: implement once a real materialized "
        "Difference fixture exists and V3 target authorization is granted"
    )


@pytest.mark.skip(reason=_SKIP_REASON)
def test_v3_project_a_real_change_to_a_github_pull_request(tmp_path: Path) -> None:
    """Would project one canonical Change to a branch/commit/Pull Request projection and
    re-observe it -- Issue #62's own V3 requirement, item 2. See the Issue-projection test's
    own docstring for why the assertion body is deferred rather than half-implemented."""

    raise NotImplementedError(
        "V3 Change-to-Pull-Request vertical proof body: implement once V3 target "
        "authorization is granted"
    )


@pytest.mark.skip(reason=_SKIP_REASON)
def test_v3_project_a_real_evidence_item_to_a_github_artifact(tmp_path: Path) -> None:
    """Would project one canonical Evidence item to a check/review/artifact projection and
    re-observe it -- Issue #62's own V3 requirement, item 3. This is the one projection kind
    ``RealGitHubAdapter.materialize`` does not yet implement at all (see its own module
    docstring) -- disclosed there, not only here."""

    store, ctx = _bound(tmp_path)
    evidence = derive_evidence(observation_evidence_request())
    evidence_id = evidence["evidence_id"]
    successor = dict(ctx["genesis_state"])
    successor["state_revision"] = ctx["genesis_state"]["state_revision"] + 1
    successor["previous_state_fingerprint"] = ctx["genesis_state"]["semantic_fingerprint"]
    successor["lineage_head_ref"] = {"kind": "state_transition", "id": "TX-V3-HARNESS-0001"}
    successor["semantic_fingerprint"] = fingerprint_project_state(
        successor, schema_root=SCHEMA_ROOT
    ).as_dict()
    event = {
        "schema_version": "0.1",
        "transaction_id": "TX-V3-HARNESS-0001",
        "event_type": "TRANSITION",
        "project_id": ctx["project_id"],
        "from_revision": ctx["genesis_state"]["state_revision"],
        "to_revision": successor["state_revision"],
        "before_fingerprint": ctx["genesis_state"]["semantic_fingerprint"],
        "after_fingerprint": successor["semantic_fingerprint"],
        "after_state": successor,
        "evidence_refs": [],
        "committed_at": "2026-09-08T00:00:00Z",
    }
    store.commit(
        ctx["project_id"],
        ctx["genesis_state"]["state_revision"],
        ctx["genesis_state"]["semantic_fingerprint"],
        successor,
        event,
        records=[("observation_evidence", evidence_id, evidence)],
    )
    boot_context = boot_project(
        store, project_id=ctx["project_id"], project_binding_id=ctx["project_binding_id"]
    )
    adapter = RealGitHubAdapter(token=os.environ[_V3_TOKEN_ENV])
    target_owner, target_repo = os.environ[_V3_TARGET_REPOSITORY_ENV].split("/")
    outcome = project_to_github(
        store,
        project_id=ctx["project_id"],
        project_binding_id=ctx["project_binding_id"],
        subject_ref={"kind": "observation_evidence", "id": evidence_id},
        projection_kind="EVIDENCE_ARTIFACT",
        target_repository={"host": "github", "owner": target_owner, "repo": target_repo},
        projection_payload={"title": "MANOSUBE V3 proof (do not merge)", "body": "harness"},
        github_authority_ref=dict(boot_context.human_authority_ref),
        materialized_at="2026-09-08T00:00:01Z",
        adapter=adapter,
    )
    assert outcome["receipt"].status == "VERIFIED"
