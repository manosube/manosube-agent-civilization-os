"""Comparative Benchmark (Issue #89, `ADOPT_PHASE_21_COMPARATIVE_BENCHMARK`; PR #90 Round 3,
`ADOPT_P90_R3_BOUNDED_REAL_AGENT_AND_INDEPENDENT_REPRODUCER_LANE`; PR #90 Round 4,
`ADOPT_P90_R4_REAL_AGENT_CORPUS_AND_PRETRUSTED_INDEPENDENT_REPRODUCER`).

Public surface: exactly the ten commit/resolve/admit entrypoints in `route.py`. Every other
module in this package (`engine.py`, `identity.py`, `types.py`, `errors.py`) is an internal
detail a caller reaches only through these ten -- stated as an explicit count so an eleventh
route appearing here cannot go unnoticed."""

from __future__ import annotations

from .route import (
    admit_independent_reproducer_trust_anchor,
    admit_independent_reproduction_submission,
    commit_protocol_freeze,
    commit_reproduction_receipt,
    commit_result_bundle,
    resolve_independent_reproducer_trust_anchor,
    resolve_independent_reproduction_submission,
    resolve_protocol_freeze,
    resolve_reproduction_receipt,
    resolve_result_bundle,
)

PUBLIC_COMPARATIVE_BENCHMARK_ENTRY_POINT_COUNT = 10

__all__ = [
    "PUBLIC_COMPARATIVE_BENCHMARK_ENTRY_POINT_COUNT",
    "admit_independent_reproducer_trust_anchor",
    "admit_independent_reproduction_submission",
    "commit_protocol_freeze",
    "commit_reproduction_receipt",
    "commit_result_bundle",
    "resolve_independent_reproducer_trust_anchor",
    "resolve_independent_reproduction_submission",
    "resolve_protocol_freeze",
    "resolve_reproduction_receipt",
    "resolve_result_bundle",
]
