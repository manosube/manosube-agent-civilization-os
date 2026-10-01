"""Issue #102 (Decision 0003): `GITHUB_COPILOT` is now an eligible implementation executor
alongside `CLAUDE_CODE` (`development_binding.policy.EXECUTOR_PROVIDERS`). Eligibility is not
authority -- this proves the mechanical check for the narrower question of which eligible
provider is the *selected* executor for one exact work unit, at one exact scope, right now.

See `development_binding.executor_selection` and `03_BINDING/COPILOT_PARTICIPATION.md` for the
design this suite proves: missing, forged, stale and replayed selections are refused; a scope
or SHA mismatch is refused; two providers simultaneously active for one work unit is refused;
and a complete, verified selection for either eligible provider is admitted.
"""

from __future__ import annotations

import ast
from copy import deepcopy
import inspect
from typing import Any

import pytest

from manosube_agent_civilization.development_binding import (
    EXECUTOR_SELECTION_ADMITTED,
    EXECUTOR_SELECTION_REFUSED,
    ExecutorSelectionError,
    evaluate_executor_selection,
    executor_selection as executor_selection_module,
)

pytestmark = pytest.mark.contract

_REAL_COMMENT_URL = (
    "https://github.com/manosube/manosube-agent-civilization-os/issues/102#issuecomment-5921931690"
)
_SHA_A = "a1b2c3d4e5f60718293a4b5c6d7e8f9011223344"
_SHA_B = "b2c3d4e5f60718293a4b5c6d7e8f901122334455"
_WORK_UNIT_ID = "WORK-UNIT-ISSUE-102-COPILOT-TRIAL-1"
_REPOSITORY = "manosube/manosube-agent-civilization-os"
_BRANCH = "agent/issue-102-copilot-trial-1"


def _receipt(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "work_unit_id": _WORK_UNIT_ID,
        "governing_issue": "#102",
        "selected_executor_provider": "GITHUB_COPILOT",
        "comment_url": _REAL_COMMENT_URL,
        "decision_authority": "SHUKOU",
        "decision_status": "RATIFIED",
    }
    base.update(overrides)
    return base


def _record(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema_version": "0.1",
        "work_unit_id": _WORK_UNIT_ID,
        "invoked_work_unit_id": _WORK_UNIT_ID,
        "governing_issue": "#102",
        "selected_executor_provider": "GITHUB_COPILOT",
        "comment_url": _REAL_COMMENT_URL,
        "decision_authority": "SHUKOU",
        "decision_status": "RATIFIED",
        "api_read_back_receipt": _receipt(),
        "authorized_repository": _REPOSITORY,
        "authorized_branch": _BRANCH,
        "authorized_base_sha": _SHA_A,
        "expected_head_sha": _SHA_A,
        "current_repository": _REPOSITORY,
        "current_branch": _BRANCH,
        "current_base_sha": _SHA_A,
        "current_head_sha": _SHA_A,
        "concurrently_active_provider_for_work_unit": "",
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------- #
# the required positive cases: both eligible providers, independently
# --------------------------------------------------------------------------- #


def test_a_complete_verified_copilot_selection_is_admitted() -> None:
    decision = evaluate_executor_selection(_record())
    assert decision["decision"] == EXECUTOR_SELECTION_ADMITTED
    assert decision["decision_reason_codes"] == []
    assert decision["selected_executor_provider"] == "GITHUB_COPILOT"


def test_a_complete_verified_claude_code_selection_is_also_admitted() -> None:
    """Decision 0003 does not narrow Claude Code's own path: an explicit selection record
    naming it is admitted exactly as one naming Copilot is."""

    record = _record(
        selected_executor_provider="CLAUDE_CODE",
        api_read_back_receipt=_receipt(selected_executor_provider="CLAUDE_CODE"),
    )
    decision = evaluate_executor_selection(record)
    assert decision["decision"] == EXECUTOR_SELECTION_ADMITTED
    assert decision["decision_reason_codes"] == []


def test_the_decision_is_deterministic_and_the_input_is_never_mutated() -> None:
    record = _record()
    before = deepcopy(record)
    first = evaluate_executor_selection(record)
    second = evaluate_executor_selection(deepcopy(record))
    assert record == before
    assert first == second


# --------------------------------------------------------------------------- #
# the required counterexample matrix
# --------------------------------------------------------------------------- #


def test_an_absent_selection_raises_rather_than_defaulting_to_admitted() -> None:
    """'Missing' is not a decision this evaluator answers -- there is no record to evaluate,
    and a caller that proceeds without one is not a caller this module authorized."""

    with pytest.raises(ExecutorSelectionError):
        evaluate_executor_selection(None)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "forged_url",
    [
        "SHUKOU said in chat: Copilot can take this one",
        "https://github.com/manosube/manosube-agent-civilization-os/issues/102",
        "https://github.com/manosube/manosube-agent-civilization-os/issues/102#discussion",
    ],
)
def test_a_forged_or_unposted_selection_is_refused(forged_url: str) -> None:
    decision = evaluate_executor_selection(_record(comment_url=forged_url))
    assert decision["decision"] == EXECUTOR_SELECTION_REFUSED
    assert "COMMENT_URL_NOT_A_VERIFIABLE_GITHUB_COMMENT" in decision["decision_reason_codes"]


