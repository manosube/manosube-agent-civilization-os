"""Phase 14 (Issue #62), Structural Review Round 2 (P14-R2-F3): independent Store
corroboration of a ``GitHubObservationReceipt`` at hand-off, over a real ``FileStateStore``.

Deliberately a separate, self-contained fixture world from ``test_project_to_github.py``'s
own -- it needs to construct *forged* ``GitHubObservationReceipt`` instances directly (a
receipt is a plain, publicly constructible dataclass, exactly the gap this finding closes),
which the other suite's own fixtures have no reason to expose.

The Round 1 fix (``receipt.project_id == project_id``) compared a publicly settable field
against itself -- a caller could copy a genuine receipt, overwrite ``project_id``, and pass
the same value both places, and the check would pass trivially. This suite proves the Round 2
fix instead: ``route_observation_receipt_to_evidence`` now resolves ``receipt.projection_
envelope_id`` under the *requested* project's own Store partition and cross-checks
``subject_ref``/``external_artifact_ref``/``github_authority_ref`` against the real, resolved
Envelope -- never trusting the receipt's own self-reported copies of any of them.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from tests.evidence_helpers import (
    change_free_verification_evidence_request,
    observation_evidence_request,
)
from tests.fixtures.product_binding import (
    bind_project_kwargs,
    genesis_records,
    sign_github_projection_grant_declaration,
)
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.authority.identity import github_projection_grant_id
from manosube_agent_civilization.binding import bind_project, declare_github_projection_grant
from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.evidence import derive_evidence
from manosube_agent_civilization.evidence.identity import evidence_semantic_fingerprint
from manosube_agent_civilization.projection import (
    FakeGitHubAdapter,
    GitHubObservationReceipt,
    ProjectionRequirementError,
    project_to_github,
    route_observation_receipt_to_evidence,
)
from manosube_agent_civilization.projection.identity import projection_payload_fingerprint
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import FileStateStore

_TARGET_REPOSITORY = {"host": "github", "owner": "acme", "repo": "receipt-corroboration"}
_PAYLOAD = {
    "name": "MANOSUBE Evidence Check",
    "head_sha": "c" * 40,
    "status": "completed",
    "conclusion": "neutral",
    "output": {"title": "Evidence artifact", "summary": "hello"},
}
_PERMITTED_ACTION = "MATERIALIZE_PROJECTION"


def _commit_records(
    store: FileStateStore,
    project_id: str,
    current_state: dict[str, Any],
    transaction_id: str,
    records: list[tuple[str, str, Mapping[str, Any]]],
    committed_at: str = "2026-09-08T00:00:00Z",
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
        "committed_at": committed_at,
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


def _bind_and_project(
    tmp_path_segment: str, tmp_path: Path, *, repo: str = "receipt-corroboration"
) -> dict[str, Any]:
    """Build one fully independent, real, bound project (its own ``FileStateStore`` root)
    and genuinely materialize+commit one Projection Envelope in it -- the base every test in
    this suite either uses honestly or forges from.

    *repo* is deliberately overridable: two worlds built from the identical
    ``bind_project_kwargs()`` fixture otherwise produce a *content-identical* Envelope
    (``projection_mapping_key`` never includes ``project_id``), which would make a genuine
    cross-project test accidentally pass for the wrong reason -- both stores would honestly
    hold the identical envelope. A distinct target repository per world keeps the two
    Envelopes genuinely distinct, so resolving one world's envelope id under the other
    world's Store fails for the real reason this suite exists to prove."""

    store_root = tmp_path / tmp_path_segment
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
    kwargs = bind_project_kwargs()
    result = bind_project(
        store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
    )
    project_id = kwargs["project_id"]
    project_binding_id = result["project_binding_id"]
    genesis_state = result["committed_state"]

    evidence = derive_evidence(observation_evidence_request())
    evidence_id = evidence["evidence_id"]
    current_state = _commit_records(
        store,
        project_id,
        genesis_state,
        f"TX-RECEIPT-TEST-{tmp_path_segment.upper()}-0001",
        [("observation_evidence", evidence_id, evidence)],
    )
    boot_context = boot_project(store, project_id=project_id, project_binding_id=project_binding_id)
    human_authority_ref = dict(boot_context.human_authority_ref)
    evidence_subject_ref = {"kind": "observation_evidence", "id": evidence_id}
    evidence_fingerprint = evidence_semantic_fingerprint(evidence)
    payload_fingerprint = projection_payload_fingerprint(dict(_PAYLOAD))
    target_repository = {"host": "github", "owner": "acme", "repo": repo}

    grant: dict[str, Any] = {
        "schema_version": "0.1",
        "github_projection_grant_id": "",
        "project_id": project_id,
        "subject_ref": dict(evidence_subject_ref),
        "subject_fingerprint": evidence_fingerprint,
        "projection_kind": "EVIDENCE_ARTIFACT",
        "target_repository": dict(target_repository),
        "payload_fingerprint": payload_fingerprint,
        "permitted_action": _PERMITTED_ACTION,
        "status": "ACTIVE",
        "granted_by": dict(human_authority_ref),
    }
    grant["github_projection_grant_id"] = github_projection_grant_id(grant)
    current_state = _commit_records(
        store,
        project_id,
        current_state,
        f"TX-RECEIPT-TEST-{tmp_path_segment.upper()}-0002",
        [("github_projection_grant", grant["github_projection_grant_id"], grant)],
    )
    grant_ref = {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]}
    declaration_result = declare_github_projection_grant(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        grant_ref=grant_ref,
        status="ACTIVE",
        declared_at="2026-09-08T00:00:00Z",
        signature=sign_github_projection_grant_declaration(
            project_id=project_id,
            project_binding_id=project_binding_id,
            grant_ref=grant_ref,
            declared_by=human_authority_ref,
            subject_ref=evidence_subject_ref,
            subject_fingerprint=evidence_fingerprint,
            projection_kind="EVIDENCE_ARTIFACT",
            target_repository=target_repository,
            payload_fingerprint=payload_fingerprint,
            permitted_action=_PERMITTED_ACTION,
            status="ACTIVE",
            declared_at="2026-09-08T00:00:00Z",
        ),
        schema_root=SCHEMA_ROOT,
    )
    declaration = declaration_result["github_projection_grant_declaration"]
    declaration_ref = {
        "kind": "github_projection_grant_declaration",
        "id": declaration["github_projection_grant_declaration_id"],
    }

    adapter = FakeGitHubAdapter()
    outcome = project_to_github(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        subject_ref=evidence_subject_ref,
        projection_kind="EVIDENCE_ARTIFACT",
        target_repository=target_repository,
        projection_payload=_PAYLOAD,
        github_authority_ref=human_authority_ref,
        materialized_at="2026-09-08T00:00:01Z",
        adapter=adapter,
        github_projection_grant_refs=[grant_ref],
        github_projection_grant_declaration_refs=[declaration_ref],
        attempt_claim_token=f"PROJECTION-ATTEMPT-{tmp_path_segment.upper()}",
    )

    return {
        "store": store,
        "project_id": project_id,
        "receipt": outcome["receipt"],
        "envelope": outcome["envelope"],
        "adapter": adapter,
    }


