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

from manosube_agent_civilization.difference.admissibility import (
    is_scalar_tag,
    require_object,
    require_scalar_tag,
)
from manosube_agent_civilization.difference.identity import difference_id as _difference_id
from manosube_agent_civilization.difference.validation import (
    DIFFERENCE_SCHEMA_BASE,
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

#: Built once from the canonical schema, on first use.
_ACTION_KIND: Any = None

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

#: A true end of input, in ECMA-262 and in Python alike. ``$`` is a true end in only one of
#: them: Python's ``re`` matches it *before a trailing newline*, and ``jsonschema`` evaluates
#: ``pattern`` with ``re.search``. So every canonical pattern written with a terminal ``$``
#: silently admitted a second spelling of every value it matched -- and where that value is a
#: *matching key* rather than an address, the second spelling was a different key. That is
#: how a line feed on ``action_kind`` walked past the human-only floor, and how one on
#: ``project_id`` walked past a PROJECT-class prohibition.
TRUE_END = r"(?![\s\S])"

#: The schemas an Authority decision actually evaluates: the four this package owns, plus the
#: Difference schema ``admit_difference`` validates against. The closure of their ``$ref``
#: graph is what a guard over "Authority's patterns" has to mean -- a directory glob names
#: the four and misses ``common/identity``, which is where the ``project_id`` alias lived.
AUTHORITY_SCHEMA_SEEDS: tuple[str, ...] = (
    AUTHORITY_SCHEMA_BASE + "authority.schema.json",
    AUTHORITY_SCHEMA_BASE + "authority_rule.schema.json",
    AUTHORITY_SCHEMA_BASE + "prohibition.schema.json",
    AUTHORITY_SCHEMA_BASE + "approval.schema.json",
    CANONICAL_SCHEMA_BASE + "difference/difference.schema.json",
)


def _references(node: Any) -> list[str]:
    """Every ``$ref`` string in a schema document, in document order."""

    found: list[str] = []
    if isinstance(node, dict):
        target = node.get("$ref")
        if isinstance(target, str):
            found.append(target)
        for child in node.values():
            found.extend(_references(child))
    elif isinstance(node, list):
        for child in node:
            found.extend(_references(child))
    return found


def authority_reachable_schemas() -> dict[str, dict[str, Any]]:
    """Return every schema an Authority decision can evaluate, keyed by canonical ``$id``.

    The transitive ``$ref`` closure of :data:`AUTHORITY_SCHEMA_SEEDS`, resolved against the
    one schema registry this repository has. Cycle-safe by construction: a schema is expanded
    once, when it is first reached.

    ``scripts/validate_schemas.py`` walks ``$ref`` too, for a different question -- whether
    *any* reference in *any* schema resolves. Unifying the two walkers is not in this
    correction's scope; what matters here is that the boundary is derived rather than
    declared, so a schema entering the closure cannot escape the guard by living elsewhere.
    """

    from urllib.parse import urljoin

    from manosube_agent_civilization.difference.validation import validators

    documents = {schema_id: entry.schema for schema_id, entry in validators().items()}
    reached: dict[str, dict[str, Any]] = {}
    pending = list(AUTHORITY_SCHEMA_SEEDS)
    while pending:
        schema_id = pending.pop()
        if schema_id in reached:
            continue
        document = documents.get(schema_id)
        if document is None:
            raise AuthorityError(f"Authority reaches an unregistered schema: {schema_id}")
        reached[schema_id] = document
        for reference in _references(document):
            path = reference.split("#")[0]
            target = schema_id if not path else urljoin(schema_id, path)
            if target not in reached:
                pending.append(target)
    return reached


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
#: RFC 3339 §5.6 fixes ``time-hour = 00-23`` and ``time-minute = 00-59`` for a numeric
#: offset, and the range is part of the grammar rather than something the parser catches
#: afterwards. It has to be, here: for every other over-range component -- month 13, hour 24,
#: second 60 -- the "parse second" step lets ``datetime(...)`` refuse the value, but
#: ``timezone(timedelta(hours=…, minutes=…))`` **normalises** an over-range minute into an
#: hour carry instead of rejecting it. So ``+00:60`` became ``+01:00`` silently, and 1840
#: offset spellings RFC 3339 forbids named instants and reached decisions -- including one
#: that returned ``AUTONOMOUS`` on a validity window.
#:
#: The grammar is the only gate that can see this, which is why the range lives in it.
_OFFSET_HOUR = "(?:[01][0-9]|2[0-3])"
_OFFSET_MINUTE = "[0-5][0-9]"
_NUMERIC_OFFSET = f"[+-]{_OFFSET_HOUR}:{_OFFSET_MINUTE}"

#: The stored form. ``01_SCHEMA/common/timestamp.schema.json`` carries this string verbatim
#: and a contract test holds the two to each other, so the grammar has one owner rather than
#: a copy in code and a looser copy in the schema. Written as an ECMA-262 expression -- no
#: named groups, and ASCII digit classes because Python's ``\d`` also matches Devanagari and
#: Arabic-Indic digits, which ``int`` then parses happily and the schema never accepted.
STORED_TIMESTAMP_PATTERN = f"^{_DATE}T{_TIME}{_CANONICAL_FRACTION}Z{TRUE_END}"
#: The transient form: the stored form widened by RFC 3339's own case, offset and fraction
#: latitude, none of which can reach a content-addressed field.
TRANSIENT_TIMESTAMP_PATTERN = (
    f"^{_DATE}[Tt]{_TIME}{_ANY_FRACTION}([Zz]|{_NUMERIC_OFFSET}){TRUE_END}"
)

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


def validate(
    record: dict[str, Any],
    schema_name: str,
    context: str,
    base: str = AUTHORITY_SCHEMA_BASE,
) -> None:
    """Validate against the canonical schema, in Authority's error vocabulary.

    Schema validation has one owner in this repository. Authority reads that registry rather
    than building a second one; only the vocabulary at this boundary is its own.
    """

    try:
        _validate_canonical_record(record, schema_name, base=base)
    except ValueError as error:
        raise AuthorityValidationError(f"{context}: {error}") from error


def _action_kind_validator() -> Any:
    """The canonical vocabulary for an action kind, read from the schema that owns it.

    Not a hand-copied regular expression. The pattern lives in
    ``authority/authority.schema.json#/$defs/action_kind``; a copy here would be a second
    statement of the vocabulary, and the first time the two disagreed the disagreement would
    be silent -- which is the shape this package has already had to correct for the timestamp
    grammar and for the evaluation route.
    """

    global _ACTION_KIND
    if _ACTION_KIND is None:
        from manosube_agent_civilization.difference.validation import validators

        # The registry's own validator, and its own validator *class*: this module does not
        # import the validation library, so there is one place that decides which draft the
        # repository validates against.
        registered = validators()[AUTHORITY_SCHEMA_BASE + "authority.schema.json"]
        _ACTION_KIND = type(registered)(registered.schema["$defs"]["action_kind"])
    return _ACTION_KIND


def require_action_kind(value: Any, context: str) -> str:
    """Return *value* once it is a well-formed action kind; reject it otherwise.

    ``action_kind`` was the last caller-supplied value with no vocabulary check at the input
    boundary. It was constrained only by the *output* schema, so a malformed kind produced
    ``generated authority.schema.json is schema-invalid`` -- the evaluator reporting its own
    emitted record as the problem when the caller's request was. That is the same escape
    round 6 closed for duplicate records and scope members, at the one site not reached.

    Being *well-formed* is not being *known*: an unrecognised but well-formed kind is
    governed by no rule and is therefore fail-closed to ``HUMAN_APPROVAL_REQUIRED``
    (``ACTION_KIND_VOCABULARY_CLOSED=false``). This gate separates the two, so a caller can
    tell a typo from a decision.
    """

    kind = require_scalar_tag(value, context)
    if not _action_kind_validator().is_valid(kind):
        raise AuthorityError(
            f"{context} is not a canonical action kind: {kind!r}. "
            "An action kind is upper-case ASCII, 2 to 64 characters, digits and underscores "
            "permitted after the first."
        )
    return str(kind)


def admit_difference(value: Any, context: str) -> dict[str, Any]:
    """Return the bound Difference once it is canonical, including its own address.

    The Difference was the one supplied record that reached a decision without its identity
    being recomputed. Everything else about it was checked -- shape, schema, project -- and
    those are exactly the checks that pass on a record whose fields were edited after it was
    addressed.

    Identity is **not** recomputed here. It is asked of the Difference package's own owner,
    because a second implementation of a content address is a second answer to what the
    address is, and the first time the two disagree the disagreement is silent.

    **What this proves, exactly.** ``difference_id`` is a *semantic* identity over a
    deliberately closed projection -- ``difference_identity_input`` -- and not a content hash
    of the whole record. Recomputing it therefore detects edits to the fields **in** that
    projection, and to the declared identifier itself. It does not detect an edit to a field
    outside it, and ``observed_state_revision`` and ``observed_state_fingerprint`` are
    outside it.

    An earlier version of this docstring said a caller could not "change what it says", and
    the PR evidence claimed every payload edit was refused. Both were too broad: a genuine
    Difference re-pointed at the current revision keeps its address and is admitted here.
    The staleness comparison in :func:`~.engine.evaluate_authority` is an **exact consistency
    check among admitted request inputs** -- it establishes that the Difference and the
    declared current State agree, not that either was supplied honestly.

    ```text
    RECOMPUTED difference_id  → the identity projection was not edited
    STALE STATE CHECK         → the request's own inputs agree with each other
    NEITHER                   → proof that the observed-State pair is authentic
    ```

    Authenticating the current State and the complete Difference record against a trusted
    backend is a **Binding** obligation. Phase 4 has no Binding owner, so this is a stated
    non-claim (``AUTHORITY_CONTRACT.md`` §4.1) rather than a gap left implicit -- refusing to
    overstate it is what keeps it bounded.
    """

    difference = require_object(value, context)
    validate(difference, "difference.schema.json", context, base=DIFFERENCE_SCHEMA_BASE)
    declared = difference["difference_id"]
    recomputed = _difference_id(difference)
    if declared != recomputed:
        raise AuthorityError(
            f"{context} identity does not match the Difference it names: "
            f"{declared!r} != {recomputed!r}"
        )
    return difference


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


def admit_all(
    values: Any,
    type_name: str,
    context: str,
    *,
    refine: Callable[[dict[str, Any], str], None] | None = None,
) -> list[dict[str, Any]]:
    """Admit every member of a supplied collection, or refuse the request.

    *refine* is whatever else that record kind must satisfy -- a rule's decision vocabulary,
    an enumerated scope. It runs here rather than in a caller's own loop so that every
    supplied collection crosses the same gate, distinctness included.

    **A repeated record is refused, not folded away.** These collections are sets written as
    lists: a record appearing twice is one record supplied twice, and the decision's
    reference arrays are ``uniqueItems``. Silently de-duplicating would make the evaluator
    quietly correct its input, which is the same move as rewriting a non-canonical timestamp;
    ignoring it produced a decision record that failed its *own* schema on the way out, so a
    malformed input surfaced as an internal generation failure. Refusing says which entry
    repeated which, at the boundary, before anything is decided.
    """

    from manosube_agent_civilization.difference.admissibility import require_collection

    identity_field = RECORD_TYPES[type_name].identity_field
    members = require_collection(values, context)
    seen: dict[str, str] = {}
    records: list[dict[str, Any]] = []
    for position, member in enumerate(members):
        where = f"{context}[{position}]"
        record = admit(member, type_name, where)
        if refine is not None:
            refine(record, where)
        identity = str(record[identity_field])
        if identity in seen:
            raise AuthorityError(
                f"{where} repeats {seen[identity]}: {identity}. "
                "A canonical record supplied twice is one record, not two."
            )
        seen[identity] = where
        records.append(record)
    return records
