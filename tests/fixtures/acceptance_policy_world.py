"""Shared Acceptance Policy Lineage (FD-0004, Issue #80) test world.

Deliberately minimal: this package's own records never reference Difference/Change/Authority/
Evidence at all (FD4-C10 reuses only the Store commit path and the literal ``SHUKOU`` Human
Authority), so the only real-Kernel prerequisite a test needs is one genuinely bound project to
commit against -- the same ``bind_project_kwargs()``/``genesis_records()`` fixtures every other
suite in this repository already shares.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.fixtures.product_binding import (
    bind_project_kwargs,
    genesis_records,
    sign_governance_adoption_authority,
)
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.binding import bind_project
from manosube_agent_civilization.store import FileStateStore

GOVERNING_ISSUE = 80


def bound_world(tmp_path: Path) -> dict[str, Any]:
    """One real, freshly bound project over a real ``FileStateStore`` -- nothing this
    package's own records need beyond a valid ``project_id`` to bind their own ``scope`` and
    ``project_id`` fields to. P82-R3-F1: also exposes the real, committed Project Binding's
    own id, so tests can name it as the trusted signing authority an adoption is bound to."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = bind_project_kwargs()
    result = bind_project(
        store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
    )
    return {
        "store": store,
        "project_id": kwargs["project_id"],
        "project_binding_id": result["project_binding_id"],
    }


def source_reference(
    comment_id: str,
    *,
    source_kind: str,
    path: str = "issues/80",
    comment_author: str = "manosube",
    comment_author_association: str = "OWNER",
) -> dict[str, Any]:
    return {
        "comment_url": (
            f"https://github.com/manosube/manosube-agent-civilization-os/{path}"
            f"#issuecomment-{comment_id}"
        ),
        "comment_id": comment_id,
        "comment_author": comment_author,
        "comment_author_association": comment_author_association,
        "source_kind": source_kind,
    }


def governance_adoption_record(
    *,
    project_id: str,
    governing_issue: int,
    adopted_ref: dict[str, str],
    source_reference: dict[str, Any],
    project_binding_id: str,
    decided_at: str,
    decision_owner: str = "SHUKOU",
    adoption_id: str = "ADOPT_TEST_FIXTURE",
    comment_url: str | None = None,
    reviewed_sha: str = "a" * 40,
    authorized_target_sha: str | None = None,
    decision_authority: str = "SHUKOU",
    decision_status: str = "RATIFIED",
    receipt_overrides: dict[str, Any] | None = None,
    signature_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """P82-R2-F1/P82-R3-F1/P82-R4-F2: a well-formed Governance Adoption Record
    (``development_binding.adoption_record``'s own closed shape), genuinely signed (by
    :func:`~tests.fixtures.product_binding.sign_governance_adoption_authority`'s fixed test
    Ed25519 key) over the complete Human-Authority act it is bound to -- *project_id*,
    *governing_issue*, *adopted_ref*, *decision_owner*, the complete *source_reference*, the
    canonical *project_binding_id*, *decided_at*, and this record's own signature-excluded
    core -- so it verifies against the real Project Binding's own trusted public key by
    default. ``comment_url`` defaults to *source_reference*'s own, but may be overridden
    independently (e.g. to construct a record whose own claimed comment disagrees with the
    adoption's real source) -- signing still binds to the real *source_reference* passed in,
    never to this override. Callers pass ``receipt_overrides``, ``signature_override``, or
    override a top-level field directly to construct the decisive forged/mismatched/replayed
    controls F1 requires."""

    record_comment_url = comment_url if comment_url is not None else source_reference["comment_url"]
    governing_issue_str = f"#{governing_issue}"
    target_sha = authorized_target_sha if authorized_target_sha is not None else reviewed_sha
    receipt = {
        "adoption_id": adoption_id,
        "governing_issue": governing_issue_str,
        "reviewed_sha": reviewed_sha,
        "comment_url": record_comment_url,
        "decision_authority": decision_authority,
        "decision_status": decision_status,
    }
    if receipt_overrides:
        receipt.update(receipt_overrides)
    core = {
        "schema_version": "0.1",
        "adoption_id": adoption_id,
        "governing_issue": governing_issue_str,
        "comment_url": record_comment_url,
        "decision_authority": decision_authority,
        "decision_status": decision_status,
        "api_read_back_receipt": receipt,
        "reviewed_sha": reviewed_sha,
        "authorized_target_sha": target_sha,
    }
    signature = (
        signature_override
        if signature_override is not None
        else sign_governance_adoption_authority(
            project_id=project_id,
            governing_issue=governing_issue,
            adopted_ref=adopted_ref,
            decision_owner=decision_owner,
            source_reference=source_reference,
            project_binding_id=project_binding_id,
            decided_at=decided_at,
            governance_adoption_record_core=core,
        )
    )
    return {**core, "signature": signature}


def clause(
    clause_id: str,
    *,
    policy_class: str,
    project_id: str,
    existed_in_original_contract: bool,
    implementation: bool = False,
    structural_review: bool = False,
    merge: bool = False,
    issue_closure: bool = False,
    phase_completion: bool = False,
    affected_phases: list[int] | None = None,
    affected_prs: list[int] | None = None,
) -> dict[str, Any]:
    return {
        "clause_id": clause_id,
        "policy_class": policy_class,
        "statement": f"{clause_id} statement (non-authoritative provenance prose)",
        "blocking_effect": {
            "implementation": implementation,
            "structural_review": structural_review,
            "merge": merge,
            "issue_closure": issue_closure,
            "phase_completion": phase_completion,
        },
        "scope": {
            "project_id": project_id,
            "affected_phases": affected_phases if affected_phases is not None else [19],
            "affected_prs": affected_prs if affected_prs is not None else [78],
        },
        "rationale": f"{clause_id} rationale (non-authoritative provenance prose)",
        "existed_in_original_contract": existed_in_original_contract,
    }