@pytest.fixture
def _worldA(tmp_path: Path) -> dict[str, Any]:
    return _bind_and_project("projectA", tmp_path)


@pytest.fixture
def _worldB(tmp_path: Path) -> dict[str, Any]:
    return _bind_and_project("projectB", tmp_path, repo="receipt-corroboration-b")


def _rebind_project(value: Any, old_project_id: str, new_project_id: str) -> Any:
    """Recursively replace every exact *old_project_id* string occurrence with
    *new_project_id* -- ``change_free_verification_evidence_request``'s own ``difference_
    request`` is a fixed fixture bound to ``"PRJ-0001"``, never this suite's own real bound
    project, and since this route now independently resolves the receipt's own Projection
    Envelope from the *requested* project's own Store, the request's own project must
    genuinely be the one the receipt was produced under."""

    if isinstance(value, dict):
        return {
            key: _rebind_project(item, old_project_id, new_project_id)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_rebind_project(item, old_project_id, new_project_id) for item in value]
    if value == old_project_id:
        return new_project_id
    return value


def _request(project_id: str) -> dict[str, Any]:
    rebound: dict[str, Any] = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", project_id
    )
    return rebound


# ---------------------------------------------------------------------------
# Positive route
# ---------------------------------------------------------------------------


def test_genuine_receipt_against_its_own_store_and_project_succeeds(
    _worldA: dict[str, Any],
) -> None:
    evidence = route_observation_receipt_to_evidence(
        _worldA["store"],
        _worldA["receipt"],
        _worldA["project_id"],
        _request(_worldA["project_id"]),
        adapter=_worldA["adapter"],
    )
    assert evidence["target"]["project_id"] == _worldA["project_id"]


