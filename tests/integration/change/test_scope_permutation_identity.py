"""A scope is a set. Two requests naming the same members are the same request.

`authority.scope.require_scope` admitted unique ``paths`` and ``subjects`` in caller order.
Containment and overlap read them as sets, but Authority Decision identity and everything
downstream hashed the ordered representation, so permuting members preserved the decision and
changed four identities:

```text
SCOPE_AUTHORIZATION_SEMANTICS=SET
SCOPE_IDENTITY_SEMANTICS=LIST_ORDER
```

Issue #31 requires ``same semantic input and input permutation -> identical Change identity``,
so this was a straight acceptance failure.

Every case below drives the **real** route -- ``derive_differences`` to ``evaluate_authority``
to ``derive_change`` -- and none asserts on a hand-built record.
"""

from __future__ import annotations

import itertools
from typing import Any

import pytest
from tests.authority_helpers import action, approval, prohibition, rule, scope
from tests.change_helpers import derived_difference, route

from manosube_agent_civilization.authority import AUTONOMOUS, AuthorityError
from manosube_agent_civilization.authority.identity import change_intent_fingerprint
from manosube_agent_civilization.authority.scope import canonical_scope, require_scope
from manosube_agent_civilization.change import derive_change

pytestmark = pytest.mark.integration

PATHS: tuple[str, ...] = ("src/app.py", "src/lib.py", "src/util.py")
SUBJECTS: tuple[str, ...] = ("svc:api", "svc:worker")

#: Every ordering of the same members. 3! x 2! = 12 requests that must be one request.
PERMUTATIONS: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
    (paths, subjects)
    for paths in itertools.permutations(PATHS)
    for subjects in itertools.permutations(SUBJECTS)
]


@pytest.fixture(scope="module")
def difference() -> dict[str, Any]:
    return derived_difference()


def _granting_rule(project_id: str) -> dict[str, Any]:
    return rule(
        project_id,
        action_kinds=["RUN_COMMAND"],
        rule_scope=scope(paths=list(PATHS), subjects=list(SUBJECTS)),
    )


