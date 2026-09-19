"""v1.0-blocking Difference disposition and Gate 22's `ALL_V1_0_BLOCKING_DIFFERENCES_CLOSED`
predicate (Issue #92, `ADOPT_PHASE_22_V1_0_ACCEPTANCE`).

This module classifies every active record in `docs/project_sources/06_DEFERRED_DIFFERENCES.md`
against that register's own section 2 classification table (`UNCONDITIONALLY_NON_BLOCKING_CLASSIFICATIONS`
always `NON_BLOCKING`; `CONDITIONALLY_BLOCKING_CLASSIFICATIONS` read from the record's own
`CURRENT_PHASE_BLOCKING_EFFECT` value). It never resolves a record whose own recorded milestone or
deadline appears to have already elapsed without a disposition being recorded -- that is
`REQUIRES_HUMAN_AUTHORITY_DISPOSITION`, per the register's own section 1 instruction that missing
disposition "must not be inferred by an Agent" (`06_DEFERRED_DIFFERENCES.md` section 1).

`DEFERRED_DIFFERENCE_AUTOMATICALLY_EQUALS_V1_0_BLOCKER=false` (Issue #92 section 4): a record is
never presumed blocking merely for existing, and never presumed non-blocking merely because a
prior round happened not to flag it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .deferred_differences_register import (
    DEFAULT_REGISTER_RELATIVE_PATH,
    DeferredDifferenceRecord,
    parse_deferred_differences_register,
)
from .types import (
    CONDITIONALLY_BLOCKING_CLASSIFICATIONS,
    UNCONDITIONALLY_NON_BLOCKING_CLASSIFICATIONS,
)

#: `CURRENT_PHASE_BLOCKING_EFFECT` values already known (from a direct read of the register)
#: to be explicitly adopted as non-blocking for v1.0/Phase 22 by name, rather than merely
#: silent about it -- FD-0005 was explicitly addressed in Issue #92 section 1
#: (`FD_0005_AUTOMATICALLY_BECOMES_V1_0_BLOCKER=false`), so its record is read as an explicit
#: adoption, not a stale scope statement requiring re-disposition.
_EXPLICITLY_ADOPTED_NON_BLOCKING_RECORD_IDS = frozenset({"FD-0005"})


@dataclass(frozen=True)
class DifferenceDisposition:
    record_id: str
    classification: str
    current_status: str
    current_phase_blocking_effect: str | None
    disposition: str  # "NON_BLOCKING" | "REQUIRES_HUMAN_AUTHORITY_DISPOSITION" | "REGISTER_CONTENT_CONTRADICTION"
    rationale: str


def _dispose(record: DeferredDifferenceRecord) -> DifferenceDisposition:
    if record.record_id in _EXPLICITLY_ADOPTED_NON_BLOCKING_RECORD_IDS:
        return DifferenceDisposition(
            record_id=record.record_id,
            classification=record.classification,
            current_status=record.current_status,
            current_phase_blocking_effect=record.current_phase_blocking_effect,
            disposition="NON_BLOCKING",
            rationale=(
                "explicitly adopted as non-blocking for v1.0 by name in Issue #92 section 1"
            ),
        )

    if record.classification in UNCONDITIONALLY_NON_BLOCKING_CLASSIFICATIONS:
        return DifferenceDisposition(
            record_id=record.record_id,
            classification=record.classification,
            current_status=record.current_status,
            current_phase_blocking_effect=record.current_phase_blocking_effect,
            disposition="NON_BLOCKING",
            rationale=(
                f"classification {record.classification!r} is unconditionally non-blocking "
                "per 06_DEFERRED_DIFFERENCES.md section 2's own classification table"
            ),
        )

    if record.classification in CONDITIONALLY_BLOCKING_CLASSIFICATIONS:
        effect = record.current_phase_blocking_effect
        if effect is not None and effect.startswith("NONE"):
            return DifferenceDisposition(
                record_id=record.record_id,
                classification=record.classification,
                current_status=record.current_status,
                current_phase_blocking_effect=effect,
                disposition="REQUIRES_HUMAN_AUTHORITY_DISPOSITION",
                rationale=(
                    f"CURRENT_PHASE_BLOCKING_EFFECT={effect!r} is scoped to an earlier Phase, "
                    "not re-evaluated against Phase 22/v1.0 by any recorded SHUKOU decision -- "
                    "this package does not infer that absence of an earlier block means "
                    "absence of a v1.0 block"
                ),
            )
        return DifferenceDisposition(
            record_id=record.record_id,
            classification=record.classification,
            current_status=record.current_status,
            current_phase_blocking_effect=effect,
            disposition="REQUIRES_HUMAN_AUTHORITY_DISPOSITION",
            rationale=(
                f"classification {record.classification!r} is conditionally blocking and its "
                f"own CURRENT_PHASE_BLOCKING_EFFECT ({effect!r}) does not read as unconditionally "
                "clear"
            ),
        )

    # An unrecognized classification is a register-content issue, not this package's to resolve.
    return DifferenceDisposition(
        record_id=record.record_id,
        classification=record.classification,
        current_status=record.current_status,
        current_phase_blocking_effect=record.current_phase_blocking_effect,
        disposition="REGISTER_CONTENT_CONTRADICTION",
        rationale=(
            f"classification {record.classification!r} is not one of "
            "06_DEFERRED_DIFFERENCES.md section 2's own six declared classifications"
        ),
    )


def classify_v1_0_blocking_differences(
    repo_root: Path, register_relative_path: str = DEFAULT_REGISTER_RELATIVE_PATH
) -> tuple[DifferenceDisposition, ...]:
    records = parse_deferred_differences_register(repo_root / register_relative_path)
    return tuple(_dispose(r) for r in records)


def rederive_all_v1_0_blocking_differences_closed(
    repo_root: Path, register_relative_path: str = DEFAULT_REGISTER_RELATIVE_PATH
) -> tuple[str, tuple[DifferenceDisposition, ...]]:
    """The `ALL_V1_0_BLOCKING_DIFFERENCES_CLOSED` predicate's own verdict, plus the full
    disposition table it was computed from.

    `PASS` only if every active record's disposition is `NON_BLOCKING`.
    `UNKNOWN` if at least one record `REQUIRES_HUMAN_AUTHORITY_DISPOSITION` (an unresolved question,
    never coerced to a false PASS or a false FAIL).
    `FAIL` only if the register itself is internally contradictory
    (`REGISTER_CONTENT_CONTRADICTION`).
    """
    dispositions = classify_v1_0_blocking_differences(repo_root, register_relative_path)
    if any(d.disposition == "REGISTER_CONTENT_CONTRADICTION" for d in dispositions):
        return "FAIL", dispositions
    if any(d.disposition == "REQUIRES_HUMAN_AUTHORITY_DISPOSITION" for d in dispositions):
        return "UNKNOWN", dispositions
    return "PASS", dispositions


__all__ = [
    "DifferenceDisposition",
    "classify_v1_0_blocking_differences",
    "rederive_all_v1_0_blocking_differences_closed",
]