# ---------------------------------------------------------------------------
# Structural Review Round 2 (P14-R2-F3): independent corroboration against the
# real, committed Envelope -- never the receipt's own self-reported fields
# ---------------------------------------------------------------------------


def test_receipt_naming_an_envelope_id_never_committed_under_this_store_refuses(
    _worldA: dict[str, Any],
) -> None:
    forged = GitHubObservationReceipt(
        status=_worldA["receipt"].status,
        projection_envelope_id="PROJECTION-" + "0" * 64,
        project_id=_worldA["project_id"],
        subject_ref=_worldA["receipt"].subject_ref,
        external_artifact_ref=_worldA["receipt"].external_artifact_ref,
        adapter_identity=_worldA["receipt"].adapter_identity,
        github_authority_ref=_worldA["receipt"].github_authority_ref,
    )
    with pytest.raises(ProjectionRequirementError):
        route_observation_receipt_to_evidence(
            _worldA["store"],
            forged,
            _worldA["project_id"],
            _request(_worldA["project_id"]),
            adapter=_worldA["adapter"],
        )


def test_receipt_genuinely_from_a_different_projects_own_store_refuses(
    _worldA: dict[str, Any], _worldB: dict[str, Any]
) -> None:
    """The literal Structural Review Round 2 counterexample: a genuine receipt, copied
    verbatim (project_id included) from one real, independently-bound project's own real
    materialization, presented against a *different* project's own Store -- which never
    committed that envelope at all, regardless of what the receipt's own project_id claims."""

    copied_receipt = _worldA["receipt"]
    with pytest.raises(ProjectionRequirementError):
        route_observation_receipt_to_evidence(
            _worldB["store"],
            copied_receipt,
            _worldB["project_id"],
            _request(_worldB["project_id"]),
            adapter=_worldB["adapter"],
        )


def test_receipt_with_forged_subject_ref_refuses_even_with_a_real_envelope_id(
    _worldA: dict[str, Any],
) -> None:
    real = _worldA["receipt"]
    forged = GitHubObservationReceipt(
        status=real.status,
        projection_envelope_id=real.projection_envelope_id,
        project_id=real.project_id,
        subject_ref={"kind": "observation_evidence", "id": "EVIDENCE-FORGED"},
        external_artifact_ref=real.external_artifact_ref,
        adapter_identity=real.adapter_identity,
        github_authority_ref=real.github_authority_ref,
    )
    with pytest.raises(ProjectionRequirementError):
        route_observation_receipt_to_evidence(
            _worldA["store"],
            forged,
            _worldA["project_id"],
            _request(_worldA["project_id"]),
            adapter=_worldA["adapter"],
        )


def test_receipt_with_forged_external_artifact_ref_refuses(
    _worldA: dict[str, Any],
) -> None:
    real = _worldA["receipt"]
    forged = GitHubObservationReceipt(
        status=real.status,
        projection_envelope_id=real.projection_envelope_id,
        project_id=real.project_id,
        subject_ref=real.subject_ref,
        external_artifact_ref={
            "host": "github",
            "owner": _TARGET_REPOSITORY["owner"],
            "repo": _TARGET_REPOSITORY["repo"],
            "artifact_kind": "check_run",
            "external_id": "999999",
            "url": f"https://github.com/{_TARGET_REPOSITORY['owner']}/{_TARGET_REPOSITORY['repo']}/check_run/999999",
        },
        adapter_identity=real.adapter_identity,
        github_authority_ref=real.github_authority_ref,
    )
    with pytest.raises(ProjectionRequirementError):
        route_observation_receipt_to_evidence(
            _worldA["store"],
            forged,
            _worldA["project_id"],
            _request(_worldA["project_id"]),
            adapter=_worldA["adapter"],
        )


def test_receipt_with_forged_github_authority_ref_refuses(_worldA: dict[str, Any]) -> None:
    real = _worldA["receipt"]
    forged = GitHubObservationReceipt(
        status=real.status,
        projection_envelope_id=real.projection_envelope_id,
        project_id=real.project_id,
        subject_ref=real.subject_ref,
        external_artifact_ref=real.external_artifact_ref,
        adapter_identity=real.adapter_identity,
        github_authority_ref={"kind": "human_authority", "id": "AUTH-FORGED"},
    )
    with pytest.raises(ProjectionRequirementError):
        route_observation_receipt_to_evidence(
            _worldA["store"],
            forged,
            _worldA["project_id"],
            _request(_worldA["project_id"]),
            adapter=_worldA["adapter"],
        )