def test_a_stale_selection_is_refused_when_new_commits_have_landed() -> None:
    """Commits landed on the authorized branch after the grant was issued: the grant no
    longer describes the current world and must not silently keep authorizing it."""

    decision = evaluate_executor_selection(_record(current_head_sha=_SHA_B))
    assert decision["decision"] == EXECUTOR_SELECTION_REFUSED
    assert decision["decision_reason_codes"] == ["HEAD_SHA_STALE"]


def test_an_unknown_provider_is_refused() -> None:
    decision = evaluate_executor_selection(
        _record(
            selected_executor_provider="CODEX",
            api_read_back_receipt=_receipt(selected_executor_provider="CODEX"),
        )
    )
    assert decision["decision"] == EXECUTOR_SELECTION_REFUSED
    assert "UNKNOWN_EXECUTOR_PROVIDER" in decision["decision_reason_codes"]


@pytest.mark.parametrize(
    "field,value,reason_code",
    [
        ("current_repository", "manosube/some-other-repository", "REPOSITORY_SCOPE_MISMATCH"),
        ("current_branch", "some-other-branch", "BRANCH_SCOPE_MISMATCH"),
        ("current_base_sha", _SHA_B, "BASE_SHA_SCOPE_MISMATCH"),
    ],
)
def test_a_scope_mismatch_is_refused(field: str, value: str, reason_code: str) -> None:
    decision = evaluate_executor_selection(_record(**{field: value}))
    assert decision["decision"] == EXECUTOR_SELECTION_REFUSED
    assert reason_code in decision["decision_reason_codes"]


def test_a_changed_base_and_a_changed_head_are_each_refused_and_independently_detected() -> None:
    decision = evaluate_executor_selection(
        _record(current_base_sha=_SHA_B, current_head_sha=_SHA_B)
    )
    assert decision["decision"] == EXECUTOR_SELECTION_REFUSED
    assert set(decision["decision_reason_codes"]) == {
        "BASE_SHA_SCOPE_MISMATCH",
        "HEAD_SHA_STALE",
    }


def test_a_grant_for_a_foreign_repository_is_refused_even_when_internally_consistent() -> None:
    foreign = "manosube/some-other-repository"
    decision = evaluate_executor_selection(
        _record(authorized_repository=foreign, current_repository=foreign)
    )
    assert decision["decision"] == EXECUTOR_SELECTION_REFUSED
    assert "AUTHORIZED_REPOSITORY_NOT_THIS_REPOSITORY" in decision["decision_reason_codes"]


