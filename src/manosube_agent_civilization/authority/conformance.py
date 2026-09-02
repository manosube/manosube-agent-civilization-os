"""One admission path for every canonical record an Authority decision may rest on.

A rule, an approval and a prohibition are all *supplied* by a caller, and all three were
previously admitted by hand-written key checks that each covered a little less than the
schema they claimed to enforce. The consequence was uniform: a record could keep a
well-formed identity, change its content, name an Agent as its author, declare an
unsupported schema version and carry unknown properties -- and still govern a decision.

So there is one gate, and it asks the same four questions of every record:

```text
1. can it be read at all
2. does it satisfy its canonical schema, at a supported version, with no unknown property
3. does its content-addressed identity match the content actually present
4. is it declared by the authority its schema says must declare it
```

Question 3 is the one a per-record check will always forget. An identity is a *claim about
content*; recomputing it is the only thing that makes forgery visible, because every other
check passes on a record whose fields were edited after it was addressed.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
import re
from typing import Any

from manosube_agent_civilization.difference.admissibility import is_scalar_tag, require_object
from manosube_agent_civilization.difference.validation import (
    SCHEMA_BASE as CANONICAL_SCHEMA_BASE,
    validate_record as _validate_canonical_record,
)

from .errors import AuthorityError, AuthorityValidationError
from .identity import approval_id, prohibition_id, rule_id

AUTHORITY_SCHEMA_BASE = CANONICAL_SCHEMA_BASE + "authority/"
SUPPORTED_SCHEMA_VERSION = "0.1"


@dataclass(frozen=True)
class RecordType:
    """What one supplied record kind must satisfy before it can affect a decision."""

    schema_name: str
    identity_field: str
    identity: Callable[[dict[str, Any]], str]
    #: The reference kind that must appear under ``declared_by`` / ``approved_by``. Every
    #: supplied record is declared by a Human Authority: none of these three may be authored
    #: by an Agent, an Adapter or the Kernel (``CAPABILITY_AUTHORITY_SEPARATION.md`` §2).
    provenance_field: str


#: Every record kind a caller may supply. Adding one without adding it here means it has no
#: admission path, and a record with no admission path never reaches a decision.
RECORD_TYPES: dict[str, RecordType] = {
    "authority_rule": RecordType(
        "authority_rule.schema.json", "authority_rule_id", rule_id, "declared_by"
    ),
    "approval": RecordType("approval.schema.json", "approval_id", approval_id, "approved_by"),
    "prohibition": RecordType(
        "prohibition.schema.json", "prohibition_id", prohibition_id, "declared_by"
    ),
}

HUMAN_AUTHORITY_KIND = "human_authority"

# --------------------------------------------------------------------------- #
# time: one grammar, two admitted forms, and no truncation
# --------------------------------------------------------------------------- #
#
# RFC 3339 §5.6, and only that. ``datetime.fromisoformat`` is a *superset*: it accepts an
# arbitrary date/time separator, a space separator, ISO week dates, the basic unseparated
# form, a comma as the fraction separator and a four-digit offset -- none of which is
# RFC 3339, and all of which produced decisions on inputs the admission contract says are
# malformed. Parsing is not validation, so the grammar is checked first and parsed second.
#
# Two forms are admitted, and what separates them is whether the value is *stored*:
#
# ```text
# stored     a field of a content-addressed record: approved_at, expires_at. UTC 'Z' and an
#            uppercase 'T', exactly what common/timestamp.schema.json has always required.
#            One spelling per instant, because a record whose identity is its own content
#            may not carry two spellings of the same field.
# transient  the caller-supplied evaluation_time. Never stored, never addressed, so
#            RFC 3339's own offset and case latitude costs nothing here and lets a caller
#            pass the clock reading it actually holds.
# ```
#
# Splitting them is the point. One grammar admitting both let a *stored* bound carry
# ``+09:00`` in code while the schema refused it -- a boundary described in two places and
# agreeing in neither.

_D2 = "[0-9]{2}"
_DATE = f"[0-9]{{4}}-{_D2}-{_D2}"
_TIME = f"{_D2}:{_D2}:{_D2}"
#: The *stored* fraction, and the reason it is not simply ``(\.[0-9]+)?``: a whole second
#: written ``.0``, ``.00`` and ``.000`` is one instant with four spellings, and an approval
#: is addressed by hashing the text it carries -- so four spellings meant four
#: ``approval_id`` values, and four decision identities, for one semantic authorization.
#: Requiring the fraction to *end* in a non-zero digit leaves exactly one spelling per
#: instant: whole seconds carry no fraction at all, and no fraction carries a trailing zero.
_CANONICAL_FRACTION = r"(\.[0-9]*[1-9])?"
#: The *transient* fraction: anything RFC 3339 allows. A caller's clock reading is compared
#: and never addressed, so ``.5``, ``.50`` and ``.500`` are the same question asked three
#: ways, and normalising them at comparison is right where rejecting them would be pedantry.
_ANY_FRACTION = r"(\.[0-9]+)?"
_NUMERIC_OFFSET = f"[+-]{_D2}:{_D2}"

#: The stored form. ``01_SCHEMA/common/timestamp.schema.json`` carries this string verbatim
#: and a contract test holds the two to each other, so the grammar has one owner rather than
#: a copy in code and a looser copy in the schema. Written as an ECMA-262 expression -- no
#: named groups, and ASCII digit classes because Python's ``\d`` also matches Devanagari and
#: Arabic-Indic digits, which ``int`` then parses happily and the schema never accepted.
STORED_TIMESTAMP_PATTERN = f"^{_DATE}T{_TIME}{_CANONICAL_FRACTION}Z$"
#: The transient form: the stored form widened by RFC 3339's own case, offset and fraction
#: latitude, none of which can reach a content-addressed field.
TRANSIENT_TIMESTAMP_PATTERN = f"^{_DATE}[Tt]{_TIME}{_ANY_FRACTION}([Zz]|{_NUMERIC_OFFSET})$"

_STORED = re.compile(STORED_TIMESTAMP_PATTERN)
_TRANSIENT = re.compile(TRANSIENT_TIMESTAMP_PATTERN)
_STORED_FORM = "an RFC 3339 UTC timestamp in canonical form"
_TRANSIENT_FORM = "an RFC 3339 timestamp"

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


@dataclass(frozen=True, order=True)
class Instant:
    """One point in time, exactly as written: no rounding, and nothing converted to a number.

    ``datetime`` holds microseconds, so it *silently* truncated anything longer: an approval
    opening at ``2026-06-01T00:00:00.0000002Z`` compared equal to an evaluation at
    ``...0000001Z``, and a not-yet-effective approval bound the request and returned
    ``AUTONOMOUS``.

    The fraction is therefore kept as **digits**, not as a number. An earlier form of this
    fix used an exact rational, which reintroduced the same shape of defect one level down:
    ``int(digits)`` raises above CPython's 4,300-digit integer-conversion limit, and it did
    so *outside* this module's refusal path, so a long enough fraction left the evaluator as
    a raw ``ValueError``. Digits have no such ceiling.

    Ordering is the field order below: whole seconds first, then the digit strings compared
    left to right. With trailing zeros removed that comparison *is* numeric comparison of the
    decimal expansions -- where one string is a prefix of the other, the longer one has a
    non-zero digit beyond it and is therefore greater -- and it costs one pass over the
    characters at any length.
    """

    seconds_since_epoch: int
    #: Fractional digits with trailing zeros removed; ``""`` for a whole second.
    fraction_digits: str


def _instant(value: str, context: str, *, grammar: re.Pattern[str], form: str) -> Instant:
    """Admit one timestamp against *grammar* and return the exact instant it names."""

    if not is_scalar_tag(value) or not grammar.fullmatch(value):
        raise AuthorityError(f"{context} is not {form}: {value!r}")

    # Both grammars are fixed-width through the seconds, so the parts are read off the value
    # directly. A second regular expression here would be a second description of the same
    # grammar, and two descriptions are what this function exists to stop.
    tail = value[19:]
    if tail[-1] in ("Z", "z"):
        offset_text, fraction_text = tail[-1], tail[:-1]
    else:
        offset_text, fraction_text = tail[-6:], tail[:-6]

    try:
        if len(offset_text) == 1:
            zone = UTC
        else:
            sign = -1 if offset_text[0] == "-" else 1
            zone = timezone(
                sign * timedelta(hours=int(offset_text[1:3]), minutes=int(offset_text[4:6]))
            )
        base = datetime(
            int(value[0:4]),
            int(value[5:7]),
            int(value[8:10]),
            int(value[11:13]),
            int(value[14:16]),
            int(value[17:19]),
            tzinfo=zone,
        )
    except ValueError as error:
        # The grammar matched but the value names no instant -- hour 24, month 13, an offset
        # beyond a day. Refused for the same reason: there is no point in time to compare.
        raise AuthorityError(f"{context} is not {form}: {value!r}") from error

    # ``base`` and ``_EPOCH`` are both built without a microsecond argument, so the whole
    # seconds below are exact and the fraction is carried entirely by the digits.
    elapsed = base - _EPOCH
    return Instant(elapsed.days * 86400 + elapsed.seconds, fraction_text[1:].rstrip("0"))


def stored_instant(value: str, context: str) -> Instant:
    """Admit a timestamp held *inside a canonical record*. One owner, every caller.

    Strings do not order chronologically: ``2026-06-01T00:00:00Z`` sorts *after*
    ``2026-06-01T00:00:00.5Z`` because ``Z`` exceeds ``.``, so a still-valid approval
    evaluated half a second before its expiry was reported outside its window. Only parsing
    sees that, and only an exact fraction sees it at every precision.

    A non-canonical spelling is **refused, never rewritten**. Normalising it here would mean
    silently deciding that a record whose identity was computed over one text really means
    another, and a content address that its own owner is willing to reinterpret is not an
    address. The refusal happens before the identity is recomputed or used.
    """

    return _instant(value, context, grammar=_STORED, form=_STORED_FORM)


def transient_instant(value: str, context: str) -> Instant:
    """Admit a caller-supplied clock reading, which is compared and never stored."""

    return _instant(value, context, grammar=_TRANSIENT, form=_TRANSIENT_FORM)


def validate(record: dict[str, Any], schema_name: str, context: str) -> None:
    """Validate against the canonical schema, in Authority's error vocabulary.

    Schema validation has one owner in this repository. Authority reads that registry rather
    than building a second one; only the vocabulary at this boundary is its own.
    """

    try:
        _validate_canonical_record(record, schema_name, base=AUTHORITY_SCHEMA_BASE)
    except ValueError as error:
        raise AuthorityValidationError(f"{context}: {error}") from error


def admit(value: Any, type_name: str, context: str) -> dict[str, Any]:
    """Return *value* once it is a canonical record of *type_name*; reject it otherwise."""

    canonical = RECORD_TYPES[type_name]
    record = require_object(value, context)

    # Version first. An unsupported version means the schema below is not the contract this
    # record was written against, so validating it would answer a question nobody asked.
    version = record.get("schema_version")
    if version != SUPPORTED_SCHEMA_VERSION:
        raise AuthorityError(f"{context} declares an unsupported schema_version: {version!r}")

    # The schema closes the key set, the enums and the reference shapes, so unknown
    # properties and malformed provenance references are refused here rather than by a
    # second hand-written copy of the same rules.
    validate(record, canonical.schema_name, context)

    # The identity is a claim about content. Recompute it: every check above passes on a
    # record whose fields were edited after it was addressed, and this one does not.
    declared = record[canonical.identity_field]
    recomputed = canonical.identity(record)
    if declared != recomputed:
        raise AuthorityError(
            f"{context} identity does not match its content: {declared!r} != {recomputed!r}"
        )

    # Provenance. The schema fixes the reference *shape*; this fixes who may occupy it.
    provenance = record[canonical.provenance_field]
    if provenance.get("kind") != HUMAN_AUTHORITY_KIND:
        raise AuthorityError(
            f"{context} is not declared by a Human Authority: {provenance.get('kind')!r}"
        )
    return record


def admit_all(values: Any, type_name: str, context: str) -> list[dict[str, Any]]:
    """Admit every member of a supplied collection, or refuse the request."""

    from manosube_agent_civilization.difference.admissibility import require_collection

    members = require_collection(values, context)
    return [
        admit(member, type_name, f"{context}[{position}]")
        for position, member in enumerate(members)
    ]
