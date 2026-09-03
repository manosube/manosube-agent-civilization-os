"""Every mutation of an Evidence request lands on a refusal or a valid record. Never a crash.

The property is stated once, over cases generated from the engine's own declared key sets
rather than from a list somebody remembered to update:

```text
for every mutation m of a valid request:
    derive_evidence(m(request))  raises EvidenceError   or   returns a schema-valid record
```

An incidental ``TypeError`` or ``KeyError`` is neither. It means a value reached a hash, a
sort, a subscript or a membership test before anything established it could bear one -- the
blind spot ``difference/admissibility.py`` was written for, checked here for this engine.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from tests.evidence_helpers import (
    change_result_evidence_request,
    observation_evidence_request,
    sufficiency_request,
)

from manosube_agent_civilization.difference.validation import (
    DIFFERENCE_SCHEMA_BASE,
    validate_record,
)
from manosube_agent_civilization.evidence import (
    EvidenceError,
    derive_evidence,
    evaluate_sufficiency,
)
from manosube_agent_civilization.evidence.engine import (
    EVIDENCE_SCHEMA_BASE,
    REQUIRED_REQUEST_KEYS as EVIDENCE_REQUEST_KEYS,
)
from manosube_agent_civilization.evidence.sufficiency import (
    REQUIRED_REQUEST_KEYS as SUFFICIENCY_REQUEST_KEYS,
)

#: Values chosen because each one reaches a *different* operation in the engine: a hash, a
#: sort key, a mapping subscript, a membership test, a truth test, a length.
SUBSTITUTIONS: tuple[Any, ...] = (
    None,
    True,
    0,
    -1,
    "",
    "unexpected",
    [],
    [None],
    {},
    {"kind": "unexpected"},
    [{"kind": "unexpected", "id": "X-0001"}],
)

#: The repository's own schema validation owner, called rather than re-instantiated. A second
#: validator built here could load a different registry from the same tree and disagree with
#: the one the engines validate against, which would make an admission look valid to this
#: sweep and invalid in production.
EVIDENCE_SCHEMA = (EVIDENCE_SCHEMA_BASE, "evidence.schema.json")
SUFFICIENCY_SCHEMA = (DIFFERENCE_SCHEMA_BASE, "evidence_sufficiency_result.schema.json")


def _schema_errors(record: dict[str, Any], schema: tuple[str, str]) -> None:
    base, name = schema
    validate_record(record, name, base=base)


def _sweep(
    call: Any, request: dict[str, Any], schema: tuple[str, str], extract: Any
) -> tuple[int, int]:
    """Return (refusals, admissions) after asserting neither is a crash.

    Both engines share this function on purpose: a sweep written twice is a sweep that can
    diverge, and the halves that diverge are the ones nobody re-reads.
    """

    refused = 0
    admitted = 0
    cases: list[dict[str, Any]] = []
    for key in sorted(request):
        for value in SUBSTITUTIONS:
            case = deepcopy(request)
            case[key] = deepcopy(value)
            cases.append(case)
        dropped = deepcopy(request)
        del dropped[key]
        cases.append(dropped)
    extra = deepcopy(request)
    extra["unexpected_key"] = "value"
    cases.append(extra)

    for case in cases:
        try:
            produced = call(case)
        except EvidenceError:
            refused += 1
            continue
        admitted += 1
        _schema_errors(extract(produced), schema)
    return refused, admitted


def test_every_evidence_request_mutation_is_refused_or_produces_a_valid_record() -> None:
    refused, admitted = _sweep(
        derive_evidence,
        observation_evidence_request(),
        EVIDENCE_SCHEMA,
        lambda record: record,
    )
    # The control: a sweep that refused everything, or admitted everything, would prove
    # nothing about the boundary between the two.
    assert refused > 0
    assert admitted > 0
    assert refused + admitted == len(EVIDENCE_REQUEST_KEYS) * (len(SUBSTITUTIONS) + 1) + 1


def test_every_change_result_request_mutation_is_refused_or_produces_a_valid_record() -> None:
    refused, admitted = _sweep(
        derive_evidence,
        change_result_evidence_request(),
        EVIDENCE_SCHEMA,
        lambda record: record,
    )
    assert refused > 0
    assert admitted > 0


def test_every_sufficiency_request_mutation_is_refused_or_produces_a_valid_result() -> None:
    refused, admitted = _sweep(
        evaluate_sufficiency,
        sufficiency_request(),
        SUFFICIENCY_SCHEMA,
        lambda produced: produced["evidence_sufficiency_result"],
    )
    assert refused > 0
    assert admitted > 0
    assert refused + admitted == len(SUFFICIENCY_REQUEST_KEYS) * (len(SUBSTITUTIONS) + 1) + 1


@pytest.mark.parametrize("key", sorted(EVIDENCE_REQUEST_KEYS))
def test_removing_any_declared_evidence_request_key_is_refused(key: str) -> None:
    """Totality over the declared set, so a key added later is covered without anyone
    remembering to add a case for it."""

    request = observation_evidence_request()
    del request[key]
    with pytest.raises(EvidenceError) as raised:
        derive_evidence(request)
    assert "omits required keys" in str(raised.value) or "unsupported" in str(raised.value)


@pytest.mark.parametrize("key", sorted(SUFFICIENCY_REQUEST_KEYS))
def test_removing_any_declared_sufficiency_request_key_is_refused(key: str) -> None:
    request = sufficiency_request()
    del request[key]
    with pytest.raises(EvidenceError):
        evaluate_sufficiency(request)


def test_an_undeclared_key_is_refused_rather_than_ignored() -> None:
    """``AUTHORITY_CONTRACT.md`` §4: an ignored key is still a channel."""

    request = observation_evidence_request()
    request["evidence_level"] = "E6"
    with pytest.raises(EvidenceError) as raised:
        derive_evidence(request)
    assert "unknown keys" in str(raised.value)

    sufficiency = sufficiency_request()
    sufficiency["result"] = "SUFFICIENT"
    with pytest.raises(EvidenceError) as raised:
        evaluate_sufficiency(sufficiency)
    assert "unknown keys" in str(raised.value)


def test_the_request_is_not_an_object_at_all() -> None:
    values: tuple[Any, ...] = (None, [], "request", 0, True)
    for value in values:
        with pytest.raises(EvidenceError):
            derive_evidence(value)
        with pytest.raises(EvidenceError):
            evaluate_sufficiency(value)