def test_cross_work_unit_replay_is_refused() -> None:
    """A grant issued for one work unit must not authorize a different one, even when every
    other field of the replayed record is otherwise well-formed."""

    decision = evaluate_executor_selection(
        _record(invoked_work_unit_id="WORK-UNIT-ISSUE-102-COPILOT-TRIAL-2")
    )
    assert decision["decision"] == EXECUTOR_SELECTION_REFUSED
    assert decision["decision_reason_codes"] == ["CROSS_WORK_UNIT_REPLAY"]


def test_a_duplicate_concurrently_active_executor_is_refused() -> None:
    """Two providers simultaneously claiming to be the active executor for one work unit is
    refused -- eligibility never implies more than one selected executor at a time."""

    decision = evaluate_executor_selection(
        _record(concurrently_active_provider_for_work_unit="CLAUDE_CODE")
    )
    assert decision["decision"] == EXECUTOR_SELECTION_REFUSED
    assert decision["decision_reason_codes"] == ["DUPLICATE_ACTIVE_EXECUTOR_FOR_WORK_UNIT"]


def test_a_concurrently_active_record_naming_the_same_provider_is_not_a_duplicate() -> None:
    """A provider is not a duplicate of itself: re-evaluating the same provider's own active
    selection must not be refused as though it conflicted with itself."""

    decision = evaluate_executor_selection(
        _record(concurrently_active_provider_for_work_unit="GITHUB_COPILOT")
    )
    assert decision["decision"] == EXECUTOR_SELECTION_ADMITTED


@pytest.mark.parametrize("status", ["DRAFT", "PROPOSED", "SUPERSEDED", ""])
def test_a_non_ratified_decision_status_is_refused(status: str) -> None:
    decision = evaluate_executor_selection(_record(decision_status=status))
    assert decision["decision"] == EXECUTOR_SELECTION_REFUSED
    assert "DECISION_STATUS_NOT_RATIFIED" in decision["decision_reason_codes"]


def test_a_non_shukou_decision_authority_is_refused() -> None:
    decision = evaluate_executor_selection(_record(decision_authority="CLAUDE_CODE"))
    assert decision["decision"] == EXECUTOR_SELECTION_REFUSED
    assert "DECISION_AUTHORITY_NOT_HUMAN" in decision["decision_reason_codes"]


def test_an_unverified_read_back_receipt_is_refused_even_when_otherwise_complete() -> None:
    empty_receipt = {
        "work_unit_id": "",
        "governing_issue": "",
        "selected_executor_provider": "",
        "comment_url": "",
        "decision_authority": "",
        "decision_status": "",
    }
    decision = evaluate_executor_selection(_record(api_read_back_receipt=empty_receipt))
    assert decision["decision"] == EXECUTOR_SELECTION_REFUSED
    assert set(decision["decision_reason_codes"]) >= {
        "API_READ_BACK_RECEIPT_WORK_UNIT_ID_MISMATCH",
        "API_READ_BACK_RECEIPT_GOVERNING_ISSUE_MISMATCH",
        "API_READ_BACK_RECEIPT_SELECTED_EXECUTOR_PROVIDER_MISMATCH",
        "API_READ_BACK_RECEIPT_COMMENT_URL_MISMATCH",
        "API_READ_BACK_RECEIPT_DECISION_AUTHORITY_MISMATCH",
        "API_READ_BACK_RECEIPT_DECISION_STATUS_MISMATCH",
    }


# --------------------------------------------------------------------------- #
# every declared reason code is reachable, and nothing else escapes
# --------------------------------------------------------------------------- #

