"""The approval-combination truth table, and the grammar the evaluator actually accepts.

Two findings, and both are about a rule that was stated but not enumerated.

**`ANY_APPLICABLE_EXCLUSION -> NEVER_AUTONOMOUS`** was implemented for the shape the previous
tests exercised -- one excluding approval, alone. Add a *second* approval that binds and
permits, and the permitting one was selected and lowered the decision back to `AUTONOMOUS`
while `excluding_approval_refs` stayed non-empty. So the rule held on the cases someone
thought of and failed on the combination nobody enumerated, which is what a truth table is
for.

**RFC 3339** was enforced by calling ``datetime.fromisoformat``, which is a *superset* of it.
Parsing is not validation: the grammar has to be checked before the parser is asked, or the
parser's tolerances silently become the contract.

The pre-correction table is committed as data at
``tests/contract/fixtures/authority/frozen/approval_combination_baseline.json`` (ADR-0022),
so "the fix closed exactly these and introduced none" is checkable rather than asserted.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any

import pytest
from tests.authority_helpers import (
    action,
    approval,
    authority_request,
    derived_difference,
    rule,
    scope,
)

from manosube_agent_civilization.authority import (
    AUTONOMOUS,
    HUMAN_APPROVAL_REQUIRED,
    AuthorityError,
    AuthorityValidationError,
    conformance,
    evaluate_authority,
)

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[3]
BASELINE = (
    ROOT / "tests" / "contract" / "fixtures" / "authority" / "frozen"
    / "approval_combination_baseline.json"
)

#: The four roles an approval can play in one request. ``nonbinding_excluding`` is the
#: control: it withholds the action but does not cover this request, so it must not narrow.
APPROVAL_ROLES = ("permitting", "excluding", "excluding_other", "nonbinding_excluding")
APPLICABLE_EXCLUSIONS = ("excluding", "excluding_other")
RULE_SETS = ("no_rule", "autonomous", "requires")
ACTION_KINDS = ("WRITE_FILE", "MERGE")


def _pool(
    difference: dict[str, Any], kind: str, requested: dict[str, Any], where: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    return {
        "permitting": approval(
            difference, requested, where, approved_at="2026-01-01T00:00:00Z"
        ),
        "excluding": approval(
            difference, requested, where, prohibited_actions=[kind],
            approved_at="2026-02-01T00:00:00Z",
        ),
        "excluding_other": approval(
            difference, requested, where, prohibited_actions=[kind],
            approved_at="2026-03-01T00:00:00Z",
        ),
        "nonbinding_excluding": approval(
            difference, requested, where, prohibited_actions=[kind], project_id="PRJ-9999"
        ),
    }


def _rules(difference: dict[str, Any], kind: str, name: str) -> list[dict[str, Any]]:
    return {
        "no_rule": [],
        "autonomous": [
            rule(difference["project_id"], action_kinds=[kind], decision=AUTONOMOUS)
        ],
        "requires": [
            rule(difference["project_id"], action_kinds=[kind], decision=HUMAN_APPROVAL_REQUIRED)
        ],
    }[name]


def _table() -> list[dict[str, Any]]:
    """Every combination and permutation of approval roles, over every rule set."""

    difference = derived_difference()
    where = scope()
    rows: list[dict[str, Any]] = []
    for kind in ACTION_KINDS:
        requested = action(kind)
        pool = _pool(difference, kind, requested, where)
        for size in range(len(APPROVAL_ROLES) + 1):
            for combination in itertools.combinations(APPROVAL_ROLES, size):
                for order in itertools.permutations(combination):
                    for rule_name in RULE_SETS:
                        rows.append(
                            {
                                "difference": difference,
                                "action": requested,
                                "scope": where,
                                "action_kind": kind,
                                "rule": rule_name,
                                "rules": _rules(difference, kind, rule_name),
                                "order": order,
                                "approvals": [pool[name] for name in order],
                                "has_applicable_exclusion": any(
                                    name in APPLICABLE_EXCLUSIONS for name in order
                                ),
                            }
                        )
    return rows


TABLE = _table()


def _decide(row: dict[str, Any]) -> dict[str, Any]:
    return evaluate_authority(
        authority_request(
            row["difference"],
            row["action"],
            row["scope"],
            rules=row["rules"],
            approvals=row["approvals"],
        )
    )


def test_the_table_is_neither_empty_nor_shrunk() -> None:
    """The harness before its subject: a table that enumerates nothing passes everything."""

    assert len(TABLE) == 390, len(TABLE)
    assert sum(1 for row in TABLE if row["has_applicable_exclusion"]) == 360


def test_the_frozen_baseline_records_what_was_measured_before_the_fix() -> None:
    """Committed pre-correction data, so the correction's extent is checkable."""

    manifest = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert manifest["measured_at_head"] == "f91d049cd98e04d47861f4f9cf0bc0efece284f3"
    assert manifest["row_count"] == len(TABLE)
    assert manifest["violation_count"] == 276
    # Every frozen violation was an output-schema rejection, not a wrong permission: the
    # AUTONOMOUS -> excluding_approval_refs=[] constraint caught the logic error at runtime.
    assert {violation["decision"] for violation in manifest["violations"]} == {
        "ERROR:AuthorityValidationError"
    }


