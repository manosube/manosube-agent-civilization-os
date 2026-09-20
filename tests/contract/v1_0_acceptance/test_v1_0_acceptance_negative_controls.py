"""Required decisive negative/tamper controls (Issue #92 section 7,
`ADOPT_PHASE_22_V1_0_ACCEPTANCE`; extended by PR #93 Structural Review Round 1,
`ADOPT_P93_R1_F1_F2_F3_F4_F5`, finding `P93-R1-F5`; extended again by PR #93
Structural Review Round 2, `ADOPT_P93_R2_F1_F2`, findings `P93-R2-F1`/`P93-R2-F2`;
extended once more by PR #93 Structural Review Round 3, `ADOPT_P93_R3_F1`).

NC-1 through NC-10 are the originally adopted ten. NC-11 through NC-17 close the eight
additional decisive scenarios `P93-R1-F5` names by id, and NC-2 is rewritten (the
original only checked object identity across two calls, which is trivially true
regardless of mutation -- Structural Review's own "nominal, does not mutate anything"
finding). NC-18 through NC-21 close `P93-R2-F1`'s wrong-repository/project substitution
requirement and `P93-R2-F2`'s remaining decisive scenarios (a staged-only dirty index,
and real pytest internal-error/usage-error outcomes). NC-22 closes `P93-R3-F1`'s
GitHub-hostname boundary requirement -- a lookalike host that merely contains the
substring `github.com` in its URL. Every control here is a real fail-closed attempt
against this package's own real code -- never a mocked assertion of intent.
"""

from __future__ import annotations

