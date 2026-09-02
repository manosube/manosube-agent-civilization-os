"""Which prohibitions a request touches, evaluated before any rule is looked at.

Order is the substance of this module, not an implementation detail. A prohibition is a
*found refusal*, not a *missing permission*, so it is answered first -- otherwise a
successful rule lookup becomes a path that skips the refusal entirely
(``PROHIBITION_CONTRACT.md`` §4).
"""

from __future__ import annotations

from typing import Any

from .conformance import admit
from .scope import overlaps, require_scope

CONSTITUTIONAL = "CONSTITUTIONAL"
PROJECT = "PROJECT"
PROHIBITION_CLASSES: frozenset[str] = frozenset({CONSTITUTIONAL, PROJECT})

def require_prohibition(value: Any, context: str) -> dict[str, Any]:
    """Return *value* once it is a canonical prohibition; reject it otherwise.

    The same shared admission every supplied record crosses. A prohibition that could be
    forged would be worse than one that could be missed: it is the half of the vocabulary
    that cannot be appealed.
    """

    prohibition = admit(value, "prohibition", context)
    require_scope(prohibition["scope"], f"{context} scope")
    return prohibition


def applies_to_project(prohibition: dict[str, Any], project_id: str) -> bool:
    """Whether this prohibition reaches *project_id*.

    A ``PROJECT`` prohibition stops at its own project. A ``CONSTITUTIONAL`` one belongs to
    the Kernel and does not stop at a project boundary -- ``PROHIBITION_CONTRACT.md`` §7.
    """

    if prohibition["prohibition_class"] == CONSTITUTIONAL:
        return True
    return bool(prohibition["project_id"] == project_id)


def matching(
    prohibitions: list[dict[str, Any]],
    *,
    project_id: str,
    action_kind: str,
    requested_scope: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return every prohibition this request touches, in canonical identity order.

    Ordering is by identity rather than by input position so that the same set of
    prohibitions, supplied in any order, produces the same decision record.
    """

    matched = [
        prohibition
        for prohibition in prohibitions
        if applies_to_project(prohibition, project_id)
        and action_kind in prohibition["action_kinds"]
        and overlaps(requested_scope, prohibition["scope"])
    ]
    return sorted(matched, key=lambda prohibition: str(prohibition["prohibition_id"]))


def has_constitutional(prohibitions: list[dict[str, Any]]) -> bool:
    """Whether any matched prohibition is one an approval can never lift."""

    return any(prohibition["prohibition_class"] == CONSTITUTIONAL for prohibition in prohibitions)