@pytest.mark.parametrize(
    "row",
    TABLE,
    ids=lambda row: f"{row['action_kind']}-{row['rule']}-{'+'.join(row['order']) or 'none'}",
)
def test_any_applicable_exclusion_is_never_autonomous(row: dict[str, Any]) -> None:
    """The rule, over every combination and every permutation.

    A second approval that binds and permits does not overrule the first one's refusal. An
    approval may narrow and may never widen, and "one of them said yes" is exactly the
    widening that forbids.
    """

    decision = _decide(row)
    if row["has_applicable_exclusion"]:
        assert decision["decision"] == HUMAN_APPROVAL_REQUIRED
        assert "APPROVAL_EXCLUDES_ACTION" in decision["decision_reason_codes"]
        assert decision["approval_ref"] is None
        assert decision["excluding_approval_refs"]


def test_the_permitting_path_is_intact(  ) -> None:
    """The control. Refusing more must not have refused everything.

    Without this, a fix that returned ``HUMAN_APPROVAL_REQUIRED`` unconditionally would pass
    every assertion above.
    """

    outcomes = {AUTONOMOUS: 0, HUMAN_APPROVAL_REQUIRED: 0}
    for row in TABLE:
        if row["has_applicable_exclusion"]:
            continue
        outcomes[_decide(row)["decision"]] += 1
    assert outcomes[AUTONOMOUS] > 0, outcomes
    assert outcomes[HUMAN_APPROVAL_REQUIRED] > 0, outcomes


def test_a_non_binding_exclusion_does_not_narrow() -> None:
    """An approval that withholds the action but does not cover this request is inert."""

    difference = derived_difference()
    requested, where = action("WRITE_FILE"), scope()
    elsewhere = approval(
        difference, requested, where, project_id="PRJ-9999", prohibited_actions=["WRITE_FILE"]
    )
    decision = evaluate_authority(
        authority_request(
            difference,
            requested,
            where,
            rules=[rule(difference["project_id"], action_kinds=["WRITE_FILE"])],
            approvals=[elsewhere],
        )
    )
    assert decision["decision"] == AUTONOMOUS
    assert decision["excluding_approval_refs"] == []


def test_the_whole_table_is_permutation_invariant() -> None:
    """Reversing the approval list is the same question, and must be the same record."""

    grouped: dict[tuple[Any, ...], set[str]] = {}
    for row in TABLE:
        key = (row["action_kind"], row["rule"], tuple(sorted(row["order"])))
        grouped.setdefault(key, set()).add(_decide(row)["authority_decision_id"])
    unstable = {key: ids for key, ids in grouped.items() if len(ids) > 1}
    assert not unstable, unstable


# --------------------------------------------------------------------------- #
# RFC 3339, not whatever the parser happens to tolerate
# --------------------------------------------------------------------------- #

_ACCEPTED = (
    "2026-06-01T00:00:00Z",
    "2026-06-01t00:00:00z",
    "2026-06-01T09:00:00+09:00",
    "2026-06-01T00:00:00.500Z",
    "2026-06-01T00:00:00.000001Z",
    "2026-06-01T00:00:00-05:00",
)