_REACHABILITY_CASES: tuple[tuple[str, dict[str, Any]], ...] = (
    (
        "UNKNOWN_EXECUTOR_PROVIDER",
        {
            "selected_executor_provider": "CODEX",
            "api_read_back_receipt": _receipt(selected_executor_provider="CODEX"),
        },
    ),
    (
        "WORK_UNIT_ID_MALFORMED",
        {
            "work_unit_id": "",
            "invoked_work_unit_id": "",
            "api_read_back_receipt": _receipt(work_unit_id=""),
        },
    ),
    (
        "GOVERNING_REFERENCE_MALFORMED",
        {"governing_issue": "", "api_read_back_receipt": _receipt(governing_issue="")},
    ),
    (
        "COMMENT_URL_NOT_A_VERIFIABLE_GITHUB_COMMENT",
        {"comment_url": "", "api_read_back_receipt": _receipt(comment_url="")},
    ),
    (
        "API_READ_BACK_RECEIPT_WORK_UNIT_ID_MISMATCH",
        {"api_read_back_receipt": _receipt(work_unit_id="WORK-UNIT-SOMETHING-ELSE")},
    ),
    (
        "API_READ_BACK_RECEIPT_GOVERNING_ISSUE_MISMATCH",
        {"api_read_back_receipt": _receipt(governing_issue="#99")},
    ),
    (
        "API_READ_BACK_RECEIPT_SELECTED_EXECUTOR_PROVIDER_MISMATCH",
        {"api_read_back_receipt": _receipt(selected_executor_provider="CLAUDE_CODE")},
    ),
    (
        "API_READ_BACK_RECEIPT_COMMENT_URL_MISMATCH",
        {
            "api_read_back_receipt": _receipt(
                comment_url="https://github.com/manosube/manosube-agent-civilization-os/issues/999#issuecomment-1"
            )
        },
    ),
    (
        "API_READ_BACK_RECEIPT_DECISION_AUTHORITY_MISMATCH",
        {"api_read_back_receipt": _receipt(decision_authority="CLAUDE_CODE")},
    ),
    (
        "API_READ_BACK_RECEIPT_DECISION_STATUS_MISMATCH",
        {"api_read_back_receipt": _receipt(decision_status="DRAFT")},
    ),
    (
        "DECISION_AUTHORITY_NOT_HUMAN",
        {
            "decision_authority": "CLAUDE_CODE",
            "api_read_back_receipt": _receipt(decision_authority="CLAUDE_CODE"),
        },
    ),
    (
        "DECISION_STATUS_NOT_RATIFIED",
        {"decision_status": "DRAFT", "api_read_back_receipt": _receipt(decision_status="DRAFT")},
    ),
    (
        "AUTHORIZED_REPOSITORY_NOT_THIS_REPOSITORY",
        {
            "authorized_repository": "manosube/some-other-repository",
            "current_repository": "manosube/some-other-repository",
        },
    ),
    ("REPOSITORY_SCOPE_MISMATCH", {"current_repository": "manosube/some-other-repository"}),
    ("BRANCH_SCOPE_MISMATCH", {"current_branch": "some-other-branch"}),
    ("AUTHORIZED_BASE_SHA_NOT_A_COMMIT_SHA", {"authorized_base_sha": "not-a-sha"}),
    ("EXPECTED_HEAD_SHA_NOT_A_COMMIT_SHA", {"expected_head_sha": "not-a-sha"}),
    ("CURRENT_BASE_SHA_NOT_A_COMMIT_SHA", {"current_base_sha": "not-a-sha"}),
    ("CURRENT_HEAD_SHA_NOT_A_COMMIT_SHA", {"current_head_sha": "not-a-sha"}),
    ("BASE_SHA_SCOPE_MISMATCH", {"current_base_sha": _SHA_B}),
    ("HEAD_SHA_STALE", {"current_head_sha": _SHA_B}),
    ("CROSS_WORK_UNIT_REPLAY", {"invoked_work_unit_id": "WORK-UNIT-SOMETHING-ELSE"}),
    (
        "DUPLICATE_ACTIVE_EXECUTOR_FOR_WORK_UNIT",
        {"concurrently_active_provider_for_work_unit": "CLAUDE_CODE"},
    ),
)


