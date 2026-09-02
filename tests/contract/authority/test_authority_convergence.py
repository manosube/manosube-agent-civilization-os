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
_REFUSED = (
    "2026-06-01X00:00:00+00:00",   # arbitrary separator
    "2026-06-01 00:00:00+00:00",   # space separator
    "2026-W23-1T00:00:00+00:00",   # ISO week date
    "20260601T000000Z",            # basic unseparated form
    "2026-06-01T00:00:00+0000",    # offset without a colon
    "2026-06-01T00:00:00,5Z",      # comma fraction separator
    "2026-06-01T00:00:00",         # no offset at all
    "2026-06-01",                  # date only
    "2026-06-01T00:00:00.Z",       # fraction marker with no digits
    "2026-06-01T24:00:00Z",        # grammar matches, names no instant
    "2026-13-01T00:00:00Z",
    "2026-06-01T00:00:00+99:00",
    "not-a-time",
)

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
    """The evaluation time and both approval bounds cross the same admission function."""

    from manosube_agent_civilization.authority import (
        approval as approval_module,
        conformance,
        engine,
    )

    assert vars(approval_module)["instant"] is conformance.instant
    assert vars(engine)["instant"] is conformance.instant
