"""The decision path itself: what the answer rests on, and when it is settled.

The conformance boundary made every *input* canonical. These four findings were about the
*path* that consumes them, and they share one shape: **a check that ran only on the branch
that happened to need it.**

```text
an approval exclusion examined only when a rule already required approval
a rule cited only by identity, not by whether it supported the answer
a payload digest computed without asking whether the payload can be serialised
an instant parsed only inside the approval check
```

Each reads as complete from inside its own branch. Each is missing everywhere else.
"""

from __future__ import annotations

from typing import Any

import pytest
from tests.authority_helpers import (
    action,
    approval,
    authority_request,
    derived_difference,
    prohibition,
    rule,
    scope,
)

from manosube_agent_civilization.authority import (
    AUTONOMOUS,
    HUMAN_APPROVAL_REQUIRED,
    PROHIBITED,
    AuthorityError,
    evaluate_authority,
)

pytestmark = pytest.mark.contract


@pytest.fixture(scope="module")
def difference() -> dict[str, Any]:
    return derived_difference()


# --------------------------------------------------------------------------- #
# 1. an approval narrows regardless of what the rules decided
# --------------------------------------------------------------------------- #


def test_an_approval_exclusion_applies_even_when_a_rule_grants_autonomy(
    difference: dict[str, Any]
) -> None:
    """`APPROVAL_CONTRACT.md` §6: an approval may narrow, and may never widen.

    A narrowing that applies only when a rule already required approval is not a narrowing;
    it is a coincidence of which branch ran.
    """

    requested, where = action("WRITE_FILE"), scope()
    excluding = approval(difference, requested, where, prohibited_actions=["WRITE_FILE"])
    decision = evaluate_authority(
        authority_request(
            difference,
            requested,
            where,
            rules=[rule(difference["project_id"], action_kinds=["WRITE_FILE"])],
            approvals=[excluding],
        )
    )
    assert decision["decision"] == HUMAN_APPROVAL_REQUIRED
    assert "APPROVAL_EXCLUDES_ACTION" in decision["decision_reason_codes"]
    assert decision["approval_ref"] is None


def test_an_excluding_approval_never_also_authorizes_the_action(
    difference: dict[str, Any]
) -> None:
    """The approval that withheld the action does not then become the one that permits it."""

    requested, where = action("MERGE"), scope()
    excluding = approval(difference, requested, where, prohibited_actions=["MERGE"])
    decision = evaluate_authority(
        authority_request(difference, requested, where, approvals=[excluding])
    )
    assert decision["decision"] == HUMAN_APPROVAL_REQUIRED
    assert decision["approval_ref"] is None
    assert decision["excluding_approval_refs"] == [
        {"kind": "approval", "id": excluding["approval_id"]}
    ]


def test_an_approval_that_binds_and_excludes_nothing_still_authorizes(
    difference: dict[str, Any]
) -> None:
    """The control. Splitting binding from exclusion must not break the permitting path."""

    requested, where = action("MERGE"), scope()
    granted = approval(difference, requested, where)
    decision = evaluate_authority(
        authority_request(difference, requested, where, approvals=[granted])
    )
    assert decision["decision"] == AUTONOMOUS
    assert decision["approval_ref"] == {"kind": "approval", "id": granted["approval_id"]}
    assert decision["excluding_approval_refs"] == []


