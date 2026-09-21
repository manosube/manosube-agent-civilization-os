"""V1: v1.0 acceptance bundle assembly, schema-validated (Issue #92,
`ADOPT_PHASE_22_V1_0_ACCEPTANCE`).

Uses monkeypatching on the (already independently tested) rederivation functions so this
module stays fast -- the one real, full end-to-end assembly (real subprocess pytest calls
for all eleven owned predicates, real register read) is
`tests/contract/v1_0_acceptance/test_gate22_rederivation.py`'s own job.
"""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
import pytest

from manosube_agent_civilization.v1_0_acceptance import engine as engine_module
from manosube_agent_civilization.v1_0_acceptance.blocking_differences import (
    DifferenceDisposition,
)
from manosube_agent_civilization.v1_0_acceptance.commit_binding import AUTHORIZED_PROJECT
from manosube_agent_civilization.v1_0_acceptance.gate22 import PredicateRederivation
from manosube_agent_civilization.v1_0_acceptance.release_identity import ReleaseIdentity
from manosube_agent_civilization.v1_0_acceptance.types import GATE_22_PREDICATES

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "01_SCHEMA" / "v1_0_acceptance" / "v1_0_acceptance_bundle.schema.json"


def _fake_pytest_owned(repo_root: Path) -> dict[str, PredicateRederivation]:
    owned = {p for p in GATE_22_PREDICATES if p != "ALL_V1_0_BLOCKING_DIFFERENCES_CLOSED"}
    return {
        predicate: PredicateRederivation(
            predicate=predicate,
            owner_test_paths=("tests/fake/test_fake.py",),
            verification_result="PASS",
            exit_code=0,
            missing_paths=(),
        )
        for predicate in owned
    }


def _fake_blocking_closed(
    repo_root: Path, register_relative_path: str = ""
) -> tuple[str, tuple[DifferenceDisposition, ...]]:
    return "PASS", (
        DifferenceDisposition(
            record_id="DC-0001",
            classification="DEFERRED_DESIGN_CANDIDATE",
            current_status="PROTOTYPE",
            current_phase_blocking_effect="NONE",
            disposition="NON_BLOCKING",
            rationale="test fixture",
        ),
    )


def _fake_release_identity(repo_root: Path, commit_sha: str, version_label: str) -> ReleaseIdentity:
    return ReleaseIdentity(
        commit_sha=commit_sha,
        tree_entry_count=10,
        blob_count=8,
        directory_count=2,
        version_label=version_label,
        tag_created=False,
        release_published=False,
    )


#: A stand-in resolved delivery commit -- this module's own commit-binding checks
#: (`resolve_and_bind_delivery_head`/`resolve_and_verify_authorized_base`) are real git
#: operations against a real repository, exercised end-to-end by
#: `tests/contract/v1_0_acceptance/test_gate22_rederivation.py`; here they are
#: monkeypatched too so this module stays fast and independent of the live repo's
#: worktree cleanliness.
_FAKE_DELIVERY_HEAD_SHA = "0" * 40
_FAKE_BASE_SHA = "1" * 40

#: Likewise, `verify_repository_project_binding` is a real `git remote get-url` call --
#: monkeypatched here for the same reason (PR #93 Structural Review Round 2, `P93-R2-F1`).
#: Must equal `AUTHORIZED_PROJECT` exactly: the bundle schema fixes `repository_project`
#: to that one constant (`P93-R3-F1`), so a differently-shaped fake value here would fail
#: `test_bundle_validates_against_its_own_schema` for reasons unrelated to what that test
#: actually verifies.
_FAKE_REPOSITORY_PROJECT = AUTHORIZED_PROJECT


@pytest.fixture(autouse=True)
def _patched(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine_module, "rederive_all_pytest_owned_predicates", _fake_pytest_owned)
    monkeypatch.setattr(
        engine_module, "rederive_all_v1_0_blocking_differences_closed", _fake_blocking_closed
    )
    monkeypatch.setattr(engine_module, "compute_release_identity", _fake_release_identity)
    monkeypatch.setattr(
        engine_module,
        "resolve_and_bind_delivery_head",
        lambda repo_root, delivery_head: _FAKE_DELIVERY_HEAD_SHA,
    )
    monkeypatch.setattr(
        engine_module,
        "resolve_and_verify_authorized_base",
        lambda repo_root, base, resolved_head: _FAKE_BASE_SHA,
    )
    monkeypatch.setattr(
        engine_module,
        "verify_repository_project_binding",
        lambda repo_root: _FAKE_REPOSITORY_PROJECT,
    )


def test_bundle_validates_against_its_own_schema() -> None:
    bundle = engine_module.build_v1_0_acceptance_bundle(
        REPO_ROOT, "b2a5d287113d3a98e77a2212f8b89359d8e09c5d", "abc123", "v1.0-candidate"
    )
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(bundle)


def test_gate_22_all_pass_true_when_every_predicate_passes() -> None:
    bundle = engine_module.build_v1_0_acceptance_bundle(
        REPO_ROOT, "b2a5d287113d3a98e77a2212f8b89359d8e09c5d", "abc123", "v1.0-candidate"
    )
    assert bundle["gate_22_all_pass"] is True
    assert set(bundle["gate_22_predicate_matrix"]) == set(GATE_22_PREDICATES)


def test_gate_22_all_pass_false_when_one_predicate_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def _one_fails(repo_root: Path) -> dict[str, PredicateRederivation]:
        rows = _fake_pytest_owned(repo_root)
        rows["OBJECTIVE_CONTINUITY_PROVEN"] = PredicateRederivation(
            predicate="OBJECTIVE_CONTINUITY_PROVEN",
            owner_test_paths=("tests/fake/test_fake.py",),
            verification_result="FAIL",
            exit_code=1,
            missing_paths=(),
        )
        return rows

    monkeypatch.setattr(engine_module, "rederive_all_pytest_owned_predicates", _one_fails)
    bundle = engine_module.build_v1_0_acceptance_bundle(
        REPO_ROOT, "b2a5d287113d3a98e77a2212f8b89359d8e09c5d", "abc123", "v1.0-candidate"
    )
    assert bundle["gate_22_all_pass"] is False


def test_bundle_identity_deterministic_across_two_builds_same_inputs() -> None:
    first = engine_module.build_v1_0_acceptance_bundle(
        REPO_ROOT, "b2a5d287113d3a98e77a2212f8b89359d8e09c5d", "abc123", "v1.0-candidate"
    )
    second = engine_module.build_v1_0_acceptance_bundle(
        REPO_ROOT, "b2a5d287113d3a98e77a2212f8b89359d8e09c5d", "abc123", "v1.0-candidate"
    )
    assert first["acceptance_bundle_id"] == second["acceptance_bundle_id"]