#: Every one of these is accepted by ``datetime.fromisoformat`` and is not RFC 3339. They
#: are the reason the grammar is checked before the parser is asked.
_REFUSED_BY_GRAMMAR = (
    "2026-06-01X00:00:00+00:00",   # arbitrary separator
    "2026-06-01 00:00:00+00:00",   # space separator
    "2026-W23-1T00:00:00+00:00",   # ISO week date
    "20260601T000000Z",            # basic unseparated form
    "2026-06-01T00:00:00+0000",    # offset without a colon
    "2026-06-01T00:00:00,5Z",      # comma fraction separator
    "2026-06-01T00:00:00",         # no offset at all
    "2026-06-01",                  # date only
    "2026-06-01T00:00:00.Z",       # fraction marker with no digits
    "not-a-time",
)

#: Refused for a different reason, and the difference is structural rather than incidental:
#: the *grammar* matches and the value still names no point in time. A regular expression
#: cannot see that June has thirty days or that an hour ends at 23, which is why the owner
#: parses after it matches -- and why these are the only values below on which the schema's
#: pattern and the admission owner part company.
_REFUSED_AS_NO_INSTANT = (
    "2026-06-01T24:00:00Z",
    "2026-13-01T00:00:00Z",
    "2026-06-01T00:00:00+99:00",
)

_REFUSED = _REFUSED_BY_GRAMMAR + _REFUSED_AS_NO_INSTANT

#: Refused one gate earlier, by the scalar-tag admission, and so with that gate's message.
#: Kept as its own case rather than folded into the set above: which gate refuses a value is
#: part of what is being asserted.
_REFUSED_BEFORE_THE_GRAMMAR = ("",)


@pytest.mark.parametrize("value", _ACCEPTED)
def test_an_rfc3339_instant_is_accepted(value: str) -> None:
    difference = derived_difference()
    decision = evaluate_authority(
        authority_request(
            difference,
            action(),
            scope(),
            rules=[rule(difference["project_id"])],
            evaluation_time=value,
        )
    )
    assert decision["decision"] == AUTONOMOUS


@pytest.mark.parametrize("value", _REFUSED)
def test_an_iso_extension_that_is_not_rfc3339_is_refused(value: str) -> None:
    """Parsing is not validation: the parser's tolerances are not the contract."""

    difference = derived_difference()
    with pytest.raises(AuthorityError, match="RFC 3339"):
        evaluate_authority(
            authority_request(
                difference,
                action(),
                scope(),
                rules=[rule(difference["project_id"])],
                evaluation_time=value,
            )
        )


@pytest.mark.parametrize("value", _REFUSED_BEFORE_THE_GRAMMAR)
def test_a_value_that_is_not_even_a_tag_is_refused_before_the_grammar(value: str) -> None:
    """Still refused, one gate earlier, and the message names that gate."""

    difference = derived_difference()
    with pytest.raises(AuthorityError, match="not a canonical tag"):
        evaluate_authority(
            authority_request(
                difference,
                action(),
                scope(),
                rules=[rule(difference["project_id"])],
                evaluation_time=value,
            )
        )


def test_one_owner_answers_for_every_timestamp() -> None:
    """The evaluation time and both approval bounds cross the same admission functions."""

    from manosube_agent_civilization.authority import (
        approval as approval_module,
        conformance,
        engine,
    )

    assert vars(approval_module)["stored_instant"] is conformance.stored_instant
    assert vars(approval_module)["transient_instant"] is conformance.transient_instant
    assert vars(engine)["transient_instant"] is conformance.transient_instant


# --------------------------------------------------------------------------- #
# stored and transient are different questions, asked of one grammar
# --------------------------------------------------------------------------- #
#
# A stored timestamp is a field of a content-addressed record, so it has one spelling: UTC
# ``Z``, exactly what ``common/timestamp.schema.json`` has always required. A transient one
# is the caller's supplied clock reading, never stored and never addressed, so RFC 3339's own
# offset and case latitude costs nothing. Admitting both through one permissive grammar meant
# the code accepted ``+09:00`` in an ``approved_at`` the schema refused -- a boundary written
# in two places and agreeing in neither.

#: Accepted as a *stored* record field. A subset of ``_ACCEPTED``: everything here is also a
#: valid evaluation time, and the reverse does not hold.
_STORED_ACCEPTED = (
    "2026-06-01T00:00:00Z",
    "2026-06-01T00:00:00.5Z",
    "2026-06-01T00:00:00.05Z",          # leading zeros are content, not padding
    "2026-06-01T00:00:00.000000000000001Z",
)