def _derive(
    difference: dict[str, Any], paths: tuple[str, ...], subjects: tuple[str, ...]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """One decision and one Change, through the public route, for one ordering."""

    requested = action("RUN_COMMAND", operation={"argv": ["pytest", "-q"]})
    where = scope(paths=list(paths), subjects=list(subjects))
    _, decision, request = route(
        difference, requested, where, rules=[_granting_rule(difference["project_id"])]
    )
    return decision, derive_change(request)


@pytest.fixture(scope="module")
def baseline(difference: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    return _derive(difference, PATHS, SUBJECTS)


# --------------------------------------------------------------------------- #
# The harness, before its subject
# --------------------------------------------------------------------------- #


def test_the_permutation_inventory_is_neither_empty_nor_shrunk() -> None:
    assert len(PERMUTATIONS) == 12, len(PERMUTATIONS)
    assert len({tuple(sorted(p)) for p, _ in PERMUTATIONS}) == 1


def test_the_orderings_really_are_different_inputs() -> None:
    """Otherwise every equality below would be comparing a request with itself."""

    distinct = {(paths, subjects) for paths, subjects in PERMUTATIONS}
    assert len(distinct) == 12
    assert (PATHS, SUBJECTS) in distinct
    assert (tuple(reversed(PATHS)), tuple(reversed(SUBJECTS))) in distinct


def test_the_baseline_authorizes(baseline: tuple[dict[str, Any], dict[str, Any]]) -> None:
    decision, change = baseline
    assert decision["decision"] == AUTONOMOUS
    assert change["status"] == "AUTHORIZED"


# --------------------------------------------------------------------------- #
# Every permutation is one request
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "paths,subjects", PERMUTATIONS, ids=lambda value: "-".join(part.split("/")[-1] for part in value)
)
def test_every_permutation_derives_the_same_identities(
    difference: dict[str, Any],
    baseline: tuple[dict[str, Any], dict[str, Any]],
    paths: tuple[str, ...],
    subjects: tuple[str, ...],
) -> None:
    """The eight equalities the adopted finding requires, over all twelve orderings."""

    expected_decision, expected_change = baseline
    decision, change = _derive(difference, paths, subjects)

    assert decision["decision"] == expected_decision["decision"] == AUTONOMOUS
    assert decision["authority_decision_id"] == expected_decision["authority_decision_id"]
    assert (
        decision["decision_semantic_fingerprint"]
        == expected_decision["decision_semantic_fingerprint"]
    )
    assert change["change_id"] == expected_change["change_id"]
    assert change["idempotency_key"] == expected_change["idempotency_key"]
    assert change["change_semantic_fingerprint"] == expected_change["change_semantic_fingerprint"]
    assert change["scope"] == expected_change["scope"]
    assert change["authority_ref"] == expected_change["authority_ref"]


def test_the_emitted_scope_is_the_canonical_one(
    baseline: tuple[dict[str, Any], dict[str, Any]]
) -> None:
    """Not merely equal across permutations -- equal to the canonical representation."""

    _, change = baseline
    assert change["scope"]["paths"] == sorted(PATHS)
    assert change["scope"]["subjects"] == sorted(SUBJECTS)
    assert change["scope"] == canonical_scope(change["scope"])


# --------------------------------------------------------------------------- #
# Different member sets are still different
# --------------------------------------------------------------------------- #


def _wide_rule(project_id: str) -> dict[str, Any]:
    return rule(
        project_id,
        action_kinds=["RUN_COMMAND"],
        rule_scope=scope(
            paths=[*PATHS, "src/other.py"], subjects=[*SUBJECTS, "svc:batch"]
        ),
    )


def _derive_wide(
    difference: dict[str, Any], paths: list[str], subjects: list[str]
) -> dict[str, Any]:
    requested = action("RUN_COMMAND", operation={"argv": ["pytest", "-q"]})
    where = scope(paths=paths, subjects=subjects)
    _, _, request = route(
        difference, requested, where, rules=[_wide_rule(difference["project_id"])]
    )
    return derive_change(request)


@pytest.mark.parametrize(
    "paths,subjects,why",
    [
        (["src/app.py", "src/other.py", "src/util.py"], list(SUBJECTS), "a swapped path"),
        ([*PATHS, "src/other.py"], list(SUBJECTS), "an added path"),
        (["src/app.py", "src/lib.py"], list(SUBJECTS), "a removed path"),
        (list(PATHS), ["svc:api"], "a removed subject"),
        (list(PATHS), [*SUBJECTS, "svc:batch"], "an added subject"),
    ],
    ids=["swapped-path", "added-path", "removed-path", "removed-subject", "added-subject"],
)
def test_a_different_member_set_derives_a_different_identity(
    difference: dict[str, Any], paths: list[str], subjects: list[str], why: str
) -> None:
    """The control that keeps normalization from having flattened everything together."""

    reference = _derive_wide(difference, list(PATHS), list(SUBJECTS))
    other = _derive_wide(difference, paths, subjects)
    assert other["change_id"] != reference["change_id"], why
    assert other["idempotency_key"] != reference["idempotency_key"], why


# --------------------------------------------------------------------------- #
# Duplicate rejection survives
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "paths,subjects",
    [
        (["src/app.py", "src/app.py"], list(SUBJECTS)),
        (list(PATHS), ["svc:api", "svc:api"]),
        (["src/app.py", "src/lib.py", "src/app.py"], list(SUBJECTS)),
    ],
    ids=["repeated-path", "repeated-subject", "repeat-not-adjacent"],
)
def test_a_repeated_member_is_still_refused(paths: list[str], subjects: list[str]) -> None:
    """Normalization sorts; it does not deduplicate. An input defect stays an input defect."""

    with pytest.raises(AuthorityError, match="repeats"):
        require_scope(scope(paths=paths, subjects=subjects), "requested scope")


