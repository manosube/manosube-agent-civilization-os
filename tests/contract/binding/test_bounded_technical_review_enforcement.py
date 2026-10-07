"""Decision 0004 (Issue #109): CODEX is a bounded, non-default-active technical reviewer --
never an implementer, never a structural reviewer, never an acceptance or merge authority.
This proves the mechanical admission chain for the one action its capability may ever
perform: an absent, malformed, expired, revoked, or scope-mismatched Bounded Review Grant is
refused by :mod:`.review_selection`; the durable operational ledger and activation/spending
gate :mod:`.review_control` owns are proven separately against every one of their own declared
reason codes; and the ratified numeric ceiling and native-trigger prohibition this decision
must never weaken are pinned exactly, the same discipline every other ratified value in this
package already receives.

Following `test_executor_selection_enforcement.py`'s own convention (Decision 0003's
equivalent proof for `executor_selection`): every fixture below is a syntactically well-shaped
but explicitly synthetic comment URL/identifier; none asserts to be, or is compared against,
any actual GitHub record. Matching the URL pattern is a shape check, not proof of authorship
or existence (`review_selection`'s own module docstring states this limit explicitly).
"""

from __future__ import annotations

import ast
from copy import deepcopy
import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from manosube_agent_civilization.development_binding import (
    ReviewSelectionError,
    review_control as review_control_module,
    review_selection as review_selection_module,
)
from manosube_agent_civilization.development_binding.policy import (
    BOUNDED_REVIEW_NUMERIC_LIMITS,
    POLICY_PATH,
    load_policy,
)
from manosube_agent_civilization.development_binding.review_control import (
    ACTIVATION_GATE_ACTIVATED,
    ACTIVATION_GATE_NOT_ACTIVATED,
    evaluate_activation_gate,
)
from manosube_agent_civilization.development_binding.review_selection import (
    NATIVE_REVIEW_NOT_RELEVANT,
    NATIVE_REVIEW_RELEVANT,
    RECEIPT_KEYS,
    REVIEW_SELECTION_ADMITTED,
    REVIEW_SELECTION_REFUSED,
    SUPPORTED_ENVIRONMENT_FINGERPRINT,
    evaluate_native_review_relevance,
    evaluate_review_selection,
)

pytestmark = pytest.mark.contract

_SYNTHETIC_COMMENT_URL = (
    "https://github.com/manosube/manosube-agent-civilization-os/issues/109#issuecomment-1000000109"
)
_SHA_A = "a1b2c3d4e5f60718293a4b5c6d7e8f9011223344"
_SHA_B = "b2c3d4e5f60718293a4b5c6d7e8f901122334455"
_WORK_UNIT_ID = "WORK-UNIT-ISSUE-109-BOUNDED-REVIEW-ENFORCEMENT-1"
_DIFFERENCE_ID = "D-BOUNDED-TECHNICAL-REVIEW-ENFORCEMENT"
_ADOPTION_ID = "ADOPT_I109_ENFORCEMENT_TEST_1"
_REPOSITORY = "manosube/manosube-agent-civilization-os"
_PULL_REQUEST = "#109"
_REQUIREMENT_ID = "REQ-I109-ENFORCEMENT-1"
_NOW = "2026-10-06T12:00:00Z"


def _receipt(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "work_unit_id": _WORK_UNIT_ID,
        "difference_id": _DIFFERENCE_ID,
        "governing_issue": "#109",
        "adoption_id": _ADOPTION_ID,
        "comment_url": _SYNTHETIC_COMMENT_URL,
        "decision_authority": "SHUKOU",
        "decision_status": "RATIFIED",
        "authorized_repository": _REPOSITORY,
        "authorized_pull_request": _PULL_REQUEST,
        "authorized_base_sha": _SHA_A,
        "authorized_head_sha": _SHA_A,
        "requirement_id": _REQUIREMENT_ID,
        "implementation_provider": "CLAUDE_CODE",
        "implementation_session_ref": "session-enforcement-1",
        "inspector_provider": "CODEX",
        "inspector_session_ref": "codex-session-enforcement-1",
        "permitted_paths": ["tests/contract/binding/test_bounded_technical_review_enforcement.py"],
        "permitted_checks": ["CORRECTNESS"],
        "environment_fingerprint": dict(SUPPORTED_ENVIRONMENT_FINGERPRINT),
        "input_digest": "a" * 64,
        "not_before": "2026-10-06T00:00:00Z",
        "not_after": "2026-10-07T00:00:00Z",
    }
    base.update(overrides)
    return base


