"""Phase 14 (Issue #62): the one public Projection route (``project_to_github``), end-to-end,
over a real ``FileStateStore`` -- V2 (controlled Adapter contract proof) and V4 (failure/tamper
proof).

A real bound Project (Phase 9 Binding), with one real, Store-committed ``observation_evidence``
record derived through the existing Evidence owner's own ``derive_evidence`` (never a bare,
schema-invalid fixture dict), a real, Store-committed ``difference`` and ``change`` record
derived through the existing Difference/Change owners' own public producers (Structural Review
Round 1, P14-R1-F2), the real Human Authority reference Boot independently re-verifies for it,
a real, Store-resolved ``github_projection_grant`` Authority Decision anchor (Structural Review
Round 1, P14-R1-F1), and a controlled :class:`~manosube_agent_civilization.projection.
github_adapter.FakeGitHubAdapter` -- proves the canonical successful route (create then reuse),
the required rejection proofs (authority mismatch, no/fabricated/mismatched Authority Decision,
unresolvable/fabricated subject, conflicting payload, adapter failure at each of materialize/
observe, a tampered/missing external artifact on replay, recoverable idempotent retry, distinct
typed observation outcomes, cross-project receipt relabeling), and the receipt hand-off into the
existing Evidence owner's own Change-Free Verification Evidence position.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from tests.authority_helpers import action, derived_difference, rule, scope
from tests.change_helpers import route as change_route
from tests.evidence_helpers import (
    change_free_verification_evidence_request,
    observation_evidence_request,
)
from tests.fixtures.product_binding import bind_project_kwargs, genesis_records
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.authority.identity import github_projection_grant_id
from manosube_agent_civilization.binding import bind_project
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
    ConflictingProjectionPayloadError,
    FakeGitHubAdapter,
    ProjectionAdapterError,
    ProjectionRequirementError,
    project_to_github,
    route_observation_receipt_to_evidence,
)
from manosube_agent_civilization.projection.identity import projection_mapping_key
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import FileStateStore

_TARGET_REPOSITORY = {"host": "github", "owner": "acme", "repo": "widget"}
#: An ``EVIDENCE_ARTIFACT`` payload's own observable fields are
#: ``name``/``head_sha``/``status``/``conclusion``/``output`` (Structural Review Round 1,
#: P14-R1-F3's own per-projection-kind observable projection) -- never ``title``/``body``,
#: which only ``DIFFERENCE_ISSUE``/``CHANGE_PULL_REQUEST`` payloads carry.
_PAYLOAD = {
    "name": "MANOSUBE Evidence Check",
    "head_sha": "a" * 40,
    "status": "completed",
    "conclusion": "neutral",
    "output": {"title": "Evidence artifact", "summary": "hello"},
}
_PERMITTED_ACTION = "MATERIALIZE_PROJECTION"


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


def _commit_records(
    store: FileStateStore,
    project_id: str,
    current_state: dict[str, Any],
    transaction_id: str,
    records: list[tuple[str, str, Mapping[str, Any]]],
) -> dict[str, Any]:
    """Commit *records* over *current_state* and return the resulting next State -- the
    shared shape every fixture-side commit in this suite uses."""

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


def _real_difference(project_id: str) -> dict[str, Any]:
    """One real, schema-valid, self-consistent Difference record -- built through the
    existing Difference owner's own public producer, then rebound to *project_id* (the
    fixture's own ``derived_difference`` hardcodes a different project) with its own
    ``difference_id`` recomputed so the record stays internally self-consistent."""

    difference = dict(derived_difference())
    difference["project_id"] = project_id
    difference["difference_id"] = compute_difference_id(difference)
    return difference


def _real_change(difference: dict[str, Any]) -> dict[str, Any]:
    """One real, schema-valid, genuinely-authorized Change record for *difference* -- built
    through the existing Authority/Change owners' own public producers, never hand-assembled."""

    _authority_input, _decision, change_request = change_route(
        difference, action(), scope(), rules=[rule(difference["project_id"])]
    )
    change: dict[str, Any] = derive_change(change_request)
    return change


