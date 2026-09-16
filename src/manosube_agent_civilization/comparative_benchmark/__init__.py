"""Comparative Benchmark (Issue #89, `ADOPT_PHASE_21_COMPARATIVE_BENCHMARK`; PR #90 Round 3,
`ADOPT_P90_R3_BOUNDED_REAL_AGENT_AND_INDEPENDENT_REPRODUCER_LANE`).

Public surface: exactly the eight commit/resolve/admit entrypoints in `route.py`. Every other
module in this package (`engine.py`, `identity.py`, `types.py`, `errors.py`) is an internal
detail a caller reaches only through these eight -- stated as an explicit count so a ninth
route appearing here cannot go unnoticed."""

from __future__ import annotations

from .route import (
    admit_independent_reproduction_submission,
    commit_protocol_freeze,
    commit_reproduction_receipt,
    commit_result_bundle,
    resolve_independent_reproduction_submission,
    resolve_protocol_freeze,
    resolve_reproduction_receipt,
    resolve_result_bundle,
)

PUBLIC_COMPARATIVE_BENCHMARK_ENTRY_POINT_COUNT = 8

__all__ = [
    "PUBLIC_COMPARATIVE_BENCHMARK_ENTRY_POINT_COUNT",
    "admit_independent_reproduction_submission",
    "commit_protocol_freeze",
    "commit_reproduction_receipt",
    "commit_result_bundle",
    "resolve_independent_reproduction_submission",
    "resolve_protocol_freeze",
    "resolve_reproduction_receipt",
    "resolve_result_bundle",
]
