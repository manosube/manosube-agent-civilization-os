"""The pinned Evidence Level scale is the one the Kernel actually declares.

``CLOSURE_POLICY.md`` §5 requires the sufficiency gate to resolve the ordered scale from
``00_KERNEL/COMPLETION_SEMANTICS.md`` by content-addressed blob reference, and to treat an
unknown level, an unclear order or a source mismatch as ``BLOCKED``. A pure engine cannot
open a file, so the obligation is split in two and both halves are checkable:

```text
levels.EVIDENCE_LEVEL_SCALE      pinned      <- this module proves it equals the document
sufficiency.evidence_level_...   addressed   <- the engine refuses a ref naming another
```

Without this module the pin could drift from the constitution and nothing would notice,
which is the whole failure mode ``CLOSURE_POLICY.md`` is guarding against: a policy written
against one scale, evaluated against another.
"""

from __future__ import annotations

from pathlib import Path
import re

from manosube_agent_civilization.evidence.levels import (
    EVIDENCE_LEVEL_LABELS,
    EVIDENCE_LEVEL_SCALE,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
COMPLETION_SEMANTICS = REPOSITORY_ROOT / "00_KERNEL" / "COMPLETION_SEMANTICS.md"
CONSTITUTION = REPOSITORY_ROOT / "00_KERNEL" / "KERNEL_CONSTITUTION.md"

#: ``E<n> = <label>`` as both documents write it, anchored so a level named inside prose
#: cannot be mistaken for a declaration.
DECLARATION = re.compile(r"^(E[0-6]) = (.+?)\s*$", re.MULTILINE)


def _declared(path: Path) -> dict[str, str]:
    return dict(DECLARATION.findall(path.read_text(encoding="utf-8")))


def test_the_pinned_scale_is_the_scale_completion_semantics_declares() -> None:
    assert _declared(COMPLETION_SEMANTICS) == EVIDENCE_LEVEL_LABELS


def test_the_pinned_scale_is_the_scale_the_constitution_declares() -> None:
    """第29条 and ``COMPLETION_SEMANTICS.md`` chapter 3 must not have diverged either."""

    assert _declared(CONSTITUTION) == EVIDENCE_LEVEL_LABELS


def test_the_scale_is_ordered_weakest_first_and_complete() -> None:
    assert tuple(sorted(EVIDENCE_LEVEL_LABELS)) == EVIDENCE_LEVEL_SCALE
    assert len(EVIDENCE_LEVEL_SCALE) == len(set(EVIDENCE_LEVEL_SCALE)) == 7


def test_the_source_documents_are_present_and_declare_something() -> None:
    """The positive control. Without it, a moved or emptied document would read as agreement.

    A regex that finds nothing returns ``{}``, and ``{} == {}`` is true, so two missing
    documents would silently satisfy both tests above.
    """

    assert _declared(COMPLETION_SEMANTICS)
    assert _declared(CONSTITUTION)