def test_an_exclusion_from_an_approval_that_does_not_bind_is_ignored(
    difference: dict[str, Any]
) -> None:
    """A narrowing only reaches a request the approval actually covers."""

    requested, where = action("WRITE_FILE"), scope()
    elsewhere = approval(
        difference,
        requested,
        where,
        project_id="PRJ-9999",
        prohibited_actions=["WRITE_FILE"],
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


def test_two_excluding_approvals_do_not_share_a_decision_identity(
    difference: dict[str, Any]
) -> None:
    """The provenance lesson, applied before it is reported: which approval withheld matters."""

    requested, where = action("MERGE"), scope()
    first = approval(
        difference, requested, where, prohibited_actions=["MERGE"],
        approved_at="2026-01-01T00:00:00Z",
    )
    second = approval(
        difference, requested, where, prohibited_actions=["MERGE"],
        approved_at="2026-02-01T00:00:00Z",
    )
    assert first["approval_id"] != second["approval_id"]
    one = evaluate_authority(
        authority_request(difference, requested, where, approvals=[first])
    )
    other = evaluate_authority(
        authority_request(difference, requested, where, approvals=[second])
    )
    assert one["decision"] == other["decision"]
    assert one["decision_reason_codes"] == other["decision_reason_codes"]
    assert one["authority_decision_id"] != other["authority_decision_id"]


# --------------------------------------------------------------------------- #
# 2. the cited rule supports the answer
# --------------------------------------------------------------------------- #


def _rules_where_the_permissive_one_sorts_first(
    project_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Find a governing pair whose lexicographically smallest ID is the permissive rule.

    Identity order is a hash order, so the case has to be searched for rather than assumed.
    Without this, the test would silently pass on a pair that never exercised the defect.
    """

    restrictive = rule(
        project_id, action_kinds=["WRITE_FILE"], decision=HUMAN_APPROVAL_REQUIRED
    )
    for index in range(500):
        permissive = rule(
            project_id, action_kinds=["WRITE_FILE", f"K{index}"], decision=AUTONOMOUS
        )
        if permissive["authority_rule_id"] < restrictive["authority_rule_id"]:
            return permissive, restrictive
    raise AssertionError("no governing pair found; the search itself is the defect")


def test_the_cited_rule_is_one_that_supports_the_resolved_decision(
    difference: dict[str, Any]
) -> None:
    """Citing the smallest governing ID named the rule that argued the other way.

    The reference participates in the decision's content address, so it has to identify the
    provenance of the answer and not merely a rule that happened to be present.
    """

    permissive, restrictive = _rules_where_the_permissive_one_sorts_first(
        difference["project_id"]
    )
    assert permissive["authority_rule_id"] < restrictive["authority_rule_id"]
    decision = evaluate_authority(
        authority_request(
            difference, action("WRITE_FILE"), scope(), rules=[permissive, restrictive]
        )
    )
    assert decision["decision"] == HUMAN_APPROVAL_REQUIRED
    assert decision["resolved_rule_ref"] == {
        "kind": "authority_rule",
        "id": restrictive["authority_rule_id"],
    }


def test_rule_order_does_not_change_the_cited_rule(difference: dict[str, Any]) -> None:
    permissive, restrictive = _rules_where_the_permissive_one_sorts_first(
        difference["project_id"]
    )
    requested, where = action("WRITE_FILE"), scope()
    forward = evaluate_authority(
        authority_request(difference, requested, where, rules=[permissive, restrictive])
    )
    backward = evaluate_authority(
        authority_request(difference, requested, where, rules=[restrictive, permissive])
    )
    assert forward == backward


def test_an_autonomous_decision_cites_a_rule_that_granted_it(
    difference: dict[str, Any]
) -> None:
    """The other direction: where all governing rules permit, the citation is one of them."""

    requested, where = action("WRITE_FILE"), scope()
    first = rule(difference["project_id"], action_kinds=["WRITE_FILE"])
    second = rule(difference["project_id"], action_kinds=["WRITE_FILE", "DELETE_FILE"])
    decision = evaluate_authority(
        authority_request(difference, requested, where, rules=[first, second])
    )
    assert decision["decision"] == AUTONOMOUS
    cited = decision["resolved_rule_ref"]["id"]
    assert cited in {first["authority_rule_id"], second["authority_rule_id"]}


# --------------------------------------------------------------------------- #
# 2b. provenance is derived from the answer, and the answer is not final until the end
# --------------------------------------------------------------------------- #
#
# "The cited rule supports the resolved decision" was asserted for the rule-conflict path and
# implemented there alone. A rule was chosen at *rule resolution*, before the two floors and
# before any approval narrowing -- so a ``MERGE`` request under an ``AUTONOMOUS`` rule
# returned ``HUMAN_APPROVAL_REQUIRED`` while citing a rule that declares ``AUTONOMOUS``. The
# record's provenance argued against its own answer, and that reference is part of the
# decision's content address.
#
# The rule holds where it is enumerated, so it is enumerated here: every combination of the
# two floors, the rule sets that reach them, and the approvals that narrow or lower.

_PROVENANCE_RULE_SETS = ("none", "autonomous", "requires", "both")
_PROVENANCE_APPROVALS = ("none", "permitting", "excluding")


def _provenance_rules(project_id: str, kind: str, name: str) -> list[dict[str, Any]]:
    permits = rule(
        project_id,
        action_kinds=[kind],
        decision=AUTONOMOUS,
        maximum_reversibility="IRREVERSIBLE",
    )
    requires = rule(
        project_id,
        action_kinds=[kind],
        decision=HUMAN_APPROVAL_REQUIRED,
        maximum_reversibility="IRREVERSIBLE",
    )
    return {
        "none": [],
        "autonomous": [permits],
        "requires": [requires],
        "both": [permits, requires],
    }[name]


def _provenance_matrix() -> list[dict[str, Any]]:
    difference = derived_difference()
    where = scope()
    rows: list[dict[str, Any]] = []
    for kind in ("WRITE_FILE", "MERGE"):          # no floor, then the human-only floor
        for reversibility in ("REVERSIBLE", "IRREVERSIBLE"):   # then the irreversible floor
            requested = action(kind, reversibility)
            for rule_name in _PROVENANCE_RULE_SETS:
                for approval_name in _PROVENANCE_APPROVALS:
                    granted = {
                        "none": [],
                        "permitting": [approval(difference, requested, where)],
                        "excluding": [
                            approval(difference, requested, where, prohibited_actions=[kind])
                        ],
                    }[approval_name]
                    rows.append(
                        {
                            "id": f"{kind}-{reversibility}-{rule_name}-{approval_name}",
                            "difference": difference,
                            "action": requested,
                            "scope": where,
                            "rules": _provenance_rules(difference["project_id"], kind, rule_name),
                            "approvals": granted,
                        }
                    )
    return rows


_PROVENANCE_MATRIX = _provenance_matrix()


def test_the_provenance_matrix_is_neither_empty_nor_shrunk() -> None:
    """The harness before its subject."""

    assert len(_PROVENANCE_MATRIX) == 48, len(_PROVENANCE_MATRIX)


def _provenance_decision(row: dict[str, Any]) -> dict[str, Any]:
    return evaluate_authority(
        authority_request(
            row["difference"],
            row["action"],
            row["scope"],
            rules=row["rules"],
            approvals=row["approvals"],
        )
    )


@pytest.mark.parametrize(
    "row", _PROVENANCE_MATRIX, ids=lambda row: row["id"]
)
def test_a_cited_rule_always_declares_the_decision_it_is_cited_for(
    row: dict[str, Any]
) -> None:
    """Over every floor and every narrowing: the citation never contradicts the answer."""

    decision = _provenance_decision(row)
    cited = decision["resolved_rule_ref"]
    if cited is None:
        return
    by_id = {supplied["authority_rule_id"]: supplied for supplied in row["rules"]}
    assert cited["id"] in by_id, cited
    assert by_id[cited["id"]]["decision"] == decision["decision"], (
        row["id"], by_id[cited["id"]]["decision"], decision["decision"]
    )


@pytest.mark.parametrize(
    "row", _PROVENANCE_MATRIX, ids=lambda row: row["id"]
)
def test_the_reason_codes_and_the_citation_cannot_disagree(row: dict[str, Any]) -> None:
    """Exactly one of the three rule codes, and it says what the citation shows.

    Without this the citation could be cleared while ``RULE_RESOLVED`` stayed behind -- a
    record reporting a resolved rule and naming none.
    """

    decision = _provenance_decision(row)
    codes = set(decision["decision_reason_codes"])
    present = codes & {"RULE_RESOLVED", "RULE_NOT_DECISIVE", "NO_RULE_RESOLVED"}
    assert len(present) == 1, (row["id"], sorted(present))
    cited = decision["resolved_rule_ref"]
    assert (cited is not None) == ("RULE_RESOLVED" in present), (row["id"], present, cited)
    if "NO_RULE_RESOLVED" in present:
        assert not row["rules"] or _no_rule_governs(row), row["id"]


def _no_rule_governs(row: dict[str, Any]) -> bool:
    """Whether every supplied rule fails to govern -- reversibility is the only way here."""

    return all(
        rule_record["maximum_reversibility"] == "REVERSIBLE"
        and row["action"]["reversibility"] == "IRREVERSIBLE"
        for rule_record in row["rules"]
    )


def test_the_matrix_exercises_all_three_provenance_outcomes() -> None:
    """The control. A matrix that only ever reaches one outcome asserts nothing.

    ``RULE_NOT_DECISIVE`` is the outcome the finding was about, so its presence here is what
    makes the two tests above a regression rather than a restatement.
    """

    seen: dict[str, int] = {"RULE_RESOLVED": 0, "RULE_NOT_DECISIVE": 0, "NO_RULE_RESOLVED": 0}
    for row in _PROVENANCE_MATRIX:
        for code in _provenance_decision(row)["decision_reason_codes"]:
            if code in seen:
                seen[code] += 1
    assert all(count > 0 for count in seen.values()), seen


def test_a_floor_alone_does_not_borrow_a_permissive_rule(
    difference: dict[str, Any]
) -> None:
    """The finding itself, named: ``MERGE`` under a rule that grants autonomy.

    The human-only floor created the whole of the restriction. No rule declares it, so the
    honest citation is none -- not the rule that argued the other way.
    """

    requested, where = action("MERGE"), scope()
    permits = rule(difference["project_id"], action_kinds=["MERGE"], decision=AUTONOMOUS)
    decision = evaluate_authority(
        authority_request(difference, requested, where, rules=[permits])
    )
    assert decision["decision"] == HUMAN_APPROVAL_REQUIRED
    assert "ACTION_IS_HUMAN_ONLY" in decision["decision_reason_codes"]
    assert "RULE_NOT_DECISIVE" in decision["decision_reason_codes"]
    assert decision["resolved_rule_ref"] is None


def test_the_irreversible_floor_does_not_borrow_a_permissive_rule(
    difference: dict[str, Any]
) -> None:
    """The other floor, which a fix aimed only at the first one would leave open."""

    requested, where = action("WRITE_FILE", "IRREVERSIBLE"), scope()
    permits = rule(
        difference["project_id"],
        action_kinds=["WRITE_FILE"],
        decision=AUTONOMOUS,
        maximum_reversibility="IRREVERSIBLE",
    )
    decision = evaluate_authority(
        authority_request(difference, requested, where, rules=[permits])
    )
    assert decision["decision"] == HUMAN_APPROVAL_REQUIRED
    assert "IRREVERSIBLE_ACTION" in decision["decision_reason_codes"]
    assert decision["resolved_rule_ref"] is None


def test_an_exclusion_alone_does_not_borrow_a_permissive_rule(
    difference: dict[str, Any]
) -> None:
    """Narrowing by approval raises the decision too, and cannot borrow a rule either."""

    requested, where = action("WRITE_FILE"), scope()
    permits = rule(difference["project_id"], action_kinds=["WRITE_FILE"], decision=AUTONOMOUS)
    withheld = approval(difference, requested, where, prohibited_actions=["WRITE_FILE"])
    decision = evaluate_authority(
        authority_request(
            difference, requested, where, rules=[permits], approvals=[withheld]
        )
    )
    assert decision["decision"] == HUMAN_APPROVAL_REQUIRED
    assert "APPROVAL_EXCLUDES_ACTION" in decision["decision_reason_codes"]
    assert decision["resolved_rule_ref"] is None


def test_a_floor_cleared_by_an_approval_still_cites_the_rule_that_permits(
    difference: dict[str, Any]
) -> None:
    """The control in the other direction. Clearing a citation is not the goal.

    Where the approval clears the floor and a governing rule *does* declare the resolved
    decision, that rule is the provenance of the answer and is cited.
    """

    requested, where = action("MERGE"), scope()
    permits = rule(difference["project_id"], action_kinds=["MERGE"], decision=AUTONOMOUS)
    granted = approval(difference, requested, where)
    decision = evaluate_authority(
        authority_request(
            difference, requested, where, rules=[permits], approvals=[granted]
        )
    )
    assert decision["decision"] == AUTONOMOUS
    assert decision["resolved_rule_ref"] == {
        "kind": "authority_rule",
        "id": permits["authority_rule_id"],
    }
    assert decision["approval_ref"] is not None


# --------------------------------------------------------------------------- #
# 3. the opaque payload must still be canonically serialisable
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("label", "payload"),
    [
        ("float", {"ratio": 1.5}),
        ("nested float", {"outer": {"inner": [1, 2.5]}}),
        ("bare float", 0.1),
        ("non-string key", {1: "a"}),
    ],
)
def test_a_payload_that_cannot_be_canonically_serialised_is_refused(
    difference: dict[str, Any], label: str, payload: Any
) -> None:
    """Opaque means Authority does not *interpret* the payload, not that it may be unrepresentable.

    Without a canonical serialisation there is no fingerprint over it, so there is nothing
    for an approval to bind -- and the state layer's ``CanonicalizationError`` was escaping
    the Authority boundary rather than becoming its documented rejection.
    """

    hand_built = {
        "action_kind": "WRITE_FILE",
        "reversibility": "REVERSIBLE",
        "operation": payload,
        "action_semantic_fingerprint": "sha256:" + "0" * 64,
    }
    with pytest.raises(AuthorityError):
        evaluate_authority(
            authority_request(
                difference, hand_built, scope(), rules=[rule(difference["project_id"])]
            )
        )


def test_no_state_layer_exception_escapes_the_authority_boundary(
    difference: dict[str, Any]
) -> None:
    """The vocabulary property, asserted rather than assumed."""

    from manosube_agent_civilization.state.errors import CanonicalizationError

    hand_built = {
        "action_kind": "WRITE_FILE",
        "reversibility": "REVERSIBLE",
        "operation": {"ratio": 1.5},
        "action_semantic_fingerprint": "sha256:" + "0" * 64,
    }
    try:
        evaluate_authority(authority_request(difference, hand_built, scope()))
    except AuthorityError:
        pass
    except CanonicalizationError as error:  # pragma: no cover - the defect this forbids
        raise AssertionError(f"a state-layer error escaped: {error}") from error


# --------------------------------------------------------------------------- #
# 4. the evaluation time is admitted before any route can return
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "route",
    ["rule grants autonomy", "prohibition returns first", "approval required, none supplied"],
)
@pytest.mark.parametrize("bad", ["not-a-time", "2026-13-01T00:00:00Z", "2026-06-01", ""])
def test_every_early_return_route_admits_the_evaluation_time_first(
    difference: dict[str, Any], route: str, bad: str
) -> None:
    """Time conformance belongs to admission, not to the one branch that reads a clock value.

    Parsed only inside the approval check, a malformed instant produced a decision on every
    route that never reached the parser -- which was most of them.
    """

    requested, where = action("WRITE_FILE"), scope()
    supplied: dict[str, Any] = {
        "rule grants autonomy": {
            "rules": [rule(difference["project_id"], action_kinds=["WRITE_FILE"])]
        },
        "prohibition returns first": {"prohibitions": [prohibition(difference["project_id"])]},
        "approval required, none supplied": {},
    }[route]
    with pytest.raises(AuthorityError):
        evaluate_authority(
            authority_request(
                difference, requested, where, evaluation_time=bad, **supplied
            )
        )


def test_a_naive_timestamp_names_no_instant(difference: dict[str, Any]) -> None:
    """Guessing a timezone is how two evaluators disagree about one approval.

    Refused by the RFC 3339 grammar now rather than by the post-parse timezone check --
    earlier and stricter, since RFC 3339 requires an offset. The later check remains as an
    unreachable backstop rather than being deleted: it costs nothing and it is the assertion
    that would fire if the grammar were ever loosened.
    """

    with pytest.raises(AuthorityError, match="RFC 3339"):
        evaluate_authority(
            authority_request(
                difference,
                action(),
                scope(),
                rules=[rule(difference["project_id"])],
                evaluation_time="2026-06-01T00:00:00",
            )
        )


def test_a_wellformed_time_still_decides_on_every_route(difference: dict[str, Any]) -> None:
    """The control: admission must not have made every route refuse."""

    requested, where = action("WRITE_FILE"), scope()
    permitted = evaluate_authority(
        authority_request(
            difference,
            requested,
            where,
            rules=[rule(difference["project_id"], action_kinds=["WRITE_FILE"])],
        )
    )
    refused = evaluate_authority(
        authority_request(
            difference, requested, where, prohibitions=[prohibition(difference["project_id"])]
        )
    )
    asked = evaluate_authority(authority_request(difference, action("MERGE"), where))
    assert permitted["decision"] == AUTONOMOUS
    assert refused["decision"] == PROHIBITED
    assert asked["decision"] == HUMAN_APPROVAL_REQUIRED