def _commit_grant(
    store: FileStateStore,
    project_id: str,
    human_authority_ref: dict[str, Any],
    transaction_id: str,
    *,
    subject_ref: dict[str, Any],
    subject_fingerprint: str,
    projection_kind: str = "EVIDENCE_ARTIFACT",
    target_repository: dict[str, Any] | None = None,
    payload_fingerprint: str,
    permitted_action: str = _PERMITTED_ACTION,
    status: str = "ACTIVE",
) -> dict[str, Any]:
    """Commit one real, genuine, Store-resolvable ``github_projection_grant`` and return its
    own ``{"kind", "id"}`` reference -- the caller's own explicit grant ref, never grant
    content, mirroring Independent Verification's own Round 4 ``verifier_selection_grant``
    resolution discipline."""

    grant: dict[str, Any] = {
        "schema_version": "0.1",
        "github_projection_grant_id": "",
        "project_id": project_id,
        "subject_ref": dict(subject_ref),
        "subject_fingerprint": subject_fingerprint,
        "projection_kind": projection_kind,
        "target_repository": dict(target_repository or _TARGET_REPOSITORY),
        "payload_fingerprint": payload_fingerprint,
        "permitted_action": permitted_action,
        "status": status,
        "granted_by": dict(human_authority_ref),
    }
    grant["github_projection_grant_id"] = github_projection_grant_id(grant)
    current_state = store.load_current(project_id)
    _commit_records(
        store,
        project_id,
        current_state,
        transaction_id,
        [("github_projection_grant", grant["github_projection_grant_id"], grant)],
    )
    return {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]}


@pytest.fixture
def _world(tmp_path: Path) -> dict[str, Any]:
    store, ctx = _bound(tmp_path)
    evidence = derive_evidence(observation_evidence_request())
    evidence_id = evidence["evidence_id"]
    current_state = _commit_records(
        store,
        ctx["project_id"],
        ctx["genesis_state"],
        "TX-PROJECTION-TEST-0001",
        [("observation_evidence", evidence_id, evidence)],
    )
    boot_context = boot_project(
        store, project_id=ctx["project_id"], project_binding_id=ctx["project_binding_id"]
    )
    human_authority_ref = dict(boot_context.human_authority_ref)
    from manosube_agent_civilization.projection.identity import projection_payload_fingerprint

    evidence_subject_ref = {"kind": "observation_evidence", "id": evidence_id}
    evidence_fingerprint = evidence_semantic_fingerprint(evidence)
    grant_ref = _commit_grant(
        store,
        ctx["project_id"],
        human_authority_ref,
        "TX-PROJECTION-TEST-0002",
        subject_ref=evidence_subject_ref,
        subject_fingerprint=evidence_fingerprint,
        payload_fingerprint=projection_payload_fingerprint(dict(_PAYLOAD)),
    )
    return {
        "store": store,
        "project_id": ctx["project_id"],
        "project_binding_id": ctx["project_binding_id"],
        "evidence_id": evidence_id,
        "evidence_fingerprint": evidence_fingerprint,
        "human_authority_ref": human_authority_ref,
        "grant_ref": grant_ref,
        "current_state": current_state,
        "_next_tx": 3,
    }


