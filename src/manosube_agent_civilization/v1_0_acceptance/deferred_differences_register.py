"""A read-only parser over `docs/project_sources/06_DEFERRED_DIFFERENCES.md`
(Issue #92, `ADOPT_PHASE_22_V1_0_ACCEPTANCE`).

This module never writes to the register and never resolves an ambiguous or stale
record on its own authority (`06_DEFERRED_DIFFERENCES.md` section 1: "Missing
placement or deadline information must be expressed as unresolved Human decision.
It must not be inferred by an Agent"). It only extracts each active record's own
already-recorded fields, mechanically, by regex over the document's own fenced
`text` blocks -- the same "pin the parsed value, drift-test it against the live
document" idiom `reflow/invariant_registry.py` already uses for
`KERNEL_INVARIANTS.md`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .errors import DeferredDifferencesRegisterError

_RECORD_ID_PATTERN = re.compile(r"^(?:DIFFERENCE_ID|CANDIDATE_ID)=(\S+)$", re.MULTILINE)
_CLASSIFICATION_PATTERN = re.compile(r"^CLASSIFICATION=(\S+)$", re.MULTILINE)
_CURRENT_STATUS_PATTERN = re.compile(r"^CURRENT_STATUS=(\S+)$", re.MULTILINE)
_BLOCKING_EFFECT_PATTERN = re.compile(r"^CURRENT_PHASE_BLOCKING_EFFECT=(\S+)$", re.MULTILINE)

#: A `# N. <heading>` (or `# Na. <heading>`) top-level section boundary -- the register's
#: own consistent section-numbering convention (see `06_DEFERRED_DIFFERENCES.md` sections
#: 0-15). A record's own fields never cross into the next section.
_SECTION_HEADING_PATTERN = re.compile(r"^# \S+\.\s", re.MULTILINE)

DEFAULT_REGISTER_RELATIVE_PATH = "docs/project_sources/06_DEFERRED_DIFFERENCES.md"


@dataclass(frozen=True)
class DeferredDifferenceRecord:
    """One active record's own already-recorded fields, exactly as the register
    states them -- never inferred, never normalized beyond whitespace stripping."""

    record_id: str
    classification: str
    current_status: str
    current_phase_blocking_effect: str | None


def _iter_sections(text: str) -> list[str]:
    boundaries = [m.start() for m in _SECTION_HEADING_PATTERN.finditer(text)]
    boundaries.append(len(text))
    return [text[boundaries[i] : boundaries[i + 1]] for i in range(len(boundaries) - 1)]


def parse_deferred_differences_register(
    register_path: Path,
) -> tuple[DeferredDifferenceRecord, ...]:
    """Parse every active record (`DIFFERENCE_ID=` or `CANDIDATE_ID=`) out of the register at
    `register_path`, one `DeferredDifferenceRecord` per record, in document order.

    Raises `DeferredDifferencesRegisterError` if the file is unreadable, or a section
    declaring a record id is missing `CLASSIFICATION=` or `CURRENT_STATUS=` -- this
    package must never silently skip a record the register itself declares active.
    """
    try:
        text = register_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DeferredDifferencesRegisterError(
            f"could not read Deferred Differences register at {register_path}: {exc}"
        ) from exc

    records: list[DeferredDifferenceRecord] = []
    for section in _iter_sections(text):
        id_match = _RECORD_ID_PATTERN.search(section)
        if id_match is None:
            continue
        record_id = id_match.group(1)

        classification_match = _CLASSIFICATION_PATTERN.search(section)
        if classification_match is None:
            raise DeferredDifferencesRegisterError(
                f"record {record_id!r} declares an id but no CLASSIFICATION= field"
            )
        status_match = _CURRENT_STATUS_PATTERN.search(section)
        if status_match is None:
            raise DeferredDifferencesRegisterError(
                f"record {record_id!r} declares an id but no CURRENT_STATUS= field"
            )
        blocking_match = _BLOCKING_EFFECT_PATTERN.search(section)

        records.append(
            DeferredDifferenceRecord(
                record_id=record_id,
                classification=classification_match.group(1),
                current_status=status_match.group(1),
                current_phase_blocking_effect=(
                    blocking_match.group(1) if blocking_match is not None else None
                ),
            )
        )
    return tuple(records)


__all__ = [
    "DEFAULT_REGISTER_RELATIVE_PATH",
    "DeferredDifferenceRecord",
    "parse_deferred_differences_register",
]