def _record(**overrides: Any) -> dict[str, Any]:
    receipt = _receipt()
    base: dict[str, Any] = {
        "schema_version": "0.1",
        "work_unit_id": _WORK_UNIT_ID,
        "invoked_work_unit_id": _WORK_UNIT_ID,
        "difference_id": _DIFFERENCE_ID,
        "governing_issue": "#109",
        "adoption_id": _ADOPTION_ID,
        "comment_url": _SYNTHETIC_COMMENT_URL,
        "decision_authority": "SHUKOU",
        "decision_status": "RATIFIED",
        "api_read_back_receipt": receipt,
        "authorized_repository": _REPOSITORY,
        "authorized_pull_request": _PULL_REQUEST,
        "authorized_base_sha": _SHA_A,
        "authorized_head_sha": _SHA_A,
        "requirement_id": _REQUIREMENT_ID,
        "implementation_provider": "CLAUDE_CODE",
        "implementation_session_ref": "session-enforcement-1",
        "inspector_provider": "CODEX",
        "inspector_session_ref": "codex-session-enforcement-1",
        "permitted_paths": ["tests/contract/binding/test_bounded_technical_review_enforcement.py"],
        "permitted_checks": ["CORRECTNESS"],
        "environment_fingerprint": dict(SUPPORTED_ENVIRONMENT_FINGERPRINT),
        "input_digest": "a" * 64,
        "not_before": "2026-10-06T00:00:00Z",
        "not_after": "2026-10-07T00:00:00Z",
        "current_repository": _REPOSITORY,
        "current_pull_request": _PULL_REQUEST,
        "current_base_sha": _SHA_A,
        "current_head_sha": _SHA_A,
        "revoked": False,
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------- #
# the positive route
# --------------------------------------------------------------------------- #


def test_a_complete_internally_consistent_grant_is_admitted() -> None:
    decision = evaluate_review_selection(_record(), now=_NOW)
    assert decision["decision"] == REVIEW_SELECTION_ADMITTED
    assert decision["decision_reason_codes"] == []


# --------------------------------------------------------------------------- #
# the hand-named reachability matrix -- one crafted record per declared code
# --------------------------------------------------------------------------- #

_REACHABILITY_CASES: tuple[tuple[str, dict[str, Any]], ...] = (
    (
        "WORK_UNIT_ID_MALFORMED",
        {
            "work_unit_id": "not-a-work-unit",
            "invoked_work_unit_id": "not-a-work-unit",
            "api_read_back_receipt": _receipt(work_unit_id="not-a-work-unit"),
        },
    ),
    (
        "DIFFERENCE_ID_MALFORMED",
        {
            "difference_id": "not-a-difference",
            "api_read_back_receipt": _receipt(difference_id="not-a-difference"),
        },
    ),
    (
        "GOVERNING_REFERENCE_MALFORMED",
        {"governing_issue": "109", "api_read_back_receipt": _receipt(governing_issue="109")},
    ),
    (
        "ADOPTION_ID_MALFORMED",
        {
            "adoption_id": "not-adopted",
            "api_read_back_receipt": _receipt(adoption_id="not-adopted"),
        },
    ),
    (
        "COMMENT_URL_NOT_A_VERIFIABLE_GITHUB_COMMENT",
        {
            "comment_url": "https://example.com/not-github",
            "api_read_back_receipt": _receipt(comment_url="https://example.com/not-github"),
        },
    ),
    (
        "AUTHORIZED_PULL_REQUEST_MALFORMED",
        {
            "authorized_pull_request": "109",
            "api_read_back_receipt": _receipt(authorized_pull_request="109"),
            "current_pull_request": "109",
        },
    ),
    (
        "REQUIREMENT_ID_MALFORMED",
        {
            "requirement_id": "req-lowercase",
            "api_read_back_receipt": _receipt(requirement_id="req-lowercase"),
        },
    ),
    (
        "IMPLEMENTATION_SESSION_REF_MALFORMED",
        {
            "implementation_session_ref": "",
            "api_read_back_receipt": _receipt(implementation_session_ref=""),
        },
    ),
    (
        "INSPECTOR_SESSION_REF_MALFORMED",
        {"inspector_session_ref": "", "api_read_back_receipt": _receipt(inspector_session_ref="")},
    ),
    (
        "INPUT_DIGEST_MALFORMED",
        {"input_digest": "not-hex", "api_read_back_receipt": _receipt(input_digest="not-hex")},
    ),
    (
        "PERMITTED_PATHS_MALFORMED",
        {
            "permitted_paths": ["../outside.py"],
            "api_read_back_receipt": _receipt(permitted_paths=["../outside.py"]),
        },
    ),
    (
        "PERMITTED_CHECKS_OUTSIDE_RATIFIED_CATEGORIES",
        {
            "permitted_checks": ["NOT_A_RATIFIED_CATEGORY"],
            "api_read_back_receipt": _receipt(permitted_checks=["NOT_A_RATIFIED_CATEGORY"]),
        },
    ),
    (
        "UNKNOWN_IMPLEMENTATION_PROVIDER",
        {
            "implementation_provider": "CODEX",
            "api_read_back_receipt": _receipt(implementation_provider="CODEX"),
        },
    ),
    (
        "INSPECTOR_PROVIDER_NOT_THE_RATIFIED_REVIEWER",
        {
            "inspector_provider": "CLAUDE_CODE",
            "api_read_back_receipt": _receipt(inspector_provider="CLAUDE_CODE"),
        },
    ),
    (
        "ENVIRONMENT_FINGERPRINT_UNSUPPORTED",
        {
            "environment_fingerprint": {
                **SUPPORTED_ENVIRONMENT_FINGERPRINT,
                "model": "a-different-model",
            },
            "api_read_back_receipt": _receipt(
                environment_fingerprint={
                    **SUPPORTED_ENVIRONMENT_FINGERPRINT,
                    "model": "a-different-model",
                }
            ),
        },
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
            "authorized_repository": "someone/else",
            "api_read_back_receipt": _receipt(authorized_repository="someone/else"),
            "current_repository": "someone/else",
        },
    ),
    ("REPOSITORY_SCOPE_MISMATCH", {"current_repository": "someone/else"}),
    ("PULL_REQUEST_SCOPE_MISMATCH", {"current_pull_request": "#999"}),
    (
        "AUTHORIZED_BASE_SHA_NOT_A_COMMIT_SHA",
        {
            "authorized_base_sha": "not-a-sha",
            "api_read_back_receipt": _receipt(authorized_base_sha="not-a-sha"),
        },
    ),
    (
        "AUTHORIZED_HEAD_SHA_NOT_A_COMMIT_SHA",
        {
            "authorized_head_sha": "not-a-sha",
            "api_read_back_receipt": _receipt(authorized_head_sha="not-a-sha"),
        },
    ),
    ("CURRENT_BASE_SHA_NOT_A_COMMIT_SHA", {"current_base_sha": "not-a-sha"}),
    ("CURRENT_HEAD_SHA_NOT_A_COMMIT_SHA", {"current_head_sha": "not-a-sha"}),
    ("BASE_SHA_SCOPE_MISMATCH", {"current_base_sha": _SHA_B}),
    ("HEAD_SHA_STALE", {"current_head_sha": _SHA_B}),
    ("CROSS_WORK_UNIT_REPLAY", {"invoked_work_unit_id": "WORK-UNIT-SOMETHING-ELSE"}),
    ("REVIEW_GRANT_REVOKED", {"revoked": True}),
    (
        "REVIEW_GRANT_WINDOW_INVERTED",
        {
            "not_before": "2026-10-07T00:00:00Z",
            "not_after": "2026-10-06T00:00:00Z",
            "api_read_back_receipt": _receipt(
                not_before="2026-10-07T00:00:00Z", not_after="2026-10-06T00:00:00Z"
            ),
        },
    ),
    (
        "REVIEW_GRANT_NOT_YET_VALID",
        {
            "not_before": "2026-10-07T00:00:00Z",
            "api_read_back_receipt": _receipt(not_before="2026-10-07T00:00:00Z"),
        },
    ),
    (
        "REVIEW_GRANT_EXPIRED",
        {
            "not_before": "2026-10-04T00:00:00Z",
            "not_after": "2026-10-05T00:00:00Z",
            "api_read_back_receipt": _receipt(
                not_before="2026-10-04T00:00:00Z", not_after="2026-10-05T00:00:00Z"
            ),
        },
    ),
)


