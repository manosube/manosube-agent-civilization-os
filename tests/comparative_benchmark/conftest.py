"""Shared, session-scoped fixture for the Phase 21 Comparative Benchmark test suite.

:func:`comparative_benchmark_run` performs one full, real, end-to-end run (protocol freeze ->
both comparison-group families' real raw events -> result bundle -> independent reproduction
receipt) -- real Observation/Difference/Authority/Reflow calls for the ``MANOSUBE_PRESENT``
group's 8-task corpus, twice over (the original run and the independent reproducer's own re-run).
This is genuinely expensive (several real ``reflow()`` commits), so it is computed exactly once
per test session and shared by every test in this package that only needs to *read* its result --
the identical "share one already-expensive real run rather than paying for a second one" economy
``tests/contract/long_running_proof_artifact/test_long_running_proof_artifact_bundle.py``'s own
module docstring already states for Phase 20."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.comparative_benchmark.orchestrator import run_comparative_benchmark


@pytest.fixture(scope="session")
def comparative_benchmark_run(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    root: Path = tmp_path_factory.mktemp("comparative_benchmark_run")
    return run_comparative_benchmark(root)