def _project(world: dict[str, Any], adapter: Any, **overrides: Any) -> dict[str, Any]:
    kwargs = {
        "store": world["store"],
        "project_id": world["project_id"],
        "project_binding_id": world["project_binding_id"],
        "subject_ref": {"kind": "observation_evidence", "id": world["evidence_id"]},
        "projection_kind": "EVIDENCE_ARTIFACT",
        "target_repository": _TARGET_REPOSITORY,
        "projection_payload": _PAYLOAD,
        "github_authority_ref": world["human_authority_ref"],
        "materialized_at": "2026-09-08T00:00:01Z",
        "adapter": adapter,
        "github_projection_grant_refs": [world["grant_ref"]],
    }
    kwargs.update(overrides)
    return project_to_github(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Canonical successful route (create, then reuse)
# ---------------------------------------------------------------------------


def test_first_call_materializes_and_commits_a_new_envelope(_world: dict[str, Any]) -> None:
    adapter = FakeGitHubAdapter()
    outcome = _project(_world, adapter)
    assert outcome["reused"] is False
    assert adapter.materialize_call_count == 1
    assert adapter.find_by_correlation_key_call_count == 1
    assert adapter.observe_call_count == 1
    assert outcome["envelope"]["projection_envelope_id"].startswith("PROJECTION-")
    assert outcome["receipt"].status == "VERIFIED"
    assert outcome["receipt"].project_id == _world["project_id"]

    resolved = _world["store"].resolve_record(
        _world["project_id"], "projection_envelope", outcome["envelope"]["projection_envelope_id"]
    )
    assert resolved == outcome["envelope"]


def test_replay_with_identical_payload_reuses_and_never_remateralizes(
    _world: dict[str, Any],
) -> None:
    adapter = FakeGitHubAdapter()
    first = _project(_world, adapter)
    second = _project(_world, adapter, materialized_at="2026-09-08T00:00:02Z")
    assert second["reused"] is True
    assert adapter.materialize_call_count == 1
    assert adapter.observe_call_count == 2
    assert second["envelope"] == first["envelope"]


def test_conflicting_payload_at_the_identical_identity_refuses_with_zero_writes(
    _world: dict[str, Any],
) -> None:
    from manosube_agent_civilization.projection.identity import projection_payload_fingerprint

    adapter = FakeGitHubAdapter()
    first = _project(_world, adapter)
    envelope_id = first["envelope"]["projection_envelope_id"]
    before = _world["store"].resolve_record(
        _world["project_id"], "projection_envelope", envelope_id
    )

    different_payload = {"title": "DIFFERENT", "body": "hello"}
    # A different payload at the identical identity needs its own grant (the grant binds
    # payload_fingerprint exactly, per F1) -- committed here so the request reaches the
    # envelope-level conflict check rather than being refused earlier, at authorization.
    different_grant_ref = _commit_grant(
        _world["store"],
        _world["project_id"],
        _world["human_authority_ref"],
        "TX-PROJECTION-TEST-CONFLICT",
        subject_ref={"kind": "observation_evidence", "id": _world["evidence_id"]},
        subject_fingerprint=_world["evidence_fingerprint"],
        payload_fingerprint=projection_payload_fingerprint(different_payload),
    )

    with pytest.raises(ConflictingProjectionPayloadError):
        _project(
            _world,
            adapter,
            projection_payload=different_payload,
            github_projection_grant_refs=[different_grant_ref],
        )

    assert adapter.materialize_call_count == 1
    after = _world["store"].resolve_record(_world["project_id"], "projection_envelope", envelope_id)
    assert after == before


# ---------------------------------------------------------------------------
# Authority admission (Boot identity precondition)
# ---------------------------------------------------------------------------


def test_github_authority_ref_not_matching_the_real_human_authority_ref_refuses(
    _world: dict[str, Any],
) -> None:
    adapter = FakeGitHubAdapter()
    with pytest.raises(ProjectionRequirementError):
        _project(
            _world, adapter, github_authority_ref={"kind": "human_authority", "id": "FABRICATED"}
        )
    assert adapter.materialize_call_count == 0


# ---------------------------------------------------------------------------
# Structural Review Round 1 (P14-R1-F1): genuine, exact-binding Authority Decision
# ---------------------------------------------------------------------------


def test_no_grant_at_all_refuses_with_zero_adapter_calls(_world: dict[str, Any]) -> None:
    adapter = FakeGitHubAdapter()
    with pytest.raises(ProjectionRequirementError):
        _project(_world, adapter, github_projection_grant_refs=[])
    assert adapter.materialize_call_count == 0
    assert adapter.observe_call_count == 0


def test_unresolvable_grant_ref_refuses_with_zero_adapter_calls(_world: dict[str, Any]) -> None:
    adapter = FakeGitHubAdapter()
    with pytest.raises(ProjectionRequirementError):
        _project(
            _world,
            adapter,
            github_projection_grant_refs=[
                {"kind": "github_projection_grant", "id": "GH-PROJ-GRANT-NOPE"}
            ],
        )
    assert adapter.materialize_call_count == 0
    assert adapter.observe_call_count == 0


def test_grant_bound_to_a_different_target_repository_refuses(_world: dict[str, Any]) -> None:
    from manosube_agent_civilization.projection.identity import projection_payload_fingerprint

    adapter = FakeGitHubAdapter()
    wrong_target_grant_ref = _commit_grant(
        _world["store"],
        _world["project_id"],
        _world["human_authority_ref"],
        "TX-PROJECTION-TEST-WRONG-TARGET",
        subject_ref={"kind": "observation_evidence", "id": _world["evidence_id"]},
        subject_fingerprint=_world["evidence_fingerprint"],
        target_repository={"host": "github", "owner": "someone-else", "repo": "widget"},
        payload_fingerprint=projection_payload_fingerprint(dict(_PAYLOAD)),
    )
    with pytest.raises(ProjectionRequirementError):
        _project(_world, adapter, github_projection_grant_refs=[wrong_target_grant_ref])
    assert adapter.materialize_call_count == 0


def test_grant_bound_to_a_different_payload_fingerprint_refuses(_world: dict[str, Any]) -> None:
    from manosube_agent_civilization.projection.identity import projection_payload_fingerprint

    adapter = FakeGitHubAdapter()
    wrong_payload_grant_ref = _commit_grant(
        _world["store"],
        _world["project_id"],
        _world["human_authority_ref"],
        "TX-PROJECTION-TEST-WRONG-PAYLOAD",
        subject_ref={"kind": "observation_evidence", "id": _world["evidence_id"]},
        subject_fingerprint=_world["evidence_fingerprint"],
        payload_fingerprint=projection_payload_fingerprint({"title": "WRONG", "body": "wrong"}),
    )
    with pytest.raises(ProjectionRequirementError):
        _project(_world, adapter, github_projection_grant_refs=[wrong_payload_grant_ref])
    assert adapter.materialize_call_count == 0


def test_revoked_grant_refuses(_world: dict[str, Any]) -> None:
    from manosube_agent_civilization.projection.identity import projection_payload_fingerprint

    adapter = FakeGitHubAdapter()
    revoked_grant_ref = _commit_grant(
        _world["store"],
        _world["project_id"],
        _world["human_authority_ref"],
        "TX-PROJECTION-TEST-REVOKED",
        subject_ref={"kind": "observation_evidence", "id": _world["evidence_id"]},
        subject_fingerprint=_world["evidence_fingerprint"],
        payload_fingerprint=projection_payload_fingerprint(dict(_PAYLOAD)),
        status="REVOKED",
    )
    with pytest.raises(ProjectionRequirementError):
        _project(_world, adapter, github_projection_grant_refs=[revoked_grant_ref])
    assert adapter.materialize_call_count == 0


def test_grant_merely_owner_equal_but_fabricated_subject_refuses(_world: dict[str, Any]) -> None:
    """A grant genuinely granted by the real Human Authority (owner-equal) but bound to a
    subject that does not match this exact request still refuses -- owner identity is not
    itself an authorization decision for this exact projection (P14-R1-F1's own core finding)."""

    from manosube_agent_civilization.projection.identity import projection_payload_fingerprint

    adapter = FakeGitHubAdapter()
    fabricated_subject_grant_ref = _commit_grant(
        _world["store"],
        _world["project_id"],
        _world["human_authority_ref"],
        "TX-PROJECTION-TEST-FABRICATED-SUBJECT",
        subject_ref={"kind": "observation_evidence", "id": "EVIDENCE-FABRICATED"},
        subject_fingerprint="sha256:" + "a" * 64,
        payload_fingerprint=projection_payload_fingerprint(dict(_PAYLOAD)),
    )
    with pytest.raises(ProjectionRequirementError):
        _project(_world, adapter, github_projection_grant_refs=[fabricated_subject_grant_ref])
    assert adapter.materialize_call_count == 0


def test_grant_content_supplied_directly_instead_of_a_reference_refuses(
    _world: dict[str, Any],
) -> None:
    """Grant *content* is never an accepted argument shape -- only a ``{"kind", "id"}``
    reference, resolved through the Store (the identical discipline Independent
    Verification's own Structural Review Round 4 already established)."""

    adapter = FakeGitHubAdapter()
    with pytest.raises(ProjectionRequirementError):
        _project(
            _world,
            adapter,
            github_projection_grant_refs=[
                {
                    "schema_version": "0.1",
                    "github_projection_grant_id": "GH-PROJ-GRANT-FAKE",
                    "status": "ACTIVE",
                }
            ],
        )
    assert adapter.materialize_call_count == 0


# ---------------------------------------------------------------------------
# Subject admission (Structural Review Round 1, P14-R1-F2)
# ---------------------------------------------------------------------------


def test_unresolvable_subject_ref_refuses_before_any_adapter_call(_world: dict[str, Any]) -> None:
    adapter = FakeGitHubAdapter()
    with pytest.raises(ProjectionRequirementError):
        _project(
            _world, adapter, subject_ref={"kind": "observation_evidence", "id": "EVIDENCE-NOPE"}
        )
    assert adapter.materialize_call_count == 0


def test_projection_kind_subject_kind_mismatch_refuses(_world: dict[str, Any]) -> None:
    adapter = FakeGitHubAdapter()
    with pytest.raises(ProjectionRequirementError):
        _project(_world, adapter, projection_kind="DIFFERENCE_ISSUE")
    assert adapter.materialize_call_count == 0


def test_difference_subject_with_no_subject_record_refuses(_world: dict[str, Any]) -> None:
    adapter = FakeGitHubAdapter()
    with pytest.raises(ProjectionRequirementError):
        _project(
            _world,
            adapter,
            subject_ref={"kind": "difference", "id": "D-DOESNOTMATTER"},
            projection_kind="DIFFERENCE_ISSUE",
            subject_record=None,
        )
    assert adapter.materialize_call_count == 0


def test_difference_subject_with_fabricated_identity_refuses(_world: dict[str, Any]) -> None:
    """A caller-declared ``subject_ref.id`` that does not equal the real, recomputed identity
    of the supplied ``subject_record`` refuses -- ``D-DOESNOTMATTER`` (a bare, non-canonical
    string) can no longer be projected as if it named a real Difference (P14-R1-F2's own
    reproduction case)."""

    adapter = FakeGitHubAdapter()
    real_difference = _real_difference(_world["project_id"])
    with pytest.raises(ProjectionRequirementError):
        _project(
            _world,
            adapter,
            subject_ref={"kind": "difference", "id": "D-DOESNOTMATTER"},
            projection_kind="DIFFERENCE_ISSUE",
            subject_record=real_difference,
        )
    assert adapter.materialize_call_count == 0


def test_difference_subject_from_a_different_project_refuses(_world: dict[str, Any]) -> None:
    adapter = FakeGitHubAdapter()
    foreign_difference = dict(derived_difference())  # keeps its own, different project_id
    with pytest.raises(ProjectionRequirementError):
        _project(
            _world,
            adapter,
            subject_ref={"kind": "difference", "id": foreign_difference["difference_id"]},
            projection_kind="DIFFERENCE_ISSUE",
            subject_record=foreign_difference,
        )
    assert adapter.materialize_call_count == 0


def test_difference_subject_with_a_real_record_projects_successfully(
    _world: dict[str, Any],
) -> None:
    import hashlib

    from manosube_agent_civilization.projection.identity import projection_payload_fingerprint

    real_difference = _real_difference(_world["project_id"])
    real_id = real_difference["difference_id"]
    real_fingerprint = "sha256:" + hashlib.sha256(real_id.encode("utf-8")).hexdigest()
    subject_ref = {"kind": "difference", "id": real_id}
    issue_payload = {"title": "Difference issue", "body": "hello"}
    grant_ref = _commit_grant(
        _world["store"],
        _world["project_id"],
        _world["human_authority_ref"],
        "TX-PROJECTION-TEST-DIFFERENCE",
        subject_ref=subject_ref,
        subject_fingerprint=real_fingerprint,
        projection_kind="DIFFERENCE_ISSUE",
        payload_fingerprint=projection_payload_fingerprint(issue_payload),
    )
    adapter = FakeGitHubAdapter()
    outcome = _project(
        _world,
        adapter,
        subject_ref=subject_ref,
        projection_kind="DIFFERENCE_ISSUE",
        projection_payload=issue_payload,
        subject_record=real_difference,
        github_projection_grant_refs=[grant_ref],
    )
    assert outcome["reused"] is False
    assert outcome["envelope"]["subject_fingerprint"] == real_fingerprint
    assert outcome["receipt"].status == "VERIFIED"


def test_change_subject_with_a_fabricated_record_refuses(_world: dict[str, Any]) -> None:
    adapter = FakeGitHubAdapter()
    real_difference = _real_difference(_world["project_id"])
    real_change = _real_change(real_difference)
    fabricated_change = dict(real_change)
    fabricated_change["scope"] = {**dict(fabricated_change["scope"]), "paths": ["src/other.py"]}
    with pytest.raises(ProjectionRequirementError):
        _project(
            _world,
            adapter,
            subject_ref={"kind": "change", "id": real_change["change_id"]},
            projection_kind="CHANGE_PULL_REQUEST",
            subject_record=fabricated_change,
        )
    assert adapter.materialize_call_count == 0


def test_change_subject_with_a_real_record_projects_successfully(_world: dict[str, Any]) -> None:
    from manosube_agent_civilization.projection.identity import projection_payload_fingerprint

    real_difference = _real_difference(_world["project_id"])
    real_change = _real_change(real_difference)
    real_id = real_change["change_id"]
    real_fingerprint = change_semantic_fingerprint(real_change)
    subject_ref = {"kind": "change", "id": real_id}
    pr_payload = {
        "title": "Change PR",
        "body": "hello",
        "head_ref": "agent/change",
        "base_ref": "main",
    }
    grant_ref = _commit_grant(
        _world["store"],
        _world["project_id"],
        _world["human_authority_ref"],
        "TX-PROJECTION-TEST-CHANGE",
        subject_ref=subject_ref,
        subject_fingerprint=real_fingerprint,
        projection_kind="CHANGE_PULL_REQUEST",
        payload_fingerprint=projection_payload_fingerprint(pr_payload),
    )
    adapter = FakeGitHubAdapter()
    outcome = _project(
        _world,
        adapter,
        subject_ref=subject_ref,
        projection_kind="CHANGE_PULL_REQUEST",
        projection_payload=pr_payload,
        subject_record=real_change,
        github_projection_grant_refs=[grant_ref],
    )
    assert outcome["reused"] is False
    assert outcome["envelope"]["subject_fingerprint"] == real_fingerprint
    assert outcome["envelope"]["subject_fingerprint"] != compute_change_id(real_change)
    assert outcome["receipt"].status == "VERIFIED"


# ---------------------------------------------------------------------------
# Structural Review Round 1 (P14-R1-F3): artifact/content identity binding
# ---------------------------------------------------------------------------


def test_adapter_materialize_return_naming_a_different_repository_refuses(
    _world: dict[str, Any],
) -> None:
    class _WrongRepoAdapter(FakeGitHubAdapter):
        def materialize(self, **kwargs: Any) -> Any:
            ref = dict(super().materialize(**kwargs))
            ref["repo"] = "other-repo"
            return ref

    adapter = _WrongRepoAdapter()
    with pytest.raises(ProjectionAdapterError):
        _project(_world, adapter)
    resolved_subject = _world["store"].resolve_record(
        _world["project_id"], "observation_evidence", _world["evidence_id"]
    )
    mapping_key = projection_mapping_key(
        {"kind": "observation_evidence", "id": _world["evidence_id"]},
        evidence_semantic_fingerprint(resolved_subject),
        "EVIDENCE_ARTIFACT",
        _TARGET_REPOSITORY,
    )
    assert (
        _world["store"].resolve_record(_world["project_id"], "projection_envelope", mapping_key)
        is None
    )


def test_content_mismatch_on_replay_yields_a_failed_not_verified_receipt(
    _world: dict[str, Any],
) -> None:
    """Structural Review Round 1 (P14-R1-F3): a tampered external artifact must never yield a
    ``VERIFIED`` receipt -- only the fingerprint changing is not itself the proof; the
    receipt's own ``status`` must actually reflect the mismatch."""

    adapter = FakeGitHubAdapter()
    first = _project(_world, adapter)
    assert first["receipt"].status == "VERIFIED"
    adapter.tamper(
        external_artifact_ref=first["envelope"]["external_artifact_ref"],
        new_payload={"title": "TAMPERED", "body": "TAMPERED"},
    )
    second = _project(_world, adapter, materialized_at="2026-09-08T00:00:04Z")
    assert second["reused"] is True
    assert adapter.materialize_call_count == 1  # never recreated/repaired
    assert second["receipt"].status == "FAILED"
    assert second["receipt"].observations["exists"] is True
    assert (
        second["receipt"].observations["observed_content_fingerprint"]
        != first["receipt"].observations["observed_content_fingerprint"]
    )


def test_cross_project_receipt_relabeling_refuses(_world: dict[str, Any]) -> None:
    """Structural Review Round 1 (P14-R1-F3): a real GitHub Observation Receipt, genuinely
    produced for one project, must never be usable as Evidence for a different project --
    the explicit subproof Issue #62's own adoption and the correction both require."""

    adapter = FakeGitHubAdapter()
    outcome = _project(_world, adapter)
    request = change_free_verification_evidence_request(provenance=None)
    with pytest.raises(ProjectionRequirementError):
        route_observation_receipt_to_evidence(outcome["receipt"], "PRJ-SOME-OTHER-PROJECT", request)


# ---------------------------------------------------------------------------
# Structural Review Round 1 (P14-R1-F4): recoverable external-side-effect idempotency
# ---------------------------------------------------------------------------


def test_adapter_materialize_failure_propagates_with_zero_commit(_world: dict[str, Any]) -> None:
    adapter = FakeGitHubAdapter(fail_materialize=ProjectionAdapterError("simulated outage"))
    with pytest.raises(ProjectionAdapterError):
        _project(_world, adapter)
    assert adapter.materialize_call_count == 1  # attempted, but its result was never committed

    resolved_subject = _world["store"].resolve_record(
        _world["project_id"], "observation_evidence", _world["evidence_id"]
    )
    mapping_key = projection_mapping_key(
        {"kind": "observation_evidence", "id": _world["evidence_id"]},
        evidence_semantic_fingerprint(resolved_subject),
        "EVIDENCE_ARTIFACT",
        _TARGET_REPOSITORY,
    )
    assert (
        _world["store"].resolve_record(_world["project_id"], "projection_envelope", mapping_key)
        is None
    )


def test_adapter_observe_failure_on_first_materialization_propagates(
    _world: dict[str, Any],
) -> None:
    adapter = FakeGitHubAdapter(fail_observe=ProjectionAdapterError("simulated rate limit"))
    with pytest.raises(ProjectionAdapterError):
        _project(_world, adapter)
    # The Envelope was already committed (materialize succeeded); only the receipt failed.
    assert adapter.materialize_call_count == 1


def test_store_commit_failure_after_materialize_converges_on_retry_without_duplicate(
    _world: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The crash boundary Structural Review Round 1 (P14-R1-F4) requires: ``materialize``
    genuinely succeeds (the external artifact now exists), but the Store commit that would
    have recorded the Envelope fails. Retrying converges on the *same* external artifact via
    ``find_by_correlation_key`` -- it never calls ``materialize`` a second time."""

    import manosube_agent_civilization.projection.route as route_module
    from manosube_agent_civilization.store.commit import (
        commit_state_transition as real_commit,
    )

    call_count = {"n": 0}

    def _flaky_commit(*args: Any, **kwargs: Any) -> Any:
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated Store commit failure")
        return real_commit(*args, **kwargs)

    monkeypatch.setattr(route_module, "commit_state_transition", _flaky_commit)

    adapter = FakeGitHubAdapter()
    with pytest.raises(RuntimeError):
        _project(_world, adapter)
    assert adapter.materialize_call_count == 1
    assert adapter.find_by_correlation_key_call_count == 1

    resolved_subject = _world["store"].resolve_record(
        _world["project_id"], "observation_evidence", _world["evidence_id"]
    )
    mapping_key = projection_mapping_key(
        {"kind": "observation_evidence", "id": _world["evidence_id"]},
        evidence_semantic_fingerprint(resolved_subject),
        "EVIDENCE_ARTIFACT",
        _TARGET_REPOSITORY,
    )
    assert (
        _world["store"].resolve_record(_world["project_id"], "projection_envelope", mapping_key)
        is None
    )

    # Retry: the second attempt's own commit succeeds (call_count now == 2); materialize is
    # never called again -- find_by_correlation_key recovers the artifact the first attempt
    # genuinely created.
    outcome = _project(_world, adapter, materialized_at="2026-09-08T00:00:05Z")
    assert outcome["reused"] is False
    assert adapter.materialize_call_count == 1  # still just the one, real, external artifact
    assert adapter.find_by_correlation_key_call_count == 2
    assert (
        _world["store"].resolve_record(_world["project_id"], "projection_envelope", mapping_key)
        == outcome["envelope"]
    )


def test_missing_external_artifact_on_replay_yields_a_negative_receipt_not_a_recreation(
    _world: dict[str, Any],
) -> None:
    adapter = FakeGitHubAdapter()
    first = _project(_world, adapter)
    adapter.delete(external_artifact_ref=first["envelope"]["external_artifact_ref"])
    second = _project(_world, adapter, materialized_at="2026-09-08T00:00:03Z")
    assert second["reused"] is True
    assert adapter.materialize_call_count == 1  # never recreated
    assert second["receipt"].status == "FAILED"
    assert second["receipt"].observations["exists"] is False
    assert second["receipt"].observations["observation_outcome"] == "NOT_FOUND"


def test_adapter_without_a_readable_identity_refuses_before_materialize(
    _world: dict[str, Any],
) -> None:
    class _NoIdentityAdapter:
        def materialize(self, **kwargs: Any) -> Any:  # pragma: no cover - must never be called
            raise AssertionError("materialize must not be called")

        def find_by_correlation_key(self, **kwargs: Any) -> Any:  # pragma: no cover
            raise AssertionError("find_by_correlation_key must not be called")

        def observe(self, **kwargs: Any) -> Any:  # pragma: no cover - must never be called
            raise AssertionError("observe must not be called")

    with pytest.raises(ProjectionAdapterError):
        _project(_world, _NoIdentityAdapter())


# ---------------------------------------------------------------------------
# Structural Review Round 1 (P14-R1-F6): distinct typed observation outcomes
# ---------------------------------------------------------------------------


def test_permission_denied_observation_yields_unavailable_receipt_not_a_false_absence(
    _world: dict[str, Any],
) -> None:
    adapter = FakeGitHubAdapter()
    first = _project(_world, adapter)
    adapter._observation_outcome_override = "PERMISSION_DENIED"
    second = _project(_world, adapter, materialized_at="2026-09-08T00:00:06Z")
    assert second["reused"] is True
    assert adapter.materialize_call_count == 1
    assert second["receipt"].status == "UNAVAILABLE"
    assert second["receipt"].observations["exists"] is None
    assert second["receipt"].observations["observation_outcome"] == "PERMISSION_DENIED"
    del first  # only used to establish the envelope for reuse


def test_unavailable_observation_yields_unavailable_receipt_not_a_false_absence(
    _world: dict[str, Any],
) -> None:
    adapter = FakeGitHubAdapter()
    _project(_world, adapter)
    adapter._observation_outcome_override = "UNAVAILABLE"
    second = _project(_world, adapter, materialized_at="2026-09-08T00:00:07Z")
    assert second["receipt"].status == "UNAVAILABLE"
    assert second["receipt"].observations["exists"] is None
    assert second["receipt"].observations["observation_outcome"] == "UNAVAILABLE"


def test_adapter_observe_return_missing_observation_outcome_refuses(
    _world: dict[str, Any],
) -> None:
    class _NoOutcomeAdapter(FakeGitHubAdapter):
        def observe(self, **kwargs: Any) -> Any:
            return {"observed_content_fingerprint": None, "observed_at": "2026-01-01T00:00:00Z"}

    adapter = _NoOutcomeAdapter()
    with pytest.raises(ProjectionAdapterError):
        _project(_world, adapter)


def test_adapter_observe_found_with_no_fingerprint_refuses(_world: dict[str, Any]) -> None:
    class _EmptyFingerprintAdapter(FakeGitHubAdapter):
        def observe(self, **kwargs: Any) -> Any:
            return {
                "observation_outcome": "FOUND",
                "observed_content_fingerprint": None,
                "observed_at": "2026-01-01T00:00:00Z",
            }

    adapter = _EmptyFingerprintAdapter()
    with pytest.raises(ProjectionAdapterError):
        _project(_world, adapter)


# ---------------------------------------------------------------------------
# Structural Review Round 1 (P14-R1-F7): real SHA-256 content fingerprint
# ---------------------------------------------------------------------------


def test_fake_adapter_observed_content_fingerprint_is_a_real_independently_reproducible_sha256(
    _world: dict[str, Any],
) -> None:
    import hashlib

    from manosube_agent_civilization.projection.observable import expected_observable_projection
    from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

    adapter = FakeGitHubAdapter()
    outcome = _project(_world, adapter)
    fingerprint = outcome["receipt"].observations["observed_content_fingerprint"]
    expected = expected_observable_projection("EVIDENCE_ARTIFACT", dict(_PAYLOAD))
    independently_recomputed = "sha256:" + hashlib.sha256(canonical_json_bytes(expected)).hexdigest()
    assert fingerprint == independently_recomputed


def test_fake_adapter_fingerprint_is_collision_sensitive_to_a_single_field_change(
    _world: dict[str, Any],
) -> None:
    """F7's own required proof: two payloads differing only in one observable field must not
    share a fingerprint -- the prior truncated-hex "hash" could and did collide."""

    adapter = FakeGitHubAdapter()
    first = _project(_world, adapter)
    original_fingerprint = first["receipt"].observations["observed_content_fingerprint"]
    tampered_payload = dict(_PAYLOAD)
    # Differs from the original only in one observable field's own trailing character.
    tampered_payload["output"] = {"title": "Evidence artifact", "summary": "hellp"}
    adapter.tamper(
        external_artifact_ref=first["envelope"]["external_artifact_ref"],
        new_payload=tampered_payload,
    )
    second = _project(_world, adapter, materialized_at="2026-09-08T00:00:08Z")
    assert (
        second["receipt"].observations["observed_content_fingerprint"] != original_fingerprint
    )
    assert second["receipt"].status == "FAILED"


# ---------------------------------------------------------------------------
# Receipt -> Evidence hand-off
# ---------------------------------------------------------------------------


def test_receipt_routes_to_a_real_change_free_verification_evidence_record(
    _world: dict[str, Any],
) -> None:
    adapter = FakeGitHubAdapter()
    outcome = _project(_world, adapter)
    request = change_free_verification_evidence_request(provenance=None)
    # change_free_verification_evidence_request()'s own difference_request is a fixed fixture
    # bound to a different project_id ("PRJ-0001") than _world's own bound project -- a real
    # receipt is therefore constructed directly, carrying that same project_id, rather than
    # reusing outcome["receipt"] (which genuinely belongs to _world's own project and, per
    # P14-R1-F3's own cross-project check, could not be handed off under a different one).
    from manosube_agent_civilization.projection.types import GitHubObservationReceipt

    receipt = GitHubObservationReceipt(
        status=outcome["receipt"].status,
        projection_envelope_id=outcome["receipt"].projection_envelope_id,
        project_id=request["difference_request"]["project_id"],
        subject_ref=outcome["receipt"].subject_ref,
        external_artifact_ref=outcome["receipt"].external_artifact_ref,
        adapter_identity=outcome["receipt"].adapter_identity,
        github_authority_ref=outcome["receipt"].github_authority_ref,
        input_refs=outcome["receipt"].input_refs,
        observations=outcome["receipt"].observations,
    )
    evidence = route_observation_receipt_to_evidence(
        receipt, request["difference_request"]["project_id"], request
    )
    assert evidence["evidence_position"] == "CHANGE_FREE_VERIFICATION_EVIDENCE"
    assert evidence["verification_result_provenance"]["status"] == "VERIFIED"
    assert (
        evidence["verification_result_provenance"]["requirement_id"]
        == outcome["envelope"]["projection_envelope_id"]
    )
