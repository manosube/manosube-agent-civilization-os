"""The one shared, minimal time-support surface every module in this package uses to convert
between canonical UTC timestamps (``01_SCHEMA/common/timestamp.schema.json``, always
``Z``-suffixed) and whole-minute integer durations.

No module in this package reads a clock to decide what "now" is *except* the one default
:func:`default_clock` implementation below, which :mod:`~manosube_agent_civilization.
work_time_transparency.adapters`'s own composition primitive uses only as its own *default* --
every test, and every other caller, injects its own deterministic clock instead (Structural
Review Round 1, P84-R1-F4). ``route.py``/``engine.py`` never call :func:`default_clock`
themselves; they only ever convert already-observed timestamps.
"""

from __future__ import annotations

from datetime import UTC, datetime


def parse_canonical_timestamp(value: str) -> datetime:
    """Both timestamps are canonical UTC (``01_SCHEMA/common/timestamp.schema.json``, always
    ``Z``-suffixed) -- ``fromisoformat`` needs the offset spelled ``+00:00`` to parse it."""

    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def elapsed_minutes(start: str, end: str) -> int:
    """Whole minutes between two canonical UTC timestamps, rounded to the nearest minute and
    floored at zero. The canonical serializer (``state.canonicalize``) prohibits floating-point
    values repository-wide, so every committed duration field in this package is an integer
    minute count, never a fractional one."""

    started = parse_canonical_timestamp(start)
    ended = parse_canonical_timestamp(end)
    return max(round((ended - started).total_seconds() / 60.0), 0)


def is_monotonic(earlier: str, later: str) -> bool:
    """Whether *later* is not before *earlier* (non-decreasing) -- the one check every lineage
    continuation (a Work Coordination Update or Terminal Notice) must pass against its own
    resolved predecessor's own timestamp before it may be committed (Structural Review Round 1,
    P84-R1-F2/F4). Two observations at the identical instant are accepted (``>=``, not ``>``) --
    a real wall clock's resolution is finite, and refusing a genuinely simultaneous continuation
    would make this check flaky rather than meaningful; only a strictly *earlier* observation
    (an actual time reversal) is refused."""

    return parse_canonical_timestamp(later) >= parse_canonical_timestamp(earlier)


def default_clock() -> str:
    """A real wall-clock reading, canonically formatted with microsecond precision (trailing
    zero fractional digits stripped, per ``01_SCHEMA/common/timestamp.schema.json``'s own
    pattern, which forbids a fractional part ending in ``0``). The one and only place in this
    entire package that reads the actual system clock -- used only as
    :func:`~manosube_agent_civilization.work_time_transparency.adapters.
    with_work_time_coordination`'s own default ``clock=`` argument, always overridable by an
    injected deterministic clock."""

    now = datetime.now(UTC)
    base = now.strftime("%Y-%m-%dT%H:%M:%S")
    fraction = now.strftime("%f").rstrip("0")
    return f"{base}.{fraction}Z" if fraction else f"{base}Z"


__all__ = ["default_clock", "elapsed_minutes", "is_monotonic", "parse_canonical_timestamp"]