def test_receipt_with_mismatched_project_id_argument_still_refuses(
    _worldA: dict[str, Any],
) -> None:
    """The original Round 1 check remains in force alongside the new corroboration -- a
    receipt whose own ``project_id`` field disagrees with the requested ``project_id`` still
    refuses even when every other field happens to be real and corroborated."""

    with pytest.raises(ProjectionRequirementError):
        route_observation_receipt_to_evidence(
            _worldA["store"],
            _worldA["receipt"],
            "PRJ-SOME-OTHER-PROJECT",
            _request(_worldA["project_id"]),
            adapter=_worldA["adapter"],
        )


# ---------------------------------------------------------------------------
# Structural Review Round 3 (P14-R3-F2) and Round 4 (P14-R4-F2): independent
# re-observation at handoff is not itself an attestation of *receipt* -- every one of
# receipt's own Evidence-relevant fields (status, observations, adapter_identity, input_refs)
# must now exactly equal the freshly, independently recomputed candidate before any Evidence
# is derived. A single forged field, even with every other field genuine, refuses.
# ---------------------------------------------------------------------------


def _forged_receipt(real: GitHubObservationReceipt, **overrides: Any) -> GitHubObservationReceipt:
    """Copy every field of *real* verbatim except whichever ones *overrides* names -- the
    shared body every one-field-at-a-time forgery test below uses, so each test's own intent
    (which single field is forged) is visible in its own call, not buried in repetition."""

    fields: dict[str, Any] = {
        "status": real.status,
        "projection_envelope_id": real.projection_envelope_id,
        "project_id": real.project_id,
        "subject_ref": real.subject_ref,
        "external_artifact_ref": real.external_artifact_ref,
        "adapter_identity": real.adapter_identity,
        "github_authority_ref": real.github_authority_ref,
        "input_refs": real.input_refs,
        "observations": dict(real.observations),
    }
    fields.update(overrides)
    return GitHubObservationReceipt(**fields)


def test_receipt_with_forged_verified_status_over_genuinely_tampered_content_refuses(
    _worldA: dict[str, Any],
) -> None:
    """The literal Structural Review Round 3 counterexample, now refused outright rather than
    merely yielding non-VERIFIED Evidence (Structural Review Round 4, P14-R4-F2): copy every
    Envelope-bound field from a genuine receipt, forge ``status="VERIFIED"`` (plus fabricated
    ``observations``/``adapter_identity``/``input_refs``), but genuinely tamper the adapter's
    own underlying content first -- a real re-observation would report ``FAILED``. Because
    every one of those forged fields is now required to exactly equal the freshly recomputed
    candidate, this receipt is refused before any Evidence is derived at all."""

    real = _worldA["receipt"]
    _worldA["adapter"].tamper(
        external_artifact_ref=dict(real.external_artifact_ref),
        new_payload={**_PAYLOAD, "output": {"title": "TAMPERED", "summary": "not the original"}},
    )
    forged = GitHubObservationReceipt(
        status="VERIFIED",
        projection_envelope_id=real.projection_envelope_id,
        project_id=real.project_id,
        subject_ref=real.subject_ref,
        external_artifact_ref=real.external_artifact_ref,
        adapter_identity={"adapter": "forged_adapter", "version": "9.9"},
        github_authority_ref=real.github_authority_ref,
        input_refs=({"kind": "forged_kind", "id": "FORGED-INPUT"},),
        observations={
            "observation_outcome": "FOUND",
            "exists": True,
            "observed_content_fingerprint": "sha256:" + "0" * 64,
            "observed_at": "1970-01-01T00:00:00Z",
        },
    )
    with pytest.raises(ProjectionRequirementError):
        route_observation_receipt_to_evidence(
            _worldA["store"],
            forged,
            _worldA["project_id"],
            _request(_worldA["project_id"]),
            adapter=_worldA["adapter"],
        )