import inspect
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from manosube_agent_civilization.v1_0_acceptance import (
    PUBLIC_V1_0_ACCEPTANCE_ENTRY_POINT_COUNT,
    __all__ as public_surface,
    build_v1_0_acceptance_bundle,
)
from manosube_agent_civilization.v1_0_acceptance.blocking_differences import (
    classify_v1_0_blocking_differences,
)
from manosube_agent_civilization.v1_0_acceptance.commit_binding import (
    resolve_commit_sha,
    verify_authorized_base_ancestry,
    verify_repo_root_bound_to_commit,
    verify_repository_project_binding,
)
from manosube_agent_civilization.v1_0_acceptance.errors import (
    CommitResolutionError,
    DeliveryHeadBindingError,
    RepositoryProjectBindingError,
)
from manosube_agent_civilization.v1_0_acceptance.gate22 import PREDICATE_TEST_OWNERS
from manosube_agent_civilization.v1_0_acceptance.release_identity import (
    compute_release_identity,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "src" / "manosube_agent_civilization" / "v1_0_acceptance"

_GIT = shutil.which("git")


def _run_git(repo: Path, *args: str) -> str:
    assert _GIT is not None, "git executable not found on PATH"
    result = subprocess.run(  # noqa: S603 -- fixed Git executable resolved via shutil.which above
        [_GIT, *args], cwd=repo, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _init_scratch_git_repo(repo: Path) -> tuple[str, str]:
    """Create a minimal two-commit git repository at `repo`, returning
    `(first_commit_sha, second_commit_sha)`. `repo`'s checked-out `HEAD` is the second
    commit when this returns."""
    _run_git(repo, "init", "-q")
    _run_git(repo, "config", "user.email", "test@example.invalid")
    _run_git(repo, "config", "user.name", "Test")
    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    _run_git(repo, "add", "a.txt")
    _run_git(repo, "commit", "-q", "-m", "first")
    first = _run_git(repo, "rev-parse", "HEAD")
    (repo / "b.txt").write_text("b\n", encoding="utf-8")
    _run_git(repo, "add", "b.txt")
    _run_git(repo, "commit", "-q", "-m", "second")
    second = _run_git(repo, "rev-parse", "HEAD")
    return first, second


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


def test_nc2_a_mutated_owning_suite_is_actually_re_executed_not_cached(tmp_path: Path) -> None:
    """NC-2: a stale/mutable receipt cannot satisfy a predicate -- the owning suite is
    genuinely re-run every call, and a real content mutation between two calls changes
    the result. (The original NC-2 only checked object identity across two calls, which
    is trivially true regardless of mutation and proves nothing about re-execution --
    PR #93 Structural Review Round 1, `P93-R1-F5`.)"""
    owner_dir = tmp_path / "owner"
    owner_dir.mkdir()
    test_file = owner_dir / "test_mutable.py"
    test_file.write_text("def test_mutable() -> None:\n    assert True\n", encoding="utf-8")

    from manosube_agent_civilization.v1_0_acceptance import gate22 as gate22_module

    original = gate22_module.PREDICATE_TEST_OWNERS["COMPARATIVE_BENCHMARK_PASS"]
    try:
        gate22_module.PREDICATE_TEST_OWNERS["COMPARATIVE_BENCHMARK_PASS"] = (
            "owner/test_mutable.py",
        )
        first = gate22_module.rederive_predicate("COMPARATIVE_BENCHMARK_PASS", tmp_path)
        test_file.write_text("def test_mutable() -> None:\n    assert False\n", encoding="utf-8")
        second = gate22_module.rederive_predicate("COMPARATIVE_BENCHMARK_PASS", tmp_path)
    finally:
        gate22_module.PREDICATE_TEST_OWNERS["COMPARATIVE_BENCHMARK_PASS"] = original

    assert first.verification_result == "PASS"
    assert second.verification_result == "FAIL"


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


def test_nc8_delivery_head_and_release_identity_commit_share_one_resolved_source() -> None:
    """NC-8: reviewed head / merge tree / release tree mismatch fails closed at the point
    this package can enforce it -- within one bundle, `delivery_head` and
    `release_identity.commit_sha` are always bound to the identical *resolved* canonical
    40-hex commit SHA, never a raw caller-supplied ref like `"HEAD"` (PR #93 Structural
    Review Round 1, `P93-R1-F1`/`P93-R1-F2`). Cross-round reviewed-head vs. merged-tree
    equality remains the Structural Advisor/SHUKOU's own verification, outside this
    package's scope."""
    bundle = build_v1_0_acceptance_bundle(
        REPO_ROOT, "b2a5d287113d3a98e77a2212f8b89359d8e09c5d", "HEAD", "v1.0-candidate"
    )
    assert bundle["delivery_head"] == bundle["release_identity"]["commit_sha"]
    assert re.fullmatch(r"[0-9a-f]{40}", bundle["delivery_head"])


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


def test_nc11_historical_delivery_sha_with_current_worktree_evidence_fails_closed(
    tmp_path: Path,
) -> None:
    """NC-11: a historical commit SHA cannot be delivered while the worktree it is checked
    against is actually sitting at a later commit -- rederiving current-worktree evidence
    while claiming it belongs to an older, already-superseded delivery_head is exactly the
    substitution `P93-R1-F1` closes."""
    first, _second = _init_scratch_git_repo(tmp_path)
    with pytest.raises(DeliveryHeadBindingError):
        verify_repo_root_bound_to_commit(tmp_path, first)


def test_nc12_dirty_tracked_worktree_fails_closed(tmp_path: Path) -> None:
    """NC-12: uncommitted tracked-file changes at the claimed delivery commit fail closed --
    evidence rederived against an unclean worktree is never accepted as belonging to that
    commit's clean, reviewed content."""
    _first, second = _init_scratch_git_repo(tmp_path)
    (tmp_path / "b.txt").write_text("mutated\n", encoding="utf-8")
    with pytest.raises(DeliveryHeadBindingError):
        verify_repo_root_bound_to_commit(tmp_path, second)


def test_nc13_raw_tree_object_rejected_as_a_commit_identity(tmp_path: Path) -> None:
    """NC-13: a raw tree (or blob) object -- which has no commit metadata, author, or
    parent lineage -- is never silently accepted as a commit identity merely because it is
    a 40-hex string."""
    _first, second = _init_scratch_git_repo(tmp_path)
    tree_sha = _run_git(tmp_path, "rev-parse", f"{second}^{{tree}}")
    with pytest.raises(CommitResolutionError):
        resolve_commit_sha(tmp_path, tree_sha)


def test_nc14_unresolvable_commit_fails_closed() -> None:
    """NC-14: a well-formed 40-hex value that does not resolve to any real commit object in
    the target repository is rejected outright, never treated as a plausible identity merely
    because it matches the SHA pattern."""
    with pytest.raises(CommitResolutionError):
        resolve_commit_sha(REPO_ROOT, "0" * 40)


def test_nc15_unauthorized_non_ancestor_base_sha_fails_closed() -> None:
    """NC-15: an `authorized_base_main_sha` that is not actually an ancestor of the
    delivery_head -- e.g. it is a later, divergent, or unrelated commit -- fails closed
    rather than being accepted merely because both are real, resolvable commits
    (`P93-R1-F5`'s closing ancestry-verification requirement)."""
    later = resolve_commit_sha(REPO_ROOT, "HEAD")
    earlier = resolve_commit_sha(REPO_ROOT, "HEAD~3")
    with pytest.raises(DeliveryHeadBindingError):
        verify_authorized_base_ancestry(REPO_ROOT, later, earlier)


def test_nc16_pytest_collection_failure_is_unknown_not_fail(tmp_path: Path) -> None:
    """NC-16: a broken/uncollectable owning test file (e.g. a syntax error) is never
    silently scored as a passing or failing predicate verdict -- it is UNKNOWN, with an
    explicit infrastructure `failure_category`, never negative predicate evidence
    (`P93-R1-F3`)."""
    owner_dir = tmp_path / "owner"
    owner_dir.mkdir()
    (owner_dir / "test_broken_collection.py").write_text(
        "def test_broken(:\n    pass\n", encoding="utf-8"
    )

    from manosube_agent_civilization.v1_0_acceptance import gate22 as gate22_module

    original = gate22_module.PREDICATE_TEST_OWNERS["COMPARATIVE_BENCHMARK_PASS"]
    try:
        gate22_module.PREDICATE_TEST_OWNERS["COMPARATIVE_BENCHMARK_PASS"] = (
            "owner/test_broken_collection.py",
        )
        outcome = gate22_module.rederive_predicate("COMPARATIVE_BENCHMARK_PASS", tmp_path)
    finally:
        gate22_module.PREDICATE_TEST_OWNERS["COMPARATIVE_BENCHMARK_PASS"] = original

    assert outcome.verification_result == "UNKNOWN"
    assert outcome.exit_code not in (0, 1)
    assert outcome.failure_category is not None


def test_nc17_corrupted_fd_0005_classification_is_not_exempted(tmp_path: Path) -> None:
    """NC-17: the FD-0005-specific non-blocking exemption never overrides recognized-
    classification validation -- a register entry claiming record id FD-0005 with a
    corrupted/unrecognized `CLASSIFICATION` value is still rejected as a register-content
    contradiction, not silently waved through by id (`P93-R1-F4`)."""
    register = tmp_path / "register.md"
    register.write_text(
        "# 5. FD-0005 scratch\n\n```text\n"
        "DIFFERENCE_ID=FD-0005\n"
        "CLASSIFICATION=NOT_A_REAL_CLASSIFICATION\n"
        "CURRENT_STATUS=OPEN_NON_BLOCKING_DEFERRED\n"
        "CURRENT_PHASE_BLOCKING_EFFECT=NONE_FOR_PHASE_21\n"
        "```\n",
        encoding="utf-8",
    )
    dispositions = classify_v1_0_blocking_differences(
        tmp_path, register_relative_path="register.md"
    )
    fd_0005 = next(d for d in dispositions if d.record_id == "FD-0005")
    assert fd_0005.disposition == "REGISTER_CONTENT_CONTRADICTION"


def test_nc18_staged_only_dirty_index_fails_closed(tmp_path: Path) -> None:
    """NC-18: a change that is staged into the index -- with no further unstaged diff on
    top of it, i.e. the working tree exactly matches what was just staged -- still fails
    closed. `git status --porcelain` reports a purely staged ("index-only") change too,
    not only an unstaged working-tree change (`P93-R2-F2`)."""
    _first, second = _init_scratch_git_repo(tmp_path)
    (tmp_path / "b.txt").write_text("staged mutation\n", encoding="utf-8")
    _run_git(tmp_path, "add", "b.txt")
    with pytest.raises(DeliveryHeadBindingError):
        verify_repo_root_bound_to_commit(tmp_path, second)


def test_nc19_pytest_internal_error_is_unknown_not_fail(tmp_path: Path) -> None:
    """NC-19: a real pytest internal error -- an unhandled exception inside pytest's own
    hook machinery, `pytest`'s documented exit code 3 (`EXIT_INTERNALERROR`) -- is
    `UNKNOWN` with `failure_category="INTERNAL_ERROR"`, never `FAIL` (`P93-R2-F2`)."""
    owner_dir = tmp_path / "owner"
    owner_dir.mkdir()
    (owner_dir / "test_ok.py").write_text(
        "def test_ok() -> None:\n    assert True\n", encoding="utf-8"
    )
    (tmp_path / "conftest.py").write_text(
        "def pytest_configure(config):\n"
        "    raise RuntimeError('simulated internal error in pytest_configure')\n",
        encoding="utf-8",
    )

    from manosube_agent_civilization.v1_0_acceptance import gate22 as gate22_module

    original = gate22_module.PREDICATE_TEST_OWNERS["COMPARATIVE_BENCHMARK_PASS"]
    try:
        gate22_module.PREDICATE_TEST_OWNERS["COMPARATIVE_BENCHMARK_PASS"] = ("owner/test_ok.py",)
        outcome = gate22_module.rederive_predicate("COMPARATIVE_BENCHMARK_PASS", tmp_path)
    finally:
        gate22_module.PREDICATE_TEST_OWNERS["COMPARATIVE_BENCHMARK_PASS"] = original

    assert outcome.verification_result == "UNKNOWN"
    assert outcome.exit_code == 3
    assert outcome.failure_category == "INTERNAL_ERROR"


def test_nc20_pytest_usage_error_is_unknown_not_fail(tmp_path: Path) -> None:
    """NC-20: a real pytest usage error -- an unrecognized configured CLI option,
    `pytest`'s documented exit code 4 (`EXIT_USAGEERROR`) -- is `UNKNOWN` with
    `failure_category="USAGE_ERROR"`, never `FAIL` (`P93-R2-F2`)."""
    owner_dir = tmp_path / "owner"
    owner_dir.mkdir()
    (owner_dir / "test_ok.py").write_text(
        "def test_ok() -> None:\n    assert True\n", encoding="utf-8"
    )
    (tmp_path / "pytest.ini").write_text(
        "[pytest]\naddopts = --this-option-does-not-exist-xyz\n", encoding="utf-8"
    )

    from manosube_agent_civilization.v1_0_acceptance import gate22 as gate22_module

    original = gate22_module.PREDICATE_TEST_OWNERS["COMPARATIVE_BENCHMARK_PASS"]
    try:
        gate22_module.PREDICATE_TEST_OWNERS["COMPARATIVE_BENCHMARK_PASS"] = ("owner/test_ok.py",)
        outcome = gate22_module.rederive_predicate("COMPARATIVE_BENCHMARK_PASS", tmp_path)
    finally:
        gate22_module.PREDICATE_TEST_OWNERS["COMPARATIVE_BENCHMARK_PASS"] = original

    assert outcome.verification_result == "UNKNOWN"
    assert outcome.exit_code == 4
    assert outcome.failure_category == "USAGE_ERROR"


def test_nc21_wrong_repository_project_binding_fails_closed(tmp_path: Path) -> None:
    """NC-21: a repository that carries the exact same git objects as the authorized
    project -- a real `git clone` of it, identical commit SHAs and ancestry -- but whose
    `origin` remote resolves to a different GitHub project is rejected. Commit-object
    identity and ancestry prove nothing about *which* repository a caller-supplied
    `repo_root` actually is (`P93-R2-F1`)."""
    origin_repo = tmp_path / "origin_repo"
    origin_repo.mkdir()
    _init_scratch_git_repo(origin_repo)
    clone_repo = tmp_path / "clone_repo"
    _run_git(tmp_path, "clone", "-q", str(origin_repo), str(clone_repo))
    _run_git(
        clone_repo,
        "remote",
        "set-url",
        "origin",
        "https://github.com/someone-else/unrelated-repo.git",
    )

    with pytest.raises(RepositoryProjectBindingError):
        verify_repository_project_binding(clone_repo)


def test_nc22_lookalike_hostname_bypass_fails_closed(tmp_path: Path) -> None:
    """NC-22: a remote URL on a lookalike host that merely *contains* the substring
    `github.com` -- `https://evilgithub.com/manosube/manosube-agent-civilization-os.git`
    -- is rejected. The exact authorized `owner/repo` appears in the URL path, so a
    substring-based host check would have wrongly accepted this; only a structural
    hostname check (`urllib.parse.urlsplit(url).hostname == "github.com"`) closes it
    (`P93-R3-F1`)."""
    _first, _second = _init_scratch_git_repo(tmp_path)
    _run_git(
        tmp_path,
        "remote",
        "add",
        "origin",
        "https://evilgithub.com/manosube/manosube-agent-civilization-os.git",
    )

    with pytest.raises(RepositoryProjectBindingError):
        verify_repository_project_binding(tmp_path)
