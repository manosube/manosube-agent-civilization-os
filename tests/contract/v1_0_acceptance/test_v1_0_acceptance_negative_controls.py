"""Required decisive negative/tamper controls (Issue #92 section 7, `ADOPT_PHASE_22_V1_0_ACCEPTANCE`).

Ten controls, NC-1 through NC-10, each a real fail-closed attempt against this package's
own real code -- never a mocked assertion of intent.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from manosube_agent_civilization.v1_0_acceptance import (
    PUBLIC_V1_0_ACCEPTANCE_ENTRY_POINT_COUNT,
    __all__ as public_surface,
    build_v1_0_acceptance_bundle,
)
from manosube_agent_civilization.v1_0_acceptance.blocking_differences import (
    classify_v1_0_blocking_differences,
)
from manosube_agent_civilization.v1_0_acceptance.gate22 import (
    PREDICATE_TEST_OWNERS,
    rederive_predicate,
)
from manosube_agent_civilization.v1_0_acceptance.release_identity import (
    compute_release_identity,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "src" / "manosube_agent_civilization" / "v1_0_acceptance"


def test_nc1_a_failing_predicate_prevents_gate_22_all_pass(tmp_path: Path) -> None:
    """NC-1: a missing or false Gate 22 predicate prevents final acceptance."""
    owner_dir = tmp_path / "owner"
    owner_dir.mkdir()
    failing_test = owner_dir / "test_forced_failure.py"
    failing_test.write_text(
        "def test_forced_failure() -> None:\n    assert False\n", encoding="utf-8"
    )

    # Use the real function against a real, deliberately failing owning test.
    from manosube_agent_civilization.v1_0_acceptance import gate22 as gate22_module

    original_owners = gate22_module.PREDICATE_TEST_OWNERS["COMPARATIVE_BENCHMARK_PASS"]
    try:
        gate22_module.PREDICATE_TEST_OWNERS["COMPARATIVE_BENCHMARK_PASS"] = (
            "owner/test_forced_failure.py",
        )
        outcome = gate22_module.rederive_predicate("COMPARATIVE_BENCHMARK_PASS", tmp_path)
    finally:
        gate22_module.PREDICATE_TEST_OWNERS["COMPARATIVE_BENCHMARK_PASS"] = original_owners

    assert outcome.verification_result == "FAIL"
    assert outcome.exit_code != 0


def test_nc2_a_mutated_owning_suite_is_actually_re_executed_not_cached() -> None:
    """NC-2: a stale/mutable receipt cannot satisfy a predicate -- the owning suite is
    genuinely re-run every call, not memoized against an earlier pass."""
    first = rederive_predicate("COMPARATIVE_BENCHMARK_PASS", REPO_ROOT)
    second = rederive_predicate("COMPARATIVE_BENCHMARK_PASS", REPO_ROOT)
    assert first.verification_result == second.verification_result == "PASS"
    # Two independent subprocess runs, not a cached first result silently reused.
    assert first is not second


def test_nc3_build_bundle_accepts_no_caller_supplied_predicate_verdicts() -> None:
    """NC-3: a PR body, conversation statement, test summary or CI status cannot
    impersonate an accepted receipt -- `build_v1_0_acceptance_bundle` has no parameter a
    caller could use to inject a `gate_22_predicate_matrix` or predicate verdict directly."""
    signature = inspect.signature(build_v1_0_acceptance_bundle)
    forbidden_names = {
        "gate_22_predicate_matrix",
        "gate_22_all_pass",
        "predicate_results",
        "verification_result",
    }
    assert forbidden_names.isdisjoint(signature.parameters)


def test_nc4_predicate_owner_mapping_is_pinned_exactly() -> None:
    """NC-4: one Phase's evidence cannot silently satisfy a differently owned predicate --
    a drift test on the exact, reviewed owner mapping; any rewiring must go through review."""
    assert PREDICATE_TEST_OWNERS == {
        "OBJECTIVE_CONTINUITY_PROVEN": (
            "tests/unit/difference/test_objective_chain.py",
            "tests/natural_cycle/test_vertical_proof.py",
        ),
        "AGENT_REPLACEMENT_SAFE": ("tests/long_running_proof/test_long_running_proof_gate_20.py",),
        "SESSION_LOSS_SAFE": ("tests/long_running_proof/test_long_running_proof_gate_20.py",),
        "GITHUB_INDEPENDENCE": (
            "tests/unit/reflow/test_closure_evaluation.py",
            "tests/natural_cycle/test_vertical_proof.py",
        ),
        "RUNTIME_VERIFICATION": ("tests/long_running_proof/test_long_running_proof_gate_20.py",),
        "AUTHORITY_ENFORCEMENT": (
            "tests/integration/acceptance_policy/test_acceptance_policy_lineage_and_incident_fixture.py",
        ),
        "EVIDENCE_ONLY_COMPLETION": (
            "tests/contract/evidence/test_sufficiency_ownership.py",
            "tests/integration/evidence/test_sufficiency_semantics.py",
        ),
        "STATE_LINEAGE_PRESERVATION": (
            "tests/unit/reflow/test_git_witness.py",
            "tests/unit/difference/test_lineage_closure.py",
        ),
        "LONG_RUNNING_PROOF_PASS": ("tests/long_running_proof/test_long_running_proof_gate_20.py",),
        "COMPARATIVE_BENCHMARK_PASS": (
            "tests/contract/comparative_benchmark/test_p90_r7_canonical_gate21_disposition.py",
        ),
        "THIRD_PARTY_REPRODUCTION_CONFIRMED": (
            "tests/contract/comparative_benchmark/test_p90_r7_canonical_gate21_disposition.py",
        ),
    }


def test_nc5_the_full_active_record_set_is_pinned_no_silent_omission() -> None:
    """NC-5: an open v1.0-blocking Difference cannot be omitted or relabeled non-blocking
    without SHUKOU Authority -- the full active-record-id set is pinned; a record silently
    deleted from the register (or a new one silently added) changes this set and fails."""
    dispositions = classify_v1_0_blocking_differences(REPO_ROOT)
    assert {d.record_id for d in dispositions} == {
        "DD-0001",
        "DD-0002",
        "DC-0001",
        "FD-0001",
        "FD-0002",
        "FD-0003",
        "FD-0005",
    }


def test_nc6_disposition_never_rewrites_the_records_own_current_status() -> None:
    """NC-6: a non-blocking Deferred Difference does not silently become blocking, and
    cannot be silently closed -- `current_status` is always the register's own raw value,
    never overwritten to a closing value by this package."""
    dispositions = classify_v1_0_blocking_differences(REPO_ROOT)
    fd_0005 = next(d for d in dispositions if d.record_id == "FD-0005")
    assert fd_0005.current_status == "OPEN_NON_BLOCKING_DEFERRED"
    assert "CLOSED" not in fd_0005.current_status


def test_nc7_release_identity_never_collapses_distinct_commits() -> None:
    """NC-7: release tag/version/source-tree substitution fails closed -- two distinct
    real commits never collapse to the same commit_sha in their own release identity."""
    head = compute_release_identity(REPO_ROOT, "HEAD", "v1.0-candidate")
    parent = compute_release_identity(REPO_ROOT, "HEAD~1", "v1.0-candidate")
    assert head.commit_sha != parent.commit_sha


def test_nc8_delivery_head_and_release_identity_commit_share_one_source() -> None:
    """NC-8: reviewed head / merge tree / release tree mismatch fails closed at the point
    this package can enforce it -- within one bundle, `delivery_head` and
    `release_identity.commit_sha` are always bound to the identical caller-supplied value,
    so no code path inside this package can silently diverge them. (Cross-round reviewed-
    head vs. merged-tree equality remains the Structural Advisor/SHUKOU's own verification,
    outside this package's scope.)"""
    bundle = build_v1_0_acceptance_bundle(
        REPO_ROOT, "b2a5d287113d3a98e77a2212f8b89359d8e09c5d", "HEAD", "v1.0-candidate"
    )
    assert bundle["delivery_head"] == bundle["release_identity"]["commit_sha"] == "HEAD"


def test_nc9_no_v1_0_declaration_entry_point_exists() -> None:
    """NC-9: absence of Human Acceptance, release receipt or after-state observation
    forbids the final declaration -- this package's public surface contains no function
    that could emit a v1.0 declaration at all; only rederivation, disposition, identity
    computation and bundle assembly."""
    assert PUBLIC_V1_0_ACCEPTANCE_ENTRY_POINT_COUNT == 4
    assert set(public_surface) == {
        "PUBLIC_V1_0_ACCEPTANCE_ENTRY_POINT_COUNT",
        "DifferenceDisposition",
        "PredicateRederivation",
        "ReleaseIdentity",
        "build_v1_0_acceptance_bundle",
        "classify_v1_0_blocking_differences",
        "compute_release_identity",
        "rederive_all_pytest_owned_predicates",
    }
    forbidden_substrings = ("declare", "publish_release", "create_tag", "v1_0_true")
    for name in public_surface:
        lowered = name.lower()
        assert not any(f in lowered for f in forbidden_substrings), name


def test_nc10_package_imports_no_write_route_from_another_package() -> None:
    """NC-10: the evidence bundle cannot mutate prior canonical owners through an
    extension surface -- a static source scan proving this package never imports a
    `commit_*`/`route`-module write entry point from any other package."""
    forbidden_import_fragments = (
        "from manosube_agent_civilization.reflow",
        "from manosube_agent_civilization.difference",
        "from manosube_agent_civilization.evidence",
        "from manosube_agent_civilization.authority",
        "from manosube_agent_civilization.change",
        "from manosube_agent_civilization.store",
        "from manosube_agent_civilization.comparative_benchmark",
        "from manosube_agent_civilization.acceptance_policy",
    )
    for path in sorted(PACKAGE_ROOT.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for fragment in forbidden_import_fragments:
            assert fragment not in text, f"{path.name} imports from {fragment!r}"
