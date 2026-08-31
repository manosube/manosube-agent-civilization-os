"""The single canonical Fact effective-boundary matching authority.

`NORMALIZED_FACT.md` gives a Normalized Fact three contract-legal effective boundary
forms. Deciding whether one of them was actually observed by a given Observation is a
single rule, owned here by the Observation element and reused by every downstream
consumer, so no second copy can drift.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

FACT_BOUNDARY_KINDS: frozenset[str] = frozenset(
    {"SOURCE_SNAPSHOT", "TIME_INTERVAL", "STATE_REVISION"}
)


def fact_boundary_observed(boundary: dict[str, Any], observation: dict[str, Any]) -> bool:
    """Return whether *boundary* was observed by *observation*.

    Each legal kind is matched against the exact binding the Observation carries, so a
    mismatched snapshot identity, effective window or State revision is never accepted,
    and an unknown kind is always rejected.
    """

    kind = boundary.get("kind")
    if kind == "SOURCE_SNAPSHOT":
        declared = {reference["id"] for reference in observation["source_snapshot_refs"]}
        return bool(
            boundary["identity"] in declared
            and boundary["start"] is None
            and boundary["end"] is None
        )
    if kind == "TIME_INTERVAL":
        window = observation["time_boundary"]
        return bool(
            boundary["start"] == window["target_effective_start"]
            and boundary["end"] == window["target_effective_end"]
        )
    if kind == "STATE_REVISION":
        revision = observation["state_revision_observed"]
        return bool(boundary["start"] == revision and boundary["end"] == revision)
    return False


def instant(value: str) -> datetime:
    """Parse a canonical UTC instant.

    A value that is not a string, not ISO-8601, or carries no timezone offset raises, so
    every caller of this module fails closed rather than comparing a naive instant against
    an aware one.
    """

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        raise ValueError(f"instant carries no timezone offset: {value!r}")
    return parsed


def time_boundary_within_scope(observation: dict[str, Any], scope: dict[str, Any]) -> bool:
    """Return whether *observation*'s time boundary falls inside the resolved Scope.

    This is the single executable projection of the canonical Observation Scope time
    contract, and it carries every obligation that contract states:

    ```text
    parseable, timezone-aware instants        else fail closed
    observation window ordering               observed_start <= observed_end
    Target effective window ordering          effective_start <= effective_end
    observation window containment            inside scope.observation_window
    Target effective window containment       inside scope.target_effective_window
    snapshot inside the observed interval      effective_start <= snapshot <= observed_end
    snapshot not after cutoff                 snapshot <= cutoff
    snapshot within the freshness limit       cutoff - snapshot <= freshness_limit_seconds
    ```

    The freshness limit is not implied by the cutoff: a snapshot may precede the cutoff and
    still be older than the Scope permits. Dropping it would let a stale source reach a
    COMPLETE Observation, bounded absence and a Difference.

    The Observation Engine that reports completeness, the Difference Engine that verifies
    an Observation's binding, and the independent validator all decide this one way.
    """

    try:
        boundary = observation["time_boundary"]
        observed_start = instant(boundary["observation_started_at"])
        observed_end = instant(boundary["observation_ended_at"])
        effective_start = instant(boundary["target_effective_start"])
        effective_end = instant(boundary["target_effective_end"])
        snapshot = instant(boundary["source_snapshot_time"])
        scope_observed_start = instant(scope["observation_window"]["start"])
        scope_observed_end = instant(scope["observation_window"]["end"])
        scope_effective_start = instant(scope["target_effective_window"]["start"])
        scope_effective_end = instant(scope["target_effective_window"]["end"])
        cutoff = instant(scope["cutoff"])
        freshness_limit = scope["freshness_limit_seconds"]
        if isinstance(freshness_limit, bool) or not isinstance(freshness_limit, (int, float)):
            return False
    except (AttributeError, KeyError, TypeError, ValueError):
        return False
    return (
        observed_start <= observed_end
        and effective_start <= effective_end
        and scope_observed_start <= observed_start <= observed_end <= scope_observed_end
        and scope_effective_start <= effective_start <= effective_end <= scope_effective_end
        and effective_start <= snapshot <= observed_end
        and snapshot <= cutoff
        and (cutoff - snapshot).total_seconds() <= freshness_limit
    )
