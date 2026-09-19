"""Gate 22 mechanical predicate rederivation (Issue #92, `ADOPT_PHASE_22_V1_0_ACCEPTANCE`).

Eleven of the twelve canonical predicates (all but `ALL_V1_0_BLOCKING_DIFFERENCES_CLOSED`,
owned by `blocking_differences.py`) are rederived by actually re-running the exact,
already-accepted test module(s) that proved them in their owning Phase -- never by
regex-parsing prose, never by trusting a restated boolean, matching
`reflow/closure.py`'s own "provenance by reproduction, not by trust" principle. A
predicate's `verification_result` is `PASS` only when every one of its owning test
modules exits `0`; `FAIL` when the owning suite ran and reported a failure; `UNKNOWN`
when the owning suite could not even be collected (e.g. the module does not exist at
the given `repo_root` -- a genuine "this predicate has no resolvable owner here" state,
never silently coerced to `FAIL`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys

from .types import GATE_22_PREDICATES

#: Each predicate's owning, already-accepted test module(s) -- the exact evidence this
#: package re-executes rather than re-derives from scratch. Paths are relative to the
#: repository root and are re-run through the same interpreter this process runs under
#: so the rederivation uses the identical environment the full suite itself uses.
PREDICATE_TEST_OWNERS: dict[str, tuple[str, ...]] = {
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

#: `ALL_V1_0_BLOCKING_DIFFERENCES_CLOSED` is deliberately absent from
#: `PREDICATE_TEST_OWNERS` -- it has no owning pytest module; `blocking_differences.py`
#: rederives it directly from the Deferred Differences register.
_PYTEST_OWNED_PREDICATES = frozenset(GATE_22_PREDICATES) - {"ALL_V1_0_BLOCKING_DIFFERENCES_CLOSED"}


@dataclass(frozen=True)
class PredicateRederivation:
    predicate: str
    owner_test_paths: tuple[str, ...]
    verification_result: str  # "PASS" | "FAIL" | "UNKNOWN"
    exit_code: int | None
    missing_paths: tuple[str, ...]


def rederive_predicate(predicate: str, repo_root: Path) -> PredicateRederivation:
    """Re-run `predicate`'s owning test module(s) under `repo_root` and report the
    mechanical verdict. Never raises on a test failure -- a failing owning suite is a
    legitimate `FAIL` result, not an error in this package."""
    if predicate not in _PYTEST_OWNED_PREDICATES:
        raise KeyError(f"{predicate!r} is not a pytest-owned Gate 22 predicate")

    owner_paths = PREDICATE_TEST_OWNERS[predicate]
    missing = tuple(p for p in owner_paths if not (repo_root / p).is_file())
    if missing:
        return PredicateRederivation(
            predicate=predicate,
            owner_test_paths=owner_paths,
            verification_result="UNKNOWN",
            exit_code=None,
            missing_paths=missing,
        )

    result = subprocess.run(  # noqa: S603 -- fixed interpreter (sys.executable); owner paths are pinned literals
        [sys.executable, "-m", "pytest", "-q", *owner_paths],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    verdict = "PASS" if result.returncode == 0 else "FAIL"
    return PredicateRederivation(
        predicate=predicate,
        owner_test_paths=owner_paths,
        verification_result=verdict,
        exit_code=result.returncode,
        missing_paths=(),
    )


def rederive_all_pytest_owned_predicates(repo_root: Path) -> dict[str, PredicateRederivation]:
    """Rederive every pytest-owned predicate, running each distinct owner test-path set
    exactly once even when several predicates share it (e.g. four predicates all owned
    by `test_long_running_proof_gate_20.py`) -- never re-invoking the same subprocess
    suite once per predicate that happens to cite it."""
    by_paths: dict[tuple[str, ...], PredicateRederivation] = {}
    results: dict[str, PredicateRederivation] = {}
    for predicate in sorted(_PYTEST_OWNED_PREDICATES):
        owner_paths = PREDICATE_TEST_OWNERS[predicate]
        cached = by_paths.get(owner_paths)
        if cached is None:
            cached = rederive_predicate(predicate, repo_root)
            by_paths[owner_paths] = cached
        results[predicate] = PredicateRederivation(
            predicate=predicate,
            owner_test_paths=cached.owner_test_paths,
            verification_result=cached.verification_result,
            exit_code=cached.exit_code,
            missing_paths=cached.missing_paths,
        )
    return results


__all__ = [
    "PREDICATE_TEST_OWNERS",
    "PredicateRederivation",
    "rederive_all_pytest_owned_predicates",
    "rederive_predicate",
]