#: Valid RFC 3339, valid as an evaluation time, and refused in a stored field because the
#: spelling names a zone rather than UTC, or names it in a second casing.
_STORED_REFUSED_OFFSET = (
    "2026-06-01T09:00:00+09:00",
    "2026-06-01T00:00:00-05:00",
    "2026-06-01t00:00:00z",
    "2026-06-01T00:00:00z",
    "2026-06-01t00:00:00Z",
)

#: Refused for the other reason: each is a *second spelling of an instant already spellable*.
#: ``00:00:00Z``, ``.0Z``, ``.00Z`` and ``.000Z`` are one moment written four ways, and an
#: approval is addressed by hashing the text it carries -- so four spellings produced four
#: ``approval_id`` values and four decision identities for one authorization.
_STORED_REFUSED_FRACTION = (
    "2026-06-01T00:00:00.0Z",
    "2026-06-01T00:00:00.00Z",
    "2026-06-01T00:00:00.000Z",
    "2026-06-01T00:00:00.500Z",
    "2026-06-01T00:00:00.50Z",
    "2026-06-01T00:00:00.0000000Z",
)

_STORED_REFUSED = _STORED_REFUSED_OFFSET + _STORED_REFUSED_FRACTION


def _timestamp_validator() -> Any:
    from manosube_agent_civilization.difference.validation import SCHEMA_BASE, validators

    return validators()[SCHEMA_BASE + "common/timestamp.schema.json"]


def test_the_stored_grammar_has_one_owner_and_the_schema_carries_it() -> None:
    """The schema's pattern *is* the owner's string, not a second description of it.

    ``pattern`` was ``Z$`` -- a suffix test that accepted a space separator, an ISO week date
    and an unseparated basic form, none of which the code accepted. The schema now carries
    the owner's expression verbatim, which is why the corpus below can be asked of both.
    """

    schema = json.loads(
        (ROOT / "01_SCHEMA" / "common" / "timestamp.schema.json").read_text(encoding="utf-8")
    )
    assert schema["pattern"] == conformance.STORED_TIMESTAMP_PATTERN


def _admits(value: str) -> tuple[bool, bool]:
    """Whether the schema and the admission owner each accept *value* as a stored timestamp.

    The schema is asked through the repository's real validator registry, so this is the
    schema deciding and not a regular expression recompiled here to agree with itself.
    """

    by_schema = _timestamp_validator().is_valid(value)
    try:
        conformance.stored_instant(value, "corpus value")
    except AuthorityError:
        return by_schema, False
    return by_schema, True


@pytest.mark.parametrize(
    "value", _STORED_ACCEPTED + _STORED_REFUSED + _ACCEPTED + _REFUSED
)
def test_the_owner_is_never_looser_than_the_stored_schema(value: str) -> None:
    """Every value in every corpus: what the owner admits, the schema admits.

    This is the direction that matters for admission. The schema runs first, inside
    ``admit``; an owner that accepted something the schema refuses would be a second, looser
    contract reachable only through code.
    """

    by_schema, by_code = _admits(value)
    assert by_schema or not by_code, (value, by_schema, by_code)


def test_the_two_part_company_only_where_a_pattern_cannot_see_a_calendar() -> None:
    """The other direction, stated exactly rather than asserted as equality.

    ``pattern`` is a grammar. It cannot know that June has thirty days, that an hour ends at
    23, or that no zone is ninety-nine hours from UTC, so the schema admits three spellings
    the owner refuses. Naming them is the point: this is the residual gap, it is closed by
    the owner before any stored bound is compared, and it is *not* closed by the schema.

    The non-claim, said plainly: validating a record against ``timestamp.schema.json`` alone
    does not establish that its timestamps name real instants. Authority establishes that
    because every stored bound it compares crosses :func:`stored_instant` first.
    """

    disagreeing = {
        value
        for value in _STORED_ACCEPTED + _STORED_REFUSED + _ACCEPTED + _REFUSED
        for by_schema, by_code in [_admits(value)]
        if by_schema != by_code
    }
    assert disagreeing == {
        value for value in _REFUSED_AS_NO_INSTANT if _timestamp_validator().is_valid(value)
    }
    # ...and each one is refused by the owner naming the form it failed, not silently.
    for value in disagreeing:
        with pytest.raises(AuthorityError, match="RFC 3339"):
            conformance.stored_instant(value, "residual gap")


