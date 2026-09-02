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
from datetime import datetime
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

#: RFC 3339 §5.6, and only that. ``datetime.fromisoformat`` is a *superset*: it accepts an
#: arbitrary date/time separator, a space separator, ISO week dates, the basic unseparated
#: form, a comma as the fraction separator and a four-digit offset -- none of which is
#: RFC 3339, and all of which produced decisions on inputs the admission contract says are
#: malformed. Parsing is not validation, so the grammar is checked first and parsed second.
_RFC3339 = re.compile(
    r"^\d{4}-\d{2}-\d{2}"          # full-date
    r"[Tt]"                         # the only permitted separator
    r"\d{2}:\d{2}:\d{2}"           # partial-time
    r"(\.\d+)?"                     # optional fraction, '.' only, at least one digit
    r"([Zz]|[+-]\d{2}:\d{2})$"      # offset, colon required
)


def instant(value: str, context: str) -> datetime:
    """Parse an RFC 3339 timestamp into a comparable instant. One owner, every caller.

    Strings do not order chronologically. ``2026-06-01T00:00:00Z`` sorts *after*
    ``2026-06-01T00:00:00.5Z`` because ``Z`` exceeds ``.``, so a still-valid approval
    evaluated half a second before its expiry was reported outside its window. Fractional
    seconds and equivalent offsets are the same instant written differently, and only
    parsing sees that.
    """

    if not is_scalar_tag(value) or not _RFC3339.match(value):
        raise AuthorityError(f"{context} is not an RFC 3339 timestamp: {value!r}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00").replace("z", "+00:00"))
    except ValueError as error:
        # The grammar matched but the value is not a real instant -- hour 24, month 13, an
        # offset beyond a day. Refused for the same reason: it names no point in time.
        raise AuthorityError(f"{context} is not an RFC 3339 timestamp: {value!r}") from error
    if parsed.tzinfo is None:  # pragma: no cover - the grammar already requires an offset
        raise AuthorityError(f"{context} carries no timezone: {value!r}")
    return parsed


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