@pytest.mark.parametrize(
    "reason_code,overrides", _REACHABILITY_CASES, ids=[case[0] for case in _REACHABILITY_CASES]
)
def test_every_hand_named_reason_code_is_reachable(
    reason_code: str, overrides: dict[str, Any]
) -> None:
    decision = evaluate_review_selection(_record(**overrides), now=_NOW)
    assert decision["decision"] == REVIEW_SELECTION_REFUSED
    assert reason_code in decision["decision_reason_codes"]


# --------------------------------------------------------------------------- #
# REUSE_NATIVE_ONLY supplement (Issue #109 comment 6019865174): the identical bidirectional
# reachability proof, for this module's second evaluator.
# --------------------------------------------------------------------------- #

_NATIVE_GRANT = _record(permitted_paths=["reviewed/native_sample.py"])


def _native_evidence(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema_version": "0.1",
        "provider": "CODEX",
        "repository": _REPOSITORY,
        "pull_request": _PULL_REQUEST,
        "review_id": "6030487245",
        "reviewed_commit_sha": _SHA_A,
        "inspected_base_sha": _SHA_A,
        "review_state": "APPROVED",
        "submitted_at": "2026-10-06T10:30:00Z",
        "inspected_paths": ["reviewed/native_sample.py"],
        "findings": [],
        "fetched_via": "github_mcp_pull_request_read",
    }
    base.update(overrides)
    return base


