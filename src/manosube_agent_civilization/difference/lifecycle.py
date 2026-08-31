"""The single canonical Difference lifecycle transition authority.

``LEGAL_TRANSITIONS`` is the executable projection of the transition table in
``00_KERNEL/04_DIFFERENCE/DIFFERENCE_LIFECYCLE.md`` section 3. It is defined once here
and imported by every consumer, including the independent cross-record contract
validator, so no second transition table can drift from the contract.
"""

from __future__ import annotations

LEGAL_TRANSITIONS: frozenset[tuple[str | None, str]] = frozenset(
    {
        (None, "DETECTED"),
        ("DETECTED", "OPEN"),
        ("DETECTED", "INVALIDATED"),
        ("OPEN", "ACTIVE"),
        ("OPEN", "BLOCKED"),
        ("OPEN", "RETAINED"),
        ("OPEN", "SUPERSEDED"),
        ("OPEN", "INVALIDATED"),
        ("ACTIVE", "VERIFYING"),
        ("ACTIVE", "BLOCKED"),
        ("ACTIVE", "RETAINED"),
        ("ACTIVE", "SUPERSEDED"),
        ("ACTIVE", "INVALIDATED"),
        ("VERIFYING", "CLOSED"),
        ("VERIFYING", "ACTIVE"),
        ("VERIFYING", "BLOCKED"),
        ("VERIFYING", "RETAINED"),
        ("VERIFYING", "SUPERSEDED"),
        ("VERIFYING", "INVALIDATED"),
        ("BLOCKED", "OPEN"),
        ("BLOCKED", "ACTIVE"),
        ("BLOCKED", "VERIFYING"),
        ("BLOCKED", "RETAINED"),
        ("BLOCKED", "SUPERSEDED"),
        ("BLOCKED", "INVALIDATED"),
        ("RETAINED", "OPEN"),
        ("RETAINED", "ACTIVE"),
        ("RETAINED", "VERIFYING"),
        ("RETAINED", "BLOCKED"),
        ("RETAINED", "SUPERSEDED"),
        ("RETAINED", "INVALIDATED"),
        ("CLOSED", "REOPENED"),
        ("CLOSED", "SUPERSEDED"),
        ("CLOSED", "INVALIDATED"),
        ("REOPENED", "ACTIVE"),
        ("REOPENED", "VERIFYING"),
        ("REOPENED", "BLOCKED"),
        ("REOPENED", "RETAINED"),
        ("REOPENED", "SUPERSEDED"),
        ("REOPENED", "INVALIDATED"),
    }
)

#: ``SUPERSEDED`` and ``INVALIDATED`` are terminal. ``CLOSED`` is not the end of history:
#: it can be reopened by contradiction, so it is not listed here.
TERMINAL_STATUSES: frozenset[str] = frozenset({"SUPERSEDED", "INVALIDATED"})

#: A status-preserving ``OBSERVATION_BOUND`` provenance append is never allowed on these.
OBSERVATION_BOUND_FORBIDDEN: frozenset[str] = frozenset(
    {"CLOSED", "SUPERSEDED", "INVALIDATED"}
)

#: Statuses whose lifecycle event must carry a Next Observation Request.
REQUIRES_NEXT_OBSERVATION: frozenset[str] = frozenset({"BLOCKED", "RETAINED", "REOPENED"})

#: The Next Observation Request reason code each such status requires.
NEXT_OBSERVATION_REASON: dict[str, str] = {
    "BLOCKED": "BLOCKER_REOBSERVATION",
    "RETAINED": "RETAINED_REOBSERVATION",
    "REOPENED": "REOPEN_REOBSERVATION",
}


def is_legal_transition(from_status: str | None, to_status: str) -> bool:
    """Return whether the lifecycle contract permits this status transition."""

    return (from_status, to_status) in LEGAL_TRANSITIONS


def legal_supersession_sources() -> frozenset[str]:
    """Return every status whose legal transitions include ``SUPERSEDED``."""

    return frozenset(
        source
        for source, target in LEGAL_TRANSITIONS
        if target == "SUPERSEDED" and source is not None
    )
