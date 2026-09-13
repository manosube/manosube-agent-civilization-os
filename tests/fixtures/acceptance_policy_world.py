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

from tests.fixtures.product_binding import bind_project_kwargs, genesis_records
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.binding import bind_project
from manosube_agent_civilization.store import FileStateStore

GOVERNING_ISSUE = 80


def bound_world(tmp_path: Path) -> dict[str, Any]:
    """One real, freshly bound project over a real ``FileStateStore`` -- nothing this
    package's own records need beyond a valid ``project_id`` to bind their own ``scope`` and
    ``project_id`` fields to."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = bind_project_kwargs()
    bind_project(
        store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
    )
    return {"store": store, "project_id": kwargs["project_id"]}


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
