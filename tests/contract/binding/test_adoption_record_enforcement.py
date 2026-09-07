"""Issue #53 (`ADOPT_GOVERNANCE_ADOPTION_RECORD_ENFORCEMENT`): only a SHUKOU semantic
decision that the Structural Advisor has recorded on GitHub, read back through the API, and
identified by its immutable comment URL, may become implementation authority for Claude
Code. This proves the mechanical check for that rule -- the four required negative cases
(a chat draft, unposted text, a reviewed-SHA mismatch, an unverified URL), the required
positive case, and that the module never performs the network call it is not allowed to
perform.

See `03_BINDING/GOVERNANCE_ADOPTION_RECORD_ENFORCEMENT.md` for the operating guide this
suite proves.
"""

from __future__ import annotations

import ast
from copy import deepcopy
import inspect
from typing import Any

import pytest

from manosube_agent_civilization.development_binding import (
    ADOPTION_RECORD_ADMITTED,
    ADOPTION_RECORD_REFUSED,
    AdoptionRecordError,
    adoption_record as adoption_record_module,
    evaluate_adoption_record,
)

pytestmark = pytest.mark.contract

_REAL_COMMENT_URL = (
    "https://github.com/manosube/manosube-agent-civilization-os/issues/53#issuecomment-5565102236"
)
_SHA_A = "2a81f782bfaccd72f1e27bbe3378bd5cd3f2e9c5"
_SHA_B = "070c1fa88f7eebce77b38d3ed026f23e500a6e4f"


def _record(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema_version": "0.1",
        "adoption_id": "ADOPT_GOVERNANCE_ADOPTION_RECORD_ENFORCEMENT",
        "governing_issue": "#53",
        "comment_url": _REAL_COMMENT_URL,
        "decision_authority": "SHUKOU",
        "decision_status": "RATIFIED",
        "api_read_back_confirmed": True,
        "reviewed_sha": _SHA_A,
        "authorized_target_sha": _SHA_A,
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------- #
# the required positive case
# --------------------------------------------------------------------------- #


def test_a_complete_verified_adoption_url_with_matching_reviewed_sha_is_admitted() -> None:
    decision = evaluate_adoption_record(_record())
    assert decision["decision"] == ADOPTION_RECORD_ADMITTED
    assert decision["decision_reason_codes"] == []
    assert decision["comment_url"] == _REAL_COMMENT_URL


def test_the_decision_is_deterministic_and_the_input_is_never_mutated() -> None:
    record = _record()
    before = deepcopy(record)
    first = evaluate_adoption_record(record)
    second = evaluate_adoption_record(deepcopy(record))
    assert record == before
    assert first == second


# --------------------------------------------------------------------------- #
# the four required negative cases
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "chat_draft_url",
    [
        "SHUKOU said in chat: implement the governance enforcement",
        "the adoption is whatever we discussed just now",
        "(no URL -- SHUKOU approved this verbally)",
    ],
)
def test_a_chat_draft_is_refused(chat_draft_url: str) -> None:
    decision = evaluate_adoption_record(
        _record(comment_url=chat_draft_url, api_read_back_confirmed=False)
    )
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert "COMMENT_URL_NOT_A_VERIFIABLE_GITHUB_COMMENT" in decision["decision_reason_codes"]


@pytest.mark.parametrize(
    "unposted_url",
    [
        "",
        "https://github.com/manosube/manosube-agent-civilization-os/issues/53",
        "https://github.com/manosube/manosube-agent-civilization-os/issues/53#discussion",
    ],
)
def test_unposted_text_is_refused(unposted_url: str) -> None:
    """An Issue/PR URL with no `#issuecomment-<id>` fragment names a whole, editable,
    ever-changing body -- never one individually addressable, immutable comment."""

    decision = evaluate_adoption_record(
        _record(comment_url=unposted_url, api_read_back_confirmed=False)
    )
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert "COMMENT_URL_NOT_A_VERIFIABLE_GITHUB_COMMENT" in decision["decision_reason_codes"]


def test_a_reviewed_sha_mismatch_is_refused() -> None:
    decision = evaluate_adoption_record(_record(authorized_target_sha=_SHA_B))
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert decision["decision_reason_codes"] == ["REVIEWED_SHA_DOES_NOT_MATCH_AUTHORIZED_TARGET"]


def test_an_unverified_url_is_refused_even_when_otherwise_complete() -> None:
    """A syntactically real, individually addressable comment URL is not enough on its
    own -- the caller must also claim the API read-back that confirms it actually
    happened."""

    decision = evaluate_adoption_record(_record(api_read_back_confirmed=False))
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert decision["decision_reason_codes"] == ["API_READ_BACK_NOT_CONFIRMED"]


# --------------------------------------------------------------------------- #
# every other individual admission condition, proven directly
# --------------------------------------------------------------------------- #


def test_a_non_shukou_decision_authority_is_refused() -> None:
    decision = evaluate_adoption_record(_record(decision_authority="CHATGPT"))
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert "DECISION_AUTHORITY_NOT_HUMAN" in decision["decision_reason_codes"]


