"""The single answer to one question: can this canonical record be read?

Readability is not correctness. It is the narrower question every consumer must be able to
settle *before* it indexes a record, iterates a section, or uses an identity as a map key --
because a consumer that reads first raises an incidental ``KeyError`` or ``TypeError`` in
place of the canonical answer its boundary owes.

That question had four answers. ``validate_typed_record`` held the complete one; the
predecessor boundary, the record union, the emitted-section gate and the independent
validator's entry gate each restated part of it, and the emitted-bundle gate restated a
*narrower* part -- it skipped every check for a type with no canonical schema, so a carried
Change or Reflow record whose declared identity was absent or unhashable passed it and the
auditor then indexed it. The rule already existed and was already correct one module away.

So it lives here once, and every gate delegates:

```text
CANONICAL_OWNER   this module
DELEGATING_GATE   conformance.validate_typed_record / validate_typed_section / merge_records
                  conformance.emitted_bundle_readability_errors
                  predecessor.validate_carried_records
                  scripts.difference_contract_validator.validate_bundle
DUPLICATED_RULE   none -- asserted in both directions by
                  tests/contract/difference/test_readability_authority.py
```

Two things are deliberately **not** here, because folding them in would recreate the defect
this module exists to remove. Neither is a read failure:

* **semantic admissibility** -- the full schema pass, ``oneOf``/``enum``/``pattern``, the
  per-type semantic hooks. A record that is readable and *wrong* keeps its own diagnosis
  (ADR-0013); pre-empting that reported a supersession cycle as a schema failure once
  already.
* **identity recomputation** -- whether a content-addressed identity *recomputes* is a
  question about the payload's meaning. Whether it can be used as a mapping key is not.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from manosube_agent_civilization.observation.verification import is_unreadable_error

#: A record that is not a JSON object at all. Nothing below it can be read.
NOT_AN_OBJECT = "NOT_AN_OBJECT"

#: The declared identity key is absent, or its value cannot serve as a mapping key. Every
#: consumer indexes records by this key; ``{}`` and ``[]`` raise ``unhashable type`` and an
#: absent key raises ``KeyError``, both from inside whichever comprehension reaches it first.
IDENTITY_NOT_USABLE = "IDENTITY_NOT_USABLE"


@dataclass(frozen=True)
class RecordReadability:
    """Why a record cannot be read, or ``None`` if it can.

    One reason at a time, in the order a consumer meets them: a non-object is not asked for
    its identity. Callers keep their own message wording -- what is shared is the decision,
    not the sentence.
    """

    reason: str | None
    key: str

    @property
    def readable(self) -> bool:
        return self.reason is None


def of_record_by_key(record: Any, key: str) -> RecordReadability:
    """Decide readability from the declared identity key alone.

    The key-addressed entry, for the union and the auditor, which hold a key rather than a
    type name. ``of_record`` is this function plus the record-type table.
    """

    if not isinstance(record, dict):
        return RecordReadability(NOT_AN_OBJECT, key)
    identity = record.get(key)
    if not isinstance(identity, str) or not identity:
        return RecordReadability(IDENTITY_NOT_USABLE, key)
    return RecordReadability(None, key)


def of_record(record: Any, type_name: str) -> RecordReadability:
    """Decide readability for one canonical record type.

    Applies to **every** declared type, schema-backed or not: the identity key comes from
    ``RecordType.key``, which v0.1 declares for Change and Reflow exactly as it does for the
    types that have a schema. A type without a schema is unvalidated, not unreadable.
    """

    from .conformance import RECORD_TYPES

    return of_record_by_key(record, RECORD_TYPES[type_name].key)


def mechanical_schema_errors(record: dict[str, Any], type_name: str) -> list[str]:
    """Return only the schema violations that make a record impossible to read.

    Empty for a type with no canonical schema in v0.1 -- there is nothing to validate
    against, which `of_record` covers instead. Which schema keywords are mechanical is
    itself one declaration, shared with the Observation side rather than restated here.
    """

    from .conformance import RECORD_TYPES
    from .validation import validators

    canonical = RECORD_TYPES[type_name]
    if canonical.schema is None:
        return []
    validator = validators()[canonical.base + canonical.schema]
    return [
        error.message
        for error in validator.iter_errors(record)
        if is_unreadable_error(error)
    ]


def is_record_list(records: Any) -> bool:
    """Whether a section can be iterated as records at all.

    Trivial, and owned here anyway: every gate that iterates a section asked this question
    itself, which is how four of them ended up asking three different versions of it.
    Callers keep their own wording; the decision is one line, in one place.
    """

    return isinstance(records, list)


def is_canonical_object(value: Any) -> bool:
    """Whether an envelope member can be read as an object."""

    return isinstance(value, dict)


def emitted_bundle_errors(bundle: Any) -> list[str]:
    """Every reason a returned bundle cannot be read, across envelope and every section.

    The composition the independent validator's entry gate and the Engine's output gate both
    hold. It answers readability only: a bundle that is complete but wrong is silent here
    and keeps its own cross-record diagnosis.
    """

    from .conformance import EMITTED_SECTIONS, REQUIRED_EMITTED_KEYS

    if not is_canonical_object(bundle):
        return ["emitted bundle is not a canonical object"]
    missing = REQUIRED_EMITTED_KEYS - set(bundle)
    if missing:
        return [f"emitted bundle omits required sections: {sorted(missing)}"]
    errors: list[str] = []
    if not is_canonical_object(bundle["materialized_status"]):
        errors.append("emitted bundle materialized status is not a canonical object")
    for section, type_name in EMITTED_SECTIONS.items():
        if section not in bundle:
            continue
        errors.extend(section_errors(section, bundle[section], type_name))
    return errors


def section_errors(section: str, records: Any, type_name: str) -> list[str]:
    """Every reason the records in one section cannot be read, in consumer order."""

    if not is_record_list(records):
        return [f"section is not a list of records: {section}"]
    errors: list[str] = []
    for record in records:
        verdict = of_record(record, type_name)
        if verdict.reason == NOT_AN_OBJECT:
            errors.append(f"record is not an object: {section}")
            continue
        errors.extend(f"{section}: {message}" for message in mechanical_schema_errors(record, type_name))
        if verdict.reason is not None:
            errors.append(f"record has no usable identity in {section}: {verdict.key}")
    return errors