def test_receipt_with_forged_status_over_genuine_content_refuses(_worldA: dict[str, Any]) -> None:
    """Structural Review Round 4 (P14-R4-F2), one-field-at-a-time: content is genuinely
    untampered (a real re-observation would report ``VERIFIED``, exactly what ``real`` itself
    already carries), but the receipt's own ``status`` is forged to ``FAILED``. A prior,
    mistaken version of this handoff would have let the fresh, honest re-observation simply
    override the forgery and still yield ``VERIFIED`` Evidence; this receipt must instead be
    refused outright, because its own claimed status disagrees with the truth."""

    real = _worldA["receipt"]
    forged = _forged_receipt(real, status="FAILED")
    with pytest.raises(ProjectionRequirementError):
        route_observation_receipt_to_evidence(
            _worldA["store"],
            forged,
            _worldA["project_id"],
            _request(_worldA["project_id"]),
            adapter=_worldA["adapter"],
        )


def test_receipt_with_forged_observation_outcome_over_genuine_content_refuses(
    _worldA: dict[str, Any],
) -> None:
    real = _worldA["receipt"]
    observations = dict(real.observations)
    observations["observation_outcome"] = "NOT_FOUND"
    forged = _forged_receipt(real, observations=observations)
    with pytest.raises(ProjectionRequirementError):
        route_observation_receipt_to_evidence(
            _worldA["store"],
            forged,
            _worldA["project_id"],
            _request(_worldA["project_id"]),
            adapter=_worldA["adapter"],
        )


def test_receipt_with_forged_observed_fingerprint_over_genuine_content_refuses(
    _worldA: dict[str, Any],
) -> None:
    real = _worldA["receipt"]
    observations = dict(real.observations)
    observations["observed_content_fingerprint"] = "sha256:" + "0" * 64
    forged = _forged_receipt(real, observations=observations)
    with pytest.raises(ProjectionRequirementError):
        route_observation_receipt_to_evidence(
            _worldA["store"],
            forged,
            _worldA["project_id"],
            _request(_worldA["project_id"]),
            adapter=_worldA["adapter"],
        )


def test_receipt_with_forged_observed_timestamp_over_genuine_content_refuses(
    _worldA: dict[str, Any],
) -> None:
    real = _worldA["receipt"]
    observations = dict(real.observations)
    observations["observed_at"] = "1970-01-01T00:00:00Z"
    forged = _forged_receipt(real, observations=observations)
    with pytest.raises(ProjectionRequirementError):
        route_observation_receipt_to_evidence(
            _worldA["store"],
            forged,
            _worldA["project_id"],
            _request(_worldA["project_id"]),
            adapter=_worldA["adapter"],
        )


def test_receipt_with_forged_adapter_identity_over_genuine_content_refuses(
    _worldA: dict[str, Any],
) -> None:
    real = _worldA["receipt"]
    forged = _forged_receipt(real, adapter_identity={"adapter": "forged_adapter", "version": "9.9"})
    with pytest.raises(ProjectionRequirementError):
        route_observation_receipt_to_evidence(
            _worldA["store"],
            forged,
            _worldA["project_id"],
            _request(_worldA["project_id"]),
            adapter=_worldA["adapter"],
        )


def test_receipt_with_forged_input_refs_over_genuine_content_refuses(
    _worldA: dict[str, Any],
) -> None:
    real = _worldA["receipt"]
    forged = _forged_receipt(real, input_refs=({"kind": "forged_kind", "id": "FORGED-INPUT"},))
    with pytest.raises(ProjectionRequirementError):
        route_observation_receipt_to_evidence(
            _worldA["store"],
            forged,
            _worldA["project_id"],
            _request(_worldA["project_id"]),
            adapter=_worldA["adapter"],
        )


def test_receipt_with_every_field_exactly_matching_the_fresh_reobservation_verifies(
    _worldA: dict[str, Any],
) -> None:
    """The positive control every forgery test above needs: a receipt built from ``real``'s
    own exact fields, copied through :func:`_forged_receipt` with *no* overrides at all, must
    still verify -- proving the exact-equality requirement itself, not merely absence of a
    particular forged field, is what the six tests above exercise."""

    real = _worldA["receipt"]
    unforged = _forged_receipt(real)
    evidence = route_observation_receipt_to_evidence(
        _worldA["store"],
        unforged,
        _worldA["project_id"],
        _request(_worldA["project_id"]),
        adapter=_worldA["adapter"],
    )
    assert evidence["verification_result_provenance"]["status"] == "VERIFIED"