@pytest.mark.parametrize("status", ["DRAFT", "PROPOSED", "SUPERSEDED", ""])
def test_a_non_ratified_decision_status_is_refused(status: str) -> None:
    decision = evaluate_adoption_record(_record(decision_status=status))
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert "DECISION_STATUS_NOT_RATIFIED" in decision["decision_reason_codes"]


@pytest.mark.parametrize(
    "bad_sha", ["", "not-a-sha", "abc123", "g" * 40, _SHA_A + "x", _SHA_A[:-1]]
)
def test_a_malformed_reviewed_sha_is_refused(bad_sha: str) -> None:
    decision = evaluate_adoption_record(_record(reviewed_sha=bad_sha))
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert "REVIEWED_SHA_NOT_A_COMMIT_SHA" in decision["decision_reason_codes"]


# --------------------------------------------------------------------------- #
# GAR-R1-F1 (Issue #53 comment 5565302174): bind adoption_id and governing_issue
# to the individually-addressable comment context they claim to authorize.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "bad_adoption_id",
    ["", "not shaped like an adoption id", "adopt_lowercase_is_wrong", "ADOPTION_MISSING_PREFIX"],
)
def test_a_malformed_adoption_id_is_refused(bad_adoption_id: str) -> None:
    decision = evaluate_adoption_record(_record(adoption_id=bad_adoption_id))
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert "ADOPTION_ID_MALFORMED" in decision["decision_reason_codes"]


@pytest.mark.parametrize("bad_reference", ["", "53", "Issue 53", "#", "# 53", "issue-53"])
def test_a_malformed_governing_reference_is_refused(bad_reference: str) -> None:
    decision = evaluate_adoption_record(_record(governing_issue=bad_reference))
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert "GOVERNING_REFERENCE_MALFORMED" in decision["decision_reason_codes"]


def test_a_governing_reference_naming_a_different_issue_than_the_comment_url_is_refused() -> None:
    """A syntactically real, individually addressable comment URL under Issue #53 must not
    be relabeled as authority for a different governing Issue or Pull Request."""

    decision = evaluate_adoption_record(_record(governing_issue="#54"))
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert decision["decision_reason_codes"] == ["GOVERNING_REFERENCE_NOT_BOUND_TO_COMMENT_CONTEXT"]


def test_a_governing_reference_naming_the_comment_urls_own_issue_is_not_a_binding_failure() -> None:
    decision = evaluate_adoption_record(_record(governing_issue="#53"))
    assert (
        "GOVERNING_REFERENCE_NOT_BOUND_TO_COMMENT_CONTEXT" not in decision["decision_reason_codes"]
    )


def test_the_binding_check_is_not_compounded_onto_an_already_malformed_url_or_reference() -> None:
    """The binding check runs only once both halves are independently well-formed -- a
    malformed URL or reference is reported once by its own check, not doubled."""

    malformed_url = evaluate_adoption_record(_record(comment_url=""))
    assert (
        "GOVERNING_REFERENCE_NOT_BOUND_TO_COMMENT_CONTEXT"
        not in malformed_url["decision_reason_codes"]
    )

    malformed_reference = evaluate_adoption_record(_record(governing_issue=""))
    assert (
        "GOVERNING_REFERENCE_NOT_BOUND_TO_COMMENT_CONTEXT"
        not in malformed_reference["decision_reason_codes"]
    )


def test_a_pull_request_governing_reference_binds_against_a_pull_request_comment_url() -> None:
    """The binding is symmetric across Issue and Pull Request comment URLs -- only the
    number in the URL's own path is what ``governing_issue`` must match."""

    pr_url = "https://github.com/manosube/manosube-agent-civilization-os/pull/56#issuecomment-1"
    decision = evaluate_adoption_record(
        _record(comment_url=pr_url, governing_issue="#56", api_read_back_confirmed=True)
    )
    assert (
        "GOVERNING_REFERENCE_NOT_BOUND_TO_COMMENT_CONTEXT" not in decision["decision_reason_codes"]
    )


# --------------------------------------------------------------------------- #
# GAR-R1: every declared reason code is actually reachable
# --------------------------------------------------------------------------- #
#
# One crafted record per reason code, isolated so it is the *only* failure -- proving the
# allowlist a route-drift guard elsewhere in this suite trusts is neither wider nor narrower
# than what this evaluator can actually emit.

