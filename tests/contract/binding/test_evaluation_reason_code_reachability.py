"""GAR-R1 (Issue #53 comment 5565302174): every reason code ``evaluation.evaluate()`` can
name is actually reachable, and the reachability matrix itself cannot silently go stale.

Before this file, no test in this repository exercised ``evaluate()`` by reason code -- the
route-drift guard in ``test_active_document_terminal_state.py`` trusted an allowlist scraped
from ``evaluation.py``'s source without any proof that every code on it corresponds to a real,
constructible record, or that the scrape had found all of them. One crafted record per
reason code closes that gap directly: each case is isolated so the named code is the *cause*
of the refusal (or, for the two ``PERMITTED`` codes, the reason the record was admitted), not
an incidental side effect of some other check.

GAR-R2-F2 (Issue #53 comment 5565703135) required a stronger, bidirectional static proof --
every declared reason code is reachable, *and* every emittable reason code is declared --
against an explicit ``EMITTED_REASON_CODES`` surface each evaluator module now declares,
rather than one this file infers on the route-drift guard's behalf. Both directions are
proven below: the reachability cases above prove every declared code is reachable; a
self-contained AST extraction proves nothing outside that declared set is emittable.
"""

from __future__ import annotations

import ast
import inspect
from typing import Any

import pytest

from manosube_agent_civilization.development_binding import (
    PERMITTED,
    REFUSED,
    evaluate,
    evaluation as evaluation_module,
    load_policy,
)
from manosube_agent_civilization.development_binding.policy import (
    EXECUTOR,
    EXECUTOR_TERMINAL_STATE,
    FINAL_ACCEPTANCE_STATE,
    HUMAN_AUTHORITY,
    MERGE_OPERATION_STATE,
    MERGE_RECOMMENDATION_STATE,
    STRUCTURAL_ADVISOR,
)

pytestmark = pytest.mark.contract

POLICY = load_policy()
_SOURCE = POLICY["external_finding_sources"][0]
_FORBIDDEN_DISPOSITION = POLICY["external_finding_forbidden_dispositions_without_adoption"][0]
_INITIAL_STATUS = POLICY["external_finding_initial_status"]
_ADOPTION_AUTHORITY = POLICY["external_finding_adoption_authority"]


def _finding(**overrides: Any) -> dict[str, Any]:
    base = {"observation_id": "OBS-1", "source": _SOURCE, "status": _INITIAL_STATUS}
    base.update(overrides)
    return base


