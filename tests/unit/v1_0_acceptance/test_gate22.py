"""V1: Gate 22 mechanical predicate rederivation (Issue #92, `ADOPT_PHASE_22_V1_0_ACCEPTANCE`).

Only `COMPARATIVE_BENCHMARK_PASS` is re-run here at unit scope (its owning suite is fast
and already exercised elsewhere) -- rederiving *all* pytest-owned predicates end-to-end is
`tests/contract/v1_0_acceptance/test_gate22_rederivation.py`'s own job, run once.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from manosube_agent_civilization.v1_0_acceptance.gate22 import (
    PREDICATE_TEST_OWNERS,
    rederive_predicate,
)
from manosube_agent_civilization.v1_0_acceptance.types import GATE_22_PREDICATES

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_every_pytest_owned_predicate_has_at_least_one_owner_path() -> None:
    pytest_owned = set(GATE_22_PREDICATES) - {"ALL_V1_0_BLOCKING_DIFFERENCES_CLOSED"}
    assert set(PREDICATE_TEST_OWNERS) == pytest_owned
    for predicate, paths in PREDICATE_TEST_OWNERS.items():
        assert paths, predicate


def test_every_owner_path_exists_in_this_repository() -> None:
    for predicate, paths in PREDICATE_TEST_OWNERS.items():
        for path in paths:
            assert (REPO_ROOT / path).is_file(), f"{predicate}: missing owner {path}"


def test_comparative_benchmark_pass_rederives_pass() -> None:
    result = rederive_predicate("COMPARATIVE_BENCHMARK_PASS", REPO_ROOT)
    assert result.verification_result == "PASS"
    assert result.exit_code == 0
    assert result.missing_paths == ()
    assert result.failure_category is None


def test_missing_owner_path_yields_unknown_never_a_silent_fail(tmp_path: Path) -> None:
    result = rederive_predicate("COMPARATIVE_BENCHMARK_PASS", tmp_path)
    assert result.verification_result == "UNKNOWN"
    assert result.exit_code is None
    assert result.missing_paths
    assert result.failure_category == "MISSING_OWNER"


def test_unowned_predicate_raises() -> None:
    with pytest.raises(KeyError):
        rederive_predicate("ALL_V1_0_BLOCKING_DIFFERENCES_CLOSED", REPO_ROOT)