@pytest.mark.parametrize("value", _STORED_REFUSED_OFFSET)
def test_a_stored_approval_bound_may_not_carry_an_explicit_offset(value: str) -> None:
    """An offset in a stored field is refused at admission, before it can bind anything."""

    difference = derived_difference()
    requested, where = action("WRITE_FILE"), scope()
    # Both bounds, because a fix applied to the opening one alone leaves the closing one
    # reading an offset the schema refuses.
    bounds = (
        approval(difference, requested, where, approved_at=value),
        approval(difference, requested, where, expires_at=value),
    )
    for granted in bounds:
        with pytest.raises(AuthorityError):
            evaluate_authority(
                authority_request(
                    difference, requested, where, rules=[], approvals=[granted]
                )
            )


@pytest.mark.parametrize("value", _STORED_ACCEPTED)
def test_the_stored_form_is_still_accepted(value: str) -> None:
    """The control. Refusing more must not have refused the canonical spelling too."""

    assert conformance.stored_instant(value, "control") == conformance.transient_instant(
        value, "control"
    )


def test_the_transient_form_never_becomes_a_stored_one() -> None:
    """Why the looser transient grammar is safe: the evaluation time is not written down.

    If an offset spelling could reach a content-addressed field the split would only move the
    problem. It cannot: the decision record carries no evaluation time, and the same request
    evaluated at two equivalent spellings of one instant is one decision with one identity.
    """

    difference = derived_difference()
    requested, where = action("WRITE_FILE"), scope()
    governing = [rule(difference["project_id"], action_kinds=["WRITE_FILE"])]
    utc = evaluate_authority(
        authority_request(
            difference,
            requested,
            where,
            rules=governing,
            evaluation_time="2026-06-01T00:00:00Z",
        )
    )
    offset = evaluate_authority(
        authority_request(
            difference,
            requested,
            where,
            rules=governing,
            evaluation_time="2026-06-01T09:00:00+09:00",
        )
    )
    assert utc == offset
    written = json.dumps(utc, sort_keys=True)
    for spelling in ("2026-06-01T00:00:00Z", "2026-06-01T09:00:00+09:00"):
        assert spelling not in written


# --------------------------------------------------------------------------- #
# a fraction is compared, never truncated
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("digits", [1, 3, 6, 7, 9, 15, 30, 4301, 10000])
def test_a_fraction_orders_exactly_at_every_precision(digits: int) -> None:
    """``datetime`` holds microseconds and silently drops the rest.

    At seven digits and beyond the two values below became the *same* instant, so the
    strictly-later one compared as not-later. The ordering has to hold at every precision a
    caller may write, not at the six ``datetime`` happens to store.

    The two largest cases are the second half of that lesson. An exact-rational fix ordered
    them correctly in principle and raised ``ValueError`` in practice, because ``int(digits)``
    stops at CPython's 4,300-digit conversion limit -- so the ceiling moved rather than went
    away. Digits are compared as digits and have no ceiling.
    """

    earlier = f"2026-06-01T00:00:00.{'0' * (digits - 1)}1Z"
    later = f"2026-06-01T00:00:00.{'0' * (digits - 1)}2Z"
    assert conformance.stored_instant(earlier, "a") < conformance.stored_instant(later, "b")


def test_a_fraction_past_the_integer_limit_does_not_leave_as_a_raw_error() -> None:
    """The finding: the refusal path was there and the conversion happened outside it.

    ``int(digits)`` above 4,300 digits raises a plain ``ValueError`` that no Authority
    vocabulary covers, so a long enough evaluation time left ``evaluate_authority`` as a raw
    Python error -- the same shape as round 2's fourth finding, one level down.
    """

    difference = derived_difference()
    requested, where = action("WRITE_FILE"), scope()
    long_fraction = "2026-06-01T00:00:00." + "0" * 4400 + "1Z"
    decision = evaluate_authority(
        authority_request(
            difference,
            requested,
            where,
            rules=[rule(difference["project_id"])],
            evaluation_time=long_fraction,
        )
    )
    # Accepted, not refused: an unbounded fraction is well-formed RFC 3339 and the evaluator
    # has no reason to reject one. What it may not do is crash on it.
    assert decision["decision"] == AUTONOMOUS