def _adoption(**overrides: Any) -> dict[str, Any]:
    base = {
        "authority": _ADOPTION_AUTHORITY,
        "observation_id": "OBS-1",
        "disposition": _FORBIDDEN_DISPOSITION,
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------- #
# One crafted record per reason code -- (reason_code, expected_decision, record)
# --------------------------------------------------------------------------- #

_REACHABILITY_CASES: tuple[tuple[str, str, Any], ...] = (
    # evaluate(): the record shape itself
    ("RECORD_UNREADABLE", REFUSED, "not even a mapping"),
    ("RECORD_FIELD_IS_NOT_A_SCALAR", REFUSED, {"record_type": ["not a scalar"]}),
    ("UNKNOWN_RECORD_TYPE", REFUSED, {"record_type": "SOMETHING_ELSE"}),
    # _evaluate_handoff(): closed shape, reused across all three record types
    (
        "RECORD_CARRIES_UNKNOWN_KEYS",
        REFUSED,
        {
            "record_type": "HANDOFF_TRANSITION",
            "actor": EXECUTOR,
            "from_state": "IMPLEMENTATION_IN_PROGRESS",
            "to_state": "CLAUDE_CODE_IMPLEMENTATION_COMPLETE",
            "extra_key": "not part of the schema",
        },
    ),
    (
        "RECORD_OMITS_REQUIRED_KEYS",
        REFUSED,
        {
            "record_type": "HANDOFF_TRANSITION",
            "actor": EXECUTOR,
            "from_state": "IMPLEMENTATION_IN_PROGRESS",
        },
    ),
    (
        "UNKNOWN_ACTOR",
        REFUSED,
        {
            "record_type": "HANDOFF_TRANSITION",
            "actor": "NOT_A_REAL_ROLE",
            "from_state": "IMPLEMENTATION_IN_PROGRESS",
            "to_state": "CLAUDE_CODE_IMPLEMENTATION_COMPLETE",
        },
    ),
    (
        "UNKNOWN_FROM_STATE",
        REFUSED,
        {
            "record_type": "HANDOFF_TRANSITION",
            "actor": EXECUTOR,
            "from_state": "NOT_A_REAL_STATE",
            "to_state": "CLAUDE_CODE_IMPLEMENTATION_COMPLETE",
        },
    ),
    (
        "UNKNOWN_TO_STATE",
        REFUSED,
        {
            "record_type": "HANDOFF_TRANSITION",
            "actor": EXECUTOR,
            "from_state": "IMPLEMENTATION_IN_PROGRESS",
            "to_state": "NOT_A_REAL_STATE",
        },
    ),
    (
        "FINAL_ACCEPTANCE_DRIFT",
        REFUSED,
        {
            "record_type": "HANDOFF_TRANSITION",
            "actor": EXECUTOR,
            "from_state": "IMPLEMENTATION_IN_PROGRESS",
            "to_state": FINAL_ACCEPTANCE_STATE,
        },
    ),
    (
        "HUMAN_ONLY_STATE_ENTERED_BY_NON_HUMAN",
        REFUSED,
        {
            "record_type": "HANDOFF_TRANSITION",
            "actor": EXECUTOR,
            "from_state": "IMPLEMENTATION_IN_PROGRESS",
            "to_state": FINAL_ACCEPTANCE_STATE,
        },
    ),
    (
        "MERGE_OPERATION_DRIFT",
        REFUSED,
        {
            "record_type": "HANDOFF_TRANSITION",
            "actor": EXECUTOR,
            "from_state": FINAL_ACCEPTANCE_STATE,
            "to_state": MERGE_OPERATION_STATE,
        },
    ),
    (
        "MERGE_READINESS_RECOMMENDATION_DRIFT",
        REFUSED,
        {
            "record_type": "HANDOFF_TRANSITION",
            "actor": EXECUTOR,
            "from_state": "STRUCTURAL_REVIEW_PASS",
            "to_state": MERGE_RECOMMENDATION_STATE,
        },
    ),
    (
        "ADVISOR_ONLY_STATE_ENTERED_BY_NON_ADVISOR",
        REFUSED,
        {
            "record_type": "HANDOFF_TRANSITION",
            "actor": EXECUTOR,
            "from_state": "STRUCTURAL_REVIEW_PASS",
            "to_state": MERGE_RECOMMENDATION_STATE,
        },
    ),
    (
        "STRUCTURAL_REVIEW_DRIFT",
        REFUSED,
        {
            "record_type": "HANDOFF_TRANSITION",
            "actor": EXECUTOR,
            "from_state": "STRUCTURAL_REVIEW_RUNNING",
            "to_state": "BLOCKED",
        },
    ),
    (
        "EXECUTOR_CONTINUED_PAST_TERMINAL_STATE",
        REFUSED,
        {
            "record_type": "HANDOFF_TRANSITION",
            "actor": EXECUTOR,
            "from_state": EXECUTOR_TERMINAL_STATE,
            "to_state": "STRUCTURAL_REVIEW_RUNNING",
        },
    ),
    (
        "STRUCTURAL_REVIEW_SKIPPED",
        REFUSED,
        {
            "record_type": "HANDOFF_TRANSITION",
            "actor": STRUCTURAL_ADVISOR,
            "from_state": "STRUCTURAL_REVIEW_RUNNING",
            "to_state": MERGE_RECOMMENDATION_STATE,
        },
    ),
    (
        "MERGE_WITHOUT_FINAL_ACCEPTANCE",
        REFUSED,
        {
            "record_type": "HANDOFF_TRANSITION",
            "actor": HUMAN_AUTHORITY,
            "from_state": MERGE_RECOMMENDATION_STATE,
            "to_state": MERGE_OPERATION_STATE,
        },
    ),
    (
        "TRANSITION_NOT_DECLARED",
        REFUSED,
        {
            "record_type": "HANDOFF_TRANSITION",
            "actor": EXECUTOR,
            "from_state": "IMPLEMENTATION_IN_PROGRESS",
            "to_state": "EXECUTOR_SELF_REVIEW_COMPLETE",
        },
    ),
    (
        "DECLARED_TRANSITION",
        PERMITTED,
        {
            "record_type": "HANDOFF_TRANSITION",
            "actor": EXECUTOR,
            "from_state": "IMPLEMENTATION_IN_PROGRESS",
            "to_state": "CLAUDE_CODE_IMPLEMENTATION_COMPLETE",
        },
    ),
    # _evaluate_action()
    (
        "UNKNOWN_ACTOR",
        REFUSED,
        {"record_type": "ACTOR_ACTION", "actor": "NOT_A_REAL_ROLE", "action": "IMPLEMENTATION"},
    ),
    (
        "AUTOMATED_REVIEW_TRIGGER_PROHIBITED",
        REFUSED,
        {
            "record_type": "ACTOR_ACTION",
            "actor": STRUCTURAL_ADVISOR,
            "action": "REQUEST_AUTOMATED_EXTERNAL_REVIEW",
        },
    ),
    (
        "ROLE_DRIFT",
        REFUSED,
        {"record_type": "ACTOR_ACTION", "actor": EXECUTOR, "action": "STRUCTURAL_REVIEW"},
    ),
    (
        "ACTION_WITHIN_ROLE",
        PERMITTED,
        {"record_type": "ACTOR_ACTION", "actor": EXECUTOR, "action": "IMPLEMENTATION"},
    ),
    (
        "ACTION_NOT_GRANTED_TO_ROLE",
        REFUSED,
        {"record_type": "ACTOR_ACTION", "actor": EXECUTOR, "action": "NOT_A_GRANTED_ACTION"},
    ),
    # _evaluate_finding()
    (
        "FINDING_UNREADABLE",
        REFUSED,
        {
            "record_type": "EXTERNAL_FINDING_DISPOSITION",
            "actor": STRUCTURAL_ADVISOR,
            "finding": {"observation_id": "OBS-1", "source": _SOURCE},
            "requested_disposition": "PRESENT_TO_HUMAN",
            "adoption": None,
        },
    ),
    (
        "UNKNOWN_FINDING_SOURCE",
        REFUSED,
        {
            "record_type": "EXTERNAL_FINDING_DISPOSITION",
            "actor": STRUCTURAL_ADVISOR,
            "finding": _finding(source="NOT_A_REAL_SOURCE"),
            "requested_disposition": "PRESENT_TO_HUMAN",
            "adoption": None,
        },
    ),
    (
        "FINDING_ASSERTS_ITS_OWN_VERIFICATION",
        REFUSED,
        {
            "record_type": "EXTERNAL_FINDING_DISPOSITION",
            "actor": STRUCTURAL_ADVISOR,
            "finding": _finding(status="ALREADY_VERIFIED"),
            "requested_disposition": "PRESENT_TO_HUMAN",
            "adoption": None,
        },
    ),
    (
        "OBSERVATION_PRESENTED_NOT_ADOPTED",
        PERMITTED,
        {
            "record_type": "EXTERNAL_FINDING_DISPOSITION",
            "actor": STRUCTURAL_ADVISOR,
            "finding": _finding(),
            "requested_disposition": "PRESENT_TO_HUMAN",
            "adoption": None,
        },
    ),
    (
        "UNKNOWN_DISPOSITION",
        REFUSED,
        {
            "record_type": "EXTERNAL_FINDING_DISPOSITION",
            "actor": STRUCTURAL_ADVISOR,
            "finding": _finding(),
            "requested_disposition": "NOT_A_REAL_DISPOSITION",
            "adoption": None,
        },
    ),
    (
        "BOT_FINDING_AUTO_ADOPTION",
        REFUSED,
        {
            "record_type": "EXTERNAL_FINDING_DISPOSITION",
            "actor": STRUCTURAL_ADVISOR,
            "finding": _finding(),
            "requested_disposition": _FORBIDDEN_DISPOSITION,
            "adoption": None,
        },
    ),
    (
        "EXPLICIT_HUMAN_ADOPTION_ABSENT",
        REFUSED,
        {
            "record_type": "EXTERNAL_FINDING_DISPOSITION",
            "actor": STRUCTURAL_ADVISOR,
            "finding": _finding(),
            "requested_disposition": _FORBIDDEN_DISPOSITION,
            "adoption": None,
        },
    ),
    (
        "ADOPTION_UNREADABLE",
        REFUSED,
        {
            "record_type": "EXTERNAL_FINDING_DISPOSITION",
            "actor": STRUCTURAL_ADVISOR,
            "finding": _finding(),
            "requested_disposition": _FORBIDDEN_DISPOSITION,
            "adoption": {"authority": _ADOPTION_AUTHORITY, "observation_id": "OBS-1"},
        },
    ),
    (
        "ADOPTION_BY_NON_HUMAN_AUTHORITY",
        REFUSED,
        {
            "record_type": "EXTERNAL_FINDING_DISPOSITION",
            "actor": STRUCTURAL_ADVISOR,
            "finding": _finding(),
            "requested_disposition": _FORBIDDEN_DISPOSITION,
            "adoption": _adoption(authority="CHATGPT"),
        },
    ),
    (
        "ADOPTION_NOT_BOUND_TO_THIS_OBSERVATION",
        REFUSED,
        {
            "record_type": "EXTERNAL_FINDING_DISPOSITION",
            "actor": STRUCTURAL_ADVISOR,
            "finding": _finding(),
            "requested_disposition": _FORBIDDEN_DISPOSITION,
            "adoption": _adoption(observation_id="OBS-DIFFERENT"),
        },
    ),
    (
        "ADOPTION_NOT_BOUND_TO_THIS_DISPOSITION",
        REFUSED,
        {
            "record_type": "EXTERNAL_FINDING_DISPOSITION",
            "actor": STRUCTURAL_ADVISOR,
            "finding": _finding(),
            "requested_disposition": _FORBIDDEN_DISPOSITION,
            "adoption": _adoption(disposition="A_DIFFERENT_DISPOSITION"),
        },
    ),
    (
        "HUMAN_ADOPTED_OBSERVATION",
        PERMITTED,
        {
            "record_type": "EXTERNAL_FINDING_DISPOSITION",
            "actor": STRUCTURAL_ADVISOR,
            "finding": _finding(),
            "requested_disposition": _FORBIDDEN_DISPOSITION,
            "adoption": _adoption(),
        },
    ),
)


@pytest.mark.parametrize(
    "reason_code,expected_decision,record",
    _REACHABILITY_CASES,
    ids=[f"{index:02d}-{case[0]}" for index, case in enumerate(_REACHABILITY_CASES)],
)
def test_every_declared_reason_code_is_reachable(
    reason_code: str, expected_decision: str, record: Any
) -> None:
    verdict = evaluate(record)
    assert verdict["decision"] == expected_decision
    assert reason_code in verdict["reason_codes"]


# --------------------------------------------------------------------------- #
# GAR-R2-F2 (Issue #53 comment 5565703135): the bidirectional proof, against the
# module's own declared emitted-reason-code surface rather than an inferred one
# --------------------------------------------------------------------------- #


def _codes_from_source(source: str) -> frozenset[str]:
    """A string literal passed as a non-decision argument to ``_verdict(...)``, ``.append()``
    -ed onto a ``reasons`` list, or ``return``-ed directly by a ``_closed``/``_scalars``
    -shaped helper -- the three syntactic forms a reason code reaches its caller through in
    this codebase. Self-contained rather than importing
    ``test_active_document_terminal_state._codes_from_source`` -- this repository's tests are
    not a package other test modules import from -- but this is now purely a proof helper,
    never the production allowlist's own source (GAR-R2-F2 moved that to
    ``evaluation.EMITTED_REASON_CODES`` itself).
    """

    codes: set[str] = set()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Return):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                codes.add(node.value.value)
            continue
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if name == "_verdict":
            literal_args = node.args[1:]
        elif name == "append":
            literal_args = node.args
        else:
            continue
        for arg in literal_args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                codes.add(arg.value)
    return frozenset(codes)


def test_every_declared_reason_code_is_covered_by_a_reachability_case() -> None:
    """Direction one: every code ``evaluation.EMITTED_REASON_CODES`` declares is reachable --
    proven dynamically above, and checked here for completeness against the declared set
    itself rather than only against whatever the crafted cases happen to cover."""

    covered = {reason_code for reason_code, _decision, _record in _REACHABILITY_CASES}
    assert covered == evaluation_module.EMITTED_REASON_CODES


def test_every_emittable_reason_code_is_declared() -> None:
    """Direction two: nothing ``evaluate()``'s own source can actually emit escapes the
    declared surface -- a static proof, since a branch can be emittable in source shape
    without this suite's own crafted cases having found it yet."""

    emittable = _codes_from_source(inspect.getsource(evaluation_module))
    assert emittable == evaluation_module.EMITTED_REASON_CODES