def test_the_normalizer_itself_does_not_collapse_duplicates() -> None:
    """Read from the normalizer directly, so the refusal above cannot be its only evidence."""

    collapsed = canonical_scope({"repository": "r/x", "branch": "main", "paths": ["a", "a"], "subjects": []})
    assert collapsed["paths"] == ["a", "a"]


# --------------------------------------------------------------------------- #
# Containment and overlap keep their meaning
# --------------------------------------------------------------------------- #


def test_a_permuted_request_still_falls_inside_a_rule(difference: dict[str, Any]) -> None:
    decision, _ = _derive(difference, tuple(reversed(PATHS)), tuple(reversed(SUBJECTS)))
    assert decision["decision"] == AUTONOMOUS
    assert "RULE_PERMITS_AUTONOMOUS" in decision["decision_reason_codes"]


def test_a_permuted_request_still_overlaps_a_prohibition(difference: dict[str, Any]) -> None:
    """Refusal must not have become order-sensitive either."""

    requested = action("RUN_COMMAND", operation={"argv": ["pytest", "-q"]})
    where = scope(paths=list(reversed(PATHS)), subjects=list(reversed(SUBJECTS)))
    forbidden = prohibition(
        difference["project_id"],
        action_kinds=["RUN_COMMAND"],
        prohibited_scope=scope(paths=["src/util.py"], subjects=[]),
    )
    _, decision, _ = route(
        difference,
        requested,
        where,
        rules=[_granting_rule(difference["project_id"])],
        prohibitions=[forbidden],
    )
    assert decision["decision"] == "PROHIBITED"


def test_a_request_outside_the_rule_is_still_refused(difference: dict[str, Any]) -> None:
    requested = action("RUN_COMMAND", operation={"argv": ["pytest", "-q"]})
    where = scope(paths=["src/elsewhere.py"], subjects=[])
    _, decision, _ = route(
        difference, requested, where, rules=[_granting_rule(difference["project_id"])]
    )
    assert decision["decision"] != AUTONOMOUS


# --------------------------------------------------------------------------- #
# Approval continuity
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "paths,subjects", PERMUTATIONS, ids=lambda value: "-".join(part.split("/")[-1] for part in value)
)
def test_an_approval_binds_every_permutation_of_the_scope_it_covers(
    difference: dict[str, Any], paths: tuple[str, ...], subjects: tuple[str, ...]
) -> None:
    """An approval a human granted must not become unfindable by rewriting the order.

    ``APPROVAL_CONTRACT.md`` §2 binds ``change_intent_fingerprint(action, scope)``. Granted
    over one ordering and requested in another, that digest differed and the approval no
    longer bound -- a Human-only action silently falling back to approval-required.
    """

    requested = action("MERGE")
    granted_over = scope(paths=list(PATHS), subjects=list(SUBJECTS))
    granted = approval(difference, requested, granted_over)

    asked_as = scope(paths=list(paths), subjects=list(subjects))
    _, decision, request = route(difference, requested, asked_as, approvals=[granted])

    assert decision["decision"] == AUTONOMOUS
    assert decision["approval_ref"] == {"kind": "approval", "id": granted["approval_id"]}
    change = derive_change(request)
    assert granted["change_intent_fingerprint"] == change_intent_fingerprint(
        change["action"], change["scope"]
    )


def test_an_approval_for_another_scope_still_does_not_bind(difference: dict[str, Any]) -> None:
    """Continuity across permutations is not the same as covering a different scope."""

    requested = action("MERGE")
    granted = approval(difference, requested, scope(paths=["src/elsewhere.py"], subjects=[]))
    _, decision, _ = route(
        difference, requested, scope(paths=list(PATHS), subjects=list(SUBJECTS)),
        approvals=[granted],
    )
    assert decision["decision"] != AUTONOMOUS