_REACHABILITY_CASES: tuple[tuple[str, dict[str, Any]], ...] = (
    (
        "COMMENT_URL_NOT_A_VERIFIABLE_GITHUB_COMMENT",
        {"comment_url": "", "api_read_back_confirmed": False},
    ),
    ("API_READ_BACK_NOT_CONFIRMED", {"api_read_back_confirmed": False}),
    ("ADOPTION_ID_MALFORMED", {"adoption_id": ""}),
    ("GOVERNING_REFERENCE_MALFORMED", {"governing_issue": ""}),
    ("GOVERNING_REFERENCE_NOT_BOUND_TO_COMMENT_CONTEXT", {"governing_issue": "#54"}),
    ("DECISION_AUTHORITY_NOT_HUMAN", {"decision_authority": "CHATGPT"}),
    ("DECISION_STATUS_NOT_RATIFIED", {"decision_status": "DRAFT"}),
    (
        "REVIEWED_SHA_NOT_A_COMMIT_SHA",
        {"reviewed_sha": "not-a-sha", "authorized_target_sha": "not-a-sha"},
    ),
    (
        "AUTHORIZED_TARGET_SHA_NOT_A_COMMIT_SHA",
        {"reviewed_sha": "not-a-sha", "authorized_target_sha": "not-a-sha"},
    ),
    ("REVIEWED_SHA_DOES_NOT_MATCH_AUTHORIZED_TARGET", {"authorized_target_sha": _SHA_B}),
)


@pytest.mark.parametrize(
    "reason_code,overrides", _REACHABILITY_CASES, ids=[case[0] for case in _REACHABILITY_CASES]
)
def test_every_declared_reason_code_is_reachable(
    reason_code: str, overrides: dict[str, Any]
) -> None:
    decision = evaluate_adoption_record(_record(**overrides))
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert reason_code in decision["decision_reason_codes"]


def test_the_reachability_matrix_covers_every_reason_code_this_module_can_emit() -> None:
    """The control on the sweep above: every reason code this module's source can name is
    covered by exactly one crafted case, so the matrix cannot silently go stale.

    Deliberately self-contained rather than importing the AST extraction
    ``test_active_document_terminal_state._codes_from_source`` uses (GAR-R1-F2) -- this test
    file has no dependency on that one's private implementation, and this repository's tests
    are not a package other test modules import from. The two extractions agreeing is what
    the reachability property actually rests on, so this proves it independently rather than
    by construction.
    """

    tree = ast.parse(inspect.getsource(adoption_record_module))
    emittable: set[str] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr != "append":
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                emittable.add(arg.value)
    covered = {reason_code for reason_code, _ in _REACHABILITY_CASES}
    assert covered == emittable


def test_multiple_failures_are_reported_together() -> None:
    decision = evaluate_adoption_record(
        _record(comment_url="", api_read_back_confirmed=False, decision_authority="CHATGPT")
    )
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert set(decision["decision_reason_codes"]) == {
        "COMMENT_URL_NOT_A_VERIFIABLE_GITHUB_COMMENT",
        "API_READ_BACK_NOT_CONFIRMED",
        "DECISION_AUTHORITY_NOT_HUMAN",
    }


# --------------------------------------------------------------------------- #
# unreadable records raise, they are never silently refused or admitted
# --------------------------------------------------------------------------- #


def test_an_unknown_key_raises() -> None:
    with pytest.raises(AdoptionRecordError, match="unknown keys"):
        evaluate_adoption_record(_record(extra_field="not part of the schema"))


@pytest.mark.parametrize("missing_key", list(_record().keys()))
def test_a_missing_required_key_raises(missing_key: str) -> None:
    record = _record()
    del record[missing_key]
    with pytest.raises(AdoptionRecordError, match="omits required keys"):
        evaluate_adoption_record(record)


def test_a_non_object_record_raises() -> None:
    with pytest.raises(AdoptionRecordError):
        evaluate_adoption_record("this is not even a mapping")  # type: ignore[arg-type]


def test_an_unsupported_schema_version_raises() -> None:
    with pytest.raises(AdoptionRecordError, match="schema_version"):
        evaluate_adoption_record(_record(schema_version="99.9"))


def test_a_non_boolean_api_read_back_confirmed_raises() -> None:
    """``"true"`` is not ``True`` -- a string that merely looks like the claim must not be
    accepted as the claim itself."""

    with pytest.raises(AdoptionRecordError, match="api_read_back_confirmed"):
        evaluate_adoption_record(_record(api_read_back_confirmed="true"))


@pytest.mark.parametrize("field", ["comment_url", "adoption_id", "reviewed_sha"])
def test_a_non_string_field_raises(field: str) -> None:
    with pytest.raises(AdoptionRecordError):
        evaluate_adoption_record(_record(**{field: 12345}))


# --------------------------------------------------------------------------- #
# the boundary: no network call, no token, no secret, ever
# --------------------------------------------------------------------------- #


def test_the_module_source_contains_no_network_or_credential_surface() -> None:
    source = inspect.getsource(adoption_record_module)
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


def test_the_module_imports_nothing_beyond_the_standard_library_and_its_own_errors() -> None:
    tree = ast.parse(inspect.getsource(adoption_record_module))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    assert modules <= {"__future__", "copy", "re", "typing", "errors"}


def test_evaluate_adoption_record_never_writes_a_file() -> None:
    tree = ast.parse(inspect.getsource(adoption_record_module))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            assert name not in ("open", "write_text", "write_bytes")
