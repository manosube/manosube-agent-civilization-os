"""The one mutation Reflow applies to ``semantic_state``, scoped exactly as
``REFLOW_CONTRACT.md`` section 4.1 states: Kernel bookkeeping fields only, never a
domain's opaque ``claims``.

```text
書き換える       open_differences, active_changes, evidence,
                unresolved_contradictions, reflow_state, lineage, authority
書き換えない     project, objective, repository, requirements, code, tests,
                runtime, infrastructure, deployment の claims/status/identity_refs
```

``open_differences`` is a plain reference list nothing else in the Kernel writes to (no
other producer mints one) -- Reflow is its first and only writer, so what this module
decides is simply: a Difference's reference is a member of it exactly while the
Difference's own current status is non-terminal, and absent exactly while it is CLOSED,
SUPERSEDED or INVALIDATED. ``lineage`` gets the minted lifecycle event appended to its
``identity_refs``; nothing beyond that field of the domain shape is touched, since no
grammar for the domain's ``claims``/``status`` exists anywhere in the frozen tree for
Reflow to invent one against.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from manosube_agent_civilization.difference.lifecycle import TERMINAL_STATUSES

#: CLOSED is not in ``difference/lifecycle.py``'s own ``TERMINAL_STATUSES`` -- it can be
#: reopened -- but it is still a resolution, and ``open_differences`` tracks differences
#: still needing attention, not differences that can never again be reopened.
_REMOVES_FROM_OPEN_DIFFERENCES = TERMINAL_STATUSES | {"CLOSED"}


def _unique_sorted_refs(refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    for ref in refs:
        seen[(ref["kind"], ref["id"])] = ref
    return [seen[key] for key in sorted(seen)]


def apply_reflow_bookkeeping(
    before_semantic_state: dict[str, Any],
    *,
    difference_ref: dict[str, Any],
    to_status: str,
    new_evidence_refs: list[dict[str, Any]],
    lifecycle_event_ref: dict[str, Any],
    contradiction_refs: list[dict[str, Any]],
    transaction_ref: dict[str, Any],
) -> dict[str, Any]:
    """Return the next ``semantic_state`` with exactly the bookkeeping fields updated."""

    next_state = deepcopy(before_semantic_state)

    open_differences = [
        ref
        for ref in next_state["open_differences"]
        if (ref["kind"], ref["id"]) != (difference_ref["kind"], difference_ref["id"])
    ]
    if to_status not in _REMOVES_FROM_OPEN_DIFFERENCES:
        open_differences.append(dict(difference_ref))
    next_state["open_differences"] = _unique_sorted_refs(open_differences)

    next_state["evidence"] = _unique_sorted_refs(next_state["evidence"] + list(new_evidence_refs))

    next_state["unresolved_contradictions"] = _unique_sorted_refs(
        next_state["unresolved_contradictions"] + list(contradiction_refs)
    )

    next_state["reflow_state"] = {"last_transaction_ref": dict(transaction_ref)}

    lineage = next_state["lineage"]
    lineage["identity_refs"] = _unique_sorted_refs(
        lineage["identity_refs"] + [dict(lifecycle_event_ref)]
    )

    return next_state