_NATIVE_RELEVANCE_REACHABILITY_CASES: tuple[tuple[str, dict[str, Any]], ...] = (
    ("NATIVE_REPOSITORY_MISMATCH", {"repository": "someone/else"}),
    ("NATIVE_PULL_REQUEST_MISMATCH", {"pull_request": "#999"}),
    ("NATIVE_REVIEWED_BASE_UNKNOWN", {"reviewed_commit_sha": None}),
    ("NATIVE_REVIEWED_BASE_STALE", {"reviewed_commit_sha": _SHA_B}),
    ("NATIVE_INSPECTED_BASE_UNKNOWN", {"inspected_base_sha": None}),
    ("NATIVE_INSPECTED_BASE_STALE", {"inspected_base_sha": _SHA_B}),
    ("NATIVE_COVERAGE_INSUFFICIENT_FOR_GRANT_SCOPE", {"inspected_paths": []}),
)


def test_a_fully_relevant_native_review_is_admitted() -> None:
    decision = evaluate_native_review_relevance(_native_evidence(), grant=_NATIVE_GRANT)
    assert decision == {"decision": NATIVE_REVIEW_RELEVANT, "decision_reason_codes": []}


@pytest.mark.parametrize(
    "reason_code,overrides",
    _NATIVE_RELEVANCE_REACHABILITY_CASES,
    ids=[case[0] for case in _NATIVE_RELEVANCE_REACHABILITY_CASES],
)
def test_every_hand_named_native_relevance_reason_code_is_reachable(
    reason_code: str, overrides: dict[str, Any]
) -> None:
    decision = evaluate_native_review_relevance(_native_evidence(**overrides), grant=_NATIVE_GRANT)
    assert decision["decision"] == NATIVE_REVIEW_NOT_RELEVANT
    assert reason_code in decision["decision_reason_codes"]