def test_an_unbounded_fraction_still_binds_a_validity_window() -> None:
    """And the comparison it feeds is still exact at that length."""

    difference = derived_difference()
    requested, where = action("WRITE_FILE"), scope()
    opens = "2026-06-01T00:00:00." + "0" * 4400 + "2Z"
    granted = approval(difference, requested, where, approved_at=opens)
    decision = evaluate_authority(
        authority_request(
            difference,
            requested,
            where,
            rules=[],
            approvals=[granted],
            evaluation_time="2026-06-01T00:00:00." + "0" * 4400 + "1Z",
        )
    )
    assert decision["decision"] == HUMAN_APPROVAL_REQUIRED
    assert "APPROVAL_OUTSIDE_VALIDITY_WINDOW" in decision["decision_reason_codes"]


# --------------------------------------------------------------------------- #
# one instant, one stored spelling
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("value", _STORED_REFUSED_FRACTION)
def test_a_stored_bound_may_not_spell_one_instant_a_second_way(value: str) -> None:
    """Refused at admission, on both bounds, before the identity is recomputed or used."""

    difference = derived_difference()
    requested, where = action("WRITE_FILE"), scope()
    bounds = (
        approval(difference, requested, where, approved_at=value),
        approval(difference, requested, where, expires_at=value),
    )
    for granted in bounds:
        with pytest.raises(AuthorityError):
            evaluate_authority(
                authority_request(
                    difference, requested, where, rules=[], approvals=[granted]
                )
            )


def test_one_instant_has_exactly_one_stored_spelling() -> None:
    """The property the two tests above are instances of, over two instants.

    Without this a fix could refuse ``.0Z`` and still admit ``.00Z``, leaving the identity
    collision open in the case nobody listed.
    """

    for equivalents in (
        (
            "2026-06-01T00:00:00Z",
            "2026-06-01T00:00:00.0Z",
            "2026-06-01T00:00:00.00Z",
            "2026-06-01T00:00:00.000000Z",
        ),
        (
            "2026-06-01T00:00:00.5Z",
            "2026-06-01T00:00:00.50Z",
            "2026-06-01T00:00:00.500Z",
            "2026-06-01T00:00:00.5000000Z",
        ),
    ):
        admitted = [value for value in equivalents if _admits(value)[1]]
        assert admitted == [equivalents[0]], admitted


def test_a_non_canonical_stored_spelling_is_refused_and_never_rewritten() -> None:
    """The refusal is the point: normalising it would reinterpret a computed address.

    An approval's ``approval_id`` is a hash of the text it carries. Silently reading ``.0Z``
    as ``Z`` would mean deciding that a record whose identity was computed over one text
    really means another -- and an address its own owner will reinterpret is not an address.
    """

    difference = derived_difference()
    requested, where = action("WRITE_FILE"), scope()
    granted = approval(difference, requested, where, approved_at="2026-06-01T00:00:00.0Z")
    with pytest.raises(AuthorityValidationError, match="approved_at"):
        evaluate_authority(
            authority_request(difference, requested, where, rules=[], approvals=[granted])
        )
    # The record is untouched: refusing it did not quietly repair it on the way out.
    assert granted["approved_at"] == "2026-06-01T00:00:00.0Z"


def test_the_transient_form_still_normalises_equivalent_fractions() -> None:
    """The other half. A clock reading is compared, not addressed, so padding is inert.

    The control for the rule above: refusing extra spellings *in a record* must not start
    refusing them from a caller, and three spellings of one evaluation time must produce one
    decision rather than three.
    """

    difference = derived_difference()
    requested, where = action("WRITE_FILE"), scope()
    governing = [rule(difference["project_id"], action_kinds=["WRITE_FILE"])]
    records = [
        evaluate_authority(
            authority_request(
                difference,
                requested,
                where,
                rules=governing,
                evaluation_time=spelling,
            )
        )
        for spelling in (
            "2026-06-01T00:00:00.5Z",
            "2026-06-01T00:00:00.50Z",
            "2026-06-01T00:00:00.500Z",
        )
    ]
    assert records[0] == records[1] == records[2]
    assert len({record["authority_decision_id"] for record in records}) == 1


