"""V5 (Issue #64): Phase 14 runtime-provisioning continuity proof.

Proves :func:`~manosube_agent_civilization.runtime.bootstrap.
bootstrap_projection_execution_capability` -- the Phase-14-deferred trusted runtime bootstrap
this delivery ships -- genuinely constructs one production
:class:`~manosube_agent_civilization.projection.ProjectionExecutionCapability` from canonical
Store/Boot state alone, reaches a controlled GitHub adapter through it with zero live network
calls, and refuses on every malformed/incomplete/mismatched authority input -- never minting,
signing, or committing anything of its own.

Since Structural Review Round 3 (P15-R3-F1) every call here does what a real deployment
composition boundary does, through entirely shipped code: construct a ``TrustedRuntimeRoot``
(public, unrestricted -- it grants nothing by itself), present a genuinely committed
``runtime_root_admission`` record for exactly this project and Binding, and supply the
``trust_anchor_public_key_hex`` that record was actually signed under. The admission record's
own *signature* is produced test-side, by the fixture layer's own trust-anchor key pair, for the
identical reason every other signature in this repository's test suite is: shipped code only
ever verifies, and no private key of any kind lives in ``src/``.

``tests/integration/runtime/test_runtime_root_admission.py`` owns the controls proving that a
root without a genuine admission -- however it was constructed, and however internally
self-consistent its own world is -- reaches nothing at all.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.evidence_helpers import observation_evidence_request
from tests.fixtures.runtime_world import (
    admitted_root,
    bound,
    commit_declaration,
    commit_grant,
    commit_records,
)

from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.evidence import derive_evidence
from manosube_agent_civilization.evidence.identity import evidence_semantic_fingerprint
from manosube_agent_civilization.projection import FakeGitHubAdapter, ProjectionExecutionCapability
from manosube_agent_civilization.projection.identity import projection_payload_fingerprint
from manosube_agent_civilization.runtime.bootstrap import (
    bootstrap_projection_execution_capability,
)
from manosube_agent_civilization.runtime.errors import RuntimeRequirementError

_TARGET_REPOSITORY = {"host": "github", "owner": "acme", "repo": "widget"}
_PAYLOAD = {
    "name": "MANOSUBE Evidence Check",
    "head_sha": "a" * 40,
    "status": "completed",
    "conclusion": "neutral",
    "output": {"title": "Evidence artifact", "summary": "hello"},
}


@pytest.fixture
def _world(tmp_path: Path) -> dict[str, Any]:
    store, ctx = bound(tmp_path)
    evidence = derive_evidence(observation_evidence_request())
    evidence_id = evidence["evidence_id"]
    current_state = commit_records(
        store,
        ctx["project_id"],
        ctx["genesis_state"],
        "TX-RUNTIME-BOOTSTRAP-0001",
        [("observation_evidence", evidence_id, evidence)],
    )
    boot_context = boot_project(
        store, project_id=ctx["project_id"], project_binding_id=ctx["project_binding_id"]
    )
    human_authority_ref = dict(boot_context.human_authority_ref)
    evidence_subject_ref = {"kind": "observation_evidence", "id": evidence_id}
    evidence_fingerprint = evidence_semantic_fingerprint(evidence)
    grant_ref, grant = commit_grant(
        store,
        ctx["project_id"],
        human_authority_ref,
        "TX-RUNTIME-BOOTSTRAP-0002",
        subject_ref=evidence_subject_ref,
        subject_fingerprint=evidence_fingerprint,
        projection_kind="EVIDENCE_ARTIFACT",
        target_repository=_TARGET_REPOSITORY,
        payload_fingerprint=projection_payload_fingerprint(dict(_PAYLOAD)),
    )
    declaration_ref = commit_declaration(
        store, ctx["project_id"], ctx["project_binding_id"], human_authority_ref, grant
    )
    return {
        "store": store,
        "project_id": ctx["project_id"],
        "project_binding_id": ctx["project_binding_id"],
        "evidence_id": evidence_id,
        "grant_ref": grant_ref,
        "grant": grant,
        "declaration_ref": declaration_ref,
        "current_state": current_state,
        # P15-R3-F1: the admission triple every legitimate provisioning call now needs.
        "admitted": admitted_root(
            store,
            project_id=ctx["project_id"],
            project_binding_id=ctx["project_binding_id"],
        ),
    }


def _bootstrap(world: dict[str, Any], *, grant_refs: list[Any], declaration_refs: list[Any]) -> Any:
    """One legitimately admitted provisioning call -- the exact shape a real deployment
    composition boundary makes (P15-R3-F1)."""

    admitted = world["admitted"]
    return bootstrap_projection_execution_capability(
        admitted["trusted_runtime_root"],
        runtime_root_admission_ref=admitted["runtime_root_admission_ref"],
        trust_anchor_public_key_hex=admitted["trust_anchor_public_key_hex"],
        github_projection_grant_refs=grant_refs,
        github_projection_grant_declaration_refs=declaration_refs,
    )


def test_bootstrap_constructs_a_real_capability_that_reaches_the_controlled_adapter(
    _world: dict[str, Any],
) -> None:
    capability = _bootstrap(
        _world,
        grant_refs=[_world["grant_ref"]],
        declaration_refs=[_world["declaration_ref"]],
    )
    assert isinstance(capability, ProjectionExecutionCapability)

    adapter = FakeGitHubAdapter()  # controlled -- zero live network calls
    result = capability.execute(
        projection_kind="EVIDENCE_ARTIFACT",
        target_repository=_TARGET_REPOSITORY,
        projection_payload=_PAYLOAD,
        adapter=adapter,
        materialized_at="2026-09-09T00:00:00Z",
        attempt_claim_token="RUNTIME-BOOTSTRAP-ATTEMPT-0001",  # noqa: S106
    )
    assert adapter.materialize_call_count == 1
    assert result["receipt"].status == "VERIFIED"
    assert result["reused"] is False


def test_bootstrap_refuses_with_no_grant_refs(_world: dict[str, Any]) -> None:
    with pytest.raises(RuntimeRequirementError):
        _bootstrap(_world, grant_refs=[], declaration_refs=[])


def test_bootstrap_refuses_an_unresolvable_grant_ref(_world: dict[str, Any]) -> None:
    with pytest.raises(RuntimeRequirementError):
        _bootstrap(
            _world,
            grant_refs=[
                {"kind": "github_projection_grant", "id": "GITHUB-PROJECTION-GRANT-NONEXISTENT"}
            ],
            declaration_refs=[_world["declaration_ref"]],
        )


def test_bootstrap_refuses_a_grant_with_no_anchoring_declaration(_world: dict[str, Any]) -> None:
    with pytest.raises(RuntimeRequirementError):
        _bootstrap(_world, grant_refs=[_world["grant_ref"]], declaration_refs=[])


def test_bootstrap_refuses_two_grants_for_the_identical_projection_kind(
    _world: dict[str, Any],
) -> None:
    # A second, distinct observation_evidence subject (a different recorded_at genuinely
    # changes its own content address) so the second grant is a genuinely different,
    # resolvable record -- never a duplicate.
    evidence = derive_evidence(observation_evidence_request(recorded_at="2026-09-09T00:00:01Z"))
    current_state = _world["store"].load_current(_world["project_id"])
    commit_records(
        _world["store"],
        _world["project_id"],
        current_state,
        "TX-RUNTIME-BOOTSTRAP-SECOND-EVIDENCE",
        [("observation_evidence", evidence["evidence_id"], evidence)],
    )
    boot_context = boot_project(
        _world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
    )
    human_authority_ref = dict(boot_context.human_authority_ref)
    second_grant_ref, second_grant = commit_grant(
        _world["store"],
        _world["project_id"],
        human_authority_ref,
        "TX-RUNTIME-BOOTSTRAP-SECOND-GRANT",
        subject_ref={"kind": "observation_evidence", "id": evidence["evidence_id"]},
        subject_fingerprint=evidence_semantic_fingerprint(evidence),
        projection_kind="EVIDENCE_ARTIFACT",
        target_repository=_TARGET_REPOSITORY,
        payload_fingerprint=projection_payload_fingerprint(dict(_PAYLOAD)),
    )
    second_declaration_ref = commit_declaration(
        _world["store"],
        _world["project_id"],
        _world["project_binding_id"],
        human_authority_ref,
        second_grant,
    )

    with pytest.raises(RuntimeRequirementError):
        _bootstrap(
            _world,
            grant_refs=[_world["grant_ref"], second_grant_ref],
            declaration_refs=[_world["declaration_ref"], second_declaration_ref],
        )


def test_bootstrap_module_imports_no_test_module_and_no_network_transport_surface() -> None:
    """Static proof: production code that will one day call this bootstrap must never import
    a test module or reach for a network transport surface itself -- both refused by
    inspection of the module's own top-level imports."""

    import ast
    import inspect

    from manosube_agent_civilization.runtime import bootstrap as bootstrap_module

    source = inspect.getsource(bootstrap_module)
    tree = ast.parse(source)
    imported_names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.append(node.module)

    assert not any(name.startswith("tests") for name in imported_names)
    forbidden_transport_prefixes = ("urllib", "http", "socket", "requests", "httpx")
    assert not any(
        name.startswith(prefix)
        for name in imported_names
        for prefix in forbidden_transport_prefixes
    )