def test_the_reachability_matrix_covers_every_hand_named_declared_code() -> None:
    covered = {reason_code for reason_code, _overrides in _REACHABILITY_CASES}
    covered |= {reason_code for reason_code, _overrides in _NATIVE_RELEVANCE_REACHABILITY_CASES}
    assert covered == review_selection_module.EMITTED_REASON_CODES


def test_every_hand_named_emittable_reason_code_is_declared() -> None:
    """Direction two, for the hand-written half of this module's own reason-code surface --
    the receipt-mismatch half is generated, and proven separately below by construction.

    This module now hosts two evaluators (:func:`evaluate_review_selection` and, since the
    REUSE_NATIVE_ONLY supplement, :func:`evaluate_native_review_relevance`), sharing this one
    module-wide :data:`EMITTED_REASON_CODES` set -- the convention ``test_active_document_
    terminal_state.py``'s own generic, package-wide bidirectional proof already binds to the
    name ``EMITTED_REASON_CODES`` per module, not per evaluator inside it.
    """

    tree = ast.parse(inspect.getsource(review_selection_module))
    emittable: set[str] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr != "append":
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                emittable.add(arg.value)
    assert emittable == review_selection_module.EMITTED_REASON_CODES


# --------------------------------------------------------------------------- #
# the generated receipt-mismatch half -- one crafted record per RECEIPT_KEYS field
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("field", sorted(RECEIPT_KEYS))
def test_every_receipt_field_mismatch_is_reachable(field: str) -> None:
    record = _record()
    receipt = dict(record["api_read_back_receipt"])
    # A value that disagrees with the declared field, of a type that still passes every
    # upstream shape check for *that* field (so the mismatch, not a shape refusal, is what
    # fires) -- achieved generically by appending a marker to the declared value's own repr
    # where that stays a legal value, or substituting a structurally distinct same-shaped
    # alternative otherwise.
    declared = record[field]
    if isinstance(declared, str):
        receipt[field] = declared + "-DIVERGED"
    elif isinstance(declared, list):
        receipt[field] = (
            [*declared, "DIVERGED-EXTRA-ENTRY"] if field != "permitted_checks" else ["SECURITY"]
        )
    elif isinstance(declared, dict):
        receipt[field] = {**declared, "cli_version": declared.get("cli_version", "") + "-DIVERGED"}
    else:  # pragma: no cover -- RECEIPT_KEYS carries no other type today
        pytest.fail(f"unexpected declared value type for {field!r}: {type(declared)!r}")
    record["api_read_back_receipt"] = receipt
    decision = evaluate_review_selection(record, now=_NOW)
    assert decision["decision"] == REVIEW_SELECTION_REFUSED
    expected_code = f"API_READ_BACK_RECEIPT_{field.upper()}_MISMATCH"
    assert expected_code in decision["decision_reason_codes"], decision


def test_the_generated_receipt_mismatch_codes_are_exactly_the_receipt_keys() -> None:
    expected = {f"API_READ_BACK_RECEIPT_{field.upper()}_MISMATCH" for field in RECEIPT_KEYS}
    assert expected == review_selection_module.EMITTED_RECEIPT_MISMATCH_REASON_CODES


# --------------------------------------------------------------------------- #
# unreadable records raise; they are never silently refused or admitted
# --------------------------------------------------------------------------- #


def test_an_unknown_key_raises() -> None:
    with pytest.raises(ReviewSelectionError, match="unknown keys"):
        evaluate_review_selection(_record(extra_field="not part of the schema"), now=_NOW)


def test_a_missing_key_raises() -> None:
    record = _record()
    del record["revoked"]
    with pytest.raises(ReviewSelectionError, match="omits required keys"):
        evaluate_review_selection(record, now=_NOW)


def test_a_non_object_record_raises() -> None:
    with pytest.raises(ReviewSelectionError):
        evaluate_review_selection("not even a mapping", now=_NOW)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad_now", ["not-a-timestamp", "", "2026-13-45T99:99:99Z"])