def test_an_approval_effective_after_the_evaluation_time_does_not_bind() -> None:
    """The finding itself: a not-yet-effective approval returned ``AUTONOMOUS``.

    The approval opens one ten-millionth of a second *after* the evaluation. Truncated to
    microseconds the two are equal, the window contains the evaluation, and the request was
    authorized by an approval that was not yet in force.
    """

    difference = derived_difference()
    requested, where = action("WRITE_FILE"), scope()
    granted = approval(
        difference, requested, where, approved_at="2026-06-01T00:00:00.0000002Z"
    )
    decision = evaluate_authority(
        authority_request(
            difference,
            requested,
            where,
            rules=[],
            approvals=[granted],
            evaluation_time="2026-06-01T00:00:00.0000001Z",
        )
    )
    assert decision["decision"] == HUMAN_APPROVAL_REQUIRED
    assert "APPROVAL_OUTSIDE_VALIDITY_WINDOW" in decision["decision_reason_codes"]
    assert decision["approval_ref"] is None


def test_an_approval_already_effective_at_that_precision_still_binds() -> None:
    """The control: refusing the earlier instant must not refuse the later one too."""

    difference = derived_difference()
    requested, where = action("WRITE_FILE"), scope()
    granted = approval(
        difference, requested, where, approved_at="2026-06-01T00:00:00.0000001Z"
    )
    decision = evaluate_authority(
        authority_request(
            difference,
            requested,
            where,
            rules=[],
            approvals=[granted],
            evaluation_time="2026-06-01T00:00:00.0000002Z",
        )
    )
    assert decision["decision"] == AUTONOMOUS
    assert decision["approval_ref"] is not None


def test_an_expiry_beyond_microseconds_is_not_rounded_into_the_window() -> None:
    """The same truncation at the closing bound: an expired approval read as still valid."""

    difference = derived_difference()
    requested, where = action("WRITE_FILE"), scope()
    granted = approval(
        difference, requested, where, expires_at="2026-06-01T00:00:00.0000001Z"
    )
    decision = evaluate_authority(
        authority_request(
            difference,
            requested,
            where,
            rules=[],
            approvals=[granted],
            evaluation_time="2026-06-01T00:00:00.0000002Z",
        )
    )
    assert decision["decision"] == HUMAN_APPROVAL_REQUIRED
    assert "APPROVAL_OUTSIDE_VALIDITY_WINDOW" in decision["decision_reason_codes"]


# --------------------------------------------------------------------------- #
# a numeric offset has a range, and the grammar is the only gate that sees it
# --------------------------------------------------------------------------- #
#
# RFC 3339 §5.6 fixes `time-hour = 00-23` and `time-minute = 00-59`. For every other
# over-range component the "parse second" step catches the value -- `datetime(...)` refuses
# month 13, hour 24 and second 60. It does not catch this one:
# `timezone(timedelta(hours=…, minutes=…))` *normalises* an over-range minute into an hour
# carry, so `+00:60` silently became `+01:00` and named a real instant.
#
# `_REFUSED_AS_NO_INSTANT` already carries `+99:00` on the reasoning that a regular
# expression cannot see range. `+00:99` is the case where the *parser* cannot see it either,
# which is why the range had to move into the grammar rather than beside it.

_OFFSET_HOURS = range(24)
_OFFSET_MINUTES = range(60)


def _offset_instant(offset: str) -> object:
    return conformance.transient_instant(f"2026-06-01T00:00:00{offset}", "evaluation time")


def test_every_offset_rfc3339_permits_is_accepted() -> None:
    """The whole legal space, not a handful of examples: 2 x 24 x 60 = 2880 offsets."""

    refused: list[str] = []
    for sign in ("+", "-"):
        for hour in _OFFSET_HOURS:
            for minute in _OFFSET_MINUTES:
                offset = f"{sign}{hour:02d}:{minute:02d}"
                try:
                    _offset_instant(offset)
                except AuthorityError:
                    refused.append(offset)
    assert not refused, refused[:20]


