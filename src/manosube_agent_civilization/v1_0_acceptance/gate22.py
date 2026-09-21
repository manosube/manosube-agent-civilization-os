"""Gate 22 mechanical predicate rederivation (Issue #92, `ADOPT_PHASE_22_V1_0_ACCEPTANCE`).

Eleven of the twelve canonical predicates (all but `ALL_V1_0_BLOCKING_DIFFERENCES_CLOSED`,
owned by `blocking_differences.py`) are rederived by actually re-running the exact,
already-accepted test module(s) that proved them in their owning Phase -- never by
regex-parsing prose, never by trusting a restated boolean, matching
`reflow/closure.py`'s own "provenance by reproduction, not by trust" principle.

A predicate's `verification_result` is `PASS` only when every one of its owning test
modules exits `0` (`pytest`'s own `EXIT_OK`); `FAIL` only when `pytest` exits `1`
(`EXIT_TESTSFAILED` -- tests were actually collected, run, and some failed); `UNKNOWN`
for every other outcome: the owning module does not exist at the given `repo_root`, the
subprocess itself could not be launched, it was terminated by a signal, or `pytest`
exited `2` (`EXIT_INTERRUPTED`), `3` (`EXIT_INTERNALERROR`), `4` (`EXIT_USAGEERROR`) or
`5` (`EXIT_NOTESTSCOLLECTED`). Infrastructure inability to even collect or run the
owning suite must never be recorded as negative predicate evidence -- only a real,
completed test run that actually failed does that (PR #93 Structural Review Round 1,
`P93-R1-F3`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys

from .types import GATE_22_PREDICATES

#: `pytest`'s own documented non-{0,1} exit codes -- each one is an infrastructure/
#: collection outcome, never negative predicate evidence. Any other, unrecognized
#: nonnegative exit code (a `pytest` version this mapping has not seen) fails closed to
#: `UNKNOWN` too, under `"UNRECOGNIZED_EXIT_CODE"`.
_PYTEST_EXIT_CODE_CATEGORIES: dict[int, str] = {
    2: "INTERRUPTED",
    3: "INTERNAL_ERROR",
    4: "USAGE_ERROR",
    5: "NO_TESTS_COLLECTED",
}

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
    #: `None` for `PASS`/`FAIL`; a machine-readable reason for every `UNKNOWN`
    #: (`"MISSING_OWNER"`, `"LAUNCH_ERROR"`, `"TERMINATED_BY_SIGNAL"`,
    #: `"INTERRUPTED"`, `"INTERNAL_ERROR"`, `"USAGE_ERROR"`, `"NO_TESTS_COLLECTED"`, or
    #: `"UNRECOGNIZED_EXIT_CODE"`).
    failure_category: str | None = None


def rederive_predicate(predicate: str, repo_root: Path) -> PredicateRederivation:
    """Re-run `predicate`'s owning test module(s) under `repo_root` and report the
    mechanical verdict. Never raises on a test failure -- a failing owning suite is a
    legitimate `FAIL` result, not an error in this package. Distinguishes a real
    completed-and-failed run (`FAIL`, `pytest` exit `1`) from every infrastructure
    outcome (`UNKNOWN`) -- a missing owner, a subprocess launch failure, termination by
    signal, or any other `pytest` exit code (PR #93 Structural Review Round 1,
    `P93-R1-F3`)."""
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
            failure_category="MISSING_OWNER",
        )

    try:
        result = subprocess.run(  # noqa: S603 -- fixed interpreter (sys.executable); owner paths are pinned literals
            [sys.executable, "-m", "pytest", "-q", *owner_paths],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return PredicateRederivation(
            predicate=predicate,
            owner_test_paths=owner_paths,
            verification_result="UNKNOWN",
            exit_code=None,
            missing_paths=(),
            failure_category="LAUNCH_ERROR",
        )

    code = result.returncode
    if code == 0:
        verdict, category = "PASS", None
    elif code == 1:
        verdict, category = "FAIL", None
    elif code < 0:
        # A negative returncode is Python's own convention for "terminated by signal
        # -code" -- never a completed, failed test run.
        verdict, category = "UNKNOWN", "TERMINATED_BY_SIGNAL"
    else:
        verdict = "UNKNOWN"
        category = _PYTEST_EXIT_CODE_CATEGORIES.get(code, "UNRECOGNIZED_EXIT_CODE")

    return PredicateRederivation(
        predicate=predicate,
        owner_test_paths=owner_paths,
        verification_result=verdict,
        exit_code=code,
        missing_paths=(),
        failure_category=category,
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
            failure_category=cached.failure_category,
        )
    return results


__all__ = [
    "PREDICATE_TEST_OWNERS",
    "PredicateRederivation",
    "rederive_all_pytest_owned_predicates",
    "rederive_predicate",
]