def test_an_unparseable_now_raises(bad_now: str) -> None:
    with pytest.raises(ReviewSelectionError):
        evaluate_review_selection(_record(), now=bad_now)


# --------------------------------------------------------------------------- #
# review_control's own declared reason-code surface, proven the identical way
# --------------------------------------------------------------------------- #


def test_every_review_control_emittable_reason_code_is_declared() -> None:
    tree = ast.parse(inspect.getsource(review_control_module))
    emittable: set[str] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr != "append":
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                emittable.add(arg.value)
    assert emittable == review_control_module.EMITTED_REASON_CODES


# --------------------------------------------------------------------------- #
# the ratified numeric ceiling is pinned exactly -- never redeclared by a grant, never
# independently settable from the JSON artifact
# --------------------------------------------------------------------------- #


def test_the_json_artifact_numeric_limits_match_the_ratified_code_constant() -> None:
    document = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    assert document["bounded_review_numeric_limits"] == BOUNDED_REVIEW_NUMERIC_LIMITS


def test_the_ratified_numeric_limits_match_the_handoff_exactly() -> None:
    """Issue #109 handoff, comment 6017544351, §4 -- transcribed once, here, as a literal
    control against the ratified constant every other owner reads."""

    assert BOUNDED_REVIEW_NUMERIC_LIMITS == {
        "max_concurrent_reviews_per_repository": 1,
        "max_launches_per_jst_day": 4,
        "max_process_seconds": 1800,
        "max_poll_window_seconds": 28800,
        "poll_interval_seconds": 60,
        "max_input_bytes": 1048576,
        "max_result_bytes": 1048576,
        "automatic_retries_allowed": 0,
    }


@pytest.mark.parametrize(
    "mutated_field,mutated_value",
    [
        ("max_concurrent_reviews_per_repository", 2),
        ("max_launches_per_jst_day", 5),
        ("max_process_seconds", 1801),
        ("max_poll_window_seconds", 28801),
        ("poll_interval_seconds", 61),
        ("max_input_bytes", 1048577),
        ("max_result_bytes", 1048577),
        ("automatic_retries_allowed", 1),
    ],
)
def test_a_widened_numeric_limit_in_the_json_artifact_is_refused(
    tmp_path: Path, mutated_field: str, mutated_value: int
) -> None:
    document = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    document["bounded_review_numeric_limits"] = {
        **document["bounded_review_numeric_limits"],
        mutated_field: mutated_value,
    }
    target = tmp_path / "policy.json"
    target.write_text(json.dumps(document), encoding="utf-8")
    from manosube_agent_civilization.development_binding.errors import PolicyIntegrityError

    with pytest.raises(PolicyIntegrityError):
        load_policy(target)


def test_activation_default_edited_to_true_is_refused(tmp_path: Path) -> None:
    document = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    document["bounded_review_activation_default"] = True
    target = tmp_path / "policy.json"
    target.write_text(json.dumps(document), encoding="utf-8")
    from manosube_agent_civilization.development_binding.errors import PolicyIntegrityError

    with pytest.raises(PolicyIntegrityError):
        load_policy(target)


# --------------------------------------------------------------------------- #
# the native/unconditional trigger prohibition is untouched by this decision
# --------------------------------------------------------------------------- #


def test_automated_review_trigger_allowed_is_still_false() -> None:
    assert load_policy()["automated_review_trigger_allowed"] is False


def test_the_prohibited_trigger_list_was_not_shrunk_by_this_decision() -> None:
    """Decision 0004 opens exactly one new, narrowly-grant-gated action
    (``BOUNDED_TECHNICAL_REVIEW``) -- it must never do so by quietly removing one of the
    unconditional triggers Decision 0002 already prohibited."""

    triggers = set(load_policy()["prohibited_automated_review_triggers"])
    assert {
        "@codex review",
        "@codex security review",
        "@codex",
        "request_copilot_review",
    } <= triggers