def test_no_offset_rfc3339_forbids_is_accepted() -> None:
    """The whole illegal space in the same two-digit shape: hours 24-99 or minutes 60-99.

    1840 spellings were admitted before this correction -- 920 per sign, both signs -- and
    each one named an instant the grammar claimed to refuse.
    """

    admitted: list[str] = []
    for sign in ("+", "-"):
        for hour in range(100):
            for minute in range(100):
                if hour in _OFFSET_HOURS and minute in _OFFSET_MINUTES:
                    continue
                offset = f"{sign}{hour:02d}:{minute:02d}"
                try:
                    _offset_instant(offset)
                    admitted.append(offset)
                except AuthorityError:
                    pass
    assert not admitted, admitted[:20]


def test_the_offset_matrices_are_neither_empty_nor_overlapping() -> None:
    """The harness before its subject: an empty illegal set passes the test above."""

    legal = {
        f"{sign}{hour:02d}:{minute:02d}"
        for sign in ("+", "-")
        for hour in _OFFSET_HOURS
        for minute in _OFFSET_MINUTES
    }
    illegal = {
        f"{sign}{hour:02d}:{minute:02d}"
        for sign in ("+", "-")
        for hour in range(100)
        for minute in range(100)
        if hour not in _OFFSET_HOURS or minute not in _OFFSET_MINUTES
    }
    assert len(legal) == 2880, len(legal)
    assert len(illegal) == 17120, len(illegal)
    assert not (legal & illegal)


@pytest.mark.parametrize(
    "offset", ["+00:60", "-00:60", "+00:99", "+23:60", "+24:00", "-99:00", "+99:99"]
)
def test_an_over_range_offset_never_reaches_the_timezone_constructor(offset: str) -> None:
    """Named cases, and the reason they matter: normalisation is what made them invisible."""

    with pytest.raises(AuthorityError, match="RFC 3339"):
        _offset_instant(offset)


def test_an_over_range_offset_no_longer_decides_a_validity_window() -> None:
    """The failure the reviewer reproduced: `+00:60` returned AUTONOMOUS through the boundary.

    The approval opens at 00:59:59Z and closes at 01:00:01Z. `+01:00` places the evaluation
    inside it; `+00:60` is the same instant spelled in a way RFC 3339 forbids, and used to
    reach the same decision.
    """

    difference = derived_difference()
    requested, where = action("WRITE_FILE"), scope()
    granted = approval(
        difference, requested, where,
        approved_at="2026-06-01T00:59:59Z", expires_at="2026-06-01T01:00:01Z",
    )

    inside = evaluate_authority(
        authority_request(
            difference, requested, where, rules=[], approvals=[granted],
            evaluation_time="2026-06-01T02:00:00+01:00",
        )
    )
    assert inside["decision"] == AUTONOMOUS
    assert "APPROVAL_EXACT" in inside["decision_reason_codes"]

    with pytest.raises(AuthorityError, match="RFC 3339"):
        evaluate_authority(
            authority_request(
                difference, requested, where, rules=[], approvals=[granted],
                evaluation_time="2026-06-01T02:00:00+00:60",
            )
        )


def test_the_offset_correction_did_not_touch_the_stored_surface() -> None:
    """Stored timestamps take `Z` only, so no offset range applies to them at all.

    Asserted rather than assumed: this correction is confined to the transient grammar, and
    the stored pattern is still the string the canonical schema carries.
    """

    import json

    assert "Z" in conformance.STORED_TIMESTAMP_PATTERN
    assert "[+-]" not in conformance.STORED_TIMESTAMP_PATTERN
    schema = json.loads(
        (ROOT / "01_SCHEMA" / "common" / "timestamp.schema.json").read_text(encoding="utf-8")
    )
    assert schema["pattern"] == conformance.STORED_TIMESTAMP_PATTERN


def test_equivalent_offsets_still_name_one_instant() -> None:
    """The control. Narrowing the range must not have broken offset arithmetic."""

    assert _offset_instant("+09:00") == conformance.transient_instant(
        "2026-05-31T15:00:00Z", "control"
    )
    assert _offset_instant("-05:00") == conformance.transient_instant(
        "2026-06-01T05:00:00Z", "control"
    )
    assert _offset_instant("+00:00") == conformance.transient_instant(
        "2026-06-01T00:00:00Z", "control"
    )