@pytest.mark.parametrize(
    "reason_code,overrides", _REACHABILITY_CASES, ids=[case[0] for case in _REACHABILITY_CASES]
)
def test_every_declared_reason_code_is_reachable(
    reason_code: str, overrides: dict[str, Any]
) -> None:
    decision = evaluate_executor_selection(_record(**overrides))
    assert decision["decision"] == EXECUTOR_SELECTION_REFUSED
    assert decision["decision_reason_codes"] == [reason_code]


def test_the_reachability_matrix_covers_every_declared_reason_code() -> None:
    covered = {reason_code for reason_code, _overrides in _REACHABILITY_CASES}
    assert covered == executor_selection_module.EMITTED_REASON_CODES


def test_every_emittable_reason_code_is_declared() -> None:
    tree = ast.parse(inspect.getsource(executor_selection_module))
    emittable: set[str] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr != "append":
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                emittable.add(arg.value)
    assert emittable == executor_selection_module.EMITTED_REASON_CODES


# --------------------------------------------------------------------------- #
# unreadable records raise, they are never silently refused or admitted
# --------------------------------------------------------------------------- #


def test_an_unknown_key_raises() -> None:
    with pytest.raises(ExecutorSelectionError, match="unknown keys"):
        evaluate_executor_selection(_record(extra_field="not part of the schema"))


@pytest.mark.parametrize("missing_key", list(_record().keys()))
def test_a_missing_required_key_raises(missing_key: str) -> None:
    record = _record()
    del record[missing_key]
    with pytest.raises(ExecutorSelectionError, match="omits required keys"):
        evaluate_executor_selection(record)


def test_a_non_object_record_raises() -> None:
    with pytest.raises(ExecutorSelectionError):
        evaluate_executor_selection("this is not even a mapping")  # type: ignore[arg-type]


def test_an_unsupported_schema_version_raises() -> None:
    with pytest.raises(ExecutorSelectionError, match="schema_version"):
        evaluate_executor_selection(_record(schema_version="99.9"))


def test_a_non_object_receipt_raises() -> None:
    with pytest.raises(ExecutorSelectionError, match="api_read_back_receipt"):
        evaluate_executor_selection(_record(api_read_back_receipt="true"))


def test_a_receipt_carrying_an_unknown_key_raises() -> None:
    with pytest.raises(ExecutorSelectionError, match="unknown keys"):
        evaluate_executor_selection(_record(api_read_back_receipt=_receipt(extra="not part")))


@pytest.mark.parametrize("missing_key", list(_receipt().keys()))
def test_a_receipt_missing_a_required_key_raises(missing_key: str) -> None:
    receipt = _receipt()
    del receipt[missing_key]
    with pytest.raises(ExecutorSelectionError, match="omits required keys"):
        evaluate_executor_selection(_record(api_read_back_receipt=receipt))


@pytest.mark.parametrize("field", list(_record().keys()))
def test_a_non_string_field_raises(field: str) -> None:
    if field in ("schema_version", "api_read_back_receipt"):
        pytest.skip("covered by the shape/version tests above")
    with pytest.raises(ExecutorSelectionError):
        evaluate_executor_selection(_record(**{field: 12345}))


# --------------------------------------------------------------------------- #
# the boundary: no network call, no token, no secret, ever
# --------------------------------------------------------------------------- #


def test_the_module_source_contains_no_network_or_credential_surface() -> None:
    source = inspect.getsource(executor_selection_module)
    forbidden = (
        "requests",
        "urllib",
        "httpx",
        "socket",
        "http.client",
        "GITHUB_TOKEN",
        "token=",
        "Authorization",
        "os.environ",
        "getenv",
    )
    for term in forbidden:
        assert term not in source, term


def test_the_module_imports_nothing_beyond_the_standard_library_and_its_own_policy() -> None:
    tree = ast.parse(inspect.getsource(executor_selection_module))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    assert modules <= {"__future__", "copy", "re", "typing", "errors", "policy"}


def test_evaluate_executor_selection_never_writes_a_file() -> None:
    tree = ast.parse(inspect.getsource(executor_selection_module))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            assert name not in ("open", "write_text", "write_bytes")