# --------------------------------------------------------------------------- #
# the activation gate, exercised directly against its own declared reason-code surface
# --------------------------------------------------------------------------- #


def _full_activation_evidence(**overrides: Any) -> dict[str, Any]:
    base = {
        "auth_confirmed": True,
        "cli_version": SUPPORTED_ENVIRONMENT_FINGERPRINT["cli_version"],
        "model": SUPPORTED_ENVIRONMENT_FINGERPRINT["model"],
        "allowance_confirmed_adequate": True,
        "auto_recharge_verified_disabled": True,
        "native_github_dedup_disposition": "DISABLED",
        "live_bounded_review_grant_admitted": True,
        "activation_enabled": True,
    }
    base.update(overrides)
    return base


def test_fully_satisfied_evidence_activates() -> None:
    decision = evaluate_activation_gate(_full_activation_evidence())
    assert decision == {"decision": ACTIVATION_GATE_ACTIVATED, "reason_codes": []}


@pytest.mark.parametrize(
    "field,bad_value,expected_code",
    [
        ("auth_confirmed", False, "AUTH_NOT_CONFIRMED"),
        ("auth_confirmed", "yes", "AUTH_NOT_CONFIRMED"),
        ("cli_version", "0.0.0", "CLI_VERSION_UNSUPPORTED"),
        ("model", "a-different-model", "MODEL_UNSUPPORTED"),
        ("allowance_confirmed_adequate", False, "ALLOWANCE_NOT_CONFIRMED_ADEQUATE"),
        ("auto_recharge_verified_disabled", False, "AUTO_RECHARGE_NOT_VERIFIED_DISABLED"),
        ("auto_recharge_verified_disabled", "unverified", "AUTO_RECHARGE_NOT_VERIFIED_DISABLED"),
        (
            "native_github_dedup_disposition",
            "UNRESOLVED",
            "NATIVE_GITHUB_DEDUP_DISPOSITION_UNRESOLVED",
        ),
        (
            "native_github_dedup_disposition",
            "ENABLED",
            "NATIVE_GITHUB_DEDUP_DISPOSITION_UNRESOLVED",
        ),
        ("live_bounded_review_grant_admitted", False, "LIVE_BOUNDED_REVIEW_GRANT_NOT_ADMITTED"),
        ("activation_enabled", False, "ACTIVATION_NOT_ENABLED"),
    ],
)
def test_any_single_missing_precondition_refuses_activation(
    field: str, bad_value: Any, expected_code: str
) -> None:
    evidence = _full_activation_evidence(**{field: bad_value})
    decision = evaluate_activation_gate(evidence)
    assert decision["decision"] == ACTIVATION_GATE_NOT_ACTIVATED
    assert expected_code in decision["reason_codes"]


def test_an_absent_field_is_never_defaulted_to_pass() -> None:
    evidence = _full_activation_evidence()
    del evidence["auto_recharge_verified_disabled"]
    decision = evaluate_activation_gate(evidence)
    assert decision["decision"] == ACTIVATION_GATE_NOT_ACTIVATED
    assert "ACTIVATION_EVIDENCE_OMITS_REQUIRED_KEYS" in decision["reason_codes"]


def test_an_unreadable_evidence_mapping_is_refused_not_raised() -> None:
    decision = evaluate_activation_gate("not even a mapping")  # type: ignore[arg-type]
    assert decision == {
        "decision": ACTIVATION_GATE_NOT_ACTIVATED,
        "reason_codes": ["ACTIVATION_EVIDENCE_UNREADABLE"],
    }


def test_deepcopy_of_a_record_never_shares_mutable_state_with_a_fixture() -> None:
    """A guard on the test fixtures themselves: `_record()`/`_receipt()` must build fresh
    dicts every call, or one reachability case's mutation could leak into another's."""

    first = _record()
    second = _record()
    assert first is not second
    assert first["api_read_back_receipt"] is not second["api_read_back_receipt"]
    mutated = deepcopy(first)
    mutated["permitted_paths"].append("tests/unrelated.py")
    assert mutated["permitted_paths"] != first["permitted_paths"]
