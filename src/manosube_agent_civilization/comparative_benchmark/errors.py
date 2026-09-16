"""Typed exception hierarchy for the Comparative Benchmark package (Issue #89,
`ADOPT_PHASE_21_COMPARATIVE_BENCHMARK`)."""

from __future__ import annotations


class ComparativeBenchmarkError(Exception):
    """Base for every error this package raises."""


class ProtocolFreezeValidationError(ComparativeBenchmarkError):
    """A protocol freeze failed schema validation or one of this package's own
    fail-closed structural checks (e.g. `MANOSUBE_PRESENT`/`MANOSUBE_ABSENT`
    `mechanism_identity` sets overlapping)."""


class ResultBundleValidationError(ComparativeBenchmarkError):
    """A result bundle failed schema validation, or referenced a `comparison_group_id`
    the bound protocol freeze never declared."""


class ReproductionReceiptValidationError(ComparativeBenchmarkError):
    """A reproduction receipt failed schema validation, or a self-run reproduction
    claimed `is_original_author=False` while its own reproducer identity matches the
    original run's."""


class IndependentReproductionSubmissionValidationError(ComparativeBenchmarkError):
    """An independent reproduction submission (P90-R3-F2) failed schema validation, its own
    signature does not verify against its own declared public key, or it does not genuinely
    bind to an already-committed protocol freeze/result bundle."""


__all__ = [
    "ComparativeBenchmarkError",
    "IndependentReproductionSubmissionValidationError",
    "ProtocolFreezeValidationError",
    "ReproductionReceiptValidationError",
    "ResultBundleValidationError",
]
