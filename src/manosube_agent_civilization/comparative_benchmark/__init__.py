"""Comparative Benchmark (Issue #89, `ADOPT_PHASE_21_COMPARATIVE_BENCHMARK`).

Public surface: exactly the six commit/resolve entrypoints in `route.py`. Every other module
in this package (`engine.py`, `identity.py`, `types.py`, `errors.py`) is an internal detail a
caller reaches only through these six -- stated as an explicit count so a seventh route
appearing here cannot go unnoticed."""

from __future__ import annotations

from .route import (
    commit_protocol_freeze,
    commit_reproduction_receipt,
    commit_result_bundle,
    resolve_protocol_freeze,
    resolve_reproduction_receipt,
    resolve_result_bundle,
)

PUBLIC_COMPARATIVE_BENCHMARK_ENTRY_POINT_COUNT = 6

__all__ = [
    "PUBLIC_COMPARATIVE_BENCHMARK_ENTRY_POINT_COUNT",
    "commit_protocol_freeze",
    "commit_reproduction_receipt",
    "commit_result_bundle",
    "resolve_protocol_freeze",
    "resolve_reproduction_receipt",
    "resolve_result_bundle",
]
