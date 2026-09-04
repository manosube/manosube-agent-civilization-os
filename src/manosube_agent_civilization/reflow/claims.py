"""Reconstruct the append-only ``candidate_claim_evaluation_event`` series G21 must trust.

``CLOSURE_POLICY.md``'s G21 requires replaying this series from ``event_revision`` 0
through a binding's declared head rather than trusting the binding's own
``evaluation_status`` -- a caller who can write a binding can write any status onto it, so
the status is only real once it is the terminus of a chain this module has actually walked
and checked for contiguity, not a label copied from the chain's most recent claim.

Event identity uses the same repo-wide content-address convention every other Difference
and Reflow record uses (:func:`~manosube_agent_civilization.difference.canonical.
content_address`) -- the "Difference-owned public boundary" this vertical's docstrings
elsewhere refer to as the one identity convention, not a second one invented here.
"""

from __future__ import annotations

from typing import Any

from manosube_agent_civilization.difference.canonical import content_address

from .errors import ReflowValidationError


def candidate_claim_evaluation_event_id(event: dict[str, Any]) -> str:
    """Return the content address of a ``candidate_claim_evaluation_event`` record."""

    return content_address("CAND-CLAIM-EVT-", event, "event_id")


def reconstruct_claim_status(
    events: list[dict[str, Any]],
    *,
    head_event_id: str,
    difference_id: str,
    required_claim_ref: dict[str, Any],
    candidate_id: str,
) -> str:
    """Walk the series backward from *head_event_id* to revision 0; return its head status.

    Every event supplied must recompute its own declared ``event_id`` (an edited event is
    refused), the walk from the declared head must reach exactly one revision-0 event with
    a null ``predecessor_event_ref`` (a missing, reordered or non-contiguous series is
    refused), and every event on the walked chain must belong to the same Difference,
    required Claim and candidate the caller is evaluating (a foreign series is refused).
    The returned status is the *head* event's own ``evaluation_status`` -- the most recent
    admitted claim about this series, not any earlier or later one.
    """

    by_id: dict[str, dict[str, Any]] = {}
    for event in events:
        identity = candidate_claim_evaluation_event_id(event)
        if event.get("event_id") != identity:
            raise ReflowValidationError(
                "candidate_claim_evaluation_event fails its own content address: "
                f"{event.get('event_id')!r}"
            )
        if identity in by_id and by_id[identity] != event:
            raise ReflowValidationError(
                f"candidate_claim_evaluation_event series carries two bodies for {identity}"
            )
        by_id[identity] = event

    if head_event_id not in by_id:
        raise ReflowValidationError(
            f"claim evaluation series does not include its declared head: {head_event_id!r}"
        )

    seen: set[str] = set()
    current = by_id[head_event_id]
    head_status: str = current["evaluation_status"]
    while True:
        if current["event_id"] in seen:
            raise ReflowValidationError("claim evaluation series is not acyclic")
        seen.add(current["event_id"])
        if current["difference_id"] != difference_id:
            raise ReflowValidationError(
                "claim evaluation series belongs to a different Difference"
            )
        if current["required_claim_ref"] != required_claim_ref:
            raise ReflowValidationError(
                "claim evaluation series belongs to a different required Claim"
            )
        if current["candidate_id"] != candidate_id:
            raise ReflowValidationError(
                "claim evaluation series belongs to a different candidate"
            )
        predecessor_ref = current["predecessor_event_ref"]
        if current["event_revision"] == 0:
            if predecessor_ref is not None:
                raise ReflowValidationError(
                    "claim evaluation event_revision 0 must carry a null predecessor_event_ref"
                )
            break
        if predecessor_ref is None:
            raise ReflowValidationError(
                f"claim evaluation event_revision {current['event_revision']} carries a "
                "null predecessor_event_ref"
            )
        predecessor_id = predecessor_ref.get("id")
        if predecessor_id not in by_id:
            raise ReflowValidationError(
                f"claim evaluation series is missing revision {current['event_revision'] - 1}"
            )
        predecessor = by_id[predecessor_id]
        if predecessor["event_revision"] != current["event_revision"] - 1:
            raise ReflowValidationError(
                "claim evaluation series is non-contiguous: revision "
                f"{predecessor['event_revision']} precedes {current['event_revision']}"
            )
        current = predecessor

    return head_status
